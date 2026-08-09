---
id: TASK-214
title: Audit public query performance bottlenecks
status: done
type: research
team: Analista
supporting_teams:
  - Frontend Senior
  - Backend Senior
  - Arquitecto de Base de Datos
roadmap_item: foundation
priority: high
---

# TASK-214 - Audit public query performance bottlenecks

## Goal

Auditar los posibles cuellos de botella de las consultas publicas de HLL Vietnam y producir un analisis tecnico accionable para futuras optimizaciones, sin implementar cambios funcionales todavia.

## Context

El ranking anual ya sufrio un cuello de botella grave y quedo corregido al sacar `initialize_rcon_materialized_storage()` del path publico de lectura anual en PostgreSQL. Tras ese fix, las latencias confirmadas de API de ranking son bajas, pero la UI publica aun puede percibirse lenta o quedarse temporalmente en estados de carga.

La regla arquitectonica objetivo de esta auditoria es explicita:

- los endpoints publicos deben leer read models propios en PostgreSQL
- no deben consultar RCON directo
- no deben consultar scoreboard publico
- no deben recalcular rankings en runtime
- no deben escanear `rcon_match_player_stats` salvo en procesos internos
- no deben inicializar o migrar storage dentro de request publico
- no deben bloquearse por health checks no necesarios

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Revisar primero la documentacion base, las rutas publicas y los frontends que las consumen.
2. Auditar endpoints publicos, fallbacks, read models, polling, cargas secuenciales y riesgos de runtime.
3. Redactar el informe tecnico en `docs/PERFORMANCE_PUBLIC_QUERY_AUDIT.md`.
4. Cerrar esta task en `ai/tasks/done/` documentando hallazgos, validacion y exclusiones.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `docs/decisions.md`
- `backend/app/routes.py`
- `backend/app/payloads.py`

## Expected Files to Modify

- `docs/PERFORMANCE_PUBLIC_QUERY_AUDIT.md`
- `ai/tasks/done/TASK-214-audit-public-query-performance-bottlenecks.md`

## Constraints

- Keep the change minimal.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- Do not implement backend functionality unless the task explicitly requires it.
- Do not expand Elo/MMR, historical workers or RCON server #03 handling unless the task explicitly requires it.
- Do not overwrite repository-specific context with generic platform template text.
- No ejecutar `ai-platform run`.
- No implementar optimizaciones funcionales todavia.
- No cambiar comportamiento de endpoints.
- No tocar frontend funcional.
- No tocar backend funcional.
- No tocar tests.
- No tocar assets de armas.
- No tocar SVGs.
- No modificar imagenes fisicas.
- No reactivar Elo/MMR.
- No reintroducir Comunidad Hispana #03.
- No hacer `push`.

## Validation

Before completing the task ensure:

- `git status --short --untracked-files=all`
- `git diff --name-only`
- confirmar que solo se crean o modifican:
  - `docs/PERFORMANCE_PUBLIC_QUERY_AUDIT.md`
  - `ai/tasks/done/TASK-214-audit-public-query-performance-bottlenecks.md`
- no unrelated files were modified
- documentation remains consistent with the repository state

## Outcome

Archivos creados:

- `docs/PERFORMANCE_PUBLIC_QUERY_AUDIT.md`
- `ai/tasks/done/TASK-214-audit-public-query-performance-bottlenecks.md`

Resumen de hallazgos:

- `ranking.js` y `stats.js` bloquean carga principal detras de `/health`.
- `ranking.js` no protege request race ni estados de carga obsoletos.
- `/api/ranking` weekly/monthly conserva fallback runtime sobre tablas materializadas.
- search y profile de `stats` pueden caer a runtime si faltan read models dedicados.
- `historico.js` ya muestra un patron frontend mas sano: cache, deduplicacion y `requestId`.
- `/api/current-match` sigue consultando RCON directo en request publico.
- `partida-actual.js` hace polling agresivo a tres endpoints en paralelo.
- varias queries runtime filtran con `COALESCE(CAST(... AS TEXT))`, con riesgo de degradar indices.

Validacion ejecutada:

- lectura de contexto base: `AGENTS.md`, `ai/repo-context.md`, `ai/architecture-index.md`, `docs/decisions.md`
- lectura de endpoints y builders: `backend/app/routes.py`, `backend/app/payloads.py`
- lectura de modulos clave: `backend/app/rcon_annual_rankings.py`, `backend/app/rcon_historical_leaderboards.py`, `backend/app/rcon_historical_player_stats.py`, `backend/app/rcon_historical_read_model.py`, `backend/app/postgres_rcon_storage.py`, `backend/app/historical_runner.py`, `backend/app/main.py`, `backend/app/config.py`
- lectura de frontends clave: `frontend/assets/js/ranking.js`, `stats.js`, `historico.js`, `historico-partida.js`, `partida-actual.js`, `main.js`
- lectura de paginas clave: `frontend/ranking.html`, `stats.html`, `historico.html`, `partida-actual.html`
- lectura de tests relevantes: `backend/tests/test_annual_ranking_payload.py`, `test_rcon_materialization_pipeline.py`, `test_historical_snapshot_refresh.py`
- validacion de alcance con `git status --short --untracked-files=all` y `git diff --name-only`

Confirmaciones de exclusiones:

- no se toco codigo funcional de frontend ni backend
- no se tocaron tests
- no se tocaron endpoints ni contratos
- no se tocaron assets de armas, SVGs ni imagenes fisicas
- no se reactivo Elo/MMR
- no se reintrodujo Comunidad Hispana #03
- no se ejecuto `ai-platform run`
- no se hizo `push`

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
