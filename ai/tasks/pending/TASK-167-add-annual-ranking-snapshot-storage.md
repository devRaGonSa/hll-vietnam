---
id: TASK-167
title: Add annual ranking snapshot storage
status: pending
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

## Steps

1. Read all files listed below before any edit.
2. Add snapshot table creation for both SQLite and PostgreSQL-compatible schema paths if present.
3. Include SQLite/Postgres-safe DDL in migration-like storage initializer surfaces used by the project.
4. Keep changes minimal and avoid endpoint or generator creation.
5. Validate syntax/initialization and keep changed files within expected scope.
6. Update task outcome once completed and move to `ai/tasks/done` only after scope checks pass.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `docs/annual-ranking-snapshot-schema-plan.md`
- `backend/app/rcon_admin_log_materialization.py`
- `backend/app/postgres_rcon_storage.py`
- `backend/app/sqlite_to_postgres_migration.py`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/rcon_historical_player_stats.py`

## Expected Files to Modify

- `backend/app/rcon_admin_log_materialization.py` or equivalent materialized-RCON storage init module
- `backend/app/postgres_rcon_storage.py` or equivalent PostgreSQL schema initializer
- `backend/app/sqlite_to_postgres_migration.py` if migration table lists and sequence sync require alignment
- `ai/tasks/done/TASK-167-add-annual-ranking-snapshot-storage.md`

## Constraints

- No generador anual de ranking en este scope.
- No endpoint anual agregado aún.
- No modificaciones de frontend.
- No tocar `frontend/assets/js/partida-actual.js`.
- No tocar `frontend/assets/img/clans/bxb.png`.
- Mantener compatibilidad SQLite/Postgres si la capa existente ya la usa.
- No reactivar Elo/MMR.
- No reintroducir Comunidad Hispana #03.
- No ampliar `historical workers` salvo cambios estrictamente necesarios en inicialización de storage.

## Validation

- `python -m compileall backend/app`
- `scripts/run-integration-tests.ps1` (si aplica).
- Validación de inicialización de storage para SQLite.
- Validación de compatibilidad SQL/DDL con Postgres en los módulos de compatibilidad existentes.
- `git diff --name-only` debe mostrar sólo el alcance esperado.

## Outcome

Documentar en el cierre de task:
- Archivos modificados.
- Tablas nuevas añadidas (`rcon_annual_ranking_snapshots`, `rcon_annual_ranking_snapshot_items`).
- Compatibilidad SQLite/Postgres.
- Validaciones ejecutadas.
- Limitaciones conocidas.
- Siguiente task recomendada: generador de snapshot anual top 20.

