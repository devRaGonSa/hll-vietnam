---
id: TASK-158
title: Current match realtime transport
status: done
type: backend
team: Backend Senior
supporting_teams: [Frontend Senior]
roadmap_item: foundation
priority: high
---

# TASK-158 - Current match realtime transport

## Goal

Implement a real-time or near-real-time update strategy for the current-match page, prioritizing the kill feed and then current match metadata/player stats.

## Background

The current-match page currently refreshes through polling. In `frontend/assets/js/partida-actual.js`, the current interval is:

`CURRENT_MATCH_POLL_INTERVAL_MS = 30 * 1000`

The user explicitly rejected this behavior:

- "He dicho que se actualice en vivo y no cada 20 segundos"

The page should behave much closer to real time, especially for the kill feed. A 20/30-second refresh is too slow for a live combat screen.

Current endpoints:

- `GET /api/current-match?server=...`
- `GET /api/current-match/kills?server=...`
- `GET /api/current-match/players?server=...`

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `frontend/assets/js/partida-actual.js`
- `backend/app/routes.py`
- `backend/app/rcon_admin_log_storage.py`

Inspect the current frontend refresh flow, current-match route payloads, kill feed read model, trusted server validation, and recent AdminLog materialization cadence before changing code.

## Expected Files to Modify

Allowed changes:

- `backend/app/routes.py`
- `backend/app/payloads.py`
- `backend/app/rcon_admin_log_storage.py`
- backend helper/read-model files if needed
- `frontend/assets/js/partida-actual.js`
- `frontend/partida-actual.html` if needed
- focused tests

## Constraints - DO NOT BREAK

- Do not query RCON directly from the frontend.
- Do not expose raw AdminLog lines.
- Do not fabricate events.
- Do not show stale kills as live kills.
- Do not depend on server #03.
- Do not break existing REST endpoints.
- Do not break historical pages or historical match detail pages.
- Keep trusted server validation.
- Keep current public scoreboard URLs without `/games`.
- Avoid overloading the backend/RCON/AdminLog pipeline.
- Commit and push after implementation.

## Implementation Requirements

### 1. RCA first

- Document current update flow in TASK done notes.
- Confirm which parts are safe to update at high frequency:
  - kill feed
  - player stats
  - match metadata/scoreboard
- Identify whether the backend has access to sufficiently fresh AdminLog data without calling RCON per browser poll.

### 2. Preferred transport

Evaluate and implement the safest available option:

- Server-Sent Events (SSE) endpoint for live kill events, OR
- short polling for killfeed every 1-2 seconds with ETag/since cursor/last_event_id, OR
- another minimal transport that gives near-real-time updates without duplicating events.

Prefer SSE if it is simple and safe in the current backend stack.

If SSE is not appropriate, implement short polling with cursor semantics.

### 3. Kill feed endpoint behavior

Add support for incremental fetching:

- `since_event_id` or since timestamp/server_time
- `limit`
- server slug
- trusted server validation

The endpoint must return only new events where possible.

### 4. Frontend behavior

- Remove dependency on a 20/30-second interval for kill feed updates.
- Kill feed should update in near-real-time.
- Avoid overlapping requests.
- Preserve `event_id` deduplication.
- Do not re-render the whole panel if no new events arrived.
- Keep a capped event buffer.

### 5. Match metadata and player stats

- These do not need to update every second.
- Keep a slower safe refresh for scoreboard/player stats if needed, for example 10-30 seconds.
- The kill feed must be faster than metadata refresh.

### 6. Failure/reconnect

- If SSE is used, implement reconnect behavior.
- If short polling is used, handle transient errors without breaking the page.
- Show a small stale/error state only when needed.

### 7. Backend load

- Do not query expensive RCON calls per browser every second.
- Prefer reading already persisted/recent AdminLog materialized data.
- If a live AdminLog ingestion cadence is insufficient, document it instead of hiding the limitation.

## Validation

Run:

- `python -m compileall backend/app`
- focused backend tests if added/updated
- `node --check frontend/assets/js/partida-actual.js`
- `git diff --check`

Before completing the task also confirm that `git diff --name-only` matches the expected scope.

## Manual Verification Steps

- Rebuild backend and frontend.
- Open `http://localhost:8080/partida-actual.html?server=comunidad-hispana-01`.
- Open `http://localhost:8080/partida-actual.html?server=comunidad-hispana-02`.
- During an active match, verify new kill events appear without waiting 20/30 seconds.
- Verify repeated updates do not duplicate events.
- Verify no raw AdminLog lines appear.
- Verify stale events are not displayed as live.
- Verify metadata/scoreboard remains stable and does not flicker.
- Verify backend logs do not show excessive RCON/API pressure.

## Expected Outcome

The current-match kill feed updates in near-real-time, without depending on the existing 30-second page refresh cycle.

## Outcome

RCA:

- The current page used one `30s` interval in `frontend/assets/js/partida-actual.js` for current-match metadata, player stats and the kill feed together.
- The kill feed read path is already safe for higher-frequency reads because it queries normalized persisted `rcon_admin_log_events` rows through `/api/current-match/kills`; it does not query RCON from the browser or expose raw AdminLog lines.
- Current match metadata can still call live RCON through the existing payload path, and player stats aggregate the kill feed read model, so those surfaces remain on the slower refresh path.

Transport decision:

- Implemented incremental short polling for the kill feed instead of SSE. The backend is still the standard-library JSON route stack, while the existing persisted read model can cheaply support a cursor.
- `/api/current-match/kills` now accepts `since_event_id` plus the existing `server` and `limit` inputs. Trusted server validation remains in `routes.py`.
- The frontend polls kill-feed rows every `1500ms`, sends the latest event id cursor after the first load, deduplicates by `event_id`, caps the in-memory visible buffer and avoids overlapping kill-feed requests. Metadata and player stats keep the existing `30s` refresh cadence.

Validation performed:

- `python -m compileall backend/app`
- `node --check frontend/assets/js/partida-actual.js`
- `git diff --check`
- Ran a direct Python smoke check for `list_current_match_kill_feed(..., since_event_id=...)` with temporary AdminLog rows after the focused pytest command could not run.
- Attempted focused backend tests with `python -m pytest backend/tests/test_current_match_payload.py backend/tests/test_rcon_admin_log_storage.py`; this environment failed with `No module named pytest`.
- Reviewed `git diff --name-only`; task-owned code changes are limited to the allowed current-match backend/frontend files plus the focused storage test and this task transition. The worktree already contained frontend and prior task changes from `TASK-156`/`TASK-157`.

Load and freshness limit:

- Browser polling now reads persisted AdminLog rows rather than issuing per-browser RCON calls.
- New kill visibility is still bounded by how quickly `app.rcon_historical_worker` or manual AdminLog ingestion persists fresh AdminLog rows. The current documented worker example is a `120s` loop, so operations may need a follow-up cadence decision if that persisted source is not fresh enough for the desired live screen.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
