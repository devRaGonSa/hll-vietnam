---
id: TASK-110
title: Restore historical RCON-first fallback policy
status: pending
type: backend
team: Backend Senior
supporting_teams: ["Arquitecto Python", "PM"]
roadmap_item: foundation
priority: high
---

# TASK-110 - Restore historical RCON-first fallback policy

## Goal

Correct repository defaults and documentation so historical ingestion is RCON-first, with public-scoreboard used only as a fallback when RCON fails.

Keep the simplified deployment posture intact:

- Live data source: `rcon`
- Historical data source: `rcon`
- Historical fallback: `public-scoreboard` when RCON fails
- Elo/MMR: paused and decoupled from backend startup
- Comunidad Hispana #03: removed from default targets
- Comunidad Hispana #01 and #02: active in default RCON targets

## Context

HLL Vietnam recently simplified deployment and removed Comunidad Hispana #03 from default operational targets. The intended historical data policy has now been clarified: historical ingestion must not be disabled, and public-scoreboard must not be the normal primary historical source.

The desired policy is RCON-first historical ingestion with public-scoreboard fallback when RCON fails. Documentation and defaults that currently imply "historical source is public-scoreboard" need to be corrected to "historical source is RCON-first with public-scoreboard fallback."

This task is implementation-ready for branch:

- `fix/historical-rcon-first-fallback-policy`

## Steps

1. Work on branch `fix/historical-rcon-first-fallback-policy`.
2. Inspect the listed files before changing anything.
3. Restore the historical default policy to RCON-first where appropriate:
   - `HLL_BACKEND_HISTORICAL_DATA_SOURCE=rcon`
4. Keep public-scoreboard documented and configured only as fallback, not as the normal primary historical source.
5. Ensure `docker-compose.yml` defaults and backend example env files do not include Comunidad Hispana #03.
6. Ensure Comunidad Hispana #01 and #02 remain in default RCON targets.
7. Keep advanced historical workers under the advanced profile if they are already configured that way.
8. Keep Elo/MMR paused and decoupled from backend startup.
9. Do not delete code, migrations, persisted data, or historical ingestion modules.
10. Update documentation and decisions to correct the historical source wording.
11. Do not add real credentials, secrets, passwords, or local `.env` values.
12. Run the required validation before committing.
13. Move this task file to `ai/tasks/done/` only after validation is complete and the outcome is documented.
14. Stage only intended files, commit, and push the branch to origin.

## Files to Read First

- `docker-compose.yml`
- `backend/.env.example`
- `backend/app/config.py`
- `backend/app/data_sources.py`
- `backend/app/historical_runner.py`
- `backend/app/rcon_historical_worker.py`, if present
- `README.md`
- `backend/README.md`
- `docs/decisions.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`

## Expected Files to Modify

- `docker-compose.yml`
- `backend/.env.example`
- `backend/app/config.py`
- `README.md`
- `backend/README.md`
- `docs/decisions.md`
- possibly `ai/repo-context.md`
- possibly `ai/architecture-index.md`
- this task file moved from `ai/tasks/pending/` to `ai/tasks/done/`

If additional files become necessary, explain why in the task outcome and commit message.

## Expected Files Not to Modify

- `frontend/**`
- database migrations
- persisted data
- Elo/MMR algorithm implementation files
- unrelated backend modules
- local `.env`

## Constraints

- Do not reintroduce Comunidad Hispana #03.
- Do not reactivate Elo/MMR.
- Do not delete historical ingestion code.
- Do not delete database migrations or persisted data.
- Do not modify frontend behavior.
- Do not add real secrets, passwords, tokens, or credentials.
- Keep advanced historical workers under the advanced profile if already configured.
- Keep the default Compose services limited to `backend` and `frontend`.
- Keep the change focused on defaults, source policy, and documentation wording.
- Do not modify unrelated files.
- Do not leave completed work only in local; commit and push after validation.

