"""Server-card and legacy snapshot-history route dispatch."""

from __future__ import annotations

from http import HTTPStatus
from urllib.parse import ParseResult

from ..payloads.servers import (
    build_server_detail_history_payload,
    build_server_history_payload,
    build_server_latest_payload,
    build_servers_payload,
)
from ..payloads.static import build_error_payload
from .common import RouteResult, parse_limit, unmatched_route


def resolve_servers_route(parsed: ParseResult) -> RouteResult:
    """Resolve server cards before their dynamic history compatibility path."""
    if parsed.path == "/api/servers":
        return HTTPStatus.OK, build_servers_payload()

    if parsed.path == "/api/servers/latest":
        return HTTPStatus.OK, build_server_latest_payload()

    if parsed.path == "/api/servers/history":
        limit = parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        return HTTPStatus.OK, build_server_history_payload(limit=limit)

    if parsed.path.startswith("/api/servers/") and parsed.path.endswith("/history"):
        server_id = parsed.path.removeprefix("/api/servers/").removesuffix("/history")
        server_id = server_id.strip("/")
        if not server_id:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Server id is required")

        limit = parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")

        return HTTPStatus.OK, build_server_detail_history_payload(server_id, limit=limit)

    return unmatched_route()
