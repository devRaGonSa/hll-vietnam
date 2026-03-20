"""SQLite persistence for historical CRCON scoreboard data."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Mapping

from .config import get_storage_path
from .historical_models import HistoricalServerDefinition


DEFAULT_HISTORICAL_SERVERS = (
    HistoricalServerDefinition(
        slug="comunidad-hispana-01",
        display_name="Comunidad Hispana #01",
        scoreboard_base_url="https://scoreboard.comunidadhll.es",
        server_number=1,
    ),
    HistoricalServerDefinition(
        slug="comunidad-hispana-02",
        display_name="Comunidad Hispana #02",
        scoreboard_base_url="https://scoreboard.comunidadhll.es:5443",
        server_number=2,
    ),
)
DEFAULT_WEEKLY_WINDOW_DAYS = 7
DEFAULT_REFRESH_OVERLAP_HOURS = 12


def initialize_historical_storage(*, db_path: Path | None = None) -> Path:
    """Create or migrate the local SQLite schema for historical data."""
    resolved_path = db_path or get_storage_path()
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    with _connect(resolved_path) as connection:
        legacy_historical_schema = _has_legacy_historical_schema(connection)
        if legacy_historical_schema:
            _rename_legacy_historical_tables(connection)
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS historical_servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                scoreboard_base_url TEXT NOT NULL UNIQUE,
                server_number INTEGER,
                source_kind TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS historical_maps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_map_id TEXT UNIQUE,
                map_name TEXT,
                pretty_name TEXT,
                game_mode TEXT,
                image_name TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS historical_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                historical_server_id INTEGER NOT NULL,
                external_match_id TEXT NOT NULL,
                historical_map_id INTEGER,
                created_at_source TEXT,
                started_at TEXT,
                ended_at TEXT,
                map_name TEXT,
                map_pretty_name TEXT,
                game_mode TEXT,
                image_name TEXT,
                allied_score INTEGER,
                axis_score INTEGER,
                last_seen_at TEXT NOT NULL,
                raw_payload_ref TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(historical_server_id, external_match_id),
                FOREIGN KEY (historical_server_id) REFERENCES historical_servers(id),
                FOREIGN KEY (historical_map_id) REFERENCES historical_maps(id)
            );

            CREATE TABLE IF NOT EXISTS historical_players (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stable_player_key TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                steam_id TEXT,
                source_player_id TEXT,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS historical_player_match_stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                historical_match_id INTEGER NOT NULL,
                historical_player_id INTEGER NOT NULL,
                match_player_ref TEXT,
                team_side TEXT,
                level INTEGER,
                kills INTEGER,
                deaths INTEGER,
                teamkills INTEGER,
                time_seconds INTEGER,
                kills_per_minute REAL,
                deaths_per_minute REAL,
                kill_death_ratio REAL,
                combat INTEGER,
                offense INTEGER,
                defense INTEGER,
                support INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(historical_match_id, historical_player_id),
                FOREIGN KEY (historical_match_id) REFERENCES historical_matches(id),
                FOREIGN KEY (historical_player_id) REFERENCES historical_players(id)
            );

            CREATE TABLE IF NOT EXISTS historical_ingestion_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mode TEXT NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                target_server_slug TEXT,
                pages_processed INTEGER NOT NULL DEFAULT 0,
                matches_seen INTEGER NOT NULL DEFAULT 0,
                matches_inserted INTEGER NOT NULL DEFAULT 0,
                matches_updated INTEGER NOT NULL DEFAULT 0,
                player_rows_inserted INTEGER NOT NULL DEFAULT 0,
                player_rows_updated INTEGER NOT NULL DEFAULT 0,
                notes TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_historical_matches_server_end
            ON historical_matches(historical_server_id, ended_at DESC, started_at DESC);

            CREATE INDEX IF NOT EXISTS idx_historical_player_stats_match
            ON historical_player_match_stats(historical_match_id);

            CREATE INDEX IF NOT EXISTS idx_historical_players_steam
            ON historical_players(steam_id);
            """
        )
        _seed_default_historical_servers(connection)
        if legacy_historical_schema:
            _migrate_legacy_historical_data(connection)
        _normalize_historical_player_identities(connection)

    return resolved_path


