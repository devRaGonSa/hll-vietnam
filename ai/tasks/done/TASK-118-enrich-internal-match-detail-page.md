---
id: TASK-118
title: Enrich internal match detail page
status: done
type: frontend
team: Frontend Senior
supporting_teams:
  - Backend Senior
  - Experto en interfaz
roadmap_item: historical-ui
priority: medium
---

# TASK-118 - Enrich internal match detail page

## Goal

Make the internal match detail page more useful when no scoreboard link exists.

## Context

The internal match detail page is the safe fallback for RCON synthetic matches and any match without a trusted external scoreboard URL. It should present all available local data clearly without trying to clone the external scoreboard site.

Use branch:

- `plan/scoreboard-match-linking-tasks`

## Steps

1. Work from this task only after moving it to `ai/tasks/in-progress/`.
2. Inspect the listed files before changing anything.
3. Show all available RCON/persisted fields clearly:
   - server
   - map
   - start
   - end
   - duration
   - average players
   - peak players
   - sample count
   - result if available
   - capture basis
   - capabilities
4. If player-level data exists in persisted scoreboard storage, show a simple player table.
5. If player-level data is unavailable, show a clear friendly message.
6. Keep the visual style consistent with HLL Vietnam's sober military/Vietnam tactical identity.
7. Do not attempt to fully clone the scoreboard site yet.
8. Keep the page graceful for partial RCON data.
9. Validate the result.
10. Move this task to `ai/tasks/done/` only after validation is complete and document the outcome in this file.
11. Commit and push the completed implementation branch.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/frontend-senior.md`
- `ai/orchestrator/ui-expert.md`
- `ai/orchestrator/backend-senior.md`
- `frontend/historico-partida.html`
- `frontend/assets/js/historico-partida.js`
- `frontend/assets/css/historico.css`
- `backend/app/routes.py`
- `backend/app/historical_storage.py`
- `backend/app/rcon_historical_read_model.py`
- `scripts/run-integration-tests.ps1`

## Expected Files to Modify

- `frontend/historico-partida.html`
- `frontend/assets/js/historico-partida.js`
- possibly `frontend/assets/css/historico.css`
- possibly `backend/app/routes.py`
- possibly `backend/app/historical_storage.py`
- possibly `backend/app/rcon_historical_read_model.py`
- this task file, moved to `ai/tasks/done/`

If additional files become necessary, explain why in the task outcome and commit message.

## Expected Files Not to Modify

- historical ingestion policy/config
- database migrations unless absolutely required and justified
- persisted data
- local `.env`
- Docker/Compose config
- Elo/MMR implementation files
- unrelated frontend pages

## Constraints

- Do not reintroduce Comunidad Hispana #03.
- Do not reintroduce paused MVP/Elo UI.
- Do not change historical ingestion policy.
- Do not add real credentials.
- Do not modify local `.env`.
- Do not delete persisted data, migrations, backend endpoints or historical ingestion code.
- Do not use the public word "snapshot" in user-facing UI.
- Keep the page focused on local/internal match detail presentation.

## Validation

Before completing the task, run and document:

- `git status`
- `node --check frontend/assets/js/historico-partida.js`
- Python compile checks for touched backend modules, if any
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- served or static check confirming the internal detail page renders partial RCON data gracefully
- served or static check confirming persisted scoreboard details render richer data when available
- check confirming a friendly message appears when player-level data is unavailable
- check confirming no Comunidad Hispana #03 appears
- check confirming paused MVP/Elo UI remains absent
- check confirming no public "snapshot" wording appears
- `git diff --name-only` and confirmation that changed files match the expected scope

If a configured validation command cannot be run, document the exact reason in the outcome.

## Commit And Push Requirements

- Run validation before committing.
- Run `git status`.
- Stage only intended files.
- Commit with message: `feat: enrich internal match detail page`
- Push the branch to origin.
- Do not leave completed work only in local.

## Outcome

Completed.

Implementation decisions:

- Enriched persisted public-scoreboard match detail payloads with `players` rows from local historical storage.
- Added an empty `players` list for RCON competitive-window details so the frontend can treat partial RCON data gracefully.
- Expanded the internal detail page summary to show server, map, start, end, duration, average players, peak players, sample count, result, capture basis and capabilities.
- Added a simple player table for persisted player-level rows.
- Added a friendly unavailable message for RCON windows or persisted matches without player rows.
- Kept the page as a local/internal detail view and did not attempt to clone the external scoreboard.

Validation performed:

- `git status --short --branch` confirmed branch `plan/scoreboard-match-linking-tasks`.
- `node --check frontend/assets/js/historico-partida.js` passed.
- `python -m compileall backend/app` passed.
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1` passed.
- Static Node render check confirmed partial RCON data renders gracefully with sample count, peak players and capability fields.
- Static Node render check confirmed persisted scoreboard details render a player table when player rows are present.
- Static Node render check confirmed the friendly no-player-data message appears when player-level data is unavailable.
- Static Node render check confirmed no `Comunidad Hispana #03` appears.
- Static Node render check confirmed paused MVP/Elo UI remains absent in the checked detail states.
- Static Node render check confirmed no public `snapshot` wording appears in the checked detail states.
- `$env:PYTHONPATH='backend'; python -m unittest backend.tests.test_scoreboard_match_links` passed after backend payload changes.
- `git diff --name-only` and `git status --short` were reviewed. Changed files match the expected scope: match detail HTML/JS/CSS, backend detail payloads and this task file.

Note:

- The focused backend unittest still emits existing SQLite `ResourceWarning` messages from the repository connection helper pattern during forced cleanup, but all assertions pass.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split follow-up work into a new task if the scope grows.
