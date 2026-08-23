---
id: TASK-303
title: Move player search to CRCON API and audit legacy dependencies
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto Python
  - Arquitecto de Base de Datos
roadmap_item: crcon-cutover
priority: high
---

# TASK-303 - Move player search to CRCON API and audit legacy dependencies

## Goal

Move the CRCON-selected public player-name search from PostgreSQL to the
authenticated CRCON 12.0.1 `get_players_history` API, preserve legacy rollback
and publish the complete reader/writer dependency and cutover-readiness audit.

## Context

TASK-302 proved that PostgreSQL name search should not be the canonical public
path. CRCON 12.0.1 already exposes the bounded historical-player API under
`api.can_view_player_history`; the backend must own the credential and adapt
only safe identity/search fields. Player profiles and cross-match aggregates
remain read-only PostgreSQL work.

## Exact Implementation Plan

1. Pin the v12.0.1 handler, permission, GET arguments, auth header and response
   shape from commit `17c5880684cc419b27ef2bcca0dc439dfd623eae`.
2. Add a typed `get_players_history` client/DTO contract that accepts only the
   bounded safe filters and never exposes moderation or raw upstream payloads.
3. Reuse each server binding's server-side `api_headers`; require Bearer auth
   for player history without creating a browser token or another registry.
4. Add a player-search service that resolves N selected canonical targets,
   calls each HLL target explicitly, keeps HLLV unverified, merges only equal
   opaque IDs inside the same game and performs an empty-name-result ID fallback
   without inspecting the identifier format.
5. Route only CRCON-selected player search through that service. Keep profile,
   ranking and other aggregate reads on CRCON PostgreSQL and keep legacy as the
   immediate selector rollback.
6. Preserve the public search JSON keys; represent unavailable match counts as
   `null` with an explicit status, and preserve Stats UI behavior.
7. Prove the old PostgreSQL fuzzy-name helper has no production consumer and
   mark it deprecated instead of adding an index or another database.
8. Inventory all legacy tables, materializations, jobs, readers, writers,
   schedules and rollback/product dependencies using the required status
   vocabulary, then issue a per-family readiness matrix.
