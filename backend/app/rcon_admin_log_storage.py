"""Storage helpers for parsed RCON AdminLog events."""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Mapping
from pathlib import Path

from .config import get_storage_path
from .rcon_admin_log_parser import parse_rcon_admin_log_entry
from .rcon_historical_storage import initialize_rcon_historical_storage
from .sqlite_utils import connect_sqlite_writer


def initialize_rcon_admin_log_storage(*, db_path: Path | None = None) -> Path:
    """Create SQLite structures for parsed RCON AdminLog events."""
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

    return {
        "events_seen": len(entries),
        "events_inserted": inserted,
        "duplicate_events": duplicates,
    }


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
