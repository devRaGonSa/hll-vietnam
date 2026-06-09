# Ranking Snapshot Read Model Plan

## Objective

Define a snapshot-backed read model for weekly and monthly public ranking so `GET /api/ranking` does not depend on runtime aggregation over materialized RCON match stats on every request.

The design follows the same philosophy as the current annual ranking snapshot path:
- generate outside the public request path
- serve stable snapshot rows through a small read model
- expose clear metadata for `ready`, `missing` and controlled fallback states

## Scope

Impacted public endpoint:
- `GET /api/ranking?timeframe=weekly|monthly|annual&server_id=<scope>&metric=<metric>&limit=<n>&year=<year-when-annual>`

Primary target of this plan:
- weekly ranking snapshots
- monthly ranking snapshots

Compatibility target:
- the model must also represent annual snapshots so the repository can converge on one ranking snapshot vocabulary over time
- `TASK-191` should keep annual requests on the existing annual snapshot path until migration is explicitly implemented

## Why This Is Needed

`TASK-188` showed:
- weekly/monthly ranking still performs repeated window counting and grouped aggregation at request time
- stats/ranking runtime reads depend on `rcon_materialized_matches` and `rcon_match_player_stats`
- the empty June 2026 window hides the structural cost, but the query plans still show scans and temp B-trees

`TASK-189` reduced some scan risk with indexes, but it did not remove the core public-request recomputation pattern.

## Proposed Tables

### `ranking_snapshots`

Purpose:
- one snapshot header per `(timeframe, server_id, metric, window_start, window_end)`

Proposed fields:
- `id`
- `timeframe`
  - allowed values: `weekly`, `monthly`, `annual`
- `server_id`
  - `all-servers`, `comunidad-hispana-01`, `comunidad-hispana-02`
- `metric`
  - V1.1 weekly/monthly: `kills`, `deaths`, `teamkills`, `matches_considered`, `kd_ratio`, `kills_per_match`
  - annual: keep `kills` as the required supported metric until annual expansion is explicitly implemented
- `window_start`
- `window_end`
- `generated_at`
- `source`
  - expected current value: `rcon-materialized-admin-log`
- `snapshot_status`
  - expected values: `ready`, `building`, `failed`
- `item_count`
- `limit_size`
- `source_matches_count`
- `freshness`
  - example values: `fresh`, `stale`
- `error_message`
  - nullable, operational only

Key rules:
- unique key on `(timeframe, server_id, metric, window_start, window_end)`
- keep only one `ready` snapshot per exact window and metric scope
- `item_count` reflects stored rows, not the request limit
- `limit_size` records how many positions were generated, for example top 20

### `ranking_snapshot_items`

Purpose:
- ordered player rows for one ranking snapshot

Proposed fields:
- `id`
- `snapshot_id`
- `ranking_position`
- `player_id`
- `player_name`
- `metric_value`
- `matches_considered`
- `kills`
- `deaths`
- `teamkills`
- `kd_ratio`
- `kills_per_match`

Key rules:
- unique key on `(snapshot_id, ranking_position)`
- unique key on `(snapshot_id, player_id)`
- all item rows must carry the common display totals even when the requested metric is different

## Snapshot Window Rules

### Weekly

Window logic:
- preserve the current weekly selection policy already exposed by `select_leaderboard_window(...)`
- snapshot window is whichever week the public runtime policy would have served:
  - `current-week` when the current week has sufficient closed matches
  - otherwise `previous-week`

Stored metadata:
- `timeframe=weekly`
- `window_start`
- `window_end`
- `snapshot_status`
- `generated_at`
- `source='rcon-materialized-admin-log'`

### Monthly

Window logic:
- preserve the current monthly selection policy already exposed by `select_leaderboard_window(...)`
- snapshot window is:
  - `previous-month` until day 7 inclusive
  - `current-month` after day 7

Stored metadata:
- `timeframe=monthly`
- `window_start`
- `window_end`
- `snapshot_status`
- `generated_at`
- `source='rcon-materialized-admin-log'`

### Annual

Window logic:
- `year-01-01T00:00:00Z` to `(year+1)-01-01T00:00:00Z`

