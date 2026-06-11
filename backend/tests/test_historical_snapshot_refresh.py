"""Regression coverage for historical snapshot runner refreshes."""

from __future__ import annotations

import io
import json
import os
import sqlite3
import unittest
from contextlib import nullcontext, redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import app.historical_runner as historical_runner_module
from app.config import (
    get_historical_refresh_interval_seconds,
    get_historical_refresh_max_retries,
    get_historical_refresh_retry_delay_seconds,
    get_public_full_refresh_enabled,
    get_public_full_refresh_time,
    get_public_full_refresh_timezone,
    get_public_historical_monthly_refresh_hour_interval,
    get_public_historical_monthly_refresh_minute,
    get_public_historical_weekly_refresh_minute,
    get_public_ranking_monthly_refresh_times,
    get_public_ranking_refresh_interval_seconds,
    get_public_ranking_weekly_refresh_minute,
    get_public_recent_matches_refresh_interval_seconds,
)
from app.payloads import (
    build_historical_server_summary_payload,
    build_leaderboard_snapshot_payload,
    build_recent_historical_matches_payload,
    build_recent_historical_matches_snapshot_payload,
)
from app.historical_runner import (
    _maybe_run_public_read_model_refreshes,
    _json_default,
    _run_refresh_with_retries,
    get_next_public_full_refresh_at,
    run_public_refresh_job_once,
    run_periodic_historical_refresh,
)
from app.historical_snapshots import _normalize_snapshot_limit
from app.historical_storage import list_monthly_mvp_v2_ranking
from app.postgres_display_storage import _json_payload_default
from app.rcon_historical_read_model import (
    _calculate_coverage_hours,
    _calculate_duration_seconds,
)
from app.rcon_historical_leaderboards import _dedupe_snapshot_rows
from app.rcon_historical_leaderboards import initialize_ranking_snapshot_storage
from app.rcon_historical_leaderboards import list_rcon_materialized_leaderboard


