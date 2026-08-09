---
id: TASK-141
title: Keep recent match actions inline
status: done
type: frontend
team: Frontend Senior
supporting_teams: [Experto en interfaz]
roadmap_item: foundation
priority: medium
---

# TASK-141 - Keep recent match actions inline

## Goal

Keep the result chip and `Ver detalles` action on the same horizontal row in recent match cards.

## Context

The recent matches cards already use the clean structure, but the right-side action controls can wrap vertically on desktop. The fix should preserve the current recent card structure, keep public scoreboard links hidden only in the recent list, and avoid affecting `historico-partida.html`.

## Steps

1. Inspect the listed files first.
2. Apply a scoped CSS fix for recent match card actions.
3. Validate syntax, Docker frontend build/start and rendered behavior.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/frontend-senior.md`
- `docs/decisions.md`
- `frontend/historico.html`
- `frontend/assets/css/historico.css`
- `frontend/assets/js/historico.js`
- `frontend/assets/js/historico-recent-live.js`

## Expected Files to Modify

- `frontend/assets/css/historico.css`
- `ai/tasks/done/TASK-141-keep-recent-match-actions-inline.md`

## Constraints

- Do not modify backend.
- Do not affect the detail page scoreboard link.
- Do not show `Ver partida` in recent cards.
- Do not reintroduce raw match ids, Estado, source or RCON debug text.
- Keep the dark HLL Vietnam theme.

## Validation

- `node --check frontend/assets/js/historico.js`
- `node --check frontend/assets/js/historico-recent-live.js`
- `node --check frontend/assets/js/historico-partida.js`
- `docker compose build --no-cache frontend`
- `docker compose up -d frontend`
- Browser verification on `http://localhost:8080/historico.html?nocache=actions-inline`
- Browser verification of the supplied detail-page scoreboard behavior

## Outcome

Implemented a scoped CSS fix for recent match actions:

- Widened the clean recent-card action grid track to fit result chip plus detail link on desktop.
- Forced `#recent-matches-list .historical-match-card__actions` to use row-direction, no-wrap flex layout on desktop.
- Kept mobile/tablet wrapping available under the existing responsive breakpoint.
- Kept the public scoreboard link hidden only under `#recent-matches-list`.

Validation completed:

- `node --check frontend/assets/js/historico.js`
- `node --check frontend/assets/js/historico-recent-live.js`
- `node --check frontend/assets/js/historico-partida.js`
- `docker compose build --no-cache frontend`
- `docker compose up -d frontend`
- Browser verification on `http://localhost:8080/historico.html?nocache=actions-inline`
- Browser verification on the supplied `historico-partida.html` detail URL

Manual verification found 10 recent cards, 10 visible `Ver detalles` links, zero visible `Ver partida` links in the recent list, no forbidden internal/debug text, all result chips inline with `Ver detalles`, all result states present, no framework overlay, no relevant console issues, and a visible scoreboard link on the detail page.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
