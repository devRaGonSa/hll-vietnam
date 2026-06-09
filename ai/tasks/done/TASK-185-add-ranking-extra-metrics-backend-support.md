---
id: TASK-185-add-ranking-extra-metrics-backend-support
title: Add ranking extra metrics backend support
status: done
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

Metrics added for `GET /api/ranking` weekly/monthly reads:

- `kills`
- `deaths`
- `teamkills`
- `matches_considered`
- `kd_ratio`
- `kills_per_match`

Backend formulas and ordering applied:

- `kills = SUM(kills)` ordered by `kills` desc, `matches_considered` desc, `player_name` asc
- `deaths = SUM(deaths)` ordered by `deaths` desc, `matches_considered` desc, `player_name` asc
- `teamkills = SUM(teamkills)` ordered by `teamkills` desc, `matches_considered` desc, `player_name` asc
- `matches_considered = COUNT(DISTINCT match_key)` ordered by `matches_considered` desc, `kills` desc, `player_name` asc
- `kd_ratio = SUM(kills) / SUM(deaths)` with `deaths=0 -> kills`, ordered by `kd_ratio` desc, `kills` desc, `matches_considered` desc, `player_name` asc
- `kills_per_match = SUM(kills) / COUNT(DISTINCT match_key)` with `matches_considered=0 -> 0`, ordered by `kills_per_match` desc, `kills` desc, `matches_considered` desc, `player_name` asc

Implementation summary:

- `backend/app/rcon_historical_leaderboards.py` now supports the V1.1 ranking metrics while preserving the existing materialized RCON read model.
- `backend/app/routes.py` now validates the expanded public Ranking metric set without changing the endpoint shape.
- `backend/app/payloads.py` now preserves decimal `metric_value` when needed and exposes `kills_per_match` in normalized ranking items.
- `backend/app/rcon_annual_rankings.py` remains snapshot-safe and returns a controlled annual-specific `400` for unsupported annual metrics.
- `scripts/run-stats-validation.ps1` now covers the new happy paths and annual guardrail failures.

Annual metric behavior and limitations:

- annual remains snapshot-backed only
- `metric=kills` remains supported
- extra annual metrics currently return controlled `400`
- no runtime full-year recomputation was introduced

Validations executed:

- `python -m compileall backend/app/routes.py backend/app/payloads.py backend/app/rcon_historical_leaderboards.py backend/app/rcon_annual_rankings.py`
- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`

Validation notes:

- live backend HTTP validation at `http://127.0.0.1:8000` was not available during execution
- route-contract validation still passed through local Python imports

Scope notes:

- task-owned modifications stayed within:
  - `backend/app/rcon_historical_leaderboards.py`
  - `backend/app/routes.py`
  - `backend/app/payloads.py`
  - `backend/app/rcon_annual_rankings.py`
  - `scripts/run-stats-validation.ps1`
- `git diff --name-only` also showed pre-existing or previous-task changes outside this task:
  - moved task files from `TASK-184` / `TASK-185`
  - `docs/global-ranking-page-plan.md` from `TASK-184`
  - unrelated existing workspace change `frontend/assets/img/weapons/black/gewehr_black.svg`
- those files were not modified as part of this backend task.

Known limitations:

- annual extra metrics are intentionally blocked until an explicit snapshot-backed implementation exists
- ranking item decimals are validated through route-contract checks, not through a running backend HTTP instance in this run

Recommended next task:

- expose the new metrics safely in the Ranking frontend UX.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
