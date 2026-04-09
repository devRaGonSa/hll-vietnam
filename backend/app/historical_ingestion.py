"""Historical CRCON ingestion bootstrap and incremental refresh."""

from __future__ import annotations

import argparse
import json
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Iterable

from .config import (
    get_historical_crcon_detail_workers,
    get_historical_crcon_page_size,
    get_historical_data_source_kind,
    get_historical_refresh_overlap_hours,
)
from .data_sources import (
    SOURCE_KIND_PUBLIC_SCOREBOARD,
    SOURCE_KIND_RCON,
    HistoricalDataSource,
    build_historical_runtime_source_policy,
    resolve_historical_ingestion_data_source,
)
from .elo_mmr_engine import rebuild_elo_mmr_models
from .historical_snapshots import generate_and_persist_historical_snapshots
from .historical_storage import (
    finalize_backfill_progress,
    finalize_ingestion_run,
    get_backfill_resume_page,
    get_refresh_cutoff_for_server,
    initialize_historical_storage,
    list_historical_coverage_report,
    list_historical_servers,
    mark_backfill_progress_page_completed,
    mark_backfill_progress_started,
    start_ingestion_run,
    upsert_historical_match,
)
from .rcon_historical_worker import run_rcon_historical_capture_unlocked
from .writer_lock import backend_writer_lock, build_writer_lock_holder


ProgressCallback = Callable[[dict[str, object]], None]
ProgressPayloadFactory = Callable[[], dict[str, object]]
PROGRESS_HEARTBEAT_INTERVAL_SECONDS = 5.0


@dataclass(slots=True)
class IngestionStats:
    """Mutable counters for one ingestion execution."""

    pages_processed: int = 0
    matches_seen: int = 0
    matches_inserted: int = 0
    matches_updated: int = 0
    player_rows_inserted: int = 0
    player_rows_updated: int = 0

    def apply(self, delta: dict[str, int]) -> None:
        self.matches_inserted += delta.get("matches_inserted", 0)
        self.matches_updated += delta.get("matches_updated", 0)
        self.player_rows_inserted += delta.get("player_rows_inserted", 0)
        self.player_rows_updated += delta.get("player_rows_updated", 0)


def run_bootstrap(
    *,
    server_slug: str | None = None,
    max_pages: int | None = None,
    page_size: int | None = None,
    start_page: int | None = None,
    detail_workers: int | None = None,
    rebuild_snapshots: bool = True,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, object]:
    """Run a first full historical import against one or all configured servers."""
    with backend_writer_lock(
        holder=build_writer_lock_holder(
            f"app.historical_ingestion bootstrap:{server_slug or 'all-servers'}"
        )
    ):
        return _run_ingestion(
            mode="bootstrap",
            server_slug=server_slug,
            max_pages=max_pages,
            page_size=page_size,
            start_page=start_page,
            detail_workers=detail_workers,
            overlap_hours=None,
            incremental=False,
            rebuild_snapshots=rebuild_snapshots,
            progress_callback=progress_callback,
        )


def run_incremental_refresh(
    *,
    server_slug: str | None = None,
    max_pages: int | None = None,
    page_size: int | None = None,
    start_page: int | None = None,
    detail_workers: int | None = None,
    overlap_hours: int | None = None,
    rebuild_snapshots: bool = True,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, object]:
    """Refresh recent historical pages without replaying the whole archive."""
    with backend_writer_lock(
        holder=build_writer_lock_holder(
            f"app.historical_ingestion refresh:{server_slug or 'all-servers'}"
        )
    ):
        return _run_ingestion(
            mode="incremental",
            server_slug=server_slug,
            max_pages=max_pages,
            page_size=page_size,
            start_page=start_page,
            detail_workers=detail_workers,
            overlap_hours=overlap_hours,
            incremental=True,
            rebuild_snapshots=rebuild_snapshots,
            progress_callback=progress_callback,
        )


