ALTER TABLE historical_servers
    ADD COLUMN IF NOT EXISTS scoreboard_base_url TEXT;

ALTER TABLE historical_servers
    ADD COLUMN IF NOT EXISTS server_number INTEGER;

ALTER TABLE historical_servers
    ADD COLUMN IF NOT EXISTS source_kind TEXT;

UPDATE historical_servers
SET scoreboard_base_url = COALESCE(scoreboard_base_url, source_base_url)
WHERE scoreboard_base_url IS NULL;

UPDATE historical_servers
SET source_kind = COALESCE(source_kind, 'public-scoreboard')
WHERE source_kind IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_historical_servers_scoreboard_base_url
    ON historical_servers (scoreboard_base_url)
    WHERE scoreboard_base_url IS NOT NULL;

ALTER TABLE historical_maps
    ALTER COLUMN historical_server_id DROP NOT NULL;

ALTER TABLE historical_maps
    ADD COLUMN IF NOT EXISTS pretty_name TEXT;

ALTER TABLE historical_maps
    ADD COLUMN IF NOT EXISTS game_mode TEXT;

ALTER TABLE historical_maps
    ADD COLUMN IF NOT EXISTS image_name TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_historical_maps_external_map_id
    ON historical_maps (external_map_id);

ALTER TABLE historical_matches
    ADD COLUMN IF NOT EXISTS created_at_source TIMESTAMPTZ;

ALTER TABLE historical_matches
    ADD COLUMN IF NOT EXISTS map_pretty_name TEXT;

ALTER TABLE historical_matches
    ADD COLUMN IF NOT EXISTS game_mode TEXT;

ALTER TABLE historical_matches
    ADD COLUMN IF NOT EXISTS image_name TEXT;

ALTER TABLE historical_matches
    ADD COLUMN IF NOT EXISTS allied_score INTEGER;

ALTER TABLE historical_matches
    ADD COLUMN IF NOT EXISTS axis_score INTEGER;

ALTER TABLE historical_matches
    ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ;

ALTER TABLE historical_matches
    ADD COLUMN IF NOT EXISTS raw_payload_ref TEXT;

UPDATE historical_matches
SET created_at_source = COALESCE(created_at_source, started_at, ended_at)
WHERE created_at_source IS NULL;

UPDATE historical_matches
SET map_pretty_name = COALESCE(map_pretty_name, map_label, map_name)
WHERE map_pretty_name IS NULL;

UPDATE historical_matches
SET allied_score = COALESCE(allied_score, team1_score)
WHERE allied_score IS NULL;

UPDATE historical_matches
SET axis_score = COALESCE(axis_score, team2_score)
WHERE axis_score IS NULL;

UPDATE historical_matches
SET last_seen_at = COALESCE(last_seen_at, ended_at, started_at, NOW())
WHERE last_seen_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_historical_matches_server_end_started
    ON historical_matches (historical_server_id, ended_at DESC, started_at DESC);

ALTER TABLE historical_players
    ADD COLUMN IF NOT EXISTS display_name TEXT;

ALTER TABLE historical_players
    ADD COLUMN IF NOT EXISTS source_player_id TEXT;

ALTER TABLE historical_players
    ADD COLUMN IF NOT EXISTS first_seen_at TIMESTAMPTZ;

ALTER TABLE historical_players
    ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ;

UPDATE historical_players
SET display_name = COALESCE(display_name, player_name, 'Unknown player')
WHERE display_name IS NULL;

UPDATE historical_players
SET first_seen_at = COALESCE(first_seen_at, created_at, NOW())
WHERE first_seen_at IS NULL;

UPDATE historical_players
SET last_seen_at = COALESCE(last_seen_at, updated_at, created_at, NOW())
WHERE last_seen_at IS NULL;

ALTER TABLE historical_player_match_stats
    ADD COLUMN IF NOT EXISTS match_player_ref TEXT;

ALTER TABLE historical_player_match_stats
    ADD COLUMN IF NOT EXISTS team_side TEXT;

ALTER TABLE historical_player_match_stats
    ADD COLUMN IF NOT EXISTS level INTEGER;

