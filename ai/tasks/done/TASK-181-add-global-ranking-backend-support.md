---
id: TASK-181-add-global-ranking-backend-support
title: Add global ranking backend support
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto Python
  - Arquitecto de Base de Datos
roadmap_item: foundation
priority: high
---

# TASK-181-add-global-ranking-backend-support - Add global ranking backend support

## Goal

Implement backend API support for the new global ranking page using existing RCON historical leaderboard logic and annual snapshot readers, without changing public Stats endpoints.

## Context

The backend now exposes a dedicated global ranking route that supports weekly, monthly and annual modes with V1 metric scope limited to `kills`.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `docs/global-ranking-page-plan.md`
- `docs/stats-section-functional-plan.md`
- `docs/annual-ranking-snapshot-runbook.md`
- `backend/app/routes.py`
- `backend/app/payloads.py`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/rcon_annual_rankings.py`
- `scripts/run-stats-validation.ps1`
- `scripts/run-integration-tests.ps1`

## Expected Files to Modify

- `backend/app/routes.py`
- `backend/app/payloads.py`
- `scripts/run-stats-validation.ps1`
- `ai/tasks/done/TASK-181-add-global-ranking-backend-support.md`

## Constraints Verified

- No new architecture was introduced.
- No migrations were added.
- Annual ranking remains snapshot-backed and is not recalculated per request.
- Stats endpoints were left compatible.
- Comunidad Hispana #03 was not exposed through the new route.
- Public scoreboard was not introduced as a primary ranking source.

## Outcome

- Added `GET /api/ranking`.
- Added route validation for:
  - `timeframe`
  - `metric`
  - `limit`
  - `server_id`
  - required `year` when `timeframe=annual`
- Reused existing readers:
  - weekly/monthly from materialized RCON leaderboard reads
  - annual from annual snapshot storage
- Normalized the dedicated ranking response with:
  - `page_kind`
  - `timeframe`
  - `server_id`
  - `metric`
  - `limit`
  - `requested_limit`
  - `effective_limit`
  - `window_start`
  - `window_end`
  - `snapshot_status`
  - `source`
  - `items`
- Updated regression validation to cover the new route and its invalid-input cases.

## Validation

Executed:

- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- Direct local route checks through `resolve_get_payload(...)` for:
  - weekly `metric=kills`
  - monthly `metric=kills`
  - annual `metric=kills`
  - annual missing `year`

Observed:

- Weekly route returned `200`.
- Monthly route returned `200`.
- Annual route returned `200`.
- Annual route without `year` returned `400`.
- Unsupported metric returned `400`.
- Unsupported timeframe returned `400`.
- High invalid limit returned `400`.

Known limitation:

- Live HTTP verification against a running backend at `http://127.0.0.1:8000` was not available during validation; route-contract checks passed through local Python imports and the integration script reported that explicitly.

## Recommended Next Task

- `TASK-182-add-global-ranking-frontend-page`
