# TASK-126

## Goal

Harden manual-versus-daemon execution safety for the SQLite-backed backend so operators do not get opaque `database is locked` failures during writer-heavy manual runs.

## Context

The backend already has a shared writer lock in `backend/app/writer_lock.py` and SQLite timeout configuration in `backend/app/config.py`, but the current operator experience is still fragile. Manual capture or manual historical refresh can still be launched while background services are active, which can lead to lock contention, raw `database is locked` failures, or ambiguous behaviour that looks like a frozen process. The current historical and RCON flows are writer-heavy enough that manual operations need clearer single-writer guardrails and more visible diagnostics.

Future implementation must turn this into a controlled, operator-friendly experience. Manual commands should detect conflicting writer activity, report what is running, explain what the operator should stop or disable, and make wait-versus-timeout-versus-abort status operationally visible instead of surfacing raw SQLite contention symptoms.

## Steps

1. Inspect the listed files first and map where writer locks are acquired, where SQLite connections and busy timeouts are configured, and where manual writer-heavy commands currently surface lock-related failures or ambiguous waits.
2. Add clear single-writer guardrails for manual writer-heavy commands so conflicting active writers are detected early, conflict details are reported to the operator, and waiting, timeout, lock acquisition, or manual abort states become explicit in output.
3. Validate that conflicting manual execution no longer ends as a raw opaque SQLite lock failure, that non-conflicting manual execution still works, and document any narrow diagnostic improvement made to current historical target status reporting if legacy target identities are currently confusing health output.

## Files to Read First

- `AGENTS.md`
- `backend/app/writer_lock.py`
- `backend/app/config.py`
- `backend/app/rcon_historical_worker.py`
- `backend/app/historical_runner.py`
- `backend/app/rcon_historical_storage.py`

## Expected Files to Modify

- `backend/app/writer_lock.py`
- `backend/app/rcon_historical_worker.py`
- `backend/app/historical_runner.py`
- small storage or helper files only if strictly necessary for better diagnostics

Rules:

- Prefer modifying only these files.
- If additional files become necessary, explain why in the task outcome or commit message.
- Do not modify unrelated files.
- Focus only on single-writer operational safety, diagnostics, and clear failure behaviour.
- Do not replace SQLite, redesign the full storage architecture, or change business data semantics in this task.

## Constraints

- Keep the change minimal.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- Do not implement backend functionality unless the task explicitly requires it.
- Manual writer-heavy commands must detect active conflicting writer activity and fail fast with a clear operator-facing message instead of surfacing a raw SQLite lock failure.
- The operator-facing message must explicitly state what is running and what should be stopped or disabled before rerunning manually.
- Writer-lock timeout, SQLite busy timeout, and conflict reporting must become operationally visible in output.
- Manual commands must report whether they acquired the writer lock, waited, timed out, or aborted because another backend writer was active.
- The system must avoid ambiguous partial starts where a manual command appears frozen while only waiting on a lock without clear visibility.
- Historical target status readouts should stop confusing active targets with clearly retired or legacy target identities if that can be achieved with a narrow and safe change.

## Validation

Before completing the task ensure:

- `python -m compileall backend/app` passes
- a conflicting manual execution path is demonstrated not to end as a raw opaque `database is locked` failure
- operator-facing error text is demonstrated to explain the conflict and corrective action
- a non-conflicting manual execution path is demonstrated to still work
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
- added explicit manual writer-lock preflight and diagnostic payload helpers in `backend/app/writer_lock.py`
- wired manual historical runner execution to report writer-lock acquisition, timeout, or abort states in structured output
- wired manual RCON historical capture CLI to use the same preflight and timeout diagnostics
- kept the change focused on manual single-writer guardrails and operator-facing diagnostics

Validation run:

- `python -m compileall backend/app`
- `python -m app.historical_runner run --phase snapshots --retries 0`
- controlled conflicting manual execution using a synthetic active writer lock file followed by `python -m app.historical_runner run --phase snapshots --retries 0`
- `git diff --name-only`
- `git status --short`

Validation results:

- `python -m compileall backend/app` passed
- non-conflicting manual snapshots execution completed successfully and reported `writer_lock.status: acquired`
- non-conflicting manual snapshots execution exposed `writer_lock_timeout_seconds`, `sqlite_writer_timeout_seconds`, and `sqlite_busy_timeout_ms` in output
- conflicting manual execution aborted immediately instead of waiting into an opaque SQLite failure
- conflicting manual execution returned structured operator-facing error text explaining that another backend writer was active and that the operator should stop or disable it before retrying
- conflicting manual execution exposed `writer_lock.status: aborted-conflict-detected-before-wait` plus `active_holder`, `active_started_at`, `active_hostname`, and `active_pid`
- no raw `database is locked` failure surfaced during the conflicting manual validation path
- no narrow historical-target status readout change was required in this pass
- `git diff --name-only` showed the intended backend files changed in this backlog batch
- `git status --short` confirmed no unrelated tracked file modifications

Branch and delivery state:

- branch: `task/elo-canonical-rating-monthly`
- final commit SHA: not created in this pass
- push: intentionally deferred because more pending tasks remain in the current working batch
