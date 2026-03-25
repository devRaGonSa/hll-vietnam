"""Incremental worker for the V2 player event ingestion pipeline."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from typing import Iterable

from .config import (
    get_historical_crcon_detail_workers,
    get_historical_crcon_page_size,
    get_player_event_refresh_interval_seconds,
    get_player_event_refresh_max_retries,
    get_player_event_refresh_overlap_hours,
    get_player_event_refresh_retry_delay_seconds,
)
from .data_sources import resolve_historical_ingestion_data_source
from .historical_storage import list_historical_servers
from .player_event_source import resolve_player_event_source
from .player_event_storage import (
    finalize_player_event_ingestion_run,
    finalize_player_event_progress,
    get_player_event_refresh_cutoff_for_server,
    get_player_event_resume_page,
    initialize_player_event_storage,
    mark_player_event_progress_page_completed,
    mark_player_event_progress_started,
    start_player_event_ingestion_run,
    upsert_player_events,
)
from .writer_lock import backend_writer_lock, build_writer_lock_holder


@dataclass(slots=True)
class PlayerEventIngestionStats:
    pages_processed: int = 0
    matches_seen: int = 0
    matches_fetched: int = 0
    events_inserted: int = 0
    duplicate_events: int = 0

    def apply(self, delta: dict[str, int]) -> None:
        self.events_inserted += int(delta.get("events_inserted", 0))
        self.duplicate_events += int(delta.get("duplicate_events", 0))


def run_player_event_refresh(
    *,
    server_slug: str | None = None,
    max_pages: int | None = None,
    page_size: int | None = None,
    start_page: int | None = None,
    detail_workers: int | None = None,
    overlap_hours: int | None = None,
) -> dict[str, object]:
    """Refresh recent player event summaries from the configured historical source."""
    with backend_writer_lock(
        holder=build_writer_lock_holder(
            f"app.player_event_worker refresh:{server_slug or 'all-servers'}"
        )
    ):
        initialize_player_event_storage()
        data_source, data_source_policy = resolve_historical_ingestion_data_source()
        event_source_selection = resolve_player_event_source()
        event_source = event_source_selection.source
        resolved_page_size = page_size or get_historical_crcon_page_size()
        resolved_detail_workers = detail_workers or get_historical_crcon_detail_workers()
        resolved_overlap_hours = (
            get_player_event_refresh_overlap_hours()
            if overlap_hours is None
            else overlap_hours
        )
        if resolved_overlap_hours < 0:
            raise ValueError("--overlap-hours must be zero or positive.")
        selected_servers = _select_servers(server_slug)
        processed_servers: list[dict[str, object]] = []
        active_runs: dict[str, int] = {}

        try:
            for server in selected_servers:
                current_server_slug = str(server["slug"])
                run_id = start_player_event_ingestion_run(
                    mode="refresh",
                    target_server_slug=current_server_slug,
                )
                active_runs[current_server_slug] = run_id
                cutoff = get_player_event_refresh_cutoff_for_server(
                    current_server_slug,
                    overlap_hours=resolved_overlap_hours,
                )
                mark_player_event_progress_started(
                    server_slug=current_server_slug,
                    mode="refresh",
                    run_id=run_id,
                    cutoff_occurred_at=cutoff,
                )
                server_stats = _ingest_server(
                    server=server,
                    run_id=run_id,
                    data_source=data_source,
                    event_source=event_source,
                    page_size=resolved_page_size,
                    max_pages=max_pages,
                    start_page=_resolve_start_page(
                        server_slug=current_server_slug,
                        start_page=start_page,
                    ),
                    detail_workers=resolved_detail_workers,
                    cutoff=cutoff,
                )
                finalize_player_event_ingestion_run(
                    run_id,
                    status="success",
                    pages_processed=server_stats["pages_processed"],
                    matches_seen=server_stats["matches_seen"],
                    matches_fetched=server_stats["matches_fetched"],
                    events_inserted=server_stats["events_inserted"],
                    duplicate_events=server_stats["duplicate_events"],
                    notes=f"source={data_source.source_kind};adapter={event_source.source_kind}",
                )
                finalize_player_event_progress(
                    server_slug=current_server_slug,
                    mode="refresh",
                    run_id=run_id,
                    status="success",
                    archive_exhausted=bool(server_stats["archive_exhausted"]),
                )
                processed_servers.append(server_stats)
                active_runs.pop(current_server_slug, None)
        except Exception as exc:
            for active_server_slug, run_id in active_runs.items():
                finalize_player_event_ingestion_run(
                    run_id,
                    status="failed",
                    pages_processed=0,
                    matches_seen=0,
                    matches_fetched=0,
                    events_inserted=0,
                    duplicate_events=0,
                    notes=str(exc),
                )
                finalize_player_event_progress(
                    server_slug=active_server_slug,
                    mode="refresh",
                    run_id=run_id,
                    status="failed",
                    error_message=str(exc),
                )
            raise

        return {
            "status": "ok",
            "mode": "refresh",
            "source_provider": data_source.source_kind,
            "source_policy": data_source_policy,
            "event_adapter": event_source.source_kind,
            "event_source_policy": event_source_selection.source_policy,
            "page_size": resolved_page_size,
            "detail_workers": resolved_detail_workers,
            "overlap_hours": resolved_overlap_hours,
            "scope": event_source.describe_scope(),
            "servers": processed_servers,
        }


def run_periodic_player_event_refresh(
    *,
    interval_seconds: int,
    max_retries: int,
    retry_delay_seconds: int,
    server_slug: str | None = None,
    max_pages: int | None = None,
    page_size: int | None = None,
    detail_workers: int | None = None,
    max_runs: int | None = None,
) -> None:
    """Run the refresh worker repeatedly with bounded retries."""
    completed_runs = 0
    print(
        json.dumps(
            {
                "event": "player-event-refresh-loop-started",
                "interval_seconds": interval_seconds,
                "max_retries": max_retries,
                "retry_delay_seconds": retry_delay_seconds,
                "server_scope": [server_slug] if server_slug else [server["slug"] for server in list_historical_servers()],
            },
            indent=2,
        )
    )
    print("Press Ctrl+C to stop.")

    try:
        while max_runs is None or completed_runs < max_runs:
            completed_runs += 1
            payload = _run_refresh_with_retries(
                max_retries=max_retries,
                retry_delay_seconds=retry_delay_seconds,
                server_slug=server_slug,
                max_pages=max_pages,
                page_size=page_size,
                detail_workers=detail_workers,
            )
            print(json.dumps({"run": completed_runs, **payload}, indent=2))
            if max_runs is not None and completed_runs >= max_runs:
                break
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\nPlayer event refresh loop stopped by user.")


def _run_refresh_with_retries(
    *,
    max_retries: int,
    retry_delay_seconds: int,
    server_slug: str | None,
    max_pages: int | None,
    page_size: int | None,
    detail_workers: int | None,
) -> dict[str, object]:
    attempt = 0
    while True:
        attempt += 1
        try:
            return {
                "status": "ok",
                "attempts_used": attempt,
                "refresh_result": run_player_event_refresh(
                    server_slug=server_slug,
                    max_pages=max_pages,
                    page_size=page_size,
                    detail_workers=detail_workers,
                ),
            }
        except Exception as exc:
            if attempt > max_retries:
                return {
                    "status": "error",
                    "attempts_used": attempt,
                    "error": str(exc),
                }
            if retry_delay_seconds > 0:
                time.sleep(retry_delay_seconds)


def _ingest_server(
    *,
    server: dict[str, object],
    run_id: int,
    data_source: object,
    event_source: object,
    page_size: int,
    max_pages: int | None,
    start_page: int,
    detail_workers: int,
    cutoff: str | None,
) -> dict[str, object]:
    page_limit = max_pages or 1000000
    local_stats = PlayerEventIngestionStats()
    discovered_total_matches: int | None = None
    archive_exhausted = False

    for page_number in range(start_page, start_page + page_limit):
        payload = data_source.fetch_match_page(
            base_url=str(server["scoreboard_base_url"]),
            page=page_number,
            limit=page_size,
        )
        if discovered_total_matches is None:
            discovered_total_matches = _coerce_int(payload.get("total"))
        page_matches = _coerce_match_list(payload.get("maps"))
        if not page_matches:
            archive_exhausted = True
            break

        local_stats.pages_processed += 1
        stop_after_page = False
        match_ids_to_fetch: list[str] = []

        for match_summary in page_matches:
            local_stats.matches_seen += 1
            reference_timestamp = _pick_match_timestamp(match_summary)
            if cutoff and reference_timestamp and reference_timestamp < cutoff:
                stop_after_page = True
                continue

            match_id = _stringify(match_summary.get("id"))
            if match_id:
                match_ids_to_fetch.append(match_id)

        detail_payloads = data_source.fetch_match_details(
            base_url=str(server["scoreboard_base_url"]),
            match_ids=match_ids_to_fetch,
            max_workers=detail_workers,
        )
        local_stats.matches_fetched += len(detail_payloads)
        for detail_payload in detail_payloads:
            match_id = _stringify(detail_payload.get("id")) or "unknown"
            source_ref = (
                f"{server['scoreboard_base_url']}/api/get_map_scoreboard?map_id={match_id}"
            )
            normalized_events = event_source.extract_match_events(
                server_slug=str(server["slug"]),
                match_payload=detail_payload,
                source_ref=source_ref,
            )
            local_stats.apply(upsert_player_events(normalized_events))

        mark_player_event_progress_page_completed(
            server_slug=str(server["slug"]),
            mode="refresh",
            page_number=page_number,
            discovered_total_matches=discovered_total_matches,
            run_id=run_id,
        )

        if stop_after_page:
            break

    return {
        "server_slug": server["slug"],
        "source_provider": data_source.source_kind,
        "event_adapter": event_source.source_kind,
        "pages_processed": local_stats.pages_processed,
        "matches_seen": local_stats.matches_seen,
        "matches_fetched": local_stats.matches_fetched,
        "events_inserted": local_stats.events_inserted,
        "duplicate_events": local_stats.duplicate_events,
        "cutoff": cutoff,
        "archive_exhausted": archive_exhausted,
        "discovered_total_matches": discovered_total_matches,
    }


def _resolve_start_page(*, server_slug: str, start_page: int | None) -> int:
    if start_page is not None:
        return max(1, start_page)
    return get_player_event_resume_page(server_slug, mode="refresh")


def _select_servers(server_slug: str | None) -> list[dict[str, object]]:
    servers = list_historical_servers()
    if server_slug is None:
        return servers
    normalized = server_slug.strip()
    selected = [server for server in servers if server["slug"] == normalized]
    if not selected:
        raise ValueError(f"Unknown historical server slug: {server_slug}")
    return selected


def _coerce_match_list(payload: object) -> list[dict[str, object]]:
    if not isinstance(payload, list):
        return []
    return [item for item in payload if isinstance(item, dict)]


def _pick_match_timestamp(match_payload: dict[str, object]) -> str | None:
    for key in ("end", "start", "creation_time"):
        value = match_payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _stringify(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for manual or periodic player event ingestion."""
    parser = argparse.ArgumentParser(
        description="Player event refresh worker for HLL Vietnam.",
    )
    parser.add_argument(
        "mode",
        choices=("refresh", "loop"),
        help="refresh runs once; loop keeps the worker running periodically",
    )
    parser.add_argument(
        "--server",
        dest="server_slug",
        help="optional historical server slug",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        help="optional page cap for local validation",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        help="override CRCON page size",
    )
    parser.add_argument(
        "--start-page",
        type=int,
        help="override the saved resume page",
    )
    parser.add_argument(
        "--detail-workers",
        type=int,
        help="parallel worker count for per-match detail requests",
    )
    parser.add_argument(
        "--overlap-hours",
        type=int,
        help="override the incremental overlap window in hours",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=get_player_event_refresh_interval_seconds(),
        help="seconds to wait between loop runs",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=get_player_event_refresh_max_retries(),
        help="retry attempts after a failed refresh",
    )
    parser.add_argument(
        "--retry-delay",
        type=int,
        default=get_player_event_refresh_retry_delay_seconds(),
        help="seconds to wait between failed attempts",
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        help="optional safety cap for loop mode",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    """Run the player event worker CLI."""
    parser = build_arg_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.mode == "refresh":
        result = run_player_event_refresh(
            server_slug=args.server_slug,
            max_pages=args.max_pages,
            page_size=args.page_size,
            start_page=args.start_page,
            detail_workers=args.detail_workers,
            overlap_hours=args.overlap_hours,
        )
        print(json.dumps(result, indent=2))
        return 0

    if args.interval <= 0:
        raise ValueError("--interval must be a positive integer.")
    if args.retries < 0:
        raise ValueError("--retries must be zero or positive.")
    if args.retry_delay < 0:
        raise ValueError("--retry-delay must be zero or positive.")
    if args.max_runs is not None and args.max_runs <= 0:
        raise ValueError("--max-runs must be positive when provided.")

    run_periodic_player_event_refresh(
        interval_seconds=args.interval,
        max_retries=args.retries,
        retry_delay_seconds=args.retry_delay,
        server_slug=args.server_slug,
        max_pages=args.max_pages,
        page_size=args.page_size,
        detail_workers=args.detail_workers,
        max_runs=args.max_runs,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
