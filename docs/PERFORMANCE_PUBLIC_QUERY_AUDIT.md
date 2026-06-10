# Performance Public Query Audit

## Resumen Ejecutivo

Esta auditoria revisa las rutas publicas que alimentan `ranking`, `stats`, `historico`, `historico-partida`, `partida-actual` e `index`, con foco en latencia percibida por UI y en el cumplimiento de la regla arquitectonica de leer read models publicos propios en PostgreSQL.

Actualizacion TASK-225, 2026-06-10: la deuda P1 de `stats search` y `stats player profile` fue corregida en codigo para que los GET publicos usen `player_search_index` y `player_period_stats` en modo read-only estricto, sin inicializar storage ni caer a runtime fallback pesado. La medicion HTTP final requiere redeploy. `current-match` sigue pendiente porque depende de RCON live y debe tratarse como hardening/degradacion sin cambiar hosts, puertos ni configuracion RCON.

Actualizacion TASK-226, 2026-06-10: `/api/current-match/kills` y `/api/current-match/players` pasan a usar AdminLog en lectura publica sin inicializar storage y con degradacion JSON controlada si el read model no esta disponible o falla. `/api/servers` pasa a ser snapshot/cache-only en el GET publico y ya no dispara refresh RCON/A2S live durante la lectura. La deuda restante de `current-match` queda en `/api/current-match`, que todavia puede intentar una muestra RCON directa antes de caer a snapshot.

Actualizacion TASK-227, 2026-06-10: la auditoria real post-`TASK-226` mostro que kills/players seguian bloqueando en produccion porque la rama PostgreSQL de AdminLog no propagaba `ensure_storage=False` a `connect_postgres_compat()`. El fix propaga `initialize=ensure_storage`, de modo que `/api/current-match/kills` y `/api/current-match/players` ya no ejecutan `initialize_postgres_rcon_storage()` en el GET publico cuando se sirven como lecturas read-only.

Actualizacion TASK-228, 2026-06-10: `/api/servers` deja de ser cache-only estricto y vuelve a ser near-real-time controlado para la home. Sirve snapshot fresco si existe; si no hay cache o esta stale, intenta RCON/A2S con timeout publico corto y degrada a snapshot stale o JSON controlado si live falla. `/api/servers/latest` e `/api/servers/history` siguen siendo lecturas de almacenamiento local, no sustitutos del estado live.

Conclusiones principales:

- El backend de `ranking` ya no muestra el cuello de botella grave del ranking anual. La evidencia mas fuerte es el test `backend/tests/test_annual_ranking_payload.py`, que confirma que la lectura anual en PostgreSQL ya no inicializa storage en request publico.
- El cuello de botella visible actual mas claro esta en frontend: `frontend/assets/js/ranking.js` y `frontend/assets/js/stats.js` bloquean la carga principal detras de `/health`, y `ranking.js` no tiene proteccion contra request race ni limpieza robusta del estado de carga.
- `historico.js` es hoy la referencia mas sana del frontend publico: usa snapshots, cache TTL, deduplicacion de peticiones y `requestId` para ignorar respuestas obsoletas.
- `partida-actual.js` no bloquea por `/health`, pero hace polling agresivo y paralelo a tres endpoints (`/api/current-match`, `/api/current-match/kills`, `/api/current-match/players`) sin `AbortController`, con intervalos de 1.5 s y 3 s que pueden amplificar carga y re-render innecesario. Tras TASK-227, kills/players usan AdminLog PostgreSQL en modo read-only real y degradan desde backend en JSON controlado.
- En backend siguen existiendo fallbacks runtime publicos sobre tablas materializadas grandes para `ranking`, `stats search` y `stats player profile`. Son mejores que consultar RCON directo, pero siguen rompiendo la meta de servir lecturas publicas desde read models dedicados.
- Las queries runtime de leaderboard y player stats usan patrones como `COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT))` y agregaciones sobre `rcon_match_player_stats`, lo que aumenta riesgo de scans y de uso parcial de indices.
- `current-match` sigue consultando RCON directo en request publico cuando hay target confiable. `/api/servers` tambien consulta live de forma controlada cuando falta cache o esta stale porque la home requiere estado actual/casi actual.

## Mapa de Arquitectura de Lectura Publica

Flujo esperado:

1. Procesos internos leen RCON, AdminLog o scoreboard publico cuando aplica.
2. Procesos internos refrescan snapshots y read models en PostgreSQL.
3. Endpoints publicos leen solo read models publicos, sin recalculo runtime ni inicializacion de storage.
4. Frontend pide datos principales sin bloquearlos por checks tecnicos no esenciales.

Flujo observado:

- `ranking` y `stats` mezclan frontend secuencial con backend que aun puede caer a runtime sobre tablas materializadas si falta snapshot o read model.
- `historico` ya prioriza snapshots y fallback controlado.
- `current-match` expone una excepcion relevante: `/api/current-match` consulta RCON directo en la ruta publica cuando encuentra target valido. Kills/players leen AdminLog sin inicializar storage en request publico, incluyendo la rama PostgreSQL corregida en `TASK-227`. `/api/servers` usa refresh live acotado cuando el cache no sirve para mantener la home casi en tiempo real.

## Inventario de Endpoints Publicos

| Ruta | Frontend | Builder backend | Read model esperado | Lectura observada | Fallback/runtime | Riesgo |
|---|---|---|---|---|---|---|
| `/api/ranking` | `frontend/assets/js/ranking.js` | `build_global_ranking_payload()` | `ranking_snapshots`, `ranking_snapshot_items`, `rcon_annual_ranking_snapshots`, `rcon_annual_ranking_snapshot_items` | Annual lee snapshot anual; weekly/monthly leen snapshot y pueden caer a `list_rcon_materialized_leaderboard()` | Si `HLL_BACKEND_RANKING_RUNTIME_FALLBACK_ENABLED=true`, si | P0 |
| `/api/stats/players/search` | `frontend/assets/js/stats.js` | `build_stats_player_search_payload()` | `player_search_index` | Primero `player_search_index`, si falla cae a runtime contra `rcon_match_player_stats` + `rcon_materialized_matches` | Si | P1 |
| `/api/stats/players/{player_id}` | `frontend/assets/js/stats.js` | `build_stats_player_profile_payload()` | `player_period_stats` | Primero `player_period_stats`, si falta cae a runtime y ademas calcula weekly/monthly ranking en caliente | Si | P1 |
| `/api/stats/rankings/annual` | `frontend/assets/js/stats.js` | `build_annual_ranking_snapshot_payload()` | `rcon_annual_ranking_snapshots`, `rcon_annual_ranking_snapshot_items` | Snapshot anual | No recalcula ranking en lectura | P2 |
| `/api/historical/snapshots/leaderboard` | `frontend/assets/js/historico.js` | `build_rcon_materialized_leaderboard_snapshot_payload()` en modo rcon | Snapshot historico publico equivalente | En modo rcon el nombre dice snapshot, pero sirve runtime fast path sobre materialized leaderboard | Si, por definicion del endpoint en modo rcon | P1 |
| `/api/historical/snapshots/recent-matches` | `frontend/assets/js/historico.js` | `build_recent_historical_matches_snapshot_payload()` | Snapshot publico de recent matches | Segun source kind puede usar RCON read model o fallback publico | Si | P2 |
| `/api/historical/matches/detail` | `frontend/assets/js/historico-partida.js` | `build_historical_match_detail_payload()` | Read model detalle de partida | Intenta `get_rcon_historical_match_detail()`, luego fallback a storage historico publico | Si | P2 |
| `/api/current-match` | `frontend/assets/js/partida-actual.js` | `build_current_match_payload()` | Read model live propio | Primero intenta `_query_current_match_rcon_sample()` directo; luego fallback a `/api/servers` snapshot | Si, y toca RCON directo | P0 |
| `/api/current-match/kills` | `frontend/assets/js/partida-actual.js` | `build_current_match_kill_feed_payload()` | Read model live propio de kill feed | AdminLog materializado en modo read-only publico; PostgreSQL usa `connect_postgres_compat(initialize=False)` | Degradacion JSON controlada si falla read model | P2 |
| `/api/current-match/players` | `frontend/assets/js/partida-actual.js` | `build_current_match_player_stats_payload()` | Read model live propio de player stats | AdminLog materializado en modo read-only publico; PostgreSQL usa `connect_postgres_compat(initialize=False)` | Degradacion JSON controlada si falla read model | P2 |
| `/api/servers` | `frontend/assets/js/main.js`, fallback de current-match | `build_servers_payload()` | Snapshot live de servidores | Snapshot fresco o refresh live RCON/A2S acotado si falta/stale | Stale snapshot o JSON controlado si live falla | P1 |
| `/health` | `frontend/assets/js/main.js`, `ranking.js`, `stats.js` | `build_health_payload()` | N/A | Check tecnico | No aplica | P1 por bloqueo UI, no por backend |

