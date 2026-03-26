"""SQLite storage for persistent Elo/MMR and monthly ranking results."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path

from .config import get_storage_path
from .sqlite_utils import connect_sqlite_readonly, connect_sqlite_writer


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
                accuracy_mode TEXT NOT NULL,
                capabilities_json TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (scope_key, stable_player_key)
            );

            CREATE TABLE IF NOT EXISTS elo_mmr_match_results (
                scope_key TEXT NOT NULL,
                month_key TEXT NOT NULL,
                external_match_id TEXT NOT NULL,
                stable_player_key TEXT NOT NULL,
                player_name TEXT NOT NULL,
                steam_id TEXT,
                server_slug TEXT NOT NULL,
                server_name TEXT NOT NULL,
                match_ended_at TEXT NOT NULL,
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
                player_count INTEGER NOT NULL,
                eligible_player_count INTEGER NOT NULL,
                source_policy_json TEXT NOT NULL,
                capabilities_summary_json TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (scope_key, month_key)
            );

            CREATE INDEX IF NOT EXISTS idx_elo_mmr_monthly_rankings_scope_month
            ON elo_mmr_monthly_rankings(scope_key, month_key, eligible, monthly_rank_score DESC);

            CREATE INDEX IF NOT EXISTS idx_elo_mmr_player_ratings_scope
            ON elo_mmr_player_ratings(scope_key, current_mmr DESC);
            """
        )
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
                accuracy_mode,
                capabilities_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                external_match_id,
                stable_player_key,
                player_name,
                steam_id,
                server_slug,
                server_name,
                match_ended_at,
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
                capabilities_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["scope_key"],
                    row["month_key"],
                    row["external_match_id"],
                    row["stable_player_key"],
                    row["player_name"],
                    row.get("steam_id"),
                    row["server_slug"],
                    row["server_name"],
                    row["match_ended_at"],
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
                eligible,
                eligibility_reason,
                accuracy_mode,
                capabilities_json,
                component_scores_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["scope_key"],
                    row["month_key"],
                    row["stable_player_key"],
                    row["player_name"],
                    row.get("steam_id"),
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
                player_count,
                eligible_player_count,
                source_policy_json,
                capabilities_summary_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["scope_key"],
                    row["month_key"],
                    row["generated_at"],
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
                SELECT generated_at, source_policy_json, capabilities_summary_json
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
                },
                "monthly_rank_score": round(float(row["monthly_rank_score"] or 0.0), 3),
                "components": json.loads(row["component_scores_json"]),
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


def _connect_writer(db_path: Path):
    return connect_sqlite_writer(db_path)


def _connect_readonly(db_path: Path):
    return connect_sqlite_readonly(db_path)


def _resolve_db_path(db_path: Path | None) -> Path:
    return db_path or get_storage_path()
