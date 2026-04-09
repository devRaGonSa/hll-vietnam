"""PostgreSQL-backed storage and run tracking for prospective RCON historical capture."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

from .config import get_primary_storage_label
from .normalizers import normalize_map_name
from .postgres_utils import connect_postgres_compat, ensure_postgres_migrations_applied
from .rcon_client import load_rcon_targets


COMPETITIVE_WINDOW_GAP_SECONDS = 1800
COMPETITIVE_MODE_PARTIAL = "partial"
COMPETITIVE_MODE_APPROXIMATE = "approximate"
COMPETITIVE_MODE_EXACT = "exact"


def initialize_rcon_historical_storage(*, db_path: Path | None = None) -> Path:
    """Ensure PostgreSQL schema bootstrap exists for prospective RCON capture."""
    resolved_path = db_path or Path(get_primary_storage_label())
    ensure_postgres_migrations_applied()
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
        row = connection.execute(
            """
            INSERT INTO rcon_historical_capture_runs (
                mode,
                status,
                target_scope,
                started_at
            ) VALUES (?, 'running', ?, ?)
            RETURNING id
            """,
            (mode, target_scope, _utc_now_iso()),
        ).fetchone()
        if row is None:
            raise RuntimeError("Failed to create RCON historical capture run.")
        return int(row["id"])


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
            INSERT INTO rcon_historical_samples (
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
            ) VALUES (?, ?, ?, 'rcon-live-sample', ?, ?, ?, ?, CAST(? AS JSONB), CAST(? AS JSONB))
            ON CONFLICT(target_id, captured_at) DO NOTHING
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
        if inserted:
            _upsert_competitive_window(
                connection,
                target_id=target_id,
                captured_at=captured_at,
                normalized_payload=normalized_payload,
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
    resolved_path = _resolve_db_path(db_path)
    try:
        with _connect_readonly(resolved_path) as connection:
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
    except Exception:
        return []
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
    resolved_path = _resolve_db_path(db_path)
    where_clause = ""
    params: list[object] = [limit]
    if target_key:
        aliases = _expand_target_key_aliases(target_key)
        alias_placeholders = ", ".join("?" for _ in aliases)
        where_clause = (
            "WHERE targets.target_key IN "
            f"({alias_placeholders}) OR targets.external_server_id IN ({alias_placeholders})"
        )
        params = [*aliases, *aliases, limit]

    try:
        with _connect_readonly(resolved_path) as connection:
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
    except Exception:
        return []
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


def list_rcon_historical_competitive_windows(
    *,
    target_key: str | None = None,
    limit: int = 20,
    db_path: Path | None = None,
) -> list[dict[str, object]]:
    """Return recent RCON-backed competitive windows derived from persisted samples."""
    resolved_path = _resolve_db_path(db_path)
    where_clause = ""
    params: list[object] = [limit]
    if target_key:
        aliases = _expand_target_key_aliases(target_key)
        alias_placeholders = ", ".join("?" for _ in aliases)
        where_clause = (
            "WHERE targets.target_key IN "
            f"({alias_placeholders}) OR targets.external_server_id IN ({alias_placeholders})"
        )
        params = [*aliases, *aliases, limit]

    try:
        with _connect_readonly(resolved_path) as connection:
            rows = connection.execute(
                f"""
            SELECT
                targets.target_key,
                targets.external_server_id,
                targets.display_name,
                targets.region,
                windows.session_key,
                windows.map_name,
                windows.map_pretty_name,
                windows.first_seen_at,
                windows.last_seen_at,
                windows.sample_count,
                windows.total_players,
                windows.peak_players,
                windows.last_players,
                windows.max_players,
                windows.status,
                windows.confidence_mode,
                windows.capabilities_json
            FROM rcon_historical_competitive_windows AS windows
            INNER JOIN rcon_historical_targets AS targets
                ON targets.id = windows.target_id
            {where_clause}
            ORDER BY windows.last_seen_at DESC, targets.display_name ASC
            LIMIT ?
            """,
                params,
            ).fetchall()
    except Exception:
        return []
    items: list[dict[str, object]] = []
    for row in rows:
        sample_count = int(row["sample_count"] or 0)
        average_players = round((int(row["total_players"] or 0) / sample_count), 2) if sample_count > 0 else 0.0
        items.append(
            {
                "target_key": row["target_key"],
                "external_server_id": row["external_server_id"],
                "display_name": row["display_name"],
                "region": row["region"],
                "session_key": row["session_key"],
                "map_name": row["map_name"],
                "map_pretty_name": row["map_pretty_name"] or row["map_name"],
                "first_seen_at": row["first_seen_at"],
                "last_seen_at": row["last_seen_at"],
                "duration_seconds": _calculate_duration_seconds(
                    row["first_seen_at"],
                    row["last_seen_at"],
                ),
                "sample_count": sample_count,
                "average_players": average_players,
                "peak_players": int(row["peak_players"] or 0),
                "last_players": row["last_players"],
                "max_players": row["max_players"],
                "status": row["status"],
                "confidence_mode": row["confidence_mode"],
                "capabilities": _deserialize_json_object(row["capabilities_json"]),
            }
        )
    return items


def count_rcon_historical_samples_since(
    since: str | None,
    *,
    db_path: Path | None = None,
) -> int:
    """Return how many RCON samples were captured after one timestamp."""
    if not since:
        return 0
    resolved_path = _resolve_db_path(db_path)
    try:
        with _connect_readonly(resolved_path) as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS sample_count
                FROM rcon_historical_samples
                WHERE captured_at > ?
                """,
                (since,),
            ).fetchone()
    except Exception:
        return 0
    return int(row["sample_count"] or 0) if row else 0


