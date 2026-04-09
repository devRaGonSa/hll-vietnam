CREATE TABLE IF NOT EXISTS elo_mmr_player_ratings (
    scope_key TEXT NOT NULL,
    stable_player_key TEXT NOT NULL,
    player_name TEXT NOT NULL,
    steam_id TEXT,
    current_mmr DOUBLE PRECISION NOT NULL,
    matches_processed INTEGER NOT NULL DEFAULT 0,
    wins INTEGER NOT NULL DEFAULT 0,
    draws INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    last_match_id TEXT,
    last_match_ended_at TEXT,
    model_version TEXT NOT NULL DEFAULT '',
    formula_version TEXT NOT NULL DEFAULT '',
    contract_version TEXT NOT NULL DEFAULT '',
    accuracy_mode TEXT NOT NULL,
    capabilities_json TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP::text,
    PRIMARY KEY (scope_key, stable_player_key)
);

CREATE TABLE IF NOT EXISTS elo_mmr_match_results (
    scope_key TEXT NOT NULL,
    month_key TEXT NOT NULL,
    canonical_match_key TEXT NOT NULL DEFAULT '',
    external_match_id TEXT NOT NULL,
    stable_player_key TEXT NOT NULL,
    player_name TEXT NOT NULL,
    steam_id TEXT,
    server_slug TEXT NOT NULL,
    server_name TEXT NOT NULL,
    match_ended_at TEXT NOT NULL,
    fact_schema_version TEXT NOT NULL DEFAULT '',
    source_input_version TEXT NOT NULL DEFAULT '',
    model_version TEXT NOT NULL DEFAULT '',
    formula_version TEXT NOT NULL DEFAULT '',
    contract_version TEXT NOT NULL DEFAULT '',
    match_valid INTEGER NOT NULL,
    quality_factor DOUBLE PRECISION NOT NULL,
    quality_bucket TEXT NOT NULL,
    role_bucket TEXT NOT NULL,
    role_bucket_mode TEXT NOT NULL,
    outcome_score DOUBLE PRECISION NOT NULL,
    combat_index DOUBLE PRECISION NOT NULL,
    objective_index DOUBLE PRECISION,
    objective_index_mode TEXT NOT NULL,
    utility_index DOUBLE PRECISION,
    utility_index_mode TEXT NOT NULL,
    leadership_index DOUBLE PRECISION,
    leadership_index_mode TEXT NOT NULL,
    discipline_index DOUBLE PRECISION,
    discipline_index_mode TEXT NOT NULL,
    impact_score DOUBLE PRECISION NOT NULL,
    delta_mmr DOUBLE PRECISION NOT NULL,
    mmr_before DOUBLE PRECISION NOT NULL,
    mmr_after DOUBLE PRECISION NOT NULL,
    match_score DOUBLE PRECISION NOT NULL,
    penalty_points DOUBLE PRECISION NOT NULL,
    time_seconds INTEGER NOT NULL DEFAULT 0,
    participation_ratio DOUBLE PRECISION NOT NULL DEFAULT 0,
    strength_of_schedule_match DOUBLE PRECISION NOT NULL DEFAULT 0,
    team_outcome TEXT,
    own_team_average_mmr DOUBLE PRECISION NOT NULL DEFAULT 0,
    enemy_team_average_mmr DOUBLE PRECISION NOT NULL DEFAULT 0,
    expected_result DOUBLE PRECISION NOT NULL DEFAULT 0,
    actual_result DOUBLE PRECISION NOT NULL DEFAULT 0,
    won_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    margin_boost DOUBLE PRECISION NOT NULL DEFAULT 0,
    outcome_adjusted DOUBLE PRECISION NOT NULL DEFAULT 0,
    match_impact DOUBLE PRECISION NOT NULL DEFAULT 0,
    combat_contribution DOUBLE PRECISION NOT NULL DEFAULT 0,
    objective_contribution DOUBLE PRECISION NOT NULL DEFAULT 0,
    utility_contribution DOUBLE PRECISION NOT NULL DEFAULT 0,
    survival_discipline_contribution DOUBLE PRECISION NOT NULL DEFAULT 0,
    exact_component_contribution DOUBLE PRECISION NOT NULL DEFAULT 0,
    proxy_component_contribution DOUBLE PRECISION NOT NULL DEFAULT 0,
    normalization_bucket_key TEXT NOT NULL DEFAULT '',
    normalization_fallback_reason TEXT,
    elo_core_delta DOUBLE PRECISION NOT NULL DEFAULT 0,
    performance_modifier_delta DOUBLE PRECISION NOT NULL DEFAULT 0,
    proxy_modifier_delta DOUBLE PRECISION NOT NULL DEFAULT 0,
    canonical_fact_capability_status TEXT NOT NULL DEFAULT 'not_available',
    identity_capability_status TEXT NOT NULL DEFAULT 'not_available',
    match_duration_seconds INTEGER NOT NULL DEFAULT 0,
    duration_source_status TEXT NOT NULL DEFAULT 'not_available',
    duration_bucket TEXT NOT NULL DEFAULT 'unknown',
    player_count INTEGER NOT NULL DEFAULT 0,
    objective_score_proxy INTEGER NOT NULL DEFAULT 0,
    objective_score_proxy_mode TEXT NOT NULL DEFAULT 'approximate',
    kills_per_minute DOUBLE PRECISION NOT NULL DEFAULT 0,
    combat_per_minute DOUBLE PRECISION NOT NULL DEFAULT 0,
    support_per_minute DOUBLE PRECISION NOT NULL DEFAULT 0,
    objective_proxy_per_minute DOUBLE PRECISION NOT NULL DEFAULT 0,
    participation_bucket TEXT NOT NULL DEFAULT 'none',
    participation_mode TEXT NOT NULL DEFAULT 'not_available',
    participation_quality_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    capabilities_json TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP::text,
    PRIMARY KEY (scope_key, external_match_id, stable_player_key)
);

