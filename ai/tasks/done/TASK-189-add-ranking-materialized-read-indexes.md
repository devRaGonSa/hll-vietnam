---
id: TASK-189-add-ranking-materialized-read-indexes
title: Add ranking materialized read indexes
status: done
type: backend
team: Arquitecto de Base de Datos
supporting_teams:
  - Backend Senior
roadmap_item: foundation
priority: high
---

# TASK-189 - Add ranking materialized read indexes

## Goal

Add safe indexes on the materialized tables used by Ranking and Stats to reduce scans and improve join performance.

## Context

The current Ranking and Stats runtime reads depend on `rcon_materialized_matches`, `rcon_match_player_stats` and annual snapshot tables. After `TASK-188` documents the real bottlenecks, HLL Vietnam needs a narrow indexing pass that improves read performance without changing API contracts, recalculating rankings or introducing a second architecture.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Read the listed files first.
2. Use `docs/ranking-stats-performance-audit.md` as the primary justification source.
3. Add only the indexes supported by the audit findings and the existing storage initialization/migration pattern.
4. Keep SQLite/Postgres compatibility if both storage modes are supported in the current backend.
5. Re-run the validation scripts and, if possible, compare before/after timing for one or two representative endpoints.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `docs/ranking-stats-performance-audit.md`
- `backend/app/rcon_admin_log_materialization.py`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/rcon_historical_player_stats.py`
- `backend/app/rcon_annual_rankings.py`
- `backend/app/postgres_rcon_storage.py`
- `backend/app/sqlite_utils.py`

## Expected Files to Modify

- `backend` storage/migration/init module correspondiente, según patrón existente
- `docs/ranking-stats-performance-audit.md`, solo si se documenta índice aplicado
- `ai/tasks/done/TASK-189-add-ranking-materialized-read-indexes.md`

## Constraints

- No cambiar contratos API.
- No cambiar frontend.
- No recalcular rankings.
- No crear snapshots en esta task.
- No reactivar Elo/MMR.
- No reintroducir Comunidad Hispana #03.
- Mantener compatibilidad SQLite/Postgres si el proyecto usa ambos.
- Basar los índices en evidencia documentada por `TASK-188`, no en suposiciones.

## Validation

Before completing the task ensure:

- the chosen indexes are justified by `TASK-188`
- candidate coverage explicitly considers:
  - `target_key + match_key`
  - `source_basis + ended_at/started_at`
  - `target_key + ended_at/started_at`
  - `player_id`
  - `player_name` if search benefits from it
  - `snapshot_id + ranking_position` in snapshot tables if applicable
- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- if possible, before/after timing is captured for one or two endpoints
- any measurement limitations are documented
- `git diff --name-only` stays within scope

## Outcome

- Added SQLite/PostgreSQL-compatible indexes in the materialized storage initialization path:
  - `idx_rcon_materialized_matches_source_window_text`
  - `idx_rcon_materialized_matches_target_source_window_text`
  - `idx_rcon_materialized_matches_external_source_window_text`
  - `idx_rcon_match_player_stats_player_id_match`
- Kept existing annual snapshot indexes unchanged because the annual read path was already using matching indexes.
- Did not add a plain `player_name` B-tree because the current search query uses `LOWER(player_name) LIKE '%term%'` with a leading wildcard, so the audit did not justify it as a useful narrow index.
- Post-index validation confirmed plan improvement:
  - weekly count queries now use the new `source_basis + window` covering index
  - the stats player-detail aggregate now narrows through the match window index and then probes stats by `(target_key, match_key, player_id)`
- Before/after timing was captured for representative endpoints:
  - `/api/stats/players/{player_id}` weekly improved from `8.924 ms / 4.494 ms SQL` to `4.300 ms / 1.043 ms SQL`
  - `/api/ranking` weekly `kills` showed no meaningful change in this dataset because the active weekly window on `2026-06-09` is empty
- Validation scripts executed successfully:
  - `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
  - `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- Remaining gap:
  - weekly/monthly public ranking still does repeated runtime counting and grouped aggregation per request, so snapshot-backed reads remain necessary in `TASK-190` and `TASK-191`

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
