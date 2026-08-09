---
id: TASK-221
title: Fix Historico loading and recent matches performance
status: in-progress
type: frontend
team: Frontend Senior
supporting_teams: ["Backend Senior"]
roadmap_item: foundation
priority: high
---

# TASK-221 - Fix Historico loading and recent matches performance

## Goal

Make the Historico screen load weekly/monthly tops and recent matches quickly from snapshots/read models, without blank limbo states or public-request heavy calculations.

## Context

The Historico page currently shows slow weekly/monthly top loading and recent matches can stay visually empty for several seconds. These public views should read precomputed snapshots or simple read models, and latest matches should be refreshed by the runner when matches finish or by short polling.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Inventory the exact frontend endpoints and backend functions used by Historico.
2. Identify frontend loading states that produce blank UI or unnecessary waits.
3. Ensure weekly/monthly top endpoints use snapshot-only public reads.
4. Ensure recent matches endpoint avoids RCON, scoreboard and heavy recalculation in public requests.
5. Validate frontend syntax, backend compilation and relevant tests.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `ai/orchestrator/frontend-senior.md`
- `ai/orchestrator/backend-senior.md`
- `frontend/historico.html`
- `frontend/assets/js/historico.js`
- `frontend/assets/css/historico.css`
- `backend/app/routes.py`
- `backend/app/payloads.py`
- `backend/app/historical_snapshot_storage.py`
- `backend/app/historical_snapshots.py`
- `backend/app/rcon_historical_read_model.py`
- `backend/app/postgres_rcon_storage.py`

## Expected Files to Modify

- `frontend/assets/js/historico.js`
- `frontend/assets/js/historico-recent-live.js`
- `backend/app/payloads.py`
- `backend/tests/test_historical_snapshot_refresh.py`
- `ai/tasks/in-progress/TASK-221-fix-historico-loading-and-recent-matches-performance.md`

## Constraints

- Do not execute `ai-platform run`.
- Do not push or commit.
- Do not touch weapon assets, SVGs or physical images.
- Do not touch `ai/system-metrics.md`.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Do not include unrelated prior changes.

## Validation

- `node --check frontend/assets/js/historico.js`
- `python -m compileall` for modified backend modules.
- Relevant backend tests.
- Measure or provide measurement commands for weekly top, monthly top and recent matches.
- Confirm public requests do not use RCON, scoreboard fallback or runtime leaderboard aggregation.
- Confirm no protected files/assets were touched by this task.

## Outcome

Done.

Inventory:

- Weekly top: `GET /api/historical/snapshots/leaderboard?server=<slug>&timeframe=weekly&metric=<metric>&limit=10`, called from `frontend/assets/js/historico.js`. Backend route: `routes.resolve_get_payload` -> `build_leaderboard_snapshot_payload`. Expected data: precomputed historical snapshot via `historical_snapshot_storage.get_historical_snapshot`, stored in `displayed_historical_snapshots` on PostgreSQL or JSON fallback. Public request must not call RCON, scoreboard, storage initialization or runtime leaderboard aggregation.
- Monthly top: `GET /api/historical/snapshots/leaderboard?server=<slug>&timeframe=monthly&metric=<metric>&limit=10`, same frontend/backend path as weekly with `timeframe=monthly`. Expected data: same precomputed snapshot path.
- Recent matches primary snapshot: `GET /api/historical/snapshots/recent-matches?server=<slug>&limit=100`, called from `frontend/assets/js/historico.js`. Backend route: `build_recent_historical_matches_snapshot_payload`. Expected data: precomputed `recent-matches` snapshot via `displayed_historical_snapshots` or JSON fallback. Generated out of band from materialized RCON matches.
- Recent matches live updater: before this task `frontend/assets/js/historico-recent-live.js` also called `GET /api/historical/recent-matches?server=<slug>&limit=100`. Backend route: `build_recent_historical_matches_payload`, which can use the RCON historical read model and public scoreboard fallback. It now calls `GET /api/historical/snapshots/recent-matches?server=<slug>&limit=100`.
- Server summary: `GET /api/historical/snapshots/server-summary?server=<slug>`, called from `frontend/assets/js/historico.js`. Backend route: `build_historical_server_summary_snapshot_payload`, using precomputed snapshots only.

Cause:

- The public leaderboard snapshot builder could still runtime-enrich items missing `total_time_seconds` by calling `_load_runtime_leaderboard_items`, which delegates to weekly/monthly runtime leaderboard builders.
- The public recent-matches snapshot builder could complete a partial snapshot by calling `list_recent_historical_matches`, adding scoreboard/RCON-backed work to a public request.
- `historico-recent-live.js` was overwriting the same recent-matches panel from `/api/historical/recent-matches`, bypassing the snapshot path used by `historico.js`.
- The initial recent-matches render cleared the list before data arrived, and on errors it could leave loading placeholders visible.

Implemented strategy:

- Leaderboard snapshot public requests now return only persisted snapshot items and mark runtime enrichment as disabled on the public snapshot path.
- Recent-matches snapshot public requests now return only persisted snapshot items; no public scoreboard/RCON completion is attempted.
- The live recent-matches frontend updater now reads `/api/historical/snapshots/recent-matches` and polls every 60 seconds, relying on the runner/snapshot refresh to pick up finished matches.
- The recent-matches panel now renders compact loading placeholders instead of a blank area, and clears them on error.

Timing:

- HTTP endpoint measurement was not possible because `http://127.0.0.1:8000/health` timed out in the local environment.
- In-process snapshot payload timing with mocked persisted snapshots:
  - weekly snapshot payload: `0.009 ms` average over 1000 calls
  - monthly snapshot payload: `0.007 ms` average over 1000 calls
  - recent matches snapshot payload: `0.006 ms` average over 1000 calls
- Commands to measure real endpoints when the backend is running:
  - `Measure-Command { Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/historical/snapshots/leaderboard?server=all-servers&timeframe=weekly&metric=kills&limit=10" }`
  - `Measure-Command { Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/historical/snapshots/leaderboard?server=all-servers&timeframe=monthly&metric=kills&limit=10" }`
  - `Measure-Command { Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:8000/api/historical/snapshots/recent-matches?server=all-servers&limit=100" }`

Validation:

- `node --check frontend/assets/js/historico.js`
- `node --check frontend/assets/js/historico-recent-live.js`
- `python -m compileall backend/app/payloads.py`
- `$env:PYTHONPATH='backend'; python -m unittest backend.tests.test_historical_snapshot_refresh`
- Local visual inspection with Chrome headless against `frontend/historico.html`. Browser plugin invocation failed because `iab` was unavailable; Playwright CLI was present but browser binaries were not installed, so Chrome headless was used. With backend unavailable, Historico showed compact error states and no blank recent-matches limbo.

Exclusions:

- Did not execute `ai-platform run`.
- Did not push or commit.
- This task did not touch weapon assets, SVGs, physical images or `ai/system-metrics.md`.
- Did not reactivate Elo/MMR.
- Did not reintroduce Comunidad Hispana #03.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
