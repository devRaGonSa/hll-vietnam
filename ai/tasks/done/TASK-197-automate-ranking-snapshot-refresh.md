---
id: TASK-197-automate-ranking-snapshot-refresh
title: Automate ranking snapshot refresh
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto de Base de Datos
  - Arquitecto Python
roadmap_item: foundation
priority: high
---

# TASK-197 - Automate ranking snapshot refresh

## Goal

Automate the periodic refresh of weekly and monthly ranking snapshots in PostgreSQL so `/api/ranking` can keep serving `ranking-snapshot` read-model responses for the supported public combinations without relying on manual one-by-one generation.

## Context

`TASK-194`, `TASK-195` and `TASK-196` already validated the manual generator path in production:

- `generate-ranking-snapshot` works
- PostgreSQL is the default operational backend
- CLI JSON serialization is fixed
- the expected `36` combinations were generated successfully
- all generated rows ended with `snapshot_status=ready`
- `/api/ranking` returns `source.read_model=ranking-snapshot`
- `/api/ranking` returns `fallback_used=false` when a ready snapshot exists
- `limit_size=30` already covers the current UI limits `10`, `20` and `30`

The remaining gap is operational automation. The repository already has a periodic backend runner in `backend/app/historical_runner.py`, so the default direction for this task is to integrate ranking snapshot refresh there rather than invent a separate scheduler. If that integration becomes too invasive, the fallback is a controlled bulk CLI/manual helper such as `python -m app.rcon_historical_leaderboards refresh-ranking-snapshots --limit 30`, with the periodic integration left prepared for the next step.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Read the listed files first.
2. Inspect the existing historical runner and ranking snapshot generator entrypoints.
3. Add the smallest safe backend mechanism that refreshes the weekly/monthly ranking snapshot matrix in PostgreSQL.
4. Generate the supported matrix with per-combination error reporting so one failure does not necessarily abort the entire refresh.
5. Keep the manual single-snapshot CLI working.
6. Preserve `/api/ranking` snapshot-first behavior and runtime fallback when a snapshot is missing.
7. Document the recommended refresh cadence and manual operational commands.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/historical_runner.py`
- `backend/app/rcon_historical_worker.py`
- `backend/app/payloads.py`
- `docs/ranking-snapshot-read-model-plan.md`
- `scripts/run-stats-validation.ps1`
- `ai/tasks/done/TASK-194-add-weekly-monthly-ranking-snapshot-generator.md`
- `ai/tasks/done/TASK-195-fix-ranking-snapshot-generator-postgres-default.md`
- `ai/tasks/done/TASK-196-fix-ranking-snapshot-cli-json-serialization.md`

## Expected Files to Modify

- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/historical_runner.py`
- `backend/app/payloads.py`
- `docs/ranking-snapshot-read-model-plan.md`
- `scripts/run-stats-validation.ps1`

## Constraints

- Keep the change minimal and backend-only.
- Do not modify frontend.
- Do not change design.
- Do not touch images or assets.
- Use PostgreSQL as the operational storage target.
- Do not depend on SQLite for the automated refresh path.
- Do not change the public `/api/ranking` contract except internal metadata already present if strictly needed.
- Do not break the manual `generate-ranking-snapshot` CLI.
- Keep runtime fallback as a safety net when a snapshot is missing.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Do not introduce an invasive scheduler architecture if the existing runner can safely host the refresh.

## Validation

Before completing the task ensure:

- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- the automated or bulk refresh path generates the expected `36` combinations:
  - timeframes: `weekly`, `monthly`
  - servers: `all`, `comunidad-hispana-01`, `comunidad-hispana-02`
  - metrics: `kills`, `deaths`, `teamkills`, `matches_considered`, `kd_ratio`, `kills_per_match`
  - limit: `30`
- validation proves per-combination failures are reported and do not necessarily stop every remaining combination
- validation proves the manual CLI `generate-ranking-snapshot` still works
- validation proves `/api/ranking` still serves `snapshot_status=ready` and `read_model=ranking-snapshot` when ready snapshots exist
- validation proves runtime fallback remains available for missing snapshots
- `git diff --name-only` matches the expected scope

## Outcome

Implemented:

- `backend/app/rcon_historical_leaderboards.py`
  - added `refresh_ranking_snapshots(...)` to generate the full weekly/monthly matrix in one run
  - added bulk CLI entrypoint:
    - `python -m app.rcon_historical_leaderboards refresh-ranking-snapshots --limit 30`
  - preserved the existing manual CLI entrypoint:
    - `python -m app.rcon_historical_leaderboards generate-ranking-snapshot --timeframe weekly --server-key all --metric kills --limit 30`
- `backend/app/historical_runner.py`
  - integrated ranking snapshot refresh into the periodic historical backend cycle through `refresh_periodic_ranking_snapshots(...)`
  - the cycle now reports `ranking_snapshot_result` separately from the existing historical snapshot result
- `docs/ranking-snapshot-read-model-plan.md`
  - documents the new bulk command
  - documents the runner integration direction
  - documents `limit=30` as the operational default for the weekly/monthly matrix
- `scripts/run-stats-validation.ps1`
  - validates the bulk CLI argument path
  - validates that bulk refresh covers `36` combinations
  - validates partial failure reporting without aborting the remaining combinations
  - keeps validating the existing manual `generate-ranking-snapshot` path

Generated matrix:

- timeframes: `weekly`, `monthly`
- servers: `all`, `comunidad-hispana-01`, `comunidad-hispana-02`
- metrics: `kills`, `deaths`, `teamkills`, `matches_considered`, `kd_ratio`, `kills_per_match`
- limit: `30`
- total combinations per refresh cycle: `36`

Per-combination failure behavior:

- bulk refresh catches exceptions per combination
- the full refresh result returns `status=partial` when at least one combination fails and at least one succeeds
- each failed combination reports:
  - `timeframe`
  - `server_key`
  - `metric`
  - `error_type`
  - `error`
- a single failure does not abort the remaining combinations

Recommended frequency:

- weekly current window: every `5` to `15` minutes
- monthly current window: every `15` to `30` minutes
- closed previous week / previous month windows: once after closure or after historical backfill

Validations executed:

- `python -m compileall backend/app/rcon_historical_leaderboards.py backend/app/historical_runner.py`
- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- isolated real CLI validation against temporary SQLite files outside the workspace:
  - `refresh-ranking-snapshots --limit 30` returned `combinations_expected=36`, `succeeded=36`, `failed=0`
  - `generate-ranking-snapshot` still returned `status=ok` and `snapshot_status=ready`

Validation notes:

- live backend HTTP at `http://127.0.0.1:8000` was not available in this environment
- `/api/ranking` snapshot-ready and fallback behavior remained validated through the existing local route-contract checks in `scripts/run-stats-validation.ps1`
- no frontend, design, asset, Elo/MMR or Comunidad Hispana `#03` changes were made

Pending limitation kept out of scope:

- this task integrates the refresh into the existing periodic historical runner and adds a bulk CLI, but it does not introduce a separate external scheduler or deployment-specific cron wiring

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
