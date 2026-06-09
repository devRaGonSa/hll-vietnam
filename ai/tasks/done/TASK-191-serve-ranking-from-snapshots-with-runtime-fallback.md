---
id: TASK-191-serve-ranking-from-snapshots-with-runtime-fallback
title: Serve ranking from snapshots with runtime fallback
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto de Base de Datos
  - Arquitecto Python
roadmap_item: foundation
priority: high
---

# TASK-191 - Serve ranking from snapshots with runtime fallback

## Goal

Implement the `/api/ranking` read path so weekly and monthly ranking are served from snapshots when available, with a controlled runtime fallback only when configured and only when the snapshot is missing.

## Context

Public Ranking requests currently pay the cost of runtime aggregation for weekly and monthly windows, while annual ranking already reads from snapshots. After `TASK-190` defines the snapshot read model, HLL Vietnam needs the public ranking endpoint to prefer snapshot-backed reads, preserve annual snapshot behavior and expose enough metadata for frontend and operations to understand source, freshness and fallback usage.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Read the listed files first.
2. Implement weekly/monthly snapshot lookup according to `docs/ranking-snapshot-read-model-plan.md`.
3. Keep annual requests on the existing annual snapshot path.
4. Add controlled runtime fallback only for missing weekly/monthly snapshots when configuration allows it.
5. Expose response metadata needed to distinguish snapshot-ready, snapshot-missing and runtime-fallback responses.
6. Validate weekly, monthly, annual and invalid-request behavior.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `docs/ranking-snapshot-read-model-plan.md`
- `backend/app/routes.py`
- `backend/app/payloads.py`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/rcon_annual_rankings.py`
- `scripts/run-stats-validation.ps1`

## Expected Files to Modify

- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/routes.py`
- `backend/app/payloads.py`
- `scripts/run-stats-validation.ps1`
- `docs/ranking-snapshot-read-model-plan.md`, solo si se documenta comportamiento final
- `ai/tasks/done/TASK-191-serve-ranking-from-snapshots-with-runtime-fallback.md`

## Constraints

- No cambiar frontend salvo que sea imprescindible y esté documentado.
- No crear nuevas features visuales.
- No reactivar Elo/MMR.
- No reintroducir Comunidad Hispana #03.
- No usar scoreboard público como fuente primaria.
- No recalcular rankings pesados si snapshot `ready` existe.
- Mantener fallback runtime controlado para transición.
- La task depende del diseño de `TASK-190`.

## Validation

Before completing the task ensure:

- `/api/ranking` weekly/monthly:
  - attempts snapshot read first
  - returns snapshot when status is `ready`
  - uses runtime materialized fallback only when snapshot is missing and fallback is allowed
  - returns controlled missing when snapshot is missing and fallback is not allowed
- `/api/ranking` annual keeps current snapshot behavior
- response metadata includes:
  - `source`
  - `snapshot_status`
  - `generated_at`
  - `freshness`
  - `fallback_used`
  - `window_start`
  - `window_end`
- run:
  - `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
  - `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- probe:
  - `/api/ranking` weekly
  - `/api/ranking` monthly
  - `/api/ranking` annual
  - snapshot-missing behavior
  - invalid `metric`
  - invalid `timeframe`
  - invalid `limit`
- confirm annual still works
- document if snapshots are not yet generated automatically
- `git diff --name-only` stays within scope

## Outcome

- Implemented weekly/monthly `/api/ranking` as snapshot-first:
  - snapshot `ready` rows are served from `ranking_snapshots` + `ranking_snapshot_items`
  - annual requests remain on the existing annual snapshot path
- Added controlled runtime fallback behavior:
  - fallback is used only when the weekly/monthly snapshot is missing
  - fallback is controlled by `HLL_BACKEND_RANKING_RUNTIME_FALLBACK_ENABLED`
  - default remains enabled for transition
  - setting the variable to `false` returns controlled `snapshot_status='missing'` with empty items
- Response metadata now distinguishes:
  - snapshot-ready
  - snapshot-missing
  - runtime-fallback
- Metadata exposed on ranking responses now includes:
  - `source`
  - `snapshot_status`
  - `generated_at`
  - `freshness`
  - `fallback_used`
  - `window_start`
  - `window_end`
- Validation completed:
  - `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
  - `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- Validation script now proves:
  - normal route-contract behavior
  - snapshot-ready behavior using temporary fixture rows
  - snapshot-missing behavior with runtime fallback disabled
- Remaining operational dependency:
  - snapshot tables now exist on first access, but snapshot rows are not generated automatically yet; a future generator/job still needs to populate weekly/monthly snapshots for production use

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
