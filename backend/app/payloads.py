"""Payload builders for the HLL Vietnam backend."""

from __future__ import annotations

from datetime import datetime, timezone
import re

from .config import (
    get_historical_data_source_kind,
    get_live_data_source_kind,
    get_refresh_interval_seconds,
)
from .data_sources import (
    LIVE_SOURCE_A2S,
    SOURCE_KIND_PUBLIC_SCOREBOARD,
    SOURCE_KIND_RCON,
    build_source_attempt,
    build_source_policy,
    build_historical_runtime_source_policy,
    describe_historical_runtime_policy,
    get_live_data_source,
    get_rcon_historical_read_model,
)
from .historical_snapshot_storage import get_historical_snapshot
from .historical_snapshots import (
    DEFAULT_MONTHLY_SNAPSHOT_WINDOW,
    DEFAULT_SNAPSHOT_WINDOW,
    DEFAULT_WEEKLY_SNAPSHOT_WINDOW,
    SNAPSHOT_TYPE_MONTHLY_LEADERBOARD,
    SNAPSHOT_TYPE_MONTHLY_MVP,
    SNAPSHOT_TYPE_MONTHLY_MVP_V2,
    SNAPSHOT_TYPE_PLAYER_EVENT_DEATH_BY,
    SNAPSHOT_TYPE_PLAYER_EVENT_DUELS,
    SNAPSHOT_TYPE_PLAYER_EVENT_MOST_KILLED,
    SNAPSHOT_TYPE_PLAYER_EVENT_TEAMKILLS,
    SNAPSHOT_TYPE_PLAYER_EVENT_WEAPON_KILLS,
    SNAPSHOT_TYPE_RECENT_MATCHES,
    SNAPSHOT_TYPE_SERVER_SUMMARY,
    SNAPSHOT_TYPE_WEEKLY_LEADERBOARD,
)
from .historical_storage import (
    ALL_SERVERS_SLUG,
    get_historical_match_detail,
    get_historical_player_profile,
    list_historical_server_summaries,
    list_monthly_leaderboard,
    list_recent_historical_matches,
    list_weekly_leaderboard,
    list_weekly_top_kills,
)
from .rcon_historical_read_model import get_rcon_historical_match_detail
from .rcon_annual_rankings import get_annual_ranking_snapshot
from .rcon_historical_leaderboards import (
    get_latest_ranking_snapshot,
    is_ranking_runtime_fallback_enabled,
    list_rcon_materialized_leaderboard,
)
from .rcon_historical_player_stats import search_rcon_materialized_players
from .rcon_historical_player_stats import get_rcon_materialized_player_stats
from .normalizers import normalize_map_name
from .rcon_client import load_rcon_targets, query_live_server_sample
from .rcon_admin_log_storage import list_current_match_kill_feed, list_current_match_player_stats
from .scoreboard_origins import get_trusted_public_scoreboard_origin
from .storage import list_latest_snapshots, list_server_history, list_snapshot_history


def build_health_payload() -> dict[str, str]:
    """Return a small status payload without committing to business contracts."""
    return {
        "status": "ok",
        "service": "hll-vietnam-backend",
        "phase": "bootstrap",
        "live_data_source": get_live_data_source_kind(),
        "historical_data_source": get_historical_data_source_kind(),
        "historical_runtime_policy": describe_historical_runtime_policy()["mode"],
        "live_runtime_policy": (
            "rcon-first-with-a2s-fallback"
            if get_live_data_source_kind() == SOURCE_KIND_RCON
            else "a2s-primary"
        ),
    }


def build_community_payload() -> dict[str, object]:
    """Return placeholder community content aligned with the documented contract."""
    return {
        "status": "ok",
        "data": {
            "title": "Comunidad Hispana HLL Vietnam",
            "summary": "Punto de encuentro para jugadores, escuadras y comunidad.",
            "discord_invite_url": "https://discord.com/invite/PedEqZ2Xsa",
        },
    }


def build_trailer_payload() -> dict[str, object]:
    """Return placeholder trailer metadata for future frontend consumption."""
    return {
        "status": "ok",
        "data": {
            "video_url": "https://www.youtube.com/embed/JzYzYNVWZ_A",
            "title": "Trailer HLL Vietnam",
            "provider": "youtube",
        },
    }


def build_discord_payload() -> dict[str, object]:
    """Return public Discord placeholder data without real integration."""
    return {
        "status": "ok",
        "data": {
            "invite_url": "https://discord.com/invite/PedEqZ2Xsa",
            "label": "Unirse al Discord",
            "availability": "manual",
        },
    }


def build_servers_payload() -> dict[str, object]:
    """Return current server status from persisted snapshots only."""
    max_snapshot_age_seconds = get_refresh_interval_seconds()
    persisted_items = _select_primary_snapshot_items(
        _enrich_server_items(list_latest_snapshots())
    )
    persisted_snapshot_at = _resolve_last_snapshot_at(persisted_items)
    persisted_snapshot_age_seconds = _calculate_snapshot_age_seconds(persisted_snapshot_at)
    refresh_errors: list[dict[str, object]] = []
    refresh_source_policy = build_source_policy(
        primary_source=get_live_data_source_kind(),
        selected_source="persisted-snapshot" if persisted_items else "none",
        fallback_reason=None,
        source_attempts=[
            build_source_attempt(
                source="persisted-snapshot",
                role="served-response",
                status="success" if persisted_items else "empty",
                reason="public-servers-read-is-cache-only",
            )
        ],
    )

    if persisted_items:
        response_source = (
            "persisted-stale-snapshot"
            if _is_snapshot_stale(persisted_snapshot_age_seconds, max_snapshot_age_seconds)
            else "persisted-fresh-snapshot"
        )
        return _build_servers_response(
            items=persisted_items,
            response_source=response_source,
            last_snapshot_at=persisted_snapshot_at,
            snapshot_age_seconds=persisted_snapshot_age_seconds,
            max_snapshot_age_seconds=max_snapshot_age_seconds,
            refresh_attempted=False,
            refresh_status="cache-only",
            refresh_errors=refresh_errors,
            source_policy=_infer_live_source_policy_from_items(
                persisted_items,
                refresh_attempted=False,
                refresh_errors=refresh_errors,
            ),
        )

    return {
        "status": "ok",
        "data": {
            "title": "Estado actual de servidores",
            "context": "current-hll-status",
            "source": "no-snapshot-available",
            "last_snapshot_at": None,
            "snapshot_age_seconds": None,
            "snapshot_age_minutes": None,
            "max_snapshot_age_seconds": max_snapshot_age_seconds,
            "is_stale": True,
            "freshness": "stale",
            "refresh_attempted": False,
            "refresh_status": "cache-only",
            "refresh_errors": refresh_errors,
            **refresh_source_policy,
            "items": [],
        },
    }


def build_server_latest_payload() -> dict[str, object]:
    """Return the latest persisted snapshot for each known server."""
    items = _enrich_server_items(list_latest_snapshots())
    return {
        "status": "ok",
        "data": {
            "title": "Ultimo estado conocido de servidores",
            "context": "current-hll-history",
            "source": "local-snapshot-storage",
            "summary_window_size": 6,
            "items": items,
        },
    }


def build_server_history_payload(*, limit: int = 20) -> dict[str, object]:
    """Return recent persisted snapshots across all known servers."""
    items = _enrich_server_items(list_snapshot_history(limit=limit))
    return {
        "status": "ok",
        "data": {
            "title": "Historial reciente de servidores",
            "context": "current-hll-history",
            "source": "local-snapshot-storage",
            "limit": limit,
            "items": items,
        },
    }


def build_server_detail_history_payload(
    server_id: str,
    *,
    limit: int = 20,
) -> dict[str, object]:
    """Return recent persisted snapshots for one server."""
    items = _enrich_server_items(list_server_history(server_id, limit=limit))
    return {
        "status": "ok",
        "data": {
            "title": "Historial por servidor",
            "context": "current-hll-history",
            "source": "local-snapshot-storage",
            "server_id": server_id,
            "limit": limit,
            "items": items,
        },
    }


def build_current_match_payload(*, server_slug: str) -> dict[str, object]:
    """Return the live page projection for one trusted active server."""
    origin = get_trusted_public_scoreboard_origin(server_slug)
    if origin is None:
        raise ValueError("Unsupported current match server.")

    sample = _query_current_match_rcon_sample(origin.slug)
    if sample is not None:
        normalized = sample["normalized"]
        raw_session = sample["raw_session"]
        captured_at = _utc_timestamp_now()
        map_id = raw_session.get("mapId") or normalized.get("current_map")
        map_name = raw_session.get("mapName") or map_id
        map_pretty_name = normalize_map_name(map_name)
        return {
            "status": "ok",
            "data": {
                "found": True,
                "server_slug": origin.slug,
                "server_name": normalized.get("server_name") or origin.display_name,
                "status": normalized.get("status") or "unavailable",
                "map": map_pretty_name,
                "map_id": map_id,
                "map_pretty_name": map_pretty_name,
                "game_mode": normalized.get("game_mode"),
                "started_at": None,
                "allied_score": normalized.get("allied_score"),
                "axis_score": normalized.get("axis_score"),
                "allied_players": normalized.get("allied_players"),
                "axis_players": normalized.get("axis_players"),
                "players": normalized.get("players"),
                "max_players": normalized.get("max_players"),
                # RCA: getSession currently reports 0 while the public scoreboard
                # can show players, so session population is exposed but unverified.
                "player_count_quality": (
                    "rcon-session-unverified"
                    if normalized.get("players") is not None
                    else None
                ),
                "player_count_source": _source_when_present(
                    normalized.get("players"),
                    source="rcon-session",
                ),
                "score_source": _source_when_present(
                    normalized.get("allied_score"),
                    normalized.get("axis_score"),
                    source="rcon-session",
                ),
                "map_source": _source_when_present(map_id, map_name, source="rcon-session"),
                "match_time_seconds": normalized.get("match_time_seconds"),
                "remaining_match_time_seconds": normalized.get(
                    "remaining_match_time_seconds"
                ),
                "captured_at": captured_at,
                "updated_at": captured_at,
                "public_scoreboard_url": origin.base_url,
            },
        }

    # The generic live server snapshot is a fallback only. It intentionally
    # drops richer RCON session fields such as game mode and current scores.
    server_payload = build_servers_payload()
    server_data = server_payload["data"]
    item = _find_current_match_snapshot_item(server_data.get("items", []), origin)
    return {
        "status": "ok",
        "data": {
            "found": item is not None,
            "server_slug": origin.slug,
            "server_name": item.get("server_name") if item else origin.display_name,
            "status": item.get("status") if item else "unavailable",
            "map": item.get("current_map") if item else None,
            "map_id": None,
            "map_pretty_name": item.get("current_map") if item else None,
            "game_mode": item.get("game_mode") if item else None,
            "started_at": item.get("started_at") if item else None,
            "allied_score": item.get("allied_score") if item else None,
            "axis_score": item.get("axis_score") if item else None,
            "allied_players": item.get("allied_players") if item else None,
            "axis_players": item.get("axis_players") if item else None,
            "players": item.get("players") if item else None,
            "max_players": item.get("max_players") if item else None,
            "player_count_quality": _snapshot_player_count_quality(item),
            "player_count_source": _snapshot_player_count_source(item),
            "score_source": _source_when_present(
                item.get("allied_score") if item else None,
                item.get("axis_score") if item else None,
                source="live-server-snapshot",
            ),
            "map_source": _source_when_present(
                item.get("current_map") if item else None,
                source="live-server-snapshot",
            ),
            "match_time_seconds": item.get("match_time_seconds") if item else None,
            "remaining_match_time_seconds": (
                item.get("remaining_match_time_seconds") if item else None
            ),
            "captured_at": item.get("captured_at") if item else None,
            "updated_at": server_data.get("last_snapshot_at"),
            "public_scoreboard_url": origin.base_url,
        },
    }


