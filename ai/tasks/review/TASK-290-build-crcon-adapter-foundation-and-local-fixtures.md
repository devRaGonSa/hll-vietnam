---
id: TASK-290
title: Build CRCON adapter foundation and local fixtures
status: review
type: backend
team: Arquitecto Python
supporting_teams: ["Arquitecto de Base de Datos", "Backend Senior"]
roadmap_item: crcon-first-architecture
priority: critical
---

# TASK-290 - Build CRCON adapter foundation and local fixtures

## Goal

Implement the additive technical foundation required for later CRCON-first HLL
Vietnam migrations without changing any current public endpoint or removing any
legacy implementation.

TASK-290 must introduce:

1. an isolated CRCON integration boundary;
2. a safe CRCON HTTP client;
3. a strictly read-only CRCON PostgreSQL adapter;
4. explicit CRCON schema/capability validation;
5. common adapter errors and source metadata;
6. a bounded, thread-safe, process-local TTL cache;
7. sanitized local fixtures pinned to the accepted CRCON revision; and
8. focused tests proving the safety and compatibility contracts.

The post-task architecture must remain:

```text
legacy HLL implementation
        remains unchanged

new backend/app/crcon/*
        exists and is fully tested
        but is not yet serving product endpoints
```

TASK-290 must not migrate a public endpoint, switch existing product traffic,
or remove a legacy database, worker, materializer, provider or fallback.

## Context

TASK-289 accepted a CRCON-first stateless target in which CRCON owns gameplay
data and HLL Vietnam becomes a lightweight frontend/BFF. The architecture was
merged at HLL commit `739b62749d126e99043c80a64bd4dff0c5fd4091`.

This is phase 1 of the accepted strangler sequence: establish the internal
adapter boundary and local evidence before migrating a single consumer. Later
tasks will use this foundation for current match, history, rankings and player
profiles one capability at a time. Existing HLL routes and legacy persistence
must behave exactly as before throughout TASK-290.

The accepted upstream contract reference is:

- repository: `https://github.com/MarechJ/hll_rcon_tool`;
- branch: `master`;
- source commit: `4cf1e7e2fa691d849eaf85abb7065010e13f28e4`.

Inspect that exact revision locally and read-only when deriving fixtures and
expected capabilities. Do not silently use a newer revision. The revision is
fixture/contract metadata, not a claim that a future deployed CRCON instance
will expose that Git SHA; runtime compatibility is determined by capability
probes.

Everything in this task is implemented and tested locally. It requires no SSH,
Portainer, production API, production PostgreSQL, production RCON, credentials
or deployment access.

## Steps

### 1. Establish lifecycle and scope

1. Move only TASK-290 from `pending` to `in-progress` and set
   `status: in-progress`.
2. Record the HLL starting commit and pinned CRCON source revision in Outcome.
3. Inspect the files listed under `Files to Read First` and representative
   existing backend tests before selecting the smallest package split.
4. Confirm that no existing route, payload, frontend or deployment file is in
   scope.
5. Preserve all legacy HLL storage, workers, materializers, providers, fallback
   paths and configuration.

### 2. Create the isolated integration boundary

Create a small repository-conventional package under `backend/app/crcon/`.
Evaluate this structure and keep only files with a clear responsibility:

```text
backend/app/crcon/
    __init__.py
    api.py
    database.py
    capabilities.py
    cache.py
    models.py
```

The package conceptually owns HTTP access, PostgreSQL read access,
schema/capability validation, common sanitized errors, source metadata and
memory caching. Do not move legacy modules into it.

No code outside this boundary should need CRCON table names. The adapter may
know verified names including `steam_id_64`, `player_soldier`, `player_names`,
`player_sessions`, `log_lines`, `map_history`, `player_stats` and
`server_counts`; routes, payload builders and frontend code must not reference
them in this task.

Create only foundation-level concepts needed across later adapters, such as:

- `CrconSourceMetadata`;
- `CrconCapability`;
- `CrconCapabilityStatus`;
- `CrconCapabilityReport`;
- `CrconUnavailableError`;
- `CrconSchemaIncompatibleError`;
- `CrconApiError`; and
- `CrconDatabaseError`.

