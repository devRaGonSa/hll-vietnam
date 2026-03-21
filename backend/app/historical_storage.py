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
SUPPORTED_WEEKLY_LEADERBOARD_METRICS = frozenset(
    {
        "kills",
        "deaths",
        "support",
        "matches_over_100_kills",
    }
)


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

            CREATE TABLE IF NOT EXISTS historical_backfill_progress (
                historical_server_id INTEGER NOT NULL,
                mode TEXT NOT NULL,
                next_page INTEGER NOT NULL DEFAULT 1,
                last_completed_page INTEGER,
                discovered_total_matches INTEGER,
                discovered_total_pages INTEGER,
                archive_exhausted INTEGER NOT NULL DEFAULT 0,
                last_run_id INTEGER,
                last_run_status TEXT,
                last_run_started_at TEXT,
                last_run_completed_at TEXT,
                last_error TEXT,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (historical_server_id, mode),
                FOREIGN KEY (historical_server_id) REFERENCES historical_servers(id)
            );

            CREATE INDEX IF NOT EXISTS idx_historical_matches_server_end
            ON historical_matches(historical_server_id, ended_at DESC, started_at DESC);

            CREATE INDEX IF NOT EXISTS idx_historical_player_stats_match
            ON historical_player_match_stats(historical_match_id);

            CREATE INDEX IF NOT EXISTS idx_historical_players_steam
            ON historical_players(steam_id);

            CREATE INDEX IF NOT EXISTS idx_historical_backfill_progress_run
            ON historical_backfill_progress(last_run_id);
            """
        )
        _seed_default_historical_servers(connection)
        if legacy_historical_schema:
            _migrate_legacy_historical_data(connection)
        _normalize_historical_player_identities(connection)
        _normalize_historical_match_identities(connection)

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


def mark_backfill_progress_started(
    *,
    server_slug: str,
    mode: str,
    run_id: int,
    db_path: Path | None = None,
) -> None:
    """Persist the start of one resumable historical backfill attempt."""
    resolved_path = initialize_historical_storage(db_path=db_path)
    with _connect(resolved_path) as connection:
        server_row = _resolve_historical_server(connection, server_slug)
        connection.execute(
            """
            INSERT INTO historical_backfill_progress (
                historical_server_id,
                mode,
                next_page,
                archive_exhausted,
                last_run_id,
                last_run_status,
                last_run_started_at,
                last_run_completed_at,
                last_error
            ) VALUES (?, ?, 1, 0, ?, 'running', ?, NULL, NULL)
            ON CONFLICT(historical_server_id, mode) DO UPDATE SET
                last_run_id = excluded.last_run_id,
                last_run_status = excluded.last_run_status,
                last_run_started_at = excluded.last_run_started_at,
                last_run_completed_at = NULL,
                last_error = NULL,
                archive_exhausted = CASE
                    WHEN excluded.mode = 'bootstrap' THEN 0
                    ELSE historical_backfill_progress.archive_exhausted
                END,
                updated_at = CURRENT_TIMESTAMP
            """,
            (server_row["id"], mode, run_id, _utc_now_iso()),
        )


def mark_backfill_progress_page_completed(
    *,
    server_slug: str,
    mode: str,
    page_number: int,
    page_size: int,
    run_id: int,
    discovered_total_matches: int | None,
    db_path: Path | None = None,
) -> None:
    """Persist the latest completed page so bootstraps can resume safely."""
    resolved_path = initialize_historical_storage(db_path=db_path)
    discovered_total_pages = None
    if discovered_total_matches and page_size > 0:
        discovered_total_pages = (discovered_total_matches + page_size - 1) // page_size

    with _connect(resolved_path) as connection:
        server_row = _resolve_historical_server(connection, server_slug)
        connection.execute(
            """
            INSERT INTO historical_backfill_progress (
                historical_server_id,
                mode,
                next_page,
                last_completed_page,
                discovered_total_matches,
                discovered_total_pages,
                archive_exhausted,
                last_run_id,
                last_run_status,
                last_run_started_at,
                last_run_completed_at,
                last_error
            ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, NULL, NULL)
            ON CONFLICT(historical_server_id, mode) DO UPDATE SET
                next_page = excluded.next_page,
                last_completed_page = excluded.last_completed_page,
                discovered_total_matches = COALESCE(
                    excluded.discovered_total_matches,
                    historical_backfill_progress.discovered_total_matches
                ),
                discovered_total_pages = COALESCE(
                    excluded.discovered_total_pages,
                    historical_backfill_progress.discovered_total_pages
                ),
                archive_exhausted = 0,
                last_run_id = excluded.last_run_id,
                last_run_status = excluded.last_run_status,
                last_run_started_at = excluded.last_run_started_at,
                last_run_completed_at = NULL,
                last_error = NULL,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                server_row["id"],
                mode,
                page_number + 1,
                page_number,
                discovered_total_matches,
                discovered_total_pages,
                run_id,
                "running",
                _utc_now_iso(),
            ),
        )