def list_rcon_historical_competitive_summary_rows(
    *,
    target_key: str | None = None,
    db_path: Path | None = None,
) -> list[dict[str, object]]:
    """Return RCON-backed per-target summary rows over competitive windows."""
    resolved_path = _resolve_db_path(db_path)
    where_clause = ""
    params: list[object] = []
    if target_key:
        aliases = _expand_target_key_aliases(target_key)
        alias_placeholders = ", ".join("?" for _ in aliases)
        where_clause = (
            "WHERE targets.target_key IN "
            f"({alias_placeholders}) OR targets.external_server_id IN ({alias_placeholders})"
        )
        params = [*aliases, *aliases]

    try:
        with _connect_readonly(resolved_path) as connection:
            rows = connection.execute(
                f"""
            SELECT
                targets.target_key,
                targets.external_server_id,
                targets.display_name,
                targets.region,
                checkpoints.last_successful_capture_at,
                checkpoints.last_run_status,
                checkpoints.last_error,
                checkpoints.last_error_at,
                COUNT(windows.id) AS window_count,
                COALESCE(SUM(windows.sample_count), 0) AS sample_count,
                MIN(windows.first_seen_at) AS first_seen_at,
                MAX(windows.last_seen_at) AS last_seen_at,
                COALESCE(MAX(windows.peak_players), 0) AS peak_players
            FROM rcon_historical_targets AS targets
            LEFT JOIN rcon_historical_checkpoints AS checkpoints
                ON checkpoints.target_id = targets.id
            LEFT JOIN rcon_historical_competitive_windows AS windows
                ON windows.target_id = targets.id
            {where_clause}
            GROUP BY targets.id
            ORDER BY targets.display_name ASC, targets.target_key ASC
            """,
                params,
            ).fetchall()
    except Exception:
        return []
    return [
        {
            "target_key": row["target_key"],
            "external_server_id": row["external_server_id"],
            "display_name": row["display_name"],
            "region": row["region"],
            "window_count": int(row["window_count"] or 0),
            "sample_count": int(row["sample_count"] or 0),
            "first_seen_at": row["first_seen_at"],
            "last_seen_at": row["last_seen_at"],
            "peak_players": int(row["peak_players"] or 0),
            "last_successful_capture_at": row["last_successful_capture_at"],
            "last_run_status": row["last_run_status"],
            "last_error": row["last_error"],
            "last_error_at": row["last_error_at"],
        }
        for row in rows
    ]


