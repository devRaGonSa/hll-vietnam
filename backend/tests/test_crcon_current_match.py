from __future__ import annotations

import json
import os
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event, Lock, Thread
import unittest
from unittest.mock import MagicMock, patch

from app.api.payloads import current_match as payloads
from app.config import (
    get_crcon_current_match_bindings,
    get_current_match_source,
    get_server_list_source,
)
from app.crcon.api import CrconApiClient
from app.crcon.cache import TtlCache
from app.crcon.dto import parse_live_game_stats
from app.crcon.postgres_repository import (
    CURRENT_MAP_MATCH_SQL,
    MATCH_COMBAT_AGGREGATE_SQL,
    MATCH_LOG_EVENTS_SQL,
    PostgresCrconRepository,
)
from app.crcon.repository import (
    CrconCurrentMap,
    CrconMatchCombatStats,
    CrconMatchLogEvent,
    CrconServerScope,
)

from app.services.current_match import (
    CURRENT_MATCH_CACHE_MAX_ENTRIES,
    CURRENT_MATCH_CACHE_TTL_SECONDS,
    CrconCurrentMatchBinding,
    CurrentMatchCursorError,
    CurrentMatchSnapshotService,
    CurrentMatchUnavailableError,
    MatchIdentityKind,
    _build_bindings,
    decode_kill_cursor,
    encode_kill_cursor,
    get_current_match_snapshot_service,
)
from app.scoreboard_origins import get_trusted_public_scoreboard_origin
from app.server_targets import ServerTarget
from app.api.routes import resolve_get_payload


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "crcon"
VERIFIED_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "crcon_12_0_1"
NOW = datetime(2026, 8, 14, 8, 15, tzinfo=UTC)


def _fixture(name: str) -> object:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _public_info() -> dict[str, object]:
    return _fixture("public_info.json")["result"]


def _live_stats() -> dict[str, object]:
    return _fixture("live_game_stats.json")["result"]


def _current_map(map_id: int = 9002) -> CrconCurrentMap:
    return CrconCurrentMap(
        id=map_id,
        start=datetime(2026, 8, 14, 8, 0, tzinfo=UTC),
        end=None,
        server_number=7,
        map_name="synthetic_forest_warfare",
        result=None,
    )


def _events() -> tuple[CrconMatchLogEvent, ...]:
    rows = _fixture("current_match_log_events.json")["events"]
    return tuple(
        CrconMatchLogEvent(
            id=row["id"],
            event_time=datetime.fromisoformat(row["event_time"].replace("Z", "+00:00")),
            type=row["type"],
            player1_name=row["player1_name"],
            player1_id=row["player1_id"],
            player2_name=row["player2_name"],
            player2_id=row["player2_id"],
            weapon=row["weapon"],
        )
        for row in rows
    )


def _aggregate_events(
    events: tuple[CrconMatchLogEvent, ...],
    *,
    started_at: datetime = datetime(2026, 8, 14, 8, 0, tzinfo=UTC),
    ended_at: datetime = NOW,
) -> tuple[CrconMatchCombatStats, ...]:
    builders: dict[str, dict[str, object]] = {}
    seen_ids: set[int] = set()

    def player(player_id: str | None, name: str | None) -> dict[str, object]:
        resolved_name = name or "Unknown player"
        key = f"id:{player_id}" if player_id else f"name:{resolved_name.casefold()}"
        return builders.setdefault(
            key,
            {
                "player_id": player_id,
                "player_name": resolved_name,
                "kills": 0,
                "deaths": 0,
                "teamkills": 0,
                "deaths_by_teamkill": 0,
                "weapons": Counter(),
            },
        )

    for event in events:
        event_time = event.event_time.astimezone(UTC)
        if (
            event.id in seen_ids
            or event.type not in {"KILL", "TEAM KILL"}
            or not started_at <= event_time <= ended_at
        ):
            continue
        seen_ids.add(event.id)
        killer = player(event.player1_id, event.player1_name)
        victim = player(event.player2_id, event.player2_name)
        if event.type == "KILL":
            killer["kills"] = int(killer["kills"]) + 1
            victim["deaths"] = int(victim["deaths"]) + 1
            if event.weapon:
                weapons = killer["weapons"]
                assert isinstance(weapons, Counter)
                weapons[event.weapon] += 1
        else:
            killer["teamkills"] = int(killer["teamkills"]) + 1
            victim["deaths_by_teamkill"] = int(victim["deaths_by_teamkill"]) + 1

    rows: list[CrconMatchCombatStats] = []
    for key in sorted(builders):
        builder = builders[key]
        weapons = builder["weapons"]
        assert isinstance(weapons, Counter)
        rows.append(
            CrconMatchCombatStats(
                player_id=builder["player_id"],
                player_name=str(builder["player_name"]),
                kills=int(builder["kills"]),
                deaths=int(builder["deaths"]),
                teamkills=int(builder["teamkills"]),
                deaths_by_teamkill=int(builder["deaths_by_teamkill"]),
                weapon_counts=tuple(sorted(weapons.items())),
            )
        )
    return tuple(rows)


def _many_events(count: int = 600) -> tuple[CrconMatchLogEvent, ...]:
    timestamp = datetime(2026, 8, 14, 8, 10, tzinfo=UTC)
    return tuple(
        CrconMatchLogEvent(
            id=1000 + index,
            event_time=timestamp,
            type="KILL",
            player1_name="Fixture Alpha",
            player1_id="synthetic-player-alpha",
            player2_name="Fixture Bravo",
            player2_id="synthetic-player-bravo",
            weapon="SYNTHETIC_RIFLE",
        )
        for index in range(count)
    )


