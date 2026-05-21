"""Idempotent phase-2 migration from displayed SQLite/files into PostgreSQL."""

from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from contextlib import closing
from pathlib import Path
from typing import Any

from .config import get_storage_path
from .postgres_display_storage import (
    connect_postgres as connect_display_postgres,
    initialize_postgres_display_storage,
    persist_snapshot_record,
)
from .postgres_rcon_storage import initialize_postgres_rcon_storage


RCON_TABLES = (
    "rcon_historical_targets",
    "rcon_historical_capture_runs",
    "rcon_historical_samples",
    "rcon_historical_checkpoints",
    "rcon_historical_competitive_windows",
    "rcon_admin_log_events",
    "rcon_player_profile_snapshots",
    "rcon_materialized_matches",
    "rcon_match_player_stats",
    "rcon_scoreboard_match_candidates",
)
DISPLAY_TABLES = (
    "game_sources",
    "servers",
    "server_snapshots",
    "historical_servers",
    "historical_maps",
    "historical_matches",
    "historical_players",
    "historical_player_match_stats",
    "player_event_raw_ledger",
)
SKIP_SLUG = "comunidad-hispana-03"


def migrate_sqlite_to_postgres() -> dict[str, object]:
    """Copy displayed legacy data to PostgreSQL without deleting legacy sources."""
    initialize_postgres_rcon_storage()
    initialize_postgres_display_storage()
    summary: dict[str, object] = {
        "status": "ok",
        "source_paths": [],
        "migrated_tables": [],
        "migrated_domains": [],
        "rows_read": {},
        "rows_inserted": {},
        "rows_updated": {},
        "rows_skipped": {},
        "errors": [],
    }
    table_totals: dict[str, dict[str, int]] = defaultdict(
        lambda: {"read": 0, "inserted": 0, "updated": 0, "skipped": 0}
    )
    for db_path in _discover_sqlite_paths():
        summary["source_paths"].append(str(db_path))
        try:
            _migrate_sqlite_path(db_path, table_totals)
        except Exception as error:  # noqa: BLE001 - report all source failures
            summary["errors"].append({"source_path": str(db_path), "error": str(error)})

    snapshots_root = get_storage_path().parent / "snapshots"
    if snapshots_root.exists():
        summary["source_paths"].append(str(snapshots_root))
        _migrate_snapshot_files(snapshots_root, table_totals, summary["errors"])
    _sync_sequences()
    summary["migrated_tables"] = sorted(table_totals)
    summary["migrated_domains"] = [
        "rcon-admin-log-events",
        "rcon-player-profile-snapshots",
        "rcon-historical-capture-samples-and-windows",
        "rcon-materialized-matches",
        "rcon-materialized-player-stats",
        "rcon-safe-scoreboard-candidates",
        "public-scoreboard-historical-matches-and-player-stats",
        "weekly-and-monthly-scoreboard-rankings",
        "displayed-historical-snapshots",
        "live-server-summary-cache",
        "player-event-ledger",
    ]
    for table_name, totals in sorted(table_totals.items()):
        summary["rows_read"][table_name] = totals["read"]
        summary["rows_inserted"][table_name] = totals["inserted"]
        summary["rows_updated"][table_name] = totals["updated"]
        summary["rows_skipped"][table_name] = totals["skipped"]
    summary["status"] = "ok" if not summary["errors"] else "completed-with-errors"
    return summary


