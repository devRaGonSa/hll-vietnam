from __future__ import annotations

import json
import os
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import URLError
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from app.config import (
    DEFAULT_CRCON_CONTRACT_REVISION,
    get_bind_address,
    get_crcon_api_base_url,
    get_crcon_api_timeout_seconds,
    get_crcon_contract_revision,
    get_crcon_database_connect_timeout_seconds,
    get_crcon_database_lock_timeout_ms,
    get_crcon_database_statement_timeout_ms,
    get_crcon_database_url,
)
from app.crcon import (
    CRCON_CONTRACT_REVISION,
    CrconApiClient,
    CrconApiError,
    CrconCapability,
    CrconCapabilityStatus,
    CrconDatabaseError,
    TtlCache,
)
from app.crcon.capabilities import CAPABILITY_SCHEMA, build_capability_report
from app.crcon.postgres_repository import PostgresCrconRepository


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "crcon"
PINNED_COMMIT = "17c5880684cc419b27ef2bcca0dc439dfd623eae"
LEGACY_FIXTURE_COMMIT = "4cf1e7e2fa691d849eaf85abb7065010e13f28e4"


class _Response:
    def __init__(self, payload: object, *, raw: bytes | None = None) -> None:
        self._body = raw if raw is not None else json.dumps(payload).encode("utf-8")

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


class _Cursor:
    def __init__(self, *, one: object = None, many: list[object] | None = None) -> None:
        self._one = one
        self._many = many or []

    def fetchone(self) -> object:
        return self._one

    def fetchall(self) -> list[object]:
        return self._many


class _Connection:
    def __init__(self, *, read_only: str = "on", schema_rows: list[object] | None = None) -> None:
        self.read_only = read_only
        self.schema_rows = schema_rows or []
        self.statements: list[tuple[str, object]] = []
        self.rolled_back = False
        self.closed = False

    def execute(self, statement: str, params: object = None) -> _Cursor:
        self.statements.append((statement, params))
        if statement == "SHOW transaction_read_only":
            return _Cursor(one=(self.read_only,))
        if "information_schema.columns" in statement:
            return _Cursor(many=self.schema_rows)
        return _Cursor()

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


class _FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _complete_schema() -> dict[str, set[str]]:
    fixture = _load_fixture("schema_capabilities.json")
    return {name: set(columns) for name, columns in fixture["tables"].items()}


def _schema_rows() -> list[dict[str, str]]:
    return [
        {"table_name": table, "column_name": column}
        for table, columns in _complete_schema().items()
        for column in columns
    ]


