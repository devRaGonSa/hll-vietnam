# Ranking And Stats Performance Audit

## Scope

Audit date:
- 2026-06-09

Target endpoints:
- `/api/ranking?timeframe=weekly&server_id=all&metric=kills&limit=20`
- `/api/ranking?timeframe=weekly&server_id=all&metric=kd_ratio&limit=20`
- `/api/ranking?timeframe=monthly&server_id=all&metric=kills_per_match&limit=20`
- `/api/ranking?timeframe=annual&year=2026&server_id=all&metric=kills&limit=20`
- `/api/stats/players/search?q=Chi&limit=10`
- `/api/stats/players/3530e19cf8a9dd6a9fada4599592fbf8?timeframe=weekly`

## Environment And Method

- Backend HTTP server was not running on `http://127.0.0.1:8000` during the audit.
- Request timing was measured in-process through `app.routes.resolve_get_payload(...)`.
- SQL timing was measured by instrumenting the SQLite read connections used by:
  - `backend/app/rcon_historical_leaderboards.py`
  - `backend/app/rcon_historical_player_stats.py`
  - `backend/app/rcon_annual_rankings.py`
- `EXPLAIN QUERY PLAN` was obtained successfully from SQLite.
- Storage inspected:
  - `backend/data/hll_vietnam_dev.sqlite3`

Important coverage note:
- The latest materialized match rows for `source_basis="admin-log-match-ended"` end on `2026-05-20T23:21:45.816Z`.
- The weekly/monthly public requests on `2026-06-09` therefore read windows with `0` qualifying matches.
- Measured latency is real for the current dataset, but it understates future production cost because the active public windows are empty.

## Measured Baseline

| Endpoint | Avg request ms | Avg SQL ms | SQL queries | Result |
| --- | ---: | ---: | ---: | --- |
| `/api/ranking` weekly `kills` | 4.045 | 0.882 | 6 | `snapshot_status=ready`, `items=0` |
| `/api/ranking` weekly `kd_ratio` | 3.801 | 0.837 | 6 | `snapshot_status=ready`, `items=0` |
| `/api/ranking` monthly `kills_per_match` | 3.612 | 0.816 | 6 | `snapshot_status=ready`, `items=0` |
| `/api/ranking` annual `kills` | 3.326 | 0.629 | 3 | `snapshot_status=ready`, `items=2` |
| `/api/stats/players/search?q=Chi&limit=10` | 6.731 | 3.593 | 3 | `items=10` |
| `/api/stats/players/{player_id}` weekly | 8.924 | 4.494 | 16 | weekly profile payload |

Slowest endpoint:
- `/api/stats/players/{player_id}` weekly
- Main reason: 16 SQL statements per request, including repeated window-count queries and two ranking subqueries.

## Relevant Table Size And Coverage

Row counts:
- `rcon_materialized_matches`: `58`
- `rcon_match_player_stats`: `3,824`
- `rcon_annual_ranking_snapshots`: `2`
- `rcon_annual_ranking_snapshot_items`: `2`

Rows actually used by runtime ranking/stats:
- `rcon_materialized_matches` with `source_basis="admin-log-match-ended"`: `22`

Observed covered range for runtime ranking/stats:
- first materialized match end/start: `2026-05-19T11:16:10.281Z`
- latest materialized match end/start: `2026-05-20T23:21:45.816Z`

Current public window coverage:
- weekly window `2026-06-01T00:00:00Z` to `2026-06-08T00:00:00Z`: `0` matches
- monthly window `2026-06-01T00:00:00Z` to `2026-06-09T23:59:59Z`: `0` matches

Annual snapshot presence:
- `2026 / all-servers / kills / ready / limit_size=2 / source_matches_count=22`

## Existing Indexes

`rcon_materialized_matches`
- unique `(target_key, match_key)`
- non-unique `(target_key, ended_at, ended_server_time)`

`rcon_match_player_stats`
- unique `(target_key, match_key, player_id)`
- non-unique `(target_key, match_key)`

`rcon_annual_ranking_snapshots`
- unique `(year, server_key, metric)`
- non-unique `(year, server_key, metric)`
- non-unique `(status)`

`rcon_annual_ranking_snapshot_items`
- unique `(snapshot_id, ranking_position)`
- unique `(snapshot_id, player_id)`
- non-unique `(snapshot_id, ranking_position)`
- non-unique `(snapshot_id, player_id)`

