"""Local development loop for periodic historical CRCON refreshes."""

from __future__ import annotations

import argparse
import json
import time
from typing import Any

from .config import (
    get_historical_refresh_interval_seconds,
    get_historical_refresh_max_retries,
    get_historical_refresh_retry_delay_seconds,
)
from .historical_ingestion import run_incremental_refresh


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
    """Run periodic historical refreshes until interrupted or the limit is reached."""
    completed_runs = 0
    print(
        "Starting historical refresh loop "
        f"(interval={interval_seconds}s, retries={max_retries}, server={server_slug or 'all'})."
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
) -> dict[str, Any]:
    attempt = 0
    while True:
        attempt += 1
        try:
            result = run_incremental_refresh(
                server_slug=server_slug,
                max_pages=max_pages,
                page_size=page_size,
            )
            return {
                "status": "ok",
                "attempts_used": attempt,
                "max_retries": max_retries,
                "result": result,
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


def main() -> None:
    """Allow local scheduled historical refresh execution without external infra."""
    parser = argparse.ArgumentParser(
        description="Run periodic historical CRCON refreshes for HLL Vietnam.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=get_historical_refresh_interval_seconds(),
        help="Seconds to wait between incremental refresh runs.",
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
