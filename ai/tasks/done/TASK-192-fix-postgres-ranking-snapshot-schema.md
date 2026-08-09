---
id: TASK-192-fix-postgres-ranking-snapshot-schema
title: Fix PostgreSQL ranking snapshot schema
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto de Base de Datos
  - Arquitecto Python
roadmap_item: foundation
priority: high
---

# TASK-192 - Fix PostgreSQL ranking snapshot schema

## Goal

Apply a backend hotfix so weekly and monthly ranking snapshot storage initializes correctly in PostgreSQL without executing SQLite-only schema syntax.

## Context

Production `GET /api/ranking?timeframe=weekly&metric=kills&limit=20` currently fails because `backend/app/rcon_historical_leaderboards.py` executes SQLite DDL with `AUTOINCREMENT` through `psycopg`. HLL Vietnam operational storage must stay in PostgreSQL, including ranking snapshots, and this fix must preserve the current annual snapshot path and avoid any SQLite expansion for this functionality.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Inspect the listed files first.
2. Create the PostgreSQL-compatible ranking snapshot schema following the existing backend storage pattern.
3. Keep annual snapshot storage intact and scoped to `rcon_annual_ranking_snapshots`.
4. Validate the backend path and document the root cause, fix and production verification steps.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/postgres_rcon_storage.py`
- `backend/app/rcon_admin_log_materialization.py`
- `backend/app/rcon_annual_rankings.py`
- `backend/app/payloads.py`
- `backend/app/routes.py`
- `scripts/run-stats-validation.ps1`
- `ai/tasks/done/TASK-191-serve-ranking-from-snapshots-with-runtime-fallback.md`

## Expected Files to Modify

- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/postgres_rcon_storage.py`, solo si el patrón del proyecto lo requiere
- `scripts/run-stats-validation.ps1`, solo si se añade validación de regresión
- `ai/tasks/done/TASK-192-fix-postgres-ranking-snapshot-schema.md`

## Constraints

- Keep the change minimal.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- Do not create or depend on a separate SQLite database for ranking snapshots.
- Do not expand legacy SQLite compatibility routes for this functionality beyond what already exists.
- Do not modify frontend, visual logic, Elo/MMR or Comunidad Hispana #03 handling.
- Keep annual ranking on `rcon_annual_ranking_snapshots`.
- Do not overwrite repository-specific context with generic platform template text.

## Validation

Before completing the task ensure:

- `node --check frontend/assets/js/ranking.js`
- `node --check frontend/assets/js/stats.js`
- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- local validation proves `initialize_ranking_snapshot_storage` does not contain or execute `AUTOINCREMENT` on the PostgreSQL path
- local validation proves PostgreSQL schema defines `ranking_snapshots` and `ranking_snapshot_items` with PostgreSQL-compatible syntax
- `/api/ranking?timeframe=weekly&metric=kills&limit=20` no longer fails because of table creation
- `/api/ranking?timeframe=annual&metric=kills&limit=20&year=2026` keeps working
- `git diff --name-only` matches the expected scope

If local PostgreSQL is unavailable, document that in Outcome and validate by code inspection plus existing scripts.

## Outcome

- Root cause:
  - `backend/app/rcon_historical_leaderboards.py` defined `ranking_snapshots` / `ranking_snapshot_items` with SQLite syntax and executed that same DDL through `psycopg` on the PostgreSQL path.
  - Production failure matched the SQLite-only token exactly: `AUTOINCREMENT`.
- Confirmation:
  - The failing path was `build_global_ranking_payload` -> `get_latest_ranking_snapshot` -> `initialize_ranking_snapshot_storage`.
  - The hotfix removes PostgreSQL execution of the SQLite snapshot DDL and routes PostgreSQL initialization through the central PostgreSQL schema initializer.
- Applied change:
  - Kept the SQLite snapshot schema local to the SQLite path in `backend/app/rcon_historical_leaderboards.py`.
  - Added PostgreSQL-compatible `ranking_snapshots` and `ranking_snapshot_items` tables plus indexes to `backend/app/postgres_rcon_storage.py`.
  - Used `BIGSERIAL` primary keys and PostgreSQL-compatible `BIGINT`, `DOUBLE PRECISION`, `TIMESTAMPTZ`, foreign keys and index syntax.
  - Added regression validation in `scripts/run-stats-validation.ps1` to prove the PostgreSQL path does not depend on `AUTOINCREMENT` and that it delegates to `initialize_postgres_rcon_storage`.
- Expected PostgreSQL tables:
  - `ranking_snapshots`
  - `ranking_snapshot_items`
  - Annual ranking remains on:
    - `rcon_annual_ranking_snapshots`
    - `rcon_annual_ranking_snapshot_items`
- Validations executed:
  - `node --check frontend/assets/js/ranking.js`
  - `node --check frontend/assets/js/stats.js`
  - `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
  - `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
  - Local regression validation now proves:
    - PostgreSQL schema text contains `ranking_snapshots` and `ranking_snapshot_items`
    - PostgreSQL schema text does not contain `AUTOINCREMENT`
    - `initialize_ranking_snapshot_storage()` delegates to PostgreSQL schema initialization on the PostgreSQL path
    - `/api/ranking?timeframe=annual&year=2026&server_id=all&metric=kills&limit=20` still resolves
- Environment note:
  - Local backend HTTP at `http://127.0.0.1:8000` was not available during validation.
  - Validation therefore completed by local Python imports, route resolution and existing scripts, which passed.
- How to validate in production:
  - Deploy the backend hotfix.
  - Confirm PostgreSQL contains `ranking_snapshots` and `ranking_snapshot_items`.
  - Request:
    - `/api/ranking?timeframe=weekly&metric=kills&limit=20`
    - `/api/ranking?timeframe=monthly&metric=kills&limit=20`
    - `/api/ranking?timeframe=annual&metric=kills&limit=20&year=2026`
  - Verify weekly/monthly no longer fail during table initialization and annual remains unchanged.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
