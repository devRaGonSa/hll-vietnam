---
id: TASK-267
title: Investigate current match live data staleness and clean copy
status: in-progress
type: investigation
team: Backend Senior
supporting_teams: ["Frontend Senior"]
roadmap_item: current-match
priority: high
---

# TASK-267 - Investigate current match live data staleness and clean copy

## Goal

Determine whether the current match killfeed and live player statistics are stale in the API, stale in frontend rendering, or mismatched against CRCON/RCON live data. Apply only the requested visible copy cleanup unless the diagnosis proves a safe code fix is required.

## Context

The current match page can show older live stats than CRCON/RCON live view. For example, CRCON may show a player with many more kills while the page still displays an older count. The killfeed may also appear stale.

Potential causes include stale `/api/current-match/players`, stale `/api/current-match/kills`, AdminLog ingestion issues, current-match window filtering, frontend signature/dedupe behavior, browser cache, or a source mismatch between live RCON scoreboard and derived event-based stats.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/frontend-senior.md`
- `ai/orchestrator/backend-senior.md`
- `frontend/assets/js/partida-actual.js`
- `backend/app/payloads.py`
- `backend/app/rcon_admin_log_storage.py`
- `backend/app/postgres_rcon_storage.py`

## Investigation Steps

1. Repeatedly sample killfeed endpoints for `comunidad-hispana-01` and `comunidad-hispana-02` with cache busters and no-cache headers.
2. Repeatedly sample current-match player endpoints for `comunidad-hispana-01` and `comunidad-hispana-02` with cache busters and no-cache headers.
3. Audit frontend polling, fetch cache behavior, render signatures, in-flight guards and dedupe logic.
4. Audit backend payload, storage and query paths for current-match kills and players.
5. Run read-only DB checks for recent AdminLog events where available.
6. Inspect local service/container availability and logs where available.
7. Classify the stale-display cause before applying any staleness fix.
8. Apply requested visible copy cleanup.
9. Validate syntax and document the result.

## Constraints

- Do not execute `ai-platform run`.
- Do not commit or push.
- Do not touch physical assets or `frontend/assets/img/`.
- Do not touch maps, weapons, clans or brands.
- Do not change RCON hosts/ports, `27001`, or server configuration.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Do not touch `ai/system-metrics.md`.
- Do not include `tmp/`, TASK-204 or unrelated pending changes.
- Do not use `git add .`.
- Do not introduce technical backend wording into visible UI copy.

## Required Copy Changes

- Remove visible text: `Estadisticas derivadas de los eventos recientes.`
- Remove visible text: `Mostrando las ultimas 12 bajas detectadas.`
- Replace visible text: `Leyendo eventos recientes para esta partida.` with `Leyendo los enfrentamientos recientes de la partida.`

## Validation

If frontend changes:

- `node --check frontend/assets/js/partida-actual.js`

If backend changes:

- `python -m compileall backend/app`
- `cd backend; python -m unittest tests.test_current_match_payload`

Functional checks:

- Repeated endpoint samples identify whether kills and players change over time.
- Public endpoints return 200 for kills and players on #01 and #02.
- UI copy no longer contains the removed text.
- No unrelated pending changes are included.

## Findings

### Repeated Production Endpoint Samples

All repeated samples used cache busters and no-cache request headers.

Killfeed samples:

- `GET /api/current-match/kills?server=comunidad-hispana-01&limit=18`
  - 10 samples over roughly 100 seconds.
  - `scope=open-admin-log-match-window`.
  - `count=0` for all samples.
  - No first/last event id because the endpoint returned no kill rows.
- `GET /api/current-match/kills?server=comunidad-hispana-02&limit=18`
  - 10 samples over roughly 100 seconds.
  - `scope=open-admin-log-match-window`.
  - `count=18` for all samples.
  - First event stayed `rcon-admin-log:comunidad-hispana-02:4246587`.
  - Last event stayed `rcon-admin-log:comunidad-hispana-02:4246570`.
  - Top rows stayed identical. Top event was `Jack -> AleixCommander` with `SMLE No.1 Mk III`.

Player-stat samples:

- `GET /api/current-match/players?server=comunidad-hispana-01`
  - 10 samples over roughly 100 seconds.
  - `count=1` for all samples.
  - Only visible row stayed `Core.D | Axis | K=0 | D=0`.
- `GET /api/current-match/players?server=comunidad-hispana-02`
  - 10 samples over roughly 100 seconds.
  - `count=12` for all samples.
  - Top row stayed `Jack | Allies | K=16 | D=6 | SMLE No.1 Mk III`.
  - Full single follow-up sample confirmed Jack had `kills=16`, `last_seen_at=2026-06-17T15:34:14.312Z`, and source `connected,kill,message,team_switch`.

Public endpoint status validation:

- `current-match-kills-comunidad-hispana-01`: 200.
- `current-match-kills-comunidad-hispana-02`: 200.
- `current-match-players-comunidad-hispana-01`: 200.
- `current-match-players-comunidad-hispana-02`: 200.

### Live-Kill Revalidation Window

This section was added after a new real-kill validation window became available. The user reported that CRCON/RCON live was visibly showing new kills while the current-match page appeared stale again.

All endpoint requests used cache busters and no-cache request headers.

`comunidad-hispana-01`:

- Sample count: 12 samples over roughly 120 seconds.
- `GET /api/current-match/kills?server=comunidad-hispana-01&limit=18`
  - `scope=open-admin-log-match-window` on every sample.
  - `kills_count=0` on every sample.
  - `kills_first_id` and `kills_last_id` stayed empty.
  - `kills_top5` stayed empty.
- `GET /api/current-match/players?server=comunidad-hispana-01`
  - `players_count=1` on every sample.
  - Top players stayed exactly: `Core.D | Axis | K=0 | D=0 | W=`.

Interpretation for #01:

- The API did not change during a user-reported real-kill window.
- Both `/api/current-match/kills` and `/api/current-match/players` stayed stale.
- Because the endpoint payload did not change, this run does not implicate frontend render/signature/dedupe.
- Classification for #01 is case 5: both endpoints stale, likely AdminLog ingestion/read-model freshness or current-match AdminLog window/query filtering.

`comunidad-hispana-02` spot-check:

- Sample count: 6 samples over roughly 60 seconds.
- `GET /api/current-match/kills?server=comunidad-hispana-02&limit=18`
  - `scope=open-admin-log-match-window` on every sample.
  - `kills_count=6` on every sample.
  - First id stayed `rcon-admin-log:comunidad-hispana-02:4246607`.
  - Last id stayed `rcon-admin-log:comunidad-hispana-02:4246602`.
  - Top kill stayed `Jack -> [LCM] ParkO | GEWEHR 43`.
- `GET /api/current-match/players?server=comunidad-hispana-02`
  - `players_count=7` on every sample.
  - Top rows stayed stable: `[LCM] ParkO K=2`, `Jack K=2`, `culebras85 K=2`.

Interpretation for #02:

- #02 had current-match data but no endpoint change during the shorter spot-check.
- This does not prove #02 staleness unless CRCON/RCON live was also changing for #02 during the same window.

Browser/network validation:

- The in-app Browser skill file advertised by the environment was not present on disk, so Browser MCP validation could not be run safely.
- Tool discovery did not expose browser navigation/network tools.
- `npx playwright --version` timed out while resolving/downloading, so a Playwright browser probe was not used.
- Static frontend audit still confirms scheduled requests every 1.5s for killfeed and every 3s for player stats.
- Direct endpoint sampling confirms that, at least for #01, the payload available to the UI did not change during the live-kill report.

### Frontend Analysis

- `CURRENT_MATCH_KILL_FEED_POLL_INTERVAL_MS` is `1500`; killfeed fetch is scheduled every 1.5 seconds.
- `CURRENT_MATCH_PLAYER_STATS_POLL_INTERVAL_MS` is `3000`; player stats fetch is scheduled every 3 seconds.
- `killFeedRefreshInFlight` and `playerStatsRefreshInFlight` are reset in `finally`, so normal request failures should not leave either flag stuck.
- Killfeed rendering consumes `data.items` directly, filters invalid events, dedupes by event id/semantic key, and renders the latest visible window after TASK-262 style dedupe.
- Killfeed visible signature includes event/window key, killer/victim names, teams, weapon and teamkill flag.
- Player stats rendering consumes `data.items`, dedupes rows, sorts by kills/deaths/name, and renders the table from the current endpoint payload.
- Player stats visible signature includes player name, team, kills, deaths, teamkills, deaths by teamkill, favorite weapon and last seen.
- If endpoint data changes in any of those fields, the frontend should re-render.
- `fetchJson` currently uses plain `fetch(url)` and does not set `cache: "no-store"`. The repeated cache-busted production samples still stayed stable, so cache was not proven as the cause in this run.
- No evidence was found that visibleSignature would block a real kills/stat change from the endpoint.

### Backend Analysis

- `/api/current-match/kills` is routed in `backend/app/routes.py` to `build_current_match_kill_feed_payload(...)`.
- `/api/current-match/players` is routed in `backend/app/routes.py` to `build_current_match_player_stats_payload(...)`.
- Both payload builders read from AdminLog storage through:
  - `list_current_match_kill_feed(...)`
  - `list_current_match_player_stats(...)`
- Neither endpoint queries live RCON directly during the public GET.
- Killfeed source table is `rcon_admin_log_events`.
- Player stat source is also `rcon_admin_log_events`; it derives kills/deaths/teamkills/favorite weapon by replaying current-window AdminLog events.
- Current match window is selected from the latest `match_start` / `match_end` boundary for the target server.
- If the latest boundary is `match_start`, the endpoints use `server_time >= open_start_time`.
- If no open match boundary exists, fallback mode uses recent AdminLog rows and filters by freshness.
- Target matching uses `(target_key = ? OR external_server_id = ?)`, so both target fields are considered for `comunidad-hispana-01` and `comunidad-hispana-02`.

### DB / Service Checks

- Local config reports:
  - `use_postgres_rcon_storage=False`
  - `database_url_set=False`
  - `storage_path=D:\Proyectos\HLL Vietnam\backend\data\hll_vietnam_dev.sqlite3`
  - `historical_data_source_kind=rcon`
- Local SQLite schema confirms `rcon_admin_log_events` stores the current-match event source.
- Local SQLite data is not production-current:
  - Latest local `comunidad-hispana-01` events are from May 20, 2026.
  - Latest local `comunidad-hispana-02` events are from May 20, 2026.
  - Production endpoint rows sampled during this task are from June 17, 2026.
- Local DB max samples repeated after 60 seconds did not change, which only proves local ingestion was not running in this workspace.
- Docker is not available locally:
  - `docker ps --format "{{.Names}}"` failed because Docker Desktop/Linux engine is not running.
  - Container logs could not be inspected from this workspace.
- Production DB/container access was not available from this workspace, so production ingestion status and worker logs could not be directly verified.

### Classification

- The initial sample window happened during a low/no-kill state and was not enough to prove a bug by itself.
- A later real-world check found that the server had changed map and the new match had no kills yet, so `/api/current-match/kills` returning `count=0` in that state is expected and does not prove a bug.
- During the new live-kill revalidation window for #01, CRCON/RCON live was reported to show new kills while both current-match API endpoints stayed unchanged.
- This supersedes the earlier low/no-kill classification for #01.
- The active data source for both current-match feed and player stats is stored AdminLog, not direct live scoreboard state.
- Since both `/api/current-match/kills` and `/api/current-match/players` stayed unchanged for #01, the current classification is backend/API source-side staleness.
- The most likely causes are AdminLog ingestion/read-model lag or current-match AdminLog window/query filtering for `comunidad-hispana-01`.
- No evidence was found that frontend visibleSignature/dedupe would ignore changed endpoint values.
- No backend staleness fix was applied because the user requested no blind fixes and no backend changes.

## Exact Cause

For the stale display reported by the user, the exact confirmed cause is not a frontend render blocker. The current page displays what `/api/current-match/kills` and `/api/current-match/players` return, and the render signatures include the fields needed to refresh changed rows.

The live-kill revalidation confirms API/source-side staleness for `comunidad-hispana-01`: CRCON/RCON live was reported to show new kills, but `/api/current-match/kills` stayed empty and `/api/current-match/players` stayed at one zeroed row for 12 samples over roughly 120 seconds.

The exact backend subcause remains open: AdminLog ingestion/read-model freshness, or current-match window/query filtering. The next step is production read-only DB/log inspection for `rcon_admin_log_events` on `comunidad-hispana-01`.

## Changes Applied

- `frontend/partida-actual.html`
  - Replaced visible copy:
    - From `Leyendo eventos recientes para esta partida.`
    - To `Leyendo los enfrentamientos recientes de la partida.`
- `frontend/assets/js/partida-actual.js`
  - Removed the visible feed status/count line when kill rows exist.
  - Removed the visible player-stats line `Estadisticas derivadas de los eventos recientes.` when stat rows exist.
  - Empty/error states remain visible.

No backend, scheduler, RCON, server configuration, physical asset or image files were changed.

## Validation Results

- Repeated production endpoint sampling for kills #01/#02 and players #01/#02.
- Repeated live-kill revalidation for #01: 12 samples over roughly 120 seconds.
- Short #02 spot-check: 6 samples over roughly 60 seconds.
- Public endpoint status checks for kills #01/#02 and players #01/#02 returned 200.
- Frontend polling/render/signature audit completed.
- Backend route/payload/storage audit completed.
- Local SQLite read-only schema/data checks completed.
- Docker/service log inspection attempted; Docker engine was unavailable locally.
- Browser/network validation could not be executed because Browser MCP tooling was unavailable and Playwright resolution timed out.
- `node --check frontend/assets/js/partida-actual.js` passed.
- Verified the requested removed/replaced visible text with `rg`.
- Reviewed `git diff -- frontend/assets/js/partida-actual.js frontend/partida-actual.html`.
