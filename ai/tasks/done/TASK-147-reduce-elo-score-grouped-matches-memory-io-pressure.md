# TASK-147-reduce-elo-score-grouped-matches-memory-io-pressure

## Goal

Reduce memory and I/O pressure in `app.elo_mmr_engine rebuild-full` during `score-grouped-matches` so the command can complete against the current large PostgreSQL dataset while preserving Elo/MMR result semantics.

## Context

TASK-145 already instrumented `app.elo_mmr_engine rebuild-full` and made the ratings-scoring failure boundary observable. The rebuild no longer disappears without context: it completes `prepare`, completes `canonical-rebuild`, enters `ratings-scoring`, loads `1,080,664` canonical rows, groups `9,751` matches, then stalls inside `score-grouped-matches` around `7199 / 9751`.

The observed process does not emit `phase-complete ratings-scoring` or `rebuild-terminal`. Runtime inspection showed the Python process entering `D (disk sleep)` / `wait_on_page_bit_common` with roughly `15 GB` RSS. PostgreSQL did not show an active Elo/MMR query at that point, only the rebuild advisory-lock session idle. Docker Desktop degraded with `500 Internal Server Error` during the long run, likely as a collateral effect of the pressure from the rebuild process rather than as the primary application failure.

This task must not reopen the base instrumentation done in TASK-145 except for narrow metrics needed to validate the memory/I/O reduction.

## Scope

- Diagnose why `score-grouped-matches` retains or creates excessive in-memory state around the current real dataset.
- Redesign the scoring path to avoid materializing more match/player data than needed at one time.
- Preserve the existing Elo/MMR scoring semantics and output contracts.
- Keep the rebuild restart/operation shape compatible with the existing `rebuild-full` command.
- Add only narrow memory/progress evidence if required to prove the improvement.
- Validate against the current Docker/PostgreSQL dataset, not only synthetic data.

## Options To Evaluate

- Process grouped matches in bounded batches or chunks instead of one large in-memory pass.
- Stream canonical rows or grouped match data where feasible instead of loading and retaining all structures at once.
- Reduce intermediate per-match and per-player structures retained after each match/group is scored.
- Explicitly release large temporary collections between substeps if the implementation proves they remain referenced.
- Persist scored results incrementally, or introduce internal checkpoints, only if that is the smallest safe way to cap memory and I/O pressure.
- Add cheap memory/progress metrics around `score-grouped-matches` to show whether RSS growth is bounded and whether the run passes the previous `7199 / 9751` stall point.

## Steps

1. Inspect the listed files first and map the current `ratings-scoring -> score-grouped-matches -> persistence` data flow, focusing on where lists, dictionaries, per-player rating state, and match result collections are retained.
2. Reproduce or review the TASK-145 evidence for the stall point before changing behavior, including the last progress event around `7199 / 9751`, process state, RSS, and PostgreSQL activity.
3. Identify the smallest change that caps memory/I/O pressure while preserving result semantics.
4. Implement the selected approach, preferring bounded iteration/chunking and narrower retained state over broad rewrites.
5. Add or adjust only the minimal logging/metrics needed to validate memory and progress across the previous failure point.
6. Validate with the real Docker/PostgreSQL dataset in an isolated run with competing daemons stopped.
7. Compare final Elo/MMR counts and representative leaderboard/player outputs against the pre-change expectations where practical.
8. Document what was proven, any remaining performance risk, and whether Docker still degrades during the isolated run.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/tasks/in-progress/TASK-145-diagnose-and-instrument-elo-rebuild-full-ratings-scoring.md`
- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/postgres_utils.py`

## Candidate Files

- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/postgres_utils.py` only if a narrow cursor/streaming helper or connection option is needed
- a focused Elo/MMR test or validation helper only if one already exists and directly covers this scoring path
- `backend/README.md` only if the operator runbook for large rebuilds changes

## Expected Files to Modify

- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_storage.py` only if storage-level streaming or batched read/write behavior belongs there

Rules:

- Prefer modifying only these files.
- If additional files become necessary, explain why in the task outcome or commit message.
- Do not modify unrelated files.
- Do not modify TASK-145 as part of this task.

## Constraints

- Keep the change minimal and focused on `score-grouped-matches` memory/I/O pressure.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- Do not redesign Elo/MMR formulas, ranking semantics, API payload contracts, or schema unless strictly required to complete the rebuild safely.
- Do not remove the instrumentation from TASK-145.
- Do not mask failures by turning exceptions into successful terminal events.
- Do not tune Docker Desktop or PostgreSQL global settings as the primary solution.
- Do not change `historical-runner`, `rcon-historical-worker`, writer-lock policy, or unrelated RCON historical behavior.

## Validation

Before completing the task ensure:

- `docker compose up -d --build postgres backend` passes.
- `docker compose stop historical-runner rcon-historical-worker` is run before the isolated rebuild validation.
- `docker compose ps -a postgres backend historical-runner rcon-historical-worker` confirms `postgres` and `backend` are running/healthy and the competing daemons are stopped.
- `docker version`, `GET /health`, and `SELECT 1` in PostgreSQL are captured before the run.
- A full isolated rebuild is run with unbuffered output and complete log capture, for example:
  - `docker compose exec backend sh -lc 'python -u -m app.elo_mmr_engine rebuild-full > /app/runtime/elo-rebuild-full-score-grouped-matches-validation.log 2>&1; code=$?; echo "rebuild-full-exit-code=$code" | tee -a /app/runtime/elo-rebuild-full-score-grouped-matches-validation.log; exit $code'`
- During the run, capture `pg_stat_activity` for `application_name LIKE 'app.elo_mmr_engine%'` at least once before `score-grouped-matches`, once near or beyond the previous `7199 / 9751` point, and once after completion/failure.
- Capture memory/progress evidence sufficient to show whether RSS remains bounded and whether `score-grouped-matches` advances beyond the previous stall point.
- The log proves one of these outcomes:
  - successful completion with `phase-complete ratings-scoring` and `rebuild-terminal` or equivalent terminal success evidence;
  - deterministic failure with `phase-error`, traceback, terminal event, and a clear subphase;
  - environment failure clearly attributable to Docker/host degradation rather than application logic.
- The run must demonstrate that `score-grouped-matches` passes `7199 / 9751`; if it does not, the task must remain `in-progress` or be marked blocked with evidence.
- After completion, verify there are no unexpected lingering `app.elo_mmr_engine%` sessions.
- Verify final Elo/MMR table counts:
  - `elo_mmr_player_ratings`
  - `elo_mmr_match_results`
  - `elo_mmr_monthly_rankings`
- Run `python -m compileall backend/app` locally or inside the backend container.
- Review `git diff --name-only` and confirm changed files match the expected scope.
- Document the observed memory behavior, the maximum progress reached, final terminal event, final table counts, and whether Docker Desktop remained stable.

## Explicit Exclusions

- Do not reopen TASK-145 except to read its evidence and preserve its instrumentation.
- Do not fix or change `historical-runner`.
- Do not fix or change `rcon-historical-worker`.
- Do not change RCON historical summary SQL or TASK-146 work.
- Do not tune PostgreSQL `max_wal_size`, Docker Desktop configuration, or global host memory settings as the primary solution.
- Do not change frontend behavior.
- Do not add backend API endpoints.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 250 lines when feasible because this may require a focused data-flow refactor.
- Split follow-up tasks if the safe solution requires schema changes, durable checkpointing, or broader rebuild orchestration changes.

## Outcome

Status: done.

Implemented a bounded scoring flow for `score-grouped-matches`: grouped matches are iterated incrementally, match results are persisted in batches of `10,000`, monthly ranking inputs are summarized while scoring instead of reloading all persisted match-results, and large temporary collections are explicitly released between substeps. The change preserves the existing rating/monthly output contracts while reducing retained match-result state during the real rebuild.

Validation was run against the current Docker/PostgreSQL dataset with `historical-runner` and `rcon-historical-worker` stopped. Full log: `backend/runtime/elo-rebuild-full-task147-validation.log`.

Observed validation:

- `docker compose up -d --build postgres backend` passed.
- `docker compose stop historical-runner rcon-historical-worker` passed.
- `docker compose ps -a postgres backend historical-runner rcon-historical-worker` showed `postgres` and `backend` healthy, with both competing daemons stopped.
- `docker version`, `GET /health`, and PostgreSQL `SELECT 1` succeeded.
- `python -m compileall backend/app` succeeded.
- `rebuild-full` reached `load-canonical-match-rows` with `1,080,664` rows and `count-canonical-match-groups` with `9,751` groups.
- `score-grouped-matches` passed the previous stall point: `7199 / 9751`, then completed `9751 / 9751`.
- Peak observed `VmHWM` in the rebuild log was `11,037,340 KiB`; RSS stayed below the previously observed ~15 GB failure region and the process completed.
- `monthly-materialization` used `streaming-score-grouped-matches` summaries with `558,688` monthly player groups.
- `phase-complete ratings-scoring` was emitted.
- `rebuild-terminal` was emitted with `status=ok`, `exit_code=0`.
- Final persisted counts were `345,115` player ratings, `2,161,328` match results, `558,688` monthly rankings, and `56` monthly checkpoints.
- Final `pg_stat_activity` check showed `0` lingering `app.elo_mmr_engine%` sessions.
- Docker remained responsive after the run.
