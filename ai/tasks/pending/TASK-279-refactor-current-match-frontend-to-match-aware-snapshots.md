---
id: TASK-279
title: Refactor current-match frontend to match-aware snapshots
status: pending
type: frontend
team: Frontend Senior
supporting_teams: ["Backend Senior", "Experto en interfaz"]
roadmap_item: current-match-crcon-parity
priority: high
---

# TASK-279 - Refactor current-match frontend to match-aware snapshots

## Goal

Make the current-match page consume one match-aware snapshot, reset correctly on every lifecycle transition and stop preserving or summing stale data from a previous match.

## Context

The current page polls summary, kills and players independently. The kill feed preserves previous events when a new response is empty and the context signature has not changed, but the kill response does not currently provide a reliable match identity. Player deduplication can also sum overlapping aggregate rows.

The unified API from TASK-278 provides the identity and state required to make frontend behavior deterministic.

## Steps

1. Replace the three independent data loops with one snapshot coordinator, plus an optional incremental kill cursor only when justified by the new API.
2. Store the active `match_instance_id` centrally for the page.
3. When the identity changes:
   - clear kill feed immediately
   - clear player rows immediately
   - reset cursors/signatures
   - render the new map/lifecycle state even before the first kill
4. When `match_status` is not `live`, show the appropriate starting/between/ended state without retaining old combat data.
5. Preserve previous data only for a transient stale/degraded response with the exact same `match_instance_id`.
6. Remove additive merging of overlapping aggregate player snapshots; prefer the canonical backend row and log/ignore identity anomalies safely.
7. Use the event cursor for incremental feed updates and reset it on match change.
8. Add `cache: "no-store"`, request timeouts/abort handling and bounded exponential backoff.
9. Pause or reduce polling while the tab is hidden and refresh immediately when it becomes visible.
10. Align polling cadence with actual producer cadence rather than querying kills every 1.5 seconds unnecessarily.
11. Display concise freshness/degraded indicators using existing visual patterns without redesigning the page.
12. Add frontend regression tests or deterministic JS harness coverage for lifecycle transitions and stale responses.

## Files to Read First

- `AGENTS.md`
- `docs/current-match-crcon-parity-contract.md`
- `docs/frontend-backend-contract.md`
- `frontend/partida-actual.html`
- `frontend/assets/js/partida-actual.js`
- relevant current-match frontend tests/harness files

## Expected Files to Modify

- `ai/tasks/in-progress/TASK-279-refactor-current-match-frontend-to-match-aware-snapshots.md`
- `frontend/assets/js/partida-actual.js`
- `frontend/partida-actual.html` only if additional existing-style state hooks are required
- current-match frontend tests/harness files
- current-match frontend contract documentation if required

## Constraints

- Preserve the current visual identity, layout, weapon icons and responsive behavior.
- Do not add a frontend framework.
- Do not call CRCON directly from the browser.
- Do not preserve kills or players across different `match_instance_id` values.
- Do not sum complete aggregate snapshots together.
- Do not increase public polling load.
- Do not modify historical/ranking pages.

## Validation

Before completing the task ensure:

- map transition clears previous kills before the first kill of the new match
- consecutive identical maps still reset because identity changes
- between-matches and unavailable states do not show old players/kills
- same-match transient failures preserve the last visible snapshot with a warning
- cursor resets on match change and does not request incompatible event ids
- hidden-tab behavior and request cancellation work
- polling frequency is reduced or aligned with snapshot production
- responsive rendering and existing weapon/team badges remain intact
- frontend regression checks pass
- `git diff --name-only` matches the current-match frontend scope

## Outcome

Document the new polling/state model, transition behavior and any compatibility endpoint still required.

## Change Budget

- Prefer one coordinated state model inside the existing JavaScript file.
- Split visual redesign requests into separate tasks.
