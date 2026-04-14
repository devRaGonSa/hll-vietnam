"""Core Elo/MMR rebuild engine backed by real historical signals."""

from __future__ import annotations

import argparse
import gc
import json
import sys
import traceback
from collections import defaultdict
from datetime import datetime, timezone
from math import sqrt
from statistics import pstdev
from time import perf_counter
from typing import Callable, Iterable

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
    clear_elo_mmr_persisted_state,
    get_elo_mmr_player_profile,
    initialize_elo_mmr_storage,
    list_elo_mmr_canonical_match_rows,
    list_elo_mmr_match_results,
    list_elo_mmr_monthly_rankings,
    persist_elo_mmr_match_results,
    persist_elo_mmr_player_ratings,
    rebuild_elo_mmr_canonical_facts,
    replace_elo_mmr_monthly_state,
)
from .historical_storage import ALL_SERVERS_SLUG, initialize_historical_storage, run_historical_storage_maintenance
from .rcon_historical_read_model import get_rcon_historical_competitive_match_context
from .writer_lock import backend_writer_lock, build_writer_lock_holder


SCOPE_ALL_SERVERS = ALL_SERVERS_SLUG
QUALITY_BUCKET_HIGH = "high"
QUALITY_BUCKET_MEDIUM = "medium"
QUALITY_BUCKET_LOW = "low"
DURATION_BUCKET_FULL = "full"
DURATION_BUCKET_STANDARD = "standard"
DURATION_BUCKET_SHORT = "short"
DURATION_BUCKET_UNKNOWN = "unknown"
PARTICIPATION_BUCKET_FULL = "full"
PARTICIPATION_BUCKET_CORE = "core"
PARTICIPATION_BUCKET_LIMITED = "limited"
PARTICIPATION_BUCKET_NONE = "none"
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
MATCH_RESULT_PERSIST_BATCH_SIZE = 10000
_CURRENT_CLI_PHASE: str | None = None

ROLE_WEIGHTS = {
    ROLE_BUCKET_SUPPORT: {"combat": 0.18, "objective": 0.18, "utility": 0.42, "discipline": 0.22},
    ROLE_BUCKET_OFFENSE: {"combat": 0.38, "objective": 0.30, "utility": 0.10, "discipline": 0.22},
    ROLE_BUCKET_DEFENSE: {"combat": 0.26, "objective": 0.34, "utility": 0.16, "discipline": 0.24},
    ROLE_BUCKET_COMBAT: {"combat": 0.48, "objective": 0.14, "utility": 0.14, "discipline": 0.24},
    ROLE_BUCKET_GENERALIST: {"combat": 0.34, "objective": 0.22, "utility": 0.20, "discipline": 0.24},
}


def rebuild_elo_mmr_models(*, db_path=None) -> dict[str, object]:
    """Rebuild canonical facts, ratings, and monthly rankings from scratch."""
    with backend_writer_lock(holder=build_writer_lock_holder("app.elo_mmr_engine rebuild-full")):
        return _run_full_rebuild(db_path=db_path, command_name="rebuild-full", compatibility_mode=False)


def rebuild_elo_mmr_canonical_model(*, db_path=None) -> dict[str, object]:
    """Rebuild only the canonical Elo/MMR fact layer."""
    with backend_writer_lock(holder=build_writer_lock_holder("app.elo_mmr_engine rebuild-canonical")):
        resolved_path, phases = _prepare_operational_storage(db_path=db_path, command_name="rebuild-canonical")
        canonical_fact_layer, phase_summary = _run_logged_phase(
            "canonical-rebuild",
            lambda: rebuild_elo_mmr_canonical_facts(
                db_path=resolved_path,
                application_name_prefix="app.elo_mmr_engine rebuild-canonical",
            ),
        )
        phases.append(phase_summary)
        return {
            "status": "ok",
            "command": "rebuild-canonical",
            "resolved_path": str(resolved_path),
            "canonical_fact_layer": canonical_fact_layer,
            "phases": phases,
        }


