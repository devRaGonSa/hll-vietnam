# Global Ranking Page Plan

## Objective

Define the V1 functional contract for a dedicated `Ranking` page that exposes public top lists across HLL Vietnam community servers without merging this flow into `Stats`.

## Why Ranking Is Separate From Stats

`Stats` and `Ranking` solve different user jobs:

- `Stats` is player-centric: search one player, open one profile, inspect personal performance.
- `Ranking` is leaderboard-centric: open a public table, switch filters, compare top players.

They can safely share:

- the same sober tactical visual system already used by `stats.html` and `historico.html`
- the same backend health/offline messaging pattern
- the same table/card rendering conventions for loading, empty and error states

They must remain separate in navigation and contracts:

- `Stats` keeps player search and personal summary endpoints.
- `Ranking` gets its own page and dedicated ranking endpoint.
- `Ranking` may link to `Stats` for player lookup, but it does not embed the player search workflow as a primary interaction.

## Current Foundation

- Weekly and monthly historical leaderboard reads already exist in `backend/app/rcon_historical_leaderboards.py`.
- Annual ranking reads already exist through snapshot storage in `backend/app/rcon_annual_rankings.py`.
- Historical ranking remains RCON-first.
- Public scoreboard remains fallback or enrichment only and must not become the primary read path while RCON coverage exists.

## V1 Scope

The first Ranking page supports:

- public top-player lists
- timeframe filter: `weekly`, `monthly`, `annual`
- server scope filter: `all`, `comunidad-hispana-01`, `comunidad-hispana-02`
- metric filter: V1 committed to `kills`
- limit filter: default `20`, with smaller values allowed
- filter changes without manual page reload where feasible
- clear differentiation between `ready`, `missing`, `empty`, `offline` and request-error states

## V1 Non-goals

- Elo/MMR
- authentication
- private or expanded player profiles
- advanced charts
- weapon or map breakdowns
- large schema changes
- annual recalculation on public request
- reintroducing Comunidad Hispana #03

## User Flow

1. User opens `Ranking`.
2. Page checks backend availability.
3. User chooses timeframe.
4. User chooses server scope.
5. User chooses metric.
6. User chooses limit if needed.
7. Frontend requests ranking data and updates the list in place.
8. User can switch filters again without manual reload.
9. If the user wants one-player analysis, the page offers a small link to `Stats`.

## Data Source Policy

### Weekly and monthly

- Source: materialized RCON/AdminLog leaderboard read model.
- Reader: existing weekly/monthly selection logic in `select_leaderboard_window(...)`.
- Ordering: metric desc, `matches_considered` desc, `player_name` asc.
- V1 metric commitment: `kills`.

### Annual

- Source: persisted annual ranking snapshots.
- Reader: existing annual snapshot loader.
- No annual recomputation during public requests.
- Missing annual data must surface as a controlled `snapshot_status="missing"` state.

## API Contract Direction

### Dedicated Ranking endpoint

```http
GET /api/ranking?timeframe=weekly|monthly|annual&server_id=<server-or-all>&metric=kills&limit=20&year=<year-when-annual>
```

Purpose:

- give Ranking its own public contract without changing Stats endpoints or mixing player-profile concerns into ranking reads

Query rules:

- `timeframe` is optional and defaults to `weekly`
- `server_id` is optional and defaults to `all`
- `metric` is optional and defaults to `kills`
- `limit` is optional and defaults to `20`
- `year` is required only when `timeframe=annual`

Validation rules:

- allowed `timeframe`: `weekly`, `monthly`, `annual`
- V1 allowed `metric`: `kills`
- allowed `limit`: `1..100`
- `year` must be a positive integer when annual is requested
- annual requests ignore weekly/monthly runtime window policy and read snapshots only

## Response Contract