## Validation

Before completing the task, run and document:

- `git status`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- `docker compose config --services`
- `docker compose config`

Also confirm and document:

- default services are still only `backend` and `frontend`
- default historical source resolves to `rcon`
- `HLL_BACKEND_RCON_TARGETS` default includes only `comunidad-hispana-01` and `comunidad-hispana-02`
- `comunidad-hispana-03` is not present in default RCON targets
- documentation says public-scoreboard is fallback, not primary, for historical mode
- no frontend files changed
- no database migrations or persisted data changed
- `backend/runtime/` is not created or committed
- `git diff --name-only` matches the expected scope

If integration tests are relevant and `scripts/run-integration-tests.ps1` exists, use it. If a configured test cannot be run, document the exact reason in the outcome.

## Commit And Push Requirements

- Run all validation before committing.
- Run `git status`.
- Stage only intended files.
- Commit with a clear message, for example: `fix: restore historical rcon-first fallback policy`.
- Push the branch to origin.
- Do not leave completed work only in local.

## Outcome

Completed for branch `fix/historical-rcon-first-fallback-policy`.

Validation performed:

- `git status --short --branch`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
  - Passed.
  - The script reported no product integration tests are configured for this platform-only scope.
  - Backend startup import check passed.
- `docker compose config --services`
  - Passed and returned only `backend` and `frontend` for the default profile.
- `docker compose config`
  - Passed.
  - The local machine had Compose environment overrides, so default policy was confirmed again with an empty env file to avoid local values.
- `docker compose --env-file <empty-temp-file> config --services`
  - Returned only `backend` and `frontend`.
- `docker compose --env-file <empty-temp-file> config --format json`
  - Confirmed `HLL_BACKEND_HISTORICAL_DATA_SOURCE=rcon`.
  - Confirmed default `HLL_BACKEND_RCON_TARGETS` includes only `comunidad-hispana-01` and `comunidad-hispana-02`.
  - Confirmed `comunidad-hispana-03` is not present in default RCON targets.
- `python -c "from backend.app.config import DEFAULT_HISTORICAL_DATA_SOURCE; print(DEFAULT_HISTORICAL_DATA_SOURCE)"`
  - Returned `rcon`.
- `git diff --name-only`
  - Matched the expected backend/defaults/docs scope plus `backend/app/historical_runner.py`.
- `Test-Path backend/runtime`
  - Returned `False`.

Final source policy:

- Historical ingestion defaults to RCON-first.
- `public-scoreboard` is fallback only for historical operations where RCON fails, lacks coverage or lacks parity for the requested competitive operation.
- Live data remains `rcon`.
- Elo/MMR remains paused and decoupled from backend startup.
- Comunidad Hispana #03 remains absent from default targets.
- Comunidad Hispana #01 and #02 remain active in default RCON targets.

Changed files:

- `docker-compose.yml`
- `backend/.env.example`
- `backend/app/config.py`
- `backend/app/historical_runner.py`
- `README.md`
- `backend/README.md`
- `docs/decisions.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- this task file moved from `ai/tasks/pending/` to `ai/tasks/done/`

Notable decision:

- `backend/app/historical_runner.py` was updated because its default advanced historical scope still included `comunidad-hispana-03`. Leaving that default in code would contradict the task's default-target policy and the updated documentation, even though the worker remains under the advanced Compose profile.

Scope confirmations:

- No frontend files changed.
- No database migrations or persisted data changed.
- No real credentials were added; repository defaults continue to use placeholder RCON passwords.
- `backend/runtime/` was not created or committed.
- No follow-up task is needed for this scope.
- The branch was pushed to origin after validation and commit.

## Change Budget

- Prefer fewer than 5 modified files when feasible.
- Prefer changes under 200 lines when feasible.
- Split follow-up work into a new task if the scope grows beyond defaults, documentation, and source-policy correction.