def _binding(
    slug: str = "comunidad-hispana-01",
    *,
    server_number: int = 7,
    game: str = "hll",
) -> CrconCurrentMatchBinding:
    return CrconCurrentMatchBinding(
        target=ServerTarget(
            key=slug,
            display_name="Synthetic Local Server",
            crcon_base_url=f"https://{slug}.fixture.invalid",
            server_number=server_number,
            game=game,  # type: ignore[arg-type]
            capabilities=frozenset({"live_state", "historical_maps", "event_logs"}),
        ),
        database_url="postgresql://fixture.invalid/crcon",
        api_headers={"X-Fixture-Auth": "synthetic"},
        log_server=f"synthetic-server-{server_number}",
    )


def _server_target_payload(
    slug: str = "comunidad-hispana-01",
    *,
    server_number: int = 7,
    game: str = "hll",
) -> str:
    return json.dumps(
        [
            {
                "key": slug,
                "display_name": "Synthetic Local Server",
                "server_number": server_number,
                "game": game,
                "crcon_base_url": f"https://{slug}.fixture.invalid",
                "enabled": True,
                "capabilities": ["live_state"],
            }
        ]
    )


class _FakeApi:
    def __init__(
        self,
        public_info: dict[str, object] | None = None,
        live_stats: object | None = None,
    ) -> None:
        self.public_info = public_info if public_info is not None else _public_info()
        self.live_stats = live_stats if live_stats is not None else _live_stats()
        self.public_error: Exception | None = None
        self.live_error: Exception | None = None
        self.public_calls = 0
        self.live_calls = 0
        self._lock = Lock()

    def get_public_info(self) -> dict[str, object]:
        with self._lock:
            self.public_calls += 1
        if self.public_error:
            raise self.public_error
        return self.public_info

    def get_live_game_stats(self) -> dict[str, object]:
        with self._lock:
            self.live_calls += 1
        if self.live_error:
            raise self.live_error
        return self.live_stats


class _FakeDatabase:
    def __init__(
        self,
        current_map: CrconCurrentMap | None = None,
        events: tuple[CrconMatchLogEvent, ...] | None = None,
    ) -> None:
        self.current_map = _current_map() if current_map is None else current_map
        self.events = _events() if events is None else events
        self.map_error: Exception | None = None
        self.event_error: Exception | None = None
        self.aggregate_error: Exception | None = None
        self.map_calls: list[dict[str, object]] = []
        self.event_calls: list[dict[str, object]] = []
        self.aggregate_calls: list[dict[str, object]] = []

    def find_current_map(self, **kwargs: object) -> CrconCurrentMap | None:
        self.map_calls.append(dict(kwargs))
        if self.map_error:
            raise self.map_error
        return self.current_map

    def list_match_log_events(self, **kwargs: object) -> tuple[CrconMatchLogEvent, ...]:
        self.event_calls.append(dict(kwargs))
        if self.event_error:
            raise self.event_error
        started_at = kwargs["started_at"]
        ended_at = kwargs["ended_at"]
        limit = int(kwargs["limit"])
        assert isinstance(started_at, datetime)
        assert isinstance(ended_at, datetime)
        bounded = (
            event
            for event in self.events
            if event.type in {"KILL", "TEAM KILL"}
            and started_at <= event.event_time.astimezone(UTC) <= ended_at
        )
        return tuple(
            sorted(
                bounded,
                key=lambda event: (event.event_time.astimezone(UTC), event.id),
                reverse=True,
            )[:limit]
        )

    def aggregate_match_combat_stats(
        self, **kwargs: object
    ) -> tuple[CrconMatchCombatStats, ...]:
        self.aggregate_calls.append(dict(kwargs))
        error = self.aggregate_error or self.event_error
        if error:
            raise error
        started_at = kwargs["started_at"]
        ended_at = kwargs["ended_at"]
        assert isinstance(started_at, datetime)
        assert isinstance(ended_at, datetime)
        return _aggregate_events(
            self.events,
            started_at=started_at,
            ended_at=ended_at,
        )


class _FakeClock:
    def __init__(self) -> None:
        self.monotonic = 100.0
        self.now = NOW

    def tick(self, seconds: float) -> None:
        self.monotonic += seconds
        self.now = self.now.replace(microsecond=0) + __import__("datetime").timedelta(
            seconds=seconds
        )


def _service(
    api: object,
    database: object | None = None,
    *,
    clock: _FakeClock | None = None,
    bindings: dict[str, CrconCurrentMatchBinding] | None = None,
) -> CurrentMatchSnapshotService:
    clock = clock or _FakeClock()
    return CurrentMatchSnapshotService(
        bindings=bindings or {_binding().server_slug: _binding()},
        api_factory=lambda _binding_value: api,
        database_factory=(
            (lambda _binding_value: database) if database is not None else None
        ),
        cache=TtlCache(
            max_entries=CURRENT_MATCH_CACHE_MAX_ENTRIES,
            ttl_seconds=CURRENT_MATCH_CACHE_TTL_SECONDS,
            clock=lambda: clock.monotonic,
        ),
        now=lambda: clock.now,
    )