def _find_current_match_snapshot_item(
    items: list[dict[str, object]],
    origin: object,
) -> dict[str, object] | None:
    """Resolve one trusted live snapshot for the current-match fallback."""
    origin_slug = str(getattr(origin, "slug", "") or "").strip()
    source_markers = {
        "comunidad-hispana-01": ("152.114.195.174", ":7779"),
        "comunidad-hispana-02": ("152.114.195.150", ":7879"),
    }.get(origin_slug)
    server_number = getattr(origin, "server_number", None)

    for item in items:
        if any(
            str(item.get(field) or "").strip() == origin_slug
            for field in (
                "external_server_id",
                "server_slug",
                "target_key",
                "slug",
                "community_slug",
            )
        ):
            return item

        server_label = str(item.get("server_name") or item.get("name") or "")
        if _current_match_server_name_matches(server_label, server_number):
            return item

        source_identity = " ".join(
            str(item.get(field) or "") for field in ("external_server_id", "source_ref")
        )
        if source_markers and any(marker in source_identity for marker in source_markers):
            return item

    return None


def _current_match_server_name_matches(server_label: str, server_number: object) -> bool:
    if not isinstance(server_number, int):
        return False

    normalized_label = server_label.strip().casefold()
    if not normalized_label:
        return False

    numbered_marker = re.compile(rf"(?<!\d)#0*{server_number}(?!\d)")
    if numbered_marker.search(normalized_label):
        return True

    return f"comunidad hispana #{server_number:02d}" in normalized_label


def build_current_match_kill_feed_payload(
    *,
    server_slug: str,
    limit: int = 30,
    since_event_id: str | None = None,
) -> dict[str, object]:
    """Return normalized AdminLog kill rows for one trusted current-match page."""
    origin = get_trusted_public_scoreboard_origin(server_slug)
    if origin is None:
        raise ValueError("Unsupported current match server.")
    try:
        feed = list_current_match_kill_feed(
            server_key=origin.slug,
            limit=limit,
            since_event_id=since_event_id,
            ensure_storage=False,
        )
        source_policy = _build_current_match_admin_log_source_policy(status="success")
    except Exception as error:  # noqa: BLE001 - public live read must degrade cleanly
        feed = _empty_current_match_kill_feed_payload()
        source_policy = _build_current_match_admin_log_source_policy(
            status="error",
            error_reason=_public_error_reason(error),
            message=str(error),
        )
    return {
        "status": "ok",
        "data": {
            "server_slug": origin.slug,
            "server_name": origin.display_name,
            **source_policy,
            **feed,
        },
    }


def build_current_match_player_stats_payload(*, server_slug: str) -> dict[str, object]:
    """Return current player stats only when safe AdminLog evidence exists."""
    origin = get_trusted_public_scoreboard_origin(server_slug)
    if origin is None:
        raise ValueError("Unsupported current match server.")
    try:
        stats = list_current_match_player_stats(
            server_key=origin.slug,
            ensure_storage=False,
        )
        source_policy = _build_current_match_admin_log_source_policy(status="success")
    except Exception as error:  # noqa: BLE001 - public live read must degrade cleanly
        stats = _empty_current_match_player_stats_payload()
        source_policy = _build_current_match_admin_log_source_policy(
            status="error",
            error_reason=_public_error_reason(error),
            message=str(error),
        )
    return {
        "status": "ok",
        "data": {
            "server_slug": origin.slug,
            "server_name": origin.display_name,
            **source_policy,
            **stats,
        },
    }


def _empty_current_match_kill_feed_payload() -> dict[str, object]:
    return {
        "scope": "no-current-match-events",
        "confidence": "unavailable",
        "stale_events_filtered": 0,
        "items": [],
    }


def _empty_current_match_player_stats_payload() -> dict[str, object]:
    return {
        "scope": "no-current-match-events",
        "confidence": "unavailable",
        "source": "rcon-admin-log-current-match-summary",
        "updated_at": None,
        "stale_events_filtered": 0,
        "items": [],
    }


def _build_current_match_admin_log_source_policy(
    *,
    status: str,
    error_reason: str | None = None,
    message: str | None = None,
) -> dict[str, object]:
    return build_source_policy(
        primary_source=SOURCE_KIND_RCON,
        selected_source="rcon-admin-log",
        fallback_used=status != "success",
        fallback_reason=error_reason,
        source_attempts=[
            build_source_attempt(
                source="rcon-admin-log",
                role="read-model",
                status=status,
                reason=error_reason,
                message=message,
            )
        ],
    )


def _public_error_reason(error: Exception) -> str:
    if isinstance(error, FileNotFoundError):
        return "admin-log-read-model-unavailable"
    if isinstance(error, TimeoutError):
        return "admin-log-read-timeout"
    message = str(error).lower()
    if "timeout" in message or "timed out" in message:
        return "admin-log-read-timeout"
    if "does not exist" in message or "no such table" in message:
        return "admin-log-read-model-unavailable"
    return "admin-log-read-failed"


def _query_current_match_rcon_sample(server_slug: str) -> dict[str, object] | None:
    """Read one configured trusted RCON target for the current-match view."""
    try:
        targets = load_rcon_targets()
    except (RuntimeError, ValueError):
        return None
    target = next(
        (candidate for candidate in targets if candidate.external_server_id == server_slug),
        None,
    )
    if target is None:
        return None
    try:
        return query_live_server_sample(target)
    except Exception:  # noqa: BLE001 - fall back to the existing live snapshot read
        return None


def _utc_timestamp_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _to_iso_or_none(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _normalize_public_server_id(server_id: str | None) -> str:
    normalized = str(server_id or "").strip().lower()
    if not normalized or normalized == "all":
        return ALL_SERVERS_SLUG
    return str(server_id).strip()


def _serialize_public_server_id(server_id: object) -> str:
    normalized = str(server_id or "").strip()
    if not normalized or normalized == ALL_SERVERS_SLUG:
        return "all"
    return normalized


def _normalize_global_ranking_items(items: object) -> list[dict[str, object]]:
    normalized_items: list[dict[str, object]] = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        matches_considered = int(item.get("matches_considered") or 0)
        kills = int(item.get("kills") or 0)
        normalized_items.append(
            {
                "ranking_position": int(item.get("ranking_position") or 0),
                "player_id": item.get("player_id"),
                "player_name": item.get("player_name"),
                "metric_value": _coerce_public_metric_value(item.get("metric_value")),
                "matches_considered": matches_considered,
                "kills": kills,
                "deaths": int(item.get("deaths") or 0),
                "teamkills": int(item.get("teamkills") or 0),
                "kd_ratio": float(item.get("kd_ratio") or 0.0),
                "kills_per_match": float(
                    item.get("kills_per_match")
                    if item.get("kills_per_match") is not None
                    else round(kills / matches_considered, 2) if matches_considered else 0.0
                ),
            }
        )
    return normalized_items


def _coerce_public_metric_value(value: object) -> int | float:
    try:
        numeric = float(value or 0)
    except (TypeError, ValueError):
        return 0
    if numeric.is_integer():
        return int(numeric)
    return round(numeric, 2)


def _source_when_present(*values: object, source: str) -> str | None:
    return source if any(value is not None for value in values) else None


def _snapshot_player_count_quality(item: dict[str, object] | None) -> str | None:
    if item is None or item.get("players") is None:
        return None
    if item.get("snapshot_origin") == "real-rcon":
        return "rcon-session-unverified"
    if item.get("snapshot_origin") == "real-a2s":
        return "a2s-query"
    return "snapshot-unverified"


def _snapshot_player_count_source(item: dict[str, object] | None) -> str | None:
    if item is None or item.get("players") is None:
        return None
    if item.get("snapshot_origin") == "real-rcon":
        return "rcon-session"
    if item.get("snapshot_origin") == "real-a2s":
        return "a2s"
    return "live-server-snapshot"


def build_error_payload(message: str) -> dict[str, str]:
    """Return the shared error payload shape used by the backend bootstrap."""
    return {
        "status": "error",
        "message": message,
    }


def build_weekly_top_kills_payload(
    *,
    limit: int = 10,
    server_id: str | None = None,
) -> dict[str, object]:
    """Return weekly top kills grouped by real community server."""
    result = list_weekly_top_kills(limit=limit, server_id=server_id)
    return {
        "status": "ok",
        "data": {
            "title": "Top kills semanales por servidor",
            "context": "historical-top-kills",
            "metric": "kills",
            "summary_basis": "closed-matches-last-7-days",
            "window_days": 7,
            "window_start": result["window_start"],
            "window_end": result["window_end"],
            "limit": limit,
            **_resolve_historical_fallback_policy(
                fallback_reason="rcon-historical-read-model-does-not-support-weekly-top-kills",
            ),
            "items": result["items"],
        },
    }


def build_historical_leaderboard_payload(
    *,
    limit: int = 10,
    server_id: str | None = None,
    metric: str = "kills",
    timeframe: str = "weekly",
) -> dict[str, object]:
    """Return one historical leaderboard for the requested timeframe and metric."""
    normalized_timeframe = timeframe.strip().lower() if isinstance(timeframe, str) else "weekly"
    if normalized_timeframe == "monthly":
        result = list_monthly_leaderboard(limit=limit, server_id=server_id, metric=metric)
        summary_basis = "closed-matches-calendar-month"
        context = "historical-monthly-leaderboard"
    else:
        normalized_timeframe = "weekly"
        result = list_weekly_leaderboard(limit=limit, server_id=server_id, metric=metric)
        summary_basis = "closed-matches-calendar-week"
        context = "historical-weekly-leaderboard"

    is_all_servers = server_id == ALL_SERVERS_SLUG
    return {
        "status": "ok",
        "data": {
            "title": _build_leaderboard_title(
                metric=metric,
                timeframe=normalized_timeframe,
                is_all_servers=is_all_servers,
            ),
            "context": context,
            "timeframe": normalized_timeframe,
            "metric": metric,
            "summary_basis": summary_basis,
            "window_days": result.get("window_days", 7),
            "window_start": result["window_start"],
            "window_end": result["window_end"],
            "window_kind": result.get("window_kind"),
            "window_label": result.get("window_label"),
            "uses_fallback": bool(result.get("uses_fallback")),
            "selection_reason": result.get("selection_reason"),
            "current_week_start": result.get("current_week_start"),
            "current_week_closed_matches": result.get("current_week_closed_matches"),
            "previous_week_closed_matches": result.get("previous_week_closed_matches"),
            "current_month_start": result.get("current_month_start"),
            "current_month_closed_matches": result.get("current_month_closed_matches"),
            "previous_month_closed_matches": result.get("previous_month_closed_matches"),
            "sufficient_sample": result.get("sufficient_sample"),
            "limit": limit,
            **_resolve_historical_fallback_policy(
                fallback_reason="rcon-historical-read-model-does-not-support-competitive-leaderboards",
            ),
            "items": result["items"],
        },
    }


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
            "weekly_ranking": result.get("weekly_ranking"),
            "monthly_ranking": result.get("monthly_ranking"),
            "source": result.get("source"),
        },
    }


