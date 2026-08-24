from __future__ import annotations

import json
import os
import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch

from app.api.payloads.static import build_health_payload
from app.config import (
    get_current_match_source,
    get_historical_aggregate_source,
    get_historical_match_source,
    get_server_list_source,
)
from app.server_targets import ServerTarget
from app.services.current_match import (
    CurrentMatchSnapshot,
    CurrentMatchSummary,
    MatchIdentityKind,
)
from app.services.history import (
    HistoricalMatchDetail,
    HistoricalMatchPage,
    HistoricalMatchRecord,
)
from app.tools.verify_crcon_first_readers import (
    LegacyReaderAccessError,
    guard_legacy_readers,
    verify_canonical_routes,
)


NOW = datetime(2026, 8, 24, 12, tzinfo=UTC)
SELECTORS = {
    "HLL_SERVER_LIST_SOURCE": "crcon",
    "HLL_CURRENT_MATCH_SOURCE": "crcon",
    "HLL_HISTORICAL_MATCH_SOURCE": "crcon",
    "HLL_HISTORICAL_AGGREGATE_SOURCE": "crcon",
}
TARGETS = (
    ServerTarget(
        key="hll-one",
        display_name="Synthetic HLL 1",
        server_number=1,
        game="hll",
        crcon_base_url="https://hll-one.invalid",
        capabilities=frozenset({"live_state", "historical_maps"}),
    ),
    ServerTarget(
        key="hll-two",
        display_name="Synthetic HLL 2",
        server_number=2,
        game="hll",
        crcon_base_url="https://hll-two.invalid",
        capabilities=frozenset({"live_state", "historical_maps"}),
    ),
    ServerTarget(
        key="hllv-one",
        display_name="Synthetic HLLV 1",
        server_number=3,
        game="hllv",
        crcon_base_url="https://hllv-one.invalid",
        capabilities=frozenset({"live_state", "historical_maps"}),
    ),
)


def _environment() -> dict[str, str]:
    return {
        **SELECTORS,
        "HLL_SERVER_TARGETS": json.dumps(
            [
                {
                    "key": target.key,
                    "display_name": target.display_name,
                    "server_number": target.server_number,
                    "game": target.game,
                    "crcon_base_url": target.crcon_base_url,
                    "capabilities": sorted(target.capabilities),
                }
                for target in TARGETS
            ]
        ),
    }


def _snapshot(server_slug: str) -> CurrentMatchSnapshot:
    return CurrentMatchSnapshot(
        server_slug=server_slug,
        match_id=f"synthetic-{server_slug}-match",
        identity_kind=MatchIdentityKind.CANONICAL,
        summary=CurrentMatchSummary(
            server_slug=server_slug,
            server_name=server_slug,
            map_name="Synthetic Map",
            layer="synthetic_layer",
            mode="warfare",
            started_at=NOW,
            allied_score=1,
            axis_score=0,
            remaining_seconds=600,
            player_count=0,
            max_player_count=100,
            allied_count=0,
            axis_count=0,
        ),
        players=(),
        kills=(),
        killfeed_truncated=False,
        version="task313",
        observed_at=NOW,
        source_states=(),
        degraded=False,
        degraded_reasons=(),
    )


class _FakeCrconApi:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def current_snapshot(self, server_slug: str) -> CurrentMatchSnapshot:
        self.calls.append(("current", server_slug))
        return _snapshot(server_slug)

    def recent_match(self, target: ServerTarget):
        self.calls.append(("recent", target.key))
        return SimpleNamespace(
            map_id=f"opaque-{target.key}",
            started_at=NOW,
            ended_at=NOW,
            layer="synthetic_layer",
            map_name="Synthetic Map",
            game=target.game,
            mode="warfare",
            match_time_seconds=0,
            score=SimpleNamespace(allied=1, axis=0),
        )

    def search(self, query: str) -> dict[str, object]:
        self.calls.append(("search", query))
        return {
            "source": "fake-crcon-api",
            "aggregate_state": "AVAILABLE",
            "query": query,
            "items": [],
        }


