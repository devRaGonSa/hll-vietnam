from __future__ import annotations

import io
import os
import unittest
from contextlib import nullcontext, redirect_stdout
from datetime import datetime, timezone
from unittest.mock import patch

import app.historical_runner as historical_runner
from app.historical_runner import _maybe_run_database_maintenance, _run_refresh_with_retries


class HistoricalRunnerMaintenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        historical_runner._LAST_DATABASE_MAINTENANCE_RUN_AT = None

    def tearDown(self) -> None:
        historical_runner._LAST_DATABASE_MAINTENANCE_RUN_AT = None

    def test_scheduler_disabled_does_not_call_cleanup(self) -> None:
        with (
            patch.dict(os.environ, {"HLL_DB_MAINTENANCE_ENABLED": "false"}, clear=False),
            patch("app.historical_runner.run_database_maintenance_cleanup") as cleanup,
        ):
            result = _maybe_run_database_maintenance(
                now=datetime(2026, 6, 20, 12, tzinfo=timezone.utc)
            )

        cleanup.assert_not_called()
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "disabled")

    def test_scheduler_enabled_but_not_due_does_not_call_cleanup(self) -> None:
        with (
            patch.dict(
                os.environ,
                {
                    "HLL_DB_MAINTENANCE_ENABLED": "true",
                    "HLL_DB_MAINTENANCE_INTERVAL_SECONDS": "43200",
                },
                clear=False,
            ),
            patch(
                "app.historical_runner.run_database_maintenance_cleanup",
                return_value={"status": "ok"},
            ) as cleanup,
        ):
            first = _maybe_run_database_maintenance(
                now=datetime(2026, 6, 20, 0, tzinfo=timezone.utc)
            )
            second = _maybe_run_database_maintenance(
                now=datetime(2026, 6, 20, 1, tzinfo=timezone.utc)
            )

        self.assertEqual(first["status"], "ok")
        self.assertEqual(second["status"], "skipped")
        self.assertEqual(second["reason"], "not-due")
        cleanup.assert_called_once()

    def test_scheduler_enabled_and_due_calls_cleanup(self) -> None:
        with (
            patch.dict(os.environ, {"HLL_DB_MAINTENANCE_ENABLED": "true"}, clear=False),
            patch(
                "app.historical_runner.run_database_maintenance_cleanup",
                return_value={"status": "ok"},
            ) as cleanup,
        ):
            result = _maybe_run_database_maintenance(
                now=datetime(2026, 6, 20, 12, tzinfo=timezone.utc)
            )

        cleanup.assert_called_once()
        self.assertEqual(result["status"], "ok")

    def test_cleanup_exception_is_logged_and_runner_continues(self) -> None:
        stream = io.StringIO()
        with (
            patch.dict(os.environ, {"HLL_DB_MAINTENANCE_ENABLED": "true"}, clear=False),
            patch("app.historical_runner.backend_writer_lock", return_value=nullcontext()),
            patch(
                "app.historical_runner._run_primary_rcon_capture",
                return_value={"status": "ok", "targets": []},
            ),
            patch(
                "app.historical_runner.run_incremental_refresh",
                return_value={"status": "ok"},
            ),
            patch(
                "app.historical_runner.generate_historical_snapshots",
                return_value={"status": "ok"},
            ),
            patch(
                "app.historical_runner.rebuild_elo_mmr_models",
                return_value={"status": "ok"},
            ),
            patch(
                "app.historical_runner.run_database_maintenance_cleanup",
                side_effect=RuntimeError("maintenance failed"),
            ),
            redirect_stdout(stream),
        ):
            result = _run_refresh_with_retries(
                max_retries=0,
                retry_delay_seconds=0,
                server_slug="comunidad-hispana-01",
                max_pages=None,
                page_size=None,
                run_number=1,
            )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["database_maintenance_result"]["status"], "error")
        self.assertIn("database-maintenance-scheduler-failed", stream.getvalue())

    def test_interval_parsing_handles_invalid_values_safely(self) -> None:
        with patch.dict(
            os.environ,
            {
                "HLL_DB_MAINTENANCE_ENABLED": "true",
                "HLL_DB_MAINTENANCE_INTERVAL_SECONDS": "bad",
            },
            clear=False,
        ):
            interval_seconds, source = historical_runner._resolve_db_maintenance_interval_seconds()

        self.assertEqual(interval_seconds, 43200)
        self.assertEqual(source, "default-invalid-env-fallback")

    def test_maintenance_state_is_tracked_in_process(self) -> None:
        with (
            patch.dict(
                os.environ,
                {
                    "HLL_DB_MAINTENANCE_ENABLED": "true",
                    "HLL_DB_MAINTENANCE_INTERVAL_SECONDS": "3600",
                },
                clear=False,
            ),
            patch(
                "app.historical_runner.run_database_maintenance_cleanup",
                return_value={"status": "ok"},
            ),
        ):
            _maybe_run_database_maintenance(now=datetime(2026, 6, 20, 12, tzinfo=timezone.utc))
            self.assertEqual(
                historical_runner._LAST_DATABASE_MAINTENANCE_RUN_AT,
                datetime(2026, 6, 20, 12, tzinfo=timezone.utc),
            )


if __name__ == "__main__":
    unittest.main()
