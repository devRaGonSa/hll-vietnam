# TASK-143-fix-structural-rebuild-flow-defects-detected-in-postgresql-validation

## Goal

Fix real structural rebuild-flow defects detected during PostgreSQL validation of the Elo/MMR rebuild path.

## Context

PostgreSQL validation exposed that the remaining risk is now in the structure of the Elo/MMR rebuild flow itself, not in the migration. Beyond hot-path maintenance coupling, oversized phases, and missing observability, the rebuild path still needs one focused defect pass for real bugs that belong specifically to this flow.

This task is intentionally narrow. It must cover only genuine rebuild-flow defects discovered in the operational PostgreSQL validation of `python -m app.elo_mmr_engine rebuild`, such as unreachable code, defective connection lifecycle, anomalous `idle in transaction` sessions, or rebuild steps located in the wrong stage. It must not become a grab bag for unrelated cleanup outside the rebuild path.

## Steps

1. Inspect the listed files first and review the current rebuild flow for real structural bugs tied directly to the Elo/MMR rebuild execution path.
2. Confirm which defects are genuine rebuild-flow issues and exclude unrelated cleanup noise.
3. Fix any defects that clearly belong in scope, including if present:
   - unreachable code
   - auxiliary connections left `idle in transaction`
   - defective connection lifecycle
   - rebuild steps placed in the wrong phase
   - helpers or side effects attached to the wrong rebuild boundary
4. Keep the fixes small and diagnosable, and document why each included defect belongs specifically to the rebuild flow.
5. Validate that the normal rebuild path no longer leaves anomalous connection states or dead logic in the critical flow.

## Files to Read First

- `AGENTS.md`
- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/historical_storage.py`
- `backend/app/postgres_utils.py`
- `backend/app/writer_lock.py`

## Expected Files to Modify

- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/postgres_utils.py`
- `backend/app/historical_storage.py` only if a confirmed rebuild-flow defect lives there
- `backend/app/writer_lock.py` only if a confirmed rebuild-flow defect lives there
- only minimal directly related files if required

Rules:

- Prefer modifying only these files.
- If additional files become necessary, explain why in the task outcome or commit message.
- Do not modify unrelated files.

## Constraints

- Keep the change minimal.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- Do not mix unrelated PostgreSQL migration cleanup into this task.
- Do not redesign the rebuild pipeline broadly here; that belongs to the sibling phase-splitting and CLI-separation tasks.
- Include only defects that are clearly inside the Elo/MMR rebuild flow scope.
- If a suspected issue cannot be tied clearly to the rebuild flow, leave it out of this task.

## Validation

Before completing the task ensure:

- `python -m compileall backend/app` passes
- no relevant dead or unreachable code remains in the rebuild flow
- the normal rebuild path no longer leaves anomalous `idle in transaction` sessions
- connection lifecycle across the rebuild flow is consistent and diagnosable
- any included bug fix is clearly tied to the Elo/MMR rebuild scope
- `git diff --name-only` is reviewed
- `git status --short` is reviewed
- no unrelated files were modified
- documentation remains consistent with the repository state

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
