# TASK-124

## Goal

Refactor the historical runner CLI so manual operations are explicit, bounded, observable, and phase-separated.

## Context

The current historical runner in `backend/app/historical_runner.py` always enters the generic loop-oriented execution shape, even when the operator uses `--max-runs 1` with one-shot intent. The current refresh cycle also bundles primary RCON capture, classic historical fallback, snapshot generation, and possible Elo/MMR rebuild work inside one combined run path. That makes manual execution feel open-ended, hides operator intent, and slows debugging when the user only wants a narrowly scoped action such as a snapshot refresh.

Future implementation must introduce a clear split between long-running daemon usage and explicit one-shot/manual usage, while also separating major phases so operators can run only the intended operation. The service/daemon loop currently used by automation or containers must remain available, but manual CLI paths must become deterministic and self-describing.

## Steps

1. Inspect the listed files first and map the current call chain from CLI parsing to `_run_refresh_with_retries()`, `_run_primary_rcon_capture()`, classic fallback policy resolution, snapshot generation, and any Elo/MMR follow-up.
2. Refactor the CLI shape so the runner exposes a dedicated one-shot/manual path distinct from the long-running loop path, and add explicit phase-oriented manual modes for at least full historical cycle, snapshots-only, capture-only, and refresh-only behaviour.
3. Keep daemon semantics available for service use, validate that one-shot/manual commands run exactly once without loop-oriented messaging, and document any small CLI naming or output contract decision needed to preserve operator clarity.

## Files to Read First

- `AGENTS.md`
- `backend/app/historical_runner.py`
- `backend/app/historical_snapshots.py`
- `backend/app/rcon_historical_worker.py`
- `backend/app/config.py`
- any CLI entrypoint wiring directly related to these commands

## Expected Files to Modify

- `backend/app/historical_runner.py`
- a minimal number of directly related CLI or entrypoint files if strictly required by the final parser shape

Rules:

- Prefer modifying only these files.
- If additional files become necessary, explain why in the task outcome or commit message.
- Do not modify unrelated files.
- Keep the work focused on CLI execution shape, operator clarity, and phase separation.
- Do not change historical data semantics, snapshot payload schema, Elo/MMR formulas, or frontend behaviour in this task.

## Constraints

- Keep the change minimal.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- Do not implement backend functionality unless the task explicitly requires it.
- Manual one-shot commands must not print loop-oriented messaging such as `Press Ctrl+C to stop.` or daemon-style loop banners.
- One-shot mode must run exactly once, emit structured final output, and return promptly to the shell.
- Snapshots-only mode must call only the snapshot materialization path needed for snapshot refresh.
- Manual snapshots-only execution must not implicitly trigger unrelated fallback ingestion or Elo/MMR rebuild work.
- The existing service or daemon loop path must remain available with periodic semantics for containerized or automated use.

## Validation

Before completing the task ensure:

- `python -m compileall backend/app` passes
- a one-shot historical command is demonstrated to run once and exit
- snapshots-only mode is demonstrated to run without loop-oriented messaging
- snapshots-only mode is demonstrated not to trigger fallback ingestion or Elo/MMR rebuild work
- `git diff --name-only` is reviewed
- `git status --short` is reviewed
- no unrelated files were modified
- documentation remains consistent with the repository state
- the final implementation response states modified files, validations run, validation results, branch name, final commit SHA, and whether push was executed or intentionally deferred because more pending tasks remain

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.

## Execution Notes

### 2026-03-31 worker pass

Status:

- completed
- ready to move to `ai/tasks/done`

Completed in this pass:

- moved the task from `ai/tasks/pending` to `ai/tasks/in-progress`
- refactored `backend/app/historical_runner.py` to expose explicit `run` and `loop` modes
- added explicit manual `--phase` handling for `full`, `snapshots`, `capture`, and `refresh`
- kept loop-oriented banner and periodic semantics under `loop` only
- made manual one-shot execution emit one structured JSON payload and return promptly

Validation run:

- `python -m compileall backend/app`
- `python -m app.historical_runner run --phase snapshots --retries 0`
- `python -m app.historical_runner loop --max-runs 1 --retries 0 --retry-delay 0 --interval 1`
- `git diff --name-only`
- `git status --short`

Validation results:

- `python -m compileall backend/app` passed
- one-shot snapshots mode ran exactly once and exited
- one-shot snapshots mode did not print loop-oriented messaging such as `Press Ctrl+C to stop.`
- snapshots-only mode reported `refresh_result.status: skipped` and `elo_mmr_result.status: skipped`
- bounded loop mode retained loop-oriented startup messaging and executed a single capped run
- the bounded loop validation exited with a controlled single-run error because no RCON targets were configured in `HLL_BACKEND_RCON_TARGETS`
- `git diff --name-only` showed only `backend/app/historical_runner.py`
- `git status --short` confirmed no unrelated tracked file modifications

Branch and delivery state:

- branch: `task/elo-canonical-rating-monthly`
- final commit SHA: not created in this pass
- push: intentionally deferred because more pending tasks remain
