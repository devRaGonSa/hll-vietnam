"""Player search, stats profile and legacy profile route dispatch."""

from __future__ import annotations

from http import HTTPStatus
from urllib.parse import ParseResult, parse_qs

from ..payloads.players import (
    build_historical_player_profile_payload,
    build_stats_player_profile_payload,
    build_stats_player_search_payload,
)
from ..payloads.static import build_error_payload
from .common import RouteResult, parse_limit_with_default, unmatched_route


def resolve_players_route(parsed: ParseResult) -> RouteResult:
    """Resolve exact search before the dynamic opaque player-ID route."""
    if parsed.path == "/api/stats/players/search":
        params = parse_qs(parsed.query)
        query = str(params.get("q", [None])[0] or "").strip()
        if not query:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Query parameter is required")
        limit = parse_limit_with_default(parsed.query, default=10)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        server_id = params.get("server_id", [None])[0]
        if server_id is None:
            server_id = params.get("server", [None])[0]
        return HTTPStatus.OK, build_stats_player_search_payload(
            query=query,
            server_id=server_id,
            limit=limit,
        )

    if parsed.path.startswith("/api/stats/players/"):
        player_id = parsed.path.removeprefix("/api/stats/players/").strip()
        if not player_id:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Player id is required")
        params = parse_qs(parsed.query)
        timeframe = params.get("timeframe", ["weekly"])[0] or "weekly"
        if timeframe not in {"weekly", "monthly"}:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid timeframe parameter")
        server_id = params.get("server_id", [None])[0]
        if server_id is None:
            server_id = params.get("server", [None])[0]
        return HTTPStatus.OK, build_stats_player_profile_payload(
            player_id=player_id,
            server_id=server_id,
            timeframe=timeframe,
        )

    if parsed.path == "/api/historical/player-profile":
        player_id = parse_qs(parsed.query).get("player", [None])[0]
        if not player_id:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Player parameter is required")
        return HTTPStatus.OK, build_historical_player_profile_payload(player_id)

    return unmatched_route()