Notas:

- El endpoint equivalente real al pedido como `/api/current-match/player-stats` es `/api/current-match/players`.
- El equivalente real de `historico` no es una sola ruta `/api/historico`; el frontend consume varias rutas bajo `/api/historical/...`.

## Analisis Frontend

### Ranking

Archivo: `frontend/assets/js/ranking.js`

Hallazgos:

- La carga inicial depende de `refreshBackendHealth()` y solo despues llama `loadRanking()`.
- Si `/health` tarda, falla o llega fuera de orden respecto a cambios del usuario, la UI puede permanecer en `Cargando ranking global...` o en estado offline aunque `/api/ranking` sea rapido.
- No hay `AbortController` ni `currentRequestId`.
- Cada cambio de filtro dispara `loadRanking()` sin proteccion contra respuestas antiguas.
- No hay `finally` dedicado para limpiar loading o reactivar controles.
- `clearRankingSurface()` vacia tabla y meta antes de cada request, amplificando el parpadeo de UI.

Impacto:

- Alto en latencia percibida.
- Alto en riesgo de estado obsoleto.

### Stats

Archivo: `frontend/assets/js/stats.js`

Hallazgos:

- Repite el patron de esperar `/health` antes de cargar el ranking anual.
- `searchPlayers()` hace una sola request, pero cualquier error marca backend offline globalmente.
- `loadPlayerProfile()` usa `Promise.allSettled()` para semanal y mensual, lo cual es correcto, pero sigue dependiendo del flag global `isBackendOnline`.
- No hay cancelacion de busquedas sucesivas ni de perfiles sucesivos.

Impacto:

- Alto en UX.
- Medio en carga backend.

### Historico

Archivo: `frontend/assets/js/historico.js`

Fortalezas observadas:

- Usa `activeServerRequestId` y `activeLeaderboardRequestId`.
- Cachea snapshots con TTL.
- Deduplica peticiones en `pendingRequestCache`.
- Hidrata desde cache y luego refresca.
- No bloquea la carga principal detras de `/health`.

Riesgos residuales:

- Mucho uso de `innerHTML` completo en bloques grandes.
- El endpoint llamado como `snapshots/leaderboard` en modo rcon puede ser runtime fast path, lo que hace que la UI se vea sana aunque backend no este sirviendo un snapshot real.

### Historico Partida

Archivo: `frontend/assets/js/historico-partida.js`

Hallazgos:

- Hace una sola request principal de detalle.
- No hay `/health` previo.
- El costo fuerte parece mas de render DOM que de orchestration.

Riesgo:

- Bajo a medio.

### Partida Actual

Archivo: `frontend/assets/js/partida-actual.js`

Hallazgos:

- Polling en tres loops independientes:
  - current match cada 30 s
  - kills cada 1.5 s
  - players cada 3 s
- Hay guardas `*_RefreshInFlight`, pero no `AbortController`.
- Si el usuario abandona la pagina sin descargar el documento, el polling sigue hasta destruir el contexto.
- `current-match` re-renderiza bloques completos con `innerHTML`.
- `kill feed` y `player stats` reducen re-render con `visibleSignature`, lo cual ayuda.

Riesgo:

- Alto para carga sostenida.
- Alto si la base live comparte recursos con lecturas publicas.

### Landing

Archivo: `frontend/assets/js/main.js`

Hallazgos:

- `fetchHealth()` es paralelo a `hydrateTrailer()` y `refreshServers()`, no bloqueante.
- El polling de servidores es cada 300 s y tiene guardas `serverRefreshInFlight`.

Riesgo:

- Bajo.

## Analisis Backend

### Confirmaciones positivas

- `backend/tests/test_annual_ranking_payload.py` confirma que `get_annual_ranking_snapshot()` no llama `initialize_rcon_materialized_storage()` en lectura PostgreSQL. Ese fix elimina el cuello de botella mas grave ya conocido del ranking anual.
- `routes.py` separa parseo/validacion de parametros y builders por endpoint de forma clara.
- `main.py` ya serializa `date` y `datetime` para no abortar respuestas por JSON.

