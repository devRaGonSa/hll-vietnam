"""Explicit RCON/AdminLog historical backfill command."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

from .config import (
    get_rcon_backfill_chunk_hours,
    get_rcon_backfill_max_days_back,
    get_rcon_backfill_sleep_seconds,
    get_rcon_request_timeout_seconds,
    use_postgres_rcon_storage,
)
from .historical_runner import generate_historical_snapshots
from .historical_storage import ALL_SERVERS_SLUG
from .rcon_admin_log_materialization import (
    MATCH_RESULT_SOURCE,
    initialize_rcon_materialized_storage,
    materialize_rcon_admin_log,
)
from .rcon_admin_log_storage import persist_rcon_admin_log_entries
from .rcon_client import HllRconConnection, RconServerTarget, build_rcon_target_key, load_rcon_targets
from .rcon_historical_leaderboards import list_rcon_materialized_leaderboard
from .sqlite_utils import connect_sqlite_readonly
from .writer_lock import backend_writer_lock, build_writer_lock_holder

DEFAULT_ALLOWED_SERVER_KEYS = frozenset({"comunidad-hispana-01", "comunidad-hispana-02"})
EXCLUDED_BY_DEFAULT_SERVER_KEYS = frozenset({"comunidad-hispana-03"})


@dataclass(frozen=True, slots=True)
class BackfillWindow:
    start: datetime
    end: datetime

    @property
    def lookback_seconds(self) -> int:
        now = datetime.now(timezone.utc)
        return max(1, int((now - self.start).total_seconds()))


def run_rcon_historical_backfill(
    *,
    servers: str | None = None,
    from_value: str | None = None,
    to_value: str | None = None,
    ensure_recent_matches: int | None = None,
    ensure_current_month: bool = False,
    ensure_leaderboard_windows: bool = False,
    chunk_hours: int | None = None,
    sleep_seconds: float | None = None,
    max_days_back: int | None = None,
    dry_run: bool = False,
    regenerate_snapshots: bool = False,
    db_path: Path | None = None,
) -> dict[str, object]:
    """Backfill AdminLog events and materialized RCON matches on explicit operator command."""
    anchor = datetime.now(timezone.utc)
    resolved_chunk_hours = chunk_hours or get_rcon_backfill_chunk_hours()
    resolved_sleep_seconds = (
        get_rcon_backfill_sleep_seconds() if sleep_seconds is None else sleep_seconds
    )
    resolved_max_days_back = max_days_back or get_rcon_backfill_max_days_back()
    selected_targets = select_backfill_targets(servers)
    recent_before = count_recent_materialized_closed_matches(db_path=db_path)
    monthly_before = _window_diagnostic("monthly", db_path=db_path, now=anchor)
    weekly_before = _window_diagnostic("weekly", db_path=db_path, now=anchor)
    requested_range = _resolve_requested_range(
        anchor=anchor,
        from_value=from_value,
        to_value=to_value,
        ensure_recent_matches=ensure_recent_matches,
        ensure_current_month=ensure_current_month,
        ensure_leaderboard_windows=ensure_leaderboard_windows,
        max_days_back=resolved_max_days_back,
    )
    windows = _build_backfill_windows(
        start=requested_range["start"],
        end=requested_range["end"],
        chunk_hours=resolved_chunk_hours,
    )

    result: dict[str, object] = {
        "status": "dry-run" if dry_run else "ok",
        "dry_run": dry_run,
        "servers_processed": [build_rcon_target_key(target) for target in selected_targets],
        "requested_range": {
            "from": _to_iso(requested_range["start"]),
            "to": _to_iso(requested_range["end"]),
            "reason": requested_range["reason"],
            "admin_log_api": "lookback-only",
        },
        "actual_windows_scanned": [],
        "events_seen": 0,
        "events_inserted": 0,
        "duplicate_events": 0,
        "matches_materialized": 0,
        "matches_updated": 0,
        "player_stats_materialized": 0,
        "player_stats_updated": 0,
        "recent_materialized_closed_match_count_before": recent_before,
        "recent_materialized_closed_match_count_after": recent_before,
        "monthly_selected_window_before": monthly_before,
        "monthly_selected_window": monthly_before,
        "weekly_selected_window_before": weekly_before,
        "weekly_selected_window": weekly_before,
        "snapshot_regeneration_result": None,
        "errors": [],
    }

    if dry_run:
        result["actual_windows_scanned"] = [
            _serialize_window(window) for window in _limit_windows_for_recent_need(
                windows,
                ensure_recent_matches=ensure_recent_matches,
                db_path=db_path,
            )
        ]
        return result

    try:
        with backend_writer_lock(
            holder=build_writer_lock_holder("app.rcon_historical_backfill")
        ):
            windows_to_scan = _limit_windows_for_recent_need(
                windows,
                ensure_recent_matches=ensure_recent_matches,
                db_path=db_path,
            )
            for window in windows_to_scan:
                for target in selected_targets:
                    window_result = _scan_target_window(target, window)
                    result["actual_windows_scanned"].append(window_result["window"])
                    result["events_seen"] = int(result["events_seen"]) + int(
                        window_result["events_seen"]
                    )
                    result["events_inserted"] = int(result["events_inserted"]) + int(
                        window_result["events_inserted"]
                    )
                    result["duplicate_events"] = int(result["duplicate_events"]) + int(
                        window_result["duplicate_events"]
                    )
                    if window_result.get("error"):
                        result["errors"].append(window_result["error"])
                    if resolved_sleep_seconds > 0:
                        time.sleep(resolved_sleep_seconds)

                materialized = materialize_rcon_admin_log(db_path=db_path)
                result["matches_materialized"] = int(result["matches_materialized"]) + int(
                    materialized.get("matches_materialized") or 0
                )
                result["matches_updated"] = int(result["matches_updated"]) + int(
                    materialized.get("matches_updated") or 0
                )
                result["player_stats_materialized"] = int(
                    result["player_stats_materialized"]
                ) + int(materialized.get("player_stats_materialized") or 0)
                result["player_stats_updated"] = int(result["player_stats_updated"]) + int(
                    materialized.get("player_stats_updated") or 0
                )

                if ensure_recent_matches and count_recent_materialized_closed_matches(
                    db_path=db_path
                ) >= ensure_recent_matches:
                    break

            if regenerate_snapshots:
                result["snapshot_regeneration_result"] = generate_historical_snapshots(
                    server_slug=None,
                    run_number=1,
                )
    except Exception as exc:  # noqa: BLE001 - CLI reports structured operator diagnostics
        result["status"] = "error"
        result["errors"].append({"error_type": type(exc).__name__, "message": str(exc)})

    recent_after = count_recent_materialized_closed_matches(db_path=db_path)
    result["recent_materialized_closed_match_count_after"] = recent_after
    result["monthly_selected_window"] = _window_diagnostic("monthly", db_path=db_path, now=anchor)
    result["weekly_selected_window"] = _window_diagnostic("weekly", db_path=db_path, now=anchor)
    if result["errors"] and result["status"] == "ok":
        result["status"] = "partial"
    return result


def select_backfill_targets(servers: str | None) -> list[RconServerTarget]:
    """Load configured RCON targets and apply safe server selection rules."""
    configured_targets = list(load_rcon_targets())
    if not configured_targets:
        raise RuntimeError("No RCON targets configured in HLL_BACKEND_RCON_TARGETS.")
    by_key = {build_rcon_target_key(target): target for target in configured_targets}
    requested_keys = _parse_server_keys(servers)
    if requested_keys:
        unknown = sorted(key for key in requested_keys if key not in by_key)
        if unknown:
            raise ValueError(f"Unknown RCON server key(s): {', '.join(unknown)}")
        return [by_key[key] for key in requested_keys]
    selected = [
        target
        for key, target in by_key.items()
        if key in DEFAULT_ALLOWED_SERVER_KEYS and key not in EXCLUDED_BY_DEFAULT_SERVER_KEYS
    ]
    if not selected:
        raise RuntimeError(
            "No default backfill targets selected. Pass --servers with configured keys explicitly."
        )
    return selected


def count_recent_materialized_closed_matches(
    *,
    server_key: str | None = None,
    db_path: Path | None = None,
) -> int:
    """Count materialized closed AdminLog matches available for recent-match UI."""
    resolved_path = initialize_rcon_materialized_storage(db_path=db_path)
    scope_sql = ""
    params: list[object] = [MATCH_RESULT_SOURCE]
    if server_key and server_key != ALL_SERVERS_SLUG:
        scope_sql = "AND (target_key = ? OR external_server_id = ?)"
        params.extend([server_key, server_key])
    if use_postgres_rcon_storage(explicit_sqlite_path=db_path):
        from .postgres_rcon_storage import connect_postgres_compat

        connection_scope = connect_postgres_compat()
    else:
        connection_scope = closing(connect_sqlite_readonly(resolved_path))
    with connection_scope as connection:
        row = connection.execute(
            f"""
            SELECT COUNT(*) AS count
            FROM rcon_materialized_matches
            WHERE source_basis = ?
              AND ended_at IS NOT NULL
              {scope_sql}
            """,
            params,
        ).fetchone()
    return int(row["count"] or 0) if row else 0


def _scan_target_window(target: RconServerTarget, window: BackfillWindow) -> dict[str, object]:
    target_metadata = _serialize_target(target)
    serialized_window = _serialize_window(window)
    try:
        with HllRconConnection(timeout_seconds=get_rcon_request_timeout_seconds()) as connection:
            connection.connect(host=target.host, port=target.port, password=target.password)
            payload = connection.execute_json(
                "GetAdminLog",
                {
                    "LogBackTrackTime": window.lookback_seconds,
                    "Filters": [],
                },
            )
        entries = payload.get("entries")
        if not isinstance(entries, list):
            entries = []
        normalized_entries = [entry for entry in entries if isinstance(entry, dict)]
        delta = persist_rcon_admin_log_entries(
            target=target_metadata,
            entries=normalized_entries,
        )
        return {"window": serialized_window, "error": None, **delta}
    except Exception as exc:  # noqa: BLE001 - per-window errors must not hide neighboring windows
        return {
            "window": serialized_window,
            "events_seen": 0,
            "events_inserted": 0,
            "duplicate_events": 0,
            "error": {
                **target_metadata,
                **serialized_window,
                "error_type": type(exc).__name__,
                "message": str(exc),
            },
        }


def _resolve_requested_range(
    *,
    anchor: datetime,
    from_value: str | None,
    to_value: str | None,
    ensure_recent_matches: int | None,
    ensure_current_month: bool,
    ensure_leaderboard_windows: bool,
    max_days_back: int,
) -> dict[str, object]:
    end = _parse_datetime_argument(to_value, default=anchor)
    starts = []
    reasons = []
    if from_value:
        starts.append(_parse_datetime_argument(from_value, default=anchor))
        reasons.append("explicit-range")
    if ensure_current_month:
        starts.append(_month_start(anchor))
        reasons.append("ensure-current-month")
    if ensure_leaderboard_windows:
        starts.append(_previous_month_start(_month_start(anchor)))
        starts.append(_week_start(anchor) - timedelta(days=7))
        reasons.append("ensure-leaderboard-windows")
    if ensure_recent_matches:
        starts.append(anchor - timedelta(days=max_days_back))
        reasons.append(f"ensure-recent-matches-{ensure_recent_matches}")
    if not starts:
        starts.append(anchor - timedelta(days=max_days_back))
        reasons.append("default-max-days-back")
    start = max(min(starts), anchor - timedelta(days=max_days_back))
    return {"start": start, "end": end, "reason": ",".join(reasons)}


def _build_backfill_windows(
    *,
    start: datetime,
    end: datetime,
    chunk_hours: int,
) -> list[BackfillWindow]:
    windows: list[BackfillWindow] = []
    cursor = _as_utc(end)
    lower = _as_utc(start)
    chunk = timedelta(hours=chunk_hours)
    while cursor > lower:
        window_start = max(lower, cursor - chunk)
        windows.append(BackfillWindow(start=window_start, end=cursor))
        cursor = window_start
    return windows


def _limit_windows_for_recent_need(
    windows: list[BackfillWindow],
    *,
    ensure_recent_matches: int | None,
    db_path: Path | None,
) -> list[BackfillWindow]:
    if not ensure_recent_matches:
        return windows
    if count_recent_materialized_closed_matches(db_path=db_path) >= ensure_recent_matches:
        return []
    return windows


def _window_diagnostic(
    timeframe: str,
    *,
    db_path: Path | None,
    now: datetime,
) -> dict[str, object]:
    payload = list_rcon_materialized_leaderboard(
        server_key=ALL_SERVERS_SLUG,
        timeframe=timeframe,
        metric="kills",
        limit=1,
        db_path=db_path,
        now=now,
    )
    return {
        "window_kind": payload.get("window_kind"),
        "window_label": payload.get("window_label"),
        "window_start": payload.get("window_start"),
        "window_end": payload.get("window_end"),
        "selection_reason": payload.get("selection_reason"),
        "current_week_closed_matches": payload.get("current_week_closed_matches"),
        "previous_week_closed_matches": payload.get("previous_week_closed_matches"),
        "selected_month_start": payload.get("selected_month_start"),
        "selected_month_end": payload.get("selected_month_end"),
        "current_month_closed_matches": payload.get("current_month_closed_matches"),
        "previous_month_closed_matches": payload.get("previous_month_closed_matches"),
        "sufficient_sample": payload.get("sufficient_sample"),
    }


def _parse_server_keys(value: str | None) -> list[str]:
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def _parse_datetime_argument(value: str | None, *, default: datetime) -> datetime:
    if value is None or str(value).strip().lower() == "now":
        return default
    raw = str(value).strip()
    if len(raw) == 10:
        raw = f"{raw}T00:00:00+00:00"
    parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    return _as_utc(parsed)


def _month_start(value: datetime) -> datetime:
    point = _as_utc(value)
    return point.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _previous_month_start(current_month_start: datetime) -> datetime:
    return _month_start(current_month_start - timedelta(days=1))


def _week_start(value: datetime) -> datetime:
    point = _as_utc(value)
    return (point - timedelta(days=point.weekday())).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _serialize_target(target: RconServerTarget) -> dict[str, object]:
    return {
        "target_key": build_rcon_target_key(target),
        "external_server_id": target.external_server_id,
        "name": target.name,
        "host": target.host,
        "port": target.port,
        "source_name": target.source_name,
    }


def _serialize_window(window: BackfillWindow) -> dict[str, object]:
    return {
        "start": _to_iso(window.start),
        "end": _to_iso(window.end),
        "requested_log_backtrack_seconds": window.lookback_seconds,
    }


def _to_iso(value: datetime) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")


def _main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill RCON AdminLog historical materialized matches.")
    parser.add_argument("--from", dest="from_value", default=None)
    parser.add_argument("--to", dest="to_value", default=None)
    parser.add_argument("--servers", default=None)
    parser.add_argument("--ensure-recent-matches", type=int, default=None)
    parser.add_argument("--ensure-current-month", action="store_true")
    parser.add_argument("--ensure-leaderboard-windows", action="store_true")
    parser.add_argument("--chunk-hours", type=int, default=get_rcon_backfill_chunk_hours())
    parser.add_argument("--sleep-seconds", type=float, default=get_rcon_backfill_sleep_seconds())
    parser.add_argument("--max-days-back", type=int, default=get_rcon_backfill_max_days_back())
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--regenerate-snapshots", action="store_true")
    parser.add_argument("--db-path", type=Path, default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.ensure_recent_matches is not None and args.ensure_recent_matches <= 0:
        raise ValueError("--ensure-recent-matches must be positive.")
    if args.chunk_hours <= 0:
        raise ValueError("--chunk-hours must be positive.")
    if args.sleep_seconds < 0:
        raise ValueError("--sleep-seconds must be zero or positive.")
    if args.max_days_back <= 0:
        raise ValueError("--max-days-back must be positive.")

    payload = run_rcon_historical_backfill(
        servers=args.servers,
        from_value=args.from_value,
        to_value=args.to_value,
        ensure_recent_matches=args.ensure_recent_matches,
        ensure_current_month=args.ensure_current_month,
        ensure_leaderboard_windows=args.ensure_leaderboard_windows,
        chunk_hours=args.chunk_hours,
        sleep_seconds=args.sleep_seconds,
        max_days_back=args.max_days_back,
        dry_run=args.dry_run,
        regenerate_snapshots=args.regenerate_snapshots,
        db_path=args.db_path,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    return 0 if payload.get("status") != "error" else 1


if __name__ == "__main__":
    raise SystemExit(_main())
