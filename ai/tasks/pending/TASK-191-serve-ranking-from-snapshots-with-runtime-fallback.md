---
id: TASK-191-serve-ranking-from-snapshots-with-runtime-fallback
title: Serve ranking from snapshots with runtime fallback
status: pending
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

Document:

- final read-path behavior
- fallback conditions
- validation results
- any remaining operational dependency for snapshot generation

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
