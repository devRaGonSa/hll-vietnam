"""Read-only minimal HTTP model over prospective RCON historical persistence."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from .historical_storage import ALL_SERVERS_SLUG
from .normalizers import normalize_map_name
from .player_external_profiles import build_external_player_profile_fields
from .rcon_scoreboard_correlation import resolve_rcon_scoreboard_match_url
from .rcon_historical_storage import (
    find_rcon_historical_competitive_window,
    get_rcon_historical_competitive_window_by_session,
    list_rcon_historical_competitive_summary_rows,
    list_rcon_historical_competitive_windows,
)

MATCH_RESULT_SOURCE = "admin-log-match-ended"
SESSION_RESULT_SOURCE = "rcon-session"


def list_rcon_historical_server_summaries(
    *,
    server_key: str | None = None,
) -> list[dict[str, object]]:
    """Return per-target coverage and freshness from RCON-backed competitive storage."""
    items = list_rcon_historical_competitive_summary_rows()
    if server_key and server_key != ALL_SERVERS_SLUG:
        normalized = server_key.strip()
        items = [
            item
            for item in items
            if item["target_key"] == normalized or item["external_server_id"] == normalized
        ]

    summaries = [_build_server_summary(item) for item in items]
    if server_key == ALL_SERVERS_SLUG:
        return [_build_all_servers_summary(summaries)]
    return summaries


def list_rcon_historical_recent_activity(
    *,
    server_key: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    """Return recent RCON-backed competitive windows for one or all targets."""
    from .rcon_admin_log_materialization import list_materialized_rcon_matches

    normalized_server_key = None if server_key == ALL_SERVERS_SLUG else server_key
    materialized_items = list_materialized_rcon_matches(
        target_key=normalized_server_key,
        only_ended=True,
        limit=limit,
    )
    primary_items = [_build_materialized_recent_item(item) for item in materialized_items]
    if primary_items:
        return primary_items[:limit]

    session_items = list_rcon_historical_competitive_windows(
        target_key=normalized_server_key,
        limit=limit,
    )
    fallback_items = [
        {
            "server": {
                "slug": item["target_key"],
                "name": item["display_name"],
                "external_server_id": item["external_server_id"],
                "region": item["region"],
            },
            "match_id": item["session_key"],
            "internal_detail_match_id": item["session_key"],
            "started_at": item["first_seen_at"],
            "ended_at": item["last_seen_at"],
            "closed_at": item["last_seen_at"],
            "map": {
                "name": item.get("map_name"),
                "pretty_name": normalize_map_name(item.get("map_pretty_name") or item.get("map_name")),
            },
            "result": _build_rcon_result(item.get("latest_payload")),
            "gamestate": _build_rcon_gamestate(item.get("latest_payload")),
            "player_count": int(round(float(item.get("average_players") or 0))),
            "peak_players": item.get("peak_players"),
            "sample_count": item.get("sample_count"),
            "duration_seconds": item.get("duration_seconds"),
            "capture_basis": "rcon-competitive-window",
            "result_source": SESSION_RESULT_SOURCE,
            "capabilities": item.get("capabilities"),
            "minutes_since_capture": _minutes_since_timestamp(item.get("last_seen_at")),
        }
        for item in session_items
    ]
    return _merge_recent_items(primary_items, fallback_items, limit=limit)


def describe_rcon_historical_read_model() -> dict[str, object]:
    """Describe what the minimal RCON historical read model currently supports."""
    return {
        "source": "rcon-historical-competitive-read-model",
        "supported_endpoints": [
            "/api/historical/server-summary",
            "/api/historical/recent-matches",
        ],
        "unsupported_endpoints": [
            "/api/historical/weekly-top-kills",
            "/api/historical/weekly-leaderboard",
            "/api/historical/leaderboard",
            "/api/historical/monthly-mvp",
            "/api/historical/monthly-mvp-v2",
            "/api/historical/elo-mmr/leaderboard",
            "/api/historical/elo-mmr/player",
            "/api/historical/player-events",
            "/api/historical/player-profile",
            "/api/historical/snapshots/*",
        ],
        "capabilities": {
            "server_summary": "exact",
            "recent_matches": "exact-when-admin-log-match-ended",
            "competitive_quality": "partial",
            "result": "admin-log-match-ended",
            "gamestate": "session-fallback",
            "player_stats": "admin-log-derived",
        },
        "limitations": [
            "No retroactive backfill of closed matches.",
            "No weekly or monthly competitive leaderboards.",
            "No MVP or player-event parity with public-scoreboard.",
            "No player-level scoreboard parity from RCON samples alone.",
        ],
    }


def get_rcon_historical_competitive_match_context(
    *,
    server_key: str,
    ended_at: str | None,
    map_name: str | None = None,
) -> dict[str, object] | None:
    """Return the closest RCON-backed competitive context for one historical match."""
    return find_rcon_historical_competitive_window(
        server_key=server_key,
        ended_at=ended_at,
        map_name=map_name,
    )


def get_rcon_historical_match_detail(
    *,
    server_key: str,
    match_id: str,
) -> dict[str, object] | None:
    """Return one RCON competitive window as a match-detail compatible payload."""
    from .rcon_admin_log_materialization import get_materialized_rcon_match_detail

    materialized = get_materialized_rcon_match_detail(server_key=server_key, match_key=match_id)
    if materialized is not None:
        return _build_materialized_detail_item(materialized)

    item = get_rcon_historical_competitive_window_by_session(
        server_key=server_key,
        session_key=match_id,
    )
    if item is None:
        return None
    player_count = int(round(float(item.get("average_players") or 0)))
    server_slug = item["external_server_id"] or item["target_key"]
    return {
        "server": {
            "slug": item["target_key"],
            "name": item["display_name"],
            "external_server_id": item["external_server_id"],
            "region": item["region"],
        },
        "match_id": item["session_key"],
        "started_at": item["first_seen_at"],
        "ended_at": item["last_seen_at"],
        "closed_at": item["last_seen_at"],
        "duration_seconds": item.get("duration_seconds"),
        "map": {
            "name": item.get("map_name"),
            "pretty_name": normalize_map_name(item.get("map_pretty_name") or item.get("map_name")),
        },
        "result": _build_rcon_result(item.get("latest_payload")),
        "gamestate": _build_rcon_gamestate(item.get("latest_payload")),
        "player_count": int(round(float(item.get("average_players") or 0))),
        "peak_players": item.get("peak_players"),
        "sample_count": item.get("sample_count"),
        "players": [],
        "capture_basis": "rcon-competitive-window",
        "confidence": item.get("confidence_mode"),
        "source_basis": "rcon-session",
        "result_source": SESSION_RESULT_SOURCE,
        "capabilities": item.get("capabilities"),
        "match_url": resolve_rcon_scoreboard_match_url(
            server_slug=server_slug,
            map_name=item.get("map_pretty_name") or item.get("map_name"),
            started_at=item["first_seen_at"],
            ended_at=item["last_seen_at"],
            duration_seconds=item.get("duration_seconds"),
            player_count=player_count,
            peak_players=item.get("peak_players"),
        ),
    }


def _build_materialized_recent_item(item: dict[str, object]) -> dict[str, object]:
    timestamps = _build_materialized_timestamp_payload(item)
    player_count = _resolve_materialized_player_count(item)
    scoreboard_correlation = build_materialized_scoreboard_correlation_input(item)
    return {
        "server": {
            "slug": item.get("target_key"),
            "name": _server_display_name(item.get("external_server_id") or item.get("target_key")),
            "external_server_id": item.get("external_server_id"),
            "region": None,
        },
        "match_id": item.get("match_key"),
        "internal_detail_match_id": item.get("match_key"),
        "started_at": timestamps["started_at"],
        "ended_at": timestamps["ended_at"],
        "closed_at": timestamps["closed_at"],
        "timestamp_confidence": timestamps["timestamp_confidence"],
        "map": {
            "name": item.get("map_name"),
            "pretty_name": item.get("map_pretty_name") or normalize_map_name(item.get("map_name")),
        },
        "game_mode": item.get("game_mode"),
        "result": {
            "allied_score": item.get("allied_score"),
            "axis_score": item.get("axis_score"),
            "winner": item.get("winner"),
        },
        "winner": item.get("winner"),
        "player_count": player_count,
        "peak_players": None,
        "sample_count": None,
        "duration_seconds": _calculate_match_duration_seconds(item),
        "capture_basis": "rcon-materialized-admin-log",
        "confidence": item.get("confidence_mode"),
        "source_basis": item.get("source_basis"),
        "result_source": (
            MATCH_RESULT_SOURCE
            if item.get("source_basis") == MATCH_RESULT_SOURCE
            else SESSION_RESULT_SOURCE
        ),
        "match_url": resolve_rcon_scoreboard_match_url(
            **scoreboard_correlation,
        ),
        "capabilities": describe_rcon_historical_read_model()["capabilities"],
    }


def _build_materialized_detail_item(materialized: dict[str, object]) -> dict[str, object]:
    from .rcon_admin_log_storage import get_latest_rcon_player_profile_summaries

    match = materialized["match"]
    recent_item = _build_materialized_recent_item(match)
    profile_summaries = get_latest_rcon_player_profile_summaries(
        target_key=str(match["target_key"]),
        player_ids=[str(row["player_id"]) for row in materialized["players"] if row.get("player_id")],
    )
    players = [
        _build_player_row(
            row,
            profile_summary=profile_summaries.get(str(row.get("player_id"))),
        )
        for row in materialized["players"]
    ]
    player_count = len(players) if players else recent_item.get("player_count")
    return {
        **recent_item,
        "match_id": match["match_key"],
        "game_mode": match.get("game_mode"),
        "winner": match.get("winner"),
        "confidence": match.get("confidence_mode"),
        "source_basis": match.get("source_basis"),
        "player_count": player_count,
        "players": players,
        "timeline": {
            "event_counts": materialized.get("timeline", []),
        },
    }


def _resolve_materialized_player_count(item: dict[str, object]) -> int | None:
    for key in (
        "player_count",
        "materialized_player_count",
        "materialized_distinct_player_count",
    ):
        value = _coerce_optional_int(item.get(key))
        if value is not None and value > 0:
            return value
    return None


def _build_player_row(
    row: dict[str, object],
    *,
    profile_summary: dict[str, object] | None = None,
) -> dict[str, object]:
    kills = _coerce_optional_int(row.get("kills")) or 0
    deaths = _coerce_optional_int(row.get("deaths")) or 0
    player = {
        "player_name": row.get("player_name"),
        "team": row.get("team"),
        "kills": kills,
        "deaths": deaths,
        "teamkills": _coerce_optional_int(row.get("teamkills")) or 0,
        "kd_ratio": round(kills / deaths, 2) if deaths else float(kills),
        "top_weapons": _top_counter(row.get("weapons_json")),
        "most_killed": _top_counter(row.get("most_killed_json")),
        "death_by": _top_counter(row.get("death_by_json")),
        **build_external_player_profile_fields(player_id=row.get("player_id")),
    }
    if profile_summary:
        player["profile_summary"] = profile_summary
    return player


def _top_counter(raw_value: object, *, limit: int = 5) -> list[dict[str, object]]:
    if not isinstance(raw_value, str) or not raw_value.strip():
        return []
    try:
        payload = json.loads(raw_value)
    except (NameError, ValueError, TypeError):
        return []
    if not isinstance(payload, dict):
        return []
    rows = [
        {"name": str(name), "count": int(count)}
        for name, count in payload.items()
        if _coerce_optional_int(count) is not None
    ]
    rows.sort(key=lambda item: (-int(item["count"]), str(item["name"])))
    return rows[:limit]


def _build_materialized_timestamp_payload(item: dict[str, object]) -> dict[str, object]:
    started_at = item.get("started_at")
    ended_at = item.get("ended_at")
    duration_seconds = _calculate_match_duration_seconds(item)
    has_server_time_duration = bool(duration_seconds and duration_seconds > 0)
    if started_at and ended_at and started_at == ended_at and has_server_time_duration:
        return {
            "started_at": None,
            "ended_at": None,
            "closed_at": ended_at,
            "timestamp_confidence": "server-time-only",
        }
    return {
        "started_at": started_at,
        "ended_at": ended_at,
        "closed_at": ended_at or started_at,
        "timestamp_confidence": "absolute" if started_at or ended_at else "server-time-only",
    }


def _build_materialized_scoreboard_correlation_window(
    item: dict[str, object],
    timestamps: dict[str, object],
) -> dict[str, object]:
    started_at = timestamps.get("started_at")
    ended_at = timestamps.get("ended_at")
    if started_at and ended_at:
        return {"started_at": started_at, "ended_at": ended_at}

    closed_at = timestamps.get("closed_at") or item.get("ended_at") or item.get("started_at")
    duration_seconds = _calculate_match_duration_seconds(item)
    closed_point = _parse_datetime(closed_at)
    if closed_point is None or not duration_seconds:
        return {"started_at": started_at, "ended_at": ended_at}

    started_point = closed_point - timedelta(seconds=int(duration_seconds))
    return {
        "started_at": started_point.isoformat().replace("+00:00", "Z"),
        "ended_at": closed_point.isoformat().replace("+00:00", "Z"),
    }


def build_materialized_scoreboard_correlation_input(
    item: dict[str, object],
) -> dict[str, object]:
    """Build safe candidate correlation inputs for one materialized RCON match."""
    timestamps = _build_materialized_timestamp_payload(item)
    correlation_window = _build_materialized_scoreboard_correlation_window(item, timestamps)
    return {
        "server_slug": item.get("external_server_id") or item.get("target_key"),
        "map_name": item.get("map_pretty_name") or item.get("map_name"),
        "started_at": correlation_window["started_at"],
        "ended_at": correlation_window["ended_at"],
        "duration_seconds": _calculate_match_duration_seconds(item),
        "allied_score": item.get("allied_score"),
        "axis_score": item.get("axis_score"),
    }


def _merge_recent_items(
    primary_items: list[dict[str, object]],
    fallback_items: list[dict[str, object]],
    *,
    limit: int,
) -> list[dict[str, object]]:
    merged: list[dict[str, object]] = []
    seen: set[tuple[object, object]] = set()
    for item in primary_items + fallback_items:
        map_payload = item.get("map") if isinstance(item.get("map"), dict) else {}
        key = (
            item.get("server", {}).get("slug") if isinstance(item.get("server"), dict) else None,
            normalize_map_name(map_payload.get("pretty_name") or map_payload.get("name")),
        )
        if key in seen:
            continue
        seen.add(key)
        merged.append(item)
    merged.sort(key=lambda row: str(row.get("closed_at") or row.get("ended_at") or row.get("started_at") or ""), reverse=True)
    return merged[:limit]


def _server_display_name(server_slug: object) -> str:
    slug = str(server_slug or "").strip()
    if slug == "comunidad-hispana-01":
        return "Comunidad Hispana #01"
    if slug == "comunidad-hispana-02":
        return "Comunidad Hispana #02"
    return slug or "RCON"


def _build_rcon_result(latest_payload: object) -> dict[str, object]:
    payload = latest_payload if isinstance(latest_payload, dict) else {}
    allied_score = _coerce_optional_int(payload.get("allied_score"))
    axis_score = _coerce_optional_int(payload.get("axis_score"))
    winner = payload.get("winner")
    if not isinstance(winner, str) or not winner:
        winner = _resolve_result_winner(allied_score, axis_score)
    return {
        "allied_score": allied_score,
        "axis_score": axis_score,
        "winner": winner,
    }


def _build_rcon_gamestate(latest_payload: object) -> dict[str, object]:
    payload = latest_payload if isinstance(latest_payload, dict) else {}
    return {
        "game_mode": payload.get("game_mode"),
        "allied_faction": payload.get("allied_faction"),
        "axis_faction": payload.get("axis_faction"),
        "allied_players": _coerce_optional_int(payload.get("allied_players")),
        "axis_players": _coerce_optional_int(payload.get("axis_players")),
        "remaining_match_time_seconds": _coerce_optional_int(
            payload.get("remaining_match_time_seconds")
        ),
        "match_time_seconds": _coerce_optional_int(payload.get("match_time_seconds")),
        "queue_count": _coerce_optional_int(payload.get("queue_count")),
        "max_queue_count": _coerce_optional_int(payload.get("max_queue_count")),
        "vip_queue_count": _coerce_optional_int(payload.get("vip_queue_count")),
        "max_vip_queue_count": _coerce_optional_int(payload.get("max_vip_queue_count")),
    }


def _resolve_result_winner(allied_score: int | None, axis_score: int | None) -> str | None:
    if allied_score is None or axis_score is None:
        return None
    if allied_score > axis_score:
        return "allied"
    if axis_score > allied_score:
        return "axis"
    return "draw"


def _coerce_optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _build_server_summary(item: dict[str, object]) -> dict[str, object]:
    sample_count = int(item.get("sample_count") or 0)
    first_last_points = list_rcon_historical_recent_activity(
        server_key=str(item["target_key"]),
        limit=1,
    )
    last_sample_at = item.get("last_seen_at")
    latest_activity = first_last_points[0] if first_last_points else None

    return {
        "server": {
            "slug": item["target_key"],
            "name": item["display_name"],
            "external_server_id": item["external_server_id"],
            "region": item["region"],
        },
        "coverage": {
            "basis": "rcon-competitive-windows",
            "status": "available" if int(item.get("window_count") or 0) > 0 else "empty",
            "window_count": int(item.get("window_count") or 0),
            "sample_count": sample_count,
            "first_sample_at": item.get("first_seen_at"),
            "last_sample_at": last_sample_at,
            "coverage_hours": _calculate_coverage_hours(item.get("first_seen_at"), last_sample_at),
        },
        "freshness": {
            "last_successful_capture_at": item.get("last_successful_capture_at"),
            "minutes_since_last_capture": _minutes_since_timestamp(last_sample_at),
            "last_run_status": item.get("last_run_status"),
            "last_error": item.get("last_error"),
            "last_error_at": item.get("last_error_at"),
        },
        "activity": {
            "latest_players": latest_activity.get("player_count") if latest_activity else None,
            "latest_peak_players": latest_activity.get("peak_players") if latest_activity else None,
            "latest_map": latest_activity.get("map", {}).get("pretty_name") if latest_activity else None,
            "latest_status": "captured" if latest_activity else None,
        },
        "time_range": {
            "start": item.get("first_seen_at"),
            "end": last_sample_at,
        },
        "capabilities": describe_rcon_historical_read_model()["capabilities"],
    }


def _build_all_servers_summary(items: list[dict[str, object]]) -> dict[str, object]:
    total_samples = sum(int(item["coverage"].get("sample_count") or 0) for item in items)
    last_points = [
        item["time_range"].get("end")
        for item in items
        if item["time_range"].get("end")
    ]
    last_capture_at = max(last_points) if last_points else None
    return {
        "server": {
            "slug": ALL_SERVERS_SLUG,
            "name": "Todos",
            "external_server_id": None,
            "region": None,
        },
        "coverage": {
            "basis": "rcon-competitive-windows-aggregate",
            "status": "available" if total_samples > 0 else "empty",
            "sample_count": total_samples,
            "first_sample_at": None,
            "last_sample_at": last_capture_at,
            "coverage_hours": None,
        },
        "freshness": {
            "last_successful_capture_at": last_capture_at,
            "minutes_since_last_capture": _minutes_since_timestamp(last_capture_at),
            "last_run_status": None,
            "last_error": None,
            "last_error_at": None,
        },
        "activity": {
            "latest_players": None,
            "latest_max_players": None,
            "latest_map": None,
            "latest_status": None,
        },
        "time_range": {
            "start": None,
            "end": last_capture_at,
        },
        "server_count": len(items),
        "capabilities": describe_rcon_historical_read_model()["capabilities"],
    }


def _minutes_since_timestamp(timestamp: str | None) -> int | None:
    if not timestamp:
        return None
    captured_at = _parse_datetime(timestamp)
    if captured_at is None:
        return None
    delta = datetime.now(timezone.utc) - captured_at.astimezone(timezone.utc)
    return max(0, int(delta.total_seconds() // 60))


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _calculate_coverage_hours(
    first_sample_at: str | None,
    last_sample_at: str | None,
) -> float | None:
    if not first_sample_at or not last_sample_at:
        return None
    first_point = datetime.fromisoformat(first_sample_at.replace("Z", "+00:00"))
    last_point = datetime.fromisoformat(last_sample_at.replace("Z", "+00:00"))
    if first_point.tzinfo is None:
        first_point = first_point.replace(tzinfo=timezone.utc)
    if last_point.tzinfo is None:
        last_point = last_point.replace(tzinfo=timezone.utc)
    delta = last_point.astimezone(timezone.utc) - first_point.astimezone(timezone.utc)
    return round(delta.total_seconds() / 3600, 2)


def _calculate_duration_seconds(first_seen_at: object, last_seen_at: object) -> int | None:
    if not isinstance(first_seen_at, str) or not isinstance(last_seen_at, str):
        return None
    first_point = datetime.fromisoformat(first_seen_at.replace("Z", "+00:00"))
    last_point = datetime.fromisoformat(last_seen_at.replace("Z", "+00:00"))
    if first_point.tzinfo is None:
        first_point = first_point.replace(tzinfo=timezone.utc)
    if last_point.tzinfo is None:
        last_point = last_point.replace(tzinfo=timezone.utc)
    return max(0, int((last_point.astimezone(timezone.utc) - first_point.astimezone(timezone.utc)).total_seconds()))


def _calculate_match_duration_seconds(item: dict[str, object]) -> int | None:
    duration = _calculate_duration_seconds(item.get("started_at"), item.get("ended_at"))
    if duration:
        return duration
    started_server_time = _coerce_optional_int(item.get("started_server_time"))
    ended_server_time = _coerce_optional_int(item.get("ended_server_time"))
    if started_server_time is None or ended_server_time is None:
        return duration
    return max(0, ended_server_time - started_server_time)
