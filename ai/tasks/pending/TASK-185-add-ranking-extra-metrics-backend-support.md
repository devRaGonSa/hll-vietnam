---
id: TASK-185-add-ranking-extra-metrics-backend-support
title: Add ranking extra metrics backend support
status: pending
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto Python
  - Arquitecto de Base de Datos
roadmap_item: foundation
priority: high
---

# TASK-185-add-ranking-extra-metrics-backend-support - Add ranking extra metrics backend support

## Goal

Add backend support for additional `Ranking global` metrics by reusing the existing RCON materialized read model, while preserving the current Ranking route and avoiding unsafe annual recomputation.

## Context

`TASK-183` confirmed that `GET /api/ranking` currently supports only `metric=kills`, with weekly/monthly reading from the RCON materialized leaderboard and annual reading from snapshots. The next backend step is to extend metric support safely for weekly/monthly and keep annual constrained to snapshot-safe behavior only.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Read the listed files first.
2. Keep the public endpoint as:
   - `GET /api/ranking?timeframe=weekly|monthly|annual&server_id=<server-or-all>&metric=<metric>&limit=<limit>&year=<year>`
3. Extend weekly/monthly support for:
   - `kills`
   - `deaths`
   - `teamkills`
   - `matches_considered`
   - `kd_ratio`
   - `kills_per_match`
4. Preserve `metric=kills` behavior and compatibility for existing Ranking requests.
5. Reuse the materialized RCON read model and avoid introducing a new ranking architecture.
6. Keep annual support safe:
   - support `kills`
   - only support additional annual metrics if they are snapshot-backed without public full-year recomputation
   - otherwise return a controlled `400` for unsupported annual metrics
7. Update route validation and payload normalization only where necessary.
8. Extend validation coverage for the new metrics and failure cases.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `docs/global-ranking-page-plan.md`
- `backend/app/routes.py`
- `backend/app/payloads.py`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/rcon_annual_rankings.py`
- `scripts/run-stats-validation.ps1`
- `scripts/run-integration-tests.ps1`
- `ai/tasks/done/TASK-183-review-global-ranking-implementation.md`
- `ai/tasks/done/TASK-184-define-ranking-metric-expansion-contract.md`

## Expected Files to Modify

- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/routes.py`
- `backend/app/payloads.py`
- `backend/app/rcon_annual_rankings.py`
- `scripts/run-stats-validation.ps1`
- `ai/tasks/done/TASK-185-add-ranking-extra-metrics-backend-support.md`

## Constraints

- Do not create migrations.
- Do not introduce a new architecture.
- Do not recalculate the annual full-year ranking on public requests.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Do not use public scoreboard as the normal primary source.
- Do not modify frontend files.
- Do not break Stats endpoints.
- Do not break the existing Ranking route for `metric=kills`.

## Validation

Before completing the task ensure:

- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- validate `GET /api/ranking` for:
  - `timeframe=weekly&metric=kills`
  - `timeframe=weekly&metric=deaths`
  - `timeframe=weekly&metric=teamkills`
  - `timeframe=weekly&metric=matches_considered`
  - `timeframe=weekly&metric=kd_ratio`
  - `timeframe=weekly&metric=kills_per_match`
  - `timeframe=monthly&metric=kd_ratio`
  - `timeframe=monthly&metric=kills_per_match`
  - `timeframe=annual&metric=kills`
  - unsupported metric
  - unsupported timeframe
  - `limit=3`
  - `limit=101` or invalid limit according to the current contract
- confirm annual behavior is still snapshot-safe
- confirm `git diff --name-only` stays within scope

## Outcome

Document:

- metrics added
- formulas applied in backend ranking logic
- annual metric behavior and limitations
- validations executed
- known limitations
- recommended next task: expose the new metrics safely in Ranking frontend UX

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
