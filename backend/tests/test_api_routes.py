from __future__ import annotations

from contextlib import ExitStack
from http import HTTPStatus
import unittest
from unittest.mock import patch
from urllib.parse import urlparse

import app.api.payloads as payload_facade
from app.api.routes import DOMAIN_ROUTERS, resolve_get_payload
from app.api.routes import current_match as current_match_routes
from app.api.routes import history as history_routes
from app.api.routes import players as player_routes
from app.api.routes import rankings as ranking_routes
from app.api.routes import servers as server_routes


PUBLIC_ROUTE_CASES = {
    "static": (
        "/health",
        "/api/community",
        "/api/trailer",
        "/api/discord",
    ),
    "servers": (
        "/api/servers",
        "/api/servers/latest",
        "/api/servers/history?limit=20",
        "/api/servers/server-one/history?limit=20",
    ),
    "current_match": (
        "/api/current-match/snapshot?server=server-one",
        "/api/current-match?server=server-one",
        "/api/current-match/kills?server=server-one&limit=20",
        "/api/current-match/players?server=server-one",
    ),
    "players": (
        "/api/stats/players/search?q=Player&limit=10",
        "/api/stats/players/opaque-player?timeframe=weekly",
        "/api/historical/player-profile?player=opaque-player",
    ),
    "rankings": (
        "/api/stats/rankings/annual?year=2026&metric=kills&limit=20",
        "/api/ranking?timeframe=weekly&metric=kills&limit=20",
        "/api/historical/weekly-top-kills?limit=20",
        "/api/historical/leaderboard?timeframe=weekly&metric=kills&limit=20",
        "/api/historical/weekly-leaderboard?metric=kills&limit=20",
        "/api/historical/monthly-leaderboard?metric=kills&limit=20",
        "/api/historical/snapshots/leaderboard?timeframe=weekly&metric=kills&limit=20",
        "/api/historical/snapshots/monthly-leaderboard?metric=kills&limit=20",
        "/api/historical/snapshots/weekly-leaderboard?metric=kills&limit=20",
        "/api/historical/snapshots/server-summary?server=server-one",
    ),
    "history": (
        "/api/historical/recent-matches?limit=20&page=1",
        "/api/historical/snapshots/recent-matches?limit=20&page=1",
        "/api/historical/matches/detail?server=server-one&match=opaque-match",
        "/api/historical/server-summary?server=server-one",
    ),
}

REMOVED_PRODUCT_ROUTE_CASES = (
    "/api/historical/monthly-mvp?limit=20",
    "/api/historical/monthly-mvp-v2?limit=20",
    "/api/historical/player-events?view=most-killed&limit=20",
    "/api/historical/snapshots/monthly-mvp?limit=20",
    "/api/historical/snapshots/monthly-mvp-v2?limit=20",
    "/api/historical/snapshots/player-events?view=most-killed&limit=20",
    "/api/historical/elo-mmr/leaderboard?limit=20",
    "/api/historical/elo-mmr/player?player=opaque-player",
)

PATCHED_BUILDERS = {
    server_routes: (
        "build_servers_payload",
        "build_server_latest_payload",
        "build_server_history_payload",
        "build_server_detail_history_payload",
    ),
    current_match_routes: (
        "build_current_match_snapshot_payload",
        "build_current_match_payload",
        "build_current_match_kill_feed_payload",
        "build_current_match_player_stats_payload",
    ),
    player_routes: (
        "build_stats_player_search_payload",
        "build_stats_player_profile_payload",
        "build_historical_player_profile_payload",
    ),
    ranking_routes: (
        "build_annual_ranking_snapshot_payload",
        "build_global_ranking_payload",
        "build_weekly_top_kills_payload",
        "build_historical_leaderboard_payload",
        "build_weekly_leaderboard_payload",
        "build_monthly_leaderboard_payload",
        "build_leaderboard_snapshot_payload",
        "build_monthly_leaderboard_snapshot_payload",
        "build_weekly_leaderboard_snapshot_payload",
        "build_historical_server_summary_snapshot_payload",
    ),
    history_routes: (
        "build_recent_historical_matches_payload",
        "build_recent_historical_matches_snapshot_payload",
        "build_historical_match_detail_payload",
        "build_historical_server_summary_payload",
    ),
}


