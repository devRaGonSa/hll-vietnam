# Real KPM Player Active Seconds Design

## Resumen ejecutivo

KPM real debe significar `kills / minutos_jugados_reales`. HLL Vietnam no puede calcularlo de forma publica y fiable hoy porque ningun read model materializa tiempo activo real por jugador y partida. Lo que existe actualmente permite dos lecturas parciales:

- Presencia observada por eventos AdminLog dentro de una partida: `rcon_match_player_stats.first_seen_server_time` y `last_seen_server_time`.
- Duracion de partida: `rcon_materialized_matches.started_server_time`, `ended_server_time`, `started_at`, `ended_at`.

La primera puede servir como base `observed` si se etiqueta claramente. La segunda no debe usarse como KPM real por jugador salvo como calidad `estimated`, y no deberia publicarse como KPM competitivo sin decision explicita futura.

Recomendacion: crear `rcon_match_player_presence` como tabla de detalle por jugador y partida, y derivar `player_active_seconds` hacia `rcon_match_player_stats` y read models publicos. Este enfoque conserva trazabilidad, permite backfill por calidad y evita mezclar datos exactos, observados y estimados.

## Definicion de KPM real

Formula:

```text
KPM = kills / (player_active_seconds / 60)
```

Reglas:

- El numerador debe ser kills agregadas del mismo scope que el tiempo.
- El denominador debe ser minutos reales jugados por el jugador, no minutos de partida.
- KPM debe calcularse en generacion de read models/snapshots, nunca en frontend salvo formateo.
- `kills_per_match` debe seguir llamandose `Kills/partida` o `KPP`; nunca KPM.

No es KPM:

- `kills / partidas`
- `kills_per_match`
- `kills / duracion completa de partida` si el jugador no estuvo toda la partida
- `kills / ventana observada` sin marcar calidad

## Estado actual

`TASK-216` confirmo que no existe hoy un campo fiable de tiempo jugado real por jugador materializado para ranking publico.

Campos existentes:

- `rcon_player_profile_snapshots.play_time`: texto de perfil, no normalizado, no por jugador/partida y no apto para ranking publico sin parser y reconciliacion.
- `rcon_match_player_stats.first_seen_server_time`: primer `server_time` observado para el jugador dentro de una partida materializada.
- `rcon_match_player_stats.last_seen_server_time`: ultimo `server_time` observado para el jugador dentro de una partida materializada.
- `rcon_materialized_matches.started_server_time` y `ended_server_time`: limites de partida, no presencia real por jugador.
- `rcon_materialized_matches.started_at` y `ended_at`: timestamps de partida, no presencia real por jugador.

`TASK-217` dejo `kills_per_match` como `Kills/partida` y no implemento KPM real.

## Por que no sirve kills_per_match

`kills_per_match` responde a otra pregunta: rendimiento medio por partida contabilizada.

Ejemplo:

```text
1222 kills / 32 partidas = 38.19 kills/partida
```

Eso no dice si el jugador estuvo 20 minutos, 45 minutos o 90 minutos por partida. Mostrar ese valor como KPM exagera o distorsiona la metrica porque el denominador no es tiempo real jugado.

## Fuentes de datos disponibles

### AdminLog raw

Tabla:

- `rcon_admin_log_events`

Campos relevantes:

- `target_key`
- `external_server_id`
- `event_timestamp`
- `server_time`
- `event_type`
- `parsed_payload_json`
- `raw_message`

Eventos parseados:

- `connected`
- `disconnected`
- `kill`
- `team_switch`
- `chat`
- `message`
- `match_start`
- `match_end`

Calidad:

- `connected` + `disconnected` dentro de limites de match pueden dar calidad `exact` si ambos eventos existen y se pueden emparejar de forma consistente.
- `kill`, `team_switch`, `chat` y `message` dan presencia `observed`, no presencia continua exacta.
- `server_time` es la unidad operativa mas util para duraciones intra-partida.

### rcon_match_player_stats

Tabla:

- `rcon_match_player_stats`

Campos relevantes:

- `target_key`
- `match_key`
- `player_id`
- `player_name`
- `kills`
- `deaths`
- `teamkills`
- `first_seen_server_time`
- `last_seen_server_time`

Calidad:

- Ya agrupa por jugador y partida.
- Sus `first_seen_server_time` y `last_seen_server_time` son presencia observada por eventos, no tiempo activo real garantizado.
- Es buen destino de agregado, pero no conserva suficiente detalle para auditar intervalos de conexion/desconexion.

### rcon_materialized_matches

Tabla:

- `rcon_materialized_matches`

Campos relevantes:

- `target_key`
- `external_server_id`
- `match_key`
- `started_server_time`
- `ended_server_time`
- `started_at`
- `ended_at`
- `source_basis`

Calidad:

- Define limites de partida.
- No debe usarse como tiempo por jugador sin presencia individual.
- Puede acotar intervalos de presencia para evitar duraciones negativas o fuera de partida.

### rcon_player_profile_snapshots

Tabla:

- `rcon_player_profile_snapshots`

Campos relevantes:

- `player_id`
- `source_server_time`
- `first_seen`
- `sessions`
- `matches_played`
- `play_time`

Calidad:

- `play_time` es texto de perfil y puede ser acumulado global del servidor.
- No esta normalizado por partida.
- No puede distribuirse con precision por weekly/monthly/annual.
- Puede servir como comparacion diagnostica, no como fuente primaria para KPM publico.

### player_period_stats y snapshots

Tablas:

- `player_period_stats`
- `ranking_snapshot_items`
- `rcon_annual_ranking_snapshot_items`

Estado:

- Tienen kills, deaths, teamkills, matches, K/D y Kills/partida.
- No tienen `player_active_seconds`, `playtime_quality` ni `kills_per_minute`.

## Evaluacion de calidad de datos

| Fuente | Calidad | Uso recomendado |
|---|---|---|
| `connected` + `disconnected` emparejados dentro de match | `exact` | Calcular intervalos reales acotados por partida |
| `connected` sin `disconnected` pero con match end | `observed` o `estimated` segun politica | Acotar hasta `ended_server_time`, no publicar como exacto |
| `disconnected` sin `connected` pero con match start | `observed` | Acotar desde primer evento observado o match start solo si se etiqueta |
| `kill`, `team_switch`, `chat`, `message` | `observed` | Inferir ventana `first_seen`/`last_seen` |
| Duracion completa de partida | `estimated` | Solo diagnostico o fallback no publico |
| Sin eventos suficientes | `unknown` | No calcular KPM |
| `rcon_player_profile_snapshots.play_time` | `unknown` para KPM por periodo | No usar como fuente primaria |

Valores recomendados para `playtime_quality`:

- `exact`: intervalos conectados/desconectados suficientemente cerrados y acotados por partida.
- `observed`: ventana inferida por eventos del jugador dentro de la partida.
- `estimated`: duracion completa o parcial inferida sin evidencia individual suficiente.
- `unknown`: no hay base util.

Regla publica recomendada:

- Publicar KPM solo con `exact` u `observed`.
- No publicar KPM para `estimated` o `unknown` salvo decision explicita futura y etiqueta visible.

## Modelo de datos propuesto

### Opcion A: anadir player_active_seconds a rcon_match_player_stats

Columnas nuevas:

- `player_active_seconds INTEGER`
- `playtime_quality TEXT NOT NULL DEFAULT 'unknown'`
- `playtime_source TEXT`
- `playtime_first_server_time BIGINT`
- `playtime_last_server_time BIGINT`
- `playtime_interval_count INTEGER NOT NULL DEFAULT 0`

Clave existente:

- `UNIQUE(target_key, match_key, player_id)`

Indices recomendados:

- `idx_rcon_match_player_stats_playtime_quality` sobre `(playtime_quality)`
- `idx_rcon_match_player_stats_player_playtime` sobre `(player_id, target_key, match_key, player_active_seconds)`

Como se rellena:

- Durante `materialize_rcon_admin_log`, despues de derivar stats por jugador.
- Se calcula a partir de eventos en la ventana del match.
- Si solo hay `first_seen_server_time` y `last_seen_server_time`, usar `observed`.

Ventajas:

- Menor cambio para read models existentes.
- Agregaciones weekly/monthly/annual simples.

Riesgos:

- Pierde detalle de intervalos exactos.
- Mezcla metrica agregada con evidencia.
- Es mas dificil auditar reconexiones multiples.

### Opcion B: crear rcon_match_player_presence

Tabla nueva propuesta:

