"""Plan, execute, and validate the SQLite-to-PostgreSQL cutover backfill."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path
from typing import Iterable

from psycopg.types.json import Jsonb


TABLE_ORDER = (
    "game_sources",
    "servers",
    "server_snapshots",
    "historical_servers",
    "historical_maps",
    "historical_matches",
    "historical_players",
    "historical_player_match_stats",
    "historical_ingestion_runs",
    "historical_backfill_progress",
    "historical_snapshot_payloads",
    "rcon_historical_targets",
    "rcon_historical_capture_runs",
    "rcon_historical_samples",
    "rcon_historical_checkpoints",
    "rcon_historical_competitive_windows",
    "player_event_raw_ledger",
    "player_event_ingestion_runs",
    "player_event_backfill_progress",
    "elo_mmr_player_ratings",
    "elo_mmr_match_results",
    "elo_mmr_monthly_rankings",
    "elo_mmr_monthly_checkpoints",
    "elo_mmr_canonical_players",
    "elo_mmr_canonical_matches",
    "elo_mmr_canonical_player_match_facts",
    "elo_event_lineage_headers",
    "elo_event_capability_registry",
    "elo_event_garrison_details",
    "elo_event_outpost_details",
    "elo_event_revive_details",
    "elo_event_supply_details",
    "elo_event_node_details",
    "elo_event_repair_details",
    "elo_event_mine_details",
    "elo_event_commander_ability_details",
    "elo_event_strongpoint_presence_details",
    "elo_event_role_assignment_details",
    "elo_event_disconnect_leave_admin_details",
    "elo_event_death_classification_details",
    "elo_mmr_normalization_buckets",
    "elo_mmr_normalization_baselines",
)
BACKFILL_MANIFEST_TABLE = "sqlite_postgres_backfill_manifest"
EXACT_POSTGRES_COUNT_THRESHOLD = 100_000


def main() -> int:
    args = build_arg_parser().parse_args()
    backend_root = Path(__file__).resolve().parents[1]
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))

    sqlite_path = Path(args.sqlite_path).resolve()
    snapshot_dir = Path(args.snapshot_dir).resolve()
    sqlite_exists = sqlite_path.exists()
    snapshot_file_count = len(list(snapshot_dir.rglob("*.json"))) if snapshot_dir.exists() else 0

    plan_payload = {
        "mode": args.mode,
        "sqlite_path": str(sqlite_path),
        "sqlite_exists": sqlite_exists,
        "snapshot_dir": str(snapshot_dir),
        "snapshot_dir_exists": snapshot_dir.exists(),
        "snapshot_file_count": snapshot_file_count,
        "strategy": {
            "relational_backfill": "direct-sqlite-read-into-postgresql",
            "snapshot_strategy": "regenerate-from-postgresql-after-relational-backfill",
            "optional_snapshot_fallback": "keep-legacy-json-as-read-only-rollback-artifact-until-cutover-signoff",
        },
        "cutover_order": [
            "postgresql migrations",
            "sqlite relational backfill",
            "parity validation",
            "historical snapshot regeneration in postgresql",
            "backend api",
            "historical runner",
            "rcon historical worker",
            "player event worker",
            "elo/mmr rebuild and reads",
        ],
    }

    if args.mode == "plan":
        plan_payload["sqlite_table_counts"] = _list_sqlite_table_counts(sqlite_path) if sqlite_exists else {}
        print(json.dumps(plan_payload, ensure_ascii=True, indent=2))
        return 0

    from app.postgres_utils import apply_postgres_migrations, connect_postgres, probe_postgres_connection

    probe = probe_postgres_connection()
    migrations = apply_postgres_migrations()

    if args.mode == "execute":
        if not sqlite_exists:
            raise FileNotFoundError(f"SQLite source file not found: {sqlite_path}")
        execution = execute_backfill(
            sqlite_path=sqlite_path,
            connect_postgres=connect_postgres,
            truncate_target_first=args.truncate_target_first,
            batch_size=args.batch_size,
        )
        print(
            json.dumps(
                {
                    **plan_payload,
                    "postgres_probe": probe,
                    "migrations": migrations,
                    "execution": execution,
                },
                ensure_ascii=True,
                indent=2,
                default=str,
            )
        )
        return 0

    validation = validate_counts(sqlite_path=sqlite_path, connect_postgres=connect_postgres)
    print(
        json.dumps(
            {
                **plan_payload,
                "postgres_probe": probe,
                "migrations": migrations,
                "validation": validation,
            },
            ensure_ascii=True,
            indent=2,
            default=str,
        )
    )
    return 0 if not validation["mismatches"] else 1


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plan, execute, or validate the SQLite-to-PostgreSQL migration cutover.",
    )
    parser.add_argument("mode", choices=("plan", "execute", "validate"))
    parser.add_argument(
        "--sqlite-path",
        default=str(Path(__file__).resolve().parents[1] / "data" / "hll_vietnam_dev.sqlite3"),
        help="legacy SQLite file used as direct-read backfill source",
    )
    parser.add_argument(
        "--snapshot-dir",
        default=str(Path(__file__).resolve().parents[1] / "data" / "snapshots"),
        help="legacy snapshot directory kept only for parity inspection and rollback artifacts",
    )
    parser.add_argument(
        "--truncate-target-first",
        action="store_true",
        help="truncate PostgreSQL target tables before inserting copied rows",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=5000,
        help="rows per PostgreSQL insert batch during execute mode",
    )
    return parser


def execute_backfill(
    *,
    sqlite_path: Path,
    connect_postgres,
    truncate_target_first: bool,
    batch_size: int,
) -> dict[str, object]:
    if batch_size <= 0:
        raise ValueError("--batch-size must be positive.")
    sqlite_connection = sqlite3.connect(sqlite_path)
    sqlite_connection.row_factory = sqlite3.Row
    copied_tables: list[dict[str, object]] = []
    started_at = time.perf_counter()
    try:
        with connect_postgres() as postgres_connection:
            with postgres_connection.cursor() as cursor:
                cursor.execute("SET client_encoding TO 'UTF8'")
                cursor.execute("SET synchronous_commit TO OFF")
            _ensure_backfill_manifest_table(postgres_connection)
            if truncate_target_first:
                _truncate_postgres_tables(postgres_connection, TABLE_ORDER)
                _clear_backfill_manifest(postgres_connection, sqlite_path=sqlite_path)
                postgres_connection.commit()
            for table_name in TABLE_ORDER:
                if not _sqlite_table_exists(sqlite_connection, table_name):
                    copied_tables.append({"table": table_name, "status": "source-missing", "rows_copied": 0})
                    continue
                table_started_at = time.perf_counter()
                row_count = _copy_table(
                    sqlite_connection,
                    postgres_connection,
                    table_name,
                    batch_size=batch_size,
                )
                postgres_connection.commit()
                _upsert_backfill_manifest_row(
                    postgres_connection,
                    sqlite_path=sqlite_path,
                    table_name=table_name,
                    sqlite_rows_copied=row_count,
                    batch_size=batch_size,
                )
                postgres_connection.commit()
                copied_tables.append(
                    {
                        "table": table_name,
                        "status": "copied",
                        "rows_copied": row_count,
                        "elapsed_seconds": round(time.perf_counter() - table_started_at, 3),
                    }
                )
    finally:
        sqlite_connection.close()
    return {
        "truncate_target_first": truncate_target_first,
        "batch_size": batch_size,
        "tables": copied_tables,
        "elapsed_seconds": round(time.perf_counter() - started_at, 3),
        "next_step": "Run `python scripts/postgresql-backfill.py validate` after execute completes.",
    }


def validate_counts(*, sqlite_path: Path, connect_postgres) -> dict[str, object]:
    sqlite_counts = _list_sqlite_table_counts(sqlite_path) if sqlite_path.exists() else {}
    with connect_postgres(autocommit=True) as postgres_connection:
        manifest_rows = _load_backfill_manifest(postgres_connection, sqlite_path=sqlite_path)
        postgres_counts: dict[str, int | None] = {}
        table_validation: list[dict[str, object]] = []
        for table_name in TABLE_ORDER:
            sqlite_rows = sqlite_counts.get(table_name)
            manifest_entry = manifest_rows.get(table_name)
            manifest_rows_copied = (
                int(manifest_entry["sqlite_rows_copied"])
                if manifest_entry and manifest_entry.get("sqlite_rows_copied") is not None
                else None
            )
            if sqlite_rows is None:
                postgres_rows = _count_postgres_rows(postgres_connection, table_name)
                postgres_counts[table_name] = postgres_rows
                table_validation.append(
                    {
                        "table": table_name,
                        "method": "postgres-exact-count-only",
                        "sqlite_rows": None,
                        "postgres_rows": postgres_rows,
                        "status": "postgres-only",
                    }
                )
                continue
            if sqlite_rows <= EXACT_POSTGRES_COUNT_THRESHOLD:
                postgres_rows = _count_postgres_rows(postgres_connection, table_name)
                postgres_counts[table_name] = postgres_rows
                table_validation.append(
                    {
                        "table": table_name,
                        "method": "sqlite-count-vs-postgres-count",
                        "sqlite_rows": sqlite_rows,
                        "postgres_rows": postgres_rows,
                        "status": "ok" if sqlite_rows == postgres_rows else "count-mismatch",
                    }
                )
                continue

            postgres_counts[table_name] = manifest_rows_copied
            table_validation.append(
                {
                    "table": table_name,
                    "method": "sqlite-count-vs-execute-manifest",
                    "sqlite_rows": sqlite_rows,
                    "postgres_rows": manifest_rows_copied,
                    "status": (
                        "ok"
                        if manifest_rows_copied is not None and sqlite_rows == manifest_rows_copied
                        else "manifest-missing-or-mismatch"
                    ),
                    "manifest_executed_at": manifest_entry.get("executed_at") if manifest_entry else None,
                }
            )
    mismatches = [
        {
            "table": table_name,
            "sqlite_rows": sqlite_counts.get(table_name),
            "postgres_rows": postgres_counts.get(table_name),
        }
        for table_name in TABLE_ORDER
        if sqlite_counts.get(table_name) is not None and sqlite_counts.get(table_name) != postgres_counts.get(table_name)
    ]
    return {
        "sqlite_counts": sqlite_counts,
        "postgres_counts": postgres_counts,
        "table_validation": table_validation,
        "mismatches": mismatches,
        "status": "ok" if not mismatches else "count-mismatch",
    }


def _copy_table(
    sqlite_connection: sqlite3.Connection,
    postgres_connection,
    table_name: str,
    *,
    batch_size: int,
) -> int:
    source_columns = _list_sqlite_columns(sqlite_connection, table_name)
    if not source_columns:
        return 0
    postgres_columns = _list_postgres_columns(postgres_connection, table_name)
    postgres_column_types = {
        str(column["column_name"]): str(column["data_type"]) for column in postgres_columns
    }
    insert_columns = _resolve_insert_columns(
        table_name=table_name,
        source_columns=source_columns,
        postgres_columns=postgres_columns,
    )
    select_sql = (
        f'SELECT {", ".join(_quote_identifier(column) for column in source_columns)} '
        f'FROM {_quote_identifier(table_name)}'
    )
    sqlite_cursor = sqlite_connection.execute(select_sql)
    first_batch = sqlite_cursor.fetchmany(batch_size)
    if not first_batch:
        _reset_postgres_identity(postgres_connection, table_name)
        return 0

    column_list = ", ".join(_quote_identifier(column) for column in insert_columns)
    placeholder_list = ", ".join(["%s"] * len(insert_columns))
    insert_sql = f"INSERT INTO {_quote_identifier(table_name)} ({column_list}) VALUES ({placeholder_list})"
    copied_row_count = 0
    batch_rows = first_batch
    with postgres_connection.cursor() as cursor:
        while batch_rows:
            normalized_rows = [
                tuple(
                    _normalize_value(
                        _resolve_source_value(table_name=table_name, row=row, column_name=column),
                        postgres_column_types.get(column),
                    )
                    for column in insert_columns
                )
                for row in batch_rows
            ]
            cursor.executemany(insert_sql, normalized_rows)
            copied_row_count += len(batch_rows)
            batch_rows = sqlite_cursor.fetchmany(batch_size)
    _reset_postgres_identity(postgres_connection, table_name)
    return copied_row_count


def _truncate_postgres_tables(postgres_connection, table_names: Iterable[str]) -> None:
    joined_tables = ", ".join(_quote_identifier(table_name) for table_name in reversed(tuple(table_names)))
    with postgres_connection.cursor() as cursor:
        cursor.execute(f"TRUNCATE TABLE {joined_tables} RESTART IDENTITY CASCADE")


def _ensure_backfill_manifest_table(postgres_connection) -> None:
    with postgres_connection.cursor() as cursor:
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {BACKFILL_MANIFEST_TABLE} (
                sqlite_path TEXT NOT NULL,
                table_name TEXT NOT NULL,
                sqlite_rows_copied BIGINT NOT NULL,
                batch_size INTEGER NOT NULL,
                executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (sqlite_path, table_name)
            )
            """
        )


