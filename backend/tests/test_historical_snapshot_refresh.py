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

    def test_runner_continues_when_legacy_snapshot_refresh_fails(self) -> None:
        with (
            patch("app.historical_runner.backend_writer_lock", return_value=nullcontext()),
            patch("app.historical_runner._run_primary_rcon_capture", return_value={"status": "ok", "targets": []}),
            patch(
                "app.historical_runner._resolve_classic_fallback_policy",
                return_value=(False, "validation-rcon-primary-cycle"),
            ),
            patch("app.historical_runner._rcon_capture_has_new_useful_data", return_value=True),
            patch(
                "app.historical_runner.generate_historical_snapshots",
                side_effect=RuntimeError("legacy snapshot failure"),
            ),
            patch(
                "app.historical_runner._build_elo_mmr_rebuild_policy",
                return_value={
                    "due": False,
                    "policy": "validation-policy",
                    "last_generated_at": None,
                    "samples_since_last_rebuild": 1,
                    "minutes_since_last_rebuild": None,
                    "rebuild_interval_minutes": 60,
                    "min_new_samples": 10,
                },
            ),
            patch("app.historical_runner.refresh_player_search_index", return_value={"status": "ok"}) as search_refresh,
            patch("app.historical_runner.refresh_player_period_stats", return_value={"status": "ok"}) as period_refresh,
            patch("app.historical_runner.refresh_ranking_snapshots", return_value={"status": "ok"}) as ranking_refresh,
            patch(
                "app.historical_runner._maybe_run_database_maintenance",
                return_value={"status": "skipped", "reason": "disabled"},
            ),
        ):
            result = _run_refresh_with_retries(
                max_retries=0,
                retry_delay_seconds=0,
                server_slug=None,
                max_pages=None,
                page_size=None,
                run_number=1,
            )

        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["historical_snapshot_result"]["status"], "error")
        self.assertEqual(result["snapshot_result"]["status"], "error")
        self.assertEqual(
            result["historical_snapshot_result"]["error"],
            "legacy snapshot failure",
        )
        search_refresh.assert_called_once()
        period_refresh.assert_called_once()
        ranking_refresh.assert_called_once()

    def test_runner_returns_ok_when_legacy_snapshot_and_read_models_succeed(self) -> None:
        with (
            patch("app.historical_runner.backend_writer_lock", return_value=nullcontext()),
            patch("app.historical_runner._run_primary_rcon_capture", return_value={"status": "ok", "targets": []}),
            patch(
                "app.historical_runner._resolve_classic_fallback_policy",
                return_value=(False, "validation-rcon-primary-cycle"),
            ),
            patch("app.historical_runner._rcon_capture_has_new_useful_data", return_value=True),
            patch(
                "app.historical_runner.generate_historical_snapshots",
                return_value={"status": "ok", "generated_at": "2026-06-09T08:00:00Z"},
            ),
            patch(
                "app.historical_runner._build_elo_mmr_rebuild_policy",
                return_value={
                    "due": False,
                    "policy": "validation-policy",
                    "last_generated_at": None,
                    "samples_since_last_rebuild": 1,
                    "minutes_since_last_rebuild": None,
                    "rebuild_interval_minutes": 60,
                    "min_new_samples": 10,
                },
            ),
            patch("app.historical_runner.refresh_player_search_index", return_value={"status": "ok"}),
            patch("app.historical_runner.refresh_player_period_stats", return_value={"status": "ok"}),
            patch("app.historical_runner.refresh_ranking_snapshots", return_value={"status": "ok"}),
            patch(
                "app.historical_runner._maybe_run_database_maintenance",
                return_value={"status": "skipped", "reason": "disabled"},
            ),
        ):
            result = _run_refresh_with_retries(
                max_retries=0,
                retry_delay_seconds=0,
                server_slug=None,
                max_pages=None,
                page_size=None,
                run_number=1,
            )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["historical_snapshot_result"]["status"], "ok")
        self.assertIn("player_search_index_result", result)
        self.assertIn("player_period_stats_result", result)
        self.assertIn("ranking_snapshot_result", result)


if __name__ == "__main__":
    unittest.main()
