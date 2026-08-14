---
id: TASK-292
title: Consolidate current-match frontend on snapshot polling
status: pending
type: frontend
team: Frontend Senior
supporting_teams: ["Backend Senior", "Experto en interfaz"]
roadmap_item: crcon-first-architecture
priority: critical
---

# TASK-292 - Consolidate current-match frontend on snapshot polling

## Goal

Implement the frontend consumer for the coherent current-match snapshot introduced by TASK-291.

The current current-match page independently requests:

- `/api/current-match`
- `/api/current-match/kills`
- `/api/current-match/players`

at different intervals. This creates multiple browser polling streams and allows the page to render summary, killfeed and player statistics from different source instants.

TASK-292 must introduce an explicit snapshot frontend transport which consumes:

`GET /api/current-match/snapshot?server=<slug>`

and derives the complete page state from that one response:

```text
browser
   |
   | one poll
   v
/api/current-match/snapshot
   |
   v
one coherent snapshot
   |
   +--> match summary
   +--> score / timer
   +--> player table
   +--> killfeed
   `--> freshness/degraded state
```

Do not remove the legacy frontend transport, change backend source selection or change deployment configuration.

## Context

TASK-291 added a coherent, cache-backed current-match snapshot and the read-only `/api/current-match/snapshot` route. That route is available when `HLL_CURRENT_MATCH_SOURCE=crcon`; the backend source default intentionally remains `legacy`.

The current `frontend/assets/js/partida-actual.js` has three separate live request owners and in-flight flags:

- summary: `/api/current-match`, every 30 seconds;
- killfeed: `/api/current-match/kills?limit=18`, every 1.5 seconds;
- players: `/api/current-match/players`, every 3 seconds.

The current timer display is refreshed with the summary request rather than by a per-second controller. Snapshot mode must use `remaining_seconds` as a synchronization basis and provide the required local countdown behavior without adding per-second network requests or redesigning the page.

The frontend already has page-scoped runtime configuration through body data attributes and `window.HLL_FRONTEND_CONFIG`. Prefer that existing convention; do not create a larger configuration framework.

Preserve the current HLL Vietnam product identity: Spanish-speaking community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Critical Rollout Rule

TASK-291 intentionally left `HLL_CURRENT_MATCH_SOURCE=legacy` as the backend default. TASK-292 must not unconditionally switch every browser to the snapshot endpoint.

Implement an explicit frontend transport selection:

`legacy | snapshot`

The frontend transport must also remain `legacy` by default.

- In `legacy` transport, retain current behavior and the existing summary/kills/players loops.
- In `snapshot` transport, use only `/api/current-match/snapshot` for live current-match data.
- Never run the legacy loops and snapshot loop concurrently.
- Do not automatically fall back from snapshot to legacy after a failed snapshot request, including HTTP 503.
- Rollback must remain an explicit operator choice.
- Do not infer frontend transport from the backend source, response probing or availability.

This keeps the two independent rollout controls explicit:

```text
backend source: legacy | crcon
frontend transport: legacy | snapshot
```

A future rollout may deliberately select `backend=crcon` and `frontend=snapshot` only after actual CRCON bindings and deployment validation exist. That rollout is outside this task.

## Frontend Transport Configuration

Inspect current frontend runtime/configuration conventions before finalizing the selector.

Prefer an existing runtime/page configuration mechanism. A minimal page-scoped static selector such as `data-current-match-transport="legacy"` is acceptable and fits the current page convention, but do not invent a larger frontend configuration framework.

Requirements:

- only `legacy` and `snapshot` are accepted;
- a missing value selects `legacy`;
- an invalid value selects safe `legacy` or produces an explicit development error consistent with current frontend conventions;
- do not use `localStorage`;
- do not use a query-string debug switch as the production mechanism;
- do not guess the backend source;
- do not probe the three legacy endpoints to determine the source;
- document the selected mechanism in Outcome.

## Steps

1. Read all required architecture, repository and TASK-291 material before editing.
2. Inspect the current page bootstrap, fetch helpers, renderer inputs, state retention, polling ownership and current frontend test conventions.
3. Add the smallest explicit `legacy | snapshot` transport selector, with `legacy` as the safe default.
4. Keep the existing legacy transport behavior available and unchanged while ensuring only one transport owns live state.
5. Add a single non-overlapping snapshot polling controller and adapt one successful snapshot into one coherent page update cycle.
6. Reuse current summary, player, killfeed, map, weapon-icon and state renderers through a small adapter where practical.
7. Implement deterministic match-transition, identity-stabilization, killfeed reconciliation, truncated-window, countdown and degraded-state handling.
8. Add focused tests using existing repository conventions or the smallest lightweight extraction; do not introduce a frontend framework.
9. Run the required frontend checks and practical backend contract regressions.
10. Move the task from `pending` to `in-progress` when work begins and to `review` after validation; do not mark it done automatically.

## Files to Read First

Read completely:

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `docs/CRCON_FIRST_STATELESS_ARCHITECTURE.md`
- `docs/CRCON_FIRST_MIGRATION_AND_DECOMMISSION_PLAN.md`
- `ai/tasks/done/TASK-291-implement-crcon-first-current-match-snapshot.md`

Inspect directly before implementation:

- `frontend/partida-actual.html`
- `frontend/assets/js/partida-actual.js`
- current-match CSS only for existing state classes; do not redesign
- shared frontend API/fetch helpers
- shared frontend bootstrap/config helpers
- current frontend test conventions
- `backend/app/current_match.py` for the snapshot contract, read only
- `backend/app/payloads.py` for compatibility contracts, read only
- `backend/app/routes.py` for route/error semantics, read only
- `backend/tests/test_crcon_current_match.py` for snapshot examples, read only

Also inspect the relevant portions of these completed frontend tasks where useful, without modifying them:

- TASK-151
- TASK-152
- TASK-153
- TASK-155
- TASK-156
- TASK-157
- TASK-158
- TASK-159
- TASK-241
- TASK-257
- TASK-258
- TASK-261
- TASK-262

## Snapshot Contract

Consume the TASK-291 snapshot fields as applicable:

- `server`
- `server_slug`
- `match_id`
- `identity_kind`
- `map`
- `layer`
- `mode`
- `started_at`
- `score`
- `remaining_seconds`
- `player_count`
- `max_player_count`
- `allied_count`
- `axis_count`
- `players`
- `kills`
- `killfeed_truncated`
- `version`
- `observed_at`
- `sources`
- `degraded`
- `degraded_reasons`

The frontend must understand only the HLL snapshot contract, not raw CRCON concepts.

## Single Polling Stream

In snapshot mode there must be exactly one live polling controller. Disable snapshot-mode use of the independent summary, killfeed and player timers; do not leave hidden duplicate fetches.

Use approximately a 2-second interval because TASK-291's backend cache TTL is 1.5 seconds. Select the exact interval after confirming current UI behavior, but keep one coherent interval and do not poll faster than the backend cache TTL without explicit justification in Outcome.

Do not use a naive `setInterval` that can stack requests when the server is slow. Use the smallest repository-conventional strategy that ensures:

- at most one snapshot request is in flight per page;
- the next refresh is scheduled only after the previous cycle settles;
- navigation/unload stops unnecessary work where practical;
- an older response cannot overwrite newer page state.

`AbortController` may be used if consistent with repository browser support, but do not add a framework.

## One Snapshot, One Page Update Cycle

Treat every successful snapshot as one coherent state transition:

```text
snapshot
   -> normalize/derive view state
   -> apply summary
   -> apply players
   -> reconcile killfeed
   -> apply freshness/degraded state
```

Do not update summary, players and kills from unrelated requests. All components in one update cycle must identify the same `match_id`, `version` and `observed_at`.

Avoid rewriting mature UI code. Prefer a small adapter from `CurrentMatchSnapshot` JSON into existing renderer inputs, including player table and killfeed shapes. Preserve current weapon normalization and icon mapping.

## Match Transition Handling

Use `match_id`, `identity_kind` and `version` as authoritative transition signals.

When `match_id` changes:

- clear match-specific killfeed reconciliation state;
- clear old player state where necessary;
- reset the local countdown basis;
- discard old event cursor/event IDs;
- render the new snapshot coherently;
- never combine previous-match kills with new-match players.

An `em1.* -> cm1.*` identity change may describe the same actual live game as CRCON identity stabilizes. Inspect TASK-291 semantics and use map/start evidence to avoid a visual new-match flash when it is only identity stabilization. Any stored kill cursor based on the old match ID is invalid and must still be reset safely. Keep this logic small and tested.

## Killfeed Reconciliation

Snapshot responses contain a bounded current-event window. Do not append the full `kills` array on every poll.

Requirements:

- the initial snapshot renders the recent window according to current UX;
- an unchanged snapshot/version creates no duplicate DOM events;
- new events append only once;
- equal timestamps with different event IDs/cursors remain distinct;
- a new match clears old events;
- order remains chronological;
- the current bounded visible/retained behavior remains intact;
- existing weapon icon normalization and TASK-258/TASK-261 layout behavior do not regress.

When `killfeed_truncated` is true and the client's last known cursor/event is no longer represented in the retained server window, do not pretend continuity. Deterministically resynchronize to the retained snapshot window, do not invent events and do not introduce duplicates. A suitable existing non-intrusive state may note resynchronization, but do not add a warning component or redesign.

## Player Table

Use snapshot `players` exclusively in snapshot mode. Preserve:

- team grouping and colors;
- player name rendering;
- K/D/TK;
- favorite weapon/icon;
- combat/offense/defense/support where shown;
- unit/role/level/status where consumed;
- existing sorting semantics unless the snapshot already provides the authoritative product ordering;
- TASK-262 deduplication expectations.

Do not concurrently use the legacy player endpoint in snapshot mode.

## Match Summary and Countdown

Use the same snapshot for map/layer/mode, score, player/team counts, match start, remaining time, server information and any existing degraded/freshness indication. Do not call `/api/current-match` in snapshot mode.

Do not require a network request every second. Use `remaining_seconds` and `observed_at` as synchronization inputs for a local countdown between successful polls. On each new snapshot:

- rebase the countdown safely;
- avoid visible jumps caused only by small network latency;
- reset correctly on a real match change;
- prevent previous-match countdown state from leaking into the new match.

Keep current copy and presentation; do not redesign the countdown.

## Degraded, Stale and Unavailable Behavior

Snapshot mode must not convert source or request problems into fake zero/empty states. Use `degraded`, `degraded_reasons`, `sources` and `observed_at` to preserve the last trustworthy display when appropriate and express stale/degraded state through existing page patterns.

A temporary request failure must not immediately erase a valid displayed match. However:

- never silently switch to legacy transport;
- never fabricate updated timestamps;
- never render a source failure as zero players, kills or score;
- do not retain stale data forever without stale/unavailable indication;
- use conservative, bounded UI behavior.

If snapshot mode receives HTTP 503, remain in snapshot transport and use existing unavailable/degraded behavior. Do not activate the three legacy streams. Explicit operator selection of legacy is the rollback mechanism.

## Preserve Existing Visual Product

This is a data-flow migration, not a visual redesign. Preserve:

- current layout and responsive behavior;
- map presentation and images;
- score display and countdown presentation;
- player tables, ordering and team colors;
- killfeed layout and bounded behavior;
- weapon icons;
- match/history links and navigation;
- loading, empty and error states;
- Spanish copy unless a correctness change is strictly necessary.

Do not change CSS merely because the source shape changes. Prefer adapting snapshot data to the current view model.

## Request-Count and Performance Acceptance

Add a deterministic test or instrumentation-friendly seam proving that in snapshot mode one poll cycle produces exactly one live current-match HTTP request, to:

`/api/current-match/snapshot`

and zero requests to:

- `/api/current-match`
- `/api/current-match/kills`
- `/api/current-match/players`

Legacy mode must preserve the existing request behavior and make no snapshot call unless explicitly configured for snapshot transport.

Document the actual before/after request cadence based on source code. The observed starting point is three independent streams at 30 seconds, 1.5 seconds and 3 seconds; verify it during execution. The target snapshot mode is one non-overlapping stream near 2 seconds. Do not invent production bandwidth/CPU savings, and do not take production measurements.

## Frontend Testing

Inspect existing test infrastructure first. Do not introduce React, Vite, Jest, Vitest or another frontend framework solely for this task.

Prefer existing repository test conventions. If Node's built-in test runner or another existing lightweight JS setup is available, use it. Otherwise use the smallest testable extraction and repository-conventional validation.

Tests must cover at minimum:

1. transport default is `legacy`;
2. explicit `snapshot` transport selection;
3. exactly one HTTP request per snapshot polling cycle;
4. no legacy endpoint calls in snapshot mode;
5. no snapshot endpoint calls in legacy mode beyond explicit configuration;
6. the same version does not duplicate killfeed events;
7. a new kill event appends once;
8. identical timestamps with different cursors remain distinct;
9. a match transition clears old match-specific state;
10. ephemeral-to-canonical identity stabilization does not mix cursor state;
11. a truncated feed resynchronizes safely;
12. the player table consumes snapshot values;
13. score, map and counts consume the same snapshot;
14. the countdown rebases correctly;
15. a degraded snapshot does not become fake zeroes;
16. a transient request failure preserves bounded last-good state;
17. HTTP 503 does not activate legacy transport;
18. overlapping snapshot requests are prevented.

Preserve or minimally improve existing visibility, scheduling, cancellation, DOM-readiness and unload behavior where present. Do not broaden this work into generic frontend performance work.

## Expected Files to Modify

Prefer a narrow scope:

- `frontend/assets/js/partida-actual.js`
- `frontend/partida-actual.html` only if needed for the explicit transport selector
- focused frontend/current-match tests using repository conventions
- the TASK-292 lifecycle file

A tiny shared frontend helper is acceptable only when an existing convention clearly warrants it.

Avoid CSS changes. Do not modify backend, deploy or dependencies unless genuinely unavoidable.

## Constraints

- Keep `legacy` as both the backend default and frontend transport default.
- Do not remove or change the compatibility endpoints.
- Do not run both frontend transports simultaneously.
- Do not add automatic snapshot-to-legacy fallback.
- Do not depend on raw CRCON response concepts in the browser.
- Do not redesign the page or regress TASK-258/TASK-261 behavior.
- Do not introduce a framework or unnecessary dependency.
- Do not modify completed tasks.
- Do not access SSH, Portainer, production Docker, production CRCON API, production PostgreSQL, production RCON, production secrets or deployments.
- Do not restart services or change runtime production environment, CRCON credentials or bindings.
- Do not modify `deploy/**`, Compose files or Dockerfiles.
- Do not modify or execute TASK-272 through TASK-281 or TASK-284.
- Do not modify resolved TASK-287, TASK-288, TASK-289, TASK-290 or TASK-291.
- Do not modify or stage the six protected local untracked task files listed below.

Protected local files:

- `ai/tasks/done/TASK-204-align-public-page-heroes-and-navigation-labels.md`
- `ai/tasks/done/TASK-242-match-countdown-label-capsule-style.md`
- `ai/tasks/in-progress/TASK-264-investigate-current-match-killfeed-adminlog-staleness.md`
- `ai/tasks/in-progress/TASK-266-audit-and-implement-historical-support-leaderboards.md`
- `ai/tasks/in-progress/TASK-267-investigate-current-match-live-data-staleness-and-clean-copy.md`
- `ai/tasks/in-progress/TASK-268-investigate-current-match-adminlog-ingestion-latency.md`

TASK-292 is frontend-only by default. Do not modify:

- `backend/app/current_match.py`
- `backend/app/crcon/**`
- `backend/app/config.py`
- `backend/app/payloads.py`
- `backend/app/routes.py`

If a real backend contract bug prevents implementation, do not silently expand the task. Record the blocker in Outcome and stop in review rather than redesigning backend contracts inside this frontend task.

## Validation

Before moving the task to review:

- run the focused frontend/current-match tests selected from repository conventions;
- run syntax/static validation for every modified JavaScript file, including `node --check frontend/assets/js/partida-actual.js` when it changes;
- run existing relevant frontend tests;
- run TASK-291 current-match tests, TASK-290 foundation tests and legacy current-match payload tests as contract regressions when practical;
- run `git diff --check`;
- run `git diff --name-only` and confirm only expected files changed;
- run `git status --short` and confirm protected files remain untouched;
- confirm through search/tests that snapshot mode makes no live request to `/api/current-match`, `/api/current-match/kills` or `/api/current-match/players`;
- confirm exactly one polling owner requests `/api/current-match/snapshot`;
- verify both `legacy` and `snapshot` transports without production access;
- document explicitly if no additional integration test is configured for the affected frontend scope;
- do not execute TASK-284.

## Outcome

Document:

- the selected frontend transport configuration mechanism and why it fits existing conventions;
- confirmation that missing configuration defaults to `legacy`;
- the actual polling owners/cadences before and after the change;
- the adapter or renderer-reuse decision;
- match transition and ephemeral-to-canonical handling;
- killfeed cursor/reconciliation and truncated-window behavior;
- countdown rebasing behavior;
- degraded, transient-failure and HTTP 503 behavior;
- the exact tests and static checks run;
- the final modified-file list;
- any backend contract blocker, as a blocker rather than an unplanned backend change;
- any follow-up task that should be created instead of expanding this scope.

## Lifecycle

- Move `pending -> in-progress` when implementation begins.
- Move `in-progress -> review` after validation.
- Do not mark the task done automatically.
- Suggested implementation branch: `feature/task-292-current-match-snapshot-frontend`.
- Open a draft PR.
- Do not merge automatically.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- If the snapshot adapter, controller and focused tests cannot fit this budget without harming clarity, document the reason rather than omitting required regression coverage.
- Split unrelated or backend work into a follow-up task.
