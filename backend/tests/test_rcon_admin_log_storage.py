import gc
import json
import sqlite3
from datetime import datetime, timezone

from app.rcon_admin_log_storage import (
    initialize_rcon_admin_log_storage,
    list_current_match_kill_feed,
    list_rcon_admin_log_event_counts,
    persist_rcon_admin_log_entries,
)


TARGET = {
    "target_key": "test-rcon-target",
    "external_server_id": "test-rcon-target",
}


def test_initialize_rcon_admin_log_storage_creates_event_table(tmp_path):
    db_path = tmp_path / "admin_log.sqlite3"

    resolved_path = initialize_rcon_admin_log_storage(db_path=db_path)

    assert resolved_path == db_path
    connection = sqlite3.connect(db_path)
    try:
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(rcon_admin_log_events)")
        }
    finally:
        connection.close()
        gc.collect()

    assert "rcon_admin_log_events" in table_names
    assert "rcon_player_profile_snapshots" in table_names
    assert {
        "target_key",
        "event_type",
        "raw_message",
        "canonical_message",
        "parsed_payload_json",
        "raw_entry_json",
    }.issubset(columns)


def test_persist_rcon_admin_log_entries_inserts_then_reports_duplicates(tmp_path):
    db_path = tmp_path / "admin_log.sqlite3"
    entries = [
        {
            "timestamp": "2026-05-19T10:00:00Z",
            "message": "[1:00 min (100)] CONNECTED Player One (steam-1)",
        },
        {
            "timestamp": "2026-05-19T10:01:00Z",
            "message": "[2:00 min (120)] DISCONNECTED Player One (steam-1)",
        },
    ]

    first_delta = persist_rcon_admin_log_entries(
        target=TARGET,
        entries=entries,
        db_path=db_path,
    )
    second_delta = persist_rcon_admin_log_entries(
        target=TARGET,
        entries=entries,
        db_path=db_path,
    )

    assert first_delta == {
        "events_seen": 2,
        "events_inserted": 2,
        "duplicate_events": 0,
    }
    assert second_delta == {
        "events_seen": 2,
        "events_inserted": 0,
        "duplicate_events": 2,
    }
    gc.collect()


def test_profile_message_snapshots_are_materialized_and_deduped(tmp_path):
    db_path = tmp_path / "admin_log.sqlite3"
    entry = {
        "timestamp": "2026-05-19T10:00:00Z",
        "message": (
            "[21:34:19 hours (1779108340)] MESSAGE: player [Jugador Uno(steam-profile-1)], "
            "content [─ Jugador Uno ─\n"
            "▒ Totales ▒\n"
            "sesiones : 12\n"
            "partidas jugadas : 9\n"
            "bajas : 141 (6 TKs)\n"
            "muertes : 268 (5 TKs)\n"
            "K/D : 0.53\n"
            "▒ VÃ­ctimas ▒\n"
            "Rival Dos : 7\n"
            "▒ NÃ©mesis ▒\n"
            "Rival Tres : 4\n"
            "▒ Armas favoritas ▒\n"
            "M1 GARAND : 31\n"
            "▒ Promedios ▒\n"
            "bajas por partida : 15.6\n"
            "▒ Sanciones ▒\n"
            "kicks : 1]"
        ),
    }

    persist_rcon_admin_log_entries(target=TARGET, entries=[entry], db_path=db_path)
    persist_rcon_admin_log_entries(target=TARGET, entries=[entry], db_path=db_path)

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute("SELECT * FROM rcon_player_profile_snapshots").fetchall()
    finally:
        connection.close()
        gc.collect()

    assert len(rows) == 1
    row = rows[0]
    assert row["target_key"] == "test-rcon-target"
    assert row["player_id"] == "steam-profile-1"
    assert row["source_server_time"] == 1779108340
    assert row["sessions"] == 12
    assert row["matches_played"] == 9
    assert row["total_kills"] == 141
    assert row["total_deaths"] == 268
    assert row["teamkills_done"] == 6
    assert row["teamkills_received"] == 5
    assert row["kd_ratio"] == 0.53
    assert json.loads(row["favorite_weapons_json"]) == {"M1 GARAND": 31}
    assert json.loads(row["victims_json"]) == {"Rival Dos": 7}
    assert json.loads(row["nemesis_json"]) == {"Rival Tres": 4}
    assert "bajas : 141" in row["raw_content"]


def test_non_profile_messages_do_not_create_profile_snapshots(tmp_path):
    db_path = tmp_path / "admin_log.sqlite3"

    persist_rcon_admin_log_entries(
        target=TARGET,
        entries=[
            {
                "timestamp": "2026-05-19T10:00:00Z",
                "message": "[1:00 min (100)] MESSAGE: player [Player One(steam-1)], content [hello]",
            }
        ],
        db_path=db_path,
    )

    connection = sqlite3.connect(db_path)
    try:
        count = connection.execute(
            "SELECT COUNT(*) FROM rcon_player_profile_snapshots"
        ).fetchone()[0]
    finally:
        connection.close()
        gc.collect()

    assert count == 0


def test_canonical_message_dedupes_changing_relative_prefixes(tmp_path):
    db_path = tmp_path / "admin_log.sqlite3"
    original_entry = {
        "timestamp": "2026-05-19T10:00:00Z",
        "message": "[1:00 min (100)] MESSAGE: player [Player One(steam-1)], content [hello]",
    }
    repeated_read_entry = {
        "timestamp": "2026-05-19T10:05:00Z",
        "message": "[6:00 min (100)] MESSAGE: player [Player One(steam-1)], content [hello]",
    }

    first_delta = persist_rcon_admin_log_entries(
        target=TARGET,
        entries=[original_entry],
        db_path=db_path,
    )
    second_delta = persist_rcon_admin_log_entries(
        target=TARGET,
        entries=[repeated_read_entry],
        db_path=db_path,
    )

    assert first_delta["events_inserted"] == 1
    assert second_delta == {
        "events_seen": 1,
        "events_inserted": 0,
        "duplicate_events": 1,
    }
    gc.collect()


