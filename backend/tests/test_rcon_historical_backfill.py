from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from contextlib import closing
from unittest.mock import patch

from app.rcon_admin_log_materialization import (
    MATCH_RESULT_SOURCE,
    initialize_rcon_materialized_storage,
)
from app.rcon_historical_backfill import (
    count_recent_materialized_closed_matches,
    run_rcon_historical_backfill,
    select_backfill_targets,
)
from app.rcon_historical_leaderboards import list_rcon_materialized_leaderboard


TARGETS_JSON = json.dumps(
    [
        {
            "name": "Comunidad Hispana #01",
            "slug": "comunidad-hispana-01",
            "external_server_id": "comunidad-hispana-01",
            "host": "127.0.0.1",
            "port": 7779,
            "password": "secret",
        },
        {
            "name": "Comunidad Hispana #02",
            "slug": "comunidad-hispana-02",
            "external_server_id": "comunidad-hispana-02",
            "host": "127.0.0.1",
            "port": 7879,
            "password": "secret",
        },
        {
            "name": "Comunidad Hispana #03",
            "slug": "comunidad-hispana-03",
            "external_server_id": "comunidad-hispana-03",
            "host": "127.0.0.1",
            "port": 7979,
            "password": "secret",
        },
    ]
)


class RconHistoricalBackfillTests(unittest.TestCase):
    def test_monthly_window_selects_previous_month_on_days_1_to_7(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            payload = list_rcon_materialized_leaderboard(
                server_key="all-servers",
                timeframe="monthly",
                metric="kills",
                db_path=Path(tmpdir) / "historical.sqlite3",
                now=datetime(2026, 5, 7, 12, tzinfo=timezone.utc),
            )

        self.assertEqual(payload["window_kind"], "previous-month")
        self.assertEqual(payload["selected_month_start"], "2026-04-01T00:00:00Z")
        self.assertEqual(payload["selected_month_end"], "2026-05-01T00:00:00Z")

    def test_monthly_window_selects_current_month_on_day_8_plus(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            payload = list_rcon_materialized_leaderboard(
                server_key="all-servers",
                timeframe="monthly",
                metric="kills",
                db_path=Path(tmpdir) / "historical.sqlite3",
                now=datetime(2026, 5, 8, 12, tzinfo=timezone.utc),
            )

        self.assertEqual(payload["window_kind"], "current-month")
        self.assertEqual(payload["selected_month_start"], "2026-05-01T00:00:00Z")

    def test_recent_match_ensure_stops_when_count_is_already_satisfied(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir, _patched_targets():
            db_path = Path(tmpdir) / "historical.sqlite3"
            _insert_closed_matches(db_path, 100)

            payload = run_rcon_historical_backfill(
                servers="comunidad-hispana-01,comunidad-hispana-02",
                ensure_recent_matches=100,
                dry_run=True,
                db_path=db_path,
            )

        self.assertEqual(payload["recent_materialized_closed_match_count_before"], 100)
        self.assertEqual(payload["actual_windows_scanned"], [])

    def test_unknown_server_is_rejected(self) -> None:
        with _patched_targets():
            with self.assertRaises(ValueError):
                select_backfill_targets("unknown-server")

    def test_comunidad_hispana_03_is_not_included_by_default(self) -> None:
        with _patched_targets():
            selected = select_backfill_targets(None)

        self.assertEqual(
            [target.external_server_id for target in selected],
            ["comunidad-hispana-01", "comunidad-hispana-02"],
        )

    def test_dry_run_does_not_insert_data(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir, _patched_targets():
            db_path = Path(tmpdir) / "historical.sqlite3"
            payload = run_rcon_historical_backfill(
                servers="comunidad-hispana-01",
                ensure_current_month=True,
                dry_run=True,
                db_path=db_path,
            )

            count_after = count_recent_materialized_closed_matches(db_path=db_path)

        self.assertEqual(payload["status"], "dry-run")
        self.assertEqual(payload["events_inserted"], 0)
        self.assertEqual(count_after, 0)

    def test_backfill_output_is_json_serializable(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir, _patched_targets():
            payload = run_rcon_historical_backfill(
                servers="comunidad-hispana-01",
                ensure_current_month=True,
                dry_run=True,
                db_path=Path(tmpdir) / "historical.sqlite3",
            )

        json.dumps(payload, ensure_ascii=True)


def _insert_closed_matches(db_path: Path, count: int) -> None:
    initialize_rcon_materialized_storage(db_path=db_path)
    with closing(sqlite3.connect(db_path)) as connection:
        for index in range(count):
            connection.execute(
                """
                INSERT INTO rcon_materialized_matches (
                    target_key, external_server_id, match_key, map_name, map_pretty_name,
                    started_at, ended_at, confidence_mode, source_basis
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "comunidad-hispana-01",
                    "comunidad-hispana-01",
                    f"match-{index}",
                    "stmariedumont",
                    "ST MARIE DU MONT",
                    "2026-05-01T10:00:00Z",
                    f"2026-05-{(index % 28) + 1:02d}T12:00:00Z",
                    "exact",
                    MATCH_RESULT_SOURCE,
                ),
            )
        connection.commit()


def _patched_targets():
    return patch.dict(os.environ, {"HLL_BACKEND_RCON_TARGETS": TARGETS_JSON})


if __name__ == "__main__":
    unittest.main()
