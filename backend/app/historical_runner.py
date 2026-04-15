"""Local development loop for periodic historical CRCON refreshes."""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from typing import Any

from .config import (
    get_historical_refresh_overlap_hours,
    get_historical_full_snapshot_every_runs,
    get_historical_elo_mmr_min_new_samples,
    get_historical_elo_mmr_rebuild_interval_minutes,
    get_historical_refresh_interval_seconds,
    get_historical_refresh_max_retries,
    get_historical_refresh_retry_delay_seconds,
    get_historical_data_source_kind,
)
from .elo_mmr_engine import rebuild_elo_mmr_models
from .elo_mmr_storage import get_latest_elo_mmr_generated_at
from .historical_ingestion import run_incremental_refresh
from .historical_storage import list_historical_coverage_report
from .historical_snapshots import (
    generate_and_persist_historical_snapshots,
    generate_and_persist_priority_historical_snapshots,
)
from .rcon_historical_storage import count_rcon_historical_samples_since
from .rcon_historical_worker import run_rcon_historical_capture
from .writer_lock import (
    BackendWriterLockConflictError,
    BackendWriterLockTimeoutError,
    backend_writer_lock,
    build_acquired_writer_lock_payload,
    build_writer_lock_holder,
    build_writer_lock_timeout_payload,
    check_manual_writer_lock_preflight,
)

HOURLY_INTERVAL_SECONDS = 3600
DEFAULT_HISTORICAL_SERVER_SCOPE = (
    "comunidad-hispana-01",
    "comunidad-hispana-02",
    "comunidad-hispana-03",
)
MANUAL_PHASE_CHOICES = ("full", "snapshots", "capture", "refresh")


def run_periodic_historical_refresh(
    *,
    interval_seconds: int,
    manual_full_elo_rebuild: bool = False,
    max_retries: int,
    retry_delay_seconds: int,
    server_slug: str | None = None,
    max_pages: int | None = None,
    page_size: int | None = None,
    max_runs: int | None = None,
) -> None:
    """Run periodic historical refreshes and rebuild persisted snapshots."""
    completed_runs = 0
    print(
        json.dumps(
            {
                "event": "historical-refresh-loop-started",
                "interval_seconds": interval_seconds,
                "max_retries": max_retries,
                "retry_delay_seconds": retry_delay_seconds,
                "server_scope": _describe_refresh_scope(server_slug),
                "snapshot_scope": _describe_snapshot_scope(server_slug),
            },
            indent=2,
            default=_json_default,
        )
    )
    print("Press Ctrl+C to stop.")

    try:
        while max_runs is None or completed_runs < max_runs:
            completed_runs += 1
            payload = _run_phase_with_retries(
                phase="full",
                execution_mode="loop",
                manual_full_elo_rebuild=manual_full_elo_rebuild,
                max_retries=max_retries,
                retry_delay_seconds=retry_delay_seconds,
                server_slug=server_slug,
                max_pages=max_pages,
                page_size=page_size,
                run_number=completed_runs,
            )
            print(json.dumps({"run": completed_runs, **payload}, indent=2, default=_json_default))

            if max_runs is not None and completed_runs >= max_runs:
                break

            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\nHistorical refresh loop stopped by user.")


