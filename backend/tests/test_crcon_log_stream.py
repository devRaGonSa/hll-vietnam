from __future__ import annotations

import json
import os
import time
import unittest
from collections import deque
from datetime import UTC, datetime, timedelta
from threading import Event, Lock
from unittest.mock import MagicMock, patch

from websocket import WebSocketBadStatusException, WebSocketTimeoutException

from app import payloads
from app import main as backend_main
from app.config import get_crcon_log_stream_tokens
from app.crcon.cache import TtlCache
from app.crcon.log_stream import (
    CRCON_CURRENT_MATCH_ACTIONS,
    CrconCurrentMatchEvent,
    CrconLogStreamManager,
    CrconLogStreamStatus,
    CrconLogStreamTarget,
    CrconLogStreamWindow,
    parse_log_stream_payload,
)
from app.current_match import (
    CrconCurrentMatchBinding,
    CurrentMatchSnapshotService,
    decode_stream_kill_cursor,
)
from app.server_targets import ServerTarget


NOW = datetime(2026, 8, 23, 12, 0, tzinfo=UTC)


def _log(
    event_id: str,
    *,
    action: str = "KILL",
    timestamp: datetime = NOW,
    killer_id: str | None = "EOS-like:opaque-player-alpha",
    victim_id: str | None = "opaque-player-bravo",
    weapon: str | None = "Synthetic Rifle",
) -> dict[str, object]:
    return {
        "id": event_id,
        "log": {
            "timestamp_ms": int(timestamp.timestamp() * 1000),
            "action": action,
            "player_name_1": "Alpha",
            "player_id_1": killer_id,
            "player_name_2": "Bravo",
            "player_id_2": victim_id,
            "weapon": weapon,
        },
    }


def _payload(
    *logs: dict[str, object],
    last_seen_id: str | None = None,
    error: str | None = None,
) -> str:
    return json.dumps(
        {
            "logs": list(logs),
            "last_seen_id": last_seen_id,
            "error": error,
        }
    )


class _FakeConnection:
    def __init__(self, responses: list[object]) -> None:
        self._responses = deque(responses)
        self.sent: list[str] = []
        self.closed = Event()

    def send(self, payload: str) -> None:
        self.sent.append(payload)

    def recv(self) -> str | bytes | None:
        if self.closed.is_set():
            return None
        if self._responses:
            response = self._responses.popleft()
            if isinstance(response, BaseException):
                raise response
            return response  # type: ignore[return-value]
        time.sleep(0.005)
        raise WebSocketTimeoutException("fixture timeout")

    def close(self) -> None:
        self.closed.set()


class _Factory:
    def __init__(self, outcomes: list[object] | dict[str, list[object]]) -> None:
        self._outcomes = outcomes
        self.calls: list[tuple[str, tuple[str, ...], float]] = []
        self.connections: list[_FakeConnection] = []
        self._lock = Lock()

    def __call__(
        self,
        url: str,
        headers: tuple[str, ...],
        timeout: float,
    ) -> _FakeConnection:
        with self._lock:
            self.calls.append((url, headers, timeout))
            if isinstance(self._outcomes, dict):
                key = next(key for key in self._outcomes if key in url)
                outcome = self._outcomes[key].pop(0)
            else:
                outcome = self._outcomes.pop(0)
            if isinstance(outcome, BaseException):
                raise outcome
            assert isinstance(outcome, _FakeConnection)
            self.connections.append(outcome)
            return outcome


def _target(slug: str = "community-01", token: str = "fixture-secret") -> CrconLogStreamTarget:
    return CrconLogStreamTarget(
        server_slug=slug,
        base_url=f"https://{slug}.fixture.invalid/crcon",
        bearer_token=token,
    )