def find_rcon_historical_competitive_window(
    *,
    server_key: str,
    ended_at: str | None,
    map_name: str | None = None,
    db_path: Path | None = None,
) -> dict[str, object] | None:
    """Return the closest competitive window for one server/match if coverage exists."""
    if not ended_at:
        return None
    resolved_path = _resolve_db_path(db_path)
    normalized_map_name = normalize_map_name(map_name)
    aliases = _expand_target_key_aliases(server_key)
    alias_placeholders = ", ".join("?" for _ in aliases)
    try:
        with _connect_readonly(resolved_path) as connection:
            candidates = connection.execute(
                f"""
            SELECT
                windows.session_key,
                windows.first_seen_at,
                windows.last_seen_at,
                windows.map_name,
                windows.map_pretty_name,
                windows.sample_count,
                windows.total_players,
                windows.peak_players,
                windows.confidence_mode,
                windows.capabilities_json
            FROM rcon_historical_competitive_windows AS windows
            INNER JOIN rcon_historical_targets AS targets
                ON targets.id = windows.target_id
            WHERE (
                targets.target_key IN ({alias_placeholders})
                OR targets.external_server_id IN ({alias_placeholders})
            )
            ORDER BY windows.last_seen_at DESC
            LIMIT 12
            """,
                [*aliases, *aliases],
            ).fetchall()
    except Exception:
        return None
    if not candidates:
        return None

    ended_point = _parse_timestamp(ended_at)
    best_row: sqlite3.Row | None = None
    best_distance: float | None = None
    for row in candidates:
        row_map_name = normalize_map_name(row["map_pretty_name"] or row["map_name"])
        if normalized_map_name and row_map_name and normalized_map_name != row_map_name:
            continue
        row_last = _parse_timestamp(row["last_seen_at"])
        distance = abs((row_last - ended_point).total_seconds())
        if best_distance is None or distance < best_distance:
            best_row = row
            best_distance = distance
    if best_row is None or best_distance is None or best_distance > 21600:
        return None
    sample_count = int(best_row["sample_count"] or 0)
    return {
        "session_key": best_row["session_key"],
        "first_seen_at": best_row["first_seen_at"],
        "last_seen_at": best_row["last_seen_at"],
        "duration_seconds": _calculate_duration_seconds(
            best_row["first_seen_at"],
            best_row["last_seen_at"],
        ),
        "map_name": best_row["map_name"],
        "map_pretty_name": best_row["map_pretty_name"] or best_row["map_name"],
        "sample_count": sample_count,
        "average_players": round((int(best_row["total_players"] or 0) / sample_count), 2) if sample_count > 0 else 0.0,
        "peak_players": int(best_row["peak_players"] or 0),
        "confidence_mode": best_row["confidence_mode"],
        "capabilities": _deserialize_json_object(best_row["capabilities_json"]),
    }


def _connect(db_path: Path) -> object:
    return connect_postgres_compat()


def _connect_readonly(db_path: Path) -> object:
    return connect_postgres_compat()


def _resolve_db_path(db_path: Path | None) -> Path:
    return db_path or Path(get_primary_storage_label())


def _expand_target_key_aliases(target_key: str) -> list[str]:
    normalized_target_key = str(target_key or "").strip()
    if not normalized_target_key:
        return [normalized_target_key]

    aliases = {normalized_target_key}
    try:
        configured_targets = load_rcon_targets()
    except Exception:
        configured_targets = ()

    for target in configured_targets:
        external_server_id = str(target.external_server_id or "").strip()
        legacy_target_key = f"rcon:{target.host}:{target.port}"
        if external_server_id and external_server_id == normalized_target_key:
            aliases.add(legacy_target_key)
            aliases.add(external_server_id)
        elif legacy_target_key == normalized_target_key:
            aliases.add(legacy_target_key)
            if external_server_id:
                aliases.add(external_server_id)

    return sorted(alias for alias in aliases if alias)


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


