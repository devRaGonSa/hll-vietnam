---
id: TASK-169-add-annual-ranking-snapshot-api
title: Add annual ranking snapshot API
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto Python
  - Arquitecto de Base de Datos
roadmap_item: foundation
priority: medium
---

# TASK-169-add-annual-ranking-snapshot-api

## Goal

Exponer una API de lectura publica para el ranking anual top 20 precomputado desde snapshots almacenadas.

## Context

La API debe consumir `rcon_annual_ranking_snapshots` y `rcon_annual_ranking_snapshot_items` generados por el modulo de generacion (TASK-168) y las tablas añadidas por TASK-167.

Mantiene compatibilidad entre SQLite y Postgres usando el patron de conexion compartido.

## Steps

1. Leer los archivos indicados en "Files to Read First".
2. Implementar el endpoint GET `/api/stats/rankings/annual` en backend sin recalcular ranking.
3. Anadir payload y registro de ruta siguiendo patrones existentes.
4. Validar comportamientos esperados (snapshot existente, faltante, metrica no soportada).

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `docs/annual-ranking-snapshot-schema-plan.md`
- `docs/stats-section-functional-plan.md`
- `backend/app/rcon_annual_rankings.py`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/rcon_historical_player_stats.py`
- `backend/app/routes.py`
- `backend/app/payloads.py`
- `backend/app/rcon_admin_log_materialization.py`
- `backend/app/postgres_rcon_storage.py`

## Expected Files to Modify

- `backend/app/rcon_annual_rankings.py`
- `backend/app/payloads.py`
- `backend/app/routes.py`

## Constraints

- Endpoint: `GET /api/stats/rankings/annual?year=<year>&server_id=<server-or-all>&metric=kills&limit=<n>`
- `server_id` opcional, `all` por defecto.
- `metric` por ahora solo `kills`.
- `limit` opcional, por defecto 20, validado razonablemente.
- Si no existe snapshot debe responder `snapshot_status="missing"` con `items=[]` y estado HTTP 200.
- No generar snapshot en el endpoint.
- Mantener compatibilidad SQLite/Postgres.
- No tocar frontend.
- No tocar `frontend/assets/js/partida-actual.js` ni `frontend/assets/img/clans/bxb.png`.
- No reactivar Elo/MMR.
- No incluir Comunidad Hispana #03.
- No modificar workers historicos salvo justificacion imprescindible.

## Validation

- `python -m compileall backend/app`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- Validacion manual del contrato con backend local o metodo equivalente.

## Outcome

### Files modified

- `backend/app/rcon_annual_rankings.py`
- `backend/app/payloads.py`
- `backend/app/routes.py`

### Endpoint created

- `GET /api/stats/rankings/annual?year=<year>&server_id=<server-or-all>&metric=kills&limit=<n>`
- Respuestas:
  - `snapshot_status=ready` cuando existe snapshot.
  - `snapshot_status=missing` cuando no existe snapshot, y devuelve `items=[]`.
- Soporta `metric=kills` y devuelve 400 para metricas no soportadas.

### Validations performed

- `python -m compileall backend/app` ✅
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1` ✅
- Validacion manual usando `app.routes.resolve_get_payload`:
  - `/api/stats/rankings/annual` (HTTP 200, respuesta OK)
  - `/api/stats/rankings/annual?year=1990` (HTTP 200)
  - `/api/stats/rankings/annual?year=1990&metric=kills&limit=3` (HTTP 200)
  - `/api/stats/rankings/annual?metric=deaths` (HTTP 400, metrica invalida)
  - `/api/stats/rankings/annual?year=1900` (HTTP 200, snapshot_status `missing`, `items=[]`)

### Limitations

- Soporta solo `metric=kills` en esta fase.
- Endpoint no genera snapshots (no recalculo); requiere que TASK-168 haya generado datos.
- No se toco frontend en este alcance.

### Next task recommendation

Conectar ranking anual top 20 desde frontend Stats.
