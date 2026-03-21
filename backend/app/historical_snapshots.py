"""Definitions for persisted precomputed historical snapshots."""

from __future__ import annotations


SNAPSHOT_TYPE_SERVER_SUMMARY = "server-summary"
SNAPSHOT_TYPE_WEEKLY_LEADERBOARD = "weekly-leaderboard"
SNAPSHOT_TYPE_RECENT_MATCHES = "recent-matches"

SUPPORTED_SNAPSHOT_TYPES = frozenset(
    {
        SNAPSHOT_TYPE_SERVER_SUMMARY,
        SNAPSHOT_TYPE_WEEKLY_LEADERBOARD,
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

DEFAULT_SNAPSHOT_WINDOW = "all-time"
DEFAULT_WEEKLY_SNAPSHOT_WINDOW = "7d"


def validate_snapshot_identity(
    *,
    snapshot_type: str,
    metric: str | None = None,
) -> None:
    """Validate the persisted snapshot selectors accepted by the storage layer."""
    if snapshot_type not in SUPPORTED_SNAPSHOT_TYPES:
        raise ValueError(f"Unsupported historical snapshot type: {snapshot_type}")

    if snapshot_type == SNAPSHOT_TYPE_WEEKLY_LEADERBOARD:
        if metric not in SUPPORTED_LEADERBOARD_METRICS:
            raise ValueError(f"Unsupported historical snapshot metric: {metric}")
        return

    if metric is not None:
        raise ValueError(f"Metric is only supported for {SNAPSHOT_TYPE_WEEKLY_LEADERBOARD}.")
