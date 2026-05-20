---
id: TASK-139
title: Align recent match cards
status: done
type: frontend
team: Frontend Senior
supporting_teams: [Experto en interfaz]
roadmap_item: foundation
priority: medium
---

# TASK-139 - Align recent match cards

## Goal

Make the recent match cards in `historico.html` use consistent metadata columns and a right-aligned action area across static and dynamic renderers.

## Context

The recent matches list should stay compact and clean while preserving the HLL Vietnam dark tactical theme. It must not show raw match IDs, internal status/source/debug text, or the public scoreboard action in the list. The public scoreboard link remains available on the match detail page.

## Steps

1. Inspect the listed files first.
2. Normalize the static and dynamic recent card markup.
3. Use CSS grid for deterministic metadata/action alignment.
4. Validate with syntax checks and the requested Docker frontend checks.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/frontend-senior.md`
- `frontend/historico.html`
- `frontend/assets/js/historico.js`
- `frontend/assets/js/historico-recent-live.js`
- `frontend/assets/css/historico.css`

## Expected Files to Modify

- `frontend/assets/js/historico.js`
- `frontend/assets/js/historico-recent-live.js`
- `frontend/assets/css/historico.css`
- `ai/tasks/done/TASK-139-align-recent-match-cards.md`

## Constraints

- Keep the change minimal.
- Preserve the HLL Vietnam visual identity.
- Do not introduce frameworks or backend changes.
- Do not alter detail page scoreboard link behavior.
- Do not remove `match_url` support.

## Validation

- `node --check frontend/assets/js/historico-recent-live.js`
- `node --check frontend/assets/js/historico.js`
- `node --check frontend/assets/js/historico-partida.js`
- `docker compose build --no-cache frontend`
- `docker compose up -d frontend`
- Manual verification on `http://localhost:8080/historico.html?nocache=alignment`

## Outcome

Implemented a shared clean recent-card structure for the static snapshot renderer and dynamic live renderer. The recent list now shows only map title, Servidor, Cierre, Jugadores, Marcador and right-aligned actions. The public scoreboard action keeps its `match_url` link in markup with a recent-list-only hidden class, while the detail page scoreboard action remains visible.

Validation completed:

- `node --check frontend/assets/js/historico-recent-live.js`
- `node --check frontend/assets/js/historico.js`
- `node --check frontend/assets/js/historico-partida.js`
- `docker compose build --no-cache frontend`
- `docker compose up -d frontend`
- Browser verification on `http://localhost:8080/historico.html?nocache=alignment`
- Browser verification on the supplied `historico-partida.html` detail URL

Manual verification found 13 recent cards, 13 visible `Ver detalles` links, zero visible `Ver partida` links in the recent list, no forbidden internal/debug text in the recent list, 0px column spread across all desktop metadata columns, and a visible public scoreboard link on the detail page.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
