---
id: TASK-268
title: Investigate current match AdminLog ingestion latency
status: in-progress
type: investigation
team: Backend Senior
supporting_teams: ["Frontend Senior"]
roadmap_item: current-match
priority: high
---

# TASK-268 - Investigate current match AdminLog ingestion latency

## Goal

Measure and explain the latency between CRCON live AdminLog events and the public current-match endpoints.

## Context

The current-match page is not fully frozen, but it can lag behind CRCON live. A real observation on Server 2 showed CRCON live kills later than the public API top event:

- API first event: `rcon-admin-log:comunidad-hispana-02:4246607`
- API top event server time: `1781711973`
- API top event local time: around `17:59:33`
- CRCON live reportedly showed later kills around `18:00:24`, `18:00:34`, and `18:00:54`

This suggests frontend polling is running and the API eventually changes, but the persisted AdminLog/read-model path may lag behind CRCON live.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/backend-senior.md`
- `ai/orchestrator/frontend-senior.md`
- `frontend/assets/js/partida-actual.js`
- `backend/app/payloads.py`
- `backend/app/rcon_admin_log_storage.py`
- `backend/app/rcon_admin_log_ingestion.py`
- `backend/app/rcon_historical_worker.py`
- `backend/app/config.py`
- `backend/app/postgres_rcon_storage.py`

## Investigation Steps

1. Confirm current frontend polling intervals and in-flight guard behavior.
2. Confirm whether `/api/current-match/kills` and `/api/current-match/players` read live RCON or persisted storage.
3. Identify the AdminLog ingestion process and configured/default interval.
4. Sample public current-match endpoints with cache busters while CRCON is producing kills.
5. Estimate endpoint freshness lag from the latest returned kill server time.
6. Run production DB freshness checks if production DB access is available.
7. Inspect service/log availability if container access is available.
8. Classify the latency source without changing frontend/backend code.

## Constraints

- Do not execute `ai-platform run`.
- Do not commit or push.
- Do not touch frontend unless the API is fresh and the UI is stale.
- Do not touch backend, scheduler, RCON hosts/ports, `27001`, server configuration, physical assets or `frontend/assets/img/`.
- Do not touch maps, weapons, clans or brands.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Do not touch `ai/system-metrics.md`.
- Do not include `tmp/`, TASK-204 or unrelated pending changes.
- Do not use `git add .`.

## Findings

### Frontend polling

Read-only review of `frontend/assets/js/partida-actual.js` confirmed:

- Current match summary polling interval: `30000ms`.
- Killfeed polling interval: `1500ms`.
- Player stats polling interval: `3000ms`.
- `killFeedRefreshInFlight` and `playerStatsRefreshInFlight` are reset in `finally` blocks.

No frontend change was made. The public endpoint payloads did not advance during the validation window, so there is no evidence that the browser received fresh data and failed to render it.

### Source of `/api/current-match/kills` and `/api/current-match/players`

Read-only backend review confirmed both public endpoints read persisted AdminLog storage, not live RCON:

- `build_current_match_kill_feed_payload(...)` calls `list_current_match_kill_feed(..., ensure_storage=False)`.
- `build_current_match_player_stats_payload(...)` calls `list_current_match_player_stats(..., ensure_storage=False)`.
- Both storage functions read `rcon_admin_log_events`.
- `list_current_match_kill_feed(...)` selects kill rows from the current open AdminLog match window.
- `list_current_match_player_stats(...)` derives player kills/deaths/team state by replaying persisted AdminLog rows in the same current-match window.
- The current-match page/API read path does not trigger AdminLog ingestion because `ensure_storage=False`.

AdminLog writes are performed by `persist_rcon_admin_log_entries(...)`, called through `ingest_rcon_admin_logs(...)`.

### Ingestion process and configured interval

Read-only service review found the AdminLog ingestion path in `rcon-historical-worker`:

- `docker-compose.yml` defines `rcon-historical-worker` with command `python -m app.rcon_historical_worker loop`.
- The service sets `HLL_RCON_HISTORICAL_CAPTURE_INTERVAL_SECONDS` default to `600`.
- The service sets `HLL_BACKEND_RCON_ADMIN_LOG_LOOKBACK_MINUTES` default to `10`.
- The worker CLI default `--interval` is `get_rcon_historical_capture_interval_seconds()`.
- The current-live 5-second interval is only selected when capture mode is `current-live` and no explicit `--interval` is supplied.
- Compose does not set `HLL_RCON_CAPTURE_MODE=current-live`, `HLL_RCON_CURRENT_MATCH_MODE=true`, or `HLL_RCON_SKIP_HISTORICAL_MATERIALIZATION=true` for this worker.

This means the checked-in service configuration points to a historical loop with an effective default interval of 600 seconds, not a 5-second live AdminLog ingest loop.

### Public endpoint sampling

Sampled public endpoints with cache busters and no-cache headers for `comunidad-hispana-02` during the real-kill validation window:

- Kills endpoint: `https://comunidadhll.devzamode.es/api/current-match/kills?server=comunidad-hispana-02&limit=18`
- Players endpoint: `https://comunidadhll.devzamode.es/api/current-match/players?server=comunidad-hispana-02`