def list_historical_servers(*, db_path: Path | None = None) -> list[dict[str, object]]:
    """Return configured CRCON historical sources."""
    resolved_path = initialize_historical_storage(db_path=db_path)
    with _connect(resolved_path) as connection:
        rows = connection.execute(
            """
            SELECT slug, display_name, scoreboard_base_url, server_number, source_kind
            FROM historical_servers
            ORDER BY slug ASC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def start_ingestion_run(
    *,
    mode: str,
    target_server_slug: str | None = None,
    db_path: Path | None = None,
) -> int:
    """Create a row tracking one ingestion execution."""
    resolved_path = initialize_historical_storage(db_path=db_path)
    with _connect(resolved_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO historical_ingestion_runs (
                mode,
                status,
                started_at,
                target_server_slug
            ) VALUES (?, 'running', ?, ?)
            """,
            (mode, _utc_now_iso(), target_server_slug),
        )
        return int(cursor.lastrowid)


def finalize_ingestion_run(
    run_id: int,
    *,
    status: str,
    pages_processed: int,
    matches_seen: int,
    matches_inserted: int,
    matches_updated: int,
    player_rows_inserted: int,
    player_rows_updated: int,
    notes: str | None = None,
    db_path: Path | None = None,
) -> None:
    """Update an ingestion run row with outcome metrics."""
    resolved_path = initialize_historical_storage(db_path=db_path)
    with _connect(resolved_path) as connection:
        connection.execute(
            """
            UPDATE historical_ingestion_runs
            SET status = ?,
                completed_at = ?,
                pages_processed = ?,
                matches_seen = ?,
                matches_inserted = ?,
                matches_updated = ?,
                player_rows_inserted = ?,
                player_rows_updated = ?,
                notes = ?
            WHERE id = ?
            """,
            (
                status,
                _utc_now_iso(),
                pages_processed,
                matches_seen,
                matches_inserted,
                matches_updated,
                player_rows_inserted,
                player_rows_updated,
                notes,
                run_id,
            ),
        )


