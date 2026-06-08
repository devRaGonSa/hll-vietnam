---
id: TASK-168
title: Add annual ranking snapshot generator
status: pending
type: backend
team: Arquitecto de Base de Datos
supporting_teams:
  - Backend Senior
  - Arquitecto Python
roadmap_item: foundation
priority: medium
---

# TASK-168 - Add annual ranking snapshot generator

## Goal

Implementar un generador backend para snapshots anuales top 20 de jugadores sobre datos RCON materializados.

## Context

TASK-166 definió el diseño de persistencia, y TASK-167 ya añadió las tablas:

- `rcon_annual_ranking_snapshots`
- `rcon_annual_ranking_snapshot_items`

Ahora se necesita el generador que rellene esas tablas desde
`rcon_materialized_matches` y `rcon_match_player_stats` con `source_basis = admin-log-match-ended`.

Debe mantenerse separado de frontend y sin introducir una API pública todavía.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `docs/annual-ranking-snapshot-schema-plan.md`
- `backend/app/rcon_admin_log_materialization.py`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/rcon_historical_player_stats.py`
- `backend/app/postgres_rcon_storage.py`
- `backend/app/sqlite_to_postgres_migration.py`

## Expected Files to Modify

- `backend/app/rcon_annual_rankings.py` (crear)
- `backend/app/rcon_admin_log_materialization.py` (si hace falta reutilizar inicialización o alcance)
- `backend/app/postgres_rcon_storage.py` (solo si detecta ajustes de soporte SQLite/Postgres)
- `backend/app/sqlite_to_postgres_migration.py` (solo si detecta ajustes migratorios necesarios)

## Steps

1. Seguir los archivos de `Files to Read First` y respetar el contrato de datos existente.
2. Implementar `generate_annual_ranking_snapshot` con:
   - `year`, `server_key`, `metric`, `limit`, `replace_existing`.
   - Soporte inicial para `metric='kills'`.
3. Agregar una ruta CLI opcional (`python -m app.rcon_annual_rankings generate --year ...`).
4. Reusar conexión SQLite/Postgres con `connect_sqlite_readonly`/`connect_postgres_compat` y placeholders `?`.
5. Validar la función con datos existentes y con BD vacía sin crash.
6. Preparar la Outcome con validación, comportamiento con vacío y limitaciones.

## Constraints

- No crear API pública en esta task.
- Mantener el cambio pequeño y verificable.
- No tocar frontend ni archivos `frontend/assets/js/partida-actual.js`.
- No tocar `frontend/assets/img/clans/bxb.png`.
- No reactivar Elo/MMR.
- No reintroducir Comunidad Hispana #03.
- No ampliar workers históricos salvo que sea imprescindible y justificable.
- No incluir métricas adicionales a `kills` salvo que no amplíe el alcance de forma razonable y segura.

## Validation

- `python -m compileall backend/app`
- `scripts/run-integration-tests.ps1` cuando aplique.
- Validación local con SQLite:
  - inicializar storage,
  - ejecutar generador con un año de prueba (si hay datos),
  - verificar que se inserta el snapshot y hasta `limit` items.
- Verificar comportamiento sin datos: debe terminar sin excepción y crear snapshot vacío o sin items cuando corresponda.
- `git diff --name-only` y confirmar que no se tocó frontend.

## Outcome

- Archivos modificados.
- Función/comando generado.
- Validaciones ejecutadas y resultados (incluyendo caso vacío).
- Limitaciones conocidas.
- Siguiente task recomendada: API pública de ranking anual snapshot.

