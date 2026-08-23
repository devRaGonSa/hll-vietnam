---
id: TASK-306
title: Split API route dispatcher by public domain
status: done
type: backend
team: Arquitecto Python
supporting_teams:
  - Backend Senior
  - Analista
roadmap_item: crcon-cutover
priority: high
---

# TASK-306 - Split API route dispatcher by public domain

## Goal

Replace the 584-line `backend/app/api/routes.py` dispatcher with coherent
domain routers behind the unchanged `app.api.routes.resolve_get_payload`
entrypoint, preserving every public GET contract and rollback path.

## Context

TASK-305 split the payload facade by domain at clean base `9632365`. Routes are
the remaining API structural hotspot. This is a behavior-preserving local
refactor: no frontend, CRCON, SQL, storage, writer or deployment behavior may
change.

## Steps

1. Inventory all routes, parsing, validation, precedence, consumers and source
   selectors before moving code.
2. Publish the explicit router registry and helper ownership plan.
3. Convert `api/routes.py` to a package with one stable resolver and uniform
   `(HTTPStatus | None, payload)` router results.
4. Extract route branches verbatim by domain and centralize only identical
   parsers.
5. Add a route contract matrix and collision/precedence tests.
6. Update structure and dependency-ledger paths, run focused/full validation,
   and commit locally if no new regression exists.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/python-architect.md`
- `ai/orchestrator/backend-senior.md`
- `backend/app/api/routes.py`
- `backend/app/main.py`
- `docs/CODE_STRUCTURE.md`

## Expected Files to Modify

- `backend/app/api/routes.py` (replaced by package)
- `backend/app/api/routes/`
- focused route tests and monolith patch paths
- `docs/CODE_STRUCTURE.md`
- `docs/CRCON_FIRST_LEGACY_DEPENDENCY_LEDGER.md`
- this task file

The normal change budget is exceeded intentionally because all 37 public routes
must move with explicit compatibility coverage.

## Constraints

- Preserve URLs, GET method, parsing/defaults/caps, status/error payloads,
  selector behavior, opaque player IDs and dynamic/static precedence exactly.
- Keep `main.py` unaware of domain routers and retain
  `resolve_get_payload(path)` unchanged.
- No framework, dynamic discovery, mutable request-global state, SQL,
  transport, persistence, frontend, CRCON or deployment changes.
- Do not modify the parity observer or disable/remove legacy writers/storage.

## Validation

- TASK-293-303 focused CRCON/current-match/server/history/player/aggregate tests.
- New route matrix and explicit collision tests.
- Historical UI, Stats/Ranking and frontend snapshot regressions.
- Python compileall, all frontend JavaScript syntax, diff checks and full
  backend discovery with TASK-304 baselines classified separately.

## Outcome

Completed locally without deployment or external runtime/storage mutation.

- Replaced the 584-line `api/routes.py` dispatcher with a routes package and a
  40-line `routes/__init__.py` stable resolver/registry.
- Preserved `app.api.routes.resolve_get_payload(path)` exactly; `main.py`,
  `app/__init__.py`, integration scripts and external consumers required no
  import changes.
- Added seven deterministic domain routers in registry order: static, servers,
  current match, players, rankings, history and product features. Route counts
  are 4, 4, 4, 3, 10, 4 and 8 respectively: all 37 public routes.
- Every domain router uses the shared `(HTTPStatus | None, payload)` result.
  Unmatched requests still return `(None, {})` from the stable resolver.
- Centralized only the identical limit, page, year, required-year and
  limit-with-default parsers in `routes/common.py`. The four identical trusted
  current-match server checks are shared only inside `current_match.py`.
- Preserved exact paths, query parsing order, defaults/caps, HTTP statuses,
  error text, payload builders, selectors and opaque player-ID handling. No URL
  decoding/coercion or platform inference was introduced.
- Preserved critical precedence inside domain owners: exact player search
  before dynamic player profile, and exact server history before dynamic
  per-server history. Registry ownership tests prove every public URL matches
  exactly one router.
- Retained every alias. None met `SAFE_DELETE`; aliases remain active,
  rollback-required or product-decision-required.
- Removed only the monolith-internal `GET_ROUTES` table as `SAFE_DELETE`: no
  external reference existed and its five entries now have explicit static or
  server ownership. No public route or alias was deleted.
- Pre-deletion AST comparison found identical old/new path literal sets (39
  literals including dynamic prefixes). Sixteen invalid/precedence edge cases
  were also executed against old and new resolvers with identical results.
- Added nine route tests covering the 37-path ownership/shape matrix, registry
  order, unknown route behavior, static/dynamic collisions, opaque IDs,
  parameter forwarding, empty/not-found payload delegation and exact error
  contracts. One existing test mock was retargeted to the canonical history
  router.
- Route modules import only canonical payload modules plus existing config,
  target/origin validation and current-match exceptions. No SQL, storage,
  CRCON parsing/transport, WebSocket or mutable request state moved into routes;
  no circular import was introduced.
- Updated `docs/CODE_STRUCTURE.md` and the CRCON-first dependency ledger with
  the routes tree, registry and ownership paths.

Validation:

- 207 route/CRCON/current-match/server/history/player/aggregate tests: pass.
- 47 historical snapshot/ranking/stats/scoreboard tests: pass; existing SQLite
  `ResourceWarning`s remain non-failing.
- Historical UI and Stats/Ranking integration scripts: pass. The optional live
  HTTP probe skipped cleanly because no backend was running; imported route
  contract checks passed.
- Frontend current-match snapshot tests: 37 pass.
- All frontend JavaScript `node --check`: pass.
- `compileall backend/app backend/tests`: pass.
- Stable resolver import and seven-router registry smoke: pass.
- `git diff --check`: pass with only repository line-ending warnings.
- Full backend discovery ran 324 tests and reproduced exactly the four TASK-304
  baselines: optional `pytest` missing; two outdated materialized recent-match
  expectations with Windows SQLite cleanup errors; and runner maintenance
  expecting `ok` instead of `partial`. No new TASK-306 regression was found.

Final assessment:

- `ROUTE_REFACTOR = GO`
- `PUBLIC_URL_COMPATIBILITY = GO`
- `PUBLIC_ERROR_CONTRACT_COMPATIBILITY = GO`
- `LEGACY_WRITER_DISABLE_READINESS = NOT_READY`

## Pre-move route audit

Every route is `GET`; `resolve_get_payload` returns `(None, {})` when unmatched.
All error bodies use `build_error_payload` unless the route is unmatched.

| Domain | Path | Parameters and exact validation/default | Builder / result | Consumer, selector and precedence |
| --- | --- | --- | --- | --- |
| SYSTEM | `/health` | none | health / 200 | landing, Ranking, Stats; config selectors |
| STATIC | `/api/community` | none | community / 200 | public compatibility; no selector |
| STATIC | `/api/trailer` | none | trailer / 200 | landing; no selector |
| STATIC | `/api/discord` | none | Discord / 200 | public compatibility; no selector |
| SERVERS | `/api/servers` | none | server cards / 200 | landing; server-list selector |
| LEGACY/SERVERS | `/api/servers/latest` | none | latest snapshot / 200 | rollback/public alias; exact before dynamic |
| LEGACY/SERVERS | `/api/servers/history` | `limit=20`, integer 1..100 | history / 200; invalid 400 `Invalid limit parameter` | rollback alias; exact before dynamic |
| LEGACY/SERVERS | `/api/servers/{id}/history` | non-empty opaque path segment; `limit=20`, 1..100 | detail history / 200; empty ID 400 | dynamic route last inside servers |
| CURRENT_MATCH | `/api/current-match/snapshot` | required trusted `server` | snapshot / 200; missing 400; unsupported 404; cursor 400; unavailable 503 | current frontend snapshot; current-match selector; exact |
| CURRENT_MATCH | `/api/current-match` | required trusted `server` | summary / same status mapping | legacy frontend transport/rollback |
| CURRENT_MATCH | `/api/current-match/kills` | required trusted `server`; `limit=20`, 1..100; optional opaque `since_event_id` | kills / same status mapping | legacy transport/rollback |
| CURRENT_MATCH | `/api/current-match/players` | required trusted `server` | players / same status mapping | legacy transport/rollback |
| PLAYERS | `/api/stats/players/search` | required nonblank `q`; `limit=10`, 1..100; `server_id` then `server` alias | search / 200; missing query or invalid limit 400 | Stats; aggregate selector; exact must precede dynamic |
| PLAYERS | `/api/stats/players/{player_id}` | non-empty opaque remainder; `timeframe=weekly`, weekly/monthly; `server_id` then `server` | profile / 200; empty ID/invalid timeframe 400 | Stats; aggregate selector; dynamic after search; no ID inference/decoding change |
| LEGACY/PLAYERS | `/api/historical/player-profile` | required opaque `player` | legacy profile / 200; missing 400 | retained public rollback alias |
| RANKINGS | `/api/stats/rankings/annual` | `metric=kills` only; `year=current UTC`, positive integer; `limit=20`, 1..100; `server_id` then `server` | annual / 200; invalid 400; builder `ValueError` 400 | Stats; aggregate selector |
| RANKINGS | `/api/ranking` | `timeframe=weekly` in weekly/monthly/annual; allowlisted metric; `limit=20`, 1..100; validated `server_id`/`server`; annual requires positive year | global ranking / 200; invalid/builder error 400 | Ranking; aggregate selector |
| LEGACY/RANKINGS | `/api/historical/weekly-top-kills` | `limit=20`, 1..100; optional `server` | weekly kills / 200 | retained public rollback route |
| LEGACY/RANKINGS | `/api/historical/leaderboard` | `limit=20`; metric kills/deaths/support/matches-over-100; timeframe weekly/monthly; optional server | leaderboard / 200; invalid 400 | compatibility route |
| LEGACY/RANKINGS | `/api/historical/weekly-leaderboard` | same metric/limit; optional server | weekly wrapper / 200 | active alias |
| LEGACY/RANKINGS | `/api/historical/monthly-leaderboard` | same metric/limit; optional server | monthly wrapper / 200 | active alias |
| RANKINGS | `/api/historical/snapshots/leaderboard` | same metric/limit plus weekly/monthly timeframe | snapshot / 200; invalid 400 | Historical frontend; aggregate selector |
| RANKINGS | `/api/historical/snapshots/monthly-leaderboard` | same metric/limit | monthly snapshot / 200 | active alias/rollback |
| RANKINGS | `/api/historical/snapshots/weekly-leaderboard` | same metric/limit | weekly snapshot / 200 | active alias/rollback |
| RANKINGS | `/api/historical/snapshots/server-summary` | optional `server` | summary snapshot / 200 | Historical frontend; aggregate selector |
| HISTORY | `/api/historical/recent-matches` | `limit=20`, 1..100; `page=1`, 1..1000; optional server | recent matches / 200; invalid limit/page 400 | compatibility; match selector |
| HISTORY | `/api/historical/snapshots/recent-matches` | same limit/page/server | recent snapshot / 200; invalid 400 | Historical frontend; match selector |
| HISTORY | `/api/historical/matches/detail` | required `server` then required opaque `match` | detail / 200; missing parameter 400 | Historical detail; match selector |
| LEGACY/HISTORY | `/api/historical/server-summary` | optional `server` | summary / 200 | retained public rollback route |
| PRODUCT_FEATURES | `/api/historical/monthly-mvp` | `limit=20`, 1..100; optional server | MVP / 200; invalid 400 | product decision required |
| PRODUCT_FEATURES | `/api/historical/monthly-mvp-v2` | same | MVP V2 / 200 | product decision required |
| PRODUCT_FEATURES | `/api/historical/player-events` | same plus allowlisted `view=most-killed` | events / 200; invalid view 400 | product decision required |
| PRODUCT_FEATURES | `/api/historical/snapshots/monthly-mvp` | same | MVP snapshot / 200 | active alias/product decision |
| PRODUCT_FEATURES | `/api/historical/snapshots/monthly-mvp-v2` | same | MVP V2 snapshot / 200 | active alias/product decision |
| PRODUCT_FEATURES | `/api/historical/snapshots/player-events` | same view/limit/server | event snapshot / 200 | active alias/product decision |
| PRODUCT_FEATURES | `/api/historical/elo-mmr/leaderboard` | `limit=20`, 1..100; optional server | Elo leaderboard / 200 | product decision required |
| PRODUCT_FEATURES | `/api/historical/elo-mmr/player` | required opaque `player`; optional server | Elo player / 200; missing 400 | product decision required |

## Move and registry plan

1. Convert `api/routes.py` to `api/routes/__init__.py`; retain only the stable
   resolver, explicit immutable registry and compatibility constants needed by
   real consumers.
2. Add `common.py` for the unchanged identical limit/page/year parsers and the
   shared route-result type. Do not centralize domain-specific validation.
3. Extract `static.py`, `servers.py`, `current_match.py`, `players.py`,
   `rankings.py`, `history.py` and `product_features.py`, mirroring payload
   ownership.
4. Registry order: static, servers, current match, players, rankings, history,
   product features. Prefix collisions are resolved inside owners: exact
   server latest/history before dynamic server history, and exact player search
   before dynamic player profile.
5. Keep all aliases. None meets `SAFE_DELETE`: each is active, rollback-required
   or product-decision-required.

## Change Budget

The larger file count is justified by the authorized behavior-preserving split
and route-level compatibility coverage. No product implementation is included.