def test_list_rcon_admin_log_event_counts_groups_by_target_and_event_type(tmp_path):
    db_path = tmp_path / "admin_log.sqlite3"
    other_target = {
        "target_key": "other-rcon-target",
        "external_server_id": "other-rcon-target",
    }

    persist_rcon_admin_log_entries(
        target=TARGET,
        entries=[
            {
                "timestamp": "2026-05-19T10:00:00Z",
                "message": "[1:00 min (100)] CONNECTED Player One (steam-1)",
            },
            {
                "timestamp": "2026-05-19T10:01:00Z",
                "message": "[2:00 min (120)] DISCONNECTED Player One (steam-1)",
            },
        ],
        db_path=db_path,
    )
    persist_rcon_admin_log_entries(
        target=other_target,
        entries=[
            {
                "timestamp": "2026-05-19T10:02:00Z",
                "message": "[3:00 min (140)] CONNECTED Player Two (steam-2)",
            }
        ],
        db_path=db_path,
    )

    counts = {
        (row["target_key"], row["event_type"]): row
        for row in list_rcon_admin_log_event_counts(db_path=db_path)
    }

    assert counts == {
        ("other-rcon-target", "connected"): {
            "target_key": "other-rcon-target",
            "event_type": "connected",
            "event_count": 1,
            "first_server_time": 140,
            "last_server_time": 140,
        },
        ("test-rcon-target", "connected"): {
            "target_key": "test-rcon-target",
            "event_type": "connected",
            "event_count": 1,
            "first_server_time": 100,
            "last_server_time": 100,
        },
        ("test-rcon-target", "disconnected"): {
            "target_key": "test-rcon-target",
            "event_type": "disconnected",
            "event_count": 1,
            "first_server_time": 120,
            "last_server_time": 120,
        },
    }
    gc.collect()


def test_current_match_kill_feed_prefers_open_match_window_and_normalizes_rows(tmp_path):
    db_path = tmp_path / "admin_log.sqlite3"
    persist_rcon_admin_log_entries(
        target=TARGET,
        entries=[
            {
                "timestamp": "2026-05-19T09:59:00Z",
                "message": (
                    "[0:59 min (90)] KILL: Old Killer(Allies/steam-old) -> "
                    "Old Victim(Axis/steam-victim-old) with M1 GARAND"
                ),
            },
            {
                "timestamp": "2026-05-19T10:00:00Z",
                "message": "[1:00 min (100)] MATCH START Mortain Warfare",
            },
            {
                "timestamp": "2026-05-19T10:01:00Z",
                "message": (
                    "[2:00 min (120)] KILL: Alpha(Allies/steam-alpha) -> "
                    "Bravo(Allies/steam-bravo) with GRENADE"
                ),
            },
        ],
        db_path=db_path,
    )

    feed = list_current_match_kill_feed(
        server_key="test-rcon-target",
        db_path=db_path,
    )

    assert feed["scope"] == "open-admin-log-match-window"
    assert feed["confidence"] == "admin-log-boundary"
    assert len(feed["items"]) == 1
    assert feed["items"][0] == {
        "event_id": "rcon-admin-log:test-rcon-target:3",
        "event_timestamp": "2026-05-19T10:01:00Z",
        "server_time": 120,
        "killer_name": "Alpha",
        "killer_team": "Allies",
        "victim_name": "Bravo",
        "victim_team": "Allies",
        "weapon": "GRENADE",
        "is_teamkill": True,
    }
    gc.collect()


def test_current_match_kill_feed_filters_stale_recent_fallback_rows(tmp_path):
    db_path = tmp_path / "admin_log.sqlite3"
    persist_rcon_admin_log_entries(
        target=TARGET,
        entries=[
            {
                "timestamp": "2026-05-21T09:30:00Z",
                "message": (
                    "[1:00 min (1779355800)] KILL: Old Killer(Allies/steam-old) -> "
                    "Old Victim(Axis/steam-victim-old) with M1 GARAND"
                ),
            }
        ],
        db_path=db_path,
    )

    feed = list_current_match_kill_feed(
        server_key="test-rcon-target",
        db_path=db_path,
        now=datetime(2026, 5, 21, 10, 0, tzinfo=timezone.utc),
    )

    assert feed["scope"] == "no-current-match-events"
    assert feed["confidence"] == "stale-filtered"
    assert feed["stale_events_filtered"] == 1
    assert feed["items"] == []
    gc.collect()


def test_current_match_kill_feed_marks_fresh_recent_fallback_rows_partial(tmp_path):
    db_path = tmp_path / "admin_log.sqlite3"
    persist_rcon_admin_log_entries(
        target=TARGET,
        entries=[
            {
                "timestamp": "2026-05-21T09:50:00Z",
                "message": (
                    "[1:00 min (1779357000)] KILL: Fresh Killer(Allies/steam-fresh) -> "
                    "Fresh Victim(Axis/steam-victim-fresh) with M1 GARAND"
                ),
            }
        ],
        db_path=db_path,
    )

    feed = list_current_match_kill_feed(
        server_key="test-rcon-target",
        db_path=db_path,
        now=datetime(2026, 5, 21, 10, 0, tzinfo=timezone.utc),
    )

    assert feed["scope"] == "recent-admin-log-window"
    assert feed["confidence"] == "partial"
    assert feed["stale_events_filtered"] == 0
    assert [item["killer_name"] for item in feed["items"]] == ["Fresh Killer"]
    gc.collect()