```json
{
  "status": "ok",
  "data": {
    "page_kind": "global-ranking",
    "timeframe": "monthly",
    "server_id": "all",
    "metric": "kills",
    "limit": 20,
    "requested_limit": 20,
    "window_start": "2026-06-01T00:00:00Z",
    "window_end": "2026-06-08T18:00:00Z",
    "window_kind": "current-month",
    "window_label": "Mes actual",
    "source": {
      "primary_source": "rcon",
      "read_model": "rcon-materialized-admin-log-leaderboard",
      "generated_at": "2026-06-08T18:00:00Z",
      "freshness": "runtime"
    },
    "snapshot_status": "ready",
    "items": [
      {
        "ranking_position": 1,
        "player_id": "76561198000000000",
        "player_name": "Rambo",
        "metric_value": 421,
        "matches_considered": 14,
        "kills": 421,
        "deaths": 280,
        "teamkills": 3,
        "kd_ratio": 1.5
      }
    ]
  }
}
```

## Field Rules

Common top-level fields:

- `timeframe`: `weekly`, `monthly`, `annual`
- `server_id`: `all` or one supported active server id
- `metric`: `kills` in V1
- `limit`: effective served limit
- `requested_limit`: requested client limit
- `snapshot_status`: always present for frontend state handling
- `items`: always an array

Required item fields:

- `ranking_position`
- `player_id`
- `player_name`
- `metric_value`
- `matches_considered`
- `kills`
- `deaths`
- `teamkills`
- `kd_ratio`

Weekly/monthly-only metadata:

- `window_start`
- `window_end`
- `window_kind`
- `window_label`
- `selection_reason`

Annual-only metadata:

- `year`
- `generated_at`
- `snapshot_limit`
- `effective_limit`
- `item_count`

## Timeframe-specific expectations

### Weekly

- Use the same weekly fallback rule already defined by the leaderboard read model.
- If current-week sample is insufficient, backend may serve previous-week data.
- Frontend must not reinterpret the window; it should display returned window metadata.

### Monthly

- Use the same current-month vs previous-month rule already defined by the leaderboard read model.
- Frontend must display the returned monthly window metadata exactly as served.

### Annual

- Read only from annual snapshots.
- `snapshot_status="ready"` with `items=[]` is a valid empty-ready state.
- `snapshot_status="missing"` is not a backend crash and must be rendered distinctly.

## UI State Contract

The Ranking page must support these states explicitly:

- `loading`: request in flight
- `backend offline`: `/health` unavailable or ranking request unreachable
- `no data`: successful response with `items=[]` in weekly/monthly
- `annual snapshot missing`: annual response with `snapshot_status="missing"`
- `unsupported metric`: client requested unsupported metric or backend returns 400 metric validation error
- `controlled error`: valid HTTP response with request validation error or unexpected backend failure

Expected rendering behavior:

- loading keeps previous table hidden or visually muted
- backend offline shows a clear retry-safe message
- no data keeps filters visible and explains that there are no rows for the active scope
- annual snapshot missing explains that the annual snapshot has not been generated yet
- unsupported metric does not silently downgrade to another metric
- controlled error does not break page navigation or filter controls

## Backend Behavior Requirements

- Preserve existing Stats endpoint compatibility.
- Do not expose public-scoreboard as the normal primary source for Ranking.
- Do not expand annual generation logic inside request handling.
- Keep server scope limited to active supported scopes: `all`, `comunidad-hispana-01`, `comunidad-hispana-02`.
- Do not surface Comunidad Hispana #03 in defaults, options or backend read scope.

## Frontend Integration Guidance

Recommended page split:

- `stats.html`: personal lookup and personal ranking context
- `ranking.html`: public top lists

Recommended safe reuse:

- backend availability chip pattern from `stats.js`
- existing tactical panel and card styling from `styles.css`
- simple select/button driven filtering similar to `historico.html`

Recommended minimal cross-links:

- `Ranking` page links to `Stats` with copy like "Buscar jugador"
- `Stats` page may link back to `Ranking` with copy like "Ver ranking global"

## Follow-up Task Suggestions

- Implement `GET /api/ranking` by adapting existing weekly/monthly leaderboard reads and annual snapshot reads.
- Build `frontend/ranking.html` and `frontend/assets/js/ranking.js` against this contract.
- Add a small regression script for Ranking endpoint and frontend state validation.
