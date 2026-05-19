---
id: TASK-117
title: Prioritize match link UX
status: done
type: frontend
team: Frontend Senior
supporting_teams:
  - Experto en interfaz
  - Backend Senior
roadmap_item: historical-ui
priority: high
---

# TASK-117 - Prioritize match link UX

## Goal

Adjust the historical UI link priority so safe external scoreboard links are primary when available, and internal details remain the fallback.

## Context

Recent cards currently show internal `Ver detalles` links when no safe external match URL exists. After persisted and correlated `match_url` support is improved, the UI must prefer safe external scoreboard links without making unsafe assumptions.

Use branch:

- `plan/scoreboard-match-linking-tasks`

## Steps

1. Work from this task only after moving it to `ai/tasks/in-progress/`.
2. Inspect the listed files before changing anything.
3. On recent match cards:
   - If safe external `match_url` exists, show primary `Ver partida`.
   - If no `match_url` exists, show internal `Ver detalles`.
4. On the internal match detail page:
   - If `match_url` exists, show `Abrir en scoreboard`.
   - If no `match_url` exists, keep internal details only.
5. Ensure external links use `target="_blank"` and `rel="noopener noreferrer"`.
6. Do not show both buttons as competing primary actions unless the existing design clearly requires it.
7. Preserve the current sober military/Vietnam tactical visual style.
8. Validate the result.
9. Move this task to `ai/tasks/done/` only after validation is complete and document the outcome in this file.
10. Commit and push the completed implementation branch.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/frontend-senior.md`
- `ai/orchestrator/ui-expert.md`
- `frontend/historico.html`
- `frontend/assets/js/historico.js`
- `frontend/assets/css/historico.css`
- `frontend/historico-partida.html`
- `frontend/assets/js/historico-partida.js`
- `backend/app/routes.py`
- `scripts/run-integration-tests.ps1`

## Expected Files to Modify

- `frontend/assets/js/historico.js`
- possibly `frontend/assets/css/historico.css`
- possibly `frontend/historico-partida.html`
- possibly `frontend/assets/js/historico-partida.js`
- this task file, moved to `ai/tasks/done/`

If additional files become necessary, explain why in the task outcome and commit message.

## Expected Files Not to Modify

- backend historical ingestion modules
- database migrations
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
- Do not fabricate or transform external URLs in the frontend; trust only backend-provided `match_url`.

## Validation

Before completing the task, run and document:

- `git status`
- `node --check frontend/assets/js/historico.js`
- `node --check frontend/assets/js/historico-partida.js` if present
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- served or static HTML check confirming recent cards show `Ver partida` when `match_url` exists
- served or static HTML check confirming recent cards show `Ver detalles` when `match_url` is absent
- served or static HTML check confirming detail page shows `Abrir en scoreboard` when `match_url` exists
- served or static HTML check confirming no Comunidad Hispana #03 appears
- served or static HTML check confirming paused MVP/Elo UI remains absent
- check confirming external links include `target="_blank"` and `rel="noopener noreferrer"`
- `git diff --name-only` and confirmation that changed files match the expected scope

If a configured validation command cannot be run, document the exact reason in the outcome.

## Commit And Push Requirements

- Run validation before committing.
- Run `git status`.
- Stage only intended files.
- Commit with message: `chore: prioritize match link ux`
- Push the branch to origin.
- Do not leave completed work only in local.

## Outcome

Completed.

Implementation decisions:

- Recent match cards now trust only backend-provided `match_url` for the external primary action.
- Existing priority remains: `Ver partida` when `match_url` exists, otherwise internal `Ver detalles`.
- Existing detail-page behavior already matched the task: it shows `Abrir en scoreboard` only when `match_url` exists and uses `target="_blank"` plus `rel="noopener noreferrer"`.
- No CSS or markup change was needed.

Validation performed:

- `git status --short --branch` confirmed branch `plan/scoreboard-match-linking-tasks`.
- `node --check frontend/assets/js/historico.js` passed.
- `node --check frontend/assets/js/historico-partida.js` passed.
- Static Node render check confirmed recent cards show `Ver partida` when `match_url` exists.
- Static Node render check confirmed recent cards show `Ver detalles` when `match_url` is absent.
- Static Node render check confirmed recent external links include `target="_blank"` and `rel="noopener noreferrer"`.
- Static Node render check confirmed the detail-page action shows `Abrir en scoreboard` when `match_url` exists and hides when absent.
- Static Node render check confirmed no `Comunidad Hispana #03` appears in the checked match-card states.
- Static Node render check confirmed paused MVP/Elo UI does not surface in the checked match-card states.
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1` passed.
- `git diff --name-only` and `git status --short` were reviewed. Changed files match the expected scope: `frontend/assets/js/historico.js` and this task file.

Note:

- The Browser plugin was not available as a callable browser automation tool in this session, so validation used the task-allowed static HTML/JS render checks instead of an in-browser screenshot pass.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split follow-up work into a new task if the scope grows.
