---
id: TASK-291
title: Implement CRCON-first coherent current-match snapshot
status: pending
type: backend
team: Backend Senior
supporting_teams: ["Arquitecto Python", "Arquitecto de Base de Datos"]
roadmap_item: crcon-first-architecture
priority: critical
---

# TASK-291 - Implement CRCON-first coherent current-match snapshot

## Goal

Implement the first product consumer of the CRCON adapter foundation.

Create a coherent CRCON-first current-match backend model and endpoint while
preserving the complete legacy current-match implementation as an explicit
rollback path.

TASK-291 must:

1. introduce the HLL current-match domain model;
2. read canonical live state from the CRCON API;
3. identify the current match using CRCON `map_history`;
4. read current-match kills and teamkills from CRCON `log_lines`;
5. derive coherent per-player current-match combat totals without HLL
   persistence;
6. add one canonical current-match snapshot service;
7. add `GET /api/current-match/snapshot`;
8. allow the three existing compatibility endpoints to project that same
   snapshot when CRCON mode is explicitly selected;
9. keep legacy current-match behavior available and the default;
10. implement request coalescing and very-short bounded memory caching; and
11. perform all development and testing locally with fixtures and fakes.

Do not migrate the frontend. Do not remove any legacy database, worker,
materializer, provider, snapshot or fallback.

## Context

TASK-289 accepted the CRCON-first stateless target and TASK-290 delivered the
dormant integration foundation in `backend/app/crcon/`. TASK-291 is the first
consumer migration in that accepted strangler sequence.

The repository must support both paths after this task:

```text
legacy mode (default)

frontend
   -> existing current-match routes
   -> existing legacy implementation

explicit CRCON mode

frontend / future frontend
   -> current-match routes
   -> one CurrentMatchSnapshotService
          |
          +-> CRCON public/live API
          +-> CRCON PostgreSQL read-only
          +-> TtlCache
          `-> per-server request coalescing
```

CRCON mode is request/cache driven. It must not write HLL gameplay persistence.
The default remains legacy until a later rollout task explicitly changes it.

The accepted upstream contract reference remains:

- repository: `https://github.com/MarechJ/hll_rcon_tool`;
- branch: `master`;
- commit: `4cf1e7e2fa691d849eaf85abb7065010e13f28e4`.

Inspect only that exact revision locally and read-only when choosing live API
operations, event values, table columns and query semantics. Do not silently
derive the implementation from a newer upstream revision.

## Critical Architecture Rules

Do not create another ingestion pipeline. CRCON mode must not use:

- HLL AdminLog storage;
- `rcon_admin_log_events`;
- `rcon_materialized_matches`;
- `rcon_match_player_stats`;
- current-match worker persistence;
- HLL checkpoints or event watermarks;
- HLL database writes; or
- HLL historical materialization.

Do not add direct RCON as a mandatory dependency. The base implementation must
work with CRCON API plus strictly read-only CRCON PostgreSQL. If the pinned
upstream proves that a required field cannot be obtained reliably, expose it as
degraded or optional and document the limitation instead of silently
reintroducing direct RCON.

## Source Selection Per Field

### CRCON API

Prefer the CRCON API for live fields such as:

- current map and layer/mode where available;
- match start;
- current score and remaining time;
- online player and Allied/Axis counts;
- live player team, unit, role and state; and
- combat, offense, defense and support values where reliably exposed.

Inspect the pinned upstream `get_live_game_stats`, `get_live_scoreboard` or the
current verified equivalent before selecting the minimum live operation(s).
Extend `CrconApiClient` only with verified operations required by this task.

Do not trust live K/D/TK aggregates blindly. TASK-289 recorded an upstream
accuracy caveat, so log-derived K/D/TK must remain canonical.

### CRCON PostgreSQL

Use the strictly read-only CRCON boundary for:

- current/open `map_history` identity;
- match start/end bounds;
- bounded current-match `log_lines`;
- kills, deaths, teamkills and weapons; and
- deterministic event ordering and cursors.

Add only capability-specific methods to `CrconDatabase`, or a small
current-match repository inside `backend/app/crcon/`. Do not expose arbitrary
SQL.

Every new query must be:

- `SELECT` only;
- parameterized;
- bounded by server and current match/time;
- deterministically ordered; and
- limit-controlled when returning events.

Retain every TASK-290 connection, read-only, timeout, cleanup and error
sanitization safeguard.

