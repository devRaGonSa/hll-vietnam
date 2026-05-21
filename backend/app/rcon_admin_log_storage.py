"""Storage helpers for parsed RCON AdminLog events."""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Mapping
from pathlib import Path

from .config import get_storage_path, use_postgres_rcon_storage
from .rcon_admin_log_parser import parse_rcon_admin_log_entry
from .rcon_admin_log_parser import parse_rcon_player_profile_snapshot
from .rcon_historical_storage import initialize_rcon_historical_storage
from .sqlite_utils import connect_sqlite_writer


def initialize_rcon_admin_log_storage(*, db_path: Path | None = None) -> Path:
    """Create SQLite structures for parsed RCON AdminLog events."""
    if use_postgres_rcon_storage(explicit_sqlite_path=db_path):
        from .postgres_rcon_storage import initialize_postgres_rcon_storage

        initialize_postgres_rcon_storage()
        return get_storage_path()

    resolved_path = initialize_rcon_historical_storage(db_path=db_path)

    with connect_sqlite_writer(resolved_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS rcon_admin_log_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_key TEXT NOT NULL,
                external_server_id TEXT,
                event_timestamp TEXT,
                server_time INTEGER,
                relative_time TEXT,
                event_type TEXT NOT NULL,
                raw_message TEXT NOT NULL,
                canonical_message TEXT NOT NULL,
                parsed_payload_json TEXT NOT NULL,
                raw_entry_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_rcon_admin_log_events_dedupe
            ON rcon_admin_log_events(target_key, server_time, canonical_message);

            CREATE INDEX IF NOT EXISTS idx_rcon_admin_log_events_target_time
            ON rcon_admin_log_events(target_key, server_time DESC);

            CREATE INDEX IF NOT EXISTS idx_rcon_admin_log_events_type
            ON rcon_admin_log_events(event_type);

            CREATE TABLE IF NOT EXISTS rcon_player_profile_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_key TEXT NOT NULL,
                external_server_id TEXT,
                player_id TEXT NOT NULL,
                player_name TEXT NOT NULL,
                source_server_time INTEGER NOT NULL,
                event_timestamp TEXT,
                first_seen TEXT,
                sessions INTEGER,
                matches_played INTEGER,
                play_time TEXT,
                total_kills INTEGER,
                total_deaths INTEGER,
                teamkills_done INTEGER,
                teamkills_received INTEGER,
                kd_ratio REAL,
                favorite_weapons_json TEXT NOT NULL DEFAULT '{}',
                victims_json TEXT NOT NULL DEFAULT '{}',
                nemesis_json TEXT NOT NULL DEFAULT '{}',
                averages_json TEXT NOT NULL DEFAULT '{}',
                sanctions_json TEXT NOT NULL DEFAULT '{}',
                raw_content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(target_key, player_id, source_server_time)
            );

            CREATE INDEX IF NOT EXISTS idx_rcon_player_profile_snapshots_player
            ON rcon_player_profile_snapshots(target_key, player_id, source_server_time DESC);
            """
        )
        _ensure_canonical_message_column(connection)

    return resolved_path


def persist_rcon_admin_log_entries(
    *,
    target: Mapping[str, object],
    entries: list[dict[str, object]],
    db_path: Path | None = None,
) -> dict[str, int]:
    """Persist raw and parsed AdminLog entries idempotently."""
    if use_postgres_rcon_storage(explicit_sqlite_path=db_path):
        return _persist_rcon_admin_log_entries_postgres(target=target, entries=entries)

    resolved_path = initialize_rcon_admin_log_storage(db_path=db_path)
    target_key = str(target.get("target_key") or target.get("external_server_id") or "")
    if not target_key:
        raise ValueError("target must include target_key or external_server_id")

    external_server_id = target.get("external_server_id")
    inserted = 0
    duplicates = 0

    with connect_sqlite_writer(resolved_path) as connection:
        for entry in entries:
            parsed = parse_rcon_admin_log_entry(entry)
            raw_message = str(parsed.get("raw_message") or "")
            canonical_message = _canonicalize_admin_log_message(raw_message)
            cursor = connection.execute(
                """
                INSERT INTO rcon_admin_log_events (
                    target_key,
                    external_server_id,
                    event_timestamp,
                    server_time,
                    relative_time,
                    event_type,
                    raw_message,
                    canonical_message,
                    parsed_payload_json,
                    raw_entry_json
                )
                SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM rcon_admin_log_events
                    WHERE target_key = ?
                      AND server_time IS ?
                      AND canonical_message = ?
                )
                """,
                (
                    target_key,
                    external_server_id,
                    parsed.get("timestamp"),
                    parsed.get("server_time"),
                    parsed.get("relative_time"),
                    parsed.get("event_type") or "unknown",
                    raw_message,
                    canonical_message,
                    json.dumps(parsed, ensure_ascii=False, separators=(",", ":")),
                    json.dumps(entry, ensure_ascii=False, separators=(",", ":")),
                    target_key,
                    parsed.get("server_time"),
                    canonical_message,
                ),
            )
            if int(cursor.rowcount or 0):
                inserted += 1
            else:
                duplicates += 1
            _persist_profile_snapshot_if_present(
                connection,
                target_key=target_key,
                external_server_id=external_server_id,
                parsed=parsed,
            )

    return {
        "events_seen": len(entries),
        "events_inserted": inserted,
        "duplicate_events": duplicates,
    }


def _persist_profile_snapshot_if_present(
    connection: sqlite3.Connection,
    *,
    target_key: str,
    external_server_id: object,
    parsed: dict[str, object],
) -> None:
    snapshot = parse_rcon_player_profile_snapshot(parsed)
    if snapshot is None:
        return
    connection.execute(
        """
        INSERT INTO rcon_player_profile_snapshots (
            target_key,
            external_server_id,
            player_id,
            player_name,
            source_server_time,
            event_timestamp,
            first_seen,
            sessions,
            matches_played,
            play_time,
            total_kills,
            total_deaths,
            teamkills_done,
            teamkills_received,
            kd_ratio,
            favorite_weapons_json,
            victims_json,
            nemesis_json,
            averages_json,
            sanctions_json,
            raw_content
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(target_key, player_id, source_server_time) DO UPDATE SET
            external_server_id = excluded.external_server_id,
            player_name = excluded.player_name,
            event_timestamp = excluded.event_timestamp,
            first_seen = excluded.first_seen,
            sessions = excluded.sessions,
            matches_played = excluded.matches_played,
            play_time = excluded.play_time,
            total_kills = excluded.total_kills,
            total_deaths = excluded.total_deaths,
            teamkills_done = excluded.teamkills_done,
            teamkills_received = excluded.teamkills_received,
            kd_ratio = excluded.kd_ratio,
            favorite_weapons_json = excluded.favorite_weapons_json,
            victims_json = excluded.victims_json,
            nemesis_json = excluded.nemesis_json,
            averages_json = excluded.averages_json,
            sanctions_json = excluded.sanctions_json,
            raw_content = excluded.raw_content,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            target_key,
            external_server_id,
            snapshot.player_id,
            snapshot.player_name,
            snapshot.source_server_time,
            snapshot.event_timestamp,
            snapshot.first_seen,
            snapshot.sessions,
            snapshot.matches_played,
            snapshot.play_time,
            snapshot.total_kills,
            snapshot.total_deaths,
            snapshot.teamkills_done,
            snapshot.teamkills_received,
            snapshot.kd_ratio,
            json.dumps(snapshot.favorite_weapons, ensure_ascii=False, separators=(",", ":")),
            json.dumps(snapshot.victims, ensure_ascii=False, separators=(",", ":")),
            json.dumps(snapshot.nemesis, ensure_ascii=False, separators=(",", ":")),
            json.dumps(snapshot.averages, ensure_ascii=False, separators=(",", ":")),
            json.dumps(snapshot.sanctions, ensure_ascii=False, separators=(",", ":")),
            snapshot.raw_content,
        ),
    )