class HistoricalSnapshotRefreshTests(unittest.TestCase):
    def setUp(self) -> None:
        historical_runner_module._LAST_PUBLIC_FULL_REFRESH_LOCAL_DATE = None
        historical_runner_module._LAST_PUBLIC_RECENT_MATCHES_REFRESH_AT = None
        historical_runner_module._LAST_PUBLIC_RANKING_WEEKLY_REFRESH_SLOT = None
        historical_runner_module._LAST_PUBLIC_RANKING_MONTHLY_REFRESH_SLOT = None
        historical_runner_module._LAST_PUBLIC_HISTORICAL_WEEKLY_REFRESH_SLOT = None
        historical_runner_module._LAST_PUBLIC_HISTORICAL_MONTHLY_REFRESH_SLOT = None
        historical_runner_module._PUBLIC_REFRESH_IN_PROGRESS.clear()

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

    def test_public_refresh_env_values_are_parsed_before_use(self) -> None:
        with patch.dict(
            os.environ,
            {
                "HLL_PUBLIC_FULL_REFRESH_ENABLED": "true",
                "HLL_PUBLIC_FULL_REFRESH_TIME": "06:00",
                "HLL_PUBLIC_FULL_REFRESH_TIMEZONE": "Europe/Madrid",
                "HLL_PUBLIC_RANKING_REFRESH_INTERVAL_SECONDS": "900",
                "HLL_PUBLIC_RECENT_MATCHES_REFRESH_INTERVAL_SECONDS": "60",
                "HLL_PUBLIC_RANKING_WEEKLY_REFRESH_MINUTE": "10",
                "HLL_PUBLIC_RANKING_MONTHLY_REFRESH_TIMES": "07:00,19:00",
                "HLL_PUBLIC_HISTORICAL_WEEKLY_REFRESH_MINUTE": "25",
                "HLL_PUBLIC_HISTORICAL_MONTHLY_REFRESH_MINUTE": "40",
                "HLL_PUBLIC_HISTORICAL_MONTHLY_REFRESH_HOUR_INTERVAL": "2",
            },
            clear=False,
        ):
            self.assertTrue(get_public_full_refresh_enabled())
            self.assertEqual(get_public_full_refresh_time(), "06:00")
            self.assertEqual(get_public_full_refresh_timezone(), "Europe/Madrid")
            self.assertEqual(get_public_ranking_refresh_interval_seconds(), 900)
            self.assertEqual(get_public_recent_matches_refresh_interval_seconds(), 60)
            self.assertEqual(get_public_ranking_weekly_refresh_minute(), 10)
            self.assertEqual(get_public_ranking_monthly_refresh_times(), ("07:00", "19:00"))
            self.assertEqual(get_public_historical_weekly_refresh_minute(), 25)
            self.assertEqual(get_public_historical_monthly_refresh_minute(), 40)
            self.assertEqual(get_public_historical_monthly_refresh_hour_interval(), 2)

    def test_next_public_full_refresh_uses_madrid_six_am(self) -> None:
        with patch.dict(
            os.environ,
            {
                "HLL_PUBLIC_FULL_REFRESH_TIME": "06:00",
                "HLL_PUBLIC_FULL_REFRESH_TIMEZONE": "Europe/Madrid",
            },
            clear=False,
        ):
            next_refresh = get_next_public_full_refresh_at(
                now=datetime(2026, 6, 10, 3, 30, tzinfo=timezone.utc),
            )

        self.assertEqual(
            next_refresh,
            datetime(2026, 6, 10, 4, 0, tzinfo=timezone.utc),
        )

    def test_public_scheduler_runs_hourly_weekly_ranking_job(self) -> None:
        historical_runner_module._LAST_PUBLIC_RECENT_MATCHES_REFRESH_AT = datetime(
            2026, 6, 10, 6, 10, tzinfo=timezone.utc
        )
        historical_runner_module._LAST_PUBLIC_RANKING_MONTHLY_REFRESH_SLOT = "2026-06-10T05:00:00Z"
        historical_runner_module._LAST_PUBLIC_HISTORICAL_WEEKLY_REFRESH_SLOT = "2026-06-10T05:25:00Z"
        historical_runner_module._LAST_PUBLIC_HISTORICAL_MONTHLY_REFRESH_SLOT = "2026-06-10T04:40:00Z"
        with (
            patch.dict(
                os.environ,
                {
                    "HLL_PUBLIC_FULL_REFRESH_ENABLED": "false",
                    "HLL_PUBLIC_RANKING_WEEKLY_REFRESH_MINUTE": "10",
                    "HLL_PUBLIC_RANKING_MONTHLY_REFRESH_TIMES": "07:00,19:00",
                    "HLL_PUBLIC_HISTORICAL_WEEKLY_REFRESH_MINUTE": "25",
                    "HLL_PUBLIC_HISTORICAL_MONTHLY_REFRESH_MINUTE": "40",
                    "HLL_PUBLIC_HISTORICAL_MONTHLY_REFRESH_HOUR_INTERVAL": "2",
                    "HLL_PUBLIC_RECENT_MATCHES_REFRESH_INTERVAL_SECONDS": "3600",
                },
                clear=False,
            ),
            patch(
                "app.historical_runner.refresh_public_weekly_ranking_snapshots",
                return_value={"status": "ok"},
            ) as weekly_ranking_refresh,
        ):
            payload = _maybe_run_public_read_model_refreshes(
                run_number=3,
                now=datetime(2026, 6, 10, 6, 10, tzinfo=timezone.utc),
            )

        self.assertEqual(payload["status"], "ok")
        self.assertIn("ranking_weekly_snapshot_result", payload)
        weekly_ranking_refresh.assert_called_once()

    def test_public_scheduler_runs_bi_hourly_monthly_historical_job(self) -> None:
        historical_runner_module._LAST_PUBLIC_RECENT_MATCHES_REFRESH_AT = datetime(
            2026, 6, 10, 6, 40, tzinfo=timezone.utc
        )
        historical_runner_module._LAST_PUBLIC_RANKING_MONTHLY_REFRESH_SLOT = "2026-06-10T05:00:00Z"
        historical_runner_module._LAST_PUBLIC_RANKING_WEEKLY_REFRESH_SLOT = "2026-06-10T06:10:00Z"
        historical_runner_module._LAST_PUBLIC_HISTORICAL_WEEKLY_REFRESH_SLOT = "2026-06-10T06:25:00Z"
        with (
            patch.dict(
                os.environ,
                {
                    "HLL_PUBLIC_FULL_REFRESH_ENABLED": "false",
                    "HLL_PUBLIC_RANKING_WEEKLY_REFRESH_MINUTE": "10",
                    "HLL_PUBLIC_RANKING_MONTHLY_REFRESH_TIMES": "07:00,19:00",
                    "HLL_PUBLIC_HISTORICAL_WEEKLY_REFRESH_MINUTE": "25",
                    "HLL_PUBLIC_HISTORICAL_MONTHLY_REFRESH_MINUTE": "40",
                    "HLL_PUBLIC_HISTORICAL_MONTHLY_REFRESH_HOUR_INTERVAL": "2",
                    "HLL_PUBLIC_RECENT_MATCHES_REFRESH_INTERVAL_SECONDS": "3600",
                },
                clear=False,
            ),
            patch(
                "app.historical_runner.refresh_public_monthly_historical_snapshots",
                return_value={"status": "ok"},
            ) as historical_monthly_refresh,
        ):
            payload = _maybe_run_public_read_model_refreshes(
                run_number=4,
                now=datetime(2026, 6, 10, 6, 40, tzinfo=timezone.utc),
            )

        self.assertEqual(payload["status"], "ok")
        self.assertIn("historical_monthly_snapshot_result", payload)
        historical_monthly_refresh.assert_called_once()

    def test_public_scheduler_skips_lower_priority_jobs_when_heavy_job_runs(self) -> None:
        historical_runner_module._LAST_PUBLIC_RECENT_MATCHES_REFRESH_AT = datetime(
            2026, 6, 10, 5, 30, tzinfo=timezone.utc
        )
        with (
            patch.dict(
                os.environ,
                {
                    "HLL_PUBLIC_FULL_REFRESH_ENABLED": "false",
                    "HLL_PUBLIC_RANKING_WEEKLY_REFRESH_MINUTE": "10",
                    "HLL_PUBLIC_RANKING_MONTHLY_REFRESH_TIMES": "07:00,19:00",
                    "HLL_PUBLIC_HISTORICAL_WEEKLY_REFRESH_MINUTE": "25",
                    "HLL_PUBLIC_HISTORICAL_MONTHLY_REFRESH_MINUTE": "40",
                    "HLL_PUBLIC_HISTORICAL_MONTHLY_REFRESH_HOUR_INTERVAL": "2",
                    "HLL_PUBLIC_RECENT_MATCHES_REFRESH_INTERVAL_SECONDS": "3600",
                },
                clear=False,
            ),
            patch(
                "app.historical_runner.refresh_public_monthly_ranking_snapshots",
                return_value={"status": "ok"},
            ) as monthly_ranking_refresh,
            patch("app.historical_runner.refresh_public_weekly_ranking_snapshots") as weekly_ranking_refresh,
            patch("app.historical_runner.refresh_public_weekly_historical_snapshots") as weekly_historical_refresh,
        ):
            payload = _maybe_run_public_read_model_refreshes(
                run_number=5,
                now=datetime(2026, 6, 10, 5, 30, tzinfo=timezone.utc),
            )

        self.assertEqual(payload["ranking_monthly_snapshot_result"]["status"], "ok")
        self.assertEqual(payload["ranking_weekly_snapshot_result"]["status"], "skipped")
        self.assertEqual(payload["historical_weekly_snapshot_result"]["status"], "skipped")
        monthly_ranking_refresh.assert_called_once()
        weekly_ranking_refresh.assert_not_called()
        weekly_historical_refresh.assert_not_called()

    def test_manual_public_job_runner_routes_to_supported_job(self) -> None:
        with patch(
            "app.historical_runner.refresh_public_weekly_historical_snapshots",
            return_value={"status": "ok", "job_name": "public-historical-weekly"},
        ) as weekly_historical_refresh:
            result = run_public_refresh_job_once(
                "historical-weekly",
                now=datetime(2026, 6, 10, 6, 25, tzinfo=timezone.utc),
            )

        self.assertEqual(result["job_name"], "public-historical-weekly")
        weekly_historical_refresh.assert_called_once()

    def test_historical_runner_json_default_serializes_datetime_payloads(self) -> None:
        payload = {
            "status": "ok",
            "data": {
                "generated_at": datetime(2026, 6, 11, 8, 0, tzinfo=timezone.utc),
            },
        }

        encoded = json.loads(json.dumps(payload, default=_json_default))

        self.assertEqual(encoded["data"]["generated_at"], "2026-06-11T08:00:00Z")

    def test_ranking_snapshot_dedupes_duplicate_player_rows(self) -> None:
        rows = [
            {"player_id": "player-1", "player_name": "Alpha", "metric_value": 20},
            {"player_id": "player-1", "player_name": "Alpha duplicate", "metric_value": 19},
            {"player_id": "player-2", "player_name": "Bravo", "metric_value": 18},
        ]

        deduplicated_rows = _dedupe_snapshot_rows(rows)

        self.assertEqual([row["player_id"] for row in deduplicated_rows], ["player-1", "player-2"])
        self.assertEqual(deduplicated_rows[0]["player_name"], "Alpha")

    def test_monthly_mvp_v2_missing_player_event_ledger_returns_empty_payload(self) -> None:
        monthly_window = {
            "window_start": datetime(2026, 6, 1, tzinfo=timezone.utc),
            "window_end": datetime(2026, 6, 11, tzinfo=timezone.utc),
            "window_kind": "current-month",
            "window_label": "Mes activo",
            "uses_fallback": False,
            "selection_reason": "test",
            "current_month_closed_matches": 4,
            "previous_month_closed_matches": 8,
            "minimum_closed_matches": 3,
            "current_month_has_sufficient_sample": True,
            "is_early_month": False,
        }
        with (
            patch("app.historical_storage.initialize_historical_storage", return_value=Path("dummy.sqlite3")),
            patch("app.historical_storage._select_monthly_window", return_value=monthly_window),
            patch(
                "app.historical_storage._get_monthly_player_event_coverage",
                side_effect=sqlite3.OperationalError("no such table: player_event_raw_ledger"),
            ),
        ):
            payload = list_monthly_mvp_v2_ranking(server_id="all-servers", limit=10)

        self.assertFalse(payload["event_coverage"]["ready"])
        self.assertEqual(payload["event_coverage"]["reason"], "player-event-raw-ledger-missing")
        self.assertEqual(payload["items"], [])

    def test_initialize_ranking_snapshot_storage_uses_materialized_initializer_without_invalid_keyword(self) -> None:
        db_path = Path("dummy.sqlite3")
        with (
            patch(
                "app.rcon_historical_leaderboards.initialize_rcon_materialized_storage",
                return_value=db_path,
            ) as materialized_initializer,
            patch("app.rcon_historical_leaderboards.use_postgres_rcon_storage", return_value=False),
            patch(
                "app.rcon_historical_leaderboards.connect_sqlite_writer",
                return_value=sqlite3.connect(":memory:"),
            ),
        ):
            resolved_path = initialize_ranking_snapshot_storage(db_path=db_path, ensure_storage=True)

        materialized_initializer.assert_called_once_with(db_path=db_path)
        self.assertEqual(resolved_path, db_path)

    def test_initialize_ranking_snapshot_storage_skips_materialized_initializer_when_disabled(self) -> None:
        db_path = Path("dummy.sqlite3")
        with (
            patch("app.rcon_historical_leaderboards.initialize_rcon_materialized_storage") as materialized_initializer,
            patch("app.rcon_historical_leaderboards.use_postgres_rcon_storage", return_value=False),
            patch(
                "app.rcon_historical_leaderboards.connect_sqlite_writer",
                return_value=sqlite3.connect(":memory:"),
            ),
        ):
            resolved_path = initialize_ranking_snapshot_storage(db_path=db_path, ensure_storage=False)

        materialized_initializer.assert_not_called()
        self.assertEqual(resolved_path, db_path)

    def test_list_rcon_materialized_leaderboard_skips_materialized_initializer_when_disabled(self) -> None:
        db_path = Path("dummy.sqlite3")
        window = {
            "start": datetime(2026, 6, 9, tzinfo=timezone.utc),
            "end": datetime(2026, 6, 10, tzinfo=timezone.utc),
            "days": 1,
            "kind": "current-week",
            "label": "Semana actual",
            "selection_reason": "test",
            "current_week_start": datetime(2026, 6, 9, tzinfo=timezone.utc),
            "current_week_closed_matches": 1,
            "previous_week_closed_matches": 2,
            "current_month_start": datetime(2026, 6, 1, tzinfo=timezone.utc),
            "selected_month_start": datetime(2026, 6, 1, tzinfo=timezone.utc),
            "selected_month_end": datetime(2026, 6, 10, tzinfo=timezone.utc),
            "current_month_closed_matches": 3,
            "previous_month_closed_matches": 4,
            "sufficient_sample": {"minimum_closed_matches": 1},
        }
        fake_connection = object()
        with (
            patch("app.rcon_historical_leaderboards.initialize_rcon_materialized_storage") as materialized_initializer,
            patch(
                "app.rcon_historical_leaderboards._connect_scope",
                return_value=nullcontext(fake_connection),
            ) as connect_scope,
            patch("app.rcon_historical_leaderboards.select_leaderboard_window", return_value=window),
            patch("app.rcon_historical_leaderboards._fetch_leaderboard_rows", return_value=[]),
            patch(
                "app.rcon_historical_leaderboards._fetch_source_range",
                return_value=(None, None),
            ),
        ):
            payload = list_rcon_materialized_leaderboard(
                server_key="all-servers",
                timeframe="weekly",
                metric="kills",
                limit=10,
                ensure_storage=False,
                db_path=db_path,
                now=datetime(2026, 6, 10, tzinfo=timezone.utc),
            )

        materialized_initializer.assert_not_called()
        connect_scope.assert_called_once_with(db_path, db_path=db_path, initialize=False)
        self.assertEqual(payload["items"], [])

    def test_historical_leaderboard_snapshot_does_not_runtime_enrich_public_request(self) -> None:
        snapshot = {
            "generated_at": "2026-06-10T04:00:00Z",
            "source_range_start": "2026-06-09T00:00:00Z",
            "source_range_end": "2026-06-10T00:00:00Z",
            "is_stale": False,
            "payload": {
                "items": [
                    {
                        "ranking_position": 1,
                        "player": {"name": "Player One"},
                        "metric_value": 12,
                        "matches_considered": 1,
                        "kills": 12,
                    }
                ],
                "window_start": "2026-06-09T00:00:00Z",
                "window_end": "2026-06-10T00:00:00Z",
                "limit": 10,
            },
        }
        with (
            patch("app.payloads._get_historical_snapshot_record", return_value=snapshot),
            patch("app.payloads._load_runtime_leaderboard_items") as runtime_loader,
        ):
            payload = build_leaderboard_snapshot_payload(
                server_id="all-servers",
                timeframe="weekly",
                metric="kills",
                limit=10,
            )

        runtime_loader.assert_not_called()
        self.assertEqual(payload["data"]["items"][0]["metric_value"], 12)
        self.assertFalse(payload["data"]["runtime_enrichment"]["applied"])

    def test_recent_matches_snapshot_does_not_complete_from_public_scoreboard(self) -> None:
        snapshot = {
            "generated_at": "2026-06-10T04:00:00Z",
            "source_range_start": "2026-06-09T21:00:00Z",
            "source_range_end": "2026-06-09T22:00:00Z",
            "is_stale": False,
            "payload": {
                "items": [
                    {
                        "match_id": "match-1",
                        "closed_at": "2026-06-09T22:00:00Z",
                    }
                ],
                "limit": 100,
            },
        }
        with (
            patch("app.payloads._get_historical_snapshot_record", return_value=snapshot),
            patch("app.payloads.get_historical_data_source_kind", return_value="rcon"),
            patch("app.payloads.list_recent_historical_matches") as fallback_loader,
        ):
            payload = build_recent_historical_matches_snapshot_payload(
                server_slug="all-servers",
                limit=100,
            )

        fallback_loader.assert_not_called()
        self.assertEqual(len(payload["data"]["items"]), 1)
        self.assertFalse(payload["data"].get("fallback_used", False))

    def test_legacy_recent_matches_uses_snapshot_fast_path(self) -> None:
        snapshot = {
            "generated_at": "2026-06-10T04:00:00Z",
            "source_range_start": "2026-06-09T21:00:00Z",
            "source_range_end": "2026-06-09T22:00:00Z",
            "is_stale": False,
            "payload": {
                "items": [
                    {
                        "match_id": "match-1",
                        "closed_at": "2026-06-09T22:00:00Z",
                    }
                ],
                "limit": 100,
            },
        }
        with (
            patch("app.payloads._get_historical_snapshot_record", return_value=snapshot),
            patch("app.payloads.get_historical_data_source_kind", return_value="rcon"),
            patch("app.payloads.get_rcon_historical_read_model") as rcon_loader,
            patch("app.payloads.list_recent_historical_matches") as fallback_loader,
        ):
            payload = build_recent_historical_matches_payload(
                server_slug="comunidad-hispana-01",
                limit=20,
            )

        rcon_loader.assert_not_called()
        fallback_loader.assert_not_called()
        self.assertEqual(payload["data"]["context"], "historical-recent-matches")
        self.assertEqual(payload["data"]["legacy_endpoint_policy"], "snapshot-read-only-fast-path")
        self.assertEqual(payload["data"]["server_slug"], "comunidad-hispana-01")
        self.assertEqual(payload["data"]["items"][0]["match_id"], "match-1")

    def test_legacy_second_server_recent_matches_uses_snapshot_fast_path(self) -> None:
        snapshot = {
            "generated_at": "2026-06-10T04:00:00Z",
            "source_range_start": "2026-06-09T21:00:00Z",
            "source_range_end": "2026-06-09T22:00:00Z",
            "is_stale": False,
            "payload": {
                "items": [
                    {
                        "match_id": "match-2",
                        "closed_at": "2026-06-09T22:00:00Z",
                    }
                ],
                "limit": 100,
            },
        }
        with (
            patch("app.payloads._get_historical_snapshot_record", return_value=snapshot),
            patch("app.payloads.get_historical_data_source_kind", return_value="rcon"),
            patch("app.payloads.get_rcon_historical_read_model") as rcon_loader,
            patch("app.payloads.list_recent_historical_matches") as fallback_loader,
        ):
            payload = build_recent_historical_matches_payload(
                server_slug="comunidad-hispana-02",
                limit=20,
            )

        rcon_loader.assert_not_called()
        fallback_loader.assert_not_called()
        self.assertEqual(payload["data"]["server_slug"], "comunidad-hispana-02")
        self.assertEqual(payload["data"]["items"][0]["match_id"], "match-2")

    def test_legacy_all_servers_recent_matches_still_uses_snapshot_fast_path(self) -> None:
        snapshot = {
            "generated_at": "2026-06-10T04:00:00Z",
            "source_range_start": "2026-06-09T21:00:00Z",
            "source_range_end": "2026-06-09T22:00:00Z",
            "is_stale": False,
            "payload": {
                "items": [
                    {
                        "match_id": "match-all",
                        "closed_at": "2026-06-09T22:00:00Z",
                    }
                ],
                "limit": 100,
            },
        }
        with (
            patch("app.payloads._get_historical_snapshot_record", return_value=snapshot),
            patch("app.payloads.get_historical_data_source_kind", return_value="rcon"),
            patch("app.payloads.get_rcon_historical_read_model") as rcon_loader,
            patch("app.payloads.list_recent_historical_matches") as fallback_loader,
        ):
            payload = build_recent_historical_matches_payload(
                server_slug="all-servers",
                limit=20,
            )

        rcon_loader.assert_not_called()
        fallback_loader.assert_not_called()
        self.assertEqual(payload["data"]["server_slug"], "all-servers")
        self.assertEqual(payload["data"]["items"][0]["match_id"], "match-all")

    def test_legacy_server_summary_uses_snapshot_fast_path(self) -> None:
        snapshot = {
            "generated_at": "2026-06-10T04:00:00Z",
            "source_range_start": "2026-06-09T00:00:00Z",
            "source_range_end": "2026-06-10T00:00:00Z",
            "is_stale": False,
            "payload": {
                "item": {
                    "server": {"slug": "comunidad-hispana-01", "name": "Comunidad Hispana #01"},
                    "matches_count": 12,
                },
            },
        }
        with (
            patch("app.payloads._get_historical_snapshot_record", return_value=snapshot),
            patch("app.payloads.get_historical_data_source_kind", return_value="rcon"),
            patch("app.payloads.get_rcon_historical_read_model") as rcon_loader,
            patch("app.payloads.list_historical_server_summaries") as fallback_loader,
        ):
            payload = build_historical_server_summary_payload(server_slug="comunidad-hispana-01")

        rcon_loader.assert_not_called()
        fallback_loader.assert_not_called()
        self.assertEqual(payload["data"]["context"], "historical-server-summary")
        self.assertEqual(payload["data"]["legacy_endpoint_policy"], "snapshot-read-only-fast-path")
        self.assertEqual(payload["data"]["server_slug"], "comunidad-hispana-01")
        self.assertEqual(payload["data"]["items"][0]["matches_count"], 12)

    def test_legacy_second_server_summary_uses_snapshot_fast_path(self) -> None:
        snapshot = {
            "generated_at": "2026-06-10T04:00:00Z",
            "source_range_start": "2026-06-09T00:00:00Z",
            "source_range_end": "2026-06-10T00:00:00Z",
            "is_stale": False,
            "payload": {
                "item": {
                    "server": {"slug": "comunidad-hispana-02", "name": "Comunidad Hispana #02"},
                    "matches_count": 8,
                },
            },
        }
        with (
            patch("app.payloads._get_historical_snapshot_record", return_value=snapshot),
            patch("app.payloads.get_historical_data_source_kind", return_value="rcon"),
            patch("app.payloads.get_rcon_historical_read_model") as rcon_loader,
            patch("app.payloads.list_historical_server_summaries") as fallback_loader,
        ):
            payload = build_historical_server_summary_payload(server_slug="comunidad-hispana-02")

        rcon_loader.assert_not_called()
        fallback_loader.assert_not_called()
        self.assertEqual(payload["data"]["server_slug"], "comunidad-hispana-02")
        self.assertEqual(payload["data"]["items"][0]["matches_count"], 8)

    def test_legacy_all_servers_summary_still_uses_snapshot_fast_path(self) -> None:
        snapshot = {
            "generated_at": "2026-06-10T04:00:00Z",
            "source_range_start": "2026-06-09T00:00:00Z",
            "source_range_end": "2026-06-10T00:00:00Z",
            "is_stale": False,
            "payload": {
                "item": {
                    "server": {"slug": "all-servers", "name": "Todos los servidores"},
                    "matches_count": 20,
                },
            },
        }
        with (
            patch("app.payloads._get_historical_snapshot_record", return_value=snapshot),
            patch("app.payloads.get_historical_data_source_kind", return_value="rcon"),
            patch("app.payloads.get_rcon_historical_read_model") as rcon_loader,
            patch("app.payloads.list_historical_server_summaries") as fallback_loader,
        ):
            payload = build_historical_server_summary_payload(server_slug="all-servers")

        rcon_loader.assert_not_called()
        fallback_loader.assert_not_called()
        self.assertEqual(payload["data"]["server_slug"], "all-servers")
        self.assertEqual(payload["data"]["items"][0]["matches_count"], 20)

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
