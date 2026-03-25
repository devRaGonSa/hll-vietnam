"""Separate storage and run tracking for prospective RCON historical capture."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

from .config import get_storage_path


def initialize_rcon_historical_storage(*, db_path: Path | None = None) -> Path:
    """Create the SQLite structures used by prospective RCON capture."""
    resolved_path = db_path or get_storage_path()
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    with _connect(resolved_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS rcon_historical_targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_key TEXT NOT NULL UNIQUE,
                external_server_id TEXT,
                display_name TEXT NOT NULL,
                host TEXT NOT NULL,
                port INTEGER NOT NULL,
                region TEXT,
                game_port INTEGER,
                query_port INTEGER,
                source_name TEXT NOT NULL,
                last_configured_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS rcon_historical_capture_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mode TEXT NOT NULL,
                status TEXT NOT NULL,
                target_scope TEXT,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                targets_seen INTEGER NOT NULL DEFAULT 0,
                samples_inserted INTEGER NOT NULL DEFAULT 0,
                duplicate_samples INTEGER NOT NULL DEFAULT 0,
                failed_targets INTEGER NOT NULL DEFAULT 0,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS rcon_historical_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                target_id INTEGER NOT NULL,
                capture_run_id INTEGER,
                captured_at TEXT NOT NULL,
                source_kind TEXT NOT NULL,
                status TEXT NOT NULL,
                players INTEGER,
                max_players INTEGER,
                current_map TEXT,
                normalized_payload_json TEXT NOT NULL,
                raw_payload_json TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(target_id, captured_at),
                FOREIGN KEY (target_id) REFERENCES rcon_historical_targets(id),
                FOREIGN KEY (capture_run_id) REFERENCES rcon_historical_capture_runs(id)
            );

            CREATE TABLE IF NOT EXISTS rcon_historical_checkpoints (
                target_id INTEGER PRIMARY KEY,
                last_successful_capture_at TEXT,
                last_sample_at TEXT,
                last_run_id INTEGER,
                last_run_status TEXT,
                last_error TEXT,
                last_error_at TEXT,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (target_id) REFERENCES rcon_historical_targets(id),
                FOREIGN KEY (last_run_id) REFERENCES rcon_historical_capture_runs(id)
            );

            CREATE INDEX IF NOT EXISTS idx_rcon_historical_samples_target_time
            ON rcon_historical_samples(target_id, captured_at DESC);
            """
        )

    return resolved_path