class CrconApiClientTests(unittest.TestCase):
    def test_public_info_unwraps_result_without_real_network(self) -> None:
        calls = []

        def transport(request, timeout):
            calls.append((request, timeout))
            return _Response(_load_fixture("public_info.json"))

        client = CrconApiClient(
            base_url="https://fixture.invalid/crcon/",
            timeout_seconds=2.5,
            headers={"User-Agent": "caller-must-not-override"},
            transport=transport,
        )

        result = client.get_public_info()

        self.assertEqual(result.player_count, 54)
        self.assertEqual(calls[0][1], 2.5)
        self.assertEqual(calls[0][0].full_url, "https://fixture.invalid/crcon/api/get_public_info")
        self.assertEqual(calls[0][0].get_header("User-agent"), "HLL-Vietnam-CRCON-BFF/0.1")

    def test_scoreboard_methods_encode_verified_queries(self) -> None:
        urls = []
        payloads = iter(
            [_load_fixture("scoreboard_maps.json"), _load_fixture("map_scoreboard.json")]
        )

        def transport(request, _timeout):
            urls.append(request.full_url)
            return _Response(next(payloads))

        client = CrconApiClient(
            base_url="https://fixture.invalid",
            timeout_seconds=1,
            transport=transport,
        )
        maps = client.get_scoreboard_maps(page=2, limit=25, server_number=7)
        detail = client.get_map_scoreboard(map_id=9001)

        self.assertEqual(maps.total, 2)
        self.assertEqual(detail.match.map_id, "9001")
        self.assertEqual(
            parse_qs(urlsplit(urls[0]).query),
            {"page": ["2"], "limit": ["25"], "server_number": ["7"]},
        )
        self.assertEqual(parse_qs(urlsplit(urls[1]).query), {"map_id": ["9001"]})

    def test_retry_is_capped_at_one(self) -> None:
        calls = 0

        def transport(_request, _timeout):
            nonlocal calls
            calls += 1
            if calls == 1:
                raise URLError("synthetic transient failure")
            return _Response(_load_fixture("public_info.json"))

        client = CrconApiClient(
            base_url="https://fixture.invalid",
            timeout_seconds=1,
            retries=1,
            transport=transport,
        )
        self.assertEqual(client.get_public_info().player_count, 54)
        self.assertEqual(calls, 2)
        with self.assertRaises(ValueError):
            CrconApiClient(
                base_url="https://fixture.invalid", timeout_seconds=1, retries=2
            )

    def test_default_has_no_retry(self) -> None:
        calls = 0

        def transport(_request, _timeout):
            nonlocal calls
            calls += 1
            raise TimeoutError("synthetic")

        client = CrconApiClient(
            base_url="https://fixture.invalid",
            timeout_seconds=1,
            transport=transport,
        )
        with self.assertRaisesRegex(CrconApiError, "request failed"):
            client.get_public_info()
        self.assertEqual(calls, 1)

    def test_malformed_json_is_sanitized(self) -> None:
        client = CrconApiClient(
            base_url="https://fixture.invalid",
            timeout_seconds=1,
            transport=lambda *_args: _Response({}, raw=b"not-json"),
        )
        with self.assertRaisesRegex(CrconApiError, "request failed") as raised:
            client.get_public_info()
        self.assertNotIn("not-json", str(raised.exception))

    def test_failed_or_unexpected_payload_is_rejected(self) -> None:
        failed_client = CrconApiClient(
            base_url="https://fixture.invalid",
            timeout_seconds=1,
            transport=lambda *_args: _Response({"failed": True, "error": "private"}),
        )
        with self.assertRaisesRegex(CrconApiError, "failed response") as raised:
            failed_client.get_public_info()
        self.assertNotIn("private", str(raised.exception))

    def test_authentication_and_url_secrets_are_not_exposed(self) -> None:
        secret = "fixture-super-secret"
        client = CrconApiClient(
            base_url="https://fixture.invalid",
            timeout_seconds=1,
            headers={"Authorization": f"Bearer {secret}", "X-Adapter-Key": secret},
            transport=lambda *_args: (_ for _ in ()).throw(URLError(secret)),
        )
        with self.assertRaises(CrconApiError) as raised:
            client.get_public_info()
        self.assertNotIn(secret, str(raised.exception))
        self.assertIsNone(raised.exception.__cause__)
        with self.assertRaises(ValueError) as url_error:
            CrconApiClient(
                base_url=f"https://user:{secret}@fixture.invalid",
                timeout_seconds=1,
            )
        self.assertNotIn(secret, str(url_error.exception))


