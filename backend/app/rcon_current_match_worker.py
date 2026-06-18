"""Dedicated lightweight AdminLog freshness worker for current-match pages."""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable, Iterable, Sequence
from datetime import datetime, timezone
from pathlib import Path

from .config import (
    get_current_match_adminlog_enabled,
    get_current_match_adminlog_interval_seconds,
    get_current_match_adminlog_lookback_seconds,
    get_rcon_current_match_writer_lock_timeout_seconds,
)
from .rcon_admin_log_ingestion import fetch_recent_admin_log_entries, serialize_rcon_target
from .rcon_admin_log_storage import persist_rcon_admin_log_entries
from .rcon_client import RconServerTarget, build_rcon_target_key, load_rcon_targets
from .scoreboard_origins import list_trusted_public_scoreboard_origins
from .writer_lock import backend_writer_lock, build_writer_lock_holder


def list_current_match_trusted_targets() -> list[RconServerTarget]:
    """Return only the configured RCON targets trusted for public current-match pages."""
    trusted_keys = {
        origin.slug for origin in list_trusted_public_scoreboard_origins()
    }
    return [
        target
        for target in load_rcon_targets()
        if build_rcon_target_key(target) in trusted_keys
    ]


def run_current_match_adminlog_refresh_once(
    *,
    lookback_seconds: int | None = None,
    targets: Sequence[RconServerTarget] | None = None,
    fetch_entries_fn: Callable[..., list[dict[str, object]]] = fetch_recent_admin_log_entries,
    persist_entries_fn: Callable[..., dict[str, int]] = persist_rcon_admin_log_entries,
    db_path: object = None,
) -> dict[str, object]:
    """Refresh recent AdminLog rows once for trusted current-match targets."""
    with backend_writer_lock(
        holder=build_writer_lock_holder("app.rcon_current_match_worker once"),
        timeout_seconds=get_rcon_current_match_writer_lock_timeout_seconds(),
    ):
        return run_current_match_adminlog_refresh_once_unlocked(
            lookback_seconds=lookback_seconds,
            targets=targets,
            fetch_entries_fn=fetch_entries_fn,
            persist_entries_fn=persist_entries_fn,
            db_path=db_path,
        )