Transition note:
- the new table design supports annual snapshots
- `TASK-191` should keep annual requests on the existing `rcon_annual_ranking_snapshots` path until a dedicated migration task consolidates storage

## Refresh Policy

Current windows:
- weekly current: refresh every `5` to `15` minutes
- monthly current: refresh every `15` to `30` minutes
- annual current: manual or daily

Closed windows:
- previous week: treated as closed and stable
- previous month: treated as closed and stable
- annual closed windows: treated as stable after generation

Operational rules:
- generation happens outside the public request path
- one refresh job should upsert the header row and replace the corresponding item set atomically
- if refresh fails, keep the last `ready` snapshot until a new `ready` snapshot is produced

## Public Fallback Policy

Public read priority:
1. serve snapshot when a matching `ready` snapshot exists
2. if no matching snapshot exists:
   - return controlled `snapshot_status='missing'`
   - or use runtime fallback only when configuration explicitly enables it
3. never recalculate by default on every public request

Required policy fields in API response:
- `source`
- `snapshot_status`
- `generated_at`
- `freshness`
- `fallback_used`
- `window_start`
- `window_end`

Expected meanings:
- `source='ranking-snapshot'` when serving stored weekly/monthly snapshot rows
- `source='rcon-materialized-runtime-fallback'` only when configuration allows fallback and snapshot is missing
- `snapshot_status='ready'` when snapshot rows were served
- `snapshot_status='missing'` when no snapshot exists for the requested window and runtime fallback is disabled

## Expected API Metadata

Weekly/monthly responses should expose:
- `page_kind`
- `timeframe`
- `server_id`
- `metric`
- `limit`
- `requested_limit`
- `window_start`
- `window_end`
- `window_kind`
- `window_label`
- `snapshot_status`
- `generated_at`
- `freshness`
- `fallback_used`
- `source`
- `items`

Snapshot item contract:
- `ranking_position`
- `player_id`
- `player_name`
- `metric_value`
- `matches_considered`
- `kills`
- `deaths`
- `teamkills`
- `kd_ratio`
- `kills_per_match`

## Generation Source

Authoritative source for weekly/monthly/annual ranking snapshots:
- `rcon_materialized_matches`
- `rcon_match_player_stats`

Source filter:
- `matches.source_basis = 'admin-log-match-ended'`

Generation logic:
- reuse the same metric formulas and tie-break ordering already documented for `Ranking`
- do not use public scoreboard as the primary ranking source
- do not reintroduce Comunidad Hispana #03

## Transition Notes For TASK-191

Implementation order:
1. add snapshot lookup helpers for weekly/monthly
2. make `/api/ranking` weekly/monthly try snapshot lookup first
3. keep annual on the current annual snapshot loader
4. add controlled runtime fallback behind configuration
5. return explicit metadata for `ready`, `missing` and fallback cases

Expected runtime behavior in `TASK-191`:
- weekly/monthly:
  - snapshot first
  - runtime fallback only when snapshot is missing and fallback is enabled
  - controlled missing when snapshot is missing and fallback is disabled
- annual:
  - keep current snapshot behavior unchanged

Operational note after `TASK-191`:
- snapshot tables are initialized automatically on first ranking access
- snapshot rows are not generated automatically yet
- runtime fallback remains enabled by default for transition through `HLL_BACKEND_RANKING_RUNTIME_FALLBACK_ENABLED=true`
- operators can force controlled missing behavior by setting `HLL_BACKEND_RANKING_RUNTIME_FALLBACK_ENABLED=false`

## Manual Generation Workflow

Manual generator entrypoint:

```bash
python -m app.rcon_historical_leaderboards generate-ranking-snapshot --timeframe weekly --server-key all --metric kills --limit 20
```

Bulk refresh entrypoint:

```bash
python -m app.rcon_historical_leaderboards refresh-ranking-snapshots --limit 30
```

Operational default:
- when `HLL_BACKEND_DATABASE_URL` is configured, the CLI uses PostgreSQL by default
- SQLite is no longer the default operational target for snapshot generation
- local SQLite generation remains available only through an explicit override such as:

