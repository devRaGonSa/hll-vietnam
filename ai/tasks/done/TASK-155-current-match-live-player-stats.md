# TASK-155 - Current match live player stats

Status: in-progress

## Goal

Investigate and implement live player/statistics rendering for the current-match page using the safest available data source.

## Background

The current-match page has an "Estadísticas en vivo" section, but it currently remains a placeholder:

> "Las estadísticas en vivo aparecerán cuando haya datos suficientes."

The user reports that players are not being shown.

Known context:

- `/api/current-match` exposes players and team player counts from RCON `getSession`, but those counts may be marked as `rcon-session-unverified`.
- Public scoreboard can show player population even when RCON `getSession` reports 0.
- AdminLog kill events already expose player names through normalized kill feed rows.
- Historical materialization already derives player stats from AdminLog data for completed matches.
- The current-match page should eventually show useful live player rows, but only if data is reliable enough.

## Scope

Investigate the available live player data sources and wire the current-match page to a safe current player statistics payload.

Allowed changes:

- `backend/app/routes.py`
- `backend/app/payloads.py`
- `backend/app/rcon_admin_log_storage.py`
- backend read-model/helper files if needed
- `frontend/assets/js/partida-actual.js`
- `frontend/partida-actual.html`
- `frontend/assets/css/historico.css` or relevant CSS
- focused backend tests

## Constraints - DO NOT BREAK

- Do not fabricate player stats.
- Do not show an empty/misleading table as if it were real data.
- Do not show RCON `getSession` `playerCount=0` as reliable if quality is `rcon-session-unverified`.
- Do not expose raw AdminLog lines.
- Do not expose admin-only/sensitive data.
- Do not break historical materialization.
- Do not break historical match detail stats.
- Do not query RCON directly from the frontend.
- Do not depend on server #03.
- Do not scrape the public scoreboard unless explicitly chosen and documented as a safe server-side fallback.
- Keep current public scoreboard URLs trusted and without `/games`.

## Files to inspect first

Read:

- `frontend/partida-actual.html`
- `frontend/assets/js/partida-actual.js`
- `backend/app/routes.py`
- `backend/app/payloads.py`
- `backend/app/rcon_admin_log_storage.py`
- focused tests and historical player stat materialization helpers related to current-match or AdminLog data

Inspect the existing RCON session payload, current kill feed freshness logic, open AdminLog match window support, and historical player stat aggregation before choosing a source.

## Required investigation before implementation

Perform RCA first and determine what live player data sources currently exist:

- RCON session payload
- any RCON player-list command/wrapper already available in the codebase
- AdminLog kill/death events
- existing historical player stat materialization
- current open AdminLog match window if available

Document the chosen source in the done task notes:

- what was available
- what was not available
- whether stats are complete, partial, or event-derived

## Implementation requirements

### 1. Backend endpoint

Add or extend a backend endpoint for current-match player stats.

Preferred route:

- `GET /api/current-match/players?server=...`

### 2. Supported servers

Support:

- `comunidad-hispana-01`
- `comunidad-hispana-02`

### 3. Unknown server values

- Return a safe 400/404 style response.
- Do not query arbitrary targets.

### 4. Data model

The endpoint should return:

- `server_slug`
- `server_name`
- `scope`
- `confidence`
- `source`
- `captured_at` or `updated_at`
- `items`: array of player rows

### 5. Player row fields

Include only fields that can be supported reliably:

- `player_name`
- `team` if known
- `kills` if known
- `deaths` if known
- `teamkills` if known
- `deaths_by_teamkill` if known
- `favorite_weapon` or `most_used_weapon` if known
- `last_seen_at` if known
- `confidence`/`source` if needed

### 6. AdminLog-derived data

If using AdminLog-derived data:

- Clearly mark scope/confidence as partial/event-derived.
- Only include players observed in recent/current match event windows.
- Do not imply this is the full server roster.
- Use a freshness threshold consistent with kill feed freshness logic.
- If no current/open event window exists, return empty items with a clear scope.

### 7. RCON player-list data

If a real RCON player-list command exists:

- Prefer it for live roster.
- Combine it with AdminLog-derived kills/deaths only when safe.
- Mark fields not supported by RCON as null.
- Do not block the endpoint indefinitely on RCON timeouts.

