---
id: TASK-115
title: Resolve persisted scoreboard links
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Frontend Senior
  - PM
roadmap_item: historical
priority: high
---

# TASK-115 - Resolve persisted scoreboard links

## Goal

Make sure all existing persisted public-scoreboard matches expose a safe `match_url` consistently.

## Context

The UI should prefer safe external scoreboard links when the match is already a persisted public-scoreboard match. This task is limited to persisted scoreboard data and must not use RCON synthetic IDs to construct external URLs.

Use branch:

- `plan/scoreboard-match-linking-tasks`

## Steps

1. Work from this task only after moving it to `ai/tasks/in-progress/`.
2. Inspect the listed files before changing anything.
3. Inspect historical storage detail and recent match payloads.
4. Ensure recent match list responses return `match_url` when `raw_payload_ref` exists and passes trusted origin validation.
5. Ensure the match detail endpoint returns `match_url` for persisted scoreboard matches when `raw_payload_ref` exists and passes trusted origin validation.
6. Do not use RCON synthetic IDs for this task.
7. Do not fabricate external URLs when no trusted persisted URL exists.
8. Add tests or focused checks if feasible in the current repo.
9. Validate the result.
10. Move this task to `ai/tasks/done/` only after validation is complete and document the outcome in this file.
11. Commit and push the completed implementation branch.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/backend-senior.md`
- `backend/app/historical_storage.py`
- `backend/app/historical_snapshots.py`
- `backend/app/payloads.py`
- `backend/app/routes.py`
- backend trusted scoreboard origin helper/config from TASK-114
- `backend/tests/` if present
- `scripts/run-integration-tests.ps1`

## Expected Files to Modify

- `backend/app/historical_storage.py`
- possibly `backend/app/historical_snapshots.py`
- possibly `backend/app/payloads.py`
- possibly `backend/app/routes.py`
- possibly backend tests
- this task file, moved to `ai/tasks/done/`

If additional files become necessary, explain why in the task outcome and commit message.

## Expected Files Not to Modify

- `frontend/**`
- local `.env`
- database migrations
- persisted data
- Docker/Compose config
- Elo/MMR implementation files
- historical ingestion policy/config

## Constraints

- Do not reintroduce Comunidad Hispana #03.
- Do not reintroduce paused MVP/Elo UI.
- Do not change historical ingestion policy.
- Do not add real credentials.
- Do not modify local `.env`.
- Do not delete persisted data, migrations, backend endpoints or historical ingestion code.
- Do not use the public word "snapshot" in user-facing UI.
- Keep the change limited to safe `match_url` exposure for persisted public-scoreboard matches.

## Validation

Before completing the task, run and document:

- `git status`
- Python compile checks for touched backend modules
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- recent matches endpoint check confirming persisted scoreboard matches expose safe `match_url` when available
- match detail endpoint check for a persisted scoreboard match if fixture/data exists
- focused check confirming unsafe or untrusted URLs are not accepted
- focused check confirming RCON synthetic IDs are not used to construct external URLs
- `git diff --name-only` and confirmation that changed files match the expected scope

If a configured validation command cannot be run, document the exact reason in the outcome.

## Commit And Push Requirements

- Run validation before committing.
- Run `git status`.
- Stage only intended files.
- Commit with message: `fix: resolve persisted scoreboard match links`
- Push the branch to origin.
- Do not leave completed work only in local.

## Outcome

Completed.

Implementation decisions:

- No additional production-code change was needed in this task because TASK-114 already routed recent-match and detail `match_url` resolution through the trusted scoreboard origin catalog.
- Added `backend/tests/test_scoreboard_match_links.py` as a focused stdlib `unittest` regression check for persisted public-scoreboard match links.
- The test verifies recent-match and match-detail payloads expose safe persisted URLs, rejects an untrusted #03 origin, and confirms RCON synthetic match IDs are not used to fabricate external scoreboard URLs.

Validation performed:

- `git status --short --branch` confirmed branch `plan/scoreboard-match-linking-tasks`.
- `$env:PYTHONPATH='backend'; python -m unittest backend.tests.test_scoreboard_match_links` passed.
- `python -m compileall backend/app backend/tests` passed.
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1` passed.
- Recent matches endpoint behavior was covered by the regression test through `list_recent_historical_matches`.
- Match detail endpoint behavior was covered by the regression test through `get_historical_match_detail`.
- Unsafe/untrusted URL rejection was covered with a persisted #03-origin `raw_payload_ref`.
- RCON synthetic ID non-fabrication was covered with `get_rcon_historical_match_detail`.
- `git diff --name-only` and `git status --short` were reviewed. Changed files match the expected scope: backend test coverage plus this task file.

Note:

- The focused unittest emits existing SQLite `ResourceWarning` messages from the repository connection helper pattern during forced cleanup, but all assertions pass and no temp database remains locked.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split follow-up work into a new task if the scope grows.