def _run_phase_with_retries(
    *,
    phase: str,
    execution_mode: str,
    manual_full_elo_rebuild: bool,
    max_retries: int,
    retry_delay_seconds: int,
    server_slug: str | None,
    max_pages: int | None,
    page_size: int | None,
    run_number: int,
) -> dict[str, Any]:
    attempt = 0
    manual_holder = build_writer_lock_holder(
        f"app.historical_runner {phase}:{server_slug or 'all-servers'}"
    )
    while True:
        attempt += 1
        try:
            if execution_mode == "manual":
                check_manual_writer_lock_preflight(holder=manual_holder)
            payload = run_manual_historical_phase(
                phase=phase,
                execution_mode=execution_mode,
                manual_full_elo_rebuild=manual_full_elo_rebuild,
                server_slug=server_slug,
                max_pages=max_pages,
                page_size=page_size,
                run_number=run_number,
                progress_callback=_build_runner_progress_callback(
                    execution_mode=execution_mode,
                    phase=phase,
                    run_number=run_number,
                ),
            )
            return {
                "status": "ok",
                "attempts_used": attempt,
                "max_retries": max_retries,
                "writer_lock": (
                    build_acquired_writer_lock_payload(
                        holder=manual_holder,
                        metadata=payload.pop("writer_lock_metadata", None),
                    )
                    if execution_mode == "manual"
                    else None
                ),
                **payload,
            }
        except BackendWriterLockConflictError as exc:
            return {
                "status": "error",
                "attempts_used": attempt,
                "max_retries": max_retries,
                "error": str(exc),
                "writer_lock": exc.payload,
            }
        except BackendWriterLockTimeoutError as exc:
            return {
                "status": "error",
                "attempts_used": attempt,
                "max_retries": max_retries,
                "error": str(exc),
                "writer_lock": build_writer_lock_timeout_payload(holder=manual_holder),
            }
        except Exception as exc:
            if attempt > max_retries:
                return {
                    "status": "error",
                    "attempts_used": attempt,
                    "max_retries": max_retries,
                    "error": str(exc),
                }
            if retry_delay_seconds > 0:
                time.sleep(retry_delay_seconds)


def run_manual_historical_phase(
    *,
    phase: str,
    execution_mode: str = "manual",
    manual_full_elo_rebuild: bool = False,
    server_slug: str | None = None,
    max_pages: int | None = None,
    page_size: int | None = None,
    run_number: int = 1,
    progress_callback: Any = None,
) -> dict[str, Any]:
    """Run one explicit historical maintenance phase and return one structured result."""
    normalized_phase = phase.strip().lower()
    if normalized_phase not in MANUAL_PHASE_CHOICES:
        raise ValueError(
            f"--phase must be one of {', '.join(MANUAL_PHASE_CHOICES)}."
        )

    if normalized_phase == "capture":
        return {
            "mode": execution_mode,
            "phase": normalized_phase,
            "run_number": run_number,
            "rcon_capture_result": _run_primary_rcon_capture(),
            "classic_fallback_used": False,
            "classic_fallback_reason": "manual-phase-capture-only",
            "refresh_result": _build_phase_skip_result("manual-phase-capture-only"),
            "snapshot_result": _build_phase_skip_result("manual-phase-capture-only"),
            "elo_mmr_result": _build_elo_mmr_follow_up_result(
                workload="skipped",
                reason="manual-phase-capture-only",
                policy_mode="manual-no-elo-follow-up",
            ),
        }

    with backend_writer_lock(
        holder=build_writer_lock_holder(
            f"app.historical_runner {normalized_phase}:{server_slug or 'all-servers'}"
        )
    ) as writer_lock_metadata:
        return {
            **_run_manual_historical_phase_unlocked(
            phase=normalized_phase,
            execution_mode=execution_mode,
            manual_full_elo_rebuild=manual_full_elo_rebuild,
            server_slug=server_slug,
            max_pages=max_pages,
            page_size=page_size,
            run_number=run_number,
            progress_callback=progress_callback,
            ),
            "writer_lock_metadata": writer_lock_metadata,
        }


