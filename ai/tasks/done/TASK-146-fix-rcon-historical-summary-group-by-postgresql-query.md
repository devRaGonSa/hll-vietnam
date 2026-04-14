# TASK-146-fix-rcon-historical-summary-group-by-postgresql-query

## Goal

Fix the PostgreSQL SQL error in the RCON historical summary query where checkpoint columns are selected outside the `GROUP BY` or an aggregate, while preserving the expected functional result.

## Context

PostgreSQL reports a real SQL error independent of the Elo/MMR rebuild issue:

`column "checkpoints.last_successful_capture_at" must appear in the GROUP BY clause or be used in an aggregate function`

The failing query joins `rcon_historical_targets`, `rcon_historical_checkpoints`, and `rcon_historical_competitive_windows`. Local inspection points to the RCON historical summary read path, especially the query in `backend/app/rcon_historical_storage.py` that selects checkpoint fields, aggregates competitive windows, and groups only by `targets.id`. This task is only for the SQL correctness and semantic preservation of that RCON historical read.

## Scope

- Locate the exact failing query and the functional route that executes it.
- Correct the query in a PostgreSQL-compatible way.
- Decide deliberately whether the right fix is to expand `GROUP BY`, aggregate checkpoint columns, or restructure the query with a subquery/CTE.
- Preserve result semantics for per-target summary rows: target identity, checkpoint status/error fields, window counts, sample totals, first/last seen timestamps, and peak players.
- Validate against real data in the Docker/PostgreSQL environment.

## Steps

1. Inspect the listed files first and reproduce the current SQL error through the smallest route that executes the summary query.
2. Locate the exact query and confirm which selected columns are functionally one row per target and which values are true aggregates over windows.
3. Choose the least surprising PostgreSQL-compatible fix:
   - expand `GROUP BY` only if it preserves one row per target without accidental duplication;
   - aggregate checkpoint columns only if the value is semantically singular per target;
   - prefer a subquery or CTE if separating checkpoint reads from window aggregation makes the semantics clearer.
4. Apply only the SQL/read-model change needed for this bug.
5. Validate that the error disappears and that returned summary rows remain coherent with the underlying checkpoint and window data.
6. Record the before/after evidence and the semantic decision in the task outcome.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `backend/app/rcon_historical_storage.py`
- `backend/app/rcon_historical_read_model.py`
- `backend/README.md`

## Candidate Files

- `backend/app/rcon_historical_storage.py`
- `backend/app/rcon_historical_read_model.py` only if the route-level behavior or normalization needs a narrow adjustment
- the smallest directly related test or validation helper, if one already exists for RCON historical storage
- `backend/README.md` only if the task discovers that a documented operator command is now wrong

## Expected Files to Modify

- `backend/app/rcon_historical_storage.py`
- a directly related test file only if the repository already has one for this storage/read-model path

Rules:

- Prefer modifying only these files.
- If additional files become necessary, explain why in the task outcome or commit message.
- Do not modify unrelated files.

## Constraints

- Keep the change minimal.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- Do not change Elo/MMR code or rebuild behavior.
- Do not tune PostgreSQL settings.
- Do not change locking behavior between `historical-runner` and `rcon-historical-worker`.
- Do not hide the SQL error by broad exception swallowing; the route should produce valid SQL.

## Validation

Before completing the task ensure:

- Reproduce the current error before the fix with a Docker/PostgreSQL route, for example: `docker compose exec backend python -c "from app.rcon_historical_storage import list_rcon_historical_competitive_summary_rows; print(list_rcon_historical_competitive_summary_rows()[:3])"` or the smallest route that currently logs the PostgreSQL `GROUP BY` error.
- `docker compose up -d postgres backend` passes.
- After the fix, run `docker compose exec backend python -c "from app.rcon_historical_storage import list_rcon_historical_competitive_summary_rows; rows = list_rcon_historical_competitive_summary_rows(); print(len(rows)); print(rows[:3])"` and verify the PostgreSQL `GROUP BY` error is gone.
- Run a direct coherence check against the underlying tables, adapted only for the target keys present in the returned rows: `docker compose exec postgres psql -U hll_vietnam -d hll_vietnam -c "SELECT targets.target_key, checkpoints.last_successful_capture_at, checkpoints.last_run_status, COUNT(windows.id) AS window_count, COALESCE(SUM(windows.sample_count), 0) AS sample_count, MIN(windows.first_seen_at) AS first_seen_at, MAX(windows.last_seen_at) AS last_seen_at, COALESCE(MAX(windows.peak_players), 0) AS peak_players FROM rcon_historical_targets AS targets LEFT JOIN rcon_historical_checkpoints AS checkpoints ON checkpoints.target_id = targets.id LEFT JOIN rcon_historical_competitive_windows AS windows ON windows.target_id = targets.id GROUP BY targets.id, targets.target_key, checkpoints.last_successful_capture_at, checkpoints.last_run_status ORDER BY targets.target_key ASC LIMIT 5;"`.
- Run the functional route that consumes the read model if it is already exposed in the backend, and capture the returned summary shape or logs.
- `python -m compileall backend/app` passes locally or inside the backend container.
- `git diff --name-only` is reviewed and changed files match the expected scope.
- The task outcome includes the reproduced error, the corrected command output, and a short explanation of why the chosen SQL shape preserves result semantics.

## Explicit Exclusions

- Do not change Elo/MMR code, commands, tables, or rebuild instrumentation.
- Do not tune PostgreSQL `max_wal_size` or any general database setting.
- Do not change writer locking, scheduling, or contention behavior between `historical-runner` and `rcon-historical-worker`.
- Do not address Docker Desktop exec `502 Bad Gateway`.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.

## Implementation Notes

- The failing query was located in `backend/app/rcon_historical_storage.py`, inside `list_rcon_historical_competitive_summary_rows()`.
- The functional route that consumes this read is `backend/app/rcon_historical_read_model.py`, through `list_rcon_historical_server_summaries()` and the `/api/historical/server-summary` read model.
- The query previously joined `rcon_historical_targets`, `rcon_historical_checkpoints` and `rcon_historical_competitive_windows`, selected checkpoint columns directly, aggregated window columns, and grouped only by `targets.id`.
- The fix uses a `window_summary` CTE grouped by `target_id` to aggregate only `rcon_historical_competitive_windows` first.
- The outer query now joins `targets` and `checkpoints` to one pre-aggregated row per target, preserving checkpoint fields as per-target values and preserving window metrics as aggregates.
- No Elo/MMR code, PostgreSQL tuning, historical-runner locking, or rcon-historical-worker behavior was changed for this task.

## Validation Outcome

- The old PostgreSQL query shape was reproduced against real PostgreSQL and failed with the expected error:
  - `ERROR: column "checkpoints.last_successful_capture_at" must appear in the GROUP BY clause or be used in an aggregate function`.
- The corrected query shape using the `window_summary` CTE was validated against real PostgreSQL and returned one row per target without the `GROUP BY` error.
- After rebuilding the backend image with the current branch, the loaded runtime function confirmed the corrected query was present:
  - `window_summary` present in `list_rcon_historical_competitive_summary_rows()`: `True`.
- The real backend read path returned coherent PostgreSQL rows:
  - `row_count 6`;
  - `comunidad-hispana-01`: `window_count = 9`, `sample_count = 86`, `peak_players = 3`;
  - `comunidad-hispana-02`: `window_count = 11`, `sample_count = 85`, `peak_players = 99`;
  - targets without competitive windows returned `window_count = 0`, `sample_count = 0`.
- The direct PostgreSQL coherence query over `rcon_historical_targets` and `rcon_historical_competitive_windows` matched the corrected read-model metrics for the returned targets.
- The functional HTTP route was validated after rebuilding `backend`:
  - `GET /api/historical/server-summary?server=all-servers` returned `status: "ok"`, `selected_source: "rcon"`, `fallback_used: false`, `sample_count = 171`;
  - `GET /api/historical/server-summary?server=comunidad-hispana-02` returned `status: "ok"`, `selected_source: "rcon"`, `fallback_used: false`, `window_count = 11`, `sample_count = 85`.
- Result: `done`.
