---
id: TASK-181-add-global-ranking-backend-support
title: Add global ranking backend support
status: pending
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

The backend should expose a dedicated global ranking endpoint that supports weekly/monthly and annual modes, with initial metric support set to `kills` and clear behavior for unsupported inputs and limits.

## Steps

1. Read the listed files first.
2. Reuse leaderboard query modules for weekly/monthly ranking reads.
3. Reuse annual snapshot reader for annual ranking reads, with no recalculation per request.
4. Add route-level validation for timeframe/metric/limit/year behavior.
5. Keep payload shapes compatible with future frontend rendering and existing frontend patterns.
6. Document any optional follow-up if additional metrics are delayed beyond V1.

## Files to Read First

- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- docs/global-ranking-page-plan.md
- docs/stats-section-functional-plan.md
- docs/annual-ranking-snapshot-runbook.md
- backend/app/routes.py
- backend/app/payloads.py
- backend/app/rcon_historical_leaderboards.py
- backend/app/rcon_annual_rankings.py
- scripts/run-stats-validation.ps1
- scripts/run-integration-tests.ps1

## Expected Files to Modify

- backend/app/routes.py
- backend/app/payloads.py, if required for response normalization
- backend/app/rcon_historical_leaderboards.py, only if small reusable exposure is needed
- backend/app/rcon_annual_rankings.py, only if response shape/read behavior adaptation is needed without changing core logic
- scripts/run-stats-validation.ps1 or a new script to cover global ranking
- ai/tasks/done/TASK-181-add-global-ranking-backend-support.md

## Constraints

- Do not create new architecture.
- Do not add large migrations.
- Do not recalculate annual ranking on each public request.
- Do not re-enable Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Do not use public scoreboard as primary source while RCON coverage exists.
- Preserve existing Stats endpoint compatibility.
- Avoid frontend changes unless strictly required for backend documentation-only validation.
- Keep changes scoped and verifiable.

## Outcome

- Endpoint created and documented.
- Final payload contract captured and aligned with Ranking page requirements.
- Source flow documented by timeframe:
  - weekly/monthly from RCON materialized data
  - annual from annual snapshot records
- Validation outputs and known limits recorded.
- Follow-up recommendation for next task: frontend page implementation.

## Validation

- Run `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`.
- If endpoint-specific checks are added, run them in this task.
- Validate endpoint cases:
  - weekly, `metric=kills`, `limit=20`
  - monthly, `metric=kills`, `limit=20`
  - annual, `metric=kills`, `limit=20`
  - annual path with year if the implementation requires it
  - low limit, for example `3`
  - high invalid limit
  - unsupported metric
  - unsupported timeframe
- Run `git diff --name-only` within the scoped files.

