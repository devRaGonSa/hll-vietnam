---
id: TASK-109
title: Keep backend startup independent from paused Elo/MMR
status: pending
type: backend
team: Backend Senior
supporting_teams: ["Arquitecto Python"]
roadmap_item: foundation
priority: high
---

# TASK-109 - Keep backend startup independent from paused Elo/MMR

## Goal

Fix backend startup so the default operational Compose profile can start `backend` and `frontend` while Elo/MMR and complex historical materialization remain paused.

The backend must expose `/health` and non-Elo routes even if Elo/MMR engine internals are unavailable or temporarily broken.

## Context

HLL Vietnam has simplified its default operational mode. The normal Compose profile should start only `backend` and `frontend`; historical workers, Elo/MMR, complex historical materialization, and server #03 are paused operationally.

Current validation shows:

- `docker compose config --services` returns only `backend` and `frontend`.
- `docker compose up -d --build` starts the frontend successfully.
- The frontend responds with HTTP 200.
- The backend restarts continuously.
- `/health` fails because backend startup imports Elo/MMR code.
- Backend logs include: `ImportError: cannot import name 'ELO_K_FACTOR' from 'app.elo_mmr_models'`.
- The startup import path is: `app.main -> app.routes -> app.payloads -> app.elo_mmr_engine -> app.elo_mmr_models`.
- `payloads.py` imports Elo/MMR payload functions at module import time, so a paused or broken Elo implementation can break the whole backend, including `/health`.

This task is startup-focused. Preserve the existing HLL Vietnam product identity and repository discipline, and keep the fix narrow.

## Steps

1. Inspect the listed files before changing anything.
2. Confirm the backend startup import path and where Elo/MMR is imported at module load time.
3. Refactor only the startup boundary needed so `/health` and non-Elo routes do not depend on successful import of Elo/MMR engine internals.
4. Prefer lazy importing Elo/MMR functions only inside Elo-specific payload builders or routes.
5. If Elo/MMR is paused or unavailable, make Elo-specific endpoints return a controlled unavailable or fallback payload instead of crashing backend import.
6. Preserve the public API shape as much as possible.
7. Add or update tests if a backend test framework exists.
8. Update lightweight validation if needed so future startup import regressions are caught.
9. Document the paused Elo/MMR startup boundary if documentation needs adjustment.
10. Run the required validation before committing.
11. Move this task file to `ai/tasks/done/` only after validation is complete and the outcome is documented.
12. Stage only intended files, commit, and push the branch to origin.

## Files to Read First

- `backend/app/main.py`
- `backend/app/routes.py`
- `backend/app/payloads.py`
- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_models.py`
- `backend/app/config.py`
- `backend/tests/` if present
- `docker-compose.yml`
- `scripts/run-integration-tests.ps1`
- `README.md`
- `docs/decisions.md`

## Expected Files to Modify

- likely `backend/app/payloads.py`
- possibly `backend/app/routes.py`
- possibly `backend/app/elo_mmr_engine.py`
- possibly `backend/app/elo_mmr_models.py` only if justified
- possibly tests under `backend/tests/`
- possibly `scripts/run-integration-tests.ps1`
- this task file moved from `ai/tasks/pending/` to `ai/tasks/done/`

If additional files become necessary, explain why in the task outcome and commit message.

## Expected Files Not to Modify

- `frontend/**`
- `docker-compose.yml`, unless validation proves a Compose-only issue also exists
- database migrations
- persisted data
- unrelated backend modules
- server #03 configuration

## Constraints

- Do not delete Elo/MMR code.
- Do not delete historical ingestion code.
- Do not remove database migrations or persisted data.
- Do not change frontend behavior.
- Do not reintroduce server #03.
- Keep the fix narrow and startup-focused.
- Do not implement a new Elo/MMR algorithm.
- Do not reintroduce `ELO_K_FACTOR` as a blind compatibility patch unless you prove it is the smallest safe fix and still prevents startup coupling.
- Keep `/health` available even if Elo/MMR import fails.
- Preserve existing public API shape as much as possible.
- Do not modify unrelated files.
- Do not leave completed work only in local; commit and push after validation.

## Validation

Before completing the task, run and document:

- `git status`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- `docker compose down`
- `docker compose up -d --build`
- `docker compose ps`
- `docker compose logs --tail=100 backend`
- `Invoke-WebRequest http://localhost:8000/health | Select-Object -ExpandProperty Content`
- `Invoke-WebRequest http://localhost:8080 | Select-Object -ExpandProperty StatusCode`

Also confirm and document:

- backend is not restarting
- `/health` returns a valid payload
- frontend still returns 200
- no frontend files changed
- no database migrations or persisted data changed
- `backend/runtime/` is not created or committed
- `git diff --name-only` matches the expected scope

If integration tests are relevant and `scripts/run-integration-tests.ps1` exists, use it. If no backend test framework exists for this scope, document that explicitly in the outcome.

## Commit And Push Requirements

- Run all validation before committing.
- Run `git status`.
- Stage only intended files.
- Commit with a clear message, for example: `fix: keep backend startup independent from paused elo`.
- Push the branch to origin.
- Do not leave completed work only in local.

## Outcome

- Validation performed:
  - `git status --short`
  - `python -c "import sys; sys.path.insert(0, 'backend'); import app.main; from app.routes import resolve_get_payload; print(resolve_get_payload('/health'))"`
  - `python -c "import sys; sys.path.insert(0, 'backend'); from app.routes import resolve_get_payload; print(resolve_get_payload('/api/historical/elo-mmr/leaderboard'))"`
  - `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
  - `docker compose down`
  - `docker compose up -d --build`
  - `docker compose ps`
  - `docker compose logs --tail=100 backend`
  - `Invoke-WebRequest http://localhost:8000/health | Select-Object -ExpandProperty Content`
  - `Invoke-WebRequest http://localhost:8080 | Select-Object -ExpandProperty StatusCode`
  - `Invoke-WebRequest 'http://localhost:8000/api/historical/elo-mmr/leaderboard' | Select-Object -ExpandProperty Content`
  - `git diff --name-only`
- Startup coupling removed:
  - `backend/app/payloads.py` no longer imports `app.elo_mmr_engine` at module load time.
  - Elo/MMR engine imports now happen only inside Elo/MMR payload builders.
  - `app.main -> app.routes -> app.payloads` can load and serve `/health` without importing paused Elo/MMR internals.
- Elo/MMR unavailable behavior:
  - If the Elo/MMR engine cannot be imported, Elo/MMR endpoints return the existing `status` + `data` envelope with `source: "elo-mmr-paused"`, `available: false`, `unavailable_reason: "elo-mmr-engine-import-unavailable"`, normal source policy metadata, and empty/null Elo data.
- Tests and validation:
  - No backend test framework is configured for this scope.
  - `scripts/run-integration-tests.ps1` now includes a lightweight backend startup import check and `/health` route resolution check.
- Scope confirmation:
  - Backend was up and not restarting in `docker compose ps`.
  - `/health` returned a valid JSON payload with `status: "ok"`.
  - Frontend returned HTTP `200`.
  - No frontend files changed.
  - No database migrations, persisted data, or server #03 configuration changed.
  - `backend/runtime/` was not created.
  - `git diff --name-only` matched the expected scope: `backend/app/payloads.py` and `scripts/run-integration-tests.ps1`.
- Commit and push:
  - Commit hash and pushed branch are recorded in the final task execution response.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split follow-up work into a new task if the scope expands beyond startup independence.
