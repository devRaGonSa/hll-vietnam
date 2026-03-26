"""Dedicated prospective RCON historical capture worker."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from typing import Iterable

from .config import (
    get_rcon_historical_capture_interval_seconds,
    get_rcon_historical_capture_max_retries,
    get_rcon_historical_capture_retry_delay_seconds,
    get_rcon_request_timeout_seconds,
)
from .rcon_client import (
    RconQueryError,
    build_rcon_target_key,
    load_rcon_targets,
    query_live_server_sample,
)
from .rcon_historical_storage import (
    finalize_rcon_historical_capture_run,
    initialize_rcon_historical_storage,
    list_rcon_historical_target_statuses,
    mark_rcon_historical_capture_failure,
    persist_rcon_historical_sample,
    start_rcon_historical_capture_run,
)
from .snapshots import utc_now
from .writer_lock import backend_writer_lock, build_writer_lock_holder


@dataclass(slots=True)
class RconHistoricalCaptureStats:
    targets_seen: int = 0
    samples_inserted: int = 0
    duplicate_samples: int = 0
    failed_targets: int = 0


def run_rcon_historical_capture(
    *,
    target_key: str | None = None,
) -> dict[str, object]:
    """Capture one prospective RCON sample for one or all configured targets."""
    with backend_writer_lock(
        holder=build_writer_lock_holder(
            f"app.rcon_historical_worker capture:{target_key or 'all-targets'}"
        )
    ):
        return run_rcon_historical_capture_unlocked(target_key=target_key)


def run_rcon_historical_capture_unlocked(
    *,
    target_key: str | None = None,
) -> dict[str, object]:
    """Capture one prospective RCON sample assuming the shared writer lock is already held."""
    initialize_rcon_historical_storage()
    selected_targets = _select_targets(target_key)
    captured_at = utc_now().isoformat().replace("+00:00", "Z")
    target_scope = target_key or "all-configured-rcon-targets"
    run_id = start_rcon_historical_capture_run(mode="capture", target_scope=target_scope)
    stats = RconHistoricalCaptureStats()
    items: list[dict[str, object]] = []
    errors: list[dict[str, object]] = []
    timeout_seconds = get_rcon_request_timeout_seconds()

    try:
        for target in selected_targets:
            target_metadata = _serialize_target(target)
            stats.targets_seen += 1
            try:
                sample = query_live_server_sample(
                    target,
                    timeout_seconds=timeout_seconds,
                )
                delta = persist_rcon_historical_sample(
                    run_id=run_id,
                    captured_at=captured_at,
                    target=target_metadata,
                    normalized_payload=sample["normalized"],
                    raw_payload=sample["raw_session"],
                )
                stats.samples_inserted += int(delta["samples_inserted"])
                stats.duplicate_samples += int(delta["duplicate_samples"])
                items.append(
                    {
                        "target_key": target_metadata["target_key"],
                        "external_server_id": target.external_server_id,
                        "name": target.name,
                        "host": target.host,
                        "port": target.port,
                        "timeout_seconds": timeout_seconds,
                        "captured_at": captured_at,
                        "sample_inserted": bool(delta["samples_inserted"]),
                        "normalized": sample["normalized"],
                    }
                )
            except Exception as exc:  # noqa: BLE001 - controlled worker failures
                stats.failed_targets += 1
                mark_rcon_historical_capture_failure(
                    run_id=run_id,
                    target=target_metadata,
                    error_message=_format_error_message(exc),
                )
                errors.append(_serialize_capture_error(target, exc, timeout_seconds=timeout_seconds))

        status = "success" if not errors else ("partial" if items else "failed")
        finalize_rcon_historical_capture_run(
            run_id,
            status=status,
            targets_seen=stats.targets_seen,
            samples_inserted=stats.samples_inserted,
            duplicate_samples=stats.duplicate_samples,
            failed_targets=stats.failed_targets,
            notes=None if not errors else json.dumps(errors, separators=(",", ":")),
        )
    except Exception as exc:
        finalize_rcon_historical_capture_run(
            run_id,
            status="failed",
            targets_seen=stats.targets_seen,
            samples_inserted=stats.samples_inserted,
            duplicate_samples=stats.duplicate_samples,
            failed_targets=max(1, stats.failed_targets),
            notes=str(exc),
        )
        raise

    return {
        "status": "ok" if items else "error",
        "run_status": status,
        "captured_at": captured_at,
        "target_scope": target_scope,
        "targets": items,
        "errors": errors,
        "storage_status": list_rcon_historical_target_statuses(),
        "totals": {
            "targets_seen": stats.targets_seen,
            "samples_inserted": stats.samples_inserted,
            "duplicate_samples": stats.duplicate_samples,
            "failed_targets": stats.failed_targets,
        },
    }


def run_periodic_rcon_historical_capture(
    *,
    interval_seconds: int,
    max_retries: int,
    retry_delay_seconds: int,
    target_key: str | None = None,
    max_runs: int | None = None,
) -> None:
    """Run prospective RCON capture in a local loop."""
    completed_runs = 0
    print(
        json.dumps(
            {
                "event": "rcon-historical-capture-loop-started",
                "interval_seconds": interval_seconds,
                "max_retries": max_retries,
                "retry_delay_seconds": retry_delay_seconds,
                "target_scope": target_key or "all-configured-rcon-targets",
            },
            indent=2,
        )
    )
    print("Press Ctrl+C to stop.")

    try:
        while max_runs is None or completed_runs < max_runs:
            completed_runs += 1
            payload = _run_capture_with_retries(
                max_retries=max_retries,
                retry_delay_seconds=retry_delay_seconds,
                target_key=target_key,
            )
            print(json.dumps({"run": completed_runs, **payload}, indent=2))
            if max_runs is not None and completed_runs >= max_runs:
                break
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\nRCON historical capture loop stopped by user.")


def _run_capture_with_retries(
    *,
    max_retries: int,
    retry_delay_seconds: int,
    target_key: str | None,
) -> dict[str, object]:
    attempt = 0
    while True:
        attempt += 1
        try:
            return {
                "status": "ok",
                "attempts_used": attempt,
                "capture_result": run_rcon_historical_capture(target_key=target_key),
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


def _select_targets(target_key: str | None) -> list[object]:
    configured_targets = list(load_rcon_targets())
    if not configured_targets:
        raise RuntimeError("No RCON targets configured in HLL_BACKEND_RCON_TARGETS.")
    if target_key is None:
        return configured_targets

    normalized = target_key.strip()
    selected = [
        target
        for target in configured_targets
        if build_rcon_target_key(target) == normalized
    ]
    if not selected:
        raise ValueError(f"Unknown RCON target key: {target_key}")
    return selected


def _serialize_target(target: object) -> dict[str, object]:
    return {
        "target_key": build_rcon_target_key(target),
        "external_server_id": target.external_server_id,
        "name": target.name,
        "host": target.host,
        "port": target.port,
        "region": target.region,
        "game_port": target.game_port,
        "query_port": target.query_port,
        "source_name": target.source_name,
    }


def _serialize_capture_error(
    target: object,
    error: Exception,
    *,
    timeout_seconds: float,
) -> dict[str, object]:
    error_type = _classify_capture_error_type(error)
    error_stage = _classify_capture_error_stage(error)
    return {
        "target_key": build_rcon_target_key(target),
        "external_server_id": target.external_server_id,
        "name": target.name,
        "host": target.host,
        "port": target.port,
        "timeout_seconds": timeout_seconds,
        "error_type": error_type,
        "error_stage": error_stage,
        "message": str(error),
    }


def _classify_capture_error_type(error: Exception) -> str:
    if isinstance(error, RconQueryError):
        return error.error_type
    message = str(error).lower()
    if "timed out" in message or "timeout" in message:
        return "timeout"
    if "401" in message or "403" in message or "login" in message or "auth" in message:
        return "auth/login"
    if "refused" in message:
        return "connection-refused"
    if "payload" in message or "json" in message or "malformed" in message:
        return "payload-invalid"
    return "other-error"


def _classify_capture_error_stage(error: Exception) -> str | None:
    if isinstance(error, RconQueryError):
        return error.error_stage
    return None


def _format_error_message(error: Exception) -> str:
    error_type = _classify_capture_error_type(error)
    error_stage = _classify_capture_error_stage(error)
    if error_stage:
        return f"[{error_type}:{error_stage}] {error}"
    return f"[{error_type}] {error}"


def build_arg_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for manual or periodic prospective RCON capture."""
    parser = argparse.ArgumentParser(
        description="Prospective RCON historical capture for HLL Vietnam.",
    )
    parser.add_argument(
        "mode",
        choices=("capture", "loop"),
        help="capture runs once; loop keeps collecting periodically",
    )
    parser.add_argument(
        "--target",
        dest="target_key",
        help="optional target key; defaults to all configured RCON targets",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=get_rcon_historical_capture_interval_seconds(),
        help="seconds to wait between loop runs",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=get_rcon_historical_capture_max_retries(),
        help="retry attempts after a failed capture",
    )
    parser.add_argument(
        "--retry-delay",
        type=int,
        default=get_rcon_historical_capture_retry_delay_seconds(),
        help="seconds to wait between failed attempts",
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        help="optional safety cap for loop mode",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    """Run the prospective RCON historical capture CLI."""
    parser = build_arg_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.mode == "capture":
        result = run_rcon_historical_capture(target_key=args.target_key)
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

    run_periodic_rcon_historical_capture(
        interval_seconds=args.interval,
        max_retries=args.retries,
        retry_delay_seconds=args.retry_delay,
        target_key=args.target_key,
        max_runs=args.max_runs,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
