"""Stable compatibility exports for all public API payload builders."""

from .current_match import (
    _build_legacy_current_match_payload,
    _build_legacy_current_match_player_stats_payload,
    build_current_match_kill_feed_payload,
    build_current_match_payload,
    build_current_match_player_stats_payload,
    build_current_match_snapshot_payload,
)
from .history import (
    _build_recent_historical_matches_legacy_snapshot_payload,
    build_historical_match_detail_payload,
    build_historical_server_summary_payload,
    build_recent_historical_matches_payload,
    build_recent_historical_matches_snapshot_payload,
)
from .players import (
    build_historical_player_profile_payload,
    build_stats_player_profile_payload,
    build_stats_player_search_payload,
)
from .rankings import (
    build_annual_ranking_snapshot_payload,
    build_global_ranking_payload,
    build_historical_leaderboard_payload,
    build_historical_server_summary_snapshot_payload,
    build_leaderboard_snapshot_payload,
    build_monthly_leaderboard_payload,
    build_monthly_leaderboard_snapshot_payload,
    build_weekly_leaderboard_payload,
    build_weekly_leaderboard_snapshot_payload,
    build_weekly_top_kills_payload,
)
from .servers import (
    build_server_detail_history_payload,
    build_server_history_payload,
    build_server_latest_payload,
    build_servers_payload,
)
from .static import (
    build_community_payload,
    build_discord_payload,
    build_error_payload,
    build_health_payload,
    build_trailer_payload,
)

__all__ = [
    "build_annual_ranking_snapshot_payload",
    "build_community_payload",
    "build_current_match_kill_feed_payload",
    "build_current_match_payload",
    "build_current_match_player_stats_payload",
    "build_current_match_snapshot_payload",
    "build_discord_payload",
    "build_error_payload",
    "build_global_ranking_payload",
    "build_health_payload",
    "build_historical_leaderboard_payload",
    "build_historical_match_detail_payload",
    "build_historical_player_profile_payload",
    "build_historical_server_summary_payload",
    "build_historical_server_summary_snapshot_payload",
    "build_leaderboard_snapshot_payload",
    "build_monthly_leaderboard_payload",
    "build_monthly_leaderboard_snapshot_payload",
    "build_recent_historical_matches_payload",
    "build_recent_historical_matches_snapshot_payload",
    "build_server_detail_history_payload",
    "build_server_history_payload",
    "build_server_latest_payload",
    "build_servers_payload",
    "build_stats_player_profile_payload",
    "build_stats_player_search_payload",
    "build_trailer_payload",
    "build_weekly_leaderboard_payload",
    "build_weekly_leaderboard_snapshot_payload",
    "build_weekly_top_kills_payload",
]