def _run_manual_historical_phase_unlocked(
    *,
    phase: str,
    execution_mode: str,
    manual_full_elo_rebuild: bool,
    server_slug: str | None,
    max_pages: int | None,
    page_size: int | None,
    run_number: int,
    progress_callback: Any,
) -> dict[str, Any]:
    _emit_runner_progress(
        progress_callback,
        {
            "event": "historical-runner-phase-started",
            "mode": execution_mode,
            "phase": phase,
            "run_number": run_number,
            "server_scope": _describe_refresh_scope(server_slug),
            "max_pages": max_pages,
            "page_size": page_size,
            "bounded_debug": any(value is not None for value in (server_slug, max_pages, page_size)),
        },
    )
    if phase == "snapshots":
        result = {
            "mode": execution_mode,
            "phase": phase,
            "run_number": run_number,
            "rcon_capture_result": _build_phase_skip_result("manual-phase-snapshots-only"),
            "classic_fallback_used": False,
            "classic_fallback_reason": "manual-phase-snapshots-only",
            "refresh_result": _build_phase_skip_result("manual-phase-snapshots-only"),
            "snapshot_result": {
                **generate_historical_snapshots(
                    server_slug=server_slug,
                    run_number=run_number,
                ),
                "generation_policy": "manual-phase-snapshots-only",
                "reason": "manual-phase-requested-snapshot-materialization-only",
            },
            "elo_mmr_result": _build_elo_mmr_follow_up_result(
                workload="skipped",
                reason="manual-phase-snapshots-only",
                policy_mode="manual-no-elo-follow-up",
            ),
        }
        _emit_runner_progress(
            progress_callback,
            {
                "event": "historical-runner-phase-completed",
                "mode": execution_mode,
                "phase": phase,
                "run_number": run_number,
                "server_scope": _describe_refresh_scope(server_slug),
                "max_pages": max_pages,
                "page_size": page_size,
                "bounded_debug": any(value is not None for value in (server_slug, max_pages, page_size)),
                "classic_fallback_used": result["classic_fallback_used"],
                "classic_fallback_reason": result["classic_fallback_reason"],
            },
        )
        return result

    if phase == "refresh":
        result = {
            "mode": execution_mode,
            "phase": phase,
            "run_number": run_number,
            "rcon_capture_result": _build_phase_skip_result("manual-phase-refresh-only"),
            "classic_fallback_used": True,
            "classic_fallback_reason": "manual-phase-refresh-only",
            "refresh_result": _run_classic_refresh(
                server_slug=server_slug,
                max_pages=max_pages,
                page_size=page_size,
                progress_callback=progress_callback,
            ),
            "snapshot_result": _build_phase_skip_result("manual-phase-refresh-only"),
            "elo_mmr_result": _build_elo_mmr_follow_up_result(
                workload="skipped",
                reason="manual-phase-refresh-only",
                policy_mode="manual-no-elo-follow-up",
            ),
        }
        _emit_runner_progress(
            progress_callback,
            {
                "event": "historical-runner-phase-completed",
                "mode": execution_mode,
                "phase": phase,
                "run_number": run_number,
                "server_scope": _describe_refresh_scope(server_slug),
                "max_pages": max_pages,
                "page_size": page_size,
                "bounded_debug": any(value is not None for value in (server_slug, max_pages, page_size)),
                "classic_fallback_used": result["classic_fallback_used"],
                "classic_fallback_reason": result["classic_fallback_reason"],
            },
        )
        return result

    rcon_capture_result = _run_primary_rcon_capture()
    if phase == "capture":
        raise RuntimeError("Capture phase must be handled before acquiring the manual writer lock.")

    should_run_classic_fallback, classic_fallback_reason = _resolve_classic_fallback_policy(
        server_slug=server_slug,
        run_number=run_number,
        rcon_capture_result=rcon_capture_result,
    )
    _emit_runner_progress(
        progress_callback,
        {
            "event": "historical-runner-classic-fallback-policy-resolved",
            "mode": execution_mode,
            "phase": phase,
            "run_number": run_number,
            "classic_fallback_used": should_run_classic_fallback,
            "classic_fallback_reason": classic_fallback_reason,
            "rcon_capture_status": rcon_capture_result.get("status"),
        },
    )
    if should_run_classic_fallback:
        refresh_result = _run_classic_refresh(
            server_slug=server_slug,
            max_pages=max_pages,
            page_size=page_size,
            progress_callback=progress_callback,
        )
        snapshot_result = generate_historical_snapshots(
            server_slug=server_slug,
            run_number=run_number,
        )
        elo_mmr_result = _resolve_elo_mmr_follow_up(
            execution_mode=execution_mode,
            manual_full_elo_rebuild=manual_full_elo_rebuild,
            rcon_capture_result=rcon_capture_result,
            default_skip_reason="manual-full-cycle-defaults-to-no-elo-rebuild",
            auto_skip_reason="rcon-primary-cycle-had-classic-fallback-but-auto-elo-policy-not-due",
        )
    else:
        should_generate_snapshots = _rcon_capture_has_new_useful_data(rcon_capture_result)
        refresh_result = {
            "status": "skipped",
            "reason": "rcon-primary-cycle-no-classic-fallback-needed",
        }
        if should_generate_snapshots:
            snapshot_result = generate_historical_snapshots(
                server_slug=server_slug,
                run_number=run_number,
            )
            snapshot_result = {
                **snapshot_result,
                "generation_policy": "rcon-primary-useful-cycle",
                "reason": "rcon-primary-cycle-produced-new-useful-coverage",
            }
            elo_mmr_result = _resolve_elo_mmr_follow_up(
                execution_mode=execution_mode,
                manual_full_elo_rebuild=manual_full_elo_rebuild,
                rcon_capture_result=rcon_capture_result,
                default_skip_reason="manual-full-cycle-defaults-to-no-elo-rebuild",
                auto_skip_reason="rcon-primary-useful-cycle-elo-rebuild-throttled",
            )
        else:
            snapshot_result = {
                "status": "skipped",
                "reason": "rcon-primary-cycle-had-no-new-useful-data",
                "generation_policy": "rcon-primary-no-new-useful-data",
            }
            elo_mmr_result = _resolve_elo_mmr_follow_up(
                execution_mode=execution_mode,
                manual_full_elo_rebuild=manual_full_elo_rebuild,
                rcon_capture_result=rcon_capture_result,
                default_skip_reason="manual-full-cycle-defaults-to-no-elo-rebuild",
                auto_skip_reason="rcon-primary-cycle-had-no-new-useful-data",
            )

    result = {
        "mode": execution_mode,
        "phase": phase,
        "run_number": run_number,
        "rcon_capture_result": rcon_capture_result,
        "classic_fallback_used": should_run_classic_fallback,
        "classic_fallback_reason": classic_fallback_reason,
        "refresh_result": refresh_result,
        "snapshot_result": snapshot_result,
        "elo_mmr_result": elo_mmr_result,
    }
    _emit_runner_progress(
        progress_callback,
        {
            "event": "historical-runner-phase-completed",
            "mode": execution_mode,
            "phase": phase,
            "run_number": run_number,
            "server_scope": _describe_refresh_scope(server_slug),
            "max_pages": max_pages,
            "page_size": page_size,
            "bounded_debug": any(value is not None for value in (server_slug, max_pages, page_size)),
            "classic_fallback_used": result["classic_fallback_used"],
            "classic_fallback_reason": result["classic_fallback_reason"],
        },
    )
    return result


