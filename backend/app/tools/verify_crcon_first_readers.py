"""Fail-closed, read-only probe for canonical CRCON-first public readers."""

from __future__ import annotations

import importlib
import json
from contextlib import ExitStack, contextmanager
from http import HTTPStatus
from typing import Iterator
from unittest.mock import patch
from urllib.parse import quote, urlencode

from ..api.routes import resolve_get_payload
from ..config import (
    get_current_match_source,
    get_historical_aggregate_source,
    get_historical_match_source,
    get_server_list_source,
)
from ..server_targets import load_server_targets
from ..services.current_match import (
    start_current_match_log_streams,
    stop_current_match_log_streams,
)


class LegacyReaderAccessError(RuntimeError):
    """Raised when a guarded application-owned legacy reader is invoked."""


# These are aliases at the payload use site, not definitions in storage modules.
# High-level rollback builders are included because some legacy implementations
# deliberately catch low-level read errors to return degraded public payloads.
LEGACY_READER_BOUNDARIES: tuple[tuple[str, str], ...] = (
    ("app.api.payloads.servers", "_build_legacy_servers_payload"),
    ("app.api.payloads.servers", "list_latest_snapshots"),
    ("app.api.payloads.servers", "list_snapshot_history"),
    ("app.api.payloads.servers", "list_server_history"),
    ("app.api.payloads.servers", "get_live_data_source"),
    ("app.api.payloads.current_match", "_build_legacy_current_match_payload"),
    ("app.api.payloads.current_match", "_build_legacy_current_match_kill_feed_payload"),
    ("app.api.payloads.current_match", "_build_legacy_current_match_player_stats_payload"),
    ("app.api.payloads.current_match", "_query_current_match_rcon_sample"),
    ("app.api.payloads.current_match", "list_current_match_kill_feed"),
    ("app.api.payloads.current_match", "list_current_match_player_stats"),
    ("app.api.payloads.current_match", "_build_legacy_servers_payload"),
    ("app.api.payloads.history", "_build_recent_historical_matches_legacy_snapshot_payload"),
    ("app.api.payloads.history", "_build_historical_server_summary_legacy_snapshot_payload"),
    ("app.api.payloads.history", "list_recent_historical_matches"),
    ("app.api.payloads.history", "get_historical_match_detail"),
    ("app.api.payloads.history", "list_historical_server_summaries"),
    ("app.api.payloads.history", "_get_historical_snapshot_record"),
    ("app.api.payloads.history", "get_rcon_historical_match_detail"),
    ("app.api.payloads.history", "get_rcon_historical_read_model"),
    ("app.api.payloads.rankings", "list_monthly_leaderboard"),
    ("app.api.payloads.rankings", "list_weekly_leaderboard"),
    ("app.api.payloads.rankings", "list_weekly_top_kills"),
    ("app.api.payloads.rankings", "get_annual_ranking_snapshot"),
    ("app.api.payloads.rankings", "get_latest_ranking_snapshot"),
    ("app.api.payloads.rankings", "list_rcon_materialized_leaderboard"),
    ("app.api.payloads.rankings", "_get_historical_snapshot_record"),
    ("app.api.payloads.players", "search_rcon_materialized_players"),
    ("app.api.payloads.players", "get_rcon_materialized_player_stats"),
    ("app.api.payloads.players", "get_historical_player_profile"),
)


def effective_selectors() -> dict[str, str]:
    """Return the four selectors that own canonical gameplay dispatch."""
    return {
        "server_list_source": get_server_list_source(),
        "current_match_source": get_current_match_source(),
        "historical_match_source": get_historical_match_source(),
        "historical_aggregate_source": get_historical_aggregate_source(),
    }


def _safe_effective_selectors() -> dict[str, str]:
    try:
        return effective_selectors()
    except ValueError:
        return {"configuration": "invalid"}


def _safe_failure_reason(error: Exception) -> str:
    reason = str(error)
    safe_reasons = {
        "all-four-effective-selectors-must-be-crcon",
        "no-enabled-server-targets",
        "kills-route-not-on-crcon-log-stream",
        "no-recent-match-for-detail",
    }
    if reason in safe_reasons or reason.startswith("canonical-route-status:"):
        return reason
    return "configuration-or-route-validation-failed"


