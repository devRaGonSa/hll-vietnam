# TASK-127

## Goal

Eliminate Python module-entrypoint bootstrap warnings caused by eager package imports when running `python -m app.<module>` commands.

## Context

The current `backend/app/__init__.py` imports high-level runtime surfaces such as `main`, `payloads`, and `routes` during package import. That eager import chain can preload the same module that an operator is trying to execute through `python -m`, which leads to the known runtime warning about the module already being present in `sys.modules` before execution. The warning currently affects module-entrypoint workflows such as `python -m app.main`, `python -m app.elo_mmr_engine`, and `python -m app.rcon_historical_worker`.

Future implementation must make package import hygiene more surgical so importing `app` does not eagerly import runtime module-entrypoints. Public package behaviour should stay as stable as reasonably possible, but package bootstrap must stop preloading modules that are also expected to behave as CLI entrypoints.

## Steps

1. Inspect the listed files first and trace which imports in `backend/app/__init__.py` preload module-entrypoint surfaces or their transitive dependencies during package import.
2. Refactor package bootstrap so importing `app` no longer eagerly imports runtime entrypoint modules, while preserving stable public package behaviour as far as reasonably possible through deferred imports or narrower export surfaces.
3. Validate at least the listed `python -m app.*` commands and explicitly confirm that the previous bootstrap warning no longer appears.

## Files to Read First

- `AGENTS.md`
- `backend/app/__init__.py`
- `backend/app/main.py`
- `backend/app/routes.py`
- `backend/app/payloads.py`
- `backend/app/elo_mmr_engine.py`
- `backend/app/rcon_historical_worker.py`

## Expected Files to Modify

- `backend/app/__init__.py`
- a minimal number of directly related bootstrap or import-surface files if strictly necessary

Rules:

- Prefer modifying only these files.
- If additional files become necessary, explain why in the task outcome or commit message.
- Do not modify unrelated files.
- Keep the work surgical and limited to package bootstrap import hygiene.
- Do not change storage, formulas, telemetry, or payload semantics in this task.

## Constraints

- Keep the change minimal.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- Do not implement backend functionality unless the task explicitly requires it.
- Importing `app` must not eagerly import runtime module-entrypoints.
- `python -m app.main` must no longer emit the warning.
- `python -m app.elo_mmr_engine` must no longer emit the warning.
- `python -m app.rcon_historical_worker` must no longer emit the warning.
- Public package behaviour should remain stable as far as reasonably possible.

## Validation

Before completing the task ensure:

- `python -m compileall backend/app` passes
- `python -m app.main` is run
- `python -m app.elo_mmr_engine leaderboard --server all-servers --limit 1` is run
- `python -m app.rcon_historical_worker capture --target comunidad-hispana-01` or another safe targeted command path is run
- it is explicitly demonstrated that the previous warning no longer appears
- `git diff --name-only` is reviewed
- `git status --short` is reviewed
- no unrelated files were modified
- documentation remains consistent with the repository state
- the final implementation response explicitly confirms whether push happened or was deferred because more pending tasks remain

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
- replaced eager package bootstrap imports in `backend/app/__init__.py` with lazy attribute resolution
- preserved the public package export surface through `__getattr__`, `__dir__`, and the existing lazy proxy functions
- kept the change surgical and limited to package bootstrap import hygiene

Validation run:

- `python -m compileall backend/app`
- controlled subprocess run of `python -m app.main`
- `python -m app.elo_mmr_engine leaderboard --server all-servers --limit 1`
- `python -m app.elo_mmr_engine --help`
- `python -m app.rcon_historical_worker capture --target comunidad-hispana-01`
- `python -m app.rcon_historical_worker --help`
- `git diff --name-only`
- `git status --short`

Validation results:

- `python -m compileall backend/app` passed
- `python -m app.main` no longer emitted the previous module bootstrap warning; the process failed later with a local socket permission error (`WinError 10013`) while trying to bind the server
- `python -m app.elo_mmr_engine leaderboard --server all-servers --limit 1` completed without the previous module bootstrap warning
- `python -m app.elo_mmr_engine --help` completed without the previous module bootstrap warning
- `python -m app.rcon_historical_worker capture --target comunidad-hispana-01` no longer emitted the previous module bootstrap warning; the command failed later because no RCON targets were configured in `HLL_BACKEND_RCON_TARGETS`
- `python -m app.rcon_historical_worker --help` completed without the previous module bootstrap warning
- `git diff --name-only` showed only `backend/app/__init__.py` and the already-in-progress `backend/app/historical_runner.py`
- `git status --short` confirmed no unrelated tracked file modifications

Branch and delivery state:

- branch: `task/elo-canonical-rating-monthly`
- final commit SHA: not created in this pass
- push: intentionally deferred because more pending tasks remain
