"""Ranking, leaderboard and aggregate-summary route dispatch."""

from __future__ import annotations

from http import HTTPStatus
from urllib.parse import ParseResult, parse_qs

from ...config import get_historical_aggregate_source
from ...server_targets import load_server_targets
from ..payloads.rankings import (
    build_annual_ranking_snapshot_payload,
    build_global_ranking_payload,
    build_historical_leaderboard_payload,
    build_historical_server_summary_snapshot_payload,
    build_leaderboard_snapshot_payload,
    build_monthly_leaderboard_payload,
    build_monthly_leaderboard_snapshot_payload,
    build_weekly_leaderboard_payload,
    build_weekly_leaderboard_snapshot_payload,
    build_weekly_top_kills_payload,
)
from ..payloads.static import build_error_payload
from .common import (
    RouteResult,
    parse_limit,
    parse_required_year,
    parse_year,
    unmatched_route,
)

RANKING_METRICS = {
    "kills",
    "deaths",
    "teamkills",
    "matches_considered",
    "kd_ratio",
    "kills_per_match",
}

HISTORICAL_LEADERBOARD_METRICS = {
    "kills",
    "deaths",
    "support",
    "matches_over_100_kills",
}


def resolve_rankings_route(parsed: ParseResult) -> RouteResult:
    """Resolve ranking, leaderboard and aggregate snapshot routes."""
    if parsed.path == "/api/stats/rankings/annual":
        params = parse_qs(parsed.query)
        metric = params.get("metric", ["kills"])[0]
        if metric != "kills":
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid metric parameter")
        year = parse_year(parsed.query)
        if year is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid year parameter")
        limit = parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        server_id = params.get("server_id", [None])[0]
        if server_id is None:
            server_id = params.get("server", [None])[0]
        try:
            return HTTPStatus.OK, build_annual_ranking_snapshot_payload(
                year=year,
                server_id=server_id,
                metric=metric,
                limit=limit,
            )
        except ValueError as error:
            return HTTPStatus.BAD_REQUEST, build_error_payload(str(error))

    if parsed.path == "/api/ranking":
        params = parse_qs(parsed.query)
        timeframe = params.get("timeframe", ["weekly"])[0]
        if timeframe not in {"weekly", "monthly", "annual"}:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid timeframe parameter")
        metric = params.get("metric", ["kills"])[0]
        if metric not in RANKING_METRICS:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid metric parameter")
        limit = parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        server_id = params.get("server_id", [None])[0]
        if server_id is None:
            server_id = params.get("server", [None])[0]
        if not _is_supported_ranking_server_id(server_id):
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid server_id parameter")
        year = None
        if timeframe == "annual":
            year = parse_required_year(parsed.query)
            if year is None:
                return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid year parameter")
        try:
            return HTTPStatus.OK, build_global_ranking_payload(
                timeframe=timeframe,
                server_id=server_id,
                metric=metric,
                limit=limit,
                year=year,
            )
        except ValueError as error:
            return HTTPStatus.BAD_REQUEST, build_error_payload(str(error))

    if parsed.path == "/api/historical/weekly-top-kills":
        limit = parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        server_id = parse_qs(parsed.query).get("server", [None])[0]
        return HTTPStatus.OK, build_weekly_top_kills_payload(limit=limit, server_id=server_id)

    if parsed.path == "/api/historical/leaderboard":
        limit = parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        params = parse_qs(parsed.query)
        server_id = params.get("server", [None])[0]
        metric = params.get("metric", ["kills"])[0]
        timeframe = params.get("timeframe", ["weekly"])[0]
        if metric not in HISTORICAL_LEADERBOARD_METRICS:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid metric parameter")
        if timeframe not in {"weekly", "monthly"}:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid timeframe parameter")
        return HTTPStatus.OK, build_historical_leaderboard_payload(
            limit=limit,
            server_id=server_id,
            metric=metric,
            timeframe=timeframe,
        )

    if parsed.path == "/api/historical/weekly-leaderboard":
        limit = parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        params = parse_qs(parsed.query)
        server_id = params.get("server", [None])[0]
        metric = params.get("metric", ["kills"])[0]
        if metric not in HISTORICAL_LEADERBOARD_METRICS:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid metric parameter")
        return HTTPStatus.OK, build_weekly_leaderboard_payload(
            limit=limit,
            server_id=server_id,
            metric=metric,
        )

    if parsed.path == "/api/historical/monthly-leaderboard":
        limit = parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        params = parse_qs(parsed.query)
        server_id = params.get("server", [None])[0]
        metric = params.get("metric", ["kills"])[0]
        if metric not in HISTORICAL_LEADERBOARD_METRICS:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid metric parameter")
        return HTTPStatus.OK, build_monthly_leaderboard_payload(
            limit=limit,
            server_id=server_id,
            metric=metric,
        )

    if parsed.path == "/api/historical/snapshots/leaderboard":
        limit = parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        params = parse_qs(parsed.query)
        server_id = params.get("server", [None])[0]
        metric = params.get("metric", ["kills"])[0]
        timeframe = params.get("timeframe", ["weekly"])[0]
        if metric not in HISTORICAL_LEADERBOARD_METRICS:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid metric parameter")
        if timeframe not in {"weekly", "monthly"}:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid timeframe parameter")
        return HTTPStatus.OK, build_leaderboard_snapshot_payload(
            limit=limit,
            server_id=server_id,
            metric=metric,
            timeframe=timeframe,
        )

    if parsed.path == "/api/historical/snapshots/monthly-leaderboard":
        limit = parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        params = parse_qs(parsed.query)
        server_id = params.get("server", [None])[0]
        metric = params.get("metric", ["kills"])[0]
        if metric not in HISTORICAL_LEADERBOARD_METRICS:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid metric parameter")
        return HTTPStatus.OK, build_monthly_leaderboard_snapshot_payload(
            limit=limit,
            server_id=server_id,
            metric=metric,
        )

    if parsed.path == "/api/historical/snapshots/weekly-leaderboard":
        limit = parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        params = parse_qs(parsed.query)
        server_id = params.get("server", [None])[0]
        metric = params.get("metric", ["kills"])[0]
        if metric not in HISTORICAL_LEADERBOARD_METRICS:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid metric parameter")
        return HTTPStatus.OK, build_weekly_leaderboard_snapshot_payload(
            limit=limit,
            server_id=server_id,
            metric=metric,
        )

    if parsed.path == "/api/historical/snapshots/server-summary":
        server_slug = parse_qs(parsed.query).get("server", [None])[0]
        return HTTPStatus.OK, build_historical_server_summary_snapshot_payload(
            server_slug=server_slug
        )

    return unmatched_route()


def _is_supported_ranking_server_id(server_id: str | None) -> bool:
    if server_id is None:
        return True
    normalized = str(server_id).strip().lower()
    if get_historical_aggregate_source() == "crcon":
        if normalized in {"", "all", "all-servers"}:
            return True
        return load_server_targets().get(normalized) is not None
    return normalized in {
        "",
        "all",
        "all-servers",
        "comunidad-hispana-01",
        "comunidad-hispana-02",
    }