def rebuild_elo_mmr_ratings_from_canonical(*, db_path=None) -> dict[str, object]:
    """Rebuild ratings and monthly materialization from existing canonical facts."""
    with backend_writer_lock(holder=build_writer_lock_holder("app.elo_mmr_engine rebuild-ratings")):
        resolved_path, phases = _prepare_operational_storage(db_path=db_path, command_name="rebuild-ratings")
        ratings_result, ratings_phases = _rebuild_ratings_pipeline(
            resolved_path=resolved_path,
            command_name="rebuild-ratings",
        )
        phases.extend(ratings_phases)
        return {
            "status": "ok",
            "command": "rebuild-ratings",
            "resolved_path": str(resolved_path),
            "historical_source_policy": ratings_result["historical_source_policy"],
            "persistent_rating_contract": _build_persistent_rating_contract_metadata(),
            "monthly_ranking_contract": _build_monthly_ranking_contract_metadata(),
            "totals": ratings_result["totals"],
            "latest_month_by_scope": ratings_result["latest_month_by_scope"],
            "phases": phases,
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


def refresh_elo_mmr_monthly_materialization_from_persisted_results(*, db_path=None) -> dict[str, object]:
    """Rebuild monthly rankings/checkpoints from persisted match results only."""
    with backend_writer_lock(holder=build_writer_lock_holder("app.elo_mmr_engine refresh-monthly")):
        resolved_path, phases = _prepare_operational_storage(db_path=db_path, command_name="refresh-monthly")
        match_results, match_result_phase = _run_logged_phase(
            "load-persisted-match-results",
            lambda: list_elo_mmr_match_results(db_path=resolved_path),
        )
        phases.append(match_result_phase)
        if not match_results:
            return {
                "status": "no_data",
                "command": "refresh-monthly",
                "message": "No persisted Elo/MMR match results are available for monthly rematerialization.",
                "totals": {
                    "match_results": 0,
                    "monthly_rankings": 0,
                    "monthly_checkpoints": 0,
                },
                "phases": phases,
            }
        monthly_aggregation, materialize_phase = _run_logged_phase(
            "monthly-materialization",
            lambda: _build_monthly_ranking_materialization(
                match_results=match_results,
                historical_source_policy=_build_historical_source_policy_for_elo(),
            ),
            extra={"match_results": len(match_results)},
        )
        phases.append(materialize_phase)
        _, persist_phase = _run_logged_phase(
            "persist-monthly",
            lambda: replace_elo_mmr_monthly_state(
                monthly_rankings=monthly_aggregation["monthly_rankings"],
                monthly_checkpoints=monthly_aggregation["monthly_checkpoints"],
                db_path=resolved_path,
                application_name="app.elo_mmr_engine refresh-monthly materialize-monthly",
            ),
            extra={"monthly_rankings": len(monthly_aggregation["monthly_rankings"])},
        )
        phases.append(persist_phase)
        return {
            "status": "ok",
            "command": "refresh-monthly",
            "totals": {
                "match_results": len(match_results),
                "monthly_rankings": len(monthly_aggregation["monthly_rankings"]),
                "monthly_checkpoints": len(monthly_aggregation["monthly_checkpoints"]),
            },
            "latest_month_by_scope": {
                checkpoint["scope_key"]: checkpoint["month_key"]
                for checkpoint in monthly_aggregation["monthly_checkpoints"]
            },
            "phases": phases,
        }


def run_historical_maintenance(*, db_path=None) -> dict[str, object]:
    """Run explicit heavyweight historical normalization outside the rebuild hot path."""
    with backend_writer_lock(holder=build_writer_lock_holder("app.elo_mmr_engine historical-maintenance")):
        resolved_path, phases = _prepare_operational_storage(db_path=db_path, command_name="historical-maintenance")
        maintenance_result, maintenance_phase = _run_logged_phase(
            "historical-maintenance",
            lambda: run_historical_storage_maintenance(db_path=resolved_path),
        )
        phases.append(maintenance_phase)
        return {
            "status": "ok",
            "command": "historical-maintenance",
            "resolved_path": str(maintenance_result),
            "phases": phases,
        }


def _run_full_rebuild(*, db_path, command_name: str, compatibility_mode: bool) -> dict[str, object]:
    resolved_path, phases = _prepare_operational_storage(db_path=db_path, command_name=command_name)
    canonical_fact_layer, canonical_phase = _run_logged_phase(
        "canonical-rebuild",
        lambda: rebuild_elo_mmr_canonical_facts(
            db_path=resolved_path,
            application_name_prefix=f"app.elo_mmr_engine {command_name}",
        ),
    )
    phases.append(canonical_phase)
    ratings_result, ratings_phases = _rebuild_ratings_pipeline(
        resolved_path=resolved_path,
        command_name=command_name,
    )
    phases.extend(ratings_phases)
    response = {
        "status": "ok",
        "command": command_name,
        "resolved_path": str(resolved_path),
        "canonical_fact_layer": canonical_fact_layer,
        "historical_source_policy": ratings_result["historical_source_policy"],
        "persistent_rating_contract": _build_persistent_rating_contract_metadata(),
        "monthly_ranking_contract": _build_monthly_ranking_contract_metadata(),
        "totals": ratings_result["totals"],
        "latest_month_by_scope": ratings_result["latest_month_by_scope"],
        "phases": phases,
    }
    if compatibility_mode:
        response["compatibility_alias"] = {
            "requested_command": "rebuild",
            "effective_command": command_name,
        }
    return response


def _prepare_operational_storage(*, db_path, command_name: str) -> tuple[object, list[dict[str, object]]]:
    phases: list[dict[str, object]] = []
    resolved_path, phase = _run_logged_phase(
        "prepare",
        lambda: _prepare_storage_for_command(db_path=db_path, command_name=command_name),
    )
    phases.append(phase)
    return resolved_path, phases


def _prepare_storage_for_command(*, db_path, command_name: str):
    resolved_path = initialize_historical_storage(db_path=db_path)
    initialize_elo_mmr_storage(
        db_path=resolved_path,
        application_name=f"app.elo_mmr_engine {command_name} prepare-storage",
    )
    return resolved_path


def _rebuild_ratings_pipeline(*, resolved_path, command_name: str) -> tuple[dict[str, object], list[dict[str, object]]]:
    phases: list[dict[str, object]] = []
    _, clear_phase = _run_logged_phase(
        "persist-clear",
        lambda: clear_elo_mmr_persisted_state(
            db_path=resolved_path,
            application_name=f"app.elo_mmr_engine {command_name} persist-clear",
        ),
        extra={"source_phase": "ratings-scoring"},
    )
    phases.append(clear_phase)
    scoring_result, scoring_phase = _run_logged_phase(
        "ratings-scoring",
        lambda: _compute_ratings_from_canonical(
            db_path=resolved_path,
            match_results_application_name=f"app.elo_mmr_engine {command_name} incremental-match-results",
        ),
    )
    phases.append(scoring_phase)
    _, rating_phase = _run_logged_phase(
        "persist-player-ratings",
        lambda: persist_elo_mmr_player_ratings(
            player_ratings=scoring_result["player_ratings"],
            db_path=resolved_path,
            application_name=f"app.elo_mmr_engine {command_name} persist-player-ratings",
        ),
        extra={"player_ratings": len(scoring_result["player_ratings"])},
    )
    phases.append(rating_phase)
    _, monthly_phase = _run_logged_phase(
        "persist-monthly",
        lambda: replace_elo_mmr_monthly_state(
            monthly_rankings=scoring_result["monthly_rankings"],
            monthly_checkpoints=scoring_result["monthly_checkpoints"],
            db_path=resolved_path,
            application_name=f"app.elo_mmr_engine {command_name} persist-monthly",
        ),
        extra={"monthly_rankings": len(scoring_result["monthly_rankings"])},
    )
    phases.append(monthly_phase)
    return {
        "historical_source_policy": scoring_result["historical_source_policy"],
        "totals": scoring_result["totals"],
        "latest_month_by_scope": scoring_result["latest_month_by_scope"],
    }, phases


def _compute_ratings_from_canonical(
    *,
    db_path=None,
    match_results_application_name: str = "app.elo_mmr_engine incremental-match-results",
) -> dict[str, object]:
    historical_source_policy = _run_scoring_step(
        "source-policy",
        _build_historical_source_policy_for_elo,
    )
    rcon_read_model = _run_scoring_step(
        "rcon-read-model-selection",
        get_rcon_historical_read_model,
    )
    match_rows = _run_scoring_step(
        "load-canonical-match-rows",
        lambda: list_elo_mmr_canonical_match_rows(db_path=db_path),
    )
    total_grouped_matches = _run_scoring_step(
        "count-canonical-match-groups",
        lambda: _count_grouped_match_rows(match_rows),
        extra={"canonical_rows": len(match_rows)},
    )
    rcon_match_context_cache: dict[tuple[str, str | None, str | None], dict[str, object] | None] = {}

    ratings_by_scope: dict[str, dict[str, dict[str, object]]] = {SCOPE_ALL_SERVERS: {}}
    player_ratings: list[dict[str, object]] = []
    match_result_batch: list[dict[str, object]] = []
    monthly_summaries: dict[tuple[str, str, str], dict[str, object]] = {}
    match_result_count = 0
    scoped_matches_scored = 0

    def flush_match_result_batch(*, force: bool = False) -> None:
        nonlocal match_result_count
        if not match_result_batch or (not force and len(match_result_batch) < MATCH_RESULT_PERSIST_BATCH_SIZE):
            return
        persist_elo_mmr_match_results(
            match_results=match_result_batch,
            db_path=db_path,
            application_name=match_results_application_name,
        )
        match_result_count += len(match_result_batch)
        match_result_batch.clear()

    def score_grouped_matches() -> None:
        nonlocal scoped_matches_scored
        for match_index, match_group in enumerate(_iter_grouped_match_rows(match_rows), start=1):
            if match_index == 1 or match_index % 100 == 0 or match_index == total_grouped_matches:
                _emit_cli_progress(
                    "ratings-scoring-progress",
                    step="score-grouped-matches",
                    processed_matches=match_index - 1,
                    total_matches=total_grouped_matches,
                    persisted_match_results=match_result_count,
                    pending_match_results=len(match_result_batch),
                    **_process_memory_payload(),
                )
            server_scope = match_group["server_slug"]
            ratings_by_scope.setdefault(server_scope, {})
            rcon_match_context = None
            if rcon_read_model is not None:
                cache_key = (
                    str(match_group["server_slug"]),
                    str(match_group.get("ended_at")) if match_group.get("ended_at") is not None else None,
                    str(match_group.get("map_pretty_name") or match_group.get("map_name") or "") or None,
                )
                if cache_key not in rcon_match_context_cache:
                    rcon_match_context_cache[cache_key] = get_rcon_historical_competitive_match_context(
                        server_key=str(match_group["server_slug"]),
                        ended_at=match_group.get("ended_at"),
                        map_name=match_group.get("map_pretty_name") or match_group.get("map_name"),
                    )
                rcon_match_context = rcon_match_context_cache[cache_key]
            for scope_key in (server_scope, SCOPE_ALL_SERVERS):
                scoped_match_results = _score_match_for_scope(
                    match_group=match_group,
                    scope_key=scope_key,
                    ratings_by_scope=ratings_by_scope[scope_key],
                    rcon_match_context=rcon_match_context,
                )
                for result_row in scoped_match_results:
                    _update_monthly_ranking_summary(monthly_summaries, result_row)
                match_result_batch.extend(scoped_match_results)
                scoped_matches_scored += 1
                flush_match_result_batch()
            if match_index % 100 == 0:
                gc.collect()
        flush_match_result_batch(force=True)
        _emit_cli_progress(
            "ratings-scoring-progress",
            step="score-grouped-matches",
            processed_matches=total_grouped_matches,
            total_matches=total_grouped_matches,
            persisted_match_results=match_result_count,
            pending_match_results=len(match_result_batch),
            **_process_memory_payload(),
        )

    _run_scoring_step(
        "score-grouped-matches",
        score_grouped_matches,
        extra={
            "grouped_matches": total_grouped_matches,
            "rcon_read_model": rcon_read_model is not None,
            "match_result_persist_batch_size": MATCH_RESULT_PERSIST_BATCH_SIZE,
            "persistence": "incremental",
        },
    )
    match_rows.clear()
    gc.collect()

    def flatten_player_ratings() -> None:
        for scope_ratings in ratings_by_scope.values():
            player_ratings.extend(scope_ratings.values())

    _run_scoring_step(
        "flatten-player-ratings",
        flatten_player_ratings,
        extra={"scope_count": len(ratings_by_scope), "match_results": match_result_count},
    )

    monthly_aggregation = _run_scoring_step(
        "monthly-materialization",
        lambda: _build_monthly_ranking_materialization_from_summaries(
            monthly_summaries=monthly_summaries,
            historical_source_policy=historical_source_policy,
        ),
        extra={
            "match_results": match_result_count,
            "player_ratings": len(player_ratings),
            "monthly_player_groups": len(monthly_summaries),
            "source": "streaming-score-grouped-matches",
        },
    )
    monthly_summaries.clear()
    gc.collect()
    monthly_rankings = monthly_aggregation["monthly_rankings"]
    monthly_checkpoints = monthly_aggregation["monthly_checkpoints"]
    latest_month_by_scope = {
        checkpoint["scope_key"]: checkpoint["month_key"] for checkpoint in monthly_checkpoints
    }
    return {
        "historical_source_policy": historical_source_policy,
        "player_ratings": player_ratings,
        "match_results": [],
        "monthly_rankings": monthly_rankings,
        "monthly_checkpoints": monthly_checkpoints,
        "latest_month_by_scope": latest_month_by_scope,
        "totals": {
            "matches_scored": scoped_matches_scored,
            "player_ratings": len(player_ratings),
            "match_results": match_result_count,
            "monthly_rankings": len(monthly_rankings),
            "monthly_checkpoints": len(monthly_checkpoints),
        },
    }


def _run_logged_phase(
    phase_name: str,
    runner: Callable[[], object],
    *,
    extra: dict[str, object] | None = None,
) -> tuple[object, dict[str, object]]:
    global _CURRENT_CLI_PHASE
    _CURRENT_CLI_PHASE = phase_name
    _emit_cli_progress("phase-start", phase=phase_name, details=extra)
    started = perf_counter()
    try:
        result = runner()
    except BaseException as exc:
        elapsed_ms = round((perf_counter() - started) * 1000.0, 3)
        _emit_cli_progress(
            "phase-error",
            phase=phase_name,
            elapsed_ms=elapsed_ms,
            details=extra,
            **_exception_payload(exc),
        )
        raise
    elapsed_ms = round((perf_counter() - started) * 1000.0, 3)
    summary = {
        "phase": phase_name,
        "status": "ok",
        "elapsed_ms": elapsed_ms,
    }
    if extra:
        summary["details"] = extra
    _emit_cli_progress("phase-complete", phase=phase_name, elapsed_ms=elapsed_ms, details=extra)
    return result, summary


def _emit_cli_progress(event: str, **payload: object) -> None:
    print(
        json.dumps(
            {
                "event": event,
                "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                **payload,
            },
            ensure_ascii=True,
        ),
        flush=True,
    )
    sys.stdout.flush()


def _run_scoring_step(
    step_name: str,
    runner: Callable[[], object],
    *,
    extra: dict[str, object] | None = None,
):
    _emit_cli_progress("ratings-scoring-step-start", step=step_name, details=extra)
    started = perf_counter()
    try:
        result = runner()
    except BaseException as exc:
        elapsed_ms = round((perf_counter() - started) * 1000.0, 3)
        _emit_cli_progress(
            "ratings-scoring-step-error",
            step=step_name,
            elapsed_ms=elapsed_ms,
            details=extra,
            **_exception_payload(exc),
        )
        raise
    elapsed_ms = round((perf_counter() - started) * 1000.0, 3)
    _emit_cli_progress(
        "ratings-scoring-step-complete",
        step=step_name,
        elapsed_ms=elapsed_ms,
        details=extra,
        result_summary=_summarize_observable_result(result),
    )
    return result


def _run_cli_operation(command_name: str, runner: Callable[[], dict[str, object]]) -> int:
    _emit_cli_progress("rebuild-command-start", command=command_name)
    try:
        result = runner()
    except BaseException as exc:
        exit_code = _exit_code_for_exception(exc)
        _emit_cli_progress(
            "rebuild-terminal",
            command=command_name,
            status="error",
            exit_code=exit_code,
            terminal_phase=_CURRENT_CLI_PHASE,
            **_exception_payload(exc),
        )
        raise
    _emit_cli_progress(
        "rebuild-terminal",
        command=command_name,
        status=str(result.get("status") or "ok"),
        exit_code=0,
        terminal_phase=_CURRENT_CLI_PHASE,
        totals=result.get("totals"),
    )
    print(json.dumps(result, indent=2), flush=True)
    sys.stdout.flush()
    return 0


def _exception_payload(exc: BaseException) -> dict[str, object]:
    payload: dict[str, object] = {
        "exception_type": type(exc).__name__,
        "exception_message": str(exc),
        "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
    }
    if isinstance(exc, SystemExit):
        payload["system_exit_code"] = exc.code
    return payload


def _exit_code_for_exception(exc: BaseException) -> int:
    if isinstance(exc, KeyboardInterrupt):
        return 130
    if isinstance(exc, SystemExit):
        try:
            return int(exc.code)
        except (TypeError, ValueError):
            return 1
    return 1


def _summarize_observable_result(result: object) -> dict[str, object]:
    if isinstance(result, list):
        return {"type": "list", "count": len(result)}
    if isinstance(result, dict):
        summary: dict[str, object] = {"type": "dict", "keys": sorted(result.keys())[:20]}
        if "totals" in result:
            summary["totals"] = result["totals"]
        return summary
    if result is None:
        return {"type": "none"}
    return {"type": type(result).__name__}


def _process_memory_payload() -> dict[str, object]:
    payload: dict[str, object] = {}
    try:
        with open("/proc/self/status", encoding="utf-8") as status_file:
            for line in status_file:
                if line.startswith("VmRSS:"):
                    payload["memory_rss_kb"] = _safe_int(line.split()[1])
                elif line.startswith("VmHWM:"):
                    payload["memory_hwm_kb"] = _safe_int(line.split()[1])
    except OSError:
        return payload
    return payload


def get_elo_mmr_player_payload(*, player_id: str, server_id: str | None) -> dict[str, object] | None:
    """Return one Elo/MMR player profile."""
    return get_elo_mmr_player_profile(
        player_id=player_id,
        scope_key=_normalize_scope_key(server_id),
    )


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for Elo/MMR maintenance."""
    parser = argparse.ArgumentParser(
        description="Operate or inspect the Elo/MMR monthly ranking system.",
    )
    parser.add_argument(
        "mode",
        choices=(
            "rebuild",
            "rebuild-full",
            "rebuild-canonical",
            "rebuild-ratings",
            "refresh-monthly",
            "historical-maintenance",
            "leaderboard",
            "player",
        ),
        help=(
            "rebuild is a compatibility alias for rebuild-full; rebuild-canonical refreshes only the canonical "
            "fact layer; rebuild-ratings recalculates ratings from existing canonical facts; refresh-monthly "
            "rematerializes monthly outputs from persisted match results; historical-maintenance runs explicit "
            "global historical normalization"
        ),
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
        def run_rebuild_alias() -> dict[str, object]:
            result = rebuild_elo_mmr_models()
            result["compatibility_alias"] = {
                "requested_command": "rebuild",
                "effective_command": "rebuild-full",
            }
            return result

        return _run_cli_operation("rebuild", run_rebuild_alias)
    if args.mode == "rebuild-full":
        return _run_cli_operation("rebuild-full", rebuild_elo_mmr_models)
    if args.mode == "rebuild-canonical":
        return _run_cli_operation("rebuild-canonical", rebuild_elo_mmr_canonical_model)
    if args.mode == "rebuild-ratings":
        return _run_cli_operation("rebuild-ratings", rebuild_elo_mmr_ratings_from_canonical)
    if args.mode == "refresh-monthly":
        return _run_cli_operation("refresh-monthly", refresh_elo_mmr_monthly_materialization_from_persisted_results)
    if args.mode == "historical-maintenance":
        return _run_cli_operation("historical-maintenance", run_historical_maintenance)
    if args.mode == "leaderboard":
        print(json.dumps(list_elo_mmr_leaderboard_payload(server_id=args.server_id, limit=args.limit), indent=2))
        return 0
    if not args.player_id:
        parser.error("--player is required in player mode")
    print(json.dumps(get_elo_mmr_player_payload(player_id=args.player_id, server_id=args.server_id), indent=2))
    return 0


def _group_match_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return list(_iter_grouped_match_rows(rows))


def _count_grouped_match_rows(rows: Iterable[dict[str, object]]) -> int:
    previous_key: tuple[str, str] | None = None
    count = 0
    for row in rows:
        key = (str(row["server_slug"]), str(row["external_match_id"]))
        if key != previous_key:
            count += 1
            previous_key = key
    return count


def _iter_grouped_match_rows(rows: Iterable[dict[str, object]]):
    current_key: tuple[str, str] | None = None
    current_players: list[dict[str, object]] = []
    for row in rows:
        key = (str(row["server_slug"]), str(row["external_match_id"]))
        if current_key is not None and key != current_key:
            yield _build_match_group(server_slug=current_key[0], match_id=current_key[1], players=current_players)
            current_players = []
        current_key = key
        current_players.append(row)
    if current_key is not None:
        yield _build_match_group(server_slug=current_key[0], match_id=current_key[1], players=current_players)


def _build_match_group(*, server_slug: str, match_id: str, players: list[dict[str, object]]) -> dict[str, object]:
    first = players[0]
    return {
        "server_slug": server_slug,
        "server_name": first["server_name"],
        "canonical_match_key": first.get("canonical_match_key"),
        "external_match_id": match_id,
        "started_at": first["started_at"],
        "ended_at": first["ended_at"],
        "game_mode": first["game_mode"],
        "allied_score": _safe_int(first["allied_score"]),
        "axis_score": _safe_int(first["axis_score"]),
        "resolved_duration_seconds": _safe_int(first.get("resolved_duration_seconds")),
        "duration_source_status": first.get("duration_source_status"),
        "duration_bucket": first.get("duration_bucket"),
        "player_count": _safe_int(first.get("player_count")),
        "match_capability_status": first.get("match_capability_status"),
        "fact_schema_version": first.get("fact_schema_version"),
        "source_input_version": first.get("source_input_version"),
        "players": players,
    }


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
    duration_bucket = str(match_group.get("duration_bucket") or _classify_duration_bucket(duration_seconds))
    player_count = max(
        _safe_int(match_group.get("player_count")),
        max(len(players), int(rcon_match_context.get("peak_players") or 0)) if rcon_match_context is not None else len(players),
    )
    quality_factor = _build_quality_factor(
        player_count=player_count,
        duration_seconds=duration_seconds,
        has_score=match_group.get("allied_score") is not None and match_group.get("axis_score") is not None,
    )
    quality_bucket = _classify_quality_bucket(quality_factor)
    match_valid = duration_seconds >= MIN_VALID_MATCH_DURATION_SECONDS and player_count >= MIN_VALID_MATCH_PLAYERS
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
        participation_ratio = float(player.get("participation_ratio") or 0.0) or _build_participation_ratio(
            time_seconds=time_seconds,
            duration_seconds=duration_seconds,
        )
        participation_bucket = str(
            player.get("participation_bucket") or _classify_participation_bucket(participation_ratio)
        )
        participation_mode = str(player.get("participation_mode") or duration_mode or CAPABILITY_UNAVAILABLE)
        participation_quality_score = round(
            float(player.get("participation_quality_score") or (participation_ratio * 100.0)),
            3,
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
            signals.append(
                build_signal(
                    "PlayerParticipation",
                    participation_mode if participation_mode in {CAPABILITY_EXACT, CAPABILITY_APPROXIMATE} else CAPABILITY_EXACT,
                    "Uses persisted player time_seconds relative to the resolved match duration.",
                )
            )
        signals.append(
            build_signal(
                "DurationBucket",
                duration_mode if duration_mode in {CAPABILITY_EXACT, CAPABILITY_APPROXIMATE} else CAPABILITY_APPROXIMATE,
                "Persists normalization-ready match length categorization from canonical match facts.",
            )
        )
        signals.append(
            build_signal(
                "ParticipationBucket",
                participation_mode if participation_mode in {CAPABILITY_EXACT, CAPABILITY_APPROXIMATE} else CAPABILITY_APPROXIMATE,
                "Persists player participation quality buckets from canonical player-match facts.",
            )
        )

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

        objective_proxy = _safe_int(player.get("objective_score_proxy")) or (
            _safe_int(player.get("offense")) + _safe_int(player.get("defense"))
        )
        objective_index = round(100.0 * (objective_proxy / max_objective), 3) if max_objective > 0 else 0.0
        signals.append(build_signal("ObjectiveIndex", CAPABILITY_APPROXIMATE, "Approximated from offense and defense scoreboard points because no tactical event feed exists yet."))
        signals.append(build_signal("ObjectiveScoreProxy", CAPABILITY_APPROXIMATE, "Persists offense plus defense as an explicit tactical proxy rather than implying exact tactical telemetry."))

        teamkills = _safe_int(player.get("teamkill_exact_count") or player.get("teamkills"))
        death_type_capability_status = str(player.get("death_type_capability_status") or CAPABILITY_UNAVAILABLE)
        leave_admin_capability_status = str(player.get("leave_admin_capability_status") or CAPABILITY_UNAVAILABLE)
        completion_component = round(participation_ratio * 100.0, 3)
        discipline_index = round(
            max(
                0.0,
                (88.0 - (teamkills * 18.0)) + (0.12 * completion_component),
            ),
            3,
        )
        signals.append(build_signal("DisciplineIndex", CAPABILITY_APPROXIMATE, "Uses exact teamkill counts plus participation as an honest proxy because leave, kick and admin telemetry remain unavailable."))
        signals.append(
            build_signal(
                "DeathTypeClassification",
                death_type_capability_status if death_type_capability_status in {CAPABILITY_EXACT, CAPABILITY_APPROXIMATE} else CAPABILITY_UNAVAILABLE,
                "Approximate summary-backed death classification is available for combat and friendly-fire proxy categories; redeploy, suicide and menu-exit exact types remain unavailable.",
            )
        )
        signals.append(
            build_signal(
                "LeaveAdminLineage",
                leave_admin_capability_status if leave_admin_capability_status in {CAPABILITY_EXACT, CAPABILITY_APPROXIMATE} else CAPABILITY_UNAVAILABLE,
                "No exact disconnect, kick, ban or admin-action event family is persisted yet.",
            )
        )
        leadership_index = None
        signals.append(build_signal("LeadershipIndex", CAPABILITY_UNAVAILABLE, "No leadership-specific telemetry is stored in the repository yet."))

        role_bucket = str(player.get("role_primary") or _resolve_role_bucket(player))
        role_bucket_mode = str(player.get("role_primary_mode") or CAPABILITY_APPROXIMATE)
        signals.append(
            build_signal(
                "role_bucket",
                role_bucket_mode if role_bucket_mode in {CAPABILITY_EXACT, CAPABILITY_APPROXIMATE} else CAPABILITY_APPROXIMATE,
                "Uses persisted role-primary normalization input when available; current fallback remains scoreboard-axis approximation because literal role assignment events are unavailable.",
            )
        )
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
        normalization_bucket_key = str(player.get("normalization_bucket_key") or "")
        normalization_fallback_reason = player.get("normalization_fallback_reason")
        combat_contribution = round(weights["combat"] * _build_centered_modifier_edge(combat_index, participation_ratio=1.0), 4)
        objective_contribution = round(weights["objective"] * _build_centered_modifier_edge(objective_index, participation_ratio=1.0), 4)
        utility_contribution = round(weights["utility"] * _build_centered_modifier_edge(utility_index, participation_ratio=1.0), 4)
        survival_discipline_contribution = round(weights["discipline"] * _build_centered_modifier_edge(discipline_index, participation_ratio=1.0), 4)
        exact_component_contribution = round(combat_contribution + utility_contribution, 4)
        proxy_component_contribution = round(objective_contribution + survival_discipline_contribution, 4)
        match_impact = round(
            max(-1.0, min(1.0, exact_component_contribution + proxy_component_contribution)),
            4,
        )
        if not player_match_valid:
            delta_mmr = 0.0
            match_score = 0.0
            expected_result = 0.0
            actual_result = 0.0
            won_score = 0.0
            own_team_average_mmr = 0.0
            enemy_team_average_mmr = 0.0
            margin_boost = 0.0
            outcome_adjusted = 0.0
            elo_core_delta = 0.0
            performance_modifier_delta = 0.0
            proxy_modifier_delta = 0.0
        else:
            own_team_average_mmr = _resolve_own_team_average_rating(
                stable_player_key=stable_player_key,
                team_side=team_side,
                players=players,
                rating_before_by_player=rating_before_by_player,
            )
            enemy_team_average_mmr = _resolve_opponent_average_rating(
                stable_player_key=stable_player_key,
                team_side=team_side,
                players=players,
                rating_before_by_player=rating_before_by_player,
            )
            expected_result = _build_expected_result(
                player_rating=own_team_average_mmr,
                opponent_average_rating=enemy_team_average_mmr,
            )
            won_score = _build_won_score(team_outcome=team_outcome)
            actual_result = won_score
            margin_boost = _build_margin_boost(
                team_outcome=team_outcome,
                allied_score=_safe_int(match_group.get("allied_score")),
                axis_score=_safe_int(match_group.get("axis_score")),
            )
            outcome_adjusted = _build_outcome_adjusted(
                won_score=won_score,
                expected_win=expected_result,
                margin_boost=margin_boost,
            )
            elo_core_delta = round(
                ELO_K_FACTOR * quality_factor * 0.80 * outcome_adjusted,
                3,
            )
            performance_modifier_delta = round(
                ELO_K_FACTOR * quality_factor * 0.20 * exact_component_contribution,
                3,
            )
            proxy_modifier_delta = round(
                ELO_K_FACTOR * quality_factor * 0.20 * proxy_component_contribution,
                3,
            )
            delta_mmr = round(elo_core_delta + performance_modifier_delta + proxy_modifier_delta, 3)
            combined_rating_signal = max(-1.0, min(1.0, (0.80 * outcome_adjusted) + (0.20 * match_impact)))
            match_score = round((50.0 + (combined_rating_signal * 50.0)) * quality_factor, 3)
            signals.append(build_signal("OutcomeAdjusted", CAPABILITY_EXACT, "Uses explicit ExpectedWin, won score and bounded margin boost."))
            signals.append(build_signal("MatchImpact", CAPABILITY_APPROXIMATE, "Uses bounded role-adjusted combat, objective, utility and survival-discipline contributions with exact and proxy source separation."))
            signals.append(build_signal("DeltaMMR", CAPABILITY_APPROXIMATE, "Uses DeltaMMR = K * Q * (0.80 * OutcomeAdjusted + 0.20 * MatchImpact) with exact and proxy contribution split persisted per row."))
            signals.append(build_signal("MatchScore", CAPABILITY_APPROXIMATE, "Uses the bounded persistent-rating signal mapped to a reviewable 0-100 scale."))
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
                "role_bucket_mode": role_bucket_mode,
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
                "canonical_fact_capability_status": player.get("fact_capability_status", CAPABILITY_UNAVAILABLE),
                "identity_capability_status": player.get("identity_capability_status", CAPABILITY_UNAVAILABLE),
                "time_seconds": time_seconds,
                "participation_ratio": participation_ratio,
                "participation_bucket": participation_bucket,
                "participation_mode": participation_mode,
                "participation_quality_score": participation_quality_score,
                "strength_of_schedule_match": strength_of_schedule_match,
                "team_outcome": team_outcome,
                "own_team_average_mmr": own_team_average_mmr,
                "enemy_team_average_mmr": enemy_team_average_mmr,
                "expected_result": expected_result,
                "actual_result": actual_result,
                "won_score": won_score,
                "margin_boost": margin_boost,
                "outcome_adjusted": outcome_adjusted,
                "match_impact": match_impact,
                "combat_contribution": combat_contribution,
                "objective_contribution": objective_contribution,
                "utility_contribution": utility_contribution,
                "survival_discipline_contribution": survival_discipline_contribution,
                "exact_component_contribution": exact_component_contribution,
                "proxy_component_contribution": proxy_component_contribution,
                "normalization_bucket_key": normalization_bucket_key,
                "normalization_fallback_bucket_key": player.get("normalization_fallback_bucket_key"),
                "normalization_fallback_reason": normalization_fallback_reason,
                "elo_core_delta": elo_core_delta,
                "performance_modifier_delta": performance_modifier_delta,
                "proxy_modifier_delta": proxy_modifier_delta,
                "match_duration_seconds": duration_seconds,
                "duration_source_status": duration_mode,
                "duration_bucket": duration_bucket,
                "player_count": player_count,
                "objective_score_proxy": objective_proxy,
                "objective_score_proxy_mode": CAPABILITY_APPROXIMATE,
                "kills_per_minute": round(float(player.get("kills_per_minute") or 0.0), 3),
                "combat_per_minute": round(float(player.get("combat_per_minute") or 0.0), 3),
                "support_per_minute": round(float(player.get("support_per_minute") or 0.0), 3),
                "objective_proxy_per_minute": round(float(player.get("objective_proxy_per_minute") or 0.0), 3),
                "discipline_capability_status": player.get("discipline_capability_status", CAPABILITY_UNAVAILABLE),
                "leave_admin_capability_status": leave_admin_capability_status,
                "death_type_capability_status": death_type_capability_status,
                "teamkill_exact_count": _safe_int(player.get("teamkill_exact_count")),
                "tactical_event_count": _safe_int(player.get("tactical_event_count")),
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
        exact_duration_match_count = sum(
            1 for row in rows if row.get("duration_source_status") == CAPABILITY_EXACT
        )
        approximate_duration_match_count = sum(
            1 for row in rows if row.get("duration_source_status") == CAPABILITY_APPROXIMATE
        )
        full_participation_match_count = sum(
            1 for row in valid_rows if row.get("participation_bucket") == PARTICIPATION_BUCKET_FULL
        )
        core_participation_match_count = sum(
            1 for row in valid_rows if row.get("participation_bucket") == PARTICIPATION_BUCKET_CORE
        )
        high_quality_match_count = sum(
            1 for row in valid_rows if row.get("quality_bucket") == QUALITY_BUCKET_HIGH
        )
        medium_quality_match_count = sum(
            1 for row in valid_rows if row.get("quality_bucket") == QUALITY_BUCKET_MEDIUM
        )
        low_quality_match_count = sum(
            1 for row in valid_rows if row.get("quality_bucket") == QUALITY_BUCKET_LOW
        )
        avg_participation_ratio = round(
            sum(float(row.get("participation_ratio") or 0.0) for row in rows) / max(1, len(rows)),
            3,
        )
        avg_participation_quality_score = round(
            sum(float(row.get("participation_quality_score") or 0.0) for row in rows) / max(1, len(rows)),
            3,
        )
        avg_tactical_event_count = round(
            sum(float(row.get("tactical_event_count") or 0.0) for row in rows) / max(1, len(rows)),
            3,
        )
        avg_teamkill_exact_count = round(
            sum(float(row.get("teamkill_exact_count") or 0.0) for row in rows) / max(1, len(rows)),
            3,
        )
        strength_of_schedule = round(
            sum(float(row.get("strength_of_schedule_match") or 0.0) for row in valid_rows) / max(1, len(valid_rows)),
            3,
        )
        avg_kills_per_minute = round(
            sum(float(row.get("kills_per_minute") or 0.0) for row in valid_rows) / max(1, len(valid_rows)),
            3,
        )
        avg_combat_per_minute = round(
            sum(float(row.get("combat_per_minute") or 0.0) for row in valid_rows) / max(1, len(valid_rows)),
            3,
        )
        avg_support_per_minute = round(
            sum(float(row.get("support_per_minute") or 0.0) for row in valid_rows) / max(1, len(valid_rows)),
            3,
        )
        avg_objective_proxy_per_minute = round(
            sum(float(row.get("objective_proxy_per_minute") or 0.0) for row in valid_rows) / max(1, len(valid_rows)),
            3,
        )
        consistency = _build_consistency_score(valid_rows)
        activity = _build_activity_score(valid_rows, total_time_seconds)
        role_counts: dict[str, int] = defaultdict(int)
        for row in valid_rows or rows:
            role_counts[str(row.get("role_bucket") or ROLE_BUCKET_GENERALIST)] += 1
        role_primary = max(role_counts.items(), key=lambda item: item[1])[0] if role_counts else ROLE_BUCKET_GENERALIST
        role_primary_mode = (
            CAPABILITY_EXACT
            if valid_rows and all(row.get("role_bucket_mode") == CAPABILITY_EXACT for row in valid_rows)
            else CAPABILITY_APPROXIMATE
            if role_counts
            else CAPABILITY_UNAVAILABLE
        )
        normalization_fallback_used = any(bool(row.get("normalization_fallback_reason")) for row in rows)
        comparison_path = "role-all-parent-fallback" if normalization_fallback_used else "role-primary-bucket"
        comparison_bucket_key = next(
            (
                str(
                    row.get("normalization_fallback_bucket_key")
                    or row.get("normalization_bucket_key")
                    or ""
                )
                for row in rows
                if row.get("normalization_bucket_key")
            ),
            "",
        )
        role_bucket_sample_sufficient = not normalization_fallback_used
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
            and avg_participation_quality_score >= 45.0
        )
        eligibility_reason = _build_monthly_eligibility_reason(
            valid_match_count=len(valid_rows),
            total_time_seconds=total_time_seconds,
            avg_participation_ratio=avg_participation_ratio,
            avg_participation_quality_score=avg_participation_quality_score,
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
                        build_signal("DurationBucket", CAPABILITY_APPROXIMATE, "Duration buckets are materialized from exact timestamps when present or approximate duration fallbacks otherwise."),
                        build_signal("ParticipationBucket", CAPABILITY_APPROXIMATE, "Participation quality is explicit, but can inherit approximate duration boundaries when timestamps are missing."),
                        build_signal("MonthlyEligibility", CAPABILITY_EXACT, "Uses persisted valid-match count, playtime, participation ratio and participation quality thresholds."),
                        build_signal("MonthlyRoleComparison", role_primary_mode if role_primary_mode in {CAPABILITY_EXACT, CAPABILITY_APPROXIMATE} else CAPABILITY_UNAVAILABLE, "Uses role-primary bucket comparison when bucket coverage is sufficient and falls back to role-all parent buckets otherwise."),
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
                    "canonical_fact_schema_version": rows[-1].get("fact_schema_version"),
                    "canonical_source_input_version": rows[-1].get("source_input_version"),
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
                    "avg_kills_per_minute": avg_kills_per_minute,
                    "avg_combat_per_minute": avg_combat_per_minute,
                    "avg_support_per_minute": avg_support_per_minute,
                    "avg_objective_proxy_per_minute": avg_objective_proxy_per_minute,
                    "avg_participation_ratio": avg_participation_ratio,
                    "avg_participation_quality_score": avg_participation_quality_score,
                    "avg_tactical_event_count": avg_tactical_event_count,
                    "avg_teamkill_exact_count": avg_teamkill_exact_count,
                    "exact_duration_match_count": exact_duration_match_count,
                    "approximate_duration_match_count": approximate_duration_match_count,
                    "full_participation_match_count": full_participation_match_count,
                    "core_participation_match_count": core_participation_match_count,
                    "high_quality_match_count": high_quality_match_count,
                    "medium_quality_match_count": medium_quality_match_count,
                    "low_quality_match_count": low_quality_match_count,
                    "role_primary": role_primary,
                    "role_primary_mode": role_primary_mode,
                    "comparison_path": comparison_path,
                    "comparison_bucket_key": comparison_bucket_key,
                    "role_bucket_sample_sufficient": role_bucket_sample_sufficient,
                    "normalization_fallback_used": normalization_fallback_used,
                    "minimum_participation_quality_threshold": 45.0,
                    "discipline_capability_status": _most_common_status(rows, "discipline_capability_status"),
                    "leave_admin_capability_status": _most_common_status(rows, "leave_admin_capability_status"),
                    "death_type_capability_status": _most_common_status(rows, "death_type_capability_status"),
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


def _update_monthly_ranking_summary(
    summaries: dict[tuple[str, str, str], dict[str, object]],
    row: dict[str, object],
) -> None:
    key = (str(row["scope_key"]), str(row["month_key"]), str(row["stable_player_key"]))
    summary = summaries.get(key)
    if summary is None:
        summary = {
            "scope_key": key[0],
            "month_key": key[1],
            "stable_player_key": key[2],
            "player_name": row["player_name"],
            "steam_id": row.get("steam_id"),
            "baseline_mmr": round(float(row["mmr_before"]), 3),
            "current_mmr": round(float(row["mmr_after"]), 3),
            "fact_schema_version": row.get("fact_schema_version"),
            "source_input_version": row.get("source_input_version"),
            "total_matches": 0,
            "valid_matches": 0,
            "total_time_seconds": 0,
            "penalty_points": 0.0,
            "capability_exact_sum": 0.0,
            "capability_approximate_sum": 0.0,
            "capability_unavailable_sum": 0.0,
            "valid_match_score_sum": 0.0,
            "valid_match_score_sum_squares": 0.0,
            "elo_core_gain": 0.0,
            "performance_modifier_gain": 0.0,
            "proxy_modifier_gain": 0.0,
            "exact_duration_match_count": 0,
            "approximate_duration_match_count": 0,
            "full_participation_match_count": 0,
            "core_participation_match_count": 0,
            "high_quality_match_count": 0,
            "medium_quality_match_count": 0,
            "low_quality_match_count": 0,
            "participation_ratio_sum": 0.0,
            "participation_quality_score_sum": 0.0,
            "tactical_event_count_sum": 0.0,
            "teamkill_exact_count_sum": 0.0,
            "strength_of_schedule_sum": 0.0,
            "kills_per_minute_sum": 0.0,
            "combat_per_minute_sum": 0.0,
            "support_per_minute_sum": 0.0,
            "objective_proxy_per_minute_sum": 0.0,
            "all_role_counts": defaultdict(int),
            "valid_role_counts": defaultdict(int),
            "valid_role_exact_count": 0,
            "normalization_fallback_used": False,
            "comparison_bucket_key": "",
            "discipline_capability_status_counts": defaultdict(int),
            "leave_admin_capability_status_counts": defaultdict(int),
            "death_type_capability_status_counts": defaultdict(int),
        }
        summaries[key] = summary

    summary["total_matches"] = int(summary["total_matches"]) + 1
    summary["player_name"] = row["player_name"]
    summary["steam_id"] = row.get("steam_id")
    summary["current_mmr"] = round(float(row["mmr_after"]), 3)
    summary["fact_schema_version"] = row.get("fact_schema_version")
    summary["source_input_version"] = row.get("source_input_version")
    summary["total_time_seconds"] = int(summary["total_time_seconds"]) + int(row["time_seconds"] or 0)
    summary["penalty_points"] = float(summary["penalty_points"]) + float(row["penalty_points"])
    capabilities = row["capabilities"]
    summary["capability_exact_sum"] = float(summary["capability_exact_sum"]) + float(capabilities["exact_ratio"])
    summary["capability_approximate_sum"] = float(summary["capability_approximate_sum"]) + float(capabilities["approximate_ratio"])
    summary["capability_unavailable_sum"] = float(summary["capability_unavailable_sum"]) + float(capabilities["unavailable_ratio"])
    summary["elo_core_gain"] = float(summary["elo_core_gain"]) + float(row.get("elo_core_delta") or 0.0)
    summary["performance_modifier_gain"] = float(summary["performance_modifier_gain"]) + float(row.get("performance_modifier_delta") or 0.0)
    summary["proxy_modifier_gain"] = float(summary["proxy_modifier_gain"]) + float(row.get("proxy_modifier_delta") or 0.0)
    summary["participation_ratio_sum"] = float(summary["participation_ratio_sum"]) + float(row.get("participation_ratio") or 0.0)
    summary["participation_quality_score_sum"] = float(summary["participation_quality_score_sum"]) + float(
        row.get("participation_quality_score") or 0.0
    )
    summary["tactical_event_count_sum"] = float(summary["tactical_event_count_sum"]) + float(row.get("tactical_event_count") or 0.0)
    summary["teamkill_exact_count_sum"] = float(summary["teamkill_exact_count_sum"]) + float(row.get("teamkill_exact_count") or 0.0)

    if row.get("duration_source_status") == CAPABILITY_EXACT:
        summary["exact_duration_match_count"] = int(summary["exact_duration_match_count"]) + 1
    if row.get("duration_source_status") == CAPABILITY_APPROXIMATE:
        summary["approximate_duration_match_count"] = int(summary["approximate_duration_match_count"]) + 1
    role_bucket = str(row.get("role_bucket") or ROLE_BUCKET_GENERALIST)
    summary["all_role_counts"][role_bucket] += 1
    if row["match_valid"]:
        if row.get("quality_bucket") == QUALITY_BUCKET_HIGH:
            summary["high_quality_match_count"] = int(summary["high_quality_match_count"]) + 1
        if row.get("quality_bucket") == QUALITY_BUCKET_MEDIUM:
            summary["medium_quality_match_count"] = int(summary["medium_quality_match_count"]) + 1
        if row.get("quality_bucket") == QUALITY_BUCKET_LOW:
            summary["low_quality_match_count"] = int(summary["low_quality_match_count"]) + 1
        summary["valid_matches"] = int(summary["valid_matches"]) + 1
        match_score = float(row["match_score"])
        summary["valid_match_score_sum"] = float(summary["valid_match_score_sum"]) + match_score
        summary["valid_match_score_sum_squares"] = float(summary["valid_match_score_sum_squares"]) + (match_score * match_score)
        summary["strength_of_schedule_sum"] = float(summary["strength_of_schedule_sum"]) + float(
            row.get("strength_of_schedule_match") or 0.0
        )
        summary["kills_per_minute_sum"] = float(summary["kills_per_minute_sum"]) + float(row.get("kills_per_minute") or 0.0)
        summary["combat_per_minute_sum"] = float(summary["combat_per_minute_sum"]) + float(row.get("combat_per_minute") or 0.0)
        summary["support_per_minute_sum"] = float(summary["support_per_minute_sum"]) + float(row.get("support_per_minute") or 0.0)
        summary["objective_proxy_per_minute_sum"] = float(summary["objective_proxy_per_minute_sum"]) + float(
            row.get("objective_proxy_per_minute") or 0.0
        )
        summary["valid_role_counts"][role_bucket] += 1
        if row.get("role_bucket_mode") == CAPABILITY_EXACT:
            summary["valid_role_exact_count"] = int(summary["valid_role_exact_count"]) + 1
        if row.get("participation_bucket") == PARTICIPATION_BUCKET_FULL:
            summary["full_participation_match_count"] = int(summary["full_participation_match_count"]) + 1
        if row.get("participation_bucket") == PARTICIPATION_BUCKET_CORE:
            summary["core_participation_match_count"] = int(summary["core_participation_match_count"]) + 1

    if row.get("normalization_fallback_reason"):
        summary["normalization_fallback_used"] = True
    if not summary["comparison_bucket_key"] and row.get("normalization_bucket_key"):
        summary["comparison_bucket_key"] = str(
            row.get("normalization_fallback_bucket_key") or row.get("normalization_bucket_key") or ""
        )
    for field_name in (
        "discipline_capability_status",
        "leave_admin_capability_status",
        "death_type_capability_status",
    ):
        summary[f"{field_name}_counts"][str(row.get(field_name) or CAPABILITY_UNAVAILABLE)] += 1


def _build_monthly_rankings_from_summaries(
    summaries: dict[tuple[str, str, str], dict[str, object]],
) -> list[dict[str, object]]:
    rankings: list[dict[str, object]] = []
    grouped_by_scope_month: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for summary in summaries.values():
        scope_key = str(summary["scope_key"])
        month_key = str(summary["month_key"])
        total_matches = int(summary["total_matches"])
        valid_matches = int(summary["valid_matches"])
        exact_ratio = round(float(summary["capability_exact_sum"]) / max(1, total_matches), 3)
        approximate_ratio = round(float(summary["capability_approximate_sum"]) / max(1, total_matches), 3)
        unavailable_ratio = round(float(summary["capability_unavailable_sum"]) / max(1, total_matches), 3)
        accuracy_mode = "partial" if unavailable_ratio > 0 else "approximate" if approximate_ratio > 0 else "exact"
        avg_match_score = round(float(summary["valid_match_score_sum"]) / max(1, valid_matches), 3)
        current_mmr = round(float(summary["current_mmr"]), 3)
        baseline_mmr = round(float(summary["baseline_mmr"]), 3)
        mmr_gain = round(current_mmr - baseline_mmr, 3)
        elo_core_gain = round(float(summary["elo_core_gain"]), 3)
        performance_modifier_gain = round(float(summary["performance_modifier_gain"]), 3)
        proxy_modifier_gain = round(float(summary["proxy_modifier_gain"]), 3)
        avg_participation_ratio = round(float(summary["participation_ratio_sum"]) / max(1, total_matches), 3)
        avg_participation_quality_score = round(float(summary["participation_quality_score_sum"]) / max(1, total_matches), 3)
        avg_tactical_event_count = round(float(summary["tactical_event_count_sum"]) / max(1, total_matches), 3)
        avg_teamkill_exact_count = round(float(summary["teamkill_exact_count_sum"]) / max(1, total_matches), 3)
        strength_of_schedule = round(float(summary["strength_of_schedule_sum"]) / max(1, valid_matches), 3)
        avg_kills_per_minute = round(float(summary["kills_per_minute_sum"]) / max(1, valid_matches), 3)
        avg_combat_per_minute = round(float(summary["combat_per_minute_sum"]) / max(1, valid_matches), 3)
        avg_support_per_minute = round(float(summary["support_per_minute_sum"]) / max(1, valid_matches), 3)
        avg_objective_proxy_per_minute = round(float(summary["objective_proxy_per_minute_sum"]) / max(1, valid_matches), 3)
        consistency = _build_consistency_score_from_summary(summary)
        total_time_seconds = int(summary["total_time_seconds"])
        activity = _build_activity_score_from_counts(valid_matches, total_time_seconds)
        role_counts = summary["valid_role_counts"] if valid_matches else summary["all_role_counts"]
        role_primary = max(role_counts.items(), key=lambda item: item[1])[0] if role_counts else ROLE_BUCKET_GENERALIST
        role_primary_mode = (
            CAPABILITY_EXACT
            if valid_matches and int(summary["valid_role_exact_count"]) == valid_matches
            else CAPABILITY_APPROXIMATE
            if role_counts
            else CAPABILITY_UNAVAILABLE
        )
        normalization_fallback_used = bool(summary["normalization_fallback_used"])
        comparison_path = "role-all-parent-fallback" if normalization_fallback_used else "role-primary-bucket"
        role_bucket_sample_sufficient = not normalization_fallback_used
        confidence = round(
            min(
                100.0,
                (valid_matches / MONTHLY_MIN_VALID_MATCHES) * 35.0
                + (total_time_seconds / MONTHLY_MIN_TIME_SECONDS) * 30.0
                + (avg_participation_ratio * 20.0)
                + (exact_ratio * 15.0),
            ),
            3,
        )
        eligible = (
            valid_matches >= MONTHLY_MIN_VALID_MATCHES
            and total_time_seconds >= MONTHLY_MIN_TIME_SECONDS
            and avg_participation_ratio >= MONTHLY_MIN_AVG_PARTICIPATION_RATIO
            and avg_participation_quality_score >= 45.0
        )
        eligibility_reason = _build_monthly_eligibility_reason(
            valid_match_count=valid_matches,
            total_time_seconds=total_time_seconds,
            avg_participation_ratio=avg_participation_ratio,
            avg_participation_quality_score=avg_participation_quality_score,
        )
        grouped_by_scope_month[(scope_key, month_key)].append(
            {
                "scope_key": scope_key,
                "month_key": month_key,
                "stable_player_key": summary["stable_player_key"],
                "player_name": summary["player_name"],
                "steam_id": summary.get("steam_id"),
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
                "penalty_points": round(float(summary["penalty_points"]), 3),
                "monthly_rank_score": 0.0,
                "valid_matches": valid_matches,
                "total_matches": total_matches,
                "total_time_seconds": total_time_seconds,
                "avg_participation_ratio": avg_participation_ratio,
                "eligible": eligible,
                "eligibility_reason": eligibility_reason,
                "accuracy_mode": accuracy_mode,
                "capabilities": _build_monthly_capabilities(
                    accuracy_mode=accuracy_mode,
                    exact_ratio=exact_ratio,
                    approximate_ratio=approximate_ratio,
                    unavailable_ratio=unavailable_ratio,
                    role_primary_mode=role_primary_mode,
                ),
                "component_scores": _build_monthly_component_scores(
                    summary=summary,
                    avg_match_score=avg_match_score,
                    mmr_gain=mmr_gain,
                    elo_core_gain=elo_core_gain,
                    performance_modifier_gain=performance_modifier_gain,
                    proxy_modifier_gain=proxy_modifier_gain,
                    strength_of_schedule=strength_of_schedule,
                    consistency=consistency,
                    activity=activity,
                    confidence=confidence,
                    avg_kills_per_minute=avg_kills_per_minute,
                    avg_combat_per_minute=avg_combat_per_minute,
                    avg_support_per_minute=avg_support_per_minute,
                    avg_objective_proxy_per_minute=avg_objective_proxy_per_minute,
                    avg_participation_ratio=avg_participation_ratio,
                    avg_participation_quality_score=avg_participation_quality_score,
                    avg_tactical_event_count=avg_tactical_event_count,
                    avg_teamkill_exact_count=avg_teamkill_exact_count,
                    role_primary=role_primary,
                    role_primary_mode=role_primary_mode,
                    comparison_path=comparison_path,
                    role_bucket_sample_sufficient=role_bucket_sample_sufficient,
                    normalization_fallback_used=normalization_fallback_used,
                ),
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


def _build_consistency_score_from_summary(summary: dict[str, object]) -> float:
    valid_count = int(summary["valid_matches"])
    if valid_count <= 1:
        return 100.0 if valid_count else 0.0
    average = float(summary["valid_match_score_sum"]) / valid_count
    if average <= 0:
        return 0.0
    variance = max(0.0, (float(summary["valid_match_score_sum_squares"]) / valid_count) - (average * average))
    return round(100.0 * (1.0 - min(1.0, sqrt(variance) / max(average, 1.0))), 3)


def _build_activity_score_from_counts(valid_match_count: int, total_time_seconds: int) -> float:
    match_component = min(1.0, valid_match_count / MONTHLY_ACTIVITY_TARGET_MATCHES)
    hour_component = min(1.0, (total_time_seconds / 3600.0) / MONTHLY_ACTIVITY_TARGET_HOURS)
    return round(((0.6 * match_component) + (0.4 * hour_component)) * 100.0, 3)


def _most_common_status_from_counts(counts: dict[str, int]) -> str:
    if not counts:
        return CAPABILITY_UNAVAILABLE
    return max(counts.items(), key=lambda item: item[1])[0]


def _build_monthly_capabilities(
    *,
    accuracy_mode: str,
    exact_ratio: float,
    approximate_ratio: float,
    unavailable_ratio: float,
    role_primary_mode: str,
) -> dict[str, object]:
    return {
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
            build_signal("DurationBucket", CAPABILITY_APPROXIMATE, "Duration buckets are materialized from exact timestamps when present or approximate duration fallbacks otherwise."),
            build_signal("ParticipationBucket", CAPABILITY_APPROXIMATE, "Participation quality is explicit, but can inherit approximate duration boundaries when timestamps are missing."),
            build_signal("MonthlyEligibility", CAPABILITY_EXACT, "Uses persisted valid-match count, playtime, participation ratio and participation quality thresholds."),
            build_signal(
                "MonthlyRoleComparison",
                role_primary_mode if role_primary_mode in {CAPABILITY_EXACT, CAPABILITY_APPROXIMATE} else CAPABILITY_UNAVAILABLE,
                "Uses role-primary bucket comparison when bucket coverage is sufficient and falls back to role-all parent buckets otherwise.",
            ),
        ],
    }


def _build_monthly_component_scores(
    *,
    summary: dict[str, object],
    avg_match_score: float,
    mmr_gain: float,
    elo_core_gain: float,
    performance_modifier_gain: float,
    proxy_modifier_gain: float,
    strength_of_schedule: float,
    consistency: float,
    activity: float,
    confidence: float,
    avg_kills_per_minute: float,
    avg_combat_per_minute: float,
    avg_support_per_minute: float,
    avg_objective_proxy_per_minute: float,
    avg_participation_ratio: float,
    avg_participation_quality_score: float,
    avg_tactical_event_count: float,
    avg_teamkill_exact_count: float,
    role_primary: str,
    role_primary_mode: str,
    comparison_path: str,
    role_bucket_sample_sufficient: bool,
    normalization_fallback_used: bool,
) -> dict[str, object]:
    return {
        "model_version": MONTHLY_RANKING_MODEL_VERSION,
        "ranking_formula_version": MONTHLY_RANKING_FORMULA_VERSION,
        "persistent_rating_model_version": PERSISTENT_RATING_MODEL_VERSION,
        "persistent_rating_formula_version": PERSISTENT_RATING_FORMULA_VERSION,
        "persistent_rating_contract_version": PERSISTENT_RATING_CONTRACT_VERSION,
        "match_result_contract_version": MATCH_RESULT_CONTRACT_VERSION,
        "monthly_ranking_contract_version": MONTHLY_RANKING_CONTRACT_VERSION,
        "canonical_fact_schema_version": summary.get("fact_schema_version"),
        "canonical_source_input_version": summary.get("source_input_version"),
        "avg_match_score": avg_match_score,
        "mmr_gain_raw": mmr_gain,
        "elo_core_gain": elo_core_gain,
        "performance_modifier_gain": performance_modifier_gain,
        "proxy_modifier_gain": proxy_modifier_gain,
        "competitive_gain": round(elo_core_gain + (0.25 * performance_modifier_gain) + (0.10 * proxy_modifier_gain), 3),
        "strength_of_schedule": strength_of_schedule,
        "consistency": consistency,
        "activity": activity,
        "confidence": confidence,
        "avg_kills_per_minute": avg_kills_per_minute,
        "avg_combat_per_minute": avg_combat_per_minute,
        "avg_support_per_minute": avg_support_per_minute,
        "avg_objective_proxy_per_minute": avg_objective_proxy_per_minute,
        "avg_participation_ratio": avg_participation_ratio,
        "avg_participation_quality_score": avg_participation_quality_score,
        "avg_tactical_event_count": avg_tactical_event_count,
        "avg_teamkill_exact_count": avg_teamkill_exact_count,
        "exact_duration_match_count": int(summary["exact_duration_match_count"]),
        "approximate_duration_match_count": int(summary["approximate_duration_match_count"]),
        "full_participation_match_count": int(summary["full_participation_match_count"]),
        "core_participation_match_count": int(summary["core_participation_match_count"]),
        "high_quality_match_count": int(summary["high_quality_match_count"]),
        "medium_quality_match_count": int(summary["medium_quality_match_count"]),
        "low_quality_match_count": int(summary["low_quality_match_count"]),
        "role_primary": role_primary,
        "role_primary_mode": role_primary_mode,
        "comparison_path": comparison_path,
        "comparison_bucket_key": str(summary["comparison_bucket_key"]),
        "role_bucket_sample_sufficient": role_bucket_sample_sufficient,
        "normalization_fallback_used": normalization_fallback_used,
        "minimum_participation_quality_threshold": 45.0,
        "discipline_capability_status": _most_common_status_from_counts(summary["discipline_capability_status_counts"]),
        "leave_admin_capability_status": _most_common_status_from_counts(summary["leave_admin_capability_status_counts"]),
        "death_type_capability_status": _most_common_status_from_counts(summary["death_type_capability_status_counts"]),
        "penalty_points": round(float(summary["penalty_points"]), 3),
    }


def _build_monthly_ranking_materialization(
    *,
    match_results: list[dict[str, object]],
    historical_source_policy: dict[str, object],
) -> dict[str, list[dict[str, object]]]:
    monthly_rankings = _build_monthly_rankings(match_results)
    return _build_monthly_ranking_materialization_from_rankings(
        monthly_rankings=monthly_rankings,
        historical_source_policy=historical_source_policy,
    )


def _build_monthly_ranking_materialization_from_summaries(
    *,
    monthly_summaries: dict[tuple[str, str, str], dict[str, object]],
    historical_source_policy: dict[str, object],
) -> dict[str, list[dict[str, object]]]:
    monthly_rankings = _build_monthly_rankings_from_summaries(monthly_summaries)
    return _build_monthly_ranking_materialization_from_rankings(
        monthly_rankings=monthly_rankings,
        historical_source_policy=historical_source_policy,
    )


def _build_monthly_ranking_materialization_from_rankings(
    *,
    monthly_rankings: list[dict[str, object]],
    historical_source_policy: dict[str, object],
) -> dict[str, list[dict[str, object]]]:
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
                    "monthly_aggregation_lineage": {
                        "source": "elo_mmr_match_results",
                        "uses_bucket_aware_comparison": True,
                        "role_parent_fallback_enabled": True,
                        "penalty_boundary": "discipline-exact-plus-leave-admin-capability-aware",
                    },
                    "notes": [
                        "Outcome, combat, utility, match validity and player participation use real stored signals.",
                        "Canonical player-match facts now persist duration buckets, participation buckets and per-minute rates from the currently available repository data.",
                        "Canonical player-match facts also carry event-backed summary counters for approximate death classification lineage from the player-event ledger.",
                        "Normalization bucket keys and bucket-level baselines are persisted so later rating and monthly tasks can use explicit fallback-aware comparisons.",
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
    canonical_duration = _safe_int(match_group.get("resolved_duration_seconds"))
    canonical_mode = str(match_group.get("duration_source_status") or "").strip() or CAPABILITY_UNAVAILABLE
    if canonical_duration > 0:
        return canonical_duration, canonical_mode
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


def _resolve_own_team_average_rating(
    *,
    stable_player_key: str,
    team_side: str,
    players: list[dict[str, object]],
    rating_before_by_player: dict[str, float],
) -> float:
    normalized_team_side = str(team_side or "").strip().lower()
    own_team_ratings = [
        rating_before_by_player.get(str(player["stable_player_key"]), DEFAULT_BASE_MMR)
        for player in players
        if str(player["stable_player_key"]) == stable_player_key
        or _is_same_team(str(player.get("team_side") or ""), normalized_team_side)
    ]
    if not own_team_ratings:
        return DEFAULT_BASE_MMR
    return round(sum(own_team_ratings) / len(own_team_ratings), 3)


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


def _build_won_score(*, team_outcome: str) -> float:
    if team_outcome == "win":
        return 1.0
    if team_outcome == "draw":
        return 0.5
    return 0.0


def _build_margin_boost(*, team_outcome: str, allied_score: int | None, axis_score: int | None) -> float:
    if allied_score is None or axis_score is None or team_outcome == "draw":
        return 0.0
    total_score = max(1, allied_score + axis_score)
    margin_ratio = abs(allied_score - axis_score) / total_score
    signed_boost = min(0.15, margin_ratio * 0.30)
    return round(signed_boost if team_outcome == "win" else -signed_boost, 4)


def _build_outcome_adjusted(*, won_score: float, expected_win: float, margin_boost: float) -> float:
    raw_score = (2.0 * (won_score - expected_win)) + margin_boost
    return round(max(-1.0, min(1.0, raw_score)), 4)


def _build_monthly_eligibility_reason(
    *,
    valid_match_count: int,
    total_time_seconds: int,
    avg_participation_ratio: float,
    avg_participation_quality_score: float,
) -> str | None:
    if valid_match_count < MONTHLY_MIN_VALID_MATCHES:
        return "minimum-valid-matches-not-met"
    if total_time_seconds < MONTHLY_MIN_TIME_SECONDS:
        return "minimum-playtime-not-met"
    if avg_participation_ratio < MONTHLY_MIN_AVG_PARTICIPATION_RATIO:
        return "minimum-participation-ratio-not-met"
    if avg_participation_quality_score < 45.0:
        return "minimum-participation-quality-not-met"
    return None


def _most_common_status(rows: list[dict[str, object]], field_name: str) -> str:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[str(row.get(field_name) or CAPABILITY_UNAVAILABLE)] += 1
    if not counts:
        return CAPABILITY_UNAVAILABLE
    return max(counts.items(), key=lambda item: item[1])[0]


def _classify_quality_bucket(quality_factor: float) -> str:
    if quality_factor >= 0.8:
        return QUALITY_BUCKET_HIGH
    if quality_factor >= 0.55:
        return QUALITY_BUCKET_MEDIUM
    return QUALITY_BUCKET_LOW


def _classify_duration_bucket(duration_seconds: int) -> str:
    if duration_seconds >= 3600:
        return DURATION_BUCKET_FULL
    if duration_seconds >= 1800:
        return DURATION_BUCKET_STANDARD
    if duration_seconds > 0:
        return DURATION_BUCKET_SHORT
    return DURATION_BUCKET_UNKNOWN


def _classify_participation_bucket(participation_ratio: float) -> str:
    if participation_ratio >= 0.85:
        return PARTICIPATION_BUCKET_FULL
    if participation_ratio >= 0.50:
        return PARTICIPATION_BUCKET_CORE
    if participation_ratio > 0:
        return PARTICIPATION_BUCKET_LIMITED
    return PARTICIPATION_BUCKET_NONE


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