def _run_classic_refresh(
    *,
    server_slug: str | None,
    max_pages: int | None,
    page_size: int | None,
    progress_callback: Any = None,
) -> dict[str, Any]:
    return run_incremental_refresh(
        server_slug=server_slug,
        max_pages=max_pages,
        page_size=page_size,
        rebuild_snapshots=False,
        progress_callback=progress_callback,
    )


def _build_phase_skip_result(reason: str) -> dict[str, str]:
    return {
        "status": "skipped",
        "reason": reason,
    }


def _resolve_elo_mmr_follow_up(
    *,
    execution_mode: str,
    manual_full_elo_rebuild: bool,
    rcon_capture_result: dict[str, Any],
    default_skip_reason: str,
    auto_skip_reason: str,
) -> dict[str, Any]:
    if execution_mode == "manual":
        if not manual_full_elo_rebuild:
            return _build_elo_mmr_follow_up_result(
                workload="skipped",
                reason=default_skip_reason,
                policy_mode="manual-default-skip",
                explicit_path="python -m app.elo_mmr_engine rebuild or --full-elo-rebuild",
            )
        return {
            **rebuild_elo_mmr_models(),
            "workload": "full",
            "policy_mode": "manual-explicit-full-rebuild",
            "requested_explicitly": True,
        }

    elo_policy = _build_elo_mmr_rebuild_policy(rcon_capture_result=rcon_capture_result)
    if bool(elo_policy["due"]):
        return {
            **rebuild_elo_mmr_models(),
            "workload": "full",
            "policy_mode": "automatic-loop-policy",
            "requested_explicitly": False,
            "generation_policy": "automatic-loop-elo-rebuild-due",
            "reason": "automatic-loop-policy-met-elo-rebuild-threshold",
            **elo_policy,
        }
    return _build_elo_mmr_follow_up_result(
        workload="skipped",
        reason=auto_skip_reason,
        policy_mode="automatic-loop-policy",
        requested_explicitly=False,
        **elo_policy,
    )


