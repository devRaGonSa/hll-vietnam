"""Product-decision-required MVP, player-event and Elo route dispatch."""

from __future__ import annotations

from http import HTTPStatus
from urllib.parse import ParseResult, parse_qs

from ..payloads.product_features import (
    build_elo_mmr_leaderboard_payload,
    build_elo_mmr_player_payload,
    build_monthly_mvp_payload,
    build_monthly_mvp_snapshot_payload,
    build_monthly_mvp_v2_payload,
    build_monthly_mvp_v2_snapshot_payload,
    build_player_event_payload,
    build_player_event_snapshot_payload,
)
from ..payloads.static import build_error_payload
from .common import RouteResult, parse_limit, unmatched_route

PLAYER_EVENT_VIEWS = {
    "most-killed",
    "death-by",
    "duels",
    "weapon-kills",
    "teamkills",
}


def resolve_product_features_route(parsed: ParseResult) -> RouteResult:
    """Resolve retained product-feature routes without changing disposition."""
    if parsed.path == "/api/historical/monthly-mvp":
        limit = parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        server_id = parse_qs(parsed.query).get("server", [None])[0]
        return HTTPStatus.OK, build_monthly_mvp_payload(
            limit=limit,
            server_id=server_id,
        )

    if parsed.path == "/api/historical/monthly-mvp-v2":
        limit = parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        server_id = parse_qs(parsed.query).get("server", [None])[0]
        return HTTPStatus.OK, build_monthly_mvp_v2_payload(
            limit=limit,
            server_id=server_id,
        )

    if parsed.path == "/api/historical/player-events":
        limit = parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        params = parse_qs(parsed.query)
        server_id = params.get("server", [None])[0]
        view = params.get("view", ["most-killed"])[0]
        if view not in PLAYER_EVENT_VIEWS:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid view parameter")
        return HTTPStatus.OK, build_player_event_payload(
            limit=limit,
            server_id=server_id,
            view=view,
        )

    if parsed.path == "/api/historical/snapshots/monthly-mvp":
        limit = parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        server_id = parse_qs(parsed.query).get("server", [None])[0]
        return HTTPStatus.OK, build_monthly_mvp_snapshot_payload(
            limit=limit,
            server_id=server_id,
        )

    if parsed.path == "/api/historical/snapshots/monthly-mvp-v2":
        limit = parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        server_id = parse_qs(parsed.query).get("server", [None])[0]
        return HTTPStatus.OK, build_monthly_mvp_v2_snapshot_payload(
            limit=limit,
            server_id=server_id,
        )

    if parsed.path == "/api/historical/snapshots/player-events":
        limit = parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        params = parse_qs(parsed.query)
        server_id = params.get("server", [None])[0]
        view = params.get("view", ["most-killed"])[0]
        if view not in PLAYER_EVENT_VIEWS:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid view parameter")
        return HTTPStatus.OK, build_player_event_snapshot_payload(
            limit=limit,
            server_id=server_id,
            view=view,
        )

    if parsed.path == "/api/historical/elo-mmr/leaderboard":
        limit = parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        server_id = parse_qs(parsed.query).get("server", [None])[0]
        return HTTPStatus.OK, build_elo_mmr_leaderboard_payload(
            limit=limit,
            server_id=server_id,
        )

    if parsed.path == "/api/historical/elo-mmr/player":
        params = parse_qs(parsed.query)
        player_id = params.get("player", [None])[0]
        if not player_id:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Player parameter is required")
        server_id = params.get("server", [None])[0]
        return HTTPStatus.OK, build_elo_mmr_player_payload(
            player_id=player_id,
            server_id=server_id,
        )

    return unmatched_route()
