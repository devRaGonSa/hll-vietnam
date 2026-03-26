"""Core Elo/MMR rebuild engine backed by real historical signals."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from statistics import pstdev
from typing import Iterable

from .config import get_historical_data_source_kind
from .data_sources import (
    SOURCE_KIND_PUBLIC_SCOREBOARD,
    SOURCE_KIND_RCON,
    build_source_attempt,
    build_source_policy,
    get_rcon_historical_read_model,
)
from .elo_mmr_models import (
    CAPABILITY_APPROXIMATE,
    CAPABILITY_EXACT,
    CAPABILITY_UNAVAILABLE,
    DEFAULT_BASE_MMR,
    ELO_K_FACTOR,
    FULL_QUALITY_DURATION_SECONDS,
    FULL_QUALITY_PLAYER_COUNT,
    MATCH_RESULT_CONTRACT_VERSION,
    MIN_VALID_MATCH_DURATION_SECONDS,
    MIN_VALID_PLAYER_PARTICIPATION_RATIO,
    MIN_VALID_PLAYER_PARTICIPATION_SECONDS,
    MIN_VALID_MATCH_PLAYERS,
    MONTHLY_ACTIVITY_TARGET_HOURS,
    MONTHLY_ACTIVITY_TARGET_MATCHES,
    MONTHLY_CHECKPOINT_CONTRACT_VERSION,
    MONTHLY_MIN_TIME_SECONDS,
    MONTHLY_MIN_VALID_MATCHES,
    MONTHLY_RANKING_CONTRACT_VERSION,
    MONTHLY_RANKING_FORMULA_VERSION,
    MONTHLY_RANKING_MODEL_VERSION,
    PERSISTENT_RATING_CONTRACT_VERSION,
    PERSISTENT_RATING_FORMULA_VERSION,
    PERSISTENT_RATING_MODEL_VERSION,
    build_signal,
    summarize_accuracy,
)
from .elo_mmr_storage import (
    get_elo_mmr_player_profile,
    initialize_elo_mmr_storage,
    list_elo_mmr_canonical_match_rows,
    list_elo_mmr_monthly_rankings,
    rebuild_elo_mmr_canonical_facts,
    replace_elo_mmr_state,
)
from .historical_storage import ALL_SERVERS_SLUG, initialize_historical_storage
from .rcon_historical_read_model import get_rcon_historical_competitive_match_context
from .writer_lock import backend_writer_lock, build_writer_lock_holder


SCOPE_ALL_SERVERS = ALL_SERVERS_SLUG
QUALITY_BUCKET_HIGH = "high"
QUALITY_BUCKET_MEDIUM = "medium"
QUALITY_BUCKET_LOW = "low"
ROLE_BUCKET_SUPPORT = "support"
ROLE_BUCKET_OFFENSE = "offense"
ROLE_BUCKET_DEFENSE = "defense"
ROLE_BUCKET_COMBAT = "combat"
ROLE_BUCKET_GENERALIST = "generalist"
MONTHLY_MIN_AVG_PARTICIPATION_RATIO = 0.45
MONTHLY_RANK_WEIGHT_COMPETITIVE_GAIN = 0.70
MONTHLY_RANK_WEIGHT_MATCH_SCORE = 0.14
MONTHLY_RANK_WEIGHT_STRENGTH_OF_SCHEDULE = 0.05
MONTHLY_RANK_WEIGHT_CONSISTENCY = 0.04
MONTHLY_RANK_WEIGHT_CONFIDENCE = 0.04
MONTHLY_RANK_WEIGHT_ACTIVITY = 0.03
EXACT_MODIFIER_K_SHARE = 0.06
PROXY_MODIFIER_K_SHARE = 0.02

ROLE_WEIGHTS = {
    ROLE_BUCKET_SUPPORT: {"combat": 0.18, "objective": 0.18, "utility": 0.42, "discipline": 0.22},
    ROLE_BUCKET_OFFENSE: {"combat": 0.38, "objective": 0.30, "utility": 0.10, "discipline": 0.22},
    ROLE_BUCKET_DEFENSE: {"combat": 0.26, "objective": 0.34, "utility": 0.16, "discipline": 0.24},
    ROLE_BUCKET_COMBAT: {"combat": 0.48, "objective": 0.14, "utility": 0.14, "discipline": 0.24},
    ROLE_BUCKET_GENERALIST: {"combat": 0.34, "objective": 0.22, "utility": 0.20, "discipline": 0.24},
}


def rebuild_elo_mmr_models(*, db_path=None) -> dict[str, object]:
    """Rebuild persistent player ratings and monthly rankings from scratch."""
    with backend_writer_lock(holder=build_writer_lock_holder("app.elo_mmr_engine rebuild")):
        resolved_path = initialize_historical_storage(db_path=db_path)
        initialize_elo_mmr_storage(db_path=resolved_path)
        canonical_fact_layer = rebuild_elo_mmr_canonical_facts(db_path=resolved_path)
        historical_source_policy = _build_historical_source_policy_for_elo()
        rcon_read_model = get_rcon_historical_read_model()
        match_rows = list_elo_mmr_canonical_match_rows(db_path=resolved_path)
        grouped_matches = _group_match_rows(match_rows)
        rcon_match_context_cache: dict[tuple[str, str | None, str | None], dict[str, object] | None] = {}

        ratings_by_scope: dict[str, dict[str, dict[str, object]]] = {SCOPE_ALL_SERVERS: {}}
        player_ratings: list[dict[str, object]] = []
        match_results: list[dict[str, object]] = []
        monthly_checkpoints: list[dict[str, object]] = []

        for match_group in grouped_matches:
            server_scope = match_group["server_slug"]
            ratings_by_scope.setdefault(server_scope, {})
            rcon_match_context = None
            if rcon_read_model is not None:
                cache_key = (
                    str(match_group["server_slug"]),
                    str(match_group.get("ended_at")) if match_group.get("ended_at") is not None else None,
                    str(match_group.get("map_pretty_name") or match_group.get("map_name") or "")
                    or None,
                )
                if cache_key not in rcon_match_context_cache:
                    rcon_match_context_cache[cache_key] = get_rcon_historical_competitive_match_context(
                        server_key=str(match_group["server_slug"]),
                        ended_at=match_group.get("ended_at"),
                        map_name=match_group.get("map_pretty_name") or match_group.get("map_name"),
                    )
                rcon_match_context = rcon_match_context_cache[cache_key]
            for scope_key in (server_scope, SCOPE_ALL_SERVERS):
                match_results.extend(
                    _score_match_for_scope(
                        match_group=match_group,
                        scope_key=scope_key,
                        ratings_by_scope=ratings_by_scope[scope_key],
                        rcon_match_context=rcon_match_context,
                    )
                )

        for scope_ratings in ratings_by_scope.values():
            player_ratings.extend(scope_ratings.values())

        monthly_aggregation = _build_monthly_ranking_materialization(
            match_results=match_results,
            historical_source_policy=historical_source_policy,
        )
        monthly_rankings = monthly_aggregation["monthly_rankings"]
        monthly_checkpoints = monthly_aggregation["monthly_checkpoints"]

        replace_elo_mmr_state(
            player_ratings=player_ratings,
            match_results=match_results,
            monthly_rankings=monthly_rankings,
            monthly_checkpoints=monthly_checkpoints,
            db_path=resolved_path,
        )
        latest_month_by_scope = {
            checkpoint["scope_key"]: checkpoint["month_key"] for checkpoint in monthly_checkpoints
        }
        return {
            "status": "ok",
            "canonical_fact_layer": canonical_fact_layer,
            "historical_source_policy": historical_source_policy,
            "persistent_rating_contract": _build_persistent_rating_contract_metadata(),
            "monthly_ranking_contract": _build_monthly_ranking_contract_metadata(),
            "totals": {
                "matches_scored": len({(row["scope_key"], row["external_match_id"]) for row in match_results}),
                "player_ratings": len(player_ratings),
                "match_results": len(match_results),
                "monthly_rankings": len(monthly_rankings),
                "monthly_checkpoints": len(monthly_checkpoints),
            },
            "latest_month_by_scope": latest_month_by_scope,
        }


def list_elo_mmr_leaderboard_payload(*, server_id: str | None, limit: int) -> dict[str, object]:
    """Return the current monthly Elo/MMR leaderboard for one scope."""
    scope_key = _normalize_scope_key(server_id)
    result = list_elo_mmr_monthly_rankings(scope_key=scope_key, limit=limit)
    return {
        "scope_key": scope_key,
        "month_key": result["month_key"],
        "found": result["found"],
        "generated_at": result["generated_at"],
        "model_version": result.get("model_version"),
        "formula_version": result.get("formula_version"),
        "contract_version": result.get("contract_version"),
        "items": result["items"],
        "source_policy": result["source_policy"] or _build_historical_source_policy_for_elo(),
        "capabilities_summary": result["capabilities_summary"],
    }


def get_elo_mmr_player_payload(*, player_id: str, server_id: str | None) -> dict[str, object] | None:
    """Return one Elo/MMR player profile."""
    return get_elo_mmr_player_profile(
        player_id=player_id,
        scope_key=_normalize_scope_key(server_id),
    )


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for Elo/MMR maintenance."""
    parser = argparse.ArgumentParser(
        description="Rebuild or inspect the Elo/MMR monthly ranking system.",
    )
    parser.add_argument(
        "mode",
        choices=("rebuild", "leaderboard", "player"),
        help="rebuild recomputes all persisted Elo/MMR state; leaderboard and player inspect the read model",
    )
    parser.add_argument("--server", dest="server_id", help="optional server scope")
    parser.add_argument("--limit", type=int, default=10, help="max rows for leaderboard mode")
    parser.add_argument("--player", dest="player_id", help="player id or steam id for player mode")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    """Run the Elo/MMR CLI."""
    parser = build_arg_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.mode == "rebuild":
        print(json.dumps(rebuild_elo_mmr_models(), indent=2))
        return 0
    if args.mode == "leaderboard":
        print(json.dumps(list_elo_mmr_leaderboard_payload(server_id=args.server_id, limit=args.limit), indent=2))
        return 0
    if not args.player_id:
        parser.error("--player is required in player mode")
    print(json.dumps(get_elo_mmr_player_payload(player_id=args.player_id, server_id=args.server_id), indent=2))
    return 0


