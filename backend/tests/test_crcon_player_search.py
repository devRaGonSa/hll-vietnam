from __future__ import annotations

import json
import os
import unittest
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
from unittest.mock import Mock, patch

from app import payloads
from app.crcon.api import CrconApiClient
from app.crcon.dto import CrconPlayerHistoryEntry, CrconPlayerHistoryPage
from app.crcon.models import (
    CrconApiAuthenticationError,
    CrconApiError,
    CrconPlayerHistoryState,
)
from app.services.player_search import PlayerSearchBinding, PlayerSearchService
from app.domain import PlayerIdentity, player_id_from
from app.server_targets import ServerTarget


SECRET = "task-303-secret"


class _Response:
    def __init__(self, payload: object) -> None:
        self._raw = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return self._raw


def _target(key: str, number: int, game: str = "hll") -> ServerTarget:
    return ServerTarget(
        key=key,
        display_name=key,
        server_number=number,
        game=game,  # type: ignore[arg-type]
        crcon_base_url=f"https://{key}.invalid",
    )


def _entry(
    player_id: str,
    name: str,
    *,
    last_seen: datetime | None = None,
) -> CrconPlayerHistoryEntry:
    return CrconPlayerHistoryEntry(
        identity=PlayerIdentity(player_id=player_id_from(player_id), display_name=name),  # type: ignore[arg-type]
        names=(name,),
        last_seen_at=last_seen,
    )