def _upsert_competitive_window(
    connection: sqlite3.Connection,
    *,
    target_id: int,
    captured_at: str,
    normalized_payload: Mapping[str, object],
) -> None:
    current_map_raw = str(normalized_payload.get("current_map") or "").strip()
    if not current_map_raw:
        return
    map_pretty_name = normalize_map_name(current_map_raw) or current_map_raw
    players = int(normalized_payload.get("players") or 0)
    max_players = normalized_payload.get("max_players")
    status = str(normalized_payload.get("status") or "unknown")
    latest_window = connection.execute(
        """
        SELECT *
        FROM rcon_historical_competitive_windows
        WHERE target_id = ?
        ORDER BY last_seen_at DESC, id DESC
        LIMIT 1
        """,
        (target_id,),
    ).fetchone()
    if latest_window and _should_extend_competitive_window(
        latest_window=latest_window,
        captured_at=captured_at,
        current_map=current_map_raw,
    ):
        connection.execute(
            """
            UPDATE rcon_historical_competitive_windows
            SET map_name = ?,
                map_pretty_name = ?,
                last_seen_at = ?,
                sample_count = sample_count + 1,
                total_players = total_players + ?,
                peak_players = CASE WHEN peak_players > ? THEN peak_players ELSE ? END,
                last_players = ?,
                max_players = ?,
                status = ?,
                confidence_mode = ?,
                capabilities_json = CAST(? AS JSONB),
                latest_payload_json = CAST(? AS JSONB),
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                current_map_raw,
                map_pretty_name,
                captured_at,
                players,
                players,
                players,
                players,
                max_players,
                status,
                COMPETITIVE_MODE_APPROXIMATE,
                json.dumps(_build_competitive_capabilities(), ensure_ascii=True, separators=(",", ":")),
                json.dumps(dict(normalized_payload), ensure_ascii=True, separators=(",", ":")),
                latest_window["id"],
            ),
        )
        return

    session_key = f"{target_id}:{captured_at}"
    connection.execute(
        """
        INSERT INTO rcon_historical_competitive_windows (
            target_id,
            session_key,
            source_kind,
            map_name,
            map_pretty_name,
            first_seen_at,
            last_seen_at,
            sample_count,
            total_players,
            peak_players,
            last_players,
            max_players,
            status,
            confidence_mode,
            capabilities_json,
            latest_payload_json
        ) VALUES (?, ?, 'rcon-historical-samples', ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, CAST(? AS JSONB), CAST(? AS JSONB))
        """,
        (
            target_id,
            session_key,
            current_map_raw,
            map_pretty_name,
            captured_at,
            captured_at,
            players,
            players,
            players,
            max_players,
            status,
            COMPETITIVE_MODE_APPROXIMATE,
            json.dumps(_build_competitive_capabilities(), ensure_ascii=True, separators=(",", ":")),
            json.dumps(dict(normalized_payload), ensure_ascii=True, separators=(",", ":")),
        ),
    )


def _should_extend_competitive_window(
    *,
    latest_window: sqlite3.Row,
    captured_at: str,
    current_map: str,
) -> bool:
    latest_map = str(latest_window["map_name"] or "").strip()
    if normalize_map_name(latest_map) != normalize_map_name(current_map):
        return False
    latest_seen = _parse_timestamp(str(latest_window["last_seen_at"]))
    captured_point = _parse_timestamp(captured_at)
    return (captured_point - latest_seen).total_seconds() <= COMPETITIVE_WINDOW_GAP_SECONDS


def _build_competitive_capabilities() -> dict[str, object]:
    return {
        "recent_matches": COMPETITIVE_MODE_APPROXIMATE,
        "server_summary": COMPETITIVE_MODE_EXACT,
        "competitive_quality": COMPETITIVE_MODE_PARTIAL,
        "player_stats": "unavailable",
    }


def _deserialize_json_object(raw_value: object) -> dict[str, object]:
    if isinstance(raw_value, dict):
        return dict(raw_value)
    if isinstance(raw_value, str) and raw_value.strip():
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError:
            return {}
        if isinstance(parsed, dict):
            return parsed
    return {}


def _parse_timestamp(raw_value: object) -> datetime:
    if isinstance(raw_value, datetime):
        timestamp = raw_value
    else:
        timestamp = datetime.fromisoformat(str(raw_value).replace("Z", "+00:00"))
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def _calculate_duration_seconds(first_seen_at: str | None, last_seen_at: str | None) -> int | None:
    if not first_seen_at or not last_seen_at:
        return None
    return max(0, int((_parse_timestamp(last_seen_at) - _parse_timestamp(first_seen_at)).total_seconds()))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
