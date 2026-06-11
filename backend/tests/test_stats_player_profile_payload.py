from __future__ import annotations

import unittest
from unittest.mock import patch

from app.payloads import build_stats_player_profile_payload
from app.rcon_historical_player_stats import (
    _build_profile_active_time_payload,
    get_rcon_materialized_player_stats,
)


class StatsPlayerProfilePayloadTests(unittest.TestCase):
    def test_player_stats_returns_lightweight_missing_payload_when_period_read_model_is_empty(self) -> None:
        with patch(
            "app.rcon_historical_player_stats._get_player_period_stats_read_model",
            return_value=(None, "player-period-stats-empty"),
        ):
            result = get_rcon_materialized_player_stats(
                player_id="76561198000000000",
                timeframe="weekly",
            )

        self.assertEqual(result["matches_considered"], 0)
        self.assertEqual(result["kpm_status"], "missing_active_time")
        self.assertEqual(result["platform"], "steam")
        self.assertIn("steam", result["external_profile_links"])
        self.assertEqual(result["source"]["missing_reason"], "player-period-stats-empty")
        self.assertFalse(result["source"]["fallback_used"])

    def test_build_stats_player_profile_payload_exposes_ready_real_kpm_and_external_links(self) -> None:
        with patch(
            "app.payloads.get_rcon_materialized_player_stats",
            return_value={
                "player_id": "76561198000000000",
                "player_name": "Steam Player",
                "server_id": "all-servers",
                "timeframe": "weekly",
                "window_start": None,
                "window_end": None,
                "window_kind": "current-week",
                "matches_considered": 4,
                "kills": 20,
                "deaths": 10,
                "teamkills": 0,
                "player_active_seconds": 1200,
                "player_active_minutes": 20.0,
                "kpm": 1.0,
                "kpm_status": "ready",
                "active_time_source": "connection_intervals",
                "active_time_coverage": {
                    "eligible_matches": 4,
                    "real_source_matches": 4,
                    "observed_matches": 4,
                    "total_matches_considered": 4,
                    "eligible_kills": 20,
                    "minimum_active_seconds": 60,
                    "sources": ["connection_intervals"],
                },
                "platform": "steam",
                "steam_id_64": "76561198000000000",
                "external_profile_links": {
                    "steam": "https://steamcommunity.com/profiles/76561198000000000",
                    "hellor": "https://hellor.pro/player/76561198000000000",
                    "hll_records": "https://hllrecords.com/profiles/76561198000000000",
                    "helo": "https://helo-system.de/statistics/players/76561198000000000?series=2024",
                },
                "weekly_ranking": {"metric": "kills", "ranking_position": 4},
                "monthly_ranking": {"metric": "kills", "ranking_position": 7},
                "source": {"primary_source": "rcon"},
            },
        ):
            payload = build_stats_player_profile_payload(
                player_id="76561198000000000",
                timeframe="weekly",
            )

        data = payload["data"]
        self.assertEqual(data["kpm"], 1.0)
        self.assertEqual(data["kpm_status"], "ready")
        self.assertEqual(data["active_time_source"], "connection_intervals")
        self.assertEqual(data["steam_id_64"], "76561198000000000")
        self.assertEqual(data["platform"], "steam")
        self.assertIn("steam", data["external_profile_links"])

    def test_build_stats_player_profile_payload_keeps_kpm_null_when_connection_intervals_are_missing(self) -> None:
        with patch(
            "app.payloads.get_rcon_materialized_player_stats",
            return_value={
                "player_id": "epic-player-id",
                "player_name": "Epic Player",
                "server_id": "all-servers",
                "timeframe": "monthly",
                "window_start": None,
                "window_end": None,
                "window_kind": "current-month",
                "matches_considered": 2,
                "kills": 7,
                "deaths": 4,
                "teamkills": 0,
                "player_active_seconds": None,
                "player_active_minutes": None,
                "kpm": None,
                "kpm_status": "missing_connection_intervals",
                "active_time_source": "event_span_fallback",
                "active_time_coverage": {
                    "eligible_matches": 0,
                    "real_source_matches": 0,
                    "observed_matches": 2,
                    "total_matches_considered": 2,
                    "eligible_kills": 0,
                    "minimum_active_seconds": 60,
                    "sources": ["event_span_fallback"],
                },
                "platform": "epic",
                "epic_id": "0123456789abcdef0123456789abcdef",
                "external_profile_links": {
                    "hellor": "https://hellor.pro/player/0123456789abcdef0123456789abcdef",
                    "hll_records": "https://hllrecords.com/profiles/0123456789abcdef0123456789abcdef",
                },
                "weekly_ranking": {"metric": "kills", "ranking_position": None},
                "monthly_ranking": {"metric": "kills", "ranking_position": None},
                "source": {"primary_source": "rcon"},
            },
        ):
            payload = build_stats_player_profile_payload(
                player_id="0123456789abcdef0123456789abcdef",
                timeframe="monthly",
            )

        data = payload["data"]
        self.assertIsNone(data["kpm"])
        self.assertEqual(data["kpm_status"], "missing_connection_intervals")
        self.assertNotIn("steam", data["external_profile_links"])

    def test_profile_active_time_payload_marks_ready_only_for_real_connection_intervals(self) -> None:
        payload = _build_profile_active_time_payload(
            row={
                "observed_matches": 3,
                "real_source_matches": 3,
                "eligible_matches": 3,
                "player_active_seconds": 600,
                "eligible_kills": 10,
                "eligible_sources": "connection_intervals,connection_intervals_carryover",
                "observed_sources": "connection_intervals,connection_intervals_carryover",
            },
            total_matches_considered=3,
            min_active_seconds=60,
        )

        self.assertEqual(payload["kpm"], 1.0)
        self.assertEqual(payload["kpm_status"], "ready")
        self.assertEqual(payload["active_time_source"], "connection_intervals_mixed")


if __name__ == "__main__":
    unittest.main()
