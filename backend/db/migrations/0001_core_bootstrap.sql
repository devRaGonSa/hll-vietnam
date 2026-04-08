CREATE TABLE IF NOT EXISTS game_sources (
    id BIGSERIAL PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    provider_kind TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS servers (
    id BIGSERIAL PRIMARY KEY,
    game_source_id BIGINT NOT NULL REFERENCES game_sources(id),
    external_server_id TEXT NOT NULL,
    server_name TEXT NOT NULL,
    region TEXT,
    first_seen_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (game_source_id, external_server_id)
);

CREATE TABLE IF NOT EXISTS server_snapshots (
    id BIGSERIAL PRIMARY KEY,
    server_id BIGINT NOT NULL REFERENCES servers(id),
    captured_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL,
    players INTEGER,
    max_players INTEGER,
    current_map TEXT,
    source_name TEXT NOT NULL,
    snapshot_origin TEXT,
    source_ref TEXT,
    raw_payload_ref TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_server_snapshots_server_time
    ON server_snapshots (server_id, captured_at DESC);

CREATE TABLE IF NOT EXISTS historical_servers (
    id BIGSERIAL PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    source_base_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS historical_maps (
    id BIGSERIAL PRIMARY KEY,
    historical_server_id BIGINT NOT NULL REFERENCES historical_servers(id),
    external_map_id TEXT NOT NULL,
    map_name TEXT,
    map_label TEXT,
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (historical_server_id, external_map_id)
);

CREATE TABLE IF NOT EXISTS historical_matches (
    id BIGSERIAL PRIMARY KEY,
    historical_server_id BIGINT NOT NULL REFERENCES historical_servers(id),
    historical_map_id BIGINT REFERENCES historical_maps(id),
    external_match_id TEXT NOT NULL,
    match_state TEXT,
    map_name TEXT,
    map_label TEXT,
    team1_name TEXT,
    team2_name TEXT,
    team1_score INTEGER,
    team2_score INTEGER,
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    raw_payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (historical_server_id, external_match_id)
);

CREATE INDEX IF NOT EXISTS idx_historical_matches_server_end
    ON historical_matches (historical_server_id, ended_at DESC);

CREATE TABLE IF NOT EXISTS historical_players (
    id BIGSERIAL PRIMARY KEY,
    stable_player_key TEXT NOT NULL UNIQUE,
    player_name TEXT,
    steam_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_historical_players_steam
    ON historical_players (steam_id);

CREATE TABLE IF NOT EXISTS historical_player_match_stats (
    id BIGSERIAL PRIMARY KEY,
    historical_match_id BIGINT NOT NULL REFERENCES historical_matches(id),
    historical_player_id BIGINT NOT NULL REFERENCES historical_players(id),
    team_name TEXT,
    role_name TEXT,
    kills INTEGER,
    deaths INTEGER,
    assists INTEGER,
    support_points INTEGER,
    attack_points INTEGER,
    defense_points INTEGER,
    score INTEGER,
    time_seconds INTEGER,
    raw_payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (historical_match_id, historical_player_id)
);

CREATE INDEX IF NOT EXISTS idx_historical_player_stats_match
    ON historical_player_match_stats (historical_match_id);

CREATE TABLE IF NOT EXISTS historical_ingestion_runs (
    id BIGSERIAL PRIMARY KEY,
    historical_server_id BIGINT REFERENCES historical_servers(id),
    run_kind TEXT NOT NULL,
    status TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS historical_backfill_progress (
    id BIGSERIAL PRIMARY KEY,
    historical_server_id BIGINT NOT NULL REFERENCES historical_servers(id),
    last_completed_page INTEGER,
    next_page INTEGER,
    discovered_total_matches INTEGER,
    discovered_total_pages INTEGER,
    archive_exhausted BOOLEAN NOT NULL DEFAULT FALSE,
    last_run_at TIMESTAMPTZ,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (historical_server_id)
);

CREATE INDEX IF NOT EXISTS idx_historical_backfill_progress_run
    ON historical_backfill_progress (last_run_at DESC);