def start_rcon_historical_capture_run(
    *,
    mode: str,
    target_scope: str,
    db_path: Path | None = None,
) -> int:
    """Create one run row for prospective RCON capture."""
    resolved_path = initialize_rcon_historical_storage(db_path=db_path)
    with _connect(resolved_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO rcon_historical_capture_runs (
                mode,
                status,
                target_scope,
                started_at
            ) VALUES (?, 'running', ?, ?)
            """,
            (mode, target_scope, _utc_now_iso()),
        )
        return int(cursor.lastrowid)


def finalize_rcon_historical_capture_run(
    run_id: int,
    *,
    status: str,
    targets_seen: int,
    samples_inserted: int,
    duplicate_samples: int,
    failed_targets: int,
    notes: str | None = None,
    db_path: Path | None = None,
) -> None:
    """Finalize one prospective RCON capture run."""
    resolved_path = initialize_rcon_historical_storage(db_path=db_path)
    with _connect(resolved_path) as connection:
        connection.execute(
            """
            UPDATE rcon_historical_capture_runs
            SET status = ?,
                completed_at = ?,
                targets_seen = ?,
                samples_inserted = ?,
                duplicate_samples = ?,
                failed_targets = ?,
                notes = ?
            WHERE id = ?
            """,
            (
                status,
                _utc_now_iso(),
                targets_seen,
                samples_inserted,
                duplicate_samples,
                failed_targets,
                notes,
                run_id,
            ),
        )


def persist_rcon_historical_sample(
    *,
    run_id: int,
    captured_at: str,
    target: Mapping[str, object],
    normalized_payload: Mapping[str, object],
    raw_payload: Mapping[str, object] | None,
    db_path: Path | None = None,
) -> dict[str, int]:
    """Persist one prospective RCON sample and refresh its checkpoint."""
    resolved_path = initialize_rcon_historical_storage(db_path=db_path)
    with _connect(resolved_path) as connection:
        target_id = _upsert_target(connection, target=target)
        cursor = connection.execute(
            """
            INSERT OR IGNORE INTO rcon_historical_samples (
                target_id,
                capture_run_id,
                captured_at,
                source_kind,
                status,
                players,
                max_players,
                current_map,
                normalized_payload_json,
                raw_payload_json
            ) VALUES (?, ?, ?, 'rcon-live-sample', ?, ?, ?, ?, ?, ?)
            """,
            (
                target_id,
                run_id,
                captured_at,
                normalized_payload.get("status") or "unknown",
                normalized_payload.get("players"),
                normalized_payload.get("max_players"),
                normalized_payload.get("current_map"),
                json.dumps(dict(normalized_payload), separators=(",", ":")),
                json.dumps(dict(raw_payload), separators=(",", ":")) if raw_payload else None,
            ),
        )
        inserted = int(cursor.rowcount or 0)
        _upsert_checkpoint_success(
            connection,
            target_id=target_id,
            run_id=run_id,
            captured_at=captured_at,
        )
        return {
            "samples_inserted": inserted,
            "duplicate_samples": 0 if inserted else 1,
        }


def mark_rcon_historical_capture_failure(
    *,
    run_id: int,
    target: Mapping[str, object],
    error_message: str,
    db_path: Path | None = None,
) -> None:
    """Persist failure metadata for one target inside a capture run."""
    resolved_path = initialize_rcon_historical_storage(db_path=db_path)
    with _connect(resolved_path) as connection:
        target_id = _upsert_target(connection, target=target)
        connection.execute(
            """
            INSERT INTO rcon_historical_checkpoints (
                target_id,
                last_run_id,
                last_run_status,
                last_error,
                last_error_at
            ) VALUES (?, ?, 'failed', ?, ?)
            ON CONFLICT(target_id) DO UPDATE SET
                last_run_id = excluded.last_run_id,
                last_run_status = excluded.last_run_status,
                last_error = excluded.last_error,
                last_error_at = excluded.last_error_at,
                updated_at = CURRENT_TIMESTAMP
            """,
            (target_id, run_id, error_message, _utc_now_iso()),
        )


def list_rcon_historical_target_statuses(
    *,
    db_path: Path | None = None,
) -> list[dict[str, object]]:
    """Return per-target coverage and freshness for prospective RCON capture."""
    resolved_path = initialize_rcon_historical_storage(db_path=db_path)
    with _connect(resolved_path) as connection:
        rows = connection.execute(
            """
            SELECT
                targets.target_key,
                targets.external_server_id,
                targets.display_name,
                targets.host,
                targets.port,
                targets.region,
                targets.source_name,
                checkpoints.last_successful_capture_at,
                checkpoints.last_sample_at,
                checkpoints.last_run_id,
                checkpoints.last_run_status,
                checkpoints.last_error,
                checkpoints.last_error_at,
                (
                    SELECT MIN(samples.captured_at)
                    FROM rcon_historical_samples AS samples
                    WHERE samples.target_id = targets.id
                ) AS first_sample_at,
                (
                    SELECT MAX(samples.captured_at)
                    FROM rcon_historical_samples AS samples
                    WHERE samples.target_id = targets.id
                ) AS latest_sample_at,
                (
                    SELECT COUNT(*)
                    FROM rcon_historical_samples AS samples
                    WHERE samples.target_id = targets.id
                ) AS sample_count
            FROM rcon_historical_targets AS targets
            LEFT JOIN rcon_historical_checkpoints AS checkpoints
                ON checkpoints.target_id = targets.id
            ORDER BY targets.display_name ASC, targets.target_key ASC
            """
        ).fetchall()
    return [
        {
            "target_key": row["target_key"],
            "external_server_id": row["external_server_id"],
            "display_name": row["display_name"],
            "host": row["host"],
            "port": row["port"],
            "region": row["region"],
            "source_name": row["source_name"],
            "sample_count": int(row["sample_count"] or 0),
            "first_sample_at": row["first_sample_at"],
            "last_successful_capture_at": row["last_successful_capture_at"],
            "last_sample_at": row["latest_sample_at"] or row["last_sample_at"],
            "last_run_id": row["last_run_id"],
            "last_run_status": row["last_run_status"],
            "last_error": row["last_error"],
            "last_error_at": row["last_error_at"],
        }
        for row in rows
    ]


def list_recent_rcon_historical_samples(
    *,
    target_key: str | None = None,
    limit: int = 20,
    db_path: Path | None = None,
) -> list[dict[str, object]]:
    """Return recent prospective RCON samples for one or all configured targets."""
    resolved_path = initialize_rcon_historical_storage(db_path=db_path)
    where_clause = ""
    params: list[object] = [limit]
    if target_key:
        where_clause = "WHERE targets.target_key = ? OR targets.external_server_id = ?"
        params = [target_key, target_key, limit]

    with _connect(resolved_path) as connection:
        rows = connection.execute(
            f"""
            SELECT
                targets.target_key,
                targets.external_server_id,
                targets.display_name,
                targets.region,
                samples.captured_at,
                samples.status,
                samples.players,
                samples.max_players,
                samples.current_map
            FROM rcon_historical_samples AS samples
            INNER JOIN rcon_historical_targets AS targets
                ON targets.id = samples.target_id
            {where_clause}
            ORDER BY samples.captured_at DESC, targets.display_name ASC
            LIMIT ?
            """,
            params,
        ).fetchall()
    return [
        {
            "target_key": row["target_key"],
            "external_server_id": row["external_server_id"],
            "display_name": row["display_name"],
            "region": row["region"],
            "captured_at": row["captured_at"],
            "status": row["status"],
            "players": row["players"],
            "max_players": row["max_players"],
            "current_map": row["current_map"],
        }
        for row in rows
    ]


def _connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _upsert_target(connection: sqlite3.Connection, *, target: Mapping[str, object]) -> int:
    target_key = str(target.get("target_key") or "").strip()
    if not target_key:
        raise ValueError("Prospective RCON targets require a non-empty target_key.")
    display_name = str(target.get("name") or target.get("display_name") or target_key).strip()
    host = str(target.get("host") or "").strip()
    port = int(target.get("port") or 0)
    if not host or port <= 0:
        raise ValueError("Prospective RCON targets require host and port.")

    connection.execute(
        """
        INSERT INTO rcon_historical_targets (
            target_key,
            external_server_id,
            display_name,
            host,
            port,
            region,
            game_port,
            query_port,
            source_name,
            last_configured_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(target_key) DO UPDATE SET
            external_server_id = excluded.external_server_id,
            display_name = excluded.display_name,
            host = excluded.host,
            port = excluded.port,
            region = excluded.region,
            game_port = excluded.game_port,
            query_port = excluded.query_port,
            source_name = excluded.source_name,
            last_configured_at = excluded.last_configured_at,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            target_key,
            target.get("external_server_id"),
            display_name,
            host,
            port,
            target.get("region"),
            target.get("game_port"),
            target.get("query_port"),
            str(target.get("source_name") or "community-hispana-rcon"),
            _utc_now_iso(),
        ),
    )
    row = connection.execute(
        "SELECT id FROM rcon_historical_targets WHERE target_key = ?",
        (target_key,),
    ).fetchone()
    if row is None:
        raise RuntimeError("Failed to resolve prospective RCON target id.")
    return int(row["id"])


def _upsert_checkpoint_success(
    connection: sqlite3.Connection,
    *,
    target_id: int,
    run_id: int,
    captured_at: str,
) -> None:
    connection.execute(
        """
        INSERT INTO rcon_historical_checkpoints (
            target_id,
            last_successful_capture_at,
            last_sample_at,
            last_run_id,
            last_run_status,
            last_error,
            last_error_at
        ) VALUES (?, ?, ?, ?, 'success', NULL, NULL)
        ON CONFLICT(target_id) DO UPDATE SET
            last_successful_capture_at = excluded.last_successful_capture_at,
            last_sample_at = excluded.last_sample_at,
            last_run_id = excluded.last_run_id,
            last_run_status = excluded.last_run_status,
            last_error = NULL,
            last_error_at = NULL,
            updated_at = CURRENT_TIMESTAMP
        """,
        (target_id, captured_at, captured_at, run_id),
    )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
