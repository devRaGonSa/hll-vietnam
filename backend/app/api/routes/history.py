"""Historical match browsing and legacy summary route dispatch."""

from __future__ import annotations

from http import HTTPStatus
from urllib.parse import ParseResult, parse_qs

from ..payloads.history import (
    build_historical_match_detail_payload,
    build_historical_server_summary_payload,
    build_recent_historical_matches_payload,
    build_recent_historical_matches_snapshot_payload,
)
from ..payloads.static import build_error_payload
from .common import RouteResult, parse_limit, parse_page, unmatched_route


def resolve_history_route(parsed: ParseResult) -> RouteResult:
    """Resolve recent match, match detail and legacy summary routes."""
    if parsed.path == "/api/historical/recent-matches":
        limit = parse_limit(parsed.query)
        page = parse_page(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        if page is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid page parameter")
        server_slug = parse_qs(parsed.query).get("server", [None])[0]
        return HTTPStatus.OK, build_recent_historical_matches_payload(
            limit=limit,
            server_slug=server_slug,
            page=page,
        )

    if parsed.path == "/api/historical/snapshots/recent-matches":
        limit = parse_limit(parsed.query)
        page = parse_page(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        if page is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid page parameter")
        server_slug = parse_qs(parsed.query).get("server", [None])[0]
        return HTTPStatus.OK, build_recent_historical_matches_snapshot_payload(
            limit=limit,
            server_slug=server_slug,
            page=page,
        )

    if parsed.path == "/api/historical/matches/detail":
        params = parse_qs(parsed.query)
        server_slug = params.get("server", [None])[0]
        match_id = params.get("match", [None])[0]
        if not server_slug:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Server parameter is required")
        if not match_id:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Match parameter is required")
        return HTTPStatus.OK, build_historical_match_detail_payload(
            server_slug=server_slug,
            match_id=match_id,
        )

    if parsed.path == "/api/historical/server-summary":
        server_slug = parse_qs(parsed.query).get("server", [None])[0]
        return HTTPStatus.OK, build_historical_server_summary_payload(server_slug=server_slug)

    return unmatched_route()