def _run_ingestion(
    *,
    mode: str,
    server_slug: str | None,
    max_pages: int | None,
    page_size: int | None,
    start_page: int | None,
    detail_workers: int | None,
    overlap_hours: int | None,
    incremental: bool,
    rebuild_snapshots: bool,
    progress_callback: ProgressCallback | None,
) -> dict[str, object]:
    run_started_at = time.monotonic()
    selected_servers = _select_servers(server_slug)
    _emit_progress(
        progress_callback,
        {
            "event": "historical-ingestion-run-started",
            "mode": mode,
            "server_scope": [str(server["slug"]) for server in selected_servers],
            "bounded_debug": any(
                value is not None for value in (server_slug, max_pages, page_size, start_page)
            ),
            "max_pages": max_pages,
            "page_size": page_size or get_historical_crcon_page_size(),
            "start_page": start_page,
            "detail_workers": detail_workers or get_historical_crcon_detail_workers(),
            "overlap_hours": overlap_hours if incremental else None,
        },
    )
    _emit_progress(
        progress_callback,
        {
            "event": "historical-storage-initialization-started",
            "mode": mode,
            "scope": "once-per-ingestion-run",
            "server_count": len(selected_servers),
        },
    )
    initialize_historical_storage()
    _emit_progress(
        progress_callback,
        {
            "event": "historical-storage-initialization-completed",
            "mode": mode,
            "scope": "once-per-ingestion-run",
            "storage_backend": "postgresql",
            "maintenance_passes": [
                "sql-first-migration-bootstrap",
                "historical-player-identity-normalization",
                "historical-match-identity-normalization",
            ],
        },
    )
    stats = IngestionStats()
    fallback_data_source, fallback_source_policy = resolve_historical_ingestion_data_source()
    processed_servers: list[dict[str, object]] = []
    active_runs: dict[str, int] = {}
    resolved_overlap_hours = (
        get_historical_refresh_overlap_hours()
        if overlap_hours is None
        else overlap_hours
    )
    if resolved_overlap_hours < 0:
        raise ValueError("--overlap-hours must be zero or positive.")

    primary_writer_result = _attempt_primary_rcon_writer(
        mode=mode,
        server_slug=server_slug,
        selected_servers=selected_servers,
        progress_callback=progress_callback,
    )
    source_policy = _resolve_ingestion_source_policy(
        fallback_source_policy=fallback_source_policy,
        primary_writer_result=primary_writer_result,
    )
    use_classic_fallback = _should_use_classic_fallback(primary_writer_result)
    _emit_progress(
        progress_callback,
        {
            "event": "historical-ingestion-source-selected",
            "mode": mode,
            "primary_source": source_policy.get("primary_source"),
            "selected_source": source_policy.get("selected_source"),
            "fallback_used": bool(source_policy.get("fallback_used")),
            "fallback_reason": source_policy.get("fallback_reason"),
        },
    )

    try:
        if use_classic_fallback:
            for server_index, server in enumerate(selected_servers, start=1):
                run_id = start_ingestion_run(mode=mode, target_server_slug=str(server["slug"]))
                active_runs[str(server["slug"])] = run_id
                mark_backfill_progress_started(
                    server_slug=str(server["slug"]),
                    mode=mode,
                    run_id=run_id,
                )
                cutoff = (
                    get_refresh_cutoff_for_server(
                        str(server["slug"]),
                        overlap_hours=resolved_overlap_hours,
                    )
                    if incremental
                    else None
                )
                resolved_start_page = _resolve_start_page(
                    start_page=start_page,
                    server_slug=str(server["slug"]),
                    mode=mode,
                )
                server_stats = _ingest_server(
                    server=server,
                    server_index=server_index,
                    server_count=len(selected_servers),
                    mode=mode,
                    run_id=run_id,
                    stats=stats,
                    data_source=fallback_data_source,
                    max_pages=max_pages,
                    page_size=page_size,
                    start_page=resolved_start_page,
                    detail_workers=detail_workers,
                    cutoff=cutoff,
                    progress_callback=progress_callback,
                    source_policy=source_policy,
                )
                processed_servers.append(server_stats)
                finalize_ingestion_run(
                    run_id,
                    status="success",
                    pages_processed=server_stats["pages_processed"],
                    matches_seen=server_stats["matches_seen"],
                    matches_inserted=server_stats["matches_inserted"],
                    matches_updated=server_stats["matches_updated"],
                    player_rows_inserted=server_stats["player_rows_inserted"],
                    player_rows_updated=server_stats["player_rows_updated"],
                    notes=f"public_name={server_stats['public_name']}",
                )
                finalize_backfill_progress(
                    server_slug=str(server["slug"]),
                    mode=mode,
                    run_id=run_id,
                    status="success",
                    archive_exhausted=bool(server_stats["archive_exhausted"]),
                )
                active_runs.pop(str(server["slug"]), None)
        if rebuild_snapshots:
            snapshot_result = generate_and_persist_historical_snapshots(server_key=server_slug)
            elo_mmr_result = rebuild_elo_mmr_models()
        else:
            snapshot_result = {
                "status": "skipped",
                "reason": "snapshot-rebuild-disabled",
                "generation_policy": "handled-by-caller",
            }
            elo_mmr_result = {
                "status": "skipped",
                "reason": "snapshot-rebuild-disabled",
            }
    except Exception as exc:
        for active_server_slug, run_id in active_runs.items():
            finalize_ingestion_run(
                run_id,
                status="failed",
                pages_processed=stats.pages_processed,
                matches_seen=stats.matches_seen,
                matches_inserted=stats.matches_inserted,
                matches_updated=stats.matches_updated,
                player_rows_inserted=stats.player_rows_inserted,
                player_rows_updated=stats.player_rows_updated,
                notes=str(exc),
            )
            finalize_backfill_progress(
                server_slug=active_server_slug,
                mode=mode,
                run_id=run_id,
                status="failed",
                error_message=str(exc),
            )
        raise
    result = {
        "status": "ok",
        "mode": mode,
        "source_provider": source_policy.get("selected_source"),
        "source_policy": source_policy,
        "primary_writer_result": primary_writer_result,
        "page_size": page_size or get_historical_crcon_page_size(),
        "start_page": start_page,
        "detail_workers": detail_workers or get_historical_crcon_detail_workers(),
        "overlap_hours": resolved_overlap_hours if incremental else None,
        "servers": processed_servers,
        "coverage": list_historical_coverage_report(server_slug=server_slug),
        "snapshot_result": snapshot_result,
        "elo_mmr_result": elo_mmr_result,
        "totals": {
            "pages_processed": stats.pages_processed,
            "matches_seen": stats.matches_seen,
            "matches_inserted": stats.matches_inserted,
            "matches_updated": stats.matches_updated,
            "player_rows_inserted": stats.player_rows_inserted,
            "player_rows_updated": stats.player_rows_updated,
        },
    }
    _emit_progress(
        progress_callback,
        {
            "event": "historical-ingestion-run-completed",
            "mode": mode,
            "elapsed_seconds": round(time.monotonic() - run_started_at, 3),
            "server_scope": [str(server["slug"]) for server in selected_servers],
            "bounded_debug": any(
                value is not None for value in (server_slug, max_pages, page_size, start_page)
            ),
            **result["totals"],
        },
    )
    return result


