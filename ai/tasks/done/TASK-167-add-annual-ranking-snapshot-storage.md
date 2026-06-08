---
id: TASK-167
title: Add annual ranking snapshot storage
status: done
type: backend
team: Arquitecto de Base de Datos
supporting_teams:
  - Arquitecto Python
  - Backend Senior
roadmap_item: foundation
---

# TASK-167 - Add annual ranking snapshot storage

## Goal

Implement storage primitives to persist annual top 20 player ranking snapshots, following the schema plan in `docs/annual-ranking-snapshot-schema-plan.md`, without adding generator logic or annual ranking APIs yet.

## Context

`TASK-166-design-annual-ranking-snapshot-schema.md` defined the intended schema and constraints for:

- `rcon_annual_ranking_snapshots`
- `rcon_annual_ranking_snapshot_items`

This task creates the storage layer so future yearly ranking generators can run on top of materialized RCON data in SQLite and PostgreSQL-compatible paths.

The implementation must stay backend-only and must not touch frontend assets.

## Validation Scope

The work intentionally stayed limited to backend storage schema initialization and migration compatibility.

## Outcome

### Archivos modificados

- backend/app/rcon_admin_log_materialization.py
- backend/app/postgres_rcon_storage.py
- backend/app/sqlite_to_postgres_migration.py
- ai/tasks/done/TASK-167-add-annual-ranking-snapshot-storage.md

### Tablas nuevas añadidas

- rcon_annual_ranking_snapshots
- rcon_annual_ranking_snapshot_items

### Compatibilidad SQLite/Postgres

- SQLite: tablas y restricciones añadidas en `initialize_rcon_materialized_storage()` (backend/app/rcon_admin_log_materialization.py).
- PostgreSQL: tablas, índices y restricciones añadidas a `RCON_SCHEMA_SQL` (backend/app/postgres_rcon_storage.py).
- Migración: tablas añadidas a `RCON_TABLES` y a `_sync_sequences()` en `backend/app/sqlite_to_postgres_migration.py`.

### Validaciones realizadas

- `python -m compileall backend/app`
- `scripts/run-integration-tests.ps1`
- Validación de inicialización de storage SQLite con base temporal y consulta en `sqlite_master` para ambas tablas.

### Limitaciones conocidas

- No se implementó generador anual ni endpoint de ranking anual.
- No se tocó frontend.
- No hay validación de runtime PostgreSQL porque no había entorno Postgres requerido por el alcance de esta task.

### Próximo task recomendado

- TASK-168 (Generador de snapshot anual top 20).

