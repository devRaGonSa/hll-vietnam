---
id: TASK-166
title: Design annual ranking snapshot schema
status: done
type: documentation
team: Arquitecto de Base de Datos
supporting_teams: []
roadmap_item: foundation
priority: medium
---

# TASK-166 - Design annual ranking snapshot schema

## Goal

Define a backend storage plan for annual top-20 ranking snapshots (kills) that avoids
full recalculation on each public request.

## Context

- TASK-162 implementó el endpoint de búsqueda de jugadores para Stats.
- TASK-163 implementó el endpoint de stats personales.
- TASK-165 implementó la vista frontend de Stats.

This task is documentation-only and prepares the schema needed by the next backend
endpoint iteration:

- `GET /api/stats/rankings/annual?year=<year>&server_id=<server-or-all>&metric=kills`

## Steps

1. Revisión de archivos listados en `Files to Read First`.
2. Diseñar propuesta de tablas para snapshots anuales y sus items.
3. Definir restricciones de unicidad, índices y política de reemplazo.
4. Documentar compatibilidad SQLite/Postgres siguiendo el patrón usado en `rcon_historical_leaderboards.py`.
5. Especificar API y estados esperados para lectura de snapshot.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `docs/stats-section-functional-plan.md`
- `docs/stats-frontend-integration-plan.md`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/rcon_historical_player_stats.py`
- `backend/app/rcon_admin_log_materialization.py`
- `backend/app/postgres_rcon_storage.py`
- `backend/app/postgres_display_storage.py`
- `backend/app/sqlite_to_postgres_migration.py`

## Expected Files to Modify

- `ai/tasks/done/TASK-166-design-annual-ranking-snapshot-schema.md`
- `docs/annual-ranking-snapshot-schema-plan.md`

## Constraints

- No migrations in this task.
- No backend implementation code changes in this task.
- No frontend changes in this task.
- No Elo/MMR reactivation.
- No Comunidad Hispana #03 reintroduction.
- No modification of historical workers.
- No touch to:
  - `frontend/assets/js/partida-actual.js`
  - `frontend/assets/img/clans/bxb.png`

## Validation

- Confirm only documentation files were created/updated.
- `git diff --name-only` must match expected scope.
- Document that no automated tests are applicable for documentation-only task.

## Outcome

- Documento creado:
  - `docs/annual-ranking-snapshot-schema-plan.md`
- Archivos revisados:
  - `AGENTS.md`
  - `ai/repo-context.md`
  - `ai/architecture-index.md`
  - `docs/stats-section-functional-plan.md`
  - `docs/stats-frontend-integration-plan.md`
  - `backend/app/rcon_historical_leaderboards.py`
  - `backend/app/rcon_historical_player_stats.py`
  - `backend/app/rcon_admin_log_materialization.py`
  - `backend/app/postgres_rcon_storage.py`
  - `backend/app/postgres_display_storage.py`
  - `backend/app/sqlite_to_postgres_migration.py`
- Validación realizada:
  - Confirmado que la tarea quedó en alcance documental y no se introdujeron cambios de backend/frontend.
  - Se validó que los únicos archivos esperados para esta tarea estén cubiertos por su documentación.
  - No se requiere ejecutar pruebas automáticas: es una tarea de documentación.
- Limitaciones:
  - No se tocó código backend ni frontend.
  - No se ejecutaron migraciones.
- Siguiente task recomendada:
  - Crear migración y estructura de persistencia para snapshots anuales de ranking (`rcon_annual_ranking_*`) y su job de generación.

## Change Budget

- Prefer fewer than 5 modified files.
- Keep changes concise and reviewable.
