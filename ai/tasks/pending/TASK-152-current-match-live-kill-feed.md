---
id: TASK-152
title: Current match live kill feed
status: pending
type: backend
team: Backend Senior
supporting_teams:
  - Frontend Senior
roadmap_item: rcon-full-data
priority: high
---

# TASK-152 - Current match live kill feed

## Goal

Expose recent current-match kill events and render them as a live visual feed
on `partida-actual.html`.

## Background

The current-match page will exist at
`partida-actual.html?server=<server_slug>`. The backend already stores/parses
RCON AdminLog data and materializes kill/player stats for historical matches.

Existing materialization logic uses AdminLog kill payload fields such as:

- `killer_id`
- `killer_name`
- `killer_team`
- `victim_id`
- `victim_name`
- `victim_team`
- `weapon`

We now want a live/current-match kill feed similar to a FPS kill feed: killer,
weapon, victim, teamkill distinction, timestamp.

## Constraints / DO NOT BREAK

- Do not query RCON directly from the frontend.
- Do not expose raw AdminLog lines.
- Do not expose admin-only/sensitive fields.
- Do not break existing historical materialization.
- Do not break existing match detail player stats.
- Do not depend on server #03.
- Do not fabricate kill events.
- Do not duplicate kill rows on repeated polling.
- Keep polling safe.

## Allowed Changes

- backend endpoint for current match kill feed
- backend read-model/helper for current/open match event window
- frontend current-match JS/CSS
- tests for event normalization/filtering where practical

## Implementation Requirements

1. Add a backend endpoint for recent current-match kill events by server.
2. Supported servers:
   - `comunidad-hispana-01`
   - `comunidad-hispana-02`
3. Unknown server values must return a safe 400/404 style response and must
   not query arbitrary targets.
4. The endpoint should return normalized event rows:
   - `event_id`
   - `event_timestamp` or `server_time`
   - `killer_name`
   - `killer_team`
   - `victim_name`
   - `victim_team`
   - `weapon`
   - `is_teamkill`
   - confidence/source if needed
5. The endpoint should only return events belonging to the current/open match
   if that can be determined.
6. If the current/open match window cannot be determined reliably, return a
   safe recent window and include a clear confidence marker, for example:
   - scope: `"recent-admin-log-window"`
   - confidence: `"partial"`
7. Do not return raw AdminLog text.
8. Add frontend rendering for a kill feed:
   - newest events visible at top or bottom consistently
   - killer name
   - weapon label/icon placeholder
   - victim name
   - timestamp
   - teamkill visual distinction
9. Prevent duplicate rendering:
   - track `event_id` values already rendered
   - update existing rows only if needed
10. Poll every 15-30 seconds.
11. Add an empty state:
    - "Todavía no se han detectado bajas en esta partida."
12. Add an error/stale state:
    - "No se pudo actualizar el feed de combate."
13. Do not show fake/sample kill events in production UI.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/backend-senior.md`
- current-match page files created by TASK-151
- AdminLog materialization/read-model files that already normalize kill data

## Expected Files to Modify

- backend current-match kill feed endpoint/read-model files
- current-match frontend JS/CSS files
- focused tests for event normalization/filtering where practical

## Validation

- `python -m compileall backend/app`
- Run backend tests related to AdminLog/materialization/current-match feed.
- Run `node --check` on current-match frontend JS.
- Review `git diff --name-only` and confirm the changed files match this task.

## Manual Verification

1. Open `partida-actual.html?server=comunidad-hispana-01`.
2. Open `partida-actual.html?server=comunidad-hispana-02`.
3. Verify kill feed renders only normalized events.
4. Verify repeated polling does not duplicate rows.
5. Verify teamkills are visually distinguishable.
6. Verify raw AdminLog lines are never displayed.

## Commit Message

`feat: add current match live kill feed`

## Expected Outcome

The current-match page can show a safe, normalized, non-duplicated live kill
feed based on RCON/AdminLog data.

## Outcome

Document the feed scope and confidence behavior, event normalization choices,
polling validation, and any follow-up task instead of expanding scope.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if the scope grows.