CREATE TABLE IF NOT EXISTS elo_mmr_monthly_rankings (
    scope_key TEXT NOT NULL,
    month_key TEXT NOT NULL,
    stable_player_key TEXT NOT NULL,
    player_name TEXT NOT NULL,
    steam_id TEXT,
    model_version TEXT NOT NULL DEFAULT '',
    formula_version TEXT NOT NULL DEFAULT '',
    contract_version TEXT NOT NULL DEFAULT '',
    current_mmr DOUBLE PRECISION NOT NULL,
    baseline_mmr DOUBLE PRECISION NOT NULL,
    mmr_gain DOUBLE PRECISION NOT NULL,
    avg_match_score DOUBLE PRECISION NOT NULL,
    strength_of_schedule DOUBLE PRECISION NOT NULL,
    consistency DOUBLE PRECISION NOT NULL,
    activity DOUBLE PRECISION NOT NULL,
    confidence DOUBLE PRECISION NOT NULL,
    penalty_points DOUBLE PRECISION NOT NULL,
    monthly_rank_score DOUBLE PRECISION NOT NULL,
    valid_matches INTEGER NOT NULL,
    total_matches INTEGER NOT NULL,
    total_time_seconds INTEGER NOT NULL,
    avg_participation_ratio DOUBLE PRECISION NOT NULL DEFAULT 0,
    eligible INTEGER NOT NULL,
    eligibility_reason TEXT,
    accuracy_mode TEXT NOT NULL,
    capabilities_json TEXT NOT NULL,
    component_scores_json TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP::text,
    PRIMARY KEY (scope_key, month_key, stable_player_key)
);

CREATE TABLE IF NOT EXISTS elo_mmr_monthly_checkpoints (
    scope_key TEXT NOT NULL,
    month_key TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    model_version TEXT NOT NULL DEFAULT '',
    formula_version TEXT NOT NULL DEFAULT '',
    contract_version TEXT NOT NULL DEFAULT '',
    player_count INTEGER NOT NULL,
    eligible_player_count INTEGER NOT NULL,
    source_policy_json TEXT NOT NULL,
    capabilities_summary_json TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP::text,
    PRIMARY KEY (scope_key, month_key)
);

