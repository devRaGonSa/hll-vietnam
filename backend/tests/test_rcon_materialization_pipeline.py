"""Regression tests for the materialized RCON AdminLog pipeline."""

from __future__ import annotations

import gc
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.historical_storage import upsert_historical_match
from app.payloads import build_recent_historical_matches_payload
from app.rcon_historical_player_stats import (
    get_rcon_materialized_player_stats,
    initialize_player_period_stats_storage,
    initialize_player_search_index_storage,
    search_rcon_materialized_players,
)
from app.rcon_admin_log_materialization import (
    get_materialized_rcon_match_detail,
    materialize_rcon_admin_log,
    summarize_rcon_materialization_status,
)
from app.rcon_admin_log_storage import persist_rcon_admin_log_entries
from app.rcon_historical_read_model import (
    _build_player_active_time_payload,
    get_rcon_historical_match_detail,
    list_rcon_historical_recent_activity,
)
from app.scoreboard_origins import resolve_trusted_scoreboard_match_url


class RconMaterializationPipelineTests(unittest.TestCase):
    def test_materializes_match_result_and_player_stats_idempotently(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "historical.sqlite3"
            _persist_admin_log_fixture(db_path)

            first = materialize_rcon_admin_log(db_path=db_path)
            second = materialize_rcon_admin_log(db_path=db_path)
            detail = get_materialized_rcon_match_detail(
                server_key="comunidad-hispana-01",
                match_key="comunidad-hispana-01:100:500:stmariedumontwarfare",
                db_path=db_path,
            )
            status = summarize_rcon_materialization_status(db_path=db_path)

            self.assertEqual(first["matches_materialized"], 1)
            self.assertEqual(second["matches_materialized"], 0)
            self.assertEqual(second["matches_updated"], 1)
            self.assertIsNotNone(detail)
            match = detail["match"]
            self.assertEqual(match["allied_score"], 5)
            self.assertEqual(match["axis_score"], 0)
            self.assertEqual(match["winner"], "allied")
            players = {row["player_name"]: row for row in detail["players"]}
            self.assertEqual(players["Alpha"]["kills"], 1)
            self.assertEqual(players["Alpha"]["teamkills"], 1)
            self.assertEqual(players["Bravo"]["deaths"], 1)
            self.assertEqual(players["Charlie"]["deaths_by_teamkill"], 1)
            self.assertEqual(players["Alpha"]["player_active_seconds"], 350)
            self.assertEqual(players["Alpha"]["active_time_source"], "connection_intervals")
            self.assertEqual(players["Bravo"]["player_active_seconds"], 0)
            self.assertEqual(players["Bravo"]["active_time_source"], "event_span_fallback")
            self.assertEqual(status["materialized_matches"], 1)
            self.assertEqual(status["matches_with_player_stats"], 1)
            gc.collect()

    def test_match_detail_read_model_hides_raw_player_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "historical.sqlite3"
            previous_storage_path = os.environ.get("HLL_BACKEND_STORAGE_PATH")
            os.environ["HLL_BACKEND_STORAGE_PATH"] = str(db_path)
            try:
                _persist_admin_log_fixture(db_path)
                materialize_rcon_admin_log(db_path=db_path)
                detail = get_rcon_historical_match_detail(
                    server_key="comunidad-hispana-01",
                    match_id="comunidad-hispana-01:100:500:stmariedumontwarfare",
                )
            finally:
                _restore_env("HLL_BACKEND_STORAGE_PATH", previous_storage_path)

            self.assertIsNotNone(detail)
            self.assertEqual(detail["result_source"], "admin-log-match-ended")
            self.assertEqual(detail["result"]["allied_score"], 5)
            self.assertEqual(detail["timestamp_confidence"], "absolute")
            players = {row["player_name"]: row for row in detail["players"]}
            self.assertNotIn("player_id", players["Alpha"])
            self.assertIn("kd_ratio", players["Alpha"])
            self.assertEqual(players["Alpha"]["player_active_seconds"], 350)
            self.assertEqual(players["Alpha"]["kpm_status"], "ready")
            self.assertEqual(players["Alpha"]["kpm"], 0.17)
            self.assertEqual(players["Bravo"]["kpm_status"], "missing_connection_intervals")
            self.assertIsNone(players["Bravo"]["kpm"])
            self.assertEqual(players["Alpha"]["steam_id_64"], "76561198000000001")
            self.assertEqual(players["Alpha"]["platform"], "steam")
            self.assertEqual(
                players["Alpha"]["external_profile_links"]["hellor"],
                "https://hellor.pro/player/76561198000000001",
            )
            self.assertEqual(players["Charlie"]["platform"], "unknown")
            self.assertNotIn("steam_id_64", players["Charlie"])
            self.assertEqual(players["Charlie"]["external_profile_links"], {})
            gc.collect()

    def test_materialization_migrates_existing_player_stats_schema_with_active_time_columns(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            db_path = Path(tmpdir) / "historical.sqlite3"
            connection = sqlite3.connect(db_path)
            try:
                connection.executescript(
                    """
                    CREATE TABLE rcon_admin_log_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        target_key TEXT NOT NULL,
                        external_server_id TEXT,
                        event_timestamp TEXT,
                        server_time INTEGER,
                        relative_time TEXT,
                        event_type TEXT NOT NULL,
                        raw_message TEXT NOT NULL,
                        canonical_message TEXT NOT NULL,
                        parsed_payload_json TEXT NOT NULL,
                        raw_entry_json TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                    );

                    CREATE TABLE rcon_materialized_matches (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        target_key TEXT NOT NULL,
                        external_server_id TEXT,
                        match_key TEXT NOT NULL,
                        map_name TEXT,
                        map_pretty_name TEXT,
                        game_mode TEXT,
                        started_server_time INTEGER,
                        ended_server_time INTEGER,
                        started_at TEXT,
                        ended_at TEXT,
                        allied_score INTEGER,
                        axis_score INTEGER,
                        winner TEXT,
                        confidence_mode TEXT NOT NULL,
                        source_basis TEXT NOT NULL,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(target_key, match_key)
                    );

                    CREATE TABLE rcon_match_player_stats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        target_key TEXT NOT NULL,
                        match_key TEXT NOT NULL,
                        player_id TEXT NOT NULL,
                        player_name TEXT NOT NULL,
                        team TEXT,
                        kills INTEGER NOT NULL DEFAULT 0,
                        deaths INTEGER NOT NULL DEFAULT 0,
                        teamkills INTEGER NOT NULL DEFAULT 0,
                        deaths_by_teamkill INTEGER NOT NULL DEFAULT 0,
                        weapons_json TEXT NOT NULL DEFAULT '{}',
                        death_by_weapons_json TEXT NOT NULL DEFAULT '{}',
                        most_killed_json TEXT NOT NULL DEFAULT '{}',
                        death_by_json TEXT NOT NULL DEFAULT '{}',
                        first_seen_server_time INTEGER,
                        last_seen_server_time INTEGER,
                        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(target_key, match_key, player_id)
                    );
                    """
                )
            finally:
                connection.close()

            materialize_rcon_admin_log(db_path=db_path)

            connection = sqlite3.connect(db_path)
            try:
                columns = {
                    row[1]
                    for row in connection.execute("PRAGMA table_info(rcon_match_player_stats)")
                }
            finally:
                connection.close()

            self.assertIn("player_active_seconds", columns)
            self.assertIn("active_time_source", columns)
            gc.collect()

    def test_match_detail_keeps_kpm_missing_for_legacy_rows_without_active_time(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            db_path = Path(tmpdir) / "historical.sqlite3"
            previous_storage_path = os.environ.get("HLL_BACKEND_STORAGE_PATH")
            os.environ["HLL_BACKEND_STORAGE_PATH"] = str(db_path)
            try:
                materialize_rcon_admin_log(db_path=db_path)
                connection = sqlite3.connect(db_path)
                try:
                    connection.execute(
                        """
                        INSERT INTO rcon_materialized_matches (
                            target_key, external_server_id, match_key, map_name, map_pretty_name,
                            game_mode, started_server_time, ended_server_time, started_at, ended_at,
                            allied_score, axis_score, winner, confidence_mode, source_basis
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "comunidad-hispana-01",
                            "comunidad-hispana-01",
                            "legacy-match",
                            "mortain_warfare",
                            "Mortain",
                            "warfare",
                            100,
                            500,
                            "2026-05-01T10:00:00Z",
                            "2026-05-01T11:00:00Z",
                            5,
                            3,
                            "allied",
                            "exact",
                            "admin-log-match-ended",
                        ),
                    )
                    connection.execute(
                        """
                        INSERT INTO rcon_match_player_stats (
                            target_key, match_key, player_id, player_name, team,
                            kills, deaths, teamkills, deaths_by_teamkill,
                            weapons_json, death_by_weapons_json, most_killed_json, death_by_json,
                            first_seen_server_time, last_seen_server_time, player_active_seconds, active_time_source
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "comunidad-hispana-01",
                            "legacy-match",
                            "steam-legacy",
                            "Legacy",
                            "Allies",
                            10,
                            5,
                            0,
                            0,
                            "{}",
                            "{}",
                            "{}",
                            "{}",
                            120,
                            480,
                            None,
                            None,
                        ),
                    )
                    connection.commit()
                finally:
                    connection.close()
                detail = get_rcon_historical_match_detail(
                    server_key="comunidad-hispana-01",
                    match_id="legacy-match",
                )
            finally:
                _restore_env("HLL_BACKEND_STORAGE_PATH", previous_storage_path)

            self.assertIsNotNone(detail)
            player = detail["players"][0]
            self.assertIsNone(player["kpm"])
            self.assertEqual(player["kpm_status"], "missing_active_time")
            gc.collect()

    def test_active_time_counts_full_match_for_player_connected_before_start(self) -> None:
        detail = _materialize_detail_from_entries(
            entries=[
                {
                    "timestamp": "2026-05-01T09:58:00Z",
                    "message": "[0 min (80)] CONNECTED Carry Over (steam-carry)",
                },
                {
                    "timestamp": "2026-05-01T10:00:00Z",
                    "message": "[1 min (100)] MATCH START Mortain Warfare",
                },
                {
                    "timestamp": "2026-05-01T10:30:00Z",
                    "message": (
                        "[31 min (1900)] KILL: Carry Over(Allies/steam-carry) -> "
                        "Victim(Axis/steam-victim) with M1 GARAND"
                    ),
                },
                {
                    "timestamp": "2026-05-01T11:00:00Z",
                    "message": "[61 min (3700)] MATCH ENDED `Mortain Warfare` ALLIED (5 - 0) AXIS",
                },
            ]
        )

        player = {row["player_name"]: row for row in detail["players"]}["Carry Over"]
        self.assertEqual(player["player_active_seconds"], 3600)
        self.assertEqual(player["active_time_source"], "connection_intervals_carryover")
        self.assertEqual(player["kpm_status"], "ready")
        self.assertEqual(player["kpm"], 0.02)

    def test_active_time_counts_until_disconnect_for_player_connected_before_start(self) -> None:
        detail = _materialize_detail_from_entries(
            entries=[
                {
                    "timestamp": "2026-05-01T09:58:00Z",
                    "message": "[0 min (80)] CONNECTED Carry Over (steam-carry)",
                },
                {
                    "timestamp": "2026-05-01T10:00:00Z",
                    "message": "[1 min (100)] MATCH START Mortain Warfare",
                },
                {
                    "timestamp": "2026-05-01T10:20:00Z",
                    "message": "[21 min (1300)] DISCONNECTED Carry Over (steam-carry)",
                },
                {
                    "timestamp": "2026-05-01T11:00:00Z",
                    "message": "[61 min (3700)] MATCH ENDED `Mortain Warfare` ALLIED (5 - 0) AXIS",
                },
            ]
        )

        player = detail["players"][0]
        self.assertEqual(player["player_active_seconds"], 1200)
        self.assertEqual(player["active_time_source"], "connection_intervals_carryover")

    def test_active_time_counts_from_connect_until_match_end(self) -> None:
        detail = _materialize_detail_from_entries(
            entries=[
                {
                    "timestamp": "2026-05-01T10:00:00Z",
                    "message": "[1 min (100)] MATCH START Mortain Warfare",
                },
                {
                    "timestamp": "2026-05-01T10:10:00Z",
                    "message": "[11 min (700)] CONNECTED Late Join (steam-late)",
                },
                {
                    "timestamp": "2026-05-01T11:00:00Z",
                    "message": "[61 min (3700)] MATCH ENDED `Mortain Warfare` ALLIED (5 - 0) AXIS",
                },
            ]
        )

        player = detail["players"][0]
        self.assertEqual(player["player_active_seconds"], 3000)
        self.assertEqual(player["active_time_source"], "connection_intervals")

    def test_active_time_sums_multiple_connection_intervals(self) -> None:
        detail = _materialize_detail_from_entries(
            entries=[
                {
                    "timestamp": "2026-05-01T10:00:00Z",
                    "message": "[1 min (100)] MATCH START Mortain Warfare",
                },
                {
                    "timestamp": "2026-05-01T10:05:00Z",
                    "message": "[6 min (400)] CONNECTED Reconnect (steam-reconnect)",
                },
                {
                    "timestamp": "2026-05-01T10:15:00Z",
                    "message": "[16 min (1000)] DISCONNECTED Reconnect (steam-reconnect)",
                },
                {
                    "timestamp": "2026-05-01T10:20:00Z",
                    "message": "[21 min (1300)] CONNECTED Reconnect (steam-reconnect)",
                },
                {
                    "timestamp": "2026-05-01T10:35:00Z",
                    "message": "[36 min (2200)] DISCONNECTED Reconnect (steam-reconnect)",
                },
                {
                    "timestamp": "2026-05-01T11:00:00Z",
                    "message": "[61 min (3700)] MATCH ENDED `Mortain Warfare` ALLIED (5 - 0) AXIS",
                },
            ]
        )

        player = detail["players"][0]
        self.assertEqual(player["player_active_seconds"], 1500)
        self.assertEqual(player["active_time_source"], "connection_intervals")

    def test_active_time_uses_event_span_fallback_without_ready_kpm_when_connection_intervals_missing(self) -> None:
        detail = _materialize_detail_from_entries(
            entries=[
                {
                    "timestamp": "2026-05-01T10:00:00Z",
                    "message": "[1 min (100)] MATCH START Mortain Warfare",
                },
                {
                    "timestamp": "2026-05-01T10:05:00Z",
                    "message": (
                        "[6 min (400)] KILL: Fallback(Allies/steam-fallback) -> "
                        "Victim(Axis/steam-victim) with M1 GARAND"
                    ),
                },
                {
                    "timestamp": "2026-05-01T10:20:00Z",
                    "message": "[21 min (1300)] CHAT[Team][Fallback(Allies/steam-fallback)]: test",
                },
                {
                    "timestamp": "2026-05-01T11:00:00Z",
                    "message": "[61 min (3700)] MATCH ENDED `Mortain Warfare` ALLIED (5 - 0) AXIS",
                },
            ]
        )

        player = {row["player_name"]: row for row in detail["players"]}["Fallback"]
        self.assertEqual(player["player_active_seconds"], 900)
        self.assertEqual(player["active_time_source"], "event_span_fallback")
        self.assertEqual(player["kpm_status"], "missing_connection_intervals")
        self.assertIsNone(player["kpm"])

    def test_kpm_is_null_when_active_time_is_below_threshold(self) -> None:
        detail = _materialize_detail_from_entries(
            entries=[
                {
                    "timestamp": "2026-05-01T10:00:00Z",
                    "message": "[1 min (100)] MATCH START Mortain Warfare",
                },
                {
                    "timestamp": "2026-05-01T10:01:00Z",
                    "message": "[2 min (120)] CONNECTED Short (steam-short)",
                },
                {
                    "timestamp": "2026-05-01T10:01:30Z",
                    "message": "[2 min (150)] DISCONNECTED Short (steam-short)",
                },
                {
                    "timestamp": "2026-05-01T11:00:00Z",
                    "message": "[61 min (3700)] MATCH ENDED `Mortain Warfare` ALLIED (5 - 0) AXIS",
                },
            ]
        )

        player = detail["players"][0]
        self.assertEqual(player["player_active_seconds"], 30)
        self.assertEqual(player["kpm_status"], "insufficient_active_time")
        self.assertIsNone(player["kpm"])

    def test_kpm_payload_helper_returns_ready_for_ten_kills_in_ten_minutes(self) -> None:
        payload = _build_player_active_time_payload(
            kills=10,
            player_active_seconds=600,
            active_time_source="connection_intervals",
        )

        self.assertEqual(payload["kpm"], 1.0)
        self.assertEqual(payload["kpm_status"], "ready")

    def test_kpm_payload_helper_returns_zero_for_zero_kills_with_valid_active_time(self) -> None:
        payload = _build_player_active_time_payload(
            kills=0,
            player_active_seconds=600,
            active_time_source="connection_intervals",
        )

        self.assertEqual(payload["kpm"], 0.0)
        self.assertEqual(payload["kpm_status"], "ready")

    def test_kpm_payload_helper_returns_missing_when_active_time_is_null(self) -> None:
        payload = _build_player_active_time_payload(
            kills=10,
            player_active_seconds=None,
            active_time_source="unavailable",
        )

        self.assertIsNone(payload["kpm"])
        self.assertEqual(payload["kpm_status"], "missing_active_time")

    def test_match_detail_marks_equal_materialized_timestamps_as_server_time_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "historical.sqlite3"
            previous_storage_path = os.environ.get("HLL_BACKEND_STORAGE_PATH")
            os.environ["HLL_BACKEND_STORAGE_PATH"] = str(db_path)
            try:
                persist_rcon_admin_log_entries(
                    target={
                        "target_key": "comunidad-hispana-01",
                        "external_server_id": "comunidad-hispana-01",
                    },
                    entries=[
                        {
                            "timestamp": "2026-05-01T12:00:00Z",
                            "message": "[1 min (100)] MATCH START ST MARIE DU MONT Warfare",
                        },
                        {
                            "timestamp": "2026-05-01T12:00:00Z",
                            "message": "[91 min (5500)] MATCH ENDED `ST MARIE DU MONT Warfare` ALLIED (5 - 0) AXIS",
                        },
                    ],
                    db_path=db_path,
                )
                materialize_rcon_admin_log(db_path=db_path)
                detail = get_rcon_historical_match_detail(
                    server_key="comunidad-hispana-01",
                    match_id="comunidad-hispana-01:100:5500:stmariedumontwarfare",
                )
            finally:
                _restore_env("HLL_BACKEND_STORAGE_PATH", previous_storage_path)

            self.assertIsNotNone(detail)
            self.assertIsNone(detail["started_at"])
            self.assertIsNone(detail["ended_at"])
            self.assertEqual(detail["closed_at"], "2026-05-01T12:00:00Z")
            self.assertEqual(detail["timestamp_confidence"], "server-time-only")
            self.assertEqual(detail["duration_seconds"], 5400)
            gc.collect()

    def test_equal_timestamp_materialized_detail_uses_closed_at_window_for_scoreboard_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "historical.sqlite3"
            previous_storage_path = os.environ.get("HLL_BACKEND_STORAGE_PATH")
            os.environ["HLL_BACKEND_STORAGE_PATH"] = str(db_path)
            try:
                upsert_historical_match(
                    server_slug="comunidad-hispana-02",
                    match_payload={
                        "id": "1779183861",
                        "creation_time": "2026-05-01T10:30:00Z",
                        "start": "2026-05-01T10:30:00Z",
                        "end": "2026-05-01T12:00:00Z",
                        "map": {"name": "ST MARIE DU MONT Warfare"},
                        "result": {"allied": 5, "axis": 0},
                        "player_stats": [],
                    },
                    db_path=db_path,
                )
                persist_rcon_admin_log_entries(
                    target={
                        "target_key": "comunidad-hispana-02",
                        "external_server_id": "comunidad-hispana-02",
                    },
                    entries=[
                        {
                            "timestamp": "2026-05-01T12:00:00Z",
                            "message": "[1 min (100)] MATCH START ST MARIE DU MONT Warfare",
                        },
                        {
                            "timestamp": "2026-05-01T12:00:00Z",
                            "message": "[91 min (5500)] MATCH ENDED `ST MARIE DU MONT Warfare` ALLIED (5 - 0) AXIS",
                        },
                    ],
                    db_path=db_path,
                )
                materialize_rcon_admin_log(db_path=db_path)
                detail = get_rcon_historical_match_detail(
                    server_key="comunidad-hispana-02",
                    match_id="comunidad-hispana-02:100:5500:stmariedumontwarfare",
                )
            finally:
                _restore_env("HLL_BACKEND_STORAGE_PATH", previous_storage_path)

            self.assertIsNotNone(detail)
            self.assertIsNone(detail["started_at"])
            self.assertIsNone(detail["ended_at"])
            self.assertEqual(detail["duration_seconds"], 5400)
            self.assertEqual(
                detail["match_url"],
                "https://scoreboard.comunidadhll.es:5443/games/1779183861",
            )
            gc.collect()

    def test_match_detail_omits_profile_summary_when_snapshot_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "historical.sqlite3"
            previous_storage_path = os.environ.get("HLL_BACKEND_STORAGE_PATH")
            os.environ["HLL_BACKEND_STORAGE_PATH"] = str(db_path)
            try:
                _persist_admin_log_fixture(db_path)
                persist_rcon_admin_log_entries(
                    target={
                        "target_key": "comunidad-hispana-01",
                        "external_server_id": "comunidad-hispana-01",
                    },
                    entries=[
                        {
                            "timestamp": "2026-05-01T10:30:00Z",
                            "message": (
                                "[31 min (300)] MESSAGE: player [Alpha(76561198000000001)], "
                                "content [─ Alpha ─\n"
                                "▒ Totales ▒\n"
                                "sesiones : 12\n"
                                "partidas jugadas : 9\n"
                                "bajas : 141 (6 TKs)\n"
                                "muertes : 268 (5 TKs)\n"
                                "K/D : 0.53\n"
                                "▒ Armas favoritas ▒\n"
                                "M1 Garand : 31]"
                            ),
                        }
                    ],
                    db_path=db_path,
                )
                materialize_rcon_admin_log(db_path=db_path)
                detail = get_rcon_historical_match_detail(
                    server_key="comunidad-hispana-01",
                    match_id="comunidad-hispana-01:100:500:stmariedumontwarfare",
                )
            finally:
                _restore_env("HLL_BACKEND_STORAGE_PATH", previous_storage_path)

            self.assertIsNotNone(detail)
            players = {row["player_name"]: row for row in detail["players"]}
            self.assertNotIn("profile_summary", players["Alpha"])
            self.assertNotIn("profile_summary", players["Bravo"])
            self.assertNotIn("player_id", players["Alpha"])
            self.assertEqual(players["Alpha"]["steam_id_64"], "76561198000000001")
            self.assertIn("external_profile_links", players["Alpha"])
            gc.collect()

    def test_recent_matches_prefer_materialized_rcon_over_scoreboard_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "historical.sqlite3"
            previous_storage_path = os.environ.get("HLL_BACKEND_STORAGE_PATH")
            os.environ["HLL_BACKEND_STORAGE_PATH"] = str(db_path)
            try:
                _persist_admin_log_fixture(db_path)
                materialize_rcon_admin_log(db_path=db_path)
                _persist_scoreboard_match(db_path)

                payload = build_recent_historical_matches_payload(
                    limit=5,
                    server_slug="comunidad-hispana-01",
                )
                recent = list_rcon_historical_recent_activity(
                    server_key="comunidad-hispana-01",
                    limit=5,
                )
            finally:
                _restore_env("HLL_BACKEND_STORAGE_PATH", previous_storage_path)

            self.assertEqual(payload["data"]["selected_source"], "rcon")
            self.assertEqual(payload["data"]["items"][0]["result_source"], "admin-log-match-ended")
            self.assertEqual(recent[0]["result_source"], "admin-log-match-ended")
            self.assertNotEqual(payload["data"]["selected_source"], "public-scoreboard")
            gc.collect()

    def test_recent_materialized_detail_id_resolves_through_detail_read_model(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "historical.sqlite3"
            previous_storage_path = os.environ.get("HLL_BACKEND_STORAGE_PATH")
            os.environ["HLL_BACKEND_STORAGE_PATH"] = str(db_path)
            try:
                _persist_admin_log_fixture(db_path)
                materialize_rcon_admin_log(db_path=db_path)
                recent = list_rcon_historical_recent_activity(
                    server_key="comunidad-hispana-01",
                    limit=1,
                )[0]
                detail = get_rcon_historical_match_detail(
                    server_key="comunidad-hispana-01",
                    match_id=str(recent["internal_detail_match_id"]),
                )
            finally:
                _restore_env("HLL_BACKEND_STORAGE_PATH", previous_storage_path)

            self.assertIsNotNone(detail)
            self.assertEqual(detail["match_id"], recent["internal_detail_match_id"])
            gc.collect()

    def test_public_scoreboard_fallback_used_only_without_rcon_activity(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "historical.sqlite3"
            previous_storage_path = os.environ.get("HLL_BACKEND_STORAGE_PATH")
            os.environ["HLL_BACKEND_STORAGE_PATH"] = str(db_path)
            try:
                _persist_scoreboard_match(db_path)
                payload = build_recent_historical_matches_payload(
                    limit=5,
                    server_slug="comunidad-hispana-01",
                )
            finally:
                _restore_env("HLL_BACKEND_STORAGE_PATH", previous_storage_path)

            self.assertTrue(payload["data"]["fallback_used"])
            self.assertEqual(payload["data"]["selected_source"], "public-scoreboard")
            self.assertEqual(payload["data"]["items"][0]["result_source"], "public-scoreboard-fallback")
            gc.collect()

    def test_public_player_search_uses_read_model_without_initialize_or_runtime_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "historical.sqlite3"
            initialize_player_search_index_storage(db_path=db_path)
            _insert_player_search_index_fixture(db_path)

            with (
                patch(
                    "app.rcon_historical_player_stats.initialize_player_search_index_storage",
                    side_effect=AssertionError("public read must not initialize player search storage"),
                ),
                patch(
                    "app.rcon_historical_player_stats._search_rcon_materialized_players_runtime",
                    side_effect=AssertionError("public read must not use runtime player search fallback"),
                ),
            ):
                payload = search_rcon_materialized_players(
                    query="Medu",
                    server_id="all",
                    limit=10,
                    db_path=db_path,
                )

            self.assertEqual(payload["source"]["read_model"], "player-search-index")
            self.assertFalse(payload["source"]["fallback_used"])
            self.assertEqual(payload["items"][0]["player_id"], "76561198092154180")
            gc.collect()

    def test_public_player_detail_returns_controlled_empty_without_initialize_or_runtime_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "missing.sqlite3"

            with (
                patch(
                    "app.rcon_historical_player_stats.initialize_player_period_stats_storage",
                    side_effect=AssertionError("public read must not initialize player period storage"),
                ),
                patch(
                    "app.rcon_historical_player_stats._get_rcon_materialized_player_stats_runtime",
                    side_effect=AssertionError("public read must not use runtime player detail fallback"),
                ),
            ):
                payload = get_rcon_materialized_player_stats(
                    player_id="76561198092154180",
                    server_id="all",
                    timeframe="weekly",
                    db_path=db_path,
                )

            self.assertEqual(payload["player_id"], "76561198092154180")
            self.assertEqual(payload["matches_considered"], 0)
            self.assertEqual(payload["source"]["read_model"], "player-period-stats")
            self.assertEqual(payload["source"]["status"], "unavailable")
            self.assertFalse(payload["source"]["fallback_used"])
            gc.collect()

    def test_public_match_detail_read_does_not_initialize_materialized_storage(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "historical.sqlite3"
            previous_storage_path = os.environ.get("HLL_BACKEND_STORAGE_PATH")
            os.environ["HLL_BACKEND_STORAGE_PATH"] = str(db_path)
            try:
                _persist_admin_log_fixture(db_path)
                materialize_rcon_admin_log(db_path=db_path)
                with patch(
                    "app.rcon_admin_log_materialization.initialize_rcon_materialized_storage",
                    side_effect=AssertionError("public match detail read must not initialize storage"),
                ):
                    detail = get_rcon_historical_match_detail(
                        server_key="comunidad-hispana-01",
                        match_id="comunidad-hispana-01:100:500:stmariedumontwarfare",
                    )
            finally:
                _restore_env("HLL_BACKEND_STORAGE_PATH", previous_storage_path)

            self.assertIsNotNone(detail)
            self.assertEqual(detail["result_source"], "admin-log-match-ended")
            gc.collect()

    def test_safe_scoreboard_match_url_allowlist_for_active_origins(self) -> None:
        self.assertEqual(
            resolve_trusted_scoreboard_match_url(
                "https://scoreboard.comunidadhll.es/games/1561515",
                "comunidad-hispana-01",
            ),
            "https://scoreboard.comunidadhll.es/games/1561515",
        )
        self.assertEqual(
            resolve_trusted_scoreboard_match_url(
                "https://scoreboard.comunidadhll.es:5443/games/222",
                "comunidad-hispana-02",
            ),
            "https://scoreboard.comunidadhll.es:5443/games/222",
        )
        self.assertIsNone(
            resolve_trusted_scoreboard_match_url(
                "https://example.com/games/222",
                "comunidad-hispana-02",
            )
        )
        self.assertIsNone(
            resolve_trusted_scoreboard_match_url(
                "https://scoreboard.comunidadhll.es:5443/admin/222",
                "comunidad-hispana-02",
            )
        )


def _persist_admin_log_fixture(db_path: Path) -> None:
    persist_rcon_admin_log_entries(
        target={
            "target_key": "comunidad-hispana-01",
            "external_server_id": "comunidad-hispana-01",
        },
        entries=[
            {
                "timestamp": "2026-05-01T10:00:00Z",
                "message": "[1 min (100)] MATCH START ST MARIE DU MONT Warfare",
            },
            {
                "timestamp": "2026-05-01T10:05:00Z",
                "message": "[6 min (150)] CONNECTED Alpha (76561198000000001)",
            },
            {
                "timestamp": "2026-05-01T10:06:00Z",
                "message": "[7 min (160)] TEAMSWITCH Alpha (None > Allies)",
            },
            {
                "timestamp": "2026-05-01T10:10:00Z",
                "message": (
                    "[11 min (200)] KILL: Alpha(Allies/76561198000000001) -> "
                    "Bravo(Axis/76561198000000002) with M1 Garand"
                ),
            },
            {
                "timestamp": "2026-05-01T10:12:00Z",
                "message": (
                    "[13 min (220)] KILL: Alpha(Allies/76561198000000001) -> "
                    "Charlie(Allies/nonsteam-local) with M1 Garand"
                ),
            },
            {
                "timestamp": "2026-05-01T11:20:00Z",
                "message": "[81 min (500)] MATCH ENDED `ST MARIE DU MONT Warfare` ALLIED (5 - 0) AXIS",
            },
        ],
        db_path=db_path,
    )


def _materialize_detail_from_entries(*, entries: list[dict[str, object]]) -> dict[str, object]:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = Path(tmpdir) / "historical.sqlite3"
        previous_storage_path = os.environ.get("HLL_BACKEND_STORAGE_PATH")
        os.environ["HLL_BACKEND_STORAGE_PATH"] = str(db_path)
        try:
            persist_rcon_admin_log_entries(
                target={
                    "target_key": "comunidad-hispana-01",
                    "external_server_id": "comunidad-hispana-01",
                },
                entries=entries,
                db_path=db_path,
            )
            materialize_rcon_admin_log(db_path=db_path)
            match_rows = list_materialized_rcon_matches_for_test(db_path)
            detail = get_rcon_historical_match_detail(
                server_key="comunidad-hispana-01",
                match_id=str(match_rows[0]["match_key"]),
            )
        finally:
            _restore_env("HLL_BACKEND_STORAGE_PATH", previous_storage_path)
        if detail is None:
            raise AssertionError("expected materialized detail")
        return detail


def list_materialized_rcon_matches_for_test(db_path: Path) -> list[dict[str, object]]:
    from app.rcon_admin_log_materialization import list_materialized_rcon_matches

    return list_materialized_rcon_matches(
        target_key="comunidad-hispana-01",
        only_ended=True,
        limit=5,
        db_path=db_path,
    )


def _persist_scoreboard_match(db_path: Path) -> None:
    upsert_historical_match(
        server_slug="comunidad-hispana-01",
        match_payload={
            "id": "1561515",
            "creation_time": "2026-05-01T10:00:00Z",
            "start": "2026-05-01T10:00:00Z",
            "end": "2026-05-01T11:20:00Z",
            "map": {"name": "ST MARIE DU MONT Warfare"},
            "result": {"allied": 2, "axis": 3},
            "player_stats": [],
        },
        db_path=db_path,
    )


def _insert_player_search_index_fixture(db_path: Path) -> None:
    import sqlite3

    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO player_search_index (
                server_id,
                player_id,
                player_name,
                normalized_player_name,
                first_seen_at,
                last_seen_at,
                servers_seen,
                matches_current_year,
                kills_current_year,
                deaths_current_year,
                teamkills_current_year,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "all-servers",
                "76561198092154180",
                "Medu",
                "medu",
                "2026-01-01T00:00:00Z",
                "2026-06-01T00:00:00Z",
                '["comunidad-hispana-01"]',
                12,
                100,
                50,
                0,
                "2026-06-01T00:00:00Z",
            ),
        )


def _restore_env(name: str, previous_value: str | None) -> None:
    if previous_value is None:
        os.environ.pop(name, None)
    else:
        os.environ[name] = previous_value


if __name__ == "__main__":
    unittest.main()