def _build_elo_mmr_follow_up_result(
    *,
    workload: str,
    reason: str,
    policy_mode: str,
    requested_explicitly: bool = False,
    explicit_path: str | None = None,
    **extra: Any,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "ok" if workload in {"lightweight", "full"} else "skipped",
        "workload": workload,
        "reason": reason,
        "policy_mode": policy_mode,
        "requested_explicitly": requested_explicitly,
    }
    if explicit_path:
        result["explicit_path"] = explicit_path
    result.update(extra)
    return result


def generate_historical_snapshots(
    *,
    server_slug: str | None = None,
    run_number: int = 1,
) -> dict[str, Any]:
    """Build priority prewarm snapshots on every run and the full matrix on cadence."""
    generated_at = datetime.now(timezone.utc)
    full_snapshot_every_runs = get_historical_full_snapshot_every_runs()
    should_run_full_refresh = bool(server_slug) or run_number % full_snapshot_every_runs == 0
    if should_run_full_refresh:
        result = generate_and_persist_historical_snapshots(
            server_key=server_slug,
            generated_at=generated_at,
        )
    else:
        result = generate_and_persist_priority_historical_snapshots(
            generated_at=generated_at,
        )
    return {
        **result,
        "run_number": run_number,
        "full_snapshot_every_runs": full_snapshot_every_runs,
        "prewarm_only": not should_run_full_refresh,
        "refresh_interval_seconds": get_historical_refresh_interval_seconds(),
        "includes_monthly_mvp_v2": True,
    }


def _describe_refresh_scope(server_slug: str | None) -> list[str]:
    if server_slug:
        return [server_slug]
    return list(DEFAULT_HISTORICAL_SERVER_SCOPE)


def _describe_snapshot_scope(server_slug: str | None) -> list[str]:
    if server_slug:
        return [server_slug, "all-servers"]
    return [*DEFAULT_HISTORICAL_SERVER_SCOPE, "all-servers"]


def _run_primary_rcon_capture() -> dict[str, Any]:
    if get_historical_data_source_kind() != "rcon":
        return {
            "status": "skipped",
            "reason": "historical-data-source-configured-without-rcon-primary",
        }
    return run_rcon_historical_capture()


def _resolve_classic_fallback_policy(
    *,
    server_slug: str | None,
    run_number: int,
    rcon_capture_result: dict[str, Any],
) -> tuple[bool, str]:
    if get_historical_data_source_kind() != "rcon":
        return True, "public-scoreboard-configured-as-primary-historical-source"

    if not _rcon_capture_has_usable_results(rcon_capture_result):
        return True, "rcon-historical-capture-failed-or-returned-no-usable-targets"

    if server_slug:
        return True, "manual-server-scope-still-needs-classic-historical-fallback"

    base_refresh_reason = _resolve_base_historical_refresh_need()
    if base_refresh_reason:
        return True, base_refresh_reason

    if run_number % get_historical_full_snapshot_every_runs() == 0:
        return True, "periodic-classic-fallback-for-competitive-historical-coverage"

    return False, "rcon-primary-cycle-succeeded-without-needing-classic-fallback"


