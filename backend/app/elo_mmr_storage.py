"""SQLite storage for persistent Elo/MMR and monthly ranking results."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from .config import get_storage_path
from .elo_event_telemetry_contract import ELO_EVENT_TELEMETRY_CONTRACT_VERSION
from .elo_mmr_models import (
    CAPABILITY_APPROXIMATE,
    CAPABILITY_UNAVAILABLE,
    NORMALIZATION_BASELINE_VERSION,
    NORMALIZATION_BUCKET_VERSION,
    NORMALIZATION_MIN_BUCKET_SAMPLE,
)
from .player_event_storage import initialize_player_event_storage
from .sqlite_utils import connect_sqlite_readonly, connect_sqlite_writer

ELO_MMR_CANONICAL_FACT_SCHEMA_VERSION = "elo-canonical-v3"
ELO_MMR_CANONICAL_SOURCE_INPUT_VERSION = "historical-closed-match-v1-plus-player-event-summary-v1"


def initialize_elo_mmr_storage(*, db_path: Path | None = None) -> Path:
    """Create the Elo/MMR persistence tables in the shared backend SQLite."""
    resolved_path = _resolve_db_path(db_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    with _connect_writer(resolved_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS elo_mmr_player_ratings (
                scope_key TEXT NOT NULL,
                stable_player_key TEXT NOT NULL,
                player_name TEXT NOT NULL,
                steam_id TEXT,
                current_mmr REAL NOT NULL,
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
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
                quality_factor REAL NOT NULL,
                quality_bucket TEXT NOT NULL,
                role_bucket TEXT NOT NULL,
                role_bucket_mode TEXT NOT NULL,
                outcome_score REAL NOT NULL,
                combat_index REAL NOT NULL,
                objective_index REAL,
                objective_index_mode TEXT NOT NULL,
                utility_index REAL,
                utility_index_mode TEXT NOT NULL,
                leadership_index REAL,
                leadership_index_mode TEXT NOT NULL,
                discipline_index REAL,
                discipline_index_mode TEXT NOT NULL,
                impact_score REAL NOT NULL,
                delta_mmr REAL NOT NULL,
                mmr_before REAL NOT NULL,
                mmr_after REAL NOT NULL,
                match_score REAL NOT NULL,
                penalty_points REAL NOT NULL,
                time_seconds INTEGER NOT NULL DEFAULT 0,
                participation_ratio REAL NOT NULL DEFAULT 0,
                strength_of_schedule_match REAL NOT NULL DEFAULT 0,
                team_outcome TEXT,
                own_team_average_mmr REAL NOT NULL DEFAULT 0,
                enemy_team_average_mmr REAL NOT NULL DEFAULT 0,
                expected_result REAL NOT NULL DEFAULT 0,
                actual_result REAL NOT NULL DEFAULT 0,
                won_score REAL NOT NULL DEFAULT 0,
                margin_boost REAL NOT NULL DEFAULT 0,
                outcome_adjusted REAL NOT NULL DEFAULT 0,
                match_impact REAL NOT NULL DEFAULT 0,
                combat_contribution REAL NOT NULL DEFAULT 0,
                objective_contribution REAL NOT NULL DEFAULT 0,
                utility_contribution REAL NOT NULL DEFAULT 0,
                survival_discipline_contribution REAL NOT NULL DEFAULT 0,
                exact_component_contribution REAL NOT NULL DEFAULT 0,
                proxy_component_contribution REAL NOT NULL DEFAULT 0,
                normalization_bucket_key TEXT NOT NULL DEFAULT '',
                normalization_fallback_reason TEXT,
                elo_core_delta REAL NOT NULL DEFAULT 0,
                performance_modifier_delta REAL NOT NULL DEFAULT 0,
                proxy_modifier_delta REAL NOT NULL DEFAULT 0,
                canonical_fact_capability_status TEXT NOT NULL DEFAULT 'not_available',
                identity_capability_status TEXT NOT NULL DEFAULT 'not_available',
                match_duration_seconds INTEGER NOT NULL DEFAULT 0,
                duration_source_status TEXT NOT NULL DEFAULT 'not_available',
                duration_bucket TEXT NOT NULL DEFAULT 'unknown',
                player_count INTEGER NOT NULL DEFAULT 0,
                objective_score_proxy INTEGER NOT NULL DEFAULT 0,
                objective_score_proxy_mode TEXT NOT NULL DEFAULT 'approximate',
                kills_per_minute REAL NOT NULL DEFAULT 0,
                combat_per_minute REAL NOT NULL DEFAULT 0,
                support_per_minute REAL NOT NULL DEFAULT 0,
                objective_proxy_per_minute REAL NOT NULL DEFAULT 0,
                participation_bucket TEXT NOT NULL DEFAULT 'none',
                participation_mode TEXT NOT NULL DEFAULT 'not_available',
                participation_quality_score REAL NOT NULL DEFAULT 0,
                capabilities_json TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
                current_mmr REAL NOT NULL,
                baseline_mmr REAL NOT NULL,
                mmr_gain REAL NOT NULL,
                avg_match_score REAL NOT NULL,
                strength_of_schedule REAL NOT NULL,
                consistency REAL NOT NULL,
                activity REAL NOT NULL,
                confidence REAL NOT NULL,
                penalty_points REAL NOT NULL,
                monthly_rank_score REAL NOT NULL,
                valid_matches INTEGER NOT NULL,
                total_matches INTEGER NOT NULL,
                total_time_seconds INTEGER NOT NULL,
                eligible INTEGER NOT NULL,
                eligibility_reason TEXT,
                accuracy_mode TEXT NOT NULL,
                capabilities_json TEXT NOT NULL,
                component_scores_json TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
                kills_per_minute REAL NOT NULL DEFAULT 0,
                combat_per_minute REAL NOT NULL DEFAULT 0,
                support_per_minute REAL NOT NULL DEFAULT 0,
                objective_proxy_per_minute REAL NOT NULL DEFAULT 0,
                participation_ratio REAL NOT NULL DEFAULT 0,
                participation_bucket TEXT NOT NULL DEFAULT 'none',
                participation_mode TEXT NOT NULL DEFAULT 'not_available',
                participation_quality_score REAL NOT NULL DEFAULT 0,
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
                supply_effectiveness REAL NOT NULL DEFAULT 0,
                supply_event_mode TEXT NOT NULL DEFAULT 'not_available',
                nodes_built INTEGER NOT NULL DEFAULT 0,
                nodes_destroyed INTEGER NOT NULL DEFAULT 0,
                node_active_seconds INTEGER NOT NULL DEFAULT 0,
                node_event_mode TEXT NOT NULL DEFAULT 'not_available',
                repairs_performed INTEGER NOT NULL DEFAULT 0,
                repair_points REAL NOT NULL DEFAULT 0,
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
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
                inserted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
                distance_meters REAL,
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
                repair_amount REAL,
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
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS elo_mmr_normalization_baselines (
                bucket_key TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                sample_count INTEGER NOT NULL DEFAULT 0,
                avg_value REAL NOT NULL DEFAULT 0,
                min_value REAL NOT NULL DEFAULT 0,
                max_value REAL NOT NULL DEFAULT 0,
                p50_value REAL NOT NULL DEFAULT 0,
                p90_value REAL NOT NULL DEFAULT 0,
                normalization_version TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (bucket_key, metric_name),
                FOREIGN KEY (bucket_key) REFERENCES elo_mmr_normalization_buckets(bucket_key)
            );

            CREATE INDEX IF NOT EXISTS idx_elo_event_headers_match_family
            ON elo_event_lineage_headers(canonical_match_key, event_family, occurred_at, match_second);

            CREATE INDEX IF NOT EXISTS idx_elo_event_headers_actor_target
            ON elo_event_lineage_headers(actor_player_key, target_player_key, event_family);

            CREATE INDEX IF NOT EXISTS idx_elo_mmr_normalization_buckets_role
            ON elo_mmr_normalization_buckets(role_primary, game_mode, duration_bucket, participation_bucket);
            """
        )
        _ensure_schema_extensions(connection)
        _seed_elo_event_capability_registry(connection)
    return resolved_path


