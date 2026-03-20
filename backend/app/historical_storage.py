"""Persistence and queries for scoreboard-backed historical player stats."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import get_storage_path


def initialize_historical_storage(*, db_path: Path | None = None) -> Path:
    """Ensure the local database contains the historical scoreboard tables."""
    resolved_path = db_path or get_storage_path()
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    with _connect(resolved_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS historical_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_server_id TEXT NOT NULL,
                source_url TEXT NOT NULL,
                source_match_ref TEXT NOT NULL,
                server_name TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                duration_seconds INTEGER,
                map_slug TEXT,
                map_name TEXT NOT NULL,
                mode_name TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (external_server_id, source_match_ref)
            );

            CREATE TABLE IF NOT EXISTS historical_players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_player_ref TEXT NOT NULL UNIQUE,
                canonical_name TEXT NOT NULL,
                last_seen_name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS historical_player_match_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL,
                player_id INTEGER NOT NULL,
                player_name TEXT NOT NULL,
                kills INTEGER NOT NULL DEFAULT 0,
                deaths INTEGER,
                time_seconds INTEGER,
                captured_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (match_id, player_id),
                FOREIGN KEY (match_id) REFERENCES historical_matches(id),
                FOREIGN KEY (player_id) REFERENCES historical_players(id)
            );

            CREATE INDEX IF NOT EXISTS idx_historical_matches_server_started_at
            ON historical_matches(external_server_id, started_at);

            CREATE INDEX IF NOT EXISTS idx_historical_player_match_stats_match_id
            ON historical_player_match_stats(match_id);
            """
        )

    return resolved_path


def persist_historical_capture(
    capture: dict[str, object],
    *,
    db_path: Path | None = None,
) -> dict[str, object]:
    """Persist one scoreboard capture without duplicating match-player rows."""
    resolved_path = initialize_historical_storage(db_path=db_path)
    match = dict(capture.get("match") or {})
    players = list(capture.get("players") or [])

    with _connect(resolved_path) as connection:
        match_id = _upsert_match(connection, capture, match)
        persisted_players = 0
        for player in players:
            player_id = _upsert_player(connection, player)
            _upsert_player_match_stats(connection, match_id, player_id, player)
            persisted_players += 1

    return {
        "db_path": str(resolved_path),
        "external_server_id": capture.get("external_server_id"),
        "source_match_ref": match.get("source_match_ref"),
        "persisted_players": persisted_players,
    }


def list_weekly_top_kills(
    *,
    limit: int = 10,
    server_id: str | None = None,
    now: datetime | None = None,
    db_path: Path | None = None,
) -> dict[str, object]:
    """Return weekly aggregated kills grouped by server and player."""
    resolved_path = initialize_historical_storage(db_path=db_path)
    resolved_now = now or datetime.now(timezone.utc)
    window_start = resolved_now - timedelta(days=7)

    clauses = ["historical_matches.started_at >= ?"]
    params: list[object] = [window_start.isoformat().replace("+00:00", "Z")]
    if server_id:
        clauses.append("historical_matches.external_server_id = ?")
        params.append(server_id)

    where_clause = " AND ".join(clauses)
    query = f"""
        SELECT
            historical_matches.external_server_id,
            historical_matches.server_name,
            historical_players.source_player_ref AS player_ref,
            historical_players.last_seen_name AS player_name,
            SUM(historical_player_match_stats.kills) AS weekly_kills
        FROM historical_player_match_stats
        INNER JOIN historical_matches
            ON historical_matches.id = historical_player_match_stats.match_id
        INNER JOIN historical_players
            ON historical_players.id = historical_player_match_stats.player_id
        WHERE {where_clause}
        GROUP BY
            historical_matches.external_server_id,
            historical_matches.server_name,
            historical_players.id
        ORDER BY
            historical_matches.external_server_id ASC,
            weekly_kills DESC,
            player_name ASC
    """

    with _connect(resolved_path) as connection:
        rows = connection.execute(query, tuple(params)).fetchall()

    grouped_items: list[dict[str, object]] = []
    current_server_id = None
    current_group: dict[str, object] | None = None

    for row in rows:
        external_server_id = str(row["external_server_id"])
        if external_server_id != current_server_id:
            current_server_id = external_server_id
            current_group = {
                "external_server_id": external_server_id,
                "server_name": row["server_name"],
                "rankings": [],
            }
            grouped_items.append(current_group)

        assert current_group is not None
        rankings = current_group["rankings"]
        if len(rankings) >= limit:
            continue

        rankings.append(
            {
                "rank": len(rankings) + 1,
                "player_id": row["player_ref"],
                "player_name": row["player_name"],
                "weekly_kills": int(row["weekly_kills"] or 0),
            }
        )

    return {
        "window_start": window_start.isoformat().replace("+00:00", "Z"),
        "window_end": resolved_now.isoformat().replace("+00:00", "Z"),
        "items": grouped_items,
    }


