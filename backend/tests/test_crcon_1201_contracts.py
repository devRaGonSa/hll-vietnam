from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from app.crcon import (
    CRCON_MAP_HISTORY_DEFAULT_MAX_ENTRIES,
    CrconApiClient,
    CrconContractStatus,
)
from app.crcon.capabilities import (
    API_ENDPOINTS_12_0_1,
    get_api_contract_status,
    get_contract_evidence_status,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "crcon_12_0_1"


def _fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


class _Response:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


class Crcon1201SanitizedContractTests(unittest.TestCase):
    def _client(self, payload_by_path: dict[str, str], urls: list[str] | None = None):
        def transport(request, _timeout):
            if urls is not None:
                urls.append(request.full_url)
            path = urlsplit(request.full_url).path
            return _Response(_fixture(payload_by_path[path]))

        return CrconApiClient(
            base_url="https://fixture.invalid",
            timeout_seconds=1,
            transport=transport,
        )

    def test_version_and_autodocumentation_match_real_wrapper(self) -> None:
        client = self._client(
            {
                "/api/get_version": "get_version.json",
                "/api/get_api_documentation": "api_documentation.json",
            }
        )

        self.assertEqual(client.get_version(), "12.0.1")
        documentation = client.get_api_documentation()
        selected = {
            endpoint.endpoint: endpoint for endpoint in documentation.endpoints
        }

        self.assertEqual(set(selected), set(API_ENDPOINTS_12_0_1))
        self.assertTrue(
            all(endpoint.allowed_http_methods == ("GET",) for endpoint in selected.values())
        )
        self.assertTrue(
            all(endpoint.permissions_required == () for endpoint in selected.values())
        )
        self.assertIn("currently playing match", selected["get_live_game_stats"].doc_string)
        self.assertIn("reset on disconnect", selected["get_live_scoreboard"].doc_string)

    def test_public_info_parses_real_nested_map_and_config_game(self) -> None:
        client = self._client({"/api/get_public_info": "public_info.json"})

        result = client.get_public_info()

        self.assertEqual(result.game, "hll")
        self.assertEqual(result.current_map.layer, "synthetic_forest_warfare")
        self.assertEqual(result.current_map.map_name, "Synthetic Forest")
        self.assertIsNotNone(result.current_map.started_at)
        self.assertIsNone(result.next_map.started_at)
        self.assertEqual(result.contract_status, CrconContractStatus.SUPPORTED)

    def test_live_game_and_live_scoreboard_keep_distinct_semantics(self) -> None:
        client = self._client(
            {
                "/api/get_live_game_stats": "live_game_stats.json",
                "/api/get_live_scoreboard": "live_scoreboard.json",
            }
        )

        match_stats = client.get_live_game_stats()
        connected_stats = client.get_live_scoreboard()

        self.assertEqual(str(match_stats.players[0].identity.player_id), "opaque-player-001")
        self.assertEqual(match_stats.players[0].identity.platform, "steam")
        self.assertIsNone(match_stats.players[0].identity.steam_id)
        self.assertIsNone(match_stats.players[0].identity.eos_id)
        self.assertEqual(str(connected_stats.players[0].identity.player_id), "opaque-player-002")
        self.assertEqual(connected_stats.players[0].identity.platform, "epic")
        self.assertIsNotNone(match_stats.observed_at)
        self.assertEqual(connected_stats.refresh_interval_seconds, 60)

    def test_live_scoreboard_accepts_observed_empty_stats(self) -> None:
        client = self._client(
            {"/api/get_live_scoreboard": "live_scoreboard_empty.json"}
        )

        result = client.get_live_scoreboard()

        self.assertEqual(result.players, ())
        self.assertIsNotNone(result.observed_at)

    def test_scoreboard_maps_paginates_without_embedded_player_stats(self) -> None:
        urls: list[str] = []
        client = self._client(
            {"/api/get_scoreboard_maps": "scoreboard_maps.json"}, urls
        )

        result = client.get_scoreboard_maps(page=1, limit=2, server_number=1)

        self.assertEqual((result.page, result.page_size, result.total), (1, 2, 6))
        self.assertTrue(all(match.player_stats_count == 0 for match in result.maps))
        self.assertEqual(result.maps[0].map_id, "9001")
        self.assertIsNone(result.maps[0].game)
        self.assertEqual(
            parse_qs(urlsplit(urls[0]).query),
            {"page": ["1"], "limit": ["2"], "server_number": ["1"]},
        )

    def test_map_scoreboard_has_detail_weapons_scores_and_encounters(self) -> None:
        client = self._client(
            {"/api/get_map_scoreboard": "map_scoreboard.json"}
        )

        result = client.get_map_scoreboard(map_id="9001")

        self.assertTrue(result.supports_match_detail)
        self.assertEqual(result.match.map_id, "9001")
        self.assertEqual(result.match.score.allied, 5)
        self.assertEqual(result.players[0].kills, 14)
        self.assertEqual(result.players[0].weapons, (("Synthetic Rifle", 14),))
        self.assertEqual(result.players[0].encounters[0].action, "KILL")
        self.assertEqual(result.players[0].encounters[0].player_id, "opaque-player-002")

    def test_map_history_is_recent_redis_history_not_permanent_history(self) -> None:
        client = self._client({"/api/get_map_history": "map_history.json"})

        result = client.get_map_history()

        self.assertTrue(result.recent_only)
        self.assertEqual(
            result.default_max_entries,
            CRCON_MAP_HISTORY_DEFAULT_MAX_ENTRIES,
        )
        self.assertEqual(len(result.maps), 2)
        self.assertEqual(result.maps[0].player_stats_count, 1)
        self.assertIsNone(result.maps[0].ended_at)

    def test_previous_map_supports_real_value_and_source_verified_null(self) -> None:
        present = self._client({"/api/get_previous_map": "previous_map.json"})
        empty = self._client({"/api/get_previous_map": "previous_map_empty.json"})

        self.assertEqual(present.get_previous_map().match.layer, "synthetic_valley_offensive")
        self.assertIsNone(empty.get_previous_map().match)

    def test_hll_and_hllv_evidence_are_never_collapsed(self) -> None:
        for endpoint in API_ENDPOINTS_12_0_1:
            self.assertEqual(
                get_api_contract_status(endpoint, game="hll"),
                CrconContractStatus.SUPPORTED,
            )
            self.assertEqual(
                get_api_contract_status(endpoint, game="hllv"),
                CrconContractStatus.UNVERIFIED,
            )

        self.assertEqual(
            get_contract_evidence_status("identity_explicit_steam_id", game="hll"),
            CrconContractStatus.UNSUPPORTED,
        )
        self.assertEqual(
            get_contract_evidence_status("identity_explicit_eos_id", game="hllv"),
            CrconContractStatus.UNVERIFIED,
        )
        self.assertEqual(
            get_contract_evidence_status("postgres_map_history", game="hll"),
            CrconContractStatus.UNVERIFIED,
        )
        self.assertEqual(
            get_contract_evidence_status("logs_game_string_filter", game="hll"),
            CrconContractStatus.UNSUPPORTED,
        )

    def test_every_1201_fixture_declares_provenance_and_contains_no_real_ids(self) -> None:
        for path in FIXTURE_DIR.glob("*.json"):
            fixture = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn(fixture["source"], {"synthetic", "sanitized_real"})
            self.assertEqual(fixture["verified_version"], "12.0.1")
            self.assertIn(fixture["verified_game"], {"hll", "hllv", None})
            self.assertIn(
                fixture["verification_status"],
                {"supported", "unsupported", "unverified"},
            )

        fixture_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(FIXTURE_DIR.glob("*.json"))
            if path.name != "metadata.json"
        )
        self.assertIsNone(re.search(r"\b7656119\d{10}\b", fixture_text))
        self.assertNotIn("postgresql://", fixture_text.lower())
        self.assertNotIn("authorization", fixture_text.lower())
        self.assertNotIn("bearer ", fixture_text.lower())


if __name__ == "__main__":
    unittest.main()