def _clear_backfill_manifest(postgres_connection, *, sqlite_path: Path) -> None:
    with postgres_connection.cursor() as cursor:
        cursor.execute(
            f"DELETE FROM {BACKFILL_MANIFEST_TABLE} WHERE sqlite_path = %s",
            (str(sqlite_path),),
        )


def _upsert_backfill_manifest_row(
    postgres_connection,
    *,
    sqlite_path: Path,
    table_name: str,
    sqlite_rows_copied: int,
    batch_size: int,
) -> None:
    with postgres_connection.cursor() as cursor:
        cursor.execute(
            f"""
            INSERT INTO {BACKFILL_MANIFEST_TABLE} (
                sqlite_path,
                table_name,
                sqlite_rows_copied,
                batch_size,
                executed_at
            )
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (sqlite_path, table_name)
            DO UPDATE SET
                sqlite_rows_copied = EXCLUDED.sqlite_rows_copied,
                batch_size = EXCLUDED.batch_size,
                executed_at = EXCLUDED.executed_at
            """,
            (str(sqlite_path), table_name, sqlite_rows_copied, batch_size),
        )


def _load_backfill_manifest(postgres_connection, *, sqlite_path: Path) -> dict[str, dict[str, object]]:
    with postgres_connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT table_name, sqlite_rows_copied, batch_size, executed_at
            FROM {BACKFILL_MANIFEST_TABLE}
            WHERE sqlite_path = %s
            """,
            (str(sqlite_path),),
        )
        rows = cursor.fetchall()
    return {str(row["table_name"]): row for row in rows}


def _reset_postgres_identity(postgres_connection, table_name: str) -> None:
    with postgres_connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s AND column_name = 'id'
            """,
            (table_name,),
        )
        if cursor.fetchone() is None:
            return
        cursor.execute(
            "SELECT pg_get_serial_sequence(%s, 'id') AS sequence_name",
            (table_name,),
        )
        row = cursor.fetchone() or {}
        sequence_name = row.get("sequence_name")
        if not sequence_name:
            return
        cursor.execute(
            f"""
            SELECT setval(
                %s,
                COALESCE((SELECT MAX(id) FROM {_quote_identifier(table_name)}), 1),
                EXISTS (SELECT 1 FROM {_quote_identifier(table_name)})
            )
            """,
            (sequence_name,),
        )


