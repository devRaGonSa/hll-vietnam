"""Read-only minimal HTTP model over prospective RCON historical persistence."""

from __future__ import annotations

from datetime import datetime, timezone

from .historical_storage import ALL_SERVERS_SLUG
from .normalizers import normalize_map_name
from .rcon_historical_storage import (
    find_rcon_historical_competitive_window,
    list_rcon_historical_competitive_summary_rows,
    list_rcon_historical_competitive_windows,
)


def list_rcon_historical_server_summaries(
    *,
    server_key: str | None = None,
) -> list[dict[str, object]]:
    """Return per-target coverage and freshness from RCON-backed competitive storage."""
    items = list_rcon_historical_competitive_summary_rows(
        target_key=None if server_key == ALL_SERVERS_SLUG else server_key,
    )
    summaries = [_build_server_summary(item, requested_server_key=server_key) for item in items]
    if server_key == ALL_SERVERS_SLUG:
        return [_build_all_servers_summary(summaries)]
    return summaries


def list_rcon_historical_recent_activity(
    *,
    server_key: str | None = None,
    limit: int = 20,
) -> list[dict[str, object]]:
    """Return recent RCON-backed competitive windows for one or all targets."""
    normalized_server_key = None if server_key == ALL_SERVERS_SLUG else server_key
    items = list_rcon_historical_competitive_windows(target_key=normalized_server_key, limit=limit)
    return [
        {
            "server": {
                "slug": _resolve_presented_server_slug(
                    item,
                    requested_server_key=server_key,
                ),
                "name": item["display_name"],
                "target_key": item["target_key"],
                "external_server_id": item["external_server_id"],
                "region": item["region"],
            },
            "match_id": item["session_key"],
            "started_at": item["first_seen_at"],
            "ended_at": item["last_seen_at"],
            "closed_at": item["last_seen_at"],
            "map": {
                "name": item.get("map_name"),
                "pretty_name": normalize_map_name(item.get("map_pretty_name") or item.get("map_name")),
            },
            "result": {
                "allied_score": None,
                "axis_score": None,
                "winner": None,
            },
            "player_count": int(round(float(item.get("average_players") or 0))),
            "peak_players": item.get("peak_players"),
            "sample_count": item.get("sample_count"),
            "duration_seconds": item.get("duration_seconds"),
            "capture_basis": "rcon-competitive-window",
            "capabilities": item.get("capabilities"),
            "minutes_since_capture": _minutes_since_timestamp(item.get("last_seen_at")),
        }
        for item in items
    ]


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
            "recent_matches": "approximate",
            "competitive_quality": "partial",
            "player_stats": "unavailable",
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


def _build_server_summary(
    item: dict[str, object],
    *,
    requested_server_key: str | None = None,
) -> dict[str, object]:
    sample_count = int(item.get("sample_count") or 0)
    first_last_points = list_rcon_historical_recent_activity(
        server_key=str(item["target_key"]),
        limit=1,
    )
    last_sample_at = item.get("last_seen_at")
    latest_activity = first_last_points[0] if first_last_points else None

    return {
        "server": {
            "slug": _resolve_presented_server_slug(
                item,
                requested_server_key=requested_server_key,
            ),
            "name": item["display_name"],
            "target_key": item["target_key"],
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
    captured_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if captured_at.tzinfo is None:
        captured_at = captured_at.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - captured_at.astimezone(timezone.utc)
    return max(0, int(delta.total_seconds() // 60))


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


def _resolve_presented_server_slug(
    item: dict[str, object],
    *,
    requested_server_key: str | None,
) -> str:
    external_server_id = str(item.get("external_server_id") or "").strip()
    if external_server_id:
        return external_server_id
    normalized_requested_server_key = str(requested_server_key or "").strip()
    if normalized_requested_server_key and normalized_requested_server_key != ALL_SERVERS_SLUG:
        return normalized_requested_server_key
    return str(item["target_key"])


def has_rcon_historical_server_summary_coverage(
    items: list[dict[str, object]],
) -> bool:
    """Return whether the RCON summary items have usable competitive coverage."""
    return any(_summary_item_has_coverage(item) for item in items)


def has_rcon_historical_recent_activity_coverage(
    items: list[dict[str, object]],
) -> bool:
    """Return whether the RCON recent-activity items are usable for runtime reads."""
    return any(_recent_activity_item_has_coverage(item) for item in items)


def _summary_item_has_coverage(item: dict[str, object]) -> bool:
    coverage = item.get("coverage")
    if not isinstance(coverage, dict):
        return False
    if str(coverage.get("status") or "") == "empty":
        return False
    return int(coverage.get("window_count") or coverage.get("sample_count") or 0) > 0


def _recent_activity_item_has_coverage(item: dict[str, object]) -> bool:
    return (
        bool(item.get("match_id"))
        and bool(item.get("closed_at"))
        and int(item.get("sample_count") or 0) > 0
    )
