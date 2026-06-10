"""Local development loop for periodic historical CRCON refreshes."""

from __future__ import annotations

import argparse
import json
import time
import traceback
from datetime import date, datetime, time as datetime_time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .config import (
    DEFAULT_DB_MAINTENANCE_INTERVAL_SECONDS,
    get_db_maintenance_enabled,
    get_db_maintenance_interval_seconds,
    get_historical_full_snapshot_every_runs,
    get_historical_elo_mmr_min_new_samples,
    get_historical_elo_mmr_rebuild_interval_minutes,
    get_historical_refresh_interval_seconds,
    get_historical_refresh_max_retries,
    get_historical_refresh_retry_delay_seconds,
    get_historical_data_source_kind,
    get_public_full_refresh_enabled,
    get_public_full_refresh_time,
    get_public_full_refresh_timezone,
    get_public_ranking_refresh_interval_seconds,
    get_public_recent_matches_refresh_interval_seconds,
)
from .database_maintenance import run_database_maintenance_cleanup
from .elo_mmr_engine import rebuild_elo_mmr_models
from .elo_mmr_storage import get_latest_elo_mmr_generated_at
from .historical_ingestion import run_incremental_refresh
from .historical_snapshots import (
    generate_and_persist_historical_snapshots,
    generate_and_persist_priority_historical_snapshots,
    generate_and_persist_recent_historical_snapshots,
)
from .historical_storage import ALL_SERVERS_SLUG
from .rcon_annual_rankings import (
    SUPPORTED_ANNUAL_RANKING_METRICS,
    generate_annual_ranking_snapshot,
)
from .rcon_historical_leaderboards import refresh_ranking_snapshots
from .rcon_historical_leaderboards import SNAPSHOT_GENERATOR_SERVER_KEYS
from .rcon_historical_player_stats import (
    refresh_player_period_stats,
    refresh_player_search_index,
)
from .rcon_historical_storage import count_rcon_historical_samples_since
from .rcon_historical_worker import run_rcon_historical_capture
from .writer_lock import backend_writer_lock, build_writer_lock_holder

HOURLY_INTERVAL_SECONDS = 3600
DEFAULT_HISTORICAL_SERVER_SCOPE = (
    "comunidad-hispana-01",
    "comunidad-hispana-02",
)
_LAST_DATABASE_MAINTENANCE_RUN_AT: datetime | None = None
_LAST_PUBLIC_FULL_REFRESH_LOCAL_DATE: date | None = None
_LAST_PUBLIC_RANKING_REFRESH_AT: datetime | None = None
_LAST_PUBLIC_RECENT_MATCHES_REFRESH_AT: datetime | None = None
_PUBLIC_REFRESH_IN_PROGRESS: set[str] = set()
PUBLIC_FULL_REFRESH_YEAR = 2026
PUBLIC_REFRESH_LOCK_FULL = "public-full-refresh"
PUBLIC_REFRESH_LOCK_RANKING = "public-ranking-refresh"
PUBLIC_REFRESH_LOCK_RECENT_MATCHES = "public-recent-matches-refresh"


def run_periodic_historical_refresh(
    *,
    interval_seconds: int,
    max_retries: int,
    retry_delay_seconds: float,
    server_slug: str | None = None,
    max_pages: int | None = None,
    page_size: int | None = None,
    max_runs: int | None = None,
) -> None:
    """Run periodic historical refreshes and rebuild persisted snapshots."""
    completed_runs = 0
    print(
        json.dumps(
            {
                "event": "historical-refresh-loop-started",
                "interval_seconds": interval_seconds,
                "max_retries": max_retries,
                "retry_delay_seconds": retry_delay_seconds,
                "server_scope": _describe_refresh_scope(server_slug),
                "snapshot_scope": _describe_snapshot_scope(server_slug),
            },
            indent=2,
        )
    )
    print("Press Ctrl+C to stop.")

    last_historical_refresh_started_at: datetime | None = None
    loop_tick_seconds = _resolve_runner_tick_seconds(interval_seconds)
    try:
        while max_runs is None or completed_runs < max_runs:
            now = datetime.now(timezone.utc)
            historical_refresh_due = _is_interval_due(
                last_run_at=last_historical_refresh_started_at,
                interval_seconds=interval_seconds,
                now=now,
            )
            if historical_refresh_due:
                completed_runs += 1
                last_historical_refresh_started_at = now
                payload = _run_refresh_with_retries(
                    max_retries=max_retries,
                    retry_delay_seconds=retry_delay_seconds,
                    server_slug=server_slug,
                    max_pages=max_pages,
                    page_size=page_size,
                    run_number=completed_runs,
                )
                _record_public_refreshes_from_cycle(payload, now=now)
                _emit_json_log({"run": completed_runs, **payload})
            else:
                payload = _maybe_run_public_read_model_refreshes(
                    run_number=completed_runs,
                    now=now,
                )
                if payload["status"] != "skipped":
                    _emit_json_log({"run": completed_runs, **payload})

            if max_runs is not None and completed_runs >= max_runs:
                break

            time.sleep(loop_tick_seconds)
    except KeyboardInterrupt:
        print("\nHistorical refresh loop stopped by user.")


