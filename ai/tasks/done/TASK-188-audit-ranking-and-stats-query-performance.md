---
id: TASK-188-audit-ranking-and-stats-query-performance
title: Audit ranking and stats query performance
status: done
type: research
team: Arquitecto de Base de Datos
supporting_teams:
  - Backend Senior
  - Arquitecto Python
roadmap_item: foundation
priority: high
---

# TASK-188 - Audit ranking and stats query performance

## Goal

Measure and document the real performance of the public Ranking and Stats endpoints before applying any optimization.

## Context

`/api/ranking` weekly/monthly currently reads runtime aggregates over materialized RCON/AdminLog tables, while annual ranking already uses snapshots. `Stats` search and player detail also depend on runtime reads over the same materialized domain. HLL Vietnam needs a concrete baseline for latency, query shape, table size and execution plan so follow-up work can target the real bottlenecks instead of guessing.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Read the listed files first.
2. Identify the exact queries and tables used by the target endpoints.
3. Measure request time and, if possible, approximate SQL time for each target endpoint.
4. Inspect relevant row counts, current indexes and execution plans when the engine allows it.
5. Document the slowest endpoint and provide a concrete index/snapshot recommendation without changing runtime code.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `backend/app/routes.py`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/rcon_historical_player_stats.py`
- `backend/app/rcon_annual_rankings.py`
- `docs/global-ranking-page-plan.md`
- `scripts/run-stats-validation.ps1`

## Expected Files to Modify

- `docs/ranking-stats-performance-audit.md`
- `ai/tasks/done/TASK-188-audit-ranking-and-stats-query-performance.md`

## Constraints

- No modificar lógica de backend.
- No modificar frontend.
- No crear migraciones.
- No crear índices todavía.
- No cambiar APIs.
- No reactivar Elo/MMR.
- No reintroducir Comunidad Hispana #03.
- Mantener el trabajo limitado a medición y documentación.

## Validation

Before completing the task ensure:

- the audit covers:
  - `/api/ranking` weekly `kills`
  - `/api/ranking` weekly `kd_ratio`
  - `/api/ranking` monthly `kills_per_match`
  - `/api/ranking` annual `kills`
  - `/api/stats/players/search`
  - `/api/stats/players/{player_id}`
- the document records:
  - total request time
  - approximate SQL time if measurable
  - row counts for relevant tables
  - existing indexes
  - current query shapes
  - execution plan if available
  - slowest endpoint
  - concrete recommendation for indexes and/or snapshots
- executed commands are documented
- inability to obtain `EXPLAIN` is documented if the environment blocks it
- `git diff --name-only` stays within scope

## Outcome

- Audit completed in `docs/ranking-stats-performance-audit.md`.
- Measured baseline captured for the six required endpoint probes.
- Environment limitation documented: backend HTTP server was not running locally, so request timing used in-process route resolution and SQL tracing over SQLite.
- Current runtime weekly/monthly ranking windows on `2026-06-09` are empty because the latest materialized `admin-log-match-ended` data ends on `2026-05-20T23:21:45.816Z`.
- Slowest measured endpoint is `/api/stats/players/{player_id}` because it issues 16 SQL statements, including repeated window counts and two ranking-position subqueries.
- Primary future performance risks identified:
  - full scans on `rcon_materialized_matches` for `source_basis + time-window` filters
  - a full scan on `rcon_match_player_stats` for player-detail-by-`player_id`
  - temp B-trees for grouping, `COUNT(DISTINCT)` and ordering in leaderboard/search queries
- Follow-up recommendation for `TASK-189`:
  - add time-window indexes on `rcon_materialized_matches`
  - add a direct `player_id` index on `rcon_match_player_stats`
  - keep annual snapshot indexes as-is
- Follow-up recommendation for `TASK-190`:
  - move weekly/monthly public ranking to snapshot-backed reads with controlled runtime fallback

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
