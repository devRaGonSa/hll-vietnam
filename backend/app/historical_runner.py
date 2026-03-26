"""Local development loop for periodic historical CRCON refreshes."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from typing import Any

from .config import (
    get_historical_full_snapshot_every_runs,
    get_historical_elo_mmr_min_new_samples,
    get_historical_elo_mmr_rebuild_interval_minutes,
    get_historical_refresh_interval_seconds,
    get_historical_refresh_max_retries,
    get_historical_refresh_retry_delay_seconds,
    get_historical_data_source_kind,
)
from .elo_mmr_engine import rebuild_elo_mmr_models
from .elo_mmr_storage import get_latest_elo_mmr_generated_at
from .historical_ingestion import run_incremental_refresh
from .historical_snapshots import (
    generate_and_persist_historical_snapshots,
    generate_and_persist_priority_historical_snapshots,
)
from .rcon_historical_storage import count_rcon_historical_samples_since
from .rcon_historical_worker import run_rcon_historical_capture
from .writer_lock import backend_writer_lock, build_writer_lock_holder

HOURLY_INTERVAL_SECONDS = 3600
DEFAULT_HISTORICAL_SERVER_SCOPE = (
    "comunidad-hispana-01",
    "comunidad-hispana-02",
    "comunidad-hispana-03",
)


def run_periodic_historical_refresh(
    *,
    interval_seconds: int,
    max_retries: int,
    retry_delay_seconds: int,
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

    try:
        while max_runs is None or completed_runs < max_runs:
            completed_runs += 1
            payload = _run_refresh_with_retries(
                max_retries=max_retries,
                retry_delay_seconds=retry_delay_seconds,
                server_slug=server_slug,
                max_pages=max_pages,
                page_size=page_size,
                run_number=completed_runs,
            )
            print(json.dumps({"run": completed_runs, **payload}, indent=2))

            if max_runs is not None and completed_runs >= max_runs:
                break

            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\nHistorical refresh loop stopped by user.")


def _run_refresh_with_retries(
    *,
    max_retries: int,
    retry_delay_seconds: int,
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
                    snapshot_result = generate_historical_snapshots(
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
                        snapshot_result = generate_historical_snapshots(
                            server_slug=server_slug,
                            run_number=run_number,
                        )
                        snapshot_result = {
                            **snapshot_result,
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
                        snapshot_result = {
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
            return {
                "status": "ok",
                "attempts_used": attempt,
                "max_retries": max_retries,
                "rcon_capture_result": rcon_capture_result,
                "classic_fallback_used": should_run_classic_fallback,
                "classic_fallback_reason": classic_fallback_reason,
                "refresh_result": refresh_result,
                "snapshot_result": snapshot_result,
                "elo_mmr_result": elo_mmr_result,
            }
        except Exception as exc:
            if attempt > max_retries:
                return {
                    "status": "error",
                    "attempts_used": attempt,
                    "max_retries": max_retries,
                    "error": str(exc),
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
        type=int,
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
