# TASK-123-elo-final-merge-cleanup-and-materialization-refresh

## Goal

Perform the final pre-merge cleanup and refresh for the Elo/MMR branch so the branch is safe to merge into `main`, with no accidental runtime or data artifacts, with the latest backend code actually served at runtime, and with Elo/MMR payloads showing a fully coherent surface after a fresh rebuild and materialization pass.

## Context

The current Elo/MMR branch already contains the practical v3 surface work and the final payload-surface normalization work, including:

- explicit non-null surface values for `comparison_path` and `role_primary`
- explicit non-null surface value for `monthly_aggregation_lineage`
- explicit checkpoint contract exposure
- practical v3 naming in payload surface and auditability helpers

However, the branch still needs one final controlled pass before merge because:

1. accidental runtime or data artifacts are still present in the branch diff and must not be merged:
   - `backend/backend/data/elo_mmr_task001_validation.sqlite3`
   - `backend/backend/data/hll_vietnam_dev.sqlite3`
   - `backend/data/hll_vietnam_dev.writer.lock`

2. the published repo code appears to contain the intended payload normalization, but runtime HTTP checks still showed mixed version values across:
   - top-level model and auditability surface
   - nested `persistent_rating`
   - nested `monthly_ranking`
   - nested `components`
   - nested `rating_breakdown`

3. the leaderboard top ordering must be confirmed against the latest rebuilt and materialized Elo/MMR state, not against stale persisted rows or stale checkpoint state

This task is not a new Elo feature task. It is a final cleanup, rebuild, and validation task so the branch can be merged safely.

## Steps

1. Inspect the current branch diff and remove accidental runtime or data artifacts from version control if they are still tracked in the branch.
2. Confirm that only intended source-code, docs, and task files remain in the final diff.
3. Rebuild or recreate the backend runtime so the running service definitely serves the latest pushed backend code.
4. Run the required Elo/MMR rebuild and materialization flow so persisted rows and monthly checkpoints reflect the current branch logic.
5. Validate that the leaderboard uses the current materialized state and not stale rows or stale checkpoints.
6. Validate that the player endpoint uses the same coherent version surface as the leaderboard.
7. Verify that version naming is coherent across all of these payload layers:
   - `model_contract`
   - `auditability.contracts`
   - `persistent_rating`
   - `monthly_ranking`
   - `components`
   - `rating_breakdown`
8. Verify that the leaderboard top results are refreshed after the rebuild and materialization pass.
9. Commit and push only if all validations pass and this task is being implemented in a future execution.

## Files to Read First

- `AGENTS.md`
- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_models.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/payloads.py`
- `docs/elo-full-system-contracts-surface-and-auditability.md`
- `docs/elo-mmr-monthly-ranking-design.md`

## Expected Files to Modify

Only if needed during future implementation:

- `backend/app/payloads.py`
- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_storage.py`
- docs directly related to Elo/MMR surface wording
- git index state for accidental tracked runtime or data artifacts

Expected removals from version control if still present:

- `backend/backend/data/elo_mmr_task001_validation.sqlite3`
- `backend/backend/data/hll_vietnam_dev.sqlite3`
- `backend/data/hll_vietnam_dev.writer.lock`

## Constraints

- Do not open a new Elo feature iteration.
- Do not add new telemetry families.
- Do not change frontend.
- Do not expand the model scope.
- Do not change formulas unless a real bug prevents correct rebuild or materialization.
- Keep the future implementation strictly limited to:
  - branch cleanup
  - runtime refresh
  - Elo/MMR rebuild and materialization refresh
  - final payload and version consistency validation
- If the runtime HTTP surface still shows mixed old and new versions after rebuild, fix the minimum necessary code path only.
- Do not merge or delete unrelated branch work.

