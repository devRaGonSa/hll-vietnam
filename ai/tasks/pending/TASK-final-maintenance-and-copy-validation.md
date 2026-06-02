---
id: TASK-final-maintenance-and-copy-validation
title: Final maintenance and copy validation
status: pending
type: platform
team: PM
supporting_teams: [Backend Senior, Frontend Senior, Arquitecto de Base de Datos]
roadmap_item: validation
priority: high
---

# TASK-final-maintenance-and-copy-validation - Final maintenance and copy validation

## Goal

Validate the database maintenance implementation, historical-runner integration, documentation and home copy update together before merge to main.

## Context

This task is a final validation task. It should not expand scope. It should verify that previous tasks work together and that the branch is safe to push/merge.

## Steps

1. Inspect the listed files first.
2. Run backend validations.
3. Run frontend validations.
4. Run Docker/local smoke checks where available.
5. Verify no unexpected files changed.
6. Commit/push only if this task produces documentation or small validation notes. Otherwise report validation results.

## Files to Read First

- `AGENTS.md`
- `ai/tasks/done/`
- `backend/app/database_maintenance.py`
- `backend/app/historical_runner.py`
- `docs/database-maintenance.md`
- `frontend/index.html`

## Expected Files to Modify

Normally none.

Optional only if the project convention requires a validation note:

- `ai/tasks/review/TASK-final-maintenance-and-copy-validation-report.md`

Do not modify runtime code unless a blocking validation issue is discovered. If a bug is discovered, create a follow-up task instead of expanding this validation task.

## Required Validation Commands

Run:

```powershell
python -m compileall backend/app
PYTHONPATH=backend python -m unittest backend.tests.test_database_maintenance
PYTHONPATH=backend python -m unittest backend.tests.test_historical_runner_maintenance
PYTHONPATH=backend python -m unittest discover -s backend/tests -p "*historical*"
node --check frontend/assets/js/main.js
node --check frontend/assets/js/historico.js
node --check frontend/assets/js/partida-actual.js
git diff --check
```

If a known unrelated test fails, document:

- exact failing test;
- why it is unrelated;
- whether this task introduced it.

Docker/local smoke checks:

```powershell
docker compose up -d --build backend frontend postgres
docker compose --profile advanced up -d --build historical-runner rcon-historical-worker
docker compose --profile advanced ps
docker compose logs --tail=200 historical-runner
```

Endpoint checks:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/historical/snapshots/recent-matches?server=all-servers&limit=10" | ConvertTo-Json -Depth 10
Invoke-RestMethod "http://127.0.0.1:8000/api/historical/snapshots/leaderboard?server=all-servers&timeframe=weekly&metric=kills&limit=10" | ConvertTo-Json -Depth 10
Invoke-RestMethod "http://127.0.0.1:8000/api/historical/snapshots/leaderboard?server=all-servers&timeframe=monthly&metric=kills&limit=10" | ConvertTo-Json -Depth 10
```

Maintenance dry-run:

```powershell
docker compose exec backend python -m app.database_maintenance cleanup --dry-run
```

Do not run destructive production apply during this validation unless the user explicitly asks.

Frontend visual checks:

`http://localhost:8080/?v=maintenance-copy-validation`

`http://localhost:8080/historico.html?v=maintenance-copy-validation`

`http://localhost:8080/partida-actual.html?server=comunidad-hispana-01&v=maintenance-copy-validation`

Expected frontend result:

- home does not show “HLL Vietnam” in the main hero;
- trailer still says “HLL Vietnam”;
- historical page loads;
- current match page loads.

## Constraints

- Do not add new services.
- Do not touch main directly.
- Do not run production destructive cleanup.
- Do not expand scope.
- Do not reintroduce RCON server #03.
- Do not modify unrelated UI.

## Outcome

Document:

- validation commands run;
- pass/fail result;
- Docker status;
- maintenance dry-run summary;
- endpoint summaries;
- any unrelated failures;
- whether branch was pushed.

Codex CLI must push the completed validation branch if any files changed.

Suggested implementation branch:

`task/final-maintenance-and-copy-validation`

Suggested commit message if a validation note is created:

`test: validate database maintenance and home copy`

## Change Budget

- Prefer no code changes.
- Validation/report only.