def _run_refresh_with_retries(
    *,
    max_retries: int,
    retry_delay_seconds: float,
    server_slug: str | None,
    max_pages: int | None,
    page_size: int | None,
    run_number: int,
) -> dict[str, Any]:
    attempt = 0
    while True:
        attempt += 1
        try:
            with backend_writer_lock(
                holder=build_writer_lock_holder(
                    f"app.historical_runner refresh:{server_slug or 'all-servers'}"
                )
            ):
                rcon_capture_result = _run_primary_rcon_capture()
                should_run_classic_fallback, classic_fallback_reason = (
                    _resolve_classic_fallback_policy(
                        server_slug=server_slug,
                        run_number=run_number,
                        rcon_capture_result=rcon_capture_result,
                    )
                )
                if should_run_classic_fallback:
                    refresh_result = run_incremental_refresh(
                        server_slug=server_slug,
                        max_pages=max_pages,
                        page_size=page_size,
                        rebuild_snapshots=False,
                    )
                    historical_snapshot_result = refresh_periodic_historical_snapshots(
                        server_slug=server_slug,
                        run_number=run_number,
                    )
                    elo_mmr_result = rebuild_elo_mmr_models()
                else:
                    should_generate_snapshots = _rcon_capture_has_new_useful_data(
                        rcon_capture_result
                    )
                    refresh_result = {
                        "status": "skipped",
                        "reason": "rcon-primary-cycle-no-classic-fallback-needed",
                    }
                    if should_generate_snapshots:
                        historical_snapshot_result = refresh_periodic_historical_snapshots(
                            server_slug=server_slug,
                            run_number=run_number,
                        )
                        historical_snapshot_result = {
                            **historical_snapshot_result,
                            "generation_policy": "rcon-primary-useful-cycle",
                            "reason": "rcon-primary-cycle-produced-new-useful-coverage",
                        }
                        elo_policy = _build_elo_mmr_rebuild_policy(
                            rcon_capture_result=rcon_capture_result
                        )
                        if bool(elo_policy["due"]):
                            elo_mmr_result = {
                                **rebuild_elo_mmr_models(),
                                "generation_policy": "rcon-primary-useful-cycle-elo-rebuild-due",
                                "reason": "rcon-primary-useful-cycle-met-elo-rebuild-threshold",
                                **elo_policy,
                            }
                        else:
                            elo_mmr_result = {
                                "status": "skipped",
                                "reason": "rcon-primary-useful-cycle-elo-rebuild-throttled",
                                "generation_policy": "rcon-primary-useful-cycle-elo-rebuild-throttled",
                                **elo_policy,
                            }
                    else:
                        historical_snapshot_result = {
                            "status": "skipped",
                            "reason": "rcon-primary-cycle-had-no-new-useful-data",
                            "generation_policy": "rcon-primary-no-new-useful-data",
                        }
                        elo_mmr_result = {
                            "status": "skipped",
                            "reason": "rcon-primary-cycle-had-no-new-useful-data",
                            "generation_policy": "rcon-primary-no-new-useful-data",
                            **_build_elo_mmr_rebuild_policy(
                                rcon_capture_result=rcon_capture_result
                            ),
                        }
                player_search_index_result = refresh_periodic_player_search_index(
                    server_slug=server_slug,
                    run_number=run_number,
                )
                player_period_stats_result = refresh_periodic_player_period_stats(
                    server_slug=server_slug,
                    run_number=run_number,
                )
                ranking_snapshot_result = refresh_periodic_ranking_snapshots(
                    server_slug=server_slug,
                    run_number=run_number,
                )
                recent_matches_event_result = _maybe_refresh_recent_matches_after_capture(
                    rcon_capture_result=rcon_capture_result,
                    server_slug=server_slug,
                    run_number=run_number,
                )
                maintenance_result = _maybe_run_database_maintenance()
            return {
                "status": _resolve_refresh_cycle_status(
                    refresh_result=refresh_result,
                    historical_snapshot_result=historical_snapshot_result,
                    player_search_index_result=player_search_index_result,
                    player_period_stats_result=player_period_stats_result,
                    ranking_snapshot_result=ranking_snapshot_result,
                    recent_matches_event_result=recent_matches_event_result,
                    elo_mmr_result=elo_mmr_result,
                    database_maintenance_result=maintenance_result,
                ),
                "attempts_used": attempt,
                "max_retries": max_retries,
                "rcon_capture_result": rcon_capture_result,
                "classic_fallback_used": should_run_classic_fallback,
                "classic_fallback_reason": classic_fallback_reason,
                "refresh_result": refresh_result,
                "historical_snapshot_result": historical_snapshot_result,
                "snapshot_result": historical_snapshot_result,
                "player_search_index_result": player_search_index_result,
                "player_period_stats_result": player_period_stats_result,
                "ranking_snapshot_result": ranking_snapshot_result,
                "recent_matches_event_result": recent_matches_event_result,
                "elo_mmr_result": elo_mmr_result,
                "database_maintenance_result": maintenance_result,
            }
        except Exception as exc:
            failure_payload = {
                "event": "historical-refresh-attempt-failed",
                "attempt": attempt,
                "max_retries": max_retries,
                "server_scope": _describe_refresh_scope(server_slug),
                "snapshot_scope": _describe_snapshot_scope(server_slug),
                "error_type": type(exc).__name__,
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }
            _emit_json_log(failure_payload)
            if attempt > max_retries:
                return {
                    "status": "error",
                    "attempts_used": attempt,
                    "max_retries": max_retries,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "traceback": failure_payload["traceback"],
                }
            if retry_delay_seconds > 0:
                time.sleep(retry_delay_seconds)