class CurrentMatchConfigurationTests(unittest.TestCase):
    def test_source_defaults_to_legacy_and_accepts_explicit_values(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_current_match_source(), "legacy")
        with patch.dict(os.environ, {"HLL_CURRENT_MATCH_SOURCE": " crcon "}, clear=True):
            self.assertEqual(get_current_match_source(), "crcon")
        with patch.dict(os.environ, {"HLL_CURRENT_MATCH_SOURCE": " shadow "}, clear=True):
            self.assertEqual(get_current_match_source(), "shadow")

    def test_server_list_source_is_one_explicit_legacy_crcon_selector(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_server_list_source(), "legacy")
        with patch.dict(os.environ, {"HLL_SERVER_LIST_SOURCE": " crcon "}, clear=True):
            self.assertEqual(get_server_list_source(), "crcon")
        with patch.dict(os.environ, {"HLL_SERVER_LIST_SOURCE": "mixed"}, clear=True):
            with self.assertRaisesRegex(ValueError, "HLL_SERVER_LIST_SOURCE"):
                get_server_list_source()

    def test_invalid_source_is_actionable(self) -> None:
        with patch.dict(os.environ, {"HLL_CURRENT_MATCH_SOURCE": "mixed"}, clear=True):
            with self.assertRaisesRegex(ValueError, "HLL_CURRENT_MATCH_SOURCE"):
                get_current_match_source()

    def test_bindings_are_per_server_and_synthetic(self) -> None:
        configured = {
            "comunidad-hispana-01": {
                "api_base_url": "https://one.fixture.invalid",
                "server_number": 7,
                "api_headers": {"X-Test": "synthetic"},
                "capabilities": ["live_state", "historical_maps", "event_logs"],
            },
            "comunidad-hispana-02": {
                "api_base_url": "https://two.fixture.invalid",
                "server_number": 8,
                "game": "hllv",
                "log_server": "explicit-log-server-two",
                "log_game": 2,
            },
        }
        with patch.dict(
            os.environ,
            {"HLL_CRCON_CURRENT_MATCH_BINDINGS": json.dumps(configured)},
            clear=True,
        ):
            bindings = get_crcon_current_match_bindings()
        self.assertEqual([item["server_number"] for item in bindings], [7, 8])
        self.assertEqual([item["game"] for item in bindings], ["hll", "hllv"])
        self.assertEqual(bindings[1]["log_server"], "explicit-log-server-two")
        self.assertEqual(bindings[1]["log_game"], 2)
        self.assertNotEqual(bindings[0]["api_base_url"], bindings[1]["api_base_url"])

    def test_missing_bindings_do_not_break_legacy_config(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_current_match_source(), "legacy")
            self.assertEqual(get_crcon_current_match_bindings(), ())

    def test_binding_builder_uses_canonical_server_target(self) -> None:
        bindings = _build_bindings(
            (
                {
                    "server_slug": "comunidad-hll-vietnam-01",
                    "display_name": "HLL Vietnam",
                    "api_base_url": "https://hllv.fixture.invalid",
                    "server_number": 2,
                    "game": "hllv",
                    "enabled": True,
                    "capabilities": ("live_state",),
                    "log_server": None,
                },
            ),
            shared_database_url=None,
        )

        binding = bindings["comunidad-hll-vietnam-01"]
        self.assertEqual(binding.target.server_number, 2)
        self.assertEqual(binding.target.game, "hllv")
        self.assertEqual(binding.target.crcon_base_url, "https://hllv.fixture.invalid")

    def test_runtime_api_only_binding_drops_database_capabilities(self) -> None:
        bindings = _build_bindings(
            (
                {
                    "server_slug": "community-01",
                    "display_name": "Community",
                    "api_base_url": "https://fixture.invalid",
                    "server_number": 1,
                    "game": "hll",
                    "enabled": True,
                    "capabilities": ("live_state", "historical_maps", "event_logs"),
                },
            ),
            shared_database_url="postgresql://must-not-be-used.invalid/crcon",
            api_only=True,
        )

        self.assertEqual(bindings["community-01"].capabilities, frozenset({"live_state"}))
        self.assertIsNone(bindings["community-01"].database_url)