### Riesgos de backend por area

#### Ranking publico

Archivos: `backend/app/payloads.py`, `backend/app/rcon_historical_leaderboards.py`, `backend/app/rcon_annual_rankings.py`

Hallazgos:

- Weekly/monthly `build_global_ranking_payload()` puede caer a `list_rcon_materialized_leaderboard()` si falta snapshot y el flag runtime fallback sigue activo.
- `list_rcon_materialized_leaderboard()` hace agregacion runtime sobre `rcon_match_player_stats` + `rcon_materialized_matches`.
- Las ventanas usan filtros sobre `COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT))`, lo que puede degradar indices y elevar costo.

Riesgo:

- El endpoint publico sigue siendo rapido hoy en muchos casos, pero no esta totalmente blindado contra crecimiento de datos.

#### Stats search

Archivo: `backend/app/rcon_historical_player_stats.py`

Hallazgos:

- `search_rcon_materialized_players()` usa `player_search_index` primero, bien.
- Si el read model falla o falta, cae a runtime contra tablas grandes.
- La busqueda runtime usa `LOWER(COALESCE(stats.player_name,'')) LIKE LOWER(?)`, agregacion por jugador y luego lookups adicionales de nombres y `servers_seen`.

Riesgo:

- Posible scan costoso y plan poco estable al crecer el historico.

#### Stats player profile

Archivo: `backend/app/rcon_historical_player_stats.py`

Hallazgos:

- `get_rcon_materialized_player_stats()` usa `player_period_stats` primero, bien.
- Si falta, cae a runtime y ademas consulta ranking semanal y mensual del jugador contra tablas materializadas.
- La ruta runtime agrega sobre stats, busca source range y ranking semanal/mensual en la misma lectura.

Riesgo:

- Latencia alta en cold path o con crecimiento de tabla.

#### Historical endpoints

Archivo: `backend/app/payloads.py`

Hallazgos:

- `build_recent_historical_matches_payload()` y `build_historical_match_detail_payload()` permiten fallback a storage publico cuando el read model RCON no cubre el caso.
- El test `test_public_scoreboard_fallback_used_only_without_rcon_activity` confirma que el fallback sigue activo y esperado.

Riesgo:

- Correcto como compatibilidad, pero dificulta garantizar tiempos uniformes y pureza de read model publico.

#### Current match

Archivo: `backend/app/payloads.py`

Hallazgos:

- `build_current_match_payload()` intenta `_query_current_match_rcon_sample()` en request publico.
- Solo si falla usa snapshot de `/api/servers`.

Riesgo:

- Este es el incumplimiento arquitectonico mas claro: request publico consultando RCON directo.

#### Conexiones y cold path

Archivos: `backend/app/postgres_rcon_storage.py`, `backend/app/config.py`

Hallazgos:

- Se usa `psycopg.connect(...)` por contexto, no se observa pool reutilizable.
- No se observan migrations/initializers pesados dentro de rutas publicas, salvo funciones de read model que aun llaman wrappers de initialize en algunas rutas runtime.

Riesgo:

- Medio. La ausencia de pooling puede no ser critica hoy, pero empeora cold starts y bursts cortos.

## Analisis PostgreSQL / Read Models

### Tablas publicas esperadas

- `player_search_index`
- `player_period_stats`
- `ranking_snapshots`
- `ranking_snapshot_items`
- `rcon_annual_ranking_snapshots`
- `rcon_annual_ranking_snapshot_items`

### Tablas grandes o candidatas a crecimiento

- `rcon_materialized_matches`
- `rcon_match_player_stats`

### Indices confirmados por codigo

- `idx_ranking_snapshots_lookup`
- `idx_ranking_snapshot_items_snapshot`
- `idx_ranking_snapshot_items_player`
- `idx_rcon_annual_ranking_snapshots_year`
- `idx_rcon_annual_ranking_snapshots_status`
- `idx_player_search_index_name`
- `idx_player_search_index_last_seen`
- `idx_player_search_index_player`
- `idx_player_period_stats_player_period_server`
- `idx_player_period_stats_server_period`
- `idx_player_period_stats_last_seen`
- `idx_player_period_stats_updated`
- `idx_rcon_materialized_matches_recent`
- indices textuales sobre `COALESCE(CAST(ended_at AS TEXT), CAST(started_at AS TEXT))`
- `idx_rcon_match_player_stats_match`
- `idx_rcon_match_player_stats_player_id_match`

