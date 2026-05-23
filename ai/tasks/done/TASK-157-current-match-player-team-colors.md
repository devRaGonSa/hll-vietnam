# TASK-157 - Current match player team colors

Status: done

## Goal

Render current-match player/stat rows with team-aware colors/styles consistent with the historical match detail page.

## Background

The current-match page now has a live player/statistics section backed by:

- `GET /api/current-match/players?server=...`

The current implementation is AdminLog-derived and partial/event-derived because:

- RCON `getSession` player counts are unverified.
- No current RCON player-list wrapper exists in the codebase.
- AdminLog kill events can identify players involved in recent/current events.

The user now wants players to be shown like in the historical detailed match page:

- Players should be visually distinguishable depending on team.
- Team coloring should match or be consistent with the historical match detail page.
- The current live stats section should not remain visually generic.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `frontend/assets/js/partida-actual.js`
- `frontend/partida-actual.html`
- the historical match detail frontend code and CSS that already color player teams

Inspect the current `/api/current-match/players` payload, the live player rendering, and existing historical detail team classes before choosing frontend or backend changes.

## Expected Files to Modify

Allowed changes:

- `frontend/assets/js/partida-actual.js`
- `frontend/partida-actual.html` if needed
- `frontend/assets/css/historico.css` or relevant current-match CSS
- `backend/app/payloads.py` only if team fields are not currently projected clearly
- `backend/app/rcon_admin_log_storage.py` only if normalized team values need cleanup
- focused tests if backend normalization changes

## Constraints - DO NOT BREAK

- Do not fabricate team values.
- Do not imply the player list is a complete live roster if it is only AdminLog-derived.
- Do not expose raw AdminLog lines.
- Do not expose admin-only/sensitive fields.
- Do not break historical match detail player stats.
- Do not break historical materialization.
- Do not query RCON directly from the frontend.
- Do not depend on server #03.
- Do not show misleading team colors if team is unknown.
- Do not show fake players.

## Implementation Requirements

### 1. RCA first

- Inspect the current `/api/current-match/players` response.
- Determine whether each player row includes team or enough information to infer team safely.
- Compare CSS/classes used by the historical match detail page for team coloring.

### 2. Backend data contract

If player rows already include reliable team values:

- Preserve the existing endpoint and document available team fields.

If team values exist in storage but are not exposed:

- Add normalized team fields to each player row, for example:
  - `team`
  - `team_label`
  - `team_side`
- Use only values supported by AdminLog/current data.

If team is unknown:

- Return null/unknown.
- Do not guess.

### 3. Frontend rendering

- Update the current-match player stats section so rows/cards are styled by team:
  - Allied/US/Soviet/Commonwealth/etc. side should use the same or consistent allied styling.
  - Axis/Germany side should use the same or consistent axis styling.
  - Unknown team should use neutral styling.
- Reuse historical detail team classes if possible.
- If historical detail uses existing CSS modifiers, prefer them over creating conflicting styles.

### 4. Visual requirements

- Player name should be readable.
- Team color should be visible but not overwhelming.
- Team badge/label may be shown if useful.
- Partial/event-derived confidence must remain visible.
- The section should not look like a final historical table unless data is complete.

### 5. Sorting

- Preserve current sorting if implemented:
  - kills descending
  - deaths ascending
  - name
- If not implemented, add stable sorting consistent with current endpoint.

### 6. Empty state

If no player data exists:

- Show: "Todavia no hay estadisticas fiables de jugadores para esta partida."

### 7. Partial state

If stats are AdminLog-derived:

- Show: "Estadisticas parciales derivadas de eventos recientes."
- Do not imply this is the complete roster.

### 8. Tests

If backend changes are made, add/update focused tests for:

- team fields are projected when available
- unknown team remains unknown/neutral
- no raw AdminLog exposure
- unsupported server rejection still works
- partial/event-derived metadata is preserved

### 9. Validation

- Run `python -m compileall backend/app` if backend changed.
- Run focused backend tests if changed.
- Run `node --check frontend/assets/js/partida-actual.js`.
- Run `git diff --check`.

## Manual Verification Steps

- Call `Invoke-RestMethod "http://localhost:8000/api/current-match/players?server=comunidad-hispana-01" | ConvertTo-Json -Depth 20`.
- Call `Invoke-RestMethod "http://localhost:8000/api/current-match/players?server=comunidad-hispana-02" | ConvertTo-Json -Depth 20`.
- Verify player rows include team/side data when available or unknown/null when not.
- Open `http://localhost:8080/partida-actual.html?server=comunidad-hispana-01`.
- Open `http://localhost:8080/partida-actual.html?server=comunidad-hispana-02`.
- Verify live player/stat rows are colored by team when team is known.
- Verify unknown-team players use neutral styling.
- Verify the section clearly indicates partial/event-derived stats.
- Verify no fake complete roster is implied.
- Verify historical match detail player colors still work.

## Expected Outcome

The current-match player/stat section uses team-aware colors consistent with the historical detail page while remaining honest about partial/event-derived live data.

## Outcome

- RCA found no backend contract gap: a live
  `/api/current-match/players?server=comunidad-hispana-01` response observed
  before the validation rebuild already exposed AdminLog-derived `team` values
  such as `Allies` and `Axis`; unknown values remain handled by the existing
  frontend neutral path.
- Reused the historical detail player row and team badge CSS modifiers from
  `historico-scoreboard-detail.css` in the current-match player table instead
  of adding a parallel style system.
- Included `team` in the visible player-table signature so a future team update
  can rerender an already-visible row without changing its stats.
- Validated with:
  - `node --check frontend/assets/js/partida-actual.js`
  - `git diff --check`
  - `docker compose up -d --build frontend`
  - live `/api/current-match/players` checks on Comunidad Hispana `#01` and
    `#02`
  - rendered Chrome headless current-match validation for the available player
    empty state after the backend restart
  - served-script check confirming the historical row and badge modifiers are
    present in `frontend/assets/js/partida-actual.js`
- The final rendered validation window had no current player rows after the
  backend rebuild, so known-team colors were validated from the observed live
  payload contract plus the reused historical class mapping rather than from a
  live colored-row screenshot.
- Repository-level follow-up validation ran
  `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`.
  It returned exit code `0`, but its output also printed a historical SQLite
  `database disk image is malformed` traceback after the pass banner; that
  historical storage issue is outside this frontend task scope.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
