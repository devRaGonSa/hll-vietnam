# Stats Section Functional Plan

## Objective

Define the V1 functional contract for a future `Stats` section where a player can search their profile, review personal historical performance across HLL Vietnam community servers, and understand their weekly and monthly ranking position without implementing backend or frontend yet.

## Current Foundation

- HLL Vietnam historical read paths are RCON-first.
- `backend/app/rcon_historical_leaderboards.py` already defines weekly and monthly leaderboard windows over materialized RCON/AdminLog match stats.
- Current reliable materialized counters for public player-facing V1 are kills, deaths, teamkills and matches considered.
- Public scoreboard data remains fallback or enrichment only; it must not become the normal primary source for this section while RCON coverage exists.

## V1 Scope

The first `Stats` contract covers:

- player search by name or player id
- player detail view for one selected player
- personal totals for a selected timeframe and server scope
- weekly ranking position by kills
- monthly ranking position by kills
- data freshness and source metadata
- annual top 20 preparation through a dedicated snapshot model

V1 should support two server scopes:

- one specific server id
- `all` aggregated across active supported servers

## User Flow

1. User opens the future `Stats` section.
2. User searches by partial player name or exact player id.
3. Backend returns compact search matches ordered by best textual match and recent activity.
4. User selects one player result.
5. Frontend requests the player detail payload for a chosen server scope and timeframe.
6. UI shows core totals, calculated ratios, weekly rank position and monthly rank position.
7. UI may later request annual ranking snapshot data for the selected year without recalculating it on each public request.

## API Contract Direction

### 1. Player search

```http
GET /api/stats/players/search?q=<query>&server_id=<server-or-all>&limit=10
```

Purpose:

- resolve a user-entered name fragment or player id into selectable player records backed by materialized historical data

Query rules:

- `q` is required
- `server_id` is optional and defaults to `all`
- `limit` is optional and defaults to `10`, with a hard cap such as `20`

Response shape:

```json
{
  "status": "ok",
  "data": {
    "query": "rambo",
    "server_id": "all",
    "items": [
      {
        "player_id": "76561198000000000",
        "player_name": "Rambo",
        "matches_considered": 42,
        "last_seen_at": "2026-06-06T21:40:00Z",
        "servers_seen": ["comunidad-hispana-01", "comunidad-hispana-02"]
      }
    ]
  }
}
```

Search result notes:

- `player_id` is the canonical selection key for later requests
- `player_name` is the latest display name known from materialized stats
- `matches_considered` is the aggregated closed-match count in the selected scope
- `servers_seen` is optional and may be omitted when `server_id` is not `all`

### 2. Personal player stats

```http
GET /api/stats/players/{player_id}?server_id=<server-or-all>&timeframe=weekly|monthly|all
```

Purpose:

- return the selected player summary for the chosen scope and timeframe plus ranking position context

Response shape:

```json
{
  "status": "ok",
  "data": {
    "player_id": "76561198000000000",
    "player_name": "Rambo",
    "server_id": "all",
    "timeframe": "monthly",
    "window_start": "2026-06-01T00:00:00Z",
    "window_end": "2026-06-07T18:00:00Z",
    "matches_considered": 12,
    "kills": 356,
    "deaths": 241,
    "teamkills": 4,
    "kd_ratio": 1.48,
    "kills_per_match": 29.67,
    "deaths_per_match": 20.08,
    "weekly_ranking": {
      "metric": "kills",
      "ranking_position": 8,
      "window_kind": "current-week",
      "window_start": "2026-06-02T00:00:00Z",
      "window_end": "2026-06-07T18:00:00Z"
    },
    "monthly_ranking": {
      "metric": "kills",
      "ranking_position": 5,
      "window_kind": "current-month",
      "window_start": "2026-06-01T00:00:00Z",
      "window_end": "2026-06-07T18:00:00Z"
    },
    "source": {
      "primary_source": "rcon",
      "read_model": "rcon-materialized-admin-log-player-stats",
      "generated_at": "2026-06-07T18:02:00Z",
      "source_range_start": "2026-06-01T00:14:00Z",
      "source_range_end": "2026-06-07T17:51:00Z",
      "freshness": "runtime"
    }
  }
}
```

Field rules:

- `timeframe=weekly` returns the player totals within the same weekly window policy used by leaderboard reads
- `timeframe=monthly` returns the player totals within the same monthly window policy used by leaderboard reads
- `timeframe=all` returns all-time totals for the selected scope, but still includes weekly and monthly ranking blocks as separate comparative context
- `kd_ratio`, `kills_per_match` and `deaths_per_match` should be rounded for display-safe payloads