def _group_match_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["server_slug"]), str(row["external_match_id"]))].append(row)
    items: list[dict[str, object]] = []
    for (server_slug, match_id), players in grouped.items():
        first = players[0]
        items.append(
            {
                "server_slug": server_slug,
                "server_name": first["server_name"],
                "canonical_match_key": first.get("canonical_match_key"),
                "external_match_id": match_id,
                "started_at": first["started_at"],
                "ended_at": first["ended_at"],
                "game_mode": first["game_mode"],
                "allied_score": _safe_int(first["allied_score"]),
                "axis_score": _safe_int(first["axis_score"]),
                "match_capability_status": first.get("match_capability_status"),
                "fact_schema_version": first.get("fact_schema_version"),
                "source_input_version": first.get("source_input_version"),
                "players": players,
            }
        )
    return items


def _score_match_for_scope(
    *,
    match_group: dict[str, object],
    scope_key: str,
    ratings_by_scope: dict[str, dict[str, object]],
    rcon_match_context: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    players = list(match_group["players"])
    duration_seconds, duration_mode = _resolve_match_duration(
        match_group,
        players,
        rcon_match_context=rcon_match_context,
    )
    quality_factor = _build_quality_factor(
        player_count=max(len(players), int(rcon_match_context.get("peak_players") or 0))
        if rcon_match_context is not None
        else len(players),
        duration_seconds=duration_seconds,
        has_score=match_group.get("allied_score") is not None and match_group.get("axis_score") is not None,
    )
    quality_bucket = _classify_quality_bucket(quality_factor)
    match_valid = duration_seconds >= MIN_VALID_MATCH_DURATION_SECONDS and len(players) >= MIN_VALID_MATCH_PLAYERS
    month_key = str(match_group["ended_at"])[:7]
    max_kills = max(max(_safe_int(player.get("kills")), 0) for player in players) or 1
    max_support = max(max(_safe_int(player.get("support")), 0) for player in players) or 1
    max_combat = max(max(_safe_int(player.get("combat")), 0) for player in players) or 1
    max_objective = max(
        max(_safe_int(player.get("offense")) + _safe_int(player.get("defense")), 0)
        for player in players
    ) or 1
    results: list[dict[str, object]] = []
    rating_before_by_player = {
        str(player["stable_player_key"]): float(
            ratings_by_scope.get(str(player["stable_player_key"]), {}).get("current_mmr", DEFAULT_BASE_MMR)
        )
        for player in players
    }

    for player in players:
        stable_player_key = str(player["stable_player_key"])
        rating_row = ratings_by_scope.setdefault(
            stable_player_key,
            {
                "scope_key": scope_key,
                "stable_player_key": stable_player_key,
                "player_name": player["player_name"],
                "steam_id": player.get("steam_id"),
                "current_mmr": DEFAULT_BASE_MMR,
                "matches_processed": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "last_match_id": None,
                "last_match_ended_at": None,
                "model_version": PERSISTENT_RATING_MODEL_VERSION,
                "formula_version": PERSISTENT_RATING_FORMULA_VERSION,
                "contract_version": PERSISTENT_RATING_CONTRACT_VERSION,
                "accuracy_mode": "partial",
                "capabilities": summarize_accuracy([]),
            },
        )
        signals: list[dict[str, object]] = []
        time_seconds = _safe_int(player.get("time_seconds"))
        participation_ratio = _build_participation_ratio(
            time_seconds=time_seconds,
            duration_seconds=duration_seconds,
        )
        player_match_valid = match_valid and _is_player_match_eligible(
            time_seconds=time_seconds,
            participation_ratio=participation_ratio,
        )
        team_outcome = _resolve_team_outcome(
            team_side=str(player.get("team_side") or ""),
            allied_score=_safe_int(match_group.get("allied_score")),
            axis_score=_safe_int(match_group.get("axis_score")),
        )
        outcome_score = _build_outcome_score(
            team_outcome=team_outcome,
            allied_score=_safe_int(match_group.get("allied_score")),
            axis_score=_safe_int(match_group.get("axis_score")),
        )
        signals.append(build_signal("OutcomeScore", CAPABILITY_EXACT, "Derived from team side and final match score."))
        signals.append(build_signal("MatchValidity", CAPABILITY_EXACT, "Uses closed match state, duration and lobby size thresholds."))
        if duration_seconds > 0:
            signals.append(build_signal("PlayerParticipation", CAPABILITY_EXACT, "Uses persisted player time_seconds relative to match duration."))

        kills = _safe_int(player.get("kills"))
        deaths = max(1, _safe_int(player.get("deaths")))
        combat_raw = _safe_int(player.get("combat"))
        combat_index = round(
            (40.0 * (kills / max_kills))
            + (35.0 * min(1.0, (kills / deaths) / 3.0))
            + (25.0 * (combat_raw / max_combat)),
            3,
        )
        signals.append(build_signal("CombatIndex", CAPABILITY_EXACT, "Uses kills, KDA proxy and persisted combat score."))

        support = _safe_int(player.get("support"))
        utility_index = round(100.0 * (support / max_support), 3) if max_support > 0 else 0.0
        signals.append(build_signal("UtilityIndex", CAPABILITY_EXACT, "Uses persisted support points."))

        objective_proxy = _safe_int(player.get("offense")) + _safe_int(player.get("defense"))
        objective_index = round(100.0 * (objective_proxy / max_objective), 3) if max_objective > 0 else 0.0
        signals.append(build_signal("ObjectiveIndex", CAPABILITY_APPROXIMATE, "Approximated from offense and defense scoreboard points because no tactical event feed exists yet."))

        teamkills = _safe_int(player.get("teamkills"))
        completion_component = round(participation_ratio * 100.0, 3)
        discipline_index = round(
            max(
                0.0,
                (88.0 - (teamkills * 18.0)) + (0.12 * completion_component),
            ),
            3,
        )
        signals.append(build_signal("DisciplineIndex", CAPABILITY_APPROXIMATE, "Uses exact teamkills plus participation as an honest proxy for leave or AFK risk because direct discipline telemetry is unavailable."))
        leadership_index = None
        signals.append(build_signal("LeadershipIndex", CAPABILITY_UNAVAILABLE, "No leadership-specific telemetry is stored in the repository yet."))

        role_bucket = _resolve_role_bucket(player)
        signals.append(build_signal("role_bucket", CAPABILITY_APPROXIMATE, "Inferred from the dominant combat/offense/defense/support axis because literal player role is unavailable."))
        if duration_mode == CAPABILITY_EXACT:
            signals.append(build_signal("quality_duration", CAPABILITY_EXACT, "Duration computed from match timestamps."))
        else:
            signals.append(build_signal("quality_duration", CAPABILITY_APPROXIMATE, "Duration approximated from the maximum persisted player time."))
        if rcon_match_context is not None:
            signals.append(
                build_signal(
                    "RconCompetitiveWindow",
                    CAPABILITY_APPROXIMATE,
                    "Uses the closest RCON-backed competitive window for match duration and lobby density when coverage exists.",
                )
            )

        weights = ROLE_WEIGHTS.get(role_bucket, ROLE_WEIGHTS[ROLE_BUCKET_GENERALIST])
        impact_score = round(
            sum(
                {
                    "combat": combat_index,
                    "objective": objective_index,
                    "utility": utility_index,
                    "discipline": discipline_index,
                }[key]
                * weight
                for key, weight in weights.items()
            ),
            3,
        )
        team_side = str(player.get("team_side") or "")
        strength_of_schedule_match = _build_strength_of_schedule_match(
            stable_player_key=stable_player_key,
            team_side=team_side,
            players=players,
            rating_before_by_player=rating_before_by_player,
            quality_factor=quality_factor,
        )
        signals.append(build_signal("StrengthOfScheduleMatch", CAPABILITY_APPROXIMATE, "Approximated from opponent average MMR pressure plus match quality because no full roster graph is stored."))
        exact_modifier_index = _build_weighted_modifier_index(
            left_value=combat_index,
            right_value=utility_index,
            left_weight=weights["combat"],
            right_weight=weights["utility"],
        )
        proxy_modifier_index = _build_weighted_modifier_index(
            left_value=objective_index,
            right_value=discipline_index,
            left_weight=weights["objective"],
            right_weight=weights["discipline"],
        )
        effective_score = round(
            (
                (0.60 * outcome_score)
                + (0.25 * impact_score)
                + (0.10 * strength_of_schedule_match)
                + (0.05 * discipline_index)
            )
            * participation_ratio,
            3,
        )
        if not player_match_valid:
            delta_mmr = 0.0
            match_score = 0.0
            expected_result = 0.0
            actual_result = 0.0
            elo_core_delta = 0.0
            performance_modifier_delta = 0.0
            proxy_modifier_delta = 0.0
        else:
            expected_result = _build_expected_result(
                player_rating=rating_before_by_player.get(stable_player_key, DEFAULT_BASE_MMR),
                opponent_average_rating=_resolve_opponent_average_rating(
                    stable_player_key=stable_player_key,
                    team_side=team_side,
                    players=players,
                    rating_before_by_player=rating_before_by_player,
                ),
            )
            actual_result = _build_actual_result(
                team_outcome=team_outcome,
                allied_score=_safe_int(match_group.get("allied_score")),
                axis_score=_safe_int(match_group.get("axis_score")),
                participation_ratio=participation_ratio,
            )
            exact_modifier_edge = _build_centered_modifier_edge(
                exact_modifier_index,
                participation_ratio=participation_ratio,
            )
            proxy_modifier_edge = _build_centered_modifier_edge(
                proxy_modifier_index,
                participation_ratio=participation_ratio,
            )
            elo_core_delta = round(
                ELO_K_FACTOR * quality_factor * (actual_result - expected_result),
                3,
            )
            exact_modifier_delta = round(
                ELO_K_FACTOR * quality_factor * EXACT_MODIFIER_K_SHARE * exact_modifier_edge,
                3,
            )
            proxy_modifier_delta = round(
                ELO_K_FACTOR * quality_factor * PROXY_MODIFIER_K_SHARE * proxy_modifier_edge,
                3,
            )
            performance_modifier_delta = exact_modifier_delta
            delta_mmr = round(elo_core_delta + performance_modifier_delta + proxy_modifier_delta, 3)
            match_score = round(effective_score * quality_factor, 3)
            signals.append(build_signal("DeltaMMR", CAPABILITY_APPROXIMATE, "Uses Elo-like expected-vs-actual movement plus bounded HLL performance modifiers and honest proxy boundaries."))
            signals.append(build_signal("MatchScore", CAPABILITY_APPROXIMATE, "Uses outcome-first competitive scoring with bounded HLL impact and schedule context, then scales by match quality."))
        capability_summary = summarize_accuracy(signals)
        rating_before = float(rating_row["current_mmr"])
        rating_after = round(rating_before + delta_mmr, 3)
        results.append(
            {
                "scope_key": scope_key,
                "month_key": month_key,
                "canonical_match_key": match_group.get("canonical_match_key"),
                "external_match_id": match_group["external_match_id"],
                "stable_player_key": stable_player_key,
                "player_name": player["player_name"],
                "steam_id": player.get("steam_id"),
                "server_slug": match_group["server_slug"],
                "server_name": match_group["server_name"],
                "match_ended_at": match_group["ended_at"],
                "fact_schema_version": match_group.get("fact_schema_version"),
                "source_input_version": match_group.get("source_input_version"),
                "model_version": PERSISTENT_RATING_MODEL_VERSION,
                "formula_version": PERSISTENT_RATING_FORMULA_VERSION,
                "contract_version": MATCH_RESULT_CONTRACT_VERSION,
                "match_valid": player_match_valid,
                "quality_factor": quality_factor,
                "quality_bucket": quality_bucket,
                "role_bucket": role_bucket,
                "role_bucket_mode": CAPABILITY_APPROXIMATE,
                "outcome_score": outcome_score,
                "combat_index": combat_index,
                "objective_index": objective_index,
                "objective_index_mode": CAPABILITY_APPROXIMATE,
                "utility_index": utility_index,
                "utility_index_mode": CAPABILITY_EXACT,
                "leadership_index": leadership_index,
                "leadership_index_mode": CAPABILITY_UNAVAILABLE,
                "discipline_index": discipline_index,
                "discipline_index_mode": CAPABILITY_APPROXIMATE,
                "impact_score": impact_score,
                "delta_mmr": delta_mmr,
                "mmr_before": rating_before,
                "mmr_after": rating_after,
                "match_score": match_score,
                "penalty_points": round((teamkills * 2.0) + max(0.0, (0.5 - participation_ratio) * 8.0), 3),
                "capabilities": capability_summary,
                "time_seconds": time_seconds,
                "participation_ratio": participation_ratio,
                "strength_of_schedule_match": strength_of_schedule_match,
                "team_outcome": team_outcome,
                "expected_result": expected_result,
                "actual_result": actual_result,
                "elo_core_delta": elo_core_delta,
                "performance_modifier_delta": performance_modifier_delta,
                "proxy_modifier_delta": proxy_modifier_delta,
            }
        )
        rating_row["current_mmr"] = rating_after
        rating_row["matches_processed"] = int(rating_row["matches_processed"]) + 1
        rating_row["last_match_id"] = match_group["external_match_id"]
        rating_row["last_match_ended_at"] = match_group["ended_at"]
        rating_row["model_version"] = PERSISTENT_RATING_MODEL_VERSION
        rating_row["formula_version"] = PERSISTENT_RATING_FORMULA_VERSION
        rating_row["contract_version"] = PERSISTENT_RATING_CONTRACT_VERSION
        rating_row["accuracy_mode"] = capability_summary["accuracy_mode"]
        rating_row["capabilities"] = capability_summary
        if team_outcome == "win":
            rating_row["wins"] = int(rating_row["wins"]) + 1
        elif team_outcome == "draw":
            rating_row["draws"] = int(rating_row["draws"]) + 1
        else:
            rating_row["losses"] = int(rating_row["losses"]) + 1
    return results


def _build_monthly_rankings(match_results: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in match_results:
        grouped[(row["scope_key"], row["month_key"], row["stable_player_key"])].append(row)

    rankings: list[dict[str, object]] = []
    grouped_by_scope_month: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for (scope_key, month_key, stable_player_key), rows in grouped.items():
        rows.sort(key=lambda item: (item["match_ended_at"], item["external_match_id"]))
        valid_rows = [row for row in rows if row["match_valid"]]
        total_time_seconds = sum(int(row["time_seconds"] or 0) for row in rows)
        penalty_points = round(sum(float(row["penalty_points"]) for row in rows), 3)
        capability_rows = [row["capabilities"] for row in rows]
        exact_ratio = round(sum(float(item["exact_ratio"]) for item in capability_rows) / max(1, len(capability_rows)), 3)
        approximate_ratio = round(sum(float(item["approximate_ratio"]) for item in capability_rows) / max(1, len(capability_rows)), 3)
        unavailable_ratio = round(sum(float(item["unavailable_ratio"]) for item in capability_rows) / max(1, len(capability_rows)), 3)
        accuracy_mode = "partial" if unavailable_ratio > 0 else "approximate" if approximate_ratio > 0 else "exact"
        avg_match_score = round(sum(float(row["match_score"]) for row in valid_rows) / max(1, len(valid_rows)), 3)
        baseline_mmr = round(float(rows[0]["mmr_before"]), 3)
        current_mmr = round(float(rows[-1]["mmr_after"]), 3)
        mmr_gain = round(current_mmr - baseline_mmr, 3)
        elo_core_gain = round(sum(float(row.get("elo_core_delta") or 0.0) for row in rows), 3)
        performance_modifier_gain = round(
            sum(float(row.get("performance_modifier_delta") or 0.0) for row in rows),
            3,
        )
        proxy_modifier_gain = round(
            sum(float(row.get("proxy_modifier_delta") or 0.0) for row in rows),
            3,
        )
        avg_participation_ratio = round(
            sum(float(row.get("participation_ratio") or 0.0) for row in rows) / max(1, len(rows)),
            3,
        )
        strength_of_schedule = round(
            sum(float(row.get("strength_of_schedule_match") or 0.0) for row in valid_rows) / max(1, len(valid_rows)),
            3,
        )
        consistency = _build_consistency_score(valid_rows)
        activity = _build_activity_score(valid_rows, total_time_seconds)
        confidence = round(
            min(
                100.0,
                (len(valid_rows) / MONTHLY_MIN_VALID_MATCHES) * 35.0
                + (total_time_seconds / MONTHLY_MIN_TIME_SECONDS) * 30.0
                + (avg_participation_ratio * 20.0)
                + (exact_ratio * 15.0),
            ),
            3,
        )
        eligible = (
            len(valid_rows) >= MONTHLY_MIN_VALID_MATCHES
            and total_time_seconds >= MONTHLY_MIN_TIME_SECONDS
            and avg_participation_ratio >= MONTHLY_MIN_AVG_PARTICIPATION_RATIO
        )
        eligibility_reason = _build_monthly_eligibility_reason(
            valid_match_count=len(valid_rows),
            total_time_seconds=total_time_seconds,
            avg_participation_ratio=avg_participation_ratio,
        )
        grouped_by_scope_month[(scope_key, month_key)].append(
            {
                "scope_key": scope_key,
                "month_key": month_key,
                "stable_player_key": stable_player_key,
                "player_name": rows[-1]["player_name"],
                "steam_id": rows[-1].get("steam_id"),
                "model_version": MONTHLY_RANKING_MODEL_VERSION,
                "formula_version": MONTHLY_RANKING_FORMULA_VERSION,
                "contract_version": MONTHLY_RANKING_CONTRACT_VERSION,
                "current_mmr": current_mmr,
                "baseline_mmr": baseline_mmr,
                "mmr_gain": mmr_gain,
                "avg_match_score": avg_match_score,
                "strength_of_schedule": strength_of_schedule,
                "consistency": consistency,
                "activity": activity,
                "confidence": confidence,
                "penalty_points": penalty_points,
                "monthly_rank_score": 0.0,
                "valid_matches": len(valid_rows),
                "total_matches": len(rows),
                "total_time_seconds": total_time_seconds,
                "avg_participation_ratio": avg_participation_ratio,
                "eligible": eligible,
                "eligibility_reason": eligibility_reason,
                "accuracy_mode": accuracy_mode,
                "capabilities": {
                    "accuracy_mode": accuracy_mode,
                    "exact_ratio": exact_ratio,
                    "approximate_ratio": approximate_ratio,
                    "unavailable_ratio": unavailable_ratio,
                    "signals": [
                        build_signal("OutcomeScore", CAPABILITY_EXACT, "Uses final scores and team side."),
                        build_signal("CombatIndex", CAPABILITY_EXACT, "Uses historical player stats."),
                        build_signal("ObjectiveIndex", CAPABILITY_APPROXIMATE, "Uses offense and defense scores as a tactical proxy."),
                        build_signal("UtilityIndex", CAPABILITY_EXACT, "Uses support points."),
                        build_signal("LeadershipIndex", CAPABILITY_UNAVAILABLE, "No leadership telemetry exists yet."),
                        build_signal("DisciplineIndex", CAPABILITY_APPROXIMATE, "Uses teamkills exactly plus participation as a leave-risk proxy."),
                        build_signal("StrengthOfSchedule", CAPABILITY_APPROXIMATE, "Uses opponent average MMR pressure plus match quality, not a full roster graph."),
                        build_signal("MonthlyEligibility", CAPABILITY_EXACT, "Uses persisted valid-match count, playtime and participation thresholds."),
                    ],
                },
                "component_scores": {
                    "model_version": MONTHLY_RANKING_MODEL_VERSION,
                    "ranking_formula_version": MONTHLY_RANKING_FORMULA_VERSION,
                    "persistent_rating_model_version": PERSISTENT_RATING_MODEL_VERSION,
                    "persistent_rating_formula_version": PERSISTENT_RATING_FORMULA_VERSION,
                    "persistent_rating_contract_version": PERSISTENT_RATING_CONTRACT_VERSION,
                    "match_result_contract_version": MATCH_RESULT_CONTRACT_VERSION,
                    "monthly_ranking_contract_version": MONTHLY_RANKING_CONTRACT_VERSION,
                    "avg_match_score": avg_match_score,
                    "mmr_gain_raw": mmr_gain,
                    "elo_core_gain": elo_core_gain,
                    "performance_modifier_gain": performance_modifier_gain,
                    "proxy_modifier_gain": proxy_modifier_gain,
                    "competitive_gain": round(
                        elo_core_gain
                        + (0.25 * performance_modifier_gain)
                        + (0.10 * proxy_modifier_gain),
                        3,
                    ),
                    "strength_of_schedule": strength_of_schedule,
                    "consistency": consistency,
                    "activity": activity,
                    "confidence": confidence,
                    "avg_participation_ratio": avg_participation_ratio,
                    "penalty_points": penalty_points,
                },
            }
        )

    for rows in grouped_by_scope_month.values():
        max_avg = max((row["avg_match_score"] for row in rows), default=1.0) or 1.0
        max_competitive_gain = max(
            (max(0.0, float(row["component_scores"].get("competitive_gain") or 0.0)) for row in rows),
            default=1.0,
        ) or 1.0
        max_sos = max((row["strength_of_schedule"] for row in rows), default=1.0) or 1.0
        max_consistency = max((row["consistency"] for row in rows), default=1.0) or 1.0
        max_activity = max((row["activity"] for row in rows), default=1.0) or 1.0
        max_confidence = max((row["confidence"] for row in rows), default=1.0) or 1.0
        for row in rows:
            competitive_gain = max(0.0, float(row["component_scores"].get("competitive_gain") or 0.0))
            normalized_gain = competitive_gain / max_competitive_gain if max_competitive_gain > 0 else 0.0
            row["component_scores"]["normalized_mmr_gain"] = round(normalized_gain * 100.0, 3)
            row["monthly_rank_score"] = round(
                (MONTHLY_RANK_WEIGHT_COMPETITIVE_GAIN * normalized_gain * 100.0)
                + (MONTHLY_RANK_WEIGHT_MATCH_SCORE * (row["avg_match_score"] / max_avg) * 100.0)
                + (MONTHLY_RANK_WEIGHT_STRENGTH_OF_SCHEDULE * (row["strength_of_schedule"] / max_sos) * 100.0)
                + (MONTHLY_RANK_WEIGHT_CONSISTENCY * (row["consistency"] / max_consistency) * 100.0)
                + (MONTHLY_RANK_WEIGHT_ACTIVITY * (row["activity"] / max_activity) * 100.0)
                + (MONTHLY_RANK_WEIGHT_CONFIDENCE * (row["confidence"] / max_confidence) * 100.0)
                - row["penalty_points"],
                3,
            )
            rankings.append(row)
    return rankings


def _build_monthly_ranking_materialization(
    *,
    match_results: list[dict[str, object]],
    historical_source_policy: dict[str, object],
) -> dict[str, list[dict[str, object]]]:
    monthly_rankings = _build_monthly_rankings(match_results)
    checkpoint_groups: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in monthly_rankings:
        checkpoint_groups[(row["scope_key"], row["month_key"])].append(row)

    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    monthly_checkpoints: list[dict[str, object]] = []
    for (scope_key, month_key), rows in checkpoint_groups.items():
        eligible_count = sum(1 for row in rows if row["eligible"])
        exact_ratio = round(
            sum(float(row["capabilities"]["exact_ratio"]) for row in rows) / max(1, len(rows)),
            3,
        )
        approximate_ratio = round(
            sum(float(row["capabilities"]["approximate_ratio"]) for row in rows) / max(1, len(rows)),
            3,
        )
        unavailable_ratio = round(
            sum(float(row["capabilities"]["unavailable_ratio"]) for row in rows) / max(1, len(rows)),
            3,
        )
        partial_count = sum(1 for row in rows if row["accuracy_mode"] == "partial")
        monthly_checkpoints.append(
            {
                "scope_key": scope_key,
                "month_key": month_key,
                "generated_at": generated_at,
                "model_version": MONTHLY_RANKING_MODEL_VERSION,
                "formula_version": MONTHLY_RANKING_FORMULA_VERSION,
                "contract_version": MONTHLY_CHECKPOINT_CONTRACT_VERSION,
                "player_count": len(rows),
                "eligible_player_count": eligible_count,
                "source_policy": historical_source_policy,
                "capabilities_summary": {
                    "accuracy_mode": "partial" if partial_count > 0 else "approximate" if approximate_ratio > 0 else "exact",
                    "exact_ratio": exact_ratio,
                    "approximate_ratio": approximate_ratio,
                    "unavailable_ratio": unavailable_ratio,
                    "partial_count": partial_count,
                    "aggregation_contract": _build_monthly_ranking_contract_metadata(),
                    "notes": [
                        "Outcome, combat, utility, match validity and player participation use real stored signals.",
                        "ObjectiveIndex, role bucket, discipline and strength of schedule rely partly on honest proxies.",
                        "LeadershipIndex is not available with the current repository telemetry.",
                    ],
                },
            }
        )
    return {
        "monthly_rankings": monthly_rankings,
        "monthly_checkpoints": monthly_checkpoints,
    }


def _build_persistent_rating_contract_metadata() -> dict[str, object]:
    return {
        "model_version": PERSISTENT_RATING_MODEL_VERSION,
        "formula_version": PERSISTENT_RATING_FORMULA_VERSION,
        "contract_version": PERSISTENT_RATING_CONTRACT_VERSION,
        "match_result_contract_version": MATCH_RESULT_CONTRACT_VERSION,
    }


def _build_monthly_ranking_contract_metadata() -> dict[str, object]:
    return {
        "model_version": MONTHLY_RANKING_MODEL_VERSION,
        "formula_version": MONTHLY_RANKING_FORMULA_VERSION,
        "contract_version": MONTHLY_RANKING_CONTRACT_VERSION,
        "checkpoint_contract_version": MONTHLY_CHECKPOINT_CONTRACT_VERSION,
        "persistent_rating_model_version": PERSISTENT_RATING_MODEL_VERSION,
        "persistent_rating_formula_version": PERSISTENT_RATING_FORMULA_VERSION,
        "match_result_contract_version": MATCH_RESULT_CONTRACT_VERSION,
    }


def _build_historical_source_policy_for_elo() -> dict[str, object]:
    if get_historical_data_source_kind() != SOURCE_KIND_RCON:
        return build_source_policy(
            primary_source=SOURCE_KIND_PUBLIC_SCOREBOARD,
            selected_source=SOURCE_KIND_PUBLIC_SCOREBOARD,
            source_attempts=[build_source_attempt(source=SOURCE_KIND_PUBLIC_SCOREBOARD, role="primary", status="success")],
        )
    return build_source_policy(
        primary_source=SOURCE_KIND_RCON,
        selected_source="hybrid-rcon-competitive-plus-public-scoreboard",
        fallback_used=True,
        fallback_reason="rcon-competitive-context-primary-but-player-stats-still-require-public-scoreboard-supplement",
        source_attempts=[
            build_source_attempt(
                source=SOURCE_KIND_RCON,
                role="primary",
                status="partial",
                reason="rcon-competitive-context-used-for-match-coverage-and-quality",
            ),
            build_source_attempt(
                source=SOURCE_KIND_PUBLIC_SCOREBOARD,
                role="supplemental-fallback",
                status="success",
                reason="public-scoreboard-still-provides-player-level-competitive-stats",
            ),
        ],
    )


def _resolve_match_duration(
    match_group: dict[str, object],
    players: list[dict[str, object]],
    *,
    rcon_match_context: dict[str, object] | None = None,
) -> tuple[int, str]:
    if rcon_match_context and int(rcon_match_context.get("duration_seconds") or 0) > 0:
        return int(rcon_match_context["duration_seconds"]), CAPABILITY_APPROXIMATE
    started_at = _parse_optional_timestamp(match_group.get("started_at"))
    ended_at = _parse_optional_timestamp(match_group.get("ended_at"))
    if started_at and ended_at and ended_at >= started_at:
        return int((ended_at - started_at).total_seconds()), CAPABILITY_EXACT
    return max((_safe_int(player.get("time_seconds")) for player in players), default=0), CAPABILITY_APPROXIMATE


def _build_quality_factor(*, player_count: int, duration_seconds: int, has_score: bool) -> float:
    player_component = min(1.0, player_count / FULL_QUALITY_PLAYER_COUNT)
    duration_component = min(1.0, duration_seconds / FULL_QUALITY_DURATION_SECONDS)
    score_component = 1.0 if has_score else 0.7
    return round((0.4 * player_component) + (0.4 * duration_component) + (0.2 * score_component), 3)


def _build_actual_result(
    *,
    team_outcome: str,
    allied_score: int | None,
    axis_score: int | None,
    participation_ratio: float,
) -> float:
    if team_outcome == "draw":
        base_result = 0.5
    elif team_outcome == "win":
        base_result = 1.0
    else:
        base_result = 0.0
    if allied_score is None or axis_score is None:
        margin_adjustment = 0.0
    else:
        total_score = max(1, allied_score + axis_score)
        margin_ratio = abs(allied_score - axis_score) / total_score
        margin_adjustment = min(0.08, margin_ratio * 0.12)
    if team_outcome == "win":
        adjusted = min(1.0, base_result + margin_adjustment)
    elif team_outcome == "loss":
        adjusted = max(0.0, base_result - margin_adjustment)
    else:
        adjusted = base_result
    return round(0.5 + ((adjusted - 0.5) * participation_ratio), 4)


def _build_weighted_modifier_index(
    *,
    left_value: float,
    right_value: float,
    left_weight: float,
    right_weight: float,
) -> float:
    total_weight = max(0.001, left_weight + right_weight)
    return round(((left_value * left_weight) + (right_value * right_weight)) / total_weight, 3)


def _build_centered_modifier_edge(index_value: float, *, participation_ratio: float) -> float:
    centered = (index_value - 50.0) / 50.0
    return round(max(-1.0, min(1.0, centered * participation_ratio)), 4)


def _build_participation_ratio(*, time_seconds: int, duration_seconds: int) -> float:
    if duration_seconds <= 0:
        return 0.0
    return round(min(1.0, max(0.0, time_seconds / duration_seconds)), 3)


def _is_player_match_eligible(*, time_seconds: int, participation_ratio: float) -> bool:
    return (
        time_seconds >= MIN_VALID_PLAYER_PARTICIPATION_SECONDS
        and participation_ratio >= MIN_VALID_PLAYER_PARTICIPATION_RATIO
    )


def _build_outcome_score(*, team_outcome: str, allied_score: int | None, axis_score: int | None) -> float:
    if allied_score is None or axis_score is None:
        return 50.0 if team_outcome == "draw" else 65.0 if team_outcome == "win" else 35.0
    total_score = max(1, allied_score + axis_score)
    margin_ratio = abs(allied_score - axis_score) / total_score
    if team_outcome == "draw":
        return 50.0
    if team_outcome == "win":
        return round(min(100.0, 68.0 + (margin_ratio * 32.0)), 3)
    return round(max(0.0, 32.0 - (margin_ratio * 32.0)), 3)


def _resolve_opponent_average_rating(
    *,
    stable_player_key: str,
    team_side: str,
    players: list[dict[str, object]],
    rating_before_by_player: dict[str, float],
) -> float:
    normalized_team_side = str(team_side or "").strip().lower()
    opponent_ratings = [
        rating_before_by_player.get(str(player["stable_player_key"]), DEFAULT_BASE_MMR)
        for player in players
        if str(player["stable_player_key"]) != stable_player_key
        and _is_same_team(str(player.get("team_side") or ""), normalized_team_side) is False
    ]
    if not opponent_ratings:
        return DEFAULT_BASE_MMR
    return round(sum(opponent_ratings) / len(opponent_ratings), 3)


def _build_strength_of_schedule_match(
    *,
    stable_player_key: str,
    team_side: str,
    players: list[dict[str, object]],
    rating_before_by_player: dict[str, float],
    quality_factor: float,
) -> float:
    opponent_average = _resolve_opponent_average_rating(
        stable_player_key=stable_player_key,
        team_side=team_side,
        players=players,
        rating_before_by_player=rating_before_by_player,
    )
    mmr_pressure = 50.0 + ((opponent_average - DEFAULT_BASE_MMR) / 8.0)
    quality_pressure = quality_factor * 35.0
    return round(min(100.0, max(0.0, mmr_pressure + quality_pressure)), 3)


def _build_expected_result(*, player_rating: float, opponent_average_rating: float) -> float:
    exponent = (opponent_average_rating - player_rating) / 400.0
    return round(1.0 / (1.0 + (10.0**exponent)), 4)


def _build_monthly_eligibility_reason(
    *,
    valid_match_count: int,
    total_time_seconds: int,
    avg_participation_ratio: float,
) -> str | None:
    if valid_match_count < MONTHLY_MIN_VALID_MATCHES:
        return "minimum-valid-matches-not-met"
    if total_time_seconds < MONTHLY_MIN_TIME_SECONDS:
        return "minimum-playtime-not-met"
    if avg_participation_ratio < MONTHLY_MIN_AVG_PARTICIPATION_RATIO:
        return "minimum-participation-ratio-not-met"
    return None


def _classify_quality_bucket(quality_factor: float) -> str:
    if quality_factor >= 0.8:
        return QUALITY_BUCKET_HIGH
    if quality_factor >= 0.55:
        return QUALITY_BUCKET_MEDIUM
    return QUALITY_BUCKET_LOW


def _resolve_team_outcome(*, team_side: str, allied_score: int | None, axis_score: int | None) -> str:
    if allied_score is None or axis_score is None or allied_score == axis_score:
        return "draw"
    normalized = team_side.strip().lower()
    allied_won = allied_score > axis_score
    if normalized.startswith("all"):
        return "win" if allied_won else "loss"
    if normalized.startswith("ax"):
        return "win" if not allied_won else "loss"
    return "draw"


def _is_same_team(team_side: str, normalized_team_side: str) -> bool:
    candidate = team_side.strip().lower()
    if normalized_team_side.startswith("all"):
        return candidate.startswith("all")
    if normalized_team_side.startswith("ax"):
        return candidate.startswith("ax")
    return candidate == normalized_team_side


def _resolve_role_bucket(player: dict[str, object]) -> str:
    axes = {
        ROLE_BUCKET_SUPPORT: _safe_int(player.get("support")),
        ROLE_BUCKET_OFFENSE: _safe_int(player.get("offense")),
        ROLE_BUCKET_DEFENSE: _safe_int(player.get("defense")),
        ROLE_BUCKET_COMBAT: _safe_int(player.get("combat")),
    }
    top_bucket, top_value = max(axes.items(), key=lambda item: item[1])
    sorted_values = sorted(axes.values(), reverse=True)
    if top_value <= 0 or (len(sorted_values) >= 2 and sorted_values[0] == sorted_values[1]):
        return ROLE_BUCKET_GENERALIST
    return top_bucket


def _build_consistency_score(rows: list[dict[str, object]]) -> float:
    if len(rows) <= 1:
        return 100.0 if rows else 0.0
    values = [float(row["match_score"]) for row in rows]
    average = sum(values) / len(values)
    if average <= 0:
        return 0.0
    return round(100.0 * (1.0 - min(1.0, pstdev(values) / max(average, 1.0))), 3)


def _build_activity_score(rows: list[dict[str, object]], total_time_seconds: int) -> float:
    match_component = min(1.0, len(rows) / MONTHLY_ACTIVITY_TARGET_MATCHES)
    hour_component = min(1.0, (total_time_seconds / 3600.0) / MONTHLY_ACTIVITY_TARGET_HOURS)
    return round(((0.6 * match_component) + (0.4 * hour_component)) * 100.0, 3)


def _normalize_scope_key(server_id: str | None) -> str:
    normalized = str(server_id or SCOPE_ALL_SERVERS).strip()
    return normalized or SCOPE_ALL_SERVERS


def _parse_optional_timestamp(value: object) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _safe_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
