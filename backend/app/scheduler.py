"""Local development loop for periodic snapshot refreshes."""

from __future__ import annotations

import argparse
import json
import time

from .a2s_client import DEFAULT_A2S_TIMEOUT
from .collector import collect_server_snapshots
from .config import get_refresh_interval_seconds


def run_local_refresh_loop(
    *,
    interval_seconds: int,
    source_mode: str,
    timeout: float,
    allow_controlled_fallback: bool,
    max_runs: int | None = None,
) -> None:
    """Run the collector periodically until interrupted or the run limit is reached."""
    completed_runs = 0
    print(
        "Starting local snapshot refresh loop "
        f"(interval={interval_seconds}s, source={source_mode}, persist=true)."
    )
    print("Press Ctrl+C to stop.")

    try:
        while max_runs is None or completed_runs < max_runs:
            completed_runs += 1
            payload = collect_server_snapshots(
                source_mode=source_mode,
                timeout=timeout,
                allow_controlled_fallback=allow_controlled_fallback,
                persist=True,
            )
            print(json.dumps({"run": completed_runs, **payload}, indent=2))

            if max_runs is not None and completed_runs >= max_runs:
                break

            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\nLocal snapshot refresh loop stopped by user.")


def main() -> None:
    """Allow local scheduled refresh execution without adding external infrastructure."""
    parser = argparse.ArgumentParser(
        description="Run periodic local snapshot refreshes for development and landing demos.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=get_refresh_interval_seconds(),
        help="Seconds to wait between persisted refresh runs. Defaults to env value or 60.",
    )
    parser.add_argument(
        "--source",
        choices=("controlled", "a2s", "auto"),
        default="auto",
        help="Choose controlled data, configured A2S targets, or auto with fallback.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_A2S_TIMEOUT,
        help="Socket timeout in seconds for A2S probes.",
    )
    parser.add_argument(
        "--no-fallback",
        action="store_true",
        help="Disable fallback to controlled data when A2S fails.",
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
    if args.max_runs is not None and args.max_runs <= 0:
        raise ValueError("--max-runs must be positive when provided.")

    run_local_refresh_loop(
        interval_seconds=args.interval,
        source_mode=args.source,
        timeout=args.timeout,
        allow_controlled_fallback=not args.no_fallback,
        max_runs=args.max_runs,
    )


if __name__ == "__main__":
    main()
