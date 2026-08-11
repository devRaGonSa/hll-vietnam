from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from scripts.audit_rcon_match_materialization import (
    ReadOnlyDatabase,
    TargetResolver,
    audit_scoreboard_parity,
    audit_requested_event_range,
    assert_public_result_is_sanitized,
    bound_class,
    build_match_key,
    candidate_score,
    canonicalize_admin_message,
    classify_parser_signature,
    count_ordered_boundary_pairs,
    derive_admin_matches,
    duration_seconds,
    ensure_read_only_sql,
    match_time_bounds,
    mutual_unique_best_assignments,
    open_sqlite_read_only,
    scan_target_events,
    server_time_timestamp,
)


def _resolver() -> TargetResolver:
    return TargetResolver(
        key_to_slug={"target-01": "comunidad-hispana-01"},
        target_id_to_slug={},
        target_id_to_key={},
        historical_server_id_to_slug={},
    )


def _boundary(
    event_id: int,
    event_type: str,
    server_time: int,
    *,
    map_name: str = "Carentan Warfare",
) -> dict[str, object]:
    payload = (
        f'{{"map_name": "{map_name}", "game_mode": "Warfare"}}'
        if event_type == "match_start"
        else f'{{"map_name": "{map_name}", "allied_score": 5, "axis_score": 3}}'
    )
    return {
        "id": event_id,
        "target_key": "target-01",
        "external_server_id": "comunidad-hispana-01",
        "event_timestamp": f"2026-01-01T00:{event_id:02d}:00Z",
        "server_time": server_time,
        "event_type": event_type,
        "parsed_payload_json": payload,
        "canonical_message": f"boundary-{event_id}",
        "created_at": f"2026-01-01T00:{event_id:02d}:01Z",
    }


def test_read_only_sql_guard_rejects_mutation() -> None:
    ensure_read_only_sql("SELECT 1")
    ensure_read_only_sql("WITH sample AS (SELECT 1) SELECT * FROM sample")
    ensure_read_only_sql("PRAGMA index_list(rcon_admin_log_events)")
    with pytest.raises(ValueError, match="mutating SQL"):
        ensure_read_only_sql("CREATE TEMP TABLE audit_rows(id INTEGER)")
    with pytest.raises(ValueError, match="mutating SQL"):
        ensure_read_only_sql("SELECT 1; DELETE FROM events")
    with pytest.raises(ValueError, match="non-metadata PRAGMA"):
        ensure_read_only_sql("PRAGMA writable_schema = ON")
    with pytest.raises(ValueError, match="multiple SQL statements"):
        ensure_read_only_sql("SELECT 1; SELECT 2")


def test_boundary_state_machine_covers_normal_orphan_and_final_open() -> None:
    rows = [
        _boundary(1, "match_start", 10),
        _boundary(2, "match_end", 20),
        _boundary(3, "match_end", 30),
        _boundary(4, "match_start", 40),
    ]
    derived, summary = derive_admin_matches(
        rows,
        _resolver(),
        {"comunidad-hispana-01"},
    )
    assert [bound_class(match) for match in derived] == [
        "both_bounds",
        "upper_only",
        "lower_only",
    ]
    server_summary = summary["comunidad-hispana-01"]
    assert server_summary["normal_start_end"] == 1
    assert server_summary["orphan_end"] == 1
    assert server_summary["final_open_start"] == 1
    assert set(server_summary["sanitized_examples"]) == {
        "orphan_end",
        "final_open_start",
    }


def test_consecutive_start_emits_lower_only_partial() -> None:
    rows = [
        _boundary(1, "match_start", 10),
        _boundary(2, "match_start", 20),
        _boundary(3, "match_end", 30),
    ]
    derived, summary = derive_admin_matches(rows, _resolver(), {"comunidad-hispana-01"})
    assert [bound_class(match) for match in derived] == ["lower_only", "both_bounds"]
    assert summary["comunidad-hispana-01"]["consecutive_start"] == 1


def test_postgres_boundary_order_places_null_server_time_last() -> None:
    rows = [
        {**_boundary(1, "match_start", 0), "server_time": None},
        _boundary(2, "match_end", 10),
    ]
    derived, _ = derive_admin_matches(
        rows,
        _resolver(),
        {"comunidad-hispana-01"},
        nulls_last=True,
    )
    assert [bound_class(match) for match in derived] == ["upper_only", "no_bounds"]


