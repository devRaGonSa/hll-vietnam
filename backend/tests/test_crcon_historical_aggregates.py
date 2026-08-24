from __future__ import annotations

import os
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from http import HTTPStatus
from unittest.mock import patch

from app import payloads
from app.config import get_historical_aggregate_source
from app.services.historical_aggregates import HistoricalAggregateService, build_window
from app.crcon.capabilities import build_capability_report
from app.crcon.postgres_repository import (
    RANKING_AGGREGATE_CTE,
    RANKING_METRIC_SQL,
    SERVER_AGGREGATE_SQL,
    PostgresCrconRepository,
)
from app.crcon.repository import (
    CrconPlayerProfileAggregate,
    CrconRankingRow,
    CrconServerAggregate,
    CrconServerScope,
)
from app.server_targets import (
    PublicAggregateScopeKind,
    ServerTarget,
    resolve_public_aggregate_scope,
)
from app.api.routes import resolve_get_payload


def _target(key: str, number: int, game: str = "hll") -> ServerTarget:
    return ServerTarget(
        key=key,
        display_name=key,
        server_number=number,
        game=game,
        crcon_base_url=f"https://{key}.invalid",
    )


def _profile(*, steam_id: str | None = None) -> CrconPlayerProfileAggregate:
    return CrconPlayerProfileAggregate(
        player_id="opaque-player-id",
        player_name="Player",
        steam_id=steam_id,
        eos_id=None,
        platform="steam" if steam_id else None,
        matches_played=2,
        record_kills=12,
        kills=20,
        deaths=10,
        teamkills=1,
        deaths_by_teamkill=1,
        time_seconds=1200,
        combat=100,
        offense=20,
        defense=30,
        support=40,
        vehicle_kills=2,
        vehicles_destroyed=1,
        last_seen_at=datetime(2026, 8, 20, tzinfo=timezone.utc),
        servers_seen=(1,),
        kills_ranking_position=3,
    )


class _Repository:
    configured = True

    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        self.profile = _profile()
        self.summary = CrconServerAggregate(
            3,
            8,
            datetime(2026, 8, 1, tzinfo=timezone.utc),
            datetime(2026, 8, 20, tzinfo=timezone.utc),
            (("Carentan", 2),),
        )

    def probe_capabilities(self, **_kwargs):
        schema = {
            "map_history": {"id", "start", "end", "server_number", "map_name", "game"},
            "steam_id_64": {"id", "steam_id_64", "steam_id"},
            "player_soldier": {"playersteamid_id", "eos_id", "name", "level", "platform", "clan_tag"},
            "player_names": {"playersteamid_id", "name", "created", "last_seen"},
            "player_stats": {
                "id", "playersteamid_id", "map_id", "name", "kills", "deaths",
                "teamkills", "deaths_by_tk", "time_seconds", "combat", "offense",
                "defense", "support", "vehicle_kills", "vehicles_destroyed", "weapons",
            },
        }
        return build_capability_report(
            schema_columns=schema, database_configured=True, api_configured=False
        )

    def get_server_aggregate(self, *, scopes):
        self.calls.append(("summary", scopes))
        return self.summary

    def list_rankings(self, **kwargs):
        self.calls.append(("ranking", kwargs))
        return (
            CrconRankingRow(
                "opaque-player-id", "Player", 2, 12, 20, 10, 1, 1200,
                100, 20, 30, 40, 2, 1, 0, 1, 20.0, 1, 3,
            ),
        )

    def get_player_profile_aggregate(self, **kwargs):
        self.calls.append(("profile", kwargs))
        return self.profile

    def close(self):
        return None


class HistoricalAggregateServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = _Repository()
        self.service = HistoricalAggregateService(
            repository=self.repository,
            targets=(_target("server-1", 1), _target("server-2", 2)),
            now=lambda: datetime(2026, 8, 23, 12, tzinfo=timezone.utc),
        )

    def test_weekly_window_is_half_open_from_monday_to_observation(self) -> None:
        window = build_window(
            "weekly", now=datetime(2026, 8, 23, 12, tzinfo=timezone.utc)
        )
        self.assertEqual(window.start, datetime(2026, 8, 17, tzinfo=timezone.utc))
        self.assertEqual(window.end, datetime(2026, 8, 23, 12, tzinfo=timezone.utc))
        annual = build_window(
            "annual", now=datetime(2026, 8, 23, tzinfo=timezone.utc), year=2025
        )
        self.assertEqual(annual.start, datetime(2025, 1, 1, tzinfo=timezone.utc))
        self.assertEqual(annual.end, datetime(2026, 1, 1, tzinfo=timezone.utc))
        alltime = build_window(
            "all-time", now=datetime(2026, 8, 23, tzinfo=timezone.utc)
        )
        self.assertIsNone(alltime.start)
        self.assertIsNone(alltime.end)

    def test_ranking_scopes_all_selected_servers_and_preserves_contract(self) -> None:
        result = self.service.ranking(
            server_id="all", timeframe="monthly", metric="kills", limit=10
        )
        self.assertEqual(result["aggregate_state"], "AVAILABLE")
        self.assertEqual(result["items"][0]["player_id"], "opaque-player-id")
        self.assertEqual(result["items"][0]["kd_ratio"], 2.0)
        scopes = self.repository.calls[-1][1]["scopes"]
        self.assertEqual(tuple(scope.server_number for scope in scopes), (1, 2))
        self.assertTrue(all(scope.game == "hll" for scope in scopes))

    def test_server_summary_preserves_empty_and_populated_frontend_shapes(self) -> None:
        populated = self.service.server_summary(server_id="server-1")
        self.assertTrue(populated["found"])
        self.assertEqual(populated["item"]["matches_count"], 3)
        self.assertEqual(populated["item"]["unique_players"], 8)
        self.assertEqual(
            populated["item"]["top_maps"],
            [{"map_name": "Carentan", "matches_count": 2}],
        )
        self.repository.summary = CrconServerAggregate(0, 0, None, None, ())
        empty = HistoricalAggregateService(
            repository=self.repository,
            targets=(_target("server-1", 1),),
        ).server_summary(server_id="server-1")
        self.assertFalse(empty["found"])
        self.assertEqual(empty["item"]["coverage"]["status"], "empty")

    def test_classic_all_server_query_excludes_hllv(self) -> None:
        service = HistoricalAggregateService(
            repository=self.repository,
            targets=(_target("hll-1", 1), _target("hll-2", 2), _target("hllv", 3, "hllv")),
        )
        result = service.server_summary(server_id="all")
        self.assertEqual(result["aggregate_state"], "AVAILABLE")
        scopes = self.repository.calls[-1][1]
        self.assertEqual(tuple(scope.server_number for scope in scopes), (1, 2))
        self.assertTrue(all(scope.game == "hll" for scope in scopes))

    def test_public_scope_is_typed_and_hllv_remains_explicit(self) -> None:
        targets = (_target("hll-1", 1), _target("hll-2", 2), _target("hllv", 3, "hllv"))
        classic = resolve_public_aggregate_scope(targets, "all-servers")
        explicit = resolve_public_aggregate_scope(targets, "hllv")
        self.assertIsNotNone(classic)
        self.assertIsNotNone(explicit)
        self.assertEqual(classic.kind, PublicAggregateScopeKind.CLASSIC_HLL)
        self.assertEqual(tuple(target.key for target in classic.targets), ("hll-1", "hll-2"))
        self.assertEqual(explicit.kind, PublicAggregateScopeKind.EXPLICIT_TARGET)
        self.assertEqual(explicit.targets[0].game, "hllv")

    def test_explicit_hllv_ranking_creates_only_hllv_scope(self) -> None:
        service = HistoricalAggregateService(
            repository=self.repository,
            targets=(_target("hll-1", 1), _target("hllv", 3, "hllv")),
        )
        result = service.ranking(
            server_id="hllv", timeframe="monthly", metric="kills", limit=10
        )
        self.assertEqual(result["aggregate_state"], "AVAILABLE")
        scopes = self.repository.calls[-1][1]["scopes"]
        self.assertEqual(scopes, (CrconServerScope(3, "hllv"),))

    def test_all_weekly_and_monthly_rankings_use_both_classic_servers(self) -> None:
        service = HistoricalAggregateService(
            repository=self.repository,
            targets=(_target("hll-1", 1), _target("hll-2", 2), _target("hllv", 3, "hllv")),
            now=lambda: datetime(2026, 8, 23, 12, tzinfo=timezone.utc),
        )
        for timeframe in ("weekly", "monthly"):
            with self.subTest(timeframe=timeframe):
                result = service.ranking(
                    server_id="all", timeframe=timeframe, metric="kills", limit=10
                )
                self.assertTrue(result["found"])
                self.assertEqual(result["items"][0]["player_name"], "Player")
                scopes = self.repository.calls[-1][1]["scopes"]
                self.assertEqual(tuple(scope.server_number for scope in scopes), (1, 2))

    def test_individual_classic_rankings_remain_addressable(self) -> None:
        for server_id, number in (("server-1", 1), ("server-2", 2)):
            with self.subTest(server_id=server_id):
                result = self.service.ranking(
                    server_id=server_id, timeframe="weekly", metric="deaths", limit=10
                )
                self.assertTrue(result["found"])
                scopes = self.repository.calls[-1][1]["scopes"]
                self.assertEqual(scopes, (CrconServerScope(number, "hll"),))

    def test_missing_canonical_name_never_falls_back_to_opaque_id(self) -> None:
        original = self.repository.list_rankings
        def unnamed(**kwargs):
            row = original(**kwargs)[0]
            return (replace(row, player_name=None),)
        self.repository.list_rankings = unnamed
        result = self.service.ranking(
            server_id="all", timeframe="weekly", metric="kills", limit=10
        )
        self.assertIsNone(result["items"][0]["player_name"])
        self.assertNotEqual(result["items"][0]["player_name"], "opaque-player-id")

    def test_profile_links_require_explicit_steam_metadata(self) -> None:
        result = self.service.player_profile(
            player_id="opaque-player-id", server_id="server-1", timeframe="weekly"
        )
        self.assertEqual(result["external_profile_links"], {})
        self.repository.profile = _profile(steam_id="76561198000000000")
        second = HistoricalAggregateService(
            repository=self.repository,
            targets=(_target("server-1", 1),),
            now=lambda: datetime(2026, 8, 23, 12, tzinfo=timezone.utc),
        ).player_profile(
            player_id="opaque-player-id", server_id="server-1", timeframe="weekly"
        )
        self.assertIn("76561198000000000", second["external_profile_links"]["steam"])
        eos_like = "0123456789abcdef0123456789abcdef"
        self.repository.profile = replace(
            _profile(), player_id=eos_like, eos_id=None, steam_id=None
        )
        opaque = HistoricalAggregateService(
            repository=self.repository, targets=(_target("server-1", 1),)
        ).player_profile(
            player_id=eos_like, server_id="server-1", timeframe="weekly"
        )
        self.assertEqual(opaque["external_profile_links"], {})
        self.repository.profile = replace(_profile(), eos_id=eos_like)
        explicit_eos = HistoricalAggregateService(
            repository=self.repository, targets=(_target("server-1", 1),)
        ).player_profile(
            player_id="opaque", server_id="server-1", timeframe="weekly"
        )
        self.assertEqual(explicit_eos["epic_id"], eos_like)

    def test_selector_defaults_to_legacy_and_rejects_unknown(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_historical_aggregate_source(), "legacy")
        with patch.dict(
            os.environ, {"HLL_HISTORICAL_AGGREGATE_SOURCE": "CRCON"}, clear=True
        ):
            self.assertEqual(get_historical_aggregate_source(), "crcon")
        with patch.dict(
            os.environ, {"HLL_HISTORICAL_AGGREGATE_SOURCE": "shadow"}, clear=True
        ):
            with self.assertRaises(ValueError):
                get_historical_aggregate_source()

    def test_sql_is_bounded_scoped_and_contains_no_mutation(self) -> None:
        sql = "\n".join([SERVER_AGGREGATE_SQL, RANKING_AGGREGATE_CTE]).upper()
        self.assertIn("COUNT(DISTINCT STATS.MAP_ID)", sql)
        self.assertIn("SERVER_NUMBER = ANY(%S)", sql)
        self.assertIn("GAME = %S", sql)
        self.assertIn('"END" < %S', sql)
        self.assertIn("FILTER (WHERE NULLIF(BTRIM(STATS.NAME), '') IS NOT NULL)", sql)
        self.assertNotIn("IDENTITIES.STEAM_ID_64\n           ) AS PLAYER_NAME", sql)
        for keyword in ("INSERT ", "UPDATE ", "DELETE ", "CREATE ", "ALTER ", "DROP "):
            self.assertNotIn(keyword, sql)
        self.assertEqual(RANKING_METRIC_SQL["kills"], "kills")
        self.assertNotIn("arbitrary", RANKING_METRIC_SQL)
        self.assertEqual(
            set(RANKING_METRIC_SQL),
            {
                "kills", "deaths", "teamkills", "matches_considered", "kd_ratio",
                "kills_per_match", "kpm", "combat", "offense", "defense",
                "support", "vehicle_kills", "vehicles_destroyed", "playtime",
                "matches_over_100_kills",
            },
        )

    def test_ranking_bounds_and_metric_allowlist_fail_before_connecting(self) -> None:
        repository = PostgresCrconRepository(
            dsn=None,
            connect_timeout_seconds=1,
            statement_timeout_ms=1000,
            lock_timeout_ms=10,
        )
        scopes = (CrconServerScope(1, "hll"),)
        with self.assertRaises(ValueError):
            repository.list_rankings(
                scopes=scopes, started_at=None, ended_at=None,
                metric="kills; DROP TABLE map_history", limit=10,
            )
        with self.assertRaises(ValueError):
            repository.list_rankings(
                scopes=scopes, started_at=None, ended_at=None,
                metric="kills", limit=101,
            )

    def test_runtime_pool_reuses_connection_and_closes_cleanly(self) -> None:
        class Cursor:
            def __init__(self, one=None, many=None):
                self.one = one
                self.many = many or []

            def fetchone(self):
                return self.one

            def fetchall(self):
                return self.many

        class Connection:
            def __init__(self):
                self.closed = False
                self.rollbacks = 0

            def execute(self, statement, _params=None):
                if statement == "SHOW transaction_read_only":
                    return Cursor(one=("on",))
                return Cursor(many=[])

            def rollback(self):
                self.rollbacks += 1

            def close(self):
                self.closed = True

        connection = Connection()
        connect_calls = []

        def connector(*args, **kwargs):
            connect_calls.append((args, kwargs))
            return connection

        with patch(
            "app.crcon.postgres_repository._load_connector", return_value=connector
        ):
            repository = PostgresCrconRepository(
                dsn="postgresql://fixture.invalid/crcon",
                connect_timeout_seconds=1,
                statement_timeout_ms=1000,
                lock_timeout_ms=10,
                pool_size=2,
            )
            repository.probe_capabilities()
            repository.probe_capabilities()
            self.assertEqual(len(connect_calls), 1)
            self.assertFalse(connection.closed)
            self.assertEqual(connection.rollbacks, 2)
            repository.close()
        self.assertTrue(connection.closed)