class CrconCurrentMatchAdapterTests(unittest.TestCase):
    def test_api_only_snapshot_uses_both_verified_calls_and_live_stats_as_canonical(self) -> None:
        verified_payload = json.loads(
            (VERIFIED_FIXTURE_DIR / "live_game_stats.json").read_text(encoding="utf-8")
        )
        api = _FakeApi(live_stats=parse_live_game_stats(verified_payload["result"]))
        binding = _build_bindings(
            (
                {
                    "server_slug": "comunidad-hispana-01",
                    "display_name": "Synthetic Local Server",
                    "api_base_url": "https://fixture.invalid",
                    "server_number": 7,
                    "game": "hll",
                    "enabled": True,
                },
            ),
            shared_database_url=None,
            api_only=True,
        )

        snapshot = _service(api, bindings=binding).get_snapshot("comunidad-hispana-01")

        self.assertEqual(api.public_calls, 1)
        self.assertEqual(api.live_calls, 1)
        self.assertEqual(snapshot.identity_kind, MatchIdentityKind.EPHEMERAL)
        self.assertFalse(snapshot.degraded)
        self.assertEqual(snapshot.kills, ())
        self.assertEqual(len(snapshot.source_states), 1)
        player = snapshot.players[0]
        self.assertEqual(player.player_id, "opaque-player-001")
        self.assertEqual((player.kills, player.deaths, player.teamkills), (3, 2, 0))
        self.assertEqual(player.deaths_by_teamkill, 0)
        self.assertEqual(player.favorite_weapon, "Synthetic Rifle")
        self.assertEqual(player.weapon_counts, (("Synthetic Rifle", 3),))

    def test_runtime_current_match_service_does_not_construct_postgres(self) -> None:
        configured = {
            "comunidad-hispana-01": {
                "api_base_url": "https://fixture.invalid",
                "server_number": 7,
            }
        }
        with (
            patch.dict(
                os.environ,
                {"HLL_CRCON_CURRENT_MATCH_BINDINGS": json.dumps(configured)},
                clear=False,
            ),
            patch("app.services.current_match._runtime_service", None),
            patch("app.services.current_match._runtime_fingerprint", None),
        ):
            service = get_current_match_snapshot_service()

        self.assertIsNone(service._database_factory)
        self.assertEqual(
            service._bindings["comunidad-hispana-01"].capabilities,
            frozenset({"live_state"}),
        )

    def test_api_only_refresh_failure_returns_stale_last_good(self) -> None:
        api = _FakeApi()
        database = MagicMock()
        clock = _FakeClock()
        binding = _build_bindings(
            (
                {
                    "server_slug": "comunidad-hispana-01",
                    "display_name": "Synthetic Local Server",
                    "api_base_url": "https://fixture.invalid",
                    "server_number": 7,
                    "game": "hll",
                    "enabled": True,
                    "capabilities": ("live_state",),
                },
            ),
            shared_database_url=None,
            api_only=True,
        )
        service = _service(api, clock=clock, bindings=binding)
        fresh = service.get_snapshot("comunidad-hispana-01")
        clock.tick(CURRENT_MATCH_CACHE_TTL_SECONDS + 0.1)
        api.public_error = TimeoutError("offline")
        api.live_error = TimeoutError("offline")

        stale = service.get_snapshot("comunidad-hispana-01")

        self.assertEqual(stale.match_id, fresh.match_id)
        self.assertTrue(stale.degraded)
        self.assertIn("crcon-live-last-good-stale", stale.degraded_reasons)
        self.assertFalse(fresh.degraded)
        self.assertEqual(fresh.players[0].kills, 99)
        database.assert_not_called()

    def test_live_game_stats_uses_verified_endpoint(self) -> None:
        requests: list[object] = []

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def read(self) -> bytes:
                return b'{"result":{"stats":[]},"failed":false}'

        def transport(request, _timeout):
            requests.append(request)
            return Response()

        client = CrconApiClient(
            base_url="https://fixture.invalid",
            timeout_seconds=1,
            transport=transport,
        )
        self.assertEqual(client.get_live_game_stats().players, ())
        self.assertEqual(requests[0].full_url, "https://fixture.invalid/api/get_live_game_stats")

    def test_database_methods_are_read_only_bounded_and_deterministic(self) -> None:
        connections: list[_RecordingConnection] = []

        def connector(*_args, **_kwargs):
            connection = _RecordingConnection()
            connections.append(connection)
            return connection

        database = PostgresCrconRepository(
            dsn="postgresql://fixture.invalid/crcon",
            connect_timeout_seconds=2,
            statement_timeout_ms=1000,
            lock_timeout_ms=10,
            connector=connector,
        )
        current_map = database.find_current_map(
            server_number=7,
            map_name="synthetic_forest_warfare",
            started_at=datetime(2026, 8, 14, 8, 0, tzinfo=UTC),
        )
        events = database.list_match_log_events(
            scope=CrconServerScope(7, "hll", "synthetic-server-7", 1),
            started_at=datetime(2026, 8, 14, 8, 0, tzinfo=UTC),
            ended_at=NOW,
            limit=50,
        )
        combat = database.aggregate_match_combat_stats(
            scope=CrconServerScope(7, "hll", "synthetic-server-7", 1),
            started_at=datetime(2026, 8, 14, 8, 0, tzinfo=UTC),
            ended_at=NOW,
        )
        self.assertEqual(current_map.id, 9002)
        self.assertEqual([event.id for event in events], [411, 410])
        self.assertEqual((combat[0].kills, combat[0].teamkills), (1, 1))
        self.assertEqual(combat[0].weapon_counts, (("SYNTHETIC_RIFLE", 1),))
        self.assertIn("ORDER BY start DESC, id DESC", connections[0].statements[-1][0])
        self.assertIn("ORDER BY logs.event_time DESC, logs.id DESC", connections[1].statements[-1][0])
        self.assertEqual(connections[1].statements[-1][1][-1], 50)
        self.assertIn("ORDER BY totals.player_key ASC", connections[2].statements[-1][0])
        self.assertNotIn("LIMIT", connections[2].statements[-1][0])
        self.assertIn("WHERE type = 'KILL'", connections[2].statements[-1][0])
        self.assertEqual(
            connections[2].statements[-1][1],
            (
                "synthetic-server-7",
                1,
                datetime(2026, 8, 14, 8, 0, tzinfo=UTC),
                NOW,
                ["KILL", "TEAM KILL"],
            ),
        )
        self.assertTrue(all(connection.rolled_back and connection.closed for connection in connections))

    def test_new_sql_surface_contains_no_mutation_statement(self) -> None:
        sql = (
            f"{CURRENT_MAP_MATCH_SQL}\n{MATCH_LOG_EVENTS_SQL}\n"
            f"{MATCH_COMBAT_AGGREGATE_SQL}"
        ).upper()
        for keyword in (
            "INSERT",
            "UPDATE",
            "DELETE",
            "MERGE",
            "CREATE",
            "ALTER",
            "DROP",
            "TRUNCATE",
            "VACUUM",
            "REINDEX",
        ):
            self.assertNotIn(keyword, sql)