class ApiRouteRegistryTests(unittest.TestCase):
    def test_registry_order_is_explicit_and_stable(self) -> None:
        self.assertEqual(
            [router.__module__.rsplit(".", 1)[-1] for router in DOMAIN_ROUTERS],
            [
                "static",
                "servers",
                "current_match",
                "players",
                "rankings",
                "history",
            ],
        )

    def test_every_public_path_has_exactly_one_owner_and_stable_payload_shape(self) -> None:
        with self._patched_builders():
            for domain, paths in PUBLIC_ROUTE_CASES.items():
                for path in paths:
                    with self.subTest(domain=domain, path=path):
                        parsed = urlparse(path)
                        matched = [
                            result
                            for router in DOMAIN_ROUTERS
                            if (result := router(parsed))[0] is not None
                        ]
                        self.assertEqual(len(matched), 1)
                        status, payload = resolve_get_payload(path)
                        self.assertEqual(status, HTTPStatus.OK)
                        self.assertEqual(payload["status"], "ok")

        self.assertEqual(sum(map(len, PUBLIC_ROUTE_CASES.values())), 29)

    def test_removed_product_routes_use_normal_unknown_route_behavior(self) -> None:
        for path in REMOVED_PRODUCT_ROUTE_CASES:
            with self.subTest(path=path):
                self.assertEqual(resolve_get_payload(path), (None, {}))

    def test_payload_facade_does_not_export_removed_product_builders(self) -> None:
        removed_builders = {
            "build_monthly_mvp_payload",
            "build_monthly_mvp_v2_payload",
            "build_player_event_payload",
            "build_monthly_mvp_snapshot_payload",
            "build_monthly_mvp_v2_snapshot_payload",
            "build_player_event_snapshot_payload",
            "build_elo_mmr_leaderboard_payload",
            "build_elo_mmr_player_payload",
        }
        self.assertTrue(removed_builders.isdisjoint(payload_facade.__all__))
        for builder in removed_builders:
            self.assertFalse(hasattr(payload_facade, builder))

    def test_unknown_route_keeps_unmatched_contract(self) -> None:
        self.assertEqual(resolve_get_payload("/api/not-a-route"), (None, {}))

    def test_player_search_precedes_dynamic_opaque_player_id(self) -> None:
        search_payload = {"status": "ok", "data": {"kind": "search"}}
        profile_payload = {"status": "ok", "data": {"kind": "profile"}}
        with (
            patch.object(
                player_routes,
                "build_stats_player_search_payload",
                return_value=search_payload,
            ) as search_builder,
            patch.object(
                player_routes,
                "build_stats_player_profile_payload",
                return_value=profile_payload,
            ) as profile_builder,
        ):
            search_status, search = resolve_get_payload(
                "/api/stats/players/search?q=Player"
            )
            profile_status, profile = resolve_get_payload(
                "/api/stats/players/search-shadow?timeframe=monthly"
            )

        self.assertEqual((search_status, search), (HTTPStatus.OK, search_payload))
        self.assertEqual((profile_status, profile), (HTTPStatus.OK, profile_payload))
        search_builder.assert_called_once_with(query="Player", server_id=None, limit=10)
        profile_builder.assert_called_once_with(
            player_id="search-shadow",
            server_id=None,
            timeframe="monthly",
        )

    def test_exact_server_history_precedes_dynamic_server_history(self) -> None:
        history_payload = {"status": "ok", "data": {"kind": "history"}}
        detail_payload = {"status": "ok", "data": {"kind": "detail"}}
        with (
            patch.object(
                server_routes,
                "build_server_history_payload",
                return_value=history_payload,
            ) as history_builder,
            patch.object(
                server_routes,
                "build_server_detail_history_payload",
                return_value=detail_payload,
            ) as detail_builder,
        ):
            history_status, history = resolve_get_payload(
                "/api/servers/history?limit=7"
            )
            detail_status, detail = resolve_get_payload(
                "/api/servers/server-one/history?limit=8"
            )

        self.assertEqual((history_status, history), (HTTPStatus.OK, history_payload))
        self.assertEqual((detail_status, detail), (HTTPStatus.OK, detail_payload))
        history_builder.assert_called_once_with(limit=7)
        detail_builder.assert_called_once_with("server-one", limit=8)

    def test_opaque_player_path_is_not_coerced_or_platform_inferred(self) -> None:
        payload = {"status": "ok", "data": {"found": False}}
        with patch.object(
            player_routes,
            "build_stats_player_profile_payload",
            return_value=payload,
        ) as builder:
            status, result = resolve_get_payload(
                "/api/stats/players/steam%3Aopaque%2Fvalue?server=server-one"
            )

        self.assertEqual((status, result), (HTTPStatus.OK, payload))
        builder.assert_called_once_with(
            player_id="steam%3Aopaque%2Fvalue",
            server_id="server-one",
            timeframe="weekly",
        )

    def test_history_parameters_and_empty_match_payload_are_forwarded(self) -> None:
        recent_payload = {"status": "ok", "data": {"items": []}}
        detail_payload = {"status": "ok", "data": {"found": False}}
        with (
            patch.object(
                history_routes,
                "build_recent_historical_matches_snapshot_payload",
                return_value=recent_payload,
            ) as recent_builder,
            patch.object(
                history_routes,
                "build_historical_match_detail_payload",
                return_value=detail_payload,
            ) as detail_builder,
        ):
            recent_status, recent = resolve_get_payload(
                "/api/historical/snapshots/recent-matches?server=server-one&limit=6&page=2"
            )
            detail_status, detail = resolve_get_payload(
                "/api/historical/matches/detail?server=server-one&match=unknown-match"
            )

        self.assertEqual((recent_status, recent), (HTTPStatus.OK, recent_payload))
        self.assertEqual((detail_status, detail), (HTTPStatus.OK, detail_payload))
        recent_builder.assert_called_once_with(limit=6, server_slug="server-one", page=2)
        detail_builder.assert_called_once_with(
            server_slug="server-one",
            match_id="unknown-match",
        )

    def test_invalid_parameters_keep_exact_status_and_error_messages(self) -> None:
        cases = (
            ("/api/servers/history?limit=0", "Invalid limit parameter"),
            ("/api/stats/players/search", "Query parameter is required"),
            ("/api/stats/players/?timeframe=weekly", "Player id is required"),
            ("/api/stats/players/opaque?timeframe=yearly", "Invalid timeframe parameter"),
            ("/api/stats/rankings/annual?metric=deaths", "Invalid metric parameter"),
            ("/api/ranking?timeframe=annual", "Invalid year parameter"),
            ("/api/historical/leaderboard?metric=teamkills", "Invalid metric parameter"),
            ("/api/historical/recent-matches?page=0", "Invalid page parameter"),
            ("/api/historical/matches/detail?server=server-one", "Match parameter is required"),
            ("/api/historical/player-profile", "Player parameter is required"),
        )
        for path, message in cases:
            with self.subTest(path=path):
                status, payload = resolve_get_payload(path)
                self.assertEqual(status, HTTPStatus.BAD_REQUEST)
                self.assertEqual(payload, {"status": "error", "message": message})

    def test_current_match_missing_and_unknown_server_contracts(self) -> None:
        missing_status, missing = resolve_get_payload("/api/current-match/snapshot")
        with patch.object(
            current_match_routes,
            "get_trusted_public_scoreboard_origin",
            return_value=None,
        ):
            unknown_status, unknown = resolve_get_payload(
                "/api/current-match?server=unknown"
            )

        self.assertEqual(missing_status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            missing,
            {"status": "error", "message": "Server parameter is required"},
        )
        self.assertEqual(unknown_status, HTTPStatus.NOT_FOUND)
        self.assertEqual(
            unknown,
            {"status": "error", "message": "Current match server is not supported"},
        )

    def _patched_builders(self) -> ExitStack:
        stack = ExitStack()
        payload = {"status": "ok", "data": {"route": "stub"}}
        for module, builders in PATCHED_BUILDERS.items():
            for builder in builders:
                stack.enter_context(patch.object(module, builder, return_value=payload))
        stack.enter_context(
            patch.object(
                current_match_routes,
                "get_trusted_public_scoreboard_origin",
                return_value=object(),
            )
        )
        return stack


if __name__ == "__main__":
    unittest.main()