## Multi-Server Binding

Do not assume that one CRCON API origin represents every HLL server. Inspect the
existing trusted server/origin mapping, current CRCON scoreboard mapping and
pinned `server_number` behavior.

Introduce or reuse a small explicit, locally testable binding abstraction that
resolves per HLL server slug:

- API origin/configuration;
- CRCON `server_number`;
- database source when shared; and
- enabled capabilities.

Do not hardcode production addresses or require production values. Reuse an
existing safe mapping when available rather than duplicating it.

## Source Switch And Rollback

Introduce a narrowly scoped current-match source setting following repository
conventions, conceptually:

```text
HLL_CURRENT_MATCH_SOURCE=legacy|crcon
```

Requirements:

- default is `legacy`;
- legacy mode preserves existing behavior exactly;
- CRCON mode uses the new snapshot service;
- invalid values fail with an actionable configuration error;
- absent CRCON configuration does not break legacy startup; and
- an individual CRCON request failure never automatically falls back to
  legacy.

Rollback is explicit: an operator selects legacy mode. Automatic fallback is
forbidden because it would hide source failures and reintroduce mixed/coherence
problems.

## Domain Model

Add only current-match product models needed now. Recommended concepts are:

- `CurrentMatchSnapshot`;
- `CurrentMatchSummary`;
- `CurrentPlayer`;
- `KillEvent`; and
- `CurrentMatchSourceState`.

Exact names and module boundaries should follow repository conventions. The
domain must be independent of CRCON API payloads and database rows.

At minimum represent:

- server slug;
- match ID and identity kind (`canonical` or `ephemeral`);
- map, layer and game mode;
- `started_at`, score and `remaining_seconds`;
- total, Allied and Axis player counts;
- players and recent kills;
- deterministic version and `observed_at`;
- per-source freshness and source states; and
- degraded flag and reasons.

Never expose raw CRCON rows, raw log text or upstream payload objects.

## Canonical Match Identity

Prefer CRCON `map_history.id`, represented as an opaque HLL match ID.

If the API reports a live match before the matching `map_history` row exists,
derive a deterministic ephemeral identity from verified safe fields such as:

```text
configured server identity
+ public-info match start
+ canonical map/layer information
```

Mark the identity kind as `ephemeral`. When the real CRCON map ID appears, the
canonical identity replaces it. That transition must:

- change the snapshot version;
- invalidate cached live state for the previous identity;
- reset incompatible event cursors;
- never merge events from unrelated matches; and
- remain process-local without persisting an identity mapping.

Locate the current `map_history` row using a bounded read-only query with the
server discriminator, API match start, map identity, open/current state and
deterministic ordering. Do not accept an arbitrary latest row when it conflicts
materially with API state. When the DB lags, keep the ephemeral identity and
mark the DB identity source degraded; do not guess a canonical ID.

## Kill Events And Cursor

Read verified upstream equivalents of `KILL` and `TEAM KILL` from `log_lines`.
Bound every query by the current match identity/time window and never use an
unbounded historical predicate.

Order events deterministically by:

1. `event_time`;
2. unique event ID.

Timestamp alone is insufficient. Each HLL `KillEvent` may expose only approved
fields:

- opaque cursor;
- timestamp;
- killer and victim identity/display data;
- team information where available;
- weapon;
- teamkill boolean; and
- canonical or ephemeral match identity.

The cursor must be opaque, deterministic and scoped to the current match. A
cursor from a different or prior match must not continue the new feed. Invalid
cursors must fail safely or produce an explicit reset indication, and duplicate
timestamps must remain distinguishable by event ID. Do not persist cursors.

## Player Current-Match Combat Stats

Derive canonical current-match kills, deaths and teamkills from bounded CRCON
log events. Derive weapon counts when useful. The live API may supplement team,
unit, role, level, combat, offense, defense, support and live status.

If API and log totals disagree:

- log-derived K/D/TK remain canonical;
- disagreement is surfaced in source/degraded metadata; and
- values from both sources are never silently summed.

Prevent duplicate event counting.

## Snapshot Coherence And Version

Implement one repository-conventional service call equivalent to:

```python
CurrentMatchSnapshotService.get_snapshot(server, ...)
```

Build the full snapshot against one logical refresh cycle. In CRCON mode, the
snapshot endpoint and all compatibility endpoints must consume the same
cached/coalesced snapshot rather than rebuilding independently at different
source instants.