def _resolve_base_historical_refresh_need() -> str | None:
    try:
        coverage_report = list_historical_coverage_report()
    except Exception:  # noqa: BLE001 - an unreadable base archive still needs classic refresh.
        return "classic-historical-coverage-check-failed"
    if not coverage_report:
        return "classic-historical-coverage-missing"

    stale_after_seconds = max(0, get_historical_refresh_overlap_hours()) * 3600
    now = datetime.now(timezone.utc)
    for item in coverage_report:
        server = item.get("server")
        server_slug = (
            str(server.get("slug"))
            if isinstance(server, dict) and server.get("slug")
            else "unknown-server"
        )
        imported_matches_count = int(item.get("imported_matches_count") or 0)
        if imported_matches_count <= 0:
            return f"classic-historical-coverage-missing-for-{server_slug}"

        last_match_at = _parse_policy_timestamp(item.get("last_match_at"))
        if last_match_at is None:
            return f"classic-historical-latest-match-unknown-for-{server_slug}"

        age_seconds = max(0, int((now - last_match_at).total_seconds()))
        if stale_after_seconds and age_seconds > stale_after_seconds:
            return f"classic-historical-coverage-stale-for-{server_slug}"

    return None


def _parse_policy_timestamp(value: object) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        normalized = value.strip().replace("Z", "+00:00")
        if normalized.endswith("+00"):
            normalized = f"{normalized}:00"
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError:
            return None
    else:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _rcon_capture_has_usable_results(rcon_capture_result: dict[str, Any]) -> bool:
    if rcon_capture_result.get("status") != "ok":
        return False
    targets = rcon_capture_result.get("targets")
    return isinstance(targets, list) and len(targets) > 0


def _rcon_capture_has_new_useful_data(rcon_capture_result: dict[str, Any]) -> bool:
    if rcon_capture_result.get("status") != "ok":
        return False
    totals = rcon_capture_result.get("totals")
    if isinstance(totals, dict) and int(totals.get("samples_inserted") or 0) > 0:
        return True
    targets = rcon_capture_result.get("targets")
    if not isinstance(targets, list):
        return False
    return any(bool(target.get("sample_inserted")) for target in targets if isinstance(target, dict))


def _build_elo_mmr_rebuild_policy(
    *,
    rcon_capture_result: dict[str, Any],
) -> dict[str, Any]:
    interval_minutes = get_historical_elo_mmr_rebuild_interval_minutes()
    min_new_samples = get_historical_elo_mmr_min_new_samples()
    last_generated_at = get_latest_elo_mmr_generated_at()
    last_generated_at_iso = (
        last_generated_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        if last_generated_at is not None
        else None
    )
    minutes_since_last_rebuild = None
    if last_generated_at is not None:
        minutes_since_last_rebuild = int(
            max(
                0,
                (
                    datetime.now(timezone.utc) - last_generated_at.astimezone(timezone.utc)
                ).total_seconds() // 60,
            )
        )
    samples_since_last_rebuild = count_rcon_historical_samples_since(last_generated_at_iso)
    due = (
        _rcon_capture_has_new_useful_data(rcon_capture_result)
        and samples_since_last_rebuild >= min_new_samples
        and (
            last_generated_at is None
            or minutes_since_last_rebuild is None
            or minutes_since_last_rebuild >= interval_minutes
        )
    )
    return {
        "policy": "min-new-rcon-samples-and-minutes-since-last-successful-rebuild",
        "due": due,
        "last_generated_at": last_generated_at_iso,
        "samples_since_last_rebuild": samples_since_last_rebuild,
        "minutes_since_last_rebuild": minutes_since_last_rebuild,
        "rebuild_interval_minutes": interval_minutes,
        "min_new_samples": min_new_samples,
    }