### 8. Frontend rendering

Replace the static "Estadísticas en vivo" placeholder with dynamic rendering.

If items exist:

- Show a compact table or cards with player stats.
- Sort by kills descending, then deaths ascending, then name.
- Indicate if stats are partial.

If items are empty, show:

- "Todavía no hay estadísticas fiables de jugadores para esta partida."

If data is partial, show:

- "Estadísticas parciales derivadas de eventos recientes."

### 9. Frontend polling

- Poll player stats with the current-match page refresh cycle or a safe separate interval.
- Avoid overlapping requests.
- Do not flicker table rows on every poll.
- Avoid duplicate player rows.

### 10. Tests

Add focused backend tests for:

- unsupported server rejection
- empty current stats response
- AdminLog-derived player aggregation if used
- stale event filtering
- no raw AdminLog exposure
- stable sorting
- partial confidence metadata

## Validation

Run:

- `python -m compileall backend/app`
- focused backend tests if available
- `node --check frontend/assets/js/partida-actual.js`

## Manual verification checklist

- Call `Invoke-RestMethod "http://localhost:8000/api/current-match/players?server=comunidad-hispana-01" | ConvertTo-Json -Depth 20`.
- Call `Invoke-RestMethod "http://localhost:8000/api/current-match/players?server=comunidad-hispana-02" | ConvertTo-Json -Depth 20`.
- Verify unsupported server values are rejected safely.
- Open `http://localhost:8080/partida-actual.html?server=comunidad-hispana-01`.
- Open `http://localhost:8080/partida-actual.html?server=comunidad-hispana-02`.
- Verify the "Estadísticas en vivo" section no longer remains permanently empty when current reliable/partial player data exists.
- Verify the UI clearly says when stats are partial or unavailable.
- Verify no fake players are shown.
- Verify no raw AdminLog lines are shown.
- Verify existing historical detail stats still work.

## Expected outcome

The current-match page can show live or partial player statistics when supported by reliable/current data, and otherwise shows a clear honest empty state.

## AI Platform lifecycle

After implementation and validation:

- Move this task according to the lifecycle defined in `AGENTS.md`.
- Do not mark unrelated tasks as done automatically.

## Outcome

### RCA and source choice

- `RCON getSession` remains available for the current-match header but its current player count is explicitly marked `rcon-session-unverified`.
- No dedicated RCON player-list wrapper or route exists in the current `rcon_client` implementation.
- AdminLog kill events already expose safe normalized player names, teams, weapons and current-match window/freshness handling through the kill-feed read model.
- The historical AdminLog materializer derives player combat stats from the same kind of kill events for closed matches.
- Chosen source: current/fresh normalized AdminLog kill rows. The new current-match player projection is intentionally `event-derived-partial`, not a complete live roster.

### Change summary

- Added `GET /api/current-match/players?server=...` for trusted active current-match servers only.
- Added a safe AdminLog-derived player aggregator with kills, deaths, teamkills, teamkill deaths, team, last-seen timestamp and favorite weapon when observed.
- Kept stale fallback filtering aligned with the current kill feed and kept raw AdminLog messages out of the payload.
- Replaced the static current-match player placeholder with a polled partial-stat table and an honest empty state.

### Validation

- Ran `python -m compileall backend/app`.
- Ran `node --check frontend/assets/js/partida-actual.js`.
- Attempted `python -m pytest backend/tests/test_current_match_payload.py backend/tests/test_rcon_admin_log_storage.py`; the active Python environment does not have `pytest` installed.
- Ran a direct Python smoke harness for trusted/unsupported route resolution, AdminLog aggregation, teamkill handling, stale filtering and raw-log exclusion.
- Ran `scripts/run-historical-ui-regression-tests.ps1`.
- Ran `git diff --check` and `git diff --name-only`.
- Task-specific changed product files are `backend/app/routes.py`, `backend/app/payloads.py`, `backend/app/rcon_admin_log_storage.py`, `backend/tests/test_current_match_payload.py` and `frontend/assets/js/partida-actual.js`. The current worktree also contains `frontend/assets/css/historico.css` from completed `TASK-154`.
- Rendered Browser QA remains to be repeated when the Browser automation entry point is exposed in-session.
