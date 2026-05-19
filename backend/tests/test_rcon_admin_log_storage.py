import gc
import sqlite3

from app.rcon_admin_log_storage import (
    initialize_rcon_admin_log_storage,
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
