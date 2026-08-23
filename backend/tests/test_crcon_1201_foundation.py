from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from urllib.error import URLError
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from app.crcon import (
    CrconApiClient,
    CrconApiError,
    CrconCapability,
    CrconCapabilityStatus,
    CrconContractStatus,
    CrconServerScope,
)
from app.crcon.capabilities import build_capability_report, get_api_contract_status
from app.crcon.postgres_repository import PLAYER_AGGREGATE_SQL
from app.crcon.postgres_repository import PostgresCrconRepository
from app.domain import PlayerIdentity, player_id_from
from app.player_external_profiles import build_external_player_profile_fields
from app.rcon_client import load_rcon_targets
from app.server_targets import ServerTarget, ServerTargetRegistry, load_server_targets


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


class _Cursor:
    def __init__(self, *, one: object = None, many: list[object] | None = None) -> None:
        self._one = one
        self._many = many or []

    def fetchone(self) -> object:
        return self._one

    def fetchall(self) -> list[object]:
        return self._many


class _AggregateConnection:
    def __init__(self, aggregate_row: object) -> None:
        self.aggregate_row = aggregate_row
        self.statements: list[tuple[str, object]] = []
        self.rolled_back = False
        self.closed = False

    def execute(self, statement: str, params: object = None) -> _Cursor:
        self.statements.append((statement, params))
        if statement == "SHOW transaction_read_only":
            return _Cursor(one=("on",))
        if "count(DISTINCT stats.map_id)" in statement:
            return _Cursor(one=self.aggregate_row)
        return _Cursor()

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


class ServerTargetTests(unittest.TestCase):
    def test_hll_hllv_and_multiple_targets_are_supported(self) -> None:
        hll = ServerTarget(
            key="comunidad-hll-01",
            display_name="Comunidad HLL #01",
            server_number=1,
            game="hll",
            crcon_base_url="https://hll.fixture.invalid/",
            capabilities=frozenset({"live_state"}),
        )
        hllv = ServerTarget(
            key="comunidad-hll-vietnam-01",
            display_name="Comunidad HLL Vietnam #01",
            server_number=2,
            game="hllv",
            crcon_base_url="https://hllv.fixture.invalid",
        )
        registry = ServerTargetRegistry((hll, hllv))

        self.assertEqual([target.server_number for target in registry.all()], [1, 2])
        self.assertEqual(registry.get("comunidad-hll-vietnam-01").game, "hllv")
        self.assertEqual(hll.crcon_base_url, "https://hll.fixture.invalid")

    def test_registry_loads_n_targets_without_credentials(self) -> None:
        payload = [
            {
                "key": "comunidad-hll-01",
                "display_name": "HLL",
                "server_number": 1,
                "game": "hll",
                "crcon_base_url": "https://one.fixture.invalid",
            },
            {
                "key": "comunidad-hll-vietnam-01",
                "display_name": "HLL Vietnam",
                "server_number": 2,
                "game": "hllv",
                "crcon_base_url": "https://two.fixture.invalid",
                "enabled": False,
            },
        ]
        with patch.dict(os.environ, {"HLL_SERVER_TARGETS": json.dumps(payload)}, clear=True):
            registry = load_server_targets()

        self.assertEqual(len(registry.all(enabled_only=False)), 2)
        self.assertEqual(len(registry.all()), 1)

    def test_credentials_in_base_url_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unauthenticated"):
            ServerTarget(
                key="unsafe",
                display_name="Unsafe",
                server_number=1,
                game="hll",
                crcon_base_url="https://user:secret@fixture.invalid",
            )

    def test_legacy_rcon_transport_links_to_canonical_target(self) -> None:
        server_targets = [
            {
                "key": "comunidad-hll-01",
                "display_name": "HLL",
                "server_number": 1,
                "game": "hll",
                "crcon_base_url": "https://one.fixture.invalid",
            }
        ]
        legacy_rcon = [
            {
                "external_server_id": "comunidad-hll-01",
                "name": "Legacy HLL",
                "host": "127.0.0.1",
                "port": 7779,
                "password": "synthetic-only",
            }
        ]
        with patch.dict(
            os.environ,
            {
                "HLL_SERVER_TARGETS": json.dumps(server_targets),
                "HLL_BACKEND_RCON_TARGETS": json.dumps(legacy_rcon),
            },
            clear=True,
        ):
            target = load_rcon_targets()[0]

        self.assertEqual(target.server_target.key, "comunidad-hll-01")
        self.assertEqual(target.server_target.server_number, 1)