def _ingest_server(
    *,
    server: dict[str, object],
    server_index: int,
    server_count: int,
    mode: str,
    run_id: int,
    stats: IngestionStats,
    data_source: HistoricalDataSource,
    max_pages: int | None,
    page_size: int | None,
    start_page: int,
    detail_workers: int | None,
    cutoff: str | None,
    progress_callback: ProgressCallback | None,
    source_policy: dict[str, object],
) -> dict[str, object]:
    server_started_at = time.monotonic()
    resolved_page_size = page_size or get_historical_crcon_page_size()
    resolved_detail_workers = detail_workers or get_historical_crcon_detail_workers()
    page_limit = max_pages or 1000000
    start_page = max(1, start_page)
    local_stats = IngestionStats()
    public_info = data_source.fetch_public_info(base_url=str(server["scoreboard_base_url"]))
    discovered_total_matches: int | None = None
    last_page_processed: int | None = None
    archive_exhausted = False
    _emit_progress(
        progress_callback,
        {
            "event": "historical-ingestion-server-started",
            "mode": mode,
            "server_slug": server["slug"],
            "server_index": server_index,
            "server_count": server_count,
            "selected_source": source_policy.get("selected_source"),
            "fallback_used": bool(source_policy.get("fallback_used")),
            "start_page": start_page,
            "cutoff": cutoff,
            "max_pages": max_pages,
            "page_size": resolved_page_size,
            "detail_workers": resolved_detail_workers,
            "bounded_debug": any(value is not None for value in (max_pages, page_size, start_page)),
        },
    )

    for page_number in range(start_page, start_page + page_limit):
        with _progress_stage(
            progress_callback,
            stage="page-fetch",
            payload_factory=lambda: _build_progress_payload(
                mode=mode,
                server=server,
                server_index=server_index,
                server_count=server_count,
                stats=stats,
                local_stats=local_stats,
                current_page=page_number,
                extra={
                    "max_pages": max_pages,
                    "page_size": resolved_page_size,
                    "detail_workers": resolved_detail_workers,
                },
            ),
        ):
            payload = data_source.fetch_match_page(
                base_url=str(server["scoreboard_base_url"]),
                page=page_number,
                limit=resolved_page_size,
            )
        if discovered_total_matches is None:
            discovered_total_matches = _coerce_int(payload.get("total"))
        page_matches = _coerce_match_list(payload.get("maps"))
        if not page_matches:
            archive_exhausted = True
            break

        local_stats.pages_processed += 1
        stats.pages_processed += 1
        last_page_processed = page_number
        stop_after_page = False
        match_ids_to_fetch: list[str] = []

        for match_summary in page_matches:
            local_stats.matches_seen += 1
            stats.matches_seen += 1

            reference_timestamp = _pick_match_timestamp(match_summary)
            if cutoff and reference_timestamp and reference_timestamp < cutoff:
                stop_after_page = True
                continue

            match_id = _stringify(match_summary.get("id"))
            if match_id:
                match_ids_to_fetch.append(match_id)

        _emit_progress(
            progress_callback,
            {
                "event": "historical-ingestion-page-loaded",
                "mode": mode,
                "server_slug": server["slug"],
                "page": page_number,
                "selected_source": source_policy.get("selected_source"),
                "match_ids_to_detail": len(match_ids_to_fetch),
                "page_matches": len(page_matches),
                "cutoff_reached": stop_after_page,
            },
        )

        with _progress_stage(
            progress_callback,
            stage="detail-fetch",
            payload_factory=lambda: _build_progress_payload(
                mode=mode,
                server=server,
                server_index=server_index,
                server_count=server_count,
                stats=stats,
                local_stats=local_stats,
                current_page=page_number,
                extra={
                    "match_ids_to_detail": len(match_ids_to_fetch),
                    "page_matches": len(page_matches),
                    "page_size": resolved_page_size,
                    "detail_workers": resolved_detail_workers,
                },
            ),
        ):
            detail_payloads = list(
                data_source.fetch_match_details(
                    base_url=str(server["scoreboard_base_url"]),
                    match_ids=match_ids_to_fetch,
                    max_workers=resolved_detail_workers,
                )
            )

        with _progress_stage(
            progress_callback,
            stage="page-persist",
            payload_factory=lambda: _build_progress_payload(
                mode=mode,
                server=server,
                server_index=server_index,
                server_count=server_count,
                stats=stats,
                local_stats=local_stats,
                current_page=page_number,
                extra={
                    "detail_payloads": len(detail_payloads),
                    "match_ids_to_detail": len(match_ids_to_fetch),
                    "page_matches": len(page_matches),
                },
            ),
        ):
            for persisted_matches, detail_payload in enumerate(detail_payloads, start=1):
                delta = upsert_historical_match(
                    server_slug=str(server["slug"]),
                    match_payload=detail_payload,
                )
                local_stats.apply(delta)
                stats.apply(delta)
                if persisted_matches == len(detail_payloads) or persisted_matches % 10 == 0:
                    _emit_progress(
                        progress_callback,
                        {
                            "event": "historical-ingestion-persist-progress",
                            **_build_progress_payload(
                                mode=mode,
                                server=server,
                                server_index=server_index,
                                server_count=server_count,
                                stats=stats,
                                local_stats=local_stats,
                                current_page=page_number,
                                extra={
                                    "persisted_matches": persisted_matches,
                                    "detail_payloads": len(detail_payloads),
                                },
                            ),
                        },
                    )

        mark_backfill_progress_page_completed(
            server_slug=str(server["slug"]),
            mode=mode,
            page_number=page_number,
            page_size=resolved_page_size,
            run_id=run_id,
            discovered_total_matches=discovered_total_matches,
        )

        if stop_after_page:
            break

    server_result = {
        "server_slug": server["slug"],
        "public_name": _extract_public_name(public_info),
        "server_number": public_info.get("server_number") or server.get("server_number"),
        "source_provider": data_source.source_kind,
        "pages_processed": local_stats.pages_processed,
        "matches_seen": local_stats.matches_seen,
        "discovered_total_matches": discovered_total_matches,
        "matches_inserted": local_stats.matches_inserted,
        "matches_updated": local_stats.matches_updated,
        "player_rows_inserted": local_stats.player_rows_inserted,
        "player_rows_updated": local_stats.player_rows_updated,
        "start_page": start_page,
        "last_page_processed": last_page_processed,
        "cutoff": cutoff,
        "archive_exhausted": archive_exhausted,
    }
    _emit_progress(
        progress_callback,
        {
            "event": "historical-ingestion-server-completed",
            "mode": mode,
            "server_slug": server["slug"],
            "server_index": server_index,
            "server_count": server_count,
            "elapsed_seconds": round(time.monotonic() - server_started_at, 3),
            **_build_stats_payload(stats=stats, local_stats=local_stats),
            "last_page_processed": last_page_processed,
            "archive_exhausted": archive_exhausted,
            "discovered_total_matches": discovered_total_matches,
        },
    )
    return server_result


