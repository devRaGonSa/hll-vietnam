---
id: TASK-final-maintenance-and-copy-validation-report
title: Final maintenance and copy validation report
status: review
type: report
team: PM
supporting_teams: [Backend Senior, Frontend Senior, Arquitecto de Base de Datos]
roadmap_item: validation
priority: high
---

# TASK-final-maintenance-and-copy-validation-report

## Scope

Validation-only report for:

- database maintenance cleanup command
- historical-runner maintenance scheduler
- database maintenance operations documentation
- home copy update removing `Vietnam` outside the trailer block

No runtime code was changed during this validation task.

## Validation Commands Run

```powershell
python -m compileall backend/app
PYTHONPATH=backend python -m unittest backend.tests.test_database_maintenance
PYTHONPATH=backend python -m unittest backend.tests.test_historical_runner_maintenance
PYTHONPATH=backend python -m unittest discover -s backend/tests -p "*historical*"
node --check frontend/assets/js/main.js
node --check frontend/assets/js/historico.js
node --check frontend/assets/js/partida-actual.js
git diff --check
Invoke-RestMethod "http://127.0.0.1:8000/api/historical/snapshots/recent-matches?server=all-servers&limit=10" | ConvertTo-Json -Depth 10
Invoke-RestMethod "http://127.0.0.1:8000/api/historical/snapshots/leaderboard?server=all-servers&timeframe=weekly&metric=kills&limit=10" | ConvertTo-Json -Depth 10
Invoke-RestMethod "http://127.0.0.1:8000/api/historical/snapshots/leaderboard?server=all-servers&timeframe=monthly&metric=kills&limit=10" | ConvertTo-Json -Depth 10
$env:PYTHONPATH='backend'; python -m app.database_maintenance cleanup --dry-run
Invoke-WebRequest "http://127.0.0.1:8080/?v=maintenance-copy-validation"
Invoke-WebRequest "http://127.0.0.1:8080/historico.html?v=maintenance-copy-validation"
Invoke-WebRequest "http://127.0.0.1:8080/partida-actual.html?server=comunidad-hispana-01&v=maintenance-copy-validation"
```

## Result

- `compileall`: passed
- `test_database_maintenance`: passed
- `test_historical_runner_maintenance`: passed
- `*historical*` discovery suite: passed
- frontend JavaScript syntax checks: passed
- `git diff --check`: passed

## Docker Status

Docker smoke validation could not run because the local Docker daemon was unavailable.

Observed error:

`failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`

This prevented:

- `docker compose up -d --build backend frontend postgres`
- `docker compose --profile advanced up -d --build historical-runner rcon-historical-worker`
- `docker compose --profile advanced ps`
- `docker compose logs --tail=200 historical-runner`
- `docker compose exec backend python -m app.database_maintenance cleanup --dry-run`

## Local Smoke Checks

Fallback local processes were started instead:

- backend: `python -m app.main`
- frontend: `python -m http.server 8080`

Endpoint summary:

- recent matches endpoint returned `200` with snapshot data for `all-servers`
- weekly leaderboard endpoint returned `200` with a valid empty weekly result for the current dataset
- monthly leaderboard endpoint returned `200` with valid leaderboard rows

Maintenance dry-run summary:

- backend mode: `sqlite`
- protected materialized matches: `22`
- candidate materialized matches: `0`
- candidate player-stat rows: `0`
- candidate admin-log rows: `0`
- candidate server snapshots: `298`
- skipped tables: none

Frontend HTTP checks:

- `/`: `200`
- `/historico.html`: `200`
- `/partida-actual.html?server=comunidad-hispana-01`: `200`

## Copy Validation

Confirmed in the diff for `frontend/index.html`:

- meta description changed from `HLL Vietnam` to `HLL`
- page title changed from `Comunidad Hispana - HLL Vietnam` to `Comunidad Hispana - HLL`
- logo alt text changed from `HLL Vietnam` to `HLL`
- hero accent changed from `HLL Vietnam` to `HLL`
- trailer text `Primer vistazo a HLL Vietnam` was preserved
- iframe title `Trailer HLL Vietnam` was preserved

No browser-based visual QA was performed in this task.

## Unrelated Notes

Python test runs emitted existing `ResourceWarning` messages about unclosed SQLite connections from current initialization helpers. The test suites still passed, and this task did not change that behavior.

An unintended local runtime artifact at `backend/backend/data/hll_vietnam_dev.sqlite3` was created during smoke setup and removed before final scope review.

## Branch/Push Status

- branch push: not performed
- commit: not performed