def _migrate_sqlite_path(db_path: Path, totals: dict[str, dict[str, int]]) -> None:
    with closing(sqlite3.connect(db_path)) as sqlite_connection:
        sqlite_connection.row_factory = sqlite3.Row
        available_tables = {
            row["name"]
            for row in sqlite_connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        tables = [table for table in (*RCON_TABLES, *DISPLAY_TABLES) if table in available_tables]
        with connect_display_postgres() as postgres_connection:
            postgres_columns = {
                table: _postgres_columns(postgres_connection, table)
                for table in tables
            }
            historical_server_ids = _legacy_server03_ids(sqlite_connection)
            historical_match_ids = _legacy_match_ids(sqlite_connection, historical_server_ids)
            legacy_rcon_target_ids = _legacy_rcon_target03_ids(sqlite_connection)
            for table_name in tables:
                _copy_table(
                    sqlite_connection,
                    postgres_connection,
                    table_name=table_name,
                    postgres_columns=postgres_columns[table_name],
                    totals=totals[table_name],
                    historical_server_ids=historical_server_ids,
                    historical_match_ids=historical_match_ids,
                    legacy_rcon_target_ids=legacy_rcon_target_ids,
                )


def _copy_table(
    sqlite_connection: sqlite3.Connection,
    postgres_connection: Any,
    *,
    table_name: str,
    postgres_columns: list[str],
    totals: dict[str, int],
    historical_server_ids: set[int],
    historical_match_ids: set[int],
    legacy_rcon_target_ids: set[int],
) -> None:
    sqlite_columns = [
        str(row["name"])
        for row in sqlite_connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    ]
    columns = [column for column in sqlite_columns if column in postgres_columns]
    if not columns:
        return
    rows = sqlite_connection.execute(
        f"SELECT {', '.join(columns)} FROM {table_name}"
    ).fetchall()
    placeholders = ", ".join(["%s"] * len(columns))
    sql = (
        f"INSERT INTO {table_name} ({', '.join(columns)}) "
        f"VALUES ({placeholders}) ON CONFLICT DO NOTHING"
    )
    values: list[tuple[object, ...]] = []
    for row in rows:
        totals["read"] += 1
        row_dict = dict(row)
        if _skip_row(
            table_name,
            row_dict,
            historical_server_ids=historical_server_ids,
            historical_match_ids=historical_match_ids,
            legacy_rcon_target_ids=legacy_rcon_target_ids,
        ):
            totals["skipped"] += 1
            continue
        values.append(tuple(_postgres_value(column, row_dict[column]) for column in columns))
    with postgres_connection.cursor() as cursor:
        for start in range(0, len(values), 1000):
            batch = values[start : start + 1000]
            cursor.executemany(sql, batch)
            inserted = max(0, int(cursor.rowcount or 0))
            totals["inserted"] += inserted
            totals["skipped"] += len(batch) - inserted


def _migrate_snapshot_files(
    snapshots_root: Path,
    totals: dict[str, dict[str, int]],
    errors: list[object],
) -> None:
    snapshot_totals = totals["displayed_historical_snapshots"]
    for snapshot_path in sorted(snapshots_root.glob("*/*.json")):
        snapshot_totals["read"] += 1
        try:
            document = json.loads(snapshot_path.read_text(encoding="utf-8"))
            if str(document.get("server_key") or "") == SKIP_SLUG:
                snapshot_totals["skipped"] += 1
                continue
            before = _snapshot_exists(document)
            persist_snapshot_record(document)
            snapshot_totals["updated" if before else "inserted"] += 1
        except Exception as error:  # noqa: BLE001 - keep migrating neighboring snapshots
            snapshot_totals["skipped"] += 1
            errors.append({"source_path": str(snapshot_path), "error": str(error)})


def _snapshot_exists(document: dict[str, object]) -> bool:
    with connect_display_postgres() as connection:
        row = connection.execute(
            """
            SELECT 1 FROM displayed_historical_snapshots
            WHERE server_key = %s AND snapshot_type = %s AND metric = %s AND snapshot_window = %s
            """,
            (
                str(document.get("server_key") or ""),
                str(document.get("snapshot_type") or ""),
                str(document.get("metric") or ""),
                str(document.get("window") or ""),
            ),
        ).fetchone()
    return bool(row)


def _skip_row(
    table_name: str,
    row: dict[str, object],
    *,
    historical_server_ids: set[int],
    historical_match_ids: set[int],
    legacy_rcon_target_ids: set[int],
) -> bool:
    if row.get("server_slug") == SKIP_SLUG or row.get("slug") == SKIP_SLUG:
        return True
    if row.get("external_server_id") == SKIP_SLUG or row.get("target_key") == SKIP_SLUG:
        return True
    if table_name == "historical_matches" and row.get("historical_server_id") in historical_server_ids:
        return True
    if (
        table_name == "historical_player_match_stats"
        and row.get("historical_match_id") in historical_match_ids
    ):
        return True
    if table_name == "rcon_historical_samples" and row.get("target_id") in legacy_rcon_target_ids:
        return True
    if table_name == "rcon_historical_checkpoints" and row.get("target_id") in legacy_rcon_target_ids:
        return True
    if table_name == "rcon_historical_competitive_windows" and row.get("target_id") in legacy_rcon_target_ids:
        return True
    return False


def _legacy_server03_ids(connection: sqlite3.Connection) -> set[int]:
    if not _has_table(connection, "historical_servers"):
        return set()
    return {
        int(row["id"])
        for row in connection.execute(
            "SELECT id FROM historical_servers WHERE slug = ?",
            (SKIP_SLUG,),
        ).fetchall()
    }


def _legacy_rcon_target03_ids(connection: sqlite3.Connection) -> set[int]:
    if not _has_table(connection, "rcon_historical_targets"):
        return set()
    return {
        int(row["id"])
        for row in connection.execute(
            """
            SELECT id FROM rcon_historical_targets
            WHERE external_server_id = ? OR target_key = ?
            """,
            (SKIP_SLUG, SKIP_SLUG),
        ).fetchall()
    }


def _legacy_match_ids(connection: sqlite3.Connection, historical_server_ids: set[int]) -> set[int]:
    if not historical_server_ids or not _has_table(connection, "historical_matches"):
        return set()
    placeholders = ", ".join(["?"] * len(historical_server_ids))
    return {
        int(row["id"])
        for row in connection.execute(
            f"SELECT id FROM historical_matches WHERE historical_server_id IN ({placeholders})",
            tuple(sorted(historical_server_ids)),
        ).fetchall()
    }


def _postgres_columns(connection: Any, table_name: str) -> list[str]:
    rows = connection.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table_name,),
    ).fetchall()
    return [str(row["column_name"]) for row in rows]


