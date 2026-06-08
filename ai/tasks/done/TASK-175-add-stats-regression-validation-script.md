---
id: TASK-175-add-stats-regression-validation-script
title: Add Stats regression validation script
status: done
type: platform
team: PM
supporting_teams:
  - Backend Senior
  - Frontend Senior
roadmap_item: foundation
priority: high
---

# TASK-175-add-stats-regression-validation-script - Add Stats regression validation script

## Goal

Add a small, repeatable validation for the existing Stats frontend/backend surfaces that protects current endpoints and assets, without changing behavior.

## Context

The Stats section already has public-facing pages, JS assets, and backend endpoints that can regress independently. This task should add a lightweight executable validation flow (script-based) that is tolerant to envs with no local data and can still verify expected behavior and error states.

## Steps

1. Read the listed files first.
2. Define a focused Stats validation workflow without changing any application behavior.
3. Add/update a script that checks key assets and endpoints, including supported and empty/missing states.
4. Ensure the validation outputs clear status and actionable next steps when backend is unavailable.
5. Document endpoint behavior, known environment limits, and the recommended follow-up task.

## Files to Read First

- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- docs/stats-section-functional-plan.md
- docs/annual-ranking-snapshot-runbook.md
- frontend/stats.html
- frontend/assets/js/stats.js
- backend/app/routes.py
- scripts/run-integration-tests.ps1

## Expected Files to Modify

- scripts/run-stats-validation.ps1 (or equivalent repo-preferred validation script)
- scripts/run-integration-tests.ps1 only if a safe integration point is justified
- ai/tasks/done/TASK-175-add-stats-regression-validation-script.md

## Constraints

- No behavior change in Stats.
- No UI redesign.
- No ranking logic changes.
- No database schema changes.
- Do not re-enable Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Keep validation tolerant to environments without positive local data.
- If backend is unavailable, document the expected validation behavior instead of failing with ambiguous output.

## Validation

- Run `node --check frontend/assets/js/stats.js`.
- Run `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`.
- Run the new Stats validation script.
- Run `git diff --name-only` and verify scope is within the task plan.

## Outcome

Validated surfaces:

- `frontend/stats.html` asset wiring and required Stats UI anchors
- `GET /health`
- `GET /api/stats/players/search`
- `GET /api/stats/players/{player_id}`
- `GET /api/stats/rankings/annual`

Implemented validation:

- Added `scripts/run-stats-validation.ps1` to check Stats asset presence, route-contract behavior, invalid parameter handling, and controlled backend-unavailable messaging.
- Wired `scripts/run-integration-tests.ps1` to execute the Stats validation and fail on non-zero child process exit codes.

Controlled limitations observed during validation:

- The local live backend was not running during task validation, so live HTTP checks reported the expected offline guidance instead of ambiguous failure.
- Current normalized all-server scope is returned as `all-servers`.
- Annual ranking `data.limit` currently reflects the effective stored snapshot size when a ready snapshot contains fewer rows than the requested limit; the validator accepts that current behavior without changing runtime logic.

Validation run:

- `node --check frontend/assets/js/stats.js`
- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`

Immediate follow-up recommendation:

- Continue with `TASK-176-add-stats-player-comparison-cards`, using the new Stats validation script as the regression guard for the existing Stats surface.