class CurrentMatchSnapshotTests(unittest.TestCase):
    def test_current_match_without_players_is_valid_and_not_fabricated(self) -> None:
        api = _FakeApi(live_stats={"stats": []})
        database = _FakeDatabase(events=())

        snapshot = _service(api, database).get_snapshot(_binding().server_slug)

        self.assertEqual(snapshot.players, ())
        self.assertEqual(snapshot.kills, ())

    def test_canonical_identity_and_coherent_snapshot(self) -> None:
        api = _FakeApi()
        database = _FakeDatabase()
        snapshot = _service(api, database).get_snapshot(_binding().server_slug)

        self.assertEqual(snapshot.identity_kind, MatchIdentityKind.CANONICAL)
        self.assertTrue(snapshot.match_id.startswith("cm1."))
        self.assertEqual(snapshot.summary.layer, "synthetic_forest_warfare")
        self.assertEqual(snapshot.summary.allied_score, 3)
        self.assertEqual(len(snapshot.kills), 3)
        self.assertEqual(database.event_calls[0]["started_at"], snapshot.summary.started_at)
        self.assertEqual(database.event_calls[0]["ended_at"], NOW)

    def test_api_ahead_of_database_uses_ephemeral_identity(self) -> None:
        database = _FakeDatabase()
        database.current_map = None
        snapshot = _service(_FakeApi(), database).get_snapshot(_binding().server_slug)

        self.assertEqual(snapshot.identity_kind, MatchIdentityKind.EPHEMERAL)
        self.assertTrue(snapshot.match_id.startswith("em1."))
        self.assertIn("crcon-map-identity-pending", snapshot.degraded_reasons)

    def test_conflicting_latest_map_is_not_selected(self) -> None:
        database = _FakeDatabase(current_map=_current_map(8999))
        database.current_map = None
        snapshot = _service(_FakeApi(), database).get_snapshot(_binding().server_slug)
        self.assertEqual(snapshot.identity_kind, MatchIdentityKind.EPHEMERAL)

    def test_events_use_type_order_weapon_and_distinct_duplicate_timestamps(self) -> None:
        snapshot = _service(_FakeApi(), _FakeDatabase()).get_snapshot(_binding().server_slug)
        self.assertEqual([event.position_id for event in snapshot.kills], [410, 411, 412])
        self.assertFalse(snapshot.kills[0].teamkill)
        self.assertTrue(snapshot.kills[1].teamkill)
        self.assertEqual(snapshot.kills[1].weapon, "SYNTHETIC_GRENADE")
        self.assertNotEqual(snapshot.kills[0].cursor, snapshot.kills[1].cursor)

    def test_events_outside_current_match_bounds_do_not_leak(self) -> None:
        outside = (
            CrconMatchLogEvent(
                id=1,
                event_time=datetime(2026, 8, 14, 7, 59, 59, tzinfo=UTC),
                type="KILL",
                player1_name="Outside Killer",
                player1_id="outside-killer",
                player2_name="Outside Victim",
                player2_id="outside-victim",
                weapon="OUTSIDE_WEAPON",
            ),
            CrconMatchLogEvent(
                id=999,
                event_time=datetime(2026, 8, 14, 8, 15, 1, tzinfo=UTC),
                type="KILL",
                player1_name="Future Killer",
                player1_id="future-killer",
                player2_name="Future Victim",
                player2_id="future-victim",
                weapon="FUTURE_WEAPON",
            ),
        )
        database = _FakeDatabase(events=outside + _events())
        snapshot = _service(_FakeApi(), database).get_snapshot(_binding().server_slug)
        self.assertEqual([event.position_id for event in snapshot.kills], [410, 411, 412])

    def test_more_than_500_events_use_complete_aggregate_and_newest_feed(self) -> None:
        clock = _FakeClock()
        database = _FakeDatabase(events=_many_events())
        service = _service(_FakeApi(), database, clock=clock)

        first = service.get_snapshot(_binding().server_slug)
        players = {player.name: player for player in first.players}
        self.assertEqual(len(first.kills), 500)
        self.assertEqual(first.kills[0].position_id, 1100)
        self.assertEqual(first.kills[-1].position_id, 1599)
        self.assertEqual(
            [event.position_id for event in first.kills[:3]],
            [1100, 1101, 1102],
        )
        self.assertTrue(first.killfeed_truncated)
        self.assertEqual(players["Fixture Alpha"].kills, 600)
        self.assertEqual(players["Fixture Bravo"].deaths, 600)
        self.assertEqual(
            players["Fixture Alpha"].weapon_counts,
            (("SYNTHETIC_RIFLE", 600),),
        )
        self.assertEqual(database.event_calls[0]["limit"], 500)
        self.assertNotIn("limit", database.aggregate_calls[0])

        database.events = _many_events(601)
        clock.tick(2)
        second = service.get_snapshot(_binding().server_slug)
        self.assertEqual(second.kills[-1].position_id, 1600)
        self.assertNotEqual(first.version, second.version)

    def test_same_match_cursor_before_truncated_same_timestamp_window_is_rejected(self) -> None:
        service = _service(_FakeApi(), _FakeDatabase(events=_many_events()))
        snapshot = service.get_snapshot(_binding().server_slug)
        old_cursor = encode_kill_cursor(
            snapshot.match_id,
            snapshot.kills[0].timestamp,
            snapshot.kills[0].position_id - 1,
        )
        with self.assertRaisesRegex(CurrentMatchCursorError, "predates"):
            service.project_kills(snapshot, since_cursor=old_cursor, limit=100)

        continued = service.project_kills(
            snapshot,
            since_cursor=snapshot.kills[0].cursor,
            limit=2,
        )
        self.assertEqual(
            [event.position_id for event in continued],
            [snapshot.kills[0].position_id + 1, snapshot.kills[0].position_id + 2],
        )

    def test_cursor_continues_same_match_and_rejects_malformed_or_old_match(self) -> None:
        service = _service(_FakeApi(), _FakeDatabase())
        snapshot = service.get_snapshot(_binding().server_slug)
        continued = service.project_kills(
            snapshot,
            since_cursor=snapshot.kills[0].cursor,
            limit=10,
        )
        self.assertEqual([event.position_id for event in continued], [411, 412])
        with self.assertRaises(CurrentMatchCursorError):
            service.project_kills(snapshot, since_cursor="bad", limit=10)
        old_cursor = encode_kill_cursor("cm1.b2xk", NOW, 1)
        with self.assertRaisesRegex(CurrentMatchCursorError, "different"):
            service.project_kills(snapshot, since_cursor=old_cursor, limit=10)

    def test_cursor_encoding_is_deterministic_and_match_scoped(self) -> None:
        cursor = encode_kill_cursor("cm1.OTAwMg", NOW, 411)
        self.assertEqual(cursor, encode_kill_cursor("cm1.OTAwMg", NOW, 411))
        self.assertEqual(decode_kill_cursor(cursor), ("cm1.OTAwMg", NOW, 411))

    def test_logs_are_canonical_for_player_kd_and_teamkills(self) -> None:
        snapshot = _service(_FakeApi(), _FakeDatabase()).get_snapshot(_binding().server_slug)
        players = {player.name: player for player in snapshot.players}
        alpha = players["Fixture Alpha"]
        bravo = players["Fixture Bravo"]
        charlie = players["Fixture Charlie"]
        self.assertEqual((alpha.kills, alpha.deaths, alpha.teamkills), (1, 1, 1))
        self.assertEqual((bravo.kills, bravo.deaths, bravo.teamkills), (1, 1, 0))
        self.assertEqual((charlie.deaths, charlie.deaths_by_teamkill), (0, 1))
        self.assertEqual(alpha.favorite_weapon, "SYNTHETIC_RIFLE")
        self.assertEqual(alpha.weapon_counts, (("SYNTHETIC_RIFLE", 1),))
        self.assertNotIn("SYNTHETIC_GRENADE", dict(alpha.weapon_counts))
        self.assertIn("crcon-api-log-combat-disagreement", snapshot.degraded_reasons)

    def test_version_is_stable_for_identical_material_and_changes_with_score(self) -> None:
        clock = _FakeClock()
        api = _FakeApi()
        database = _FakeDatabase()
        service = _service(api, database, clock=clock)
        first = service.get_snapshot(_binding().server_slug)
        clock.tick(2)
        second = service.get_snapshot(_binding().server_slug)
        self.assertEqual(first.version, second.version)

        api.public_info = json.loads(json.dumps(api.public_info))
        api.public_info["score"]["allied"] = 4
        clock.tick(2)
        third = service.get_snapshot(_binding().server_slug)
        self.assertNotEqual(second.version, third.version)

    def test_match_transition_changes_identity_version_and_rejects_old_cursor(self) -> None:
        clock = _FakeClock()
        api = _FakeApi()
        database = _FakeDatabase()
        service = _service(api, database, clock=clock)
        first = service.get_snapshot(_binding().server_slug)
        old_cursor = first.kills[-1].cursor

        api.public_info = json.loads(json.dumps(api.public_info))
        api.public_info["current_map"] = {
            "map": "synthetic_river_offensive",
            "start": "2026-08-14T08:16:00Z",
        }
        database.current_map = CrconCurrentMap(
            id=9003,
            start=datetime(2026, 8, 14, 8, 16, tzinfo=UTC),
            end=None,
            server_number=7,
            map_name="synthetic_river_offensive",
            result=None,
        )
        database.events = ()
        clock.tick(120)
        second = service.get_snapshot(_binding().server_slug)
        self.assertNotEqual(first.match_id, second.match_id)
        self.assertNotEqual(first.version, second.version)
        with self.assertRaises(CurrentMatchCursorError):
            service.project_kills(second, since_cursor=old_cursor, limit=10)

    def test_api_healthy_database_unavailable_is_degraded_without_fake_combat_zero(self) -> None:
        database = _FakeDatabase()
        database.map_error = RuntimeError("offline")
        database.event_error = RuntimeError("offline")
        snapshot = _service(_FakeApi(), database).get_snapshot(_binding().server_slug)
        self.assertTrue(snapshot.degraded)
        self.assertIn("crcon-map-history-unavailable", snapshot.degraded_reasons)
        self.assertIn("crcon-event-feed-unavailable", snapshot.degraded_reasons)
        self.assertIn("crcon-combat-aggregate-unavailable", snapshot.degraded_reasons)
        self.assertIsNone(snapshot.players[0].kills)

    def test_map_history_failure_does_not_hide_available_bounded_logs(self) -> None:
        database = _FakeDatabase()
        database.map_error = RuntimeError("map history offline")
        snapshot = _service(_FakeApi(), database).get_snapshot(_binding().server_slug)
        self.assertEqual(snapshot.identity_kind, MatchIdentityKind.EPHEMERAL)
        self.assertEqual(len(snapshot.kills), 3)
        self.assertIn("crcon-map-history-unavailable", snapshot.degraded_reasons)

    def test_database_healthy_api_unavailable_keeps_bounded_db_state(self) -> None:
        api = _FakeApi()
        api.public_error = TimeoutError()
        api.live_error = TimeoutError()
        snapshot = _service(api, _FakeDatabase()).get_snapshot(_binding().server_slug)
        self.assertEqual(snapshot.identity_kind, MatchIdentityKind.CANONICAL)
        self.assertIsNone(snapshot.summary.player_count)
        self.assertEqual(len(snapshot.kills), 3)
        self.assertIn("crcon-api-public-info-unavailable", snapshot.degraded_reasons)

    def test_both_sources_unavailable_raise_instead_of_fake_empty_match(self) -> None:
        api = _FakeApi()
        api.public_error = TimeoutError()
        api.live_error = TimeoutError()
        database = _FakeDatabase()
        database.map_error = RuntimeError("offline")
        with self.assertRaises(CurrentMatchUnavailableError):
            _service(api, database).get_snapshot(_binding().server_slug)


