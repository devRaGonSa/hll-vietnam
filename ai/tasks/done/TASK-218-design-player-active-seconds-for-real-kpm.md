---
id: TASK-218
title: Design player active seconds for real KPM
status: done
type: documentation
team: Arquitecto de Base de Datos
supporting_teams:
  - Backend Senior
  - Arquitecto Python
roadmap_item: foundation
priority: high
---

# TASK-218 - Design player active seconds for real KPM

## Goal

Analizar y disenar como calcular KPM real en HLL Vietnam sin implementar cambios funcionales todavia.

KPM real se define como:

```text
kills / minutos_jugados_reales
```

No debe confundirse con `kills_per_match`, `Kills/partida` ni kills divididas por duracion completa de partida cuando el jugador no estuvo toda la partida.

## Context

`TASK-216` confirmo que hoy no existe tiempo jugado real por jugador materializado para ranking publico.

Campos encontrados:

- `rcon_player_profile_snapshots.play_time`: texto de perfil, no normalizado y no por jugador/partida.
- `rcon_match_player_stats.first_seen_server_time` y `last_seen_server_time`: presencia observada por eventos dentro de partida.
- `rcon_materialized_matches.started_at`, `ended_at`, `started_server_time` y `ended_server_time`: duracion de partida, no tiempo por jugador.

`TASK-217` dejo `kills_per_match` como `Kills/partida` y no implemento KPM real.

Esta task produce un diseno tecnico accionable para crear `player_active_seconds` o `rcon_match_player_presence` en tasks futuras, sin modificar codigo funcional ni esquema real.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Revisar fuentes de AdminLog, materializacion, read models y snapshots.
2. Evaluar eventos disponibles para presencia real o observada.
3. Clasificar calidad de datos: `exact`, `observed`, `estimated`, `unknown`.
4. Proponer opciones de modelo de datos.
5. Recomendar una estrategia de backfill y propagacion a read models.
6. Documentar plan de implementacion dividido en tasks.
7. Validar que solo se crearon documentos.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `backend/app/rcon_admin_log_storage.py`
- `backend/app/rcon_admin_log_materialization.py`
- `backend/app/rcon_admin_log_parser.py`

Tambien se revisaron:

- `backend/app/postgres_rcon_storage.py`
- `backend/app/rcon_historical_player_stats.py`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/rcon_annual_rankings.py`
- `backend/app/historical_runner.py`
- `backend/app/payloads.py`
- `docs/PERFORMANCE_PUBLIC_QUERY_AUDIT.md`
- `ai/tasks/done/TASK-216-clean-ranking-ui-and-fix-kpm-metric.md`
- `ai/tasks/done/TASK-217-add-annual-ranking-snapshots-for-supported-metrics.md`

## Expected Files to Modify

- `docs/REAL_KPM_PLAYER_ACTIVE_SECONDS_DESIGN.md`
- `ai/tasks/done/TASK-218-design-player-active-seconds-for-real-kpm.md`

## Constraints

- Keep the change minimal.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- Do not implement backend functionality.
- Do not change endpoints.
- Do not change frontend.
- Do not change backend functional code.
- Do not change real schema yet.
- No ejecutar `ai-platform run`.
- No hacer push.
- No tocar `frontend/assets/img/weapons/`.
- No tocar SVGs.
- No modificar imagenes fisicas.
- No tocar `ai/system-metrics.md`.
- No reactivar Elo/MMR.
- No reintroducir Comunidad Hispana #03.
- No incluir cambios previos no relacionados.

## Validation

Before completing the task ensure:

- `git status --short --untracked-files=all`
- `git diff --name-only`
- Confirmar que solo se crean/modifican:
  - `docs/REAL_KPM_PLAYER_ACTIVE_SECONDS_DESIGN.md`
  - `ai/tasks/done/TASK-218-design-player-active-seconds-for-real-kpm.md`

## Outcome

Archivos creados:

- `docs/REAL_KPM_PLAYER_ACTIVE_SECONDS_DESIGN.md`
- `ai/tasks/done/TASK-218-design-player-active-seconds-for-real-kpm.md`

Conclusion:

- No se puede calcular KPM real publico hoy.
- La fuente recomendada para `player_active_seconds` es AdminLog con `connected`/`disconnected` cuando sea posible y ventana observada por eventos como fallback etiquetado.
- El modelo recomendado es Opcion C:
  - crear `rcon_match_player_presence` como detalle auditable por jugador/partida;
  - denormalizar `player_active_seconds` y `playtime_quality` en `rcon_match_player_stats` para agregaciones rapidas.
- KPM futuro debe calcularse en generacion de read models/snapshots como `kills / (player_active_seconds / 60)`, nunca en frontend y nunca usando `kills_per_match`.

Plan de implementacion propuesto:

1. `TASK-219-create-rcon-match-player-presence-schema`
2. `TASK-220-materialize-player-presence-from-adminlog`
3. `TASK-221-backfill-player-active-seconds`
4. `TASK-222-denormalize-player-active-seconds-into-match-stats`
5. `TASK-223-extend-player-period-stats-with-kpm`
6. `TASK-224-add-kpm-ranking-snapshots`
7. `TASK-225-expose-real-kpm-in-api-payloads`
8. `TASK-226-show-real-kpm-in-ranking-ui`
9. `TASK-227-validate-kpm-quality-and-performance`

Riesgos principales:

- Cobertura incompleta de eventos `connected`/`disconnected`.
- Presencia observada por eventos puede subestimar tiempo activo.
- Duracion completa de partida no representa tiempo por jugador y debe quedar `estimated`.
- Mezclar calidades sin metadata haria KPM enganoso.
- Backfill masivo puede competir con lecturas publicas si no se agenda bien.

Validacion ejecutada:

- `git status --short --untracked-files=all`
- `git diff --name-only`

Confirmacion de exclusiones:

- No se ejecuto `ai-platform run`.
- No se hizo push.
- No se tocaron assets de armas.
- No se tocaron SVGs.
- No se modificaron imagenes fisicas.
- No se toco `ai/system-metrics.md`.
- No se reactivo Elo/MMR.
- No se reintrodujo Comunidad Hispana #03.
- No se modifico frontend.
- No se modifico backend funcional.
- No se modificaron tests.
- No se modifico esquema real.
- No se incluyeron cambios previos no relacionados.

## Change Budget

- Archivos modificados por esta task: 2.
- Sin cambios funcionales.