class _FakeCrconRepository:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str | None]] = []

    def server_summary(self, server_id: str | None) -> dict[str, object]:
        self.calls.append(("summary", server_id))
        return {
            "aggregate_state": "AVAILABLE",
            "server_slug": server_id or "all-servers",
            "found": False,
            "item": None,
        }

    def ranking(self, server_id: str | None) -> dict[str, object]:
        self.calls.append(("ranking", server_id))
        return {
            "aggregate_state": "AVAILABLE",
            "server_id": server_id or "all-servers",
            "generated_at": NOW.isoformat(),
            "items": [],
        }

    def player_profile(self, player_id: str) -> dict[str, object]:
        self.calls.append(("profile", player_id))
        return {
            "aggregate_state": "AVAILABLE",
            "player_id": player_id,
            "player_name": None,
            "matches_considered": 0,
        }


class _FakeServerItem:
    captured_at = NOW
    public_info = object()

    def to_frontend_dict(self) -> dict[str, object]:
        return {"server_slug": "synthetic", "freshness": "fresh"}


class _FakeServerListService:
    def __init__(self, api: _FakeCrconApi) -> None:
        self.api = api

    def get_server_list(self):
        self.api.calls.append(("servers", "all"))
        return SimpleNamespace(
            items=(_FakeServerItem(),),
            observed_at=NOW,
            refresh_status="success",
            errors=(),
            cache_hit=False,
        )


class _FakeCurrentMatchService:
    def __init__(self, api: _FakeCrconApi, repository: _FakeCrconRepository) -> None:
        self.api = api
        self.repository = repository

    def get_snapshot(self, server_slug: str) -> CurrentMatchSnapshot:
        self.repository.calls.append(("current-map", server_slug))
        return self.api.current_snapshot(server_slug)

    @staticmethod
    def project_kills(snapshot: CurrentMatchSnapshot, **_kwargs):
        return snapshot.kills


class _FakeHistoryService:
    def __init__(self, api: _FakeCrconApi) -> None:
        self.api = api
        self.by_key = {target.key: target for target in TARGETS}

    def list_recent_matches(self, *, server_slug: str, page: int, page_size: int):
        target = self.by_key[server_slug]
        match = self.api.recent_match(target)
        return HistoricalMatchPage(
            items=(HistoricalMatchRecord(target, match),),
            page=page,
            page_size=page_size,
            total=1,
        )

    def get_match_detail(self, *, server_slug: str, match_id: str):
        target = self.by_key[server_slug]
        match = self.api.recent_match(target)
        self.api.calls.append(("detail", server_slug))
        assert match_id == match.map_id
        scoreboard = SimpleNamespace(match=match, players=())
        return HistoricalMatchDetail(target=target, scoreboard=scoreboard)


class _FakeAggregateService:
    def __init__(self, repository: _FakeCrconRepository) -> None:
        self.repository = repository

    def server_summary(self, *, server_id: str | None):
        return self.repository.server_summary(server_id)

    def ranking(self, *, server_id: str | None, **_kwargs):
        return self.repository.ranking(server_id)

    def player_profile(self, *, player_id: str, **_kwargs):
        return self.repository.player_profile(player_id)


class _FakePlayerSearchService:
    def __init__(self, api: _FakeCrconApi) -> None:
        self.api = api

    def search(self, *, query: str, **_kwargs):
        return self.api.search(query)