def upsert_historical_match(
    *,
    server_slug: str,
    match_payload: Mapping[str, object],
    db_path: Path | None = None,
) -> dict[str, int]:
    """Persist one historical match and its player stats idempotently."""
    resolved_path = initialize_historical_storage(db_path=db_path)
    match_external_id = _stringify(match_payload.get("id"))
    if not match_external_id:
        raise ValueError("Historical match payload is missing a stable id.")

    with _connect(resolved_path) as connection:
        server_row = _resolve_historical_server(connection, server_slug)
        map_id = _upsert_historical_map(connection, match_payload)
        match_row = connection.execute(
            """
            SELECT id
            FROM historical_matches
            WHERE historical_server_id = ? AND external_match_id = ?
            """,
            (server_row["id"], match_external_id),
        ).fetchone()
        match_exists = match_row is not None

        connection.execute(
            """
            INSERT INTO historical_matches (
                historical_server_id,
                external_match_id,
                historical_map_id,
                created_at_source,
                started_at,
                ended_at,
                map_name,
                map_pretty_name,
                game_mode,
                image_name,
                allied_score,
                axis_score,
                last_seen_at,
                raw_payload_ref
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(historical_server_id, external_match_id) DO UPDATE SET
                historical_map_id = excluded.historical_map_id,
                created_at_source = excluded.created_at_source,
                started_at = excluded.started_at,
                ended_at = excluded.ended_at,
                map_name = excluded.map_name,
                map_pretty_name = excluded.map_pretty_name,
                game_mode = excluded.game_mode,
                image_name = excluded.image_name,
                allied_score = excluded.allied_score,
                axis_score = excluded.axis_score,
                last_seen_at = excluded.last_seen_at,
                raw_payload_ref = excluded.raw_payload_ref,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                server_row["id"],
                match_external_id,
                map_id,
                _normalize_timestamp(match_payload.get("creation_time")),
                _normalize_timestamp(match_payload.get("start")),
                _normalize_timestamp(match_payload.get("end")),
                _extract_map_name(match_payload),
                _extract_map_pretty_name(match_payload),
                _extract_map_game_mode(match_payload),
                _extract_map_image_name(match_payload),
                _coerce_int(_get_nested(match_payload, "result", "allied")),
                _coerce_int(_get_nested(match_payload, "result", "axis")),
                _utc_now_iso(),
                f"{server_row['scoreboard_base_url']}/games/{match_external_id}",
            ),
        )
        match_id_row = connection.execute(
            """
            SELECT id
            FROM historical_matches
            WHERE historical_server_id = ? AND external_match_id = ?
            """,
            (server_row["id"], match_external_id),
        ).fetchone()
        if match_id_row is None:
            raise RuntimeError("Failed to persist historical match.")

        player_rows_inserted = 0
        player_rows_updated = 0
        for player_payload in _coerce_list(match_payload.get("player_stats")):
            player_id = _upsert_historical_player(connection, player_payload)
            stat_exists = connection.execute(
                """
                SELECT id
                FROM historical_player_match_stats
                WHERE historical_match_id = ? AND historical_player_id = ?
                """,
                (match_id_row["id"], player_id),
            ).fetchone()
            connection.execute(
                """
                INSERT INTO historical_player_match_stats (
                    historical_match_id,
                    historical_player_id,
                    match_player_ref,
                    team_side,
                    level,
                    kills,
                    deaths,
                    teamkills,
                    time_seconds,
                    kills_per_minute,
                    deaths_per_minute,
                    kill_death_ratio,
                    combat,
                    offense,
                    defense,
                    support
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(historical_match_id, historical_player_id) DO UPDATE SET
                    match_player_ref = excluded.match_player_ref,
                    team_side = excluded.team_side,
                    level = excluded.level,
                    kills = excluded.kills,
                    deaths = excluded.deaths,
                    teamkills = excluded.teamkills,
                    time_seconds = excluded.time_seconds,
                    kills_per_minute = excluded.kills_per_minute,
                    deaths_per_minute = excluded.deaths_per_minute,
                    kill_death_ratio = excluded.kill_death_ratio,
                    combat = excluded.combat,
                    offense = excluded.offense,
                    defense = excluded.defense,
                    support = excluded.support,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    match_id_row["id"],
                    player_id,
                    _stringify(player_payload.get("id")),
                    _stringify(_get_nested(player_payload, "team", "side")),
                    _coerce_int(player_payload.get("level")),
                    _coerce_int(player_payload.get("kills")),
                    _coerce_int(player_payload.get("deaths")),
                    _coerce_int(player_payload.get("teamkills")),
                    _coerce_int(player_payload.get("time_seconds")),
                    _coerce_float(player_payload.get("kills_per_minute")),
                    _coerce_float(player_payload.get("deaths_per_minute")),
                    _coerce_float(player_payload.get("kill_death_ratio")),
                    _coerce_int(player_payload.get("combat")),
                    _coerce_int(player_payload.get("offense")),
                    _coerce_int(player_payload.get("defense")),
                    _coerce_int(player_payload.get("support")),
                ),
            )
            if stat_exists is None:
                player_rows_inserted += 1
            else:
                player_rows_updated += 1

    return {
        "matches_inserted": 0 if match_exists else 1,
        "matches_updated": 1 if match_exists else 0,
        "player_rows_inserted": player_rows_inserted,
        "player_rows_updated": player_rows_updated,
    }