def _connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def _upsert_match(
    connection: sqlite3.Connection,
    capture: dict[str, object],
    match: dict[str, object],
) -> int:
    connection.execute(
        """
        INSERT INTO historical_matches (
            external_server_id,
            source_url,
            source_match_ref,
            server_name,
            started_at,
            ended_at,
            duration_seconds,
            map_slug,
            map_name,
            mode_name
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(external_server_id, source_match_ref) DO UPDATE SET
            server_name = excluded.server_name,
            ended_at = excluded.ended_at,
            duration_seconds = CASE
                WHEN historical_matches.duration_seconds IS NULL THEN excluded.duration_seconds
                WHEN excluded.duration_seconds IS NULL THEN historical_matches.duration_seconds
                WHEN excluded.duration_seconds > historical_matches.duration_seconds
                    THEN excluded.duration_seconds
                ELSE historical_matches.duration_seconds
            END,
            map_slug = excluded.map_slug,
            map_name = excluded.map_name,
            mode_name = excluded.mode_name,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            capture.get("external_server_id"),
            capture.get("scoreboard_base_url"),
            match.get("source_match_ref"),
            match.get("server_name"),
            match.get("started_at"),
            match.get("ended_at"),
            match.get("duration_seconds"),
            match.get("map_slug"),
            match.get("map_name"),
            match.get("mode_name"),
        ),
    )
    row = connection.execute(
        """
        SELECT id
        FROM historical_matches
        WHERE external_server_id = ? AND source_match_ref = ?
        """,
        (capture.get("external_server_id"), match.get("source_match_ref")),
    ).fetchone()
    if row is None:
        raise RuntimeError("Failed to resolve historical match id.")

    return int(row["id"])


def _upsert_player(connection: sqlite3.Connection, player: dict[str, object]) -> int:
    connection.execute(
        """
        INSERT INTO historical_players (
            source_player_ref,
            canonical_name,
            last_seen_name
        ) VALUES (?, ?, ?)
        ON CONFLICT(source_player_ref) DO UPDATE SET
            canonical_name = excluded.canonical_name,
            last_seen_name = excluded.last_seen_name,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            player.get("source_player_ref"),
            player.get("canonical_name"),
            player.get("last_seen_name"),
        ),
    )
    row = connection.execute(
        "SELECT id FROM historical_players WHERE source_player_ref = ?",
        (player.get("source_player_ref"),),
    ).fetchone()
    if row is None:
        raise RuntimeError("Failed to resolve historical player id.")

    return int(row["id"])


def _upsert_player_match_stats(
    connection: sqlite3.Connection,
    match_id: int,
    player_id: int,
    player: dict[str, object],
) -> None:
    connection.execute(
        """
        INSERT INTO historical_player_match_stats (
            match_id,
            player_id,
            player_name,
            kills,
            deaths,
            time_seconds,
            captured_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(match_id, player_id) DO UPDATE SET
            player_name = excluded.player_name,
            kills = CASE
                WHEN excluded.kills > historical_player_match_stats.kills
                    THEN excluded.kills
                ELSE historical_player_match_stats.kills
            END,
            deaths = CASE
                WHEN historical_player_match_stats.deaths IS NULL THEN excluded.deaths
                WHEN excluded.deaths IS NULL THEN historical_player_match_stats.deaths
                WHEN excluded.deaths > historical_player_match_stats.deaths
                    THEN excluded.deaths
                ELSE historical_player_match_stats.deaths
            END,
            time_seconds = CASE
                WHEN historical_player_match_stats.time_seconds IS NULL THEN excluded.time_seconds
                WHEN excluded.time_seconds IS NULL THEN historical_player_match_stats.time_seconds
                WHEN excluded.time_seconds > historical_player_match_stats.time_seconds
                    THEN excluded.time_seconds
                ELSE historical_player_match_stats.time_seconds
            END,
            captured_at = excluded.captured_at,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            match_id,
            player_id,
            player.get("last_seen_name"),
            player.get("kills"),
            player.get("deaths"),
            player.get("time_seconds"),
            player.get("captured_at"),
        ),
    )