def replace_elo_mmr_state(
    *,
    player_ratings: list[dict[str, object]],
    match_results: list[dict[str, object]],
    monthly_rankings: list[dict[str, object]],
    monthly_checkpoints: list[dict[str, object]],
    db_path: Path | None = None,
) -> Path:
    """Replace the persisted Elo/MMR state with a freshly rebuilt dataset."""
    resolved_path = initialize_elo_mmr_storage(db_path=db_path)
    with _connect_writer(resolved_path) as connection:
        connection.execute("DELETE FROM elo_mmr_monthly_checkpoints")
        connection.execute("DELETE FROM elo_mmr_monthly_rankings")
        connection.execute("DELETE FROM elo_mmr_match_results")
        connection.execute("DELETE FROM elo_mmr_player_ratings")

        connection.executemany(
            """
            INSERT INTO elo_mmr_player_ratings (
                scope_key,
                stable_player_key,
                player_name,
                steam_id,
                current_mmr,
                matches_processed,
                wins,
                draws,
                losses,
                last_match_id,
                last_match_ended_at,
                model_version,
                formula_version,
                contract_version,
                accuracy_mode,
                capabilities_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["scope_key"],
                    row["stable_player_key"],
                    row["player_name"],
                    row.get("steam_id"),
                    row["current_mmr"],
                    row["matches_processed"],
                    row["wins"],
                    row["draws"],
                    row["losses"],
                    row.get("last_match_id"),
                    row.get("last_match_ended_at"),
                    row.get("model_version", ""),
                    row.get("formula_version", ""),
                    row.get("contract_version", ""),
                    row["accuracy_mode"],
                    json.dumps(row["capabilities"], ensure_ascii=True, separators=(",", ":")),
                )
                for row in player_ratings
            ],
        )

        connection.executemany(
            """
            INSERT INTO elo_mmr_match_results (
                scope_key,
                month_key,
                canonical_match_key,
                external_match_id,
                stable_player_key,
                player_name,
                steam_id,
                server_slug,
                server_name,
                match_ended_at,
                fact_schema_version,
                source_input_version,
                model_version,
                formula_version,
                contract_version,
                match_valid,
                quality_factor,
                quality_bucket,
                role_bucket,
                role_bucket_mode,
                outcome_score,
                combat_index,
                objective_index,
                objective_index_mode,
                utility_index,
                utility_index_mode,
                leadership_index,
                leadership_index_mode,
                discipline_index,
                discipline_index_mode,
                impact_score,
                delta_mmr,
                mmr_before,
                mmr_after,
                match_score,
                penalty_points,
                time_seconds,
                participation_ratio,
                strength_of_schedule_match,
                team_outcome,
                own_team_average_mmr,
                enemy_team_average_mmr,
                expected_result,
                actual_result,
                won_score,
                margin_boost,
                outcome_adjusted,
                match_impact,
                combat_contribution,
                objective_contribution,
                utility_contribution,
                survival_discipline_contribution,
                exact_component_contribution,
                proxy_component_contribution,
                normalization_bucket_key,
                normalization_fallback_reason,
                elo_core_delta,
                performance_modifier_delta,
                proxy_modifier_delta,
                canonical_fact_capability_status,
                identity_capability_status,
                match_duration_seconds,
                duration_source_status,
                duration_bucket,
                player_count,
                objective_score_proxy,
                objective_score_proxy_mode,
                kills_per_minute,
                combat_per_minute,
                support_per_minute,
                objective_proxy_per_minute,
                participation_bucket,
                participation_mode,
                participation_quality_score,
                capabilities_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["scope_key"],
                    row["month_key"],
                    row.get("canonical_match_key", ""),
                    row["external_match_id"],
                    row["stable_player_key"],
                    row["player_name"],
                    row.get("steam_id"),
                    row["server_slug"],
                    row["server_name"],
                    row["match_ended_at"],
                    row.get("fact_schema_version", ""),
                    row.get("source_input_version", ""),
                    row.get("model_version", ""),
                    row.get("formula_version", ""),
                    row.get("contract_version", ""),
                    1 if row["match_valid"] else 0,
                    row["quality_factor"],
                    row["quality_bucket"],
                    row["role_bucket"],
                    row["role_bucket_mode"],
                    row["outcome_score"],
                    row["combat_index"],
                    row.get("objective_index"),
                    row["objective_index_mode"],
                    row.get("utility_index"),
                    row["utility_index_mode"],
                    row.get("leadership_index"),
                    row["leadership_index_mode"],
                    row.get("discipline_index"),
                    row["discipline_index_mode"],
                    row["impact_score"],
                    row["delta_mmr"],
                    row["mmr_before"],
                    row["mmr_after"],
                    row["match_score"],
                    row["penalty_points"],
                    row.get("time_seconds", 0),
                    row.get("participation_ratio", 0.0),
                    row.get("strength_of_schedule_match", 0.0),
                    row.get("team_outcome"),
                    row.get("own_team_average_mmr", 0.0),
                    row.get("enemy_team_average_mmr", 0.0),
                    row.get("expected_result", 0.0),
                    row.get("actual_result", 0.0),
                    row.get("won_score", 0.0),
                    row.get("margin_boost", 0.0),
                    row.get("outcome_adjusted", 0.0),
                    row.get("match_impact", 0.0),
                    row.get("combat_contribution", 0.0),
                    row.get("objective_contribution", 0.0),
                    row.get("utility_contribution", 0.0),
                    row.get("survival_discipline_contribution", 0.0),
                    row.get("exact_component_contribution", 0.0),
                    row.get("proxy_component_contribution", 0.0),
                    row.get("normalization_bucket_key", ""),
                    row.get("normalization_fallback_reason"),
                    row.get("elo_core_delta", 0.0),
                    row.get("performance_modifier_delta", 0.0),
                    row.get("proxy_modifier_delta", 0.0),
                    row.get("canonical_fact_capability_status", "not_available"),
                    row.get("identity_capability_status", "not_available"),
                    row.get("match_duration_seconds", 0),
                    row.get("duration_source_status", "not_available"),
                    row.get("duration_bucket", "unknown"),
                    row.get("player_count", 0),
                    row.get("objective_score_proxy", 0),
                    row.get("objective_score_proxy_mode", "approximate"),
                    row.get("kills_per_minute", 0.0),
                    row.get("combat_per_minute", 0.0),
                    row.get("support_per_minute", 0.0),
                    row.get("objective_proxy_per_minute", 0.0),
                    row.get("participation_bucket", "none"),
                    row.get("participation_mode", "not_available"),
                    row.get("participation_quality_score", 0.0),
                    json.dumps(row["capabilities"], ensure_ascii=True, separators=(",", ":")),
                )
                for row in match_results
            ],
        )

        connection.executemany(
            """
            INSERT INTO elo_mmr_monthly_rankings (
                scope_key,
                month_key,
                stable_player_key,
                player_name,
                steam_id,
                model_version,
                formula_version,
                contract_version,
                current_mmr,
                baseline_mmr,
                mmr_gain,
                avg_match_score,
                strength_of_schedule,
                consistency,
                activity,
                confidence,
                penalty_points,
                monthly_rank_score,
                valid_matches,
                total_matches,
                total_time_seconds,
                avg_participation_ratio,
                eligible,
                eligibility_reason,
                accuracy_mode,
                capabilities_json,
                component_scores_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["scope_key"],
                    row["month_key"],
                    row["stable_player_key"],
                    row["player_name"],
                    row.get("steam_id"),
                    row.get("model_version", ""),
                    row.get("formula_version", ""),
                    row.get("contract_version", ""),
                    row["current_mmr"],
                    row["baseline_mmr"],
                    row["mmr_gain"],
                    row["avg_match_score"],
                    row["strength_of_schedule"],
                    row["consistency"],
                    row["activity"],
                    row["confidence"],
                    row["penalty_points"],
                    row["monthly_rank_score"],
                    row["valid_matches"],
                    row["total_matches"],
                    row["total_time_seconds"],
                    row.get("avg_participation_ratio", 0.0),
                    1 if row["eligible"] else 0,
                    row.get("eligibility_reason"),
                    row["accuracy_mode"],
                    json.dumps(row["capabilities"], ensure_ascii=True, separators=(",", ":")),
                    json.dumps(row["component_scores"], ensure_ascii=True, separators=(",", ":")),
                )
                for row in monthly_rankings
            ],
        )

        connection.executemany(
            """
            INSERT INTO elo_mmr_monthly_checkpoints (
                scope_key,
                month_key,
                generated_at,
                model_version,
                formula_version,
                contract_version,
                player_count,
                eligible_player_count,
                source_policy_json,
                capabilities_summary_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["scope_key"],
                    row["month_key"],
                    row["generated_at"],
                    row.get("model_version", ""),
                    row.get("formula_version", ""),
                    row.get("contract_version", ""),
                    row["player_count"],
                    row["eligible_player_count"],
                    json.dumps(row["source_policy"], ensure_ascii=True, separators=(",", ":")),
                    json.dumps(
                        row["capabilities_summary"],
                        ensure_ascii=True,
                        separators=(",", ":"),
                    ),
                )
                for row in monthly_checkpoints
            ],
        )
    return resolved_path


def replace_elo_mmr_monthly_state(
    *,
    monthly_rankings: list[dict[str, object]],
    monthly_checkpoints: list[dict[str, object]],
    db_path: Path | None = None,
) -> Path:
    """Replace only the persisted monthly Elo/MMR state with a freshly built dataset."""
    resolved_path = initialize_elo_mmr_storage(db_path=db_path)
    with _connect_writer(resolved_path) as connection:
        connection.execute("DELETE FROM elo_mmr_monthly_checkpoints")
        connection.execute("DELETE FROM elo_mmr_monthly_rankings")

        connection.executemany(
            """
            INSERT INTO elo_mmr_monthly_rankings (
                scope_key,
                month_key,
                stable_player_key,
                player_name,
                steam_id,
                model_version,
                formula_version,
                contract_version,
                current_mmr,
                baseline_mmr,
                mmr_gain,
                avg_match_score,
                strength_of_schedule,
                consistency,
                activity,
                confidence,
                penalty_points,
                monthly_rank_score,
                valid_matches,
                total_matches,
                total_time_seconds,
                avg_participation_ratio,
                eligible,
                eligibility_reason,
                accuracy_mode,
                capabilities_json,
                component_scores_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["scope_key"],
                    row["month_key"],
                    row["stable_player_key"],
                    row["player_name"],
                    row.get("steam_id"),
                    row.get("model_version", ""),
                    row.get("formula_version", ""),
                    row.get("contract_version", ""),
                    row["current_mmr"],
                    row["baseline_mmr"],
                    row["mmr_gain"],
                    row["avg_match_score"],
                    row["strength_of_schedule"],
                    row["consistency"],
                    row["activity"],
                    row["confidence"],
                    row["penalty_points"],
                    row["monthly_rank_score"],
                    row["valid_matches"],
                    row["total_matches"],
                    row["total_time_seconds"],
                    row.get("avg_participation_ratio", 0.0),
                    1 if row["eligible"] else 0,
                    row.get("eligibility_reason"),
                    row["accuracy_mode"],
                    json.dumps(row["capabilities"], ensure_ascii=True, separators=(",", ":")),
                    json.dumps(row["component_scores"], ensure_ascii=True, separators=(",", ":")),
                )
                for row in monthly_rankings
            ],
        )

        connection.executemany(
            """
            INSERT INTO elo_mmr_monthly_checkpoints (
                scope_key,
                month_key,
                generated_at,
                model_version,
                formula_version,
                contract_version,
                player_count,
                eligible_player_count,
                source_policy_json,
                capabilities_summary_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["scope_key"],
                    row["month_key"],
                    row["generated_at"],
                    row.get("model_version", ""),
                    row.get("formula_version", ""),
                    row.get("contract_version", ""),
                    row["player_count"],
                    row["eligible_player_count"],
                    json.dumps(row["source_policy"], ensure_ascii=True, separators=(",", ":")),
                    json.dumps(
                        row["capabilities_summary"],
                        ensure_ascii=True,
                        separators=(",", ":"),
                    ),
                )
                for row in monthly_checkpoints
            ],
        )
    return resolved_path


