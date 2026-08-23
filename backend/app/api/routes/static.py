"""System, health and static community route dispatch."""

from __future__ import annotations

from http import HTTPStatus
from urllib.parse import ParseResult

from ..payloads.static import (
    build_community_payload,
    build_discord_payload,
    build_health_payload,
    build_trailer_payload,
)
from .common import RouteResult, unmatched_route

STATIC_GET_ROUTES = {
    "/health": build_health_payload,
    "/api/community": build_community_payload,
    "/api/trailer": build_trailer_payload,
    "/api/discord": build_discord_payload,
}


def resolve_static_route(parsed: ParseResult) -> RouteResult:
    """Resolve system and static community routes."""
    builder = STATIC_GET_ROUTES.get(parsed.path)
    if builder is None:
        return unmatched_route()
    return HTTPStatus.OK, builder()
