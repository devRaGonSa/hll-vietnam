"""SQLite storage for persistent Elo/MMR and monthly ranking results."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from .config import get_storage_path
from .sqlite_utils import connect_sqlite_readonly, connect_sqlite_writer

ELO_MMR_CANONICAL_FACT_SCHEMA_VERSION = "elo-canonical-v1"
ELO_MMR_CANONICAL_SOURCE_INPUT_VERSION = "historical-closed-match-v1"


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
            """
        )
        _ensure_schema_extensions(connection)
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
                expected_result,
                actual_result,
                elo_core_delta,
                performance_modifier_delta,
                proxy_modifier_delta,
                capabilities_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    row.get("expected_result", 0.0),
                    row.get("actual_result", 0.0),
                    row.get("elo_core_delta", 0.0),
                    row.get("performance_modifier_delta", 0.0),
                    row.get("proxy_modifier_delta", 0.0),
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


def rebuild_elo_mmr_canonical_facts(*, db_path: Path | None = None) -> dict[str, object]:
    """Materialize the canonical Elo fact layer from persisted historical closed matches."""
    resolved_path = initialize_elo_mmr_storage(db_path=db_path)
    with _connect_writer(resolved_path) as connection:
        connection.execute("DELETE FROM elo_mmr_canonical_player_match_facts")
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
                match_capability_status,
                source_kind,
                fact_schema_version,
                source_input_version
            )
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
                CASE
                    WHEN historical_matches.started_at IS NOT NULL
                     AND historical_matches.allied_score IS NOT NULL
                     AND historical_matches.axis_score IS NOT NULL THEN 'exact'
                    WHEN historical_matches.started_at IS NOT NULL
                      OR historical_matches.allied_score IS NOT NULL
                      OR historical_matches.axis_score IS NOT NULL THEN 'approximate'
                    ELSE 'not_available'
                END AS match_capability_status,
                'historical-closed-match' AS source_kind,
                ? AS fact_schema_version,
                ? AS source_input_version
            FROM historical_matches
            INNER JOIN historical_servers
                ON historical_servers.id = historical_matches.historical_server_id
            WHERE historical_matches.ended_at IS NOT NULL
            """,
            (
                ELO_MMR_CANONICAL_FACT_SCHEMA_VERSION,
                ELO_MMR_CANONICAL_SOURCE_INPUT_VERSION,
            ),
        )

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
                CASE
                    WHEN historical_player_match_stats.team_side IS NOT NULL
                     AND COALESCE(historical_player_match_stats.time_seconds, 0) > 0 THEN 'exact'
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
            WHERE historical_matches.ended_at IS NOT NULL
            """,
            (
                ELO_MMR_CANONICAL_FACT_SCHEMA_VERSION,
                ELO_MMR_CANONICAL_SOURCE_INPUT_VERSION,
            ),
        )

        totals_row = connection.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM elo_mmr_canonical_players) AS players_count,
                (SELECT COUNT(*) FROM elo_mmr_canonical_matches) AS matches_count,
                (SELECT COUNT(*) FROM elo_mmr_canonical_player_match_facts) AS player_match_facts_count
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
        },
    }


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
            "expected_result": "REAL NOT NULL DEFAULT 0",
            "actual_result": "REAL NOT NULL DEFAULT 0",
            "elo_core_delta": "REAL NOT NULL DEFAULT 0",
            "performance_modifier_delta": "REAL NOT NULL DEFAULT 0",
            "proxy_modifier_delta": "REAL NOT NULL DEFAULT 0",
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
