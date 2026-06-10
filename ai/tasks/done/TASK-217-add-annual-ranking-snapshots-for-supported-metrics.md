---
id: TASK-217
title: Add annual ranking snapshots for supported metrics
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Frontend Senior
  - Arquitecto de Base de Datos
  - Arquitecto Python
roadmap_item: foundation
priority: high
---

# TASK-217 - Add annual ranking snapshots for supported metrics

## Goal

Permitir ranking anual para metricas adicionales usando un snapshot anual independiente por metrica, sin runtime publico pesado ni reutilizacion del snapshot top kills para otras metricas.

## Context

`TASK-211` dejo la lectura publica anual rapida y basada en `rcon_annual_ranking_snapshots` y `rcon_annual_ranking_snapshot_items`. `TASK-216` mantuvo annual limitado a `kills` porque no habia snapshot propio para otras metricas y corrigio el falso KPM: `kills_per_match` debe mostrarse como `Kills/partida`, no como kills por minuto.

Esta task amplia la generacion annual para metricas que ya se pueden calcular de forma segura desde los read models materializados durante un proceso interno/CLI. La lectura publica sigue leyendo solo snapshots anuales ya generados.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Revisar la lectura y generacion anual actual.
2. Confirmar que el esquema permite `metric_value` decimal para ratios.
3. Actualizar la normalizacion de metricas annual soportadas.
4. Generar snapshots independientes por metrica:
   - `kills`
   - `deaths`
   - `teamkills`
   - `matches_considered`
   - `kd_ratio`
   - `kills_per_match`
5. Mantener la lectura publica anual sobre tablas de snapshot, sin fallback runtime.
6. Actualizar frontend para permitir metricas annual soportadas y mostrar `kills_per_match` como `Kills/partida`.
7. Añadir tests de normalizacion, lectura publica y calculo/orden de `kd_ratio` y `kills_per_match`.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `backend/app/rcon_annual_rankings.py`
- `backend/app/payloads.py`
- `frontend/assets/js/ranking.js`

## Expected Files to Modify

- `backend/app/rcon_annual_rankings.py`
- `backend/app/rcon_admin_log_materialization.py`
- `backend/app/postgres_rcon_storage.py`
- `backend/tests/test_annual_ranking_payload.py`
- `frontend/ranking.html`
- `frontend/assets/js/ranking.js`
- `ai/tasks/done/TASK-217-add-annual-ranking-snapshots-for-supported-metrics.md`

## Constraints

- Keep the change minimal.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- No ejecutar `ai-platform run`.
- No hacer push.
- No tocar `frontend/assets/img/weapons/`.
- No tocar SVGs.
- No modificar imagenes fisicas.
- No tocar `ai/system-metrics.md`.
- No reactivar Elo/MMR.
- No reintroducir Comunidad Hispana #03.
- No implementar KPM real en esta task.
- No mostrar `kills_per_match` como KPM.
- No exponer metricas annual sin snapshot anual propio.
- No usar el snapshot top kills para representar otras metricas.
- La lectura publica annual debe leer solo `rcon_annual_ranking_snapshots` y `rcon_annual_ranking_snapshot_items`.

## Validation

Before completing the task ensure:

- `node --check frontend/assets/js/ranking.js`
- `python -m compileall backend\app\rcon_annual_rankings.py backend\app\payloads.py backend\tests\test_annual_ranking_payload.py`
- `python -m unittest backend.tests.test_annual_ranking_payload`
- Medicion directa de `build_global_ranking_payload` annual para metricas soportadas si el entorno local tiene datos.
- `git diff --name-only` matches the expected scope.
- No unrelated files were modified.

## Outcome

Archivos modificados por esta task:

- `backend/app/rcon_annual_rankings.py`
- `backend/app/rcon_admin_log_materialization.py`
- `backend/app/postgres_rcon_storage.py`
- `backend/tests/test_annual_ranking_payload.py`
- `frontend/ranking.html`
- `frontend/assets/js/ranking.js`
- `ai/tasks/done/TASK-217-add-annual-ranking-snapshots-for-supported-metrics.md`

Metricas anuales soportadas:

- `kills`
- `deaths`
- `teamkills`
- `matches_considered`
- `kd_ratio`
- `kills_per_match`

Cambios de backend:

- `_normalize_metric()` acepta solo las seis metricas anuales soportadas.
- La generacion anual calcula y ordena snapshots independientes por metrica real.
- `kd_ratio` se calcula como `kills / deaths` sobre agregados.
- `kills_per_match` se calcula como `kills / matches_considered` y sigue siendo `Kills/partida`, no KPM.
- La lectura publica anual no cambia de modelo: sigue usando `rcon_annual_ranking_snapshots` y `rcon_annual_ranking_snapshot_items`.
- No se introdujo fallback runtime ni lectura publica sobre `rcon_match_player_stats`.
- Se agregaron tests de normalizacion, rechazo de metrica no soportada, lectura publica sin inicializar storage y orden/calculo para `kd_ratio` y `kills_per_match`.

Cambios de esquema:

- Si hubo cambios de esquema.
- `rcon_annual_ranking_snapshots.metric` ahora permite:
  - `kills`
  - `deaths`
  - `teamkills`
  - `matches_considered`
  - `kd_ratio`
  - `kills_per_match`
- `rcon_annual_ranking_snapshot_items.metric_value` pasa de entero a valor decimal:
  - SQLite: `REAL`
  - PostgreSQL: `DOUBLE PRECISION`
- La inicializacion PostgreSQL incluye una migracion idempotente para ajustar `metric_value` y reemplazar el `CHECK` antiguo.

Cambios de frontend:

- Annual permite seleccionar las metricas soportadas.
- No se muestra KPM.
- `kills_per_match` se muestra como `Kills/partida`.
- Se renombraron identificadores internos heredados de KPM a KPP.
- Annual mantiene `2026` interno y no muestra input de año.
- Si falta un snapshot anual, la UI muestra `Snapshot anual no disponible para esta metrica.` sin fallback ni bloqueo.

Comandos de produccion para generar snapshots anuales 2026:

```bash
for server in all-servers comunidad-hispana-01 comunidad-hispana-02; do
  for metric in kills deaths teamkills matches_considered kd_ratio kills_per_match; do
    docker compose exec backend python -m app.rcon_annual_rankings generate \
      --year 2026 \
      --server-key "$server" \
      --metric "$metric" \
      --limit 30 \
      --replace-existing
  done
done
```

Validaciones ejecutadas:

- `node --check frontend/assets/js/ranking.js`
- `$env:PYTHONPATH='backend'; python -m compileall backend\app\rcon_annual_rankings.py backend\app\payloads.py backend\tests\test_annual_ranking_payload.py backend\app\postgres_rcon_storage.py backend\app\rcon_admin_log_materialization.py`
- `$env:PYTHONPATH='backend'; python -m unittest backend.tests.test_annual_ranking_payload`
- Busqueda en `frontend/ranking.html` y `frontend/assets/js/ranking.js` para confirmar que no aparecen `KPM`, `Actualizar ranking`, `ranking-year`, `El ranking expone`, `Kills listo`, `listo en` ni `annualMetric`.
- Medicion directa con `build_global_ranking_payload(timeframe="annual", year=2026)` para las seis metricas soportadas.

Tiempos obtenidos en lectura directa local:

- `kills`: `1.66 ms`, `snapshot_status=ready`, `read_model=rcon-annual-ranking-snapshot`, `fallback_used=False`, `items=20`.
- `deaths`: `1.17 ms`, `snapshot_status=missing`, `read_model=rcon-annual-ranking-snapshot`, `fallback_used=False`, `items=0`.
- `teamkills`: `1.10 ms`, `snapshot_status=missing`, `read_model=rcon-annual-ranking-snapshot`, `fallback_used=False`, `items=0`.
- `matches_considered`: `1.09 ms`, `snapshot_status=missing`, `read_model=rcon-annual-ranking-snapshot`, `fallback_used=False`, `items=0`.
- `kd_ratio`: `1.11 ms`, `snapshot_status=missing`, `read_model=rcon-annual-ranking-snapshot`, `fallback_used=False`, `items=0`.
- `kills_per_match`: `1.10 ms`, `snapshot_status=missing`, `read_model=rcon-annual-ranking-snapshot`, `fallback_used=False`, `items=0`.

Confirmacion de exclusiones:

- No se ejecuto `ai-platform run`.
- No se hizo push.
- No se hizo commit.
- No se tocaron assets de armas.
- No se tocaron SVGs.
- No se modificaron imagenes fisicas.
- No se toco `ai/system-metrics.md`.
- No se reactivo Elo/MMR.
- No se reintrodujo Comunidad Hispana #03.
- No se incluyeron cambios previos no relacionados.

## Change Budget

- Archivos modificados por la task: 7.
- El cambio supera el objetivo preferente de 5 archivos porque incluye schema SQLite/PostgreSQL, generador, test, frontend y documentacion de task.
- No se implemento KPM real; queda fuera de alcance hasta materializar tiempo jugado real por jugador.