CREATE TABLE IF NOT EXISTS elo_mmr_canonical_players (
    stable_player_key TEXT NOT NULL PRIMARY KEY,
    player_name TEXT NOT NULL,
    steam_id TEXT,
    identity_capability_status TEXT NOT NULL,
    identity_source TEXT NOT NULL,
    first_seen_at TEXT,
    last_seen_at TEXT,
    fact_schema_version TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP::text
);

CREATE TABLE IF NOT EXISTS elo_mmr_canonical_matches (
    canonical_match_key TEXT NOT NULL PRIMARY KEY,
    server_slug TEXT NOT NULL,
    server_name TEXT NOT NULL,
    external_match_id TEXT NOT NULL,
    started_at TEXT,
    ended_at TEXT NOT NULL,
    game_mode TEXT,
    allied_score INTEGER,
    axis_score INTEGER,
    resolved_duration_seconds INTEGER NOT NULL DEFAULT 0,
    duration_source_status TEXT NOT NULL DEFAULT 'not_available',
    duration_bucket TEXT NOT NULL DEFAULT 'unknown',
    player_count INTEGER NOT NULL DEFAULT 0,
    match_capability_status TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    fact_schema_version TEXT NOT NULL,
    source_input_version TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP::text,
    UNIQUE (server_slug, external_match_id)
);

