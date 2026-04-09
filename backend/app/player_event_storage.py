"""PostgreSQL-backed raw storage and run tracking for the V2 player event pipeline."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import get_player_event_refresh_overlap_hours, get_primary_storage_label
from .player_event_models import PlayerEventRecord
from .postgres_utils import connect_postgres_compat, ensure_postgres_migrations_applied


def initialize_player_event_storage(*, db_path: Path | None = None) -> Path:
    """Ensure PostgreSQL schema bootstrap exists for the V2 player event pipeline."""
    resolved_path = db_path or Path(get_primary_storage_label())
    ensure_postgres_migrations_applied()
    return resolved_path


def upsert_player_events(
    events: Iterable[PlayerEventRecord],
    *,
    db_path: Path | None = None,
) -> dict[str, int]:
    """Insert normalized events idempotently into the raw ledger."""
    resolved_path = initialize_player_event_storage(db_path=db_path)
    inserted = 0
    duplicates = 0
    with _connect(resolved_path) as connection:
        for event in events:
            cursor = connection.execute(
                """
                INSERT INTO player_event_raw_ledger (
                    event_id,
                    event_type,
                    occurred_at,
                    server_slug,
                    external_match_id,
                    source_kind,
                    source_ref,
                    raw_event_ref,
                    killer_player_key,
                    killer_display_name,
                    victim_player_key,
                    victim_display_name,
                    weapon_name,
                    weapon_category,
                    kill_category,
                    is_teamkill,
                    event_value
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(event_id) DO NOTHING
                """,
                (
                    event.event_id,
                    event.event_type,
                    event.occurred_at,
                    event.server_slug,
                    event.external_match_id,
                    event.source_kind,
                    event.source_ref,
                    event.raw_event_ref,
                    event.killer_player_key,
                    event.killer_display_name,
                    event.victim_player_key,
                    event.victim_display_name,
                    event.weapon_name,
                    event.weapon_category,
                    event.kill_category,
                    event.is_teamkill,
                    max(1, int(event.event_value)),
                ),
            )
            if int(cursor.rowcount or 0) > 0:
                inserted += 1
            else:
                duplicates += 1
    return {
        "events_inserted": inserted,
        "duplicate_events": duplicates,
    }


def start_player_event_ingestion_run(
    *,
    mode: str,
    target_server_slug: str | None = None,
    db_path: Path | None = None,
) -> int:
    """Persist one player event ingestion attempt."""
    resolved_path = initialize_player_event_storage(db_path=db_path)
    with _connect(resolved_path) as connection:
        row = connection.execute(
            """
            INSERT INTO player_event_ingestion_runs (
                mode,
                status,
                target_server_slug,
                started_at
            ) VALUES (?, 'running', ?, ?)
            RETURNING id
            """,
            (mode, target_server_slug, _utc_now_iso()),
        ).fetchone()
        if row is None:
            raise RuntimeError("Failed to create player event ingestion run.")
        return int(row["id"])


def finalize_player_event_ingestion_run(
    run_id: int,
    *,
    status: str,
    pages_processed: int,
    matches_seen: int,
    matches_fetched: int,
    events_inserted: int,
    duplicate_events: int,
    notes: str | None = None,
    db_path: Path | None = None,
) -> None:
    """Update one player event ingestion attempt with final counters."""
    resolved_path = initialize_player_event_storage(db_path=db_path)
    with _connect(resolved_path) as connection:
        connection.execute(
            """
            UPDATE player_event_ingestion_runs
            SET status = ?,
                completed_at = ?,
                pages_processed = ?,
                matches_seen = ?,
                matches_fetched = ?,
                events_inserted = ?,
                duplicate_events = ?,
                notes = ?
            WHERE id = ?
            """,
            (
                status,
                _utc_now_iso(),
                pages_processed,
                matches_seen,
                matches_fetched,
                events_inserted,
                duplicate_events,
                notes,
                run_id,
            ),
        )


def mark_player_event_progress_started(
    *,
    server_slug: str,
    mode: str,
    run_id: int,
    cutoff_occurred_at: str | None,
    db_path: Path | None = None,
) -> None:
    """Persist the start state for one server ingestion attempt."""
    resolved_path = initialize_player_event_storage(db_path=db_path)
    with _connect(resolved_path) as connection:
        connection.execute(
            """
            INSERT INTO player_event_backfill_progress (
                server_slug,
                mode,
                next_page,
                cutoff_occurred_at,
                archive_exhausted,
                last_run_id,
                last_run_status,
                last_run_started_at,
                last_run_completed_at,
                last_error
            ) VALUES (?, ?, 1, ?, FALSE, ?, 'running', ?, NULL, NULL)
            ON CONFLICT(server_slug, mode) DO UPDATE SET
                cutoff_occurred_at = excluded.cutoff_occurred_at,
                last_run_id = excluded.last_run_id,
                last_run_status = excluded.last_run_status,
                last_run_started_at = excluded.last_run_started_at,
                last_run_completed_at = NULL,
                last_error = NULL,
                updated_at = CURRENT_TIMESTAMP
            """,
            (server_slug, mode, cutoff_occurred_at, run_id, _utc_now_iso()),
        )


def mark_player_event_progress_page_completed(
    *,
    server_slug: str,
    mode: str,
    page_number: int,
    discovered_total_matches: int | None,
    run_id: int,
    db_path: Path | None = None,
) -> None:
    """Advance the resume checkpoint after one page completes successfully."""
    resolved_path = initialize_player_event_storage(db_path=db_path)
    with _connect(resolved_path) as connection:
        connection.execute(
            """
            INSERT INTO player_event_backfill_progress (
                server_slug,
                mode,
                next_page,
                last_completed_page,
                discovered_total_matches,
                archive_exhausted,
                last_run_id,
                last_run_status,
                last_run_started_at,
                last_run_completed_at,
                last_error
            ) VALUES (?, ?, ?, ?, ?, FALSE, ?, 'running', ?, NULL, NULL)
            ON CONFLICT(server_slug, mode) DO UPDATE SET
                next_page = excluded.next_page,
                last_completed_page = excluded.last_completed_page,
                discovered_total_matches = COALESCE(
                    excluded.discovered_total_matches,
                    player_event_backfill_progress.discovered_total_matches
                ),
                archive_exhausted = FALSE,
                last_run_id = excluded.last_run_id,
                last_run_status = excluded.last_run_status,
                last_run_started_at = excluded.last_run_started_at,
                last_run_completed_at = NULL,
                last_error = NULL,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                server_slug,
                mode,
                page_number + 1,
                page_number,
                discovered_total_matches,
                run_id,
                _utc_now_iso(),
            ),
        )


