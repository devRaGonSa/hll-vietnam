# Player Period Stats Read Model

## Objective

Define the PostgreSQL read model that backs personal player stats by period so `/api/stats/players/{player_id}` does not aggregate large RCON historical tables on every public request when a regenerated read model is available.

## Table

Primary table:

- `player_period_stats`

Operational scope:

- PostgreSQL is the default operational store
- SQLite remains available only as explicit local compatibility for validation and isolated maintenance runs

Read-model nature:

- this table is regenerable
- it is not the canonical source of truth
- canonical historical data remains in `rcon_materialized_matches` and `rcon_match_player_stats`

## Stored Fields

Each row stores one player projection for one public scope and one active period window:

- `period_type`
- `window_kind`
- `period_start`
- `period_end`
- `server_id`
- `player_id`
- `player_name`
- `matches_considered`
- `kills`
- `deaths`
- `teamkills`
- `ranking_position`
- `kd_ratio`
- `kills_per_match`
- `first_seen_at`
- `last_seen_at`
- `updated_at`

Current period types:

- `weekly`
- `monthly`
- `yearly`

Current scope rows:

- `all-servers`
- `comunidad-hispana-01`
- `comunidad-hispana-02`

Why `server_id` exists:

- the public profile endpoint already supports `server_id`
- keeping one row per scope preserves the current frontend contract without recalculating large runtime aggregates for server-filtered profiles

Why `window_kind` exists:

- the profile payload already exposes weekly and monthly ranking context
- persisting `current-week`, `previous-week`, `current-month` or `previous-month` keeps the public contract stable without recomputing that selection on each request

## Period Windows

Window selection follows the same policy already used by ranking/stats reads where applicable:

- `weekly`
  - uses `select_leaderboard_window(... timeframe="weekly")`
  - current week is used only when the closed-match threshold is sufficient
  - otherwise the read model stores the previous week window
- `monthly`
  - uses `select_leaderboard_window(... timeframe="monthly")`
  - from day 1 to day 7 it stores the previous month
  - from day 8 onward it stores the current month
- `yearly`
  - stores the current UTC year from January 1 until refresh time
  - it is prepared internally even if the current public profile contract still requests weekly/monthly only

## Refresh Command

Manual command:

```bash
python -m app.rcon_historical_player_stats refresh-player-period-stats
```

SQLite-only local override:

```bash
python -m app.rcon_historical_player_stats refresh-player-period-stats --sqlite-path backend/data/hll_vietnam_dev.sqlite3
```

Refresh policy:

- rebuild from materialized RCON/AdminLog tables
- replace rows scope by scope and period by period
- keep the latest player name seen inside the selected period window
- persist ranking position by kills inside each generated period window

## Public Read Path

Priority for `/api/stats/players/{player_id}`:

1. use `player_period_stats` when the requested scope has generated rows for the required periods
2. serve the requested weekly/monthly totals and ranking context directly from the read model
3. fall back to runtime aggregation only when:
   - the read model table is unavailable
   - the requested scope has no generated rows yet
   - the player has no generated row for one required period
   - a controlled read error occurs

Returned compatibility:

- the payload still returns `player_id`
- the payload still returns `player_name`
- the payload still returns `matches_considered`
- the payload still returns `kills`
- the payload still returns `deaths`
- the payload still returns `teamkills`
- the payload still returns `kd_ratio`
- the payload still returns `kills_per_match`
- the payload still returns weekly/monthly ranking blocks

Source metadata:

- read-model path reports `source.read_model = "player-period-stats"`
- read-model path reports `source.fallback_used = false`
- runtime fallback keeps the same public contract and reports `source.fallback_used = true`

## PostgreSQL Notes

No extra PostgreSQL extensions are required.

Indexes kept for the public profile flow:

- `(player_id, period_type, server_id)`
- `(server_id, period_type)`
- `last_seen_at`
- `updated_at`

## Production Validation

Recommended checks after refresh:

- run `python -m app.rcon_historical_player_stats refresh-player-period-stats`
- confirm the command reports rows for:
  - `all-servers`
  - `comunidad-hispana-01`
  - `comunidad-hispana-02`
  - `weekly`
  - `monthly`
  - `yearly`
- call `/api/stats/players/<known-player>?timeframe=weekly`
- verify response metadata reports `read_model=player-period-stats`
- verify response metadata reports `fallback_used=false` when the read model is populated
- verify fallback metadata appears only when the read model is empty, incomplete or unavailable

## Current Limitations

- periodic refresh is still manual; there is no scheduled operational refresh yet
- the public route still exposes weekly/monthly only; yearly is prepared internally for future use
- runtime fallback remains necessary until production refresh automation is in place
- canonical historical truth remains in materialized RCON tables, not in the read model