def get_refresh_cutoff_for_server(
    server_slug: str,
    *,
    overlap_hours: int = DEFAULT_REFRESH_OVERLAP_HOURS,
    db_path: Path | None = None,
) -> str | None:
    """Return the timestamp used to stop incremental scans once older pages appear."""
    resolved_path = initialize_historical_storage(db_path=db_path)
    with _connect(resolved_path) as connection:
        server_row = _resolve_historical_server(connection, server_slug)
        row = connection.execute(
            """
            SELECT COALESCE(MAX(ended_at), MAX(started_at), MAX(created_at_source)) AS latest_seen_at
            FROM historical_matches
            WHERE historical_server_id = ?
            """,
            (server_row["id"],),
        ).fetchone()
    latest_seen_at = _stringify(row["latest_seen_at"] if row else None)
    if not latest_seen_at:
        return None

    cutoff = _parse_timestamp(latest_seen_at) - timedelta(hours=overlap_hours)
    return cutoff.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def list_recent_historical_matches(
    *,
    server_slug: str | None = None,
    limit: int = 20,
    db_path: Path | None = None,
) -> list[dict[str, object]]:
    """Return recent persisted matches for validation and later API work."""
    resolved_path = initialize_historical_storage(db_path=db_path)
    where_clause = ""
    params: list[object] = []
    if server_slug:
        where_clause = "WHERE historical_servers.slug = ?"
        params.append(server_slug)
    params.append(limit)

    with _connect(resolved_path) as connection:
        rows = connection.execute(
            f"""
            SELECT
                historical_servers.slug AS server_slug,
                historical_servers.display_name AS server_name,
                historical_matches.external_match_id,
                historical_matches.started_at,
                historical_matches.ended_at,
                historical_matches.map_pretty_name,
                historical_matches.map_name,
                historical_matches.allied_score,
                historical_matches.axis_score,
                COUNT(historical_player_match_stats.id) AS player_count
            FROM historical_matches
            INNER JOIN historical_servers
                ON historical_servers.id = historical_matches.historical_server_id
            LEFT JOIN historical_player_match_stats
                ON historical_player_match_stats.historical_match_id = historical_matches.id
            {where_clause}
            GROUP BY historical_matches.id
            ORDER BY COALESCE(historical_matches.ended_at, historical_matches.started_at) DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def list_weekly_top_kills(
    *,
    limit: int = 10,
    server_id: str | None = None,
    db_path: Path | None = None,
) -> dict[str, object]:
    """Return ranked weekly kill totals from persisted historical match stats."""
    resolved_path = initialize_historical_storage(db_path=db_path)
    window_end = datetime.now(timezone.utc)
    window_start = window_end - timedelta(days=DEFAULT_WEEKLY_WINDOW_DAYS)

    where_clauses = [
        "COALESCE(historical_matches.ended_at, historical_matches.started_at, historical_matches.created_at_source) >= ?",
        "COALESCE(historical_matches.ended_at, historical_matches.started_at, historical_matches.created_at_source) <= ?",
    ]
    params: list[object] = [
        window_start.isoformat().replace("+00:00", "Z"),
        window_end.isoformat().replace("+00:00", "Z"),
    ]
    if server_id:
        normalized_server_id = server_id.strip()
        where_clauses.append(
            "(historical_servers.slug = ? OR CAST(historical_servers.server_number AS TEXT) = ?)"
        )
        params.extend([normalized_server_id, normalized_server_id])

    with _connect(resolved_path) as connection:
        rows = connection.execute(
            f"""
            WITH ranked_players AS (
                SELECT
                    historical_servers.slug AS server_slug,
                    historical_servers.display_name AS server_name,
                    historical_players.stable_player_key,
                    historical_players.display_name AS player_name,
                    historical_players.steam_id,
                    COUNT(DISTINCT historical_matches.id) AS matches_count,
                    COALESCE(SUM(historical_player_match_stats.kills), 0) AS kills,
                    ROW_NUMBER() OVER (
                        PARTITION BY historical_servers.slug
                        ORDER BY
                            COALESCE(SUM(historical_player_match_stats.kills), 0) DESC,
                            COUNT(DISTINCT historical_matches.id) ASC,
                            historical_players.display_name ASC
                    ) AS ranking_position
                FROM historical_player_match_stats
                INNER JOIN historical_matches
                    ON historical_matches.id = historical_player_match_stats.historical_match_id
                INNER JOIN historical_servers
                    ON historical_servers.id = historical_matches.historical_server_id
                INNER JOIN historical_players
                    ON historical_players.id = historical_player_match_stats.historical_player_id
                WHERE {" AND ".join(where_clauses)}
                GROUP BY historical_servers.slug, historical_players.id
            )
            SELECT *
            FROM ranked_players
            WHERE ranking_position <= ?
            ORDER BY server_slug ASC, ranking_position ASC
            """,
            [*params, limit],
        ).fetchall()

    items: list[dict[str, object]] = []
    for row in rows:
        items.append(
            {
                "server": {
                    "slug": row["server_slug"],
                    "name": row["server_name"],
                },
                "time_range": {
                    "start": window_start.isoformat().replace("+00:00", "Z"),
                    "end": window_end.isoformat().replace("+00:00", "Z"),
                    "window_days": DEFAULT_WEEKLY_WINDOW_DAYS,
                },
                "player": {
                    "stable_player_key": row["stable_player_key"],
                    "name": row["player_name"],
                    "steam_id": row["steam_id"],
                },
                "ranking_position": int(row["ranking_position"]),
                "weekly_kills": int(row["kills"] or 0),
                "matches_considered": int(row["matches_count"] or 0),
            }
        )

    return {
        "window_start": window_start.isoformat().replace("+00:00", "Z"),
        "window_end": window_end.isoformat().replace("+00:00", "Z"),
        "items": items,
    }


def _connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def _has_legacy_historical_schema(connection: sqlite3.Connection) -> bool:
    columns = {
        str(row["name"])
        for row in connection.execute("PRAGMA table_info(historical_matches)").fetchall()
    }
    return bool(columns) and "historical_server_id" not in columns


def _rename_legacy_historical_tables(connection: sqlite3.Connection) -> None:
    rename_plan = (
        ("historical_player_match_stats", "historical_player_match_stats_legacy"),
        ("historical_players", "historical_players_legacy"),
        ("historical_matches", "historical_matches_legacy"),
    )
    for current_name, legacy_name in rename_plan:
        table_exists = connection.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table' AND name = ?
            """,
            (current_name,),
        ).fetchone()
        if not table_exists:
            continue

        legacy_exists = connection.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table' AND name = ?
            """,
            (legacy_name,),
        ).fetchone()
        if legacy_exists:
            continue

        connection.execute(f"ALTER TABLE {current_name} RENAME TO {legacy_name}")


def _migrate_legacy_historical_data(connection: sqlite3.Connection) -> None:
    matches_table = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = 'historical_matches_legacy'
        """
    ).fetchone()
    if not matches_table:
        return

    player_map: dict[int, int] = {}
    for row in connection.execute(
        """
        SELECT id, source_player_ref, canonical_name, last_seen_name
        FROM historical_players_legacy
        ORDER BY id ASC
        """
    ).fetchall():
        stable_player_key = _stringify(row["source_player_ref"]) or f"legacy-player:{row['id']}"
        display_name = _stringify(row["last_seen_name"]) or _stringify(row["canonical_name"]) or "Unknown player"
        now = _utc_now_iso()
        connection.execute(
            """
            INSERT INTO historical_players (
                stable_player_key,
                display_name,
                steam_id,
                source_player_id,
                first_seen_at,
                last_seen_at
            ) VALUES (?, ?, NULL, NULL, ?, ?)
            ON CONFLICT(stable_player_key) DO UPDATE SET
                display_name = excluded.display_name,
                last_seen_at = excluded.last_seen_at,
                updated_at = CURRENT_TIMESTAMP
            """,
            (stable_player_key, display_name, now, now),
        )
        new_row = connection.execute(
            "SELECT id FROM historical_players WHERE stable_player_key = ?",
            (stable_player_key,),
        ).fetchone()
        if new_row is not None:
            player_map[int(row["id"])] = int(new_row["id"])

    match_map: dict[int, int] = {}
    for row in connection.execute(
        """
        SELECT *
        FROM historical_matches_legacy
        ORDER BY id ASC
        """
    ).fetchall():
        server_slug = _stringify(row["external_server_id"]) or "comunidad-hispana-01"
        server_row = _resolve_historical_server(connection, server_slug)
        connection.execute(
            """
            INSERT INTO historical_matches (
                historical_server_id,
                external_match_id,
                historical_map_id,
                created_at_source,
                started_at,
                ended_at,
                map_name,
                map_pretty_name,
                game_mode,
                image_name,
                allied_score,
                axis_score,
                last_seen_at,
                raw_payload_ref
            ) VALUES (?, ?, NULL, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?)
            ON CONFLICT(historical_server_id, external_match_id) DO UPDATE SET
                started_at = excluded.started_at,
                ended_at = excluded.ended_at,
                map_name = excluded.map_name,
                map_pretty_name = excluded.map_pretty_name,
                game_mode = excluded.game_mode,
                last_seen_at = excluded.last_seen_at,
                raw_payload_ref = excluded.raw_payload_ref,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                server_row["id"],
                _stringify(row["source_match_ref"]) or f"legacy-match:{row['id']}",
                _stringify(row["created_at"]),
                _stringify(row["started_at"]),
                _stringify(row["ended_at"]),
                _stringify(row["map_name"]),
                _stringify(row["map_name"]),
                _stringify(row["mode_name"]),
                _utc_now_iso(),
                _stringify(row["source_url"]),
            ),
        )
        new_row = connection.execute(
            """
            SELECT id
            FROM historical_matches
            WHERE historical_server_id = ? AND external_match_id = ?
            """,
            (
                server_row["id"],
                _stringify(row["source_match_ref"]) or f"legacy-match:{row['id']}",
            ),
        ).fetchone()
        if new_row is not None:
            match_map[int(row["id"])] = int(new_row["id"])

    for row in connection.execute(
        """
        SELECT *
        FROM historical_player_match_stats_legacy
        ORDER BY id ASC
        """
    ).fetchall():
        new_match_id = match_map.get(int(row["match_id"]))
        new_player_id = player_map.get(int(row["player_id"]))
        if new_match_id is None or new_player_id is None:
            continue

        connection.execute(
            """
            INSERT INTO historical_player_match_stats (
                historical_match_id,
                historical_player_id,
                match_player_ref,
                team_side,
                level,
                kills,
                deaths,
                teamkills,
                time_seconds,
                kills_per_minute,
                deaths_per_minute,
                kill_death_ratio,
                combat,
                offense,
                defense,
                support
            ) VALUES (?, ?, NULL, NULL, NULL, ?, ?, NULL, ?, NULL, NULL, NULL, NULL, NULL, NULL, NULL)
            ON CONFLICT(historical_match_id, historical_player_id) DO UPDATE SET
                kills = excluded.kills,
                deaths = excluded.deaths,
                time_seconds = excluded.time_seconds,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                new_match_id,
                new_player_id,
                _coerce_int(row["kills"]),
                _coerce_int(row["deaths"]),
                _coerce_int(row["time_seconds"]),
            ),
        )