def generate_historical_snapshots(
    *,
    server_slug: str | None = None,
    run_number: int = 1,
) -> dict[str, Any]:
    """Build priority prewarm snapshots on every run and the full matrix on cadence."""
    generated_at = datetime.now(timezone.utc)
    full_snapshot_every_runs = get_historical_full_snapshot_every_runs()
    should_run_full_refresh = bool(server_slug) or run_number % full_snapshot_every_runs == 0
    _emit_json_log(
        {
            "event": "historical-snapshot-refresh-started",
            "run_number": run_number,
            "snapshot_step": "full-matrix" if should_run_full_refresh else "priority-prewarm",
            "server_slug": server_slug,
            "snapshot_scope": _describe_snapshot_scope(server_slug),
        }
    )
    if should_run_full_refresh:
        result = generate_and_persist_historical_snapshots(
            server_key=server_slug,
            generated_at=generated_at,
        )
    else:
        result = generate_and_persist_priority_historical_snapshots(
            generated_at=generated_at,
        )
    return {
        **result,
        "run_number": run_number,
        "full_snapshot_every_runs": full_snapshot_every_runs,
        "prewarm_only": not should_run_full_refresh,
        "refresh_interval_seconds": get_historical_refresh_interval_seconds(),
        "includes_monthly_mvp_v2": True,
    }


def refresh_periodic_historical_snapshots(
    *,
    server_slug: str | None = None,
    run_number: int = 1,
) -> dict[str, Any]:
    """Refresh legacy historical snapshots without aborting operational read-model refreshes."""
    try:
        return generate_historical_snapshots(
            server_slug=server_slug,
            run_number=run_number,
        )
    except Exception as exc:  # noqa: BLE001 - legacy failures must remain visible but isolated
        failure_result = {
            "status": "error",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
            "run_number": run_number,
            "refresh_interval_seconds": get_historical_refresh_interval_seconds(),
            "server_slug": server_slug,
            "generation_policy": "periodic-historical-refresh-cycle",
            "snapshot_scope": _describe_snapshot_scope(server_slug),
            "legacy_block": "historical-snapshots",
        }
        _emit_json_log({"event": "historical-snapshot-refresh-failed", **failure_result})
        return failure_result


def refresh_periodic_ranking_snapshots(
    *,
    server_slug: str | None = None,
    run_number: int = 1,
) -> dict[str, Any]:
    """Refresh the public weekly/monthly ranking snapshot matrix for the current cycle."""
    _emit_json_log(
        {
            "event": "ranking-snapshot-refresh-started",
            "run_number": run_number,
            "server_slug": server_slug,
            "snapshot_scope": _describe_snapshot_scope(server_slug),
            "ranking_snapshot_limit": 30,
        }
    )
    result = refresh_ranking_snapshots(limit=30)
    return {
        **result,
        "run_number": run_number,
        "refresh_interval_seconds": get_historical_refresh_interval_seconds(),
        "server_slug": server_slug,
        "generation_policy": "periodic-historical-refresh-cycle",
        "recommended_frequency": {
            "weekly": "5-15-minutes",
            "monthly": "15-30-minutes",
        },
    }


def refresh_periodic_player_search_index(
    *,
    server_slug: str | None = None,
    run_number: int = 1,
) -> dict[str, Any]:
    """Refresh the player search read model without aborting the remaining cycle on failure."""
    _emit_json_log(
        {
            "event": "player-search-index-refresh-started",
            "run_number": run_number,
            "server_slug": server_slug,
            "refresh_scope": "supported-public-player-search-scopes",
        }
    )
    try:
        result = refresh_player_search_index()
    except Exception as exc:  # noqa: BLE001 - one read-model failure must stay visible
        failure_result = {
            "status": "error",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "run_number": run_number,
            "refresh_interval_seconds": get_historical_refresh_interval_seconds(),
            "server_slug": server_slug,
            "generation_policy": "periodic-historical-refresh-cycle",
            "scope_policy": "always-refresh-supported-public-player-search-scopes",
        }
        _emit_json_log({"event": "player-search-index-refresh-failed", **failure_result})
        return failure_result
    return {
        **result,
        "run_number": run_number,
        "refresh_interval_seconds": get_historical_refresh_interval_seconds(),
        "server_slug": server_slug,
        "generation_policy": "periodic-historical-refresh-cycle",
        "scope_policy": "always-refresh-supported-public-player-search-scopes",
    }