### Riesgos de SQL

- Varios paths runtime filtran por `COALESCE(CAST(matches.ended_at AS TEXT), CAST(matches.started_at AS TEXT)) >= ?`.
- Ese patron tiende a forzar expresiones calculadas en filtro, incluso aunque existan indices funcionales; es un area clara para `EXPLAIN ANALYZE`.
- `LIKE` sobre `LOWER(player_name)` puede degradarse sin estrategia de indice orientada a busqueda parcial.
- Agregaciones publicas sobre `COUNT(DISTINCT stats.match_key)` y `SUM(...)` en tablas grandes deben salir de snapshots o read models, no del path web.

### Queries candidatas a EXPLAIN ANALYZE

- Runtime fallback de `list_rcon_materialized_leaderboard()`
- Runtime fallback de `_search_rcon_materialized_players_runtime()`
- Runtime fallback de `_get_rcon_materialized_player_stats_runtime()`
- Lectura de `get_latest_ranking_snapshot()`
- Lectura de `get_annual_ranking_snapshot()`
- Lectura de `player_search_index` por `server_id + normalized_player_name`
- Lectura de `player_period_stats` por `player_id + period_type + server_id`

### Locks y refresh

- Los runners usan `backend_writer_lock` para procesos internos, lo cual ayuda a writers.
- Aun asi, refreshes completos de snapshots y read models pueden competir por IO con lecturas publicas si comparten la misma base y no se mide el impacto.
- La auditoria no encontro evidencia directa de locks de lectura publica, pero si suficiente motivo para instrumentarlos.

## Riesgos de Fallback / Runtime

Principio deseado:

- Publico: solo read models publicos.
- Interno: materializacion y recalculo.

Desviaciones observadas:

- `/api/ranking` weekly/monthly puede recalcular agregados runtime sobre tablas materializadas.
- `/api/stats/players/search` puede escanear runtime si falta `player_search_index`.
- `/api/stats/players/{player_id}` puede recalcular runtime si falta `player_period_stats`.
- `/api/current-match` consulta RCON directo en request publico.
- `historico` snapshot en modo rcon puede servir runtime fast path en lugar de snapshot real.

## Observabilidad Recomendada

Medicion backend por request:

- `endpoint`
- `status_code`
- `total_duration_ms`
- `db_duration_ms`
- `payload_build_duration_ms`
- `query_count`
- `read_model`
- `fallback_used`
- `fallback_reason`
- `snapshot_status`
- `payload_bytes`
- `timeframe`
- `server_id`
- `metric`
- `limit`

Medicion frontend por vista:

- `page`
- `request_started_at`
- `response_received_at`
- `render_completed_at`
- `perceived_latency_ms`
- `health_blocked_main_data` boolean
- `request_aborted`
- `request_superseded`
- `render_error`
- `stale_response_ignored`

Puntos concretos:

- `performance.mark()` / `performance.measure()` en `ranking.js`, `stats.js`, `partida-actual.js`
- Logging estructurado por endpoint en `main.py` o wrapper de builders
- Incluir `read_model`, `fallback_used`, `snapshot_status` y `payload_bytes` en la respuesta o en logs
- Contador de queries por request en paths publicos costosos

## Matriz de Hallazgos Priorizados

