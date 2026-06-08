---
id: TASK-182-add-global-ranking-frontend-page
title: Add global ranking frontend page
status: done
type: frontend
team: Frontend Senior
supporting_teams:
  - Experto en interfaz
  - Disenador grafico
  - Backend Senior
roadmap_item: foundation
priority: high
---

# TASK-182-add-global-ranking-frontend-page - Add global ranking frontend page

## Goal

Create a dedicated Ranking page that displays public top lists by timeframe, server, metric and limit, consuming the backend support built in TASK-181.

## Context

Ranking is now separated from Stats in both navigation and interaction model. Stats remains player-centric; Ranking is list-centric and links back to Stats only when a user wants individual lookup.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `docs/global-ranking-page-plan.md`
- `frontend/index.html`
- `frontend/historico.html`
- `frontend/stats.html`
- `frontend/assets/js/stats.js`
- `frontend/assets/css/styles.css`
- `backend/app/routes.py`
- `ai/tasks/done/TASK-181-add-global-ranking-backend-support.md`

## Expected Files Modified

- `frontend/ranking.html`
- `frontend/assets/js/ranking.js`
- `frontend/assets/css/styles.css`
- `frontend/index.html`
- `ai/tasks/done/TASK-182-add-global-ranking-frontend-page.md`

## Constraints Verified

- No backend files were changed in this task.
- No new endpoints were added.
- No database changes were made.
- No Elo/MMR reactivation.
- No Comunidad Hispana #03 reintroduction.
- Stats behavior was left intact.
- Implementation stayed in vanilla HTML/CSS/JS.

## Outcome

- Added `frontend/ranking.html` as a dedicated Ranking page.
- Added `frontend/assets/js/ranking.js` to:
  - check backend health
  - request `/api/ranking`
  - switch between weekly, monthly and annual flows
  - render loading, offline, no-data, annual-missing and controlled-error states
- Extended shared styling in `frontend/assets/css/styles.css` for:
  - ranking filter layout
  - ranking metadata cards
  - ranking table
  - ranking empty state
- Added a minimal `Ranking` entry point in `frontend/index.html`.
- Kept cross-linking minimal by linking from Ranking to Stats without modifying `stats.html`.

## Validation

Executed:

- `node --check frontend/assets/js/ranking.js`
- `node --check frontend/assets/js/stats.js`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- Local static serving with `python -m http.server`

HTTP checks:

- `ranking.html` -> `200`
- `assets/js/ranking.js` -> `200`
- `stats.html` -> `200`

Offline-state check:

- Backend was unavailable at `http://127.0.0.1:8000`.
- A headless Edge DOM capture of `ranking.html` showed `#ranking-backend-state` rendered as `Backend no disponible`, confirming the intended offline fallback path.

Known limitation:

- Live successful ranking calls could not be verified through a running backend during this task because the backend was not available over HTTP in the environment.

## Recommended Follow-up

- Add a dedicated ranking frontend regression script so `ranking.html` state coverage is validated alongside existing historical and stats checks.
