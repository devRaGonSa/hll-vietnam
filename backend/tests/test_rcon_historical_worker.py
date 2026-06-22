from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from contextlib import closing, contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from app import rcon_historical_storage
from app.rcon_historical_worker import (
    CAPTURE_MODE_CURRENT_LIVE,
    CAPTURE_MODE_HISTORICAL,
    build_arg_parser,
    main,
    run_rcon_historical_capture,
    run_rcon_historical_capture_unlocked,
)


TARGET = SimpleNamespace(
    external_server_id="comunidad-hispana-01",
    name="Comunidad Hispana #01",
    host="203.0.113.10",
    port=7779,
    region="ES",
    game_port=7777,
    query_port=7778,
    source_name="community-hispana-rcon",
)


class RconHistoricalWorkerTests(unittest.TestCase):
    def test_current_live_capture_skips_materialization(self) -> None:
        with (
            patch("app.rcon_historical_worker.initialize_rcon_historical_storage"),
            patch("app.rcon_historical_worker._select_targets", return_value=[TARGET]),
            patch(
                "app.rcon_historical_worker.query_live_server_sample",
                return_value={"normalized": {"players": 10}, "raw_session": {"raw": True}},
            ),
            patch(
                "app.rcon_historical_worker.persist_rcon_historical_sample",
                return_value={"samples_inserted": 1, "duplicate_samples": 0},
            ),
            patch(
                "app.rcon_historical_worker._ingest_target_admin_log",
                return_value={
                    "status": "ok",
                    "errors": [],
                    "totals": {
                        "events_seen": 4,
                        "events_inserted": 2,
                        "duplicate_events": 2,
                        "failed_targets": 0,
                    },
                },
            ),
            patch("app.rcon_historical_worker.start_rcon_historical_capture_run", return_value=101),
            patch("app.rcon_historical_worker.finalize_rcon_historical_capture_run"),
            patch(
                "app.rcon_historical_worker.list_rcon_historical_target_statuses",
                return_value=[{"target_key": "comunidad-hispana-01"}],
            ),
            patch("app.rcon_historical_worker.materialize_rcon_admin_log") as materialize,
        ):
            payload = run_rcon_historical_capture_unlocked(capture_mode=CAPTURE_MODE_CURRENT_LIVE)

        materialize.assert_not_called()
        self.assertEqual(payload["capture_mode"], CAPTURE_MODE_CURRENT_LIVE)
        self.assertIs(payload["materialization_skipped"], True)
        self.assertEqual(payload["admin_log_events_seen"], 4)
        self.assertEqual(payload["admin_log_events_inserted"], 2)
        self.assertEqual(payload["duplicate_events"], 2)
        self.assertEqual(payload["samples_inserted"], 1)
        self.assertEqual(payload["materialization_result"]["status"], "skipped")

    def test_historical_capture_keeps_materialization(self) -> None:
        with (
            patch("app.rcon_historical_worker.initialize_rcon_historical_storage"),
            patch("app.rcon_historical_worker._select_targets", return_value=[TARGET]),
            patch(
                "app.rcon_historical_worker.query_live_server_sample",
                return_value={"normalized": {"players": 10}, "raw_session": {"raw": True}},
            ),
            patch(
                "app.rcon_historical_worker.persist_rcon_historical_sample",
                return_value={"samples_inserted": 1, "duplicate_samples": 0},
            ),
            patch(
                "app.rcon_historical_worker._ingest_target_admin_log",
                return_value={
                    "status": "ok",
                    "errors": [],
                    "totals": {
                        "events_seen": 1,
                        "events_inserted": 1,
                        "duplicate_events": 0,
                        "failed_targets": 0,
                    },
                },
            ),
            patch("app.rcon_historical_worker.start_rcon_historical_capture_run", return_value=102),
            patch("app.rcon_historical_worker.finalize_rcon_historical_capture_run"),
            patch(
                "app.rcon_historical_worker.list_rcon_historical_target_statuses",
                return_value=[{"target_key": "comunidad-hispana-01"}],
            ),
            patch(
                "app.rcon_historical_worker.materialize_rcon_admin_log",
                return_value={"matches_materialized": 3, "matches_updated": 2},
            ) as materialize,
        ):
            payload = run_rcon_historical_capture_unlocked(capture_mode=CAPTURE_MODE_HISTORICAL)

        materialize.assert_called_once_with()
        self.assertEqual(payload["capture_mode"], CAPTURE_MODE_HISTORICAL)
        self.assertIs(payload["materialization_skipped"], False)
        self.assertEqual(payload["totals"]["materialized_matches_inserted"], 3)
        self.assertEqual(payload["totals"]["materialized_matches_updated"], 2)

    def test_cli_and_env_can_activate_current_live_mode(self) -> None:
        with _temporary_env(
            HLL_RCON_CURRENT_MATCH_MODE="true",
            HLL_RCON_CURRENT_MATCH_CAPTURE_INTERVAL_SECONDS="5",
        ):
            args = build_arg_parser().parse_args(["loop"])
            with patch("app.rcon_historical_worker.run_periodic_rcon_historical_capture") as runner:
                exit_code = main(["loop"])

        self.assertEqual(args.capture_mode, CAPTURE_MODE_CURRENT_LIVE)
        self.assertEqual(exit_code, 0)
        runner.assert_called_once()
        self.assertEqual(runner.call_args.kwargs["capture_mode"], CAPTURE_MODE_CURRENT_LIVE)
        self.assertEqual(runner.call_args.kwargs["interval_seconds"], 5)

        explicit = build_arg_parser().parse_args(["capture", "--skip-materialization"])
        self.assertIs(explicit.skip_materialization, True)

    def test_current_live_capture_uses_short_lock_timeout(self) -> None:
        seen: dict[str, object] = {}

        @contextmanager
        def fake_lock(**kwargs):
            seen.update(kwargs)
            yield {"holder": kwargs["holder"]}

        with (
            _temporary_env(HLL_RCON_CURRENT_MATCH_WRITER_LOCK_TIMEOUT_SECONDS="3.5"),
            patch("app.rcon_historical_worker.backend_writer_lock", side_effect=fake_lock),
            patch(
                "app.rcon_historical_worker.run_rcon_historical_capture_unlocked",
                return_value={"status": "ok"},
            ),
        ):
            run_rcon_historical_capture(capture_mode=CAPTURE_MODE_CURRENT_LIVE)

        self.assertEqual(seen["timeout_seconds"], 3.5)

    def test_historical_capture_skips_when_previous_heavy_run_is_still_running(self) -> None:
        with (
            patch(
                "app.rcon_historical_worker.historical_capture_runtime_guard",
                side_effect=_yield_guard(False),
            ),
            patch("app.rcon_historical_worker.start_rcon_historical_capture_run") as start_run,
        ):
            payload = run_rcon_historical_capture_unlocked(capture_mode=CAPTURE_MODE_HISTORICAL)

        start_run.assert_not_called()
        self.assertEqual(payload["status"], "skipped")
        self.assertEqual(payload["run_status"], "skipped")
        self.assertEqual(payload["materialization_result"]["reason"], "already-running")

    def test_historical_storage_can_start_with_duplicate_stale_running_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "historical.sqlite3"
            rcon_historical_storage.initialize_rcon_historical_storage(db_path=db_path)

            with closing(sqlite3.connect(db_path)) as connection:
                connection.execute(
                    """
                    INSERT INTO rcon_historical_capture_runs (
                        mode, status, target_scope, started_at
                    ) VALUES (?, ?, ?, ?)
                    """,
                    ("historical", "running", "all-configured-rcon-targets", "2026-01-01T00:00:00Z"),
                )
                connection.execute(
                    """
                    INSERT INTO rcon_historical_capture_runs (
                        mode, status, target_scope, started_at
                    ) VALUES (?, ?, ?, ?)
                    """,
                    ("historical", "running", "all-configured-rcon-targets", "2026-01-01T00:05:00Z"),
                )
                connection.commit()

            run_id = rcon_historical_storage.start_rcon_historical_capture_run(
                mode="historical",
                target_scope="all-configured-rcon-targets",
                db_path=db_path,
            )

            self.assertGreater(run_id, 0)
            with closing(sqlite3.connect(db_path)) as connection:
                rows = connection.execute(
                    """
                    SELECT status
                    FROM rcon_historical_capture_runs
                    WHERE mode = 'historical'
                    ORDER BY id ASC
                    """
                ).fetchall()
            self.assertEqual([row[0] for row in rows[:2]], ["stale", "stale"])
            self.assertEqual(rows[-1][0], "running")

    def test_historical_runtime_guard_releases_non_stale_conflict_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "historical.sqlite3"
            rcon_historical_storage.initialize_rcon_historical_storage(db_path=db_path)
            with closing(sqlite3.connect(db_path)) as connection:
                connection.execute(
                    """
                    INSERT INTO rcon_historical_capture_runs (
                        mode, status, target_scope, started_at
                    ) VALUES (?, ?, ?, ?)
                    """,
                    ("historical", "running", "all-configured-rcon-targets", "2099-01-01T00:00:00Z"),
                )
                connection.commit()

            with rcon_historical_storage.historical_capture_runtime_guard(
                capture_mode="historical",
                db_path=db_path,
            ) as acquired:
                self.assertIs(acquired, False)

    def test_postgres_historical_runtime_guard_uses_advisory_lock(self) -> None:
        with (
            patch.object(rcon_historical_storage, "use_postgres_rcon_storage", return_value=True),
            patch(
                "app.postgres_rcon_storage.postgres_historical_capture_advisory_guard",
                side_effect=_yield_guard(False),
            ) as advisory_guard,
        ):
            with rcon_historical_storage.historical_capture_runtime_guard(
                capture_mode="historical",
            ) as acquired:
                self.assertIs(acquired, False)

        advisory_guard.assert_called_once_with()


@contextmanager
def _temporary_env(**values: str):
    previous = {name: os.environ.get(name) for name in values}
    try:
        for name, value in values.items():
            os.environ[name] = value
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def _yield_guard(value: bool):
    @contextmanager
    def _guard(*_args, **_kwargs):
        yield value

    return _guard
