---
id: TASK-205
title: Fix annual ranking generator PostgreSQL default
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto de Base de Datos
  - Arquitecto Python
roadmap_item: foundation
priority: high
---

# TASK-205 - Fix annual ranking generator PostgreSQL default

## Goal

Corregir el CLI anual de `backend/app/rcon_annual_rankings.py` para que use PostgreSQL por defecto cuando `HLL_BACKEND_DATABASE_URL` esta configurado, alineando la generacion operativa con el read path de `/api/ranking?timeframe=annual...`.

## Context

Produccion ya confirma que la API anual consulta el read model correcto pero no encuentra snapshot, mientras el comando manual anual generaba en SQLite local. La causa raiz validada era que `_main()` llamaba a `generate_annual_ranking_snapshot(..., db_path=get_storage_path())`, lo que forzaba `explicit_sqlite_path != None` y desactivaba `use_postgres_rcon_storage(...)` aunque `get_database_url()` existiera.

Este comportamiento ya se habia corregido en weekly/monthly durante `TASK-195`, por lo que esta task replica el mismo criterio operacional en el flujo anual sin tocar frontend, endpoints publicos ni la logica anual fuera de la seleccion de storage por defecto.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Revisar el flujo anual actual y comparar `_main()` con el patron corregido en weekly/monthly.
2. Cambiar el CLI anual para que use `db_path=None` por defecto y PostgreSQL cuando el entorno lo soporte.
3. Mantener SQLite solo como override explicito mediante `--sqlite-path`.
4. Preservar la salida JSON del CLI y el contrato publico del endpoint anual.
5. Extender la regresion de `scripts/run-stats-validation.ps1` para cubrir la ruta anual.
6. Documentar causa raiz, comportamiento anterior, comportamiento nuevo y validacion operacional.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `backend/app/rcon_annual_rankings.py`
- `backend/app/config.py`
- `backend/app/postgres_rcon_storage.py`
- `backend/app/rcon_historical_leaderboards.py`
- `scripts/run-stats-validation.ps1`
- `docs/ranking-snapshot-read-model-plan.md`
- `docs/annual-ranking-snapshot-runbook.md`
- `docs/annual-ranking-snapshot-schema-plan.md`
- `ai/tasks/done/TASK-195-fix-ranking-snapshot-generator-postgres-default.md`
- `ai/tasks/done/TASK-196-fix-ranking-snapshot-cli-json-serialization.md`

## Expected Files to Modify

- `backend/app/rcon_annual_rankings.py`
- `scripts/run-stats-validation.ps1`
- `docs/annual-ranking-snapshot-runbook.md`
- `ai/tasks/done/TASK-205-fix-annual-ranking-generator-postgres-default.md`

## Constraints

- Keep the change minimal.
- No ejecutar `ai-platform run`.
- No modificar frontend ni diseno.
- No cambiar el contrato publico de `/api/ranking?timeframe=annual...`.
- No cambiar la logica de calculo anual salvo lo necesario para usar PostgreSQL por defecto.
- No tocar weekly/monthly salvo reutilizacion minima de patron o helper ya existente.
- No tocar `player_search_index`, `player_period_stats` ni el runner.
- No tocar `frontend/assets/img/weapons/` ni SVGs de armas.
- No reactivar Elo/MMR.
- No reintroducir Comunidad Hispana #03.
- No mezclar esta task con los cambios visuales pendientes de `TASK-204`.

## Validation

Before completing the task ensure:

- `python -m py_compile backend/app/rcon_annual_rankings.py`
- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- validacion local o por import demuestra que `_main()` ya no pasa `get_storage_path()` por defecto
- validacion local demuestra que `generate_annual_ranking_snapshot(..., db_path=None)` usa PostgreSQL cuando `HLL_BACKEND_DATABASE_URL` esta configurado
- la salida JSON del CLI anual sigue serializando correctamente
- `git diff --name-only` matches the expected scope

## Outcome

Causa raiz:

- `backend/app/rcon_annual_rankings.py` llamaba a `generate_annual_ranking_snapshot(..., db_path=get_storage_path())` desde `_main()`
- eso forzaba `explicit_sqlite_path != None`
- `use_postgres_rcon_storage(...)` devolvia `False` incluso con `HLL_BACKEND_DATABASE_URL` configurado
- el CLI anual generaba snapshots en SQLite mientras `/api/ranking?timeframe=annual...` leia PostgreSQL