ALTER TABLE historical_player_match_stats
    ADD COLUMN IF NOT EXISTS teamkills INTEGER;

ALTER TABLE historical_player_match_stats
    ADD COLUMN IF NOT EXISTS kills_per_minute DOUBLE PRECISION;

ALTER TABLE historical_player_match_stats
    ADD COLUMN IF NOT EXISTS deaths_per_minute DOUBLE PRECISION;

ALTER TABLE historical_player_match_stats
    ADD COLUMN IF NOT EXISTS kill_death_ratio DOUBLE PRECISION;

ALTER TABLE historical_player_match_stats
    ADD COLUMN IF NOT EXISTS combat INTEGER;

ALTER TABLE historical_player_match_stats
    ADD COLUMN IF NOT EXISTS offense INTEGER;

ALTER TABLE historical_player_match_stats
    ADD COLUMN IF NOT EXISTS defense INTEGER;

ALTER TABLE historical_player_match_stats
    ADD COLUMN IF NOT EXISTS support INTEGER;

UPDATE historical_player_match_stats
SET support = COALESCE(support, support_points)
WHERE support IS NULL;

ALTER TABLE historical_ingestion_runs
    ADD COLUMN IF NOT EXISTS mode TEXT;

ALTER TABLE historical_ingestion_runs
    ADD COLUMN IF NOT EXISTS target_server_slug TEXT;

ALTER TABLE historical_ingestion_runs
    ADD COLUMN IF NOT EXISTS pages_processed INTEGER NOT NULL DEFAULT 0;

ALTER TABLE historical_ingestion_runs
    ADD COLUMN IF NOT EXISTS matches_seen INTEGER NOT NULL DEFAULT 0;

ALTER TABLE historical_ingestion_runs
    ADD COLUMN IF NOT EXISTS matches_inserted INTEGER NOT NULL DEFAULT 0;

ALTER TABLE historical_ingestion_runs
    ADD COLUMN IF NOT EXISTS matches_updated INTEGER NOT NULL DEFAULT 0;

ALTER TABLE historical_ingestion_runs
    ADD COLUMN IF NOT EXISTS player_rows_inserted INTEGER NOT NULL DEFAULT 0;

ALTER TABLE historical_ingestion_runs
    ADD COLUMN IF NOT EXISTS player_rows_updated INTEGER NOT NULL DEFAULT 0;

ALTER TABLE historical_ingestion_runs
    ADD COLUMN IF NOT EXISTS notes TEXT;

UPDATE historical_ingestion_runs
SET mode = COALESCE(mode, run_kind)
WHERE mode IS NULL;

ALTER TABLE historical_backfill_progress
    DROP CONSTRAINT IF EXISTS historical_backfill_progress_historical_server_id_key;

ALTER TABLE historical_backfill_progress
    ADD COLUMN IF NOT EXISTS mode TEXT NOT NULL DEFAULT 'bootstrap';

ALTER TABLE historical_backfill_progress
    ADD COLUMN IF NOT EXISTS next_page INTEGER NOT NULL DEFAULT 1;

ALTER TABLE historical_backfill_progress
    ADD COLUMN IF NOT EXISTS last_run_id BIGINT;

ALTER TABLE historical_backfill_progress
    ADD COLUMN IF NOT EXISTS last_run_status TEXT;

ALTER TABLE historical_backfill_progress
    ADD COLUMN IF NOT EXISTS last_run_started_at TIMESTAMPTZ;

ALTER TABLE historical_backfill_progress
    ADD COLUMN IF NOT EXISTS last_run_completed_at TIMESTAMPTZ;

ALTER TABLE historical_backfill_progress
    ADD COLUMN IF NOT EXISTS last_error TEXT;

UPDATE historical_backfill_progress
SET next_page = COALESCE(next_page, 1)
WHERE next_page IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS idx_historical_backfill_progress_server_mode
    ON historical_backfill_progress (historical_server_id, mode);

CREATE INDEX IF NOT EXISTS idx_historical_backfill_progress_last_run_id
    ON historical_backfill_progress (last_run_id);
