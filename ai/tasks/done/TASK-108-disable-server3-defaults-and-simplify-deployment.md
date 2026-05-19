---
id: TASK-108
title: Disable server #03 defaults and simplify deployment
status: done
type: documentation
team: PM
supporting_teams:
  - Backend Senior
  - Arquitecto Python
roadmap_item: foundation
priority: high
branch: chore/disable-server3-defaults
---

# TASK-108 - Disable server #03 defaults and simplify deployment

## Goal

Remove Comunidad Hispana server #03 from the default operational deployment/configuration path and document the simplified normal mode for HLL Vietnam.

This task must keep the existing Elo/MMR, historical ingestion, migrations, and persisted data available in the repository. The goal is to stop treating server #03 and complex historical/Elo work as default operational requirements for the current phase, not to delete that work.

## Context

The AI Platform integration has just been updated and merged into `main`. The project now needs a simpler operational deployment path because the previous Elo/MMR and historical materialization work became too complex for the current phase, and Comunidad Hispana server #03 is no longer relevant because the server appears to have disappeared.

The recommended default deployment path should be `backend` + `frontend`. Historical workers and RCON historical services may remain available for explicit advanced use, but they should not be part of the recommended normal startup.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Create or switch to branch `chore/disable-server3-defaults`.
2. Inspect all files listed in **Files to Read First** before changing anything.
3. Locate every default deployment/configuration reference that treats Comunidad Hispana server #03 as part of the normal RCON operational path.
4. Remove Comunidad Hispana server #03 from default RCON targets in `docker-compose.yml`.
5. Ensure the default operational deployment path is clearly `backend` + `frontend`.
6. Keep `historical-runner` and `rcon-historical-worker` available only as explicit/advanced services, not part of the recommended normal startup.
7. Update `README.md` deployment/runbook documentation accordingly.
8. Update any relevant docs to state:
   - server #03 is disabled or removed from defaults;
   - Elo/MMR and complex historical ranking/materialization are paused for now;
   - code and data are not deleted in this task;
   - rollback or reintroduction remains possible later.
9. Do not remove code, migrations, persisted data, or database schemas.
10. Do not change live server #01 or #02 definitions except where required for formatting or consistency.
11. Keep secrets as placeholders or environment variables; do not add real passwords.
12. Validate the change with the checks below.
13. Move this task file from `ai/tasks/pending/` to `ai/tasks/done/` when validation is complete, or to `ai/tasks/review/` only if human/orchestrator review is explicitly required.
14. Commit and push the completed work. Do not leave completed work only in local.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `docker-compose.yml`
- `README.md`
- `backend/.env.example`
- `backend/app/config.py`
- `backend/app/data_sources.py`
- `backend/app/historical_runner.py`
- `backend/app/rcon_historical_worker.py` if present
- `docs/`

## Expected Files to Modify

- `docker-compose.yml`
- `README.md`
- possibly `backend/.env.example`
- possibly docs under `docs/`
- possibly `ai/repo-context.md`
- possibly `ai/architecture-index.md`
- this task file, moved from `ai/tasks/pending/` to `ai/tasks/done/` or `ai/tasks/review/` according to the AI Platform workflow

If additional files become necessary, explain why in the task outcome and commit message.

## Expected Files Not to Modify

- `frontend/**`, unless there is a direct hardcoded visible reference to server #03 that must be removed
- database migrations
- persisted data
- Elo/MMR algorithm implementation files
- unrelated backend modules

## Constraints

- Keep the change narrow and operational.
- Do not delete Elo/MMR code.
- Do not delete historical ingestion code.
- Do not delete database migrations or persisted data.
- Do not alter database schemas.
- Do not introduce unnecessary frameworks or dependencies.
- Do not build new backend functionality.
- Do not change frontend behavior unless a visible server #03 default reference is directly found and must be adjusted.
- Do not modify unrelated files.
- Preserve HLL Vietnam project identity.
- Keep secrets as placeholders or environment variables; never add real credentials.

## Validation

Before completing the task ensure:

- Run `git status`.
- Validate that `docker-compose.yml` remains syntactically valid YAML if a YAML parser is available.
- Run `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`.
- Confirm `backend/runtime/` is not created or committed.
- Confirm server #03 is no longer present in default RCON targets.
- Confirm server #01 and server #02 remain present.
- Confirm no Elo/MMR code was deleted.
- Confirm no historical ingestion code was deleted.
- Confirm no database migrations, persisted data, or schema definitions were removed.
- Confirm no frontend behavior was unintentionally changed.
- Review `git diff --name-only` and confirm changed files match the expected scope.

If any validation cannot be run, document the reason in the outcome before moving the task.

## Commit And Push Requirements

1. Run validation before committing.
2. Run `git status`.
3. Stage only intended files.
4. Commit with a clear message, for example:

   ```text
   chore: disable server3 defaults and simplify deployment
   ```

5. Push branch `chore/disable-server3-defaults` to `origin`.

Do not leave completed work only in local.

## Outcome

- Removed Comunidad Hispana #03 from default RCON targets in `docker-compose.yml` and `backend/.env.example`; Comunidad Hispana #01 and #02 remain present.
- Simplified the recommended default deployment to `backend` + `frontend`. `docker compose up --build` now resolves only those services because historical workers are behind the `advanced` profile.
- Kept `historical-runner` and `rcon-historical-worker` available for explicit advanced use via `docker compose --profile advanced ...`.
- Paused Elo/MMR and complex historical materialization in documentation without deleting code, migrations, schemas, snapshots or persisted data.
- Changed backend historical defaults to `public-scoreboard` for normal operation while preserving RCON historical code for explicit advanced use.
- Updated root README, backend README, AI context and the decision log so future work does not treat #03 or historical/Elo automation as the default path.

Validation performed:

- `docker compose config --services` returned only `backend` and `frontend` for the default profile.
- Python YAML parser validation was skipped because `PyYAML` is not installed; Compose config validation succeeded instead.
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1` passed and reported no product integration tests configured for this platform-only scope.
- Confirmed `backend/runtime/` is not present.
- Reviewed `git diff --name-only`; modified files match the expected operational/documentation scope plus backend config default alignment.
- Confirmed no frontend files, migrations, persisted data, Elo/MMR implementation files, historical ingestion implementation files, or database schemas were removed.

Follow-up:

- If Comunidad Hispana #03 becomes available again, create a separate validation/reintroduction task instead of restoring it as a default target directly.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
