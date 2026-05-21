---
id: TASK-145
title: Add match detail player table controls
status: done
type: frontend
team: Frontend Senior
supporting_teams: []
roadmap_item: foundation
priority: medium
---

# TASK-145 - Add match detail player table controls

## Goal

Keep inactive match-detail player rows low priority and add compact search, team
filtering and sorting controls to the player table.

## Context

The internal match detail page already exposes a compact player stat table and
expandable detail panels. Profile and lobby snapshot rows with no team and no
match activity can currently compete with real participants in that table, and
larger matches need client-side controls to find and compare players without
changing backend contracts.

## Steps

1. Inspect the listed files first.
2. Apply only the scoped match-detail player table change.
3. Validate the result and document relevant findings.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/frontend-senior.md`
- `frontend/historico-partida.html`
- `frontend/assets/js/historico-partida.js`
- `frontend/assets/css/historico-scoreboard-detail.css`

## Expected Files to Modify

- `frontend/historico-partida.html`
- `frontend/assets/js/historico-partida.js`
- `frontend/assets/css/historico-scoreboard-detail.css`
- `ai/tasks/done/TASK-145-match-detail-player-table-controls.md`

## Constraints

- Preserve the compact main columns and click-to-open player detail panels.
- Keep Aliados and Eje row treatments and badges.
- Filter team labels through the existing localized team mapping.
- Do not reintroduce expanded stats, event data or backend changes as table columns.
- Keep frontend behavior responsive and browser-loaded without new dependencies.

## Validation

- `node --check frontend/assets/js/historico-partida.js`
- `node --check frontend/assets/js/historico.js`
- `node --check frontend/assets/js/historico-recent-live.js`
- `docker compose build --no-cache frontend`
- `docker compose up -d frontend`
- Manual match-detail verification for default inactive ordering, stat sorting,
  name search, team filters and panel close-on-filter behavior.
- Review `git diff --name-only` against task scope.

## Outcome

Implemented. The match-detail player table now has client-side player-name
search, localized team filtering, sort-column and direction controls above the
existing compact table. Default row ordering keeps active participants first,
orders them by kills descending, deaths ascending and name, and sends rows with
unknown team, zero combat stats and no expanded match stats to the bottom.
Numeric explicit sorts retain that inactive demotion, while name/team sorts can
compare all visible rows and inactive rows stay visually muted.

The table continues to render row/detail pairs together after control changes.
Player-name clicks still open the existing expanded detail panel, and search or
team-filter changes close any open panel before the visible rows refresh.

Validation passed:

- `node --check frontend/assets/js/historico-partida.js`
- `node --check frontend/assets/js/historico.js`
- `node --check frontend/assets/js/historico-recent-live.js`
- `docker compose build --no-cache frontend`
- `docker compose up -d frontend`
- Rendered fallback verification on
  `historico-partida.html?server=comunidad-hispana-02&match=comunidad-hispana-02%3A1779315955%3A1779319098%3Akharkovwarfare`
  for control visibility, row detail opening, close-on-search, player-name
  search, Aliados/Eje/Sin equipo filters and Jugador/Equipo/K/D/TK/K-D/KPM
  sort selectors.
- Rendered default ordering on the provided match showed 18 active rows before
  44 inactive/no-team rows; visible zero-kill rows with deaths stayed in the
  active block before the inactive rows.
- Desktop and mobile controls screenshots were inspected outside the repo.

Notes:

- Browser plugin runtime tools were not exposed by tool discovery in this
  session, so rendered validation used a temporary local headless
  Chrome/Selenium fallback outside the repository.
- Browser console output on the tested route only reported the existing missing
  `favicon.ico` request.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