class OpaquePlayerIdentityTests(unittest.TestCase):
    def test_numeric_and_eos_player_ids_remain_opaque_strings(self) -> None:
        numeric = player_id_from("76561198000000000")
        eos = player_id_from("EOS-synthetic-player")

        self.assertIsInstance(numeric, str)
        self.assertEqual(str(numeric), "76561198000000000")
        self.assertEqual(str(eos), "EOS-synthetic-player")

    def test_numeric_player_id_does_not_create_steam_metadata_or_links(self) -> None:
        result = build_external_player_profile_fields(player_id="76561198000000000")

        self.assertEqual(result["platform"], "unknown")
        self.assertEqual(result["external_profile_links"], {})
        self.assertNotIn("steam_id_64", result)

    def test_explicit_steam_and_eos_metadata_are_separate(self) -> None:
        steam = build_external_player_profile_fields(steam_id="76561198000000000")
        eos = build_external_player_profile_fields(
            player_id="opaque-player",
            eos_id="0123456789abcdef0123456789abcdef",
            platform="eos",
        )

        self.assertEqual(steam["steam_id_64"], "76561198000000000")
        self.assertIn("steam", steam["external_profile_links"])
        self.assertEqual(eos["eos_id"], "0123456789abcdef0123456789abcdef")
        self.assertEqual(eos["platform"], "eos")
        self.assertNotIn("steam_id_64", eos)


class Crcon1201ApiContractTests(unittest.TestCase):
    def test_all_required_endpoint_methods_return_internal_dtos(self) -> None:
        payload_by_path = {
            "/api/get_public_info": "public_info.json",
            "/api/get_live_game_stats": "live_game_stats.json",
            "/api/get_live_scoreboard": "live_scoreboard.json",
            "/api/get_scoreboard_maps": "scoreboard_maps.json",
            "/api/get_map_scoreboard": "map_scoreboard.json",
            "/api/get_map_history": "map_history.json",
            "/api/get_previous_map": "previous_map.json",
        }
        urls: list[str] = []

        def transport(request, _timeout):
            urls.append(request.full_url)
            path = urlsplit(request.full_url).path
            return _Response(_fixture(payload_by_path[path]))

        client = CrconApiClient(
            base_url="https://fixture.invalid",
            timeout_seconds=1,
            transport=transport,
        )

        public = client.get_public_info()
        live = client.get_live_game_stats()
        live_scoreboard = client.get_live_scoreboard()
        maps = client.get_scoreboard_maps(server_number=1)
        detail = client.get_map_scoreboard(map_id="9001")
        history = client.get_map_history()
        previous = client.get_previous_map()

        self.assertEqual(public.game, "hll")
        self.assertEqual(str(live.players[0].identity.player_id), "opaque-player-001")
        self.assertEqual(str(live_scoreboard.players[0].identity.player_id), "opaque-player-002")
        self.assertEqual(maps.maps[0].server_number, 1)
        self.assertIsNone(detail.match.game)
        self.assertIsNone(detail.players[0].identity.steam_id)
        self.assertEqual(len(history.maps), 2)
        self.assertEqual(previous.match.layer, "synthetic_valley_offensive")
        self.assertEqual(len(urls), 7)
        self.assertEqual(parse_qs(urlsplit(urls[-2]).query), {})

    def test_version_manifest_is_supported_for_hll_only(self) -> None:
        metadata = _fixture("metadata.json")
        contracts = _fixture("contracts.json")

        self.assertEqual(metadata["verified_version"], "12.0.1")
        self.assertEqual(metadata["verification_status"], "supported")
        self.assertTrue(
            all(
                status["hll"] == "supported" and status["hllv"] == "unverified"
                for status in contracts["endpoints"].values()
            )
        )
        self.assertEqual(
            get_api_contract_status("get_public_info"),
            CrconContractStatus.SUPPORTED,
        )
        self.assertEqual(
            get_api_contract_status("get_public_info", game="hllv"),
            CrconContractStatus.UNVERIFIED,
        )
        self.assertEqual(
            get_api_contract_status("not_a_crcon_endpoint"),
            CrconContractStatus.UNSUPPORTED,
        )

    def test_incomplete_response_degrades_to_empty_dto_without_invented_fields(self) -> None:
        client = CrconApiClient(
            base_url="https://fixture.invalid",
            timeout_seconds=1,
            transport=lambda *_args: _Response({"result": {}, "failed": False}),
        )

        result = client.get_public_info()

        self.assertIsNone(result.current_map.layer)
        self.assertIsNone(result.player_count)
        self.assertEqual(result.contract_status, CrconContractStatus.SUPPORTED)

    def test_timeout_is_sanitized(self) -> None:
        client = CrconApiClient(
            base_url="https://fixture.invalid",
            timeout_seconds=0.1,
            transport=lambda *_args: (_ for _ in ()).throw(URLError("secret timeout")),
        )
        with self.assertRaises(CrconApiError) as raised:
            client.get_previous_map()
        self.assertNotIn("secret", str(raised.exception))


