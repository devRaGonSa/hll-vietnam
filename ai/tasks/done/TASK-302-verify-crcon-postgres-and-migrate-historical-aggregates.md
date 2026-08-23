---
id: TASK-302
title: Verify CRCON PostgreSQL and migrate historical aggregates read-only
status: done
type: backend
team: Arquitecto de Base de Datos
supporting_teams:
  - Backend Senior
  - Arquitecto Python
roadmap_item: crcon-cutover
priority: high
---

# TASK-302 - Verify CRCON PostgreSQL and migrate historical aggregates read-only

## Goal

Verify the exact CRCON 12.0.1 PostgreSQL read schema against authorized targets, then make server summary, rankings and player-stat aggregate contracts selectable from a bounded read-only CRCON repository while preserving legacy rollback.

## Context

TASK-301 moves only historical match browsing to CRCON REST. The remaining historical UI contracts need cross-match aggregates that must not be reconstructed by crawling REST details. CRCON PostgreSQL is the intended source of truth for those reads, but its exact v12.0.1 schema and target scoping must be verified before local aggregate mappings are implemented.

## Steps

1. Preserve the exact public shapes used by `historico.html`, `ranking.html` and
   `stats.html`: server summary, weekly/monthly leaderboard, global
   weekly/monthly/annual ranking, player search and player profile.
2. Verify the pinned CRCON 12.0.1 source contract at commit
   `17c5880684cc419b27ef2bcca0dc439dfd623eae`: `map_history.game` is integer
   `1=hll`, `2=hllv`; `player_stats.map_id -> map_history.id`;
   `steam_id_64.steam_id_64` is the opaque player ID; and the separate nullable
   `steam_id_64.steam_id` is the only Steam-link input.
3. Probe authorized deployed schema metadata with `SELECT` only. Require the
   exact aggregate columns and relevant indexes. Runtime evidence remains
   `UNVERIFIED_SCHEMA` when no canonical read-only DSN is configured.
4. Extend `CrconReadRepository` with typed server-summary, ranking, exact-player
   lookup and profile aggregate reads. All SQL is allowlisted, parameterized,
   bounded, filters finalized `map_history.end` with half-open windows, and
   always filters `server_number` plus `game`.
5. Count matches with `COUNT(DISTINCT player_stats.map_id)`, use `SUM(kills)` for
   totals and `MAX(kills)` only for a single-match record. Compute ratios in the
   application layer. Never use `player_sessions` as match count.
6. Add a small bounded connection pool with clean shutdown while retaining
   `BEGIN READ ONLY`, `transaction_read_only=on`, connection/statement/lock
   timeouts and a repository API with no arbitrary execute or write method.
7. Add `HistoricalAggregateService` with bounded TTL caches. Cache keys include
   aggregate family, game, selected server numbers, timeframe/window, metric,
   limit/offset and opaque player ID where applicable.
8. Add the single selector
   `HLL_HISTORICAL_AGGREGATE_SOURCE=legacy|crcon`, defaulting to `legacy`.
   CRCON mode has no hidden legacy fallback and returns explicit
   `AVAILABLE`, `UNAVAILABLE`, `UNVERIFIED_SCHEMA` or `PERFORMANCE_BLOCKED`
   source state.
9. Preserve explicit cross-server aggregation only inside one game. Reject
   cross-game aggregation instead of merging HLL and HLLV data. Resolve any
   number of enabled canonical `ServerTarget` entries.
10. Preserve annual rankings as a direct timeframe query because Ranking and
    Stats consume them. Do not add annual snapshot persistence. Do not migrate
    MVP or Elo/MMR in this task: both remain application-owned derived products
    on legacy paths and have no direct CRCON aggregate equivalence.
11. Treat exact opaque-ID search as indexed. Since canonical 12.0.1 has no
    index supporting case-insensitive name search on `player_names.name`, fail
    that access path as `PERFORMANCE_BLOCKED` unless the deployed index probe
    proves a suitable index. Never run an unbounded history/name scan.
