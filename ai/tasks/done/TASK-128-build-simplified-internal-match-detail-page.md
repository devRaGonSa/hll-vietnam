---
id: TASK-128
title: Build simplified internal match detail page
status: done
type: frontend
team: Frontend Senior
supporting_teams:
  - Experto en interfaz
  - Backend Senior
roadmap_item: rcon-full-data
priority: high
---

# TASK-128 - Build simplified internal match detail page

## Goal

Make `frontend/historico-partida.html` useful as a lightweight internal scoreboard-style match detail page backed by the internal RCON detail API.

## Background

When a safe public scoreboard link is unavailable, users should still be able to inspect the match through HLL Vietnam. The page should show summary, score, winner, factions/teams if available, player stats and a relevant event timeline without advanced charts.

## Constraints

- Do not add advanced charts or graphs.
- Do not expose raw player IDs unless required by an already approved API contract.
- Do not reintroduce Comunidad Hispana #03.
- Do not show paused Elo/MVP blocks.
- Do not expose public "snapshot" wording.
- Preserve HLL Vietnam styling.

## Allowed Changes

- `frontend/historico-partida.html`
- `frontend/assets/js/historico-partida.js`
- `frontend/assets/css/historico.css` if needed
- this task file when moving it through the workflow

## Implementation Requirements

- Work from a dedicated branch for this task.
- Read first:
  - `AGENTS.md`
  - `ai/architecture-index.md`
  - `ai/repo-context.md`
  - `ai/orchestrator/frontend-senior.md`
  - `ai/orchestrator/ui-expert.md`
  - `frontend/historico-partida.html`
  - `frontend/assets/js/historico-partida.js`
  - `frontend/assets/css/historico.css`
  - backend match detail API code from TASK-124
- Use the internal match detail API.
- Display map, server, result, winner, game mode, start/end time, source/confidence and external scoreboard link when available.
- Add player stats table with player, team, kills, deaths, teamkills, K/D, top weapons, most killed and death by.
- Add event/timeline section for match start, match end, kill sample/recent kills and useful team switches.
- Handle partial or missing data gracefully with controlled empty states.
- Keep implementation in vanilla JavaScript.

## Validation Commands

- `node --check frontend/assets/js/historico-partida.js`
- `docker compose up -d --build backend frontend`

## Manual Verification Steps

- Open a match detail from the recent matches list.
- Verify a match with AdminLog kill data shows at least one kill/weapon row.
- Verify a match without player stats shows a controlled empty state.
- Confirm no Elo/MVP/server #03/snapshot wording appears.
- Confirm `git diff --name-only` matches the allowed scope.

## Git Requirements

- Create a dedicated branch for this task, for example `codex/task-128-internal-match-detail-page`.
- Run relevant validation before committing.
- Stage only intended files.
- Commit the completed implementation.
- Push the branch to origin.

## Outcome

Reworked `frontend/historico-partida.html` and `frontend/assets/js/historico-partida.js` into a simplified internal scoreboard-style detail page backed by `/api/historical/matches/detail?server=...&match=...`.

The page correctly URL-encodes materialized RCON match ids containing colons, displays match summary cards, source/confidence, optional external scoreboard action, player stats with K/D, top weapons, most-killed/death-by summaries, and timeline event counts. It handles missing player/timeline data with controlled empty states and does not expose raw player IDs.

## Validation Result

- Passed: `node --check frontend/assets/js/historico-partida.js`
- Passed: `docker compose up -d --build backend frontend`
- Browser-verified detail navigation from `http://localhost:8080/historico.html`.
- Browser-verified known materialized match detail renders at `http://localhost:8080/historico-partida.html?server=comunidad-hispana-02&match=comunidad-hispana-02%3A1779178461%3A1779183861%3Acarentanwarfare`.
- Confirmed AntonioPruna renders with 1 kill, 0 deaths and `M1 GARAND`.
- Confirmed the victim row renders 1 death and `death_by` AntonioPruna.
- Confirmed timeline/event counts render.
- Confirmed no visible Elo/MVP/Comunidad Hispana #03/snapshot wording appears.
