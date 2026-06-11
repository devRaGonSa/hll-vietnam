"""Materialize RCON AdminLog events into match and player-stat read models."""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from collections.abc import Iterable
from contextlib import closing
from pathlib import Path

from .config import get_storage_path, use_postgres_rcon_storage
from .normalizers import normalize_map_name
from .rcon_admin_log_storage import initialize_rcon_admin_log_storage
from .rcon_historical_storage import list_rcon_historical_competitive_windows
from .sqlite_utils import connect_sqlite_readonly, connect_sqlite_writer


MATCH_RESULT_SOURCE = "admin-log-match-ended"
SESSION_RESULT_SOURCE = "rcon-session"


def initialize_rcon_materialized_storage(*, db_path: Path | None = None) -> Path:
    """Create SQLite structures used by the materialized RCON match pipeline."""
    if use_postgres_rcon_storage(explicit_sqlite_path=db_path):
        from .postgres_rcon_storage import initialize_postgres_rcon_storage

        initialize_postgres_rcon_storage()
        return get_storage_path()

    resolved_path = initialize_rcon_admin_log_storage(db_path=db_path)
    with closing(connect_sqlite_writer(resolved_path)) as connection:
        with connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS rcon_materialized_matches (
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

                CREATE INDEX IF NOT EXISTS idx_rcon_materialized_matches_recent
                ON rcon_materialized_matches(target_key, ended_at DESC, ended_server_time DESC);

                CREATE INDEX IF NOT EXISTS idx_rcon_materialized_matches_source_window_text
                ON rcon_materialized_matches(
                    source_basis,
                    COALESCE(CAST(ended_at AS TEXT), CAST(started_at AS TEXT))
                );

                CREATE INDEX IF NOT EXISTS idx_rcon_materialized_matches_target_source_window_text
                ON rcon_materialized_matches(
                    target_key,
                    source_basis,
                    COALESCE(CAST(ended_at AS TEXT), CAST(started_at AS TEXT))
                );

                CREATE INDEX IF NOT EXISTS idx_rcon_materialized_matches_external_source_window_text
                ON rcon_materialized_matches(
                    external_server_id,
                    source_basis,
                    COALESCE(CAST(ended_at AS TEXT), CAST(started_at AS TEXT))
                );

                CREATE TABLE IF NOT EXISTS rcon_match_player_stats (
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
                    player_active_seconds INTEGER,
                    active_time_source TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(target_key, match_key, player_id)
                );

                CREATE INDEX IF NOT EXISTS idx_rcon_match_player_stats_match
                ON rcon_match_player_stats(target_key, match_key);

                CREATE INDEX IF NOT EXISTS idx_rcon_match_player_stats_player_id_match
                ON rcon_match_player_stats(player_id, target_key, match_key);

                CREATE TABLE IF NOT EXISTS rcon_annual_ranking_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    year INTEGER NOT NULL,
                    server_key TEXT NOT NULL,
                    metric TEXT NOT NULL,
                    limit_size INTEGER NOT NULL DEFAULT 20,
                    source_basis TEXT NOT NULL DEFAULT 'rcon-admin-log',
                    window_start TEXT,
                    window_end TEXT,
                    generated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    status TEXT NOT NULL DEFAULT 'ready',
                    source_matches_count INTEGER NOT NULL DEFAULT 0,
                    CHECK (limit_size > 0),
                    CHECK (metric IN ('kills', 'deaths', 'teamkills', 'matches_considered', 'kd_ratio', 'kills_per_match')),
                    UNIQUE (year, server_key, metric)
                );

                CREATE INDEX IF NOT EXISTS idx_rcon_annual_ranking_snapshots_year
                ON rcon_annual_ranking_snapshots(year, server_key, metric);

                CREATE INDEX IF NOT EXISTS idx_rcon_annual_ranking_snapshots_status
                ON rcon_annual_ranking_snapshots(status);

                CREATE TABLE IF NOT EXISTS rcon_annual_ranking_snapshot_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_id INTEGER NOT NULL REFERENCES rcon_annual_ranking_snapshots(id) ON DELETE CASCADE,
                    ranking_position INTEGER NOT NULL,
                    player_id TEXT NOT NULL,
                    player_name TEXT NOT NULL,
                    metric_value REAL NOT NULL DEFAULT 0,
                    matches_considered INTEGER NOT NULL DEFAULT 0,
                    kills INTEGER NOT NULL DEFAULT 0,
                    deaths INTEGER NOT NULL DEFAULT 0,
                    teamkills INTEGER NOT NULL DEFAULT 0,
                    kd_ratio REAL NOT NULL DEFAULT 0.0,
                    UNIQUE(snapshot_id, ranking_position),
                    UNIQUE(snapshot_id, player_id)
                );

                CREATE INDEX IF NOT EXISTS idx_rcon_annual_snapshot_items_snapshot
                ON rcon_annual_ranking_snapshot_items(snapshot_id, ranking_position);

                CREATE INDEX IF NOT EXISTS idx_rcon_annual_snapshot_items_player
                ON rcon_annual_ranking_snapshot_items(snapshot_id, player_id);
                """
            )
            _ensure_materialized_player_stat_columns(connection)
    return resolved_path


def materialize_rcon_admin_log(*, db_path: Path | None = None) -> dict[str, object]:
    """Materialize matches and player stats from stored AdminLog events."""
    resolved_path = initialize_rcon_materialized_storage(db_path=db_path)
    if use_postgres_rcon_storage(explicit_sqlite_path=db_path):
        from .postgres_rcon_storage import connect_postgres_compat

        with connect_postgres_compat() as connection:
            payload = _materialize_rcon_admin_log_with_connection(
                connection,
                session_window_db_path=None,
                caught_errors=(Exception,),
            )
        freshness = summarize_rcon_materialization_status()
        return {
            **payload,
            "latest_materialized_matches": freshness["latest_materialized_matches"],
            "latest_admin_log_match_end_events": freshness["latest_admin_log_match_end_events"],
            "match_end_status": freshness["match_end_status"],
        }

    with closing(connect_sqlite_writer(resolved_path)) as connection:
        with connection:
            payload = _materialize_rcon_admin_log_with_connection(
                connection,
                session_window_db_path=resolved_path,
                caught_errors=(sqlite3.Error,),
            )

    freshness = summarize_rcon_materialization_status(db_path=resolved_path)
    return {
        **payload,
        "latest_materialized_matches": freshness["latest_materialized_matches"],
        "latest_admin_log_match_end_events": freshness["latest_admin_log_match_end_events"],
        "match_end_status": freshness["match_end_status"],
    }


def _materialize_rcon_admin_log_with_connection(
    connection: object,
    *,
    session_window_db_path: Path | None,
    caught_errors: tuple[type[BaseException], ...],
) -> dict[str, object]:
    errors: list[str] = []
    matches_seen = 0
    matches_materialized = 0
    matches_updated = 0
    player_stats_seen = 0
    player_stats_materialized = 0
    player_stats_updated = 0

    try:
        match_rows = _derive_admin_log_matches(connection)
        matches_seen = len(match_rows)
        for row in match_rows:
            outcome = _upsert_match(connection, row)
            matches_materialized += int(outcome == "inserted")
            matches_updated += int(outcome == "updated")
        session_rows = _derive_session_fallback_matches(
            connection,
            db_path=session_window_db_path,
        )
        matches_seen += len(session_rows)
        for row in session_rows:
            outcome = _upsert_match(connection, row)
            matches_materialized += int(outcome == "inserted")
            matches_updated += int(outcome == "updated")

        persisted_matches = _list_materialized_matches(connection)
        for match in persisted_matches:
            stats = _derive_player_stats_for_match(connection, match)
            player_stats_seen += len(stats)
            connection.execute(
                """
                DELETE FROM rcon_match_player_stats
                WHERE target_key = ? AND match_key = ?
                """,
                (match["target_key"], match["match_key"]),
            )
            for stat in stats:
                _insert_player_stat(connection, stat)
                player_stats_materialized += 1
    except caught_errors as error:
        errors.append(str(error))
    return {
        "matches_seen": matches_seen,
        "matches_materialized": matches_materialized,
        "matches_updated": matches_updated,
        "player_stats_seen": player_stats_seen,
        "player_stats_materialized": player_stats_materialized,
        "player_stats_updated": player_stats_updated,
        "errors": errors,
    }


def list_materialized_rcon_matches(
    *,
    target_key: str | None = None,
    only_ended: bool = False,
    limit: int = 20,
    db_path: Path | None = None,
) -> list[dict[str, object]]:
    """Return recent materialized RCON matches."""
    resolved_path = initialize_rcon_materialized_storage(db_path=db_path)
    clauses: list[str] = []
    params: list[object] = []
    if target_key:
        clauses.append("(m.target_key = ? OR m.external_server_id = ?)")
        params.extend([target_key, target_key])
    if only_ended:
        clauses.append("m.source_basis = ?")
        params.append(MATCH_RESULT_SOURCE)
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    params.append(limit)
    if use_postgres_rcon_storage(explicit_sqlite_path=db_path):
        from .postgres_rcon_storage import connect_postgres_compat

        connection_scope = connect_postgres_compat()
    else:
        connection_scope = closing(connect_sqlite_readonly(resolved_path))
    with connection_scope as connection:
        rows = connection.execute(
            f"""
            SELECT
                m.*,
                (
                    SELECT COUNT(*)
                    FROM rcon_match_player_stats AS stats
                    WHERE stats.target_key = m.target_key
                      AND stats.match_key = m.match_key
                ) AS materialized_player_count,
                (
                    SELECT COUNT(DISTINCT TRIM(stats.player_name))
                    FROM rcon_match_player_stats AS stats
                    WHERE stats.target_key = m.target_key
                      AND stats.match_key = m.match_key
                      AND TRIM(COALESCE(stats.player_name, '')) != ''
                ) AS materialized_distinct_player_count
            FROM rcon_materialized_matches AS m
            {where}
            ORDER BY COALESCE(m.ended_at, m.started_at) DESC,
                     COALESCE(m.ended_server_time, m.started_server_time) DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def get_materialized_rcon_match_detail(
    *,
    server_key: str,
    match_key: str,
    db_path: Path | None = None,
    ensure_storage: bool = False,
) -> dict[str, object] | None:
    """Return one materialized match with player stats."""
    resolved_path = (
        initialize_rcon_materialized_storage(db_path=db_path)
        if ensure_storage
        else (db_path or get_storage_path())
    )
    if use_postgres_rcon_storage(explicit_sqlite_path=db_path):
        from .postgres_rcon_storage import connect_postgres_compat

        connection_scope = connect_postgres_compat(initialize=ensure_storage)
    else:
        connection_scope = closing(connect_sqlite_readonly(resolved_path))
    try:
        with connection_scope as connection:
            match = connection.execute(
                """
                SELECT *
                FROM rcon_materialized_matches
                WHERE match_key = ?
                  AND (target_key = ? OR external_server_id = ?)
                LIMIT 1
                """,
                (match_key, server_key, server_key),
            ).fetchone()
            if match is None and match_key.startswith(f"{server_key}:"):
                match = connection.execute(
                    """
                    SELECT *
                    FROM rcon_materialized_matches
                    WHERE match_key = ?
                    LIMIT 1
                    """,
                    (match_key,),
                ).fetchone()
            if match is None:
                return None
            stat_rows = connection.execute(
                """
                SELECT *
                FROM rcon_match_player_stats
                WHERE target_key = ? AND match_key = ?
                ORDER BY kills DESC, deaths ASC, player_name ASC
                """,
                (match["target_key"], match["match_key"]),
            ).fetchall()
            timeline_rows = connection.execute(
                """
                SELECT event_type, COUNT(*) AS event_count
                FROM rcon_admin_log_events
                WHERE target_key = ?
                  AND server_time IS NOT NULL
                  AND (? IS NULL OR server_time >= ?)
                  AND (? IS NULL OR server_time <= ?)
                GROUP BY event_type
                ORDER BY event_count DESC, event_type ASC
                """,
                (
                    match["target_key"],
                    match["started_server_time"],
                    match["started_server_time"],
                    match["ended_server_time"],
                    match["ended_server_time"],
                ),
            ).fetchall()
    except Exception:
        return None

    return {
        "match": dict(match),
        "players": [dict(row) for row in stat_rows],
        "timeline": [dict(row) for row in timeline_rows],
    }