class CurrentMatchCacheAndSingleFlightTests(unittest.TestCase):
    def test_ttl_hit_and_expiry_control_refreshes(self) -> None:
        clock = _FakeClock()
        api = _FakeApi()
        service = _service(api, _FakeDatabase(), clock=clock)
        service.get_snapshot(_binding().server_slug)
        service.get_snapshot(_binding().server_slug)
        self.assertEqual(api.public_calls, 1)
        clock.tick(2)
        service.get_snapshot(_binding().server_slug)
        self.assertEqual(api.public_calls, 2)

    def test_simultaneous_same_server_callers_share_one_refresh(self) -> None:
        api = _BlockingApi()
        service = _service(api, _FakeDatabase())
        results: list[object] = []
        errors: list[BaseException] = []

        def call() -> None:
            try:
                results.append(service.get_snapshot(_binding().server_slug))
            except BaseException as error:
                errors.append(error)

        threads = [Thread(target=call) for _ in range(6)]
        for thread in threads:
            thread.start()
        self.assertTrue(api.started.wait(timeout=2))
        api.release.set()
        for thread in threads:
            thread.join(timeout=2)
        self.assertEqual(errors, [])
        self.assertEqual(len(results), 6)
        self.assertEqual(api.public_calls, 1)
        self.assertEqual(api.live_calls, 1)
        self.assertEqual(len({id(result) for result in results}), 1)

    def test_different_server_keys_refresh_independently(self) -> None:
        started = {"comunidad-hispana-01": Event(), "comunidad-hispana-02": Event()}
        release = Event()
        apis = {
            slug: _PerServerBlockingApi(started[slug], release)
            for slug in started
        }
        databases = {
            "comunidad-hispana-01": _FakeDatabase(),
            "comunidad-hispana-02": _FakeDatabase(
                current_map=CrconCurrentMap(
                    id=9100,
                    start=datetime(2026, 8, 14, 8, 0, tzinfo=UTC),
                    end=None,
                    server_number=8,
                    map_name="synthetic_forest_warfare",
                    result=None,
                )
            ),
        }
        bindings = {
            "comunidad-hispana-01": _binding(),
            "comunidad-hispana-02": _binding("comunidad-hispana-02", server_number=8),
        }
        service = CurrentMatchSnapshotService(
            bindings=bindings,
            api_factory=lambda binding: apis[binding.server_slug],
            database_factory=lambda binding: databases[binding.server_slug],
            now=lambda: NOW,
        )
        threads = [
            Thread(target=service.get_snapshot, args=(slug,))
            for slug in bindings
        ]
        for thread in threads:
            thread.start()
        self.assertTrue(all(event.wait(timeout=2) for event in started.values()))
        release.set()
        for thread in threads:
            thread.join(timeout=2)
        self.assertEqual([api.public_calls for api in apis.values()], [1, 1])

    def test_refresh_exception_clears_flight_for_later_retry(self) -> None:
        api = _FakeApi()
        api.public_error = TimeoutError()
        api.live_error = TimeoutError()
        database = _FakeDatabase()
        database.map_error = RuntimeError("offline")
        service = _service(api, database)
        with self.assertRaises(CurrentMatchUnavailableError):
            service.get_snapshot(_binding().server_slug)
        api.public_error = None
        api.live_error = None
        database.map_error = None
        snapshot = service.get_snapshot(_binding().server_slug)
        self.assertTrue(snapshot.match_id)
        self.assertEqual(api.public_calls, 2)


class CurrentMatchRouteAndCompatibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        targets = patch.dict(
            os.environ,
            {"HLL_SERVER_TARGETS": _server_target_payload()},
            clear=False,
        )
        targets.start()
        self.addCleanup(targets.stop)

    def test_new_snapshot_route_and_unsupported_server(self) -> None:
        service = _service(_FakeApi(), _FakeDatabase())
        with (
            patch.dict(os.environ, {"HLL_CURRENT_MATCH_SOURCE": "crcon"}, clear=False),
            patch.object(payloads, "get_current_match_snapshot_service", return_value=service),
        ):
            status, response = resolve_get_payload(
                "/api/current-match/snapshot?server=comunidad-hispana-01"
            )
        self.assertEqual(int(status), 200)
        self.assertEqual(response["data"]["identity_kind"], "canonical")
        self.assertIn("version", response["data"])

        status, _response = resolve_get_payload(
            "/api/current-match/snapshot?server=not-trusted"
        )
        self.assertEqual(int(status), 404)

    def test_hllv_snapshot_route_does_not_require_scoreboard_origin(self) -> None:
        slug = "comunidad-hll-vietnam-01"
        binding = _binding(slug, server_number=3, game="hllv")
        service = _service(_FakeApi(), bindings={slug: binding})
        self.assertIsNone(get_trusted_public_scoreboard_origin(slug))
        with (
            patch.dict(
                os.environ,
                {
                    "HLL_CURRENT_MATCH_SOURCE": "crcon",
                    "HLL_SERVER_TARGETS": _server_target_payload(
                        slug,
                        server_number=3,
                        game="hllv",
                    ),
                },
                clear=False,
            ),
            patch.object(payloads, "get_current_match_snapshot_service", return_value=service),
        ):
            status, response = resolve_get_payload(
                f"/api/current-match/snapshot?server={slug}"
            )

        self.assertEqual(int(status), 200)
        self.assertEqual(response["data"]["server_slug"], slug)

    def test_malformed_crcon_kill_cursor_returns_stable_400(self) -> None:
        service = _service(_FakeApi(), _FakeDatabase())
        with (
            patch.dict(os.environ, {"HLL_CURRENT_MATCH_SOURCE": "crcon"}, clear=False),
            patch.object(payloads, "get_current_match_snapshot_service", return_value=service),
        ):
            status, response = resolve_get_payload(
                "/api/current-match/kills?server=comunidad-hispana-01&limit=20&since_event_id=bad"
            )
        self.assertEqual(int(status), 400)
        self.assertEqual(response["status"], "error")

    def test_truncated_crcon_kill_cursor_returns_stable_400(self) -> None:
        service = _service(_FakeApi(), _FakeDatabase(events=_many_events()))
        snapshot = service.get_snapshot(_binding().server_slug)
        old_cursor = encode_kill_cursor(
            snapshot.match_id,
            snapshot.kills[0].timestamp,
            snapshot.kills[0].position_id - 1,
        )
        with (
            patch.dict(os.environ, {"HLL_CURRENT_MATCH_SOURCE": "crcon"}, clear=False),
            patch.object(payloads, "get_current_match_snapshot_service", return_value=service),
        ):
            status, response = resolve_get_payload(
                "/api/current-match/kills"
                f"?server=comunidad-hispana-01&limit=20&since_event_id={old_cursor}"
            )
        self.assertEqual(int(status), 400)
        self.assertEqual(response["status"], "error")

    def test_crcon_compatibility_routes_share_one_cached_snapshot(self) -> None:
        api = _FakeApi()
        binding = _build_bindings(
            (
                {
                    "server_slug": "comunidad-hispana-01",
                    "display_name": "Synthetic Local Server",
                    "api_base_url": "https://fixture.invalid",
                    "server_number": 7,
                    "game": "hll",
                    "enabled": True,
                },
            ),
            shared_database_url=None,
            api_only=True,
        )
        service = _service(api, bindings=binding)
        with (
            patch.dict(os.environ, {"HLL_CURRENT_MATCH_SOURCE": "crcon"}, clear=False),
            patch.object(payloads, "get_current_match_snapshot_service", return_value=service),
        ):
            summary = payloads.build_current_match_payload(
                server_slug="comunidad-hispana-01"
            )
            kills = payloads.build_current_match_kill_feed_payload(
                server_slug="comunidad-hispana-01",
                limit=30,
            )
            players = payloads.build_current_match_player_stats_payload(
                server_slug="comunidad-hispana-01"
            )
        self.assertEqual(api.public_calls, 1)
        self.assertEqual(summary["data"]["map_pretty_name"], "Synthetic Forest Warfare")
        self.assertEqual(kills["data"]["items"], [])
        self.assertEqual(kills["data"]["selected_source"], "crcon-log-stream")
        self.assertIn("player_name", players["data"]["items"][0])
        self.assertEqual(players["data"]["items"][0]["kills"], 99)
        self.assertEqual(players["data"]["selected_source"], "crcon-live-game-stats")

    def test_legacy_default_does_not_construct_crcon_service(self) -> None:
        sample = {
            "normalized": {
                "server_name": "Synthetic Legacy",
                "status": "online",
                "current_map": "carentan_warfare",
            },
            "raw_session": {"mapId": "carentan_warfare"},
        }
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(payloads, "_query_current_match_rcon_sample", return_value=sample),
            patch.object(payloads, "get_current_match_snapshot_service") as service_factory,
        ):
            response = payloads.build_current_match_payload(
                server_slug="comunidad-hispana-01"
            )
        service_factory.assert_not_called()
        self.assertEqual(response["data"]["status"], "online")

    def test_crcon_failure_never_calls_legacy_helpers(self) -> None:
        unavailable = MagicMock()
        unavailable.get_snapshot.side_effect = CurrentMatchUnavailableError("offline")
        with (
            patch.dict(os.environ, {"HLL_CURRENT_MATCH_SOURCE": "crcon"}, clear=False),
            patch.object(payloads, "get_current_match_snapshot_service", return_value=unavailable),
            patch.object(payloads, "_query_current_match_rcon_sample") as legacy_summary,
            patch.object(payloads, "list_current_match_kill_feed") as legacy_kills,
            patch.object(payloads, "list_current_match_player_stats") as legacy_players,
        ):
            status, _response = resolve_get_payload(
                "/api/current-match?server=comunidad-hispana-01"
            )
        self.assertEqual(int(status), 503)
        legacy_summary.assert_not_called()
        legacy_kills.assert_not_called()
        legacy_players.assert_not_called()


