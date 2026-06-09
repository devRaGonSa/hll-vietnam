---
id: TASK-200-fix-player-profile-runtime-postgres-grouping
title: Fix player profile runtime PostgreSQL grouping
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto de Base de Datos
  - Arquitecto Python
roadmap_item: foundation
priority: high
---

# TASK-200 - Fix player profile runtime PostgreSQL grouping

## Goal

Corregir el `500` de `/api/stats/players/{player_id}?server_id={server}` cuando el jugador no tiene fila en `player_period_stats` para el timeframe solicitado y la ruta cae al fallback runtime sobre PostgreSQL.

## Context

`TASK-199` introdujo `player_period_stats` y el endpoint público ya usa correctamente el read model cuando existe una fila para el jugador/scope/timeframe solicitado. El problema aparece cuando el read model no tiene fila para ese jugador en el timeframe pedido y la lectura cae a `_get_rcon_materialized_player_stats_runtime(...)`.

La causa raíz validada en producción es una query de `_fetch_player_stats(...)` en `backend/app/rcon_historical_player_stats.py` que usa una expresión equivalente a `COALESCE(MAX(stats.player_name), stats.player_id)` sin agregar ni agrupar `stats.player_id`. SQLite lo tolera, pero PostgreSQL lanza `psycopg.errors.GroupingError`, provocando un `500` para casos como `server_id=comunidad-hispana-01` cuando no hay fila `weekly` o `monthly` en `player_period_stats`.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Inspect the listed files first.
2. Fix the runtime fallback query used by `_fetch_player_stats(...)` so it is valid in PostgreSQL.
3. Preserve SQLite/local compatibility when the explicit local path is used.
4. Keep `player_period_stats` as the preferred source whenever a row exists.
5. Keep runtime fallback when the read model is missing, incomplete or unavailable.
6. Ensure the no-read-model-row case returns the existing controlled contract instead of a `500`.
7. Validate the affected player-profile, player-search and ranking snapshot paths.
8. Document the root cause, affected SQL, new behavior and production validation path.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `backend/app/rcon_historical_player_stats.py`
- `backend/app/payloads.py`
- `backend/app/routes.py`
- `backend/app/postgres_rcon_storage.py`
- `scripts/run-stats-validation.ps1`
- `docs/player-period-stats-read-model-plan.md`
- `ai/tasks/done/TASK-199-add-player-period-stats-read-model.md`

## Expected Files to Modify

- `backend/app/rcon_historical_player_stats.py`
- `scripts/run-stats-validation.ps1`
- `ai/tasks/in-progress/TASK-200-fix-player-profile-runtime-postgres-grouping.md`

## Constraints

- Keep the change minimal and backend-only.
- Do not execute `ai-platform run`.
- Do not modify frontend.
- Do not change design.
- Do not touch images or assets.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana `#03`.
- Do not mix automation changes into this task.
- Do not change public contracts except to avoid the runtime `500`.
- Keep `player_period_stats` as the preferred source when data exists.
- Keep runtime fallback active when the read model has no row for the requested scope/window.
- If runtime also has no rows for that scope/window, return the existing controlled empty/zero contract instead of throwing.
- Do not break:
  - `/api/stats/players/search`
  - `/api/stats/players/{player_id}`
  - ranking snapshots
  - `refresh-player-search-index`
  - `refresh-player-period-stats`

## Validation

Before completing the task ensure:

- `python -m py_compile backend/app/rcon_historical_player_stats.py`
- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- local validation proves `_fetch_player_stats(...)` no longer emits PostgreSQL-invalid aggregate SQL
- local validation proves the runtime fallback path does not throw when a server-specific read-model row is missing
- local validation proves `player_period_stats` is still used when a row exists
- local validation proves `player_search_index` still works
- local validation proves ranking snapshots are not broken
- validate these profile cases:
  - `/api/stats/players/76561197978442431`
  - `/api/stats/players/76561197978442431?server_id=all`
  - `/api/stats/players/76561197978442431?server_id=all-servers`
  - `/api/stats/players/76561197978442431?server_id=comunidad-hispana-02`
  - `/api/stats/players/76561197978442431?server_id=comunidad-hispana-01`