9. Run focused client/service/payload/route/frontend/security tests plus the
   stacked CRCON suites, compile checks, integration validation when configured,
   diff scope and whitespace checks.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/backend-senior.md`
- `backend/app/crcon/api.py`
- `backend/app/crcon/aggregate_service.py`
- `backend/app/payloads.py`

## Expected Files to Modify

- `backend/app/crcon/api.py`
- `backend/app/crcon/dto.py`
- `backend/app/crcon/models.py`
- `backend/app/crcon/player_search_service.py`
- `backend/app/payloads.py`
- focused backend/frontend validation tests
- `backend/README.md`
- structured CRCON legacy-dependency/readiness documentation
- this task file

The scope intentionally exceeds the preferred five-file budget because the
versioned transport/DTO boundary, service selection, regression tests and
mandatory operational ledger are independently reviewable artifacts. No
unrelated product files are in scope.

## Constraints

- Use authenticated CRCON REST only for player search; no PostgreSQL name
  search, direct RCON, GetAdminLog, Redis or CRCON modification.
- Treat `player_id` as an opaque string. Never classify it from its shape.
- Keep credentials server-side and sanitize all errors and evidence.
- Keep profile aggregates on PostgreSQL and keep `legacy` rollback.
- Support N explicit targets; never assume HLL/HLLV equivalence or shared
  storage.
- Do not deploy, stop writers, remove storage or add persistence.

## Validation

- Handler/permission/argument evidence matches CRCON v12.0.1 source.
- Authenticated request, sanitized failure and no-secret-response tests pass.
- Name/opaque-ID/empty/pagination/multitarget/rollback tests pass.
- Stats public JSON and frontend rendering remain compatible.
- No production call site uses the PostgreSQL fuzzy-name helper.
- The full dependency ledger and readiness matrix name every active blocker.
- Relevant integration validation, compileall and `git diff --check` pass.

## Outcome

Completed locally. CRCON-selected public player search now uses the typed,
authenticated CRCON 12.0.1 `get_players_history` API; it no longer invokes the
CRCON PostgreSQL exact/fuzzy player-search helpers. Profiles, rankings and
other cross-match aggregates remain on the TASK-302 read-only PostgreSQL
repository. `HLL_HISTORICAL_AGGREGATE_SOURCE=legacy` remains the immediate
rollback and no hidden fallback was added.

Pinned source verification at commit
`17c5880684cc419b27ef2bcca0dc439dfd623eae` confirmed GET/POST support, the
`api.can_view_player_history` permission, Bearer API-key authentication and the
safe argument subset. The HLL Vietnam client uses GET with exactly one of
`player_name` or `player_id`, bounded `page/page_size`, and optional
`exact_name_match`. It parses a safe DTO subset and rejects malformed payloads;
moderation, watchlist, blacklist, session, account and raw response data never
cross the adapter.

The search service:

- reuses aligned per-target `api_headers` from the existing server-side binding
  configuration and adds no token registry or persistence;
- exposes `SUPPORTED`, `AUTH_REQUIRED`, `UNAVAILABLE` and
  `UNVERIFIED_HLLV` independently of database capability;
- calls every selected HLL target explicitly, never calls unverified HLLV, and
  deduplicates only equal `(game, opaque player_id)` values;
- uses at most one bounded name call plus one empty-result ID call per target;
  the ID fallback retains literal equality because upstream v12.0.1 implements
  its `player_id` filter as substring `ILIKE`;
- keeps `matches_considered=null` with an explicit not-provided status and the
  frontend renders it as unavailable instead of fabricating zero.

`PLAYER_NAME_SEARCH_CRCON_DB=NOT_REQUIRED`. The old PostgreSQL exact/name
helpers have no production call site or repository-protocol method and are
marked deprecated for later cleanup. No index or database was created.

The full storage/job audit is documented in
`docs/CRCON_FIRST_LEGACY_DEPENDENCY_LEDGER.md`. It covers server snapshots,
every historical/application/RCON/ranking/player-index/Elo table family,
filesystem snapshots, readers, writers, Compose/manual schedules,
replacements and the required status vocabulary. The final writer decision is
`NOT_READY`: runtime API auth and aggregate database evidence are not configured
locally; explicit snapshot-history rollback readers remain; and MVP V1/V2,
player-event and Elo/MMR require product decisions. Consequently no TASK-304
writer-disable specification was created or authorized.

Runtime configuration was inspected only through the canonical process and
`.env.example` variable names. `HLL_SERVER_TARGETS`,
`HLL_CRCON_CURRENT_MATCH_BINDINGS`, `HLL_CRCON_DATABASE_URL` and the aggregate
selector were absent. No credential discovery, deployed request, CRCON change,
database write, deployment, writer stop or deletion occurred.

Validation:

- 157 CRCON adapter/service/route contract tests passed;
- 51 current-match/parity/payload/serialization/ranking/profile tests passed;
- focused TASK-303 authentication, malformed response, name, opaque-ID,
  pagination, empty, multi-target, HLLV, no-secret and rollback cases passed;
- Stats regression, Historical UI regression and repository integration
  validation passed (live HTTP was not running; the integration script used
  its documented local-import route checks);
- Python compileall, JavaScript syntax and `git diff --check` passed;
- the broad 312-test discovery retained the already documented unrelated
  baseline: missing optional `pytest`, two legacy materialization/fallback
  errors and one historical-runner maintenance expectation failure.

TASK-298 remains done with `CURRENT_MATCH_HLL=INSUFFICIENT_EVIDENCE`. Its
observer and evidence were neither changed nor run.

## Change Budget

Keep implementation adapters small and isolate the larger dependency inventory
in documentation. Do not expand into deployment, writer shutdown or deletion.
