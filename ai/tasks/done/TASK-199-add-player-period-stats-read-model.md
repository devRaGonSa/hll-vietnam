---
id: TASK-199-add-player-period-stats-read-model
title: Add player period stats read model
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto de Base de Datos
  - Arquitecto Python
roadmap_item: foundation
priority: high
---

# TASK-199 - Add player period stats read model

## Goal

Add a dedicated PostgreSQL read model for player personal stats by period so `/api/stats/players/{player_id}` can avoid aggregating large RCON historical tables on every public request when a regenerated read model is available.

## Context

The repository already has PostgreSQL-backed ranking snapshots and a player search read model with controlled runtime fallback. The next expensive public path is the player profile/stats flow, which still aggregates directly from `rcon_materialized_matches` and `rcon_match_player_stats` at request time.

This task adds a regenerable `player_period_stats` read model for weekly, monthly and yearly player totals across the supported public scopes. The profile read path must prefer the read model when it exists and contains rows for the requested player, scope and period, while preserving the current runtime fallback path if the table is missing, empty, incomplete or temporarily unreadable.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Read the listed files first.
2. Add a dedicated PostgreSQL read-model table for player personal stats by period.
3. Implement a refresh function that rebuilds the table from materialized RCON PostgreSQL tables for the supported scopes and windows.
4. Add a manual CLI command to rebuild the read model on demand.
5. Make `/api/stats/players/{player_id}` prefer the read model and keep controlled runtime fallback when needed.
6. Preserve the current frontend contract consumed by `frontend/assets/js/stats.js`.
7. Document the operational command, fallback behavior and current limitations.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `backend/app/routes.py`
- `backend/app/payloads.py`
- `backend/app/rcon_historical_player_stats.py`
- `backend/app/postgres_rcon_storage.py`
- `backend/app/rcon_admin_log_materialization.py`
- `docs/stats-section-functional-plan.md`
- `docs/player-search-read-model-plan.md`
- `ai/tasks/done/TASK-198-add-player-search-read-model.md`

## Expected Files to Modify

- `backend/app/rcon_historical_player_stats.py`
- `backend/app/postgres_rcon_storage.py`
- `scripts/run-stats-validation.ps1`
- `docs/player-period-stats-read-model-plan.md`
- `ai/tasks/done/TASK-199-add-player-period-stats-read-model.md`

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
- Do not require PostgreSQL extensions that are not already installed.
- Keep the current frontend contract for player profile data compatible with `frontend/assets/js/stats.js`.
- Minimum supported period types are `weekly`, `monthly` and `yearly`.
- Minimum supported public scopes are `all-servers`, `comunidad-hispana-01` and `comunidad-hispana-02`.

## Validation

Before completing the task ensure:

- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- local validation proves the `player_period_stats` table can be initialized
- local validation proves `refresh_player_period_stats(...)` generates rows from materialized test data
- local validation proves player profile/stats uses `player_period_stats` when data exists
- local validation proves profile/stats falls back when the read model is empty, missing or unavailable
- the public player profile payload remains compatible with `frontend/assets/js/stats.js`
- player search refresh and read path remain functional
- `git diff --name-only` matches the expected scope

## Outcome

Implemented:

- `backend/app/rcon_historical_player_stats.py`
  - added `player_period_stats` initialization for SQLite compatibility and PostgreSQL-first operational mode
  - added `refresh_player_period_stats(...)`
  - added snapshot-first player profile reads over `player_period_stats`
  - preserved runtime fallback when the read model is empty, incomplete or unavailable
  - added manual CLI:
    - `python -m app.rcon_historical_player_stats refresh-player-period-stats`
- `backend/app/postgres_rcon_storage.py`
  - added PostgreSQL schema for `player_period_stats`
  - added indexes for:
    - `(player_id, period_type, server_id)`
    - `(server_id, period_type)`
    - `last_seen_at`
    - `updated_at`
- `scripts/run-stats-validation.ps1`
  - validates PostgreSQL schema wiring
  - validates CLI defaults
  - validates fixture-driven refresh generation
  - validates read-model-first profile reads
  - validates fallback when the read model is empty, incomplete or unavailable
- `docs/player-period-stats-read-model-plan.md`
  - documents objective, fields, windows, CLI, PostgreSQL role, fallback and current limitations

Created table:

- `player_period_stats`

Table behavior:

- regenerable read model only
- one row per `(period_type, server_id, player_id)` public scope
- supported periods:
  - `weekly`
  - `monthly`
  - `yearly`
- supported scopes:
  - `all-servers`
  - `comunidad-hispana-01`
  - `comunidad-hispana-02`
- stores ranking position by kills for the selected window
- preserves latest player name inside each generated window

CLI added:

- `python -m app.rcon_historical_player_stats refresh-player-period-stats`

Production validation path:

- refresh manually with the CLI above
- confirm row counts are reported for the supported scopes and periods
- call `/api/stats/players/<known-player>?timeframe=weekly`
- verify `data.source.read_model=player-period-stats`
- verify `data.source.fallback_used=false` when the read model is populated
- verify fallback metadata appears only when the read model is empty, incomplete or unavailable

Validations executed:

- `python -m py_compile backend/app/rcon_historical_player_stats.py backend/app/postgres_rcon_storage.py`
- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`

Validation notes:

- live backend HTTP at `http://127.0.0.1:8000` was not available in this environment
- route-contract validation still passed through local Python imports
- no frontend, design, asset, Elo/MMR or Comunidad Hispana `#03` changes were made

Pending follow-up kept out of scope:

- automate periodic refresh scheduling for `player_period_stats`
- decide whether production refresh should be chained with ranking snapshot/search index refresh jobs

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
