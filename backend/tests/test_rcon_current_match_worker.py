from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from contextlib import closing, contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app import postgres_rcon_storage
from app import rcon_admin_log_storage
from app.config import (
    get_current_match_adminlog_enabled,
    get_current_match_adminlog_interval_seconds,
    get_current_match_adminlog_lookback_seconds,
)
from app.rcon_current_match_worker import (
    list_current_match_trusted_targets,
    run_current_match_adminlog_refresh_loop,
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

        def fake_persist(*, target, entries, db_path=None, ensure_storage=True):
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
        self.assertEqual(persist_calls[0]["db_path"], None)
        self.assertEqual(result["totals"]["events_inserted"], 1)
        self.assertEqual(result["status"], "ok")

    def test_once_unlocked_initializes_storage_once_and_persists_without_repeated_ddl(self) -> None:
        persist_calls: list[dict[str, object]] = []

        def fake_fetch(target, *, lookback_seconds, timeout_seconds):
            return [{"timestamp": "2026-06-18T18:00:00Z", "message": "[1 (1)] Killer(Allies) -> Victim(Axis) with Rifle"}]

        def fake_persist(*, target, entries, db_path=None, ensure_storage=True):
            persist_calls.append(
                {
                    "target": target,
                    "entries": entries,
                    "db_path": db_path,
                    "ensure_storage": ensure_storage,
                }
            )
            return {
                "events_seen": len(entries),
                "events_inserted": len(entries),
                "duplicate_events": 0,
            }

        with patch("app.rcon_current_match_worker.initialize_rcon_admin_log_storage") as initialize:
            result = run_current_match_adminlog_refresh_once_unlocked(
                lookback_seconds=180,
                targets=[TARGET_01],
                fetch_entries_fn=fake_fetch,
                persist_entries_fn=fake_persist,
            )

        initialize.assert_called_once_with(db_path=None)
        self.assertEqual(persist_calls[0]["ensure_storage"], False)
        self.assertEqual(result["status"], "ok")

    def test_failing_target_does_not_block_other_target(self) -> None:
        def fake_fetch(target, *, lookback_seconds, timeout_seconds):
            if target.external_server_id == "comunidad-hispana-01":
                raise RuntimeError("boom")
            return [{"timestamp": "2026-06-18T18:00:00Z", "message": "[1 (1)] Killer(Allies) -> Victim(Axis) with Rifle"}]

        def fake_persist(*, target, entries, db_path=None, ensure_storage=True):
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

    def test_live_worker_starts_when_duplicate_historical_runs_exist(self) -> None:
        entry = {
            "timestamp": "2026-06-18T18:00:00Z",
            "message": (
                "[5:00 min (321)] KILL: Alpha(Allies/steam-alpha) -> "
                "Victim(Axis/steam-victim) with Rifle"
            ),
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "current_match.sqlite3")
            rcon_admin_log_storage.initialize_rcon_admin_log_storage(db_path=Path(db_path))
            with closing(sqlite3.connect(db_path)) as connection:
                connection.execute(
                    """
                    INSERT INTO rcon_historical_capture_runs (
                        mode, status, target_scope, started_at
                    ) VALUES (?, ?, ?, ?)
                    """,
                    ("historical", "running", "all-configured-rcon-targets", "2099-01-01T00:00:00Z"),
                )
                connection.execute(
                    """
                    INSERT INTO rcon_historical_capture_runs (
                        mode, status, target_scope, started_at
                    ) VALUES (?, ?, ?, ?)
                    """,
                    ("historical", "running", "all-configured-rcon-targets", "2099-01-01T00:05:00Z"),
                )
                connection.commit()

            result = run_current_match_adminlog_refresh_once_unlocked(
                lookback_seconds=180,
                targets=[TARGET_01],
                fetch_entries_fn=lambda *_args, **_kwargs: [entry],
                db_path=db_path,
            )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["totals"]["events_inserted"], 1)
        self.assertEqual(result["totals"]["failed_targets"], 0)

    def test_live_worker_does_not_trigger_admin_log_materialization(self) -> None:
        def fake_fetch(target, *, lookback_seconds, timeout_seconds):
            return [
                {
                    "timestamp": "2026-06-18T18:00:00Z",
                    "message": "[1:00 min (60)] CONNECTED Alpha (steam-alpha)",
                }
            ]

        with (
            tempfile.TemporaryDirectory() as temp_dir,
            patch("app.rcon_admin_log_materialization.materialize_rcon_admin_log") as materialize,
        ):
            db_path = os.path.join(temp_dir, "current_match.sqlite3")
            result = run_current_match_adminlog_refresh_once_unlocked(
                lookback_seconds=180,
                targets=[TARGET_01],
                fetch_entries_fn=fake_fetch,
                db_path=db_path,
            )

        materialize.assert_not_called()
        self.assertEqual(result["status"], "ok")

    def test_live_worker_does_not_use_historical_runtime_guard(self) -> None:
        def fake_fetch(target, *, lookback_seconds, timeout_seconds):
            return [
                {
                    "timestamp": "2026-06-18T18:00:00Z",
                    "message": "[1:00 min (60)] CONNECTED Alpha (steam-alpha)",
                }
            ]

        def fake_persist(*, target, entries, db_path=None, ensure_storage=True):
            return {
                "events_seen": len(entries),
                "events_inserted": len(entries),
                "duplicate_events": 0,
            }

        with (
            patch("app.rcon_current_match_worker.initialize_rcon_admin_log_storage"),
            patch("app.rcon_historical_storage.historical_capture_runtime_guard") as guard,
        ):
            result = run_current_match_adminlog_refresh_once_unlocked(
                lookback_seconds=180,
                targets=[TARGET_01],
                fetch_entries_fn=fake_fetch,
                persist_entries_fn=fake_persist,
            )

        guard.assert_not_called()
        self.assertEqual(result["status"], "ok")

    def test_loop_honors_max_runs(self) -> None:
        results = [{"status": "ok"}, {"status": "ok"}]

        with (
            patch("app.rcon_current_match_worker.initialize_rcon_admin_log_storage") as initialize,
            patch(
                "app.rcon_current_match_worker.run_current_match_adminlog_refresh_once",
                side_effect=results,
            ) as run_once,
            patch("app.rcon_current_match_worker.time.sleep") as sleep,
        ):
            run_current_match_adminlog_refresh_loop(
                interval_seconds=5,
                lookback_seconds=900,
                max_runs=2,
            )

        initialize.assert_called_once_with()
        self.assertEqual(run_once.call_count, 2)
        self.assertEqual(sleep.call_count, 1)

    def test_postgres_admin_log_storage_uses_admin_log_bootstrap_only(self) -> None:
        with (
            patch.object(rcon_admin_log_storage, "use_postgres_rcon_storage", return_value=True),
            patch("app.postgres_rcon_storage.initialize_postgres_admin_log_storage") as admin_log_init,
            patch("app.postgres_rcon_storage.initialize_postgres_rcon_storage") as full_init,
        ):
            rcon_admin_log_storage.initialize_rcon_admin_log_storage()

        admin_log_init.assert_called_once_with()
        full_init.assert_not_called()

    def test_postgres_schema_strings_no_longer_create_historical_running_unique_index(self) -> None:
        self.assertNotIn(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_rcon_historical_single_running_historical",
            postgres_rcon_storage.RCON_SCHEMA_SQL,
        )
        self.assertNotIn(
            "idx_rcon_historical_single_running_historical",
            postgres_rcon_storage.POSTGRES_ADMIN_LOG_SCHEMA_SQL,
        )
        self.assertIn(
            "DROP INDEX IF EXISTS idx_rcon_historical_single_running_historical",
            postgres_rcon_storage.DROP_LEGACY_HISTORICAL_GUARD_INDEX_SQL,
        )

    def test_initialize_postgres_rcon_storage_does_not_execute_removed_unique_index(self) -> None:
        executed_sql: list[str] = []

        with patch.object(
            postgres_rcon_storage,
            "connect_postgres",
            return_value=_FakePostgresConnectionScope(executed_sql),
        ):
            postgres_rcon_storage.initialize_postgres_rcon_storage()

        executed_text = "\n".join(executed_sql)
        self.assertIn(
            "DROP INDEX IF EXISTS idx_rcon_historical_single_running_historical",
            executed_text,
        )
        self.assertNotIn(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_rcon_historical_single_running_historical",
            executed_text,
        )

    def test_compose_nas_runs_split_live_worker_and_safe_historical_interval(self) -> None:
        compose_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "..",
            "deploy",
            "portainer",
            "docker-compose.nas.yml",
        )
        with open(compose_path, encoding="utf-8") as handle:
            compose_text = handle.read()

        self.assertIn("rcon-live-adminlog-worker:", compose_text)
        self.assertIn("app.rcon_current_match_worker", compose_text)
        self.assertIn('--lookback-minutes\n      - "15"', compose_text)
        self.assertIn('HLL_RCON_HISTORICAL_CAPTURE_INTERVAL_SECONDS: ${HLL_RCON_HISTORICAL_CAPTURE_INTERVAL_SECONDS:-900}', compose_text)
        self.assertNotIn('HLL_RCON_HISTORICAL_CAPTURE_INTERVAL_SECONDS: ${HLL_RCON_HISTORICAL_CAPTURE_INTERVAL_SECONDS:-2}', compose_text)

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


class _FakePostgresConnectionScope:
    def __init__(self, executed_sql: list[str]) -> None:
        self.connection = _FakePostgresConnection(executed_sql)

    def __enter__(self):
        return self.connection

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None


class _FakePostgresConnection:
    def __init__(self, executed_sql: list[str]) -> None:
        self.executed_sql = executed_sql

    @contextmanager
    def cursor(self):
        yield _FakePostgresCursor(self.executed_sql)


class _FakePostgresCursor:
    def __init__(self, executed_sql: list[str]) -> None:
        self.executed_sql = executed_sql

    def execute(self, sql: str) -> None:
        self.executed_sql.append(sql)
