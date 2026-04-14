# TASK-145-diagnose-and-instrument-elo-rebuild-full-ratings-scoring

## Goal

Diagnose and, where useful inside this scope, instrument the `app.elo_mmr_engine rebuild-full` path so the transition into `ratings-scoring` always leaves deterministic evidence of success, failure, exception, signal, early return, or abnormal termination.

## Context

Local operational validation on branch `task/elo-canonical-rating-monthly` shows that the Elo/MMR full rebuild enters and completes `prepare`, enters and completes `canonical-rebuild`, and then emits `phase-start ratings-scoring`. After that point no `phase-complete ratings-scoring` or final rebuild closure is visible. At that same point `pg_stat_activity` no longer shows `app.elo_mmr_engine` sessions.

A repeated command also produced a Docker Desktop exec `502 Bad Gateway` on `/exec/.../json`. The main backend container stayed `running/healthy` with `RestartCount=0` and `OOMKilled=false`. PostgreSQL recovered after the abrupt restart and became ready again. There is also external noise from `historical-runner` conflicting with `rcon-historical-worker` on the writer lock, plus a separate RCON historical SQL `GROUP BY` bug and WAL checkpoint pressure. Those are relevant context only; this task must isolate Elo/MMR rebuild behavior and not fix those separate problems.

## Scope

- Isolate the `app.elo_mmr_engine rebuild-full` execution from competing daemons while diagnosing.
- Review `app.elo_mmr_engine` and the modules called by `rebuild-full`, especially the transition from `canonical-rebuild` into `ratings-scoring`.
- Add structured logging immediately before and after `ratings-scoring`, plus relevant subphase boundaries inside the scoring path if needed.
- Ensure unhandled exceptions, terminal status, final route, and exit code are observable in logs or CLI output.
- Ensure log output is flushed before long work and before process exit paths.
- Investigate whether subprocesses, multiprocessing, `os._exit`, signals, `sys.exit`, cancellation, custom handlers, daemon shutdown, or abrupt close paths can explain a process disappearing without final output.
- Add a narrow operational option or documented route to execute `rebuild-full` isolated from competing daemons, if the existing Docker workflow does not already make that clear.
- Leave evidence on failure: final log event, terminal state, traceback, exit code, or explicit terminal reason.

## Steps

1. Inspect the listed files first and map the actual call chain for `rebuild-full -> canonical-rebuild -> ratings-scoring -> persistence`.
2. Reproduce the missing terminal event in an isolated Docker run before changing behavior, or document if the current state no longer reproduces it.
3. Add narrowly scoped instrumentation around `ratings-scoring` and its meaningful substeps, including structured events, elapsed time, counters where cheap, and explicit flush points.
4. Add a top-level terminal event for the rebuild command that reports status, final route, and exit code or exception class without swallowing failures.
5. Review and document any code path that can terminate or detach unexpectedly, including `subprocess`, `multiprocessing`, `os._exit`, signals, `sys.exit`, cancellation, or container lifecycle behavior.
6. Validate with the exact Docker checks below and record in the task outcome what was proven and what remains unproven.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/postgres_utils.py`

## Candidate Files

- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/postgres_utils.py`
- `backend/app/writer_lock.py`
- `backend/README.md` only if an isolated operational runbook note is needed
- narrow logging/runtime helper files only if the call chain already uses them

## Expected Files to Modify

- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_storage.py` only if scoring subphase instrumentation belongs beside storage reads
- `backend/app/postgres_utils.py` only if connection/application tagging or flush-safe logging needs a narrow helper change
- `backend/README.md` only if documenting the isolated Docker route is necessary

Rules:

- Prefer modifying only these files.
- If additional files become necessary, explain why in the task outcome or commit message.
- Do not modify unrelated files.

## Constraints

- Keep the change minimal.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- Do not redesign Elo/MMR formulas, ranking semantics, or persistence schema in this task.
- Do not mix this work with RCON historical runner fixes, RCON worker fixes, SQL query fixes, or PostgreSQL tuning.
- Do not mask failures by converting them to success responses.
- Keep output useful for operators and deterministic enough for a future investigation if Docker exec itself fails.

## Validation

Before completing the task ensure:

- `docker compose up -d postgres backend` passes.
- `docker compose stop historical-runner rcon-historical-worker` is run before the isolated rebuild validation.
- `docker compose ps` confirms `postgres` and `backend` are running and `historical-runner` and `rcon-historical-worker` are not running for the isolated run.
- `docker compose exec postgres psql -U hll_vietnam -d hll_vietnam -c "SELECT pid, application_name, state, wait_event_type, wait_event, query FROM pg_stat_activity WHERE application_name LIKE 'app.elo_mmr_engine%' ORDER BY pid;"` is captured before or during the run as relevant.
- `docker compose exec backend sh -lc 'python -u -m app.elo_mmr_engine rebuild-full > /app/runtime/elo-rebuild-full-ratings-scoring-validation.log 2>&1; code=$?; echo "rebuild-full-exit-code=$code" | tee -a /app/runtime/elo-rebuild-full-ratings-scoring-validation.log; exit $code'` is run.
- `docker compose exec backend sh -lc 'grep -E "phase-start|phase-complete|ratings-scoring|terminal|exit|traceback|exception" /app/runtime/elo-rebuild-full-ratings-scoring-validation.log | tail -n 120'` shows either `phase-complete` for `ratings-scoring` and a final terminal event, or a deterministic failure event with traceback/reason.
- `docker compose exec postgres psql -U hll_vietnam -d hll_vietnam -c "SELECT application_name, state, count(*) FROM pg_stat_activity WHERE application_name LIKE 'app.elo_mmr_engine%' GROUP BY application_name, state ORDER BY application_name, state;"` verifies no unexpected lingering `app.elo_mmr_engine` sessions after completion/failure.
- `docker compose exec postgres psql -U hll_vietnam -d hll_vietnam -c "SELECT 'elo_mmr_player_ratings' AS table_name, count(*) FROM elo_mmr_player_ratings UNION ALL SELECT 'elo_mmr_match_results', count(*) FROM elo_mmr_match_results UNION ALL SELECT 'elo_mmr_monthly_rankings', count(*) FROM elo_mmr_monthly_rankings;"` verifies Elo/MMR tables after the run.
- `python -m compileall backend/app` passes locally or inside the backend container.
- `git diff --name-only` is reviewed and changed files match the expected scope.
- The task outcome states exactly what was proven, what was not proven, and whether the run ended with visible `phase-complete ratings-scoring` or an equivalent terminal event.

## Explicit Exclusions

- Do not fix `historical-runner`.
- Do not fix `rcon-historical-worker`.
- Do not tune PostgreSQL `max_wal_size` or general WAL/checkpoint settings.
- Do not correct the RCON historical SQL `GROUP BY` bug.
- Do not change writer-lock behavior except for logging that is strictly required to identify this rebuild path.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.

## Implementation Notes

- `backend/app/elo_mmr_engine.py` now emits structured terminal evidence for CLI rebuild operations.
- `_run_logged_phase` now emits `phase-error` with exception type, message and traceback before re-raising.
- `ratings-scoring` now emits internal step start/complete/error events for source policy selection, RCON read-model selection, canonical row loading, canonical grouping, grouped match scoring, player-rating flattening and monthly materialization.
- `score-grouped-matches` emits bounded progress checkpoints with processed and total match counts.
- CLI rebuild operations now emit `rebuild-command-start` and `rebuild-terminal` with status, exit code, terminal phase and totals on success; errors emit exception details and traceback before the original failure propagates.
- No subprocess, multiprocessing, `os._exit`, custom signal handler, or additional `sys.exit` path was found in `backend/app/elo_mmr_engine.py` or its direct Elo/MMR modules during the scoped search. The only `SystemExit` in the module remains the normal `if __name__ == "__main__": raise SystemExit(main())` wrapper.

## Validation Outcome

- Local `python -m compileall backend/app` passed after the implementation.
- Local `python -m app.elo_mmr_engine --help` from `backend/` passed and showed the existing command split.
- `docker compose up -d --build postgres backend` passed before the Docker validation run.
- `docker compose stop historical-runner rcon-historical-worker` passed and `docker compose ps -a historical-runner rcon-historical-worker postgres backend` confirmed `historical-runner` and `rcon-historical-worker` were stopped before the isolated run.
- Initial `pg_stat_activity` validation via Docker showed zero `app.elo_mmr_engine%` sessions before the run.
- Isolated command executed: `docker compose exec backend sh -lc 'python -u -m app.elo_mmr_engine rebuild-full > /app/runtime/elo-rebuild-full-ratings-scoring-validation.log 2>&1; code=$?; echo "rebuild-full-exit-code=$code" | tee -a /app/runtime/elo-rebuild-full-ratings-scoring-validation.log; exit $code'`.
- The command did not return before the 20 minute tool timeout. After that, Docker Desktop started returning `500 Internal Server Error` for `docker compose`, `docker ps` and `docker info`, preventing completion of Docker-based validation.
- The captured log at `backend/runtime/elo-rebuild-full-ratings-scoring-validation.log` proves the rebuild completed `prepare`, completed `canonical-rebuild`, entered `ratings-scoring`, loaded `1,080,664` canonical rows, grouped `9,751` matches, and progressed inside `score-grouped-matches` through `7,199 / 9,751` matches before output stopped.
- Host-side Postgres connectivity check showed TCP 5432 open, but a psycopg connection with `connect_timeout=5` failed with `ConnectionTimeout connection timeout expired`, so `pg_stat_activity` and final Elo/MMR table-count validation could not be completed after Docker Desktop entered the failed state.
- Current task status remains `in-progress` rather than `done` because the required Docker terminal-event and table-count validation could not be completed in this degraded Docker Desktop/PostgreSQL state.

## Administrative Closure

Status: done.

The original problem was that `app.elo_mmr_engine rebuild-full` appeared to disappear after entering `ratings-scoring`, without `phase-complete ratings-scoring`, terminal event, traceback, exit code, or final table-count evidence.

TASK-145 added deterministic instrumentation around CLI rebuild operations and `ratings-scoring`: structured phase start/complete/error events, scoring substep events, progress for `score-grouped-matches`, exception payloads with traceback, explicit flushes, and `rebuild-terminal` with status, exit code, terminal phase, and totals.

The instrumentation reduced the unknown failure to `score-grouped-matches`: the isolated rebuild loaded `1,080,664` canonical rows, counted `9,751` grouped matches, and previously stopped around `7199 / 9751` without terminal evidence while Docker Desktop degraded.

TASK-147 subsequently addressed that scoped operational blocker by reducing memory/I/O pressure in `score-grouped-matches` through incremental grouped-match iteration, batched match-result persistence, streaming monthly summaries, and explicit release of large temporary state.

Final validation evidence in `backend/runtime/elo-rebuild-full-task147-validation.log` demonstrates the full rebuild completed against the real dataset: `score-grouped-matches` reached `9751 / 9751`, `phase-complete ratings-scoring` was emitted, and `rebuild-terminal` reported `status=ok`, `exit_code=0`.

Final persisted Elo/MMR totals were plausible for the dataset: `345,115` player ratings, `2,161,328` match results, `558,688` monthly rankings, and `56` monthly checkpoints. The final check also showed no lingering `app.elo_mmr_engine%` sessions.
