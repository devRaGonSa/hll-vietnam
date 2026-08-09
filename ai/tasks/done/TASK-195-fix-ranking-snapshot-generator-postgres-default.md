---
id: TASK-195-fix-ranking-snapshot-generator-postgres-default
title: Fix ranking snapshot generator PostgreSQL default
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto de Base de Datos
  - Arquitecto Python
roadmap_item: foundation
priority: high
---

# TASK-195 - Fix ranking snapshot generator PostgreSQL default

## Goal

Correct the weekly/monthly ranking snapshot CLI so production generation uses PostgreSQL by default, matching the operational `/api/ranking` read path.

## Context

`TASK-194` added a manual weekly/monthly snapshot generator, but the CLI currently passes `db_path=get_storage_path()` into `generate_ranking_snapshot(...)`. In this repository, `use_postgres_rcon_storage(...)` only enables PostgreSQL when `explicit_sqlite_path is None` and `HLL_BACKEND_DATABASE_URL` exists, so the current CLI forces SQLite while `/api/ranking` reads PostgreSQL.

This causes operational commands to generate `ready` snapshots with `item_count=0` and `source_matches_count=0` in SQLite even when runtime fallback over PostgreSQL returns ranking players.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Read the listed files first.
2. Change the ranking snapshot CLI to use PostgreSQL by default in operational mode.
3. Keep SQLite available only as an explicit local-development override if needed.
4. Validate the CLI default path, repository scripts and documentation.
5. Document root cause, fix and production validation steps.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `backend/app/config.py`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/postgres_rcon_storage.py`
- `scripts/run-stats-validation.ps1`
- `docs/ranking-snapshot-read-model-plan.md`
- `ai/tasks/done/TASK-194-add-weekly-monthly-ranking-snapshot-generator.md`

## Expected Files to Modify

- `backend/app/rcon_historical_leaderboards.py`
- `scripts/run-stats-validation.ps1`
- `docs/ranking-snapshot-read-model-plan.md`
- `ai/tasks/done/TASK-195-fix-ranking-snapshot-generator-postgres-default.md`

## Constraints

- Keep the change minimal.
- Do not modify frontend, assets or design.
- Do not change public endpoint behavior beyond the intended generator hotfix.
- Keep annual ranking behavior unchanged.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Keep PostgreSQL as the operational default and SQLite only as an explicit local-development mode.

## Validation

Before completing the task ensure:

- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- local import or parser validation proves the CLI no longer passes `get_storage_path()` by default
- local validation proves `generate_ranking_snapshot(..., db_path=None)` uses PostgreSQL when `HLL_BACKEND_DATABASE_URL` is configured
- `git diff --name-only` matches the expected scope

## Outcome

Root cause:

- the manual CLI in `backend/app/rcon_historical_leaderboards.py` called `generate_ranking_snapshot(..., db_path=get_storage_path())`
- that forced `explicit_sqlite_path != None`
- `use_postgres_rcon_storage(...)` therefore disabled PostgreSQL even when `HLL_BACKEND_DATABASE_URL` was configured
- operational `/api/ranking` reads PostgreSQL, so the generator and the public ranking endpoint diverged onto different storage backends

Applied change:

- `backend/app/rcon_historical_leaderboards.py`
  - removed the default CLI path that forced SQLite
  - changed the operational default to `db_path=None`
  - added explicit `--sqlite-path <path>` override for local development only
- `scripts/run-stats-validation.ps1`
  - now validates that the CLI default passes `db_path=None`
  - now validates that PostgreSQL selection activates when `HLL_BACKEND_DATABASE_URL` is configured and no explicit SQLite path is provided
- `docs/ranking-snapshot-read-model-plan.md`
  - now documents PostgreSQL as the operational default
  - now documents `--sqlite-path` as an explicit local override only

Previous vs new behavior:

- before:
  - `python -m app.rcon_historical_leaderboards generate-ranking-snapshot ...`
  - forced SQLite by default
  - could generate empty snapshots operationally while `/api/ranking` fallback over PostgreSQL still returned players
- now:
  - the same command uses PostgreSQL by default when `HLL_BACKEND_DATABASE_URL` is configured
  - SQLite is used only when the operator passes `--sqlite-path`

Validation executed:

- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`

Validation notes:

- live backend HTTP at `http://127.0.0.1:8000` was not available in this environment
- route and CLI validation completed through local Python imports and repository validation scripts
- no local PostgreSQL instance was required because the validation proved backend selection by inspection and monkeypatched connection-path checks

Final recommended Docker command:

- `docker compose exec backend python -m app.rcon_historical_leaderboards generate-ranking-snapshot --timeframe weekly --server-key all --metric kills --limit 20`

How to validate in production:

1. run the Docker command above in the production backend container
2. query PostgreSQL `ranking_snapshots` for the selected `(timeframe, server_id, metric, window_start, window_end)`
3. confirm `item_count > 0` and `source_matches_count > 0` for covered windows
4. call `/api/ranking?timeframe=weekly&server_id=all&metric=kills&limit=20`
5. confirm `snapshot_status=ready` and `fallback_used=false`

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
