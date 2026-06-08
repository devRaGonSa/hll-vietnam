---
id: TASK-169-add-annual-ranking-snapshot-api
title: Add annual ranking snapshot API
status: pending
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

Exponer una API de lectura pública para el ranking anual top 20 precomputado desde snapshots almacenadas.

## Context

La API debe consumir `rcon_annual_ranking_snapshots` y `rcon_annual_ranking_snapshot_items` generados por el módulo de generación (TASK-168) y las tablas añadidas por TASK-167.

Mantiene compatibilidad entre SQLite y Postgres usando el patrón de conexión compartido.

## Steps

1. Leer los archivos indicados en "Files to Read First".
2. Implementar el endpoint GET `/api/stats/rankings/annual` en backend sin recalcular ranking.
3. Añadir payload y registro de ruta siguiendo patrones existentes.
4. Validar comportamientos esperados (snapshot existente, faltante, métrica no soportada).

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

- `ai/tasks/pending/TASK-169-add-annual-ranking-snapshot-api.md` (al crear la tarea)
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
- No modificar workers históricos salvo justificación imprescindible.

## Validation

- `python -m compileall backend/app`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- Validación manual del contrato con backend local o método equivalente.

## Outcome

- registrar archivos modificados
- validar comportamiento con y sin snapshot
- indicar limitaciones conocidas
- proponer siguiente tarea