def summarize_rcon_materialization_status(*, db_path: Path | None = None) -> dict[str, object]:
    """Return a small diagnostic summary for stored RCON materialization state."""
    resolved_path = initialize_rcon_materialized_storage(db_path=db_path)
    if use_postgres_rcon_storage(explicit_sqlite_path=db_path):
        from .postgres_rcon_storage import connect_postgres_compat

        connection_scope = connect_postgres_compat()
    else:
        connection_scope = closing(connect_sqlite_readonly(resolved_path))
    with connection_scope as connection:
        match_count = connection.execute(
            "SELECT COUNT(*) AS count FROM rcon_materialized_matches"
        ).fetchone()["count"]
        stats_match_count = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM (
                SELECT 1
                FROM rcon_match_player_stats
                GROUP BY target_key, match_key
            ) AS stats_matches
            """
        ).fetchone()["count"]
        ranges = connection.execute(
            """
            SELECT target_key, MIN(server_time) AS first_server_time, MAX(server_time) AS last_server_time
            FROM rcon_admin_log_events
            GROUP BY target_key
            ORDER BY target_key ASC
            """
        ).fetchall()
        event_counts = connection.execute(
            """
            SELECT target_key, event_type, COUNT(*) AS event_count
            FROM rcon_admin_log_events
            GROUP BY target_key, event_type
            ORDER BY target_key ASC, event_count DESC
            """
        ).fetchall()
        latest_matches = connection.execute(
            """
            SELECT
                target_key,
                external_server_id,
                match_key,
                map_pretty_name,
                COALESCE(ended_at, started_at) AS closed_at,
                ended_at,
                ended_server_time,
                source_basis,
                updated_at
            FROM (
                SELECT
                    *,
                    ROW_NUMBER() OVER (
                        PARTITION BY target_key
                        ORDER BY COALESCE(ended_at, started_at) DESC,
                                 COALESCE(ended_server_time, started_server_time) DESC,
                                 updated_at DESC
                    ) AS row_number
                FROM rcon_materialized_matches
                WHERE source_basis = ?
            ) AS ranked_matches
            WHERE row_number = 1
            ORDER BY target_key ASC
            """,
            (MATCH_RESULT_SOURCE,),
        ).fetchall()
        latest_match_end_events = connection.execute(
            """
            SELECT
                target_key,
                external_server_id,
                MAX(event_timestamp) AS latest_event_timestamp,
                MAX(server_time) AS latest_server_time,
                COUNT(*) AS match_end_events
            FROM rcon_admin_log_events
            WHERE event_type = 'match_end'
            GROUP BY target_key, external_server_id
            ORDER BY target_key ASC
            """
        ).fetchall()
    return {
        "materialized_matches": int(match_count or 0),
        "matches_with_player_stats": int(stats_match_count or 0),
        "server_time_ranges": [dict(row) for row in ranges],
        "event_counts": [dict(row) for row in event_counts],
        "latest_materialized_matches": [dict(row) for row in latest_matches],
        "latest_admin_log_match_end_events": [dict(row) for row in latest_match_end_events],
        "match_end_status": (
            "admin-log-match-end-events-available"
            if latest_match_end_events
            else "no-admin-log-match-end-events-stored"
        ),
    }


def _derive_admin_log_matches(connection: sqlite3.Connection) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT *
        FROM rcon_admin_log_events
        WHERE event_type IN ('match_start', 'match_end')
        ORDER BY target_key ASC, server_time ASC, id ASC
        """
    ).fetchall()
    matches: list[dict[str, object]] = []
    open_by_target: dict[str, sqlite3.Row] = {}
    for row in rows:
        target_key = row["target_key"]
        payload = _json_object(row["parsed_payload_json"])
        if row["event_type"] == "match_start":
            if target_key in open_by_target:
                matches.append(_build_match_row(open_by_target.pop(target_key), None))
            open_by_target[target_key] = row
            continue
        start_row = open_by_target.pop(target_key, None)
        matches.append(_build_match_row(start_row, row, end_payload=payload))
    for start_row in open_by_target.values():
        matches.append(_build_match_row(start_row, None))
    return matches


