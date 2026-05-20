---
id: TASK-140
title: Restore historical runner Elo imports
status: done
type: backend
team: Backend Senior
supporting_teams: [Arquitecto Python]
roadmap_item: foundation
priority: high
---

# TASK-140 - Restore historical runner Elo imports

## Goal

Restore `historical-runner` startup by fixing the Elo/MMR model import contract used by `app.elo_mmr_engine`.

## Context

The advanced `historical-runner` service runs `python -m app.historical_runner --hourly` and intentionally imports `rebuild_elo_mmr_models`. The engine imports scoring constants from `app.elo_mmr_models`, but that module no longer exports every constant required by the engine.

## Steps

1. Inspect the listed files first.
2. Restore the missing Elo/MMR model/config constants in the correct module.
3. Keep the change narrow and avoid disabling the runner or Elo/MMR silently.
4. Validate the backend, RCON data pipeline, integration tests, advanced Compose services and relevant HTTP endpoints.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/backend-senior.md`
- `backend/app/historical_runner.py`
- `backend/app/historical_ingestion.py`
- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_models.py`
- `backend/app/elo_mmr_storage.py`

## Expected Files to Modify

- `backend/app/elo_mmr_models.py`
- `.gitignore`
- `ai/tasks/done/TASK-140-fix-historical-runner-elo-import.md`

## Constraints

- Do not remove or disable `historical-runner`.
- Do not disable Elo/MMR silently.
- Do not modify frontend files.
- Do not reintroduce Comunidad Hispana #03.
- Do not commit runtime database files.
- Preserve RCON ingestion, AdminLog materialization, recent matches, match detail and scoreboard candidate backfill.

## Validation

- `python -m compileall backend/app`
- `powershell -ExecutionPolicy Bypass -File scripts/run-rcon-data-pipeline-tests.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- `docker compose --profile advanced up -d --build backend frontend historical-runner rcon-historical-worker`
- `docker compose --profile advanced ps`
- `docker compose logs --tail=100 historical-runner`
- `Invoke-WebRequest "http://localhost:8000/health" | Select-Object -ExpandProperty Content`
- `Invoke-WebRequest "http://localhost:8000/api/historical/recent-matches?server=all-servers&limit=20" | Select-Object -ExpandProperty Content`

## Outcome

Implemented the import-contract fix by restoring the missing Elo/MMR model constants exported from `backend/app/elo_mmr_models.py`:

- `ELO_K_FACTOR`
- `MIN_VALID_PLAYER_PARTICIPATION_SECONDS`
- `MIN_VALID_PLAYER_PARTICIPATION_RATIO`

The constants live with the rest of the Elo/MMR model thresholds, preserving the existing `app.elo_mmr_engine` import boundary and avoiding any silent disabling of the runner or Elo/MMR. `.gitignore` now also ignores `backend/data/*.writer.lock` because advanced Compose validation creates the shared SQLite writer lock as runtime state.

Validation completed:

- `python -m compileall backend/app`
- Direct imports of `app.historical_runner`, `app.historical_ingestion` and `app.elo_mmr_engine`
- `powershell -ExecutionPolicy Bypass -File scripts/run-rcon-data-pipeline-tests.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- `docker compose --profile advanced up -d --build backend frontend historical-runner rcon-historical-worker`
- `docker compose --profile advanced ps`
- `docker compose logs --tail=100 historical-runner`
- `Invoke-WebRequest "http://localhost:8000/health" | Select-Object -ExpandProperty Content`
- `Invoke-WebRequest "http://localhost:8000/api/historical/recent-matches?server=all-servers&limit=20" | Select-Object -ExpandProperty Content`
- `Invoke-WebRequest "http://localhost:8080/historico.html?nocache=runner" | Select-Object -ExpandProperty StatusCode`

Manual verification:

- `historical-runner` stayed `Up` in the advanced profile.
- `rcon-historical-worker` stayed `Up`.
- `historical-runner` logs showed `historical-refresh-loop-started` and no `ImportError`.
- `/health` returned `status: "ok"`.
- `/api/historical/recent-matches` returned RCON-backed recent match data.
- `historico.html` returned HTTP 200.
- No frontend files were modified.
- No runtime database files were staged or committed.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
