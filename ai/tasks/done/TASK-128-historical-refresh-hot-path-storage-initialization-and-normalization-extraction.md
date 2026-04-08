# TASK-128

## Goal

Remove heavyweight schema-initialization and identity-normalization work from the per-match historical ingestion hot path.

## Context

Observed runtime behaviour during manual historical refresh shows the path `historical_runner -> historical_ingestion.run_incremental_refresh -> _ingest_server -> upsert_historical_match -> initialize_historical_storage -> _normalize_historical_player_identities`. That strongly suggests the per-match ingestion path can still trigger `initialize_historical_storage()` and the broad normalization logic attached to it, including historical player identity normalization and historical match identity normalization.

This is too expensive for incremental refresh and likely explains why `python -u -m app.historical_runner run --phase refresh --retries 0` can look hung or take far longer than expected. Future implementation must guarantee that incremental refresh performs only the minimum required work inside the per-match ingestion path, while still preserving schema safety and legacy migration correctness.

## Steps

1. Inspect the listed files first and trace exactly where `initialize_historical_storage()` is called during manual refresh, which callers invoke it from hot ingestion code, and which normalization or migration helpers it triggers.
2. Refactor the storage and ingestion boundaries so schema creation or migration stays in an explicit startup or once-per-run boundary, while per-match upserts remain focused on server resolution, match upsert, player upsert, and player-match stat upsert.
3. Move heavyweight normalization or repair work to a bounded place such as one-time storage initialization, an explicit maintenance command, or an explicit post-run maintenance phase that executes at most once per refresh cycle, then validate that manual refresh no longer repeats global normalization work for each match upsert.

## Files to Read First

- `AGENTS.md`
- `backend/app/historical_storage.py`
- `backend/app/historical_ingestion.py`
- `backend/app/historical_runner.py`
- any directly related storage helpers

## Expected Files to Modify

- `backend/app/historical_storage.py`
- `backend/app/historical_ingestion.py`
- `backend/app/historical_runner.py` only if a once-per-run boundary or explicit maintenance phase must be wired there
- only minimal directly related files if strictly necessary

Rules:

- Prefer modifying only these files.
- If additional files become necessary, explain why in the task outcome or commit message.
- Do not modify unrelated files.

## Constraints

- Keep the change minimal.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- Do not implement backend functionality unless the task explicitly requires it.
- Do not redesign the historical schema in this task.
- Do not replace SQLite in this task.
- Do not change historical payload semantics.
- Do not mix Elo/MMR formula work into this task.
- Keep the work focused on hot-path performance, separation of responsibilities, and safe initialization boundaries.
- Future implementation must ensure schema creation or migration happens only in an explicit startup or init boundary, not repeatedly in per-match upsert paths.
- Historical identity normalization must not run on every match upsert.
- Heavy normalization or repair work must move to one bounded place only and must not regress legacy-safe initialization behaviour.

## Validation

Before completing the task ensure:

- `python -m compileall backend/app` passes
- manual refresh is shown not to execute heavyweight normalization inside each match upsert
- a targeted bounded validation shows refresh of a server or page completes substantially faster, or at minimum with clearly reduced repeated initialization or normalization calls
- schema init still works on empty databases
- legacy-safe paths still behave correctly if relevant to the final implementation
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
- split historical storage initialization into a schema-only ensure path and a bounded maintenance path in `backend/app/historical_storage.py`
- updated hot-path historical writer helpers to use schema ensure only, so per-match upserts no longer trigger global player or match normalization
- kept global normalization at the explicit ingestion startup boundary in `backend/app/historical_ingestion.py`
- added explicit initialization progress events so manual refresh output shows that global maintenance runs once per ingestion execution

Validation run:

- `python -m compileall backend/app`
- targeted local validation script from `backend/` that:
- monkeypatched `_normalize_historical_player_identities` and `_normalize_historical_match_identities` to count calls
- ran `initialize_historical_storage(db_path=...)` against an empty SQLite file
- ran `upsert_historical_match(..., db_path=...)` twice against that initialized database
- `git diff --name-only`
- `git status --short`

Validation results:

- `python -m compileall backend/app` passed
- empty-database initialization still succeeded and ran both global normalization passes exactly once during explicit initialization
- first and second `upsert_historical_match()` calls completed with zero normalization calls, confirming the per-match hot path no longer reruns global maintenance
- targeted validation still inserted the first match and updated it idempotently on the second pass
- manual refresh now has explicit `historical-storage-initialization-started` and `historical-storage-initialization-completed` progress events around the bounded once-per-run maintenance phase
- `git diff --name-only` showed only `backend/app/historical_storage.py` and `backend/app/historical_ingestion.py` changed for this task
- `git status --short` showed no unrelated tracked file modifications beyond the active task files and existing untracked pending tasks

Branch and delivery state:

- branch: `task/elo-canonical-rating-monthly`
- final commit SHA: not created in this pass
- push: intentionally deferred because more pending tasks remain in the current working batch