def test_match_key_preserves_missing_and_open_semantics() -> None:
    assert build_match_key("target-01", None, 20, "Carentan Warfare") == (
        "target-01:missing:20:carentanwarfare"
    )


def test_duration_prefers_server_time_bounds_over_poll_timestamp() -> None:
    assert duration_seconds(
        {
            "started_server_time": 100,
            "ended_server_time": 3700,
            "started_at": "2026-01-01T10:00:00Z",
            "ended_at": "2026-01-01T10:00:00Z",
        }
    ) == 3600
    assert build_match_key("target-01", 10, None, "Carentan Warfare") == (
        "target-01:10:open:carentanwarfare"
    )


def test_event_sweep_uses_inclusive_bounds_and_counts_overlap() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute(
        "CREATE TABLE rcon_admin_log_events "
        "(id INTEGER, target_key TEXT, server_time INTEGER, event_type TEXT)"
    )
    connection.executemany(
        "INSERT INTO rcon_admin_log_events VALUES (?, ?, ?, ?)",
        [
            (1, "target-01", 10, "kill"),
            (2, "target-01", 20, "kill"),
            (3, "target-01", 30, "kill"),
        ],
    )
    database = ReadOnlyDatabase(connection, "sqlite", "fixture")
    matches = [
        {
            "match_key": "bounded",
            "started_server_time": 10,
            "ended_server_time": 20,
        },
        {
            "match_key": "open",
            "started_server_time": 20,
            "ended_server_time": None,
        },
    ]
    metrics, overlap = scan_target_events(database, "target-01", matches)
    assert metrics["bounded"]["selected_kills"] == 2
    assert metrics["open"]["selected_kills"] == 2
    assert overlap["kill_assigned_many"] == 1
    assert overlap["maximum_multiplicity"] == 2
    connection.close()


def test_requested_date_range_filters_adminlog_inventory() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute(
        "CREATE TABLE rcon_admin_log_events "
        "(target_key TEXT, external_server_id TEXT, event_timestamp TEXT, event_type TEXT)"
    )
    connection.executemany(
        "INSERT INTO rcon_admin_log_events VALUES (?, ?, ?, ?)",
        [
            ("target-01", "comunidad-hispana-01", "2026-01-01T00:00:00Z", "kill"),
            ("target-01", "comunidad-hispana-01", "2026-01-02T00:00:00Z", "match_start"),
        ],
    )
    database = ReadOnlyDatabase(connection, "sqlite", "fixture")
    result = audit_requested_event_range(
        database,
        _resolver(),
        {"comunidad-hispana-01"},
        datetime(2026, 1, 2, tzinfo=timezone.utc),
        None,
    )
    assert result is not None
    assert result["comunidad-hispana-01"]["total_events"] == 1
    assert result["comunidad-hispana-01"]["match_start"] == 1
    connection.close()


def test_parser_signatures_never_return_message_content() -> None:
    signatures = classify_parser_signature(
        " [ (100)] team kill: private content",
        "TEAM KILL: private content",
    )
    assert "leading-whitespace" in signatures
    assert "prefix-not-recognized" in signatures
    assert "explicit-team-kill" in signatures
    assert all("private" not in signature for signature in signatures)
    assert canonicalize_admin_message("  [1:00 (100)] TEAM KILL: redacted  ") == (
        "TEAM KILL: redacted"
    )


def test_public_result_guard_rejects_sensitive_fields_and_dsn() -> None:
    assert_public_result_is_sanitized(
        {"server": "comunidad-hispana-01", "max_player_kills": 300}
    )
    with pytest.raises(ValueError, match="sensitive output key"):
        assert_public_result_is_sanitized({"raw_message": "secret"})
    with pytest.raises(ValueError, match="connection string"):
        assert_public_result_is_sanitized({"source": "postgresql://user:password@example/db"})


def test_scoreboard_candidate_requires_map_and_strong_time_evidence() -> None:
    rcon = {
        "map_name": "Carentan Warfare",
        "started_at": "2026-01-01T10:00:00Z",
        "ended_at": "2026-01-01T11:00:00Z",
        "allied_score": 5,
        "axis_score": 3,
    }
    scoreboard = {
        "map_name": "Carentan",
        "started_at": "2026-01-01T10:01:00Z",
        "ended_at": "2026-01-01T11:01:00Z",
        "allied_score": 5,
        "axis_score": 3,
    }
    assert candidate_score(rcon, scoreboard) is not None
    assert candidate_score(rcon, {**scoreboard, "map_name": "Utah Beach"}) is None