Push policy for future execution:
- If this task is implemented and other pending tasks from the same Elo backlog batch still remain open, the worker must not push yet.
- In that case, the worker may commit locally if the repo workflow requires it, but final push must wait until the last pending task of the same backlog batch is completed.
- If this task is the last remaining pending task in the same Elo backlog batch and final validation passes, the worker must commit and push.
- The final implementation response must always state:
  - modified files
  - validations run
  - validation results
  - branch name
  - final commit SHA
  - whether push was executed or intentionally deferred because more pending tasks from the same batch remain
- No task should claim final backlog completion without the required final push, unless a blocking error is documented.

## Validation

Minimum required validation for future implementation:

1. `git diff --name-only`
2. `git status --short`
3. `python -m compileall backend/app`
4. backend runtime refresh or recreate so the latest code is actually served
5. Elo/MMR rebuild and materialization refresh
6. HTTP validation of:
   - `/api/historical/elo-mmr/leaderboard`
   - `/api/historical/elo-mmr/player?server=all-servers&player=steam:76561198071222648`

The future validation must explicitly prove:

- accidental runtime or data artifacts are no longer part of the intended merge diff
- leaderboard and player endpoints both respond successfully
- top-level and nested version fields no longer contradict each other
- `monthly_checkpoint_contract_version` is explicit and correct
- `monthly_aggregation_lineage` is explicit and not null or opaque
- `comparison_path` and `role_primary` are explicit and not null or opaque
- the leaderboard top is refreshed from the current rebuilt and materialized state

## Change Budget

Small and surgical.

This is a final cleanup, refresh, and validation task only, not a new Elo/MMR development task.

## Execution Notes

### 2026-03-27 worker pass

Status:

- in progress
- not ready to move to `ai/tasks/done`

Completed in this pass:

- moved the task from `ai/tasks/pending` to `ai/tasks/in-progress`
- removed the tracked runtime/data artifacts from version control:
  - `backend/backend/data/elo_mmr_task001_validation.sqlite3`
  - `backend/backend/data/hll_vietnam_dev.sqlite3`
  - `backend/data/hll_vietnam_dev.writer.lock`
- ran `git status --short`
- ran `git diff --name-only`
- ran `python -m compileall backend/app`
- validated the live HTTP Elo/MMR endpoints against the current branch code on a local high port:
  - `/api/historical/elo-mmr/leaderboard?server=all-servers&limit=3`
  - `/api/historical/elo-mmr/player?server=all-servers&player=steam:76561198071222648`

Observed validation results:

- leaderboard endpoint returned `status: ok`
- player endpoint returned `status: ok`
- version naming was coherent across:
  - top-level model and auditability surfaces
  - nested `persistent_rating`
  - nested `monthly_ranking`
  - nested `components`
  - nested `rating_breakdown`
- `monthly_checkpoint_contract_version` was explicit as `elo-mmr-monthly-checkpoint-v4`
- `monthly_aggregation_lineage` was explicit and non-null
- `comparison_path` and `role_primary` were explicit and non-null
- current top 3 at validation time:
  1. `Baldomero W.`
  2. `%YoniVergas%`
  3. `FallenWhiteHawk`

Blocking issue still preventing completion:

- `python -m app.elo_mmr_engine rebuild` did not complete within a 15 minute execution window against the current local SQLite dataset
- direct monthly rematerialization from persisted results also did not complete within a 10 minute execution window
- both long-running attempts left stale writer-lock files after termination and those stale lock files were cleaned up
- because the fresh rebuild/materialization pass did not complete, this worker pass could not prove that the leaderboard was refreshed from a newly rebuilt checkpoint during this execution

Required follow-up before closing the task:

- run the rebuild/materialization flow to successful completion in an environment where the current local SQLite dataset can finish the operation
- re-run the HTTP validation after that successful rebuild/materialization
- only then move this task to `ai/tasks/done`

### 2026-04-15 administrative close

Status: done.

This task is closed administratively because the original blocking criteria are now covered by later branch work and current runtime validation.

