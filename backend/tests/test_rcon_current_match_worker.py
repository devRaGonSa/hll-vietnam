from __future__ import annotations

import os
import tempfile
import unittest
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

from app.config import (
    get_current_match_adminlog_enabled,
    get_current_match_adminlog_interval_seconds,
    get_current_match_adminlog_lookback_seconds,
)
from app.rcon_current_match_worker import (
    list_current_match_trusted_targets,
    run_current_match_adminlog_refresh_once_unlocked,
)


TARGET_01 = SimpleNamespace(
    external_server_id="comunidad-hispana-01",
    name="Comunidad Hispana #01",
    host="203.0.113.10",
    port=7779,
    password="secret-01",
    region="ES",
    game_port=None,
    query_port=None,
    source_name="community-hispana-rcon",
)

TARGET_02 = SimpleNamespace(
    external_server_id="comunidad-hispana-02",
    name="Comunidad Hispana #02",
    host="203.0.113.11",
    port=7879,
    password="secret-02",
    region="ES",
    game_port=None,
    query_port=None,
    source_name="community-hispana-rcon",
)

TARGET_03 = SimpleNamespace(
    external_server_id="comunidad-hispana-03",
    name="Comunidad Hispana #03",
    host="203.0.113.12",
    port=7979,
    password="secret-03",
    region="ES",
    game_port=None,
    query_port=None,
    source_name="community-hispana-rcon",
)


class RconCurrentMatchWorkerTests(unittest.TestCase):
    def test_list_current_match_trusted_targets_filters_only_01_and_02(self) -> None:
        with patch(
            "app.rcon_current_match_worker.load_rcon_targets",
            return_value=(TARGET_01, TARGET_02, TARGET_03),
        ):
            selected = list_current_match_trusted_targets()

        self.assertEqual(
            [target.external_server_id for target in selected],
            ["comunidad-hispana-01", "comunidad-hispana-02"],
        )

    def test_once_unlocked_calls_existing_persistence_path(self) -> None:
        fetch_calls: list[object] = []
        persist_calls: list[dict[str, object]] = []

        def fake_fetch(target, *, lookback_seconds, timeout_seconds):
            fetch_calls.append((target.external_server_id, lookback_seconds, timeout_seconds))
            return [{"timestamp": "2026-06-18T18:00:00Z", "message": "[1 (1)] Killer(Allies) -> Victim(Axis) with Rifle"}]

        def fake_persist(*, target, entries, db_path=None):
            persist_calls.append({"target": target, "entries": entries, "db_path": db_path})
            return {
                "events_seen": len(entries),
                "events_inserted": len(entries),
                "duplicate_events": 0,
            }

        result = run_current_match_adminlog_refresh_once_unlocked(
            lookback_seconds=180,
            targets=[TARGET_01],
            fetch_entries_fn=fake_fetch,
            persist_entries_fn=fake_persist,
        )

        self.assertEqual(fetch_calls, [("comunidad-hispana-01", 180, None)])
        self.assertEqual(len(persist_calls), 1)
        self.assertEqual(persist_calls[0]["target"]["target_key"], "comunidad-hispana-01")
        self.assertEqual(result["totals"]["events_inserted"], 1)
        self.assertEqual(result["status"], "ok")

    def test_failing_target_does_not_block_other_target(self) -> None:
        def fake_fetch(target, *, lookback_seconds, timeout_seconds):
            if target.external_server_id == "comunidad-hispana-01":
                raise RuntimeError("boom")
            return [{"timestamp": "2026-06-18T18:00:00Z", "message": "[1 (1)] Killer(Allies) -> Victim(Axis) with Rifle"}]

        def fake_persist(*, target, entries, db_path=None):
            return {
                "events_seen": len(entries),
                "events_inserted": len(entries),
                "duplicate_events": 0,
            }

        result = run_current_match_adminlog_refresh_once_unlocked(
            lookback_seconds=180,
            targets=[TARGET_01, TARGET_02],
            fetch_entries_fn=fake_fetch,
            persist_entries_fn=fake_persist,
        )

        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["totals"]["failed_targets"], 1)
        self.assertEqual(result["totals"]["events_inserted"], 1)
        self.assertEqual(len(result["targets"]), 1)
        self.assertEqual(result["targets"][0]["target_key"], "comunidad-hispana-02")

    def test_overlapping_windows_remain_idempotent_via_existing_persistence(self) -> None:
        entry = {
            "timestamp": "2026-06-18T18:00:00Z",
            "message": (
                "[5:00 min (321)] KILL: Alpha(Allies/76561198000000001) -> "
                "Bravo(Axis/76561198000000002) with M1 GARAND"
            ),
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "current_match.sqlite3")

            def fake_fetch(target, *, lookback_seconds, timeout_seconds):
                return [entry]

            first = run_current_match_adminlog_refresh_once_unlocked(
                lookback_seconds=180,
                targets=[TARGET_01],
                fetch_entries_fn=fake_fetch,
                db_path=db_path,
            )
            second = run_current_match_adminlog_refresh_once_unlocked(
                lookback_seconds=180,
                targets=[TARGET_01],
                fetch_entries_fn=fake_fetch,
                db_path=db_path,
            )

        self.assertEqual(first["totals"]["events_inserted"], 1)
        self.assertEqual(first["totals"]["duplicate_events"], 0)
        self.assertEqual(second["totals"]["events_inserted"], 0)
        self.assertEqual(second["totals"]["duplicate_events"], 1)

    def test_current_match_adminlog_config_defaults_and_overrides(self) -> None:
        with _temporary_env(
            CURRENT_MATCH_ADMINLOG_INTERVAL_SECONDS=None,
            CURRENT_MATCH_ADMINLOG_LOOKBACK_SECONDS=None,
            CURRENT_MATCH_ADMINLOG_ENABLED=None,
        ):
            self.assertEqual(get_current_match_adminlog_interval_seconds(), 10)
            self.assertEqual(get_current_match_adminlog_lookback_seconds(), 180)
            self.assertIs(get_current_match_adminlog_enabled(), False)

        with _temporary_env(
            CURRENT_MATCH_ADMINLOG_INTERVAL_SECONDS="15",
            CURRENT_MATCH_ADMINLOG_LOOKBACK_SECONDS="120",
            CURRENT_MATCH_ADMINLOG_ENABLED="true",
        ):
            self.assertEqual(get_current_match_adminlog_interval_seconds(), 15)
            self.assertEqual(get_current_match_adminlog_lookback_seconds(), 120)
            self.assertIs(get_current_match_adminlog_enabled(), True)


@contextmanager
def _temporary_env(**values: str | None):
    previous = {name: os.environ.get(name) for name in values}
    try:
        for name, value in values.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