def list_elo_mmr_match_results(*, db_path: Path | None = None) -> list[dict[str, object]]:
    """Return persisted match-result rows for monthly rematerialization or audits."""
    resolved_path = _resolve_db_path(db_path)
    try:
        with _connect_readonly(resolved_path) as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM elo_mmr_match_results
                ORDER BY
                    match_ended_at ASC,
                    scope_key ASC,
                    external_match_id ASC,
                    stable_player_key ASC
                """
            ).fetchall()
    except sqlite3.OperationalError:
        return []
    items: list[dict[str, object]] = []
    for row in rows:
        item = dict(row)
        item["match_valid"] = bool(item.get("match_valid"))
        item["capabilities"] = json.loads(item["capabilities_json"])
        items.append(item)
    return items


def rebuild_elo_mmr_canonical_facts(*, db_path: Path | None = None) -> dict[str, object]:
    """Materialize the canonical Elo fact layer from persisted historical closed matches."""
    resolved_path = initialize_elo_mmr_storage(db_path=db_path)
    initialize_player_event_storage(db_path=resolved_path)
    with _connect_writer(resolved_path) as connection:
        connection.execute("DELETE FROM elo_mmr_canonical_player_match_facts")
        connection.execute("DELETE FROM elo_event_garrison_details")
        connection.execute("DELETE FROM elo_event_outpost_details")
        connection.execute("DELETE FROM elo_event_revive_details")
        connection.execute("DELETE FROM elo_event_supply_details")
        connection.execute("DELETE FROM elo_event_node_details")
        connection.execute("DELETE FROM elo_event_repair_details")
        connection.execute("DELETE FROM elo_event_mine_details")
        connection.execute("DELETE FROM elo_event_commander_ability_details")
        connection.execute("DELETE FROM elo_event_strongpoint_presence_details")
        connection.execute("DELETE FROM elo_event_role_assignment_details")
        connection.execute("DELETE FROM elo_event_disconnect_leave_admin_details")
        connection.execute("DELETE FROM elo_event_death_classification_details")
        connection.execute("DELETE FROM elo_event_lineage_headers")
        connection.execute("DELETE FROM elo_mmr_canonical_matches")
        connection.execute("DELETE FROM elo_mmr_canonical_players")

        connection.execute(
            """
            INSERT INTO elo_mmr_canonical_players (
                stable_player_key,
                player_name,
                steam_id,
                identity_capability_status,
                identity_source,
                first_seen_at,
                last_seen_at,
                fact_schema_version
            )
            SELECT
                historical_players.stable_player_key,
                MAX(COALESCE(NULLIF(historical_players.display_name, ''), 'Unknown player')) AS player_name,
                MAX(NULLIF(historical_players.steam_id, '')) AS steam_id,
                CASE
                    WHEN MAX(NULLIF(historical_players.steam_id, '')) IS NOT NULL THEN 'exact'
                    WHEN MAX(NULLIF(historical_players.source_player_id, '')) IS NOT NULL THEN 'approximate'
                    ELSE 'not_available'
                END AS identity_capability_status,
                CASE
                    WHEN MAX(NULLIF(historical_players.steam_id, '')) IS NOT NULL THEN 'steam-id'
                    WHEN MAX(NULLIF(historical_players.source_player_id, '')) IS NOT NULL THEN 'source-player-id'
                    ELSE 'stable-player-key-only'
                END AS identity_source,
                MIN(historical_matches.ended_at) AS first_seen_at,
                MAX(historical_matches.ended_at) AS last_seen_at,
                ? AS fact_schema_version
            FROM historical_players
            LEFT JOIN historical_player_match_stats
                ON historical_player_match_stats.historical_player_id = historical_players.id
            LEFT JOIN historical_matches
                ON historical_matches.id = historical_player_match_stats.historical_match_id
               AND historical_matches.ended_at IS NOT NULL
            GROUP BY historical_players.stable_player_key
            """,
            (ELO_MMR_CANONICAL_FACT_SCHEMA_VERSION,),
        )

        connection.execute(
            """
            INSERT INTO elo_mmr_canonical_matches (
                canonical_match_key,
                server_slug,
                server_name,
                external_match_id,
                started_at,
                ended_at,
                game_mode,
                allied_score,
                axis_score,
                resolved_duration_seconds,
                duration_source_status,
                duration_bucket,
                player_count,
                match_capability_status,
                source_kind,
                fact_schema_version,
                source_input_version
            )
            SELECT
                canonical_match_key,
                server_slug,
                server_name,
                external_match_id,
                started_at,
                ended_at,
                game_mode,
                allied_score,
                axis_score,
                resolved_duration_seconds,
                duration_source_status,
                duration_bucket,
                player_count,
                CASE
                    WHEN started_at IS NOT NULL
                     AND allied_score IS NOT NULL
                     AND axis_score IS NOT NULL
                     AND resolved_duration_seconds > 0 THEN 'exact'
                    WHEN started_at IS NOT NULL
                      OR allied_score IS NOT NULL
                      OR axis_score IS NOT NULL
                      OR resolved_duration_seconds > 0 THEN 'approximate'
                    ELSE 'not_available'
                END AS match_capability_status,
                'historical-closed-match' AS source_kind,
                ? AS fact_schema_version,
                ? AS source_input_version
            FROM (
                SELECT
                    historical_servers.slug || ':' || historical_matches.external_match_id AS canonical_match_key,
                    historical_servers.slug AS server_slug,
                    historical_servers.display_name AS server_name,
                    historical_matches.external_match_id,
                    historical_matches.started_at,
                    historical_matches.ended_at,
                    historical_matches.game_mode,
                    historical_matches.allied_score,
                    historical_matches.axis_score,
                    COALESCE(match_rollup.player_count, 0) AS player_count,
                    CASE
                        WHEN historical_matches.started_at IS NOT NULL
                         AND historical_matches.ended_at IS NOT NULL
                         AND julianday(historical_matches.ended_at) >= julianday(historical_matches.started_at)
                            THEN CAST((julianday(historical_matches.ended_at) - julianday(historical_matches.started_at)) * 86400 AS INTEGER)
                        WHEN COALESCE(match_rollup.max_time_seconds, 0) > 0 THEN match_rollup.max_time_seconds
                        ELSE 0
                    END AS resolved_duration_seconds,
                    CASE
                        WHEN historical_matches.started_at IS NOT NULL
                         AND historical_matches.ended_at IS NOT NULL
                         AND julianday(historical_matches.ended_at) >= julianday(historical_matches.started_at) THEN 'exact'
                        WHEN COALESCE(match_rollup.max_time_seconds, 0) > 0 THEN 'approximate'
                        ELSE 'not_available'
                    END AS duration_source_status,
                    CASE
                        WHEN (
                            CASE
                                WHEN historical_matches.started_at IS NOT NULL
                                 AND historical_matches.ended_at IS NOT NULL
                                 AND julianday(historical_matches.ended_at) >= julianday(historical_matches.started_at)
                                    THEN CAST((julianday(historical_matches.ended_at) - julianday(historical_matches.started_at)) * 86400 AS INTEGER)
                                WHEN COALESCE(match_rollup.max_time_seconds, 0) > 0 THEN match_rollup.max_time_seconds
                                ELSE 0
                            END
                        ) >= 3600 THEN 'full'
                        WHEN (
                            CASE
                                WHEN historical_matches.started_at IS NOT NULL
                                 AND historical_matches.ended_at IS NOT NULL
                                 AND julianday(historical_matches.ended_at) >= julianday(historical_matches.started_at)
                                    THEN CAST((julianday(historical_matches.ended_at) - julianday(historical_matches.started_at)) * 86400 AS INTEGER)
                                WHEN COALESCE(match_rollup.max_time_seconds, 0) > 0 THEN match_rollup.max_time_seconds
                                ELSE 0
                            END
                        ) >= 1800 THEN 'standard'
                        WHEN (
                            CASE
                                WHEN historical_matches.started_at IS NOT NULL
                                 AND historical_matches.ended_at IS NOT NULL
                                 AND julianday(historical_matches.ended_at) >= julianday(historical_matches.started_at)
                                    THEN CAST((julianday(historical_matches.ended_at) - julianday(historical_matches.started_at)) * 86400 AS INTEGER)
                                WHEN COALESCE(match_rollup.max_time_seconds, 0) > 0 THEN match_rollup.max_time_seconds
                                ELSE 0
                            END
                        ) > 0 THEN 'short'
                        ELSE 'unknown'
                    END AS duration_bucket
                FROM historical_matches
                INNER JOIN historical_servers
                    ON historical_servers.id = historical_matches.historical_server_id
                LEFT JOIN (
                    SELECT
                        historical_match_id,
                        COUNT(*) AS player_count,
                        MAX(COALESCE(time_seconds, 0)) AS max_time_seconds
                    FROM historical_player_match_stats
                    GROUP BY historical_match_id
                ) AS match_rollup
                    ON match_rollup.historical_match_id = historical_matches.id
                WHERE historical_matches.ended_at IS NOT NULL
            )
            """,
            (
                ELO_MMR_CANONICAL_FACT_SCHEMA_VERSION,
                ELO_MMR_CANONICAL_SOURCE_INPUT_VERSION,
            ),
        )

        _ingest_summary_backed_canonical_events(connection)

        connection.execute(
            """
            INSERT INTO elo_mmr_canonical_player_match_facts (
                canonical_match_key,
                stable_player_key,
                server_slug,
                external_match_id,
                player_name,
                steam_id,
                team_side,
                kills,
                deaths,
                teamkills,
                time_seconds,
                combat,
                offense,
                defense,
                support,
                match_duration_seconds,
                match_duration_mode,
                duration_bucket,
                player_count,
                objective_score_proxy,
                objective_score_proxy_mode,
                kills_per_minute,
                combat_per_minute,
                support_per_minute,
                objective_proxy_per_minute,
                participation_ratio,
                participation_bucket,
                participation_mode,
                participation_quality_score,
                garrison_builds,
                garrison_destroys,
                garrison_event_mode,
                outpost_builds,
                outpost_destroys,
                outpost_event_mode,
                revives_given,
                revives_received,
                revive_event_mode,
                supplies_placed,
                supply_effectiveness,
                supply_event_mode,
                nodes_built,
                nodes_destroyed,
                node_active_seconds,
                node_event_mode,
                repairs_performed,
                repair_points,
                repair_event_mode,
                mines_placed,
                mine_kills,
                mine_destroys,
                mine_event_mode,
                commander_abilities_used,
                commander_ability_event_mode,
                strongpoint_occupancy_seconds,
                strongpoint_contest_seconds,
                strongpoint_event_mode,
                role_time_seconds,
                role_assignment_event_mode,
                disconnect_leave_count,
                admin_action_count,
                disconnect_leave_admin_event_mode,
                death_summary_combat_kills,
                death_summary_combat_deaths,
                death_summary_weapon_kills,
                death_summary_weapon_deaths,
                death_summary_teamkills,
                death_classification_event_mode,
                tactical_event_lineage_status,
                tactical_event_count,
                role_primary,
                role_primary_mode,
                normalization_bucket_key,
                normalization_bucket_version,
                normalization_fallback_bucket_key,
                normalization_fallback_reason,
                normalization_version,
                player_count_bucket,
                match_shape_bucket,
                teamkill_exact_count,
                leave_disconnect_exact_count,
                kick_or_ban_exact_count,
                admin_action_exact_count,
                combat_death_proxy_count,
                friendly_fire_proxy_count,
                redeploy_death_exact_count,
                suicide_death_exact_count,
                menu_exit_death_exact_count,
                discipline_capability_status,
                leave_admin_capability_status,
                death_type_capability_status,
                discipline_lineage_status,
                fact_capability_status,
                fact_schema_version,
                source_input_version
            )
            SELECT
                historical_servers.slug || ':' || historical_matches.external_match_id AS canonical_match_key,
                historical_players.stable_player_key,
                historical_servers.slug AS server_slug,
                historical_matches.external_match_id,
                COALESCE(NULLIF(historical_players.display_name, ''), canonical_players.player_name, 'Unknown player') AS player_name,
                NULLIF(historical_players.steam_id, '') AS steam_id,
                historical_player_match_stats.team_side,
                COALESCE(historical_player_match_stats.kills, 0) AS kills,
                COALESCE(historical_player_match_stats.deaths, 0) AS deaths,
                COALESCE(historical_player_match_stats.teamkills, 0) AS teamkills,
                COALESCE(historical_player_match_stats.time_seconds, 0) AS time_seconds,
                COALESCE(historical_player_match_stats.combat, 0) AS combat,
                COALESCE(historical_player_match_stats.offense, 0) AS offense,
                COALESCE(historical_player_match_stats.defense, 0) AS defense,
                COALESCE(historical_player_match_stats.support, 0) AS support,
                COALESCE(canonical_matches.resolved_duration_seconds, 0) AS match_duration_seconds,
                canonical_matches.duration_source_status AS match_duration_mode,
                canonical_matches.duration_bucket,
                canonical_matches.player_count,
                COALESCE(historical_player_match_stats.offense, 0) + COALESCE(historical_player_match_stats.defense, 0) AS objective_score_proxy,
                'approximate' AS objective_score_proxy_mode,
                CASE
                    WHEN COALESCE(historical_player_match_stats.time_seconds, 0) > 0 THEN ROUND((COALESCE(historical_player_match_stats.kills, 0) * 60.0) / historical_player_match_stats.time_seconds, 3)
                    ELSE 0.0
                END AS kills_per_minute,
                CASE
                    WHEN COALESCE(historical_player_match_stats.time_seconds, 0) > 0 THEN ROUND((COALESCE(historical_player_match_stats.combat, 0) * 60.0) / historical_player_match_stats.time_seconds, 3)
                    ELSE 0.0
                END AS combat_per_minute,
                CASE
                    WHEN COALESCE(historical_player_match_stats.time_seconds, 0) > 0 THEN ROUND((COALESCE(historical_player_match_stats.support, 0) * 60.0) / historical_player_match_stats.time_seconds, 3)
                    ELSE 0.0
                END AS support_per_minute,
                CASE
                    WHEN COALESCE(historical_player_match_stats.time_seconds, 0) > 0 THEN ROUND(((COALESCE(historical_player_match_stats.offense, 0) + COALESCE(historical_player_match_stats.defense, 0)) * 60.0) / historical_player_match_stats.time_seconds, 3)
                    ELSE 0.0
                END AS objective_proxy_per_minute,
                CASE
                    WHEN COALESCE(canonical_matches.resolved_duration_seconds, 0) <= 0 THEN 0.0
                    WHEN COALESCE(historical_player_match_stats.time_seconds, 0) >= canonical_matches.resolved_duration_seconds THEN 1.0
                    ELSE ROUND((historical_player_match_stats.time_seconds * 1.0) / canonical_matches.resolved_duration_seconds, 3)
                END AS participation_ratio,
                CASE
                    WHEN COALESCE(canonical_matches.resolved_duration_seconds, 0) <= 0
                      OR COALESCE(historical_player_match_stats.time_seconds, 0) <= 0 THEN 'none'
                    WHEN (historical_player_match_stats.time_seconds * 1.0) / canonical_matches.resolved_duration_seconds >= 0.85 THEN 'full'
                    WHEN (historical_player_match_stats.time_seconds * 1.0) / canonical_matches.resolved_duration_seconds >= 0.50 THEN 'core'
                    ELSE 'limited'
                END AS participation_bucket,
                CASE
                    WHEN canonical_matches.duration_source_status = 'exact' THEN 'exact'
                    WHEN canonical_matches.duration_source_status = 'approximate' THEN 'approximate'
                    ELSE 'not_available'
                END AS participation_mode,
                CASE
                    WHEN COALESCE(canonical_matches.resolved_duration_seconds, 0) <= 0 THEN 0.0
                    WHEN COALESCE(historical_player_match_stats.time_seconds, 0) >= canonical_matches.resolved_duration_seconds THEN 100.0
                    ELSE ROUND(((historical_player_match_stats.time_seconds * 1.0) / canonical_matches.resolved_duration_seconds) * 100.0, 3)
                END AS participation_quality_score,
                0 AS garrison_builds,
                0 AS garrison_destroys,
                'not_available' AS garrison_event_mode,
                0 AS outpost_builds,
                0 AS outpost_destroys,
                'not_available' AS outpost_event_mode,
                0 AS revives_given,
                0 AS revives_received,
                'not_available' AS revive_event_mode,
                0 AS supplies_placed,
                0.0 AS supply_effectiveness,
                'not_available' AS supply_event_mode,
                0 AS nodes_built,
                0 AS nodes_destroyed,
                0 AS node_active_seconds,
                'not_available' AS node_event_mode,
                0 AS repairs_performed,
                0.0 AS repair_points,
                'not_available' AS repair_event_mode,
                0 AS mines_placed,
                0 AS mine_kills,
                0 AS mine_destroys,
                'not_available' AS mine_event_mode,
                0 AS commander_abilities_used,
                'not_available' AS commander_ability_event_mode,
                0 AS strongpoint_occupancy_seconds,
                0 AS strongpoint_contest_seconds,
                'not_available' AS strongpoint_event_mode,
                0 AS role_time_seconds,
                'not_available' AS role_assignment_event_mode,
                0 AS disconnect_leave_count,
                0 AS admin_action_count,
                'not_available' AS disconnect_leave_admin_event_mode,
                COALESCE(death_summary_rollup.combat_kill_summaries, 0) AS death_summary_combat_kills,
                COALESCE(death_summary_rollup.combat_death_summaries, 0) AS death_summary_combat_deaths,
                COALESCE(death_summary_rollup.weapon_kill_summaries, 0) AS death_summary_weapon_kills,
                COALESCE(death_summary_rollup.weapon_death_summaries, 0) AS death_summary_weapon_deaths,
                COALESCE(death_summary_rollup.teamkill_summaries, 0) AS death_summary_teamkills,
                CASE
                    WHEN COALESCE(match_event_coverage.death_classification_event_count, 0) > 0 THEN 'approximate'
                    ELSE 'not_available'
                END AS death_classification_event_mode,
                CASE
                    WHEN COALESCE(match_event_coverage.death_classification_event_count, 0) > 0 THEN 'event-backed'
                    ELSE 'not_available'
                END AS tactical_event_lineage_status,
                COALESCE(death_summary_rollup.total_event_rows, 0) AS tactical_event_count,
                CASE
                    WHEN COALESCE(historical_player_match_stats.support, 0) > COALESCE(historical_player_match_stats.offense, 0)
                     AND COALESCE(historical_player_match_stats.support, 0) > COALESCE(historical_player_match_stats.defense, 0)
                     AND COALESCE(historical_player_match_stats.support, 0) > COALESCE(historical_player_match_stats.combat, 0) THEN 'support'
                    WHEN COALESCE(historical_player_match_stats.offense, 0) > COALESCE(historical_player_match_stats.defense, 0)
                     AND COALESCE(historical_player_match_stats.offense, 0) > COALESCE(historical_player_match_stats.combat, 0) THEN 'offense'
                    WHEN COALESCE(historical_player_match_stats.defense, 0) > COALESCE(historical_player_match_stats.combat, 0) THEN 'defense'
                    WHEN COALESCE(historical_player_match_stats.combat, 0) > 0 THEN 'combat'
                    ELSE 'generalist'
                END AS role_primary,
                CASE
                    WHEN COALESCE(historical_player_match_stats.time_seconds, 0) > 0
                      OR COALESCE(historical_player_match_stats.combat, 0) > 0
                      OR COALESCE(historical_player_match_stats.offense, 0) > 0
                      OR COALESCE(historical_player_match_stats.defense, 0) > 0
                      OR COALESCE(historical_player_match_stats.support, 0) > 0 THEN 'approximate'
                    ELSE 'not_available'
                END AS role_primary_mode,
                (
                    CASE
                        WHEN COALESCE(historical_player_match_stats.support, 0) > COALESCE(historical_player_match_stats.offense, 0)
                         AND COALESCE(historical_player_match_stats.support, 0) > COALESCE(historical_player_match_stats.defense, 0)
                         AND COALESCE(historical_player_match_stats.support, 0) > COALESCE(historical_player_match_stats.combat, 0) THEN 'support'
                        WHEN COALESCE(historical_player_match_stats.offense, 0) > COALESCE(historical_player_match_stats.defense, 0)
                         AND COALESCE(historical_player_match_stats.offense, 0) > COALESCE(historical_player_match_stats.combat, 0) THEN 'offense'
                        WHEN COALESCE(historical_player_match_stats.defense, 0) > COALESCE(historical_player_match_stats.combat, 0) THEN 'defense'
                        WHEN COALESCE(historical_player_match_stats.combat, 0) > 0 THEN 'combat'
                        ELSE 'generalist'
                    END
                    || '|'
                    || LOWER(COALESCE(NULLIF(canonical_matches.game_mode, ''), 'unknown'))
                    || '|'
                    || canonical_matches.duration_bucket
                    || '|'
                    || CASE
                        WHEN COALESCE(canonical_matches.resolved_duration_seconds, 0) <= 0
                          OR COALESCE(historical_player_match_stats.time_seconds, 0) <= 0 THEN 'none'
                        WHEN (historical_player_match_stats.time_seconds * 1.0) / canonical_matches.resolved_duration_seconds >= 0.85 THEN 'full'
                        WHEN (historical_player_match_stats.time_seconds * 1.0) / canonical_matches.resolved_duration_seconds >= 0.50 THEN 'core'
                        ELSE 'limited'
                    END
                    || '|'
                    || CASE
                        WHEN canonical_matches.player_count >= 70 THEN 'full'
                        WHEN canonical_matches.player_count >= 40 THEN 'standard'
                        WHEN canonical_matches.player_count > 0 THEN 'small'
                        ELSE 'unknown'
                    END
                    || '|'
                    || CASE
                        WHEN canonical_matches.player_count >= 70
                         AND canonical_matches.duration_bucket IN ('standard', 'full') THEN 'competitive-standard'
                        WHEN canonical_matches.player_count > 0 THEN 'underfilled'
                        ELSE 'unknown'
                    END
                ) AS normalization_bucket_key,
                ? AS normalization_bucket_version,
                NULL AS normalization_fallback_bucket_key,
                NULL AS normalization_fallback_reason,
                ? AS normalization_version,
                CASE
                    WHEN canonical_matches.player_count >= 70 THEN 'full'
                    WHEN canonical_matches.player_count >= 40 THEN 'standard'
                    WHEN canonical_matches.player_count > 0 THEN 'small'
                    ELSE 'unknown'
                END AS player_count_bucket,
                CASE
                    WHEN canonical_matches.player_count >= 70
                     AND canonical_matches.duration_bucket IN ('standard', 'full') THEN 'competitive-standard'
                    WHEN canonical_matches.player_count > 0 THEN 'underfilled'
                    ELSE 'unknown'
                END AS match_shape_bucket,
                COALESCE(historical_player_match_stats.teamkills, 0) AS teamkill_exact_count,
                0 AS leave_disconnect_exact_count,
                0 AS kick_or_ban_exact_count,
                0 AS admin_action_exact_count,
                COALESCE(death_summary_rollup.combat_death_summaries, 0) AS combat_death_proxy_count,
                COALESCE(death_summary_rollup.teamkill_summaries, 0) AS friendly_fire_proxy_count,
                0 AS redeploy_death_exact_count,
                0 AS suicide_death_exact_count,
                0 AS menu_exit_death_exact_count,
                CASE
                    WHEN COALESCE(historical_player_match_stats.teamkills, 0) > 0 THEN 'partial'
                    WHEN COALESCE(death_summary_rollup.teamkill_summaries, 0) > 0 THEN 'partial'
                    ELSE 'approximate'
                END AS discipline_capability_status,
                'not_available' AS leave_admin_capability_status,
                CASE
                    WHEN COALESCE(match_event_coverage.death_classification_event_count, 0) > 0 THEN 'approximate'
                    ELSE 'not_available'
                END AS death_type_capability_status,
                CASE
                    WHEN COALESCE(match_event_coverage.death_classification_event_count, 0) > 0 THEN 'scoreboard-teamkill-plus-summary-proxy'
                    WHEN COALESCE(historical_player_match_stats.teamkills, 0) > 0 THEN 'scoreboard-only-teamkill'
                    ELSE 'proxy-only'
                END AS discipline_lineage_status,
                CASE
                    WHEN historical_player_match_stats.team_side IS NOT NULL
                     AND COALESCE(historical_player_match_stats.time_seconds, 0) > 0
                     AND canonical_matches.duration_source_status = 'exact' THEN 'exact'
                    WHEN COALESCE(historical_player_match_stats.kills, 0) > 0
                      OR COALESCE(historical_player_match_stats.deaths, 0) > 0
                      OR COALESCE(historical_player_match_stats.teamkills, 0) > 0
                      OR COALESCE(historical_player_match_stats.time_seconds, 0) > 0
                      OR COALESCE(historical_player_match_stats.combat, 0) > 0
                      OR COALESCE(historical_player_match_stats.offense, 0) > 0
                      OR COALESCE(historical_player_match_stats.defense, 0) > 0
                      OR COALESCE(historical_player_match_stats.support, 0) > 0 THEN 'approximate'
                    ELSE 'not_available'
                END AS fact_capability_status,
                ? AS fact_schema_version,
                ? AS source_input_version
            FROM historical_player_match_stats
            INNER JOIN historical_matches
                ON historical_matches.id = historical_player_match_stats.historical_match_id
            INNER JOIN historical_servers
                ON historical_servers.id = historical_matches.historical_server_id
            INNER JOIN historical_players
                ON historical_players.id = historical_player_match_stats.historical_player_id
            INNER JOIN elo_mmr_canonical_players AS canonical_players
                ON canonical_players.stable_player_key = historical_players.stable_player_key
            INNER JOIN elo_mmr_canonical_matches AS canonical_matches
                ON canonical_matches.canonical_match_key = historical_servers.slug || ':' || historical_matches.external_match_id
            LEFT JOIN (
                SELECT
                    canonical_match_key,
                    stable_player_key,
                    COUNT(*) AS total_event_rows,
                    SUM(CASE WHEN event_subtype = 'combat-kill-summary' THEN COALESCE(event_value, 0) ELSE 0 END) AS combat_kill_summaries,
                    SUM(CASE WHEN event_subtype = 'combat-death-summary' THEN COALESCE(event_value, 0) ELSE 0 END) AS combat_death_summaries,
                    SUM(CASE WHEN event_subtype = 'weapon-kill-summary' THEN COALESCE(event_value, 0) ELSE 0 END) AS weapon_kill_summaries,
                    SUM(CASE WHEN event_subtype = 'weapon-death-summary' THEN COALESCE(event_value, 0) ELSE 0 END) AS weapon_death_summaries,
                    SUM(CASE WHEN event_subtype = 'teamkill-summary' THEN COALESCE(event_value, 0) ELSE 0 END) AS teamkill_summaries
                FROM elo_event_lineage_headers
                WHERE event_family = 'death_classification_events'
                GROUP BY canonical_match_key, stable_player_key
            ) AS death_summary_rollup
                ON death_summary_rollup.canonical_match_key = canonical_matches.canonical_match_key
               AND death_summary_rollup.stable_player_key = historical_players.stable_player_key
            LEFT JOIN (
                SELECT
                    canonical_match_key,
                    COUNT(*) AS death_classification_event_count
                FROM elo_event_lineage_headers
                WHERE event_family = 'death_classification_events'
                GROUP BY canonical_match_key
            ) AS match_event_coverage
                ON match_event_coverage.canonical_match_key = canonical_matches.canonical_match_key
            WHERE historical_matches.ended_at IS NOT NULL
            """,
            (
                NORMALIZATION_BUCKET_VERSION,
                NORMALIZATION_BASELINE_VERSION,
                ELO_MMR_CANONICAL_FACT_SCHEMA_VERSION,
                ELO_MMR_CANONICAL_SOURCE_INPUT_VERSION,
            ),
        )
        _rebuild_normalization_baselines(connection)

        totals_row = connection.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM elo_mmr_canonical_players) AS players_count,
                (SELECT COUNT(*) FROM elo_mmr_canonical_matches) AS matches_count,
                (SELECT COUNT(*) FROM elo_mmr_canonical_player_match_facts) AS player_match_facts_count,
                (SELECT COUNT(*) FROM elo_event_lineage_headers) AS canonical_event_count,
                (
                    SELECT COUNT(*)
                    FROM elo_event_lineage_headers
                    WHERE event_family = 'death_classification_events'
                ) AS death_classification_event_count,
                (SELECT COUNT(*) FROM elo_mmr_normalization_buckets) AS normalization_bucket_count
            """
        ).fetchone()
    return {
        "status": "ok",
        "fact_schema_version": ELO_MMR_CANONICAL_FACT_SCHEMA_VERSION,
        "source_input_version": ELO_MMR_CANONICAL_SOURCE_INPUT_VERSION,
        "source_kind": "historical-closed-match",
        "totals": {
            "players": int(totals_row["players_count"] or 0),
            "matches": int(totals_row["matches_count"] or 0),
            "player_match_facts": int(totals_row["player_match_facts_count"] or 0),
            "canonical_events": int(totals_row["canonical_event_count"] or 0),
            "death_classification_events": int(totals_row["death_classification_event_count"] or 0),
            "normalization_buckets": int(totals_row["normalization_bucket_count"] or 0),
        },
    }