class CrconPlayerHistoryClientTests(unittest.TestCase):
    def test_authenticated_get_is_bounded_typed_and_drops_moderation_fields(self) -> None:
        requests = []

        def transport(request, _timeout):
            requests.append(request)
            return _Response(
                {
                    "result": {
                        "total": 1,
                        "page": 1,
                        "page_size": 10,
                        "players": [
                            {
                                "player_id": "opaque-value",
                                "steam_id": None,
                                "names_by_match": ["Águila", "Alias"],
                                "soldier": {
                                    "name": "Águila",
                                    "eos_id": "explicit-eos",
                                    "platform": "steam",
                                },
                                "account": {"name": None},
                                "first_seen_timestamp_ms": 1_700_000_000_000,
                                "last_seen_timestamp_ms": 1_700_000_100_000,
                                "received_actions": [{"reason": SECRET}],
                                "blacklists": [{"reason": SECRET}],
                                "watchlist": {"reason": SECRET},
                            }
                        ],
                    }
                }
            )

        client = CrconApiClient(
            base_url="https://fixture.invalid",
            timeout_seconds=1,
            headers={"Authorization": f"Bearer {SECRET}"},
            transport=transport,
        )
        page = client.get_players_history(player_name="Ág", page=1, page_size=10)

        self.assertEqual(page.total, 1)
        self.assertEqual(str(page.players[0].identity.player_id), "opaque-value")
        self.assertEqual(page.players[0].identity.eos_id, "explicit-eos")
        self.assertFalse(hasattr(page.players[0], "received_actions"))
        query = parse_qs(urlsplit(requests[0].full_url).query)
        self.assertEqual(query["player_name"], ["Ág"])
        self.assertEqual(query["page_size"], ["10"])
        self.assertEqual(query["exact_name_match"], ["false"])
        self.assertEqual(requests[0].get_header("Authorization"), f"Bearer {SECRET}")

    def test_filters_and_pagination_fail_closed_before_transport(self) -> None:
        client = CrconApiClient(
            base_url="https://fixture.invalid",
            timeout_seconds=1,
            transport=lambda *_args: self.fail("transport should not run"),
        )
        for kwargs in (
            {},
            {"player_name": "A", "player_id": "opaque"},
            {"player_name": "A", "page": 0},
            {"player_name": "A", "page_size": 101},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                client.get_players_history(**kwargs)

    def test_auth_and_transport_failures_are_sanitized(self) -> None:
        auth_client = CrconApiClient(
            base_url="https://fixture.invalid",
            timeout_seconds=1,
            headers={"Authorization": f"Bearer {SECRET}"},
            transport=lambda *_args: (_ for _ in ()).throw(
                HTTPError("https://fixture.invalid", 403, SECRET, None, None)
            ),
        )
        with self.assertRaises(CrconApiAuthenticationError) as auth_error:
            auth_client.get_players_history(player_name="A")
        self.assertNotIn(SECRET, str(auth_error.exception))
        unavailable = CrconApiClient(
            base_url="https://fixture.invalid",
            timeout_seconds=1,
            headers={"Authorization": f"Bearer {SECRET}"},
            transport=lambda *_args: (_ for _ in ()).throw(URLError(SECRET)),
        )
        with self.assertRaises(CrconApiError) as api_error:
            unavailable.get_players_history(player_name="A")
        self.assertNotIn(SECRET, str(api_error.exception))

    def test_malformed_upstream_response_fails_cleanly(self) -> None:
        client = CrconApiClient(
            base_url="https://fixture.invalid",
            timeout_seconds=1,
            headers={"Authorization": f"Bearer {SECRET}"},
            transport=lambda *_args: _Response(
                {"result": {"total": "private-invalid", "players": SECRET}}
            ),
        )
        with self.assertRaises(CrconApiError) as error:
            client.get_players_history(player_name="Player")
        self.assertNotIn(SECRET, str(error.exception))


class _Api:
    def __init__(self, pages: list[CrconPlayerHistoryPage | Exception]) -> None:
        self.pages = pages
        self.calls: list[dict[str, object]] = []

    def get_players_history(self, **kwargs):
        self.calls.append(kwargs)
        result = self.pages.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class PlayerSearchServiceTests(unittest.TestCase):
    def test_missing_auth_and_hllv_are_distinct_and_never_call_api(self) -> None:
        bindings = {
            "hll": PlayerSearchBinding(_target("hll", 1), {}),
            "hllv": PlayerSearchBinding(_target("hllv", 2, "hllv"), {}),
        }
        service = PlayerSearchService(
            bindings=bindings,
            api_factory=lambda _binding: self.fail("API must not be called"),
        )
        hll = service.search(query="Player", server_id="hll", limit=10)
        hllv = service.search(query="Player", server_id="hllv", limit=10)
        self.assertEqual(hll["player_history_state"], "AUTH_REQUIRED")
        self.assertEqual(hllv["player_history_state"], "UNVERIFIED_HLLV")

    def test_default_public_search_excludes_unverified_hllv(self) -> None:
        class SyntheticCrossGameService(PlayerSearchService):
            def _search_target(self, binding, *, query, limit):
                return CrconPlayerHistoryState.SUPPORTED, None, (
                    _entry("same-opaque-id", f"Player {binding.target.game}"),
                )

        bindings = {
            "hll": PlayerSearchBinding(
                _target("hll", 1), {"Authorization": f"Bearer {SECRET}"}
            ),
            "hllv": PlayerSearchBinding(
                _target("hllv", 2, "hllv"),
                {"Authorization": f"Bearer {SECRET}"},
            ),
        }
        result = SyntheticCrossGameService(
            bindings=bindings,
            api_factory=lambda _binding: self.fail("synthetic override owns reads"),
        ).search(query="Player", server_id="all", limit=10)
        self.assertEqual(result["aggregate_state"], "AVAILABLE")
        self.assertEqual(result["player_history_state"], "SUPPORTED")
        self.assertEqual(result["item_count"], 1)
        self.assertEqual(result["items"][0]["game"], "hll")
        self.assertEqual([row["game"] for row in result["target_states"]], ["hll"])

    def test_explicit_hllv_search_stays_unverified(self) -> None:
        binding = PlayerSearchBinding(
            _target("hllv", 2, "hllv"), {"Authorization": f"Bearer {SECRET}"}
        )
        result = PlayerSearchService(
            bindings={"hllv": binding},
            api_factory=lambda _binding: self.fail("HLLV API must remain unqueried"),
        ).search(query="Player", server_id="hllv", limit=10)
        self.assertEqual(result["aggregate_state"], "UNAVAILABLE")
        self.assertEqual(result["player_history_state"], "UNVERIFIED_HLLV")

    def test_multitarget_merge_deduplicates_opaque_id_inside_hll_only(self) -> None:
        now = datetime(2026, 8, 23, tzinfo=timezone.utc)
        apis = {
            "one": _Api([CrconPlayerHistoryPage((_entry("opaque", "Player", last_seen=now),), 1, 10, 1)]),
            "two": _Api([CrconPlayerHistoryPage((_entry("opaque", "Alias"),), 1, 10, 1)]),
        }
        bindings = {
            key: PlayerSearchBinding(
                _target(key, index), {"Authorization": f"Bearer {SECRET}"}
            )
            for index, key in enumerate(apis, 1)
        }
        result = PlayerSearchService(
            bindings=bindings, api_factory=lambda binding: apis[binding.target.key]
        ).search(query="Player", server_id="all", limit=10)

        self.assertEqual(result["player_history_state"], "SUPPORTED")
        self.assertEqual(result["item_count"], 1)
        self.assertEqual(result["items"][0]["player_id"], "opaque")
        self.assertEqual(result["items"][0]["servers_seen"], ["one", "two"])
        self.assertIsNone(result["items"][0]["matches_considered"])

    def test_empty_name_page_uses_exact_opaque_id_fallback_without_format_logic(self) -> None:
        opaque = "not-a-platform-shaped-id"
        api = _Api(
            [
                CrconPlayerHistoryPage((), 1, 5, 0),
                CrconPlayerHistoryPage((_entry(opaque, "Player"), _entry("other", "Other")), 1, 5, 2),
            ]
        )
        binding = PlayerSearchBinding(
            _target("one", 1), {"Authorization": f"Bearer {SECRET}"}
        )
        result = PlayerSearchService(
            bindings={"one": binding}, api_factory=lambda _binding: api
        ).search(query=opaque, server_id="one", limit=5)
        self.assertEqual(result["items"][0]["player_id"], opaque)
        self.assertEqual(api.calls[0]["player_name"], opaque)
        self.assertEqual(api.calls[1]["player_id"], opaque)

    def test_empty_name_and_id_results_are_supported_empty(self) -> None:
        api = _Api(
            [CrconPlayerHistoryPage((), 1, 10, 0), CrconPlayerHistoryPage((), 1, 10, 0)]
        )
        binding = PlayerSearchBinding(
            _target("one", 1), {"Authorization": f"Bearer {SECRET}"}
        )
        result = PlayerSearchService(
            bindings={"one": binding}, api_factory=lambda _binding: api
        ).search(query="Nobody", server_id="one", limit=10)
        self.assertEqual(result["player_history_state"], "SUPPORTED")
        self.assertEqual(result["items"], [])
        self.assertEqual(len(api.calls), 2)

    def test_auth_rejection_and_unavailable_do_not_leak_credentials(self) -> None:
        binding = PlayerSearchBinding(
            _target("one", 1), {"Authorization": f"Bearer {SECRET}"}
        )
        for error, expected in (
            (CrconApiAuthenticationError(SECRET), "AUTH_REQUIRED"),
            (CrconApiError(SECRET), "UNAVAILABLE"),
        ):
            with self.subTest(expected=expected):
                result = PlayerSearchService(
                    bindings={"one": binding},
                    api_factory=lambda _binding, error=error: _Api([error]),
                ).search(query="Player", server_id="one", limit=10)
                rendered = json.dumps(result)
                self.assertEqual(result["player_history_state"], expected)
                self.assertNotIn(SECRET, rendered)


class PlayerSearchPayloadSelectionTests(unittest.TestCase):
    def test_crcon_selector_uses_api_search_and_not_postgres_or_legacy(self) -> None:
        service = Mock()
        service.search.return_value = {
            "source": "crcon-api-get-players-history",
            "player_history_state": "SUPPORTED",
            "query": "Player",
            "items": [],
        }
        with (
            patch.dict(os.environ, {"HLL_HISTORICAL_AGGREGATE_SOURCE": "crcon"}),
            patch("app.api.payloads.players.get_crcon_player_search_service", return_value=service),
            patch(
                "app.api.payloads.players.get_historical_aggregate_service",
                side_effect=AssertionError("PostgreSQL search used"),
            ),
            patch(
                "app.api.payloads.players.search_rcon_materialized_players",
                side_effect=AssertionError("legacy search used"),
            ),
        ):
            result = payloads.build_stats_player_search_payload(query=" Player ")
        self.assertEqual(result["data"]["source"], "crcon-api-get-players-history")
        service.search.assert_called_once_with(query="Player", server_id=None, limit=10)

    def test_legacy_selector_remains_immediate_rollback(self) -> None:
        with (
            patch.dict(os.environ, {"HLL_HISTORICAL_AGGREGATE_SOURCE": "legacy"}),
            patch(
                "app.api.payloads.players.search_rcon_materialized_players",
                return_value={
                    "query": "Player",
                    "server_id": None,
                    "source": "legacy",
                    "items": [{"player_id": "opaque"}],
                },
            ),
            patch(
                "app.api.payloads.players.get_crcon_player_search_service",
                side_effect=AssertionError("CRCON search used"),
            ),
        ):
            result = payloads.build_stats_player_search_payload(query="Player")
        self.assertEqual(result["data"]["source"], "legacy")


if __name__ == "__main__":
    unittest.main()