class _PayloadService:
    def server_summary(self, **_kwargs):
        return {
            "source": "crcon-postgres-read-only",
            "aggregate_state": "AVAILABLE",
            "found": True,
            "item": {"matches_count": 3, "top_maps": []},
        }

    def ranking(self, **kwargs):
        return {
            "source": "crcon-postgres-read-only",
            "aggregate_state": "AVAILABLE",
            "server_id": "server-1",
            "timeframe": kwargs["timeframe"],
            "metric": kwargs["metric"],
            "limit": kwargs["limit"],
            "window_start": "2026-08-01T00:00:00+00:00",
            "window_end": "2026-08-23T00:00:00+00:00",
            "generated_at": "2026-08-23T00:00:00+00:00",
            "snapshot_status": "ready",
            "items": [{"player_id": "opaque", "ranking_position": 1}],
        }

    def player_profile(self, **kwargs):
        return {
            "source": "crcon-postgres-read-only",
            "aggregate_state": "AVAILABLE",
            "player_id": kwargs["player_id"],
            "matches_considered": 2,
            "external_profile_links": {},
        }


class _PlayerSearchPayloadService:
    def search(self, **kwargs):
        return {
            "source": "crcon-api-get-players-history",
            "aggregate_state": "AVAILABLE",
            "player_history_state": "SUPPORTED",
            "query": kwargs["query"],
            "items": [],
        }


class AggregatePayloadSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.environment = patch.dict(
            os.environ, {"HLL_HISTORICAL_AGGREGATE_SOURCE": "crcon"}, clear=False
        )
        self.environment.start()
        self.ranking_service = patch(
            "app.api.payloads.rankings.get_historical_aggregate_service",
            return_value=_PayloadService(),
        )
        self.ranking_service.start()
        self.player_service = patch(
            "app.api.payloads.players.get_historical_aggregate_service",
            return_value=_PayloadService(),
        )
        self.player_service.start()
        self.search_service = patch(
            "app.api.payloads.players.get_crcon_player_search_service",
            return_value=_PlayerSearchPayloadService(),
        )
        self.search_service.start()

    def tearDown(self) -> None:
        self.search_service.stop()
        self.player_service.stop()
        self.ranking_service.stop()
        self.environment.stop()

    def test_all_public_aggregate_builders_delegate_without_legacy_fallback(self) -> None:
        with (
            patch(
                "app.api.payloads.players.search_rcon_materialized_players",
                side_effect=AssertionError("legacy fallback used"),
            ),
            patch(
                "app.api.payloads.rankings.get_annual_ranking_snapshot",
                side_effect=AssertionError("application annual snapshot used"),
            ),
            patch(
                "app.api.payloads.rankings.get_latest_ranking_snapshot",
                side_effect=AssertionError("application ranking snapshot used"),
            ),
        ):
            search = payloads.build_stats_player_search_payload(query="Player")
            profile = payloads.build_stats_player_profile_payload(player_id="opaque")
            annual = payloads.build_annual_ranking_snapshot_payload(year=2026)
            ranking = payloads.build_global_ranking_payload(
                timeframe="weekly", metric="kills", limit=10
            )
            summary = payloads.build_historical_server_summary_snapshot_payload(
                server_slug="server-1"
            )
            leaderboard = payloads.build_leaderboard_snapshot_payload(
                server_id="server-1", timeframe="monthly", metric="support", limit=10
            )

        self.assertEqual(search["data"]["player_history_state"], "SUPPORTED")
        self.assertEqual(profile["data"]["player_id"], "opaque")
        self.assertEqual(annual["data"]["snapshot_status"], "ready")
        self.assertEqual(ranking["data"]["source"]["primary_source"], "crcon-postgres")
        self.assertTrue(summary["data"]["found"])
        self.assertEqual(leaderboard["data"]["metric"], "support")

    def test_routes_keep_existing_contracts_with_canonical_target(self) -> None:
        targets = (
            '[{"key":"server-1","display_name":"Server 1","server_number":1,'
            '"game":"hll","crcon_base_url":"https://server-1.invalid"}]'
        )
        with patch.dict(os.environ, {"HLL_SERVER_TARGETS": targets}, clear=False):
            ranking_status, ranking = resolve_get_payload(
                "/api/ranking?timeframe=weekly&server_id=server-1&metric=kills&limit=10"
            )
            search_status, search = resolve_get_payload(
                "/api/stats/players/search?q=Player&server_id=server-1&limit=10"
            )
            profile_status, profile = resolve_get_payload(
                "/api/stats/players/opaque?server_id=server-1&timeframe=weekly"
            )
        self.assertEqual(ranking_status, HTTPStatus.OK)
        self.assertEqual(ranking["data"]["page_kind"], "global-ranking")
        self.assertEqual(search_status, HTTPStatus.OK)
        self.assertIsInstance(search["data"]["items"], list)
        self.assertEqual(profile_status, HTTPStatus.OK)
        self.assertEqual(profile["data"]["player_id"], "opaque")


if __name__ == "__main__":
    unittest.main()