def refresh_periodic_player_period_stats(
    *,
    server_slug: str | None = None,
    run_number: int = 1,
) -> dict[str, Any]:
    """Refresh the player period stats read model without aborting the remaining cycle on failure."""
    _emit_json_log(
        {
            "event": "player-period-stats-refresh-started",
            "run_number": run_number,
            "server_slug": server_slug,
            "refresh_scope": "supported-public-player-period-scopes",
        }
    )
    try:
        result = refresh_player_period_stats()
    except Exception as exc:  # noqa: BLE001 - one read-model failure must stay visible
        failure_result = {
            "status": "error",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "run_number": run_number,
            "refresh_interval_seconds": get_historical_refresh_interval_seconds(),
            "server_slug": server_slug,
            "generation_policy": "periodic-historical-refresh-cycle",
            "scope_policy": "always-refresh-supported-public-player-period-scopes",
        }
        _emit_json_log({"event": "player-period-stats-refresh-failed", **failure_result})
        return failure_result
    return {
        **result,
        "run_number": run_number,
        "refresh_interval_seconds": get_historical_refresh_interval_seconds(),
        "server_slug": server_slug,
        "generation_policy": "periodic-historical-refresh-cycle",
        "scope_policy": "always-refresh-supported-public-player-period-scopes",
    }