### 3. Annual ranking snapshot

```http
GET /api/stats/rankings/annual?year=<year>&server_id=<server-or-all>&metric=kills
```

Purpose:

- return a precomputed annual top 20 leaderboard snapshot without recalculating the full year on each public request

Response shape:

```json
{
  "status": "ok",
  "data": {
    "year": 2026,
    "server_id": "all",
    "metric": "kills",
    "generated_at": "2027-01-01T01:30:00Z",
    "snapshot_status": "ready",
    "items": [
      {
        "ranking_position": 1,
        "player_id": "76561198000000000",
        "player_name": "Rambo",
        "metric_value": 4210,
        "matches_considered": 148,
        "kills": 4210,
        "deaths": 2950,
        "teamkills": 18,
        "kd_ratio": 1.43
      }
    ]
  }
}
```

V1 annual endpoint notes:

- only `metric=kills` needs to be committed in the first annual design pass
- annual read path should be snapshot-backed, not runtime full-range aggregation
- if a requested year is not generated yet, respond with a controlled empty or pending state, not a slow public recalculation

## Ranking Calculation Rules

### Weekly position

- Use the same weekly window selected by `select_leaderboard_window(... timeframe="weekly")`
- Respect the existing sufficient-sample policy:
  - use current week when the closed-match threshold is met
  - fall back to previous week when the current week sample is insufficient
- Rank by total kills descending
- Break ties by:
  - `matches_considered` descending
  - `player_name` ascending
- Player position should be derived from the same aggregate query family as the public leaderboard to avoid contradictory ordering

### Monthly position

- Use the same monthly window selected by `select_leaderboard_window(... timeframe="monthly")`
- Respect the current rule already present in the read model:
  - from day 1 to day 7, use previous month
  - from day 8 onward, use current month
- Rank by total kills descending with the same tie-break rules used in weekly ranking

### Personal totals

- Use the same RCON materialized match/player stats source as leaderboard calculations
- Only closed matches within the selected scope and selected timeframe window should count
- Do not add support, offense, defense or weapon breakdown fields until they are proven reliable in the RCON materialized model

## Annual Snapshot Persistence Direction

Future implementation should add a dedicated persistence model instead of recomputing annual top 20 on every request.

### Table: `rcon_annual_ranking_snapshots`

Expected columns:

- `id`
- `server_id`
- `year`
- `metric`
- `generated_at`
- `source_range_start`
- `source_range_end`
- `snapshot_status`
- `item_count`
- `generation_policy`
- `notes` nullable

Expected uniqueness:

- unique on `(server_id, year, metric)`

Expected behavior:

- one authoritative snapshot row per year, scope and metric
- regenerated only by an explicit batch job, scheduled maintenance command or year-close workflow

### Table: `rcon_annual_ranking_snapshot_items`

Expected columns:

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

Expected uniqueness:

- unique on `(snapshot_id, ranking_position)`
- unique on `(snapshot_id, player_id)`

Expected behavior:

- store only the top 20 rows for the selected annual snapshot
- preserve display-ready values used by the frontend
- keep enough totals to show a concise annual card without joining additional tables at read time

### Generation policy

- Run after year close or through an explicit maintenance workflow
- Read from materialized RCON historical data, not live RCON calls
- Default scope should support both `all` and individual active servers
- Prefer idempotent replace or upsert semantics for a given `(server_id, year, metric)`
- Store `generated_at` and source range metadata for traceability

## V1 Non-goals

- Elo or MMR reactivation
- Comunidad Hispana #03 reintroduction
- support, combat, offense or defense ranking when not already reliable in materialized RCON stats
- weapon-level breakdowns
- charts, heatmaps or advanced visualizations
- authenticated or private player profiles
- backend endpoint implementation
- database migrations
- frontend page, components or scripts

## Future Extensions After V1

- map-by-map player breakdowns
- server comparison cards per player
- annual ranking filters beyond kills
- profile history charts when a stable event or snapshot series exists
- external links to trusted scoreboard detail when correlation is already validated

## Recommended Follow-up Tasks

- add player search endpoint over materialized RCON player stats
- add personal player stats endpoint with weekly and monthly ranking context
- design and implement annual ranking snapshot schema and generation command
- extend frontend data consumption plan with the `Stats` section integration sequence
- implement the `Stats` frontend section with static-safe fallback behavior
