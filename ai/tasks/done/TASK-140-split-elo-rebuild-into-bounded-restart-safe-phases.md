# TASK-140-split-elo-rebuild-into-bounded-restart-safe-phases

## Goal

Split the Elo/MMR rebuild into bounded, restart-safe, and operationally recoverable phases.

## Context

The remaining PostgreSQL issue is not migration correctness but the structure of `python -m app.elo_mmr_engine rebuild`. Current rebuild flow still performs large destructive phases in a tightly coupled sequence, including long `DELETE FROM elo_mmr_canonical_player_match_facts` and `DELETE FROM elo_mmr_canonical_players` operations observed during validation. Those large deletes create long locks, expensive rollbacks, and confusing cross-session behavior when a run is interrupted or retried.

The rebuild currently mixes canonical cleanup, canonical population, scoring, monthly rematerialization, and final persistence into phases that are too broad. Future implementation must redesign this flow so each phase is explicit, bounded, and restart-safe, with smaller transactional units or reasonable phase commits, so interruption does not leave one huge opaque rollback and retries do not easily reproduce blocking `DELETE` collisions.

## Steps

1. Inspect the listed files first and map the current rebuild execution order, write boundaries, and transaction scope across canonical rebuild, scoring, monthly rematerialization, and final persistence.
2. Identify where the current rebuild uses oversized destructive phases, especially full-table cleanup and replace operations that create long locks or expensive rollback windows.
3. Refactor the rebuild into explicit bounded phases such as:
   - prepare
   - canonical cleanup
   - canonical players
   - canonical matches
   - canonical facts
   - scoring
   - monthly materialization
   - final persistence
4. Introduce smaller transactional units, reasonable commit boundaries, or phase-by-phase persistence so interruption leaves the system recoverable and diagnosable instead of trapped in one macrotransaction.
5. Validate that retries and restart after interruption no longer reproduce the current pattern of long conflicting deletes and opaque rollback behavior.

## Files to Read First

- `AGENTS.md`
- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/postgres_utils.py`
- `backend/app/writer_lock.py`
- any directly related Elo/MMR persistence helpers

## Expected Files to Modify

- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/postgres_utils.py` only if transaction or connection helpers must be extended narrowly
- `backend/app/writer_lock.py` only if phase-safe locking integration is strictly necessary
- only minimal directly related files if required

Rules:

- Prefer modifying only these files.
- If additional files become necessary, explain why in the task outcome or commit message.
- Do not modify unrelated files.

## Constraints

- Keep the change minimal.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- Do not redesign Elo/MMR formulas or ranking semantics in this task.
- Do not widen the scope into unrelated historical ingestion work.
- The task must stay focused on rebuild execution structure, transaction boundaries, recoverability, and retry safety.
- Avoid macrotransactions that couple canonical cleanup, canonical rebuild, scoring, and monthly materialization into one opaque failure domain.
- A failed or interrupted phase must leave the system restartable without requiring manual cleanup of broken runtime state.

## Validation

Before completing the task ensure:

- `python -m compileall backend/app` passes
- the rebuild is demonstrably split into explicit bounded phases
- interruption leaves the system in a recoverable state without one huge opaque rollback
- retrying the rebuild no longer reproduces multiple long blocking `DELETE` operations against the same canonical tables
- the rebuild can be restarted without dirtying runtime state or requiring ad hoc repair steps
- `pg_stat_activity` and `pg_locks` show a materially cleaner operational pattern during rebuild
- `git diff --name-only` is reviewed
- `git status --short` is reviewed
- no unrelated files were modified
- documentation remains consistent with the repository state

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
