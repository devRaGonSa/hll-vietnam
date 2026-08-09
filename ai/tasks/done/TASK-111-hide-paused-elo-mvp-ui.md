---
id: TASK-111
title: Hide paused Elo and MVP ranking UI
status: pending
type: frontend
team: Frontend Senior
supporting_teams: [PM]
roadmap_item: historical-ui
priority: high
---

# TASK-111 - Hide paused Elo and MVP ranking UI

## Goal

Hide paused or experimental Elo/MMR and advanced MVP ranking blocks from the public historical page while preserving stable historical content.

## Context

HLL Vietnam now uses this operational backend policy:

- live data source: RCON
- historical data source: RCON
- public-scoreboard fallback only when RCON historical data fails
- Comunidad Hispana #03 removed from default targets
- Elo/MMR paused and decoupled from backend startup

Manual visual review of `http://localhost:8080/historico.html` shows that the public historical page still displays paused or experimental ranking blocks:

- MVP mensual V1
- MVP mensual V2
- Comparativa V1 vs V2
- Elo/MMR mensual / persistent rating

This contradicts the current product decision. This task is only a public UI/product-scope change. Preserve backend endpoints, historical ingestion, Elo/MMR implementation code, persisted data, snapshots, migrations and schemas.

Use branch:

- `chore/hide-paused-elo-mvp-ui`

## Steps

1. Inspect the listed files first.
2. Hide or remove from the public historical page the paused/experimental UI blocks:
   - MVP mensual V1
   - MVP mensual V2
   - Comparativa V1 vs V2
   - Elo/MMR mensual / persistent rating
3. Stop calling the related frontend fetch/render flows for those hidden sections in `historico.js`.
4. Keep normal historical content visible:
   - summary/resumen
   - weekly/monthly basic historical rankings
   - recent matches
   - any other non-Elo, non-MVP experimental historical content already considered stable
5. Remove `comunidad-hispana-03` from the frontend historical server selector and JavaScript server list if still present.
6. Preserve backend endpoints and code. Do not delete backend Elo/MMR code, historical ingestion code, endpoints, persisted data, snapshots, migrations or schemas.
7. Prefer a minimal feature-flag-like constant in frontend JavaScript if useful, for example:
   `const SHOW_PAUSED_ADVANCED_RANKINGS = false;`
   Do not leave visible empty panels.
8. Update text/docs only if necessary to clarify that advanced MVP/Elo ranking UI is paused.
9. Do not add new frameworks or dependencies.
10. Validate the result.
11. Move this task file to `ai/tasks/done/` after validation is complete.
12. Commit and push the completed work to origin. Do not leave completed work only in local.

## Files to Read First

- `frontend/historico.html`
- `frontend/assets/js/historico.js`
- `frontend/assets/css/historico.css`
- `backend/app/payloads.py`
- `README.md`
- `docs/decisions.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`

Rules:

- Read these files before implementation.
- Keep the implementation scoped to public historical UI behavior.
- Do not change backend historical policy.

## Expected Files to Modify

- `frontend/historico.html`
- `frontend/assets/js/historico.js`
- possibly `frontend/assets/css/historico.css`
- possibly `docs/decisions.md`
- possibly `ai/repo-context.md`
- possibly `ai/architecture-index.md`
- `ai/tasks/done/TASK-111-hide-paused-elo-mvp-ui.md`

Rules:

- Prefer modifying only these files.
- If additional files become necessary, explain why in the task outcome and commit message.
- The task file should be moved from `ai/tasks/pending/` to `ai/tasks/done/` only after validation is complete.

## Expected Files Not to Modify

- database migrations
- persisted data
- backend Elo/MMR implementation files
- historical ingestion implementation files
- Docker/Compose configuration
- local `.env`
- unrelated frontend pages

## Constraints

- Keep the change minimal and verifiable.
- Preserve HLL Vietnam project identity: military, Vietnam, tactical, sober.
- Do not implement backend functionality.
- Do not delete backend Elo/MMR code.
- Do not delete historical ingestion code.
- Do not delete endpoints.
- Do not delete persisted data, snapshots, migrations or schemas.
- Do not change backend historical policy.
- Do not reintroduce Comunidad Hispana #03.
- Do not remove normal historical sections such as summary, basic rankings and recent matches.
- Do not introduce unnecessary frameworks or dependencies.
- Do not overwrite repository-specific context with generic platform template text.
- Confirm `backend/runtime/` is not created or committed.

