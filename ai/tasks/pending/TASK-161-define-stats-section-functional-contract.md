---
id: TASK-161
title: Define Stats section functional contract
status: pending
type: documentation
team: Analista
supporting_teams:
  - PM
  - Backend Senior
  - Frontend Senior
  - Arquitecto de Base de Datos
  - Experto en interfaz
roadmap_item: stats-section
priority: high
---

# TASK-161 - Define Stats section functional contract

## Goal

Define the functional and technical contract for a new `Stats` section where players can search themselves, view their personal statistics across the community servers, and understand their weekly and monthly ranking position.

This task must also prepare the future annual ranking design, including a dedicated annual top 20 snapshot model, without implementing backend endpoints, database migrations or frontend UI yet.

## Context

HLL Vietnam already has an RCON-first historical architecture and materialized match/player statistics. The existing leaderboard read model in `backend/app/rcon_historical_leaderboards.py` supports weekly and monthly leaderboard payloads over RCON/AdminLog materialized tables.

The next product step is to convert this foundation into a player-facing `Stats` section with a clear V1 scope:

- player search
- personal player statistics
- weekly ranking position
- monthly ranking position
- annual top 20 ranking preparation

The annual ranking should not be recalculated on every public request. The preferred direction is to design a dedicated snapshot table/model for yearly top 20 rankings, generated from materialized RCON historical data.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Inspect the listed files first.
2. Review the current RCON-first historical and leaderboard assumptions.
3. Define the V1 user flow for the new `Stats` section.
4. Define the backend API contract needed by the frontend.
5. Define the minimum personal statistics payload.
6. Define how weekly and monthly ranking positions should be calculated for a selected player.
7. Define the annual top 20 snapshot direction and the database objects that a later implementation task should add.
8. Document explicit non-goals and future extensions.
9. Create or update a focused documentation file for this feature.
10. Do not implement backend endpoints, database migrations, frontend screens or scripts in this task.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `ai/task-template.md`
- `backend/app/rcon_historical_leaderboards.py`
- `docs/frontend-data-consumption-plan.md`

## Expected Files to Modify

- `docs/stats-section-functional-plan.md`
- `ai/tasks/pending/TASK-161-define-stats-section-functional-contract.md`

If `docs/frontend-data-consumption-plan.md` must be lightly cross-referenced, keep the change minimal and explain it in the outcome. Do not modify backend or frontend implementation files in this task.

## Functional Contract To Define

The documentation must cover at least:

### Stats section user flow

- User opens the `Stats` section.
- User searches by player name or player id.
- User selects a player from search results.
- UI displays personal statistics.
- UI displays the player's weekly and monthly ranking position.
- UI can later display annual top 20 ranking snapshot data.

### Player search contract

Propose a future endpoint similar to:

```http
GET /api/stats/players/search?q=<query>
```

Expected fields:

- `player_id`
- `player_name`
- `matches_considered`
- `last_seen_at`
- optional `servers_seen`

### Personal stats contract

Propose a future endpoint similar to:

```http
GET /api/stats/players/{player_id}?server_id=<server-or-all>&timeframe=weekly|monthly|all
```

Minimum V1 fields:

- player id
- player name
- selected server scope
- selected timeframe
- window start/end
- matches considered
- kills
- deaths
- teamkills
- K/D ratio
- kills per match
- deaths per match
- weekly ranking position by kills
- monthly ranking position by kills
- data source and freshness metadata

### Annual ranking snapshot contract

Define the future annual snapshot direction with a dedicated persistence model, preferably split into:

- `rcon_annual_ranking_snapshots`
- `rcon_annual_ranking_snapshot_items`

The documentation should describe expected columns, uniqueness rules, generation policy and read API direction, but must not create migrations yet.

Propose a future endpoint similar to:

```http
GET /api/stats/rankings/annual?year=<year>&server_id=<server-or-all>&metric=kills
```

### V1 non-goals

Explicitly exclude from this first feature contract:

- Elo/MMR reactivation
- Comunidad Hispana #03 reintroduction
- support/combat/offense/defense scoring unless already available from reliable RCON materialized data
- weapon-level breakdowns
- charts/advanced visualizations
- authentication or private player profiles
- frontend implementation
- backend endpoint implementation
- database migration implementation

## Constraints

- Keep the change documentation-only.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- Do not implement backend functionality in this task.
- Do not implement frontend functionality in this task.
- Do not expand Elo/MMR, historical workers or RCON server #03 handling.
- Do not overwrite repository-specific context with generic platform template text.
- Keep future tasks small and sequenced.

## Validation

Before completing the task ensure:

- `docs/stats-section-functional-plan.md` exists and is specific to HLL Vietnam.
- The document references the RCON-first materialized data direction.
- The document defines V1 scope, API contracts, payload expectations and annual snapshot direction.
- No backend implementation files were modified.
- No frontend implementation files were modified.
- `git diff --name-only` matches the expected scope.
- If no automated tests are relevant because this is documentation-only, document that explicitly in the outcome.

## Outcome

Document:

- validation performed
- files changed
- notable decisions
- recommended next tasks, likely:
  - add player stats search endpoint
  - add player personal stats endpoint
  - add annual leaderboard timeframe support
  - design annual ranking snapshot schema
  - add Stats frontend section

## Change Budget

- Prefer fewer than 3 modified files.
- Prefer changes under 250 lines.
- Split implementation details into follow-up tasks instead of expanding this task.