def _build_runner_progress_callback(
    *,
    execution_mode: str,
    phase: str,
    run_number: int,
):
    def _callback(payload: dict[str, Any]) -> None:
        _emit_runner_progress(
            _print_progress,
            {
                **payload,
                "runner_mode": execution_mode,
                "runner_phase": phase,
                "runner_run_number": run_number,
            },
        )

    return _callback


def _emit_runner_progress(callback: Any, payload: dict[str, Any]) -> None:
    if callback is None:
        return
    callback(payload)


def _print_progress(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=True, default=_json_default))


def _json_default(value: object) -> str:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return str(value)


def build_arg_parser() -> argparse.ArgumentParser:
    """Allow local scheduled historical refresh execution without external infra."""
    parser = argparse.ArgumentParser(
        description="Run periodic historical refreshes and regenerate snapshots for HLL Vietnam.",
    )
    parser.add_argument(
        "mode",
        nargs="?",
        choices=("run", "loop"),
        default="run",
        help="run executes one explicit manual phase; loop keeps running the full cycle periodically",
    )
    parser.add_argument(
        "--phase",
        choices=MANUAL_PHASE_CHOICES,
        default="full",
        help="manual phase for run mode: full, snapshots, capture, or refresh",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=get_historical_refresh_interval_seconds(),
        help="Seconds to wait between refresh-plus-snapshot runs.",
    )
    parser.add_argument(
        "--hourly",
        action="store_true",
        help="Shortcut for running the refresh loop every 3600 seconds.",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=get_historical_refresh_max_retries(),
        help="Retry attempts after a failed incremental refresh.",
    )
    parser.add_argument(
        "--retry-delay",
        type=int,
        default=get_historical_refresh_retry_delay_seconds(),
        help="Seconds to wait between failed attempts.",
    )
    parser.add_argument(
        "--server",
        dest="server_slug",
        help="Optional historical server slug.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional page cap for local validation.",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=None,
        help="Optional override for CRCON page size.",
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        default=None,
        help="Optional safety limit for loop mode.",
    )
    parser.add_argument(
        "--full-elo-rebuild",
        action="store_true",
        help="run mode only: explicitly trigger a full Elo/MMR rebuild after the selected manual phase",
    )
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()

    if args.hourly:
        args.interval = HOURLY_INTERVAL_SECONDS
        if args.mode == "run":
            args.mode = "loop"

    if args.retries < 0:
        raise ValueError("--retries must be zero or positive.")
    if args.retry_delay < 0:
        raise ValueError("--retry-delay must be zero or positive.")
    if args.max_runs is not None and args.max_runs <= 0:
        raise ValueError("--max-runs must be positive when provided.")
    if args.mode == "loop" and args.full_elo_rebuild:
        raise ValueError("--full-elo-rebuild is only supported in run mode.")
    if args.mode == "run" and args.full_elo_rebuild and args.phase != "full":
        raise ValueError("--full-elo-rebuild is only supported with run --phase full.")

    if args.mode == "loop":
        if args.interval <= 0:
            raise ValueError("--interval must be a positive integer.")
        run_periodic_historical_refresh(
            interval_seconds=args.interval,
            manual_full_elo_rebuild=False,
            max_retries=args.retries,
            retry_delay_seconds=args.retry_delay,
            server_slug=args.server_slug,
            max_pages=args.max_pages,
            page_size=args.page_size,
            max_runs=args.max_runs,
        )
        return

    payload = _run_phase_with_retries(
        phase=args.phase,
        execution_mode="manual",
        manual_full_elo_rebuild=args.full_elo_rebuild,
        max_retries=args.retries,
        retry_delay_seconds=args.retry_delay,
        server_slug=args.server_slug,
        max_pages=args.max_pages,
        page_size=args.page_size,
        run_number=1,
    )
    print(json.dumps(payload, indent=2, default=_json_default))


if __name__ == "__main__":
    main()