def build_annual_ranking_snapshot_payload(
    *,
    year: int,
    server_id: str | None = None,
    metric: str = "kills",
    limit: int = 20,
) -> dict[str, object]:
    """Return an annual ranking payload from precomputed snapshots."""
    result = get_annual_ranking_snapshot(
        year=year,
        server_key=server_id,
        metric=metric,
        limit=limit,
    )
    items = result.get("items") or []
    return {
        "status": "ok",
        "data": {
            "year": result.get("year"),
            "server_id": result.get("server_id"),
            "metric": result.get("metric"),
            "limit": result.get("limit"),
            "requested_limit": result.get("requested_limit"),
            "effective_limit": result.get("effective_limit"),
            "snapshot_limit": result.get("snapshot_limit"),
            "item_count": result.get("item_count"),
            "source": result.get("source"),
            "snapshot_status": result.get("snapshot_status"),
            "generated_at": result.get("generated_at"),
            "window_start": result.get("window_start"),
            "window_end": result.get("window_end"),
            "source_matches_count": int(result.get("source_matches_count") or 0),
            "items": [
                {
                    "ranking_position": int(item.get("ranking_position") or 0),
                    "player_id": item.get("player_id"),
                    "player_name": item.get("player_name"),
                    "metric_value": _coerce_public_metric_value(item.get("metric_value")),
                    "matches_considered": int(item.get("matches_considered") or 0),
                    "kills": int(item.get("kills") or 0),
                    "deaths": int(item.get("deaths") or 0),
                    "teamkills": int(item.get("teamkills") or 0),
                    "kd_ratio": float(item.get("kd_ratio") or 0.0),
                    "kills_per_match": (
                        float(item.get("kills_per_match"))
                        if item.get("kills_per_match") is not None
                        else (
                            round(
                                int(item.get("kills") or 0)
                                / int(item.get("matches_considered") or 0),
                                2,
                            )
                            if int(item.get("matches_considered") or 0) > 0
                            else 0.0
                        )
                    ),
                }
                for item in items
                if isinstance(item, dict)
            ],
        },
    }


def build_global_ranking_payload(
    *,
    timeframe: str = "weekly",
    server_id: str | None = None,
    metric: str = "kills",
    limit: int = 20,
    year: int | None = None,
) -> dict[str, object]:
    """Return the dedicated Ranking page payload without changing Stats contracts."""
    normalized_timeframe = str(timeframe or "weekly").strip().lower()
    normalized_server_id = _normalize_public_server_id(server_id)

    if normalized_timeframe == "annual":
        if year is None:
            raise ValueError("year is required when timeframe=annual")
        result = get_annual_ranking_snapshot(
            year=year,
            server_key=normalized_server_id,
            metric=metric,
            limit=limit,
        )
        return {
            "status": "ok",
            "data": {
                "page_kind": "global-ranking",
                "title": "Ranking global anual",
                "context": "global-ranking-annual",
                "timeframe": "annual",
                "server_id": _serialize_public_server_id(result.get("server_id")),
                "metric": result.get("metric"),
                "limit": int(result.get("limit") or 0),
                "requested_limit": int(result.get("requested_limit") or 0),
                "effective_limit": int(result.get("effective_limit") or 0),
                "year": int(result.get("year") or year),
                "window_start": result.get("window_start"),
                "window_end": result.get("window_end"),
                "window_kind": "annual-snapshot",
                "window_label": "Anual",
                "snapshot_status": result.get("snapshot_status"),
                "generated_at": result.get("generated_at"),
                "freshness": (
                    "snapshot" if result.get("snapshot_status") == "ready" else "missing"
                ),
                "fallback_used": False,
                "snapshot_limit": result.get("snapshot_limit"),
                "item_count": int(result.get("item_count") or 0),
                "source_matches_count": int(result.get("source_matches_count") or 0),
                "source": {
                    "primary_source": "rcon",
                    "read_model": "rcon-annual-ranking-snapshot",
                    "generated_at": result.get("generated_at"),
                    "freshness": (
                        "snapshot" if result.get("snapshot_status") == "ready" else "missing"
                    ),
                },
                "items": _normalize_global_ranking_items(result.get("items")),
            },
        }

    snapshot_result = get_latest_ranking_snapshot(
        server_key=normalized_server_id,
        timeframe=normalized_timeframe,
        metric=metric,
        limit=limit,
    )
    if snapshot_result.get("snapshot_status") == "ready":
        return {
            "status": "ok",
            "data": {
                "page_kind": "global-ranking",
                "title": "Ranking global",
                "context": f"global-ranking-{normalized_timeframe}",
                "timeframe": normalized_timeframe,
                "server_id": _serialize_public_server_id(snapshot_result.get("server_id")),
                "metric": snapshot_result.get("metric"),
                "limit": int(snapshot_result.get("limit") or 0),
                "requested_limit": int(snapshot_result.get("requested_limit") or limit),
                "effective_limit": int(snapshot_result.get("effective_limit") or 0),
                "window_start": snapshot_result.get("window_start"),
                "window_end": snapshot_result.get("window_end"),
                "window_kind": snapshot_result.get("window_kind"),
                "window_label": snapshot_result.get("window_label"),
                "snapshot_status": "ready",
                "generated_at": snapshot_result.get("generated_at"),
                "freshness": snapshot_result.get("freshness") or "fresh",
                "fallback_used": False,
                "source_matches_count": int(snapshot_result.get("source_matches_count") or 0),
                "source": {
                    "primary_source": "rcon",
                    "read_model": "ranking-snapshot",
                    "snapshot_source": snapshot_result.get("source"),
                    "generated_at": snapshot_result.get("generated_at"),
                    "freshness": snapshot_result.get("freshness") or "fresh",
                },
                "items": _normalize_global_ranking_items(snapshot_result.get("items")),
            },
        }

    runtime_fallback_enabled = is_ranking_runtime_fallback_enabled()
    if not runtime_fallback_enabled:
        return {
            "status": "ok",
            "data": {
                "page_kind": "global-ranking",
                "title": "Ranking global",
                "context": f"global-ranking-{normalized_timeframe}",
                "timeframe": normalized_timeframe,
                "server_id": _serialize_public_server_id(snapshot_result.get("server_id")),
                "metric": snapshot_result.get("metric"),
                "limit": int(snapshot_result.get("limit") or limit),
                "requested_limit": int(snapshot_result.get("requested_limit") or limit),
                "effective_limit": int(snapshot_result.get("effective_limit") or 0),
                "window_start": snapshot_result.get("window_start"),
                "window_end": snapshot_result.get("window_end"),
                "window_kind": snapshot_result.get("window_kind"),
                "window_label": snapshot_result.get("window_label"),
                "snapshot_status": "missing",
                "generated_at": None,
                "freshness": "missing",
                "fallback_used": False,
                "source_matches_count": 0,
                "source": {
                    "primary_source": "rcon",
                    "read_model": "ranking-snapshot",
                    "snapshot_source": snapshot_result.get("source"),
                    "generated_at": None,
                    "freshness": "missing",
                },
                "items": [],
            },
        }

    result = list_rcon_materialized_leaderboard(
        server_key=normalized_server_id,
        timeframe=normalized_timeframe,
        metric=metric,
        limit=limit,
    )
    return {
        "status": "ok",
        "data": {
            "page_kind": "global-ranking",
            "title": "Ranking global",
            "context": f"global-ranking-{normalized_timeframe}",
            "timeframe": normalized_timeframe,
            "server_id": _serialize_public_server_id(result.get("server_key")),
            "metric": result.get("metric"),
            "limit": int(result.get("limit") or limit),
            "requested_limit": int(limit),
            "effective_limit": int(result.get("limit") or limit),
            "window_start": result.get("window_start"),
            "window_end": result.get("window_end"),
            "window_kind": result.get("window_kind"),
            "window_label": result.get("window_label"),
            "selection_reason": result.get("selection_reason"),
            "snapshot_status": "missing",
            "generated_at": None,
            "freshness": "runtime",
            "fallback_used": True,
            "source": {
                "primary_source": "rcon",
                "read_model": "rcon-materialized-admin-log-leaderboard",
                "snapshot_source": "ranking-snapshot",
                "generated_at": _utc_timestamp_now(),
                "freshness": "runtime",
            },
            "items": _normalize_global_ranking_items(result.get("items")),
        },
    }


def build_weekly_leaderboard_payload(
    *,
    limit: int = 10,
    server_id: str | None = None,
    metric: str = "kills",
) -> dict[str, object]:
    """Return one weekly historical leaderboard for the requested metric."""
    return build_historical_leaderboard_payload(
        limit=limit,
        server_id=server_id,
        metric=metric,
        timeframe="weekly",
    )


def build_monthly_leaderboard_payload(
    *,
    limit: int = 10,
    server_id: str | None = None,
    metric: str = "kills",
) -> dict[str, object]:
    """Return one monthly historical leaderboard for the requested metric."""
    return build_historical_leaderboard_payload(
        limit=limit,
        server_id=server_id,
        metric=metric,
        timeframe="monthly",
    )