def _resolve_start_page(
    *,
    start_page: int | None,
    server_slug: str,
    mode: str,
) -> int:
    if start_page is not None:
        return max(1, start_page)
    if mode != "bootstrap":
        return 1
    return get_backfill_resume_page(server_slug, mode=mode)


def _attempt_primary_rcon_writer(
    *,
    mode: str,
    server_slug: str | None,
    selected_servers: list[dict[str, object]],
    progress_callback: ProgressCallback | None,
) -> dict[str, object]:
    configured_kind = get_historical_data_source_kind()
    if configured_kind != SOURCE_KIND_RCON:
        result = {
            "attempted": False,
            "status": "skipped",
            "primary_source": SOURCE_KIND_PUBLIC_SCOREBOARD,
            "selected_source": SOURCE_KIND_PUBLIC_SCOREBOARD,
            "fallback_used": False,
            "fallback_reason": None,
            "source_attempts": [],
        }
        _emit_progress(
            progress_callback,
            {
                "event": "historical-ingestion-rcon-primary-skipped",
                "mode": mode,
                "reason": "historical-data-source-configured-for-public-scoreboard",
            },
        )
        return result

    target_scope = server_slug or "all-configured-rcon-targets"
    _emit_progress(
        progress_callback,
        {
            "event": "historical-ingestion-rcon-primary-started",
            "mode": mode,
            "target_scope": target_scope,
            "servers": [str(server["slug"]) for server in selected_servers],
        },
    )
    try:
        capture_result = run_rcon_historical_capture_unlocked(target_key=server_slug)
    except Exception as exc:  # noqa: BLE001 - fallback remains explicit and controlled
        result = {
            "attempted": True,
            "status": "error",
            "primary_source": SOURCE_KIND_RCON,
            "selected_source": SOURCE_KIND_PUBLIC_SCOREBOARD,
            "fallback_used": True,
            "fallback_reason": "rcon-historical-writer-request-failed",
            "message": str(exc),
        }
        _emit_progress(
            progress_callback,
            {
                "event": "historical-ingestion-rcon-primary-failed",
                "mode": mode,
                "target_scope": target_scope,
                "message": str(exc),
            },
        )
        return result

    capture_run_status = str(capture_result.get("run_status") or capture_result.get("status") or "unknown")
    targets = list(capture_result.get("targets") or [])
    errors = list(capture_result.get("errors") or [])
    if targets:
        result = {
            "attempted": True,
            "status": "partial",
            "primary_source": SOURCE_KIND_RCON,
            "selected_source": SOURCE_KIND_PUBLIC_SCOREBOARD,
            "fallback_used": True,
            "fallback_reason": "rcon-primary-writer-succeeded-but-classic-match-archive-still-needs-fallback",
            "capture_result": capture_result,
        }
        _emit_progress(
            progress_callback,
            {
                "event": "historical-ingestion-rcon-primary-succeeded",
                "mode": mode,
                "target_scope": target_scope,
                "captured_targets": len(targets),
                "run_status": capture_run_status,
                "next_step": "classic-public-scoreboard-fallback-required",
            },
        )
        return result

    result = {
        "attempted": True,
        "status": "empty",
        "primary_source": SOURCE_KIND_RCON,
        "selected_source": SOURCE_KIND_PUBLIC_SCOREBOARD,
        "fallback_used": True,
        "fallback_reason": "rcon-historical-writer-returned-no-usable-samples",
        "capture_result": capture_result,
        "message": json.dumps(errors, separators=(",", ":")) if errors else None,
    }
    _emit_progress(
        progress_callback,
        {
            "event": "historical-ingestion-rcon-primary-empty",
            "mode": mode,
            "target_scope": target_scope,
            "run_status": capture_run_status,
            "errors": len(errors),
        },
    )
    return result