Generate a deterministic process-local/content-derived opaque version. It must
remain stable for identical material data and change for relevant changes such
as match identity, score, timing bucket when included, player combat state,
newest kill cursor or relevant player/source state. Do not use Python object
hashes or require a persistent sequence.

## Memory Cache And Request Coalescing

Use TASK-290 `TtlCache` with a live TTL of approximately one to two seconds,
small bounded limits and per-server keys. Do not add Redis, disk persistence,
background cleanup or a new worker. Match changes must invalidate previous
match live state.

Implement the request coalescing deliberately deferred by TASK-290. The compact
process-local mechanism must provide:

- thread safety;
- one upstream refresh per server/cache miss;
- reuse of the same result by waiting callers;
- cleanup after exceptions so a key is never permanently poisoned;
- independence between different server keys; and
- no background thread or worker.

## Routes And Compatibility

Add:

```text
GET /api/current-match/snapshot?server=<slug>
```

A full snapshot response is sufficient. Add `since_version` only if its
semantics remain simple, deterministic and precisely tested. Do not implement
WebSockets, SSE or a complex delta protocol.

When source is `legacy`, preserve the existing behavior and JSON contracts of:

- `/api/current-match`;
- `/api/current-match/kills`; and
- `/api/current-match/players`.

When source is `crcon`, those paths become compatibility projections of the
same `CurrentMatchSnapshot`. Preserve all existing fields required by the
frontend and current tests. Additive source/freshness metadata is allowed only
when compatibility remains intact. Cover both modes with golden/compatibility
tests. Do not modify the frontend.

Preserve existing server validation and error semantics unless a documented
CRCON-first requirement needs an additive change. Unsupported servers and
invalid limit/cursor/version values must fail with stable 4xx behavior.

## Error Semantics

CRCON mode must distinguish `fresh`, `stale`, `degraded` and `unavailable`.
Source failure must not become fake zero values.

- API healthy + DB healthy: return a fresh coherent snapshot.
- API healthy + DB unavailable: the summary may remain available, while kills
  and log-derived stats are unavailable and the snapshot is degraded.
- DB healthy + API unavailable: bounded DB fields may remain while API-only
  live fields are degraded.
- Both unavailable: return a stable current-match unavailable response or HTTP
  503 following current backend conventions.

One server failure must not affect another server's cache or state. Never call
the legacy implementation automatically after a CRCON failure.

## Steps

1. Move TASK-291 from `pending` to `in-progress`; record starting HLL and pinned
   CRCON commits in Outcome.
2. Read the mandatory documents, relevant code and focused tests before
   selecting the smallest implementation split.
3. Inspect the exact pinned upstream revision and document the verified live
   endpoint, stored event values and schema/query assumptions.
4. Add the minimal source/binding configuration with legacy as the default.
5. Add only the domain models and CRCON API/database reads needed for a coherent
   current-match snapshot.
6. Implement canonical/ephemeral identity, bounded ordered kill events,
   match-scoped cursor, log-derived combat totals and deterministic versioning.
7. Implement the per-server `TtlCache` integration and single-flight behavior.
8. Add the canonical snapshot endpoint and make the existing paths project the
   same service only in explicit CRCON mode.
9. Extend sanitized fixtures and add local fake-driven unit, route, safety,
   compatibility and concurrency tests.
10. Run all validation, inspect the complete diff and move TASK-291 to `review`.
    Do not mark it `done`, merge it or change the default rollout mode.

## Files to Read First

Read completely:

- `AGENTS.md`;
- `ai/repo-context.md`;
- `ai/architecture-index.md`;
- `docs/CRCON_FIRST_STATELESS_ARCHITECTURE.md`;
- `docs/CRCON_FIRST_MIGRATION_AND_DECOMMISSION_PLAN.md`;
- `ai/tasks/done/TASK-289-design-crcon-first-stateless-architecture.md`; and
- `ai/tasks/done/TASK-290-build-crcon-adapter-foundation-and-local-fixtures.md`.

Then inspect:

- `backend/app/crcon/**`;
- `backend/app/config.py`;
- `backend/app/routes.py`;
- `backend/app/payloads.py`;
- `backend/app/rcon_current_match_worker.py`;
- `backend/app/rcon_admin_log_storage.py`;
- `backend/app/rcon_admin_log_materialization.py`;
- `backend/app/providers/public_scoreboard_provider.py`;
- `backend/tests/test_current_match_payload.py`;
- all current-match-focused backend tests; and
- `frontend/assets/js/partida-actual.js`, read-only for contract understanding.

