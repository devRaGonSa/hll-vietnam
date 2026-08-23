from __future__ import annotations

import json
import os
import unittest
from dataclasses import replace
from datetime import UTC, datetime
from http import HTTPStatus
from pathlib import Path
from unittest.mock import patch

from app import payloads
from app.config import get_historical_match_source
from app.crcon.cache import TtlCache
from app.crcon.dto import (
    CrconHistoricalMap,
    CrconMapPage,
    CrconMapScoreboard,
    CrconScore,
    parse_map_scoreboard,
    parse_scoreboard_maps,
)
from app.crcon.models import CrconApiError
from app.services.history import (
    HistoricalMatchDetail,
    HistoryBinding,
    HistoryMatchNotFoundError,
    HistoryService,
    build_crcon_match_detail_payload,
    build_crcon_recent_matches_payload,
)
from app.api.routes import resolve_get_payload
from app.server_targets import ServerTarget


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "crcon_12_0_1"


def _fixture_result(name: str) -> dict[str, object]:
    payload = json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
    return payload["result"]


def _binding(
    slug: str = "server-one",
    *,
    server_number: int = 1,
    game: str = "hll",
) -> HistoryBinding:
    return HistoryBinding(
        target=ServerTarget(
            key=slug,
            display_name=f"Synthetic {slug}",
            server_number=server_number,
            game=game,  # type: ignore[arg-type]
            crcon_base_url=f"https://{slug}.fixture.invalid",
            capabilities=frozenset({"historical_maps"}),
        ),
        api_headers={"X-Synthetic": "fixture"},
    )


class _FakeApi:
    def __init__(
        self,
        *,
        pages: dict[tuple[int, int], CrconMapPage] | None = None,
        detail: CrconMapScoreboard | None = None,
        error: Exception | None = None,
    ) -> None:
        self.pages = pages or {}
        self.detail = detail or CrconMapScoreboard()
        self.error = error
        self.list_calls: list[tuple[int, int, object]] = []
        self.detail_calls: list[object] = []

    def get_scoreboard_maps(self, *, page: int, limit: int, server_number: object):
        self.list_calls.append((page, limit, server_number))
        if self.error:
            raise self.error
        return self.pages.get(
            (page, limit),
            CrconMapPage(page=page, page_size=limit, total=0),
        )

    def get_map_scoreboard(self, *, map_id: object):
        self.detail_calls.append(map_id)
        if self.error:
            raise self.error
        return self.detail


class HistoricalSourceSelectorTests(unittest.TestCase):
    def test_selector_defaults_to_legacy_and_accepts_crcon(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_historical_match_source(), "legacy")
        with patch.dict(
            os.environ, {"HLL_HISTORICAL_MATCH_SOURCE": "CRCON"}, clear=True
        ):
            self.assertEqual(get_historical_match_source(), "crcon")

    def test_selector_rejects_unknown_value(self) -> None:
        with patch.dict(
            os.environ, {"HLL_HISTORICAL_MATCH_SOURCE": "hybrid"}, clear=True
        ):
            with self.assertRaisesRegex(ValueError, "legacy.*crcon"):
                get_historical_match_source()

    def test_legacy_payload_path_is_unchanged(self) -> None:
        sentinel = {"status": "ok", "data": {"source": "legacy-sentinel"}}
        with (
            patch.dict(
                os.environ, {"HLL_HISTORICAL_MATCH_SOURCE": "legacy"}, clear=True
            ),
            patch(
                "app.api.payloads.history._build_recent_historical_matches_legacy_snapshot_payload",
                return_value=sentinel,
            ) as legacy,
        ):
            result = payloads.build_recent_historical_matches_payload(
                server_slug="server-one", limit=20
            )
        self.assertIs(result, sentinel)
        legacy.assert_called_once_with(limit=20, server_slug="server-one")

    def test_crcon_mode_delegates_only_list_and_detail(self) -> None:
        list_sentinel = {"status": "ok", "data": {"source": "crcon-list"}}
        detail_sentinel = {"status": "ok", "data": {"source": "crcon-detail"}}
        with (
            patch.dict(
                os.environ, {"HLL_HISTORICAL_MATCH_SOURCE": "crcon"}, clear=True
            ),
            patch(
                "app.api.payloads.history.build_crcon_recent_matches_payload",
                return_value=list_sentinel,
            ) as list_builder,
            patch(
                "app.api.payloads.history.build_crcon_match_detail_payload",
                return_value=detail_sentinel,
            ) as detail_builder,
        ):
            recent = payloads.build_recent_historical_matches_snapshot_payload(
                server_slug="server-one", limit=25, page=2
            )
            detail = payloads.build_historical_match_detail_payload(
                server_slug="server-one", match_id="opaque-map"
            )
        self.assertIs(recent, list_sentinel)
        self.assertIs(detail, detail_sentinel)
        list_builder.assert_called_once_with(
            limit=25, server_slug="server-one", page=2
        )
        detail_builder.assert_called_once_with(
            server_slug="server-one", match_id="opaque-map"
        )


class RecentHistoryServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.binding = _binding()
        self.fixture_page = parse_scoreboard_maps(_fixture_result("scoreboard_maps.json"))
        self.api = _FakeApi(
            pages={(1, 2): self.fixture_page, (2, 1): replace(self.fixture_page, page=2)}
        )
        self.service = HistoryService(
            bindings={self.binding.target.key: self.binding},
            api_factory=lambda _binding: self.api,
        )

    def test_empty_history_is_successful_and_explicit(self) -> None:
        api = _FakeApi(pages={(1, 100): CrconMapPage(page=1, page_size=100, total=0)})
        service = HistoryService(
            bindings={"server-one": self.binding}, api_factory=lambda _binding: api
        )
        data = build_crcon_recent_matches_payload(
            limit=100, server_slug="server-one", service=service
        )["data"]
        self.assertTrue(data["found"])
        self.assertEqual(data["items"], [])
        self.assertFalse(data["degraded"])
        self.assertFalse(data["fallback_used"])

    def test_list_maps_one_or_many_without_detail_n_plus_one(self) -> None:
        result = self.service.list_recent_matches(
            server_slug="server-one", page=1, page_size=2
        )
        self.assertEqual(len(result.items), 2)
        self.assertEqual(self.api.list_calls, [(1, 2, 1)])
        self.assertEqual(self.api.detail_calls, [])

        data = build_crcon_recent_matches_payload(
            limit=2, server_slug="server-one", service=self.service
        )["data"]
        self.assertEqual(data["items"][0]["match_id"], "9001")
        self.assertIsNone(data["items"][0]["player_count"])
        self.assertEqual(
            data["items"][0]["player_count_status"],
            "unknown-on-scoreboard-maps",
        )

    def test_pagination_and_limit_are_forwarded(self) -> None:
        result = self.service.list_recent_matches(
            server_slug="server-one", page=2, page_size=1
        )
        self.assertEqual(result.page, 2)
        self.assertEqual(result.page_size, 2)  # CRCON fixture response metadata wins.
        self.assertEqual(self.api.list_calls, [(2, 1, 1)])
        with self.assertRaisesRegex(ValueError, "page-size"):
            self.service.list_recent_matches(
                server_slug="server-one", page=1, page_size=101
            )

    def test_multiple_targets_are_merged_and_game_aware(self) -> None:
        hllv_binding = _binding("server-vietnam", server_number=2, game="hllv")
        first = self.fixture_page.maps[0]
        hll_api = _FakeApi(
            pages={(1, 2): CrconMapPage((first,), 1, 2, 1)}
        )
        hllv_map = replace(
            first,
            map_id="hllv-map-opaque",
            server_number=2,
            game="hllv",
            ended_at=datetime(2026, 8, 22, 10, tzinfo=UTC),
        )
        hllv_api = _FakeApi(
            pages={(1, 2): CrconMapPage((hllv_map,), 1, 2, 1)}
        )
        apis = {"server-one": hll_api, "server-vietnam": hllv_api}
        service = HistoryService(
            bindings={"server-one": self.binding, "server-vietnam": hllv_binding},
            api_factory=lambda binding: apis[binding.target.key],
        )
        data = build_crcon_recent_matches_payload(
            limit=2, server_slug="all-servers", service=service
        )["data"]
        self.assertEqual([item["match_id"] for item in data["items"]], ["hllv-map-opaque", "9001"])
        self.assertEqual(data["items"][0]["game"], "hllv")
        self.assertEqual(data["items"][0]["game_contract_status"], "unverified")
        self.assertEqual(hll_api.list_calls, [(1, 2, 1)])
        self.assertEqual(hllv_api.list_calls, [(1, 2, 2)])

    def test_wrong_target_rows_are_filtered_and_reported(self) -> None:
        wrong = replace(self.fixture_page.maps[0], server_number=99)
        api = _FakeApi(pages={(1, 1): CrconMapPage((wrong,), 1, 1, 1)})
        service = HistoryService(
            bindings={"server-one": self.binding}, api_factory=lambda _binding: api
        )
        result = service.list_recent_matches(
            server_slug="server-one", page=1, page_size=1
        )
        self.assertEqual(result.items, ())
        self.assertIn("wrong-target", result.degraded_reasons[0])

    def test_result_winner_and_timestamps_preserve_contract(self) -> None:
        data = build_crcon_recent_matches_payload(
            limit=2, server_slug="server-one", service=self.service
        )["data"]
        item = data["items"][0]
        self.assertEqual(item["result"], {"allied_score": 5, "axis_score": 2, "winner": "allies"})
        self.assertEqual(item["winner"], "allies")
        self.assertEqual(item["started_at"], "2026-08-21T08:00:00Z")
        self.assertEqual(item["closed_at"], "2026-08-21T09:30:00Z")
        self.assertEqual(item["duration_seconds"], 5400)
        self.assertEqual(data["source"], "crcon-scoreboard-maps")
        self.assertEqual(data["selected_source"], "crcon")

    def test_unavailable_and_invalid_target_never_fall_back(self) -> None:
        unavailable = HistoryService(
            bindings={"server-one": self.binding},
            api_factory=lambda _binding: _FakeApi(error=CrconApiError("fixture")),
        )
        data = build_crcon_recent_matches_payload(
            limit=10, server_slug="server-one", service=unavailable
        )["data"]
        self.assertTrue(data["degraded"])
        self.assertFalse(data["fallback_used"])
        missing = build_crcon_recent_matches_payload(
            limit=10, server_slug="missing", service=self.service
        )["data"]
        self.assertTrue(missing["not_found"])
        self.assertEqual(missing["items"], [])

    def test_malformed_list_metadata_is_explicitly_unavailable(self) -> None:
        malformed = HistoryService(
            bindings={"server-one": self.binding},
            api_factory=lambda _binding: _FakeApi(
                pages={(1, 10): CrconMapPage(maps=(), page=None, page_size=None, total=None)}
            ),
        )
        data = build_crcon_recent_matches_payload(
            limit=10, server_slug="server-one", service=malformed
        )["data"]
        self.assertFalse(data["found"])
        self.assertTrue(data["degraded"])
        self.assertIn("malformed", data["degraded_reasons"][0])

    def test_list_cache_is_bounded_and_avoids_duplicate_calls(self) -> None:
        self.service.list_recent_matches(server_slug="server-one", page=1, page_size=2)
        self.service.list_recent_matches(server_slug="server-one", page=1, page_size=2)
        self.assertEqual(len(self.api.list_calls), 1)