def _should_use_classic_fallback(primary_writer_result: dict[str, object]) -> bool:
    selected_source = str(primary_writer_result.get("selected_source") or "")
    return selected_source == SOURCE_KIND_PUBLIC_SCOREBOARD


def _resolve_ingestion_source_policy(
    *,
    fallback_source_policy: dict[str, object],
    primary_writer_result: dict[str, object],
) -> dict[str, object]:
    configured_kind = get_historical_data_source_kind()
    if configured_kind != SOURCE_KIND_RCON:
        return fallback_source_policy

    status = str(primary_writer_result.get("status") or "error")
    selected_source = str(
        primary_writer_result.get("selected_source") or SOURCE_KIND_PUBLIC_SCOREBOARD
    )
    fallback_reason = primary_writer_result.get("fallback_reason")
    message = primary_writer_result.get("message")
    if (
        fallback_reason
        == "rcon-primary-writer-succeeded-but-classic-match-archive-still-needs-fallback"
    ):
        message = (
            "RCON prospective capture succeeded first, but the classic historical_* "
            "archive still requires public-scoreboard for match-page import."
        )
    return build_historical_runtime_source_policy(
        operation="historical-ingestion",
        rcon_status=status,
        fallback_reason=str(fallback_reason) if fallback_reason else None,
        selected_source=selected_source,
        rcon_message=message if isinstance(message, str) else None,
    )