```bash
python -m app.rcon_historical_leaderboards generate-ranking-snapshot --timeframe weekly --server-key all --metric kills --limit 20 --sqlite-path backend/data/hll_vietnam_dev.sqlite3
```

Docker form:

```bash
docker compose exec backend python -m app.rcon_historical_leaderboards generate-ranking-snapshot --timeframe weekly --server-key all --metric kills --limit 20
```

Bulk Docker form:

```bash
docker compose exec backend python -m app.rcon_historical_leaderboards refresh-ranking-snapshots --limit 30
```

Operational expectation:
- the recommended Docker command should generate weekly/monthly snapshots in PostgreSQL, matching the `/api/ranking` production read path

Supported manual parameters:
- `timeframe`: `weekly`, `monthly`
- `server-key`: `all`, `all-servers`, `comunidad-hispana-01`, `comunidad-hispana-02`
- `metric`: `kills`, `deaths`, `teamkills`, `matches_considered`, `kd_ratio`, `kills_per_match`
- `limit`: positive integer, normally `20`

Current implementation note:
- `generate-ranking-snapshot` remains unitary per command invocation for explicit manual control
- `refresh-ranking-snapshots --limit 30` generates the full weekly/monthly public matrix in one run
- the periodic historical runner in `backend/app/historical_runner.py` invokes that bulk refresh as part of the normal backend refresh cycle
- current cycle order is:
  - existing RCON ingestion/materialization cycle
  - legacy `historical_snapshot_result`
  - `player_search_index`
  - `player_period_stats`
  - `ranking_snapshots`
- per-combination failures should be reported without aborting the entire matrix refresh
- a legacy historical snapshot failure can leave the full cycle in `partial`, but the runner should still attempt the operational PostgreSQL refreshes and report `ranking_snapshot_result`

## Recommended Combinations

Minimum production matrix for parity with the public Ranking filters:
- weekly + `all-servers` + all six supported metrics
- weekly + `comunidad-hispana-01` + all six supported metrics
- weekly + `comunidad-hispana-02` + all six supported metrics
- monthly + `all-servers` + all six supported metrics
- monthly + `comunidad-hispana-01` + all six supported metrics
- monthly + `comunidad-hispana-02` + all six supported metrics

That matrix requires `36` snapshot generations for each refresh cycle.

Operational default limit:
- generate each combination with `limit=30`
- that stored `limit_size=30` covers the current UI request limits `10`, `20` and `30`

## Suggested Frequency

Suggested operator cadence:
- weekly current window: regenerate every `5` to `15` minutes while the active week is changing
- monthly current window: regenerate every `15` to `30` minutes while the active month is changing
- previous week and previous month windows: regenerate once after closure or after any historical backfill that changes source coverage

Operational guidance:
- regenerate after materialized RCON/AdminLog data grows
- regenerate after manual backfill
- regenerate after metric SQL changes that affect ranking totals or ordering
- when using the periodic backend runner, keep ranking refresh attached to the same recurring cycle rather than a separate scheduler unless operational load proves otherwise
- the runner inherits its cadence from `HLL_HISTORICAL_REFRESH_INTERVAL_SECONDS`
- if the runner reports `partial`, review `historical_snapshot_result` and backend logs before assuming `ranking_snapshots` was skipped
- confirm `ranking_snapshots.generated_at` or the latest `updated_at`/window timestamp advanced in PostgreSQL even when a legacy snapshot error was logged
- fallback runtime remains preserved for `/api/ranking` if a requested snapshot is missing or unavailable

## Ready Vs Fallback

Expected API result after successful generation for an exact requested combination:
- `snapshot_status=ready`
- `fallback_used=false`
- `source.read_model=ranking-snapshot`

Expected API result when the requested combination has not been generated yet and fallback remains enabled:
- `snapshot_status=missing`
- `fallback_used=true`
- `freshness=runtime`

Expected API result when the requested combination has not been generated and fallback is disabled:
- `snapshot_status=missing`
- `fallback_used=false`
- `items=[]`

## Out Of Scope

- backend implementation of the snapshot generator
- migrations
- frontend changes
- annual storage migration from the legacy annual snapshot tables
- Elo/MMR
- public scoreboard as ranking primary source