def _ingest_summary_backed_canonical_events(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        INSERT INTO elo_event_lineage_headers (
            canonical_event_id,
            event_family,
            source_event_id,
            canonical_match_key,
            server_slug,
            stable_player_key,
            actor_player_key,
            target_player_key,
            occurred_at,
            match_second,
            event_time_status,
            event_window_start_second,
            event_window_end_second,
            event_type,
            event_subtype,
            event_value,
            team_side,
            role_at_event_time,
            source_kind,
            source_reliability,
            capability_status,
            source_payload_ref,
            raw_payload_strategy,
            dedupe_key,
            dedupe_strategy,
            replay_safe,
            contract_version,
            storage_strategy
        )
        SELECT
            'death-classification:' || raw_events.event_id AS canonical_event_id,
            'death_classification_events' AS event_family,
            raw_events.event_id AS source_event_id,
            raw_events.server_slug || ':' || raw_events.external_match_id AS canonical_match_key,
            raw_events.server_slug,
            owner_player.stable_player_key AS stable_player_key,
            actor_player.stable_player_key AS actor_player_key,
            target_player.stable_player_key AS target_player_key,
            NULL AS occurred_at,
            NULL AS match_second,
            'not_available' AS event_time_status,
            NULL AS event_window_start_second,
            NULL AS event_window_end_second,
            'death_classification' AS event_type,
            raw_events.event_subtype,
            raw_events.event_value,
            owner_fact.team_side,
            NULL AS role_at_event_time,
            raw_events.source_kind,
            'summary-approximate' AS source_reliability,
            'approximate' AS capability_status,
            COALESCE(raw_events.source_ref, raw_events.raw_event_ref, raw_events.event_id) AS source_payload_ref,
            'player-event-raw-ledger-summary' AS raw_payload_strategy,
            raw_events.event_id AS dedupe_key,
            'source-event-id' AS dedupe_strategy,
            1 AS replay_safe,
            ? AS contract_version,
            'hybrid-header-plus-family-detail' AS storage_strategy
        FROM (
            SELECT
                pel.event_id,
                pel.event_type,
                pel.occurred_at,
                pel.server_slug,
                pel.external_match_id,
                pel.source_kind,
                pel.source_ref,
                pel.raw_event_ref,
                pel.killer_player_key,
                pel.victim_player_key,
                pel.weapon_name,
                pel.weapon_category,
                pel.kill_category,
                pel.is_teamkill,
                pel.event_value,
                CASE
                    WHEN pel.event_type IN ('player_kill_summary', 'player_weapon_kill_summary', 'player_teamkill_summary')
                        THEN pel.killer_player_key
                    ELSE pel.victim_player_key
                END AS stable_player_key,
                CASE
                    WHEN pel.event_type = 'player_kill_summary' THEN 'combat-kill-summary'
                    WHEN pel.event_type = 'player_death_summary' THEN 'combat-death-summary'
                    WHEN pel.event_type = 'player_weapon_kill_summary' THEN 'weapon-kill-summary'
                    WHEN pel.event_type = 'player_weapon_death_summary' THEN 'weapon-death-summary'
                    WHEN pel.event_type = 'player_teamkill_summary' THEN 'teamkill-summary'
                    ELSE 'unsupported-summary'
                END AS event_subtype
            FROM player_event_raw_ledger AS pel
            WHERE pel.event_type IN (
                'player_kill_summary',
                'player_death_summary',
                'player_weapon_kill_summary',
                'player_weapon_death_summary',
                'player_teamkill_summary'
            )
        ) AS raw_events
        INNER JOIN elo_mmr_canonical_matches AS canonical_matches
            ON canonical_matches.canonical_match_key = raw_events.server_slug || ':' || raw_events.external_match_id
        LEFT JOIN elo_mmr_canonical_players AS owner_player
            ON owner_player.stable_player_key = raw_events.stable_player_key
        LEFT JOIN elo_mmr_canonical_players AS actor_player
            ON actor_player.stable_player_key = raw_events.killer_player_key
        LEFT JOIN elo_mmr_canonical_players AS target_player
            ON target_player.stable_player_key = raw_events.victim_player_key
        LEFT JOIN historical_servers AS hs
            ON hs.slug = raw_events.server_slug
        LEFT JOIN historical_matches AS hm
            ON hm.historical_server_id = hs.id
           AND hm.external_match_id = raw_events.external_match_id
           AND hm.ended_at IS NOT NULL
        LEFT JOIN historical_players AS hp
            ON hp.stable_player_key = owner_player.stable_player_key
        LEFT JOIN historical_player_match_stats AS owner_fact
            ON owner_fact.historical_match_id = hm.id
           AND owner_fact.historical_player_id = hp.id
        WHERE owner_player.stable_player_key IS NOT NULL
        """,
        (ELO_EVENT_TELEMETRY_CONTRACT_VERSION,),
    )


def _rebuild_normalization_baselines(connection: sqlite3.Connection) -> None:
    connection.execute("DELETE FROM elo_mmr_normalization_baselines")
    connection.execute("DELETE FROM elo_mmr_normalization_buckets")
    rows = connection.execute(
        """
        SELECT
            canonical_facts.canonical_match_key,
            canonical_facts.stable_player_key,
            canonical_facts.role_primary,
            canonical_facts.role_primary_mode,
            canonical_matches.game_mode,
            canonical_facts.duration_bucket,
            canonical_facts.participation_bucket,
            canonical_facts.player_count_bucket,
            canonical_facts.match_shape_bucket,
            canonical_facts.normalization_bucket_key,
            canonical_facts.kills_per_minute,
            canonical_facts.combat_per_minute,
            canonical_facts.support_per_minute,
            canonical_facts.objective_proxy_per_minute,
            canonical_facts.participation_ratio,
            canonical_facts.participation_quality_score,
            canonical_facts.death_summary_combat_kills,
            canonical_facts.death_summary_combat_deaths,
            canonical_facts.death_summary_teamkills,
            canonical_facts.tactical_event_count
        FROM elo_mmr_canonical_player_match_facts AS canonical_facts
        INNER JOIN elo_mmr_canonical_matches AS canonical_matches
            ON canonical_matches.canonical_match_key = canonical_facts.canonical_match_key
        """
    ).fetchall()
    bucket_groups: dict[str, list[sqlite3.Row]] = {}
    bucket_meta: dict[str, dict[str, str]] = {}
    parent_groups: dict[str, list[sqlite3.Row]] = {}
    parent_meta: dict[str, dict[str, str]] = {}
    for row in rows:
        bucket_key = str(row["normalization_bucket_key"] or "").strip()
        if not bucket_key:
            continue
        bucket_groups.setdefault(bucket_key, []).append(row)
        bucket_meta.setdefault(
            bucket_key,
            {
                "role_primary": str(row["role_primary"] or "generalist"),
                "role_primary_mode": str(row["role_primary_mode"] or CAPABILITY_UNAVAILABLE),
                "game_mode": str((row["game_mode"] or "unknown")).strip().lower() or "unknown",
                "duration_bucket": str(row["duration_bucket"] or "unknown"),
                "participation_bucket": str(row["participation_bucket"] or "none"),
                "player_count_bucket": str(row["player_count_bucket"] or "unknown"),
                "match_shape_bucket": str(row["match_shape_bucket"] or "unknown"),
            },
        )
        parent_key = _build_parent_normalization_bucket_key(row)
        parent_groups.setdefault(parent_key, []).append(row)
        parent_meta.setdefault(
            parent_key,
            {
                "role_primary": "all",
                "role_primary_mode": "fallback-parent",
                "game_mode": str((row["game_mode"] or "unknown")).strip().lower() or "unknown",
                "duration_bucket": str(row["duration_bucket"] or "unknown"),
                "participation_bucket": str(row["participation_bucket"] or "none"),
                "player_count_bucket": str(row["player_count_bucket"] or "unknown"),
                "match_shape_bucket": str(row["match_shape_bucket"] or "unknown"),
            },
        )

    all_groups = {**parent_groups, **bucket_groups}
    all_meta = {**parent_meta, **bucket_meta}
    connection.executemany(
        """
        INSERT INTO elo_mmr_normalization_buckets (
            bucket_key,
            bucket_version,
            normalization_version,
            role_primary,
            role_primary_mode,
            game_mode,
            duration_bucket,
            participation_bucket,
            player_count_bucket,
            match_shape_bucket,
            sample_count,
            insufficient_sample,
            fallback_bucket_key,
            fallback_reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                bucket_key,
                NORMALIZATION_BUCKET_VERSION,
                NORMALIZATION_BASELINE_VERSION,
                meta["role_primary"],
                meta["role_primary_mode"],
                meta["game_mode"],
                meta["duration_bucket"],
                meta["participation_bucket"],
                meta["player_count_bucket"],
                meta["match_shape_bucket"],
                len(group_rows),
                1 if len(group_rows) < NORMALIZATION_MIN_BUCKET_SAMPLE else 0,
                _build_parent_normalization_bucket_key_from_meta(meta)
                if meta["role_primary"] != "all"
                else None,
                (
                    "insufficient-sample-fallback-to-role-all"
                    if meta["role_primary"] != "all" and len(group_rows) < NORMALIZATION_MIN_BUCKET_SAMPLE
                    else None
                ),
            )
            for bucket_key, group_rows in all_groups.items()
            for meta in [all_meta[bucket_key]]
        ],
    )
    metric_names = (
        "kills_per_minute",
        "combat_per_minute",
        "support_per_minute",
        "objective_proxy_per_minute",
        "participation_ratio",
        "participation_quality_score",
        "death_summary_combat_kills",
        "death_summary_combat_deaths",
        "death_summary_teamkills",
        "tactical_event_count",
    )
    baseline_rows: list[tuple[object, ...]] = []
    for bucket_key, group_rows in all_groups.items():
        for metric_name in metric_names:
            values = [float(row[metric_name] or 0.0) for row in group_rows]
            baseline_rows.append(
                (
                    bucket_key,
                    metric_name,
                    len(values),
                    round(sum(values) / max(1, len(values)), 6),
                    round(min(values), 6) if values else 0.0,
                    round(max(values), 6) if values else 0.0,
                    round(_percentile(values, 0.50), 6),
                    round(_percentile(values, 0.90), 6),
                    NORMALIZATION_BASELINE_VERSION,
                )
            )
    connection.executemany(
        """
        INSERT INTO elo_mmr_normalization_baselines (
            bucket_key,
            metric_name,
            sample_count,
            avg_value,
            min_value,
            max_value,
            p50_value,
            p90_value,
            normalization_version
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        baseline_rows,
    )
    update_rows: list[tuple[object, ...]] = []
    for row in rows:
        bucket_key = str(row["normalization_bucket_key"] or "").strip()
        if not bucket_key:
            continue
        sample_count = len(bucket_groups.get(bucket_key, []))
        parent_key = _build_parent_normalization_bucket_key(row)
        parent_sample_count = len(parent_groups.get(parent_key, []))
        fallback_bucket_key = None
        fallback_reason = None
        if sample_count < NORMALIZATION_MIN_BUCKET_SAMPLE:
            fallback_bucket_key = parent_key if parent_sample_count > 0 else None
            fallback_reason = (
                "primary-bucket-insufficient-fallback-to-role-all"
                if parent_sample_count > 0
                else "primary-bucket-insufficient-no-parent-bucket"
            )
        update_rows.append(
            (
                NORMALIZATION_BUCKET_VERSION,
                fallback_bucket_key,
                fallback_reason,
                NORMALIZATION_BASELINE_VERSION,
                row["canonical_match_key"],
                row["stable_player_key"],
            )
        )
    connection.executemany(
        """
        UPDATE elo_mmr_canonical_player_match_facts
        SET normalization_bucket_version = ?,
            normalization_fallback_bucket_key = ?,
            normalization_fallback_reason = ?,
            normalization_version = ?
        WHERE canonical_match_key = ? AND stable_player_key = ?
        """,
        update_rows,
    )


def _build_parent_normalization_bucket_key(row: sqlite3.Row) -> str:
    return "|".join(
        [
            "all",
            str((row["game_mode"] or "unknown")).strip().lower() or "unknown",
            str(row["duration_bucket"] or "unknown"),
            str(row["participation_bucket"] or "none"),
            str(row["player_count_bucket"] or "unknown"),
            str(row["match_shape_bucket"] or "unknown"),
        ]
    )


def _build_parent_normalization_bucket_key_from_meta(meta: dict[str, str]) -> str:
    return "|".join(
        [
            "all",
            meta["game_mode"],
            meta["duration_bucket"],
            meta["participation_bucket"],
            meta["player_count_bucket"],
            meta["match_shape_bucket"],
        ]
    )


def _percentile(values: list[float], ratio: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * ratio))))
    return ordered[index]
    connection.execute(
        """
        INSERT INTO elo_event_death_classification_details (
            canonical_event_id,
            death_class,
            death_subclass,
            weapon_name,
            weapon_category,
            damage_source_kind,
            is_friendly_fire,
            is_redeploy,
            is_self_inflicted,
            is_menu_exit
        )
        SELECT
            'death-classification:' || pel.event_id AS canonical_event_id,
            CASE
                WHEN pel.event_type = 'player_teamkill_summary' OR pel.is_teamkill = 1 THEN 'friendly_fire_summary'
                WHEN pel.event_type IN ('player_kill_summary', 'player_death_summary') THEN 'combat_summary'
                WHEN pel.event_type IN ('player_weapon_kill_summary', 'player_weapon_death_summary') THEN 'weapon_summary'
                ELSE 'unknown_summary'
            END AS death_class,
            CASE
                WHEN pel.event_type = 'player_kill_summary' THEN COALESCE(NULLIF(pel.kill_category, ''), 'combat-kill-summary')
                WHEN pel.event_type = 'player_death_summary' THEN 'combat-death-summary'
                WHEN pel.event_type = 'player_weapon_kill_summary' THEN 'weapon-kill-summary'
                WHEN pel.event_type = 'player_weapon_death_summary' THEN 'weapon-death-summary'
                WHEN pel.event_type = 'player_teamkill_summary' THEN 'teamkill-summary'
                ELSE pel.event_type
            END AS death_subclass,
            pel.weapon_name,
            pel.weapon_category,
            CASE
                WHEN pel.event_type IN ('player_weapon_kill_summary', 'player_weapon_death_summary') THEN 'weapon-summary'
                WHEN pel.event_type = 'player_teamkill_summary' THEN 'teamkill-summary'
                ELSE COALESCE(NULLIF(pel.kill_category, ''), 'combat-summary')
            END AS damage_source_kind,
            CASE WHEN pel.event_type = 'player_teamkill_summary' OR pel.is_teamkill = 1 THEN 1 ELSE 0 END AS is_friendly_fire,
            0 AS is_redeploy,
            0 AS is_self_inflicted,
            0 AS is_menu_exit
        FROM player_event_raw_ledger AS pel
        INNER JOIN elo_event_lineage_headers AS headers
            ON headers.canonical_event_id = 'death-classification:' || pel.event_id
        WHERE pel.event_type IN (
            'player_kill_summary',
            'player_death_summary',
            'player_weapon_kill_summary',
            'player_weapon_death_summary',
            'player_teamkill_summary'
        )
        """
    )
    connection.execute(
        """
        INSERT INTO elo_event_capability_registry (
            event_family,
            source_kind,
            capability_status,
            instrumentation_status,
            storage_contract_status,
            notes,
            contract_version
        ) VALUES (
            'death_classification_events',
            'public-scoreboard-match-summary',
            'approximate',
            'implemented_from_summary_proxy',
            'implemented',
            'Summary-backed canonical death classification events are rebuilt from player_event_raw_ledger and remain approximate because the source is not a per-death raw feed.',
            ?
        )
        ON CONFLICT(event_family, source_kind) DO UPDATE SET
            capability_status = excluded.capability_status,
            instrumentation_status = excluded.instrumentation_status,
            storage_contract_status = excluded.storage_contract_status,
            notes = excluded.notes,
            contract_version = excluded.contract_version,
            updated_at = CURRENT_TIMESTAMP
        """,
        (ELO_EVENT_TELEMETRY_CONTRACT_VERSION,),
    )


def list_elo_mmr_canonical_match_rows(*, db_path: Path | None = None) -> list[dict[str, object]]:
    """Return canonical player-match fact rows ordered for deterministic rebuilds."""
    resolved_path = _resolve_db_path(db_path)
    try:
        with _connect_readonly(resolved_path) as connection:
            rows = connection.execute(
                """
                SELECT
                    canonical_matches.canonical_match_key,
                    canonical_matches.server_slug,
                    canonical_matches.server_name,
                    canonical_matches.external_match_id,
                    canonical_matches.started_at,
                    canonical_matches.ended_at,
                    canonical_matches.game_mode,
                    canonical_matches.allied_score,
                    canonical_matches.axis_score,
                    canonical_matches.resolved_duration_seconds,
                    canonical_matches.duration_source_status,
                    canonical_matches.duration_bucket,
                    canonical_matches.player_count,
                    canonical_matches.match_capability_status,
                    canonical_matches.fact_schema_version,
                    canonical_matches.source_input_version,
                    canonical_facts.stable_player_key,
                    canonical_facts.player_name,
                    canonical_facts.steam_id,
                    canonical_facts.team_side,
                    canonical_facts.kills,
                    canonical_facts.deaths,
                    canonical_facts.teamkills,
                    canonical_facts.time_seconds,
                    canonical_facts.combat,
                    canonical_facts.offense,
                    canonical_facts.defense,
                    canonical_facts.support,
                    canonical_facts.match_duration_seconds,
                    canonical_facts.match_duration_mode,
                    canonical_facts.duration_bucket AS player_duration_bucket,
                    canonical_facts.player_count AS fact_player_count,
                    canonical_facts.objective_score_proxy,
                    canonical_facts.objective_score_proxy_mode,
                    canonical_facts.kills_per_minute,
                    canonical_facts.combat_per_minute,
                    canonical_facts.support_per_minute,
                    canonical_facts.objective_proxy_per_minute,
                    canonical_facts.participation_ratio,
                    canonical_facts.participation_bucket,
                    canonical_facts.participation_mode,
                    canonical_facts.participation_quality_score,
                    canonical_facts.garrison_builds,
                    canonical_facts.garrison_destroys,
                    canonical_facts.garrison_event_mode,
                    canonical_facts.outpost_builds,
                    canonical_facts.outpost_destroys,
                    canonical_facts.outpost_event_mode,
                    canonical_facts.revives_given,
                    canonical_facts.revives_received,
                    canonical_facts.revive_event_mode,
                    canonical_facts.supplies_placed,
                    canonical_facts.supply_effectiveness,
                    canonical_facts.supply_event_mode,
                    canonical_facts.nodes_built,
                    canonical_facts.nodes_destroyed,
                    canonical_facts.node_active_seconds,
                    canonical_facts.node_event_mode,
                    canonical_facts.repairs_performed,
                    canonical_facts.repair_points,
                    canonical_facts.repair_event_mode,
                    canonical_facts.mines_placed,
                    canonical_facts.mine_kills,
                    canonical_facts.mine_destroys,
                    canonical_facts.mine_event_mode,
                    canonical_facts.commander_abilities_used,
                    canonical_facts.commander_ability_event_mode,
                    canonical_facts.strongpoint_occupancy_seconds,
                    canonical_facts.strongpoint_contest_seconds,
                    canonical_facts.strongpoint_event_mode,
                    canonical_facts.role_time_seconds,
                    canonical_facts.role_assignment_event_mode,
                    canonical_facts.disconnect_leave_count,
                    canonical_facts.admin_action_count,
                    canonical_facts.disconnect_leave_admin_event_mode,
                    canonical_facts.death_summary_combat_kills,
                    canonical_facts.death_summary_combat_deaths,
                    canonical_facts.death_summary_weapon_kills,
                    canonical_facts.death_summary_weapon_deaths,
                    canonical_facts.death_summary_teamkills,
                    canonical_facts.death_classification_event_mode,
                    canonical_facts.tactical_event_lineage_status,
                    canonical_facts.tactical_event_count,
                    canonical_facts.role_primary,
                    canonical_facts.role_primary_mode,
                    canonical_facts.normalization_bucket_key,
                    canonical_facts.normalization_bucket_version,
                    canonical_facts.normalization_fallback_bucket_key,
                    canonical_facts.normalization_fallback_reason,
                    canonical_facts.normalization_version,
                    canonical_facts.player_count_bucket,
                    canonical_facts.match_shape_bucket,
                    canonical_facts.teamkill_exact_count,
                    canonical_facts.leave_disconnect_exact_count,
                    canonical_facts.kick_or_ban_exact_count,
                    canonical_facts.admin_action_exact_count,
                    canonical_facts.combat_death_proxy_count,
                    canonical_facts.friendly_fire_proxy_count,
                    canonical_facts.redeploy_death_exact_count,
                    canonical_facts.suicide_death_exact_count,
                    canonical_facts.menu_exit_death_exact_count,
                    canonical_facts.discipline_capability_status,
                    canonical_facts.leave_admin_capability_status,
                    canonical_facts.death_type_capability_status,
                    canonical_facts.discipline_lineage_status,
                    canonical_facts.fact_capability_status,
                    canonical_players.identity_capability_status
                FROM elo_mmr_canonical_player_match_facts AS canonical_facts
                INNER JOIN elo_mmr_canonical_matches AS canonical_matches
                    ON canonical_matches.canonical_match_key = canonical_facts.canonical_match_key
                INNER JOIN elo_mmr_canonical_players AS canonical_players
                    ON canonical_players.stable_player_key = canonical_facts.stable_player_key
                ORDER BY
                    canonical_matches.ended_at ASC,
                    canonical_matches.canonical_match_key ASC,
                    canonical_facts.stable_player_key ASC
                """
            ).fetchall()
    except sqlite3.OperationalError:
        return []
    return [dict(row) for row in rows]


def list_elo_mmr_monthly_rankings(
    *,
    scope_key: str,
    limit: int = 10,
    month_key: str | None = None,
    eligible_only: bool = True,
    db_path: Path | None = None,
) -> dict[str, object]:
    """Return the persisted monthly Elo/MMR leaderboard for one scope."""
    resolved_path = _resolve_db_path(db_path)
    resolved_month_key = month_key or get_latest_elo_mmr_month_key(scope_key=scope_key, db_path=resolved_path)
    if not resolved_month_key:
        return {
            "month_key": None,
            "found": False,
            "generated_at": None,
            "items": [],
            "source_policy": None,
            "capabilities_summary": None,
        }

    where_clauses = ["scope_key = ?", "month_key = ?"]
    params: list[object] = [scope_key, resolved_month_key]
    if eligible_only:
        where_clauses.append("eligible = 1")
    params.append(limit)
    try:
        with _connect_readonly(resolved_path) as connection:
            checkpoint_row = connection.execute(
                """
                SELECT
                    generated_at,
                    model_version,
                    formula_version,
                    contract_version,
                    source_policy_json,
                    capabilities_summary_json
                FROM elo_mmr_monthly_checkpoints
                WHERE scope_key = ? AND month_key = ?
                """,
                (scope_key, resolved_month_key),
            ).fetchone()
            rows = connection.execute(
                f"""
                SELECT *
                FROM elo_mmr_monthly_rankings
                WHERE {" AND ".join(where_clauses)}
                ORDER BY monthly_rank_score DESC, current_mmr DESC, player_name COLLATE NOCASE ASC
                LIMIT ?
                """,
                params,
            ).fetchall()
    except sqlite3.OperationalError:
        return {
            "month_key": None,
            "found": False,
            "generated_at": None,
            "items": [],
            "source_policy": None,
            "capabilities_summary": None,
        }
    items = []
    for index, row in enumerate(rows, start=1):
        component_scores = json.loads(row["component_scores_json"])
        items.append(
            {
                "ranking_position": index,
                "player": {
                    "stable_player_key": row["stable_player_key"],
                    "name": row["player_name"],
                    "steam_id": row["steam_id"],
                },
                "persistent_rating": {
                    "mmr": round(float(row["current_mmr"] or 0.0), 3),
                    "baseline_mmr": round(float(row["baseline_mmr"] or 0.0), 3),
                    "mmr_gain": round(float(row["mmr_gain"] or 0.0), 3),
                    "model_version": component_scores.get("persistent_rating_model_version"),
                    "formula_version": component_scores.get("persistent_rating_formula_version"),
                    "contract_version": component_scores.get("persistent_rating_contract_version"),
                },
                "monthly_rank_score": round(float(row["monthly_rank_score"] or 0.0), 3),
                "components": component_scores,
                "model_version": row["model_version"],
                "formula_version": row["formula_version"],
                "contract_version": row["contract_version"],
                "valid_matches": int(row["valid_matches"] or 0),
                "total_matches": int(row["total_matches"] or 0),
                "total_time_seconds": int(row["total_time_seconds"] or 0),
                "eligible": bool(row["eligible"]),
                "eligibility_reason": row["eligibility_reason"],
                "accuracy_mode": row["accuracy_mode"],
                "capabilities": json.loads(row["capabilities_json"]),
            }
        )
    return {
        "month_key": resolved_month_key,
        "found": bool(items),
        "generated_at": checkpoint_row["generated_at"] if checkpoint_row else None,
        "model_version": checkpoint_row["model_version"] if checkpoint_row else None,
        "formula_version": checkpoint_row["formula_version"] if checkpoint_row else None,
        "contract_version": checkpoint_row["contract_version"] if checkpoint_row else None,
        "items": items,
        "source_policy": json.loads(checkpoint_row["source_policy_json"])
        if checkpoint_row
        else None,
        "capabilities_summary": json.loads(checkpoint_row["capabilities_summary_json"])
        if checkpoint_row
        else None,
    }


def get_elo_mmr_player_profile(
    *,
    player_id: str,
    scope_key: str,
    month_key: str | None = None,
    db_path: Path | None = None,
) -> dict[str, object] | None:
    """Return the persisted rating and monthly ranking profile for one player."""
    resolved_player_id = player_id.strip()
    if not resolved_player_id:
        return None
    resolved_path = _resolve_db_path(db_path)
    resolved_month_key = month_key or get_latest_elo_mmr_month_key(scope_key=scope_key, db_path=resolved_path)
    try:
        with _connect_readonly(resolved_path) as connection:
            rating_row = connection.execute(
                """
                SELECT *
                FROM elo_mmr_player_ratings
                WHERE scope_key = ?
                  AND (stable_player_key = ? OR steam_id = ?)
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (scope_key, resolved_player_id, resolved_player_id),
            ).fetchone()
            monthly_row = None
            if resolved_month_key:
                monthly_row = connection.execute(
                    """
                    SELECT *
                    FROM elo_mmr_monthly_rankings
                    WHERE scope_key = ?
                      AND month_key = ?
                      AND (stable_player_key = ? OR steam_id = ?)
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (scope_key, resolved_month_key, resolved_player_id, resolved_player_id),
                ).fetchone()
    except sqlite3.OperationalError:
        return None
    if rating_row is None and monthly_row is None:
        return None
    return {
        "scope_key": scope_key,
        "month_key": resolved_month_key,
        "player": {
            "stable_player_key": (
                rating_row["stable_player_key"] if rating_row else monthly_row["stable_player_key"]
            ),
            "name": rating_row["player_name"] if rating_row else monthly_row["player_name"],
            "steam_id": rating_row["steam_id"] if rating_row else monthly_row["steam_id"],
        },
        "persistent_rating": (
            {
                "mmr": round(float(rating_row["current_mmr"] or 0.0), 3),
                "matches_processed": int(rating_row["matches_processed"] or 0),
                "wins": int(rating_row["wins"] or 0),
                "draws": int(rating_row["draws"] or 0),
                "losses": int(rating_row["losses"] or 0),
                "last_match_id": rating_row["last_match_id"],
                "last_match_ended_at": rating_row["last_match_ended_at"],
                "model_version": rating_row["model_version"],
                "formula_version": rating_row["formula_version"],
                "contract_version": rating_row["contract_version"],
                "accuracy_mode": rating_row["accuracy_mode"],
                "capabilities": json.loads(rating_row["capabilities_json"]),
            }
            if rating_row
            else None
        ),
        "monthly_ranking": (
            {
                "monthly_rank_score": round(float(monthly_row["monthly_rank_score"] or 0.0), 3),
                "current_mmr": round(float(monthly_row["current_mmr"] or 0.0), 3),
                "baseline_mmr": round(float(monthly_row["baseline_mmr"] or 0.0), 3),
                "mmr_gain": round(float(monthly_row["mmr_gain"] or 0.0), 3),
                "model_version": monthly_row["model_version"],
                "formula_version": monthly_row["formula_version"],
                "contract_version": monthly_row["contract_version"],
                "valid_matches": int(monthly_row["valid_matches"] or 0),
                "total_matches": int(monthly_row["total_matches"] or 0),
                "total_time_seconds": int(monthly_row["total_time_seconds"] or 0),
                "eligible": bool(monthly_row["eligible"]),
                "eligibility_reason": monthly_row["eligibility_reason"],
                "accuracy_mode": monthly_row["accuracy_mode"],
                "components": json.loads(monthly_row["component_scores_json"]),
                "capabilities": json.loads(monthly_row["capabilities_json"]),
            }
            if monthly_row
            else None
        ),
    }


def get_latest_elo_mmr_month_key(
    *,
    scope_key: str,
    db_path: Path | None = None,
) -> str | None:
    """Return the latest month key available for one Elo/MMR scope."""
    resolved_path = _resolve_db_path(db_path)
    try:
        with _connect_readonly(resolved_path) as connection:
            row = connection.execute(
                """
                SELECT MAX(month_key) AS latest_month_key
                FROM elo_mmr_monthly_checkpoints
                WHERE scope_key = ?
                """,
                (scope_key,),
            ).fetchone()
    except sqlite3.OperationalError:
        return None
    return str(row["latest_month_key"]) if row and row["latest_month_key"] else None


def get_latest_elo_mmr_generated_at(*, db_path: Path | None = None) -> datetime | None:
    """Return the latest persisted Elo/MMR checkpoint generation time, if any."""
    resolved_path = _resolve_db_path(db_path)
    try:
        with _connect_readonly(resolved_path) as connection:
            row = connection.execute(
                """
                SELECT MAX(generated_at) AS latest_generated_at
                FROM elo_mmr_monthly_checkpoints
                """
            ).fetchone()
    except sqlite3.OperationalError:
        return None
    latest_generated_at = str(row["latest_generated_at"] or "").strip() if row else ""
    if not latest_generated_at:
        return None
    return datetime.fromisoformat(latest_generated_at.replace("Z", "+00:00"))


def _ensure_schema_extensions(connection: sqlite3.Connection) -> None:
    _ensure_table_columns(
        connection,
        "elo_event_lineage_headers",
        {
            "event_value": "INTEGER NOT NULL DEFAULT 1",
            "contract_version": "TEXT NOT NULL DEFAULT ''",
            "storage_strategy": "TEXT NOT NULL DEFAULT 'hybrid-header-plus-family-detail'",
        },
    )
    _ensure_table_columns(
        connection,
        "elo_mmr_player_ratings",
        {
            "model_version": "TEXT NOT NULL DEFAULT ''",
            "formula_version": "TEXT NOT NULL DEFAULT ''",
            "contract_version": "TEXT NOT NULL DEFAULT ''",
        },
    )
    _ensure_table_columns(
        connection,
        "elo_mmr_match_results",
        {
            "canonical_match_key": "TEXT NOT NULL DEFAULT ''",
            "fact_schema_version": "TEXT NOT NULL DEFAULT ''",
            "source_input_version": "TEXT NOT NULL DEFAULT ''",
            "model_version": "TEXT NOT NULL DEFAULT ''",
            "formula_version": "TEXT NOT NULL DEFAULT ''",
            "contract_version": "TEXT NOT NULL DEFAULT ''",
            "time_seconds": "INTEGER NOT NULL DEFAULT 0",
            "participation_ratio": "REAL NOT NULL DEFAULT 0",
            "strength_of_schedule_match": "REAL NOT NULL DEFAULT 0",
            "team_outcome": "TEXT",
            "own_team_average_mmr": "REAL NOT NULL DEFAULT 0",
            "enemy_team_average_mmr": "REAL NOT NULL DEFAULT 0",
            "expected_result": "REAL NOT NULL DEFAULT 0",
            "actual_result": "REAL NOT NULL DEFAULT 0",
            "won_score": "REAL NOT NULL DEFAULT 0",
            "margin_boost": "REAL NOT NULL DEFAULT 0",
            "outcome_adjusted": "REAL NOT NULL DEFAULT 0",
            "match_impact": "REAL NOT NULL DEFAULT 0",
            "combat_contribution": "REAL NOT NULL DEFAULT 0",
            "objective_contribution": "REAL NOT NULL DEFAULT 0",
            "utility_contribution": "REAL NOT NULL DEFAULT 0",
            "survival_discipline_contribution": "REAL NOT NULL DEFAULT 0",
            "exact_component_contribution": "REAL NOT NULL DEFAULT 0",
            "proxy_component_contribution": "REAL NOT NULL DEFAULT 0",
            "normalization_bucket_key": "TEXT NOT NULL DEFAULT ''",
            "normalization_fallback_reason": "TEXT",
            "elo_core_delta": "REAL NOT NULL DEFAULT 0",
            "performance_modifier_delta": "REAL NOT NULL DEFAULT 0",
            "proxy_modifier_delta": "REAL NOT NULL DEFAULT 0",
            "canonical_fact_capability_status": "TEXT NOT NULL DEFAULT 'not_available'",
            "identity_capability_status": "TEXT NOT NULL DEFAULT 'not_available'",
            "match_duration_seconds": "INTEGER NOT NULL DEFAULT 0",
            "duration_source_status": "TEXT NOT NULL DEFAULT 'not_available'",
            "duration_bucket": "TEXT NOT NULL DEFAULT 'unknown'",
            "player_count": "INTEGER NOT NULL DEFAULT 0",
            "objective_score_proxy": "INTEGER NOT NULL DEFAULT 0",
            "objective_score_proxy_mode": "TEXT NOT NULL DEFAULT 'approximate'",
            "kills_per_minute": "REAL NOT NULL DEFAULT 0",
            "combat_per_minute": "REAL NOT NULL DEFAULT 0",
            "support_per_minute": "REAL NOT NULL DEFAULT 0",
            "objective_proxy_per_minute": "REAL NOT NULL DEFAULT 0",
            "participation_bucket": "TEXT NOT NULL DEFAULT 'none'",
            "participation_mode": "TEXT NOT NULL DEFAULT 'not_available'",
            "participation_quality_score": "REAL NOT NULL DEFAULT 0",
        },
    )
    _ensure_table_columns(
        connection,
        "elo_mmr_monthly_rankings",
        {
            "model_version": "TEXT NOT NULL DEFAULT ''",
            "formula_version": "TEXT NOT NULL DEFAULT ''",
            "contract_version": "TEXT NOT NULL DEFAULT ''",
            "avg_participation_ratio": "REAL NOT NULL DEFAULT 0",
        },
    )
    _ensure_table_columns(
        connection,
        "elo_mmr_monthly_checkpoints",
        {
            "model_version": "TEXT NOT NULL DEFAULT ''",
            "formula_version": "TEXT NOT NULL DEFAULT ''",
            "contract_version": "TEXT NOT NULL DEFAULT ''",
        },
    )
    _ensure_table_columns(
        connection,
        "elo_mmr_canonical_matches",
        {
            "resolved_duration_seconds": "INTEGER NOT NULL DEFAULT 0",
            "duration_source_status": "TEXT NOT NULL DEFAULT 'not_available'",
            "duration_bucket": "TEXT NOT NULL DEFAULT 'unknown'",
            "player_count": "INTEGER NOT NULL DEFAULT 0",
        },
    )
    _ensure_table_columns(
        connection,
        "elo_mmr_canonical_player_match_facts",
        {
            "match_duration_seconds": "INTEGER NOT NULL DEFAULT 0",
            "match_duration_mode": "TEXT NOT NULL DEFAULT 'not_available'",
            "duration_bucket": "TEXT NOT NULL DEFAULT 'unknown'",
            "player_count": "INTEGER NOT NULL DEFAULT 0",
            "objective_score_proxy": "INTEGER NOT NULL DEFAULT 0",
            "objective_score_proxy_mode": "TEXT NOT NULL DEFAULT 'approximate'",
            "kills_per_minute": "REAL NOT NULL DEFAULT 0",
            "combat_per_minute": "REAL NOT NULL DEFAULT 0",
            "support_per_minute": "REAL NOT NULL DEFAULT 0",
            "objective_proxy_per_minute": "REAL NOT NULL DEFAULT 0",
            "participation_ratio": "REAL NOT NULL DEFAULT 0",
            "participation_bucket": "TEXT NOT NULL DEFAULT 'none'",
            "participation_mode": "TEXT NOT NULL DEFAULT 'not_available'",
            "participation_quality_score": "REAL NOT NULL DEFAULT 0",
            "garrison_builds": "INTEGER NOT NULL DEFAULT 0",
            "garrison_destroys": "INTEGER NOT NULL DEFAULT 0",
            "garrison_event_mode": "TEXT NOT NULL DEFAULT 'not_available'",
            "outpost_builds": "INTEGER NOT NULL DEFAULT 0",
            "outpost_destroys": "INTEGER NOT NULL DEFAULT 0",
            "outpost_event_mode": "TEXT NOT NULL DEFAULT 'not_available'",
            "revives_given": "INTEGER NOT NULL DEFAULT 0",
            "revives_received": "INTEGER NOT NULL DEFAULT 0",
            "revive_event_mode": "TEXT NOT NULL DEFAULT 'not_available'",
            "supplies_placed": "INTEGER NOT NULL DEFAULT 0",
            "supply_effectiveness": "REAL NOT NULL DEFAULT 0",
            "supply_event_mode": "TEXT NOT NULL DEFAULT 'not_available'",
            "nodes_built": "INTEGER NOT NULL DEFAULT 0",
            "nodes_destroyed": "INTEGER NOT NULL DEFAULT 0",
            "node_active_seconds": "INTEGER NOT NULL DEFAULT 0",
            "node_event_mode": "TEXT NOT NULL DEFAULT 'not_available'",
            "repairs_performed": "INTEGER NOT NULL DEFAULT 0",
            "repair_points": "REAL NOT NULL DEFAULT 0",
            "repair_event_mode": "TEXT NOT NULL DEFAULT 'not_available'",
            "mines_placed": "INTEGER NOT NULL DEFAULT 0",
            "mine_kills": "INTEGER NOT NULL DEFAULT 0",
            "mine_destroys": "INTEGER NOT NULL DEFAULT 0",
            "mine_event_mode": "TEXT NOT NULL DEFAULT 'not_available'",
            "commander_abilities_used": "INTEGER NOT NULL DEFAULT 0",
            "commander_ability_event_mode": "TEXT NOT NULL DEFAULT 'not_available'",
            "strongpoint_occupancy_seconds": "INTEGER NOT NULL DEFAULT 0",
            "strongpoint_contest_seconds": "INTEGER NOT NULL DEFAULT 0",
            "strongpoint_event_mode": "TEXT NOT NULL DEFAULT 'not_available'",
            "role_time_seconds": "INTEGER NOT NULL DEFAULT 0",
            "role_assignment_event_mode": "TEXT NOT NULL DEFAULT 'not_available'",
            "disconnect_leave_count": "INTEGER NOT NULL DEFAULT 0",
            "admin_action_count": "INTEGER NOT NULL DEFAULT 0",
            "disconnect_leave_admin_event_mode": "TEXT NOT NULL DEFAULT 'not_available'",
            "death_summary_combat_kills": "INTEGER NOT NULL DEFAULT 0",
            "death_summary_combat_deaths": "INTEGER NOT NULL DEFAULT 0",
            "death_summary_weapon_kills": "INTEGER NOT NULL DEFAULT 0",
            "death_summary_weapon_deaths": "INTEGER NOT NULL DEFAULT 0",
            "death_summary_teamkills": "INTEGER NOT NULL DEFAULT 0",
            "death_classification_event_mode": "TEXT NOT NULL DEFAULT 'not_available'",
            "tactical_event_lineage_status": "TEXT NOT NULL DEFAULT 'not_available'",
            "tactical_event_count": "INTEGER NOT NULL DEFAULT 0",
            "role_primary": "TEXT NOT NULL DEFAULT 'generalist'",
            "role_primary_mode": "TEXT NOT NULL DEFAULT 'not_available'",
            "normalization_bucket_key": "TEXT NOT NULL DEFAULT ''",
            "normalization_bucket_version": "TEXT NOT NULL DEFAULT ''",
            "normalization_fallback_bucket_key": "TEXT",
            "normalization_fallback_reason": "TEXT",
            "normalization_version": "TEXT NOT NULL DEFAULT ''",
            "player_count_bucket": "TEXT NOT NULL DEFAULT 'unknown'",
            "match_shape_bucket": "TEXT NOT NULL DEFAULT 'unknown'",
            "teamkill_exact_count": "INTEGER NOT NULL DEFAULT 0",
            "leave_disconnect_exact_count": "INTEGER NOT NULL DEFAULT 0",
            "kick_or_ban_exact_count": "INTEGER NOT NULL DEFAULT 0",
            "admin_action_exact_count": "INTEGER NOT NULL DEFAULT 0",
            "combat_death_proxy_count": "INTEGER NOT NULL DEFAULT 0",
            "friendly_fire_proxy_count": "INTEGER NOT NULL DEFAULT 0",
            "redeploy_death_exact_count": "INTEGER NOT NULL DEFAULT 0",
            "suicide_death_exact_count": "INTEGER NOT NULL DEFAULT 0",
            "menu_exit_death_exact_count": "INTEGER NOT NULL DEFAULT 0",
            "discipline_capability_status": "TEXT NOT NULL DEFAULT 'not_available'",
            "leave_admin_capability_status": "TEXT NOT NULL DEFAULT 'not_available'",
            "death_type_capability_status": "TEXT NOT NULL DEFAULT 'not_available'",
            "discipline_lineage_status": "TEXT NOT NULL DEFAULT 'not_available'",
        },
    )


def _ensure_table_columns(
    connection: sqlite3.Connection,
    table_name: str,
    columns: dict[str, str],
) -> None:
    existing_columns = {
        str(row["name"])
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    for column_name, column_sql in columns.items():
        if column_name in existing_columns:
            continue
        connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_sql}"
        )


def _connect_writer(db_path: Path):
    return connect_sqlite_writer(db_path)


def _connect_readonly(db_path: Path):
    return connect_sqlite_readonly(db_path)


def _resolve_db_path(db_path: Path | None) -> Path:
    return db_path or get_storage_path()


def _seed_elo_event_capability_registry(connection: sqlite3.Connection) -> None:
    families = (
        ("garrison_events", "Requires raw garrison placement and destruction capture."),
        ("outpost_events", "Requires raw outpost placement and destruction capture."),
        ("revive_events", "Current sources do not expose revive actor-recipient telemetry."),
        ("supply_events", "Current sources do not expose supply placement or usage events."),
        ("node_events", "Current sources do not expose node lifecycle telemetry."),
        ("repair_events", "Current sources do not expose repair or maintenance telemetry."),
        ("mine_events", "Current sources do not expose mine placement, detonation or destruction telemetry."),
        ("commander_ability_events", "Current sources do not expose commander ability usage telemetry."),
        ("strongpoint_presence_events", "Current sources do not expose occupancy or contest timing."),
        ("role_assignment_events", "Current role logic is proxy-only and not event-backed."),
        ("disconnect_leave_admin_events", "Current leave or admin boundaries are participation proxies only."),
        ("death_classification_events", "Current summaries do not expose per-death reason telemetry."),
    )
    source_kinds = (
        "public-scoreboard",
        "rcon-historical-competitive-read-model",
    )
    connection.executemany(
        """
        INSERT INTO elo_event_capability_registry (
            event_family,
            source_kind,
            capability_status,
            instrumentation_status,
            storage_contract_status,
            notes,
            contract_version
        ) VALUES (?, ?, 'not_available', 'blocked_by_missing_telemetry', 'defined', ?, ?)
        ON CONFLICT(event_family, source_kind) DO UPDATE SET
            capability_status = excluded.capability_status,
            instrumentation_status = excluded.instrumentation_status,
            storage_contract_status = excluded.storage_contract_status,
            notes = excluded.notes,
            contract_version = excluded.contract_version,
            updated_at = CURRENT_TIMESTAMP
        """,
        [
            (event_family, source_kind, note, ELO_EVENT_TELEMETRY_CONTRACT_VERSION)
            for event_family, note in families
            for source_kind in source_kinds
        ],
    )