CREATE TABLE IF NOT EXISTS elo_mmr_canonical_player_match_facts (
    canonical_match_key TEXT NOT NULL,
    stable_player_key TEXT NOT NULL,
    server_slug TEXT NOT NULL,
    external_match_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    steam_id TEXT,
    team_side TEXT,
    kills INTEGER NOT NULL DEFAULT 0,
    deaths INTEGER NOT NULL DEFAULT 0,
    teamkills INTEGER NOT NULL DEFAULT 0,
    time_seconds INTEGER NOT NULL DEFAULT 0,
    combat INTEGER NOT NULL DEFAULT 0,
    offense INTEGER NOT NULL DEFAULT 0,
    defense INTEGER NOT NULL DEFAULT 0,
    support INTEGER NOT NULL DEFAULT 0,
    match_duration_seconds INTEGER NOT NULL DEFAULT 0,
    match_duration_mode TEXT NOT NULL DEFAULT 'not_available',
    duration_bucket TEXT NOT NULL DEFAULT 'unknown',
    player_count INTEGER NOT NULL DEFAULT 0,
    objective_score_proxy INTEGER NOT NULL DEFAULT 0,
    objective_score_proxy_mode TEXT NOT NULL DEFAULT 'approximate',
    kills_per_minute DOUBLE PRECISION NOT NULL DEFAULT 0,
    combat_per_minute DOUBLE PRECISION NOT NULL DEFAULT 0,
    support_per_minute DOUBLE PRECISION NOT NULL DEFAULT 0,
    objective_proxy_per_minute DOUBLE PRECISION NOT NULL DEFAULT 0,
    participation_ratio DOUBLE PRECISION NOT NULL DEFAULT 0,
    participation_bucket TEXT NOT NULL DEFAULT 'none',
    participation_mode TEXT NOT NULL DEFAULT 'not_available',
    participation_quality_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    garrison_builds INTEGER NOT NULL DEFAULT 0,
    garrison_destroys INTEGER NOT NULL DEFAULT 0,
    garrison_event_mode TEXT NOT NULL DEFAULT 'not_available',
    outpost_builds INTEGER NOT NULL DEFAULT 0,
    outpost_destroys INTEGER NOT NULL DEFAULT 0,
    outpost_event_mode TEXT NOT NULL DEFAULT 'not_available',
    revives_given INTEGER NOT NULL DEFAULT 0,
    revives_received INTEGER NOT NULL DEFAULT 0,
    revive_event_mode TEXT NOT NULL DEFAULT 'not_available',
    supplies_placed INTEGER NOT NULL DEFAULT 0,
    supply_effectiveness DOUBLE PRECISION NOT NULL DEFAULT 0,
    supply_event_mode TEXT NOT NULL DEFAULT 'not_available',
    nodes_built INTEGER NOT NULL DEFAULT 0,
    nodes_destroyed INTEGER NOT NULL DEFAULT 0,
    node_active_seconds INTEGER NOT NULL DEFAULT 0,
    node_event_mode TEXT NOT NULL DEFAULT 'not_available',
    repairs_performed INTEGER NOT NULL DEFAULT 0,
    repair_points DOUBLE PRECISION NOT NULL DEFAULT 0,
    repair_event_mode TEXT NOT NULL DEFAULT 'not_available',
    mines_placed INTEGER NOT NULL DEFAULT 0,
    mine_kills INTEGER NOT NULL DEFAULT 0,
    mine_destroys INTEGER NOT NULL DEFAULT 0,
    mine_event_mode TEXT NOT NULL DEFAULT 'not_available',
    commander_abilities_used INTEGER NOT NULL DEFAULT 0,
    commander_ability_event_mode TEXT NOT NULL DEFAULT 'not_available',
    strongpoint_occupancy_seconds INTEGER NOT NULL DEFAULT 0,
    strongpoint_contest_seconds INTEGER NOT NULL DEFAULT 0,
    strongpoint_event_mode TEXT NOT NULL DEFAULT 'not_available',
    role_time_seconds INTEGER NOT NULL DEFAULT 0,
    role_assignment_event_mode TEXT NOT NULL DEFAULT 'not_available',
    disconnect_leave_count INTEGER NOT NULL DEFAULT 0,
    admin_action_count INTEGER NOT NULL DEFAULT 0,
    disconnect_leave_admin_event_mode TEXT NOT NULL DEFAULT 'not_available',
    death_summary_combat_kills INTEGER NOT NULL DEFAULT 0,
    death_summary_combat_deaths INTEGER NOT NULL DEFAULT 0,
    death_summary_weapon_kills INTEGER NOT NULL DEFAULT 0,
    death_summary_weapon_deaths INTEGER NOT NULL DEFAULT 0,
    death_summary_teamkills INTEGER NOT NULL DEFAULT 0,
    death_classification_event_mode TEXT NOT NULL DEFAULT 'not_available',
    tactical_event_lineage_status TEXT NOT NULL DEFAULT 'not_available',
    tactical_event_count INTEGER NOT NULL DEFAULT 0,
    role_primary TEXT NOT NULL DEFAULT 'generalist',
    role_primary_mode TEXT NOT NULL DEFAULT 'not_available',
    normalization_bucket_key TEXT NOT NULL DEFAULT '',
    normalization_bucket_version TEXT NOT NULL DEFAULT '',
    normalization_fallback_bucket_key TEXT,
    normalization_fallback_reason TEXT,
    normalization_version TEXT NOT NULL DEFAULT '',
    player_count_bucket TEXT NOT NULL DEFAULT 'unknown',
    match_shape_bucket TEXT NOT NULL DEFAULT 'unknown',
    teamkill_exact_count INTEGER NOT NULL DEFAULT 0,
    leave_disconnect_exact_count INTEGER NOT NULL DEFAULT 0,
    kick_or_ban_exact_count INTEGER NOT NULL DEFAULT 0,
    admin_action_exact_count INTEGER NOT NULL DEFAULT 0,
    combat_death_proxy_count INTEGER NOT NULL DEFAULT 0,
    friendly_fire_proxy_count INTEGER NOT NULL DEFAULT 0,
    redeploy_death_exact_count INTEGER NOT NULL DEFAULT 0,
    suicide_death_exact_count INTEGER NOT NULL DEFAULT 0,
    menu_exit_death_exact_count INTEGER NOT NULL DEFAULT 0,
    discipline_capability_status TEXT NOT NULL DEFAULT 'not_available',
    leave_admin_capability_status TEXT NOT NULL DEFAULT 'not_available',
    death_type_capability_status TEXT NOT NULL DEFAULT 'not_available',
    discipline_lineage_status TEXT NOT NULL DEFAULT 'not_available',
    fact_capability_status TEXT NOT NULL,
    fact_schema_version TEXT NOT NULL,
    source_input_version TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP::text,
    PRIMARY KEY (canonical_match_key, stable_player_key),
    FOREIGN KEY (canonical_match_key) REFERENCES elo_mmr_canonical_matches(canonical_match_key),
    FOREIGN KEY (stable_player_key) REFERENCES elo_mmr_canonical_players(stable_player_key)
);