## Validation

Before completing the task:

1. Run `git status`.
2. Run `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`.
3. Run `docker compose down`.
4. Run `docker compose up -d --build`.
5. Run `docker compose ps`.
6. Run `Invoke-WebRequest http://localhost:8000/health | Select-Object -ExpandProperty Content`.
7. Run `Invoke-WebRequest http://localhost:8080 | Select-Object -ExpandProperty StatusCode`.
8. Manually verify `http://localhost:8080/historico.html`:
   - no visible MVP mensual V1 block
   - no visible MVP mensual V2 block
   - no visible Comparativa V1 vs V2 block
   - no visible Elo/MMR mensual block
   - no visible Comunidad Hispana #03 selector
   - summary/basic rankings/recent matches still render
9. Confirm no backend Elo/MMR code was deleted.
10. Confirm no migrations or persisted data changed.
11. Confirm `backend/runtime/` is not created or committed.
12. Review `git diff --name-only` and confirm changed files match the expected scope.

## Commit And Push Requirements

1. Run validation before committing.
2. Run `git status`.
3. Stage only intended files.
4. Commit with a clear message, for example:
   `chore: hide paused elo and mvp UI`
5. Push the branch to origin.
6. Do not leave completed work only in local.

## Outcome

Completed.

Validation performed:

- Ran `git status`.
- Ran `node --check frontend/assets/js/historico.js`.
- Ran `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`.
  - Result: platform validation passed; no product integration tests are configured for this platform-only scope.
- Ran `docker compose down`.
- Ran `docker compose up -d --build`.
- Ran `docker compose ps`.
  - Result: `backend` and `frontend` are running.
- Ran `Invoke-WebRequest http://localhost:8000/health | Select-Object -ExpandProperty Content`.
  - Result: backend returned `status: ok`, `live_data_source: rcon`, and `historical_data_source: rcon`.
- Ran `Invoke-WebRequest http://localhost:8080 | Select-Object -ExpandProperty StatusCode`.
  - Result: `200`.
- Verified served `http://localhost:8080/historico.html` content:
  - no visible MVP mensual V1 block
  - no visible MVP mensual V2 block
  - no visible Comparativa V1 vs V2 block
  - no visible Elo/MMR mensual block
  - no visible Comunidad Hispana #03 selector
  - summary, basic rankings and recent matches markup remains present
- Verified served `frontend/assets/js/historico.js` no longer includes the monthly MVP V1, monthly MVP V2 or Elo/MMR frontend fetch wrappers/endpoints.
- Confirmed no backend Elo/MMR code was deleted.
- Confirmed no migrations or persisted data changed.
- Confirmed `backend/runtime/` was not created or committed.
- Reviewed `git diff --name-only`; changed files are limited to public historical frontend files plus this task file move.

Browser validation note:

- The Browser plugin is available, but its required Node REPL execution tool was not exposed in this session after tool discovery.
- `npx playwright --version` could not be used as a fallback because npm failed with `UNABLE_TO_VERIFY_LEAF_SIGNATURE`.
- The manual visual checklist was therefore validated through the running Docker frontend using served HTML and JavaScript HTTP assertions.

Notable decisions:

- Removed the paused/experimental public UI panels instead of hiding empty shells.
- Disabled the related frontend fetch/render flows by removing their active cache/fetch wiring from `historico.js`.
- Preserved backend endpoints, Elo/MMR implementation code, migrations, persisted data and historical ingestion code.
- Removed `comunidad-hispana-03` from the public historical selector and JavaScript historical server list.

Follow-up:

- No follow-up task is required for this scoped UI pause.

Commit and push:

- Pending at task move time; final commit hash and push result will be reported by the worker after commit/push.

The final worker report must explicitly state:

- which paused/experimental UI blocks were hidden
- whether any related frontend fetch/render flows were disabled
- whether `comunidad-hispana-03` was present and removed from the public historical selector/list
- that normal historical content still renders
- that backend Elo/MMR code, endpoints, migrations and persisted data were preserved
- that `backend/runtime/` was not created or committed
- the commit hash and push result

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
