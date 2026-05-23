---
id: TASK-143
title: Player table hover stats panel
status: done
type: frontend
team: Frontend Senior
supporting_teams: [Experto en interfaz]
roadmap_item: foundation
priority: high
---

# TASK-143 - Player table hover stats panel

## Goal

Make the internal historical match detail player table more compact by moving expanded per-player statistics into an accessible hover/focus/click details panel.

## Context

The detail page player table currently includes detailed columns for weapons, most killed and death by. The desired scoreboard-like UX keeps the table focused on player/team/core combat metrics and reveals expanded statistics per row.

## Steps

1. Inspect the current match detail renderer and scoreboard detail CSS.
2. Reduce the visible table columns to Jugador, Equipo, K, D, TK, K/D and KPM.
3. Add accessible row hover/focus/click expanded panels with weapons, most killed, death by and direct matchups.
4. Preserve team styling, scoreboard link behavior and forbidden hidden sections.
5. Validate syntax, frontend build/container and rendered behavior.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/frontend-senior.md`
- `frontend/historico-partida.html`
- `frontend/assets/js/historico-partida.js`
- `frontend/assets/css/historico-scoreboard-detail.css`
- `frontend/assets/css/historico.css`

## Expected Files to Modify

- `frontend/historico-partida.html`
- `frontend/assets/js/historico-partida.js`
- `frontend/assets/css/historico-scoreboard-detail.css`
- `ai/tasks/done/TASK-143-player-table-hover-stats-panel.md`

## Constraints

- Do not modify backend unless absolutely necessary.
- Do not modify recent match card layout.
- Do not reintroduce timeline/events/confidence/source/base or Elo/MVP blocks.
- Preserve Aliados/Eje/No disponible visual distinction.

## Validation

- `node --check frontend/assets/js/historico-partida.js`
- `node --check frontend/assets/js/historico.js`
- `node --check frontend/assets/js/historico-recent-live.js`
- `docker compose build --no-cache frontend`
- `docker compose up -d frontend`
- Browser verification on `historico-partida.html`
- Browser smoke verification on `historico.html`

## Outcome

Implemented. The match detail player table now shows only Jugador, Equipo, K, D, TK, K/D and KPM. Expanded player statistics are rendered in per-player detail panels that open on row hover, keyboard focus/Enter and touch/click via an accessible info control. The panel includes the player/team summary, weapons, most killed, death by and direct matchup balance derived from most_killed and death_by.

Validation passed:

- `node --check frontend/assets/js/historico-partida.js`
- `node --check frontend/assets/js/historico.js`
- `node --check frontend/assets/js/historico-recent-live.js`
- `docker compose build --no-cache frontend`
- `docker compose up -d frontend`
- Browser verification on `historico-partida.html` for `comunidad-hispana-02:1779178461:1779183861:carentanwarfare`
- Browser smoke verification on `historico.html?nocache=player-table-hover`

Notes:

- Browser plugin runtime tools were not exposed by tool discovery in this session, so rendered validation used local Chrome/Selenium fallback.