def finalize_backfill_progress(
    *,
    server_slug: str,
    mode: str,
    run_id: int,
    status: str,
    archive_exhausted: bool = False,
    error_message: str | None = None,
    db_path: Path | None = None,
) -> None:
    """Persist the final state of one resumable historical backfill attempt."""
    resolved_path = initialize_historical_storage(db_path=db_path)
    with _connect(resolved_path) as connection:
        server_row = _resolve_historical_server(connection, server_slug)
        connection.execute(
            """
            INSERT INTO historical_backfill_progress (
                historical_server_id,
                mode,
                next_page,
                archive_exhausted,
                last_run_id,
                last_run_status,
                last_run_started_at,
                last_run_completed_at,
                last_error
            ) VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(historical_server_id, mode) DO UPDATE SET
                archive_exhausted = CASE
                    WHEN excluded.last_run_status = 'success' AND excluded.archive_exhausted = 1
                    THEN 1
                    WHEN excluded.last_run_status = 'success'
                    THEN historical_backfill_progress.archive_exhausted
                    ELSE historical_backfill_progress.archive_exhausted
                END,
                last_run_id = excluded.last_run_id,
                last_run_status = excluded.last_run_status,
                last_run_started_at = COALESCE(
                    historical_backfill_progress.last_run_started_at,
                    excluded.last_run_started_at
                ),
                last_run_completed_at = excluded.last_run_completed_at,
                last_error = excluded.last_error,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                server_row["id"],
                mode,
                1 if archive_exhausted else 0,
                run_id,
                status,
                _utc_now_iso(),
                _utc_now_iso(),
                error_message,
            ),
        )


def get_backfill_resume_page(
    server_slug: str,
    *,
    mode: str = "bootstrap",
    db_path: Path | None = None,
) -> int:
    """Return the next page recorded for one resumable historical backfill."""
    resolved_path = initialize_historical_storage(db_path=db_path)
    with _connect(resolved_path) as connection:
        server_row = _resolve_historical_server(connection, server_slug)
        row = connection.execute(
            """
            SELECT next_page
            FROM historical_backfill_progress
            WHERE historical_server_id = ? AND mode = ?
            """,
            (server_row["id"], mode),
        ).fetchone()
    return max(1, int(row["next_page"])) if row and row["next_page"] else 1


def list_historical_backfill_progress(
    *,
    server_slug: str | None = None,
    mode: str = "bootstrap",
    db_path: Path | None = None,
) -> list[dict[str, object]]:
    """Return persisted resume checkpoints and last run state per server."""
    resolved_path = initialize_historical_storage(db_path=db_path)
    where_clause = ""
    params: list[object] = [mode]
    if server_slug:
        where_clause = "WHERE historical_servers.slug = ?"
        params.append(server_slug)

    with _connect(resolved_path) as connection:
        rows = connection.execute(
            f"""
            SELECT
                historical_servers.slug AS server_slug,
                historical_servers.display_name AS server_name,
                progress.mode AS mode,
                progress.next_page AS next_page,
                progress.last_completed_page AS last_completed_page,
                progress.discovered_total_matches AS discovered_total_matches,
                progress.discovered_total_pages AS discovered_total_pages,
                progress.archive_exhausted AS archive_exhausted,
                progress.last_run_id AS last_run_id,
                progress.last_run_status AS last_run_status,
                progress.last_run_started_at AS last_run_started_at,
                progress.last_run_completed_at AS last_run_completed_at,
                progress.last_error AS last_error
            FROM historical_servers
            LEFT JOIN historical_backfill_progress AS progress
                ON progress.historical_server_id = historical_servers.id
                AND progress.mode = ?
            {where_clause}
            ORDER BY historical_servers.server_number ASC, historical_servers.slug ASC
            """,
            params,
        ).fetchall()

    items: list[dict[str, object]] = []
    for row in rows:
        items.append(
            {
                "server": {
                    "slug": row["server_slug"],
                    "name": row["server_name"],
                },
                "mode": row["mode"] or mode,
                "next_page": int(row["next_page"] or 1),
                "last_completed_page": _coerce_int(row["last_completed_page"]),
                "discovered_total_matches": _coerce_int(row["discovered_total_matches"]),
                "discovered_total_pages": _coerce_int(row["discovered_total_pages"]),
                "archive_exhausted": bool(row["archive_exhausted"]),
                "last_run": {
                    "run_id": _coerce_int(row["last_run_id"]),
                    "status": _stringify(row["last_run_status"]),
                    "started_at": _stringify(row["last_run_started_at"]),
                    "completed_at": _stringify(row["last_run_completed_at"]),
                    "error": _stringify(row["last_error"]),
                },
            }
        )
    return items


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
    """Return recent persisted matches grouped for the historical API layer."""
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
    items: list[dict[str, object]] = []
    for row in rows:
        items.append(
            {
                "server": {
                    "slug": row["server_slug"],
                    "name": row["server_name"],
                },
                "match_id": row["external_match_id"],
                "started_at": row["started_at"],
                "ended_at": row["ended_at"],
                "closed_at": row["ended_at"] or row["started_at"],
                "map": {
                    "name": row["map_name"],
                    "pretty_name": row["map_pretty_name"] or row["map_name"],
                },
                "result": {
                    "allied_score": _coerce_int(row["allied_score"]),
                    "axis_score": _coerce_int(row["axis_score"]),
                    "winner": _resolve_match_winner(
                        row["allied_score"],
                        row["axis_score"],
                    ),
                },
                "player_count": int(row["player_count"] or 0),
            }
        )
    return items


def list_historical_server_summaries(
    *,
    server_slug: str | None = None,
    db_path: Path | None = None,
) -> list[dict[str, object]]:
    """Return aggregate historical metrics per server."""
    resolved_path = initialize_historical_storage(db_path=db_path)
    where_clause = ""
    params: list[object] = []
    if server_slug:
        where_clause = "WHERE historical_servers.slug = ?"
        params.append(server_slug)

    with _connect(resolved_path) as connection:
        summary_rows = connection.execute(
            f"""
            SELECT
                historical_servers.slug AS server_slug,
                historical_servers.display_name AS server_name,
                COUNT(DISTINCT historical_matches.id) AS matches_count,
                COUNT(DISTINCT historical_players.id) AS unique_players,
                COALESCE(SUM(historical_player_match_stats.kills), 0) AS total_kills,
                COUNT(DISTINCT COALESCE(historical_matches.map_pretty_name, historical_matches.map_name)) AS map_count,
                MIN(COALESCE(historical_matches.ended_at, historical_matches.started_at, historical_matches.created_at_source)) AS first_match_at,
                MAX(COALESCE(historical_matches.ended_at, historical_matches.started_at, historical_matches.created_at_source)) AS last_match_at
            FROM historical_servers
            LEFT JOIN historical_matches
                ON historical_matches.historical_server_id = historical_servers.id
            LEFT JOIN historical_player_match_stats
                ON historical_player_match_stats.historical_match_id = historical_matches.id
            LEFT JOIN historical_players
                ON historical_players.id = historical_player_match_stats.historical_player_id
            {where_clause}
            GROUP BY historical_servers.id
            ORDER BY historical_servers.server_number ASC, historical_servers.slug ASC
            """,
            params,
        ).fetchall()

        map_rows = connection.execute(
            f"""
            SELECT
                historical_servers.slug AS server_slug,
                COALESCE(historical_matches.map_pretty_name, historical_matches.map_name, 'Mapa no disponible') AS map_name,
                COUNT(*) AS matches_count
            FROM historical_matches
            INNER JOIN historical_servers
                ON historical_servers.id = historical_matches.historical_server_id
            {where_clause}
            GROUP BY historical_servers.slug, COALESCE(historical_matches.map_pretty_name, historical_matches.map_name, 'Mapa no disponible')
            ORDER BY historical_servers.slug ASC, matches_count DESC, map_name ASC
            """,
            params,
        ).fetchall()

    progress_by_server = {
        item["server"]["slug"]: item
        for item in list_historical_backfill_progress(
            server_slug=server_slug,
            db_path=resolved_path,
        )
    }
    top_maps_by_server: dict[str, list[dict[str, object]]] = {}
    for row in map_rows:
        server_key = str(row["server_slug"])
        top_maps_by_server.setdefault(server_key, [])
        if len(top_maps_by_server[server_key]) >= 3:
            continue
        top_maps_by_server[server_key].append(
            {
                "map_name": row["map_name"],
                "matches_count": int(row["matches_count"] or 0),
            }
        )

    items: list[dict[str, object]] = []
    for row in summary_rows:
        matches_count = int(row["matches_count"] or 0)
        first_match_at = _stringify(row["first_match_at"])
        last_match_at = _stringify(row["last_match_at"])
        coverage_days = _calculate_coverage_days(first_match_at, last_match_at)
        progress = progress_by_server.get(str(row["server_slug"]), {})
        discovered_total_matches = _coerce_int(progress.get("discovered_total_matches"))
        items.append(
            {
                "server": {
                    "slug": row["server_slug"],
                    "name": row["server_name"],
                },
                "matches_count": matches_count,
                "imported_matches_count": matches_count,
                "unique_players": int(row["unique_players"] or 0),
                "total_kills": int(row["total_kills"] or 0),
                "map_count": int(row["map_count"] or 0),
                "top_maps": top_maps_by_server.get(str(row["server_slug"]), []),
                "coverage": {
                    "basis": "persisted-import",
                    "status": _classify_coverage_status(matches_count, coverage_days),
                    "imported_matches_count": matches_count,
                    "discovered_total_matches": discovered_total_matches,
                    "first_match_at": first_match_at,
                    "last_match_at": last_match_at,
                    "coverage_days": coverage_days,
                },
                "backfill": {
                    "mode": progress.get("mode", "bootstrap"),
                    "next_page": _coerce_int(progress.get("next_page")) or 1,
                    "last_completed_page": _coerce_int(progress.get("last_completed_page")),
                    "discovered_total_matches": discovered_total_matches,
                    "discovered_total_pages": _coerce_int(progress.get("discovered_total_pages")),
                    "remaining_matches_estimate": (
                        max(discovered_total_matches - matches_count, 0)
                        if discovered_total_matches is not None
                        else None
                    ),
                    "archive_exhausted": bool(progress.get("archive_exhausted")),
                    "last_run": progress.get("last_run"),
                },
                "time_range": {
                    "start": first_match_at,
                    "end": last_match_at,
                },
            }
        )
    return items


def list_historical_coverage_report(
    *,
    server_slug: str | None = None,
    db_path: Path | None = None,
) -> list[dict[str, object]]:
    """Return persisted coverage metrics used to validate historical bootstrap depth."""
    resolved_path = initialize_historical_storage(db_path=db_path)
    where_clause = ""
    params: list[object] = []
    if server_slug:
        where_clause = "WHERE historical_servers.slug = ?"
        params.append(server_slug)

    with _connect(resolved_path) as connection:
        rows = connection.execute(
            f"""
            SELECT
                historical_servers.slug AS server_slug,
                historical_servers.display_name AS server_name,
                historical_servers.scoreboard_base_url AS scoreboard_base_url,
                historical_servers.server_number AS server_number,
                COUNT(DISTINCT historical_matches.id) AS imported_matches_count,
                COUNT(DISTINCT historical_players.id) AS unique_players,
                COUNT(DISTINCT historical_player_match_stats.id) AS player_stat_rows,
                MIN(COALESCE(historical_matches.ended_at, historical_matches.started_at, historical_matches.created_at_source)) AS first_match_at,
                MAX(COALESCE(historical_matches.ended_at, historical_matches.started_at, historical_matches.created_at_source)) AS last_match_at
            FROM historical_servers
            LEFT JOIN historical_matches
                ON historical_matches.historical_server_id = historical_servers.id
            LEFT JOIN historical_player_match_stats
                ON historical_player_match_stats.historical_match_id = historical_matches.id
            LEFT JOIN historical_players
                ON historical_players.id = historical_player_match_stats.historical_player_id
            {where_clause}
            GROUP BY historical_servers.id
            ORDER BY historical_servers.server_number ASC, historical_servers.slug ASC
            """,
            params,
        ).fetchall()

    items: list[dict[str, object]] = []
    progress_by_server = {
        item["server"]["slug"]: item
        for item in list_historical_backfill_progress(
            server_slug=server_slug,
            db_path=resolved_path,
        )
    }
    for row in rows:
        first_match_at = _stringify(row["first_match_at"])
        last_match_at = _stringify(row["last_match_at"])
        progress = progress_by_server.get(str(row["server_slug"]), {})
        items.append(
            {
                "server": {
                    "slug": row["server_slug"],
                    "name": row["server_name"],
                    "server_number": row["server_number"],
                    "scoreboard_base_url": row["scoreboard_base_url"],
                },
                "imported_matches_count": int(row["imported_matches_count"] or 0),
                "unique_players": int(row["unique_players"] or 0),
                "player_stat_rows": int(row["player_stat_rows"] or 0),
                "first_match_at": first_match_at,
                "last_match_at": last_match_at,
                "coverage_days": _calculate_coverage_days(first_match_at, last_match_at),
                "backfill": {
                    "next_page": _coerce_int(progress.get("next_page")) or 1,
                    "last_completed_page": _coerce_int(progress.get("last_completed_page")),
                    "discovered_total_matches": _coerce_int(
                        progress.get("discovered_total_matches")
                    ),
                    "discovered_total_pages": _coerce_int(
                        progress.get("discovered_total_pages")
                    ),
                    "archive_exhausted": bool(progress.get("archive_exhausted")),
                    "last_run": progress.get("last_run"),
                },
            }
        )
    return items


def get_historical_player_profile(
    player_id: str,
    *,
    db_path: Path | None = None,
) -> dict[str, object] | None:
    """Return aggregate historical metrics for one player identity."""
    resolved_player_id = player_id.strip()
    if not resolved_player_id:
        return None

    resolved_path = initialize_historical_storage(db_path=db_path)
    with _connect(resolved_path) as connection:
        player_row = connection.execute(
            """
            SELECT
                historical_players.id,
                historical_players.stable_player_key,
                historical_players.display_name,
                historical_players.steam_id,
                historical_players.source_player_id,
                COUNT(DISTINCT historical_matches.id) AS matches_count,
                COALESCE(SUM(historical_player_match_stats.kills), 0) AS total_kills,
                MIN(COALESCE(historical_matches.ended_at, historical_matches.started_at, historical_matches.created_at_source)) AS first_match_at,
                MAX(COALESCE(historical_matches.ended_at, historical_matches.started_at, historical_matches.created_at_source)) AS last_match_at
            FROM historical_players
            LEFT JOIN historical_player_match_stats
                ON historical_player_match_stats.historical_player_id = historical_players.id
            LEFT JOIN historical_matches
                ON historical_matches.id = historical_player_match_stats.historical_match_id
            WHERE historical_players.stable_player_key = ?
               OR historical_players.steam_id = ?
               OR historical_players.source_player_id = ?
            GROUP BY historical_players.id
            ORDER BY historical_players.display_name ASC
            LIMIT 1
            """,
            (resolved_player_id, resolved_player_id, resolved_player_id),
        ).fetchone()
        if player_row is None:
            return None

        server_rows = connection.execute(
            """
            SELECT
                historical_servers.slug AS server_slug,
                historical_servers.display_name AS server_name,
                COUNT(DISTINCT historical_matches.id) AS matches_count,
                COALESCE(SUM(historical_player_match_stats.kills), 0) AS total_kills,
                MIN(COALESCE(historical_matches.ended_at, historical_matches.started_at, historical_matches.created_at_source)) AS first_match_at,
                MAX(COALESCE(historical_matches.ended_at, historical_matches.started_at, historical_matches.created_at_source)) AS last_match_at
            FROM historical_player_match_stats
            INNER JOIN historical_matches
                ON historical_matches.id = historical_player_match_stats.historical_match_id
            INNER JOIN historical_servers
                ON historical_servers.id = historical_matches.historical_server_id
            WHERE historical_player_match_stats.historical_player_id = ?
            GROUP BY historical_servers.id
            ORDER BY total_kills DESC, historical_servers.server_number ASC, historical_servers.slug ASC
            """,
            (player_row["id"],),
        ).fetchall()

    return {
        "player": {
            "stable_player_key": player_row["stable_player_key"],
            "name": player_row["display_name"],
            "steam_id": player_row["steam_id"],
            "source_player_id": player_row["source_player_id"],
        },
        "matches_count": int(player_row["matches_count"] or 0),
        "total_kills": int(player_row["total_kills"] or 0),
        "time_range": {
            "start": player_row["first_match_at"],
            "end": player_row["last_match_at"],
        },
        "servers": [
            {
                "server": {
                    "slug": row["server_slug"],
                    "name": row["server_name"],
                },
                "matches_count": int(row["matches_count"] or 0),
                "total_kills": int(row["total_kills"] or 0),
                "time_range": {
                    "start": row["first_match_at"],
                    "end": row["last_match_at"],
                },
            }
            for row in server_rows
        ],
    }


def list_weekly_leaderboard(
    *,
    limit: int = 10,
    server_id: str | None = None,
    metric: str = "kills",
    db_path: Path | None = None,
) -> dict[str, object]:
    """Return ranked weekly leaderboard totals from persisted historical match stats."""
    resolved_path = initialize_historical_storage(db_path=db_path)
    window_end = datetime.now(timezone.utc)
    window_start = window_end - timedelta(days=DEFAULT_WEEKLY_WINDOW_DAYS)
    normalized_metric = metric.strip() if isinstance(metric, str) else ""
    if normalized_metric not in SUPPORTED_WEEKLY_LEADERBOARD_METRICS:
        raise ValueError(f"Unsupported weekly leaderboard metric: {metric}")

    where_clauses = [
        "historical_matches.ended_at IS NOT NULL",
        "historical_matches.ended_at >= ?",
        "historical_matches.ended_at <= ?",
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

    metric_sum_expression = {
        "kills": "COALESCE(SUM(historical_player_match_stats.kills), 0)",
        "deaths": "COALESCE(SUM(historical_player_match_stats.deaths), 0)",
        "support": "COALESCE(SUM(historical_player_match_stats.support), 0)",
        "matches_over_100_kills": (
            "COALESCE(SUM(CASE WHEN COALESCE(historical_player_match_stats.kills, 0) >= 100 "
            "THEN 1 ELSE 0 END), 0)"
        ),
    }[normalized_metric]

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
                    {metric_sum_expression} AS metric_value,
                    ROW_NUMBER() OVER (
                        PARTITION BY historical_servers.slug
                        ORDER BY
                            {metric_sum_expression} DESC,
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
                "metric": normalized_metric,
                "ranking_position": int(row["ranking_position"]),
                "metric_value": int(row["metric_value"] or 0),
                "matches_considered": int(row["matches_count"] or 0),
            }
        )

    return {
        "metric": normalized_metric,
        "window_start": window_start.isoformat().replace("+00:00", "Z"),
        "window_end": window_end.isoformat().replace("+00:00", "Z"),
        "items": items,
    }


def list_weekly_top_kills(
    *,
    limit: int = 10,
    server_id: str | None = None,
    db_path: Path | None = None,
) -> dict[str, object]:
    """Return ranked weekly kill totals from persisted historical match stats."""
    result = list_weekly_leaderboard(
        limit=limit,
        server_id=server_id,
        metric="kills",
        db_path=db_path,
    )
    items = []
    for item in result["items"]:
        legacy_item = dict(item)
        legacy_item["weekly_kills"] = legacy_item["metric_value"]
        items.append(legacy_item)

    return {
        "metric": "kills",
        "window_start": result["window_start"],
        "window_end": result["window_end"],
        "items": items,
    }


def _connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def _resolve_match_winner(allied_score: object, axis_score: object) -> str | None:
    allied = _coerce_int(allied_score)
    axis = _coerce_int(axis_score)
    if allied is None or axis is None:
        return None
    if allied > axis:
        return "allies"
    if axis > allied:
        return "axis"
    return "draw"


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
        SELECT id, stable_player_key, display_name, steam_id, source_player_id
        FROM historical_players
        ORDER BY id ASC
        """
    ).fetchall()
    for row in rows:
        player_id = int(row["id"])
        canonical_key, steam_id, source_player_id, display_name = _canonicalize_stored_player_row(row)
        existing = connection.execute(
            """
            SELECT id
            FROM historical_players
            WHERE stable_player_key = ?
            """,
            (canonical_key,),
        ).fetchone()
        if existing is not None and int(existing["id"]) != player_id:
            _merge_historical_player_rows(
                connection,
                source_player_id=player_id,
                target_player_id=int(existing["id"]),
                display_name=display_name,
                steam_id=steam_id,
                source_ref=source_player_id,
            )
            continue

        connection.execute(
            """
            UPDATE historical_players
            SET stable_player_key = ?,
                display_name = ?,
                steam_id = ?,
                source_player_id = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (canonical_key, display_name, steam_id, source_player_id, player_id),
        )


def _normalize_historical_match_identities(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT
            historical_matches.id,
            historical_matches.historical_server_id,
            historical_matches.external_match_id,
            historical_matches.started_at,
            historical_matches.ended_at,
            historical_matches.created_at_source,
            historical_matches.map_name,
            historical_matches.map_pretty_name,
            COUNT(historical_player_match_stats.id) AS player_count
        FROM historical_matches
        LEFT JOIN historical_player_match_stats
            ON historical_player_match_stats.historical_match_id = historical_matches.id
        WHERE historical_matches.started_at IS NOT NULL
        GROUP BY historical_matches.id
        ORDER BY historical_matches.historical_server_id ASC, historical_matches.started_at ASC, historical_matches.id ASC
        """
    ).fetchall()

    grouped_matches: dict[tuple[int, str, str], list[sqlite3.Row]] = {}
    for row in rows:
        group_key = (
            int(row["historical_server_id"]),
            str(row["started_at"]),
            _normalize_match_identity_label(row["map_pretty_name"] or row["map_name"]),
        )
        grouped_matches.setdefault(group_key, []).append(row)

    for grouped_rows in grouped_matches.values():
        if len(grouped_rows) < 2:
            continue
        target_row = max(grouped_rows, key=_match_identity_preference)
        for source_row in grouped_rows:
            if int(source_row["id"]) == int(target_row["id"]):
                continue
            _merge_historical_match_rows(
                connection,
                source_match_id=int(source_row["id"]),
                target_match_id=int(target_row["id"]),
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
    stable_player_key, steam_id, source_player_id = _derive_player_identity(player_payload)
    display_name = _normalize_player_display_name(player_payload.get("player")) or "Unknown player"
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
    stable_player_key, _, _ = _derive_player_identity(player_payload)
    return stable_player_key


def _derive_player_identity(player_payload: Mapping[str, object]) -> tuple[str, str | None, str | None]:
    steam_id = _stringify(_get_nested(player_payload, "steaminfo", "profile", "steamid"))
    source_player_id = _stringify(player_payload.get("player_id"))
    steaminfo_id = _stringify(_get_nested(player_payload, "steaminfo", "id"))

    if steam_id:
        return f"steam:{steam_id}", steam_id, source_player_id
    if _is_probable_steam_id(source_player_id):
        return f"steam:{source_player_id}", source_player_id, source_player_id
    if source_player_id:
        return f"crcon-player:{source_player_id}", None, source_player_id
    if steaminfo_id:
        return f"steaminfo:{steaminfo_id}", None, None

    player_name = _normalize_player_display_name(player_payload.get("player")) or "unknown-player"
    return f"name:{_normalize_name_key(player_name)}", None, None


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


def _normalize_player_display_name(value: object) -> str | None:
    text = _stringify(value)
    if not text:
        return None
    return " ".join(text.split())


def _normalize_name_key(player_name: str) -> str:
    normalized_name = "".join(
        character.lower() if character.isalnum() else "-"
        for character in player_name
    )
    compact_name = "-".join(part for part in normalized_name.split("-") if part)
    return compact_name or "unknown-player"


def _is_probable_steam_id(value: object) -> bool:
    text = _stringify(value)
    return bool(text and text.isdigit() and len(text) >= 16)


def _canonicalize_stored_player_row(
    row: sqlite3.Row,
) -> tuple[str, str | None, str | None, str]:
    stable_player_key = _stringify(row["stable_player_key"])
    display_name = _normalize_player_display_name(row["display_name"]) or "Unknown player"
    steam_id = _stringify(row["steam_id"])
    source_player_id = _stringify(row["source_player_id"])

    if _is_probable_steam_id(steam_id):
        return f"steam:{steam_id}", steam_id, source_player_id, display_name
    if _is_probable_steam_id(source_player_id):
        return f"steam:{source_player_id}", source_player_id, source_player_id, display_name
    if source_player_id:
        return f"crcon-player:{source_player_id}", None, source_player_id, display_name
    if stable_player_key and stable_player_key.startswith("steaminfo:"):
        return stable_player_key, None, None, display_name
    if stable_player_key and stable_player_key.startswith("name:"):
        return stable_player_key, None, None, display_name
    if stable_player_key and stable_player_key.startswith("steam:"):
        return stable_player_key, steam_id, source_player_id, display_name
    if stable_player_key and stable_player_key.startswith("crcon-player:"):
        source_ref = stable_player_key.removeprefix("crcon-player:")
        return stable_player_key, None, source_player_id or source_ref, display_name
    if stable_player_key:
        if _is_probable_steam_id(stable_player_key):
            return f"steam:{stable_player_key}", stable_player_key, source_player_id, display_name
        return f"crcon-player:{stable_player_key}", None, source_player_id or stable_player_key, display_name
    return f"name:{_normalize_name_key(display_name)}", None, None, display_name


def _merge_historical_player_rows(
    connection: sqlite3.Connection,
    *,
    source_player_id: int,
    target_player_id: int,
    display_name: str,
    steam_id: str | None,
    source_ref: str | None,
) -> None:
    target_row = connection.execute(
        """
        SELECT display_name, steam_id, source_player_id, first_seen_at, last_seen_at
        FROM historical_players
        WHERE id = ?
        """,
        (target_player_id,),
    ).fetchone()
    if target_row is None:
        return

    connection.execute(
        """
        UPDATE historical_players
        SET display_name = ?,
            steam_id = ?,
            source_player_id = ?,
            first_seen_at = MIN(first_seen_at, ?),
            last_seen_at = MAX(last_seen_at, ?),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            _pick_preferred_display_name(target_row["display_name"], display_name),
            _pick_preferred_steam_id(target_row["steam_id"], steam_id),
            _pick_preferred_source_player_id(target_row["source_player_id"], source_ref),
            connection.execute(
                "SELECT first_seen_at FROM historical_players WHERE id = ?",
                (source_player_id,),
            ).fetchone()["first_seen_at"],
            connection.execute(
                "SELECT last_seen_at FROM historical_players WHERE id = ?",
                (source_player_id,),
            ).fetchone()["last_seen_at"],
            target_player_id,
        ),
    )

    stats_rows = connection.execute(
        """
        SELECT *
        FROM historical_player_match_stats
        WHERE historical_player_id = ?
        ORDER BY id ASC
        """,
        (source_player_id,),
    ).fetchall()
    for stat_row in stats_rows:
        existing = connection.execute(
            """
            SELECT *
            FROM historical_player_match_stats
            WHERE historical_match_id = ? AND historical_player_id = ?
            """,
            (stat_row["historical_match_id"], target_player_id),
        ).fetchone()
        if existing is None:
            connection.execute(
                """
                UPDATE historical_player_match_stats
                SET historical_player_id = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (target_player_id, stat_row["id"]),
            )
            continue

        _merge_player_match_stats_row(connection, existing["id"], stat_row)
        connection.execute(
            "DELETE FROM historical_player_match_stats WHERE id = ?",
            (stat_row["id"],),
        )

    connection.execute(
        "DELETE FROM historical_players WHERE id = ?",
        (source_player_id,),
    )


def _normalize_match_identity_label(value: object) -> str:
    text = _stringify(value) or "unknown-map"
    return " ".join(text.lower().split())


def _match_identity_preference(row: sqlite3.Row) -> tuple[int, int, int, str, int]:
    return (
        1 if _stringify(row["ended_at"]) else 0,
        1 if (_stringify(row["external_match_id"]) or "").isdigit() else 0,
        int(row["player_count"] or 0),
        _stringify(row["created_at_source"]) or "",
        int(row["id"]),
    )


def _merge_historical_match_rows(
    connection: sqlite3.Connection,
    *,
    source_match_id: int,
    target_match_id: int,
) -> None:
    source_row = connection.execute(
        "SELECT * FROM historical_matches WHERE id = ?",
        (source_match_id,),
    ).fetchone()
    target_row = connection.execute(
        "SELECT * FROM historical_matches WHERE id = ?",
        (target_match_id,),
    ).fetchone()
    if source_row is None or target_row is None:
        return

    connection.execute(
        """
        UPDATE historical_matches
        SET historical_map_id = COALESCE(historical_map_id, ?),
            created_at_source = COALESCE(created_at_source, ?),
            started_at = COALESCE(started_at, ?),
            ended_at = COALESCE(ended_at, ?),
            map_name = COALESCE(map_name, ?),
            map_pretty_name = COALESCE(map_pretty_name, ?),
            game_mode = COALESCE(game_mode, ?),
            image_name = COALESCE(image_name, ?),
            allied_score = COALESCE(allied_score, ?),
            axis_score = COALESCE(axis_score, ?),
            raw_payload_ref = COALESCE(raw_payload_ref, ?),
            last_seen_at = MAX(last_seen_at, ?),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            source_row["historical_map_id"],
            source_row["created_at_source"],
            source_row["started_at"],
            source_row["ended_at"],
            source_row["map_name"],
            source_row["map_pretty_name"],
            source_row["game_mode"],
            source_row["image_name"],
            source_row["allied_score"],
            source_row["axis_score"],
            source_row["raw_payload_ref"],
            source_row["last_seen_at"],
            target_match_id,
        ),
    )

    stats_rows = connection.execute(
        """
        SELECT *
        FROM historical_player_match_stats
        WHERE historical_match_id = ?
        ORDER BY id ASC
        """,
        (source_match_id,),
    ).fetchall()
    for stat_row in stats_rows:
        existing = connection.execute(
            """
            SELECT *
            FROM historical_player_match_stats
            WHERE historical_match_id = ? AND historical_player_id = ?
            """,
            (target_match_id, stat_row["historical_player_id"]),
        ).fetchone()
        if existing is None:
            connection.execute(
                """
                UPDATE historical_player_match_stats
                SET historical_match_id = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (target_match_id, stat_row["id"]),
            )
            continue

        _merge_player_match_stats_row(connection, existing["id"], stat_row)
        connection.execute(
            "DELETE FROM historical_player_match_stats WHERE id = ?",
            (stat_row["id"],),
        )

    connection.execute(
        "DELETE FROM historical_matches WHERE id = ?",
        (source_match_id,),
    )


def _merge_player_match_stats_row(
    connection: sqlite3.Connection,
    target_stat_id: int,
    source_row: sqlite3.Row,
) -> None:
    target_row = connection.execute(
        "SELECT * FROM historical_player_match_stats WHERE id = ?",
        (target_stat_id,),
    ).fetchone()
    if target_row is None:
        return

    connection.execute(
        """
        UPDATE historical_player_match_stats
        SET match_player_ref = COALESCE(match_player_ref, ?),
            team_side = COALESCE(team_side, ?),
            level = ?,
            kills = ?,
            deaths = ?,
            teamkills = ?,
            time_seconds = ?,
            kills_per_minute = ?,
            deaths_per_minute = ?,
            kill_death_ratio = ?,
            combat = ?,
            offense = ?,
            defense = ?,
            support = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            source_row["match_player_ref"],
            source_row["team_side"],
            _max_int_value(target_row["level"], source_row["level"]),
            _max_int_value(target_row["kills"], source_row["kills"]),
            _max_int_value(target_row["deaths"], source_row["deaths"]),
            _max_int_value(target_row["teamkills"], source_row["teamkills"]),
            _max_int_value(target_row["time_seconds"], source_row["time_seconds"]),
            _max_float_value(target_row["kills_per_minute"], source_row["kills_per_minute"]),
            _max_float_value(target_row["deaths_per_minute"], source_row["deaths_per_minute"]),
            _max_float_value(target_row["kill_death_ratio"], source_row["kill_death_ratio"]),
            _max_int_value(target_row["combat"], source_row["combat"]),
            _max_int_value(target_row["offense"], source_row["offense"]),
            _max_int_value(target_row["defense"], source_row["defense"]),
            _max_int_value(target_row["support"], source_row["support"]),
            target_stat_id,
        ),
    )


def _pick_preferred_display_name(current_value: object, incoming_value: object) -> str:
    current_name = _normalize_player_display_name(current_value)
    incoming_name = _normalize_player_display_name(incoming_value)
    if not current_name:
        return incoming_name or "Unknown player"
    if not incoming_name:
        return current_name
    if len(incoming_name) > len(current_name):
        return incoming_name
    return current_name


def _pick_preferred_steam_id(current_value: object, incoming_value: object) -> str | None:
    current_id = _stringify(current_value)
    incoming_id = _stringify(incoming_value)
    if _is_probable_steam_id(current_id):
        return current_id
    if _is_probable_steam_id(incoming_id):
        return incoming_id
    return None


def _pick_preferred_source_player_id(current_value: object, incoming_value: object) -> str | None:
    current_id = _stringify(current_value)
    incoming_id = _stringify(incoming_value)
    if current_id:
        return current_id
    return incoming_id


def _max_int_value(current_value: object, incoming_value: object) -> int | None:
    current_number = _coerce_int(current_value)
    incoming_number = _coerce_int(incoming_value)
    if current_number is None:
        return incoming_number
    if incoming_number is None:
        return current_number
    return max(current_number, incoming_number)


def _max_float_value(current_value: object, incoming_value: object) -> float | None:
    current_number = _coerce_float(current_value)
    incoming_number = _coerce_float(incoming_value)
    if current_number is None:
        return incoming_number
    if incoming_number is None:
        return current_number
    return max(current_number, incoming_number)


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


def _calculate_coverage_days(
    first_match_at: str | None,
    last_match_at: str | None,
) -> float | None:
    if not first_match_at or not last_match_at:
        return None
    try:
        delta = _parse_timestamp(last_match_at) - _parse_timestamp(first_match_at)
    except ValueError:
        return None
    return round(delta.total_seconds() / 86400, 2)


def _classify_coverage_status(
    matches_count: int,
    coverage_days: float | None,
) -> str:
    if matches_count <= 0:
        return "empty"
    if coverage_days is None:
        return "range-unknown"
    if coverage_days < DEFAULT_WEEKLY_WINDOW_DAYS:
        return "under-week"
    return "week-plus"


def _get_nested(payload: Mapping[str, object], *path: str) -> object:
    current: object = payload
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
