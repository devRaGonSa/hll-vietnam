"""Regression coverage for historical snapshot runner refreshes."""

from __future__ import annotations

import io
import json
import os
import unittest
from contextlib import nullcontext, redirect_stdout
from datetime import datetime, timezone
from unittest.mock import patch

from app.config import (
    get_historical_refresh_interval_seconds,
    get_historical_refresh_max_retries,
    get_historical_refresh_retry_delay_seconds,
)
from app.historical_runner import _run_refresh_with_retries, run_periodic_historical_refresh
from app.historical_snapshots import _normalize_snapshot_limit
from app.postgres_display_storage import _json_payload_default
from app.rcon_historical_read_model import (
    _calculate_coverage_hours,
    _calculate_duration_seconds,
)


class HistoricalSnapshotRefreshTests(unittest.TestCase):
    def test_runner_numeric_env_values_are_parsed_before_use(self) -> None:
        with patch.dict(
            os.environ,
            {
                "HLL_HISTORICAL_SNAPSHOT_REFRESH_INTERVAL_SECONDS": "300",
                "HLL_HISTORICAL_REFRESH_MAX_RETRIES": "4",
                "HLL_HISTORICAL_REFRESH_RETRY_DELAY_SECONDS": "0.5",
            },
            clear=False,
        ):
            self.assertEqual(get_historical_refresh_interval_seconds(), 300)
            self.assertEqual(get_historical_refresh_max_retries(), 4)
            self.assertEqual(get_historical_refresh_retry_delay_seconds(), 0.5)

    def test_runner_numeric_env_values_fail_with_clear_names(self) -> None:
        with patch.dict(
            os.environ,
            {"HLL_HISTORICAL_SNAPSHOT_REFRESH_INTERVAL_SECONDS": "hourly"},
            clear=False,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "HLL_HISTORICAL_SNAPSHOT_REFRESH_INTERVAL_SECONDS must be an integer",
            ):
                get_historical_refresh_interval_seconds()

    def test_rcon_coverage_accepts_postgres_datetime_values(self) -> None:
        start = datetime(2026, 5, 21, 10, 0, tzinfo=timezone.utc)
        end = datetime(2026, 5, 21, 11, 30, tzinfo=timezone.utc)

        self.assertEqual(_calculate_coverage_hours(start, end), 1.5)
        self.assertEqual(_calculate_duration_seconds(start, end), 5400)

    def test_snapshot_limits_are_numeric_before_snapshot_queries(self) -> None:
        self.assertEqual(_normalize_snapshot_limit("recent_matches_limit", "10"), 10)
        with self.assertRaisesRegex(ValueError, "recent_matches_limit"):
            _normalize_snapshot_limit("recent_matches_limit", "ten")

    def test_postgres_snapshot_payload_serializes_datetime_values(self) -> None:
        payload = {
            "captured_at": datetime(2026, 5, 21, 20, 12, 54, tzinfo=timezone.utc),
        }

        self.assertEqual(
            json.loads(json.dumps(payload, default=_json_payload_default)),
            {"captured_at": "2026-05-21T20:12:54Z"},
        )

    def test_runner_failure_log_includes_exception_type_and_traceback(self) -> None:
        stream = io.StringIO()
        with (
            patch("app.historical_runner.backend_writer_lock", return_value=nullcontext()),
            patch(
                "app.historical_runner._run_primary_rcon_capture",
                side_effect=TypeError("bad timestamp"),
            ),
            redirect_stdout(stream),
        ):
            result = _run_refresh_with_retries(
                max_retries=0,
                retry_delay_seconds=0,
                server_slug=None,
                max_pages=None,
                page_size=None,
                run_number=1,
            )

        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_type"], "TypeError")
        self.assertIn("Traceback", result["traceback"])
        self.assertIn('"event": "historical-refresh-attempt-failed"', stream.getvalue())

    def test_runner_success_log_serializes_datetime_values(self) -> None:
        stream = io.StringIO()
        with (
            patch(
                "app.historical_runner._run_refresh_with_retries",
                return_value={
                    "status": "ok",
                    "rcon_capture_result": {
                        "captured_at": datetime(2026, 5, 22, tzinfo=timezone.utc),
                    },
                },
            ),
            redirect_stdout(stream),
        ):
            run_periodic_historical_refresh(
                interval_seconds=1,
                max_retries=0,
                retry_delay_seconds=0,
                max_runs=1,
            )

        self.assertIn('"status": "ok"', stream.getvalue())
        self.assertIn('"captured_at": "2026-05-22 00:00:00+00:00"', stream.getvalue())


if __name__ == "__main__":
    unittest.main()
