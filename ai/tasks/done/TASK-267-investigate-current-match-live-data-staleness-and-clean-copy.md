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

- During the sample window, both production endpoints were stable. This does not prove a bug by itself because there may have been no new kills/events during the 100-second window.
- A later real-world check found that the server had changed map and the new match had no kills yet, so `/api/current-match/kills` returning `count=0` in that state is expected and does not prove a bug.
- The concrete stale-display example described by the user was not reproduced in the sampled state: production `players` for #02 reported Jack with 16 kills, which is newer than the example of 15 in CRCON and much newer than the stale UI example of 5.
- The active data source for both current-match feed and player stats is stored AdminLog, not direct live scoreboard state.
- If CRCON live changes while these endpoints do not, the cause is backend/source-side: AdminLog ingestion, AdminLog query/window filtering, or mismatch between live scoreboard data and derived event data.
- No evidence was found that frontend visibleSignature/dedupe would ignore changed endpoint values.
- No backend staleness fix was applied because production DB/log access was unavailable and the current endpoint samples did not prove a specific query/window bug.

## Exact Cause

For the stale display reported by the user, the exact confirmed cause is not a frontend render blocker. The current page displays exactly what `/api/current-match/kills` and `/api/current-match/players` return, and the render signatures include the fields needed to refresh changed rows.

The most precise verified cause is source-model mismatch and/or AdminLog read-model freshness: current-match player stats are derived from stored AdminLog events, while CRCON live can show direct live scoreboard state. If stored AdminLog ingestion or the current-match AdminLog window lags behind CRCON live, both killfeed and player stats will appear stale even though the frontend polling continues.

Root-cause confirmation still requires a future validation window where CRCON/RCON live shows new kills after a map change and the current-match endpoints can be sampled at the same time.

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
- Public endpoint status checks for kills #01/#02 and players #01/#02 returned 200.
- Frontend polling/render/signature audit completed.
- Backend route/payload/storage audit completed.
- Local SQLite read-only schema/data checks completed.
- Docker/service log inspection attempted; Docker engine was unavailable locally.
- `node --check frontend/assets/js/partida-actual.js` passed.
- Verified the requested removed/replaced visible text with `rg`.
- Reviewed `git diff -- frontend/assets/js/partida-actual.js frontend/partida-actual.html`.
