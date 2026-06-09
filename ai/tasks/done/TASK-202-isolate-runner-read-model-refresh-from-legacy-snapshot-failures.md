---
id: TASK-202-isolate-runner-read-model-refresh-from-legacy-snapshot-failures
title: Isolate runner read model refresh from legacy snapshot failures
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto de Base de Datos
  - Arquitecto Python
roadmap_item: foundation
priority: high
---

# TASK-202 - Isolate runner read model refresh from legacy snapshot failures

## Goal

Prevent legacy historical snapshot failures from blocking the operational PostgreSQL read-model refreshes in the periodic historical runner.

## Context

After `TASK-201`, the periodic runner starts correctly and announces the expected hourly scope, but the first cycle aborts before reaching the PostgreSQL operational read models when legacy historical snapshot generation fails with `sqlite3.OperationalError: no such table: player_event_raw_ledger`.

The current failure path happens inside `generate_historical_snapshots(...)`, which was still executed inside the runner's broader refresh attempt. That legacy failure prevented the cycle from refreshing:

- `player_search_index`
- `player_period_stats`
- `ranking_snapshots`

This task isolates the cycle steps so the legacy error stays visible in logs and results, while the operational PostgreSQL refreshes are still attempted in the same cycle. Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Read the listed files first.
2. Confirm the current runner failure path and where legacy snapshot generation aborts the cycle.
3. Refactor the periodic runner so each refresh step is handled as an isolated unit with a separately reported result.
4. Preserve retries for full-attempt failures where they still apply, but avoid retry-only behavior for a legacy step that should no longer block operational refreshes.
5. Keep the legacy snapshot error visible in logs and cycle results.
6. Ensure the runner still attempts:
   - `refresh_player_search_index(...)`
   - `refresh_player_period_stats(...)`
   - `refresh_ranking_snapshots(...)`
   even when `generate_historical_snapshots(...)` fails.
7. Return a global cycle status of `partial` or equivalent when the legacy snapshot step fails but operational steps continue.
8. Keep manual CLIs and public API contracts unchanged.
9. Update operational documentation with the new partial-cycle behavior and production validation guidance.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `backend/app/historical_runner.py`
- `backend/app/historical_snapshots.py`
- `backend/app/historical_storage.py`
- `backend/app/rcon_historical_player_stats.py`
- `backend/app/rcon_historical_leaderboards.py`
- `scripts/run-stats-validation.ps1`
- `docs/player-search-read-model-plan.md`
- `docs/player-period-stats-read-model-plan.md`
- `docs/ranking-snapshot-read-model-plan.md`
- `ai/tasks/done/TASK-201-automate-player-read-model-refresh.md`

## Expected Files to Modify

- `backend/app/historical_runner.py`
- `backend/tests/test_historical_snapshot_refresh.py`
- `scripts/run-stats-validation.ps1`
- `docs/player-search-read-model-plan.md`
- `docs/player-period-stats-read-model-plan.md`
- `docs/ranking-snapshot-read-model-plan.md`
- `ai/tasks/done/TASK-202-isolate-runner-read-model-refresh-from-legacy-snapshot-failures.md`

## Constraints

- Keep the change minimal and backend/documentation only.
- Do not execute `ai-platform run`.
- Do not modify frontend.
- Do not change design.
- Do not touch images or assets.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana `#03`.
- Do not fix or migrate `player_event_raw_ledger` in this task unless analysis proves it is strictly necessary.
- Do not create or modify legacy tables unless it becomes strictly necessary and is explicitly justified in the outcome.
- Do not hide legacy errors; they must remain visible in logs and result payloads.
- Do not change manual CLI behavior.
- Do not change public API contracts.

## Validation

Before completing the task ensure:

- `python -m py_compile backend/app/historical_runner.py`
- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- local/import validation proves that when `generate_historical_snapshots(...)` fails:
  - `refresh_player_search_index(...)` is still attempted
  - `refresh_player_period_stats(...)` is still attempted
  - `refresh_ranking_snapshots(...)` is still attempted
  - the global result is `partial` or equivalent
  - the legacy error remains reported
- local/import validation proves that when all steps succeed, the cycle still returns `ok`
- local/import validation proves separate result payloads still exist:
  - `historical_snapshot_result`
  - `player_search_index_result`
  - `player_period_stats_result`
  - `ranking_snapshot_result`
- `git diff --name-only` matches the expected scope

## Outcome

Root cause:

- `generate_historical_snapshots(...)` still ran inside the runner attempt's broad failure boundary.
- When the legacy monthly MVP V2 snapshot path touched missing `player_event_raw_ledger` state, it raised `OperationalError`.
- That exception aborted the attempt before the PostgreSQL operational read-model refreshes were called.

Previous behavior:

- a legacy snapshot failure stopped the cycle before:
  - `player_search_index`
  - `player_period_stats`
  - `ranking_snapshots`
- the cycle returned attempt-level failure instead of a partial operational result
- operators could see the legacy error, but the operational read models stayed stale

New behavior:

- `backend/app/historical_runner.py`
  - wraps legacy snapshot refresh in an isolated step via `refresh_periodic_historical_snapshots(...)`
  - preserves the legacy error in logs and result payloads with:
    - `historical_snapshot_result`
    - compatibility alias `snapshot_result`
    - event `historical-snapshot-refresh-failed`
  - continues attempting:
    - `player_search_index`
    - `player_period_stats`
    - `ranking_snapshots`
    after a legacy snapshot failure
  - resolves the overall cycle to `partial` when the isolated legacy step fails but operational refreshes continue
- `backend/tests/test_historical_snapshot_refresh.py`
  - adds coverage for legacy snapshot failure isolation
  - adds coverage for the all-success path still returning `ok`
- `scripts/run-stats-validation.ps1`
  - validates that a legacy snapshot failure still leaves the operational read-model refresh sequence running
  - validates:
    - `historical_snapshot_result`
    - `player_search_index_result`
    - `player_period_stats_result`
    - `ranking_snapshot_result`
  - validates the global `partial` result and preserved legacy error reporting
- operational docs now explain that the runner can finish `partial` if the legacy block fails while PostgreSQL read-model refreshes still run

Validations executed:

- `python -m py_compile backend/app/historical_runner.py`
- `python -m unittest tests.test_historical_snapshot_refresh`
- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`

Production validation:

1. Run one controlled cycle:
   - `python -m app.historical_runner --max-runs 1`
2. Inspect the cycle payload and logs for:
   - `status` equal to `ok` or `partial`
   - `historical_snapshot_result`
   - `player_search_index_result`
   - `player_period_stats_result`
   - `ranking_snapshot_result`
3. If `status=partial`, confirm the legacy failure remains visible under:
   - `historical_snapshot_result.error_type`
   - `historical_snapshot_result.error`
   - `historical_snapshot_result.traceback`
4. Confirm operational timestamps still advance in PostgreSQL for:
   - `player_search_index`
   - `player_period_stats`
   - `ranking_snapshots`
5. Confirm public reads still use the refreshed read models:
   - `/api/stats/players/search`
   - `/api/stats/players/{player_id}`
   - `/api/ranking`

Scope notes:

- no frontend files were modified
- no images/assets were touched
- `player_event_raw_ledger` was not fixed or migrated in this task
- manual CLIs were preserved unchanged
- pre-existing unrelated changes in `ai/system-metrics.md` and frontend assets were intentionally left untouched

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