def _normalize_historical_player_identities(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT id, stable_player_key, steam_id
        FROM historical_players
        ORDER BY id ASC
        """
    ).fetchall()
    for row in rows:
        stable_player_key = _stringify(row["stable_player_key"])
        if not stable_player_key or ":" in stable_player_key:
            continue
        if stable_player_key.isdigit() and len(stable_player_key) >= 16:
            normalized_key = f"steam:{stable_player_key}"
            connection.execute(
                """
                UPDATE historical_players
                SET stable_player_key = ?,
                    steam_id = COALESCE(steam_id, ?),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (normalized_key, stable_player_key, row["id"]),
            )


def _seed_default_historical_servers(connection: sqlite3.Connection) -> None:
    for server in DEFAULT_HISTORICAL_SERVERS:
        connection.execute(
            """
            INSERT INTO historical_servers (
                slug,
                display_name,
                scoreboard_base_url,
                server_number,
                source_kind
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                display_name = excluded.display_name,
                scoreboard_base_url = excluded.scoreboard_base_url,
                server_number = excluded.server_number,
                source_kind = excluded.source_kind,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                server.slug,
                server.display_name,
                server.scoreboard_base_url,
                server.server_number,
                server.source_kind,
            ),
        )


def _resolve_historical_server(
    connection: sqlite3.Connection,
    server_slug: str,
) -> sqlite3.Row:
    row = connection.execute(
        """
        SELECT id, slug, scoreboard_base_url
        FROM historical_servers
        WHERE slug = ?
        """,
        (server_slug,),
    ).fetchone()
    if row is None:
        raise ValueError(f"Unknown historical server slug: {server_slug}")
    return row


def _upsert_historical_map(
    connection: sqlite3.Connection,
    match_payload: Mapping[str, object],
) -> int | None:
    external_map_id = _stringify(_get_nested(match_payload, "map", "id"))
    if not external_map_id:
        return None

    connection.execute(
        """
        INSERT INTO historical_maps (
            external_map_id,
            map_name,
            pretty_name,
            game_mode,
            image_name
        ) VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(external_map_id) DO UPDATE SET
            map_name = excluded.map_name,
            pretty_name = excluded.pretty_name,
            game_mode = excluded.game_mode,
            image_name = excluded.image_name,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            external_map_id,
            _extract_map_name(match_payload),
            _extract_map_pretty_name(match_payload),
            _extract_map_game_mode(match_payload),
            _extract_map_image_name(match_payload),
        ),
    )
    row = connection.execute(
        "SELECT id FROM historical_maps WHERE external_map_id = ?",
        (external_map_id,),
    ).fetchone()
    return int(row["id"]) if row is not None else None


