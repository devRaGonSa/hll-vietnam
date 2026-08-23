---
id: TASK-264
title: Investigate current match killfeed AdminLog staleness
status: in-progress
type: backend
team: Backend Senior
supporting_teams: ["Frontend Senior"]
roadmap_item: foundation
priority: high
---

# TASK-264 - Investigate current match killfeed AdminLog staleness

## Goal

Determine why `/api/current-match/kills` may not incorporate new kill events even when live RCON shows recent AdminLog activity.

## Context

The current match page `/partida-actual.html?server=comunidad-hispana-01` appears not to show new kills. Prior repeated samples against:

- `https://comunidadhll.devzamode.es/api/current-match/kills?server=comunidad-hispana-01&limit=18`

returned the same window:

- `scope`: `open-admin-log-match-window`
- `count`: `18`
- `first_id`: `rcon-admin-log:comunidad-hispana-01:4246256`
- `last_id`: `rcon-admin-log:comunidad-hispana-01:4246006`
- identical top 5 rows

This task must classify the issue before applying any fix:

- DB ingestion stopped.
- DB receives events but not kills.
- DB receives new kills but endpoint query/filter does not expose them.
- Endpoint changes but frontend does not render changes.
- Cache behavior hides endpoint changes.

## Steps

1. Inspect the listed files first.
2. Run repeated endpoint samples with cache buster.
3. Analyze the backend route, payload builder, storage query and serialization.
4. Run read-only DB/process/log checks where available.
5. Classify the exact case before making any code change.
6. Document findings, validation and next step.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/backend-senior.md`
- `backend/app/payloads.py`
- `backend/app/rcon_admin_log_storage.py`
- `backend/app/postgres_rcon_storage.py`

## Expected Files to Modify

- `ai/tasks/in-progress/TASK-264-investigate-current-match-killfeed-adminlog-staleness.md`

If the endpoint changes and the UI does not, `frontend/assets/js/partida-actual.js` may be considered after classification. No frontend file should be changed otherwise.

## Constraints

- Do not execute `ai-platform run`.
- Do not commit or push.
- Do not touch frontend unless `/api/current-match/kills` changes and the UI does not.
- Do not touch assets.
- Do not touch scheduler or RCON config except read-only analysis.
- Do not change RCON hosts, ports, `27001`, server configuration, Elo/MMR or Comunidad Hispana #03.
- Do not touch `ai/system-metrics.md`.
- Do not include `tmp/`, `TASK-204` or unrelated prior changes.
- Do not use `git add .`.
- Do not implement a solution without classifying the case.

## Validation

Investigation validation:

- Repeated endpoint samples with cache buster.
- Backend route and query analysis.
- Read-only DB/process/log checks where available.
- `git status --short --untracked-files=all`.
- `git diff --name-only`.

If backend code is changed:

- `python -m compileall backend/app`
- `cd backend; python -m unittest tests.test_current_match_payload`

If frontend code is changed:

- `node --check frontend/assets/js/partida-actual.js`

## Outcome

Investigation performed on 2026-06-17.

### Endpoint Samples

Repeated cache-buster sample:

- Command shape: `GET https://comunidadhll.devzamode.es/api/current-match/kills?server=comunidad-hispana-01&limit=18&_ts=<utc-ms>` with `Cache-Control: no-cache` and `Pragma: no-cache`.
- Samples: 10.
- Interval: 10 seconds.
- Result for all 10 samples:
  - `scope`: `open-admin-log-match-window`
  - `count`: `0`
  - `first_id`: empty
  - `last_id`: empty
  - `top5`: empty

Short cache comparison:

- Without `_ts`: `count=0`, `scope=open-admin-log-match-window`.
- With `_ts`: `count=0`, `scope=open-admin-log-match-window`.
- Response headers did not expose `Cache-Control`, `Pragma`, `ETag` or `Last-Modified`; content type was `application/json; charset=utf-8`.

The endpoint behavior changed compared with the prior reported samples that returned 18 rows. During this investigation it did not expose any current kill row, so there was no last API kill to convert to local time.

### Related Public Endpoint Samples

`GET /api/current-match?server=comunidad-hispana-01` returned:

- `found=True`
- `map=St. Marie Du Mont`
- `players=0`

`GET /api/current-match/players?server=comunidad-hispana-01` returned:

- `scope=open-admin-log-match-window`
- `confidence=admin-log-boundary`
- `count=9`
- `updated_at=2026-06-17T14:07:06.725Z`
- sample top rows: `D-ibiz`, `NiceJoker6040`, `Jpylr`

Repeated checks at `2026-06-17 14:17:10 UTC` and `2026-06-17 14:18:53 UTC` still showed:

- `/kills`: `count=0`
- `/players`: `count=9`, `updated_at=2026-06-17T14:07:06.725Z`

This suggests the visible read model had recent non-kill player evidence, but it did not advance during the observation window.

### Backend Route Analysis

`/api/current-match/kills` is handled in `backend/app/routes.py`:

- path: `/api/current-match/kills`
- required query param: `server`
- optional query params: `limit`, `since_event_id`
- handler: `build_current_match_kill_feed_payload(...)`

`build_current_match_kill_feed_payload(...)` in `backend/app/payloads.py`:

- validates the server with `get_trusted_public_scoreboard_origin(server_slug)`
- calls `list_current_match_kill_feed(server_key=origin.slug, limit=limit, since_event_id=since_event_id, ensure_storage=False)`
- wraps failures as a degraded empty public payload

The endpoint does not query RCON live. It reads the persisted AdminLog read model from `rcon_admin_log_events`.