## Current Query Shapes

Weekly/monthly ranking runtime path:
- 4x `COUNT(*)` over `rcon_materialized_matches` to choose weekly/monthly windows
- 1x aggregate join from `rcon_match_player_stats` to `rcon_materialized_matches`
- 1x source-range query over `rcon_materialized_matches`

Annual ranking path:
- 1x snapshot lookup in `rcon_annual_ranking_snapshots`
- 1x item count in `rcon_annual_ranking_snapshot_items`
- 1x ordered item read in `rcon_annual_ranking_snapshot_items`

Stats player search path:
- 1x grouped search query joining `rcon_match_player_stats` to `rcon_materialized_matches`
- 1x latest-name lookup for returned `player_id` set
- 1x `servers_seen` lookup for returned `player_id` set

Stats player detail path:
- 12x `COUNT(*)` window-selection queries over `rcon_materialized_matches`
- 1x player aggregate query
- 1x source-range query
- 2x ranking-position subqueries using grouped leaderboard logic

## Execution Plan Findings

SQLite `EXPLAIN QUERY PLAN` showed:

Ranking count queries:
- `SCAN matches`

Weekly/monthly leaderboard aggregate queries:
- `SCAN matches`
- `SEARCH stats USING INDEX idx_rcon_match_player_stats_match (target_key=? AND match_key=?)`
- `USE TEMP B-TREE FOR GROUP BY`
- `USE TEMP B-TREE FOR count(DISTINCT)`
- `USE TEMP B-TREE FOR ORDER BY`

Stats search primary query:
- `SCAN matches`
- `SEARCH stats USING INDEX idx_rcon_match_player_stats_match (target_key=? AND match_key=?)`
- `USE TEMP B-TREE FOR GROUP BY`
- `USE TEMP B-TREE FOR count(DISTINCT)`
- `USE TEMP B-TREE FOR ORDER BY`

Stats player detail aggregate query:
- `SCAN stats`
- `SEARCH matches USING INDEX sqlite_autoindex_rcon_materialized_matches_1 (target_key=? AND match_key=?)`
- `USE TEMP B-TREE FOR count(DISTINCT)`

Stats player detail ranking subquery:
- `SCAN stats USING INDEX sqlite_autoindex_rcon_match_player_stats_1`
- `SEARCH matches USING INDEX sqlite_autoindex_rcon_materialized_matches_1 (target_key=? AND match_key=?)`
- `USE TEMP B-TREE FOR GROUP BY`
- `USE TEMP B-TREE FOR count(DISTINCT)`
- `USE TEMP B-TREE FOR ORDER BY`

Annual snapshot lookup:
- `SEARCH rcon_annual_ranking_snapshots USING INDEX sqlite_autoindex_rcon_annual_ranking_snapshots_1 (year=? AND server_key=? AND metric=?)`

## Root Cause Assessment

Current measured latency is low because the runtime weekly/monthly windows are empty on `2026-06-09`, not because the runtime read path is already efficient at scale.

The most likely root causes for future slowdown are:
- no index that matches `source_basis + time window` on `rcon_materialized_matches`
- repeated public-request window counting against `rcon_materialized_matches`
- grouped leaderboard/search queries that spill to temp B-trees for `GROUP BY`, `COUNT(DISTINCT)` and `ORDER BY`
- no direct `player_id` read index for the stats player-detail aggregate path

The main non-performance operational issue exposed by the audit:
- runtime weekly/monthly ranking currently has stale coverage for the current public window because the latest materialized match data ends on `2026-05-20`, while the requests were evaluated on `2026-06-09`

## Recommendation For TASK-189

Priority indexes justified by the current plans:
- add a time-window read index on `rcon_materialized_matches` keyed by `source_basis` plus the runtime time field used by public reads
- add a scoped time-window index on `rcon_materialized_matches` that also includes `target_key`
- add a direct `player_id` index on `rcon_match_player_stats`

Concrete candidate coverage to evaluate in implementation:
- `rcon_materialized_matches(source_basis, ended_at)`
- `rcon_materialized_matches(source_basis, started_at)`
- `rcon_materialized_matches(target_key, source_basis, ended_at)`
- `rcon_materialized_matches(target_key, source_basis, started_at)`
- `rcon_match_player_stats(player_id)`

