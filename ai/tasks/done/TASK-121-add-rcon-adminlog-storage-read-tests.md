---
id: TASK-121
title: Add RCON AdminLog storage read tests
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto Python
roadmap_item: rcon-full-data
priority: high
---

# TASK-121 - Add RCON AdminLog storage read tests

## Goal

Add deterministic regression tests for AdminLog persistence, reads and deduplication.

## Background

AdminLog storage and manual ingestion exist, and real validation confirmed canonical message deduplication. The storage layer now needs offline tests so future RCON pipeline work can depend on it safely.

## Constraints

- Do not require real RCON.
- Do not use the real runtime database.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Do not commit runtime DB files or `backend/runtime`.
- Keep tests deterministic and offline.

## Allowed Changes

- a new backend test file under `backend/tests/`
- possibly small test-only helpers if already consistent with the test suite
- this task file when moving it through the workflow

## Implementation Requirements

- Work from a dedicated branch for this task.
- Read first:
  - `AGENTS.md`
  - `ai/architecture-index.md`
  - `ai/repo-context.md`
  - `ai/orchestrator/backend-senior.md`
  - `backend/app/rcon_admin_log_storage.py`
  - `backend/app/rcon_admin_log_parser.py`
  - `backend/tests/test_rcon_admin_log_parser.py`
- Use a temporary SQLite database path.
- Test table initialization.
- Test that first insert inserts events.
- Test that a second insert of the same events returns duplicates.
- Test that canonical message dedupes repeated AdminLog reads with changing relative prefixes.
- Test `event_counts` grouping by target and event type.
- If pytest is unavailable locally, document the docker-based pytest command in the task outcome.

## Validation Commands

- `python -m compileall backend/app`
- `python -m pytest backend/tests/test_rcon_admin_log_parser.py backend/tests/<new_admin_log_storage_test>.py`

## Manual Verification Steps

- Confirm no real RCON credentials or runtime DB paths are used.
- Confirm tests create and clean temporary data only.
- Confirm `git diff --name-only` matches the allowed scope.

## Git Requirements

- Create a dedicated branch for this task, for example `codex/task-121-adminlog-storage-tests`.
- Run relevant validation before committing.
- Stage only intended files.
- Commit the completed implementation.
- Push the branch to origin.

## Outcome

- Added deterministic offline storage tests in `backend/tests/test_rcon_admin_log_storage.py`.
- Covered AdminLog table initialization, first insert behavior, duplicate reporting, canonical-message dedupe when relative prefixes change, and event-count grouping.
- Tests use pytest `tmp_path` temporary SQLite paths and do not use real RCON or the runtime database.

## Validation Result

- `python -m compileall backend/app` passed.
- `python -m pytest backend/tests/test_rcon_admin_log_parser.py backend/tests/test_rcon_admin_log_storage.py` could not run locally because `pytest` is not installed.
- `docker compose exec backend python -m pytest backend/tests/test_rcon_admin_log_parser.py backend/tests/test_rcon_admin_log_storage.py` also could not run because `pytest` is not installed in the backend image.
- Direct Python invocation of the new storage test functions passed with `PYTHONPATH=backend`.
- `git diff --name-only` matched the expected task scope after accounting for the new untracked test file.