class CrconDatabaseTests(unittest.TestCase):
    def test_missing_dsn_reports_database_capabilities_unavailable(self) -> None:
        report = PostgresCrconRepository(
            dsn=None,
            connect_timeout_seconds=2,
            statement_timeout_ms=1000,
            lock_timeout_ms=100,
        ).probe_capabilities(api_configured=False)

        self.assertEqual(
            report.get(CrconCapability.LIVE_STATE).status,
            CrconCapabilityStatus.UNAVAILABLE,
        )
        self.assertEqual(
            report.get(CrconCapability.HISTORICAL_MAPS).status,
            CrconCapabilityStatus.UNAVAILABLE,
        )

    def test_connection_enforces_and_verifies_read_only_mode(self) -> None:
        connection = _Connection(schema_rows=_schema_rows())
        connect_calls = []

        def connector(*args, **kwargs):
            connect_calls.append((args, kwargs))
            return connection

        report = PostgresCrconRepository(
            dsn="postgresql://fixture.invalid/local",
            connect_timeout_seconds=3,
            statement_timeout_ms=2500,
            lock_timeout_ms=400,
            connector=connector,
        ).probe_capabilities(api_configured=True)

        self.assertEqual(len(report.supported), len(CrconCapability) - 2)
        self.assertEqual(connect_calls[0][1]["connect_timeout"], 3)
        self.assertEqual(connect_calls[0][1]["application_name"], "hll-vietnam-bff")
        options = connect_calls[0][1]["options"]
        self.assertIn("default_transaction_read_only=on", options)
        self.assertIn("statement_timeout=2500", options)
        self.assertIn("lock_timeout=400", options)
        statements = [statement for statement, _params in connection.statements]
        self.assertEqual(statements[:2], ["BEGIN READ ONLY", "SHOW transaction_read_only"])
        self.assertTrue(connection.rolled_back)
        self.assertTrue(connection.closed)

    def test_read_only_off_fails_closed_and_cleans_up(self) -> None:
        connection = _Connection(read_only="off")
        database = PostgresCrconRepository(
            dsn="postgresql://fixture.invalid/local",
            connect_timeout_seconds=2,
            statement_timeout_ms=1000,
            lock_timeout_ms=0,
            connector=lambda *_args, **_kwargs: connection,
        )
        with self.assertRaisesRegex(CrconDatabaseError, "did not establish read-only"):
            database.probe_capabilities()
        self.assertTrue(connection.rolled_back)
        self.assertTrue(connection.closed)

    def test_driver_failure_and_dsn_are_sanitized(self) -> None:
        secret_dsn = "postgresql://fixture-user:fixture-password@fixture.invalid/local"

        def connector(*_args, **_kwargs):
            raise RuntimeError(secret_dsn)

        database = PostgresCrconRepository(
            dsn=secret_dsn,
            connect_timeout_seconds=2,
            statement_timeout_ms=1000,
            lock_timeout_ms=0,
            connector=connector,
        )
        with self.assertRaisesRegex(CrconDatabaseError, "operation failed") as raised:
            database.probe_capabilities()
        self.assertNotIn(secret_dsn, str(raised.exception))
        self.assertNotIn("fixture-password", str(raised.exception))
        self.assertIsNone(raised.exception.__cause__)

    def test_no_public_arbitrary_sql_or_mutation_method_exists(self) -> None:
        public_names = {
            name for name in dir(PostgresCrconRepository) if not name.startswith("_")
        }
        self.assertEqual(
            public_names,
            {
                "aggregate_match_combat_stats",
                "close",
                "configured",
                "find_current_map",
                "get_player_aggregate",
                "get_player_profile_aggregate",
                "get_server_aggregate",
                "list_rankings",
                "list_match_log_events",
                "probe_capabilities",
            },
        )


class CrconCapabilityTests(unittest.TestCase):
    def test_complete_schema_supports_independent_capabilities(self) -> None:
        report = build_capability_report(
            schema_columns=_complete_schema(),
            database_configured=True,
            api_configured=True,
        )
        self.assertEqual(
            report.supported,
            frozenset(
                capability
                for capability in CrconCapability
                if capability
                not in {
                    CrconCapability.LIVE_STATE,
                    CrconCapability.EVENT_LOGS,
                }
            ),
        )
        self.assertEqual(
            report.get(CrconCapability.EVENT_LOGS).status,
            CrconCapabilityStatus.UNKNOWN,
        )
        self.assertEqual(
            report.get(CrconCapability.PLAYER_AGGREGATES).status,
            CrconCapabilityStatus.SUPPORTED,
        )
        self.assertEqual(
            report.get(CrconCapability.LIVE_STATE).status,
            CrconCapabilityStatus.UNKNOWN,
        )

    def test_missing_table_only_marks_dependent_capability_unavailable(self) -> None:
        schema = _complete_schema()
        del schema["log_lines"]
        report = build_capability_report(
            schema_columns=schema,
            database_configured=True,
            api_configured=True,
        )
        event_logs = report.get(CrconCapability.EVENT_LOGS)
        self.assertEqual(event_logs.status, CrconCapabilityStatus.UNAVAILABLE)
        self.assertEqual(event_logs.reason, "Missing table: log_lines.")
        self.assertEqual(
            report.get(CrconCapability.HISTORICAL_MAPS).status,
            CrconCapabilityStatus.SUPPORTED,
        )

    def test_missing_column_is_precisely_incompatible(self) -> None:
        schema = _complete_schema()
        schema["player_sessions"].remove("server_number")
        report = build_capability_report(
            schema_columns=schema,
            database_configured=True,
            api_configured=False,
        )
        sessions = report.get(CrconCapability.PLAYER_SESSIONS)
        self.assertEqual(sessions.status, CrconCapabilityStatus.INCOMPATIBLE)
        self.assertEqual(
            sessions.reason,
            "Missing column: player_sessions.server_number.",
        )
        self.assertEqual(
            report.get(CrconCapability.PLAYER_IDENTITIES).status,
            CrconCapabilityStatus.SUPPORTED,
        )

    def test_api_unavailable_does_not_invalidate_database_capabilities(self) -> None:
        report = build_capability_report(
            schema_columns=_complete_schema(),
            database_configured=True,
            api_configured=False,
        )
        self.assertEqual(
            report.get(CrconCapability.LIVE_STATE).status,
            CrconCapabilityStatus.UNAVAILABLE,
        )
        self.assertEqual(
            report.get(CrconCapability.SERVER_COUNT_HISTORY).status,
            CrconCapabilityStatus.SUPPORTED,
        )


