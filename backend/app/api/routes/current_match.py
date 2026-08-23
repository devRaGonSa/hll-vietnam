"""Current-match route dispatch with unchanged CRCON degradation mapping."""

from __future__ import annotations

from collections.abc import Callable
from http import HTTPStatus
from urllib.parse import ParseResult, parse_qs

from ...scoreboard_origins import get_trusted_public_scoreboard_origin
from ...services.current_match import CurrentMatchCursorError, CurrentMatchUnavailableError
from ..payloads.current_match import (
    build_current_match_kill_feed_payload,
    build_current_match_player_stats_payload,
    build_current_match_payload,
    build_current_match_snapshot_payload,
)
from ..payloads.static import build_error_payload
from .common import RouteResult, parse_limit, unmatched_route


def resolve_current_match_route(parsed: ParseResult) -> RouteResult:
    """Resolve all current-match snapshot and compatibility transports."""
    if parsed.path == "/api/current-match/snapshot":
        server_slug = parse_qs(parsed.query).get("server", [None])[0]
        validation_error = _validate_current_match_server(server_slug)
        if validation_error is not None:
            return validation_error
        return _resolve_current_match_builder(
            lambda: build_current_match_snapshot_payload(server_slug=server_slug)
        )

    if parsed.path == "/api/current-match":
        server_slug = parse_qs(parsed.query).get("server", [None])[0]
        validation_error = _validate_current_match_server(server_slug)
        if validation_error is not None:
            return validation_error
        return _resolve_current_match_builder(
            lambda: build_current_match_payload(server_slug=server_slug)
        )

    if parsed.path == "/api/current-match/kills":
        limit = parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        params = parse_qs(parsed.query)
        server_slug = params.get("server", [None])[0]
        validation_error = _validate_current_match_server(server_slug)
        if validation_error is not None:
            return validation_error
        return _resolve_current_match_builder(
            lambda: build_current_match_kill_feed_payload(
                server_slug=server_slug,
                limit=limit,
                since_event_id=params.get("since_event_id", [None])[0],
            )
        )

    if parsed.path == "/api/current-match/players":
        server_slug = parse_qs(parsed.query).get("server", [None])[0]
        validation_error = _validate_current_match_server(server_slug)
        if validation_error is not None:
            return validation_error
        return _resolve_current_match_builder(
            lambda: build_current_match_player_stats_payload(server_slug=server_slug)
        )

    return unmatched_route()


def _validate_current_match_server(server_slug: str | None) -> RouteResult | None:
    if not server_slug:
        return HTTPStatus.BAD_REQUEST, build_error_payload("Server parameter is required")
    if get_trusted_public_scoreboard_origin(server_slug) is None:
        return HTTPStatus.NOT_FOUND, build_error_payload("Current match server is not supported")
    return None


def _resolve_current_match_builder(
    builder: Callable[[], dict[str, object]],
) -> RouteResult:
    try:
        return HTTPStatus.OK, builder()
    except CurrentMatchCursorError as error:
        return HTTPStatus.BAD_REQUEST, build_error_payload(str(error))
    except CurrentMatchUnavailableError:
        return HTTPStatus.SERVICE_UNAVAILABLE, build_error_payload(
            "CRCON current match is unavailable"
        )