```sql
CREATE TABLE rcon_match_player_presence (
    id BIGSERIAL PRIMARY KEY,
    target_key TEXT NOT NULL,
    external_server_id TEXT,
    match_key TEXT NOT NULL,
    player_id TEXT NOT NULL,
    player_name TEXT NOT NULL,
    first_seen_server_time BIGINT,
    last_seen_server_time BIGINT,
    active_seconds INTEGER NOT NULL DEFAULT 0,
    playtime_quality TEXT NOT NULL DEFAULT 'unknown',
    interval_count INTEGER NOT NULL DEFAULT 0,
    evidence_event_count INTEGER NOT NULL DEFAULT 0,
    evidence_event_types TEXT NOT NULL DEFAULT '[]',
    source_basis TEXT NOT NULL DEFAULT 'rcon-admin-log',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(target_key, match_key, player_id)
);
```

Indices recomendados:

- `(target_key, match_key)`
- `(player_id, target_key, match_key)`
- `(playtime_quality, active_seconds)`
- `(external_server_id, match_key)`

Como se rellena:

- Leer `rcon_admin_log_events` acotados por `rcon_materialized_matches.started_server_time` y `ended_server_time`.
- Construir intervalos por jugador:
  - abrir intervalo en `connected`
  - cerrar intervalo en `disconnected`
  - acotar cada intervalo por match start/end
  - sumar intervalos no solapados
- Si no hay intervalos completos, usar ventana de eventos observados:
  - `first_seen_server_time = MIN(server_time)` de eventos del jugador
  - `last_seen_server_time = MAX(server_time)` de eventos del jugador
  - `active_seconds = max(0, last_seen - first_seen)`
  - `playtime_quality = observed`
- Si solo existe una observacion puntual, `active_seconds = 0` o minimo configurable, calidad `observed-low-confidence`.
  Para mantener enum simple, guardar `observed` y exponer `evidence_event_count`.
- No usar duracion completa de partida salvo como `estimated`.

Ventajas:

- Auditable.
- Permite recalculo/backfill independiente.
- No contamina stats base hasta tener calidad suficiente.

Riesgos:

- Requiere nueva tabla, backfill y runner.
- La exactitud depende de cobertura real de eventos `connected`/`disconnected`.

### Opcion C: ambas

Recomendacion final:

- Crear `rcon_match_player_presence` como fuente de verdad de presencia por jugador/partida.
- Denormalizar hacia `rcon_match_player_stats.player_active_seconds` y `playtime_quality` para agregaciones rapidas.

Por que:

- La tabla de detalle permite auditoria y recalculo.
- El campo denormalizado evita joins costosos en generacion de snapshots.
- La ruta publica sigue leyendo snapshots/read models, no calculando KPM en request.

## Estrategia de calculo

### Intervalos exactos

Entrada:

- Eventos `connected` y `disconnected` con `player_id`, `server_time`.
- Limites de match `started_server_time`, `ended_server_time`.

Algoritmo:

1. Ordenar eventos por `server_time`, `id`.
2. Por jugador, abrir intervalo en `connected`.
3. Cerrar intervalo en `disconnected`.
4. Acotar inicio/fin al rango de la partida.
5. Fusionar intervalos solapados.
6. Sumar segundos.
7. Marcar `playtime_quality = exact` solo si la evidencia permite explicar inicio y fin.

### Ventana observada

Entrada:

- Eventos `kill`, `team_switch`, `chat`, `message`, `connected`, `disconnected`.

Algoritmo:

1. Tomar min/max `server_time` por jugador dentro del match.
2. Calcular `active_seconds = max(0, last_seen - first_seen)`.
3. Guardar `evidence_event_count` y tipos.
4. Marcar `playtime_quality = observed`.

### Estimacion por duracion de partida

Entrada:

- `started_server_time`, `ended_server_time`.

Politica:

- No usar para KPM publico por defecto.
- Si se guarda, marcar `playtime_quality = estimated`.
- Requiere flag futuro para mostrarse.

## Estrategia de backfill

Fase 1:

- Crear tabla `rcon_match_player_presence`.
- Backfill desde `rcon_admin_log_events` y `rcon_materialized_matches`.
- No cambiar API publica.

Fase 2:

- Denormalizar `player_active_seconds` y `playtime_quality` en `rcon_match_player_stats`.
- Backfill stats desde presence.

Fase 3:

- Extender `player_period_stats` con:
  - `player_active_seconds`
  - `playtime_quality`
  - `kills_per_minute`
- Regenerar weekly/monthly/yearly period stats.

Fase 4:

- Extender `ranking_snapshot_items` y `rcon_annual_ranking_snapshot_items` con:
  - `player_active_seconds`
  - `playtime_quality`
  - `kills_per_minute`
- Generar snapshots KPM solo para filas con calidad permitida.

Reglas de backfill:

- Si hay intervalos exactos, usar `exact`.
- Si solo hay `first_seen`/`last_seen` por eventos, usar `observed`.
- Si solo hay duracion completa de partida, usar `estimated` y excluir de KPM publico.
- Si no hay evidencia, usar `unknown` y excluir de KPM.
- No mezclar `exact` y `observed` sin conservar calidad agregada.

Calidad agregada por periodo:

- `exact` si todos los segundos agregados vienen de exact.
- `observed` si hay mezcla exact + observed o solo observed.
- `estimated` si incluye estimated.
- `unknown` si no hay segundos validos.

## Cambios necesarios en read models

### rcon_match_player_stats

Campos recomendados:

- `player_active_seconds INTEGER`
- `playtime_quality TEXT`
- `kills_per_minute REAL`

Nota: `kills_per_minute` puede no guardarse en stats base si se prefiere derivarlo en read models. Si se guarda, debe recalcularse cada vez que cambien kills o segundos.

### player_period_stats

Campos recomendados:

- `player_active_seconds INTEGER NOT NULL DEFAULT 0`
- `playtime_quality TEXT NOT NULL DEFAULT 'unknown'`
- `kills_per_minute REAL`

Agregacion:

```text
SUM(kills) / (SUM(player_active_seconds) / 60)
```

Filtro publico:

- Incluir KPM solo si `SUM(player_active_seconds) > 0` y calidad agregada no es `estimated` ni `unknown`.

### ranking_snapshot_items

Campos recomendados:

- `player_active_seconds`
- `playtime_quality`
- `kills_per_minute`

Nueva metrica snapshot:

- `kills_per_minute`

Orden:

- `metric_value DESC`
- `player_active_seconds DESC`
- `kills DESC`
- `matches_considered DESC`
- `player_name ASC`

### rcon_annual_ranking_snapshot_items

Campos recomendados:

- `player_active_seconds`
- `playtime_quality`
- `kills_per_minute`

Regla:

- Annual KPM debe tener snapshot propio `metric = kills_per_minute`.
- No representar KPM anual con `kills_per_match`.

### Perfil de jugador

Exponer:

- `player_active_seconds`
- `player_active_minutes`
- `kills_per_minute`
- `playtime_quality`

Evitar:

- Calcular KPM runtime en request publico.
- Mezclar periodo semanal/mensual/anual sin metadata.

## Cambios necesarios en snapshots weekly/monthly/annual

Weekly/monthly:

- Extender generacion en `rcon_historical_leaderboards`.
- Agregar metrica `kills_per_minute` solo si existe `player_active_seconds`.
- Persistir `kills_per_minute` en `ranking_snapshot_items`.

Annual:

- Extender `rcon_annual_rankings` cuando exista presence/read model.
- Agregar `kills_per_minute` a metricas soportadas solo despues del backfill.
- Persistir snapshot independiente por anio, servidor y metrica.

General:

- Public read path debe seguir leyendo solo snapshots.
- Missing snapshot debe devolver `snapshot_status=missing`, sin fallback runtime.

## Cambios necesarios en API y frontend

API:

- Incluir `kills_per_minute` solo cuando venga de read model/snapshot.
- Incluir `playtime_quality`.
- Mantener `kills_per_match` como `Kills/partida`.
- Rechazar o marcar missing si se pide KPM sin snapshot real.

Frontend:

- Mostrar columna `KPM` solo si backend expone `kills_per_minute`.
- Mostrar tooltip o metadata de calidad si se decide publicar `observed`.
- No calcular KPM en JS.
- No mostrar KPM para `estimated` o `unknown`.

## Impacto en refresh runner

El runner actual refresca:

- RCON capture
- materializaciones
- player search index
- player period stats
- ranking snapshots

Orden futuro recomendado:

1. RCON capture/AdminLog ingestion.
2. Materializar matches y player stats.
3. Materializar `rcon_match_player_presence`.
4. Denormalizar `player_active_seconds` a `rcon_match_player_stats`.
5. Refrescar `player_search_index`.
6. Refrescar `player_period_stats`.
7. Refrescar ranking snapshots weekly/monthly.
8. Refrescar annual snapshots cuando aplique.

## Comandos futuros de produccion

Nombres propuestos; no existen todavia:

```bash
docker compose exec backend python -m app.rcon_player_presence migrate
docker compose exec backend python -m app.rcon_player_presence backfill --year 2026 --server-key all-servers
docker compose exec backend python -m app.rcon_player_presence backfill --year 2026 --server-key comunidad-hispana-01
docker compose exec backend python -m app.rcon_player_presence backfill --year 2026 --server-key comunidad-hispana-02
docker compose exec backend python -m app.rcon_historical_player_stats refresh-player-period-stats
docker compose exec backend python -m app.rcon_historical_leaderboards refresh-ranking-snapshots --limit 30
docker compose exec backend python -m app.rcon_annual_rankings generate --year 2026 --server-key all-servers --metric kills_per_minute --limit 30 --replace-existing
docker compose exec backend python -m app.rcon_annual_rankings generate --year 2026 --server-key comunidad-hispana-01 --metric kills_per_minute --limit 30 --replace-existing
docker compose exec backend python -m app.rcon_annual_rankings generate --year 2026 --server-key comunidad-hispana-02 --metric kills_per_minute --limit 30 --replace-existing
```

## Plan de implementacion por tasks

1. `TASK-219-create-rcon-match-player-presence-schema`
   Crear schema SQLite/Postgres para `rcon_match_player_presence`, sin cambiar API publica.

2. `TASK-220-materialize-player-presence-from-adminlog`
   Implementar materializacion exact/observed desde `rcon_admin_log_events` y `rcon_materialized_matches`.

3. `TASK-221-backfill-player-active-seconds`
   Backfill historico por servidor/anio y reporte de cobertura por calidad.

4. `TASK-222-denormalize-player-active-seconds-into-match-stats`
   Agregar `player_active_seconds` y `playtime_quality` a `rcon_match_player_stats`.

5. `TASK-223-extend-player-period-stats-with-kpm`
   Extender `player_period_stats` con segundos activos y KPM real.

6. `TASK-224-add-kpm-ranking-snapshots`
   Agregar `kills_per_minute` a weekly/monthly snapshots y annual snapshots independientes.

7. `TASK-225-expose-real-kpm-in-api-payloads`
   Exponer `kills_per_minute` y `playtime_quality` desde snapshots/read models, sin runtime publico.

8. `TASK-226-show-real-kpm-in-ranking-ui`
   Mostrar KPM solo cuando backend entregue `kills_per_minute`; mantener Kills/partida separado.

9. `TASK-227-validate-kpm-quality-and-performance`
   Medir cobertura, latencia, `fallback_used=false` y comparar contra muestras manuales.

## Riesgos principales

- Cobertura incompleta de `connected`/`disconnected`.
- `server_time` puede reiniciarse o tener discontinuidades entre partidas; siempre debe estar acotado por `match_key`.
- Jugadores con eventos escasos pueden tener `observed` subestimado.
- Usar duracion completa de partida como tiempo de jugador inflaria o distorsionaria KPM.
- Mezclar calidades sin metadata haria la metrica poco confiable.
- Backfill masivo puede competir con lecturas publicas si se ejecuta fuera de ventana controlada.
- El frontend podria volver a confundir `Kills/partida` con KPM si no se separan nombres y payloads.

## Criterios de aceptacion futuros

- Existe `player_active_seconds` por jugador/partida con `playtime_quality`.
- Cada fila puede explicar su fuente: exact, observed, estimated o unknown.
- KPM se calcula como `kills / (player_active_seconds / 60)`.
- No se calcula KPM en frontend.
- `kills_per_match` sigue separado como `Kills/partida`.
- Weekly/monthly/annual KPM tienen snapshots propios.
- Request publico de ranking no consulta `rcon_match_player_stats` para calcular KPM.
- `fallback_used=false` en rutas publicas normales.
- Si falta snapshot KPM, el endpoint devuelve missing sin fallback runtime.
- Tests cubren exact, observed, estimated/unknown excluded, division por cero y orden de ranking.