def _sync_sequences() -> None:
    tables = (
        "game_sources",
        "servers",
        "server_snapshots",
        "historical_servers",
        "historical_maps",
        "historical_matches",
        "historical_players",
        "historical_player_match_stats",
        "player_event_raw_ledger",
        "rcon_historical_targets",
        "rcon_historical_capture_runs",
        "rcon_historical_samples",
        "rcon_historical_competitive_windows",
        "rcon_admin_log_events",
        "rcon_player_profile_snapshots",
        "rcon_materialized_matches",
        "rcon_match_player_stats",
        "rcon_scoreboard_match_candidates",
    )
    with connect_display_postgres() as connection:
        for table_name in tables:
            connection.execute(
                f"""
                SELECT setval(
                    pg_get_serial_sequence(%s, 'id'),
                    GREATEST(COALESCE((SELECT MAX(id) FROM {table_name}), 1), 1),
                    TRUE
                )
                """,
                (table_name,),
            )


def _discover_sqlite_paths() -> list[Path]:
    configured = get_storage_path()
    candidates = {configured}
    if configured.parent.exists():
        candidates.update(configured.parent.glob("*.sqlite*"))
    return sorted(
        path
        for path in candidates
        if path.exists()
        and path.is_file()
        and not str(path).endswith(("-shm", "-wal"))
    )


def _has_table(connection: sqlite3.Connection, table_name: str) -> bool:
    return bool(
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table_name,),
        ).fetchone()
    )


def _postgres_value(column: str, value: object) -> object:
    if column in {"is_active", "is_teamkill"}:
        return bool(value)
    return value


def main() -> None:
    print(json.dumps(migrate_sqlite_to_postgres(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
