# TASK-144-optimize-postgresql-canonical-cleanup-for-large-elo-rebuilds

## Goal

Redesign the canonical cleanup phase so `python -u -m app.elo_mmr_engine rebuild-full` is operationally safe and performant on large PostgreSQL datasets.

## Context

Recent runtime validation on Docker Compose confirms that the previous rebuild-structure issues improved materially:

- no `idle in transaction`
- no ungranted locks
- no multiple rebuild sessions fighting each other
- PostgreSQL advisory lock works
- the rebuild hot path no longer enters heavyweight historical maintenance

However, the large-dataset runtime validation also exposed one remaining real bottleneck in the PostgreSQL rebuild path. With the real backfilled dataset in Compose:

- `historical_matches = 9708`
- `historical_player_match_stats = 1066887`
- `elo_mmr_match_results = 2128992`
- `elo_mmr_monthly_rankings = 548773`
- `elo_mmr_canonical_player_match_facts = 1064496`

the command:

- `docker compose exec backend python -u -m app.elo_mmr_engine rebuild-full`

enters:

- `prepare`
- `canonical-rebuild`

and PostgreSQL shows a real working session with:

- `application_name = app.elo_mmr_engine rebuild-full canonical-cleanup`
- visible query: `DELETE FROM elo_mmr_canonical_players`

that remains in canonical cleanup for too long.

The key conclusion is that the problem is no longer dirty retries, zombie sessions, broken advisory locking, or accidental historical maintenance in the hot path. The remaining problem is the cleanup design itself. The current PostgreSQL cleanup strategy still relies on expensive mass deletes inside canonical cleanup, and that is too costly for the large rebuild dataset.

## Scope

This task is strictly about the PostgreSQL canonical cleanup design inside the Elo/MMR rebuild flow.

Future implementation must review and improve the cleanup strategy for reconstructible canonical tables, evaluating and implementing a PostgreSQL-appropriate approach such as:

- safe `TRUNCATE` on fully rebuildable canonical tables
- cleanup split into bounded subphases with intermediate commits
- staging and swap strategy
- or a justified combination of the above

It is not acceptable to keep the current costly cleanup pattern centered on:

- `DELETE FROM elo_mmr_canonical_players`
- and or equivalent mass deletes in canonical cleanup

when rebuilding against the large PostgreSQL dataset.

## Files to Read First

- `AGENTS.md`
- `backend/app/elo_mmr_storage.py`
- `backend/app/elo_mmr_engine.py`
- `backend/app/postgres_utils.py`
- any directly related helper, SQL, or migration file strictly necessary to improve canonical cleanup safely

## Expected Files to Modify

- `backend/app/elo_mmr_storage.py`
- `backend/app/elo_mmr_engine.py` only if cleanup subphases or instrumentation boundaries must be surfaced there
- `backend/app/postgres_utils.py` only if narrowly scoped PostgreSQL helper support is required
- minimal directly related SQL, migration, or helper files only if strictly necessary

Rules:

- Prefer modifying only these files.
- If additional files become necessary, explain why in the task outcome or commit message.
- Do not modify unrelated files.

## Constraints

- Keep the change minimal.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- Do not reintroduce heavyweight historical maintenance into the rebuild hot path.
- Do not reintroduce zombie sessions, dirty retries, or `idle in transaction`.
- Keep `rebuild-full`, `rebuild-canonical`, `rebuild-ratings`, `refresh-monthly`, and `historical-maintenance` operationally intact.
- Keep the cleanup restart-safe.
- Cleanup subphases must be visible and instrumented.
- Observability must make it possible to distinguish which cleanup subphase is currently slow.
- Focus this task on canonical cleanup design for large PostgreSQL rebuilds, not on Elo/MMR formula changes.

## Acceptance Criteria

- `rebuild-full` no longer spends an excessive amount of time stuck in `DELETE FROM elo_mmr_canonical_players`
- canonical cleanup uses a strategy appropriate for large PostgreSQL rebuild datasets
- canonical cleanup is divided into visible, instrumented subphases
- `pg_stat_activity` makes it possible to distinguish cleanup subphases
- an interruption does not leave residual sessions or `idle in transaction`
- a later retry starts cleanly
- historical maintenance remains outside the rebuild hot path
- the existing operational commands continue to work:
  - `rebuild-full`
  - `rebuild-canonical`
  - `rebuild-ratings`
  - `refresh-monthly`
  - `historical-maintenance`

## Validation

Before completing the task ensure:

- `python -m compileall backend/app` passes
- real Docker Compose validation is run against the large backfilled PostgreSQL dataset
- `docker compose exec backend python -u -m app.elo_mmr_engine rebuild-full` is executed for real
- `pg_stat_activity` is inspected during canonical cleanup
- `pg_locks` is inspected during canonical cleanup
- visible cleanup subphases and their `application_name` values are captured
- session counts for `app.elo_mmr_engine%` are checked during and after rebuild
- `idle in transaction = 0` is confirmed during and after the rebuild path
- a controlled interruption is performed during the large rebuild
- a retry after interruption is validated to start cleanly
- no heavy historical-maintenance activity appears in the rebuild hot path
- `git diff --name-only` is reviewed
- `git status --short` is reviewed
- no unrelated files were modified

## Out of Scope

- Elo/MMR formula or scoring redesign
- historical maintenance redesign beyond preserving it outside the rebuild hot path
- product-facing API contract changes
- unrelated PostgreSQL migration or backfill work
- unrelated frontend or non-Elo backend changes

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