Original scope now covered:

- The accidental runtime/data artifacts named by this task are no longer tracked and are not present on disk:
  - `backend/backend/data/elo_mmr_task001_validation.sqlite3`
  - `backend/backend/data/hll_vietnam_dev.sqlite3`
  - `backend/data/hll_vietnam_dev.writer.lock`
- Later Elo/MMR stabilization work made `app.elo_mmr_engine rebuild-full` complete against the real PostgreSQL dataset. TASK-147 documents final successful rebuild evidence with `phase-complete ratings-scoring` and `rebuild-terminal` reporting `status=ok`, `exit_code=0`.
- The current runtime has live historical data, fresh historical snapshots/materializations, populated Elo/MMR persisted tables, and working Elo/MMR HTTP payloads.
- Later daemon/runtime and writer-lock tasks validated that reactivating `historical-runner` and `rcon-historical-worker` does not empty the Elo/MMR tables.

Administrative validation executed on 2026-04-15:

- `git status --short`
- `docker compose ps -a postgres backend historical-runner rcon-historical-worker`
- `docker compose exec -T postgres psql -U hll_vietnam -d hll_vietnam -c "SELECT COUNT(*) AS historical_matches, MIN(ended_at) AS first_ended_at, MAX(ended_at) AS last_ended_at FROM historical_matches; SELECT COUNT(*) AS ratings_count FROM elo_mmr_player_ratings; SELECT COUNT(*) AS match_results_count FROM elo_mmr_match_results; SELECT COUNT(*) AS monthly_rankings_count FROM elo_mmr_monthly_rankings; SELECT COUNT(*) AS monthly_checkpoints_count FROM elo_mmr_monthly_checkpoints;"`
- HTTP validation of:
  - `/api/historical/elo-mmr/leaderboard?server=all-servers&limit=5`
  - `/api/historical/elo-mmr/player?server=all-servers&player=steam:76561198071222648`
- `docker compose exec -T postgres psql -U hll_vietnam -d hll_vietnam -c "SELECT scope_key, month_key, model_version, formula_version, contract_version, player_count, eligible_player_count, generated_at, updated_at FROM elo_mmr_monthly_checkpoints ORDER BY updated_at DESC LIMIT 5; SELECT scope_key, month_key, player_name, monthly_rank_score, current_mmr, valid_matches, eligible, updated_at FROM elo_mmr_monthly_rankings WHERE scope_key='all-servers' ORDER BY monthly_rank_score DESC LIMIT 5;"`
- `docker compose exec -T postgres psql -U hll_vietnam -d hll_vietnam -c "SELECT COUNT(*) AS snapshot_payloads, MAX(generated_at) AS latest_generated_at, BOOL_OR(is_stale) AS any_stale FROM historical_snapshot_payloads;"`

Observed close evidence:

- `historical_matches = 9852`, with first `ended_at = 2024-05-17 20:48:40+00` and last `ended_at = 2026-04-14 21:36:54+00`.
- `elo_mmr_player_ratings = 345150`.
- `elo_mmr_match_results = 2161476`.
- `elo_mmr_monthly_rankings = 558762`.
- `elo_mmr_monthly_checkpoints = 58`.
- `historical_snapshot_payloads = 44`, latest `generated_at = 2026-04-15 10:00:22.365224+00`, `any_stale = false`.
- Elo/MMR leaderboard endpoint returned `status=ok`, `found=true`, 5 items, `generated_at = 2026-04-15T09:16:03.427309Z`, `month_key = 2026-04`.
- Elo/MMR player endpoint returned `status=ok`, `found=true`, with a populated `profile`.
- Latest checkpoint rows expose `model_version = elo-pdf-v3-monthly-practical`, `formula_version = elo-pdf-v3-monthly-rev4`, and `contract_version = elo-mmr-monthly-checkpoint-v4`.

No source-code implementation was performed as part of this administrative close.
