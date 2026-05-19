---
id: TASK-127
title: Update recent match link actions
status: pending
type: frontend
team: Frontend Senior
supporting_teams:
  - Experto en interfaz
  - Backend Senior
roadmap_item: rcon-full-data
priority: medium
---

# TASK-127 - Update recent match link actions

## Goal

Update recent match cards so internal details and external scoreboard links are prioritized clearly and safely.

## Background

Recent match cards should always offer internal details when supported and only show public scoreboard links when the backend provides a safe `match_url`. RCON remains primary, and the UI must not expose stale wording or paused Elo/MVP content.

## Constraints

- Do not reintroduce Comunidad Hispana #03.
- Do not show paused Elo/MVP blocks.
- Do not expose public "snapshot" wording.
- Do not show broken external links.
- Do not change backend behavior unless strictly required and justified.
- Preserve HLL Vietnam tactical, sober styling.

## Allowed Changes

- `frontend/assets/js/historico.js`
- `frontend/assets/js/historico-recent-live.js` if needed
- minimal CSS only if needed for the action layout
- this task file when moving it through the workflow

## Implementation Requirements

- Work from a dedicated branch for this task.
- Read first:
  - `AGENTS.md`
  - `ai/architecture-index.md`
  - `ai/repo-context.md`
  - `ai/orchestrator/frontend-senior.md`
  - `ai/orchestrator/ui-expert.md`
  - `frontend/historico.html`
  - `frontend/assets/js/historico.js`
  - `frontend/assets/js/historico-recent-live.js`
  - `frontend/assets/css/historico.css`
- Show score when result exists.
- Show `Ver detalles` internal link for every match with internal detail support.
- Show `Ver scoreboard` or `Ver partida externa` only when `match_url` exists.
- If a match has no score yet, show `En curso` or `Resultado no disponible` instead of `---` when a better status exists.
- Keep cards compatible with existing API fallback payloads.

## Validation Commands

- `node --check frontend/assets/js/historico.js`
- `node --check frontend/assets/js/historico-recent-live.js` if changed
- `docker compose up -d --build backend frontend`

## Manual Verification Steps

- Open `http://localhost:8080/historico.html`.
- Confirm scores appear where available.
- Confirm internal detail link is visible when supported.
- Confirm external scoreboard link appears only when `match_url` exists.
- Confirm there is no Elo/MVP/server #03/snapshot wording.
- Confirm `git diff --name-only` matches the allowed scope.

## Git Requirements

- Create a dedicated branch for this task, for example `codex/task-127-recent-match-actions`.
- Run relevant validation before committing.
- Stage only intended files.
- Commit the completed implementation.
- Push the branch to origin.