- the last case must not return `500`
- `git diff --name-only` matches the expected scope

## Outcome

Implemented:

- `backend/app/rcon_historical_player_stats.py`
  - fixed `_fetch_player_stats(...)` runtime aggregation SQL
  - removed the PostgreSQL-invalid expression `COALESCE(MAX(stats.player_name), stats.player_id)`
  - kept the player-name fallback in Python with `row["player_name"] or player_id`
- `scripts/run-stats-validation.ps1`
  - added a SQL-shape regression check for `_fetch_player_stats(...)`
  - added a fixture with a `yearly-only-player` on `comunidad-hispana-01`
  - validated the server-specific fallback path when `player_period_stats` has no weekly/monthly row and runtime also has no rows in the requested window

Root cause of the `500`:

- when `/api/stats/players/{player_id}` could not serve `player_period_stats`, it fell back to `_get_rcon_materialized_player_stats_runtime(...)`
- `_fetch_player_stats(...)` executed a grouped aggregate query that selected:
  - `COALESCE(MAX(stats.player_name), stats.player_id) AS player_name`
- PostgreSQL rejects `stats.player_id` in that expression because it is neither aggregated nor part of `GROUP BY`
- SQLite/local compatibility masked the issue because SQLite tolerates that aggregate shape

Concrete affected SQL shape:

- previous:
  - `SELECT COALESCE(MAX(stats.player_name), stats.player_id) AS player_name, ...`
- new:
  - `SELECT MAX(stats.player_name) AS player_name, ...`
- public fallback behavior stays intact because Python already normalizes the result with `str(row["player_name"] or player_id)`

Previous behavior:

- read-model hits returned `read_model=player-period-stats` and `fallback_used=false`
- if the requested scope/timeframe had no player row and runtime fallback executed on PostgreSQL, the endpoint could raise `psycopg.errors.GroupingError`
- the request then returned HTTP `500`

New behavior:

- `player_period_stats` remains the preferred source when a row exists
- runtime fallback remains active when the read model is empty, incomplete or unavailable
- PostgreSQL fallback SQL is now valid
- if the requested scope/window has no runtime rows, the endpoint returns the existing controlled zero-value profile contract instead of throwing
- no frontend, design, asset, Elo/MMR or Comunidad Hispana `#03` changes were made

Validations executed:

- `python -m py_compile backend/app/rcon_historical_player_stats.py`
- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`

Validation notes:

- local import-based validation confirmed `_fetch_player_stats(...)` no longer emits the PostgreSQL-invalid aggregate shape
- local fixture validation confirmed the server-specific missing-read-model fallback does not throw and returns a controlled response
- `player_period_stats` still serves the profile path when rows exist
- `player_search_index` and ranking snapshot validations still pass through `scripts/run-stats-validation.ps1`
- live HTTP validation at `http://127.0.0.1:8000` could not run in this environment because the backend was not up; the script reported that explicitly and route-contract checks still passed via local Python imports
- `git diff --name-only` included unrelated pre-existing changes in `ai/system-metrics.md` and `frontend/assets/img/weapons/black/*`; those files were not modified by this task

How to validate in production:

- call:
  - `/api/stats/players/76561197978442431`
  - `/api/stats/players/76561197978442431?server_id=all`
  - `/api/stats/players/76561197978442431?server_id=all-servers`
  - `/api/stats/players/76561197978442431?server_id=comunidad-hispana-02`
  - `/api/stats/players/76561197978442431?server_id=comunidad-hispana-01`
- verify the first four still report:
  - `source.read_model = "player-period-stats"`
  - `source.fallback_used = false`
- verify the last case no longer returns HTTP `500`
- verify the last case returns a controlled stats payload with fallback metadata instead of a PostgreSQL grouping exception

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