Main 18-sample run, 10 seconds apart:

- Sample window: `18:05:06` to `18:07:57` local.
- Every sample returned `kills_scope=open-admin-log-match-window`.
- Every sample returned `kills_count=6`.
- Every sample returned the same first kill: `rcon-admin-log:comunidad-hispana-02:4246607`.
- First kill local time stayed `17:59:33`.
- First kill stayed `Jack -> [LCM] ParkO | GEWEHR 43`.
- Estimated age of the first returned kill grew from `333s` to `505s`.
- Player payload stayed stable with `players_count=7`.
- Top players stayed stable, including `[LCM] ParkO K=2 D=3`, `Jack K=2 D=1`, and `culebras85 K=2 D=1`.

Follow-up samples:

- `18:09:23`: same first kill, estimated age `590s`.
- `18:09:39`: same first kill, estimated age about `606s`.
- `18:09:54`: same first kill, estimated age about `621s`.
- `18:10:09`: same first kill, estimated age about `636s`.
- `18:10:24`: same first kill, estimated age about `651s`.

The public endpoints returned HTTP `200` for both kills and players during validation.

### DB and log access

Production DB freshness could not be checked from this workspace:

- Local configuration does not have `HLL_BACKEND_DATABASE_URL` set.
- Local config reports PostgreSQL RCON storage disabled.
- The local SQLite DB is not the production-current source for the public API.

Production Docker logs could not be inspected from this workspace:

- `docker ps --format "{{.Names}}"` failed because Docker Desktop/Linux engine was not running locally.
- No production worker/backend logs were available through this shell session.

Because production DB/log access was unavailable, the investigation classifies the public API/read-model behavior from endpoint sampling plus checked-in worker configuration.

## Classification

API/read-model ingestion latency, not frontend rendering.

The `/kills` and `/players` endpoints read persisted `rcon_admin_log_events`. They do not query live RCON. During a real-kill window, both public endpoint payloads stayed pinned to the same AdminLog event and player totals while CRCON reportedly showed later kills/player stats. The observed endpoint age grew past 10 minutes, matching the checked-in `rcon-historical-worker` default historical loop interval of 600 seconds.

Most likely cause: the public current-match endpoints depend on AdminLog ingestion performed by the historical worker at a slow historical interval, so the page can lag behind CRCON live by many minutes. This is a design/worker-ingestion latency issue unless production logs/DB show a separate worker failure.

No evidence was found for:

- Frontend polling being disabled.
- Browser cache causing stale responses.
- UI receiving changed payloads and failing to re-render.
- The current-match page itself being able to force fresh AdminLog ingestion.

## Recommended Next Task

Create a follow-up task to reduce current-match AdminLog latency without changing server/RCON configuration blindly. Suggested scope:

- Verify production worker mode, interval, and recent AdminLog ingest logs with actual production access.
- Run production DB checks for `rcon_admin_log_events` max `id`, `server_time`, and `created_at` before and after a live-kill interval.
- If confirmed, introduce or enable a lightweight `current-live` AdminLog ingestion worker for current-match data with a low interval, separated from heavy historical materialization.
- Alternatively, evaluate a live read-through strategy for current-match endpoints if the persisted read model cannot satisfy live freshness requirements.
- Add API freshness metadata such as latest AdminLog `server_time`/`created_at` so future investigations can distinguish CRCON/live lag from UI rendering.

## Validation Results

- Read AGENTS/project context and relevant backend/frontend source files.
- Confirmed frontend polling intervals by read-only source review.
- Confirmed `/api/current-match/kills` and `/players` read persisted AdminLog storage by read-only backend source review.
- Sampled public `comunidad-hispana-02` kills and players endpoints with cache busters/no-cache headers.
- Confirmed public endpoints returned HTTP `200`.
- Confirmed public endpoint payloads did not advance during the sampled real-kill window.
- Confirmed local Docker/production logs were not available from this workspace.
- Confirmed production DB access was not configured in this local shell.
- No code changes were made.
- No backend, scheduler, RCON config, server config, frontend, or asset files were touched for this task.