CREATE INDEX IF NOT EXISTS idx_elo_mmr_monthly_rankings_scope_month
    ON elo_mmr_monthly_rankings(scope_key, month_key, eligible, monthly_rank_score DESC);

CREATE INDEX IF NOT EXISTS idx_elo_mmr_player_ratings_scope
    ON elo_mmr_player_ratings(scope_key, current_mmr DESC);

CREATE INDEX IF NOT EXISTS idx_elo_mmr_canonical_matches_server
    ON elo_mmr_canonical_matches(server_slug, ended_at, external_match_id);

CREATE INDEX IF NOT EXISTS idx_elo_mmr_canonical_facts_server_match
    ON elo_mmr_canonical_player_match_facts(server_slug, external_match_id, stable_player_key);

CREATE TABLE IF NOT EXISTS elo_event_lineage_headers (
    canonical_event_id TEXT NOT NULL PRIMARY KEY,
    event_family TEXT NOT NULL,
    source_event_id TEXT,
    canonical_match_key TEXT NOT NULL,
    server_slug TEXT NOT NULL,
    stable_player_key TEXT,
    actor_player_key TEXT,
    target_player_key TEXT,
    occurred_at TEXT,
    match_second INTEGER,
    event_time_status TEXT NOT NULL DEFAULT 'not_available',
    event_window_start_second INTEGER,
    event_window_end_second INTEGER,
    event_type TEXT NOT NULL,
    event_subtype TEXT,
    event_value INTEGER NOT NULL DEFAULT 1,
    team_side TEXT,
    role_at_event_time TEXT,
    source_kind TEXT NOT NULL,
    source_reliability TEXT NOT NULL DEFAULT 'unverified',
    capability_status TEXT NOT NULL DEFAULT 'not_available',
    source_payload_ref TEXT,
    raw_payload_strategy TEXT NOT NULL DEFAULT 'payload-ref-or-none',
    dedupe_key TEXT NOT NULL,
    dedupe_strategy TEXT NOT NULL DEFAULT 'family-plus-lineage-plus-timing',
    replay_safe INTEGER NOT NULL DEFAULT 1,
    contract_version TEXT NOT NULL DEFAULT '',
    storage_strategy TEXT NOT NULL DEFAULT 'hybrid-header-plus-family-detail',
    inserted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP::text,
    FOREIGN KEY (canonical_match_key) REFERENCES elo_mmr_canonical_matches(canonical_match_key),
    FOREIGN KEY (stable_player_key) REFERENCES elo_mmr_canonical_players(stable_player_key),
    FOREIGN KEY (actor_player_key) REFERENCES elo_mmr_canonical_players(stable_player_key),
    FOREIGN KEY (target_player_key) REFERENCES elo_mmr_canonical_players(stable_player_key),
    UNIQUE(event_family, dedupe_key)
);

CREATE TABLE IF NOT EXISTS elo_event_capability_registry (
    event_family TEXT NOT NULL,
    source_kind TEXT NOT NULL,
    capability_status TEXT NOT NULL,
    instrumentation_status TEXT NOT NULL,
    storage_contract_status TEXT NOT NULL,
    notes TEXT,
    contract_version TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP::text,
    PRIMARY KEY (event_family, source_kind)
);

CREATE TABLE IF NOT EXISTS elo_event_garrison_details (
    canonical_event_id TEXT NOT NULL PRIMARY KEY,
    action_kind TEXT NOT NULL,
    structure_team_side TEXT,
    sector_name TEXT,
    grid_reference TEXT,
    placement_rule TEXT,
    red_zone_flag INTEGER NOT NULL DEFAULT 0,
    structure_health_state TEXT,
    linked_spawn_type TEXT,
    FOREIGN KEY (canonical_event_id) REFERENCES elo_event_lineage_headers(canonical_event_id)
);

