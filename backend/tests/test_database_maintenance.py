from __future__ import annotations

import io
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.database_maintenance import run_database_maintenance_cleanup
from app.rcon_admin_log_materialization import MATCH_RESULT_SOURCE, initialize_rcon_materialized_storage
from app.rcon_admin_log_storage import initialize_rcon_admin_log_storage
from app.storage import initialize_storage


class DatabaseMaintenanceTests(unittest.TestCase):
    def test_dry_run_does_not_delete(self) -> None:
        with _temp_db() as db_path:
            _insert_server_snapshot(db_path, snapshot_id=1, captured_at="2026-05-01T00:00:00Z")

            payload = run_database_maintenance_cleanup(
                db_path=db_path,
                now="2026-06-20T12:00:00Z",
            )

            self.assertEqual(payload["status"], "ok")
            self.assertEqual(payload["mode"], "dry-run")
            with closing(sqlite3.connect(db_path)) as connection:
                self.assertEqual(
                    connection.execute("SELECT COUNT(*) FROM server_snapshots").fetchone()[0],
                    1,
                )

    def test_apply_deletes_old_server_snapshots(self) -> None:
        with _temp_db() as db_path:
            _insert_server_snapshot(db_path, snapshot_id=1, captured_at="2026-05-01T00:00:00Z")
            _insert_server_snapshot(db_path, snapshot_id=2, captured_at="2026-06-18T00:00:00Z")

            run_database_maintenance_cleanup(
                apply=True,
                db_path=db_path,
                now="2026-06-20T12:00:00Z",
                recent_matches_keep=1,
            )

            with closing(sqlite3.connect(db_path)) as connection:
                ids = [row[0] for row in connection.execute("SELECT id FROM server_snapshots ORDER BY id")]
            self.assertEqual(ids, [2])

    def test_apply_deletes_old_noncritical_admin_log_events(self) -> None:
        with _temp_db() as db_path:
            _insert_admin_log_event(
                db_path,
                event_id=1,
                event_type="chat",
                event_timestamp="2026-04-01T00:00:00Z",
                server_time=100,
            )
            _insert_admin_log_event(
                db_path,
                event_id=2,
                event_type="chat",
                event_timestamp="2026-06-15T00:00:00Z",
                server_time=200,
            )

            run_database_maintenance_cleanup(
                apply=True,
                db_path=db_path,
                now="2026-06-20T12:00:00Z",
            )

            with closing(sqlite3.connect(db_path)) as connection:
                remaining = [
                    tuple(row)
                    for row in connection.execute(
                        "SELECT id, event_type FROM rcon_admin_log_events ORDER BY id"
                    )
                ]
            self.assertEqual(remaining, [(2, "chat")])

    def test_apply_preserves_critical_events_within_retention(self) -> None:
        with _temp_db() as db_path:
            _insert_admin_log_event(
                db_path,
                event_id=1,
                event_type="kill",
                event_timestamp="2026-06-10T00:00:00Z",
                server_time=100,
            )

            run_database_maintenance_cleanup(
                apply=True,
                db_path=db_path,
                now="2026-06-20T12:00:00Z",
            )

            with closing(sqlite3.connect(db_path)) as connection:
                count = connection.execute(
                    "SELECT COUNT(*) FROM rcon_admin_log_events WHERE event_type = 'kill'"
                ).fetchone()[0]
            self.assertEqual(count, 1)

    def test_apply_preserves_latest_100_materialized_matches(self) -> None:
        with _temp_db() as db_path:
            for index in range(101):
                ended_at = (
                    datetime(2026, 1, 1, 12, tzinfo=timezone.utc) + timedelta(days=index)
                ).isoformat().replace("+00:00", "Z")
                _insert_materialized_match(
                    db_path,
                    match_id=index + 1,
                    match_key=f"match-{index + 1}",
                    ended_at=ended_at,
                    server_time_start=(index + 1) * 10,
                    server_time_end=(index + 1) * 10 + 5,
                )

            run_database_maintenance_cleanup(
                apply=True,
                db_path=db_path,
                now="2026-06-20T12:00:00Z",
            )

            with closing(sqlite3.connect(db_path)) as connection:
                remaining = connection.execute(
                    "SELECT COUNT(*) FROM rcon_materialized_matches"
                ).fetchone()[0]
                oldest = connection.execute(
                    "SELECT COUNT(*) FROM rcon_materialized_matches WHERE match_key = 'match-1'"
                ).fetchone()[0]
            self.assertEqual(remaining, 100)
            self.assertEqual(oldest, 0)

    def test_apply_preserves_current_month_matches(self) -> None:
        with _temp_db() as db_path:
            _insert_materialized_match(
                db_path,
                match_id=1,
                match_key="old",
                ended_at="2026-01-10T12:00:00Z",
                server_time_start=10,
                server_time_end=20,
            )
            _insert_materialized_match(
                db_path,
                match_id=2,
                match_key="current-month",
                ended_at="2026-06-03T12:00:00Z",
                server_time_start=30,
                server_time_end=40,
            )

            run_database_maintenance_cleanup(
                apply=True,
                db_path=db_path,
                now="2026-06-20T12:00:00Z",
                recent_matches_keep=1,
            )

            with closing(sqlite3.connect(db_path)) as connection:
                keys = [row[0] for row in connection.execute("SELECT match_key FROM rcon_materialized_matches")]
            self.assertEqual(keys, ["current-month"])

    def test_apply_preserves_previous_month_when_now_day_is_early(self) -> None:
        with _temp_db() as db_path:
            _insert_materialized_match(
                db_path,
                match_id=1,
                match_key="previous-month",
                ended_at="2026-05-15T12:00:00Z",
                server_time_start=10,
                server_time_end=20,
            )
            _insert_materialized_match(
                db_path,
                match_id=2,
                match_key="older",
                ended_at="2026-04-15T12:00:00Z",
                server_time_start=30,
                server_time_end=40,
            )

            run_database_maintenance_cleanup(
                apply=True,
                db_path=db_path,
                now="2026-06-05T12:00:00Z",
                recent_matches_keep=1,
            )

            with closing(sqlite3.connect(db_path)) as connection:
                keys = [row[0] for row in connection.execute("SELECT match_key FROM rcon_materialized_matches")]
            self.assertEqual(keys, ["previous-month"])

    def test_apply_preserves_current_week(self) -> None:
        with _temp_db() as db_path:
            _insert_materialized_match(
                db_path,
                match_id=1,
                match_key="current-week",
                ended_at="2026-06-10T12:00:00Z",
                server_time_start=10,
                server_time_end=20,
            )
            _insert_materialized_match(
                db_path,
                match_id=2,
                match_key="older",
                ended_at="2026-05-01T12:00:00Z",
                server_time_start=30,
                server_time_end=40,
            )

            run_database_maintenance_cleanup(
                apply=True,
                db_path=db_path,
                now="2026-06-10T13:00:00Z",
                recent_matches_keep=1,
            )

            with closing(sqlite3.connect(db_path)) as connection:
                keys = [row[0] for row in connection.execute("SELECT match_key FROM rcon_materialized_matches")]
            self.assertEqual(keys, ["current-week"])

    def test_apply_preserves_previous_week_when_fallback_may_need_it(self) -> None:
        with _temp_db() as db_path:
            _insert_materialized_match(
                db_path,
                match_id=1,
                match_key="previous-week",
                ended_at="2026-06-03T12:00:00Z",
                server_time_start=10,
                server_time_end=20,
            )
            _insert_materialized_match(
                db_path,
                match_id=2,
                match_key="current-week-sample",
                ended_at="2026-06-09T12:00:00Z",
                server_time_start=30,
                server_time_end=40,
            )
            _insert_materialized_match(
                db_path,
                match_id=3,
                match_key="older",
                ended_at="2026-05-01T12:00:00Z",
                server_time_start=50,
                server_time_end=60,
            )

            run_database_maintenance_cleanup(
                apply=True,
                db_path=db_path,
                now="2026-06-10T13:00:00Z",
                recent_matches_keep=1,
            )

            with closing(sqlite3.connect(db_path)) as connection:
                keys = {
                    row[0]
                    for row in connection.execute("SELECT match_key FROM rcon_materialized_matches")
                }
            self.assertEqual(keys, {"previous-week", "current-week-sample"})

    def test_apply_deletes_old_non_protected_match_and_child_stats(self) -> None:
        with _temp_db() as db_path:
            _insert_materialized_match(
                db_path,
                match_id=1,
                match_key="delete-me",
                ended_at="2026-01-10T12:00:00Z",
                server_time_start=10,
                server_time_end=20,
            )
            _insert_materialized_match(
                db_path,
                match_id=2,
                match_key="keep-me",
                ended_at="2026-06-18T12:00:00Z",
                server_time_start=30,
                server_time_end=40,
            )
            _insert_player_stat(db_path, match_key="delete-me", player_id="player-1")
            _insert_player_stat(db_path, match_key="keep-me", player_id="player-2")

            run_database_maintenance_cleanup(
                apply=True,
                db_path=db_path,
                now="2026-06-20T12:00:00Z",
                recent_matches_keep=1,
            )

            with closing(sqlite3.connect(db_path)) as connection:
                deleted_match_count = connection.execute(
                    "SELECT COUNT(*) FROM rcon_materialized_matches WHERE match_key = 'delete-me'"
                ).fetchone()[0]
                deleted_stat_count = connection.execute(
                    "SELECT COUNT(*) FROM rcon_match_player_stats WHERE match_key = 'delete-me'"
                ).fetchone()[0]
                kept_stat_count = connection.execute(
                    "SELECT COUNT(*) FROM rcon_match_player_stats WHERE match_key = 'keep-me'"
                ).fetchone()[0]
            self.assertEqual(deleted_match_count, 0)
            self.assertEqual(deleted_stat_count, 0)
            self.assertEqual(kept_stat_count, 1)

    def test_missing_optional_tables_are_logged_and_do_not_crash(self) -> None:
        with _temp_db(create_schema=False) as db_path:
            stream = io.StringIO()
            with redirect_stdout(stream):
                payload = run_database_maintenance_cleanup(
                    db_path=db_path,
                    now="2026-06-20T12:00:00Z",
                )

            self.assertEqual(payload["status"], "ok")
            self.assertIn("database-maintenance-table-skipped", stream.getvalue())


