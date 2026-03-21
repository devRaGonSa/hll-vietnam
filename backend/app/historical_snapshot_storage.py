"""SQLite persistence for precomputed historical snapshots."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .config import get_storage_path
from .historical_models import HistoricalSnapshotRecord
from .historical_snapshots import validate_snapshot_identity
from .historical_storage import initialize_historical_storage


def initialize_historical_snapshot_storage(*, db_path: Path | None = None) -> Path:
    """Create the snapshot table used by precomputed historical payloads."""
    resolved_path = initialize_historical_storage(db_path=db_path or get_storage_path())

    with _connect(resolved_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS historical_precomputed_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_key TEXT NOT NULL,
                snapshot_type TEXT NOT NULL,
                metric TEXT NOT NULL DEFAULT '',
                window TEXT NOT NULL DEFAULT '',
                payload_json TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                source_range_start TEXT,
                source_range_end TEXT,
                is_stale INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(server_key, snapshot_type, metric, window)
            );

            CREATE INDEX IF NOT EXISTS idx_historical_precomputed_snapshots_lookup
            ON historical_precomputed_snapshots(
                server_key,
                snapshot_type,
                metric,
                window,
                generated_at DESC
            );
            """
        )

    return resolved_path


def persist_historical_snapshot(
    *,
    server_key: str,
    snapshot_type: str,
    payload: dict[str, object] | list[object],
    metric: str | None = None,
    window: str | None = None,
    generated_at: datetime | None = None,
    source_range_start: datetime | None = None,
    source_range_end: datetime | None = None,
    is_stale: bool = False,
    db_path: Path | None = None,
) -> HistoricalSnapshotRecord:
    """Insert or replace one persisted historical snapshot."""
    if not server_key.strip():
        raise ValueError("server_key is required for historical snapshots.")

    validate_snapshot_identity(snapshot_type=snapshot_type, metric=metric)
    resolved_path = initialize_historical_snapshot_storage(db_path=db_path)
    generated_at_value = generated_at or datetime.now(timezone.utc)
    payload_json = json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
    normalized_metric = metric or ""
    normalized_window = window or ""

    with _connect(resolved_path) as connection:
        connection.execute(
            """
            INSERT INTO historical_precomputed_snapshots (
                server_key,
                snapshot_type,
                metric,
                window,
                payload_json,
                generated_at,
                source_range_start,
                source_range_end,
                is_stale
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(server_key, snapshot_type, metric, window)
            DO UPDATE SET
                payload_json = excluded.payload_json,
                generated_at = excluded.generated_at,
                source_range_start = excluded.source_range_start,
                source_range_end = excluded.source_range_end,
                is_stale = excluded.is_stale,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                server_key.strip(),
                snapshot_type,
                normalized_metric,
                normalized_window,
                payload_json,
                _to_iso(generated_at_value),
                _to_iso(source_range_start),
                _to_iso(source_range_end),
                1 if is_stale else 0,
            ),
        )

    return HistoricalSnapshotRecord(
        server_key=server_key.strip(),
        snapshot_type=snapshot_type,
        metric=metric,
        window=window,
        payload_json=payload_json,
        generated_at=_as_utc(generated_at_value),
        source_range_start=_as_utc(source_range_start),
        source_range_end=_as_utc(source_range_end),
        is_stale=is_stale,
    )


def get_historical_snapshot(
    *,
    server_key: str,
    snapshot_type: str,
    metric: str | None = None,
    window: str | None = None,
    db_path: Path | None = None,
) -> dict[str, object] | None:
    """Return one persisted snapshot and decoded payload, if present."""
    validate_snapshot_identity(snapshot_type=snapshot_type, metric=metric)
    resolved_path = initialize_historical_snapshot_storage(db_path=db_path)

    with _connect(resolved_path) as connection:
        row = connection.execute(
            """
            SELECT
                server_key,
                snapshot_type,
                metric,
                window,
                payload_json,
                generated_at,
                source_range_start,
                source_range_end,
                is_stale
            FROM historical_precomputed_snapshots
            WHERE server_key = ?
              AND snapshot_type = ?
              AND metric = ?
              AND window = ?
            """,
            (server_key, snapshot_type, metric or "", window or ""),
        ).fetchone()

    if row is None:
        return None

    payload = json.loads(row["payload_json"])
    return {
        "server_key": row["server_key"],
        "snapshot_type": row["snapshot_type"],
        "metric": row["metric"] or None,
        "window": row["window"] or None,
        "generated_at": row["generated_at"],
        "source_range_start": row["source_range_start"],
        "source_range_end": row["source_range_end"],
        "is_stale": bool(row["is_stale"]),
        "payload": payload,
    }


def list_historical_snapshots(
    *,
    server_key: str | None = None,
    snapshot_type: str | None = None,
    db_path: Path | None = None,
) -> list[dict[str, object]]:
    """List persisted snapshots for validation and operational inspection."""
    resolved_path = initialize_historical_snapshot_storage(db_path=db_path)
    where_parts: list[str] = []
    params: list[object] = []

    if server_key:
        where_parts.append("server_key = ?")
        params.append(server_key)
    if snapshot_type:
        validate_snapshot_identity(snapshot_type=snapshot_type)
        where_parts.append("snapshot_type = ?")
        params.append(snapshot_type)

    where_sql = ""
    if where_parts:
        where_sql = "WHERE " + " AND ".join(where_parts)

    with _connect(resolved_path) as connection:
        rows = connection.execute(
            f"""
            SELECT
                server_key,
                snapshot_type,
                metric,
                window,
                generated_at,
                source_range_start,
                source_range_end,
                is_stale
            FROM historical_precomputed_snapshots
            {where_sql}
            ORDER BY server_key ASC, snapshot_type ASC, generated_at DESC
            """,
            params,
        ).fetchall()

    return [
        {
            "server_key": row["server_key"],
            "snapshot_type": row["snapshot_type"],
            "metric": row["metric"] or None,
            "window": row["window"] or None,
            "generated_at": row["generated_at"],
            "source_range_start": row["source_range_start"],
            "source_range_end": row["source_range_end"],
            "is_stale": bool(row["is_stale"]),
        }
        for row in rows
    ]


def _connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def _to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _as_utc(value).isoformat().replace("+00:00", "Z")


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