def _maybe_run_public_read_model_refreshes(
    *,
    run_number: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Run due public read-model refreshes without doing the heavy RCON capture cycle."""
    anchor = _as_utc(now or datetime.now(timezone.utc))
    results: dict[str, Any] = {}

    if _is_public_full_refresh_due(anchor):
        results["public_full_refresh_result"] = _run_non_overlapping_public_refresh(
            PUBLIC_REFRESH_LOCK_FULL,
            lambda: refresh_public_full_read_models(run_number=run_number, now=anchor),
        )

    if _is_public_interval_refresh_due(
        last_run_at=_LAST_PUBLIC_RANKING_REFRESH_AT,
        interval_seconds=get_public_ranking_refresh_interval_seconds(),
        now=anchor,
    ):
        results["ranking_snapshot_result"] = _run_non_overlapping_public_refresh(
            PUBLIC_REFRESH_LOCK_RANKING,
            lambda: refresh_public_ranking_snapshots(run_number=run_number, now=anchor),
        )

    if _is_public_interval_refresh_due(
        last_run_at=_LAST_PUBLIC_RECENT_MATCHES_REFRESH_AT,
        interval_seconds=get_public_recent_matches_refresh_interval_seconds(),
        now=anchor,
    ):
        results["recent_matches_snapshot_result"] = _run_non_overlapping_public_refresh(
            PUBLIC_REFRESH_LOCK_RECENT_MATCHES,
            lambda: refresh_public_recent_matches_snapshots(
                run_number=run_number,
                now=anchor,
                trigger="polling-interval",
            ),
        )

    if not results:
        return {
            "event": "public-read-model-refresh-scheduler-skipped",
            "status": "skipped",
            "reason": "no-public-refresh-due",
        }

    return {
        "event": "public-read-model-refresh-scheduler-completed",
        "status": _resolve_refresh_cycle_status(**results),
        **results,
    }


def refresh_public_full_read_models(
    *,
    run_number: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Refresh the full public read-model set intended for the low-load nightly window."""
    global _LAST_PUBLIC_FULL_REFRESH_LOCAL_DATE

    anchor = _as_utc(now or datetime.now(timezone.utc))
    local_anchor = anchor.astimezone(_get_public_refresh_zone())
    steps: dict[str, Any] = {}
    started = time.perf_counter()
    _emit_json_log(
        {
            "event": "public-full-refresh-started",
            "run_number": run_number,
            "scheduled_local_date": local_anchor.date().isoformat(),
            "scheduled_time": get_public_full_refresh_time(),
            "timezone": get_public_full_refresh_timezone(),
        }
    )

    steps["historical_snapshots"] = _run_public_refresh_step(
        "historical-snapshots-full",
        lambda: generate_and_persist_historical_snapshots(generated_at=anchor),
    )
    steps["ranking_snapshots"] = _run_public_refresh_step(
        "ranking-snapshots-weekly-monthly",
        lambda: refresh_periodic_ranking_snapshots(run_number=run_number),
    )
    steps["annual_ranking_snapshots"] = _run_public_refresh_step(
        "annual-ranking-snapshots-2026",
        lambda: refresh_public_annual_ranking_snapshots(year=PUBLIC_FULL_REFRESH_YEAR),
    )
    steps["player_search_index"] = _run_public_refresh_step(
        "player-search-index",
        refresh_player_search_index,
    )
    steps["player_period_stats"] = _run_public_refresh_step(
        "player-period-stats",
        refresh_player_period_stats,
    )

    status = _resolve_refresh_cycle_status(**steps)
    if status in {"ok", "partial"}:
        _LAST_PUBLIC_FULL_REFRESH_LOCAL_DATE = local_anchor.date()
    result = {
        "status": status,
        "run_number": run_number,
        "generated_at": _to_iso(anchor),
        "duration_ms": _elapsed_ms(started),
        "timezone": get_public_full_refresh_timezone(),
        "scheduled_time": get_public_full_refresh_time(),
        "steps": steps,
    }
    _emit_json_log({"event": "public-full-refresh-completed", **result})
    return result


def refresh_public_ranking_snapshots(
    *,
    run_number: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Refresh weekly/monthly public ranking snapshots on the short cadence."""
    global _LAST_PUBLIC_RANKING_REFRESH_AT

    anchor = _as_utc(now or datetime.now(timezone.utc))
    started = time.perf_counter()
    _emit_json_log(
        {
            "event": "public-ranking-refresh-started",
            "run_number": run_number,
            "interval_seconds": get_public_ranking_refresh_interval_seconds(),
        }
    )
    result = refresh_periodic_ranking_snapshots(run_number=run_number)
    status = str(result.get("status") or "ok")
    if status != "error":
        _LAST_PUBLIC_RANKING_REFRESH_AT = anchor
    completed = {
        **result,
        "duration_ms": _elapsed_ms(started),
        "generated_at": _to_iso(anchor),
        "interval_seconds": get_public_ranking_refresh_interval_seconds(),
        "generation_policy": "public-ranking-short-cadence",
    }
    _emit_json_log({"event": "public-ranking-refresh-completed", **completed})
    return completed


def refresh_public_recent_matches_snapshots(
    *,
    run_number: int,
    now: datetime | None = None,
    trigger: str,
    server_slug: str | None = None,
) -> dict[str, Any]:
    """Refresh recent-match snapshots after match-finalization evidence or short polling."""
    global _LAST_PUBLIC_RECENT_MATCHES_REFRESH_AT

    anchor = _as_utc(now or datetime.now(timezone.utc))
    started = time.perf_counter()
    _emit_json_log(
        {
            "event": "public-recent-matches-refresh-started",
            "run_number": run_number,
            "trigger": trigger,
            "server_slug": server_slug,
            "interval_seconds": get_public_recent_matches_refresh_interval_seconds(),
        }
    )
    try:
        result = generate_and_persist_recent_historical_snapshots(
            server_key=server_slug,
            generated_at=anchor,
        )
    except Exception as exc:  # noqa: BLE001 - scheduler must keep the runner alive
        result = {
            "status": "error",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
    status = str(result.get("status") or "ok")
    if status != "error":
        _LAST_PUBLIC_RECENT_MATCHES_REFRESH_AT = anchor
    completed = {
        **result,
        "duration_ms": _elapsed_ms(started),
        "generated_at": _to_iso(anchor),
        "trigger": trigger,
        "server_slug": server_slug,
        "interval_seconds": get_public_recent_matches_refresh_interval_seconds(),
    }
    _emit_json_log({"event": "public-recent-matches-refresh-completed", **completed})
    return completed


def refresh_public_annual_ranking_snapshots(
    *,
    year: int = PUBLIC_FULL_REFRESH_YEAR,
    limit: int = 20,
) -> dict[str, Any]:
    """Refresh supported annual ranking snapshots for all public scopes."""
    combinations = [
        (server_key, metric)
        for server_key in SNAPSHOT_GENERATOR_SERVER_KEYS
        for metric in SUPPORTED_ANNUAL_RANKING_METRICS
    ]
    results: list[dict[str, Any]] = []
    succeeded = 0
    failed = 0
    for server_key, metric in combinations:
        try:
            payload = generate_annual_ranking_snapshot(
                year=year,
                server_key=None if server_key == ALL_SERVERS_SLUG else server_key,
                metric=metric,
                limit=limit,
                replace_existing=True,
            )
            snapshot = payload.get("snapshot") if isinstance(payload, dict) else {}
            succeeded += 1
            results.append(
                {
                    "status": "ok",
                    "year": year,
                    "server_key": server_key,
                    "metric": metric,
                    "snapshot_id": snapshot.get("id") if isinstance(snapshot, dict) else None,
                    "ranked_players": int(payload.get("ranked_players") or 0),
                    "source_matches_count": int(payload.get("source_matches_count") or 0),
                }
            )
        except Exception as exc:  # noqa: BLE001 - report per-snapshot failures
            failed += 1
            results.append(
                {
                    "status": "error",
                    "year": year,
                    "server_key": server_key,
                    "metric": metric,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )

    status = "ok"
    if failed and succeeded:
        status = "partial"
    elif failed:
        status = "error"
    return {
        "status": status,
        "year": year,
        "limit": limit,
        "combinations_expected": len(combinations),
        "totals": {
            "succeeded": succeeded,
            "failed": failed,
        },
        "results": results,
    }


def get_next_public_full_refresh_at(
    *,
    now: datetime | None = None,
) -> datetime:
    """Return the next configured daily public full refresh in UTC."""
    anchor = _as_utc(now or datetime.now(timezone.utc))
    zone = _get_public_refresh_zone()
    local_anchor = anchor.astimezone(zone)
    hour, minute = (int(part) for part in get_public_full_refresh_time().split(":"))
    candidate = datetime.combine(
        local_anchor.date(),
        datetime_time(hour=hour, minute=minute),
        tzinfo=zone,
    )
    if local_anchor >= candidate:
        candidate += timedelta(days=1)
    return candidate.astimezone(timezone.utc)


def _maybe_refresh_recent_matches_after_capture(
    *,
    rcon_capture_result: dict[str, Any],
    server_slug: str | None,
    run_number: int,
) -> dict[str, Any]:
    if not _rcon_capture_materialized_finished_match(rcon_capture_result):
        return {
            "status": "skipped",
            "reason": "no-materialized-finished-match-detected",
            "trigger": "rcon-capture",
        }
    return _run_non_overlapping_public_refresh(
        PUBLIC_REFRESH_LOCK_RECENT_MATCHES,
        lambda: refresh_public_recent_matches_snapshots(
            run_number=run_number,
            trigger="rcon-capture-materialized-match",
            server_slug=server_slug,
        ),
    )


def _run_public_refresh_step(
    step_name: str,
    callback: Any,
) -> dict[str, Any]:
    started = time.perf_counter()
    _emit_json_log({"event": "public-refresh-step-started", "step": step_name})
    try:
        result = callback()
    except Exception as exc:  # noqa: BLE001 - keep neighboring refreshes running
        result = {
            "status": "error",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "traceback": traceback.format_exc(),
        }
    completed = {
        **result,
        "step": step_name,
        "duration_ms": _elapsed_ms(started),
    }
    _emit_json_log({"event": "public-refresh-step-completed", **completed})
    return completed


def _run_non_overlapping_public_refresh(
    refresh_key: str,
    callback: Any,
) -> dict[str, Any]:
    if refresh_key in _PUBLIC_REFRESH_IN_PROGRESS:
        return {
            "status": "skipped",
            "reason": "refresh-already-in-progress",
            "refresh_key": refresh_key,
        }
    _PUBLIC_REFRESH_IN_PROGRESS.add(refresh_key)
    try:
        return callback()
    finally:
        _PUBLIC_REFRESH_IN_PROGRESS.discard(refresh_key)


def _record_public_refreshes_from_cycle(
    payload: dict[str, Any],
    *,
    now: datetime,
) -> None:
    global _LAST_PUBLIC_RANKING_REFRESH_AT, _LAST_PUBLIC_RECENT_MATCHES_REFRESH_AT

    ranking_result = payload.get("ranking_snapshot_result")
    if isinstance(ranking_result, dict) and ranking_result.get("status") != "error":
        _LAST_PUBLIC_RANKING_REFRESH_AT = now
    recent_result = payload.get("recent_matches_event_result")
    if isinstance(recent_result, dict) and recent_result.get("status") not in {
        "error",
        "skipped",
    }:
        _LAST_PUBLIC_RECENT_MATCHES_REFRESH_AT = now


def _is_public_full_refresh_due(now: datetime) -> bool:
    if not get_public_full_refresh_enabled():
        return False
    local_now = now.astimezone(_get_public_refresh_zone())
    hour, minute = (int(part) for part in get_public_full_refresh_time().split(":"))
    scheduled_today = datetime.combine(
        local_now.date(),
        datetime_time(hour=hour, minute=minute),
        tzinfo=local_now.tzinfo,
    )
    return (
        local_now >= scheduled_today
        and _LAST_PUBLIC_FULL_REFRESH_LOCAL_DATE != local_now.date()
    )


def _is_public_interval_refresh_due(
    *,
    last_run_at: datetime | None,
    interval_seconds: int,
    now: datetime,
) -> bool:
    return _is_interval_due(
        last_run_at=last_run_at,
        interval_seconds=interval_seconds,
        now=now,
    )


def _is_interval_due(
    *,
    last_run_at: datetime | None,
    interval_seconds: int,
    now: datetime,
) -> bool:
    if last_run_at is None:
        return True
    elapsed_seconds = (now - _as_utc(last_run_at)).total_seconds()
    return elapsed_seconds >= interval_seconds


def _resolve_runner_tick_seconds(interval_seconds: int) -> int:
    intervals = [
        interval_seconds,
        get_public_ranking_refresh_interval_seconds(),
        get_public_recent_matches_refresh_interval_seconds(),
    ]
    return max(1, min(intervals))


def _get_public_refresh_zone() -> ZoneInfo:
    timezone_name = get_public_full_refresh_timezone()
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as error:
        raise ValueError(
            f"HLL_PUBLIC_FULL_REFRESH_TIMEZONE is not a valid IANA timezone: {timezone_name}"
        ) from error


def _rcon_capture_materialized_finished_match(
    rcon_capture_result: dict[str, Any],
) -> bool:
    totals = rcon_capture_result.get("totals")
    if isinstance(totals, dict) and int(totals.get("materialized_matches_inserted") or 0) > 0:
        return True
    targets = rcon_capture_result.get("targets")
    if not isinstance(targets, list):
        return False
    for target in targets:
        if not isinstance(target, dict):
            continue
        if int(target.get("materialized_matches_inserted") or 0) > 0:
            return True
    return False


def _elapsed_ms(started: float) -> int:
    return int((time.perf_counter() - started) * 1000)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _to_iso(value: datetime) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")


def _resolve_refresh_cycle_status(**results: dict[str, Any]) -> str:
    statuses = [
        str(result.get("status") or "").strip().lower()
        for result in results.values()
        if isinstance(result, dict) and result.get("status") is not None
    ]
    if not statuses:
        return "ok"
    if any(status == "error" for status in statuses):
        ok_like_statuses = {"ok", "skipped"}
        if all(status not in ok_like_statuses for status in statuses):
            return "error"
        return "partial"
    if any(status == "partial" for status in statuses):
        return "partial"
    return "ok"


def _emit_json_log(payload: dict[str, Any]) -> None:
    """Print JSON logs that remain safe for Compose and log collectors."""
    print(json.dumps(payload, ensure_ascii=True, default=str), flush=True)


def _maybe_run_database_maintenance(*, now: datetime | None = None) -> dict[str, Any]:
    """Optionally run scheduled database maintenance without crashing the runner."""
    global _LAST_DATABASE_MAINTENANCE_RUN_AT

    anchor = now.astimezone(timezone.utc) if now else datetime.now(timezone.utc)
    if not get_db_maintenance_enabled():
        result = {"status": "skipped", "reason": "disabled", "enabled": False}
        _emit_json_log({"event": "database-maintenance-scheduler-skipped-disabled", **result})
        return result

    interval_seconds, interval_source = _resolve_db_maintenance_interval_seconds()
    if _LAST_DATABASE_MAINTENANCE_RUN_AT is not None:
        elapsed_seconds = max(
            0,
            int((anchor - _LAST_DATABASE_MAINTENANCE_RUN_AT).total_seconds()),
        )
        if elapsed_seconds < interval_seconds:
            result = {
                "status": "skipped",
                "reason": "not-due",
                "enabled": True,
                "interval_seconds": interval_seconds,
                "interval_source": interval_source,
                "elapsed_seconds": elapsed_seconds,
                "last_run_at": _LAST_DATABASE_MAINTENANCE_RUN_AT.isoformat().replace(
                    "+00:00", "Z"
                ),
            }
            _emit_json_log({"event": "database-maintenance-scheduler-skipped-not-due", **result})
            return result

    _emit_json_log(
        {
            "event": "database-maintenance-scheduler-started",
            "enabled": True,
            "interval_seconds": interval_seconds,
            "interval_source": interval_source,
            "scheduled_at": anchor.isoformat().replace("+00:00", "Z"),
        }
    )
    try:
        result = run_database_maintenance_cleanup(apply=True, now=anchor)
    except Exception as exc:  # noqa: BLE001 - scheduler must not crash the runner
        result = {
            "status": "error",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "enabled": True,
            "interval_seconds": interval_seconds,
            "interval_source": interval_source,
        }
        _emit_json_log({"event": "database-maintenance-scheduler-failed", **result})
        return result

    if result.get("status") == "ok":
        _LAST_DATABASE_MAINTENANCE_RUN_AT = anchor
        _emit_json_log(
            {
                "event": "database-maintenance-scheduler-completed",
                "enabled": True,
                "interval_seconds": interval_seconds,
                "interval_source": interval_source,
                "result": result,
            }
        )
        return result

    failed_result = {
        "enabled": True,
        "interval_seconds": interval_seconds,
        "interval_source": interval_source,
        "result": result,
    }
    _emit_json_log({"event": "database-maintenance-scheduler-failed", **failed_result})
    return result


def _resolve_db_maintenance_interval_seconds() -> tuple[int, str]:
    """Return a safe maintenance interval even if env configuration is invalid."""
    try:
        return get_db_maintenance_interval_seconds(), "env"
    except ValueError:
        return DEFAULT_DB_MAINTENANCE_INTERVAL_SECONDS, "default-invalid-env-fallback"


def _describe_refresh_scope(server_slug: str | None) -> list[str]:
    if server_slug:
        return [server_slug]
    return list(DEFAULT_HISTORICAL_SERVER_SCOPE)


def _describe_snapshot_scope(server_slug: str | None) -> list[str]:
    if server_slug:
        return [server_slug, "all-servers"]
    return [*DEFAULT_HISTORICAL_SERVER_SCOPE, "all-servers"]


def _run_primary_rcon_capture() -> dict[str, Any]:
    if get_historical_data_source_kind() != "rcon":
        return {
            "status": "skipped",
            "reason": "historical-data-source-configured-without-rcon-primary",
        }
    return run_rcon_historical_capture()


def _resolve_classic_fallback_policy(
    *,
    server_slug: str | None,
    run_number: int,
    rcon_capture_result: dict[str, Any],
) -> tuple[bool, str]:
    if get_historical_data_source_kind() != "rcon":
        return True, "public-scoreboard-configured-as-primary-historical-source"

    if not _rcon_capture_has_usable_results(rcon_capture_result):
        return True, "rcon-historical-capture-failed-or-returned-no-usable-targets"

    if server_slug:
        return True, "manual-server-scope-still-needs-classic-historical-fallback"

    if run_number % get_historical_full_snapshot_every_runs() == 0:
        return True, "periodic-classic-fallback-for-competitive-historical-coverage"

    return False, "rcon-primary-cycle-succeeded-without-needing-classic-fallback"


def _rcon_capture_has_usable_results(rcon_capture_result: dict[str, Any]) -> bool:
    if rcon_capture_result.get("status") != "ok":
        return False
    targets = rcon_capture_result.get("targets")
    return isinstance(targets, list) and len(targets) > 0


def _rcon_capture_has_new_useful_data(rcon_capture_result: dict[str, Any]) -> bool:
    if rcon_capture_result.get("status") != "ok":
        return False
    totals = rcon_capture_result.get("totals")
    if isinstance(totals, dict) and int(totals.get("samples_inserted") or 0) > 0:
        return True
    if isinstance(totals, dict) and int(totals.get("admin_log_events_inserted") or 0) > 0:
        return True
    if isinstance(totals, dict) and int(totals.get("materialized_matches_inserted") or 0) > 0:
        return True
    targets = rcon_capture_result.get("targets")
    if not isinstance(targets, list):
        return False
    return any(bool(target.get("sample_inserted")) for target in targets if isinstance(target, dict))


def _build_elo_mmr_rebuild_policy(
    *,
    rcon_capture_result: dict[str, Any],
) -> dict[str, Any]:
    interval_minutes = get_historical_elo_mmr_rebuild_interval_minutes()
    min_new_samples = get_historical_elo_mmr_min_new_samples()
    last_generated_at = get_latest_elo_mmr_generated_at()
    last_generated_at_iso = (
        last_generated_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        if last_generated_at is not None
        else None
    )
    minutes_since_last_rebuild = None
    if last_generated_at is not None:
        minutes_since_last_rebuild = int(
            max(
                0,
                (
                    datetime.now(timezone.utc) - last_generated_at.astimezone(timezone.utc)
                ).total_seconds() // 60,
            )
        )
    samples_since_last_rebuild = count_rcon_historical_samples_since(last_generated_at_iso)
    due = (
        _rcon_capture_has_new_useful_data(rcon_capture_result)
        and samples_since_last_rebuild >= min_new_samples
        and (
            last_generated_at is None
            or minutes_since_last_rebuild is None
            or minutes_since_last_rebuild >= interval_minutes
        )
    )
    return {
        "policy": "min-new-rcon-samples-and-minutes-since-last-successful-rebuild",
        "due": due,
        "last_generated_at": last_generated_at_iso,
        "samples_since_last_rebuild": samples_since_last_rebuild,
        "minutes_since_last_rebuild": minutes_since_last_rebuild,
        "rebuild_interval_minutes": interval_minutes,
        "min_new_samples": min_new_samples,
    }


def main() -> None:
    """Allow local scheduled historical refresh execution without external infra."""
    parser = argparse.ArgumentParser(
        description="Run periodic historical refreshes and regenerate snapshots for HLL Vietnam.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=get_historical_refresh_interval_seconds(),
        help="Seconds to wait between refresh-plus-snapshot runs.",
    )
    parser.add_argument(
        "--hourly",
        action="store_true",
        help="Shortcut for running the refresh loop every 3600 seconds.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=get_historical_refresh_max_retries(),
        help="Retry attempts after a failed incremental refresh.",
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=get_historical_refresh_retry_delay_seconds(),
        help="Seconds to wait between failed attempts.",
    )
    parser.add_argument(
        "--server",
        dest="server_slug",
        help="Optional historical server slug.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional page cap for local validation.",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=None,
        help="Optional override for CRCON page size.",
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        default=None,
        help="Optional safety limit for the number of refresh cycles to execute.",
    )
    args = parser.parse_args()

    if args.hourly:
        args.interval = HOURLY_INTERVAL_SECONDS

    if args.interval <= 0:
        raise ValueError("--interval must be a positive integer.")
    if args.retries < 0:
        raise ValueError("--retries must be zero or positive.")
    if args.retry_delay < 0:
        raise ValueError("--retry-delay must be zero or positive.")
    if args.max_runs is not None and args.max_runs <= 0:
        raise ValueError("--max-runs must be positive when provided.")

    run_periodic_historical_refresh(
        interval_seconds=args.interval,
        max_retries=args.retries,
        retry_delay_seconds=args.retry_delay,
        server_slug=args.server_slug,
        max_pages=args.max_pages,
        page_size=args.page_size,
        max_runs=args.max_runs,
    )


if __name__ == "__main__":
    main()