def build_recent_historical_matches_payload(
    *,
    limit: int = 20,
    server_slug: str | None = None,
) -> dict[str, object]:
    """Return recent historical matches from persisted CRCON data."""
    if get_historical_data_source_kind() == "rcon":
        data_source = get_rcon_historical_read_model()
        if data_source is not None:
            capabilities = data_source.describe_capabilities()
            try:
                items = data_source.list_recent_activity(server_key=server_slug, limit=limit)
            except Exception as error:  # noqa: BLE001 - explicit runtime fallback boundary
                items = []
                rcon_source_policy = build_historical_runtime_source_policy(
                    operation="historical-recent-matches",
                    rcon_status="error",
                    fallback_reason="rcon-historical-read-model-request-failed",
                    rcon_message=str(error),
                )
            else:
                rcon_source_policy = build_historical_runtime_source_policy(
                    operation="historical-recent-matches",
                    rcon_status=(
                        "success"
                        if data_source.has_recent_activity_coverage(items)
                        else "empty"
                    ),
                    fallback_reason="rcon-historical-read-model-has-no-recent-activity",
                )

            if not bool(rcon_source_policy.get("fallback_used")):
                if 0 < len(items) < limit and not _recent_items_include_rcon_results(items):
                    fallback_items = [
                        _with_recent_result_source(item, "public-scoreboard-fallback")
                        for item in list_recent_historical_matches(
                            limit=limit,
                            server_slug=server_slug,
                        )
                    ]
                    merged_items = _merge_recent_match_items(
                        primary_items=items,
                        fallback_items=fallback_items,
                        limit=limit,
                    )
                    if len(merged_items) > len(items):
                        return {
                            "status": "ok",
                            "data": {
                                "title": "Actividad competitiva reciente capturada por RCON",
                                "context": "historical-recent-matches",
                                "source": "hybrid-rcon-plus-public-scoreboard",
                                "historical_data_source": "rcon",
                                "supported": True,
                                "coverage_basis": "rcon-competitive-windows-plus-public-scoreboard-fallback",
                                "limit": limit,
                                "server_slug": server_slug,
                                **build_source_policy(
                                    primary_source=SOURCE_KIND_RCON,
                                    selected_source="hybrid-rcon-plus-public-scoreboard",
                                    fallback_used=True,
                                    fallback_reason=(
                                        "rcon-historical-recent-matches-did-not-reach-requested-limit"
                                    ),
                                    source_attempts=[
                                        build_source_attempt(
                                            source=SOURCE_KIND_RCON,
                                            role="primary",
                                            status="success",
                                            reason="historical-recent-matches-served-by-rcon",
                                        ),
                                        build_source_attempt(
                                            source=SOURCE_KIND_PUBLIC_SCOREBOARD,
                                            role="fallback",
                                            status="success",
                                            reason="historical-recent-matches-completed-from-public-scoreboard",
                                            message=(
                                                f"RCON returned {len(items)} items, completed to "
                                                f"{len(merged_items)} of requested {limit}."
                                            ),
                                        ),
                                    ],
                                ),
                                "items": merged_items,
                                "capabilities": capabilities,
                            },
                        }
                return {
                    "status": "ok",
                    "data": {
                        "title": "Actividad competitiva reciente capturada por RCON",
                        "context": "historical-recent-matches",
                        "source": "rcon-historical-competitive-read-model",
                        "historical_data_source": "rcon",
                        "supported": True,
                        "coverage_basis": "rcon-competitive-windows",
                        "limit": limit,
                        "server_slug": server_slug,
                        **rcon_source_policy,
                        "items": items,
                        "capabilities": capabilities,
                    },
                }
    items = [
        _with_recent_result_source(item, "public-scoreboard-fallback")
        for item in list_recent_historical_matches(limit=limit, server_slug=server_slug)
    ]
    return {
        "status": "ok",
        "data": {
            "title": "Partidas recientes por servidor",
            "context": "historical-recent-matches",
            "source": "historical-crcon-storage",
            "limit": limit,
            "server_slug": server_slug,
            **(
                rcon_source_policy
                if get_historical_data_source_kind() == "rcon"
                and "rcon_source_policy" in locals()
                else _resolve_historical_fallback_policy(
                    fallback_reason="rcon-historical-read-model-has-no-recent-activity",
                )
            ),
            "items": items,
        },
    }


def build_historical_match_detail_payload(
    *,
    server_slug: str,
    match_id: str,
) -> dict[str, object]:
    """Return available detail for one historical match without inventing external URLs."""
    if get_historical_data_source_kind() == SOURCE_KIND_RCON:
        item = get_rcon_historical_match_detail(
            server_key=server_slug,
            match_id=match_id,
        )
        if item is not None:
            return {
                "status": "ok",
                "data": {
                    "title": "Detalle de partida historica",
                    "context": "historical-match-detail",
                    "source": "rcon-historical-competitive-read-model",
                    "found": True,
                    **build_source_policy(
                        primary_source=SOURCE_KIND_RCON,
                        selected_source=SOURCE_KIND_RCON,
                        source_attempts=[
                            build_source_attempt(
                                source=SOURCE_KIND_RCON,
                                role="primary",
                                status="success",
                                reason="historical-match-detail-served-by-rcon",
                            )
                        ],
                    ),
                    "item": item,
                },
            }
        return {
            "status": "ok",
            "data": {
                "title": "Detalle de partida historica",
                "context": "historical-match-detail",
                "source": "rcon-historical-competitive-read-model",
                "found": False,
                **build_source_policy(
                    primary_source=SOURCE_KIND_RCON,
                    selected_source=SOURCE_KIND_RCON,
                    fallback_used=False,
                    fallback_reason=None,
                    source_attempts=[
                        build_source_attempt(
                            source=SOURCE_KIND_RCON,
                            role="primary",
                            status="empty",
                            reason="historical-match-detail-read-model-missing",
                        )
                    ],
                ),
                "item": None,
            },
        }

    item = get_historical_match_detail(server_slug=server_slug, match_id=match_id)
    return {
        "status": "ok",
        "data": {
            "title": "Detalle de partida historica",
            "context": "historical-match-detail",
            "source": "historical-crcon-storage",
            "found": item is not None,
            **(
                _resolve_historical_fallback_policy(
                    fallback_reason="rcon-historical-read-model-has-no-match-detail"
                )
                if get_historical_data_source_kind() == SOURCE_KIND_RCON
                else build_source_policy(
                    primary_source=SOURCE_KIND_PUBLIC_SCOREBOARD,
                    selected_source=SOURCE_KIND_PUBLIC_SCOREBOARD,
                    source_attempts=[
                        build_source_attempt(
                            source=SOURCE_KIND_PUBLIC_SCOREBOARD,
                            role="primary",
                            status="success" if item is not None else "empty",
                            reason="historical-match-detail-served-by-public-scoreboard",
                        )
                    ],
                )
            ),
            "item": item,
        },
    }


def build_monthly_mvp_payload(
    *,
    limit: int = 10,
    server_id: str | None = None,
) -> dict[str, object]:
    """Return the precomputed monthly MVP payload through the stable API surface."""
    snapshot_payload = build_monthly_mvp_snapshot_payload(
        limit=limit,
        server_id=server_id,
    )
    data = snapshot_payload["data"]
    return {
        "status": "ok",
        "data": {
            **data,
            "title": _build_monthly_mvp_title(
                is_all_servers=server_id == ALL_SERVERS_SLUG,
                snapshot=False,
            ),
            "context": "historical-monthly-mvp",
            "source": "historical-precomputed-snapshots",
            **_resolve_historical_fallback_policy(
                fallback_reason="rcon-historical-read-model-does-not-support-monthly-mvp-yet",
            ),
        },
    }


def build_player_event_payload(
    *,
    limit: int = 10,
    server_id: str | None = None,
    view: str = "most-killed",
) -> dict[str, object]:
    """Return one V2 player-event payload through the stable API surface."""
    snapshot_payload = build_player_event_snapshot_payload(
        limit=limit,
        server_id=server_id,
        view=view,
    )
    data = snapshot_payload["data"]
    return {
        "status": "ok",
        "data": {
            **data,
            "title": _build_player_event_title(
                view=view,
                is_all_servers=server_id == ALL_SERVERS_SLUG,
                snapshot=False,
            ),
            "context": "historical-player-events",
            "source": "historical-precomputed-player-event-snapshots",
            **_resolve_historical_fallback_policy(
                fallback_reason="rcon-historical-read-model-does-not-support-player-events-yet",
            ),
        },
    }


def build_monthly_mvp_v2_payload(
    *,
    limit: int = 10,
    server_id: str | None = None,
) -> dict[str, object]:
    """Return the precomputed monthly MVP V2 payload through the stable API surface."""
    snapshot_payload = build_monthly_mvp_v2_snapshot_payload(
        limit=limit,
        server_id=server_id,
    )
    data = snapshot_payload["data"]
    return {
        "status": "ok",
        "data": {
            **data,
            "title": _build_monthly_mvp_v2_title(
                is_all_servers=server_id == ALL_SERVERS_SLUG,
                snapshot=False,
            ),
            "context": "historical-monthly-mvp-v2",
            "source": "historical-precomputed-snapshots",
            **_resolve_historical_fallback_policy(
                fallback_reason="rcon-historical-read-model-does-not-support-monthly-mvp-v2-yet",
            ),
        },
    }


def build_historical_server_summary_snapshot_payload(
    *,
    server_slug: str | None = None,
) -> dict[str, object]:
    """Return one precomputed summary snapshot without recalculating aggregates."""
    snapshot = _get_historical_snapshot_record(
        server_key=server_slug,
        snapshot_type=SNAPSHOT_TYPE_SERVER_SUMMARY,
        window=DEFAULT_SNAPSHOT_WINDOW,
    )
    payload = snapshot.get("payload") if snapshot else {}
    item = payload.get("item") if isinstance(payload, dict) else None
    return {
        "status": "ok",
        "data": {
            "title": "Snapshot historico de resumen por servidor",
            "context": "historical-server-summary-snapshot",
            "source": "historical-precomputed-snapshots",
            "server_slug": server_slug,
            "found": snapshot is not None and isinstance(item, dict),
            **(
                build_source_policy(
                    primary_source=SOURCE_KIND_RCON,
                    selected_source=SOURCE_KIND_RCON,
                    source_attempts=[
                        build_source_attempt(
                            source=SOURCE_KIND_RCON,
                            role="primary",
                            status="success",
                            reason="server-summary-snapshot-served-by-rcon-competitive-model",
                        )
                    ],
                )
                if get_historical_data_source_kind() == SOURCE_KIND_RCON and isinstance(item, dict)
                else _resolve_historical_fallback_policy(
                    fallback_reason="rcon-historical-read-model-does-not-support-historical-snapshots-yet",
                )
            ),
            **_build_historical_snapshot_metadata(snapshot),
            "item": item if isinstance(item, dict) else None,
        },
    }