def finalize_player_event_progress(
    *,
    server_slug: str,
    mode: str,
    run_id: int,
    status: str,
    archive_exhausted: bool = False,
    error_message: str | None = None,
    db_path: Path | None = None,
) -> None:
    """Persist the final state of one server event ingestion attempt."""
    resolved_path = initialize_player_event_storage(db_path=db_path)
    with _connect(resolved_path) as connection:
        connection.execute(
            """
            INSERT INTO player_event_backfill_progress (
                server_slug,
                mode,
                next_page,
                archive_exhausted,
                last_run_id,
                last_run_status,
                last_run_started_at,
                last_run_completed_at,
                last_error
            ) VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(server_slug, mode) DO UPDATE SET
                archive_exhausted = CASE
                    WHEN excluded.last_run_status = 'success' AND excluded.archive_exhausted = TRUE
                    THEN TRUE
                    ELSE player_event_backfill_progress.archive_exhausted
                END,
                last_run_id = excluded.last_run_id,
                last_run_status = excluded.last_run_status,
                last_run_started_at = COALESCE(
                    player_event_backfill_progress.last_run_started_at,
                    excluded.last_run_started_at
                ),
                last_run_completed_at = excluded.last_run_completed_at,
                last_error = excluded.last_error,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                server_slug,
                mode,
                archive_exhausted,
                run_id,
                status,
                _utc_now_iso(),
                _utc_now_iso(),
                error_message,
            ),
        )


def get_player_event_resume_page(
    server_slug: str,
    *,
    mode: str = "bootstrap",
    db_path: Path | None = None,
) -> int:
    """Return the saved resume page for a bootstrap-like event backfill."""
    resolved_path = initialize_player_event_storage(db_path=db_path)
    with _connect(resolved_path) as connection:
        row = connection.execute(
            """
            SELECT next_page
            FROM player_event_backfill_progress
            WHERE server_slug = ? AND mode = ?
            """,
            (server_slug, mode),
        ).fetchone()
    return max(1, int(row["next_page"])) if row and row["next_page"] else 1


def get_player_event_refresh_cutoff_for_server(
    server_slug: str,
    *,
    overlap_hours: int | None = None,
    db_path: Path | None = None,
) -> str | None:
    """Return the latest occurred_at already persisted for one server."""
    resolved_overlap_hours = (
        get_player_event_refresh_overlap_hours()
        if overlap_hours is None
        else overlap_hours
    )
    if resolved_overlap_hours < 0:
        raise ValueError("overlap_hours must be zero or positive.")
    resolved_path = initialize_player_event_storage(db_path=db_path)
    with _connect(resolved_path) as connection:
        row = connection.execute(
            """
            SELECT MAX(occurred_at) AS latest_occurred_at
            FROM player_event_raw_ledger
            WHERE server_slug = ?
            """,
            (server_slug,),
        ).fetchone()
    latest_occurred_at = str(row["latest_occurred_at"]) if row and row["latest_occurred_at"] else None
    if not latest_occurred_at:
        return None

    cutoff = _parse_timestamp(latest_occurred_at) - timedelta(hours=resolved_overlap_hours)
    return cutoff.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _connect(db_path: Path) -> object:
    return connect_postgres_compat()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_timestamp(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed
