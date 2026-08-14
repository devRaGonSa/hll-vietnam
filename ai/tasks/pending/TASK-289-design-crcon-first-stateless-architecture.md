---
id: TASK-289
title: Design CRCON-first stateless HLL Vietnam architecture
status: pending
type: research
team: Arquitecto Python
supporting_teams: ["Arquitecto de Base de Datos", "Backend Senior", "Frontend Senior", "Analista", "PM"]
roadmap_item: crcon-first-architecture
priority: critical
---

# TASK-289 - Design CRCON-first stateless HLL Vietnam architecture

## Goal

Produce the complete migration architecture that removes HLL Vietnam-owned
gameplay persistence and converts the application into a lightweight stateless
frontend/BFF consuming CRCON directly wherever possible.

Determine exactly:

1. which current functionality is retained;
2. which code is adapted or retired;
3. which persistence, workers and services are removed;
4. which CRCON API operation supplies each capability;
5. which CRCON PostgreSQL data supplies capabilities not safely available via API;
6. which minimal capabilities, if any, still require direct HLL RCON;
7. how existing frontend contracts remain compatible during migration; and
8. how deployment is reduced to the minimum practical HLL Vietnam service count.

This task is architecture and planning only. Do not implement the migration.

## Context

HLL Vietnam is making a major architectural change. The application will stop
operating its own persistent gameplay/statistics database. The PostgreSQL,
AdminLog ingestion, event storage, match/player-stat materialization, snapshots,
rankings, checkpoints, backfills and worker architecture is deprecated.

The target model is:

```text
CRCON = data platform and source
HLL Vietnam = frontend + lightweight stateless Python BFF
```

The BFF may consume, in priority order by capability:

1. CRCON HTTP/API;
2. CRCON PostgreSQL using strict read-only access; and
3. direct HLL RCON only where CRCON cannot reliably provide the live capability.

HLL Vietnam must not persist a second full copy of CRCON gameplay data. No
HLL-owned PostgreSQL or Redis is required in the target architecture. If caching
is necessary, use a bounded process-local TTL cache.

The preferred deployment is the existing CRCON stack plus one HLL Vietnam
service. A temporary two-service HLL target (Python BFF plus static frontend) is
acceptable only when explicitly justified by repository/runtime evidence.

TASK-288's SSH/production PostgreSQL requirement belonged to the deprecated
architecture. This migration must not request SSH or production access. All
analysis and design before a separately authorized deployment phase must be
possible locally.

## Mandatory Architecture Principles

### CRCON is the source platform

- Do not replicate CRCON gameplay data into an HLL Vietnam database.
- Read historical matches, player statistics, log events and game/server state
  directly from CRCON wherever CRCON owns the data.
- Do not retain old storage merely to avoid adapting an endpoint.

### Preserve a lightweight BFF

- Never connect the browser directly to PostgreSQL or expose CRCON credentials.
- Keep a Python BFF that authenticates/configures upstream access, normalizes
  CRCON data into HLL contracts, applies timeouts and errors, optionally caches
  briefly in memory, and isolates the frontend from CRCON schema changes.

### Select API, DB or RCON per capability

Classify every feature as:

- **A - CRCON HTTP/API**: preferred where its contract is suitable and reliable.
- **B - CRCON PostgreSQL read-only**: use only where API coverage, aggregation,
  event granularity or indexed-query performance is insufficient.
- **C - direct RCON fallback**: use only where CRCON cannot reliably supply the
  required live field.

Do not choose PostgreSQL merely because a table exists.

### CRCON database access is strictly read-only

Design a dedicated least-privilege identity conceptually similar to
`hll_vietnam_reader`, with only required `SELECT` privileges. HLL Vietnam must
never migrate CRCON, create/alter/drop objects, mutate rows, materialize data
into CRCON or own CRCON migrations. Do not create credentials in this task.

### CRCON schema is not a product contract

All direct CRCON API/SQL access must live behind one adapter/repository boundary.
No other HLL module or frontend code may reference CRCON internal table names.
Evaluate a repository-conventional structure resembling:

```text
backend/app/crcon/
    __init__.py
    client.py
    database.py
    models.py
    mapper.py
    capabilities.py
    cache.py
    queries/
```

Do not assume this exact structure before inspecting current conventions.

### No HLL gameplay persistence

The target architecture must not require HLL PostgreSQL, Redis, AdminLog event
storage, materialized matches, player-match stats, snapshot tables, ranking
snapshots, ingestion checkpoints, capture runs or HLL backfill storage.

Identify separately any genuinely HLL-owned non-game configuration still needed
by the product; do not accidentally remove unrelated product state.

### Bounded in-memory caching only

Recommend TTLs and maximum entries based on volatility and query cost for live
server/match state, killfeed, players, recent history, match details, rankings
and player profiles. The cache must be optional and process-local. Do not add
Redis or another persistent cache.

### Preserve public contracts where sensible

Prefer the migration seam:

```text
existing frontend -> existing /api/... contracts -> new CRCON adapter
```

Document contract changes only where an existing endpoint is fundamentally
wrong. Do not rewrite the frontend solely because the upstream source changes.

## Public CRCON Upstream Analysis

Use the current official open-source repository
`https://github.com/MarechJ/hll_rcon_tool` as a read-only reference. If needed,
clone it to a temporary local directory outside HLL Vietnam; never modify it.

Record repository URL, inspected branch, exact commit SHA and inspection date.
Inspect actual current source for:

- API registration/routes and public information;
- live game state, map/layer/mode, score and player state;
- live logs and live game statistics;
- historical maps/matches and server history/counts;
- player statistics, sessions, names and identities;
- caches;
- database models/schema; and
- relevant migrations, indexes and constraints.

At minimum search current upstream for concepts corresponding to log lines, map
history, player stats, player sessions, identities/name history, server counts,
current game state, public info and live game stats. Do not assume historical
names or schemas still exist.

Known caveat: upstream live game-stat/kill accuracy requires verification. For
each current-match field independently compare CRCON live API, CRCON persisted
logs/events and direct RCON. Do not preselect a source without current evidence.

## Steps

### 1. Begin lifecycle and establish evidence scope

1. Move only TASK-289 from `pending` to `in-progress` and set `status: in-progress`.
2. Record local repository commit and current CRCON upstream reference.
3. Keep all work local except read-only public/open-source upstream inspection.
4. Do not access SSH, production, Portainer, secrets or any production database.

### 2. Inventory current architecture

Produce an exact service/process diagram. For every HLL runtime process record
purpose, image/process, dependencies, persistent storage, qualitative resource
role and target classification: `KEEP`, `MERGE`, `REMOVE` or `REPLACE`.

Cover at least `postgres`, `backend`, `frontend`, `historical-runner`,
`rcon-live-adminlog-worker`, `rcon-historical-worker`, and every other scheduler
or worker discovered in active Compose/Portainer definitions.

### 3. Inventory current persistence

Find every HLL-owned table and storage family and classify it as:

- `REMOVE`;
- `TEMPORARILY KEEP DURING MIGRATION`; or
- `NON-GAME CONFIG THAT MAY STILL BE NEEDED`.

Document owning modules, writers, readers, schema initialization/migrations,
volumes and removal prerequisites. Separate gameplay duplication from genuinely
HLL-owned product configuration.

### 4. Inventory the complete public API surface

Enumerate every public backend route. For each record:

- method, path and query parameters;
- frontend consumers;
- current payload builder and data sources;
- current tables/workers involved;
- target CRCON source and A/B/C classification;
- cache recommendation;
- contract compatibility;
- migration difficulty; and
- retain/rewrite/remove/deprecate decision.

Cover landing/server data, current match, killfeed, live player stats, historical
lists/details, rankings and weekly/monthly/annual metrics, player search/profile,
remaining MVP, event/weapon/duel surfaces, health and status endpoints.

### 5. Inventory frontend consumers

Search every frontend JS/HTML API call and produce:

```text
page/component -> endpoint -> expected contract -> polling interval -> impact
```

Identify duplicated requests, fan-out and unnecessary high-frequency polling.
Recommend request consolidation that minimizes CRCON/API/database load.

### 6. Build the CRCON capability matrix

For every product capability provide:

| HLL capability | CRCON API candidate | CRCON DB candidate | Direct RCON candidate | Chosen source | Reason |
| --- | --- | --- | --- | --- | --- |

Cover at minimum:

- **Current match:** map/layer, mode, start, score, remaining time, slots and
  online/team counts, player names/team, killfeed, teamkills, per-player kills
  and deaths, weapons, transitions and stable match identity.
- **Historical:** recent/paginated matches, match ID/start/end/map/layer/result,
  detail, player stats, kills/deaths/weapons/teamkills and player duration.
- **Rankings:** weekly/monthly/annual kills, deaths, teamkills, K/D, kills per
  match, matches considered and every public metric still required.
- **Player:** search, display/current and historical names where relevant,
  profile/period stats and recent matches.
- **Server:** availability, players, slots, queue, map and displayed history.

### 7. Define the verified CRCON schema contract

Document only tables/models/columns verified in current upstream source. For
every DB-backed capability record model/table, columns, join path, indexes and
constraints, estimated bounded query shape, temporal bounds, server
discriminator, pagination, ordering, nullability and compatibility risks.

Do not invent SQL from old schemas and do not execute SQL against production.
Read-only SQL templates may target CRCON fixtures/test schema only.

### 8. Design the anti-corruption adapter

Define HLL-owned domain models independent of CRCON, including as applicable:
`CurrentMatch`, `CurrentPlayer`, `KillEvent`, `HistoricalMatch`,
`HistoricalPlayerStat`, `PlayerSummary`, `RankingRow` and `ServerSummary`.

Map existing public payloads to these models. CRCON API/SQL objects must be
converted at the adapter boundary; never expose internal CRCON rows directly.

### 9. Redesign current match

Assess a coherent endpoint such as:

```text
GET /api/current-match/snapshot?server=...
```

It should provide canonical source match identity, map/layer/mode, start, score,
remaining time, players, killfeed cursor/version, source timestamps, freshness
and degraded/source flags. Determine whether `/api/current-match`,
`/api/current-match/kills` and `/api/current-match/players` remain temporarily as
compatibility views.

The design must use no HLL AdminLog worker, persisted event watermark or match
table. Prefer a verified stable CRCON game/map identity; otherwise define a
deterministic ephemeral identity from verified fields.

### 10. Redesign historical, rankings and profiles

Read CRCON's historical storage instead of reconstructing matches from HLL
AdminLog. Define recent/paginated history, match detail, player-match stats,
ranking queries and player-period aggregates.

For expensive rankings evaluate, in order:

1. CRCON API or existing CRCON cache;
2. indexed bounded CRCON SQL plus BFF TTL cache; and
3. bounded request-time aggregation.

Classify each legacy metric as `KEEP WITH CRCON SOURCE`, `RECOMPUTE ON REQUEST`,
`DEFER` or `REMOVE FROM PRODUCT`. Do not retain persistence solely to preserve a
metric whose value does not justify the infrastructure.

### 11. Design caching and load protection

For server list, live snapshot, killfeed, player list, recent history, match
detail, rankings and player profiles specify TTL, maximum entries, cache key and
match-change invalidation. Also define hard timeouts, limited retries,
stale-if-error, circuit-breaker/backoff and per-server isolation.

### 12. Design the read-only CRCON PostgreSQL client

Specify a small connection pool, hard query and statement timeouts, read-only
transactions, `application_name`, no write-capable autocommit behavior, startup
schema/capability probe, supported schema contract/version, graceful
`CRCON schema incompatible` failure and credential redaction.

### 13. Select the target deployment

Compare and select:

- **Target A (preferred):** one HLL container serves static frontend and `/api`,
  owns only process memory cache, and connects to CRCON API/DB/RCON as required.
- **Target B:** Python BFF plus separate static frontend, only when technically
  justified.

Both exclude HLL PostgreSQL, Redis, historical/live workers, materializers and
ranking snapshot workers. Provide the final service graph and compare current
versus target service count, persistent volumes, workers, scheduled jobs and
external dependencies. Use structural/qualitative resource savings unless real
measurements exist.

### 14. Produce the module decommission matrix

Classify current modules/tests/deployment areas as `KEEP`, `REWRITE`,
`DELETE AFTER MIGRATION`, `OBSOLETE` or `REVIEW`. Cover historical and
PostgreSQL storage, AdminLog parser/storage/materializer, workers, snapshot and
ranking generators, current-match worker, public-scoreboard fallback, RCON
client, frontend polling, deployment files and tests. Do not delete anything.

### 15. Reconcile existing tasks without executing them

Read TASK-272 through TASK-281 and classify each `KEEP`, `REWRITE`, `SUPERSEDED`
or `OBSOLETE`. Verify rather than assume the likely direction:

- TASK-272: rewrite around a CRCON-first contract.
- TASK-273: likely obsolete if it requires HLL lifecycle persistence.
- TASK-274: reassess; the parser may remain only for direct-RCON fallback.
- TASK-275: likely obsolete if it creates an HLL ingestion watermark.
- TASK-276: rewrite as a stateless/in-memory coherent snapshot.
- TASK-277: rewrite because CRCON becomes primary, not reconciliation input.
- TASK-278: retain the endpoint concept but rewrite its source.
- TASK-279: retain frontend behavior after the new snapshot contract.
- TASK-280: likely obsolete if worker-based.
- TASK-281: rewrite as CRCON-first parity/rollout validation.

Do not change their lifecycle or content.

Inspect local-only TASK-264, TASK-266, TASK-267 and TASK-268 when present and
recommend their post-migration disposition without modifying or staging them.
Keep TASK-284 independent; assess whether migration removes its failing legacy
surfaces, but do not execute or edit it.

### 16. Make authorized lifecycle decisions

After the architecture evidence and documents are complete:

- Move TASK-287 from `review` to `done`, set `status: done`, and add an Outcome
  note that its forensic findings motivated removal of duplicated HLL historical
  persistence.
- Move TASK-288 from `blocked` to `obsolete`, set `status: obsolete`, preserving
  its history and adding exactly this rationale:

  > Superseded by the CRCON-first stateless architecture decision. HLL
  > Vietnam-owned production PostgreSQL forensic reproduction is no longer
  > required because gameplay persistence/materialization will be removed
  > rather than repaired.

These transitions are authorized only during TASK-289 execution. Do not SSH or
access production to close either task.

### 17. Recommend, but do not create, the implementation backlog

Provide sequenced recommendations for:

1. CRCON adapter foundation and local fixtures;
2. current-match CRCON-first migration;
3. historical list/detail migration;
4. rankings/player profiles migration;
5. frontend contract cleanup and request consolidation;
6. removal of old HLL persistence and workers;
7. simplification to one or two HLL services; and
8. deletion of dead modules/tests/docs and obsolete baseline debt.

For each recommended task specify title, type, team, dependencies, files/areas,
acceptance criteria and approximate risk. Do not assign task IDs or create task
files; ChatGPT will review the architecture first.

### 18. Validate and hand off

Validate the documents against current local code and the pinned CRCON upstream
commit. Move TASK-289 from `in-progress` to `review` and set `status: review`
only when every required inventory, matrix and decision is complete. Do not mark
TASK-289 done automatically.

## Files to Read First

### Repository and role context

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `ai/task-template.md`
- `ai/orchestrator/python-architect.md`
- `ai/orchestrator/database-architect.md`
- `ai/orchestrator/backend-senior.md`
- `ai/orchestrator/frontend-senior.md`
- `ai/orchestrator/analyst.md`
- `ai/orchestrator/pm.md`

### Backend and providers

- `backend/app/routes.py`
- `backend/app/payloads.py`
- `backend/app/config.py`
- `backend/app/rcon_client.py`
- `backend/app/rcon_admin_log_parser.py`
- `backend/app/rcon_admin_log_storage.py`
- `backend/app/rcon_admin_log_materialization.py`
- `backend/app/rcon_current_match_worker.py`
- `backend/app/rcon_historical_worker.py`
- `backend/app/rcon_historical_storage.py`
- `backend/app/postgres_rcon_storage.py`
- `backend/app/historical_storage.py`
- `backend/app/postgres_display_storage.py`
- the actual current public-scoreboard provider and scoreboard adapters found
  through repository search

### Frontend and deployment

- every frontend JS/HTML file that calls `/api/`
- `backend/Dockerfile`
- `frontend/Dockerfile`
- every active Docker Compose/Portainer deployment file

### Audit and task context

- `docs/HISTORICAL_RCON_MATCH_BOUNDARY_AND_STAT_INFLATION_AUDIT.md`
- `ai/tasks/review/TASK-287-audit-historical-match-boundaries-and-stat-inflation.md`
- the single lifecycle path containing TASK-288
- TASK-272 through TASK-281
- local TASK-264, TASK-266, TASK-267 and TASK-268 when present
- TASK-284

Use repository search to resolve renamed/moved equivalents rather than assuming
paths. Keep unrelated product areas out of scope.

## Required Documentation Artifacts

Create `docs/CRCON_FIRST_STATELESS_ARCHITECTURE.md` with exactly:

1. Executive decision.
2. Architecture goals/non-goals.
3. Current architecture.
4. Target architecture.
5. Current service inventory.
6. Persistence inventory.
7. Full endpoint inventory.
8. Frontend consumer inventory.
9. CRCON capability matrix.
10. Verified CRCON API contracts.
11. Verified CRCON DB schema contracts.
12. Internal BFF/domain model.
13. Current-match architecture.
14. Historical architecture.
15. Ranking/profile architecture.
16. In-memory caching.
17. Connection/security model.
18. Failure/degraded behavior.
19. Target deployment.
20. Performance/resource expectations.
21. Compatibility/versioning strategy.
22. Testing strategy.
23. Security constraints.
24. Open questions.

Create `docs/CRCON_FIRST_MIGRATION_AND_DECOMMISSION_PLAN.md` with exactly:

1. Migration principles.
2. Endpoint-by-endpoint migration matrix.
3. Module KEEP/REWRITE/DELETE matrix.
4. Service decommission matrix.
5. Database/table decommission strategy.
6. Frontend compatibility strategy.
7. TASK-272 through TASK-281 classification.
8. Local TASK-264/266/267/268 classification.
9. TASK-284 assessment.
10. Phased implementation sequence.
11. Rollback strategy.
12. Definition of done for each phase.
13. Final cleanup phase.
14. Deployment handoff requirements.

## Expected Files to Modify

- The single TASK-289 lifecycle file, moving only through:
  - `ai/tasks/pending/TASK-289-design-crcon-first-stateless-architecture.md`
  - `ai/tasks/in-progress/TASK-289-design-crcon-first-stateless-architecture.md`
  - `ai/tasks/review/TASK-289-design-crcon-first-stateless-architecture.md`
- `docs/CRCON_FIRST_STATELESS_ARCHITECTURE.md`
- `docs/CRCON_FIRST_MIGRATION_AND_DECOMMISSION_PLAN.md`
- `ai/tasks/done/TASK-287-audit-historical-match-boundaries-and-stat-inflation.md`
- `ai/tasks/obsolete/TASK-288-reproduce-historical-forensics-on-production-postgres.md`

Do not modify `backend/app/**`, frontend, deployment/Compose, database schemas,
database files, credentials or runtime configuration in TASK-289.

## Constraints

- Planning/research only; do not implement product behavior.
- Local analysis and read-only public/open-source CRCON inspection only.
- Do not SSH, use Portainer, access production, inspect secrets, deploy or
  restart services.
- Do not connect to or modify any production PostgreSQL/CRCON environment.
- Do not execute TASK-272 through TASK-281 or TASK-284.
- Do not modify or stage TASK-264, TASK-266, TASK-267 or TASK-268.
- Do not introduce HLL-owned PostgreSQL, Redis or persistent gameplay caches.
- Do not fabricate CRCON routes, tables, columns, indexes or capabilities.
- Record unknowns explicitly when current upstream source does not prove them.
- Do not create follow-up tasks or assign IDs automatically.
- Preserve the old database/workers until endpoint-by-endpoint strangler
  migration has achieved validated parity.
- Do not delete code, data or services in this task.
- Keep all credentials and authenticated URLs out of artifacts.
- Do not use `git add .`, `git add -A`, `git clean`, `git stash`,
  `git reset --hard`, rebase, force push or automatic merge.

## Migration Safety

Use a strangler sequence for every endpoint/capability:

1. introduce the CRCON adapter;
2. migrate one endpoint;
3. compare old/new locally with fixtures or sanitized samples;
4. switch that endpoint;
5. verify its frontend consumer; and
6. remove the old implementation only after parity is accepted.

The decommission plan must preserve rollback until every dependent public
surface has migrated. Never delete the fallback architecture first.

## Validation

Before moving TASK-289 to review:

1. Record the HLL Vietnam and CRCON upstream commit SHAs and inspection date.
2. Verify every current public route and frontend `/api/` call appears in the
   endpoint/consumer matrices.
3. Verify every active Compose service, persistent volume, worker and scheduler
   appears in the current/target service matrix.
4. Verify every HLL-owned storage/table family has a disposition and removal
   prerequisite.
5. Verify each product capability has an evidence-backed API/DB/RCON choice.
6. Verify every direct-DB choice cites actual upstream model/table/columns and
   relevant indexes/constraints or is explicitly unresolved.
7. Verify the read-only connection/security, cache/load-protection, degraded
   behavior, compatibility, testing and rollback designs are complete.
8. Verify both documentation artifacts contain every required numbered section.
9. Verify TASK-272 through TASK-281, local TASK-264/266/267/268 and TASK-284 were
   analyzed only and remain unmodified.
10. Verify TASK-287 is uniquely in `done`, TASK-288 uniquely in `obsolete`, and
    their history/rationale is preserved.
11. Run `git diff --check`, `git diff --name-only` and `git status --short`.
12. Confirm the diff contains no backend, frontend, deploy, Compose, database,
    secret or runtime configuration changes.

Integration tests are not required because TASK-289 changes architecture
documentation and task lifecycle only. Document this explicitly in Outcome.

## Outcome

Record:

- pinned HLL Vietnam and CRCON upstream references;
- the selected one- or two-service target and justification;
- current versus target service/volume/worker structure;
- endpoint and frontend-consumer coverage;
- capability source decisions and unresolved upstream gaps;
- verified CRCON API/schema contracts;
- target BFF/domain, cache, security and failure model;
- persistence/service/module decommission decisions;
- task reconciliation and authorized TASK-287/288 transitions;
- recommended implementation sequence without task creation;
- validation results; and
- confirmation that no SSH, production, product-code, deployment or database
  mutation occurred.

TASK-289 must finish in `review`, not `done`, for architectural approval.

## Change Budget

- Prefer only the TASK-289 lifecycle file, two architecture documents and the
  two authorized TASK-287/TASK-288 lifecycle transitions.
- Documentation may exceed the normal 200-line preference because exhaustive
  endpoint, capability, persistence and decommission matrices are mandatory.
- Do not let research expand into implementation, deployment or data repair.
