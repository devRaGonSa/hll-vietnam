---
id: TASK-151
title: Current match page base
status: done
type: frontend
team: Frontend Senior
supporting_teams:
  - Backend Senior
roadmap_item: rcon-full-data
priority: high
---

# TASK-151 - Current match page base

## Goal

Create the first functional internal "Partida actual" page for active
Comunidad Hispana servers.

## Background

The home page will link to
`partida-actual.html?server=<server_slug>`. We need the first real version of
our internal current-match page.

This page should be visually aligned with the existing historical match detail
page, but it represents a live match instead of a closed historical match.

Important public scoreboard URLs:

- `comunidad-hispana-01` -> `https://scoreboard.comunidadhll.es`
- `comunidad-hispana-02` -> `https://scoreboard.comunidadhll.es:5443`

These are base URLs for the current public scoreboard and must not include
`/games`.

## Constraints / DO NOT BREAK

- Do not break the existing historical page.
- Do not break the existing match detail page.
- Do not change scoreboard correlation logic.
- Do not implement the live kill feed in this task unless there is already a
  safe endpoint that can be reused trivially.
- Do not fabricate closed-match data.
- Do not show final winner/duration/closed_at for a live match.
- Do not depend on server #03.
- Do not expose untrusted public scoreboard URLs.
- Keep polling moderate and safe.

## Allowed Changes

- `partida-actual.html`
- new frontend JS/CSS for current match page
- backend API endpoint only if needed
- backend read-model code only if needed for current live state
- tests where practical

## Implementation Requirements

1. Create or upgrade `partida-actual.html` as a real live-current-match page.
2. The page must read `?server=` from the URL.
3. Supported server values:
   - `comunidad-hispana-01`
   - `comunidad-hispana-02`
4. Unknown server values must show a safe error/empty state and must not build
   external URLs from the unknown value.
5. Add trusted current public scoreboard links:
   - `comunidad-hispana-01` -> `https://scoreboard.comunidadhll.es`
   - `comunidad-hispana-02` -> `https://scoreboard.comunidadhll.es:5443`
6. Add a "Ver scoreboard público" button using the trusted base URL for that
   server.
7. The page should display a live-match header with:
   - server name
   - live/online status
   - current map
   - game mode if available
   - `started_at` if available
   - current players / max players if available
   - last updated/captured timestamp
8. The page should display a scoreboard panel:
   - allied score if available
   - axis score if available
   - neutral state if scores are unavailable
9. Do not display:
   - final duration
   - final winner
   - `closed_at`
   - any copy implying that the match has finished
10. Add a placeholder section for future live kill feed:
    - title: "Feed de combate"
    - text explaining that live kill events will appear here when enabled
    - no fake kill rows
11. Add a player table section if current player stats are already available
    from existing APIs. If they are not available, show a clean placeholder:
    - "Las estadísticas en vivo aparecerán cuando haya datos suficientes."
12. Add frontend polling with safe in-flight protection:
    - default interval: 30 seconds
    - avoid overlapping requests
    - show stale/error states clearly
13. If no backend endpoint exists for current match state, add a minimal
    endpoint that derives the current server state from existing live/RCON
    snapshot data. Keep it read-only.
14. The endpoint response should be stable and minimal:
    - server slug/name
    - status
    - map
    - `game_mode`
    - `started_at`
    - `allied_score`
    - `axis_score`
    - players
    - `max_players`
    - `captured_at`/`updated_at`
    - `public_scoreboard_url` from trusted mapping

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/frontend-senior.md`
- current historical match detail frontend files
- live server backend/read-model files used by the existing server cards

## Expected Files to Modify

- `partida-actual.html`
- new current-match frontend JS/CSS files as needed
- minimal live-state backend endpoint/read-model files only if existing APIs
  cannot supply the page state
- focused tests where practical

## Validation

- `python -m compileall backend/app`
- Run backend tests relevant to live server/read model if available.
- Run `node --check` on modified/new frontend JS files.
- Review `git diff --name-only` and confirm the changed files match this task.

## Manual Verification

1. Open `partida-actual.html?server=comunidad-hispana-01`.
2. Open `partida-actual.html?server=comunidad-hispana-02`.
3. Verify the public scoreboard button opens:
   - `https://scoreboard.comunidadhll.es`
   - `https://scoreboard.comunidadhll.es:5443`
4. Verify `/games` is not used for the current public scoreboard button.
5. Verify no final/closed-match fields are shown.
6. Verify unknown server query values do not create unsafe links.

## Commit Message

`feat: add current match page base`

## Expected Outcome

A safe first version of the internal current-match page exists and can display
live server/match state without pretending the match is closed.

## Outcome

- Upgraded `partida-actual.html` into the first internal live match page and
  kept it aligned with the existing historical shell/styles.
- Added frontend polling every 30 seconds with an in-flight guard. The page
  rejects unknown `?server=` values before building any external link, and the
  public scoreboard button is populated only from the trusted backend
  projection.
- Added read-only `GET /api/current-match?server=`. It supports only active
  trusted scoreboard origins and projects the existing live server snapshot
  fields into the current-match shape. The current live snapshot persistence
  exposes status, map, population and capture time; score, game mode and match
  start fields remain `null`/unavailable when the snapshot source does not
  provide them.
- Kept the combat feed and live player statistics as honest empty placeholders
  for the follow-up tasks rather than fabricating closed-match or kill data.
- Validation: `python -m compileall backend/app`;
  `node --check frontend/assets/js/partida-actual.js`;
  `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`;
  narrow inline route guard check for missing/unknown current-match server
  values; narrow inline payload projection check using a controlled live
  snapshot document.
- Scope review: `git diff --name-only` and `git status --short` were reviewed.
  No focused product route test file exists in `backend/tests` for this API
  bootstrap layer yet.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if the scope grows.
