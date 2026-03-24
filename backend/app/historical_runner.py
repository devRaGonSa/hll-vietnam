"""Local development loop for periodic historical CRCON refreshes."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from typing import Any

from .config import (
    get_historical_full_snapshot_every_runs,
    get_historical_refresh_interval_seconds,
    get_historical_refresh_max_retries,
    get_historical_refresh_retry_delay_seconds,
)
from .historical_ingestion import run_incremental_refresh
from .historical_snapshots import (
    generate_and_persist_historical_snapshots,
    generate_and_persist_priority_historical_snapshots,
)

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
            return {
                "status": "ok",
                "attempts_used": attempt,
                "max_retries": max_retries,
                "refresh_result": refresh_result,
                "snapshot_result": snapshot_result,
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
