---
id: TASK-153
title: Fix current match live projection
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Frontend Senior
roadmap_item: rcon-full-data
priority: high
---

# TASK-153 - Fix current match live projection

## Goal

Project trusted live RCON match data onto the current-match page without
misrepresenting player population or stale AdminLog kills as current activity.

## Context

`/api/current-match` currently reads through `/api/servers`. The direct RCON
sample already contains `game_mode` and scores, but the server snapshot
projection drops those richer live fields. Direct RCON `playerCount` is also
currently reporting `0` while manual public scoreboard observation shows `1`,
so that population value must be labeled unverified instead of shown as a
confident live count.

## Steps

1. Inspect the listed current-match, live RCON and AdminLog files first.
2. Keep the trusted current scoreboard URL mapping and unsupported-server
   guards intact.
3. Rework the live payload, kill-feed freshness handling and current-match UI.
4. Add focused backend tests and validate the frontend JavaScript.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `backend/app/payloads.py`
- `backend/app/rcon_client.py`
- `frontend/assets/js/partida-actual.js`

## Expected Files to Modify

- `backend/app/payloads.py`
- `backend/app/rcon_admin_log_storage.py`
- `backend/tests/test_rcon_admin_log_storage.py`
- `backend/tests/test_current_match_payload.py`
- `frontend/partida-actual.html`
- `frontend/assets/js/partida-actual.js`
- current-match styling only where needed

## Constraints

- Do not break historical pages or scoreboard correlation logic.
- Do not depend on Comunidad Hispana #03.
- Do not fabricate live data or expose arbitrary public URLs.
- Keep current scoreboard buttons on trusted base URLs without `/games`.
- Preserve null versus explicit zero semantics.
- Do not display closed-match fields or stale kill rows as live data.

## Validation

- `python -m compileall backend/app`
- Run focused backend tests for current-match payload and AdminLog kill feed.
- `node --check frontend/assets/js/partida-actual.js`
- Review `git diff --name-only` against this task scope.

## Outcome

- `/api/current-match` now queries the requested configured trusted RCON target
  for the richer session projection first and falls back to the generic live
  server snapshot only when direct RCON data is unavailable.
- RCA: direct RCON `GetServerInformation` samples contain `game_mode`, scores,
  map ids and match timing fields. The prior current-match API lost the game
  mode and score because it projected through `/api/servers`, whose snapshot
  shape keeps only the server-card live fields.
- RCA: live validation on May 21, 2026 still returned RCON `playerCount: 0`
  while manual scoreboard observation for the same servers had shown `1`.
  Current-match payloads therefore expose RCON population with
  `player_count_quality: "rcon-session-unverified"` and the frontend renders
  that as `No verificado` instead of a confident `0 / 100`.
- The live page now mirrors the historical detail layout direction: map title,
  server context, map art or a clean placeholder, a large in-progress
  scoreboard, live metadata only, and trusted base scoreboard buttons.
- AdminLog current-match fallback kills are capped to a conservative 15-minute
  freshness window. Old fallback rows now return
  `scope: "no-current-match-events"` with stale-filter metadata instead of
  leaking into the live feed.
- Added focused tests for direct current-match payload projection and AdminLog
  fallback freshness. The repository environment and the rebuilt backend image
  do not install `pytest`, so the focused test files could not be executed via
  `python -m pytest`; the same payload and freshness paths were exercised with
  narrow inline Python scenarios.
- Validation: `python -m compileall backend/app`;
  `node --check frontend/assets/js/partida-actual.js`;
  `git diff --check`;
  `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`;
  rebuilt Compose `backend` and `frontend`; REST checks for both trusted
  `/api/current-match` endpoints and both kill-feed endpoints; served map asset
  checks for Carentan and St. Marie Du Mont; unsupported current-match server
  REST check returned 404.

## Change Budget

The requested projection spans backend, tests and the live page. Keep changes
focused on current-match files and split unrelated work out.
