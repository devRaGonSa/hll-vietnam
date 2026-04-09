CREATE TABLE IF NOT EXISTS player_event_raw_ledger (
    id BIGSERIAL PRIMARY KEY,
    event_id TEXT NOT NULL UNIQUE,
    event_type TEXT NOT NULL,
    occurred_at TIMESTAMPTZ,
    server_slug TEXT NOT NULL,
    external_match_id TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    source_ref TEXT,
    raw_event_ref TEXT,
    killer_player_key TEXT,
    killer_display_name TEXT,
    victim_player_key TEXT,
    victim_display_name TEXT,
    weapon_name TEXT,
    weapon_category TEXT,
    kill_category TEXT,
    is_teamkill BOOLEAN NOT NULL DEFAULT FALSE,
    event_value INTEGER NOT NULL DEFAULT 1,
    inserted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS player_event_ingestion_runs (
    id BIGSERIAL PRIMARY KEY,
    mode TEXT NOT NULL,
    status TEXT NOT NULL,
    target_server_slug TEXT,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    pages_processed INTEGER NOT NULL DEFAULT 0,
    matches_seen INTEGER NOT NULL DEFAULT 0,
    matches_fetched INTEGER NOT NULL DEFAULT 0,
    events_inserted INTEGER NOT NULL DEFAULT 0,
    duplicate_events INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS player_event_backfill_progress (
    server_slug TEXT NOT NULL,
    mode TEXT NOT NULL,
    next_page INTEGER NOT NULL DEFAULT 1,
    last_completed_page INTEGER,
    cutoff_occurred_at TIMESTAMPTZ,
    discovered_total_matches INTEGER,
    archive_exhausted BOOLEAN NOT NULL DEFAULT FALSE,
    last_run_id BIGINT,
    last_run_status TEXT,
    last_run_started_at TIMESTAMPTZ,
    last_run_completed_at TIMESTAMPTZ,
    last_error TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (server_slug, mode)
);

CREATE INDEX IF NOT EXISTS idx_player_event_raw_server_match
    ON player_event_raw_ledger (server_slug, external_match_id);

CREATE INDEX IF NOT EXISTS idx_player_event_raw_occurred_at
    ON player_event_raw_ledger (occurred_at DESC);

CREATE INDEX IF NOT EXISTS idx_player_event_raw_killer_victim
    ON player_event_raw_ledger (killer_player_key, victim_player_key);

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
    last_configured_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rcon_historical_capture_runs (
    id BIGSERIAL PRIMARY KEY,
    mode TEXT NOT NULL,
    status TEXT NOT NULL,
    target_scope TEXT,
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    targets_seen INTEGER NOT NULL DEFAULT 0,
    samples_inserted INTEGER NOT NULL DEFAULT 0,
    duplicate_samples INTEGER NOT NULL DEFAULT 0,
    failed_targets INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rcon_historical_samples (
    id BIGSERIAL PRIMARY KEY,
    target_id BIGINT NOT NULL REFERENCES rcon_historical_targets(id),
    capture_run_id BIGINT REFERENCES rcon_historical_capture_runs(id),
    captured_at TIMESTAMPTZ NOT NULL,
    source_kind TEXT NOT NULL,
    status TEXT NOT NULL,
    players INTEGER,
    max_players INTEGER,
    current_map TEXT,
    normalized_payload_json JSONB NOT NULL,
    raw_payload_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (target_id, captured_at)
);

CREATE TABLE IF NOT EXISTS rcon_historical_checkpoints (
    target_id BIGINT PRIMARY KEY REFERENCES rcon_historical_targets(id),
    last_successful_capture_at TIMESTAMPTZ,
    last_sample_at TIMESTAMPTZ,
    last_run_id BIGINT REFERENCES rcon_historical_capture_runs(id),
    last_run_status TEXT,
    last_error TEXT,
    last_error_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rcon_historical_samples_target_time
    ON rcon_historical_samples (target_id, captured_at DESC);

CREATE TABLE IF NOT EXISTS rcon_historical_competitive_windows (
    id BIGSERIAL PRIMARY KEY,
    target_id BIGINT NOT NULL REFERENCES rcon_historical_targets(id),
    session_key TEXT NOT NULL UNIQUE,
    source_kind TEXT NOT NULL,
    map_name TEXT,
    map_pretty_name TEXT,
    first_seen_at TIMESTAMPTZ NOT NULL,
    last_seen_at TIMESTAMPTZ NOT NULL,
    sample_count INTEGER NOT NULL DEFAULT 0,
    total_players INTEGER NOT NULL DEFAULT 0,
    peak_players INTEGER NOT NULL DEFAULT 0,
    last_players INTEGER,
    max_players INTEGER,
    status TEXT NOT NULL,
    confidence_mode TEXT NOT NULL,
    capabilities_json JSONB NOT NULL,
    latest_payload_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rcon_historical_windows_target_time
    ON rcon_historical_competitive_windows (target_id, last_seen_at DESC);