class TtlCacheTests(unittest.TestCase):
    def test_hit_update_and_expiry_use_injected_monotonic_clock(self) -> None:
        clock = _FakeClock()
        cache = TtlCache[str, int](max_entries=2, ttl_seconds=5, clock=clock)
        cache.put("a", 1)
        self.assertEqual(cache.get("a"), 1)
        cache.put("a", 2)
        self.assertEqual(cache.get("a"), 2)
        clock.advance(5)
        self.assertIsNone(cache.get("a"))
        self.assertEqual(len(cache), 0)

    def test_lru_eviction_is_bounded_and_deterministic(self) -> None:
        cache = TtlCache[str, int](max_entries=2, ttl_seconds=10)
        cache.put("a", 1)
        cache.put("b", 2)
        self.assertEqual(cache.get("a"), 1)
        cache.put("c", 3)
        self.assertIsNone(cache.get("b"))
        self.assertEqual(cache.get("a"), 1)
        self.assertEqual(cache.get("c"), 3)
        self.assertEqual(len(cache), 2)

    def test_per_entry_ttl_and_explicit_invalidation(self) -> None:
        clock = _FakeClock()
        cache = TtlCache[str, int](max_entries=2, ttl_seconds=10, clock=clock)
        cache.put("short", 1, ttl_seconds=1)
        self.assertTrue(cache.invalidate("short"))
        self.assertFalse(cache.invalidate("short"))
        cache.put("short", 1, ttl_seconds=1)
        clock.advance(2)
        self.assertIsNone(cache.get("short"))
        cache.put("other", 2)
        cache.clear()
        self.assertEqual(len(cache), 0)

    def test_concurrent_access_stays_bounded(self) -> None:
        cache = TtlCache[int, int](max_entries=16, ttl_seconds=60)
        errors = []

        def write_and_read(value: int) -> None:
            try:
                cache.put(value, value)
                cache.get(value)
            except Exception as error:  # pragma: no cover - assertion captures failures
                errors.append(error)

        with ThreadPoolExecutor(max_workers=8) as executor:
            list(executor.map(write_and_read, range(200)))
        self.assertEqual(errors, [])
        self.assertLessEqual(len(cache), 16)
        self.assertFalse(any(thread.name.startswith("TtlCache") for thread in threading.enumerate()))