class CrconReadRepositoryTests(unittest.TestCase):
    def test_player_aggregate_is_select_only_and_server_scoped(self) -> None:
        connection = _AggregateConnection((4, 42, 100, 50, 900, 80, 70, 60, 5, 3))
        repository = PostgresCrconRepository(
            dsn="postgresql://fixture.invalid/crcon",
            connect_timeout_seconds=2,
            statement_timeout_ms=1000,
            lock_timeout_ms=10,
            connector=lambda *_args, **_kwargs: connection,
        )
        identity = PlayerIdentity(player_id=player_id_from("76561198000000000"))

        result = repository.get_player_aggregate(
            identity=identity,
            scope=CrconServerScope(server_number=2, game="hllv"),
        )

        aggregate_statement, params = connection.statements[-1]
        self.assertEqual(result.matches_played, 4)
        self.assertEqual(result.record_kills, 42)
        self.assertEqual(result.total_kills, 100)
        self.assertEqual(result.vehicle_kills, 5)
        self.assertEqual(result.vehicles_destroyed, 3)
        self.assertIn("count(DISTINCT stats.map_id)", aggregate_statement)
        self.assertIn("max(stats.kills)", aggregate_statement)
        self.assertIn("sum(stats.kills)", aggregate_statement)
        self.assertEqual(params, ("76561198000000000", 2))
        self.assertTrue(connection.rolled_back and connection.closed)

    def test_log_scope_never_infers_server_text_from_server_number(self) -> None:
        scope = CrconServerScope(server_number=1, game="hll")
        with self.assertRaisesRegex(Exception, "discriminator is unverified"):
            scope.require_log_server()

    def test_log_scope_requires_explicit_integer_game_discriminator(self) -> None:
        scope = CrconServerScope(
            server_number=1,
            game="hll",
            log_server="synthetic-server-one",
        )
        with self.assertRaisesRegex(Exception, "game discriminator is unverified"):
            scope.require_log_discriminators()

        self.assertEqual(
            CrconServerScope(1, "hll", "synthetic-server-one", 1)
            .require_log_discriminators(),
            ("synthetic-server-one", 1),
        )

    def test_aggregate_sql_contains_no_mutation(self) -> None:
        sql = PLAYER_AGGREGATE_SQL.upper()
        self.assertTrue(sql.lstrip().startswith("SELECT"))
        for keyword in ("INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP"):
            self.assertNotIn(keyword, sql)

    def test_12_0_1_schema_capability_can_be_supported_or_missing(self) -> None:
        schema = _fixture("schema_capabilities.json")["tables"]
        report = build_capability_report(
            schema_columns={name: set(columns) for name, columns in schema.items()},
            database_configured=True,
            api_configured=True,
        )
        self.assertEqual(
            report.get(CrconCapability.PLAYER_AGGREGATES).status,
            CrconCapabilityStatus.SUPPORTED,
        )
        self.assertEqual(
            report.get(CrconCapability.LIVE_STATE).status,
            CrconCapabilityStatus.UNKNOWN,
        )
        self.assertEqual(
            report.get(CrconCapability.EVENT_LOGS).status,
            CrconCapabilityStatus.UNKNOWN,
        )

        verified_logs = build_capability_report(
            schema_columns={name: set(columns) for name, columns in schema.items()},
            database_configured=True,
            api_configured=False,
            log_semantics_verified=True,
        )
        self.assertEqual(
            verified_logs.get(CrconCapability.EVENT_LOGS).status,
            CrconCapabilityStatus.SUPPORTED,
        )

        schema["player_stats"].remove("vehicles_destroyed")
        missing = build_capability_report(
            schema_columns={name: set(columns) for name, columns in schema.items()},
            database_configured=True,
            api_configured=False,
        )
        self.assertEqual(
            missing.get(CrconCapability.PLAYER_AGGREGATES).status,
            CrconCapabilityStatus.INCOMPATIBLE,
        )


if __name__ == "__main__":
    unittest.main()
