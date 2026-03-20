"""Route resolution helpers for the HLL Vietnam backend bootstrap."""

from __future__ import annotations

from http import HTTPStatus
from urllib.parse import parse_qs, urlparse

from .payloads import (
    build_community_payload,
    build_discord_payload,
    build_error_payload,
    build_health_payload,
    build_historical_player_profile_payload,
    build_historical_server_summary_payload,
    build_recent_historical_matches_payload,
    build_server_detail_history_payload,
    build_server_history_payload,
    build_server_latest_payload,
    build_servers_payload,
    build_trailer_payload,
    build_weekly_top_kills_payload,
)


GET_ROUTES = {
    "/health": build_health_payload,
    "/api/community": build_community_payload,
    "/api/trailer": build_trailer_payload,
    "/api/discord": build_discord_payload,
    "/api/servers": build_servers_payload,
}


def resolve_get_payload(path: str) -> tuple[HTTPStatus | None, dict[str, object]]:
    """Resolve the JSON payload for a supported GET route."""
    parsed = urlparse(path)
    if parsed.path == "/api/servers/latest":
        return HTTPStatus.OK, build_server_latest_payload()

    if parsed.path == "/api/servers/history":
        limit = _parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        return HTTPStatus.OK, build_server_history_payload(limit=limit)

    if parsed.path == "/api/historical/weekly-top-kills":
        limit = _parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        server_id = parse_qs(parsed.query).get("server", [None])[0]
        return HTTPStatus.OK, build_weekly_top_kills_payload(limit=limit, server_id=server_id)

    if parsed.path == "/api/historical/recent-matches":
        limit = _parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        server_slug = parse_qs(parsed.query).get("server", [None])[0]
        return HTTPStatus.OK, build_recent_historical_matches_payload(
            limit=limit,
            server_slug=server_slug,
        )

    if parsed.path == "/api/historical/server-summary":
        server_slug = parse_qs(parsed.query).get("server", [None])[0]
        return HTTPStatus.OK, build_historical_server_summary_payload(server_slug=server_slug)

    if parsed.path == "/api/historical/player-profile":
        player_id = parse_qs(parsed.query).get("player", [None])[0]
        if not player_id:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Player parameter is required")
        return HTTPStatus.OK, build_historical_player_profile_payload(player_id)

    builder = GET_ROUTES.get(parsed.path)
    if builder is None:
        if parsed.path.startswith("/api/servers/") and parsed.path.endswith("/history"):
            server_id = parsed.path.removeprefix("/api/servers/").removesuffix("/history")
            server_id = server_id.strip("/")
            if not server_id:
                return HTTPStatus.BAD_REQUEST, build_error_payload("Server id is required")

            limit = _parse_limit(parsed.query)
            if limit is None:
                return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")

            return HTTPStatus.OK, build_server_detail_history_payload(server_id, limit=limit)
        return None, {}

    return HTTPStatus.OK, builder()


def _parse_limit(query: str) -> int | None:
    raw_limit = parse_qs(query).get("limit", ["20"])[0]
    try:
        limit = int(raw_limit)
    except ValueError:
        return None

    if limit < 1 or limit > 100:
        return None

    return limit