def build_leaderboard_snapshot_payload(
    *,
    limit: int = 10,
    server_id: str | None = None,
    metric: str = "kills",
    timeframe: str = "weekly",
) -> dict[str, object]:
    """Return one precomputed leaderboard snapshot for the requested timeframe."""
    normalized_timeframe = timeframe.strip().lower() if isinstance(timeframe, str) else "weekly"
    if normalized_timeframe == "monthly":
        snapshot_type = SNAPSHOT_TYPE_MONTHLY_LEADERBOARD
        window = DEFAULT_MONTHLY_SNAPSHOT_WINDOW
        context = "historical-monthly-leaderboard-snapshot"
    else:
        normalized_timeframe = "weekly"
        snapshot_type = SNAPSHOT_TYPE_WEEKLY_LEADERBOARD
        window = DEFAULT_WEEKLY_SNAPSHOT_WINDOW
        context = "historical-weekly-leaderboard-snapshot"

    snapshot = _get_historical_snapshot_record(
        server_key=server_id,
        snapshot_type=snapshot_type,
        metric=metric,
        window=window,
    )
    payload = snapshot.get("payload") if snapshot else {}
    items = payload.get("items") if isinstance(payload, dict) else None
    sliced_items = list(items[:limit]) if isinstance(items, list) else []
    is_all_servers = server_id == ALL_SERVERS_SLUG
    return {
        "status": "ok",
        "data": {
            "title": _build_leaderboard_title(
                metric=metric,
                timeframe=normalized_timeframe,
                is_all_servers=is_all_servers,
                snapshot=True,
            ),
            "context": context,
            "source": "historical-precomputed-snapshots",
            "server_slug": server_id,
            "timeframe": normalized_timeframe,
            "metric": metric,
            "found": snapshot is not None,
            **_build_historical_snapshot_metadata(snapshot),
            "window_days": payload.get("window_days") if isinstance(payload, dict) else 7,
            "window_start": payload.get("window_start") if isinstance(payload, dict) else None,
            "window_end": payload.get("window_end") if isinstance(payload, dict) else None,
            "window_kind": payload.get("window_kind") if isinstance(payload, dict) else None,
            "window_label": payload.get("window_label") if isinstance(payload, dict) else None,
            "uses_fallback": bool(payload.get("uses_fallback")) if isinstance(payload, dict) else False,
            "selection_reason": payload.get("selection_reason") if isinstance(payload, dict) else None,
            "current_week_start": payload.get("current_week_start") if isinstance(payload, dict) else None,
            "current_week_closed_matches": (
                payload.get("current_week_closed_matches") if isinstance(payload, dict) else None
            ),
            "previous_week_closed_matches": (
                payload.get("previous_week_closed_matches") if isinstance(payload, dict) else None
            ),
            "current_month_start": payload.get("current_month_start") if isinstance(payload, dict) else None,
            "current_month_closed_matches": (
                payload.get("current_month_closed_matches") if isinstance(payload, dict) else None
            ),
            "previous_month_closed_matches": (
                payload.get("previous_month_closed_matches") if isinstance(payload, dict) else None
            ),
            "sufficient_sample": payload.get("sufficient_sample") if isinstance(payload, dict) else None,
            "snapshot_limit": payload.get("limit") if isinstance(payload, dict) else None,
            "limit": limit,
            "runtime_enrichment": {
                "applied": False,
                "reason": "disabled-on-public-snapshot-path",
            },
            **_resolve_historical_fallback_policy(
                fallback_reason="rcon-historical-read-model-does-not-support-historical-snapshots-yet",
            ),
            "items": sliced_items,
        },
    }


def build_weekly_leaderboard_snapshot_payload(
    *,
    limit: int = 10,
    server_id: str | None = None,
    metric: str = "kills",
) -> dict[str, object]:
    """Return one precomputed weekly leaderboard snapshot."""
    return build_leaderboard_snapshot_payload(
        limit=limit,
        server_id=server_id,
        metric=metric,
        timeframe="weekly",
    )


def build_monthly_leaderboard_snapshot_payload(
    *,
    limit: int = 10,
    server_id: str | None = None,
    metric: str = "kills",
) -> dict[str, object]:
    """Return one precomputed monthly leaderboard snapshot."""
    return build_leaderboard_snapshot_payload(
        limit=limit,
        server_id=server_id,
        metric=metric,
        timeframe="monthly",
    )


def build_recent_historical_matches_snapshot_payload(
    *,
    limit: int = 20,
    server_slug: str | None = None,
) -> dict[str, object]:
    """Return one precomputed recent-matches snapshot."""
    snapshot = _get_historical_snapshot_record(
        server_key=server_slug,
        snapshot_type=SNAPSHOT_TYPE_RECENT_MATCHES,
        window=DEFAULT_SNAPSHOT_WINDOW,
    )
    payload = snapshot.get("payload") if snapshot else {}
    items = payload.get("items") if isinstance(payload, dict) else None
    sliced_items = list(items[:limit]) if isinstance(items, list) else []
    return {
        "status": "ok",
        "data": {
            "title": "Snapshot historico de partidas recientes por servidor",
            "context": "historical-recent-matches-snapshot",
            "source": "historical-precomputed-snapshots",
            "server_slug": server_slug,
            "found": snapshot is not None,
            **_build_historical_snapshot_metadata(snapshot),
            "snapshot_limit": payload.get("limit") if isinstance(payload, dict) else None,
            "limit": limit,
            **(
                build_source_policy(
                    primary_source=SOURCE_KIND_RCON,
                    selected_source=SOURCE_KIND_RCON,
                    source_attempts=[
                        build_source_attempt(
                            source=SOURCE_KIND_RCON,
                            role="primary",
                            status="success",
                            reason="recent-matches-snapshot-served-by-rcon-competitive-model",
                        )
                    ],
                )
                if get_historical_data_source_kind() == SOURCE_KIND_RCON and sliced_items
                else _resolve_historical_fallback_policy(
                    fallback_reason="rcon-historical-read-model-does-not-support-historical-snapshots-yet",
                )
            ),
            "items": sliced_items,
        },
    }


def build_monthly_mvp_snapshot_payload(
    *,
    limit: int = 10,
    server_id: str | None = None,
) -> dict[str, object]:
    """Return one precomputed monthly MVP snapshot."""
    snapshot = _get_historical_snapshot_record(
        server_key=server_id,
        snapshot_type=SNAPSHOT_TYPE_MONTHLY_MVP,
        window=DEFAULT_MONTHLY_SNAPSHOT_WINDOW,
    )
    payload = snapshot.get("payload") if snapshot else {}
    items = payload.get("items") if isinstance(payload, dict) else None
    sliced_items = list(items[:limit]) if isinstance(items, list) else []
    return {
        "status": "ok",
        "data": {
            "title": _build_monthly_mvp_title(
                is_all_servers=server_id == ALL_SERVERS_SLUG,
                snapshot=True,
            ),
            "context": "historical-monthly-mvp-snapshot",
            "source": "historical-precomputed-snapshots",
            "server_slug": server_id,
            "timeframe": "monthly",
            "metric": "mvp",
            "found": snapshot is not None,
            **_build_historical_snapshot_metadata(snapshot),
            "month_key": payload.get("month_key") if isinstance(payload, dict) else None,
            "window_days": payload.get("window_days") if isinstance(payload, dict) else None,
            "window_start": payload.get("window_start") if isinstance(payload, dict) else None,
            "window_end": payload.get("window_end") if isinstance(payload, dict) else None,
            "window_kind": payload.get("window_kind") if isinstance(payload, dict) else None,
            "window_label": payload.get("window_label") if isinstance(payload, dict) else None,
            "uses_fallback": bool(payload.get("uses_fallback")) if isinstance(payload, dict) else False,
            "selection_reason": payload.get("selection_reason") if isinstance(payload, dict) else None,
            "current_month_start": payload.get("current_month_start") if isinstance(payload, dict) else None,
            "current_month_closed_matches": (
                payload.get("current_month_closed_matches") if isinstance(payload, dict) else None
            ),
            "previous_month_closed_matches": (
                payload.get("previous_month_closed_matches") if isinstance(payload, dict) else None
            ),
            "sufficient_sample": payload.get("sufficient_sample") if isinstance(payload, dict) else None,
            "eligibility": payload.get("eligibility") if isinstance(payload, dict) else None,
            "ranking_version": payload.get("ranking_version") if isinstance(payload, dict) else None,
            "eligible_players_count": (
                payload.get("eligible_players_count") if isinstance(payload, dict) else 0
            ),
            "snapshot_limit": payload.get("limit") if isinstance(payload, dict) else None,
            "limit": limit,
            **_resolve_historical_fallback_policy(
                fallback_reason="rcon-historical-read-model-does-not-support-historical-snapshots-yet",
            ),
            "items": sliced_items,
        },
    }


def build_monthly_mvp_v2_snapshot_payload(
    *,
    limit: int = 10,
    server_id: str | None = None,
) -> dict[str, object]:
    """Return one precomputed monthly MVP V2 snapshot."""
    snapshot = _get_historical_snapshot_record(
        server_key=server_id,
        snapshot_type=SNAPSHOT_TYPE_MONTHLY_MVP_V2,
        window=DEFAULT_MONTHLY_SNAPSHOT_WINDOW,
    )
    payload = snapshot.get("payload") if snapshot else {}
    items = payload.get("items") if isinstance(payload, dict) else None
    sliced_items = list(items[:limit]) if isinstance(items, list) else []
    found = bool(payload.get("found")) if isinstance(payload, dict) else False
    return {
        "status": "ok",
        "data": {
            "title": _build_monthly_mvp_v2_title(
                is_all_servers=server_id == ALL_SERVERS_SLUG,
                snapshot=True,
            ),
            "context": "historical-monthly-mvp-v2-snapshot",
            "source": "historical-precomputed-snapshots",
            "server_slug": server_id,
            "timeframe": "monthly",
            "metric": "mvp-v2",
            "found": snapshot is not None and found,
            **_build_historical_snapshot_metadata(snapshot),
            "month_key": payload.get("month_key") if isinstance(payload, dict) else None,
            "window_days": payload.get("window_days") if isinstance(payload, dict) else None,
            "window_start": payload.get("window_start") if isinstance(payload, dict) else None,
            "window_end": payload.get("window_end") if isinstance(payload, dict) else None,
            "window_kind": payload.get("window_kind") if isinstance(payload, dict) else None,
            "window_label": payload.get("window_label") if isinstance(payload, dict) else None,
            "uses_fallback": bool(payload.get("uses_fallback")) if isinstance(payload, dict) else False,
            "selection_reason": payload.get("selection_reason") if isinstance(payload, dict) else None,
            "current_month_start": payload.get("current_month_start") if isinstance(payload, dict) else None,
            "current_month_closed_matches": (
                payload.get("current_month_closed_matches") if isinstance(payload, dict) else None
            ),
            "previous_month_closed_matches": (
                payload.get("previous_month_closed_matches") if isinstance(payload, dict) else None
            ),
            "sufficient_sample": payload.get("sufficient_sample") if isinstance(payload, dict) else None,
            "eligibility": payload.get("eligibility") if isinstance(payload, dict) else None,
            "ranking_version": payload.get("ranking_version") if isinstance(payload, dict) else None,
            "event_coverage": payload.get("event_coverage") if isinstance(payload, dict) else None,
            "eligible_players_count": (
                payload.get("eligible_players_count") if isinstance(payload, dict) else 0
            ),
            "snapshot_limit": payload.get("limit") if isinstance(payload, dict) else None,
            "limit": limit,
            **_resolve_historical_fallback_policy(
                fallback_reason="rcon-historical-read-model-does-not-support-historical-snapshots-yet",
            ),
            "items": sliced_items,
        },
    }