def _list_sqlite_table_counts(sqlite_path: Path) -> dict[str, int]:
    if not sqlite_path.exists():
        return {}
    connection = sqlite3.connect(sqlite_path)
    try:
        return {
            table_name: _count_sqlite_rows(connection, table_name)
            for table_name in TABLE_ORDER
            if _sqlite_table_exists(connection, table_name)
        }
    finally:
        connection.close()


def _count_sqlite_rows(connection: sqlite3.Connection, table_name: str) -> int:
    row = connection.execute(f"SELECT COUNT(*) FROM {_quote_identifier(table_name)}").fetchone()
    return int(row[0] or 0)


def _count_postgres_rows(connection, table_name: str) -> int:
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(*) AS row_count FROM {_quote_identifier(table_name)}")
        row = cursor.fetchone() or {}
    return int(row.get("row_count") or 0)


def _list_sqlite_columns(connection: sqlite3.Connection, table_name: str) -> list[str]:
    rows = connection.execute(f"PRAGMA table_info({_quote_identifier(table_name)})").fetchall()
    return [str(row[1]) for row in rows]


def _list_postgres_columns(connection, table_name: str) -> list[dict[str, object]]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table_name,),
        )
        rows = cursor.fetchall()
    return list(rows)


def _sqlite_table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def _normalize_value(value: object, postgres_type: str | None) -> object:
    if value is None or postgres_type is None:
        return value
    if postgres_type == "boolean":
        return bool(value)
    if postgres_type in {"json", "jsonb"}:
        if isinstance(value, str):
            return Jsonb(json.loads(value))
        if isinstance(value, (dict, list)):
            return Jsonb(value)
    return value


def _resolve_insert_columns(
    *,
    table_name: str,
    source_columns: list[str],
    postgres_columns: list[dict[str, object]],
) -> list[str]:
    source_set = set(source_columns)
    insert_columns = list(source_columns)
    for column in postgres_columns:
        column_name = str(column["column_name"])
        if column_name in source_set:
            continue
        if _has_derived_source_value(table_name=table_name, column_name=column_name):
            insert_columns.append(column_name)
            continue
        is_nullable = str(column.get("is_nullable") or "").upper() == "YES"
        has_default = column.get("column_default") is not None
        if not is_nullable and not has_default:
            raise RuntimeError(
                f"Backfill mapping for required column {table_name}.{column_name} is missing."
            )
    return insert_columns


def _has_derived_source_value(*, table_name: str, column_name: str) -> bool:
    return table_name == "historical_ingestion_runs" and column_name == "run_kind"


def _resolve_source_value(*, table_name: str, row: sqlite3.Row, column_name: str) -> object:
    if column_name in row.keys():
        return row[column_name]
    if table_name == "historical_ingestion_runs" and column_name == "run_kind":
        return row["mode"]
    raise KeyError(f"No source value available for {table_name}.{column_name}")


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


if __name__ == "__main__":
    raise SystemExit(main())