Do not prematurely create product models such as current matches, kill events,
ranking rows or historical DTOs.

### 3. Implement the safe CRCON HTTP client

Implement a small injectable client for only these verified foundation
operations:

- `get_public_info`;
- `get_scoreboard_maps`; and
- `get_map_scoreboard`.

Requirements:

- configurable base URL and hard timeout;
- validated URL joining that prevents endpoint/base confusion;
- query encoding through standard library primitives;
- JSON parsing and appropriate `result` envelope unwrapping;
- deterministic HLL Vietnam user agent;
- zero retries by default and at most one optional retry for safe idempotent
  reads;
- no unbounded loop or hidden backoff worker;
- injectable/configurable authentication without assuming an unverified
  production scheme;
- injectable network transport/test seam;
- sanitized errors that never render credentials, authorization headers or
  authenticated URLs; and
- no real network call in tests.

Prefer the existing stdlib `urllib` conventions from
`backend/app/providers/public_scoreboard_provider.py`. Do not add `requests`,
`httpx`, `aiohttp` or another networking framework.

Leave the legacy public-scoreboard provider's behavior unchanged. Prefer an
independent initial implementation. Share or refactor a tiny utility only if
zero product behavior change is demonstrable and documented.

### 4. Implement the strictly read-only PostgreSQL adapter

Use the existing `psycopg[binary]>=3.2,<4` dependency. Do not introduce another
driver, and do not add `psycopg_pool` merely to satisfy a future pooling
recommendation. Keep the design open to a bounded pool later if measured load
justifies one.

Introduce a distinct CRCON database configuration concept following repository
conventions, expected to resemble `HLL_CRCON_DATABASE_URL`. Never reuse
`HLL_BACKEND_DATABASE_URL`, which belongs to the legacy HLL database.

The adapter must enforce read-only behavior at more than one layer where
practical:

1. request `default_transaction_read_only=on` when connecting;
2. begin database work with a read-only transaction;
3. run `SHOW transaction_read_only`; and
4. fail closed unless the result is `on`.

Connection behavior must include:

- configurable connection timeout;
- configurable statement timeout;
- lock timeout where useful;
- `application_name=hll-vietnam-bff`;
- rollback and close on every exit path;
- sanitized driver errors that never contain the DSN; and
- no write-capable startup operation.

The adapter must not contain or expose:

- `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `CREATE`, `ALTER`, `DROP`, `TRUNCATE`,
  `VACUUM` or `REINDEX` operations;
- schema initialization, migrations, materialization or cache-table writes; or
- a public generic arbitrary-SQL execution method.

Expose capability-specific reads or a tightly controlled internal SELECT path.
Correct read-only enforcement takes priority over pooling or query breadth.

### 5. Implement the capability/schema contract

Represent at least these capabilities:

- public/live state;
- historical maps;
- historical player statistics;
- event logs;
- player identities and names;
- player sessions; and
- server-count history.

Implement a non-mutating probe that validates the required tables and columns
for each database-backed capability. Results must distinguish `SUPPORTED`,
`UNAVAILABLE` and `INCOMPATIBLE`, or equally precise states. A result must name
the affected capability and sanitized missing structure without invalidating an
unrelated capability.

Absence of optional future capability must not globally fail application
startup. Missing configuration should report the new adapter as unavailable
without changing current product startup. The probe must not initialize or
migrate schema.

Represent the accepted CRCON source commit as fixture/contract metadata. Do not
compare a runtime server blindly to that Git SHA.

### 6. Add minimum optional configuration

Add only configuration required to construct the dormant foundation, such as:

- CRCON API base URL;
- CRCON API timeout;
- injectable authentication input without a fixed production scheme;
- CRCON database URL;
- CRCON DB connection timeout;
- CRCON DB statement/lock timeout; and
- expected contract revision metadata.

Follow existing parsing, validation and test conventions. New configuration may
be absent. Its absence must make only the CRCON foundation unavailable; it must
not change existing defaults, route traffic to CRCON, or prevent legacy backend
startup. Do not place real values or secrets in code or tests.

### 7. Implement the bounded memory cache

Implement a small generic process-local TTL cache with:

- thread safety for the current threaded backend;
- a monotonic injectable clock;
- a strictly bounded maximum number of entries;
- per-entry or cache-instance TTL;
- deterministic LRU or equivalent eviction;
- lazy expiry, without a cleanup thread/worker;
- explicit invalidation; and
- no disk persistence or credential storage.

Prefix/server/match invalidation and bounded stale reads are optional only if
they remain simple and precisely tested. If a small single-flight/request
coalescing primitive fits naturally without excessive complexity, include it
and test it. Otherwise record coalescing as a requirement for the later
current-match migration in Outcome; do not expand TASK-290 or create a new task.

### 8. Create sanitized local fixtures

Create fixtures under `backend/tests/fixtures/crcon/` for:

1. public information;
2. scoreboard map list;
3. map scoreboard detail; and
4. representative capability/schema metadata.

Include, where structurally relevant, null optional fields, completed and
open/current maps, invented player statistics, a teamkill value, weapon data,
server number, map identity and timestamps. Use invented player identities and
names. Never copy raw production logs or community/player values.

Add a small metadata fixture recording the official repository, branch, pinned
source commit and sanitation status.

### 9. Add focused local tests

Prefer one or a small number of unittest-compatible modules. Tests must not
require production, network, Docker or Testcontainers.

API tests must cover:

- URL/query construction;
- successful result unwrapping;
- malformed response handling;
- timeout/network failure sanitation;
- retry ceiling; and
- absence of credentials/authenticated URLs in errors.

Database tests must cover:

- missing DSN reports unavailable;
- connection and transaction read-only enforcement;
- fail-closed behavior when `transaction_read_only != on`;
- SELECT-only/capability-specific access and absence of arbitrary write API;
- sanitized driver failures; and
- rollback/connection cleanup.

Use test doubles/fake connections for read-only verification and capability
introspection. Do not require a running PostgreSQL instance.

Capability tests must cover:

- all expected structures are supported;
- a missing table affects the precise capability;
- a missing column produces a precise incompatible result; and
- optional failure does not invalidate unrelated capabilities.

Cache tests must cover TTL expiry, size bounds, deterministic eviction,
explicit invalidation, basic concurrent access and absence of a cleanup worker.

Fixture tests must load every JSON fixture, assert required structural fields,
verify the pinned commit metadata and reject obvious credential/production
patterns.

### 10. Preserve strangler compatibility and complete validation

Do not wire the new package into `backend/app/routes.py`,
`backend/app/payloads.py` or any public product behavior. Do not delete or
disable legacy HLL PostgreSQL, AdminLog storage/materialization, historical
storage, workers, snapshots, scoreboard fallback, RCON client or existing
database configuration.

Run all validation listed below. Review `git diff --name-only` and confirm the
change remains inside the new adapter, its minimum optional configuration and
focused tests/fixtures. Record any justified file/dependency exception in
Outcome rather than silently widening scope.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `docs/CRCON_FIRST_STATELESS_ARCHITECTURE.md`
- `docs/CRCON_FIRST_MIGRATION_AND_DECOMMISSION_PLAN.md`
- `backend/app/config.py`
- `backend/app/providers/public_scoreboard_provider.py`
- `backend/app/postgres_rcon_storage.py`
- `backend/requirements.txt`
- representative existing backend tests showing configuration, fake
  connections and unittest conventions
- pinned CRCON upstream source at
  `MarechJ/hll_rcon_tool@4cf1e7e2fa691d849eaf85abb7065010e13f28e4`

Read these files before implementation. Inspect the pinned upstream source
locally/read-only and do not use a newer revision silently.

## Expected Files to Modify

- `backend/app/crcon/**`
- `backend/app/config.py`
- `backend/tests/test_crcon_adapter_foundation.py`, or a similarly small focused
  unittest-compatible test split when clearly justified
- `backend/tests/fixtures/crcon/**`
- the TASK-290 lifecycle file

`backend/requirements.txt` should remain unchanged because the required
PostgreSQL and HTTP primitives already exist. If implementation proves a
dependency change genuinely unavoidable, obtain explicit justification in
Outcome and keep it narrowly scoped.

The foundation may exceed the repository's normal five-file preference because
one isolated package plus sanitized fixtures and focused tests necessarily
spans several small files. This is not permission to expand into endpoint
migration.

## Constraints

- Implement locally only; do not access SSH, Portainer, production CRCON API,
  production PostgreSQL, production RCON or credentials.
- Do not call a real upstream network service from tests.
- Do not modify `backend/app/routes.py` or `backend/app/payloads.py`.
- Do not modify current-match, history, ranking or player-profile behavior.
- Do not modify frontend, deploy, Compose, Dockerfiles, schemas, database files,
  runtime secrets or production configuration.
- Do not switch or refactor the legacy provider unless a tiny shared utility is
  demonstrably behavior-neutral and explicitly justified; the preferred path
  is leaving it unchanged.
- Do not delete, disable or migrate HLL PostgreSQL, AdminLog persistence,
  materializers, historical storage, workers, snapshots, scoreboard fallback,
  direct RCON or existing configuration.
- Do not add PostgreSQL drivers, HTTP frameworks, Redis, a persistent cache,
  queues, workers, cleanup threads, Docker or Testcontainers.
- Do not expose arbitrary SQL or any mutation operation through the CRCON
  adapter.
- Do not expose secrets, DSNs, authorization headers, authenticated URLs or raw
  upstream rows in errors or public models.
- Do not implement speculative product-domain abstractions.
- Keep TASK-272 through TASK-281 and TASK-284 unmodified and unexecuted.
- Do not modify or stage the existing local TASK-204, TASK-242, TASK-264,
  TASK-266, TASK-267 or TASK-268 files.
- Do not create a follow-up task while executing TASK-290; record bounded future
  requirements in Outcome.
- Do not use `git add .`, `git add -A`, `git clean`, `git stash`,
  `git reset --hard`, rebase, force push or automatic merge.

## Validation

Run at minimum:

```powershell
python -m compileall backend/app
Set-Location backend
python -m unittest tests.test_crcon_adapter_foundation
```

If the focused test file is split, run the exact unittest modules created.
Return to the repository root and run relevant existing configuration tests if
`backend/app/config.py` changes.

Also run:

```powershell
git diff --check
git diff --name-only
git status --short
```

Validation must confirm:

- CRCON DB access fails closed when read-only mode cannot be established;
- there is no CRCON DB mutation or public arbitrary-SQL API;
- no secret, DSN, HTTP credential/header or authenticated URL appears in
  adapter exceptions;
- fixtures contain no production credentials, player data or raw logs;
- tests require no real upstream network or production PostgreSQL;
- missing optional CRCON configuration does not break existing startup;
- every capability reports its own supported/unavailable/incompatible state;
- the cache is bounded, thread-safe and process-local;
- existing routes and legacy providers are untouched and behave as before;
- no frontend, deploy, Compose, Dockerfile, schema, database or runtime-secret
  file changed; and
- the final diff matches the expected scope.

If the full backend suite is practical, run it as secondary validation. Report
unrelated pre-existing failures separately and do not fix them inside TASK-290.
Integration tests requiring external infrastructure are not required. Do not
execute TASK-284.

## Outcome

Record:

- starting HLL commit and exact pinned CRCON repository/branch/commit;
- final package/file structure and why each file exists;
- HTTP methods implemented, timeout/retry/auth injection and error-redaction
  behavior;
- CRCON DB configuration separation, read-only enforcement evidence, timeout
  behavior and cleanup;
- capability states, required schema mapping and precise degraded behavior;
- cache bounds, TTL/eviction/invalidation behavior and whether coalescing was
  included or deferred;
- fixture inventory and sanitation evidence;
- focused and relevant existing test results;
- confirmation that existing routes/product behavior and all legacy
  persistence/workers/providers remained unchanged;
- confirmation that no production/network/credential access occurred;
- explicit justification for any additional file or dependency, if required;
  and
- final diff/scope review.

TASK-290 is complete only when future tasks can consume a stable internal
foundation for CRCON HTTP, strictly read-only CRCON PostgreSQL, capability
probing, bounded memory caching and safe optional configuration without knowing
legacy HLL persistence internals.

### Implementation result

- Starting HLL commit: `23de30d430bb6eadc44c141e1a8f3246c9e95d8c`.
- Pinned upstream inspected read-only: `https://github.com/MarechJ/hll_rcon_tool`,
  branch `master`, commit `4cf1e7e2fa691d849eaf85abb7065010e13f28e4`.
- Added the isolated `backend/app/crcon/` package with `models.py` for immutable
  foundation metadata/errors, `api.py` for the three verified GET operations,
  `database.py` for capability-only read access, `capabilities.py` for the
  schema contract, `cache.py` for bounded LRU-TTL caching and `__init__.py` for
  the supported internal surface.
- The HTTP client implements `get_public_info`, `get_scoreboard_maps` and
  `get_map_scoreboard` with strict unauthenticated base-URL validation,
  standard-library query encoding, a hard timeout, zero retries by default and
  at most one optional retry. Authentication is injected as headers. Errors
  suppress exception causes and never include headers, authenticated URLs or
  raw responses.
- New optional configuration is separate from legacy HLL storage:
  `HLL_CRCON_API_BASE_URL`, `HLL_CRCON_API_TIMEOUT_SECONDS`,
  `HLL_CRCON_DATABASE_URL`,
  `HLL_CRCON_DATABASE_CONNECT_TIMEOUT_SECONDS`,
  `HLL_CRCON_DATABASE_STATEMENT_TIMEOUT_MS` and
  `HLL_CRCON_DATABASE_LOCK_TIMEOUT_MS`. Contract metadata remains the pinned
  reference constant; missing settings do not affect legacy startup.
- PostgreSQL connections request `default_transaction_read_only=on`, start
  with `BEGIN READ ONLY`, verify `SHOW transaction_read_only` equals `on`, set
  application/connect/statement/lock limits, and always roll back and close.
  Verification failure is closed with a sanitized `CrconDatabaseError`. The
  public adapter exposes only configuration state and the fixed capability
  probe; it has no arbitrary-SQL or mutation method.
- Capability states are `SUPPORTED`, `UNAVAILABLE` and `INCOMPATIBLE`, reported
  independently for live state, historical maps, historical player stats,
  event logs, player identities/names, player sessions and server-count
  history. The probe uses fixed information-schema reads for verified columns
  in `steam_id_64`, `player_soldier`, `player_names`, `player_sessions`,
  `log_lines`, `map_history`, `player_stats` and `server_counts`.
- The process-local cache is thread-safe, monotonic-clock based, lazily expires
  entries, accepts explicit maximum size/default or per-entry TTL, evicts
  deterministically by LRU and supports invalidation/clear without disk or a
  cleanup thread. Request coalescing was deliberately deferred to the
  current-match migration because it would widen this generic foundation.
- Added five synthetic JSON fixtures: public info, scoreboard map list, map
  scoreboard detail, schema capabilities and source/sanitation metadata. They
  use invented identities and contain no credentials, production URLs,
  community player data or raw production logs.
- `python -m compileall backend/app`: passed.
- `python -m unittest tests.test_crcon_adapter_foundation`: 26 tests passed.
- Secondary `python -m unittest discover -s tests`: 157 tests ran with the
  pre-existing TASK-284 baseline of 1 failure and 3 errors. The identical
  signatures were the historical-runner maintenance status assertion, both
  RCON/public-scoreboard fallback cases plus Windows SQLite cleanup, and the
  absent system `pytest` import required by the audit module. No baseline fix
  was attempted.
- The source-only mutation scan found zero occurrences of executable mutation
  SQL. `git diff --check` passed. Routes, payloads, frontend, deployment,
  Compose, Dockerfiles, requirements, database files and runtime secrets are
  unchanged.
- Existing HLL persistence, AdminLog/materialization, workers, snapshots,
  scoreboard provider and RCON client remain intact and unmodified. No public
  endpoint was migrated.
- No real upstream request, production database, credential, SSH, Portainer or
  production system was accessed. TASK-272 through TASK-281 and TASK-284 were
  not executed or edited, and no follow-up task was created.

## Change Budget

- Prefer the smallest coherent `backend/app/crcon/` package and one focused
  test/fixture family.
- The normal five-file limit may be exceeded only for the isolated adapter
  package and sanitized fixtures required by this foundation.
- Keep individual modules small and cohesive; do not create extra files without
  a clear responsibility.
- Do not use the exception to migrate endpoints, decommission legacy code or
  add infrastructure.
