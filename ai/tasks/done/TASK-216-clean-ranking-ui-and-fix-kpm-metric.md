---
id: TASK-216
title: Clean ranking UI and fix KPM metric
status: done
type: frontend
team: Frontend Senior
supporting_teams:
  - Backend Senior
  - Arquitecto Python
  - Experto en interfaz
roadmap_item: foundation
priority: high
---

# TASK-216 - Clean ranking UI and fix KPM metric

## Goal

Limpiar la UX de `frontend/ranking.html`, eliminar estados y controles redundantes, corregir el uso conceptual de KPM y ampliar el ranking anual solo para metricas soportadas por snapshots/read models seguros sin introducir lecturas runtime pesadas en requests publicos.

## Context

Despues de `TASK-213`, la vista de ranking ya carga rapido y concentra filtros + tabla dentro de una sola card. Sin embargo, la revision visual detecto varios residuos de UX y un problema funcional serio: la interfaz seguia mostrando mensajes redundantes, mantenia un boton `Actualizar ranking` innecesario y exponia `KPM` usando un valor que correspondia a `kills_per_match`.

En paralelo, `TASK-211` dejo la lectura publica annual optimizada para snapshots anuales, pero `backend/app/rcon_annual_rankings.py` sigue restringiendo annual a `kills`. Esta task revisa ese limite sin introducir lecturas publicas runtime sobre `rcon_match_player_stats`.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Leer primero los archivos listados y confirmar el estado actual de UI, payloads y snapshots de ranking.
2. Auditar si existe tiempo jugado real por jugador antes de tocar la UI.
3. Limpiar la UI de `ranking.html` y `ranking.js`:
   - eliminar del DOM visible el texto `El ranking expone los resultados de los lideres. Para busqueda individual usa Estadisticas.`
   - eliminar el estado informativo tipo `Kills listo en semanal para Todos los servidores.`
   - mantener solo estados utiles de loading, error y metadatos compactos
   - quitar el boton `Actualizar ranking`
   - cargar automaticamente al entrar y al cambiar periodo, servidor, metrica o limite
   - mover `Buscar jugador en Estadisticas` por encima de los filtros dentro de la misma card
4. Ajustar el modo annual en frontend:
   - no mostrar input de ano
   - usar `2026` internamente en JS
   - no mostrar mensaje de limitacion anual a kills
5. No exponer metricas annual que no tengan snapshots propios y seguros.
6. Documentar la decision final sobre KPM y el diseno futuro de `player_active_seconds`.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `frontend/ranking.html`
- `frontend/assets/js/ranking.js`
- `backend/app/rcon_annual_rankings.py`

Tambien se revisaron:

- `frontend/assets/css/styles.css`
- `backend/app/payloads.py`
- `backend/app/postgres_rcon_storage.py`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/rcon_historical_player_stats.py`
- `backend/app/rcon_admin_log_storage.py`
- `backend/app/rcon_admin_log_materialization.py`
- `backend/app/historical_runner.py`
- `ai/tasks/done/TASK-211-optimize-annual-ranking-read-path.md`
- `ai/tasks/done/TASK-213-fix-ranking-layout-and-loading-state.md`
- `ai/tasks/done/TASK-215-optimize-weekly-monthly-ranking-read-path.md`
- `docs/PERFORMANCE_PUBLIC_QUERY_AUDIT.md`

## Expected Files to Modify

- `frontend/ranking.html`
- `frontend/assets/js/ranking.js`
- `frontend/assets/css/styles.css`
- `ai/tasks/done/TASK-216-clean-ranking-ui-and-fix-kpm-metric.md`

## Constraints

- Keep the change minimal.
- Preserve HLL Vietnam project identity.
- Do not introduce unnecessary frameworks or dependencies.
- Do not overwrite repository-specific context with generic platform template text.
- No ejecutar `ai-platform run`.
- No tocar `frontend/assets/img/weapons/`.
- No tocar SVGs.
- No modificar imagenes fisicas.
- No tocar `ai/system-metrics.md`.
- No reactivar Elo/MMR.
- No reintroducir Comunidad Hispana #03.
- No hacer `push`.
- No hacer `commit` en esta task.
- No introducir runtime pesado ni fallback publico sobre `rcon_match_player_stats`.
- La lectura publica annual debe seguir leyendo unicamente:
  - `rcon_annual_ranking_snapshots`
  - `rcon_annual_ranking_snapshot_items`
- Weekly/monthly/annual deben seguir priorizando read models/snapshots con `fallback_used = false` en la ruta publica normal.
- No aceptar que `kills_per_match` se muestre como `KPM`.
- Si no existe tiempo jugado fiable materializado, no inventar `KPM`.
- Mantener compatibilidad con apertura directa en navegador cuando aplique.

## Validation

Before completing the task ensure:

- `node --check frontend/assets/js/ranking.js`
- validar endpoints:
  - `/api/ranking?timeframe=weekly&metric=kills&limit=20`
  - `/api/ranking?timeframe=monthly&metric=kills&limit=20`
  - `/api/ranking?timeframe=annual&metric=kills&limit=20&year=2026`
- por inspeccion visual o revision DOM:
  - no aparece boton `Actualizar ranking`
  - `Buscar jugador en Estadisticas` queda encima de filtros y dentro de la misma card
  - no aparecen los textos redundantes eliminados
  - annual no muestra input de ano
  - annual no muestra mensaje de limitacion a kills
  - la columna `KPM` no aparece si no existe KPM real
  - si no hay minutos reales, aparece `Kills/partida`
- `git diff --name-only` matches the expected scope
- no unrelated files were modified

## Outcome

Archivos modificados por esta task:

- `frontend/ranking.html`
- `frontend/assets/js/ranking.js`
- `frontend/assets/css/styles.css`
- `ai/tasks/done/TASK-216-clean-ranking-ui-and-fix-kpm-metric.md`

Resultado de auditoria KPM:

- No existe hoy un campo materializado y fiable de tiempo jugado real por jugador listo para el ranking publico.
- Se encontro `rcon_player_profile_snapshots.play_time`, pero es texto procedente de snapshots de perfil, no un campo numerico normalizado por jugador/partida ni agregado en los read models publicos de ranking.
- Se encontraron `rcon_match_player_stats.first_seen_server_time` y `rcon_match_player_stats.last_seen_server_time`, pero representan presencia observada por eventos dentro de una partida, no minutos reales jugados materializados como contrato estable de ranking.
- Se encontraron `rcon_materialized_matches.started_at`, `ended_at`, `started_server_time` y `ended_server_time`, pero son duracion de partida o ventana de partida, no tiempo real por jugador.
- Las tablas `ranking_snapshot_items`, `rcon_annual_ranking_snapshot_items` y `player_period_stats` no tienen `player_active_seconds`, `minutes_played`, `seconds_played` ni equivalente fiable.

Decision final sobre KPM:

- No se implemento KPM real.
- Se elimino el uso visible de `KPM` en `ranking.html` y `ranking.js`.
- `kills_per_match` se conserva solo bajo el nombre `Kills/partida`.
- No se reutilizo `kills_per_match` como kills por minuto.

Propuesta para KPM real futuro:

- Crear `player_active_seconds` como campo numerico base por jugador y partida.
- Ubicacion preferida: `rcon_match_player_stats`, si se acepta extender la tabla materializada principal.
- Alternativa: nueva tabla derivada `rcon_match_player_presence` con `target_key`, `match_key`, `player_id`, `first_seen_server_time`, `last_seen_server_time`, `active_seconds`, `quality`.
- Relleno exacto: eventos `connected` y `disconnected` dentro de limites `match_start`/`match_end`.
- Relleno razonable: presencia observada por eventos `kill`, `team_switch`, `chat`, `message`, acotada por `first_seen_server_time` y `last_seen_server_time`.
- Relleno estimado: duracion completa de partida solo como calidad `estimated`, no apta para publicar como KPM real sin etiqueta.
- Criterios de calidad propuestos:
  - `exact`: join/leave real dentro de partida.
  - `observed`: presencia inferida por eventos del jugador.
  - `estimated`: duracion completa de partida.
  - `unknown`: no calcular.
- Read models a extender cuando exista el campo:
  - `player_period_stats`
  - `ranking_snapshot_items`
  - `rcon_annual_ranking_snapshot_items`
- Task futura recomendada: `TASK-XXX-materialize-player-active-seconds-for-real-kpm`.

Decision sobre metricas annual:

- No se ampliaron metricas annual en esta task.
- Annual sigue exponiendo solo `kills` porque es la unica metrica con snapshot anual seguro ya soportado por `rcon_annual_rankings.py`.
- No se usa snapshot top kills para representar `deaths`, `teamkills`, `matches_considered`, `kd_ratio` ni `kills_per_match`.
- No se introdujo runtime publico pesado ni fallback sobre `rcon_match_player_stats`.

Cambios de UI aplicados:

- Se elimino el texto redundante de introduccion dentro de la card.
- Se elimino el boton `Actualizar ranking`.
- La tabla sigue cargando automaticamente al entrar y al cambiar periodo, servidor, metrica o limite.
- `Buscar jugador en Estadisticas` queda encima de los filtros dentro de la misma card.
- En annual no hay input visible de ano.
- `ranking.js` usa `2026` internamente para annual.
- Se elimino el mensaje visible de annual limitado a kills.
- Se elimino el estado de exito tipo `Kills listo en semanal para Todos los servidores.`
- La metrica `kills_per_match` se muestra como `Kills/partida`.

Comandos de produccion:

- No hace falta regenerar snapshots para este cambio de UI.
- Si falta el snapshot anual existente de kills para 2026, regenerarlo con:

```bash
docker compose exec backend python -m app.rcon_annual_rankings generate --year 2026 --server-key all-servers --metric kills --limit 30 --replace-existing
```

- No ejecutar comandos de metricas annual adicionales hasta que existan snapshots propios por metrica.

Validaciones ejecutadas:

- `node --check frontend/assets/js/ranking.js`
- Revision por busqueda de que `frontend/ranking.html` y `frontend/assets/js/ranking.js` ya no contienen `KPM`, `Actualizar ranking`, `ranking-year`, `ranking-submit`, `ranking-filter-note`, `El ranking expone` ni `listo en`.
- Intento de validacion HTTP local contra:
  - `/api/ranking?timeframe=weekly&metric=kills&limit=20`
  - `/api/ranking?timeframe=monthly&metric=kills&limit=20`
  - `/api/ranking?timeframe=annual&metric=kills&limit=20&year=2026`
- El backend local no estaba disponible en `http://127.0.0.1:8000`; las tres peticiones fallaron con `No es posible conectar con el servidor remoto`.
- Revision de alcance con `git status --short` y `git diff --name-only`.

Validaciones no ejecutadas:

- No se ejecuto `compileall` ni `unittest` porque no se tocaron archivos backend.

Tiempos obtenidos:

- No se obtuvieron tiempos nuevos de endpoint porque el backend local no estaba escuchando.
- Intentos HTTP fallidos por conexion:
  - weekly kills top 20: `2156.7 ms`
  - monthly kills top 20: `2033.7 ms`
  - annual kills top 20 2026: `2046.1 ms`
- Referencia previa de `TASK-213`: annual kills 2026 ~39 ms, weekly/monthly kills < 130 ms.

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

- Archivos de producto modificados: 3.
- Sin cambios backend.
- El alcance se mantuvo dentro de la limpieza UI y documentacion de task.