Notes:
- `(target_key, match_key)` is already covered and should be preserved.
- annual snapshot item lookup is already covered by `(snapshot_id, ranking_position)` and `(snapshot_id, player_id)`.
- a simple `player_name` B-tree is not likely to materially help the current search query because the query uses `LOWER(...) LIKE '%term%'` with a leading wildcard. If search becomes a real bottleneck later, a normalized-prefix strategy or FTS is more promising than a plain index.

## TASK-189 Applied Indexes

Applied in storage initialization for both SQLite and PostgreSQL:
- `idx_rcon_materialized_matches_source_window_text`
- `idx_rcon_materialized_matches_target_source_window_text`
- `idx_rcon_materialized_matches_external_source_window_text`
- `idx_rcon_match_player_stats_player_id_match`

Not added:
- plain `player_name` index

Reason:
- the current search query uses `LOWER(player_name) LIKE '%term%'`, so a simple B-tree on `player_name` is not expected to materially help the current search shape

## TASK-189 Post-Index Check

Observed plan change:
- weekly count query now uses `SEARCH matches USING COVERING INDEX idx_rcon_materialized_matches_source_window_text (source_basis=? AND <expr>>? AND <expr><?)`
- stats player-detail aggregate now uses:
  - `SEARCH matches USING INDEX idx_rcon_materialized_matches_source_window_text (...)`
  - `SEARCH stats USING INDEX sqlite_autoindex_rcon_match_player_stats_1 (target_key=? AND match_key=? AND player_id=?)`

Before/after timing probe:
- `/api/stats/players/{player_id}` weekly
  - before: request `8.924 ms`, SQL `4.494 ms`
  - after: request `4.300 ms`, SQL `1.043 ms`
- `/api/ranking` weekly `kills`
  - before: request `4.045 ms`, SQL `0.882 ms`
  - after: request `4.724 ms`, SQL `0.881 ms`
  - interpretation: no meaningful change in this dataset because the current public weekly window on `2026-06-09` is empty and the table is still small

Residual gap after indexes:
- weekly/monthly public ranking still performs repeated runtime counting and grouped aggregation per request
- snapshots remain the correct next step for predictable public ranking latency

## Recommendation For TASK-190

Weekly/monthly public ranking should move to snapshot-backed reads for the same reason annual ranking is already cheap:
- runtime ranking currently performs repeated window counting and grouped aggregation on every public request
- the empty-window result on `2026-06-09` hides that structural cost
- snapshot-backed weekly/monthly reads would make public ranking latency predictable and remove repeated runtime recomputation from the request path

Recommended transition policy:
- serve weekly/monthly ranking from snapshots when `snapshot_status=ready`
- keep runtime fallback controlled and optional during migration
- do not recalculate heavy weekly/monthly aggregates by default on every public request

## Commands Executed

Repository and task context:
- `Get-Content AGENTS.md`
- `Get-Content ai/architecture-index.md`
- `Get-Content ai/repo-context.md`
- `Get-Content ai/tasks/pending/TASK-188-audit-ranking-and-stats-query-performance.md`
- `Get-Content ai/orchestrator/backend-senior.md`
- `Get-Content ai/orchestrator/database-architect.md`

Relevant code inspection:
- `Get-Content backend/app/routes.py`
- `Get-Content backend/app/payloads.py`
- `Get-Content backend/app/rcon_historical_leaderboards.py`
- `Get-Content backend/app/rcon_historical_player_stats.py`
- `Get-Content backend/app/rcon_annual_rankings.py`
- `Get-Content backend/app/config.py`
- `Get-Content backend/app/postgres_rcon_storage.py`
- `Get-Content backend/app/sqlite_utils.py`
- `Get-Content docs/global-ranking-page-plan.md`
- `Get-Content scripts/run-stats-validation.ps1`

Environment inspection:
- `Get-ChildItem backend/data -Force`
- `try { (Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 http://127.0.0.1:8000/health).Content } catch { $_.Exception.Message }`

Measurement and database inspection:
- inline Python against `backend/data/hll_vietnam_dev.sqlite3` for endpoint timing, SQL timing, row counts, `PRAGMA index_list`, `PRAGMA index_info` and `EXPLAIN QUERY PLAN`

## Limitations

- No live HTTP timing was captured because the backend process was not running locally during the audit.
- The current runtime weekly/monthly windows were empty on `2026-06-09`, so the measured latency is a lower bound, not a stressed production baseline.
- The database is large on disk because the repository stores many other domains, but the materialized ranking/stats tables used by these endpoints are currently small.
