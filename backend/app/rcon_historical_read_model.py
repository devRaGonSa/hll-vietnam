"""Read-only minimal HTTP model over prospective RCON historical persistence."""

from __future__ import annotations

from datetime import datetime, timezone

from .historical_storage import ALL_SERVERS_SLUG
from .normalizers import normalize_map_name
from .rcon_historical_storage import (
    list_rcon_historical_target_statuses,
    list_recent_rcon_historical_samples,
)


def list_rcon_historical_server_summaries(
    *,
    server_key: str | None = None,
) -> list[dict[str, object]]:
    """Return per-target coverage and freshness from prospective RCON storage."""
    items = list_rcon_historical_target_statuses()
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
    """Return recent persisted RCON activity samples for one or all targets."""
    normalized_server_key = None if server_key == ALL_SERVERS_SLUG else server_key
    items = list_recent_rcon_historical_samples(target_key=normalized_server_key, limit=limit)
    return [
        {
            **item,
            "current_map": normalize_map_name(item.get("current_map")),
            "minutes_since_capture": _minutes_since_timestamp(item.get("captured_at")),
        }
        for item in items
    ]


def describe_rcon_historical_read_model() -> dict[str, object]:
    """Describe what the minimal RCON historical read model currently supports."""
    return {
        "source": "rcon-historical-read-model",
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
            "/api/historical/player-events",
            "/api/historical/player-profile",
            "/api/historical/snapshots/*",
        ],
        "capabilities": [
            "coverage by configured RCON target",
            "recent persisted live activity",
            "freshness and last successful capture metadata",
        ],
        "limitations": [
            "No retroactive backfill of closed matches.",
            "No weekly or monthly competitive leaderboards.",
            "No MVP or player-event parity with public-scoreboard.",
            "No precomputed historical snapshots for the RCON read model yet.",
        ],
    }


def _build_server_summary(item: dict[str, object]) -> dict[str, object]:
    sample_count = int(item.get("sample_count") or 0)
    first_last_points = list_rcon_historical_recent_activity(
        server_key=str(item["target_key"]),
        limit=1,
    )
    last_sample_at = item.get("last_sample_at")
    latest_activity = first_last_points[0] if first_last_points else None

    return {
        "server": {
            "slug": item["target_key"],
            "name": item["display_name"],
            "external_server_id": item["external_server_id"],
            "region": item["region"],
        },
        "coverage": {
            "basis": "prospective-rcon-samples",
            "status": "available" if sample_count > 0 else "empty",
            "sample_count": sample_count,
            "first_sample_at": item.get("first_sample_at"),
            "last_sample_at": last_sample_at,
            "coverage_hours": _calculate_coverage_hours(item.get("first_sample_at"), last_sample_at),
        },
        "freshness": {
            "last_successful_capture_at": item.get("last_successful_capture_at"),
            "minutes_since_last_capture": _minutes_since_timestamp(last_sample_at),
            "last_run_id": item.get("last_run_id"),
            "last_run_status": item.get("last_run_status"),
            "last_error": item.get("last_error"),
            "last_error_at": item.get("last_error_at"),
        },
        "activity": {
            "latest_players": latest_activity.get("players") if latest_activity else None,
            "latest_max_players": latest_activity.get("max_players") if latest_activity else None,
            "latest_map": latest_activity.get("current_map") if latest_activity else None,
            "latest_status": latest_activity.get("status") if latest_activity else None,
        },
        "time_range": {
            "start": None,
            "end": last_sample_at,
        },
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
            "basis": "prospective-rcon-samples-aggregate",
            "status": "available" if total_samples > 0 else "empty",
            "sample_count": total_samples,
            "first_sample_at": None,
            "last_sample_at": last_capture_at,
            "coverage_hours": None,
        },
        "freshness": {
            "last_successful_capture_at": last_capture_at,
            "minutes_since_last_capture": _minutes_since_timestamp(last_capture_at),
            "last_run_id": None,
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
