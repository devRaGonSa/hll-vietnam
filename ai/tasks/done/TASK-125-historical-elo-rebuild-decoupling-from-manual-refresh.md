# TASK-125

## Goal

Remove the implicit coupling between manual historical refresh flows and full Elo/MMR rebuilds.

## Context

The current historical runner can trigger `rebuild_elo_mmr_models()` during a normal historical refresh cycle when rebuild policy conditions are met. In practice, that means an operator trying to perform a manual historical refresh or snapshot-oriented maintenance run can unexpectedly launch heavyweight work such as canonical fact rebuild, full match rescoring, persistent rating replacement, and monthly ranking rematerialization. That coupling is operationally unsafe and makes manual refresh behaviour harder to predict.

Future implementation must make full Elo/MMR rebuild an explicit and opt-in operation instead of an implicit side effect of a manual historical refresh path. Operator-facing output must also make it obvious whether Elo/MMR work was skipped, a lightweight follow-up was used, or a full rebuild was explicitly requested.

## Steps

1. Inspect the listed files first and trace where `backend/app/historical_runner.py` decides to call `rebuild_elo_mmr_models()`, which configuration values influence that decision, and whether any lighter-weight Elo/MMR rematerialization surface already exists.
2. Refactor execution policy so manual snapshot-oriented or refresh-oriented commands no longer trigger full Elo/MMR rebuild by default, and keep full rebuild available only through the dedicated Elo/MMR CLI or an explicit historical-runner option with clear naming.
3. Update structured operator output so manual commands clearly report whether Elo/MMR work was skipped, lightweight, or full, and validate that the default manual refresh path no longer escalates into full rebuild work.

## Files to Read First

- `AGENTS.md`
- `backend/app/historical_runner.py`
- `backend/app/elo_mmr_engine.py`
- `backend/app/config.py`
- any directly related policy or config files

## Expected Files to Modify

- `backend/app/historical_runner.py`
- `backend/app/config.py` only if configuration or naming changes are strictly necessary
- a minimal number of directly related files if required to express the explicit policy cleanly

Rules:

- Prefer modifying only these files.
- If additional files become necessary, explain why in the task outcome or commit message.
- Do not modify unrelated files.
- Keep the work focused on execution policy and operational safety.
- Do not change Elo/MMR formulas, persisted rating semantics, or telemetry scope in this task.

## Constraints

- Keep the change minimal.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- Do not implement backend functionality unless the task explicitly requires it.
- Manual snapshot-oriented or refresh-oriented commands must not call `rebuild_elo_mmr_models()` implicitly.
- If any lightweight Elo/MMR follow-up remains necessary for some manual flows, it must use a clearly named lightweight path or be explicitly opt-in.
- Full Elo/MMR rebuild must remain available only through the dedicated Elo/MMR CLI entrypoint or an explicit historical-runner option that clearly states full Elo/MMR rebuild will happen.
- Operator-facing output must state when Elo/MMR work was skipped, lightweight, or full.

## Validation

Before completing the task ensure:

- `python -m compileall backend/app` passes
- manual historical refresh is demonstrated not to trigger full Elo/MMR rebuild by default
- an explicit full Elo/MMR rebuild path is demonstrated to remain available
- structured output is demonstrated to state whether Elo/MMR was skipped, lightweight, or full
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
- updated `backend/app/historical_runner.py` so manual runner phases default to explicit Elo/MMR skip semantics
- kept automatic Elo/MMR rebuild policy only on the loop path
- added explicit operator-facing `elo_mmr_result.workload` and `elo_mmr_result.policy_mode` reporting
- added `--full-elo-rebuild` as the only historical-runner option that can trigger the heavyweight rebuild
- constrained `--full-elo-rebuild` so it is only valid with `run --phase full`

Validation run:

- `python -m compileall backend/app`
- `python -m app.historical_runner run --phase snapshots --retries 0`
- `python -m app.historical_runner --help`
- `python -m app.elo_mmr_engine --help`
- controlled in-process validation of `run_manual_historical_phase(phase="refresh", execution_mode="manual")` with refresh stubbed
- controlled in-process validation of `run_manual_historical_phase(phase="full", execution_mode="manual", manual_full_elo_rebuild=True, server_slug="comunidad-hispana-01")` with capture, refresh, snapshots, and rebuild stubbed
- attempted bounded live validation of `python -m app.historical_runner run --phase refresh --max-pages 1 --page-size 1 --retries 0`
- `git diff --name-only`
- `git status --short`

Validation results:

- `python -m compileall backend/app` passed
- snapshots-only manual run reported `elo_mmr_result.status: skipped`, `workload: skipped`, and `policy_mode: manual-no-elo-follow-up`
- historical runner help exposed `--full-elo-rebuild` as an explicit opt-in path
- dedicated Elo/MMR CLI help continued to expose the `rebuild` command as the primary dedicated rebuild entrypoint
- controlled manual refresh validation proved the default refresh path returns `elo_mmr_result.workload: skipped`
- controlled explicit manual full validation proved `--full-elo-rebuild` maps to `elo_mmr_result.workload: full` with `policy_mode: manual-explicit-full-rebuild`
- bounded live refresh validation did not complete within the local timeout window because the underlying historical data fetch is environment-bound
- `python -m app.elo_mmr_engine --help` emitted the existing module bootstrap warning; that warning is outside this task scope and is addressed by pending `TASK-127`
- `git diff --name-only` showed only `backend/app/historical_runner.py`
- `git status --short` confirmed no unrelated tracked file modifications

Branch and delivery state:

- branch: `task/elo-canonical-rating-monthly`
- final commit SHA: not created in this pass
- push: intentionally deferred because more pending tasks remain