Comportamiento anterior:

- `python -m app.rcon_annual_rankings generate ...`
- usaba SQLite por defecto
- podia dejar `rcon_annual_ranking_snapshots` y `rcon_annual_ranking_snapshot_items` vacias en PostgreSQL aunque el operador hubiera ejecutado el comando con exito

Comportamiento nuevo:

- el CLI anual usa PostgreSQL por defecto cuando `HLL_BACKEND_DATABASE_URL` esta configurado
- SQLite queda disponible solo mediante `--sqlite-path`
- la salida JSON del CLI anual sigue serializando `datetime` y `date` correctamente

Archivos modificados:

- `backend/app/rcon_annual_rankings.py`
- `scripts/run-stats-validation.ps1`
- `docs/annual-ranking-snapshot-runbook.md`
- `ai/tasks/done/TASK-205-fix-annual-ranking-generator-postgres-default.md`

Cambio aplicado en codigo:

- `backend/app/rcon_annual_rankings.py`
  - elimina el default que forzaba `get_storage_path()` en `_main()`
  - anade `--sqlite-path <path>` como override explicito
  - pasa `db_path=args.sqlite_path` al generador anual
  - anade serializacion JSON segura para `datetime` y `date`

Regresion anadida:

- `scripts/run-stats-validation.ps1`
  - valida que el CLI anual use `db_path=None` por defecto
  - valida que `--sqlite-path` siga funcionando
  - valida por import que `generate_annual_ranking_snapshot(..., db_path=None)` seleccione PostgreSQL cuando `HLL_BACKEND_DATABASE_URL` esta configurado

Comando operativo final:

- local / contenedor backend:
  - `python -m app.rcon_annual_rankings generate --year 2026 --server-key all-servers --metric kills --limit 30 --replace-existing`

Comando Docker final recomendado:

- `docker compose exec backend python -m app.rcon_annual_rankings generate --year 2026 --server-key all-servers --metric kills --limit 30 --replace-existing`

Validaciones ejecutadas:

- `python -m py_compile backend/app/rcon_annual_rankings.py`
- validacion local por import de `_main()`:
  - confirma `db_path=None` por defecto
  - confirma serializacion JSON correcta de `datetime` y `date`
- validacion local por import de `generate_annual_ranking_snapshot(..., db_path=None)`:
  - confirma seleccion de PostgreSQL cuando `HLL_BACKEND_DATABASE_URL` esta configurado
- ejecucion manual real del CLI:
  - `python -m app.rcon_annual_rankings generate --year 2026 --server-key all-servers --metric kills --limit 30 --replace-existing --sqlite-path data/hll_vietnam_dev.sqlite3`
- validacion local del endpoint anual por import:
  - `/api/ranking?timeframe=annual&year=<current_year>&server_id=all&metric=kills&limit=20`
  - mantiene `status=ok`, `timeframe=annual`, `metric=kills`, `snapshot_status`, `items`, `generated_at`, `window_start` y `window_end`

Resultado de scripts globales:

- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
  - falla antes de la nueva regresion anual por una asercion de frontend preexistente:
    - `Stats page no longer exposes backend state chip.`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
  - falla por arrastrar el mismo fallo previo de `run-stats-validation.ps1`

Nota de alcance sobre esos fallos:

- la causa no pertenece a esta task backend
- viene del arbol local ya modificado en frontend y de la validacion global que aun espera `id="stats-backend-state"`
- no se corrigio aqui porque el usuario pidio no modificar frontend ni mezclar esta task con `TASK-204`

Como validar en produccion:

1. Ejecutar:
   - `docker compose exec backend python -m app.rcon_annual_rankings generate --year 2026 --server-key all-servers --metric kills --limit 30 --replace-existing`
2. Consultar PostgreSQL:
   - `rcon_annual_ranking_snapshots`
   - `rcon_annual_ranking_snapshot_items`
3. Confirmar que ya no se escriben filas nuevas en SQLite por defecto.
4. Llamar a:
   - `/api/ranking?timeframe=annual&metric=kills&limit=30&year=2026`
5. Confirmar:
   - `snapshot_status=ready`
   - `items` no vacio cuando exista cobertura anual
   - `read_model = rcon-annual-ranking-snapshot`

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
