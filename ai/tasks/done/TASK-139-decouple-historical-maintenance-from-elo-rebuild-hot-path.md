# TASK-139-decouple-historical-maintenance-from-elo-rebuild-hot-path

## Goal

Remove heavyweight historical maintenance from the normal `python -m app.elo_mmr_engine rebuild` hot path.

## Context

PostgreSQL migration validation is essentially complete, but the remaining structural problem is the operational rebuild flow behind `python -m app.elo_mmr_engine rebuild`.

Current code shows that `backend/app/elo_mmr_engine.py` enters `initialize_historical_storage()` before starting the Elo/MMR rebuild. In `backend/app/historical_storage.py`, `initialize_historical_storage()` currently delegates to `run_historical_storage_maintenance()`, which still executes global historical normalization passes for `historical_players` and `historical_matches`.

That means the operational Elo/MMR rebuild hot path still performs heavyweight historical maintenance before it reaches canonical rebuild, scoring, or monthly rematerialization. This is the wrong coupling. The rebuild needs a lightweight storage-preparation path that ensures schema readiness without rerunning global historical normalization on every operational rebuild, while keeping heavyweight historical maintenance available as an explicit and separate operator action.

## Steps

1. Inspect the listed files first and trace the exact path from `app.elo_mmr_engine rebuild` into historical storage initialization and maintenance helpers.
2. Identify precisely which historical normalization or repair passes are currently executed during a normal Elo/MMR rebuild and document why they are too heavy for the operational hot path.
3. Introduce a lightweight historical storage preparation route for Elo/MMR rebuilds that guarantees schema and required relational prerequisites without triggering global normalization of `historical_players` or `historical_matches`.
4. Keep heavyweight historical maintenance available only through an explicit maintenance route, command, or equivalent boundary that is clearly outside the normal Elo/MMR rebuild path.
5. Validate that a normal rebuild still prepares storage correctly but no longer starts with mass historical normalization queries.

## Files to Read First

- `AGENTS.md`
- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/historical_storage.py`
- `backend/app/postgres_utils.py`
- `backend/app/writer_lock.py`

## Expected Files to Modify

- `backend/app/elo_mmr_engine.py`
- `backend/app/historical_storage.py`
- `backend/app/elo_mmr_storage.py` only if a lightweight readiness boundary must be exposed there
- `backend/app/postgres_utils.py` only if a narrowly scoped schema-readiness helper is strictly necessary
- only minimal directly related files if required

Rules:

- Prefer modifying only these files.
- If additional files become necessary, explain why in the task outcome or commit message.
- Do not modify unrelated files.

## Constraints

- Keep the change minimal.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- Do not redesign the historical schema in this task.
- Do not change Elo/MMR formulas, scoring semantics, or product-facing payload contracts in this task.
- Do not remove heavyweight historical maintenance entirely; keep it available as an explicit operator path outside the rebuild hot path.
- The normal Elo/MMR rebuild path must not execute global normalization of `historical_players` or `historical_matches`.
- Storage and schema preparation required by Elo/MMR rebuild must still happen safely.

## Validation

Before completing the task ensure:

- `python -m compileall backend/app` passes
- the traced rebuild path is shown not to call global historical normalization during the normal hot path
- the schema still prepares correctly for a rebuild on an empty or already-initialized PostgreSQL runtime
- heavyweight historical maintenance still exists but is no longer coupled to the normal rebuild path
- launching rebuild no longer shows mass historical normalization queries at startup
- `git diff --name-only` is reviewed
- `git status --short` is reviewed
- no unrelated files were modified
- documentation remains consistent with the repository state

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