For `comunidad-hispana-01`, the effective read key is:

- `server_key=origin.slug`
- expected value: `comunidad-hispana-01`

The query accepts rows where:

- `target_key = 'comunidad-hispana-01'`
- or `external_server_id = 'comunidad-hispana-01'`

### Kill Query

`list_current_match_kill_feed(...)` first resolves the latest match boundary:

```sql
SELECT event_type, server_time
FROM rcon_admin_log_events
WHERE (target_key = ? OR external_server_id = ?)
  AND event_type IN ('match_start', 'match_end')
  AND server_time IS NOT NULL
ORDER BY server_time DESC, id DESC
LIMIT 1
```

If the latest boundary is `match_start`, it uses `scope=open-admin-log-match-window` and queries:

```sql
SELECT id, target_key, external_server_id, event_timestamp, server_time,
       parsed_payload_json
FROM rcon_admin_log_events
WHERE (target_key = ? OR external_server_id = ?)
  AND event_type = 'kill'
  AND server_time >= ?
ORDER BY server_time DESC, id DESC
LIMIT ?
```

With `since_event_id`, it also adds:

```sql
AND id > ?
```

If there is no open match boundary, it falls back to recent kills and filters by `event_timestamp` freshness.

The open boundary filter can leave out recent kills if:

- the latest stored `match_start.server_time` is newer than stored kill `server_time` values;
- new kills are not being inserted after the latest `match_start`;
- kills are inserted under a different `target_key`/`external_server_id`;
- kills parse as another `event_type`;
- the AdminLog source returns no kill rows in the worker lookback window.

### Timestamp Semantics

`server_time` is not treated by the backend as a Unix timestamp. The parser extracts it from the AdminLog message prefix:

```text
[<relative> (<server_time>)] <body>
```

`event_timestamp` comes from the raw RCON AdminLog entry `timestamp`. Use `event_timestamp`/DB `created_at` for wall-clock freshness; do not rely on converting `server_time` with Unix epoch semantics.

### Ingestion Process

The process that ingests AdminLog is `backend/app/rcon_historical_worker.py`:

- service in Compose/Portainer: `rcon-historical-worker`
- command: `python -m app.rcon_historical_worker loop`
- function path: `run_periodic_rcon_historical_capture(...)` -> `run_rcon_historical_capture(...)` -> `_ingest_target_admin_log(...)` -> `ingest_rcon_admin_logs(...)` -> `persist_rcon_admin_log_entries(...)`
- RCON command: `GetAdminLog`
- storage: `rcon_admin_log_events`

Portainer configuration:

- `HLL_RCON_HISTORICAL_CAPTURE_INTERVAL_SECONDS=${HLL_RCON_HISTORICAL_CAPTURE_INTERVAL_SECONDS:-600}`
- `HLL_BACKEND_RCON_ADMIN_LOG_LOOKBACK_MINUTES=${HLL_BACKEND_RCON_ADMIN_LOG_LOOKBACK_MINUTES:-10}`

So the configured production-style worker cadence is every 600 seconds with a 10 minute AdminLog lookback unless overridden.

### Production DB And Log Checks

Direct production DB/log checks could not be completed from this environment:

- `docker ps --format "{{.Names}}"` failed because Docker Desktop's Linux engine pipe was unavailable.
- `psql` was not available.
- `HLL_BACKEND_DATABASE_URL` was not set in this shell.
- No production container logs were accessible from this local session.

The requested SQL checks against production `rcon_admin_log_events` therefore remain pending. A local SQLite file exists under `backend/data`, but it is not the DB used by `https://comunidadhll.devzamode.es`, so it was not used as production evidence.

### Commit Review

Relevant commits:

- `d558ac8 feat: refine current match live feed`
  - introduced `since_event_id` handling in backend/frontend.
- `f1c5224 Fix current match killfeed visible limit and polling stability`
  - frontend-only polling/visible limit adjustment.
- `ba37000 Fix current match AdminLog read-only PostgreSQL path`
  - changed current-match AdminLog reads to avoid storage initialization on read-only public paths.
- `e389abf Dedupe current match live player stats`
  - touched player stat dedupe and `rcon_admin_log_storage.py`; current kill feed query shape remains the same in the inspected code.

No commit is confirmed as the cause from local analysis. The current evidence does not justify a frontend fix.

### Classification

Current classification is blocked before exact root cause:

- Cache-only issue: unlikely. With and without `_ts`, `/kills` returned the same empty result.
- Frontend issue: not supported. The endpoint itself returned no kill items.
- Endpoint query issue: possible but unproven without DB rows around the latest `match_start`.
- Ingestion issue: possible and currently the strongest operational suspect because the visible player read model did not advance from `2026-06-17T14:07:06.725Z` through later checks.
- Parser/kill-filter issue: possible if production DB receives recent AdminLog rows but stores kills as non-`kill` or under another target key.

Exact cause requires production read-only DB queries and `rcon-historical-worker`/backend logs.

### Decision

No backend, frontend, asset, scheduler or RCON configuration changes were applied. The correct next step is production read-only verification, not code changes.

Recommended next task:

- Run the requested SQL queries directly in production PostgreSQL and inspect `rcon-historical-worker` logs around `2026-06-17T14:07Z` onward.
- Confirm whether `MAX(id)`, `MAX(server_time)` and `MAX(created_at)` advance for `event_type='kill'` and for non-kill events.
- Confirm whether `rcon-historical-worker` is running and whether it logs AdminLog/RCON/DB errors.

## Change Budget

- Prefer documentation-only unless a classified backend/frontend fix is clearly required.
- Preserve scope and avoid unrelated files.
