---
id: TASK-305
title: Split API payload facade by migrated public domain
status: done
type: backend
team: Arquitecto Python
supporting_teams:
  - Backend Senior
  - Analista
roadmap_item: crcon-cutover
priority: high
---

# TASK-305 - Split API payload facade by migrated public domain

## Goal

Replace the 2,904-line `backend/app/api/payloads.py` monolith with coherent
domain-oriented API payload modules while preserving every URL, JSON contract,
source selector, CRCON integration and legacy rollback path.

## Context

TASK-304 introduced explicit `api/`, `services/` and `tools/` packages and
extracted pure shared serializers. The remaining API facade still mixes server,
current-match, historical, player, ranking, snapshot and product-feature
contracts. TASK-305 is a behavior-preserving extraction, not a migration,
product redesign or writer-shutdown task.

Verified clean base: branch
`codex/task-298-collect-current-match-parity-evidence`, HEAD `1705b10`. No reset,
clean or stash is authorized.

## Steps

1. Classify every public payload builder and map it to routes, services,
   selectors, frontend consumers, serializers and rollback dependencies.
2. Publish a concise move plan before extraction.
3. Create a practical `api/payloads/` package with a compatibility-export
   surface and domain modules; keep `api/serializers.py` cohesive unless the
   audit proves a split useful.
4. Move code in contract-focused batches, retaining `from app.api.payloads
   import ...` compatibility and keeping routes thin.
5. Delete only extraction leftovers proven `SAFE_DELETE`; do not sweep other
   legacy/product code.
6. Update architecture and dependency-ledger paths.
7. Run focused, integration, frontend, compile/syntax and full-discovery
   validation, separating baseline failures from new regressions.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `docs/CODE_STRUCTURE.md`
- `docs/CRCON_FIRST_LEGACY_DEPENDENCY_LEDGER.md`
- `backend/app/api/payloads.py`
- `backend/app/api/routes.py`

## Expected Files to Modify

- `backend/app/api/payloads.py` (replaced by package or small facade)
- `backend/app/api/payloads/`
- `backend/app/api/routes.py`
- focused backend tests only where canonical patch/import paths change
- `docs/CODE_STRUCTURE.md`
- `docs/CRCON_FIRST_LEGACY_DEPENDENCY_LEDGER.md`
- this task file

The normal change budget is exceeded intentionally because extraction preserves
the existing facade through compatibility exports and requires domain-focused
test seams.

## Constraints

- No endpoint, JSON, selector/default, CRCON transport, SQL, cache/pagination,
  opaque player-ID, killfeed or rollback behavior changes.
- No deployment, CRCON/PostgreSQL/Redis mutation, writer shutdown, database
  removal or product-feature migration.
- Do not modify the parity observer.
- Avoid circular imports and trivial one-function modules.

## Validation

- TASK-293-303 CRCON/current-match/server/history/player/aggregate tests.
- frontend snapshot tests and all JavaScript syntax checks.
- Historical UI and Stats/Ranking regression scripts.
- Python compileall and `git diff --check`.
- Full backend discovery; only new regressions block TASK-305.

## Outcome

Completed locally without deployment or external runtime/storage mutation.

- Replaced the 2,904-line `api/payloads.py` monolith with a 98-line
  `api/payloads/__init__.py` compatibility surface and eight focused modules:
  `static`, `servers`, `current_match`, `common`, `history`, `players`,
  `rankings` and `product_features`.
- Kept all 38 public builder names importable from `app.api.payloads`; retained
  the parity observer's two private legacy current-match imports. Routes now
  use canonical domain imports and changed only their import block.
- Preserved every route, selector/default, public payload body, CRCON
  service/transport, legacy fallback, opaque player ID and SQL boundary.
- Kept the cohesive 107-line `api/serializers.py` unchanged.
- Final import direction is acyclic: current match -> servers, history ->
  rankings, and history/rankings/product features -> common. No payload module
  imports routes or the package facade.
- Function-body AST comparison performed before removing the monolith showed
  exact copies for retained builders/helpers. The only import adaptation inside
  a function is the required three-dot path from the deeper
  `product_features.py` module to the existing Elo engine.
- Removed three `SAFE_DELETE` private helpers after route, frontend, worker,
  dynamic-entrypoint, test and documentation reference review:
  `_leaderboard_snapshot_items_need_playtime_enrichment`,
  `_load_runtime_leaderboard_items` and `_is_snapshot_stale`. The only test
  reference to the runtime loader asserted it was never called.
- The final extraction audit corrected the initial classification of
  `_recent_match_sort_key`: it has a live history merge caller, so it was
  retained verbatim. No endpoint/payload alias was deleted.
- Updated only focused mocks that had patched monolith implementation globals;
  they now patch the canonical owning module. Public builder imports remain
  compatible.
