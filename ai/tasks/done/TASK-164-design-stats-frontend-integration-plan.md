---
id: TASK-164
title: Design stats frontend integration plan
status: done
type: frontend
team: Frontend Senior
supporting_teams: []
roadmap_item: foundation
priority: medium
---

# TASK-164 - Design stats frontend integration plan

## Goal

Define how the future Stats section will be integrated in the frontend before implementing it.

## Context

The backend already exposes the stats query contract used by this plan:

- `GET /api/stats/players/search?q=<query>`
- `GET /api/stats/players/{player_id}`

This task is documentation only. No backend or implementation changes.

## Steps

1. Read all files listed in `Files to Read First` from the workspace first.
2. Define an integration strategy that preserves current navigation and behavior of Inicio / Historico / Partida actual.
3. Describe V1 components, endpoint usage and UI state transitions.
4. Propose minimal visual reuse from existing styles and assets.
5. Define future implementation files and order.
6. Record any known limitations and an open follow up recommendation.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `docs/stats-section-functional-plan.md`
- `frontend/index.html`
- `frontend/historico.html`
- `frontend/assets/css/styles.css`
- `frontend/assets/js/main.js`
- `backend/app/routes.py`
- `backend/app/payloads.py`

## Expected Files to Modify

- `docs/stats-frontend-integration-plan.md`
- `ai/tasks/done/TASK-164-design-stats-frontend-integration-plan.md`

## Constraints

- Keep current repo structure intact.
- Do not implement any frontend behavior now.
- Do not modify backend.
- No migrations.
- No ranking anual.
- No Elo/MMR reactivation.
- No Comunidad Hispana #03 reintro.
- Do not touch `frontend/assets/js/partida-actual.js`.
- Do not touch `frontend/assets/img/clans/bxb.png`.
- Do not add frameworks.
- Keep change size minimal and verified.

## Validation

- Confirm only documentation and task file were created/modified.
- Run `git diff --name-only`.
- Record that no automated tests are applicable for this docs-only task.

## Outcome (for worker)

- Outcome:
  - Archivos creados/modificados:
    - `docs/stats-frontend-integration-plan.md`
    - `ai/tasks/done/TASK-164-design-stats-frontend-integration-plan.md`
    - Movimiento de `ai/tasks/pending/TASK-164-design-stats-frontend-integration-plan.md` a `ai/tasks/done/...`.
  - Validación realizada:
    - `git status --short --untracked-files=all` verificado.
    - `git diff --name-only` verificado.
    - Confirmado que `docs/stats-frontend-integration-plan.md` existe y contiene el plan solicitado.
  - Al ser una task documental:
    - No se ejecutan tests automáticos.
    - No aplica validación funcional automatizada.
  - Restricciones verificadas:
    - No se tocaron archivos de backend.
    - No se implementó frontend.
    - No se tocaron `frontend/assets/js/partida-actual.js`.
    - No se tocó `frontend/assets/img/clans/bxb.png`.