def _emit_progress(
    callback: ProgressCallback | None,
    payload: dict[str, object],
) -> None:
    if callback is None:
        return
    callback(payload)


def _build_progress_payload(
    *,
    mode: str,
    server: dict[str, object],
    server_index: int,
    server_count: int,
    stats: IngestionStats,
    local_stats: IngestionStats,
    current_page: int | None = None,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "mode": mode,
        "server_slug": server["slug"],
        "server_index": server_index,
        "server_count": server_count,
        "page": current_page,
        **_build_stats_payload(stats=stats, local_stats=local_stats),
    }
    if extra:
        payload.update(extra)
    return payload


def _build_stats_payload(
    *,
    stats: IngestionStats,
    local_stats: IngestionStats,
) -> dict[str, object]:
    return {
        "pages_processed_total": stats.pages_processed,
        "matches_seen_total": stats.matches_seen,
        "matches_inserted_total": stats.matches_inserted,
        "matches_updated_total": stats.matches_updated,
        "player_rows_inserted_total": stats.player_rows_inserted,
        "player_rows_updated_total": stats.player_rows_updated,
        "pages_processed_server": local_stats.pages_processed,
        "matches_seen_server": local_stats.matches_seen,
        "matches_inserted_server": local_stats.matches_inserted,
        "matches_updated_server": local_stats.matches_updated,
        "player_rows_inserted_server": local_stats.player_rows_inserted,
        "player_rows_updated_server": local_stats.player_rows_updated,
    }


