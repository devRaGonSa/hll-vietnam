---
id: TASK-119
title: Add historical UI regression validation
status: done
type: platform
team: Frontend Senior
supporting_teams:
  - Backend Senior
  - PM
roadmap_item: historical-ui
priority: medium
---

# TASK-119 - Add historical UI regression validation

## Goal

Add lightweight validation so future changes do not reintroduce removed UI or unsafe historical match-link behavior.

## Context

HLL Vietnam has intentionally removed Comunidad Hispana #03 from public/default flows, paused MVP/Elo UI, restored RCON-first historical policy and added internal match details. A small regression validation script/check should protect those decisions without adding heavy test infrastructure.

Use branch:

- `plan/scoreboard-match-linking-tasks`

## Steps

1. Work from this task only after moving it to `ai/tasks/in-progress/`.
2. Inspect the listed files before changing anything.
3. Extend or add validation scripts/checks compatible with the current repo.
4. Check served or static frontend for:
   - no Comunidad Hispana #03 selector.
   - no MVP mensual V1/V2 blocks.
   - no Comparativa V1 vs V2.
   - no Elo/MMR public block.
   - no public "snapshot" wording.
   - recent cards include either `Ver partida` or `Ver detalles`.
5. Check backend:
   - `/health` works.
   - historical source remains RCON-first.
   - match detail endpoint works.
6. Keep validation lightweight and compatible with local PowerShell usage.
7. Update documentation only if needed to explain how to run the new check.
8. Validate the result.
9. Move this task to `ai/tasks/done/` only after validation is complete and document the outcome in this file.
10. Commit and push the completed implementation branch.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/frontend-senior.md`
- `ai/orchestrator/backend-senior.md`
- `scripts/run-integration-tests.ps1`
- `frontend/historico.html`
- `frontend/assets/js/historico.js`
- `frontend/historico-partida.html`
- `frontend/assets/js/historico-partida.js`
- `backend/app/config.py`
- `backend/app/routes.py`
- `docs/decisions.md`

## Expected Files to Modify

- `scripts/run-integration-tests.ps1` or a focused new validation script under `scripts/`
- possibly documentation for the new validation command
- possibly backend/frontend test fixtures only if needed
- this task file, moved to `ai/tasks/done/`

If additional files become necessary, explain why in the task outcome and commit message.

## Expected Files Not to Modify

- product frontend behavior except minimal test hooks if absolutely required and justified
- backend product behavior except minimal validation hooks if absolutely required and justified
- database migrations
- persisted data
- local `.env`
- Docker/Compose config unless required for validation and explicitly justified
- Elo/MMR implementation files

## Constraints

- Do not reintroduce Comunidad Hispana #03.
- Do not reintroduce paused MVP/Elo UI.
- Do not change historical ingestion policy.
- Do not add real credentials.
- Do not modify local `.env`.
- Do not delete persisted data, migrations, backend endpoints or historical ingestion code.
- Do not use the public word "snapshot" in user-facing UI.
- Keep validation lightweight; do not introduce unnecessary frameworks or dependencies.

## Validation

Before completing the task, run and document:

- `git status`
- `node --check frontend/assets/js/historico.js`
- `node --check frontend/assets/js/historico-partida.js` if present
- Python compile checks for touched backend modules, if any
- the new or updated historical UI regression validation
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- check confirming `/health` works when the backend is served for validation
- check confirming historical source remains RCON-first
- check confirming the match detail endpoint works
- check confirming no Comunidad Hispana #03, MVP mensual V1/V2, Comparativa V1 vs V2, Elo/MMR public block or public "snapshot" wording is present
- check confirming recent cards include either `Ver partida` or `Ver detalles`
- `git diff --name-only` and confirmation that changed files match the expected scope

If a configured validation command cannot be run, document the exact reason in the outcome.

## Commit And Push Requirements

- Run validation before committing.
- Run `git status`.
- Stage only intended files.
- Commit with message: `test: add historical ui regression validation`
- Push the branch to origin.
- Do not leave completed work only in local.

## Outcome

Completed.

Implementation decisions:

- Added `scripts/run-historical-ui-regression-tests.ps1` as a lightweight PowerShell validation for historical UI guardrails.
- Wired the new script into `scripts/run-integration-tests.ps1` so the regression checks run with the existing platform validation command.
- Kept validation static/route-level by default to avoid adding frontend test frameworks or browser dependencies.
- Added a separate served-backend validation during task execution for `/health` and match detail.

Validation performed:

- `git status --short --branch` confirmed branch `plan/scoreboard-match-linking-tasks`.
- `node --check frontend/assets/js/historico.js` passed.
- `node --check frontend/assets/js/historico-partida.js` passed.
- `powershell -ExecutionPolicy Bypass -File scripts/run-historical-ui-regression-tests.ps1` passed.
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1` passed and now includes the historical UI regression validation.
- Served backend check passed on `http://127.0.0.1:8765/health`.
- Served backend check confirmed `/health` reports `historical_data_source` as `rcon`.
- Served backend check passed for `/api/historical/matches/detail?server=comunidad-hispana-01&match=regression-check`.
- Regression script confirms no `Comunidad Hispana #03` selector, no MVP mensual V1/V2 blocks, no Comparativa V1 vs V2 block, no Elo/MMR public block and no visible public `snapshot` wording in historical HTML.
- Regression script confirms recent-card code includes `Ver partida` and `Ver detalles`.
- Regression script confirms recent-card code does not trust legacy `source_url` fallback.
- Regression script confirms external detail links keep `target="_blank"` and `rel="noopener noreferrer"`.
- `git diff --name-only` and `git status --short` were reviewed. Changed files match the expected scope: validation scripts and this task file.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split follow-up work into a new task if the scope grows.
