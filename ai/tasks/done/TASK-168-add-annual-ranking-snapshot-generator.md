---
id: TASK-168
title: Add annual ranking snapshot generator
status: done
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

TASK-166 definiÃ³ el diseÃ±o de persistencia, y TASK-167 ya aÃ±adiÃ³ las tablas:

- `rcon_annual_ranking_snapshots`
- `rcon_annual_ranking_snapshot_items`

Ahora se necesita el generador que rellene esas tablas desde
`rcon_materialized_matches` y `rcon_match_player_stats` con `source_basis = admin-log-match-ended`.

Debe mantenerse separado de frontend y sin introducir una API pÃºblica todavÃ­a.

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
- `backend/app/rcon_admin_log_materialization.py` (si hace falta reutilizar inicializaciÃ³n o alcance)
- `backend/app/postgres_rcon_storage.py` (solo si detecta ajustes de soporte SQLite/Postgres)
- `backend/app/sqlite_to_postgres_migration.py` (solo si detecta ajustes migratorios necesarios)

## Steps

1. Seguir los archivos de `Files to Read First` y respetar el contrato de datos existente.
2. Implementar `generate_annual_ranking_snapshot` con:
   - `year`, `server_key`, `metric`, `limit`, `replace_existing`.
   - Soporte inicial para `metric='kills'`.
3. Agregar una ruta CLI opcional (`python -m app.rcon_annual_rankings generate --year ...`).
4. Reusar conexiÃ³n SQLite/Postgres con `connect_sqlite_readonly`/`connect_postgres_compat` y placeholders `?`.
5. Validar la funciÃ³n con datos existentes y con BD vacÃ­a sin crash.
6. Preparar la Outcome con validaciÃ³n, comportamiento con vacÃ­o y limitaciones.

## Constraints

- No crear API pÃºblica en esta task.
- Mantener el cambio pequeÃ±o y verificable.
- No tocar frontend ni archivos `frontend/assets/js/partida-actual.js`.
- No tocar `frontend/assets/img/clans/bxb.png`.
- No reactivar Elo/MMR.
- No reintroducir Comunidad Hispana #03.
- No ampliar workers histÃ³ricos salvo que sea imprescindible y justificable.
- No incluir mÃ©tricas adicionales a `kills` salvo que no amplÃ­e el alcance de forma razonable y segura.

## Validation

- `python -m compileall backend/app`
- `scripts/run-integration-tests.ps1` cuando aplique.
- ValidaciÃ³n local con SQLite:
  - inicializar storage,
  - ejecutar generador con un aÃ±o de prueba (si hay datos),
  - verificar que se inserta el snapshot y hasta `limit` items.
- Verificar comportamiento sin datos: debe terminar sin excepciÃ³n y crear snapshot vacÃ­o o sin items cuando corresponda.
- `git diff --name-only` y confirmar que no se tocÃ³ frontend.

## Outcome

- Archivos modificados:
  - `backend/app/rcon_annual_rankings.py` (nuevo)
- FunciÃ³n/comando generado:
  - `generate_annual_ranking_snapshot(year: int, server_key: str | None = None, metric: str = "kills", limit: int = 20, replace_existing: bool = True, db_path: Path | None = None) -> dict[str, object]`.
  - CLI opcional: `python -m app.rcon_annual_rankings generate --year <year> [--server-key <server>] [--metric kills] [--limit <n>] [--replace-existing]`.
- Validaciones ejecutadas y resultados:
  - `python -m compileall backend/app` (sin errores).
  - `scripts/run-integration-tests.ps1` (pasado).
  - `initialize_rcon_materialized_storage()` + `generate_annual_ranking_snapshot(year=2026, metric='kills', limit=10)` con datos existentes: snapshot creado (`source_matches_count` > 0), `items <= 10`.
  - `generate_annual_ranking_snapshot(year=1990, metric='kills', limit=20)` con ventana sin datos: snapshot creado y `items: []` sin excepción.
  - `replace_existing=False` devuelve `skipped_regeneration: True` y reutiliza snapshot existente.
  - CLI manual ejecutada: `python -m app.rcon_annual_rankings generate --year 1990 --metric kills --limit 3`.
- Limitaciones conocidas:
  - Soporte inicial exclusivamente para `metric='kills'`.
  - No se implementÃ³ API pÃºblica ni refresco programado.
  - No se modificÃ³n workers histÃ³ricos.
  - No se tocÃ³ frontend ni archivos preexistentes `frontend/assets/js/partida-actual.js` y `frontend/assets/img/clans/bxb.png`.
- Siguiente task recomendada: API pÃºblica de ranking anual snapshot.