CREATE TABLE IF NOT EXISTS elo_event_outpost_details (
    canonical_event_id TEXT NOT NULL PRIMARY KEY,
    action_kind TEXT NOT NULL,
    structure_team_side TEXT,
    squad_ref TEXT,
    sector_name TEXT,
    grid_reference TEXT,
    placement_rule TEXT,
    structure_health_state TEXT,
    FOREIGN KEY (canonical_event_id) REFERENCES elo_event_lineage_headers(canonical_event_id)
);

CREATE TABLE IF NOT EXISTS elo_event_revive_details (
    canonical_event_id TEXT NOT NULL PRIMARY KEY,
    revive_method TEXT,
    target_role TEXT,
    target_team_side TEXT,
    distance_meters DOUBLE PRECISION,
    success_state TEXT,
    downed_cause_category TEXT,
    FOREIGN KEY (canonical_event_id) REFERENCES elo_event_lineage_headers(canonical_event_id)
);

CREATE TABLE IF NOT EXISTS elo_event_supply_details (
    canonical_event_id TEXT NOT NULL PRIMARY KEY,
    action_kind TEXT NOT NULL,
    supply_channel TEXT,
    supply_amount INTEGER,
    supply_amount_used INTEGER,
    target_object_type TEXT,
    sector_name TEXT,
    grid_reference TEXT,
    effectiveness_mode TEXT NOT NULL DEFAULT 'not_available',
    FOREIGN KEY (canonical_event_id) REFERENCES elo_event_lineage_headers(canonical_event_id)
);

CREATE TABLE IF NOT EXISTS elo_event_node_details (
    canonical_event_id TEXT NOT NULL PRIMARY KEY,
    action_kind TEXT NOT NULL,
    node_type TEXT,
    node_tier TEXT,
    active_seconds INTEGER,
    resource_generated_amount INTEGER,
    sector_name TEXT,
    grid_reference TEXT,
    structure_health_state TEXT,
    FOREIGN KEY (canonical_event_id) REFERENCES elo_event_lineage_headers(canonical_event_id)
);

CREATE TABLE IF NOT EXISTS elo_event_repair_details (
    canonical_event_id TEXT NOT NULL PRIMARY KEY,
    repair_target_type TEXT,
    repair_target_name TEXT,
    repair_amount DOUBLE PRECISION,
    repair_seconds INTEGER,
    target_team_side TEXT,
    repair_result TEXT,
    FOREIGN KEY (canonical_event_id) REFERENCES elo_event_lineage_headers(canonical_event_id)
);

CREATE TABLE IF NOT EXISTS elo_event_mine_details (
    canonical_event_id TEXT NOT NULL PRIMARY KEY,
    action_kind TEXT NOT NULL,
    mine_type TEXT,
    placement_grid_reference TEXT,
    trigger_result TEXT,
    victim_team_side TEXT,
    destroyed_by_category TEXT,
    multi_kill_count INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (canonical_event_id) REFERENCES elo_event_lineage_headers(canonical_event_id)
);

CREATE TABLE IF NOT EXISTS elo_event_commander_ability_details (
    canonical_event_id TEXT NOT NULL PRIMARY KEY,
    ability_type TEXT NOT NULL,
    ability_variant TEXT,
    target_team_side TEXT,
    target_sector_name TEXT,
    target_grid_reference TEXT,
    cooldown_seconds INTEGER,
    impact_window_seconds INTEGER,
    FOREIGN KEY (canonical_event_id) REFERENCES elo_event_lineage_headers(canonical_event_id)
);

CREATE TABLE IF NOT EXISTS elo_event_strongpoint_presence_details (
    canonical_event_id TEXT NOT NULL PRIMARY KEY,
    presence_kind TEXT NOT NULL,
    strongpoint_name TEXT,
    strongpoint_phase TEXT,
    occupancy_seconds INTEGER,
    contest_seconds INTEGER,
    presence_team_side TEXT,
    occupancy_source_granularity TEXT NOT NULL DEFAULT 'not_available',
    FOREIGN KEY (canonical_event_id) REFERENCES elo_event_lineage_headers(canonical_event_id)
);

