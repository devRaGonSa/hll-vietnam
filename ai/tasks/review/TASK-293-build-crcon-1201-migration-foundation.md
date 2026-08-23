---
id: TASK-293
title: Build CRCON 12.0.1 migration foundation
status: review
type: backend
team: Backend Senior
supporting_teams: ["Arquitecto Python", "Arquitecto de Base de Datos"]
roadmap_item: crcon-first-architecture
priority: critical
---

# TASK-293 - Build CRCON 12.0.1 migration foundation

## Goal

Prepare a tested, extensible CRCON 12.0.1 integration layer without migrating public endpoints or removing any legacy storage, worker or rollback path.

## Context

TASK-289 defined the CRCON-first target and TASK-290 through TASK-292 established an initial adapter, coherent current-match snapshot and optional frontend transport. This phase must make the shared target, identity, API DTO and PostgreSQL read-only boundaries safe for HLL and HLL Vietnam before endpoint migration continues.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Unify server configuration behind one extensible `ServerTarget` model while preserving legacy adapters.
2. Introduce explicit opaque player identity types and remove player-platform inference from `player_id` in active rollout paths.
3. Extend the CRCON API client with typed DTO results for the required 12.0.1 endpoints.
4. Split the PostgreSQL read contract from its implementation and add bounded, SELECT-only aggregate queries.
5. Add explicitly versioned 12.0.1 structural fixtures and distinguish supported, unsupported and unverified capabilities.
6. Run focused and existing CRCON/current-match regression checks.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `docs/CRCON_FIRST_STATELESS_ARCHITECTURE.md`
- `backend/app/crcon/api.py`
- `backend/app/crcon/database.py`

## Expected Files to Modify

- `backend/app/server_targets.py`
- `backend/app/rcon_targets.py`
- `backend/app/config.py`
- `backend/app/crcon/**`
- `backend/app/player_external_profiles.py`
- focused backend tests and CRCON 12.0.1 fixtures
- this task lifecycle file

`historical_storage.py` may receive a narrow compatibility correction only if its active identity path still infers platform from an opaque `player_id`.

## Constraints

- Do not access production, SSH, VPS, deployed CRCON, external databases or RCON.
- Do not deploy or change Compose, Dockerfiles, volumes or frontend behavior.
- Do not remove or disable legacy workers, tables, storage, endpoints or rollback selection.
- Never cast a public `player_id` to an integer or infer platform from its characters, length, regex or invented prefix.
- CRCON PostgreSQL access is SELECT-only with read-only transactions, parameters, timeouts and bounded results.
- Do not claim that an unverified field is proven by CRCON 12.0.1 fixtures.

## Validation

- focused ServerTarget, identity, API DTO and read-repository tests
- existing TASK-290 and TASK-291 test suites
- current-match legacy regressions
- `git diff --check`
- `git diff --name-only`
- `git status --short`
- integration tests if relevant and configured

## Outcome

### Implementation result

- Added canonical, non-secret `ServerTarget` and `ServerTargetRegistry` models loaded from `HLL_SERVER_TARGETS`. HLL and HLLV are explicit `game` values, any number of targets is supported, embedded URL credentials are rejected, and the legacy RCON target now links to the canonical target when keys match.
- `CrconCurrentMatchBinding` now owns one `ServerTarget` instead of duplicating slug/name/API/server-number/capability fields. Existing `HLL_CRCON_CURRENT_MATCH_BINDINGS` and `HLL_CURRENT_MATCH_SOURCE=legacy|crcon` remain supported for rollback.
- Added the domain `PlayerId` opaque string type and `PlayerIdentity` with separate `steam_id`, `eos_id`, `platform` and display name metadata. Numeric-looking and EOS IDs are never interpreted. External Steam links now require an explicit validated `steam_id`; an opaque `player_id` alone produces no platform inference or link.
- Removed active historical-storage inference based on `player_id.isdigit()`/length. Integer conversions that remain there address SQLite surrogate row IDs, not public player identifiers.
- Extended `CrconApiClient` with typed DTO returns for `get_public_info`, `get_live_game_stats`, `get_live_scoreboard`, `get_scoreboard_maps`, `get_map_scoreboard`, `get_map_history` and `get_previous_map`. `current_match.py` consumes normalized DTOs while retaining mapping compatibility for existing local test doubles.
- Added `crcon/repository.py` as the application protocol and scope boundary. Moved PostgreSQL implementation to `crcon/postgres_repository.py`; `crcon/database.py` remains a compatibility export so legacy imports continue working.
- Every PostgreSQL operation still uses `BEGIN READ ONLY`, verifies `transaction_read_only=on`, applies connection/statement/lock timeouts, rolls back and closes. The new fixed aggregate query is one parameterized `SELECT`; there is no arbitrary SQL surface or mutation statement.
- Added per-player/server aggregates: `COUNT(DISTINCT player_stats.map_id)`, `MAX(kills)`, `SUM(kills)`, and sums for deaths/combat/offense/defense/support/vehicle kills/vehicles destroyed. `map_history.server_number` is the history scope.
- Added `CrconServerScope`. Log reads require an explicit `log_server` plus `game`; the previous `log_lines.server == str(server_number)` inference was removed and now fails closed when no verified discriminator is configured.
- Added `backend/tests/fixtures/crcon_12_0_1/`. Metadata and every API contract are explicitly `unverified`; no fixture claims to have been captured from CRCON 12.0.1. Empty structural fixtures for live scoreboard, map history and previous map deliberately avoid inventing unknown response fields.
- Capability state now distinguishes supported, unsupported, unknown/unverified, unavailable and schema-incompatible. A configured API is `UNKNOWN` until the 12.0.1 contract is externally validated; missing aggregate columns fail only the aggregate capability.
- Focused CRCON/current-match/legacy-profile suite: 94 tests passed. Additional legacy worker/snapshot suite: 58 passed. Identity-affected materialization/profile subset: 7 passed. Frontend snapshot regression: 37 passed. Python compile and diff checks passed.
- The repository integration script passed backend import and historical UI validation, then stopped on pre-existing stats-page validation (`Stats page no longer exposes the annual ranking form`); this task did not modify frontend. Full unittest discovery also remains unable to import one pytest-based audit because pytest is not installed and exposes unrelated historical/environment-sensitive baseline failures.
- No production, SSH, deployed CRCON, external PostgreSQL/RCON, deploy files, Compose, frontend, workers, tables, volumes or legacy endpoint selection were modified.

### Still unverified for CRCON 12.0.1

- Exact response shapes for all seven API methods, especially live scoreboard, map history and previous map.
- Actual authentication and permission requirements for stats/player/log APIs.
- Actual `steam_id_64`, `player_soldier`, `player_stats`, `map_history` and log schema columns/indexes in 12.0.1.
- Whether `steam_id_64.steam_id_64` is the deployed canonical opaque game ID column.
- Exact values and semantics of `map_history.game`, `log_lines.game` and the explicit `log_lines.server` discriminator for servers 1 and 2.
- Availability of `vehicle_kills` and `vehicles_destroyed` in the deployed `player_stats` table.

### Next phase

Validate the marked contracts against an authorized local/sanitized CRCON 12.0.1 fixture, then migrate `/api/servers` and the current-match compatibility endpoints behind explicit source switches. Do not remove legacy writers or persistence until that endpoint parity is accepted.

## Change Budget

This cross-cutting foundation is expected to exceed the normal five-file/200-line preference because it adds isolated contracts, implementation and fixtures. Keep production modules small, avoid unrelated refactors and document the final scope.