Inspect the pinned CRCON upstream source locally/publicly and read-only at
`MarechJ/hll_rcon_tool@4cf1e7e2fa691d849eaf85abb7065010e13f28e4`.

## Expected Files to Modify

Likely areas:

- `backend/app/crcon/**`;
- `backend/app/config.py`;
- `backend/app/routes.py`;
- `backend/app/payloads.py`, only when required as a compatibility
  serialization/facade;
- one small current-match service/domain module when architecture warrants it;
- focused backend tests;
- sanitized CRCON fixtures; and
- the TASK-291 lifecycle file.

Do not modify:

- `frontend/**`;
- `deploy/**`;
- Compose files;
- Dockerfiles;
- requirements files unless genuinely unavoidable; or
- legacy worker/storage implementation except imports or interfaces strictly
  required for the explicit legacy wrapper.

Prefer keeping legacy current-match internals byte-identical and selecting the
source above them.

## Fixtures

Extend sanitized local fixtures only as required. Candidate evidence includes:

- live game stats;
- live scoreboard/player state;
- current/open map row;
- bounded current-match log events;
- match transition; and
- DB-lag/ephemeral-match state.

All player names, identities, servers and URLs must be synthetic. Pin fixture
metadata to `4cf1e7e2fa691d849eaf85abb7065010e13f28e4`. Do not copy production data,
credentials or raw community logs.

## Mandatory Test Scenarios

### Source selection

- default remains legacy;
- explicit CRCON selects the new service;
- missing CRCON configuration does not break legacy;
- invalid source configuration is rejected; and
- CRCON failure does not automatically call legacy.

### Match identity

- canonical CRCON map ID;
- API ahead of DB produces an ephemeral ID;
- ephemeral-to-canonical transition;
- match change invalidates cache and resets incompatible cursors; and
- a conflicting latest DB row is not guessed as the canonical match.

### Killfeed

- `KILL` and `TEAM KILL`;
- weapon mapping;
- deterministic `(event_time, id)` ordering;
- equal timestamps with distinct IDs;
- cursor continuation;
- old-match cursor reset/rejection; and
- no event leakage outside match bounds.

### Player stats

- kills, deaths and teamkills;
- API team/unit/role enrichment;
- API/log disagreement keeps logs canonical for K/D/TK; and
- duplicate events are not counted twice.

### Snapshot

- one coherent domain snapshot;
- stable version for identical material data;
- changed version after material state changes;
- degraded/freshness metadata; and
- unavailable data is not represented by fake zeros.

### Coalescing and cache

- concurrent callers trigger one refresh;
- TTL hits trigger no upstream refresh;
- expiry triggers a refresh;
- different server keys are independent;
- refresh exceptions release coalescing state; and
- match transition invalidates prior live cache.

### Compatibility

Add golden tests for the required legacy shapes of:

- `/api/current-match`;
- `/api/current-match/kills`; and
- `/api/current-match/players`.

In CRCON mode, confirm that all three project one shared snapshot while
preserving the frontend-required contract.

### Safety

- CRCON current-match invokes no HLL DB write/storage helper;
- no AdminLog worker or materializer is called;
- no mutation SQL exists;
- no raw upstream row/log payload is exposed; and
- tests use no real network or database.

## Constraints

- Implement and test locally only.
- Do not access SSH, Portainer, production CRCON, production PostgreSQL,
  production RCON, production secrets or deployment consoles.
- Do not create a new ingestion pipeline or persistent cache.
- Do not use HLL gameplay persistence in CRCON mode.
- Do not automatically fall back from CRCON to legacy.
- Do not add direct RCON as a mandatory dependency.
- Do not expose arbitrary SQL or mutation operations.
- Do not add Redis, queues, cleanup workers, WebSockets or SSE.
- Do not place production binding values in the repository.
- Do not modify deployment/Compose/env files in this task.
- Do not modify the frontend.
- Do not delete `rcon_current_match_worker.py`,
  `rcon_admin_log_storage.py`, `rcon_admin_log_materialization.py`, legacy
  historical storage, HLL PostgreSQL, the scoreboard provider, direct RCON
  client, workers or snapshots.
- Keep TASK-272 through TASK-281 and TASK-284 unmodified and unexecuted.
- Keep TASK-287 through TASK-290 resolved and untouched.
- Do not modify or stage local TASK-204, TASK-242, TASK-264, TASK-266, TASK-267
  or TASK-268 files.
- Do not add requirements unless genuinely unavoidable and explicitly
  justified in Outcome.
- Do not implement deployment or change the default to CRCON.
- Do not create a follow-up task merely to widen TASK-291.

If deployment-specific information later becomes necessary, document exactly
what a user must query through a user-operated read-only console prompt. Do not
block local implementation merely because production configuration is unknown.

## Validation

Run at minimum:

```powershell
python -m compileall backend/app
Set-Location backend
python -m unittest tests.test_crcon_adapter_foundation
python -m unittest tests.test_current_match_payload
python -m unittest <focused TASK-291 modules>
```

Run every existing route/current-match test affected by the implementation.
Run full backend unittest discovery when practical and classify known TASK-284
baseline failures separately without fixing or executing TASK-284.

From the repository root, run:

```powershell
git diff --check
git diff --name-only
git status --short
```

Search every new or modified CRCON SQL surface for `INSERT`, `UPDATE`, `DELETE`,
`MERGE`, `CREATE`, `ALTER`, `DROP`, `TRUNCATE`, `VACUUM` and `REINDEX`. Inspect
every hit; no executable mutation SQL is allowed.

Validation must demonstrate:

- default legacy behavior and compatibility are unchanged;
- explicit CRCON mode uses one coherent snapshot;
- read-only queries are parameterized, bounded and deterministically ordered;
- all API/DB/cache/coalescing/error paths are fake/fixture driven;
- no HLL persistence or legacy worker/materializer runs in CRCON mode;
- no frontend, deployment, requirements or unrelated task file changed; and
- the final diff matches the expected scope.

## Acceptance Criteria

TASK-291 is complete only when:

1. `/api/current-match/snapshot` exists.
2. CRCON current-match mode is fully locally testable.
3. The default source remains legacy.
4. Existing routes behave identically in legacy mode.
5. CRCON compatibility routes project one coherent cached snapshot.
6. Match identity uses the CRCON map ID when available.
7. DB lag produces an explicit ephemeral identity.
8. Every event query is bounded.
9. `KILL` and `TEAM KILL` are supported.
10. Log-derived K/D/TK are canonical.
11. API disagreement is surfaced and never summed silently.
12. An opaque match-scoped cursor works and rejects/resets old matches safely.
13. Cache is bounded and process-local.
14. Concurrent calls coalesce per server.
15. CRCON mode uses no HLL gameplay persistence.
16. No legacy module is removed.
17. No frontend or deployment code changes.
18. All tests are local, fake or fixture driven.
19. No production access occurs.

## Outcome

Record during execution:

- starting HLL commit and exact pinned upstream revision;
- verified CRCON live methods, event values and schema/query assumptions;
- source switch and per-server binding design;
- domain model, canonical/ephemeral identity and transition behavior;
- bounded database methods and read-only enforcement evidence;
- event cursor, ordering, bounds and log-derived combat rules;
- snapshot version, cache limits/TTL/invalidation and single-flight behavior;
- route behavior in legacy and explicit CRCON modes;
- degraded/unavailable semantics and API/log disagreement behavior;
- fixture inventory and sanitation evidence;
- focused, compatibility, foundation and full-suite validation results;
- confirmation that no HLL gameplay persistence or legacy fallback was called
  in CRCON mode;
- confirmation that legacy modules and default behavior remain intact;
- confirmation that frontend/deployment files and protected tasks are
  unchanged; and
- confirmation that no SSH, Portainer, production or credential access
  occurred.

## Lifecycle

During execution:

```text
pending -> in-progress -> review
```

Use a dedicated branch such as
`feature/task-291-crcon-current-match-snapshot`. Open a draft PR. Do not mark
TASK-291 done automatically, merge the PR, enable auto-merge or delete the
source branch.

## Change Budget

- Prefer the smallest coherent vertical slice that satisfies the acceptance
  criteria.
- The normal five-file/200-line preference may be exceeded only where the
  current-match domain, CRCON-boundary extensions, compatibility routes,
  fixtures and focused tests require separate cohesive files.
- Keep legacy internals byte-identical where practical.
- Document every additional file or dependency exception in Outcome instead
  of widening scope silently.
- Split genuinely separate rollout/deployment/frontend work into later tasks;
  do not perform it in TASK-291.