CREATE TABLE IF NOT EXISTS elo_event_role_assignment_details (
    canonical_event_id TEXT NOT NULL PRIMARY KEY,
    role_name TEXT,
    role_class TEXT,
    assignment_kind TEXT NOT NULL,
    assigned_by_player_key TEXT,
    role_start_second INTEGER,
    role_end_second INTEGER,
    role_duration_seconds INTEGER,
    squad_ref TEXT,
    FOREIGN KEY (canonical_event_id) REFERENCES elo_event_lineage_headers(canonical_event_id)
);

CREATE TABLE IF NOT EXISTS elo_event_disconnect_leave_admin_details (
    canonical_event_id TEXT NOT NULL PRIMARY KEY,
    action_kind TEXT NOT NULL,
    action_reason_code TEXT,
    action_reason_text TEXT,
    admin_action_type TEXT,
    removal_scope TEXT,
    returned_before_match_end INTEGER,
    return_delay_seconds INTEGER,
    FOREIGN KEY (canonical_event_id) REFERENCES elo_event_lineage_headers(canonical_event_id)
);

CREATE TABLE IF NOT EXISTS elo_event_death_classification_details (
    canonical_event_id TEXT NOT NULL PRIMARY KEY,
    death_class TEXT NOT NULL,
    death_subclass TEXT,
    weapon_name TEXT,
    weapon_category TEXT,
    damage_source_kind TEXT,
    is_friendly_fire INTEGER NOT NULL DEFAULT 0,
    is_redeploy INTEGER NOT NULL DEFAULT 0,
    is_self_inflicted INTEGER NOT NULL DEFAULT 0,
    is_menu_exit INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (canonical_event_id) REFERENCES elo_event_lineage_headers(canonical_event_id)
);

CREATE TABLE IF NOT EXISTS elo_mmr_normalization_buckets (
    bucket_key TEXT NOT NULL PRIMARY KEY,
    bucket_version TEXT NOT NULL,
    normalization_version TEXT NOT NULL,
    role_primary TEXT NOT NULL,
    role_primary_mode TEXT NOT NULL,
    game_mode TEXT NOT NULL,
    duration_bucket TEXT NOT NULL,
    participation_bucket TEXT NOT NULL,
    player_count_bucket TEXT NOT NULL,
    match_shape_bucket TEXT NOT NULL,
    sample_count INTEGER NOT NULL DEFAULT 0,
    insufficient_sample INTEGER NOT NULL DEFAULT 0,
    fallback_bucket_key TEXT,
    fallback_reason TEXT,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP::text
);

CREATE TABLE IF NOT EXISTS elo_mmr_normalization_baselines (
    bucket_key TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    sample_count INTEGER NOT NULL DEFAULT 0,
    avg_value DOUBLE PRECISION NOT NULL DEFAULT 0,
    min_value DOUBLE PRECISION NOT NULL DEFAULT 0,
    max_value DOUBLE PRECISION NOT NULL DEFAULT 0,
    p50_value DOUBLE PRECISION NOT NULL DEFAULT 0,
    p90_value DOUBLE PRECISION NOT NULL DEFAULT 0,
    normalization_version TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP::text,
    PRIMARY KEY (bucket_key, metric_name),
    FOREIGN KEY (bucket_key) REFERENCES elo_mmr_normalization_buckets(bucket_key)
);

CREATE INDEX IF NOT EXISTS idx_elo_event_headers_match_family
    ON elo_event_lineage_headers(canonical_match_key, event_family, occurred_at, match_second);

CREATE INDEX IF NOT EXISTS idx_elo_event_headers_actor_target
    ON elo_event_lineage_headers(actor_player_key, target_player_key, event_family);

CREATE INDEX IF NOT EXISTS idx_elo_mmr_normalization_buckets_role
    ON elo_mmr_normalization_buckets(role_primary, game_mode, duration_bucket, participation_bucket);