@contextmanager
def _progress_stage(
    callback: ProgressCallback | None,
    *,
    stage: str,
    payload_factory: ProgressPayloadFactory,
):
    if callback is None:
        yield
        return

    started_at = time.monotonic()
    stop_event = threading.Event()

    _emit_progress(
        callback,
        {
            "event": "historical-ingestion-stage-started",
            "stage": stage,
            "started_at": _utc_now_iso(),
            **payload_factory(),
        },
    )

    heartbeat_thread = threading.Thread(
        target=_emit_progress_heartbeats,
        kwargs={
            "callback": callback,
            "stage": stage,
            "payload_factory": payload_factory,
            "stop_event": stop_event,
        },
        daemon=True,
        name=f"historical-ingestion-{stage}-heartbeat",
    )
    heartbeat_thread.start()
    try:
        yield
    finally:
        stop_event.set()
        heartbeat_thread.join(timeout=PROGRESS_HEARTBEAT_INTERVAL_SECONDS)
        _emit_progress(
            callback,
            {
                "event": "historical-ingestion-stage-completed",
                "stage": stage,
                "elapsed_seconds": round(time.monotonic() - started_at, 3),
                **payload_factory(),
            },
        )


def _emit_progress_heartbeats(
    *,
    callback: ProgressCallback,
    stage: str,
    payload_factory: ProgressPayloadFactory,
    stop_event: threading.Event,
) -> None:
    started_at = time.monotonic()
    while not stop_event.wait(PROGRESS_HEARTBEAT_INTERVAL_SECONDS):
        _emit_progress(
            callback,
            {
                "event": "historical-ingestion-heartbeat",
                "stage": stage,
                "elapsed_seconds": round(time.monotonic() - started_at, 3),
                **payload_factory(),
            },
        )


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


def _extract_public_name(public_info: dict[str, object]) -> str | None:
    name_value = public_info.get("name")
    if isinstance(name_value, str):
        return name_value
    if isinstance(name_value, dict):
        raw_name = name_value.get("name")
        return raw_name.strip() if isinstance(raw_name, str) and raw_name.strip() else None
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


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for manual historical ingestion runs."""
    parser = argparse.ArgumentParser(
        description="Historical CRCON ingestion for HLL Vietnam.",
    )
    parser.add_argument(
        "mode",
        choices=("bootstrap", "refresh"),
        help="bootstrap imports the archive, refresh only recent pages",
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
        help="override the resume page; bootstrap uses persisted progress when omitted",
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
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    """Run the historical ingestion CLI."""
    parser = build_arg_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    def _print_progress(payload: dict[str, object]) -> None:
        print(json.dumps(payload, ensure_ascii=True))

    if args.mode == "bootstrap":
        result = run_bootstrap(
            server_slug=args.server_slug,
            max_pages=args.max_pages,
            page_size=args.page_size,
            start_page=args.start_page,
            detail_workers=args.detail_workers,
            progress_callback=_print_progress,
        )
    else:
        result = run_incremental_refresh(
            server_slug=args.server_slug,
            max_pages=args.max_pages,
            page_size=args.page_size,
            start_page=args.start_page,
            detail_workers=args.detail_workers,
            overlap_hours=args.overlap_hours,
            progress_callback=_print_progress,
        )

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
