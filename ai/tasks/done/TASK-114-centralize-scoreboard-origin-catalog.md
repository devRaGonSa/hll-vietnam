---
id: TASK-114
title: Centralize scoreboard origin catalog
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto Python
  - PM
roadmap_item: historical
priority: high
---

# TASK-114 - Centralize scoreboard origin catalog

## Goal

Create a single safe source of truth for trusted public scoreboard origins per active server.

## Context

Recent match cards can now fall back to internal details for RCON synthetic matches. The next step is to make trusted external scoreboard origin handling explicit and reusable so future link resolution remains safe.

Required origin behavior:

- Comunidad Hispana #01 must use the configured base scoreboard origin for #01, without a custom port.
- Comunidad Hispana #02 must use the same scoreboard host with port `5443`.
- Comunidad Hispana #03 must not be included in public/default origin flows.

Use branch:

- `plan/scoreboard-match-linking-tasks`

## Steps

1. Work from this task only after moving it to `ai/tasks/in-progress/`.
2. Inspect the listed files before changing anything.
3. Inspect historical storage, RCON historical read/storage modules, config, env example, Docker Compose and relevant docs.
4. Centralize trusted scoreboard origins in a backend helper/config location.
5. Ensure URL validation accepts the trusted origins for #01 and #02, including the #02 `5443` port.
6. Ensure Comunidad Hispana #03 is not part of the trusted scoreboard origin catalog.
7. Keep existing safe `raw_payload_ref` behavior intact.
8. Update or add a concise docs decision if this creates or clarifies a backend contract.
9. Validate the result.
10. Move this task to `ai/tasks/done/` only after validation is complete and document the outcome in this file.
11. Commit and push the completed implementation branch.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/backend-senior.md`
- `backend/app/config.py`
- `backend/app/historical_storage.py`
- `backend/app/rcon_historical_read_model.py`
- `backend/app/rcon_historical_storage.py`
- `backend/app/payloads.py`
- `backend/app/providers/public_scoreboard_provider.py`
- `backend/.env.example`
- `docker-compose.yml`
- `docs/decisions.md`
- `scripts/run-integration-tests.ps1`

## Expected Files to Modify

- likely one backend helper/config module for trusted scoreboard origins
- possibly `backend/app/config.py`
- possibly `backend/app/payloads.py`
- possibly `backend/app/historical_storage.py`
- possibly tests under `backend/tests/`
- possibly `docs/decisions.md`
- this task file, moved to `ai/tasks/done/`

If additional files become necessary, explain why in the task outcome and commit message.

## Expected Files Not to Modify

- `frontend/**`
- local `.env`
- database migrations
- persisted data
- Elo/MMR implementation files
- unrelated backend modules

## Constraints

- Do not reintroduce Comunidad Hispana #03.
- Do not reintroduce paused MVP/Elo UI.
- Do not change historical ingestion policy.
- Do not add real credentials.
- Do not modify local `.env`.
- Do not delete persisted data, migrations, backend endpoints or historical ingestion code.
- Do not use the public word "snapshot" in user-facing UI.
- Keep the change focused on trusted scoreboard origin configuration and validation.

## Validation

Before completing the task, run and document:

- `git status`
- Python compile checks for touched backend modules, for example `python -m compileall backend/app`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- focused check confirming #01 and #02 trusted origins exist
- focused check confirming Comunidad Hispana #03 is absent from trusted public/default origins
- focused check confirming #02 preserves port `5443`
- focused check confirming existing safe `raw_payload_ref` behavior still works
- `git diff --name-only` and confirmation that changed files match the expected scope

If a configured validation command cannot be run, document the exact reason in the outcome.

## Commit And Push Requirements

- Run validation before committing.
- Run `git status`.
- Stage only intended files.
- Commit with message: `chore: centralize scoreboard origin catalog`
- Push the branch to origin.
- Do not leave completed work only in local.

## Outcome

Completed.

Implementation decisions:

- Added `backend/app/scoreboard_origins.py` as the single trusted public scoreboard origin catalog for active default servers.
- Kept only `comunidad-hispana-01` and `comunidad-hispana-02` in the trusted catalog; #02 preserves port `5443`.
- Derived `DEFAULT_HISTORICAL_SERVERS` from the trusted catalog so new default seeds do not reintroduce `comunidad-hispana-03`.
- Routed safe match URL resolution through the trusted catalog instead of trusting each persisted `scoreboard_base_url` row. Existing persisted data is not deleted.
- Updated `docs/decisions.md` with the backend contract for trusted active public scoreboard origins.

Validation performed:

- `git status --short --branch` confirmed branch `plan/scoreboard-match-linking-tasks`.
- `python -m compileall backend/app` passed.
- Focused Python check confirmed #01 and #02 trusted origins exist.
- Focused Python check confirmed `comunidad-hispana-03` is absent from trusted public/default origins.
- Focused Python check confirmed #02 preserves port `5443`.
- Focused Python check confirmed safe `raw_payload_ref` behavior still accepts trusted `/games/` URLs and rejects #03, non-`/games/` paths and credentialed URLs.
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1` passed.
- `git diff --name-only` / `git status --short` reviewed. Changed files match the expected scope plus the new backend helper module and this task file.

Follow-up:

- Continue with TASK-115 for persisted scoreboard link resolution behavior instead of expanding this task.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split follow-up work into a new task if the scope grows.