def run_current_match_adminlog_refresh_once_unlocked(
    *,
    lookback_seconds: int | None = None,
    targets: Sequence[RconServerTarget] | None = None,
    fetch_entries_fn: Callable[..., list[dict[str, object]]] = fetch_recent_admin_log_entries,
    persist_entries_fn: Callable[..., dict[str, int]] = persist_rcon_admin_log_entries,
    db_path: object = None,
) -> dict[str, object]:
    """Refresh recent AdminLog rows once assuming the shared writer lock is already held."""
    resolved_lookback_seconds = (
        get_current_match_adminlog_lookback_seconds()
        if lookback_seconds is None
        else int(lookback_seconds)
    )
    if resolved_lookback_seconds <= 0:
        raise ValueError("lookback_seconds must be positive.")

    resolved_db_path = Path(db_path) if isinstance(db_path, str) else db_path
    selected_targets = list(targets) if targets is not None else list_current_match_trusted_targets()
    if not selected_targets:
        raise RuntimeError("No trusted current-match RCON targets are configured.")

    timeout_seconds = None
    refreshed_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    items: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    totals = {
        "targets_seen": 0,
        "entries_seen": 0,
        "events_inserted": 0,
        "duplicate_events": 0,
        "failed_targets": 0,
    }

    for target in selected_targets:
        totals["targets_seen"] += 1
        target_metadata = serialize_rcon_target(target)
        started = time.perf_counter()
        try:
            entries = fetch_entries_fn(
                target,
                lookback_seconds=resolved_lookback_seconds,
                timeout_seconds=timeout_seconds,
            )
            delta = persist_entries_fn(
                target=target_metadata,
                entries=entries,
                db_path=resolved_db_path,
            )
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            totals["entries_seen"] += int(delta.get("events_seen") or 0)
            totals["events_inserted"] += int(delta.get("events_inserted") or 0)
            totals["duplicate_events"] += int(delta.get("duplicate_events") or 0)
            items.append(
                {
                    "target_key": target_metadata["target_key"],
                    "external_server_id": target_metadata["external_server_id"],
                    "name": target_metadata["name"],
                    "entries_seen": int(delta.get("events_seen") or 0),
                    "events_inserted": int(delta.get("events_inserted") or 0),
                    "duplicate_events": int(delta.get("duplicate_events") or 0),
                    "duration_ms": duration_ms,
                }
            )
        except Exception as exc:  # noqa: BLE001 - per-target failure must not kill the loop
            totals["failed_targets"] += 1
            errors.append(
                {
                    "target_key": target_metadata["target_key"],
                    "external_server_id": target_metadata["external_server_id"],
                    "name": target_metadata["name"],
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
            )

    return {
        "status": "ok" if not errors else ("partial" if items else "error"),
        "worker_enabled": get_current_match_adminlog_enabled(),
        "refreshed_at": refreshed_at,
        "lookback_seconds": resolved_lookback_seconds,
        "targets": items,
        "errors": errors,
        "totals": totals,
    }


def run_current_match_adminlog_refresh_loop(
    *,
    interval_seconds: int | None = None,
    lookback_seconds: int | None = None,
    max_runs: int | None = None,
) -> None:
    """Run the lightweight current-match AdminLog refresher in a loop."""
    resolved_interval_seconds = (
        get_current_match_adminlog_interval_seconds()
        if interval_seconds is None
        else int(interval_seconds)
    )
    if resolved_interval_seconds <= 0:
        raise ValueError("interval_seconds must be positive.")
    if max_runs is not None and max_runs <= 0:
        raise ValueError("max_runs must be positive when provided.")

    run_count = 0
    _emit_worker_event(
        "current-match-adminlog-worker-started",
        enabled=get_current_match_adminlog_enabled(),
        interval_seconds=resolved_interval_seconds,
        lookback_seconds=(
            get_current_match_adminlog_lookback_seconds()
            if lookback_seconds is None
            else int(lookback_seconds)
        ),
        targets=[
            {
                "target_key": build_rcon_target_key(target),
                "external_server_id": target.external_server_id,
                "name": target.name,
            }
            for target in list_current_match_trusted_targets()
        ],
    )
    try:
        while max_runs is None or run_count < max_runs:
            run_count += 1
            result = run_current_match_adminlog_refresh_once(
                lookback_seconds=lookback_seconds,
            )
            _emit_worker_event(
                "current-match-adminlog-cycle-finished",
                run=run_count,
                result=result,
            )
            if max_runs is not None and run_count >= max_runs:
                break
            time.sleep(resolved_interval_seconds)
    except KeyboardInterrupt:
        _emit_worker_event("current-match-adminlog-worker-stopped", reason="keyboard-interrupt")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Lightweight current-match AdminLog freshness worker.",
    )
    parser.add_argument(
        "mode",
        choices=("once", "loop"),
        help="run once or keep polling trusted current-match targets",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=get_current_match_adminlog_interval_seconds(),
        help="seconds between loop iterations",
    )
    parser.add_argument(
        "--lookback-seconds",
        type=int,
        default=get_current_match_adminlog_lookback_seconds(),
        help="overlap-safe AdminLog lookback window in seconds",
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        help="optional safety cap for loop mode",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.mode == "once":
        print(
            json.dumps(
                run_current_match_adminlog_refresh_once(
                    lookback_seconds=args.lookback_seconds,
                ),
                indent=2,
            )
        )
        return 0

    run_current_match_adminlog_refresh_loop(
        interval_seconds=args.interval,
        lookback_seconds=args.lookback_seconds,
        max_runs=args.max_runs,
    )
    return 0


def _emit_worker_event(event: str, **fields: object) -> None:
    print(json.dumps({"event": event, **fields}, indent=2, default=str), flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