def _wait_until(predicate, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("Timed out waiting for fixture condition.")


class CrconLogStreamContractTests(unittest.TestCase):
    def test_verified_kill_teamkill_filter_order_and_optional_fields(self) -> None:
        raw = _payload(
            _log("1000-1"),
            _log(
                "1000-2",
                action="TEAM KILL",
                killer_id=None,
                victim_id="EOS:opaque-not-a-platform-claim",
                weapon=None,
            ),
            _log("1000-3", action="CHAT"),
            last_seen_id="1000-3",
        )

        batch = parse_log_stream_payload(raw)

        self.assertEqual([event.event_id for event in batch.events], ["1000-1", "1000-2"])
        self.assertEqual([event.teamkill for event in batch.events], [False, True])
        self.assertEqual(batch.events[0].killer_id, "EOS-like:opaque-player-alpha")
        self.assertIsNone(batch.events[1].killer_id)
        self.assertEqual(batch.events[1].victim_id, "EOS:opaque-not-a-platform-claim")
        self.assertIsNone(batch.events[1].weapon)
        self.assertEqual(batch.last_seen_id, "1000-3")

    def test_event_time_fallback_is_normalized_to_utc(self) -> None:
        row = _log("1000-1")
        structured = row["log"]
        assert isinstance(structured, dict)
        structured.pop("timestamp_ms")
        structured["event_time"] = "2026-08-23T14:00:00+02:00"

        event = parse_log_stream_payload(_payload(row)).events[0]

        self.assertEqual(event.timestamp, NOW)

    def test_subscription_uses_server_side_bearer_auth_and_exact_actions(self) -> None:
        connection = _FakeConnection([_payload(last_seen_id=None)])
        factory = _Factory([connection])
        manager = CrconLogStreamManager((_target(),), connection_factory=factory)
        manager.start()
        _wait_until(lambda: bool(connection.sent))

        subscription = json.loads(connection.sent[0])
        url, headers, _timeout = factory.calls[0]
        manager.stop()

        self.assertEqual(url, "wss://community-01.fixture.invalid/crcon/ws/logs")
        self.assertEqual(headers, ("Authorization: Bearer fixture-secret",))
        self.assertEqual(subscription["actions"], list(CRCON_CURRENT_MATCH_ACTIONS))
        self.assertIsNone(subscription["last_seen_id"])

    def test_tokens_are_secret_only_environment_configuration(self) -> None:
        configured = {"community-01": " secret-one ", "community-02": "secret-two"}
        with patch.dict(
            os.environ,
            {"HLL_CRCON_LOG_STREAM_TOKENS": json.dumps(configured)},
            clear=True,
        ):
            tokens = get_crcon_log_stream_tokens()
        self.assertEqual(tokens["community-01"], "secret-one")
        with patch.dict(
            os.environ,
            {"HLL_CRCON_LOG_STREAM_TOKENS": "[]"},
            clear=True,
        ):
            with self.assertRaisesRegex(ValueError, "HLL_CRCON_LOG_STREAM_TOKENS"):
                get_crcon_log_stream_tokens()


class CrconLogStreamLifecycleTests(unittest.TestCase):
    def test_buffer_is_bounded_to_frontend_useful_window(self) -> None:
        logs = tuple(_log(f"1000-{index}") for index in range(20))
        connection = _FakeConnection([_payload(*logs, last_seen_id="1000-19")])
        manager = CrconLogStreamManager(
            (_target(),),
            connection_factory=_Factory([connection]),
        )
        manager.start()
        _wait_until(
            lambda: manager.window_for_match(
                "community-01", "match-1", NOW - timedelta(minutes=1)
            ).last_seen_id
            == "1000-19"
        )
        window = manager.window_for_match(
            "community-01", "match-1", NOW - timedelta(minutes=1)
        )
        manager.stop()

        self.assertEqual(len(window.events), 18)
        self.assertEqual(window.events[0].event_id, "1000-2")
        self.assertEqual(window.events[-1].event_id, "1000-19")
        self.assertTrue(window.truncated)

    def test_last_seen_reconnect_duplicate_replay_and_order(self) -> None:
        first = _FakeConnection(
            [
                _payload(_log("1000-1"), last_seen_id="1000-1"),
                ConnectionError("transient"),
            ]
        )
        second = _FakeConnection(
            [
                _payload(
                    _log("1000-1"),
                    _log("1000-2", action="TEAM KILL"),
                    last_seen_id="1000-2",
                )
            ]
        )
        factory = _Factory([first, second])
        manager = CrconLogStreamManager(
            (_target(),),
            connection_factory=factory,
            backoff_seconds=(0.0,),
        )
        manager.start()
        _wait_until(
            lambda: len(
                manager.window_for_match("community-01", "match-1", NOW - timedelta(minutes=1)).events
            )
            == 2
        )
        window = manager.window_for_match(
            "community-01", "match-1", NOW - timedelta(minutes=1)
        )
        manager.stop()

        self.assertEqual(json.loads(second.sent[0])["last_seen_id"], "1000-1")
        self.assertEqual([event.event_id for event in window.events], ["1000-1", "1000-2"])
        self.assertEqual(window.last_seen_id, "1000-2")
        self.assertEqual(window.status, CrconLogStreamStatus.AVAILABLE)

    def test_invalid_cursor_resets_to_tail_and_marks_gap(self) -> None:
        invalid = _FakeConnection(
            [
                _payload(
                    error="Invalid stream ID specified as stream command argument"
                )
            ]
        )
        resumed = _FakeConnection(
            [_payload(_log("2000-0"), last_seen_id="2000-0")]
        )
        factory = _Factory([invalid, resumed])
        manager = CrconLogStreamManager(
            (_target(),),
            connection_factory=factory,
            backoff_seconds=(0.0,),
        )
        manager.start()
        _wait_until(lambda: bool(resumed.sent))
        _wait_until(
            lambda: manager.window_for_match(
                "community-01", "match-1", NOW - timedelta(minutes=1)
            ).status
            == CrconLogStreamStatus.AVAILABLE
        )
        window = manager.window_for_match(
            "community-01", "match-1", NOW - timedelta(minutes=1)
        )
        manager.stop()

        self.assertIsNone(json.loads(resumed.sent[0])["last_seen_id"])
        self.assertTrue(window.gap_detected)
        self.assertEqual([event.event_id for event in window.events], ["2000-0"])

    def test_disabled_auth_failed_and_unavailable_are_distinct(self) -> None:
        cases = (
            (
                _FakeConnection(
                    [_payload(error="Log stream is not enabled in your config")]
                ),
                CrconLogStreamStatus.DISABLED,
            ),
            (
                WebSocketBadStatusException("denied", 403),
                CrconLogStreamStatus.AUTH_FAILED,
            ),
            (ConnectionError("offline"), CrconLogStreamStatus.UNAVAILABLE),
        )
        for outcome, expected in cases:
            with self.subTest(expected=expected):
                waits: list[float] = []

                def stop_after_one(_stop: Event, delay: float) -> bool:
                    waits.append(delay)
                    return True

                factory = _Factory([outcome])
                manager = CrconLogStreamManager(
                    (_target(),),
                    connection_factory=factory,
                    waiter=stop_after_one,
                )
                manager.start()
                _wait_until(lambda: bool(waits))
                window = manager.window_for_match(
                    "community-01", "match-1", NOW - timedelta(minutes=1)
                )
                manager.stop()
                self.assertEqual(window.status, expected)

    def test_bounded_exponential_backoff_after_transient_disconnects(self) -> None:
        delays: list[float] = []
        outcomes: list[object] = [
            ConnectionError("one"),
            ConnectionError("two"),
            ConnectionError("three"),
        ]

        def waiter(_stop: Event, delay: float) -> bool:
            delays.append(delay)
            return len(delays) == 3

        manager = CrconLogStreamManager(
            (_target(),),
            connection_factory=_Factory(outcomes),
            backoff_seconds=(1.0, 2.0, 4.0, 4.0),
            waiter=waiter,
        )
        manager.start()
        _wait_until(lambda: len(delays) == 3)
        manager.stop()

        self.assertEqual(delays, [1.0, 2.0, 4.0])

    def test_multiple_targets_are_isolated_and_start_is_idempotent(self) -> None:
        one = _FakeConnection([_payload(_log("1000-1"), last_seen_id="1000-1")])
        two = _FakeConnection(
            [
                _payload(
                    _log("2000-1", action="TEAM KILL"),
                    last_seen_id="2000-1",
                )
            ]
        )
        factory = _Factory({"community-01": [one], "community-02": [two]})
        manager = CrconLogStreamManager(
            (_target("community-01"), _target("community-02")),
            connection_factory=factory,
        )
        manager.start()
        manager.start()
        _wait_until(lambda: bool(one.sent) and bool(two.sent))
        first = manager.window_for_match(
            "community-01", "match-1", NOW - timedelta(minutes=1)
        )
        second = manager.window_for_match(
            "community-02", "match-2", NOW - timedelta(minutes=1)
        )
        manager.stop()

        self.assertEqual(len(factory.calls), 2)
        self.assertEqual([event.event_id for event in first.events], ["1000-1"])
        self.assertEqual([event.event_id for event in second.events], ["2000-1"])

    def test_match_transition_filters_previous_match_without_player_count_signal(self) -> None:
        connection = _FakeConnection(
            [
                _payload(
                    _log("1000-1", timestamp=NOW - timedelta(minutes=2)),
                    _log("2000-1", timestamp=NOW + timedelta(seconds=5)),
                    last_seen_id="2000-1",
                )
            ]
        )
        manager = CrconLogStreamManager(
            (_target(),),
            connection_factory=_Factory([connection]),
        )
        manager.start()
        _wait_until(lambda: bool(connection.sent))
        _wait_until(
            lambda: len(
                manager.window_for_match("community-01", "old-match", NOW - timedelta(minutes=3)).events
            )
            == 2
        )
        transitioned = manager.window_for_match(
            "community-01", "new-match", NOW
        )
        manager.stop()

        self.assertEqual([event.event_id for event in transitioned.events], ["2000-1"])
        self.assertFalse(transitioned.gap_detected)

    def test_backend_run_controls_consumer_start_and_clean_shutdown(self) -> None:
        server = MagicMock()
        server.serve_forever.side_effect = RuntimeError("fixture stop")
        with (
            patch.object(backend_main, "create_server", return_value=server),
            patch.object(backend_main, "start_current_match_log_streams") as start,
            patch.object(backend_main, "stop_current_match_log_streams") as stop,
        ):
            with self.assertRaisesRegex(RuntimeError, "fixture stop"):
                backend_main.run()

        start.assert_called_once_with()
        stop.assert_called_once_with()
        server.server_close.assert_called_once_with()


class _FakeApi:
    def get_public_info(self) -> dict[str, object]:
        return {
            "current_map": {
                "map": {
                    "id": "synthetic_layer",
                    "map": "Synthetic Forest Warfare",
                    "game_mode": "Warfare",
                },
                "start": (NOW - timedelta(minutes=10)).isoformat(),
            },
            "score": {"allied": 2, "axis": 1},
            "time_remaining": 2400,
            "player_count": 2,
            "max_player_count": 100,
            "player_count_by_team": {"allied": 1, "axis": 1},
            "name": {"name": "Synthetic Community"},
        }

    def get_live_game_stats(self) -> dict[str, object]:
        return {
            "stats": [
                {
                    "player_id": "EOS-like:opaque-player-alpha",
                    "player": "Alpha",
                    "team": "allied",
                    "kills": 7,
                    "deaths": 3,
                    "teamkills": 1,
                    "deaths_by_teamkill": 0,
                    "weapons": {"Synthetic Rifle": 7},
                },
                {
                    "player_id": "opaque-player-bravo",
                    "player": "Bravo",
                    "team": "axis",
                    "kills": 2,
                    "deaths": 6,
                    "teamkills": 0,
                    "deaths_by_teamkill": 1,
                    "weapons": {},
                },
            ]
        }


class _WindowManager:
    def __init__(self, window: CrconLogStreamWindow) -> None:
        self.window = window

    def window_for_match(self, *_args) -> CrconLogStreamWindow:
        return self.window


def _snapshot_service(window: CrconLogStreamWindow) -> CurrentMatchSnapshotService:
    slug = "comunidad-hispana-01"
    binding = CrconCurrentMatchBinding(
        target=ServerTarget(
            key=slug,
            display_name="Synthetic Community",
            server_number=1,
            game="hll",
            crcon_base_url="https://fixture.invalid",
            capabilities=frozenset({"live_state"}),
        ),
        database_url=None,
        api_headers={},
    )
    return CurrentMatchSnapshotService(
        bindings={slug: binding},
        api_factory=lambda _binding: _FakeApi(),
        cache=TtlCache(max_entries=2, ttl_seconds=2),
        now=lambda: NOW,
        log_stream_manager=_WindowManager(window),  # type: ignore[arg-type]
    )


class CurrentMatchLogStreamIntegrationTests(unittest.TestCase):
    def test_snapshot_mapper_preserves_contract_and_canonical_stream_identity(self) -> None:
        event = CrconCurrentMatchEvent(
            event_id="3000-4",
            timestamp=NOW - timedelta(minutes=1),
            action="KILL",
            killer_id="EOS-like:opaque-player-alpha",
            killer_name="Alpha",
            victim_id="opaque-player-bravo",
            victim_name="Bravo",
            weapon="Synthetic Rifle",
            teamkill=False,
        )
        service = _snapshot_service(
            CrconLogStreamWindow(
                events=(event,),
                status=CrconLogStreamStatus.AVAILABLE,
                gap_detected=False,
                reason=None,
                last_seen_id="3000-4",
                truncated=False,
            )
        )

        snapshot = service.get_snapshot("comunidad-hispana-01")
        payload = snapshot.to_dict()
        kill = payload["kills"][0]
        cursor = kill["cursor"]

        self.assertEqual(decode_stream_kill_cursor(cursor)[1], "3000-4")
        self.assertEqual(kill["killer"]["id"], "EOS-like:opaque-player-alpha")
        self.assertEqual(kill["victim"]["id"], "opaque-player-bravo")
        self.assertEqual(kill["weapon"], "Synthetic Rifle")
        self.assertFalse(kill["teamkill"])
        self.assertEqual(payload["killfeed"]["source"], "crcon-log-stream")
        self.assertTrue(payload["killfeed"]["available"])
        self.assertFalse(snapshot.degraded)

    def test_degraded_killfeed_keeps_crcon_stats_and_never_calls_legacy(self) -> None:
        service = _snapshot_service(
            CrconLogStreamWindow(
                events=(),
                status=CrconLogStreamStatus.DISABLED,
                gap_detected=False,
                reason="crcon-log-stream-disabled",
                last_seen_id=None,
                truncated=False,
            )
        )
        with (
            patch.dict(os.environ, {"HLL_CURRENT_MATCH_SOURCE": "crcon"}, clear=False),
            patch.object(payloads, "get_current_match_snapshot_service", return_value=service),
            patch.object(payloads, "_query_current_match_rcon_sample") as legacy_summary,
            patch.object(payloads, "list_current_match_kill_feed") as legacy_kills,
        ):
            response = payloads.build_current_match_snapshot_payload(
                server_slug="comunidad-hispana-01"
            )

        data = response["data"]
        self.assertEqual(data["kills"], [])
        self.assertEqual(data["players"][0]["kills"], 7)
        self.assertTrue(data["degraded"])
        self.assertIn("crcon-log-stream-disabled", data["degraded_reasons"])
        self.assertEqual(data["killfeed"]["status"], "DISABLED")
        legacy_summary.assert_not_called()
        legacy_kills.assert_not_called()


if __name__ == "__main__":
    unittest.main()