def _raise_legacy_reader(boundary: str):
    def guarded(*_args: object, **_kwargs: object) -> None:
        raise LegacyReaderAccessError(f"legacy-reader-access:{boundary}")

    return guarded


@contextmanager
def guard_legacy_readers() -> Iterator[None]:
    """Patch every known payload-level legacy boundary for this process only."""
    with ExitStack() as stack:
        for module_name, attribute in LEGACY_READER_BOUNDARIES:
            module = importlib.import_module(module_name)
            stack.enter_context(
                patch.object(
                    module,
                    attribute,
                    _raise_legacy_reader(f"{module_name}.{attribute}"),
                )
            )
        yield


def _require_ok(path: str) -> dict[str, object]:
    status, payload = resolve_get_payload(path)
    if status != HTTPStatus.OK:
        raise RuntimeError(f"canonical-route-status:{int(status or 0)}")
    return payload


def verify_canonical_routes(*, manage_log_streams: bool = True) -> dict[str, object]:
    """Exercise deployed canonical routes without printing their response data."""
    selectors = effective_selectors()
    if any(value != "crcon" for value in selectors.values()):
        raise RuntimeError("all-four-effective-selectors-must-be-crcon")

    targets = load_server_targets().all(enabled_only=True)
    if not targets:
        raise RuntimeError("no-enabled-server-targets")

    route_count = 0
    detail_count = 0
    streams_started = False
    try:
        if manage_log_streams:
            start_current_match_log_streams()
            streams_started = True
        with guard_legacy_readers():
            _require_ok("/api/servers")
            route_count += 1

            for target in targets:
                query = urlencode({"server": target.key})
                _require_ok(f"/api/current-match/snapshot?{query}")
                route_count += 1
                kills = _require_ok(f"/api/current-match/kills?{query}")
                kills_data = kills.get("data") if isinstance(kills, dict) else None
                if not isinstance(kills_data, dict) or kills_data.get(
                    "selected_source"
                ) != "crcon-log-stream":
                    raise RuntimeError("kills-route-not-on-crcon-log-stream")
                route_count += 1
                _require_ok(f"/api/current-match/players?{query}")
                route_count += 1

                recent = _require_ok(
                    f"/api/historical/snapshots/recent-matches?{query}&limit=1&page=1"
                )
                route_count += 1
                data = recent.get("data") if isinstance(recent, dict) else None
                items = data.get("items") if isinstance(data, dict) else None
                first = items[0] if isinstance(items, list) and items else None
                match_id = first.get("match_id") if isinstance(first, dict) else None
                if match_id is None:
                    raise RuntimeError("no-recent-match-for-detail")
                detail_query = urlencode({"server": target.key, "match": str(match_id)})
                _require_ok(f"/api/historical/matches/detail?{detail_query}")
                route_count += 1
                detail_count += 1

            _require_ok("/api/historical/snapshots/server-summary?server=all-servers")
            _require_ok("/api/ranking?timeframe=weekly&metric=kills&limit=1")
            _require_ok("/api/stats/players/search?q=task313-nonexistent-player&limit=1")
            opaque = quote("task313-nonexistent-opaque-player", safe="")
            _require_ok(f"/api/stats/players/{opaque}?timeframe=weekly")
            route_count += 4
    finally:
        if streams_started:
            stop_current_match_log_streams()

    return {
        "status": "ok",
        "selectors": selectors,
        "enabled_target_count": len(targets),
        "route_count": route_count,
        "detail_route_count": detail_count,
        "log_stream_scope": "process-local-native-reader",
        "legacy_reader_access_count": 0,
    }


def main() -> int:
    try:
        result = verify_canonical_routes()
    except LegacyReaderAccessError as error:
        print(json.dumps({"status": "failed", "reason": str(error)}, sort_keys=True))
        return 3
    except (RuntimeError, ValueError) as error:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "reason": _safe_failure_reason(error),
                    "selectors": _safe_effective_selectors(),
                },
                sort_keys=True,
            )
        )
        return 2
    except Exception:  # noqa: BLE001 - never expose route payloads or raw identifiers
        print(json.dumps({"status": "failed", "reason": "unexpected-route-error"}))
        return 4
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
