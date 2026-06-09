# Player Search Read Model

## Objective

Define the first dedicated read model for player search so `/api/stats/players/search` does not aggregate large RCON historical tables on every public request.

## Table

Primary table:

- `player_search_index`

Operational scope:

- PostgreSQL is the default operational store
- SQLite remains available only as explicit local compatibility for validation and isolated maintenance runs

Read-model nature:

- this table is regenerable
- it is not the canonical source of truth
- canonical historical data remains in `rcon_materialized_matches` and `rcon_match_player_stats`

## Stored Fields

Each row stores one player projection for one public search scope:

- `server_id`
- `player_id`
- `player_name`
- `normalized_player_name`
- `first_seen_at`
- `last_seen_at`
- `servers_seen`
- `matches_current_year`
- `kills_current_year`
- `deaths_current_year`
- `teamkills_current_year`
- `updated_at`

Current scope rows:

- `all-servers`
- `comunidad-hispana-01`
- `comunidad-hispana-02`

Why `server_id` exists:

- the public search endpoint already supports `server_id`
- keeping one row per scope preserves the existing frontend contract without recalculating large runtime aggregates for server-filtered searches

## Refresh Command

Manual command:

```bash
python -m app.rcon_historical_player_stats refresh-player-search-index
```

SQLite-only local override:

```bash
python -m app.rcon_historical_player_stats refresh-player-search-index --sqlite-path backend/data/hll_vietnam_dev.sqlite3
```

Refresh policy:

- rebuild from materialized RCON/AdminLog tables
- replace rows scope by scope
- aggregate only the current UTC year
- keep the latest current-year player name
- store accent-insensitive normalized names in Python

Automatic runner refresh:

- `backend/app/historical_runner.py` refreshes `player_search_index` automatically
- it inherits the periodic cadence of the historical runner via `HLL_HISTORICAL_REFRESH_INTERVAL_SECONDS`
- the runner executes this step after the existing RCON ingestion/materialization cycle
- the runner still attempts this step even if the legacy historical snapshot block fails earlier in the same cycle
- the overall runner result may end as `partial` when that legacy block fails but operational PostgreSQL refreshes continue
- the runner keeps runtime fallback preserved for the public endpoint

Emergency manual command:

```bash
python -m app.rcon_historical_player_stats refresh-player-search-index
```

## Public Read Path

Priority for `/api/stats/players/search`:

1. use `player_search_index` when the requested scope has rows
2. return read-model results directly, including empty query results when the index is populated but the query does not match
3. fall back to runtime aggregation only when:
   - the read model table is unavailable
   - the requested scope has no rows yet
   - a controlled read error occurs

Returned compatibility:

- the payload still returns `player_id`
- the payload still returns `player_name`
- the payload still returns `matches_considered`
- the payload still returns `last_seen_at`
- the payload still returns `servers_seen`

`matches_considered` remains compatible by mapping from `matches_current_year`.

## PostgreSQL Notes

No extra PostgreSQL extensions are required.

Specifically:

- no `pg_trgm`
- no custom text-search extension

Search tolerance is implemented with:

- normalized lowercase names
- accent stripping in Python
- indexed scope + normalized-name reads
- runtime fallback preserved as a safety net

## Current Limitations

- this read model is focused on player search only, not personal profile totals
- counts are current-year only by design
- historical players with no activity in the current UTC year are not intentionally prioritized in this first model
- the runner refreshes all supported public scopes on each cycle even when a manual runner execution is limited with `--server`
- profile and personal stats use their own dedicated read model and still preserve runtime fallback when needed

## Production Validation

Recommended checks after refresh:

- confirm the historical runner output reports either `status=ok` or `status=partial`
- confirm `historical_snapshot_result`, `player_search_index_result`, `player_period_stats_result` and `ranking_snapshot_result` are present in the cycle payload
- if the cycle is `partial`, inspect `historical_snapshot_result.error_type`, `historical_snapshot_result.error` and the runner logs for the legacy failure
- confirm `player_search_index.updated_at` advanced even when a legacy snapshot error was reported
- confirm the historical runner output reports `player_search_index_result`
- if an emergency rebuild is needed, run `python -m app.rcon_historical_player_stats refresh-player-search-index`
- confirm the command reports rows for `all-servers`, `comunidad-hispana-01` and `comunidad-hispana-02`
- call `/api/stats/players/search?q=<known-player>&limit=5`
- verify response metadata reports `read_model=player-search-index`
- verify fallback metadata only appears when the read model is empty or unavailable