def build_player_event_snapshot_payload(
    *,
    limit: int = 10,
    server_id: str | None = None,
    view: str = "most-killed",
) -> dict[str, object]:
    """Return one precomputed V2 player-event snapshot."""
    snapshot_type = _resolve_player_event_snapshot_type(view)
    snapshot = _get_historical_snapshot_record(
        server_key=server_id,
        snapshot_type=snapshot_type,
        window=DEFAULT_MONTHLY_SNAPSHOT_WINDOW,
    )
    payload = snapshot.get("payload") if snapshot else {}
    items = payload.get("items") if isinstance(payload, dict) else None
    sliced_items = list(items[:limit]) if isinstance(items, list) else []
    found = bool(payload.get("found")) if isinstance(payload, dict) else False
    return {
        "status": "ok",
        "data": {
            "title": _build_player_event_title(
                view=view,
                is_all_servers=server_id == ALL_SERVERS_SLUG,
                snapshot=True,
            ),
            "context": "historical-player-events-snapshot",
            "source": "historical-precomputed-player-event-snapshots",
            "server_slug": server_id,
            "timeframe": "monthly",
            "metric": view,
            "found": snapshot is not None and found,
            **_build_historical_snapshot_metadata(snapshot),
            "period": payload.get("period") if isinstance(payload, dict) else "monthly",
            "month_key": payload.get("month_key") if isinstance(payload, dict) else None,
            "snapshot_limit": payload.get("limit") if isinstance(payload, dict) else None,
            "limit": limit,
            **_resolve_historical_fallback_policy(
                fallback_reason="rcon-historical-read-model-does-not-support-historical-snapshots-yet",
            ),
            "items": sliced_items,
        },
    }


