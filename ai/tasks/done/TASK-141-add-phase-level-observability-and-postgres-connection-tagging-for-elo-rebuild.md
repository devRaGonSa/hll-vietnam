# TASK-141-add-phase-level-observability-and-postgres-connection-tagging-for-elo-rebuild

## Goal

Add real phase-level observability and PostgreSQL connection tagging for the Elo/MMR rebuild flow.

## Context

Operational validation showed that `pg_stat_activity` does not clearly reveal which real rebuild phase each PostgreSQL connection is executing. Today the writer lock sets one `application_name`, but the actual working connections used by the rebuild and storage helpers do not expose a consistent per-phase identity. That makes it too hard to diagnose whether a session is cleaning canonical tables, inserting canonical data, scoring ratings, or materializing monthly outputs.

The current CLI output is also too opaque for long runs. Future implementation must add useful `application_name` tagging per real work phase, structured logs, visible timings, and progress signals so an operator can diagnose a slow or stuck rebuild from PostgreSQL and from CLI output without guessing.

## Steps

1. Inspect the listed files first and map which PostgreSQL connections are opened during rebuild, which of them already set `application_name`, and where phase boundaries can expose progress safely.
2. Add useful per-phase PostgreSQL connection tagging for the real work connections so `pg_stat_activity` clearly distinguishes states such as:
   - cleaning
   - inserting canonical data
   - calculating ratings
   - materializing monthly
3. Add structured rebuild logs with explicit phase start, phase completion, timing, and progress counters that remain useful to operators and machine-readable where practical.
4. Surface visible CLI progress so long-running rebuilds no longer look idle or opaque.
5. Validate that an operator can identify the current rebuild phase from PostgreSQL session metadata and diagnose a slow phase without reverse engineering the code path.

## Files to Read First

- `AGENTS.md`
- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/postgres_utils.py`
- `backend/app/writer_lock.py`
- any directly related runtime logging helpers

## Expected Files to Modify

- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/postgres_utils.py`
- `backend/app/writer_lock.py` only if lock-level and phase-level tagging must be aligned
- only minimal directly related files if required

Rules:

- Prefer modifying only these files.
- If additional files become necessary, explain why in the task outcome or commit message.
- Do not modify unrelated files.

## Constraints

- Keep the change minimal.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- Do not redesign rebuild semantics in this task beyond observability hooks and connection metadata.
- Keep the work focused on operator visibility, PostgreSQL diagnosability, progress output, and timing data.
- `application_name` must be useful at phase level for the real worker connections, not just for the writer-lock holder.
- Output should help diagnose blocking, waiting, long-running inserts, and slow materialization without exposing noisy or misleading pseudo-progress.

## Validation

Before completing the task ensure:

- `python -m compileall backend/app` passes
- PostgreSQL session metadata clearly exposes the active rebuild phase
- the CLI prints useful phase progress and timings during rebuild
- structured logs show phase start, completion, and elapsed time
- an operator can diagnose a stuck or slow rebuild from `pg_stat_activity` without guessing what each connection is doing
- `git diff --name-only` is reviewed
- `git status --short` is reviewed
- no unrelated files were modified
- documentation remains consistent with the repository state

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