class _Cursor:
    def __init__(self, *, one: object = None, many: object = None) -> None:
        self._one = one
        self._many = many if many is not None else []

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._many


class _RecordingConnection:
    def __init__(self) -> None:
        self.statements: list[tuple[str, tuple[object, ...]]] = []
        self.rolled_back = False
        self.closed = False

    def execute(self, sql: str, params: tuple[object, ...] = ()) -> _Cursor:
        self.statements.append((sql, params))
        normalized = " ".join(sql.split()).upper()
        if normalized.startswith("SHOW TRANSACTION_READ_ONLY"):
            return _Cursor(one=("on",))
        if "FROM MAP_HISTORY" in normalized:
            return _Cursor(
                many=[
                    (
                        9002,
                        datetime(2026, 8, 14, 8, 0, tzinfo=UTC),
                        None,
                        7,
                        "synthetic_forest_warfare",
                        None,
                    )
                ]
            )
        if normalized.startswith("WITH BOUNDED_EVENTS"):
            return _Cursor(
                many=[
                    (
                        "synthetic-player-alpha",
                        "Fixture Alpha",
                        1,
                        1,
                        1,
                        0,
                        {"SYNTHETIC_RIFLE": 1},
                    )
                ]
            )
        if "FROM LOG_LINES" in normalized:
            return _Cursor(
                many=[
                    (
                        411,
                        datetime(2026, 8, 14, 8, 4, 1, tzinfo=UTC),
                        "TEAM KILL",
                        "Fixture Alpha",
                        "synthetic-player-alpha",
                        "Fixture Charlie",
                        "synthetic-player-charlie",
                        "SYNTHETIC_GRENADE",
                    ),
                    (
                        410,
                        datetime(2026, 8, 14, 8, 4, 1, tzinfo=UTC),
                        "KILL",
                        "Fixture Alpha",
                        "synthetic-player-alpha",
                        "Fixture Bravo",
                        "synthetic-player-bravo",
                        "SYNTHETIC_RIFLE",
                    ),
                ]
            )
        return _Cursor()

    def rollback(self) -> None:
        self.rolled_back = True

    def close(self) -> None:
        self.closed = True


class _BlockingApi(_FakeApi):
    def __init__(self) -> None:
        super().__init__()
        self.started = Event()
        self.release = Event()

    def get_public_info(self) -> dict[str, object]:
        with self._lock:
            self.public_calls += 1
        self.started.set()
        if not self.release.wait(timeout=2):
            raise TimeoutError()
        return self.public_info


class _PerServerBlockingApi(_FakeApi):
    def __init__(self, started: Event, release: Event) -> None:
        super().__init__()
        self.started = started
        self.release = release

    def get_public_info(self) -> dict[str, object]:
        with self._lock:
            self.public_calls += 1
        self.started.set()
        if not self.release.wait(timeout=2):
            raise TimeoutError()
        return self.public_info


if __name__ == "__main__":
    unittest.main()
