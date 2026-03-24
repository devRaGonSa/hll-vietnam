"""Definitions for persisted precomputed historical snapshots."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .historical_storage import (
    ALL_SERVERS_SLUG,
    list_historical_server_summaries,
    list_historical_servers,
    list_monthly_leaderboard,
    list_monthly_mvp_ranking,
    list_recent_historical_matches,
    list_weekly_leaderboard,
)

SNAPSHOT_TYPE_SERVER_SUMMARY = "server-summary"
SNAPSHOT_TYPE_WEEKLY_LEADERBOARD = "weekly-leaderboard"
SNAPSHOT_TYPE_MONTHLY_LEADERBOARD = "monthly-leaderboard"
SNAPSHOT_TYPE_MONTHLY_MVP = "monthly-mvp"
SNAPSHOT_TYPE_RECENT_MATCHES = "recent-matches"

SUPPORTED_SNAPSHOT_TYPES = frozenset(
    {
        SNAPSHOT_TYPE_SERVER_SUMMARY,
        SNAPSHOT_TYPE_WEEKLY_LEADERBOARD,
        SNAPSHOT_TYPE_MONTHLY_LEADERBOARD,
        SNAPSHOT_TYPE_MONTHLY_MVP,
        SNAPSHOT_TYPE_RECENT_MATCHES,
    }
)

SUPPORTED_LEADERBOARD_METRICS = frozenset(
    {
        "kills",
        "deaths",
        "support",
        "matches_over_100_kills",
    }
)
PREWARM_SNAPSHOT_SERVER_KEYS = (
    "comunidad-hispana-01",
    "comunidad-hispana-02",
    "comunidad-hispana-03",
    ALL_SERVERS_SLUG,
)
PREWARM_LEADERBOARD_METRICS = ("kills",)
SNAPSHOT_LEADERBOARD_METRICS = (
    "kills",
    "deaths",
    "matches_over_100_kills",
    "support",
)

DEFAULT_SNAPSHOT_WINDOW = "all-time"
DEFAULT_WEEKLY_SNAPSHOT_WINDOW = "7d"
DEFAULT_MONTHLY_SNAPSHOT_WINDOW = "month"
DEFAULT_WEEKLY_LEADERBOARD_LIMIT = 10
DEFAULT_RECENT_MATCHES_LIMIT = 20


def validate_snapshot_identity(
    *,
    snapshot_type: str,
    metric: str | None = None,
) -> None:
    """Validate the persisted snapshot selectors accepted by the storage layer."""
    if snapshot_type not in SUPPORTED_SNAPSHOT_TYPES:
        raise ValueError(f"Unsupported historical snapshot type: {snapshot_type}")

    if snapshot_type in {
        SNAPSHOT_TYPE_WEEKLY_LEADERBOARD,
        SNAPSHOT_TYPE_MONTHLY_LEADERBOARD,
    }:
        if metric not in SUPPORTED_LEADERBOARD_METRICS:
            raise ValueError(f"Unsupported historical snapshot metric: {metric}")
        return

    if metric is not None:
        raise ValueError(
            "Metric is only supported for weekly-leaderboard and monthly-leaderboard."
        )


def list_snapshot_server_keys(*, db_path: Path | None = None) -> list[str]:
    """Return the historical server slugs that should receive persisted snapshots."""
    server_keys = [
        str(item["slug"])
        for item in list_historical_servers(db_path=db_path)
        if item.get("slug")
    ]
    server_keys.append(ALL_SERVERS_SLUG)
    return server_keys


def build_historical_server_snapshots(
    *,
    server_key: str,
    generated_at: datetime | None = None,
    leaderboard_limit: int = DEFAULT_WEEKLY_LEADERBOARD_LIMIT,
    recent_matches_limit: int = DEFAULT_RECENT_MATCHES_LIMIT,
    db_path: Path | None = None,
) -> list[dict[str, object]]:
    """Build all precomputed historical snapshots required for one server."""
    generated_at_value = _as_utc(generated_at or datetime.now(timezone.utc))
    snapshots = [_build_server_summary_snapshot(server_key, generated_at_value, db_path=db_path)]

    for metric in SNAPSHOT_LEADERBOARD_METRICS:
        snapshots.append(
            _build_weekly_leaderboard_snapshot(
                server_key,
                metric,
                generated_at_value,
                limit=leaderboard_limit,
                db_path=db_path,
            )
        )
        snapshots.append(
            _build_monthly_leaderboard_snapshot(
                server_key,
                metric,
                generated_at_value,
                limit=leaderboard_limit,
                db_path=db_path,
            )
    )

    snapshots.append(
        _build_monthly_mvp_snapshot(
            server_key,
            generated_at_value,
            limit=leaderboard_limit,
            db_path=db_path,
        )
    )

    snapshots.append(
        _build_recent_matches_snapshot(
            server_key,
            generated_at_value,
            limit=recent_matches_limit,
            db_path=db_path,
        )
    )
    return snapshots


def build_priority_historical_snapshots(
    *,
    server_keys: tuple[str, ...] = PREWARM_SNAPSHOT_SERVER_KEYS,
    generated_at: datetime | None = None,
    leaderboard_limit: int = DEFAULT_WEEKLY_LEADERBOARD_LIMIT,
    recent_matches_limit: int = DEFAULT_RECENT_MATCHES_LIMIT,
    db_path: Path | None = None,
) -> list[dict[str, object]]:
    """Build the minimum warm snapshot set required by the historical UI."""
    generated_at_value = _as_utc(generated_at or datetime.now(timezone.utc))
    snapshots: list[dict[str, object]] = []
    for server_key in server_keys:
        snapshots.append(
            _build_server_summary_snapshot(server_key, generated_at_value, db_path=db_path)
        )
        for metric in PREWARM_LEADERBOARD_METRICS:
            snapshots.append(
                _build_weekly_leaderboard_snapshot(
                    server_key,
                    metric,
                    generated_at_value,
                    limit=leaderboard_limit,
                    db_path=db_path,
                )
            )
            snapshots.append(
                _build_monthly_leaderboard_snapshot(
                    server_key,
                    metric,
                    generated_at_value,
                    limit=leaderboard_limit,
                    db_path=db_path,
                )
            )
        snapshots.append(
            _build_monthly_mvp_snapshot(
                server_key,
                generated_at_value,
                limit=leaderboard_limit,
                db_path=db_path,
            )
        )
        snapshots.append(
            _build_recent_matches_snapshot(
                server_key,
                generated_at_value,
                limit=recent_matches_limit,
                db_path=db_path,
            )
        )
    return snapshots


def build_all_historical_snapshots(
    *,
    server_key: str | None = None,
    generated_at: datetime | None = None,
    leaderboard_limit: int = DEFAULT_WEEKLY_LEADERBOARD_LIMIT,
    recent_matches_limit: int = DEFAULT_RECENT_MATCHES_LIMIT,
    db_path: Path | None = None,
) -> list[dict[str, object]]:
    """Build the full snapshot set for one server or for all configured servers."""
    target_server_keys = _resolve_snapshot_target_keys(server_key=server_key, db_path=db_path)
    snapshots: list[dict[str, object]] = []
    for target_server_key in target_server_keys:
        snapshots.extend(
            build_historical_server_snapshots(
                server_key=target_server_key,
                generated_at=generated_at,
                leaderboard_limit=leaderboard_limit,
                recent_matches_limit=recent_matches_limit,
                db_path=db_path,
            )
        )
    return snapshots


def generate_and_persist_historical_snapshots(
    *,
    server_key: str | None = None,
    generated_at: datetime | None = None,
    leaderboard_limit: int = DEFAULT_WEEKLY_LEADERBOARD_LIMIT,
    recent_matches_limit: int = DEFAULT_RECENT_MATCHES_LIMIT,
    db_path: Path | None = None,
) -> dict[str, object]:
    """Build and persist precomputed snapshots for one server or all servers."""
    from .historical_snapshot_storage import persist_historical_snapshot_batch

    generated_at_value = _as_utc(generated_at or datetime.now(timezone.utc))
    snapshots = build_all_historical_snapshots(
        server_key=server_key,
        generated_at=generated_at_value,
        leaderboard_limit=leaderboard_limit,
        recent_matches_limit=recent_matches_limit,
        db_path=db_path,
    )
    persisted_records = persist_historical_snapshot_batch(snapshots, db_path=db_path)
    snapshots_by_server: dict[str, int] = {}
    for record in persisted_records:
        snapshots_by_server.setdefault(record.server_key, 0)
        snapshots_by_server[record.server_key] += 1

    return {
        "generated_at": _to_iso(generated_at_value),
        "server_slug": server_key,
        "snapshot_policy": "full-matrix",
        "snapshot_count": len(persisted_records),
        "servers_processed": len(snapshots_by_server),
        "snapshots_by_server": snapshots_by_server,
    }


def generate_and_persist_priority_historical_snapshots(
    *,
    generated_at: datetime | None = None,
    leaderboard_limit: int = DEFAULT_WEEKLY_LEADERBOARD_LIMIT,
    recent_matches_limit: int = DEFAULT_RECENT_MATCHES_LIMIT,
    db_path: Path | None = None,
) -> dict[str, object]:
    """Build and persist the priority snapshot set used for prewarm."""
    from .historical_snapshot_storage import persist_historical_snapshot_batch

    generated_at_value = _as_utc(generated_at or datetime.now(timezone.utc))
    snapshots = build_priority_historical_snapshots(
        generated_at=generated_at_value,
        leaderboard_limit=leaderboard_limit,
        recent_matches_limit=recent_matches_limit,
        db_path=db_path,
    )
    persisted_records = persist_historical_snapshot_batch(snapshots, db_path=db_path)
    snapshots_by_server: dict[str, int] = {}
    for record in persisted_records:
        snapshots_by_server.setdefault(record.server_key, 0)
        snapshots_by_server[record.server_key] += 1

    return {
        "generated_at": _to_iso(generated_at_value),
        "server_slug": None,
        "snapshot_policy": "priority-prewarm",
        "prewarm_server_keys": list(PREWARM_SNAPSHOT_SERVER_KEYS),
        "prewarm_metrics": list(PREWARM_LEADERBOARD_METRICS),
        "snapshot_count": len(persisted_records),
        "servers_processed": len(snapshots_by_server),
        "snapshots_by_server": snapshots_by_server,
    }


def _build_server_summary_snapshot(
    server_key: str,
    generated_at: datetime,
    *,
    db_path: Path | None = None,
) -> dict[str, object]:
    summary_items = list_historical_server_summaries(server_slug=server_key, db_path=db_path)
    summary_item = summary_items[0] if summary_items else {}
    time_range = summary_item.get("time_range") if isinstance(summary_item, dict) else {}
    return {
        "server_key": server_key,
        "snapshot_type": SNAPSHOT_TYPE_SERVER_SUMMARY,
        "metric": None,
        "window": DEFAULT_SNAPSHOT_WINDOW,
        "generated_at": generated_at,
        "source_range_start": _parse_optional_timestamp(time_range.get("start")),
        "source_range_end": _parse_optional_timestamp(time_range.get("end")),
        "is_stale": False,
        "payload": {
            "server_key": server_key,
            "generated_at": _to_iso(generated_at),
            "item": summary_item,
        },
    }


def _build_weekly_leaderboard_snapshot(
    server_key: str,
    metric: str,
    generated_at: datetime,
    *,
    limit: int,
    db_path: Path | None = None,
) -> dict[str, object]:
    leaderboard_result = list_weekly_leaderboard(
        limit=limit,
        server_id=server_key,
        metric=metric,
        db_path=db_path,
    )
    return {
        "server_key": server_key,
        "snapshot_type": SNAPSHOT_TYPE_WEEKLY_LEADERBOARD,
        "metric": metric,
        "window": DEFAULT_WEEKLY_SNAPSHOT_WINDOW,
        "generated_at": generated_at,
        "source_range_start": _parse_optional_timestamp(leaderboard_result.get("window_start")),
        "source_range_end": _parse_optional_timestamp(leaderboard_result.get("window_end")),
        "is_stale": False,
        "payload": {
            "server_key": server_key,
            "metric": metric,
            "limit": limit,
            "generated_at": _to_iso(generated_at),
            **leaderboard_result,
        },
    }


def _build_monthly_leaderboard_snapshot(
    server_key: str,
    metric: str,
    generated_at: datetime,
    *,
    limit: int,
    db_path: Path | None = None,
) -> dict[str, object]:
    leaderboard_result = list_monthly_leaderboard(
        limit=limit,
        server_id=server_key,
        metric=metric,
        db_path=db_path,
    )
    return {
        "server_key": server_key,
        "snapshot_type": SNAPSHOT_TYPE_MONTHLY_LEADERBOARD,
        "metric": metric,
        "window": DEFAULT_MONTHLY_SNAPSHOT_WINDOW,
        "generated_at": generated_at,
        "source_range_start": _parse_optional_timestamp(leaderboard_result.get("window_start")),
        "source_range_end": _parse_optional_timestamp(leaderboard_result.get("window_end")),
        "is_stale": False,
        "payload": {
            "server_key": server_key,
            "metric": metric,
            "limit": limit,
            "generated_at": _to_iso(generated_at),
            **leaderboard_result,
        },
    }


def _build_recent_matches_snapshot(
    server_key: str,
    generated_at: datetime,
    *,
    limit: int,
    db_path: Path | None = None,
) -> dict[str, object]:
    items = list_recent_historical_matches(
        limit=limit,
        server_slug=server_key,
        db_path=db_path,
    )
    closed_points = [
        _parse_optional_timestamp(item.get("closed_at"))
        for item in items
        if isinstance(item, dict) and item.get("closed_at")
    ]
    return {
        "server_key": server_key,
        "snapshot_type": SNAPSHOT_TYPE_RECENT_MATCHES,
        "metric": None,
        "window": DEFAULT_SNAPSHOT_WINDOW,
        "generated_at": generated_at,
        "source_range_start": min(closed_points) if closed_points else None,
        "source_range_end": max(closed_points) if closed_points else None,
        "is_stale": False,
        "payload": {
            "server_key": server_key,
            "limit": limit,
            "generated_at": _to_iso(generated_at),
            "items": items,
        },
    }


def _build_monthly_mvp_snapshot(
    server_key: str,
    generated_at: datetime,
    *,
    limit: int,
    db_path: Path | None = None,
) -> dict[str, object]:
    ranking_result = list_monthly_mvp_ranking(
        limit=limit,
        server_id=server_key,
        db_path=db_path,
    )
    month_key = str(ranking_result.get("window_start") or "")[:7] or None
    return {
        "server_key": server_key,
        "snapshot_type": SNAPSHOT_TYPE_MONTHLY_MVP,
        "metric": None,
        "window": DEFAULT_MONTHLY_SNAPSHOT_WINDOW,
        "generated_at": generated_at,
        "source_range_start": _parse_optional_timestamp(ranking_result.get("window_start")),
        "source_range_end": _parse_optional_timestamp(ranking_result.get("window_end")),
        "is_stale": False,
        "payload": {
            "server_key": server_key,
            "limit": limit,
            "month_key": month_key,
            "generated_at": _to_iso(generated_at),
            **ranking_result,
        },
    }


def _resolve_snapshot_target_keys(
    *,
    server_key: str | None,
    db_path: Path | None = None,
) -> list[str]:
    """Expand targeted rebuilds so the logical global aggregate stays in sync."""
    if not server_key:
        return list_snapshot_server_keys(db_path=db_path)

    normalized_server_key = server_key.strip()
    if not normalized_server_key:
        return list_snapshot_server_keys(db_path=db_path)
    if normalized_server_key == ALL_SERVERS_SLUG:
        return [ALL_SERVERS_SLUG]

    return [normalized_server_key, ALL_SERVERS_SLUG]


def _parse_optional_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _to_iso(value: datetime) -> str:
    return _as_utc(value).isoformat().replace("+00:00", "Z")