def _derive_session_fallback_matches(
    connection: sqlite3.Connection,
    *,
    db_path: Path | None,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    existing = {
        (row["target_key"], normalize_map_name(row["map_pretty_name"] or row["map_name"]))
        for row in connection.execute(
            """
            SELECT target_key, map_name, map_pretty_name
            FROM rcon_materialized_matches
            WHERE source_basis = ?
            """,
            (MATCH_RESULT_SOURCE,),
        ).fetchall()
    }
    for window in list_rcon_historical_competitive_windows(limit=100, db_path=db_path):
        target_key = str(window.get("target_key") or "")
        map_name = window.get("map_pretty_name") or window.get("map_name")
        if (target_key, normalize_map_name(map_name)) in existing:
            continue
        session_key = str(window.get("session_key") or "").strip()
        if not target_key or not session_key:
            continue
        rows.append(
            {
                "target_key": target_key,
                "external_server_id": window.get("external_server_id"),
                "match_key": f"session:{session_key}",
                "map_name": window.get("map_name"),
                "map_pretty_name": normalize_map_name(map_name),
                "game_mode": None,
                "started_server_time": None,
                "ended_server_time": None,
                "started_at": window.get("first_seen_at"),
                "ended_at": window.get("last_seen_at"),
                "allied_score": _nested_int(window.get("latest_payload"), "allied_score"),
                "axis_score": _nested_int(window.get("latest_payload"), "axis_score"),
                "winner": _resolve_winner(
                    _nested_int(window.get("latest_payload"), "allied_score"),
                    _nested_int(window.get("latest_payload"), "axis_score"),
                ),
                "confidence_mode": "partial",
                "source_basis": SESSION_RESULT_SOURCE,
            }
        )
    return rows


def _build_match_row(
    start_row: sqlite3.Row | None,
    end_row: sqlite3.Row | None,
    *,
    end_payload: dict[str, object] | None = None,
) -> dict[str, object]:
    start_payload = _json_object(start_row["parsed_payload_json"]) if start_row else {}
    end_payload = end_payload or (_json_object(end_row["parsed_payload_json"]) if end_row else {})
    target_key = str((end_row or start_row)["target_key"])
    external_server_id = (end_row or start_row)["external_server_id"]
    started_server_time = start_row["server_time"] if start_row else None
    ended_server_time = end_row["server_time"] if end_row else None
    map_name = end_payload.get("map_name") or start_payload.get("map_name")
    match_key = _build_match_key(
        target_key=target_key,
        started_server_time=started_server_time,
        ended_server_time=ended_server_time,
        map_name=map_name,
    )
    return {
        "target_key": target_key,
        "external_server_id": external_server_id,
        "match_key": match_key,
        "map_name": map_name,
        "map_pretty_name": normalize_map_name(map_name),
        "game_mode": start_payload.get("game_mode"),
        "started_server_time": started_server_time,
        "ended_server_time": ended_server_time,
        "started_at": start_row["event_timestamp"] if start_row else None,
        "ended_at": end_row["event_timestamp"] if end_row else None,
        "allied_score": _coerce_int(end_payload.get("allied_score")),
        "axis_score": _coerce_int(end_payload.get("axis_score")),
        "winner": end_payload.get("winner")
        or _resolve_winner(
            _coerce_int(end_payload.get("allied_score")),
            _coerce_int(end_payload.get("axis_score")),
        ),
        "confidence_mode": "exact" if end_row else "partial",
        "source_basis": MATCH_RESULT_SOURCE if end_row else "admin-log-match-start",
    }


def _upsert_match(connection: sqlite3.Connection, row: dict[str, object]) -> str:
    existing = connection.execute(
        """
        SELECT id
        FROM rcon_materialized_matches
        WHERE target_key = ? AND match_key = ?
        """,
        (row["target_key"], row["match_key"]),
    ).fetchone()
    connection.execute(
        """
        INSERT INTO rcon_materialized_matches (
            target_key, external_server_id, match_key, map_name, map_pretty_name, game_mode,
            started_server_time, ended_server_time, started_at, ended_at,
            allied_score, axis_score, winner, confidence_mode, source_basis
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(target_key, match_key) DO UPDATE SET
            external_server_id = excluded.external_server_id,
            map_name = excluded.map_name,
            map_pretty_name = excluded.map_pretty_name,
            game_mode = excluded.game_mode,
            started_server_time = excluded.started_server_time,
            ended_server_time = excluded.ended_server_time,
            started_at = excluded.started_at,
            ended_at = excluded.ended_at,
            allied_score = excluded.allied_score,
            axis_score = excluded.axis_score,
            winner = excluded.winner,
            confidence_mode = excluded.confidence_mode,
            source_basis = excluded.source_basis,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            row["target_key"],
            row.get("external_server_id"),
            row["match_key"],
            row.get("map_name"),
            row.get("map_pretty_name"),
            row.get("game_mode"),
            row.get("started_server_time"),
            row.get("ended_server_time"),
            row.get("started_at"),
            row.get("ended_at"),
            row.get("allied_score"),
            row.get("axis_score"),
            row.get("winner"),
            row["confidence_mode"],
            row["source_basis"],
        ),
    )
    return "updated" if existing else "inserted"


def _list_materialized_matches(connection: sqlite3.Connection) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT *
        FROM rcon_materialized_matches
        WHERE started_server_time IS NOT NULL OR ended_server_time IS NOT NULL
        ORDER BY target_key ASC, COALESCE(started_server_time, ended_server_time) ASC
        """
    ).fetchall()
    return [dict(row) for row in rows]


def _derive_player_stats_for_match(
    connection: sqlite3.Connection,
    match: dict[str, object],
) -> list[dict[str, object]]:
    lower = match.get("started_server_time")
    upper = match.get("ended_server_time")
    if lower is None and upper is None:
        return []
    clauses = ["target_key = ?", "server_time IS NOT NULL"]
    params: list[object] = [match["target_key"]]
    if lower is not None:
        clauses.append("server_time >= ?")
        params.append(lower)
    if upper is not None:
        clauses.append("server_time <= ?")
        params.append(upper)
    rows = connection.execute(
        f"""
        SELECT *
        FROM rcon_admin_log_events
        WHERE {" AND ".join(clauses)}
          AND event_type IN ('kill', 'team_switch', 'connected', 'disconnected', 'chat')
        ORDER BY server_time ASC, id ASC
        """,
        params,
    ).fetchall()

    players: dict[str, dict[str, object]] = {}
    team_by_player: dict[str, str] = {}
    for row in rows:
        payload = _json_object(row["parsed_payload_json"])
        server_time = _coerce_int(row["server_time"])
        event_type = row["event_type"]
        if event_type == "kill":
            killer_key = _player_key(payload.get("killer_id"), payload.get("killer_name"))
            victim_key = _player_key(payload.get("victim_id"), payload.get("victim_name"))
            killer = _ensure_player(
                players,
                player_id=killer_key,
                player_name=payload.get("killer_name"),
                team=payload.get("killer_team") or team_by_player.get(killer_key),
                server_time=server_time,
            )
            victim = _ensure_player(
                players,
                player_id=victim_key,
                player_name=payload.get("victim_name"),
                team=payload.get("victim_team") or team_by_player.get(victim_key),
                server_time=server_time,
            )
            team_by_player[killer_key] = str(payload.get("killer_team") or killer.get("team") or "")
            team_by_player[victim_key] = str(payload.get("victim_team") or victim.get("team") or "")
            weapon = str(payload.get("weapon") or "Unknown")
            same_team = payload.get("killer_team") and payload.get("killer_team") == payload.get("victim_team")
            if same_team:
                killer["teamkills"] = int(killer["teamkills"]) + 1
                victim["deaths_by_teamkill"] = int(victim["deaths_by_teamkill"]) + 1
            else:
                killer["kills"] = int(killer["kills"]) + 1
            victim["deaths"] = int(victim["deaths"]) + 1
            _counter(killer, "weapons")[weapon] += 1
            _counter(victim, "death_by_weapons")[weapon] += 1
            _counter(killer, "most_killed")[str(victim["player_name"])] += 1
            _counter(victim, "death_by")[str(killer["player_name"])] += 1
            _touch_player(killer, server_time)
            _touch_player(victim, server_time)
            continue

        if event_type == "team_switch" and not payload.get("player_id"):
            continue
        player_id = _player_key(payload.get("player_id"), payload.get("player_name"))
        team = payload.get("to_team") or payload.get("chat_team") or team_by_player.get(player_id)
        player = _ensure_player(
            players,
            player_id=player_id,
            player_name=payload.get("player_name"),
            team=team,
            server_time=server_time,
        )
        if team:
            player["team"] = team
            team_by_player[player_id] = str(team)
        _touch_player(player, server_time)

    stats = []
    for player in players.values():
        active_time = _build_player_active_time_payload(
            connection,
            match=match,
            player=player,
            match_rows=rows,
        )
        stats.append(
            {
                "target_key": match["target_key"],
                "match_key": match["match_key"],
                "player_id": player["player_id"],
                "player_name": player["player_name"],
                "team": player.get("team"),
                "kills": player["kills"],
                "deaths": player["deaths"],
                "teamkills": player["teamkills"],
                "deaths_by_teamkill": player["deaths_by_teamkill"],
                "weapons_json": _dump_counter(player["weapons"]),
                "death_by_weapons_json": _dump_counter(player["death_by_weapons"]),
                "most_killed_json": _dump_counter(player["most_killed"]),
                "death_by_json": _dump_counter(player["death_by"]),
                "first_seen_server_time": player.get("first_seen_server_time"),
                "last_seen_server_time": player.get("last_seen_server_time"),
                "player_active_seconds": active_time["player_active_seconds"],
                "active_time_source": active_time["active_time_source"],
            }
        )
    return stats


def _insert_player_stat(connection: sqlite3.Connection, stat: dict[str, object]) -> None:
    connection.execute(
        """
        INSERT INTO rcon_match_player_stats (
            target_key, match_key, player_id, player_name, team,
            kills, deaths, teamkills, deaths_by_teamkill,
            weapons_json, death_by_weapons_json, most_killed_json, death_by_json,
            first_seen_server_time, last_seen_server_time,
            player_active_seconds, active_time_source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            stat["target_key"],
            stat["match_key"],
            stat["player_id"],
            stat["player_name"],
            stat.get("team"),
            stat["kills"],
            stat["deaths"],
            stat["teamkills"],
            stat["deaths_by_teamkill"],
            stat["weapons_json"],
            stat["death_by_weapons_json"],
            stat["most_killed_json"],
            stat["death_by_json"],
            stat.get("first_seen_server_time"),
            stat.get("last_seen_server_time"),
            stat.get("player_active_seconds"),
            stat.get("active_time_source"),
        ),
    )


def _ensure_player(
    players: dict[str, dict[str, object]],
    *,
    player_id: str,
    player_name: object,
    team: object,
    server_time: int | None,
) -> dict[str, object]:
    if player_id not in players:
        players[player_id] = {
            "player_id": player_id,
            "player_name": str(player_name or player_id),
            "team": team,
            "kills": 0,
            "deaths": 0,
            "teamkills": 0,
            "deaths_by_teamkill": 0,
            "weapons": Counter(),
            "death_by_weapons": Counter(),
            "most_killed": Counter(),
            "death_by": Counter(),
            "first_seen_server_time": server_time,
            "last_seen_server_time": server_time,
        }
    player = players[player_id]
    if player_name:
        player["player_name"] = str(player_name)
    if team:
        player["team"] = team
    _touch_player(player, server_time)
    return player


def _touch_player(player: dict[str, object], server_time: int | None) -> None:
    if server_time is None:
        return
    first_seen = _coerce_int(player.get("first_seen_server_time"))
    last_seen = _coerce_int(player.get("last_seen_server_time"))
    player["first_seen_server_time"] = server_time if first_seen is None else min(first_seen, server_time)
    player["last_seen_server_time"] = server_time if last_seen is None else max(last_seen, server_time)


def _calculate_event_span_seconds(
    *,
    first_seen_server_time: object,
    last_seen_server_time: object,
) -> int | None:
    first_seen = _coerce_int(first_seen_server_time)
    last_seen = _coerce_int(last_seen_server_time)
    if first_seen is None or last_seen is None:
        return None
    return max(0, last_seen - first_seen)


def _build_player_active_time_payload(
    connection: sqlite3.Connection,
    *,
    match: dict[str, object],
    player: dict[str, object],
    match_rows: list[sqlite3.Row],
) -> dict[str, object]:
    lower = _coerce_int(match.get("started_server_time"))
    upper = _coerce_int(match.get("ended_server_time"))
    fallback_seconds = _calculate_event_span_seconds(
        first_seen_server_time=player.get("first_seen_server_time"),
        last_seen_server_time=player.get("last_seen_server_time"),
    )
    player_id = str(player.get("player_id") or "").strip()

    if lower is None or upper is None or upper < lower:
        return {
            "player_active_seconds": fallback_seconds,
            "active_time_source": "event_span_fallback" if fallback_seconds is not None else "unavailable",
        }

    if not player_id or player_id.startswith("name:"):
        return {
            "player_active_seconds": fallback_seconds,
            "active_time_source": "event_span_fallback" if fallback_seconds is not None else "unavailable",
        }

    interval_events = _collect_player_connection_events_from_match_rows(
        match_rows,
        player_id=player_id,
    )
    prior_connected = _player_was_connected_at_match_start(
        connection,
        target_key=str(match["target_key"]),
        player_id=player_id,
        match_start_server_time=lower,
    )
    interval_seconds, interval_source = _calculate_connection_interval_active_seconds(
        match_start_server_time=lower,
        match_end_server_time=upper,
        prior_connected=prior_connected,
        interval_events=interval_events,
    )
    if interval_source is not None:
        return {
            "player_active_seconds": interval_seconds,
            "active_time_source": interval_source,
        }

    return {
        "player_active_seconds": fallback_seconds,
        "active_time_source": "event_span_fallback" if fallback_seconds is not None else "unavailable",
    }


def _collect_player_connection_events_from_match_rows(
    rows: list[sqlite3.Row],
    *,
    player_id: str,
) -> list[tuple[str, int]]:
    events: list[tuple[str, int]] = []
    for row in rows:
        event_type = str(row["event_type"] or "")
        if event_type not in {"connected", "disconnected"}:
            continue
        payload = _json_object(row["parsed_payload_json"])
        event_player_id = str(payload.get("player_id") or "").strip()
        server_time = _coerce_int(row["server_time"])
        if event_player_id == player_id and server_time is not None:
            events.append((event_type, server_time))
    events.sort(key=lambda item: item[1])
    return events


def _player_was_connected_at_match_start(
    connection: sqlite3.Connection,
    *,
    target_key: str,
    player_id: str,
    match_start_server_time: int,
) -> bool:
    row = connection.execute(
        """
        SELECT event_type
        FROM rcon_admin_log_events
        WHERE target_key = ?
          AND server_time IS NOT NULL
          AND server_time < ?
          AND event_type IN ('connected', 'disconnected')
          AND parsed_payload_json LIKE ?
        ORDER BY server_time DESC, id DESC
        LIMIT 1
        """,
        (
            target_key,
            match_start_server_time,
            f'%"player_id":"{player_id}"%',
        ),
    ).fetchone()
    return bool(row and row["event_type"] == "connected")


def _calculate_connection_interval_active_seconds(
    *,
    match_start_server_time: int,
    match_end_server_time: int,
    prior_connected: bool,
    interval_events: list[tuple[str, int]],
) -> tuple[int | None, str | None]:
    open_since = match_start_server_time if prior_connected else None
    total_seconds = 0
    used_carryover = prior_connected
    has_reliable_intervals = prior_connected

    for event_type, server_time in interval_events:
        clamped_time = max(match_start_server_time, min(match_end_server_time, server_time))
        if event_type == "connected":
            if open_since is None:
                open_since = clamped_time
                has_reliable_intervals = True
            continue
        if open_since is None:
            continue
        total_seconds += max(0, clamped_time - open_since)
        open_since = None
        has_reliable_intervals = True

    if open_since is not None:
        total_seconds += max(0, match_end_server_time - open_since)

    if not has_reliable_intervals:
        return None, None
    return (
        total_seconds,
        "connection_intervals_carryover" if used_carryover else "connection_intervals",
    )


def _ensure_materialized_player_stat_columns(connection: sqlite3.Connection) -> None:
    columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(rcon_match_player_stats)").fetchall()
    }
    if "player_active_seconds" not in columns:
        connection.execute(
            "ALTER TABLE rcon_match_player_stats ADD COLUMN player_active_seconds INTEGER"
        )
    if "active_time_source" not in columns:
        connection.execute(
            "ALTER TABLE rcon_match_player_stats ADD COLUMN active_time_source TEXT"
        )


def _counter(player: dict[str, object], key: str) -> Counter[str]:
    value = player[key]
    if isinstance(value, Counter):
        return value
    counter: Counter[str] = Counter()
    player[key] = counter
    return counter


def _player_key(player_id: object, player_name: object) -> str:
    raw_id = str(player_id or "").strip()
    if raw_id:
        return raw_id
    return f"name:{str(player_name or 'unknown').strip().lower()}"


def _build_match_key(
    *,
    target_key: str,
    started_server_time: object,
    ended_server_time: object,
    map_name: object,
) -> str:
    map_part = "".join(character.lower() for character in str(map_name or "unknown") if character.isalnum())
    start_part = "missing" if started_server_time is None else str(started_server_time)
    end_part = "open" if ended_server_time is None else str(ended_server_time)
    return f"{target_key}:{start_part}:{end_part}:{map_part}"


def _json_object(raw_value: object) -> dict[str, object]:
    if not isinstance(raw_value, str) or not raw_value.strip():
        return {}
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _dump_counter(counter: Counter[str]) -> str:
    ordered = dict(sorted(counter.items(), key=lambda item: (-item[1], item[0])))
    return json.dumps(ordered, ensure_ascii=False, separators=(",", ":"))


def _coerce_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _nested_int(payload: object, key: str) -> int | None:
    if not isinstance(payload, dict):
        return None
    return _coerce_int(payload.get(key))


def _resolve_winner(allied_score: int | None, axis_score: int | None) -> str | None:
    if allied_score is None or axis_score is None:
        return None
    if allied_score > axis_score:
        return "allied"
    if axis_score > allied_score:
        return "axis"
    return "draw"


def _main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Materialize stored RCON AdminLog events.")
    parser.add_argument(
        "command",
        nargs="?",
        choices=("materialize", "status"),
        default="materialize",
    )
    parser.add_argument("--db-path", type=Path, default=None)
    args = parser.parse_args(list(argv) if argv is not None else None)
    db_path = args.db_path or get_storage_path()
    payload = (
        summarize_rcon_materialization_status(db_path=db_path)
        if args.command == "status"
        else materialize_rcon_admin_log(db_path=db_path)
    )
    print(json.dumps({"status": "ok", "data": payload}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
