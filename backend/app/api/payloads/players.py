"""Player search/profile public compatibility payloads."""

from __future__ import annotations

from ...config import get_historical_aggregate_source
from ...historical_storage import get_historical_player_profile
from ...rcon_historical_player_stats import (
    get_rcon_materialized_player_stats,
    search_rcon_materialized_players,
)
from ...services.historical_aggregates import get_historical_aggregate_service
from ...services.player_search import get_crcon_player_search_service
from ..serializers import to_iso_or_none as _to_iso_or_none
from .common import _resolve_historical_fallback_policy

def build_stats_player_search_payload(
    *,
    query: str,
    server_id: str | None = None,
    limit: int = 10,
) -> dict[str, object]:
    """Return lightweight player search results for future stats UX flows."""
    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("Query cannot be empty.")

    if get_historical_aggregate_source() == "crcon":
        result = get_crcon_player_search_service().search(
            query=normalized_query,
            server_id=server_id,
            limit=limit,
        )
        return {"status": "ok", "data": result}

    result = search_rcon_materialized_players(
        query=normalized_query,
        server_id=server_id,
        limit=limit,
    )
    return {
        "status": "ok",
        "data": {
            "query": result["query"],
            "server_id": result["server_id"],
            "source": result.get("source"),
            "items": result["items"],
        },
    }


def build_stats_player_profile_payload(
    *,
    player_id: str,
    server_id: str | None = None,
    timeframe: str = "weekly",
) -> dict[str, object]:
    """Return personal RCON materialized stats and weekly/monthly ranking context."""
    if get_historical_aggregate_source() == "crcon":
        result = get_historical_aggregate_service().player_profile(
            player_id=player_id,
            server_id=server_id,
            timeframe=timeframe,
        )
        return {"status": "ok", "data": result}

    result = get_rcon_materialized_player_stats(
        player_id=player_id,
        server_id=server_id,
        timeframe=timeframe,
    )
    kills = int(result.get("kills", 0) or 0)
    deaths = int(result.get("deaths", 0) or 0)
    matches_considered = int(result.get("matches_considered", 0) or 0)
    teamkills = int(result.get("teamkills", 0) or 0)
    kills_per_match = round(kills / matches_considered, 2) if matches_considered else 0.0
    deaths_per_match = round(deaths / matches_considered, 2) if matches_considered else 0.0
    kd_ratio = round(kills / deaths, 2) if deaths else float(kills)
    return {
        "status": "ok",
        "data": {
            "player_id": result.get("player_id"),
            "player_name": result.get("player_name"),
            "platform": result.get("platform"),
            "steam_id_64": result.get("steam_id_64"),
            "epic_id": result.get("epic_id"),
            "external_profile_links": result.get("external_profile_links") or {},
            "server_id": result.get("server_id"),
            "timeframe": result.get("timeframe"),
            "window_start": _to_iso_or_none(result.get("window_start")),
            "window_end": _to_iso_or_none(result.get("window_end")),
            "window_kind": result.get("window_kind"),
            "matches_considered": matches_considered,
            "kills": kills,
            "deaths": deaths,
            "teamkills": teamkills,
            "kd_ratio": kd_ratio,
            "kills_per_match": kills_per_match,
            "deaths_per_match": deaths_per_match,
            "player_active_seconds": result.get("player_active_seconds"),
            "player_active_minutes": result.get("player_active_minutes"),
            "kpm": result.get("kpm"),
            "kpm_status": result.get("kpm_status"),
            "active_time_source": result.get("active_time_source"),
            "active_time_coverage": result.get("active_time_coverage"),
            "weekly_ranking": result.get("weekly_ranking"),
            "monthly_ranking": result.get("monthly_ranking"),
            "source": result.get("source"),
        },
    }


def build_historical_player_profile_payload(player_id: str) -> dict[str, object]:
    """Return aggregate historical metrics for one player identity."""
    profile = get_historical_player_profile(player_id)
    return {
        "status": "ok",
        "data": {
            "title": "Perfil historico de jugador",
            "context": "historical-player-profile",
            "source": "historical-crcon-storage",
            "player_id": player_id,
            "found": profile is not None,
            **_resolve_historical_fallback_policy(
                fallback_reason="rcon-historical-read-model-does-not-support-player-profile-yet",
            ),
            "profile": profile,
        },
    }