12. Validate repository safety, scoping, time windows, metric allowlists, tie
    behavior, bounded pagination/cache/pool, legacy rollback and unchanged
    frontend contracts. Run real aggregate samples only when the existing
    canonical SELECT-only DSN is configured; never discover credentials from
    another source.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/database-architect.md`
- `backend/app/crcon/postgres_repository.py`
- `backend/app/payloads.py`
- `docs/CRCON_12_0_1_CONTRACT_VERIFICATION.md`

## Expected Files to Modify

- `backend/app/config.py`
- `backend/app/crcon/models.py`
- `backend/app/crcon/repository.py`
- `backend/app/crcon/postgres_repository.py`
- `backend/app/crcon/aggregate_service.py`
- `backend/app/payloads.py`
- focused backend tests
- `docs/CRCON_12_0_1_CONTRACT_VERIFICATION.md`
- this task file

## Constraints

- Read-only CRCON PostgreSQL access only; no schema changes, writes, migrations, triggers or application-owned gameplay database.
- Do not crawl `get_map_scoreboard` to build aggregates and do not use direct RCON, GetAdminLog or Redis.
- Preserve TASK-301 REST list/detail, current-match, log-stream and all legacy rollback paths.
- Treat every player ID as opaque. Never infer Steam/EOS from format; links require explicit metadata.
- Support N enabled `ServerTarget` entries and reject data outside the selected target scope.
- Do not deploy or modify production Compose.
- If exact schema evidence is unavailable, stop with documented `INSUFFICIENT_EVIDENCE`; do not guess SQL or column semantics.

## Validation

- Sanitized schema/version evidence is documented per authorized target.
- Every query is parameterized, bounded, read-only and target-scoped.
- Focused repository/service/payload/route/frontend tests pass.
- TASK-293 through TASK-301 focused suites remain green.
- `python -m compileall backend/app backend/tests`, historical UI regression and `git diff --check` pass.
- Real aggregate samples contain no stored player identities in evidence.

## Outcome

Completed locally. Schema-model evidence was verified against the pinned CRCON
12.0.1 source and the aggregate family is selectable through
`HLL_HISTORICAL_AGGREGATE_SOURCE=legacy|crcon`. Legacy remains the default and
there is no hidden fallback in CRCON mode.

No canonical `HLL_CRCON_DATABASE_URL` or `HLL_SERVER_TARGETS` was configured in
the process or local environment file, so deployed schema/data/query-plan
validation is `UNVERIFIED_SCHEMA`. No credentials were discovered elsewhere
and no real SQL was executed.

Implemented:

- typed summary, ranking, exact-ID/index-gated search and profile repository reads;
- finalized-map half-open timeframes with server/game scoping;
- metric allowlist, deterministic dense-rank tie positions and bounded limit/offset;
- small bounded read-only connection pool with cleanup and process shutdown;
- explicit availability/error states and bounded TTL caches;
- public payload/route compatibility for Historical, Ranking and Stats;
- explicit-only external identity links; opaque player IDs are never classified;
- source/index/dependency evidence and product recommendations.

Validation:

- 183 focused TASK-293 through TASK-302/backend contract tests passed;
- 13 dedicated TASK-302 aggregate tests passed within that focused stack;
- historical UI regression passed;
- updated Stats/Ranking regression validation passed;
- JavaScript syntax checks passed;
- `python -m compileall backend/app backend/tests` passed;
- `git diff --check` passed (line-ending warnings only).

The broad unfiltered discovery command is not a clean task gate in this
workspace: it also imports a pytest-only audit without pytest installed and
retains three pre-existing legacy-suite failures (two historical fallback/
temporary-SQLite cases and one maintenance status expectation). The focused
affected and stacked suites are green.

## Dependency and Product-Value Ledger

| Legacy domain | Current consumer | TASK-302 disposition |
| --- | --- | --- |
| Server-summary snapshots | Historical page | Selectable direct CRCON aggregate |
| Weekly/monthly leaderboard snapshots | Historical page | Selectable direct CRCON aggregate |
| Weekly/monthly/annual global ranking snapshots | Ranking and Stats pages | Selectable direct CRCON timeframe query; no new persistence |
| Materialized player search/profile | Stats page | Exact-ID/profile selectable; name search performance-gated |
| Historical match list/detail | Historical page | Already TASK-301; unchanged |
| MVP V1/V2 | Legacy endpoints/derived UI helpers | Deferred; no direct CRCON equivalence |
| Elo/MMR | Legacy endpoints/derived UI helpers | Deferred; do not preserve or delete blindly |
| Workers and application storage | Rollback and unmigrated domains | Retained; no decommission in this task |

No legacy table/job has zero global readers while rollback and the unmigrated
MVP/Elo/player-event domains remain enabled. In CRCON aggregate mode, the
migrated public path no longer reads `displayed_historical_snapshots`,
`ranking_snapshots`, `ranking_snapshot_items`, `player_search_index`,
`player_period_stats`, `rcon_annual_ranking_snapshots` or
`rcon_annual_ranking_snapshot_items`; all remain retained for rollback or other
legacy consumers.

## Final Status

- `CRCON_DB_SCHEMA = UNVERIFIED`
- `CRCON_DB_RUNTIME = UNVERIFIED`
- `SERVER_SUMMARY_CRCON = NO-GO` for deployment; local implementation GO
- `RANKINGS_CRCON = NO-GO` for deployment; local implementation GO
- `PLAYER_STATS_CRCON = NO-GO` for deployment; local profile/exact-ID GO and
  canonical name search `PERFORMANCE_BLOCKED`

Recommended next task: provide an authorized SELECT-only CRCON URL and target
registry, run bounded schema/index/query-plan validation, then disable
duplicated legacy writers/read models behind rollback and prove zero dependency
before deleting any storage. No deployment or commit was performed.

## Change Budget

Split schema verification from any aggregate family whose mapping cannot stay small and independently verifiable. Do not bundle deployment or legacy removal into this task.
