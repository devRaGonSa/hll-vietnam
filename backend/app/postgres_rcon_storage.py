"""PostgreSQL persistence for the phase-1 RCON historical pipeline."""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from .config import get_database_url
from .normalizers import normalize_map_name
from .rcon_client import load_rcon_targets


COMPETITIVE_WINDOW_GAP_SECONDS = 1800
COMPETITIVE_MODE_PARTIAL = "partial"
COMPETITIVE_MODE_APPROXIMATE = "approximate"
COMPETITIVE_MODE_EXACT = "exact"
RUNNING_HISTORICAL_CAPTURE_CONFLICT_MESSAGE = (
    "historical materialization capture already running"
)
HISTORICAL_CAPTURE_ADVISORY_LOCK_KEY = 2710001
DROP_LEGACY_HISTORICAL_GUARD_INDEX_SQL = """
DROP INDEX IF EXISTS idx_rcon_historical_single_running_historical;
"""


RCON_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS rcon_historical_targets (
    id BIGSERIAL PRIMARY KEY,
    target_key TEXT NOT NULL UNIQUE,
    external_server_id TEXT,
    display_name TEXT NOT NULL,
    host TEXT NOT NULL,
    port INTEGER NOT NULL,
    region TEXT,
    game_port INTEGER,
    query_port INTEGER,
    source_name TEXT NOT NULL,
    last_configured_at TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rcon_historical_capture_runs (
    id BIGSERIAL PRIMARY KEY,
    mode TEXT NOT NULL,
    status TEXT NOT NULL,
    target_scope TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    targets_seen INTEGER NOT NULL DEFAULT 0,
    samples_inserted INTEGER NOT NULL DEFAULT 0,
    duplicate_samples INTEGER NOT NULL DEFAULT 0,
    failed_targets INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rcon_historical_samples (
    id BIGSERIAL PRIMARY KEY,
    target_id BIGINT NOT NULL REFERENCES rcon_historical_targets(id),
    capture_run_id BIGINT REFERENCES rcon_historical_capture_runs(id),
    captured_at TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    status TEXT NOT NULL,
    players INTEGER,
    max_players INTEGER,
    current_map TEXT,
    normalized_payload_json TEXT NOT NULL,
    raw_payload_json TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(target_id, captured_at)
);

CREATE TABLE IF NOT EXISTS rcon_historical_checkpoints (
    target_id BIGINT PRIMARY KEY REFERENCES rcon_historical_targets(id),
    last_successful_capture_at TEXT,
    last_sample_at TEXT,
    last_run_id BIGINT REFERENCES rcon_historical_capture_runs(id),
    last_run_status TEXT,
    last_error TEXT,
    last_error_at TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rcon_historical_competitive_windows (
    id BIGSERIAL PRIMARY KEY,
    target_id BIGINT NOT NULL REFERENCES rcon_historical_targets(id),
    session_key TEXT NOT NULL UNIQUE,
    source_kind TEXT NOT NULL,
    map_name TEXT,
    map_pretty_name TEXT,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    sample_count INTEGER NOT NULL DEFAULT 0,
    total_players INTEGER NOT NULL DEFAULT 0,
    peak_players INTEGER NOT NULL DEFAULT 0,
    last_players INTEGER,
    max_players INTEGER,
    status TEXT NOT NULL,
    confidence_mode TEXT NOT NULL,
    capabilities_json TEXT NOT NULL,
    latest_payload_json TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rcon_admin_log_events (
    id BIGSERIAL PRIMARY KEY,
    target_key TEXT NOT NULL,
    external_server_id TEXT,
    event_timestamp TEXT,
    server_time BIGINT,
    relative_time TEXT,
    event_type TEXT NOT NULL,
    raw_message TEXT NOT NULL,
    canonical_message TEXT NOT NULL,
    parsed_payload_json TEXT NOT NULL,
    raw_entry_json TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE NULLS NOT DISTINCT(target_key, server_time, canonical_message)
);

CREATE TABLE IF NOT EXISTS rcon_player_profile_snapshots (
    id BIGSERIAL PRIMARY KEY,
    target_key TEXT NOT NULL,
    external_server_id TEXT,
    player_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    source_server_time BIGINT NOT NULL,
    event_timestamp TEXT,
    first_seen TEXT,
    sessions INTEGER,
    matches_played INTEGER,
    play_time TEXT,
    total_kills INTEGER,
    total_deaths INTEGER,
    teamkills_done INTEGER,
    teamkills_received INTEGER,
    kd_ratio DOUBLE PRECISION,
    favorite_weapons_json TEXT NOT NULL DEFAULT '{}',
    victims_json TEXT NOT NULL DEFAULT '{}',
    nemesis_json TEXT NOT NULL DEFAULT '{}',
    averages_json TEXT NOT NULL DEFAULT '{}',
    sanctions_json TEXT NOT NULL DEFAULT '{}',
    raw_content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(target_key, player_id, source_server_time)
);

CREATE TABLE IF NOT EXISTS rcon_materialized_matches (
    id BIGSERIAL PRIMARY KEY,
    target_key TEXT NOT NULL,
    external_server_id TEXT,
    match_key TEXT NOT NULL,
    map_name TEXT,
    map_pretty_name TEXT,
    game_mode TEXT,
    started_server_time BIGINT,
    ended_server_time BIGINT,
    started_at TEXT,
    ended_at TEXT,
    allied_score INTEGER,
    axis_score INTEGER,
    winner TEXT,
    confidence_mode TEXT NOT NULL,
    source_basis TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(target_key, match_key)
);

CREATE TABLE IF NOT EXISTS rcon_match_player_stats (
    id BIGSERIAL PRIMARY KEY,
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
    first_seen_server_time BIGINT,
    last_seen_server_time BIGINT,
    player_active_seconds INTEGER,
    active_time_source TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(target_key, match_key, player_id)
);

CREATE TABLE IF NOT EXISTS rcon_annual_ranking_snapshots (
    id BIGSERIAL PRIMARY KEY,
    year INTEGER NOT NULL,
    server_key TEXT NOT NULL,
    metric TEXT NOT NULL,
    limit_size INTEGER NOT NULL DEFAULT 20,
    source_basis TEXT NOT NULL DEFAULT 'rcon-admin-log',
    window_start TEXT,
    window_end TEXT,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'ready',
    source_matches_count INTEGER NOT NULL DEFAULT 0,
    CHECK (limit_size > 0),
    CHECK (metric IN ('kills', 'deaths', 'teamkills', 'matches_considered', 'kd_ratio', 'kills_per_match')),
    UNIQUE (year, server_key, metric)
);

CREATE TABLE IF NOT EXISTS rcon_annual_ranking_snapshot_items (
    id BIGSERIAL PRIMARY KEY,
    snapshot_id BIGINT NOT NULL REFERENCES rcon_annual_ranking_snapshots(id) ON DELETE CASCADE,
    ranking_position INTEGER NOT NULL,
    player_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL DEFAULT 0,
    matches_considered INTEGER NOT NULL DEFAULT 0,
    kills BIGINT NOT NULL DEFAULT 0,
    deaths BIGINT NOT NULL DEFAULT 0,
    teamkills BIGINT NOT NULL DEFAULT 0,
    kd_ratio DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    UNIQUE(snapshot_id, ranking_position),
    UNIQUE(snapshot_id, player_id)
);

CREATE TABLE IF NOT EXISTS ranking_snapshots (
    id BIGSERIAL PRIMARY KEY,
    timeframe TEXT NOT NULL,
    server_id TEXT NOT NULL,
    metric TEXT NOT NULL,
    window_start TEXT NOT NULL,
    window_end TEXT NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source TEXT NOT NULL DEFAULT 'rcon-materialized-admin-log',
    snapshot_status TEXT NOT NULL DEFAULT 'ready',
    item_count INTEGER NOT NULL DEFAULT 0,
    limit_size INTEGER NOT NULL DEFAULT 20,
    source_matches_count INTEGER NOT NULL DEFAULT 0,
    freshness TEXT NOT NULL DEFAULT 'fresh',
    window_kind TEXT,
    window_label TEXT,
    error_message TEXT,
    UNIQUE(timeframe, server_id, metric, window_start, window_end)
);

CREATE TABLE IF NOT EXISTS ranking_snapshot_items (
    id BIGSERIAL PRIMARY KEY,
    snapshot_id BIGINT NOT NULL REFERENCES ranking_snapshots(id) ON DELETE CASCADE,
    ranking_position INTEGER NOT NULL,
    player_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL DEFAULT 0,
    matches_considered INTEGER NOT NULL DEFAULT 0,
    kills INTEGER NOT NULL DEFAULT 0,
    deaths INTEGER NOT NULL DEFAULT 0,
    teamkills INTEGER NOT NULL DEFAULT 0,
    kd_ratio DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    kills_per_match DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    UNIQUE(snapshot_id, ranking_position),
    UNIQUE(snapshot_id, player_id)
);

CREATE TABLE IF NOT EXISTS player_search_index (
    id BIGSERIAL PRIMARY KEY,
    server_id TEXT NOT NULL,
    player_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    normalized_player_name TEXT NOT NULL,
    first_seen_at TEXT,
    last_seen_at TEXT,
    servers_seen TEXT NOT NULL DEFAULT '[]',
    matches_current_year INTEGER NOT NULL DEFAULT 0,
    kills_current_year INTEGER NOT NULL DEFAULT 0,
    deaths_current_year INTEGER NOT NULL DEFAULT 0,
    teamkills_current_year INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(server_id, player_id)
);

CREATE TABLE IF NOT EXISTS player_period_stats (
    id BIGSERIAL PRIMARY KEY,
    period_type TEXT NOT NULL,
    window_kind TEXT NOT NULL,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    server_id TEXT NOT NULL,
    player_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    matches_considered INTEGER NOT NULL DEFAULT 0,
    kills INTEGER NOT NULL DEFAULT 0,
    deaths INTEGER NOT NULL DEFAULT 0,
    teamkills INTEGER NOT NULL DEFAULT 0,
    ranking_position INTEGER,
    kd_ratio DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    kills_per_match DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    first_seen_at TEXT,
    last_seen_at TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(period_type, server_id, player_id)
);

CREATE TABLE IF NOT EXISTS rcon_scoreboard_match_candidates (
    id BIGSERIAL PRIMARY KEY,
    server_slug TEXT NOT NULL,
    external_match_id TEXT NOT NULL,
    started_at TEXT,
    ended_at TEXT,
    map_name TEXT,
    map_pretty_name TEXT,
    allied_score INTEGER,
    axis_score INTEGER,
    player_count INTEGER,
    match_url TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(server_slug, external_match_id)
);

CREATE INDEX IF NOT EXISTS idx_rcon_historical_samples_target_time
ON rcon_historical_samples(target_id, captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_rcon_historical_windows_target_time
ON rcon_historical_competitive_windows(target_id, last_seen_at DESC);
CREATE INDEX IF NOT EXISTS idx_rcon_admin_log_events_target_time
ON rcon_admin_log_events(target_key, server_time DESC);
CREATE INDEX IF NOT EXISTS idx_rcon_admin_log_events_type
ON rcon_admin_log_events(event_type);
CREATE INDEX IF NOT EXISTS idx_rcon_player_profile_snapshots_player
ON rcon_player_profile_snapshots(target_key, player_id, source_server_time DESC);
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
CREATE INDEX IF NOT EXISTS idx_rcon_match_player_stats_match
ON rcon_match_player_stats(target_key, match_key);
CREATE INDEX IF NOT EXISTS idx_rcon_match_player_stats_player_id_match
ON rcon_match_player_stats(player_id, target_key, match_key);
CREATE INDEX IF NOT EXISTS idx_rcon_annual_ranking_snapshots_year
ON rcon_annual_ranking_snapshots(year, server_key, metric);
CREATE INDEX IF NOT EXISTS idx_rcon_annual_ranking_snapshots_status
ON rcon_annual_ranking_snapshots(status);
CREATE INDEX IF NOT EXISTS idx_rcon_annual_snapshot_items_snapshot
ON rcon_annual_ranking_snapshot_items(snapshot_id, ranking_position);
CREATE INDEX IF NOT EXISTS idx_rcon_annual_snapshot_items_player
ON rcon_annual_ranking_snapshot_items(snapshot_id, player_id);
CREATE INDEX IF NOT EXISTS idx_ranking_snapshots_lookup
ON ranking_snapshots(timeframe, server_id, metric, snapshot_status, window_end DESC, generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_ranking_snapshot_items_snapshot
ON ranking_snapshot_items(snapshot_id, ranking_position);
CREATE INDEX IF NOT EXISTS idx_ranking_snapshot_items_player
ON ranking_snapshot_items(snapshot_id, player_id);
CREATE INDEX IF NOT EXISTS idx_player_search_index_name
ON player_search_index(server_id, normalized_player_name);
CREATE INDEX IF NOT EXISTS idx_player_search_index_last_seen
ON player_search_index(server_id, last_seen_at DESC);
CREATE INDEX IF NOT EXISTS idx_player_search_index_player
ON player_search_index(server_id, player_id);
CREATE INDEX IF NOT EXISTS idx_player_period_stats_player_period_server
ON player_period_stats(player_id, period_type, server_id);
CREATE INDEX IF NOT EXISTS idx_player_period_stats_server_period
ON player_period_stats(server_id, period_type);
CREATE INDEX IF NOT EXISTS idx_player_period_stats_last_seen
ON player_period_stats(last_seen_at DESC);
CREATE INDEX IF NOT EXISTS idx_player_period_stats_updated
ON player_period_stats(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_rcon_scoreboard_candidates_server_end
ON rcon_scoreboard_match_candidates(server_slug, ended_at DESC, started_at DESC);
"""

POSTGRES_ADMIN_LOG_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS rcon_admin_log_events (
    id BIGSERIAL PRIMARY KEY,
    target_key TEXT NOT NULL,
    external_server_id TEXT,
    event_timestamp TEXT,
    server_time BIGINT,
    relative_time TEXT,
    event_type TEXT NOT NULL,
    raw_message TEXT NOT NULL,
    canonical_message TEXT NOT NULL,
    parsed_payload_json TEXT NOT NULL,
    raw_entry_json TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE NULLS NOT DISTINCT(target_key, server_time, canonical_message)
);

CREATE TABLE IF NOT EXISTS rcon_player_profile_snapshots (
    id BIGSERIAL PRIMARY KEY,
    target_key TEXT NOT NULL,
    external_server_id TEXT,
    player_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    source_server_time BIGINT NOT NULL,
    event_timestamp TEXT,
    first_seen TEXT,
    sessions INTEGER,
    matches_played INTEGER,
    play_time TEXT,
    total_kills INTEGER,
    total_deaths INTEGER,
    teamkills_done INTEGER,
    teamkills_received INTEGER,
    kd_ratio DOUBLE PRECISION,
    favorite_weapons_json TEXT NOT NULL DEFAULT '{}',
    victims_json TEXT NOT NULL DEFAULT '{}',
    nemesis_json TEXT NOT NULL DEFAULT '{}',
    averages_json TEXT NOT NULL DEFAULT '{}',
    sanctions_json TEXT NOT NULL DEFAULT '{}',
    raw_content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(target_key, player_id, source_server_time)
);

CREATE INDEX IF NOT EXISTS idx_rcon_admin_log_events_target_time
ON rcon_admin_log_events(target_key, server_time DESC);
CREATE INDEX IF NOT EXISTS idx_rcon_admin_log_events_type
ON rcon_admin_log_events(event_type);
CREATE INDEX IF NOT EXISTS idx_rcon_player_profile_snapshots_player
ON rcon_player_profile_snapshots(target_key, player_id, source_server_time DESC);
"""

POSTGRES_ANNUAL_RANKING_SCHEMA_MIGRATION_SQL = """
ALTER TABLE rcon_annual_ranking_snapshot_items
ALTER COLUMN metric_value TYPE DOUBLE PRECISION USING metric_value::double precision;

DO $$
DECLARE
    constraint_record record;
BEGIN
    FOR constraint_record IN
        SELECT con.conname
        FROM pg_constraint AS con
        JOIN pg_class AS rel ON rel.oid = con.conrelid
        JOIN pg_namespace AS nsp ON nsp.oid = rel.relnamespace
        WHERE rel.relname = 'rcon_annual_ranking_snapshots'
          AND con.contype = 'c'
          AND pg_get_constraintdef(con.oid) LIKE '%metric%'
    LOOP
        EXECUTE format(
            'ALTER TABLE rcon_annual_ranking_snapshots DROP CONSTRAINT %I',
            constraint_record.conname
        );
    END LOOP;

    ALTER TABLE rcon_annual_ranking_snapshots
    ADD CONSTRAINT rcon_annual_ranking_snapshots_metric_check
    CHECK (metric IN (
        'kills',
        'deaths',
        'teamkills',
        'matches_considered',
        'kd_ratio',
        'kills_per_match'
    ));
END $$;
"""

POSTGRES_RCON_MATCH_PLAYER_STATS_ACTIVE_TIME_MIGRATION_SQL = """
ALTER TABLE rcon_match_player_stats
ADD COLUMN IF NOT EXISTS player_active_seconds INTEGER;

ALTER TABLE rcon_match_player_stats
ADD COLUMN IF NOT EXISTS active_time_source TEXT;
"""


def initialize_postgres_rcon_storage() -> None:
    """Create deterministic PostgreSQL schema for migrated RCON domains."""
    with connect_postgres() as connection:
        with connection.cursor() as cursor:
            cursor.execute(DROP_LEGACY_HISTORICAL_GUARD_INDEX_SQL)
            cursor.execute(RCON_SCHEMA_SQL)
            cursor.execute(POSTGRES_ANNUAL_RANKING_SCHEMA_MIGRATION_SQL)
            cursor.execute(POSTGRES_RCON_MATCH_PLAYER_STATS_ACTIVE_TIME_MIGRATION_SQL)


def initialize_postgres_admin_log_storage() -> None:
    """Create only the PostgreSQL AdminLog structures used by the live worker."""
    with connect_postgres() as connection:
        with connection.cursor() as cursor:
            cursor.execute(POSTGRES_ADMIN_LOG_SCHEMA_SQL)


@contextmanager
def connect_postgres():
    """Yield one PostgreSQL connection with dict-shaped rows."""
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as error:  # pragma: no cover - dependency is environment-specific
        raise RuntimeError("psycopg is required when HLL_BACKEND_DATABASE_URL is set.") from error

    database_url = get_database_url()
    if not database_url:
        raise RuntimeError("HLL_BACKEND_DATABASE_URL is required for PostgreSQL RCON storage.")
    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        yield connection


class PostgresCompatConnection:
    """Small DB-API shim for RCON SQL shared with SQLite functions."""

    def __init__(self, connection: Any):
        self.connection = connection

    def execute(self, sql: str, params: Iterable[object] | None = None):
        normalized = sql.replace("server_time IS ?", "server_time IS NOT DISTINCT FROM ?")
        normalized = normalized.replace("?", "%s")
        return self.connection.execute(normalized, tuple(params or ()))


@contextmanager
def connect_postgres_compat(*, initialize: bool = True):
    """Yield a query shim that accepts the phase-1 SQLite-style placeholders."""
    if initialize:
        initialize_postgres_rcon_storage()
    with connect_postgres() as connection:
        yield PostgresCompatConnection(connection)


@contextmanager
def postgres_historical_capture_advisory_guard() -> Iterator[bool]:
    """Hold one PostgreSQL advisory lock for the heavy historical capture path."""
    with connect_postgres() as connection:
        row = connection.execute(
            "SELECT pg_try_advisory_lock(%s) AS acquired",
            (HISTORICAL_CAPTURE_ADVISORY_LOCK_KEY,),
        ).fetchone()
        acquired = bool(row and row["acquired"])
        if not acquired:
            yield False
            return
        try:
            yield True
        finally:
            connection.execute(
                "SELECT pg_advisory_unlock(%s)",
                (HISTORICAL_CAPTURE_ADVISORY_LOCK_KEY,),
            )


def start_capture_run(*, mode: str, target_scope: str) -> int:
    initialize_postgres_rcon_storage()
    with connect_postgres() as connection:
        row = connection.execute(
            """
            INSERT INTO rcon_historical_capture_runs (mode, status, target_scope, started_at)
            VALUES (%s, 'running', %s, %s)
            RETURNING id
            """,
            (mode, target_scope, _utc_now_iso()),
        ).fetchone()
    return int(row["id"])


def finalize_capture_run(
    run_id: int,
    *,
    status: str,
    targets_seen: int,
    samples_inserted: int,
    duplicate_samples: int,
    failed_targets: int,
    notes: str | None,
) -> None:
    initialize_postgres_rcon_storage()
    with connect_postgres() as connection:
        connection.execute(
            """
            UPDATE rcon_historical_capture_runs
            SET status = %s,
                completed_at = %s,
                targets_seen = %s,
                samples_inserted = %s,
                duplicate_samples = %s,
                failed_targets = %s,
                notes = %s
            WHERE id = %s
            """,
            (
                status,
                _utc_now_iso(),
                targets_seen,
                samples_inserted,
                duplicate_samples,
                failed_targets,
                notes,
                run_id,
            ),
        )


def persist_sample(
    *,
    run_id: int,
    captured_at: str,
    target: Mapping[str, object],
    normalized_payload: Mapping[str, object],
    raw_payload: Mapping[str, object] | None,
) -> dict[str, int]:
    initialize_postgres_rcon_storage()
    with connect_postgres() as connection:
        target_id = _upsert_target(connection, target=target)
        row = connection.execute(
            """
            INSERT INTO rcon_historical_samples (
                target_id, capture_run_id, captured_at, source_kind, status, players,
                max_players, current_map, normalized_payload_json, raw_payload_json
            ) VALUES (%s, %s, %s, 'rcon-live-sample', %s, %s, %s, %s, %s, %s)
            ON CONFLICT(target_id, captured_at) DO NOTHING
            RETURNING id
            """,
            (
                target_id,
                run_id,
                captured_at,
                normalized_payload.get("status") or "unknown",
                normalized_payload.get("players"),
                normalized_payload.get("max_players"),
                normalized_payload.get("current_map"),
                json.dumps(dict(normalized_payload), separators=(",", ":")),
                json.dumps(dict(raw_payload), separators=(",", ":")) if raw_payload else None,
            ),
        ).fetchone()
        inserted = int(row is not None)
        _upsert_checkpoint_success(
            connection,
            target_id=target_id,
            run_id=run_id,
            captured_at=captured_at,
        )
        if inserted:
            _upsert_competitive_window(
                connection,
                target_id=target_id,
                captured_at=captured_at,
                normalized_payload=normalized_payload,
            )
    return {"samples_inserted": inserted, "duplicate_samples": 0 if inserted else 1}


def mark_capture_failure(
    *,
    run_id: int,
    target: Mapping[str, object],
    error_message: str,
) -> None:
    initialize_postgres_rcon_storage()
    with connect_postgres() as connection:
        target_id = _upsert_target(connection, target=target)
        connection.execute(
            """
            INSERT INTO rcon_historical_checkpoints (
                target_id, last_run_id, last_run_status, last_error, last_error_at
            ) VALUES (%s, %s, 'failed', %s, %s)
            ON CONFLICT(target_id) DO UPDATE SET
                last_run_id = EXCLUDED.last_run_id,
                last_run_status = EXCLUDED.last_run_status,
                last_error = EXCLUDED.last_error,
                last_error_at = EXCLUDED.last_error_at,
                updated_at = CURRENT_TIMESTAMP
            """,
            (target_id, run_id, error_message, _utc_now_iso()),
        )


def list_target_statuses() -> list[dict[str, object]]:
    rows = _fetchall(
        """
        SELECT
            targets.target_key,
            targets.external_server_id,
            targets.display_name,
            targets.host,
            targets.port,
            targets.region,
            targets.source_name,
            checkpoints.last_successful_capture_at,
            checkpoints.last_sample_at,
            checkpoints.last_run_id,
            checkpoints.last_run_status,
            checkpoints.last_error,
            checkpoints.last_error_at,
            (SELECT MIN(samples.captured_at) FROM rcon_historical_samples AS samples
             WHERE samples.target_id = targets.id) AS first_sample_at,
            (SELECT MAX(samples.captured_at) FROM rcon_historical_samples AS samples
             WHERE samples.target_id = targets.id) AS latest_sample_at,
            (SELECT COUNT(*) FROM rcon_historical_samples AS samples
             WHERE samples.target_id = targets.id) AS sample_count
        FROM rcon_historical_targets AS targets
        LEFT JOIN rcon_historical_checkpoints AS checkpoints
            ON checkpoints.target_id = targets.id
        ORDER BY targets.display_name ASC, targets.target_key ASC
        """
    )
    return [
        {
            **dict(row),
            "sample_count": int(row["sample_count"] or 0),
            "last_sample_at": row["latest_sample_at"] or row["last_sample_at"],
        }
        for row in rows
    ]


def list_recent_samples(*, target_key: str | None, limit: int) -> list[dict[str, object]]:
    where_clause, params = _target_where_clause(target_key)
    rows = _fetchall(
        f"""
        SELECT targets.target_key, targets.external_server_id, targets.display_name,
               targets.region, samples.captured_at, samples.status, samples.players,
               samples.max_players, samples.current_map
        FROM rcon_historical_samples AS samples
        INNER JOIN rcon_historical_targets AS targets ON targets.id = samples.target_id
        {where_clause}
        ORDER BY samples.captured_at DESC, targets.display_name ASC
        LIMIT %s
        """,
        [*params, limit],
    )
    return [dict(row) for row in rows]


def list_competitive_windows(*, target_key: str | None, limit: int) -> list[dict[str, object]]:
    where_clause, params = _target_where_clause(target_key)
    rows = _fetchall(
        f"""
        SELECT targets.target_key, targets.external_server_id, targets.display_name,
               targets.region, windows.session_key, windows.map_name,
               windows.map_pretty_name, windows.first_seen_at, windows.last_seen_at,
               windows.sample_count, windows.total_players, windows.peak_players,
               windows.last_players, windows.max_players, windows.status,
               windows.confidence_mode, windows.capabilities_json,
               windows.latest_payload_json
        FROM rcon_historical_competitive_windows AS windows
        INNER JOIN rcon_historical_targets AS targets ON targets.id = windows.target_id
        {where_clause}
        ORDER BY windows.last_seen_at DESC, targets.display_name ASC
        LIMIT %s
        """,
        [*params, limit],
    )
    return [_serialize_window(row) for row in rows]


def count_samples_since(since: str | None) -> int:
    if not since:
        return 0
    row = _fetchone(
        "SELECT COUNT(*) AS sample_count FROM rcon_historical_samples WHERE captured_at > %s",
        (since,),
    )
    return int(row["sample_count"] or 0) if row else 0


def list_competitive_summary_rows(*, target_key: str | None) -> list[dict[str, object]]:
    where_clause, params = _target_where_clause(target_key)
    rows = _fetchall(
        f"""
        SELECT targets.target_key, targets.external_server_id, targets.display_name,
               targets.region, checkpoints.last_successful_capture_at,
               checkpoints.last_run_status, checkpoints.last_error,
               checkpoints.last_error_at, COUNT(windows.id) AS window_count,
               COALESCE(SUM(windows.sample_count), 0) AS sample_count,
               MIN(windows.first_seen_at) AS first_seen_at,
               MAX(windows.last_seen_at) AS last_seen_at,
               COALESCE(MAX(windows.peak_players), 0) AS peak_players
        FROM rcon_historical_targets AS targets
        LEFT JOIN rcon_historical_checkpoints AS checkpoints ON checkpoints.target_id = targets.id
        LEFT JOIN rcon_historical_competitive_windows AS windows ON windows.target_id = targets.id
        {where_clause}
        GROUP BY targets.id, checkpoints.target_id
        ORDER BY targets.display_name ASC, targets.target_key ASC
        """,
        params,
    )
    return [
        {
            **dict(row),
            "window_count": int(row["window_count"] or 0),
            "sample_count": int(row["sample_count"] or 0),
            "peak_players": int(row["peak_players"] or 0),
        }
        for row in rows
    ]


def find_competitive_window(
    *,
    server_key: str,
    ended_at: str | None,
    map_name: str | None,
) -> dict[str, object] | None:
    if not ended_at:
        return None
    aliases = _expand_target_key_aliases(server_key)
    candidates = _fetchall(
        """
        SELECT windows.session_key, windows.first_seen_at, windows.last_seen_at,
               windows.map_name, windows.map_pretty_name, windows.sample_count,
               windows.total_players, windows.peak_players, windows.confidence_mode,
               windows.capabilities_json, windows.latest_payload_json
        FROM rcon_historical_competitive_windows AS windows
        INNER JOIN rcon_historical_targets AS targets ON targets.id = windows.target_id
        WHERE targets.target_key = ANY(%s) OR targets.external_server_id = ANY(%s)
        ORDER BY windows.last_seen_at DESC
        LIMIT 12
        """,
        (aliases, aliases),
    )
    ended_point = _parse_timestamp(ended_at)
    if ended_point is None:
        return None
    normalized_map_name = normalize_map_name(map_name)
    best_row: dict[str, object] | None = None
    best_distance: float | None = None
    for row in candidates:
        row_map = normalize_map_name(row["map_pretty_name"] or row["map_name"])
        if normalized_map_name and row_map and normalized_map_name != row_map:
            continue
        row_last = _parse_timestamp(row["last_seen_at"])
        if row_last is None:
            continue
        distance = abs((row_last - ended_point).total_seconds())
        if best_distance is None or distance < best_distance:
            best_row = dict(row)
            best_distance = distance
    if best_row is None or best_distance is None or best_distance > 21600:
        return None
    sample_count = int(best_row["sample_count"] or 0)
    return {
        "session_key": best_row["session_key"],
        "first_seen_at": best_row["first_seen_at"],
        "last_seen_at": best_row["last_seen_at"],
        "duration_seconds": _calculate_duration_seconds(
            best_row["first_seen_at"],
            best_row["last_seen_at"],
        ),
        "map_name": best_row["map_name"],
        "map_pretty_name": best_row["map_pretty_name"] or best_row["map_name"],
        "sample_count": sample_count,
        "average_players": (
            round((int(best_row["total_players"] or 0) / sample_count), 2)
            if sample_count > 0
            else 0.0
        ),
        "peak_players": int(best_row["peak_players"] or 0),
        "confidence_mode": best_row["confidence_mode"],
        "capabilities": _deserialize_json_object(best_row["capabilities_json"]),
    }


def get_competitive_window_by_session(
    *,
    server_key: str,
    session_key: str,
) -> dict[str, object] | None:
    normalized_session_key = str(session_key or "").strip()
    if not normalized_session_key:
        return None
    aliases = _expand_target_key_aliases(server_key)
    row = _fetchone(
        """
        SELECT targets.target_key, targets.external_server_id, targets.display_name,
               targets.region, windows.session_key, windows.map_name,
               windows.map_pretty_name, windows.first_seen_at, windows.last_seen_at,
               windows.sample_count, windows.total_players, windows.peak_players,
               windows.confidence_mode, windows.capabilities_json,
               windows.latest_payload_json
        FROM rcon_historical_competitive_windows AS windows
        INNER JOIN rcon_historical_targets AS targets ON targets.id = windows.target_id
        WHERE windows.session_key = %s
          AND (targets.target_key = ANY(%s) OR targets.external_server_id = ANY(%s))
        LIMIT 1
        """,
        (normalized_session_key, aliases, aliases),
    )
    return _serialize_window(row) if row else None


def list_scoreboard_candidates(*, server_slug: str, limit: int) -> list[dict[str, object]]:
    rows = _fetchall(
        """
        SELECT external_match_id, started_at, ended_at, map_name, map_pretty_name,
               allied_score, axis_score, player_count, match_url
        FROM rcon_scoreboard_match_candidates
        WHERE server_slug = %s
        ORDER BY COALESCE(ended_at, started_at) DESC
        LIMIT %s
        """,
        (server_slug, limit),
    )
    return [dict(row) for row in rows]


def upsert_scoreboard_candidates(
    *,
    server_slug: str,
    candidates: Iterable[Mapping[str, object]],
) -> int:
    """Cache trusted scoreboard correlation candidates in PostgreSQL."""
    rows = [candidate for candidate in candidates if candidate.get("match_url")]
    if not rows:
        return 0
    initialize_postgres_rcon_storage()
    inserted_or_updated = 0
    with connect_postgres() as connection:
        for candidate in rows:
            connection.execute(
                """
                INSERT INTO rcon_scoreboard_match_candidates (
                    server_slug, external_match_id, started_at, ended_at, map_name,
                    map_pretty_name, allied_score, axis_score, player_count, match_url
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(server_slug, external_match_id) DO UPDATE SET
                    started_at = EXCLUDED.started_at,
                    ended_at = EXCLUDED.ended_at,
                    map_name = EXCLUDED.map_name,
                    map_pretty_name = EXCLUDED.map_pretty_name,
                    allied_score = EXCLUDED.allied_score,
                    axis_score = EXCLUDED.axis_score,
                    player_count = EXCLUDED.player_count,
                    match_url = EXCLUDED.match_url,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    server_slug,
                    str(candidate.get("external_match_id") or ""),
                    candidate.get("started_at"),
                    candidate.get("ended_at"),
                    candidate.get("map_name"),
                    candidate.get("map_pretty_name"),
                    candidate.get("allied_score"),
                    candidate.get("axis_score"),
                    candidate.get("player_count"),
                    candidate["match_url"],
                ),
            )
            inserted_or_updated += 1
    return inserted_or_updated


def upsert_scoreboard_candidate(
    *,
    server_slug: str,
    candidate: Mapping[str, object],
) -> str:
    """Persist one trusted scoreboard correlation candidate and report the upsert path."""
    external_match_id = str(candidate.get("external_match_id") or "").strip()
    match_url = str(candidate.get("match_url") or "").strip()
    if not external_match_id or not match_url:
        return "skipped"

    initialize_postgres_rcon_storage()
    with connect_postgres() as connection:
        existing = connection.execute(
            """
            SELECT id
            FROM rcon_scoreboard_match_candidates
            WHERE server_slug = %s AND external_match_id = %s
            LIMIT 1
            """,
            (server_slug, external_match_id),
        ).fetchone()
        connection.execute(
            """
            INSERT INTO rcon_scoreboard_match_candidates (
                server_slug, external_match_id, started_at, ended_at, map_name,
                map_pretty_name, allied_score, axis_score, player_count, match_url
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT(server_slug, external_match_id) DO UPDATE SET
                started_at = EXCLUDED.started_at,
                ended_at = EXCLUDED.ended_at,
                map_name = EXCLUDED.map_name,
                map_pretty_name = EXCLUDED.map_pretty_name,
                allied_score = EXCLUDED.allied_score,
                axis_score = EXCLUDED.axis_score,
                player_count = EXCLUDED.player_count,
                match_url = EXCLUDED.match_url,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                server_slug,
                external_match_id,
                candidate.get("started_at"),
                candidate.get("ended_at"),
                candidate.get("map_name"),
                candidate.get("map_pretty_name"),
                candidate.get("allied_score"),
                candidate.get("axis_score"),
                candidate.get("player_count"),
                match_url,
            ),
        )
    return "updated" if existing else "inserted"


def count_migrated_tables() -> dict[str, int]:
    table_names = (
        "rcon_admin_log_events",
        "rcon_player_profile_snapshots",
        "rcon_materialized_matches",
        "rcon_match_player_stats",
        "rcon_historical_targets",
        "rcon_historical_samples",
        "rcon_historical_competitive_windows",
        "rcon_scoreboard_match_candidates",
    )
    with connect_postgres() as connection:
        return {
            table_name: int(
                connection.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()[
                    "count"
                ]
                or 0
            )
            for table_name in table_names
        }


def _fetchall(sql: str, params: Iterable[object] = ()) -> list[dict[str, object]]:
    with connect_postgres() as connection:
        return [dict(row) for row in connection.execute(sql, tuple(params)).fetchall()]


def _fetchone(sql: str, params: Iterable[object] = ()) -> dict[str, object] | None:
    with connect_postgres() as connection:
        row = connection.execute(sql, tuple(params)).fetchone()
    return dict(row) if row else None


def _upsert_target(connection: Any, *, target: Mapping[str, object]) -> int:
    target_key = str(target.get("target_key") or "").strip()
    display_name = str(target.get("name") or target.get("display_name") or target_key).strip()
    host = str(target.get("host") or "").strip()
    port = int(target.get("port") or 0)
    if not target_key or not host or port <= 0:
        raise ValueError("Prospective RCON targets require target_key, host and port.")
    row = connection.execute(
        """
        INSERT INTO rcon_historical_targets (
            target_key, external_server_id, display_name, host, port, region,
            game_port, query_port, source_name, last_configured_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT(target_key) DO UPDATE SET
            external_server_id = EXCLUDED.external_server_id,
            display_name = EXCLUDED.display_name,
            host = EXCLUDED.host,
            port = EXCLUDED.port,
            region = EXCLUDED.region,
            game_port = EXCLUDED.game_port,
            query_port = EXCLUDED.query_port,
            source_name = EXCLUDED.source_name,
            last_configured_at = EXCLUDED.last_configured_at,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id
        """,
        (
            target_key,
            target.get("external_server_id"),
            display_name,
            host,
            port,
            target.get("region"),
            target.get("game_port"),
            target.get("query_port"),
            str(target.get("source_name") or "community-hispana-rcon"),
            _utc_now_iso(),
        ),
    ).fetchone()
    return int(row["id"])


def _upsert_checkpoint_success(
    connection: Any,
    *,
    target_id: int,
    run_id: int,
    captured_at: str,
) -> None:
    connection.execute(
        """
        INSERT INTO rcon_historical_checkpoints (
            target_id, last_successful_capture_at, last_sample_at, last_run_id,
            last_run_status, last_error, last_error_at
        ) VALUES (%s, %s, %s, %s, 'success', NULL, NULL)
        ON CONFLICT(target_id) DO UPDATE SET
            last_successful_capture_at = EXCLUDED.last_successful_capture_at,
            last_sample_at = EXCLUDED.last_sample_at,
            last_run_id = EXCLUDED.last_run_id,
            last_run_status = EXCLUDED.last_run_status,
            last_error = NULL,
            last_error_at = NULL,
            updated_at = CURRENT_TIMESTAMP
        """,
        (target_id, captured_at, captured_at, run_id),
    )


def _upsert_competitive_window(
    connection: Any,
    *,
    target_id: int,
    captured_at: str,
    normalized_payload: Mapping[str, object],
) -> None:
    current_map_raw = str(normalized_payload.get("current_map") or "").strip()
    if not current_map_raw:
        return
    map_pretty_name = normalize_map_name(current_map_raw) or current_map_raw
    players = int(normalized_payload.get("players") or 0)
    max_players = normalized_payload.get("max_players")
    status = str(normalized_payload.get("status") or "unknown")
    latest_window = connection.execute(
        """
        SELECT *
        FROM rcon_historical_competitive_windows
        WHERE target_id = %s
        ORDER BY last_seen_at DESC, id DESC
        LIMIT 1
        """,
        (target_id,),
    ).fetchone()
    if latest_window and _should_extend_competitive_window(
        latest_window=dict(latest_window),
        captured_at=captured_at,
        current_map=current_map_raw,
    ):
        connection.execute(
            """
            UPDATE rcon_historical_competitive_windows
            SET map_name = %s,
                map_pretty_name = %s,
                last_seen_at = %s,
                sample_count = sample_count + 1,
                total_players = total_players + %s,
                peak_players = GREATEST(peak_players, %s),
                last_players = %s,
                max_players = %s,
                status = %s,
                confidence_mode = %s,
                capabilities_json = %s,
                latest_payload_json = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (
                current_map_raw,
                map_pretty_name,
                captured_at,
                players,
                players,
                players,
                max_players,
                status,
                COMPETITIVE_MODE_APPROXIMATE,
                json.dumps(_build_competitive_capabilities(), separators=(",", ":")),
                json.dumps(dict(normalized_payload), separators=(",", ":")),
                latest_window["id"],
            ),
        )
        return
    connection.execute(
        """
        INSERT INTO rcon_historical_competitive_windows (
            target_id, session_key, source_kind, map_name, map_pretty_name,
            first_seen_at, last_seen_at, sample_count, total_players,
            peak_players, last_players, max_players, status, confidence_mode,
            capabilities_json, latest_payload_json
        ) VALUES (%s, %s, 'rcon-historical-samples', %s, %s, %s, %s, 1,
                  %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            target_id,
            f"{target_id}:{captured_at}",
            current_map_raw,
            map_pretty_name,
            captured_at,
            captured_at,
            players,
            players,
            players,
            max_players,
            status,
            COMPETITIVE_MODE_APPROXIMATE,
            json.dumps(_build_competitive_capabilities(), separators=(",", ":")),
            json.dumps(dict(normalized_payload), separators=(",", ":")),
        ),
    )


def _target_where_clause(target_key: str | None) -> tuple[str, list[object]]:
    if not target_key:
        return "", []
    aliases = _expand_target_key_aliases(target_key)
    return "WHERE targets.target_key = ANY(%s) OR targets.external_server_id = ANY(%s)", [
        aliases,
        aliases,
    ]


def _expand_target_key_aliases(target_key: str) -> list[str]:
    normalized_target_key = str(target_key or "").strip()
    aliases = {normalized_target_key}
    try:
        configured_targets = load_rcon_targets()
    except Exception:
        configured_targets = ()
    for target in configured_targets:
        external_server_id = str(target.external_server_id or "").strip()
        legacy_target_key = f"rcon:{target.host}:{target.port}"
        if external_server_id and external_server_id == normalized_target_key:
            aliases.update((legacy_target_key, external_server_id))
        elif legacy_target_key == normalized_target_key:
            aliases.add(legacy_target_key)
            if external_server_id:
                aliases.add(external_server_id)
    return sorted(alias for alias in aliases if alias)


def _serialize_window(row: Mapping[str, object]) -> dict[str, object]:
    sample_count = int(row["sample_count"] or 0)
    return {
        "target_key": row["target_key"],
        "external_server_id": row["external_server_id"],
        "display_name": row["display_name"],
        "region": row["region"],
        "session_key": row["session_key"],
        "map_name": row["map_name"],
        "map_pretty_name": row["map_pretty_name"] or row["map_name"],
        "first_seen_at": row["first_seen_at"],
        "last_seen_at": row["last_seen_at"],
        "duration_seconds": _calculate_duration_seconds(
            row["first_seen_at"],
            row["last_seen_at"],
        ),
        "sample_count": sample_count,
        "average_players": (
            round((int(row["total_players"] or 0) / sample_count), 2)
            if sample_count > 0
            else 0.0
        ),
        "peak_players": int(row["peak_players"] or 0),
        "last_players": row.get("last_players"),
        "max_players": row.get("max_players"),
        "status": row.get("status"),
        "confidence_mode": row["confidence_mode"],
        "capabilities": _deserialize_json_object(row["capabilities_json"]),
        "latest_payload": _deserialize_json_object(row["latest_payload_json"]),
    }


def _should_extend_competitive_window(
    *,
    latest_window: Mapping[str, object],
    captured_at: str,
    current_map: str,
) -> bool:
    if normalize_map_name(latest_window.get("map_name")) != normalize_map_name(current_map):
        return False
    latest_seen = _parse_timestamp(latest_window.get("last_seen_at"))
    captured_point = _parse_timestamp(captured_at)
    if latest_seen is None or captured_point is None:
        return False
    return (captured_point - latest_seen).total_seconds() <= COMPETITIVE_WINDOW_GAP_SECONDS


def _build_competitive_capabilities() -> dict[str, object]:
    return {
        "recent_matches": COMPETITIVE_MODE_APPROXIMATE,
        "server_summary": COMPETITIVE_MODE_EXACT,
        "competitive_quality": COMPETITIVE_MODE_PARTIAL,
        "result": "session-score",
        "gamestate": "session",
        "player_stats": "unavailable",
    }


def _deserialize_json_object(raw_value: object) -> dict[str, object]:
    if isinstance(raw_value, str) and raw_value.strip():
        try:
            parsed = json.loads(raw_value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _calculate_duration_seconds(first_seen_at: object, last_seen_at: object) -> int | None:
    first_point = _parse_timestamp(first_seen_at)
    last_point = _parse_timestamp(last_seen_at)
    if first_point is None or last_point is None:
        return None
    return max(0, int((last_point - first_point).total_seconds()))


def _parse_timestamp(raw_value: object) -> datetime | None:
    if not isinstance(raw_value, str) or not raw_value.strip():
        return None
    try:
        timestamp = datetime.fromisoformat(raw_value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