def test_match_correlation_prefers_plausible_server_time_over_batch_time() -> None:
    start = int(datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc).timestamp())
    end = int(datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc).timestamp())
    rcon = {
        "map_name": "Carentan Warfare",
        "started_server_time": start,
        "ended_server_time": end,
        "started_at": "2026-01-02T10:00:00Z",
        "ended_at": "2026-01-02T11:00:00Z",
        "allied_score": 5,
        "axis_score": 3,
    }
    scoreboard = {
        "map_name": "Carentan",
        "started_at": "2026-01-01T10:01:00Z",
        "ended_at": "2026-01-01T11:01:00Z",
        "allied_score": 5,
        "axis_score": 3,
    }
    assert match_time_bounds(rcon) == (
        datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc),
    )
    assert candidate_score(rcon, scoreboard) is not None
    assert server_time_timestamp(42) is None


def test_scoreboard_parity_filters_rcon_coverage_with_server_time() -> None:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE historical_servers (id INTEGER PRIMARY KEY, slug TEXT);
        CREATE TABLE historical_matches (
            id INTEGER PRIMARY KEY,
            historical_server_id INTEGER,
            started_at TEXT,
            ended_at TEXT,
            map_name TEXT,
            map_pretty_name TEXT,
            game_mode TEXT,
            allied_score INTEGER,
            axis_score INTEGER
        );
        INSERT INTO historical_servers VALUES (1, 'comunidad-hispana-01');
        INSERT INTO historical_matches VALUES (
            1, 1, '2026-01-01T10:00:00Z', '2026-01-01T11:00:00Z',
            'Carentan Warfare', 'Carentan', 'Warfare', 5, 3
        );
        """
    )
    start = int(datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc).timestamp())
    end = int(datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc).timestamp())
    derived = [
        {
            "target_key": "target-01",
            "external_server_id": "comunidad-hispana-01",
            "match_key": "match-1",
            "map_name": "Carentan Warfare",
            "started_server_time": start,
            "ended_server_time": end,
            "started_at": "2026-01-02T10:00:00Z",
            "ended_at": "2026-01-02T11:00:00Z",
            "allied_score": 5,
            "axis_score": 3,
        }
    ]

    result = audit_scoreboard_parity(
        ReadOnlyDatabase(connection, "sqlite", "fixture"),
        _resolver(),
        {"comunidad-hispana-01"},
        derived,
        [],
    )

    server = result["comunidad-hispana-01"]
    assert server["rcon_matches_in_overlap"] == 1
    assert server["classifications"]["exact_rcon_match"] == 1
    connection.close()


def test_scoreboard_assignment_requires_mutual_unique_best() -> None:
    exact, ambiguous = mutual_unique_best_assignments(
        {
            0: [(10, "rcon-a")],
            1: [(9, "rcon-a")],
            2: [(8, "rcon-b"), (8, "rcon-c")],
        }
    )
    assert exact == {0: "rcon-a"}
    assert ambiguous == {1: {"rcon-a"}, 2: {"rcon-b", "rcon-c"}}


def test_window_boundary_pairs_require_ordered_start_then_end() -> None:
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    boundaries = [
        (base, 1, "match_end"),
        (base, 2, "match_start"),
        (base, 3, "match_start"),
        (base, 4, "match_end"),
        (base, 5, "match_end"),
    ]
    assert count_ordered_boundary_pairs(boundaries) == 1


def test_sqlite_readonly_adapter_does_not_change_snapshot(tmp_path: Path) -> None:
    path = tmp_path / "audit.sqlite3"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE evidence(id INTEGER PRIMARY KEY)")
    connection.execute("INSERT INTO evidence VALUES (1)")
    connection.commit()
    connection.close()
    before = (path.stat().st_size, path.stat().st_mtime_ns, hashlib_sha256(path))
    database = open_sqlite_read_only(path, immutable=True)
    assert database.execute("SELECT COUNT(*) FROM evidence").fetchone()[0] == 1
    database.close()
    after = (path.stat().st_size, path.stat().st_mtime_ns, hashlib_sha256(path))
    assert after == before


def hashlib_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