def _temp_db(*, create_schema: bool = True):
    class _TempDbContext:
        def __enter__(self) -> Path:
            self._tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
            self.db_path = Path(self._tmpdir.name) / "maintenance.sqlite3"
            if create_schema:
                initialize_storage(db_path=self.db_path)
                initialize_rcon_admin_log_storage(db_path=self.db_path)
                initialize_rcon_materialized_storage(db_path=self.db_path)
            return self.db_path

        def __exit__(self, exc_type, exc, tb) -> None:
            self._tmpdir.cleanup()

    return _TempDbContext()


def _insert_server_snapshot(db_path: Path, *, snapshot_id: int, captured_at: str) -> None:
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO game_sources (
                id, slug, display_name, provider_kind, is_active, created_at, updated_at
            ) VALUES (1, 'current-hll', 'Current Hell Let Loose', 'development', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO servers (
                id, game_source_id, external_server_id, server_name, region, first_seen_at, last_seen_at
            ) VALUES (1, 1, 'server-1', 'Server 1', 'ES', ?, ?)
            """,
            (captured_at, captured_at),
        )
        connection.execute(
            """
            INSERT INTO server_snapshots (
                id, server_id, captured_at, status, players, max_players, current_map, source_name
            ) VALUES (?, 1, ?, 'online', 10, 100, 'hurtgen', 'test')
            """,
            (snapshot_id, captured_at),
        )
        connection.commit()


def _insert_admin_log_event(
    db_path: Path,
    *,
    event_id: int,
    event_type: str,
    event_timestamp: str,
    server_time: int,
) -> None:
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute(
            """
            INSERT INTO rcon_admin_log_events (
                id, target_key, external_server_id, event_timestamp, server_time,
                relative_time, event_type, raw_message, canonical_message,
                parsed_payload_json, raw_entry_json
            ) VALUES (?, 'comunidad-hispana-01', 'comunidad-hispana-01', ?, ?, '', ?, '', '', '{}', '{}')
            """,
            (event_id, event_timestamp, server_time, event_type),
        )
        connection.commit()


def _insert_materialized_match(
    db_path: Path,
    *,
    match_id: int,
    match_key: str,
    ended_at: str,
    server_time_start: int,
    server_time_end: int,
) -> None:
    started_at = _shift_iso(ended_at, hours=-1)
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute(
            """
            INSERT INTO rcon_materialized_matches (
                id, target_key, external_server_id, match_key, map_name, map_pretty_name,
                game_mode, started_server_time, ended_server_time, started_at, ended_at,
                allied_score, axis_score, winner, confidence_mode, source_basis
            ) VALUES (?, 'comunidad-hispana-01', 'comunidad-hispana-01', ?, 'hurtgen', 'Hurtgen Forest',
                      'warfare', ?, ?, ?, ?, 5, 3, 'allied', 'exact', ?)
            """,
            (
                match_id,
                match_key,
                server_time_start,
                server_time_end,
                started_at,
                ended_at,
                MATCH_RESULT_SOURCE,
            ),
        )
        connection.commit()


def _insert_player_stat(db_path: Path, *, match_key: str, player_id: str) -> None:
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute(
            """
            INSERT INTO rcon_match_player_stats (
                target_key, match_key, player_id, player_name, team,
                kills, deaths, teamkills, deaths_by_teamkill,
                weapons_json, death_by_weapons_json, most_killed_json, death_by_json
            ) VALUES (
                'comunidad-hispana-01', ?, ?, ?, 'Allies',
                1, 1, 0, 0, '{}', '{}', '{}', '{}'
            )
            """,
            (match_key, player_id, player_id),
        )
        connection.commit()


def _shift_iso(value: str, *, hours: int) -> str:
    point = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    shifted = point + timedelta(hours=hours)
    return shifted.isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    unittest.main()
