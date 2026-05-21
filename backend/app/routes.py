"""Route resolution helpers for the HLL Vietnam backend bootstrap."""

from __future__ import annotations

from http import HTTPStatus
from urllib.parse import parse_qs, urlparse

from .payloads import (
    build_community_payload,
    build_current_match_kill_feed_payload,
    build_current_match_payload,
    build_discord_payload,
    build_elo_mmr_leaderboard_payload,
    build_elo_mmr_player_payload,
    build_error_payload,
    build_health_payload,
    build_historical_leaderboard_payload,
    build_historical_match_detail_payload,
    build_monthly_mvp_payload,
    build_monthly_mvp_v2_payload,
    build_monthly_leaderboard_payload,
    build_monthly_leaderboard_snapshot_payload,
    build_monthly_mvp_snapshot_payload,
    build_monthly_mvp_v2_snapshot_payload,
    build_player_event_payload,
    build_player_event_snapshot_payload,
    build_historical_server_summary_snapshot_payload,
    build_historical_player_profile_payload,
    build_historical_server_summary_payload,
    build_leaderboard_snapshot_payload,
    build_recent_historical_matches_snapshot_payload,
    build_recent_historical_matches_payload,
    build_server_detail_history_payload,
    build_server_history_payload,
    build_server_latest_payload,
    build_servers_payload,
    build_trailer_payload,
    build_weekly_leaderboard_snapshot_payload,
    build_weekly_leaderboard_payload,
    build_weekly_top_kills_payload,
)
from .scoreboard_origins import get_trusted_public_scoreboard_origin


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

    if parsed.path == "/api/current-match":
        server_slug = parse_qs(parsed.query).get("server", [None])[0]
        if not server_slug:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Server parameter is required")
        if get_trusted_public_scoreboard_origin(server_slug) is None:
            return HTTPStatus.NOT_FOUND, build_error_payload("Current match server is not supported")
        return HTTPStatus.OK, build_current_match_payload(server_slug=server_slug)

    if parsed.path == "/api/current-match/kills":
        limit = _parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        server_slug = parse_qs(parsed.query).get("server", [None])[0]
        if not server_slug:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Server parameter is required")
        if get_trusted_public_scoreboard_origin(server_slug) is None:
            return HTTPStatus.NOT_FOUND, build_error_payload("Current match server is not supported")
        return HTTPStatus.OK, build_current_match_kill_feed_payload(
            server_slug=server_slug,
            limit=limit,
        )

    if parsed.path == "/api/historical/weekly-top-kills":
        limit = _parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        server_id = parse_qs(parsed.query).get("server", [None])[0]
        return HTTPStatus.OK, build_weekly_top_kills_payload(limit=limit, server_id=server_id)

    if parsed.path == "/api/historical/leaderboard":
        limit = _parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        params = parse_qs(parsed.query)
        server_id = params.get("server", [None])[0]
        metric = params.get("metric", ["kills"])[0]
        timeframe = params.get("timeframe", ["weekly"])[0]
        if metric not in {"kills", "deaths", "support", "matches_over_100_kills"}:
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
        limit = _parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        params = parse_qs(parsed.query)
        server_id = params.get("server", [None])[0]
        metric = params.get("metric", ["kills"])[0]
        if metric not in {"kills", "deaths", "support", "matches_over_100_kills"}:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid metric parameter")
        return HTTPStatus.OK, build_weekly_leaderboard_payload(
            limit=limit,
            server_id=server_id,
            metric=metric,
        )

    if parsed.path == "/api/historical/monthly-leaderboard":
        limit = _parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        params = parse_qs(parsed.query)
        server_id = params.get("server", [None])[0]
        metric = params.get("metric", ["kills"])[0]
        if metric not in {"kills", "deaths", "support", "matches_over_100_kills"}:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid metric parameter")
        return HTTPStatus.OK, build_monthly_leaderboard_payload(
            limit=limit,
            server_id=server_id,
            metric=metric,
        )

    if parsed.path == "/api/historical/monthly-mvp":
        limit = _parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        server_id = parse_qs(parsed.query).get("server", [None])[0]
        return HTTPStatus.OK, build_monthly_mvp_payload(
            limit=limit,
            server_id=server_id,
        )

    if parsed.path == "/api/historical/monthly-mvp-v2":
        limit = _parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        server_id = parse_qs(parsed.query).get("server", [None])[0]
        return HTTPStatus.OK, build_monthly_mvp_v2_payload(
            limit=limit,
            server_id=server_id,
        )

    if parsed.path == "/api/historical/player-events":
        limit = _parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        params = parse_qs(parsed.query)
        server_id = params.get("server", [None])[0]
        view = params.get("view", ["most-killed"])[0]
        if view not in {"most-killed", "death-by", "duels", "weapon-kills", "teamkills"}:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid view parameter")
        return HTTPStatus.OK, build_player_event_payload(
            limit=limit,
            server_id=server_id,
            view=view,
        )

    if parsed.path == "/api/historical/snapshots/leaderboard":
        limit = _parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        params = parse_qs(parsed.query)
        server_id = params.get("server", [None])[0]
        metric = params.get("metric", ["kills"])[0]
        timeframe = params.get("timeframe", ["weekly"])[0]
        if metric not in {"kills", "deaths", "support", "matches_over_100_kills"}:
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
        limit = _parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        params = parse_qs(parsed.query)
        server_id = params.get("server", [None])[0]
        metric = params.get("metric", ["kills"])[0]
        if metric not in {"kills", "deaths", "support", "matches_over_100_kills"}:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid metric parameter")
        return HTTPStatus.OK, build_monthly_leaderboard_snapshot_payload(
            limit=limit,
            server_id=server_id,
            metric=metric,
        )

    if parsed.path == "/api/historical/snapshots/monthly-mvp":
        limit = _parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        server_id = parse_qs(parsed.query).get("server", [None])[0]
        return HTTPStatus.OK, build_monthly_mvp_snapshot_payload(
            limit=limit,
            server_id=server_id,
        )

    if parsed.path == "/api/historical/snapshots/monthly-mvp-v2":
        limit = _parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        server_id = parse_qs(parsed.query).get("server", [None])[0]
        return HTTPStatus.OK, build_monthly_mvp_v2_snapshot_payload(
            limit=limit,
            server_id=server_id,
        )

    if parsed.path == "/api/historical/snapshots/player-events":
        limit = _parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        params = parse_qs(parsed.query)
        server_id = params.get("server", [None])[0]
        view = params.get("view", ["most-killed"])[0]
        if view not in {"most-killed", "death-by", "duels", "weapon-kills", "teamkills"}:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid view parameter")
        return HTTPStatus.OK, build_player_event_snapshot_payload(
            limit=limit,
            server_id=server_id,
            view=view,
        )

    if parsed.path == "/api/historical/snapshots/weekly-leaderboard":
        limit = _parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        params = parse_qs(parsed.query)
        server_id = params.get("server", [None])[0]
        metric = params.get("metric", ["kills"])[0]
        if metric not in {"kills", "deaths", "support", "matches_over_100_kills"}:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid metric parameter")
        return HTTPStatus.OK, build_weekly_leaderboard_snapshot_payload(
            limit=limit,
            server_id=server_id,
            metric=metric,
        )

    if parsed.path == "/api/historical/recent-matches":
        limit = _parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        server_slug = parse_qs(parsed.query).get("server", [None])[0]
        return HTTPStatus.OK, build_recent_historical_matches_payload(
            limit=limit,
            server_slug=server_slug,
        )

    if parsed.path == "/api/historical/snapshots/recent-matches":
        limit = _parse_limit(parsed.query)
        if limit is None:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Invalid limit parameter")
        server_slug = parse_qs(parsed.query).get("server", [None])[0]
        return HTTPStatus.OK, build_recent_historical_matches_snapshot_payload(
            limit=limit,
            server_slug=server_slug,
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

    if parsed.path == "/api/historical/snapshots/server-summary":
        server_slug = parse_qs(parsed.query).get("server", [None])[0]
        return HTTPStatus.OK, build_historical_server_summary_snapshot_payload(
            server_slug=server_slug
        )

    if parsed.path == "/api/historical/player-profile":
        player_id = parse_qs(parsed.query).get("player", [None])[0]
        if not player_id:
            return HTTPStatus.BAD_REQUEST, build_error_payload("Player parameter is required")
        return HTTPStatus.OK, build_historical_player_profile_payload(player_id)

    if parsed.path == "/api/historical/elo-mmr/leaderboard":
        limit = _parse_limit(parsed.query)
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