- Updated `docs/CODE_STRUCTURE.md` and the CRCON-first dependency ledger with
  the final tree, ownership/import rules and canonical legacy-reader paths.

Validation:

- 198 CRCON/current-match/server/history/player/aggregate contract tests: pass.
- 47 historical snapshot/ranking/stats/scoreboard tests: pass; existing SQLite
  `ResourceWarning`s remain non-failing.
- Historical UI and Stats/Ranking integration scripts: pass. The optional live
  HTTP probe skipped cleanly because no backend was running; imported route
  contract checks passed.
- Frontend current-match snapshot tests: 37 pass.
- All frontend JavaScript `node --check`: pass.
- `compileall app tests`: pass.
- `git diff --check`: pass with only repository line-ending warnings.
- Full backend discovery ran 315 tests and reproduced exactly the four TASK-304
  baselines: optional `pytest` missing; two outdated materialized recent-match
  expectations (with Windows SQLite cleanup errors); and runner maintenance
  expecting `ok` instead of `partial`. No new TASK-305 regression was found.

Final assessment:

- `API_PAYLOAD_REFACTOR = GO`
- `PUBLIC_CONTRACT_COMPATIBILITY = GO`
- `LEGACY_WRITER_DISABLE_READINESS = NOT_READY`

## Pre-move payload audit

All public builders were classified before extraction. `none` under frontend
means the route remains public/compatible even though no current browser script
calls it.

| Classification | Public builder | Route / frontend | Canonical service or source selector | Rollback dependency |
| --- | --- | --- | --- | --- |
| COMMUNITY/STATIC | `build_health_payload` | `/health`; landing/stats probes | config/runtime policy | none |
| COMMUNITY/STATIC | `build_community_payload` | `/api/community`; none | static contract | none |
| COMMUNITY/STATIC | `build_trailer_payload` | `/api/trailer`; `main.js` | static contract | none |
| COMMUNITY/STATIC | `build_discord_payload` | `/api/discord`; none | static contract | none |
| SHARED | `build_error_payload` | all route errors | shared response contract | none |
| SERVER | `build_servers_payload` | `/api/servers`; `main.js` | `ServerService`, `HLL_SERVER_LIST_SOURCE` | snapshots/A2S/RCON live fallback |
| LEGACY | `build_server_latest_payload` | `/api/servers/latest`; none | snapshot storage | required |
| LEGACY | `build_server_history_payload` | `/api/servers/history`; none | snapshot storage | required |
| LEGACY | `build_server_detail_history_payload` | `/api/servers/{id}/history`; none | snapshot storage | required |
| CURRENT_MATCH | `build_current_match_payload` | `/api/current-match`; `partida-actual.js` legacy transport | `CurrentMatchService`, `HLL_CURRENT_MATCH_SOURCE` | current AdminLog/RCON summary |
| CURRENT_MATCH | `build_current_match_kill_feed_payload` | `/api/current-match/kills`; legacy transport | CurrentMatchService/log stream, same selector | AdminLog killfeed |
| CURRENT_MATCH | `build_current_match_player_stats_payload` | `/api/current-match/players`; legacy transport | CurrentMatchService, same selector | AdminLog players |
| CURRENT_MATCH | `build_current_match_snapshot_payload` | `/api/current-match/snapshot`; snapshot transport | CurrentMatchService, same selector | none hidden; explicit selector only |
| HISTORY | `build_recent_historical_matches_payload` | `/api/historical/recent-matches`; compatibility | `HistoryService`, `HLL_HISTORICAL_MATCH_SOURCE` | snapshots/materialized matches |
| HISTORY | `build_recent_historical_matches_snapshot_payload` | `/api/historical/snapshots/recent-matches`; `historico*.js` | HistoryService or displayed snapshot by selector | displayed snapshots |
| HISTORY | `build_historical_match_detail_payload` | `/api/historical/matches/detail`; `historico-partida.js` | HistoryService, same selector | historical/materialized detail |
| HISTORY | `build_historical_server_summary_payload` | `/api/historical/server-summary`; none | aggregate runtime policy | displayed summary snapshot |
| RANKING | `build_historical_server_summary_snapshot_payload` | `/api/historical/snapshots/server-summary`; `historico.js` | AggregateService, `HLL_HISTORICAL_AGGREGATE_SOURCE` | displayed summary snapshot |
| PLAYER | `build_stats_player_search_payload` | `/api/stats/players/search`; `stats.js` | PlayerSearchService (`get_players_history`), aggregate selector | legacy player index |
| STATS/PLAYER | `build_stats_player_profile_payload` | `/api/stats/players/{id}`; `stats.js` | AggregateService, aggregate selector | legacy period stats |
| LEGACY/PLAYER | `build_historical_player_profile_payload` | `/api/historical/player-profile`; none | historical storage | required |
| LEGACY/RANKING | `build_weekly_top_kills_payload` | `/api/historical/weekly-top-kills`; none | historical storage/data-source policy | required |
| RANKING | `build_historical_leaderboard_payload` | `/api/historical/leaderboard`; none | legacy read model/data-source policy | required |
| RANKING | `build_weekly_leaderboard_payload` | `/api/historical/weekly-leaderboard`; none | historical leaderboard facade | required |
| RANKING | `build_monthly_leaderboard_payload` | `/api/historical/monthly-leaderboard`; none | historical leaderboard facade | required |
| RANKING | `build_annual_ranking_snapshot_payload` | `/api/stats/rankings/annual`; `stats.js` | AggregateService or annual snapshot, aggregate selector | annual snapshot |
| RANKING | `build_global_ranking_payload` | `/api/ranking`; `ranking.js` | AggregateService or ranking snapshots, aggregate selector | ranking snapshots/runtime fallback |
| RANKING | `build_leaderboard_snapshot_payload` | `/api/historical/snapshots/leaderboard`; `historico.js` | AggregateService or snapshot, aggregate selector | displayed/ranking snapshots |
| RANKING | `build_weekly_leaderboard_snapshot_payload` | weekly snapshot alias; none | leaderboard snapshot facade | same |
| RANKING | `build_monthly_leaderboard_snapshot_payload` | monthly snapshot alias; none | leaderboard snapshot facade | same |
| PRODUCT_FEATURE | `build_monthly_mvp_payload` | `/api/historical/monthly-mvp`; none | legacy/product snapshot | product decision required |
| PRODUCT_FEATURE | `build_monthly_mvp_v2_payload` | `/api/historical/monthly-mvp-v2`; none | legacy/product snapshot | product decision required |
| PRODUCT_FEATURE | `build_player_event_payload` | `/api/historical/player-events`; none | player-event snapshot | product decision required |
| PRODUCT_FEATURE | `build_monthly_mvp_snapshot_payload` | MVP snapshot alias; none | displayed snapshot | product decision required |
| PRODUCT_FEATURE | `build_monthly_mvp_v2_snapshot_payload` | MVP V2 snapshot alias; none | displayed snapshot | product decision required |
| PRODUCT_FEATURE | `build_player_event_snapshot_payload` | player-event snapshot alias; none | displayed snapshot | product decision required |
| PRODUCT_FEATURE | `build_elo_mmr_leaderboard_payload` | `/api/historical/elo-mmr/leaderboard`; none | lazy Elo engine | product decision required |
| PRODUCT_FEATURE | `build_elo_mmr_player_payload` | `/api/historical/elo-mmr/player`; none | lazy Elo engine | product decision required |

