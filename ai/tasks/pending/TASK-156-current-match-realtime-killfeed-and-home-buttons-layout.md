# TASK-156 - Current match realtime killfeed and home buttons layout

Status: pending

## Goal

Refine the current-match kill feed into a real-time FPS-style panel and make the home server card buttons sit at the bottom-right aligned with the map card, without changing unrelated layout.

## Background

The current-match page already has a compact kill feed overlay implemented in `frontend/assets/js/partida-actual.js` and related CSS.

The current visual direction is closer to the goal, but the desired behavior is now more specific:

- The feed should feel like a real-time FPS killfeed screen.
- It should not look like a static list of historical events.
- Each event should show only:
  - killer
  - weapon icon or compact weapon label
  - victim
- The feed should behave like a small rectangular live panel.
- Events should fill from top to bottom in three visual columns.
- As new events arrive, old events should visually shift left and eventually disappear.
- The visible feed must be capped and must not grow indefinitely.
- Repeated polling must not duplicate events or cause visual flicker.

There is also a small home page layout request:

- In the home server cards, only the "Historico" and "Partida actual" buttons should remain.
- Those buttons should sit lower, at the bottom-right, aligned with the map card height.
- Do not change anything else in the home layout.

Current user-observed issues:

- The kill feed is still too much like a list rather than a real-time screen.
- The home server card buttons are still too high and leave unused empty space in the bottom-right corner.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `frontend/partida-actual.html`
- `frontend/assets/js/partida-actual.js`
- `frontend/assets/js/main.js`

Inspect the current-match kill feed behavior, current polling/deduplication state, relevant current-match CSS, and the home server card action markup before changing code.

## Expected Files to Modify

Allowed changes:

- `frontend/assets/js/partida-actual.js`
- `frontend/partida-actual.html` if needed
- `frontend/assets/css/historico.css` or relevant current-match CSS
- `frontend/assets/css/styles.css` or home CSS for the server card button alignment
- `frontend/assets/js/main.js` only if the button markup still needs cleanup
- local weapon icon/fallback assets if necessary
- focused frontend validation

## Constraints - DO NOT BREAK

- Do not break `/api/current-match/kills`.
- Do not expose raw AdminLog lines.
- Do not fabricate kill events.
- Do not show stale kills as live kills.
- Do not query RCON directly from the frontend.
- Do not break the current-match scoreboard/header.
- Do not break the historical page.
- Do not break historical match detail pages.
- Do not depend on server #03.
- Do not add external/CDN image dependencies.
- Do not reintroduce the home card "Scoreboard publico" button.
- Do not change the home server card content except button placement/layout if not strictly needed.
- Keep current public scoreboard URLs trusted and without `/games`.

## Implementation Requirements

### 1. Current-match kill feed layout

- Replace any remaining card/list feel with a compact rectangular "live feed screen".
- The feed should visually fit in a bounded panel.
- It should not expand vertically without limit.
- It should show a maximum number of events, for example 12 or 15.

### 2. Event rendering

Each event must show only:

- killer name
- weapon icon or compact weapon badge
- victim name

Avoid noisy timestamp display in the main row unless it is subtle or useful.

### 3. Three-column live flow

- Desktop layout must visually use three columns.
- Events should fill top-to-bottom and then across columns in a predictable way.
- Newer events should be visually prioritized.
- Older events should move/disappear as the capped list updates.
- On tablet/mobile, fall back safely to two columns or one column.

### 4. Real-time behavior

- Preserve `event_id` deduplication.
- Do not duplicate rows on polling.
- Avoid full-panel flicker every poll.
- Keep already-rendered events stable when no new events arrive.
- Add/remove events cleanly when the cap is exceeded.

### 5. Weapon display

- Use local/fallback icons or compact glyph badges.
- Include mappings for currently seen examples:
  - `M1 GARAND`
  - `MP40`
  - `M1A1 THOMPSON`
  - `UNKNOWN`
- Unknown weapons should show a generic fallback, not broken image.
- Do not use external URLs.

### 6. Teamkill

- Teamkills must remain distinguishable but compact.
- Do not let teamkill badges dominate the layout.

### 7. Feed copy

- If there are no current events: "Todavia no se han detectado bajas en esta partida."
- If events are current/open-window: "Bajas detectadas en la partida actual."
- If events are fresh but partial: "Cobertura parcial desde AdminLog reciente."
- If stale/no current events: "Sin bajas recientes asociadas a la partida actual."

### 8. Home server card layout

- Ensure only two per-server buttons are visible:
  - "Historico"
  - "Partida actual"
- Remove/hide "Scoreboard publico" from the home server card.
- Move the two buttons down to the lower-right of the card, aligned visually with the map card at the bottom-left.
- Keep the map card compact and do not enlarge it.
- Do not change the rest of the home content/layout.
- Preserve responsive behavior.

### 9. Validation

- Run `node --check frontend/assets/js/partida-actual.js`.
- Run `node --check frontend/assets/js/main.js` if modified.
- Run `git diff --check`.
- Rebuild frontend if needed.

## Manual Verification Steps

- Open `http://localhost:8080/partida-actual.html?server=comunidad-hispana-01`.
- Open `http://localhost:8080/partida-actual.html?server=comunidad-hispana-02`.
- Verify the kill feed looks like a compact rectangular live overlay.
- Verify each event row shows:
  - killer
  - weapon icon/badge
  - victim
- Verify the feed uses three columns on desktop.
- Verify older events disappear instead of growing endlessly.
- Verify repeated polling does not duplicate events.
- Verify the feed does not flicker on every refresh.
- Verify unknown weapons use a fallback.
- Verify no raw AdminLog line is displayed.
- Open the home page: `http://localhost:8080/`.
- Verify each server card shows only:
  - Historico
  - Partida actual
- Verify those buttons sit at the bottom-right, visually aligned with the map card.
- Verify no other home page layout area changes unexpectedly.

## Expected Outcome

The current-match kill feed behaves like a compact real-time combat overlay, and the home server card action buttons are cleanly aligned bottom-right with only "Historico" and "Partida actual" visible.

## Outcome

Document the validation performed, notable decisions, and any follow-up task that should be created instead of expanding this task.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