class HistoricalMatchDetailTests(unittest.TestCase):
    def setUp(self) -> None:
        self.binding = _binding()
        self.scoreboard = parse_map_scoreboard(_fixture_result("map_scoreboard.json"))
        self.api = _FakeApi(detail=self.scoreboard)
        self.service = HistoryService(
            bindings={"server-one": self.binding}, api_factory=lambda _binding: self.api
        )

    def test_complete_detail_maps_existing_frontend_contract(self) -> None:
        data = build_crcon_match_detail_payload(
            server_slug="server-one",
            match_id="9001",
            service=self.service,
        )["data"]
        self.assertTrue(data["found"])
        self.assertEqual(data["source"], "crcon-map-scoreboard")
        item = data["item"]
        self.assertEqual(item["map"]["pretty_name"], "Synthetic Valley")
        self.assertEqual(item["player_count"], 1)
        player = item["players"][0]
        self.assertEqual(player["player_id"], "opaque-player-001")
        self.assertEqual((player["kills"], player["deaths"], player["teamkills"]), (14, 9, 1))
        self.assertEqual((player["combat"], player["offense"], player["defense"], player["support"]), (140, 320, 80, 210))
        self.assertEqual((player["vehicle_kills"], player["vehicles_destroyed"]), (2, 1))
        self.assertEqual(player["top_weapons"][0], {"name": "Synthetic Rifle", "count": 14})
        self.assertEqual(player["encounters"][0]["player_id"], "opaque-player-002")
        self.assertEqual(player["units"][0]["role"], 3)
        self.assertEqual(player["external_profile_links"], {})
        self.assertNotIn("steam_id_64", player)

    def test_opaque_eos_like_id_never_becomes_steam_link(self) -> None:
        raw = _fixture_result("map_scoreboard.json")
        raw["player_stats"][0]["player_id"] = "EOS-LIKE-OPAQUE-123"
        raw["player_stats"][0]["platform"] = "eos"
        scoreboard = parse_map_scoreboard(raw)
        service = HistoryService(
            bindings={"server-one": self.binding},
            api_factory=lambda _binding: _FakeApi(detail=scoreboard),
        )
        player = build_crcon_match_detail_payload(
            server_slug="server-one", match_id="9001", service=service
        )["data"]["item"]["players"][0]
        self.assertEqual(player["player_id"], "EOS-LIKE-OPAQUE-123")
        self.assertNotIn("steam_id_64", player)
        self.assertNotIn("steam", player["external_profile_links"])

    def test_explicit_steam_metadata_is_the_only_steam_link_source(self) -> None:
        raw = _fixture_result("map_scoreboard.json")
        raw["player_stats"][0]["steaminfo"]["profile"] = {
            "steamid": "76561198000000000"
        }
        scoreboard = parse_map_scoreboard(raw)
        service = HistoryService(
            bindings={"server-one": self.binding},
            api_factory=lambda _binding: _FakeApi(detail=scoreboard),
        )
        player = build_crcon_match_detail_payload(
            server_slug="server-one", match_id="9001", service=service
        )["data"]["item"]["players"][0]
        self.assertEqual(player["steam_id_64"], "76561198000000000")
        self.assertIn("steam", player["external_profile_links"])

    def test_invalid_missing_and_wrong_server_maps_are_safely_rejected(self) -> None:
        missing_service = HistoryService(
            bindings={"server-one": self.binding},
            api_factory=lambda _binding: _FakeApi(detail=CrconMapScoreboard()),
        )
        missing = build_crcon_match_detail_payload(
            server_slug="server-one", match_id="not-a-number", service=missing_service
        )["data"]
        self.assertFalse(missing["found"])
        self.assertFalse(missing["degraded"])

        wrong = replace(
            self.scoreboard,
            match=replace(self.scoreboard.match, server_number=2),
        )
        wrong_service = HistoryService(
            bindings={"server-one": self.binding},
            api_factory=lambda _binding: _FakeApi(detail=wrong),
        )
        with self.assertRaisesRegex(HistoryMatchNotFoundError, "wrong-target"):
            wrong_service.get_match_detail(server_slug="server-one", match_id="9001")

    def test_missing_optional_fields_serialize_without_fabrication(self) -> None:
        match = CrconHistoricalMap(
            map_id="opaque-map",
            server_number=1,
            started_at=datetime(2026, 8, 1, tzinfo=UTC),
            score=CrconScore(),
        )
        api = _FakeApi(detail=CrconMapScoreboard(match=match, players=()))
        service = HistoryService(
            bindings={"server-one": self.binding}, api_factory=lambda _binding: api
        )
        item = build_crcon_match_detail_payload(
            server_slug="server-one", match_id="opaque-map", service=service
        )["data"]["item"]
        self.assertIsNone(item["winner"])
        self.assertIsNone(item["ended_at"])
        self.assertEqual(item["players"], [])

    def test_only_completed_detail_is_cached(self) -> None:
        self.service.get_match_detail(server_slug="server-one", match_id="9001")
        self.service.get_match_detail(server_slug="server-one", match_id="9001")
        self.assertEqual(self.api.detail_calls, ["9001"])

        open_match = replace(self.scoreboard.match, map_id="open-map", ended_at=None)
        open_api = _FakeApi(detail=replace(self.scoreboard, match=open_match))
        open_service = HistoryService(
            bindings={"server-one": self.binding}, api_factory=lambda _binding: open_api
        )
        open_service.get_match_detail(server_slug="server-one", match_id="open-map")
        open_service.get_match_detail(server_slug="server-one", match_id="open-map")
        self.assertEqual(open_api.detail_calls, ["open-map", "open-map"])


class HistoricalRouteCompatibilityTests(unittest.TestCase):
    def test_recent_route_validates_and_forwards_page(self) -> None:
        sentinel = {"status": "ok", "data": {}}
        with patch(
            "app.api.routes.history.build_recent_historical_matches_snapshot_payload",
            return_value=sentinel,
        ) as builder:
            status, payload = resolve_get_payload(
                "/api/historical/snapshots/recent-matches?server=server-one&limit=25&page=3"
            )
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIs(payload, sentinel)
        builder.assert_called_once_with(limit=25, server_slug="server-one", page=3)

    def test_recent_route_rejects_invalid_page(self) -> None:
        status, _payload = resolve_get_payload(
            "/api/historical/snapshots/recent-matches?limit=25&page=0"
        )
        self.assertEqual(status, HTTPStatus.BAD_REQUEST)


if __name__ == "__main__":
    unittest.main()