def _upsert_historical_player(
    connection: sqlite3.Connection,
    player_payload: Mapping[str, object],
) -> int:
    stable_player_key = _build_stable_player_key(player_payload)
    display_name = _stringify(player_payload.get("player")) or "Unknown player"
    steam_id = _stringify(_get_nested(player_payload, "steaminfo", "profile", "steamid"))
    if not steam_id:
        steam_id = _stringify(_get_nested(player_payload, "steaminfo", "id"))
    source_player_id = _stringify(player_payload.get("player_id"))
    seen_at = _utc_now_iso()

    connection.execute(
        """
        INSERT INTO historical_players (
            stable_player_key,
            display_name,
            steam_id,
            source_player_id,
            first_seen_at,
            last_seen_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(stable_player_key) DO UPDATE SET
            display_name = excluded.display_name,
            steam_id = COALESCE(excluded.steam_id, historical_players.steam_id),
            source_player_id = COALESCE(excluded.source_player_id, historical_players.source_player_id),
            last_seen_at = excluded.last_seen_at,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            stable_player_key,
            display_name,
            steam_id,
            source_player_id,
            seen_at,
            seen_at,
        ),
    )
    row = connection.execute(
        "SELECT id FROM historical_players WHERE stable_player_key = ?",
        (stable_player_key,),
    ).fetchone()
    if row is None:
        raise RuntimeError("Failed to persist historical player identity.")
    return int(row["id"])


def _build_stable_player_key(player_payload: Mapping[str, object]) -> str:
    steam_id = _stringify(_get_nested(player_payload, "steaminfo", "profile", "steamid"))
    if steam_id:
        return f"steam:{steam_id}"

    steaminfo_id = _stringify(_get_nested(player_payload, "steaminfo", "id"))
    if steaminfo_id:
        return f"steaminfo:{steaminfo_id}"

    source_player_id = _stringify(player_payload.get("player_id"))
    if source_player_id:
        return f"crcon-player:{source_player_id}"

    player_name = _stringify(player_payload.get("player")) or "unknown-player"
    normalized_name = "".join(
        character.lower() if character.isalnum() else "-"
        for character in player_name
    )
    compact_name = "-".join(part for part in normalized_name.split("-") if part)
    return f"name:{compact_name or 'unknown-player'}"


def _extract_map_name(match_payload: Mapping[str, object]) -> str | None:
    return _stringify(match_payload.get("map_name")) or _stringify(_get_nested(match_payload, "map", "name"))


def _extract_map_pretty_name(match_payload: Mapping[str, object]) -> str | None:
    return _stringify(_get_nested(match_payload, "map", "pretty_name")) or _extract_map_name(match_payload)


def _extract_map_game_mode(match_payload: Mapping[str, object]) -> str | None:
    return _stringify(_get_nested(match_payload, "map", "game_mode"))


def _extract_map_image_name(match_payload: Mapping[str, object]) -> str | None:
    return _stringify(_get_nested(match_payload, "map", "image_name"))


def _coerce_list(value: object) -> list[Mapping[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]


def _coerce_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _stringify(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_timestamp(value: object) -> str | None:
    text = _stringify(value)
    if not text:
        return None
    try:
        return _parse_timestamp(text).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except ValueError:
        return text


def _parse_timestamp(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _get_nested(payload: Mapping[str, object], *path: str) -> object:
    current: object = payload
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
