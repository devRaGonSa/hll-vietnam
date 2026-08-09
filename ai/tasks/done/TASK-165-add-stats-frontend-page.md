---
id: TASK-165
title: Add stats frontend page
status: done
type: frontend
team: Frontend Senior
supporting_teams: []
roadmap_item: foundation
priority: medium
---

# TASK-165 - Add stats frontend page

## Goal

Implement the first frontend version of the new `Stats` section using existing backend endpoints.

## Context

TASK-163 added backend support for player search and personal stats payloads under `/api/stats`.

- `GET /api/stats/players/search?q=<query>`
- `GET /api/stats/players/{player_id}`

This task only covers frontend consumption and does not modify backend code.

## Steps

1. Read all files listed in `Files to Read First` before creating files.
2. Create `frontend/stats.html` with the V1 section layout.
3. Create `frontend/assets/js/stats.js` with vanilla JS state and API handlers:
   - search call
   - result rendering
   - player selection
   - profile request
4. Add Stats navigation entry in the shared shell used by landing/history without breaking existing sections.
5. Wire the following state blocks:
   - loading
   - error
   - sin resultados
   - jugador sin estadisticas
   - backend no disponible
6. Add reserved annual ranking top 20 block (UI placeholder only, no backend call).
7. Update CSS only if required to support the new page.
8. Validate manually (and with integration tests when available) and record results in task outcome.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `docs/stats-section-functional-plan.md`
- `docs/stats-frontend-integration-plan.md`
- `frontend/index.html`
- `frontend/historico.html`
- `frontend/assets/css/styles.css`
- `frontend/assets/js/main.js`
- `backend/app/routes.py`
- `backend/app/payloads.py`

## Expected Files to Modify

- `frontend/stats.html`
- `frontend/assets/js/stats.js`
- `frontend/index.html`
- `frontend/historico.html`
- `frontend/assets/css/styles.css` (only if necessary)

## Constraints

- No backend changes.
- No migrations.
- No annual ranking real endpoint consumption in V1.
- No changes to historical workers.
- No Elo/MMR reactivation.
- Do not touch `frontend/assets/js/partida-actual.js`.
- Do not touch `frontend/assets/img/clans/bxb.png`.
- Do not reintroduce Comunidad Hispana #03.
- Keep HTML/CSS/JS vanilla (no frameworks).
- Preserve existing HLL Vietnam identity (military, Vietnam, tactical, sober).
- Keep scope small and reviewable.

## Validation

Before task completion:

- Validate `frontend/stats.html` loads and executes without visible JS runtime errors.
- Validate search flow against local backend (if running):
  - query -> backend search
  - select player -> personal profile
- Validate empty/error/unsupported states, including backend unreachable.
- Validate annual placeholder is rendered without backend call.
- Run `scripts/run-integration-tests.ps1` when applicable.
- Run `git diff --name-only` and confirm only expected files changed for this task.
- Confirm `frontend/assets/js/partida-actual.js` and `frontend/assets/img/clans/bxb.png` were not touched.

## Outcome

- Archivos modificados:
  - `frontend/stats.html`
  - `frontend/assets/js/stats.js`
  - `frontend/index.html`
  - `frontend/historico.html`
  - `frontend/assets/css/styles.css`
- Endpoints consumidos:
  - `GET /api/stats/players/search?q=<query>`
  - `GET /api/stats/players/{player_id}`
- Validaciones realizadas:
  - Validación de carga estática:
    - se sirvió `frontend/stats.html` desde `python -m http.server` (status 200),
    - se sirvió `frontend/assets/js/stats.js` (status 200).
  - Validación del flujo con backend local:
    - `GET /health` en `http://127.0.0.1:8000` no respondió (backend sin servicio en este momento),
    - se dejó implementada la ruta de error `Backend no disponible`,
    - no fue posible validar query corta, query normal y no-resultados contra backend en esta pasada.
  - Validación de tests:
    - `scripts/run-integration-tests.ps1` ejecutado y finalizó con éxito.
- Limitaciones conocidas:
  - backend local no estaba levantado al momento de validación de integración,
  - no se validó ranking anual real ni endpoint de ese dominio por restricción de alcance V1.
- Siguiente task recomendada: `TASK-166` diseño/implementación BDD de ranking anual top 20 (snapshot).

## Change Budget

- Prefer fewer than 5 modified files (allowing one extra if CSS adjustments are needed).
- Keep changes concise and aligned with V1 scope.