def build_historical_server_summary_payload(
    *,
    server_slug: str | None = None,
) -> dict[str, object]:
    """Return aggregated historical metrics per server."""
    if get_historical_data_source_kind() == "rcon":
        data_source = get_rcon_historical_read_model()
        if data_source is not None:
            capabilities = data_source.describe_capabilities()
            try:
                items = data_source.list_server_summaries(server_key=server_slug)
            except Exception as error:  # noqa: BLE001 - explicit runtime fallback boundary
                items = []
                rcon_source_policy = build_historical_runtime_source_policy(
                    operation="historical-server-summary",
                    rcon_status="error",
                    fallback_reason="rcon-historical-read-model-request-failed",
                    rcon_message=str(error),
                )
            else:
                rcon_source_policy = build_historical_runtime_source_policy(
                    operation="historical-server-summary",
                    rcon_status=(
                        "success"
                        if data_source.has_server_summary_coverage(items)
                        else "empty"
                    ),
                    fallback_reason="rcon-historical-read-model-has-no-summary-coverage",
                )

            if not bool(rcon_source_policy.get("fallback_used")):
                return {
                    "status": "ok",
                    "data": {
                        "title": (
                            "Cobertura historica minima por RCON"
                            if server_slug != ALL_SERVERS_SLUG
                            else "Cobertura historica minima RCON agregada"
                        ),
                        "context": "historical-server-summary",
                        "source": "rcon-historical-competitive-read-model",
                        "historical_data_source": "rcon",
                        "summary_basis": "rcon-competitive-windows",
                        "server_slug": server_slug,
                        "supported": True,
                        **rcon_source_policy,
                        "items": items,
                        "capabilities": capabilities,
                    },
                }
    items = list_historical_server_summaries(server_slug=server_slug)
    return {
        "status": "ok",
        "data": {
            "title": (
                "Cobertura historica agregada de todos los servidores"
                if server_slug == ALL_SERVERS_SLUG
                else "Cobertura historica importada por servidor"
            ),
            "context": "historical-server-summary",
            "source": "historical-crcon-storage",
            "summary_basis": "persisted-import",
            "weekly_ranking_window_days": 7,
            "server_slug": server_slug,
            **(
                rcon_source_policy
                if get_historical_data_source_kind() == "rcon"
                and "rcon_source_policy" in locals()
                else _resolve_historical_fallback_policy(
                    fallback_reason="rcon-historical-read-model-has-no-summary-coverage",
                )
            ),
            "items": items,
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


def build_elo_mmr_leaderboard_payload(
    *,
    limit: int = 10,
    server_id: str | None = None,
) -> dict[str, object]:
    """Return the current Elo/MMR monthly leaderboard."""
    engine = _load_elo_mmr_engine()
    if engine is None:
        return _build_elo_mmr_unavailable_payload(
            context="historical-elo-mmr-leaderboard",
            title=(
                "Leaderboard mensual Elo/MMR global"
                if server_id == ALL_SERVERS_SLUG
                else "Leaderboard mensual Elo/MMR por servidor"
            ),
            server_id=server_id,
            limit=limit,
            extra={"items": []},
            operation="elo-mmr-leaderboard",
        )

    list_elo_mmr_leaderboard_payload = engine[1]
    payload = list_elo_mmr_leaderboard_payload(server_id=server_id, limit=limit)
    is_all_servers = server_id == ALL_SERVERS_SLUG
    accuracy_contract = _build_elo_accuracy_contract(payload.get("capabilities_summary"))
    return {
        "status": "ok",
        "data": {
            "title": (
                "Leaderboard mensual Elo/MMR global"
                if is_all_servers
                else "Leaderboard mensual Elo/MMR por servidor"
            ),
            "context": "historical-elo-mmr-leaderboard",
            "source": "elo-mmr-persisted-read-model",
            "server_slug": server_id,
            "month_key": payload.get("month_key"),
            "found": bool(payload.get("found")),
            "generated_at": payload.get("generated_at"),
            "limit": limit,
            **(payload.get("source_policy") or _resolve_historical_fallback_policy(
                operation="elo-mmr-leaderboard",
                fallback_reason="elo-mmr-source-policy-missing",
            )),
            "capabilities_summary": payload.get("capabilities_summary"),
            "accuracy_contract": accuracy_contract,
            "model_contract": _build_elo_model_contract(accuracy_contract),
            "items": [
                _enrich_elo_leaderboard_item(item, accuracy_contract=accuracy_contract)
                for item in (payload.get("items") or [])
                if isinstance(item, dict)
            ],
        },
    }


def build_elo_mmr_player_payload(
    *,
    player_id: str,
    server_id: str | None = None,
) -> dict[str, object]:
    """Return one Elo/MMR player profile."""
    engine = _load_elo_mmr_engine()
    if engine is None:
        return _build_elo_mmr_unavailable_payload(
            context="historical-elo-mmr-player",
            title="Perfil Elo/MMR de jugador",
            server_id=server_id,
            extra={
                "player_id": player_id,
                "found": False,
                "profile": None,
            },
            operation="elo-mmr-player",
        )

    get_elo_mmr_player_payload, list_elo_mmr_leaderboard_payload = engine
    profile = get_elo_mmr_player_payload(player_id=player_id, server_id=server_id)
    source_policy = list_elo_mmr_leaderboard_payload(server_id=server_id, limit=1).get("source_policy")
    accuracy_contract = _build_elo_player_accuracy_contract(profile)
    return {
        "status": "ok",
        "data": {
            "title": "Perfil Elo/MMR de jugador",
            "context": "historical-elo-mmr-player",
            "source": "elo-mmr-persisted-read-model",
            "player_id": player_id,
            "server_slug": server_id,
            "found": profile is not None,
            **(source_policy or _resolve_historical_fallback_policy(
                operation="elo-mmr-player",
                fallback_reason="elo-mmr-player-source-policy-missing",
            )),
            "accuracy_contract": accuracy_contract,
            "model_contract": _build_elo_model_contract(accuracy_contract),
            "profile": _enrich_elo_profile(profile, accuracy_contract=accuracy_contract),
        },
    }


def _load_elo_mmr_engine():
    try:
        from .elo_mmr_engine import (  # noqa: PLC0415 - lazy boundary for paused Elo/MMR
            get_elo_mmr_player_payload,
            list_elo_mmr_leaderboard_payload,
        )
    except ImportError:
        return None
    return get_elo_mmr_player_payload, list_elo_mmr_leaderboard_payload


def _build_elo_mmr_unavailable_payload(
    *,
    context: str,
    title: str,
    server_id: str | None,
    operation: str,
    limit: int | None = None,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    accuracy_contract = _build_elo_accuracy_contract(None)
    data = {
        "title": title,
        "context": context,
        "source": "elo-mmr-paused",
        "server_slug": server_id,
        "available": False,
        "unavailable_reason": "elo-mmr-engine-import-unavailable",
        **_resolve_historical_fallback_policy(
            operation=operation,
            fallback_reason="elo-mmr-operationally-paused",
        ),
        "capabilities_summary": None,
        "accuracy_contract": accuracy_contract,
        "model_contract": _build_elo_model_contract(accuracy_contract),
    }
    if limit is not None:
        data["limit"] = limit
    if extra:
        data.update(extra)
    return {
        "status": "ok",
        "data": data,
    }


def _build_elo_player_accuracy_contract(profile: dict[str, object] | None) -> dict[str, object]:
    if not isinstance(profile, dict):
        return _build_elo_accuracy_contract(None)
    monthly_ranking = profile.get("monthly_ranking")
    if isinstance(monthly_ranking, dict) and isinstance(monthly_ranking.get("capabilities"), dict):
        return _build_elo_accuracy_contract(monthly_ranking.get("capabilities"))
    persistent_rating = profile.get("persistent_rating")
    if isinstance(persistent_rating, dict) and isinstance(persistent_rating.get("capabilities"), dict):
        return _build_elo_accuracy_contract(persistent_rating.get("capabilities"))
    return _build_elo_accuracy_contract(None)


def _build_elo_accuracy_contract(summary: dict[str, object] | None) -> dict[str, object]:
    capabilities = summary if isinstance(summary, dict) else {}
    signals = capabilities.get("signals")
    normalized_signals = [signal for signal in signals if isinstance(signal, dict)] if isinstance(signals, list) else []
    component_status = {
        str(signal.get("name") or "").strip(): signal.get("status")
        for signal in normalized_signals
        if str(signal.get("name") or "").strip()
    }
    return {
        "accuracy_mode": capabilities.get("accuracy_mode") or "unknown",
        "exact_ratio": capabilities.get("exact_ratio"),
        "approximate_ratio": capabilities.get("approximate_ratio"),
        "not_available_ratio": capabilities.get("unavailable_ratio"),
        "component_status": component_status,
        "blocked_components": [
            name for name, status in component_status.items() if status == "not_available"
        ],
        "explanation": {
            "exact": "computed from persisted repository signals without proxy substitution",
            "approximate": "computed with explicit proxies because the ideal telemetry is not stored yet",
            "not_available": "not computable yet with the current repository telemetry",
        },
    }


def _build_elo_model_contract(accuracy_contract: dict[str, object]) -> dict[str, object]:
    blocked_components = accuracy_contract.get("blocked_components")
    return {
        "persistent_rating": {
            "meaning": "long-lived competitive rating rebuilt from persisted matches for the selected scope",
            "primary_field": "persistent_rating.mmr",
        },
        "monthly_rank_score": {
            "meaning": "monthly leaderboard ordering score that combines rating movement, match quality, activity and confidence",
            "primary_field": "monthly_rank_score",
        },
        "elo_core": {
            "meaning": "competitive rating movement driven by expected-vs-actual outcome against opponent rating pressure",
            "fields": ["components.elo_core_gain"],
        },
        "performance_modifiers": {
            "meaning": "bounded HLL-specific adjustments layered on top of the competitive Elo core",
            "fields": [
                "components.performance_modifier_gain",
                "components.proxy_modifier_gain",
            ],
        },
        "proxy_boundary": {
            "meaning": "subset of modifier logic that still depends on approximate signals such as role, objective, schedule or discipline proxies",
            "blocked_by_telemetry": blocked_components if isinstance(blocked_components, list) else [],
        },
    }


def _enrich_elo_leaderboard_item(
    item: dict[str, object],
    *,
    accuracy_contract: dict[str, object],
) -> dict[str, object]:
    enriched = dict(item)
    components = item.get("components") if isinstance(item.get("components"), dict) else {}
    persistent_rating = item.get("persistent_rating") if isinstance(item.get("persistent_rating"), dict) else {}
    delta_breakdown = _resolve_elo_delta_sources(
        components,
        persistent_rating=persistent_rating,
    )
    enriched["rating_breakdown"] = {
        "persistent_rating": {
            "mmr": persistent_rating.get("mmr"),
            "baseline_mmr": persistent_rating.get("baseline_mmr"),
            "net_mmr_gain": persistent_rating.get("mmr_gain"),
        },
        "monthly_ranking": {
            "score": item.get("monthly_rank_score"),
            "valid_matches": item.get("valid_matches"),
            "confidence": components.get("confidence"),
        },
        "delta_sources": delta_breakdown["values"],
        "materialization": delta_breakdown["materialization"],
        "telemetry_boundary": {
            "approximate_ratio": accuracy_contract.get("approximate_ratio"),
            "blocked_components": accuracy_contract.get("blocked_components") or [],
        },
    }
    return enriched


def _enrich_elo_profile(
    profile: dict[str, object] | None,
    *,
    accuracy_contract: dict[str, object],
) -> dict[str, object] | None:
    if not isinstance(profile, dict):
        return profile
    enriched = dict(profile)
    monthly_ranking = dict(profile.get("monthly_ranking")) if isinstance(profile.get("monthly_ranking"), dict) else None
    if monthly_ranking is not None:
        components = monthly_ranking.get("components") if isinstance(monthly_ranking.get("components"), dict) else {}
        delta_breakdown = _resolve_elo_delta_sources(
            components,
            persistent_rating={
                "mmr_gain": monthly_ranking.get("mmr_gain"),
                "baseline_mmr": monthly_ranking.get("baseline_mmr"),
                "mmr": monthly_ranking.get("current_mmr"),
            },
        )
        monthly_ranking["rating_breakdown"] = {
            "monthly_rank_score": monthly_ranking.get("monthly_rank_score"),
            "current_mmr": monthly_ranking.get("current_mmr"),
            "baseline_mmr": monthly_ranking.get("baseline_mmr"),
            "net_mmr_gain": monthly_ranking.get("mmr_gain"),
            "elo_core_gain": delta_breakdown["values"]["elo_core_gain"],
            "performance_modifier_gain": delta_breakdown["values"]["performance_modifier_gain"],
            "proxy_modifier_gain": delta_breakdown["values"]["proxy_modifier_gain"],
            "confidence": components.get("confidence"),
            "avg_participation_ratio": components.get("avg_participation_ratio"),
            "materialization": delta_breakdown["materialization"],
        }
        enriched["monthly_ranking"] = monthly_ranking
    persistent_rating = dict(profile.get("persistent_rating")) if isinstance(profile.get("persistent_rating"), dict) else None
    if persistent_rating is not None:
        persistent_rating["meaning"] = "persistent competitive rating for the selected scope"
        enriched["persistent_rating"] = persistent_rating
    enriched["telemetry_boundary"] = {
        "accuracy_mode": accuracy_contract.get("accuracy_mode"),
        "blocked_components": accuracy_contract.get("blocked_components") or [],
    }
    return enriched


def _resolve_elo_delta_sources(
    components: dict[str, object],
    *,
    persistent_rating: dict[str, object] | None,
) -> dict[str, object]:
    elo_core_gain = _coerce_optional_float(components.get("elo_core_gain"))
    performance_modifier_gain = _coerce_optional_float(components.get("performance_modifier_gain"))
    proxy_modifier_gain = _coerce_optional_float(components.get("proxy_modifier_gain"))
    if (
        elo_core_gain is not None
        or performance_modifier_gain is not None
        or proxy_modifier_gain is not None
    ):
        return {
            "values": {
                "elo_core_gain": elo_core_gain,
                "performance_modifier_gain": performance_modifier_gain,
                "proxy_modifier_gain": proxy_modifier_gain,
            },
            "materialization": {
                "status": "v3-materialized",
                "reason": "persisted-monthly-ranking-includes-v3-delta-sources",
                "delta_sources_accuracy": "exact-or-proxy-as-persisted",
            },
        }

    legacy_net_gain = _coerce_optional_float(components.get("mmr_gain_raw"))
    if legacy_net_gain is None and isinstance(persistent_rating, dict):
        legacy_net_gain = _coerce_optional_float(persistent_rating.get("mmr_gain"))
    if legacy_net_gain is None:
        return {
            "values": {
                "elo_core_gain": None,
                "performance_modifier_gain": None,
                "proxy_modifier_gain": None,
            },
            "materialization": {
                "status": "v3-delta-sources-unavailable",
                "reason": (
                    "persisted-monthly-ranking-predates-v3-delta-split-and-has-no-compatible-net-gain"
                ),
                "delta_sources_accuracy": "not_available",
            },
        }

    return {
        "values": {
            "elo_core_gain": legacy_net_gain,
            "performance_modifier_gain": 0.0,
            "proxy_modifier_gain": 0.0,
        },
        "materialization": {
            "status": "legacy-compatibility-approximation",
            "reason": (
                "persisted-monthly-ranking-predates-v3-delta-split-api-approximates-delta-sources-"
                "from-legacy-net-mmr-gain"
            ),
            "delta_sources_accuracy": "approximate",
        },
    }


def _coerce_optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 3)
    except (TypeError, ValueError):
        return None


def _leaderboard_snapshot_items_need_playtime_enrichment(items: list[object]) -> bool:
    normalized_items = [item for item in items if isinstance(item, dict)]
    if not normalized_items:
        return False
    return any("total_time_seconds" not in item for item in normalized_items)


def _load_runtime_leaderboard_items(
    *,
    limit: int,
    server_id: str | None,
    metric: str,
    timeframe: str,
) -> list[dict[str, object]]:
    if timeframe == "monthly":
        result = list_monthly_leaderboard(limit=limit, server_id=server_id, metric=metric)
    else:
        result = list_weekly_leaderboard(limit=limit, server_id=server_id, metric=metric)
    items = result.get("items") if isinstance(result, dict) else None
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def _get_historical_snapshot_record(
    *,
    server_key: str | None,
    snapshot_type: str,
    metric: str | None = None,
    window: str | None = None,
) -> dict[str, object] | None:
    if not server_key:
        return None
    return get_historical_snapshot(
        server_key=server_key,
        snapshot_type=snapshot_type,
        metric=metric,
        window=window,
    )


def _build_historical_snapshot_metadata(snapshot: dict[str, object] | None) -> dict[str, object]:
    if snapshot is None:
        return {
            "snapshot_status": "missing",
            "missing_reason": "snapshot-not-generated",
            "request_path_policy": "read-only-fast-path",
            "generation_policy": "out-of-band-refresh-only",
            "generated_at": None,
            "source_range_start": None,
            "source_range_end": None,
            "is_stale": True,
            "freshness": "stale",
        }
    is_stale = bool(snapshot.get("is_stale", False))
    return {
        "snapshot_status": "ready",
        "missing_reason": None,
        "request_path_policy": "read-only-fast-path",
        "generation_policy": "out-of-band-refresh-only",
        "generated_at": snapshot.get("generated_at"),
        "source_range_start": snapshot.get("source_range_start"),
        "source_range_end": snapshot.get("source_range_end"),
        "is_stale": is_stale,
        "freshness": "stale" if is_stale else "fresh",
    }


def _build_leaderboard_title(
    *,
    metric: str,
    timeframe: str,
    is_all_servers: bool,
    snapshot: bool = False,
) -> str:
    timeframe_label = "mensual" if timeframe == "monthly" else "semanal"
    scope_label = "totales" if is_all_servers else "por servidor"
    prefix = "Snapshot " if snapshot else ""
    title_by_metric = {
        "kills": f"{prefix}Top kills {timeframe_label} {scope_label}",
        "deaths": f"{prefix}Top muertes {timeframe_label} {scope_label}",
        "support": f"{prefix}Top puntos de soporte {timeframe_label} {scope_label}",
        "matches_over_100_kills": f"{prefix}Top partidas de 100+ kills {timeframe_label} {scope_label}",
    }
    fallback_label = f"{prefix}Ranking {timeframe_label} por servidor".strip()
    return title_by_metric.get(metric, fallback_label)


def _build_monthly_mvp_title(*, is_all_servers: bool, snapshot: bool = False) -> str:
    prefix = "Snapshot " if snapshot else ""
    scope_label = "global" if is_all_servers else "por servidor"
    return f"{prefix}Top MVP mensual {scope_label}"


def _build_monthly_mvp_v2_title(*, is_all_servers: bool, snapshot: bool = False) -> str:
    prefix = "Snapshot " if snapshot else ""
    scope_label = "global" if is_all_servers else "por servidor"
    return f"{prefix}Top MVP mensual V2 {scope_label}"


def _build_player_event_title(
    *,
    view: str,
    is_all_servers: bool,
    snapshot: bool = False,
) -> str:
    prefix = "Snapshot " if snapshot else ""
    scope_label = "global" if is_all_servers else "por servidor"
    title_by_view = {
        "most-killed": f"{prefix}Most killed mensual {scope_label}",
        "death-by": f"{prefix}Death by mensual {scope_label}",
        "duels": f"{prefix}Duelos netos mensuales {scope_label}",
        "weapon-kills": f"{prefix}Kills por arma mensuales {scope_label}",
        "teamkills": f"{prefix}Teamkills mensuales {scope_label}",
    }
    return title_by_view.get(view, f"{prefix}Metricas V2 mensuales {scope_label}")


def _resolve_player_event_snapshot_type(view: str) -> str:
    normalized_view = view.strip().lower() if isinstance(view, str) else "most-killed"
    snapshot_type_by_view = {
        "most-killed": SNAPSHOT_TYPE_PLAYER_EVENT_MOST_KILLED,
        "death-by": SNAPSHOT_TYPE_PLAYER_EVENT_DEATH_BY,
        "duels": SNAPSHOT_TYPE_PLAYER_EVENT_DUELS,
        "weapon-kills": SNAPSHOT_TYPE_PLAYER_EVENT_WEAPON_KILLS,
        "teamkills": SNAPSHOT_TYPE_PLAYER_EVENT_TEAMKILLS,
    }
    return snapshot_type_by_view.get(normalized_view, SNAPSHOT_TYPE_PLAYER_EVENT_MOST_KILLED)


def _enrich_server_items(items: list[dict[str, object]]) -> list[dict[str, object]]:
    target_index = get_live_data_source().build_target_index()
    enriched_items: list[dict[str, object]] = []
    for item in items:
        enriched_items.append(_enrich_server_item(item, target_index))
    return enriched_items


def _select_primary_snapshot_items(items: list[dict[str, object]]) -> list[dict[str, object]]:
    preferred_origin = (
        "real-rcon"
        if get_live_data_source_kind() == "rcon"
        else "real-a2s"
    )
    preferred_items = [
        item
        for item in items
        if item.get("snapshot_origin") == preferred_origin
    ]
    return preferred_items or items


def _enrich_server_item(
    item: dict[str, object],
    target_index: dict[str, object],
) -> dict[str, object]:
    enriched = dict(item)
    enriched["current_map"] = normalize_map_name(enriched.get("current_map"))
    history_url = _resolve_community_history_url(enriched.get("external_server_id"))
    enriched["community_history_url"] = history_url
    enriched["community_history_available"] = bool(history_url)
    external_server_id = enriched.get("external_server_id")
    snapshot_origin = enriched.get("snapshot_origin")
    target = target_index.get(external_server_id)

    if not target or snapshot_origin not in {"real-a2s", "real-rcon"}:
        enriched["host"] = None
        enriched["query_port"] = None
        enriched["game_port"] = None
        return enriched

    enriched["host"] = target.host
    enriched["query_port"] = target.query_port
    enriched["game_port"] = target.game_port
    return enriched


def _resolve_last_snapshot_at(items: list[dict[str, object]]) -> str | None:
    timestamps = [
        str(item["captured_at"])
        for item in items
        if item.get("captured_at")
    ]
    if not timestamps:
        return None

    return max(timestamps)


def _should_refresh_snapshot(
    items: list[dict[str, object]],
    snapshot_age_seconds: int | None,
    max_snapshot_age_seconds: int,
) -> bool:
    if not items:
        return True

    if snapshot_age_seconds is None:
        return True

    return snapshot_age_seconds > max_snapshot_age_seconds


def _is_snapshot_stale(
    snapshot_age_seconds: int | None,
    max_snapshot_age_seconds: int,
) -> bool:
    return snapshot_age_seconds is None or snapshot_age_seconds > max_snapshot_age_seconds


def _try_collect_real_time_snapshot() -> tuple[
    list[dict[str, object]],
    list[dict[str, object]],
    dict[str, object],
]:
    payload = get_live_data_source().collect_snapshots(persist=False)
    snapshots = payload.get("snapshots")
    items = _select_primary_snapshot_items(_enrich_server_items(list(snapshots or [])))
    errors = payload.get("errors")
    return (
        items,
        list(errors or []),
        {
            "primary_source": payload.get("primary_source"),
            "selected_source": payload.get("selected_source"),
            "fallback_used": bool(payload.get("fallback_used")),
            "fallback_reason": payload.get("fallback_reason"),
            "source_attempts": list(payload.get("source_attempts") or []),
        },
    )


def _build_servers_response(
    *,
    items: list[dict[str, object]],
    response_source: str,
    last_snapshot_at: str | None,
    snapshot_age_seconds: int | None,
    max_snapshot_age_seconds: int,
    refresh_attempted: bool,
    refresh_status: str,
    refresh_errors: list[dict[str, object]],
    source_policy: dict[str, object],
) -> dict[str, object]:
    freshness = (
        "fresh"
        if snapshot_age_seconds is not None and snapshot_age_seconds <= max_snapshot_age_seconds
        else "stale"
    )
    return {
        "status": "ok",
        "data": {
            "title": "Estado actual de servidores",
            "context": "current-hll-status",
            "source": response_source,
            "last_snapshot_at": last_snapshot_at,
            "snapshot_age_seconds": snapshot_age_seconds,
            "snapshot_age_minutes": _to_snapshot_age_minutes(snapshot_age_seconds),
            "max_snapshot_age_seconds": max_snapshot_age_seconds,
            "is_stale": freshness == "stale",
            "freshness": freshness,
            "refresh_attempted": refresh_attempted,
            "refresh_status": refresh_status,
            "refresh_errors": refresh_errors,
            **source_policy,
            "items": items,
        },
    }


def _calculate_snapshot_age_seconds(timestamp: str | None) -> int | None:
    if not timestamp:
        return None

    normalized = timestamp.replace("Z", "+00:00")
    captured_at = datetime.fromisoformat(normalized)
    if captured_at.tzinfo is None:
        captured_at = captured_at.replace(tzinfo=timezone.utc)

    age = datetime.now(timezone.utc) - captured_at.astimezone(timezone.utc)
    return max(0, int(age.total_seconds()))


def _to_snapshot_age_minutes(snapshot_age_seconds: int | None) -> int | None:
    if snapshot_age_seconds is None:
        return None

    return snapshot_age_seconds // 60


def _resolve_historical_fallback_policy(
    *,
    fallback_reason: str,
    operation: str = "historical-read",
) -> dict[str, object]:
    return build_historical_runtime_source_policy(
        operation=operation,
        rcon_status="unsupported",
        fallback_reason=fallback_reason,
    )


def _merge_recent_match_items(
    *,
    primary_items: list[dict[str, object]],
    fallback_items: list[dict[str, object]],
    limit: int,
) -> list[dict[str, object]]:
    merged: list[dict[str, object]] = []
    seen_keys: set[str] = set()
    for item in list(primary_items) + list(fallback_items):
        if not isinstance(item, dict):
            continue
        dedupe_key = _build_recent_match_dedupe_key(item)
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)
        merged.append(item)
    merged.sort(key=_recent_match_sort_key, reverse=True)
    return merged[:limit]


def _with_recent_result_source(
    item: dict[str, object],
    result_source: str,
) -> dict[str, object]:
    enriched = dict(item)
    enriched.setdefault("result_source", result_source)
    return enriched


def _recent_items_include_rcon_results(items: list[dict[str, object]]) -> bool:
    return any(
        item.get("result_source") in {"admin-log-match-ended", "rcon-session"}
        for item in items
        if isinstance(item, dict)
    )


def _build_recent_match_dedupe_key(item: dict[str, object]) -> str:
    server = item.get("server") if isinstance(item.get("server"), dict) else {}
    map_payload = item.get("map") if isinstance(item.get("map"), dict) else {}
    match_id = str(item.get("match_id") or "").strip()
    server_slug = str(server.get("slug") or server.get("external_server_id") or "").strip()
    map_name = str(map_payload.get("name") or map_payload.get("pretty_name") or "").strip().lower()
    closed_at = _truncate_recent_match_timestamp(
        item.get("closed_at") or item.get("ended_at")
    )
    started_at = _truncate_recent_match_timestamp(item.get("started_at"))
    if match_id and match_id.isdigit():
        return f"scoreboard:{server_slug}:{match_id}"
    return f"recent:{server_slug}:{map_name}:{started_at}:{closed_at}"


def _truncate_recent_match_timestamp(value: object) -> str:
    normalized = str(value or "").strip()
    return normalized[:16] if normalized else ""


def _recent_match_sort_key(item: dict[str, object]) -> tuple[str, str]:
    closed_at = str(item.get("closed_at") or item.get("ended_at") or "").strip()
    started_at = str(item.get("started_at") or "").strip()
    return (closed_at, started_at)


def _infer_live_source_policy_from_items(
    items: list[dict[str, object]],
    *,
    refresh_attempted: bool,
    refresh_errors: list[dict[str, object]],
) -> dict[str, object]:
    selected_source = "persisted-snapshot"
    fallback_used = False
    fallback_reason = None
    snapshot_origins = {
        str(item.get("snapshot_origin") or "").strip()
        for item in items
        if item.get("snapshot_origin")
    }
    if "real-rcon" in snapshot_origins:
        selected_source = SOURCE_KIND_RCON
    elif "real-a2s" in snapshot_origins:
        selected_source = LIVE_SOURCE_A2S
        if get_live_data_source_kind() == SOURCE_KIND_RCON:
            fallback_used = True
            fallback_reason = "persisted-live-snapshot-came-from-a2s"

    attempt_status = "success" if items else ("error" if refresh_attempted else "cached")
    attempt_reason = None if items else "no-live-snapshot-items"
    if refresh_errors and attempt_reason is None:
        attempt_reason = "live-refresh-errors-present"

    return build_source_policy(
        primary_source=get_live_data_source_kind(),
        selected_source=selected_source,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        source_attempts=[
            build_source_attempt(
                source=selected_source,
                role="served-response",
                status=attempt_status,
                reason=attempt_reason,
            )
        ],
    )


def _build_live_response_source(source_policy: dict[str, object]) -> str:
    selected_source = str(source_policy.get("selected_source") or "")
    if selected_source == SOURCE_KIND_RCON:
        return "real-time-rcon-refresh"
    if selected_source == LIVE_SOURCE_A2S:
        return "real-time-a2s-fallback"
    return "real-time-refresh"


def _resolve_community_history_url(external_server_id: object) -> str | None:
    normalized_server_id = str(external_server_id or "").strip()
    if not normalized_server_id:
        return None
    origin = get_trusted_public_scoreboard_origin(normalized_server_id)
    return f"{origin.base_url}/games" if origin else None