| Pri | Hallazgo | Impacto | Evidencia | Archivo | Propuesta | Riesgo | Validacion |
|---|---|---|---|---|---|---|---|
| P0 | `ranking.js` bloquea la carga principal detras de `/health` y no protege carreras | UI lenta o bloqueada aunque `/api/ranking` responda en <200 ms | Flujo `refreshBackendHealth() -> loadRanking()` y ausencia de `AbortController/currentRequestId` | `frontend/assets/js/ranking.js` | Separar health del dato principal y usar cancelacion o requestId | Bajo | medir `response_received_at -> render_completed_at` |
| P0 | `/api/current-match` consulta RCON directo en request publico | Rompe la regla arquitectonica y puede introducir latencia o fragilidad externa | `_query_current_match_rcon_sample()` se ejecuta antes del fallback a snapshot | `backend/app/payloads.py` | Crear read model live publico y mover la consulta RCON al runner | Medio | endpoint debe seguir respondiendo sin tocar RCON |
| P1 | `/api/ranking` weekly/monthly mantiene fallback runtime sobre tablas materializadas | Riesgo de latencia creciente y scans | `build_global_ranking_payload()` cae a `list_rcon_materialized_leaderboard()` | `backend/app/payloads.py` | Desactivar fallback runtime en publico tras completar snapshot coverage | Medio | requests solo con `read_model=ranking-snapshot` |
| P1 | `stats.js` tambien bloquea por `/health` el ranking anual inicial | Latencia percibida innecesaria | `refreshBackendHealth()` llama `loadAnnualRanking()` despues de `/health` | `frontend/assets/js/stats.js` | Cargar anual directo y tratar `/health` como señal secundaria | Bajo | anual visible sin depender de health |
| P1 | Search de jugadores puede caer a runtime costoso | Picos de latencia en busqueda | `search_rcon_materialized_players()` con fallback runtime | `backend/app/rcon_historical_player_stats.py` | Endurecer cobertura de `player_search_index` y alertar si falta | Bajo | `fallback_used=false` sostenido |
| P1 | Perfil de jugador puede caer a runtime y recomponer rankings semanales/mensuales | Respuestas lentas y carga de DB | `get_rcon_materialized_player_stats()` | `backend/app/rcon_historical_player_stats.py` | Exigir `player_period_stats` actualizado antes de publicar | Medio | `read_model=player-period-stats` |
| P1 | Endpoints snapshot historicos en modo rcon no siempre son snapshots reales | Ambiguedad operativa y mediciones engañosas | `build_rcon_materialized_leaderboard_snapshot_payload()` declara snapshot pero usa runtime materialized fast path | `backend/app/rcon_historical_leaderboards.py` | Renombrar politica o servir snapshot real | Medio | source/generation policy coherentes |
| P2 | Polling de current match demasiado agresivo | Carga sostenida y re-render frecuente | intervalos de 1.5 s / 3 s / 30 s | `frontend/assets/js/partida-actual.js` | Consolidar polling o usar fan-out backend/cache | Medio | bajar requests por minuto |
| P2 | Paths runtime usan `COALESCE(CAST(... AS TEXT))` en filtros temporales | Planes menos eficientes | multiples queries runtime en leaderboard y player stats | `backend/app/rcon_historical_leaderboards.py`, `backend/app/rcon_historical_player_stats.py` | Revisar predicados e indices funcionales con EXPLAIN | Medio | comparar buffers/scan time |
| P3 | No se observa pooling PostgreSQL reutilizable | Mayor costo de cold path y bursts | `psycopg.connect()` por contexto | `backend/app/postgres_rcon_storage.py` | Evaluar pool ligero cuando el resto del path este estabilizado | Medio | medir connect time y throughput |

## Plan de Tasks Recomendado

1. `TASK-215-decouple-public-frontend-data-load-from-health-checks`
   Alcance: `ranking.js`, `stats.js`.
   Objetivo: no bloquear datos principales por `/health`.

2. `TASK-216-add-request-race-protection-to-public-ranking-and-stats`
   Alcance: `ranking.js`, `stats.js`.
   Objetivo: `AbortController` o `currentRequestId`, cleanup robusto de loading.

3. `TASK-217-enforce-snapshot-only-public-ranking-read-path`
   Alcance: backend publico de `ranking`.
   Objetivo: eliminar fallback runtime en `/api/ranking` para weekly/monthly.

4. `TASK-218-enforce-read-model-only-public-player-search-and-profile`
   Alcance: `player_search_index`, `player_period_stats`, runners, payloads.
   Objetivo: que search y profile no caigan a runtime en request publico.

5. `TASK-219-create-live-public-current-match-read-model`
   Alcance: current match.
   Objetivo: sacar RCON directo del endpoint publico.

6. `TASK-220-add-public-request-performance-observability`
   Alcance: backend + frontend instrumentation minima.
   Objetivo: medir request, DB, payload, render y fallback.

7. `TASK-221-run-explain-analyze-for-public-runtime-and-read-model-queries`
   Alcance: SQL audit operativa.
   Objetivo: validar indices y predicados temporales.