_PREFIX_RE = re.compile(r"^\[.*?\(\d+\)\]\s+", re.DOTALL)


def _canonicalize_admin_log_message(raw_message: str) -> str:
    """Return a stable message body for deduplication across repeated AdminLog reads."""
    normalized = str(raw_message or "").strip()
    return _PREFIX_RE.sub("", normalized).strip()


def _ensure_canonical_message_column(connection: sqlite3.Connection) -> None:
    columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(rcon_admin_log_events)").fetchall()
    }
    if "canonical_message" not in columns:
        connection.execute(
            "ALTER TABLE rcon_admin_log_events ADD COLUMN canonical_message TEXT NOT NULL DEFAULT ''"
        )
        connection.execute(
            """
            UPDATE rcon_admin_log_events
            SET canonical_message = raw_message
            WHERE canonical_message = ''
            """
        )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_rcon_admin_log_events_dedupe
        ON rcon_admin_log_events(target_key, server_time, canonical_message)
        """
    )


def list_rcon_admin_log_event_counts(*, db_path: Path | None = None) -> list[dict[str, object]]:
    """Return event counts grouped by target and event type."""
    if use_postgres_rcon_storage(explicit_sqlite_path=db_path):
        from .postgres_rcon_storage import connect_postgres_compat

        with connect_postgres_compat() as connection:
            rows = connection.execute(
                """
                SELECT
                    target_key,
                    event_type,
                    COUNT(*) AS event_count,
                    MIN(server_time) AS first_server_time,
                    MAX(server_time) AS last_server_time
                FROM rcon_admin_log_events
                GROUP BY target_key, event_type
                ORDER BY target_key ASC, event_count DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    resolved_path = db_path or get_storage_path()
    initialize_rcon_admin_log_storage(db_path=resolved_path)

    with sqlite3.connect(resolved_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT
                target_key,
                event_type,
                COUNT(*) AS event_count,
                MIN(server_time) AS first_server_time,
                MAX(server_time) AS last_server_time
            FROM rcon_admin_log_events
            GROUP BY target_key, event_type
            ORDER BY target_key ASC, event_count DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def get_latest_rcon_player_profile_summaries(
    *,
    target_key: str,
    player_ids: list[str],
    db_path: Path | None = None,
) -> dict[str, dict[str, object]]:
    """Return safe latest profile summaries keyed by player id."""
    requested_ids = [str(player_id).strip() for player_id in player_ids if str(player_id).strip()]
    if not target_key or not requested_ids:
        return {}
    if use_postgres_rcon_storage(explicit_sqlite_path=db_path):
        from .postgres_rcon_storage import connect_postgres_compat

        placeholders = ",".join("?" for _ in requested_ids)
        with connect_postgres_compat() as connection:
            rows = connection.execute(
                f"""
                SELECT snapshots.*
                FROM rcon_player_profile_snapshots AS snapshots
                INNER JOIN (
                    SELECT player_id, MAX(source_server_time) AS latest_source_server_time
                    FROM rcon_player_profile_snapshots
                    WHERE target_key = ?
                      AND player_id IN ({placeholders})
                    GROUP BY player_id
                ) AS latest
                  ON latest.player_id = snapshots.player_id
                 AND latest.latest_source_server_time = snapshots.source_server_time
                WHERE snapshots.target_key = ?
                """,
                [target_key, *requested_ids, target_key],
            ).fetchall()
        return {str(row["player_id"]): _build_safe_profile_summary(row) for row in rows}

    resolved_path = db_path or get_storage_path()
    initialize_rcon_admin_log_storage(db_path=resolved_path)
    placeholders = ",".join("?" for _ in requested_ids)
    with sqlite3.connect(resolved_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            f"""
            SELECT snapshots.*
            FROM rcon_player_profile_snapshots AS snapshots
            INNER JOIN (
                SELECT player_id, MAX(source_server_time) AS latest_source_server_time
                FROM rcon_player_profile_snapshots
                WHERE target_key = ?
                  AND player_id IN ({placeholders})
                GROUP BY player_id
            ) AS latest
              ON latest.player_id = snapshots.player_id
             AND latest.latest_source_server_time = snapshots.source_server_time
            WHERE snapshots.target_key = ?
            """,
            [target_key, *requested_ids, target_key],
        ).fetchall()

    return {str(row["player_id"]): _build_safe_profile_summary(row) for row in rows}


def _build_safe_profile_summary(row: sqlite3.Row) -> dict[str, object]:
    return {
        "player_name": row["player_name"],
        "source_server_time": row["source_server_time"],
        "event_timestamp": row["event_timestamp"],
        "first_seen": row["first_seen"],
        "sessions": row["sessions"],
        "matches_played": row["matches_played"],
        "play_time": row["play_time"],
        "totals": {
            "kills": row["total_kills"],
            "deaths": row["total_deaths"],
            "teamkills_done": row["teamkills_done"],
            "teamkills_received": row["teamkills_received"],
            "kd_ratio": row["kd_ratio"],
        },
        "favorite_weapons": _json_mapping(row["favorite_weapons_json"]),
        "victims": _json_mapping(row["victims_json"]),
        "nemesis": _json_mapping(row["nemesis_json"]),
        "averages": _json_mapping(row["averages_json"]),
        "sanctions": _json_mapping(row["sanctions_json"]),
    }


def _json_mapping(raw_value: object) -> dict[str, object]:
    if not isinstance(raw_value, str) or not raw_value.strip():
        return {}
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _persist_rcon_admin_log_entries_postgres(
    *,
    target: Mapping[str, object],
    entries: list[dict[str, object]],
) -> dict[str, int]:
    from .postgres_rcon_storage import connect_postgres_compat

    target_key = str(target.get("target_key") or target.get("external_server_id") or "")
    if not target_key:
        raise ValueError("target must include target_key or external_server_id")

    external_server_id = target.get("external_server_id")
    inserted = 0
    duplicates = 0
    with connect_postgres_compat() as connection:
        for entry in entries:
            parsed = parse_rcon_admin_log_entry(entry)
            raw_message = str(parsed.get("raw_message") or "")
            canonical_message = _canonicalize_admin_log_message(raw_message)
            cursor = connection.execute(
                """
                INSERT INTO rcon_admin_log_events (
                    target_key,
                    external_server_id,
                    event_timestamp,
                    server_time,
                    relative_time,
                    event_type,
                    raw_message,
                    canonical_message,
                    parsed_payload_json,
                    raw_entry_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT DO NOTHING
                """,
                (
                    target_key,
                    external_server_id,
                    parsed.get("timestamp"),
                    parsed.get("server_time"),
                    parsed.get("relative_time"),
                    parsed.get("event_type") or "unknown",
                    raw_message,
                    canonical_message,
                    json.dumps(parsed, ensure_ascii=False, separators=(",", ":")),
                    json.dumps(entry, ensure_ascii=False, separators=(",", ":")),
                ),
            )
            if int(cursor.rowcount or 0):
                inserted += 1
            else:
                duplicates += 1
            _persist_profile_snapshot_if_present(
                connection,
                target_key=target_key,
                external_server_id=external_server_id,
                parsed=parsed,
            )
    return {
        "events_seen": len(entries),
        "events_inserted": inserted,
        "duplicate_events": duplicates,
    }