class CrconConfigurationTests(unittest.TestCase):
    CRCON_ENV = {
        "HLL_CRCON_API_BASE_URL",
        "HLL_CRCON_API_TIMEOUT_SECONDS",
        "HLL_CRCON_DATABASE_URL",
        "HLL_CRCON_DATABASE_CONNECT_TIMEOUT_SECONDS",
        "HLL_CRCON_DATABASE_STATEMENT_TIMEOUT_MS",
        "HLL_CRCON_DATABASE_LOCK_TIMEOUT_MS",
    }

    def test_new_configuration_is_optional_and_legacy_startup_defaults_remain(self) -> None:
        clean_env = {key: value for key, value in os.environ.items() if key not in self.CRCON_ENV}
        with patch.dict(os.environ, clean_env, clear=True):
            self.assertIsNone(get_crcon_api_base_url())
            self.assertIsNone(get_crcon_database_url())
            self.assertEqual(get_crcon_api_timeout_seconds(), 5.0)
            self.assertEqual(get_crcon_database_connect_timeout_seconds(), 5)
            self.assertEqual(get_crcon_database_statement_timeout_ms(), 5000)
            self.assertEqual(get_crcon_database_lock_timeout_ms(), 1000)
            self.assertEqual(get_bind_address(), ("127.0.0.1", 8000))

    def test_crcon_configuration_is_separate_and_validated(self) -> None:
        values = {
            "HLL_BACKEND_DATABASE_URL": "postgresql://legacy.invalid/hll",
            "HLL_CRCON_API_BASE_URL": " https://fixture.invalid ",
            "HLL_CRCON_DATABASE_URL": " postgresql://fixture.invalid/crcon ",
            "HLL_CRCON_API_TIMEOUT_SECONDS": "2.5",
            "HLL_CRCON_DATABASE_CONNECT_TIMEOUT_SECONDS": "3",
            "HLL_CRCON_DATABASE_STATEMENT_TIMEOUT_MS": "2500",
            "HLL_CRCON_DATABASE_LOCK_TIMEOUT_MS": "0",
        }
        with patch.dict(os.environ, values, clear=False):
            self.assertEqual(get_crcon_api_base_url(), "https://fixture.invalid")
            self.assertEqual(get_crcon_database_url(), "postgresql://fixture.invalid/crcon")
            self.assertEqual(get_crcon_api_timeout_seconds(), 2.5)
            self.assertEqual(get_crcon_database_connect_timeout_seconds(), 3)
            self.assertEqual(get_crcon_database_statement_timeout_ms(), 2500)
            self.assertEqual(get_crcon_database_lock_timeout_ms(), 0)

    def test_contract_revision_is_reference_metadata(self) -> None:
        self.assertEqual(CRCON_CONTRACT_REVISION, PINNED_COMMIT)
        self.assertEqual(DEFAULT_CRCON_CONTRACT_REVISION, PINNED_COMMIT)
        self.assertEqual(get_crcon_contract_revision(), PINNED_COMMIT)


class CrconFixtureTests(unittest.TestCase):
    def test_every_fixture_loads_and_has_expected_contract_fields(self) -> None:
        expected = {
            "current_map_rows.json",
            "current_match_log_events.json",
            "db_lag_current_match.json",
            "live_game_stats.json",
            "metadata.json",
            "match_transition.json",
            "public_info.json",
            "scoreboard_maps.json",
            "map_scoreboard.json",
            "schema_capabilities.json",
        }
        self.assertEqual({path.name for path in FIXTURE_DIR.glob("*.json")}, expected)
        public_info = _load_fixture("public_info.json")["result"]
        maps = _load_fixture("scoreboard_maps.json")["result"]["maps"]
        detail = _load_fixture("map_scoreboard.json")["result"]
        self.assertIn("current_map", public_info)
        self.assertTrue(any(item["end"] is None for item in maps))
        self.assertTrue(any(item["end"] is not None for item in maps))
        self.assertEqual(detail["player_stats"][0]["teamkills"], 1)
        self.assertIn("weapons", detail["player_stats"][0])

    def test_metadata_pins_revision_and_declares_sanitation(self) -> None:
        metadata = _load_fixture("metadata.json")
        self.assertEqual(metadata["repository"], "https://github.com/MarechJ/hll_rcon_tool")
        self.assertEqual(metadata["branch"], "master")
        self.assertEqual(metadata["commit"], LEGACY_FIXTURE_COMMIT)
        self.assertIs(metadata["sanitized"], True)

    def test_fixtures_contain_no_obvious_secret_or_production_patterns(self) -> None:
        forbidden = (
            "postgresql://",
            "authorization",
            "bearer ",
            "password",
            "comunidad hispana",
            "raw_message",
            "raw_payload",
        )
        fixture_text = "\n".join(
            path.read_text(encoding="utf-8").lower()
            for path in sorted(FIXTURE_DIR.glob("*.json"))
        )
        for pattern in forbidden:
            self.assertNotIn(pattern, fixture_text)


if __name__ == "__main__":
    unittest.main()