Serializer/helper dependencies are `api/serializers.py` for timestamps, opaque
server IDs, metric values and source display; `data_sources.py` for source
metadata; and a planned payload `common.py` for displayed-snapshot metadata and
explicit historical fallback policy. Player IDs remain untouched opaque
strings.

### Move plan

1. Convert `api/payloads.py` into `api/payloads/__init__.py` compatibility
   exports.
2. Extract `static.py`, `servers.py` and `current_match.py`; current match may
   depend on the legacy server facade, never the inverse.
3. Extract `common.py`, `history.py`, `players.py` and `rankings.py`.
4. Isolate undecided MVP/player-event/Elo API contracts in
   `product_features.py`, without relabeling their backend implementation dead.
5. Keep `api/serializers.py` cohesive. Recheck four initial private-helper
   candidates and delete only those whose final reference audit confirms
   `SAFE_DELETE`.

## Alias and compatibility audit

No endpoint or payload alias is `SAFE_DELETE` in TASK-305.

| Surface | Classification | Reason retained |
| --- | --- | --- |
| `payloads/__init__.py` public builder exports | `ACTIVE` | application bootstrap, observer, tests and external Python imports use the stable facade |
| `/api/servers/latest`, `/api/servers/history`, per-server history | `ROLLBACK_REQUIRED` | explicit public snapshot-history contracts remain active |
| `/api/current-match`, `/players`, `/kills` beside `/snapshot` | `ACTIVE` and `ROLLBACK_REQUIRED` | legacy frontend transport and immediate source rollback still use the three compatibility streams |
| weekly/monthly leaderboard wrappers and snapshot aliases | `ACTIVE` and `ROLLBACK_REQUIRED` | routes remain public; historical frontend uses snapshot families |
| historical player-profile alias | `ROLLBACK_REQUIRED` | public route backed by retained legacy storage |
| MVP, MVP V2, player-event and Elo routes/snapshot aliases | `PRODUCT_DECISION_REQUIRED` | active public contracts with no approved product disposition |

The parity observer's two private legacy current-match imports remain explicit
package attributes but are intentionally excluded from public `__all__`.

## Change Budget

Use independently testable extraction batches. Stop rather than alter product
semantics or hide baseline failures.
