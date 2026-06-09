---
id: TASK-198-add-player-search-read-model
title: Add player search read model
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto de Base de Datos
  - Arquitecto Python
roadmap_item: foundation
priority: high
---

# TASK-198 - Add player search read model

## Goal

Add the first PostgreSQL read model for player search so `/api/stats/players/search` can serve compact search results without aggregating large RCON historical tables on every public request.

## Context

Weekly and monthly ranking snapshots are already implemented and validated in PostgreSQL with runtime fallback preserved. The next high-cost public path is the player search flow, which currently reads directly from `rcon_match_player_stats` and `rcon_materialized_matches` at request time.

This task adds a dedicated regenerable read model for player lookup, refreshed manually out of band from materialized RCON PostgreSQL tables. The public search endpoint must prefer that read model when it exists and has rows, while preserving controlled runtime fallback if the read model is missing, empty or temporarily unreadable.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Read the listed files first.
2. Add a dedicated player search index table as a regenerable read model.
3. Implement a refresh function that rebuilds the index from materialized RCON PostgreSQL tables, with current-year counters and recent player rows only.
4. Add a manual CLI command to rebuild the read model on demand.
5. Make `/api/stats/players/search` prefer the read model and keep runtime fallback when needed.
6. Preserve the current frontend contract consumed by `frontend/assets/js/stats.js`.
7. Document the operational command, fallback behavior and current limitations.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `backend/app/payloads.py`
- `backend/app/rcon_historical_player_stats.py`
- `backend/app/postgres_rcon_storage.py`
- `backend/app/rcon_admin_log_materialization.py`
- `docs/stats-section-functional-plan.md`
- `docs/ranking-snapshot-read-model-plan.md`
- `ai/tasks/done/TASK-197-automate-ranking-snapshot-refresh.md`

## Expected Files to Modify

- `backend/app/rcon_historical_player_stats.py`
- `backend/app/postgres_rcon_storage.py`
- `scripts/run-stats-validation.ps1`
- `docs/player-search-read-model-plan.md`
- `ai/tasks/done/TASK-198-add-player-search-read-model.md`

## Constraints

- Keep the change minimal and backend-only.
- Do not execute `ai-platform run`.
- Do not modify frontend.
- Do not change design.
- Do not touch images or assets.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana `#03`.
- Do not mix visual corrections into this task.
- PostgreSQL is the operational storage target.
- SQLite may remain only as explicit local compatibility where the current backend architecture already supports it.
- The new table is a regenerable read model, not a canonical source of truth.
- Do not require PostgreSQL extensions such as `pg_trgm`.
- Keep the current frontend contract for player search results compatible with `frontend/assets/js/stats.js`.

## Validation

Before completing the task ensure:

- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- local validation proves the `player_search_index` table can be initialized
- local validation proves `refresh_player_search_index(...)` generates rows from materialized test data
- local validation proves player search uses `player_search_index` when data exists
- local validation proves search falls back to the runtime aggregation path when the index is empty or unavailable
- the public search payload remains compatible with `frontend/assets/js/stats.js`
- `git diff --name-only` matches the expected scope

## Outcome

Implemented:

- `backend/app/rcon_historical_player_stats.py`
  - added `player_search_index` initialization for SQLite compatibility and PostgreSQL-first operational mode
  - added `refresh_player_search_index(...)`
  - added snapshot-first search logic for `/api/stats/players/search`
  - preserved runtime fallback when the read model is empty or unavailable
  - added manual CLI:
    - `python -m app.rcon_historical_player_stats refresh-player-search-index`
- `backend/app/postgres_rcon_storage.py`
  - added PostgreSQL schema for `player_search_index`
  - added scope-aware indexes for normalized name, last seen and player id
- `backend/app/payloads.py`
  - preserved the public search payload contract and added backward-compatible source metadata
- `scripts/run-stats-validation.ps1`
  - validates PostgreSQL schema wiring
  - validates CLI defaults
  - validates fixture-driven refresh generation
  - validates read-model-first search
  - validates fallback when the index is empty or unavailable
- `docs/player-search-read-model-plan.md`
  - documents objective, fields, CLI, PostgreSQL role, fallback and current limitations

Created table:

- `player_search_index`

Table behavior:

- regenerable read model only
- one row per `(server_id, player_id)` public search scope
- supported scopes:
  - `all-servers`
  - `comunidad-hispana-01`
  - `comunidad-hispana-02`
- aggregates only current UTC year counters
- stores Python-normalized accent-insensitive `normalized_player_name`

CLI added:

- `python -m app.rcon_historical_player_stats refresh-player-search-index`

Production validation path:

- refresh manually with the CLI above
- confirm row counts are reported for `all-servers`, `comunidad-hispana-01` and `comunidad-hispana-02`
- call `/api/stats/players/search?q=<known-player>&limit=5`
- verify `data.source.read_model=player-search-index`
- verify `data.source.fallback_used=false` when the read model is populated
- verify fallback metadata appears only when the read model is empty or unavailable

Validations executed:

- `python -m py_compile backend/app/rcon_historical_player_stats.py backend/app/payloads.py backend/app/postgres_rcon_storage.py`
- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- local CLI smoke check:
  - `python -m app.rcon_historical_player_stats refresh-player-search-index --sqlite-path backend/data/hll_vietnam_dev.sqlite3`

Validation notes:

- live backend HTTP at `http://127.0.0.1:8000` was not available in this environment
- route-contract validation still passed through local Python imports
- no frontend, design, asset, Elo/MMR or Comunidad Hispana `#03` changes were made

Pending follow-up kept out of scope:

- player profile and personal stats still read from runtime aggregates; only the search path is snapshot-backed in this task

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