class CrconFirstReaderBoundaryTests(unittest.TestCase):
    def test_all_canonical_routes_dispatch_to_crcon_without_legacy_reads(self) -> None:
        api = _FakeCrconApi()
        repository = _FakeCrconRepository()
        current = _FakeCurrentMatchService(api, repository)
        history = _FakeHistoryService(api)
        aggregate = _FakeAggregateService(repository)
        search = _FakePlayerSearchService(api)
        verifier = SimpleNamespace(record_live=lambda _snapshot: None)

        with (
            patch.dict(os.environ, _environment(), clear=True),
            patch(
                "app.api.payloads.servers.get_crcon_server_list_service",
                return_value=_FakeServerListService(api),
            ),
            patch(
                "app.api.payloads.current_match.get_current_match_snapshot_service",
                return_value=current,
            ),
            patch(
                "app.api.payloads.current_match.get_final_match_verifier",
                return_value=verifier,
            ),
            patch("app.services.history.get_history_service", return_value=history),
            patch(
                "app.api.payloads.rankings.get_historical_aggregate_service",
                return_value=aggregate,
            ),
            patch(
                "app.api.payloads.players.get_historical_aggregate_service",
                return_value=aggregate,
            ),
            patch(
                "app.api.payloads.players.get_crcon_player_search_service",
                return_value=search,
            ),
        ):
            result = verify_canonical_routes(manage_log_streams=False)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["enabled_target_count"], 3)
        self.assertEqual(result["route_count"], 20)
        self.assertEqual(result["detail_route_count"], 3)
        self.assertEqual(result["legacy_reader_access_count"], 0)
        self.assertEqual(sum(call[0] == "current" for call in api.calls), 9)
        self.assertEqual(sum(call[0] == "detail" for call in api.calls), 3)
        self.assertIn(("summary", "all-servers"), repository.calls)
        self.assertIn(("ranking", "all-servers"), repository.calls)
        self.assertTrue(any(call[0] == "profile" for call in repository.calls))

    def test_guard_raises_recognizable_error_at_actual_payload_use_site(self) -> None:
        from app.api.payloads import servers

        with (
            patch.dict(os.environ, {"HLL_SERVER_LIST_SOURCE": "legacy"}, clear=True),
            guard_legacy_readers(),
            self.assertRaisesRegex(
                LegacyReaderAccessError,
                r"legacy-reader-access:app\.api\.payloads\.servers\._build_legacy_servers_payload",
            ),
        ):
            servers.build_servers_payload()

    def test_verifier_refuses_mixed_selector_configuration(self) -> None:
        environment = {**_environment(), "HLL_CURRENT_MATCH_SOURCE": "legacy"}
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaisesRegex(
                RuntimeError, "all-four-effective-selectors-must-be-crcon"
            ):
                verify_canonical_routes(manage_log_streams=False)

    def test_health_reports_effective_selectors_and_labels_old_policy_scope(self) -> None:
        with patch.dict(os.environ, _environment(), clear=True):
            payload = build_health_payload()
        self.assertEqual(
            {
                key: payload[key]
                for key in (
                    "server_list_source",
                    "current_match_source",
                    "historical_match_source",
                    "historical_aggregate_source",
                )
            },
            {
                "server_list_source": "crcon",
                "current_match_source": "crcon",
                "historical_match_source": "crcon",
                "historical_aggregate_source": "crcon",
            },
        )
        self.assertEqual(
            payload["live_runtime_policy_scope"],
            "legacy-rollback-transport-metadata",
        )
        self.assertEqual(
            payload["historical_runtime_policy_scope"],
            "legacy-rollback-transport-metadata",
        )

    def test_legacy_and_shadow_selector_values_remain_accepted(self) -> None:
        environment = {
            "HLL_SERVER_LIST_SOURCE": "legacy",
            "HLL_CURRENT_MATCH_SOURCE": "shadow",
            "HLL_HISTORICAL_MATCH_SOURCE": "legacy",
            "HLL_HISTORICAL_AGGREGATE_SOURCE": "legacy",
        }
        with patch.dict(os.environ, environment, clear=True):
            self.assertEqual(get_server_list_source(), "legacy")
            self.assertEqual(get_current_match_source(), "shadow")
            self.assertEqual(get_historical_match_source(), "legacy")
            self.assertEqual(get_historical_aggregate_source(), "legacy")


if __name__ == "__main__":
    unittest.main()
