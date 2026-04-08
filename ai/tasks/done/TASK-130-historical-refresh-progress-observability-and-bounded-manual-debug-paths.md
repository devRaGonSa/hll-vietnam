# TASK-130

## Goal

Improve manual historical refresh observability so operators can see real progress and distinguish slow work from blocked or unhealthy execution.

## Context

The current manual refresh path already emits some ingestion events from `backend/app/historical_ingestion.py`, but a long-running `python -u -m app.historical_runner run --phase refresh --retries 0` can still look hung for too long. The current output does not give operators enough phase-level or timing-level visibility to tell whether the run is making forward progress, which server or page is currently active, or whether the bottleneck is network fetch, parsing, normalization, persistence, fallback, or another maintenance boundary.

That makes manual operations hard to trust and encourages unsafe interruption. Future implementation must add clearer structured progress reporting and bounded manual debug execution so operators can distinguish heavy legitimate work from blocked execution.

## Steps

1. Inspect the listed files first and map the current progress events emitted by manual refresh, where they stop being informative, and which internal boundaries can expose progress safely without changing data semantics.
2. Add structured operator-facing progress for current server, current page, total pages processed, matches seen or inserted or updated, player rows inserted or updated, active phase, and phase timing, plus periodic heartbeats during long-running work.
3. Keep bounded manual debug paths available through existing server or page caps, make those caps explicit in output, and validate that operators can now distinguish network-bound, normalization-bound, persistence-bound, and fallback or backfill-heavy behaviour.

## Files to Read First

- `AGENTS.md`
- `backend/app/historical_runner.py`
- `backend/app/historical_ingestion.py`
- `backend/app/historical_storage.py`
- any directly related config or runner files

## Expected Files to Modify

- `backend/app/historical_runner.py`
- `backend/app/historical_ingestion.py`
- `backend/app/historical_storage.py` only if narrow timing or progress hooks are strictly necessary
- only minimal directly related files if necessary

Rules:

- Prefer modifying only these files.
- If additional files become necessary, explain why in the task outcome or commit message.
- Do not modify unrelated files.

## Constraints

- Keep the change minimal.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- Do not implement backend functionality unless the task explicitly requires it.
- Do not redesign the historical API payload surface in this task.
- Do not change business semantics of imported data.
- Do not mix writer-lock policy redesign into this task except for output integration if strictly needed.
- Keep the work focused on observability, bounded manual debugging, and operator trust.
- Future implementation must surface structured progress for current server, current page, total pages processed in the run, matches seen or inserted or updated, player rows inserted or updated, and current phase or timer.
- Manual refresh should emit periodic progress heartbeats during longer work.
- Output must help distinguish network-bound slowdowns, persistence-bound slowdowns, normalization-bound slowdowns, and fallback or backfill work.

## Validation

Before completing the task ensure:

- `python -m compileall backend/app` passes
- manual refresh now emits structured progress and or heartbeats during longer work
- bounded manual refresh output clearly indicates server or page caps and forward progress
- final output remains machine-readable and useful for operators
- `git diff --name-only` is reviewed
- `git status --short` is reviewed
- no unrelated files were modified
- documentation remains consistent with the repository state

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
- added structured run, server, stage, heartbeat, persist-progress, and completion events to `backend/app/historical_ingestion.py`
- added bounded-debug visibility for `server_scope`, `max_pages`, `page_size`, and `detail_workers` in ingestion progress payloads
- added periodic stage heartbeats for long-running work so manual refresh can distinguish slow page fetch, detail fetch, and persistence stages
- wired `backend/app/historical_runner.py` to stream manual refresh progress through a machine-readable callback path and emit explicit phase start and completion events

Validation run:

- `python -m compileall backend/app`
- targeted bounded local validation script from `backend/` that:
- redirected `HLL_BACKEND_STORAGE_PATH` to a temporary workspace SQLite file
- replaced the historical data source with a fake local provider
- forced a six-second delay in `fetch_match_details()` to trigger a heartbeat without using the network
- ran `run_manual_historical_phase(phase="refresh", server_slug="comunidad-hispana-01", max_pages=1, page_size=1, progress_callback=...)`
- `git diff --name-only`
- `git status --short`

Validation results:

- `python -m compileall backend/app` passed
- the bounded manual refresh emitted machine-readable progress events for:
- `historical-runner-phase-started`
- `historical-ingestion-run-started`
- `historical-storage-initialization-started`
- `historical-storage-initialization-completed`
- `historical-ingestion-source-selected`
- `historical-ingestion-server-started`
- `historical-ingestion-stage-started`
- `historical-ingestion-heartbeat`
- `historical-ingestion-persist-progress`
- `historical-ingestion-server-completed`
- `historical-ingestion-run-completed`
- `historical-runner-phase-completed`
- the forced slow detail-fetch path emitted `historical-ingestion-heartbeat` with `stage = "detail-fetch"`, confirming long-running work is now observable during execution instead of only after completion
- bounded manual debug output now makes `server_scope`, `max_pages`, and `page_size` explicit at both runner and ingestion boundaries
- per-event totals now expose pages processed, matches seen, matches inserted or updated, and player rows inserted or updated
- the final bounded validation refresh completed successfully with one processed page, one seen match, one inserted match, and one inserted player row
- `git diff --name-only` showed only the intended backend files changed in this backlog batch
- `git status --short` confirmed no unrelated tracked file modifications

Branch and delivery state:

- branch: `task/elo-canonical-rating-monthly`
- final commit SHA: not created in this pass
- push: intentionally deferred because no push was requested and this turn was focused on processing the pending task batch
