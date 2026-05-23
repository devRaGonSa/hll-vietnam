"""Observable operator backfill for RCON AdminLog.

This command is intentionally simple and explicit. It is meant to be run after stopping
`historical-runner` and `rcon-historical-worker`, so it does not compete with the shared
writer lock loop. It prints one JSON line per step, which makes progress visible in
PowerShell and Docker logs.
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from typing import Iterable

from .historical_runner import generate_historical_snapshots
from .rcon_admin_log_ingestion import ingest_rcon_admin_logs
from .rcon_admin_log_materialization import materialize_rcon_admin_log
from .rcon_historical_backfill import count_recent_materialized_closed_matches, select_backfill_targets
from .rcon_client import build_rcon_target_key


def run_operational_backfill(
    *,
    ensure_recent_matches: int,
    servers: str,
    max_days_back: int,
    chunk_hours: int,
    sleep_seconds: float,
    regenerate_snapshots: bool,
) -> dict[str, object]:
    started_at = datetime.now(timezone.utc)
    targets = select_backfill_targets(servers)
    target_keys = [build_rcon_target_key(target) for target in targets]
    before = count_recent_materialized_closed_matches()
    result: dict[str, object] = {
        "status": "ok",
        "started_at": _iso(started_at),
        "admin_log_api": "lookback-only",
        "exact_historical_range_supported": False,
        "servers_processed": target_keys,
        "ensure_recent_matches": ensure_recent_matches,
        "max_days_back": max_days_back,
        "chunk_hours": chunk_hours,
        "recent_materialized_closed_match_count_before": before,
        "recent_materialized_closed_match_count_after": before,
        "events_seen": 0,
        "events_inserted": 0,
        "duplicate_events": 0,
        "matches_materialized": 0,
        "matches_updated": 0,
        "windows_scanned": [],
        "errors": [],
        "snapshot_regeneration_result": None,
    }
    _log("backfill-started", result=result)

    max_minutes = max_days_back * 24 * 60
    step_minutes = chunk_hours * 60
    minutes = step_minutes

    while minutes <= max_minutes:
        current_count = count_recent_materialized_closed_matches()
        result["recent_materialized_closed_match_count_after"] = current_count
        if current_count >= ensure_recent_matches:
            result["termination_reason"] = "recent-match-target-reached"
            break

        for target_key in target_keys:
            _log("target-lookback-started", target_key=target_key, lookback_minutes=minutes)
            try:
                ingestion = ingest_rcon_admin_logs(minutes=minutes, target_key=target_key)
                totals = ingestion.get("totals") if isinstance(ingestion.get("totals"), dict) else {}
                materialized = materialize_rcon_admin_log()
                window_summary = {
                    "target_key": target_key,
                    "lookback_minutes": minutes,
                    "events_seen": int(totals.get("events_seen") or 0),
                    "events_inserted": int(totals.get("events_inserted") or 0),
                    "duplicate_events": int(totals.get("duplicate_events") or 0),
                    "matches_materialized": int(materialized.get("matches_materialized") or 0),
                    "matches_updated": int(materialized.get("matches_updated") or 0),
                }
                result["windows_scanned"].append(window_summary)
                _add(result, window_summary)
                result["recent_materialized_closed_match_count_after"] = count_recent_materialized_closed_matches()
                _log(
                    "target-lookback-finished",
                    **window_summary,
                    recent_materialized_closed_match_count_after=result["recent_materialized_closed_match_count_after"],
                )
            except Exception as exc:  # noqa: BLE001 - operator command must continue reporting
                error = {
                    "target_key": target_key,
                    "lookback_minutes": minutes,
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
                result["errors"].append(error)
                _log("target-lookback-failed", error=error)

            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

        minutes += step_minutes

    if result["recent_materialized_closed_match_count_after"] < ensure_recent_matches:
        result["status"] = "partial"
        result.setdefault("termination_reason", "exhausted_available_admin_log_or_max_days_back")

    if regenerate_snapshots:
        _log("snapshot-regeneration-started")
        try:
            result["snapshot_regeneration_result"] = generate_historical_snapshots(server_slug=None, run_number=1)
            _log("snapshot-regeneration-finished", snapshot_regeneration_result=result["snapshot_regeneration_result"])
        except Exception as exc:  # noqa: BLE001
            result["status"] = "partial"
            error = {"phase": "snapshot-regeneration", "error_type": type(exc).__name__, "message": str(exc)}
            result["errors"].append(error)
            _log("snapshot-regeneration-failed", error=error)

    result["finished_at"] = _iso(datetime.now(timezone.utc))
    _log("backfill-finished", result=result)
    return result


def _add(result: dict[str, object], window_summary: dict[str, object]) -> None:
    for key in ("events_seen", "events_inserted", "duplicate_events", "matches_materialized", "matches_updated"):
        result[key] = int(result.get(key) or 0) + int(window_summary.get(key) or 0)


def _log(event: str, **payload: object) -> None:
    print(json.dumps({"event": event, **payload}, ensure_ascii=False, default=str), flush=True)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Observable RCON AdminLog backfill operator command.")
    parser.add_argument("--ensure-recent-matches", type=int, default=100)
    parser.add_argument("--servers", default="comunidad-hispana-01,comunidad-hispana-02")
    parser.add_argument("--chunk-hours", type=int, default=3)
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    parser.add_argument("--max-days-back", type=int, default=45)
    parser.add_argument("--regenerate-snapshots", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.ensure_recent_matches <= 0:
        raise ValueError("--ensure-recent-matches must be positive.")
    if args.chunk_hours <= 0:
        raise ValueError("--chunk-hours must be positive.")
    if args.sleep_seconds < 0:
        raise ValueError("--sleep-seconds must be zero or positive.")
    if args.max_days_back <= 0:
        raise ValueError("--max-days-back must be positive.")

    payload = run_operational_backfill(
        ensure_recent_matches=args.ensure_recent_matches,
        servers=args.servers,
        chunk_hours=args.chunk_hours,
        sleep_seconds=args.sleep_seconds,
        max_days_back=args.max_days_back,
        regenerate_snapshots=args.regenerate_snapshots,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str), flush=True)
    return 0 if payload.get("status") != "error" else 1


if __name__ == "__main__":
    raise SystemExit(_main())
