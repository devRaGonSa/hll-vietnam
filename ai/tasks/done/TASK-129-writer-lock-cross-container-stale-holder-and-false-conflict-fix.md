# TASK-129

## Goal

Fix false writer-lock conflict detection in multi-container Docker execution so manual commands do not get blocked by non-existent active holders.

## Context

The current shared backend writer lock improved operator-facing diagnostics and already avoids opaque `database is locked` failures, but real executions still show false conflicts in multi-container flows. Operators can stop `historical-runner` or `rcon-historical-worker` and still see manual execution abort because the system reports an apparently active writer holder such as `app.historical_runner --hourly`. In those cases the lock often has stale holder metadata, ambiguous PID semantics, or container-local identity assumptions that do not map cleanly across containers.

That forces operators to delete the `.writer.lock` file by hand before manual recovery can proceed. Future implementation must make stale-lock detection safe and correct across container boundaries without weakening real single-writer protection.

## Steps

1. Inspect the listed files first and trace how `backend/app/writer_lock.py` currently decides whether a holder is active, stale, clearable, or still trusted when hostname, PID, cwd, or container assumptions differ across environments.
2. Refactor stale-holder and cross-container liveness handling so stopped writer containers no longer block manual execution with false-positive conflicts, while real active conflicting writers still abort fast with explicit operator-facing output.
3. Validate that normal recovery no longer requires manual deletion of `.writer.lock`, and that structured diagnostics clearly report whether a lock was active, stale and cleared, stale but unsafe to clear, or replaced by explicit recovery logic.

## Files to Read First

- `AGENTS.md`
- `backend/app/writer_lock.py`
- `backend/app/historical_runner.py`
- `backend/app/rcon_historical_worker.py`
- `backend/app/config.py`
- any directly related storage or helper files

## Expected Files to Modify

- `backend/app/writer_lock.py`
- `backend/app/historical_runner.py` only if output integration or recovery handling must be adjusted there
- `backend/app/rcon_historical_worker.py` only if output integration or recovery handling must be adjusted there
- only minimal directly related files if needed

Rules:

- Prefer modifying only these files.
- If additional files become necessary, explain why in the task outcome or commit message.
- Do not modify unrelated files.

## Constraints

- Keep the change minimal.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- Do not implement backend functionality unless the task explicitly requires it.
- Do not remove the shared writer-lock concept.
- Do not weaken real single-writer protection.
- Do not replace SQLite in this task.
- Keep the work focused on correct stale-lock and container-aware conflict handling.
- Future implementation must ensure a writer lock from a stopped writer container is recognized as stale and does not block manual commands.
- Container-aware liveness detection must not trust PID-only checks when container identity is missing or mismatched.
- Manual commands must not require deleting the lock file by hand in the normal recovery case.
- Diagnostic output must remain explicit and operator-friendly.

## Validation

Before completing the task ensure:

- `python -m compileall backend/app` passes
- a real active writer still blocks manual conflicting execution
- a stopped writer container no longer leaves a false-positive active conflict
- stale lock recovery no longer requires manual file deletion in the normal case
- structured output clearly explains whether the lock was active, stale and cleared, stale but unsafe to clear, or replaced by recovery logic
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
- added heartbeat metadata updates to the shared writer-lock file in `backend/app/writer_lock.py` so active cross-container writers refresh their lock state while running
- replaced PID-only cross-container stale detection with explicit lock-state classification for same-host, cross-container, stale-clearable, and stale-unsafe cases
- kept same-host active writer protection intact while allowing stale cross-container locks to clear automatically when their heartbeat is missing or expired
- expanded structured writer-lock payloads so manual diagnostics now expose `lock_diagnosis`, `lock_reason`, holder scope, lock age, heartbeat age, and runtime scope

Validation run:

- `python -m compileall backend/app`
- targeted local validation script from `backend/` that:
- acquired a real local writer lock and confirmed manual preflight still aborted with `lock_diagnosis = "active"`
- simulated an active foreign container lock with a recent heartbeat and confirmed manual preflight still aborted with `lock_reason = "cross-container-lock-has-recent-heartbeat"`
- simulated a stopped foreign container lock with an expired heartbeat and confirmed manual preflight auto-cleared it with `stale_lock_cleared = true`
- simulated a foreign container lock still inside the grace window and confirmed manual preflight reported `lock_diagnosis = "stale-unsafe"` instead of clearing it blindly
- `git diff --name-only`
- `git status --short`

Validation results:

- `python -m compileall backend/app` passed
- a real active same-host writer still blocked conflicting manual execution
- an active foreign container lock with a recent heartbeat still blocked conflicting manual execution
- a stale foreign container lock no longer required manual deletion and was cleared automatically in the normal recovery case
- the structured output now distinguishes `active`, `stale-cleared`, and `stale-unsafe` cases with explicit reason strings
- cross-container liveness no longer trusts PID-only metadata when the holder is foreign; it now relies on recent shared lock heartbeat data instead
- `git diff --name-only` showed only the intended backend files changed in this backlog batch
- `git status --short` confirmed no unrelated tracked file modifications

Branch and delivery state:

- branch: `task/elo-canonical-rating-monthly`
- final commit SHA: not created in this pass
- push: intentionally deferred because more pending tasks remain in the current working batch
