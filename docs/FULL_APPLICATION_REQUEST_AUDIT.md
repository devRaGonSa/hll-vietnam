# Full Application Request Audit

Fecha: 2026-06-10  
Task: `TASK-224-full-application-request-audit`  
Alcance: auditoria de peticiones publicas frontend/backend/API sin aplicar fixes funcionales.

## Resumen ejecutivo

La auditoria encontro 36 patrones HTTP publicos en `backend/app/routes.py`, 12 ocurrencias `fetch(` en JavaScript publico, 15 literales `/api/...` en frontend y 13 referencias `localhost`/`127.0.0.1` en HTML/JS publico. No se encontro `XMLHttpRequest`.

Se ejecuto la auditoria contra `https://comunidadhll.devzamode.es` con 191 probes automaticos y 4 probes manuales dependientes de `player_id`. Resultado combinado:

| Severidad | Cantidad |
| --- | ---: |
| OK | 77 |
| WARNING | 112 |
| CRITICAL | 6 |

Los fallos criticos actuales no estan en rankings/snapshots ni en el match detail historico probado. Estan en:

- `/api/stats/players/search?q=Medu&server_id=all&limit=10`: timeout a 30s.
- `/api/stats/players/{player_id}?timeframe=weekly|monthly&server_id=all`: timeout a 30s.
- `/api/current-match/kills?server=comunidad-hispana-01&limit=30`: timeout a 30s.
- `/api/current-match/players?server=comunidad-hispana-01`: timeout a 30s.
- `/api/current-match/kills?server=comunidad-hispana-02&limit=30`: 500 en una ejecucion y timeout en una repeticion manual.

`/api/historical/matches/detail` con el match real `comunidad-hispana-01:1781023156:1781028555:purpleheartlanewarfare` respondio `200` en `120.47 ms` y `125580 B`. Sigue teniendo deuda de inicializacion en lectura en la cadena estatica, pero ya no es el endpoint publico mas critico segun la medicion de produccion de esta auditoria.

Siguiente fix prioritario recomendado: aislar o eliminar inicializacion/fallback runtime de `/api/stats/players/search` y `/api/stats/players/{player_id}`. Despues, corregir `/api/current-match/kills` y `/api/current-match/players`. `/api/historical/matches/detail` debe quedar en cola de hardening para hacerlo estrictamente read-only, pero no aparece como el primer incendio operativo en esta medicion.

## Evidencia ejecutada

Comandos ejecutados:

```powershell
python -m compileall backend\app
python -m py_compile scripts\audit_public_requests.py
cd backend
python -m unittest tests.test_rcon_materialization_pipeline
```

Resultado:

- `compileall`: OK.
- `py_compile`: OK.
- `unittest`: OK, 9 tests en 0.588s. El test existente emitio `ResourceWarning` por conexiones SQLite sin cerrar, sin fallo de test.

Auditoria local:

- `http://127.0.0.1:8000/health` no estaba disponible desde el host, por lo que no se lanzo la matriz completa local.

Auditoria produccion:

```powershell
python scripts\audit_public_requests.py --base-url https://comunidadhll.devzamode.es --timeout 30 --output tmp\public_request_audit.json
```

Resultado automatico:

- Probes lanzados: 191.
- `OK`: 77.
- `WARNING`: 110.
- `CRITICAL`: 4.
- HTTP 200: 187.
- HTTP 500: 1.
- Timeout/error sin status: 3.
- Warnings con `fallback_used=true`: 109.
- Snapshots con `snapshot_status=missing`: 75.

Probes manuales adicionales dependientes de `player_id`:

| Endpoint | Resultado | Tiempo | Severidad |
| --- | ---: | ---: | --- |
| `/api/stats/players/76561198092154180?timeframe=weekly&server_id=all` | timeout | 30094.15 ms | CRITICAL |
| `/api/stats/players/76561198092154180?timeframe=monthly&server_id=all` | timeout | 30046.21 ms | CRITICAL |
| `/api/historical/player-profile?player=76561198092154180` | 200 | 4736.64 ms | WARNING |
| `/api/historical/elo-mmr/player?server=all-servers&player=76561198092154180` | 200 | 46.87 ms | WARNING |

El `player_id` se obtuvo desde `/api/ranking?timeframe=weekly&server_id=all&metric=kills&limit=1`.

## Inventario backend

Rutas HTTP publicas extraidas de `backend/app/routes.py`: 36 patrones.

| ID | Metodo | Path | Handler/payload builder | Parametros | Fuente/modelo esperado |
| --- | --- | --- | --- | --- | --- |
| B001 | GET | `/health` | `build_health_payload` | ninguno | config/runtime status |
| B002 | GET | `/api/community` | `build_community_payload` | ninguno | payload estatico |
| B003 | GET | `/api/trailer` | `build_trailer_payload` | ninguno | payload estatico |
| B004 | GET | `/api/discord` | `build_discord_payload` | ninguno | payload estatico |
| B005 | GET | `/api/servers` | `build_servers_payload` | ninguno | latest snapshots; si stale refresca RCON/A2S |
| B006 | GET | `/api/servers/latest` | `build_server_latest_payload` | ninguno | `list_latest_snapshots` |
| B007 | GET | `/api/servers/history` | `build_server_history_payload` | `limit` | `list_snapshot_history` |
| B008 | GET | `/api/servers/{id}/history` | `build_server_detail_history_payload` | `id`, `limit` | `list_server_history` |
| B009 | GET | `/api/stats/players/search` | `build_stats_player_search_payload` | `q`, `server_id/server`, `limit` | player search read model; fallback runtime RCON materialized |
| B010 | GET | `/api/stats/rankings/annual` | `build_annual_ranking_snapshot_payload` | `year`, `metric=kills`, `server_id/server`, `limit` | annual ranking snapshot |
| B011 | GET | `/api/ranking` | `build_global_ranking_payload` | `timeframe`, `server_id/server`, `metric`, `limit`, `year` for annual | ranking snapshots; annual snapshots |
| B012 | GET | `/api/current-match` | `build_current_match_payload` | `server` | direct RCON sample; fallback `/api/servers` path |
| B013 | GET | `/api/current-match/kills` | `build_current_match_kill_feed_payload` | `server`, `limit`, `since_event_id` | AdminLog storage |
| B014 | GET | `/api/current-match/players` | `build_current_match_player_stats_payload` | `server` | AdminLog storage |
| B015 | GET | `/api/stats/players/{player_id}` | `build_stats_player_profile_payload` | `player_id`, `timeframe`, `server_id/server` | player period stats read model; fallback runtime |
| B016 | GET | `/api/historical/weekly-top-kills` | `build_weekly_top_kills_payload` | `limit`, `server` | legacy historical storage |
| B017 | GET | `/api/historical/leaderboard` | `build_historical_leaderboard_payload` | `limit`, `server`, `metric`, `timeframe` | RCON read model plus public-scoreboard fallback |
| B018 | GET | `/api/historical/weekly-leaderboard` | `build_weekly_leaderboard_payload` | `limit`, `server`, `metric` | legacy weekly storage |
| B019 | GET | `/api/historical/monthly-leaderboard` | `build_monthly_leaderboard_payload` | `limit`, `server`, `metric` | legacy monthly storage |
| B020 | GET | `/api/historical/monthly-mvp` | `build_monthly_mvp_payload` | `limit`, `server` | legacy monthly storage |
| B021 | GET | `/api/historical/monthly-mvp-v2` | `build_monthly_mvp_v2_payload` | `limit`, `server` | legacy monthly storage |
| B022 | GET | `/api/historical/player-events` | `build_player_event_payload` | `limit`, `server`, `view` | legacy player event storage |
| B023 | GET | `/api/historical/snapshots/leaderboard` | `build_leaderboard_snapshot_payload` | `limit`, `server`, `metric`, `timeframe` | displayed historical snapshots |
| B024 | GET | `/api/historical/snapshots/monthly-leaderboard` | `build_monthly_leaderboard_snapshot_payload` | `limit`, `server`, `metric` | displayed historical snapshots |
| B025 | GET | `/api/historical/snapshots/monthly-mvp` | `build_monthly_mvp_snapshot_payload` | `limit`, `server` | displayed historical snapshots |
| B026 | GET | `/api/historical/snapshots/monthly-mvp-v2` | `build_monthly_mvp_v2_snapshot_payload` | `limit`, `server` | displayed historical snapshots |
| B027 | GET | `/api/historical/snapshots/player-events` | `build_player_event_snapshot_payload` | `limit`, `server`, `view` | displayed historical snapshots |
| B028 | GET | `/api/historical/snapshots/weekly-leaderboard` | `build_weekly_leaderboard_snapshot_payload` | `limit`, `server`, `metric` | displayed historical snapshots |
| B029 | GET | `/api/historical/recent-matches` | `build_recent_historical_matches_payload` | `limit`, `server` | RCON read model plus scoreboard merge |
| B030 | GET | `/api/historical/snapshots/recent-matches` | `build_recent_historical_matches_snapshot_payload` | `limit`, `server` | displayed historical snapshots |
| B031 | GET | `/api/historical/matches/detail` | `build_historical_match_detail_payload` | `server`, `match` | RCON materialized detail; fallback scoreboard detail |
| B032 | GET | `/api/historical/server-summary` | `build_historical_server_summary_payload` | `server` | RCON read model plus fallback |
| B033 | GET | `/api/historical/snapshots/server-summary` | `build_historical_server_summary_snapshot_payload` | `server` | displayed historical snapshots |
| B034 | GET | `/api/historical/player-profile` | `build_historical_player_profile_payload` | `player` | legacy historical profile |
| B035 | GET | `/api/historical/elo-mmr/leaderboard` | `build_elo_mmr_leaderboard_payload` | `limit`, `server` | Elo/MMR engine/read storage, currently fallback/paused in public payload |
| B036 | GET | `/api/historical/elo-mmr/player` | `build_elo_mmr_player_payload` | `player`, `server` | Elo/MMR engine/read storage, currently fallback/paused in public payload |

## Matriz completa de peticiones

La tabla usa rangos cuando una ruta se lanzo con varias combinaciones representativas. El JSON probe-a-probe esta en `tmp/public_request_audit.json`.

| ID | Tipo | Archivo origen | Pagina/contexto | Metodo | Endpoint/path | Parametros requeridos | Ejemplo de URL real | Handler/backend function | Fuente de datos | Usa snapshot/read-model/materialized/legacy/RCON/directo | Ejecuta initialize/ensure/bootstrap en lectura publica | Riesgo fallback pesado | Riesgo timeout | Loading/error frontend | Validacion ejecutada | Resultado HTTP | Tiempo medido | Tamano respuesta | Observaciones | Severidad | Recomendacion |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M001 | backend-api | `backend/app/routes.py` | health | GET | `/health` | ninguno | `/health` | `build_health_payload` | config | status directo | no | no | bajo | n/a | produccion | 200 | 210.37 ms | 264 B | OK | OK | mantener |
| M002 | backend-api | `backend/app/routes.py` | landing metadata | GET | `/api/community` | ninguno | `/api/community` | `build_community_payload` | estatico | directo | no | no | bajo | n/a | produccion | 200 | 22.33 ms | 203 B | OK | OK | mantener |
| M003 | backend-api | `backend/app/routes.py` | trailer | GET | `/api/trailer` | ninguno | `/api/trailer` | `build_trailer_payload` | estatico | directo | no | no | bajo | main usa error controlado | produccion | 200 | 33.08 ms | 139 B | OK | OK | mantener |
| M004 | backend-api | `backend/app/routes.py` | discord | GET | `/api/discord` | ninguno | `/api/discord` | `build_discord_payload` | estatico | directo | no | no | bajo | n/a | produccion | 200 | 47.26 ms | 137 B | OK | OK | mantener |
| M005 | backend-api | `backend/app/routes.py` | server cards | GET | `/api/servers` | ninguno | `/api/servers` | `build_servers_payload` | latest snapshots + live refresh | snapshot/RCON/A2S | no DDL, pero red externa en lectura si stale | si | medio | main tiene fallback visual | produccion | 200 | 4311.38 ms | 1751 B | `source=real-time-rcon-refresh` | WARNING | servir snapshot estricto y mover refresh fuera de request |
| M006 | backend-api | `backend/app/routes.py` | server history | GET | `/api/servers/latest` | ninguno | `/api/servers/latest` | `build_server_latest_payload` | local snapshot storage | snapshot legacy | posible `initialize_storage` por storage local | no | bajo | n/a | produccion | 200 | 42.17 ms | 184 B | OK | OK | mantener |
| M007 | backend-api | `backend/app/routes.py` | server history | GET | `/api/servers/history` | `limit` | `/api/servers/history?limit=20` | `build_server_history_payload` | local snapshot storage | snapshot legacy | posible `initialize_storage` por storage local | no | bajo | n/a | produccion | 200 | 40.59 ms | 167 B | OK | OK | mantener |
| M008 | backend-api | `backend/app/routes.py` | server history detail | GET | `/api/servers/{id}/history` | `id`, `limit` | `/api/servers/comunidad-hispana-01/history?limit=20` | `build_server_detail_history_payload` | local snapshot storage | snapshot legacy | posible `initialize_storage` por storage local | no | bajo | n/a | produccion | 200 | 46.53-78.34 ms | 194 B | OK | OK | mantener |
| M009 | backend-api | `backend/app/routes.py` | stats search | GET | `/api/stats/players/search` | `q`, `server_id/server`, `limit` | `/api/stats/players/search?q=Medu&server_id=all&limit=10` | `build_stats_player_search_payload` | player search index | read-model + runtime materialized fallback | si: `initialize_player_search_index_storage` -> `initialize_rcon_materialized_storage` -> `initialize_postgres_rcon_storage` | si | alto | stats puede quedar esperando hasta timeout navegador | produccion | timeout | 30019.46 ms | 0 B | probe CRITICAL | CRITICAL | primer fix: read-only estricto, sin inicializar ni fallback runtime |
| M010 | backend-api | `backend/app/routes.py` | stats annual ranking | GET | `/api/stats/rankings/annual` | `year`, `metric=kills`, `server_id/server`, `limit` | `/api/stats/rankings/annual?year=2026&metric=kills&server_id=all&limit=10` | `build_annual_ranking_snapshot_payload` | annual ranking snapshot | snapshot | no en lectura normal | no | bajo | stats tiene error controlado | produccion | 200 | 60.07 ms | 5236 B | OK | OK | mantener |
| M011 | backend-api | `backend/app/routes.py` | ranking | GET | `/api/ranking` | `timeframe`, `server_id/server`, `metric`, `limit`, `year` anual | `/api/ranking?timeframe=weekly&server_id=all&metric=kills&limit=20` | `build_global_ranking_payload` | ranking snapshots | snapshot/read-model | no en lectura snapshot; fallback runtime opcional por env | si si env fallback esta activo | bajo | ranking usa AbortController/requestId | produccion | 200 | 31.40-129.56 ms | 755-5668 B | 55 probes OK | OK | mantener fallback runtime desactivado en publico |
| M012 | backend-api | `backend/app/routes.py` | partida actual resumen | GET | `/api/current-match` | `server` | `/api/current-match?server=comunidad-hispana-01` | `build_current_match_payload` | RCON live | directo RCON + fallback `/api/servers` | no DDL | si, por fallback live | medio | partida actual tiene in-flight guard, sin timeout | produccion | 200 | 1242.08-2155.20 ms | 808-820 B | OK pero red externa en request | OK | mover a snapshot/read-model publico |
| M013 | backend-api | `backend/app/routes.py` | partida actual kills | GET | `/api/current-match/kills` | `server`, `limit`, `since_event_id` | `/api/current-match/kills?server=comunidad-hispana-01&limit=30` | `build_current_match_kill_feed_payload` | AdminLog | materialized AdminLog | si: `initialize_rcon_admin_log_storage` -> `initialize_postgres_rcon_storage` | desconocido | alto | polling 1.5s con in-flight guard, sin timeout | produccion | timeout/500 | 6268.78-30024.86 ms | 0-58 B | CH01 timeout, CH02 500 y luego timeout manual | CRITICAL | segundo fix: read-only connection y query/index audit |
| M014 | backend-api | `backend/app/routes.py` | partida actual jugadores | GET | `/api/current-match/players` | `server` | `/api/current-match/players?server=comunidad-hispana-01` | `build_current_match_player_stats_payload` | AdminLog | materialized AdminLog | si: `initialize_rcon_admin_log_storage` -> `initialize_postgres_rcon_storage` | desconocido | alto | polling 3s con in-flight guard, sin timeout | produccion | timeout/200 | 1090.32-30096.62 ms | 0-72280 B | CH01 timeout; CH02 OK | CRITICAL | segundo fix junto con kills |
| M015 | backend-api | `backend/app/routes.py` | stats player detail | GET | `/api/stats/players/{player_id}` | `player_id`, `timeframe`, `server_id/server` | `/api/stats/players/76561198092154180?timeframe=weekly&server_id=all` | `build_stats_player_profile_payload` | player period stats | read-model + runtime fallback | si: `initialize_player_period_stats_storage` -> `initialize_rcon_materialized_storage` -> `initialize_postgres_rcon_storage` | si | alto | stats sin AbortController/timeout | manual produccion | timeout | 30046.21-30094.15 ms | 0 B | weekly/monthly CRITICAL | CRITICAL | primer fix junto con player search |
| M016 | backend-api | `backend/app/routes.py` | legacy historical top kills | GET | `/api/historical/weekly-top-kills` | `limit`, `server` | `/api/historical/weekly-top-kills?server=all-servers&limit=10` | `build_weekly_top_kills_payload` | historical storage | legacy/fallback | si en Postgres display fallback paths | si | bajo | n/a | produccion | 200 | 53.72-75.73 ms | 806 B | `fallback_used=true` | WARNING | convertir a snapshot estricto o marcar legacy |
| M017 | backend-api | `backend/app/routes.py` | legacy historical leaderboard | GET | `/api/historical/leaderboard` | `limit`, `server`, `metric`, `timeframe` | `/api/historical/leaderboard?server=all-servers&timeframe=weekly&metric=kills&limit=10` | `build_historical_leaderboard_payload` | RCON/historical storage | read-model + legacy fallback | si en legacy display paths | si | bajo | n/a | produccion | 200 | 38-132 ms | ~1375-1414 B | `fallback_used=true` en muchos probes | WARNING | documentar deprecacion o hacer snapshot-only |
| M018 | backend-api | `backend/app/routes.py` | legacy weekly leaderboard | GET | `/api/historical/weekly-leaderboard` | `limit`, `server`, `metric` | `/api/historical/weekly-leaderboard?server=comunidad-hispana-01&metric=kills&limit=10` | `build_weekly_leaderboard_payload` | historical storage | legacy | si en Postgres display paths | si | bajo | n/a | produccion | 200 | 55-58 ms | ~1380 B | fallback | WARNING | snapshot-only o mantener como legacy controlado |
| M019 | backend-api | `backend/app/routes.py` | legacy monthly leaderboard | GET | `/api/historical/monthly-leaderboard` | `limit`, `server`, `metric` | `/api/historical/monthly-leaderboard?server=comunidad-hispana-02&metric=kills&limit=10` | `build_monthly_leaderboard_payload` | historical storage | legacy | si en Postgres display paths | si | bajo | n/a | produccion | 200 | 57-116 ms | ~1360 B | fallback | WARNING | snapshot-only o mantener como legacy controlado |
| M020 | backend-api | `backend/app/routes.py` | monthly MVP | GET | `/api/historical/monthly-mvp` | `limit`, `server` | `/api/historical/monthly-mvp?server=all-servers&limit=10` | `build_monthly_mvp_payload` | historical storage | legacy | si en Postgres display paths | si | bajo | n/a | produccion | 200 | 43-58 ms | 1470 B | fallback | WARNING | snapshot-only |
| M021 | backend-api | `backend/app/routes.py` | monthly MVP V2 | GET | `/api/historical/monthly-mvp-v2` | `limit`, `server` | `/api/historical/monthly-mvp-v2?server=all-servers&limit=10` | `build_monthly_mvp_v2_payload` | historical storage | legacy | si en Postgres display paths | si | bajo | n/a | produccion | 200 | 40-72 ms | 1509 B | fallback | WARNING | snapshot-only |
| M022 | backend-api | `backend/app/routes.py` | player events | GET | `/api/historical/player-events` | `limit`, `server`, `view` | `/api/historical/player-events?server=comunidad-hispana-01&view=duels&limit=10` | `build_player_event_payload` | player event storage | legacy | posible initialize legacy storage | si | bajo | n/a | produccion | 200 | 38-67 ms | ~1144-1156 B | fallback | WARNING | snapshot-only |
| M023 | backend-api | `backend/app/routes.py` | snapshot leaderboard | GET | `/api/historical/snapshots/leaderboard` | `limit`, `server`, `metric`, `timeframe` | `/api/historical/snapshots/leaderboard?server=all-servers&timeframe=weekly&metric=kills&limit=10` | `build_leaderboard_snapshot_payload` | displayed snapshots | snapshot | si en Postgres: `get_snapshot` -> `initialize_postgres_display_storage` | no pesado hoy | bajo | historico muestra fallback visual | produccion | 200 | 40-110 ms | ~1596-1646 B | muchos `snapshot_status=missing` | WARNING | quitar DDL/init de `get_snapshot`; completar snapshots |
| M024 | backend-api | `backend/app/routes.py` | snapshot monthly leaderboard | GET | `/api/historical/snapshots/monthly-leaderboard` | `limit`, `server`, `metric` | `/api/historical/snapshots/monthly-leaderboard?server=comunidad-hispana-02&metric=kills&limit=10` | `build_monthly_leaderboard_snapshot_payload` | displayed snapshots | snapshot | si en Postgres display | no pesado hoy | bajo | n/a | produccion | 200 | 41-116 ms | ~1612 B | snapshot missing/fallback | WARNING | completar snapshots y read-only |
| M025 | backend-api | `backend/app/routes.py` | snapshot monthly MVP | GET | `/api/historical/snapshots/monthly-mvp` | `limit`, `server` | `/api/historical/snapshots/monthly-mvp?server=all-servers&limit=10` | `build_monthly_mvp_snapshot_payload` | displayed snapshots | snapshot | si en Postgres display | no pesado hoy | bajo | n/a | produccion | 200 | 42-78 ms | 1506 B | snapshot missing/fallback | WARNING | completar snapshots |
| M026 | backend-api | `backend/app/routes.py` | snapshot monthly MVP V2 | GET | `/api/historical/snapshots/monthly-mvp-v2` | `limit`, `server` | `/api/historical/snapshots/monthly-mvp-v2?server=all-servers&limit=10` | `build_monthly_mvp_v2_snapshot_payload` | displayed snapshots | snapshot | si en Postgres display | no pesado hoy | bajo | n/a | produccion | 200 | 40-41 ms | 1539 B | snapshot missing/fallback | WARNING | completar snapshots |
| M027 | backend-api | `backend/app/routes.py` | snapshot player events | GET | `/api/historical/snapshots/player-events` | `limit`, `server`, `view` | `/api/historical/snapshots/player-events?server=all-servers&view=duels&limit=10` | `build_player_event_snapshot_payload` | displayed snapshots | snapshot | si en Postgres display | no pesado hoy | bajo | n/a | produccion | 200 | 40-57 ms | ~1176-1188 B | snapshot missing/fallback | WARNING | completar snapshots |
| M028 | backend-api | `backend/app/routes.py` | snapshot weekly leaderboard | GET | `/api/historical/snapshots/weekly-leaderboard` | `limit`, `server`, `metric` | `/api/historical/snapshots/weekly-leaderboard?server=comunidad-hispana-01&metric=kills&limit=10` | `build_weekly_leaderboard_snapshot_payload` | displayed snapshots | snapshot | si en Postgres display | no pesado hoy | bajo | n/a | produccion | 200 | 44-70 ms | ~1610 B | snapshot missing/fallback | WARNING | completar snapshots |
| M029 | backend-api | `backend/app/routes.py` | historico recent matches legacy | GET | `/api/historical/recent-matches` | `limit`, `server` | `/api/historical/recent-matches?server=all-servers&limit=20` | `build_recent_historical_matches_payload` | RCON read model + scoreboard merge | read-model/legacy merge | posible init en fallback storage | si | medio | n/a | produccion | 200 | 278.44-1286.47 ms | ~24885 B | OK pero mas lento que snapshot | OK | preferir snapshot en frontend |
| M030 | backend-api | `backend/app/routes.py` | historico recent snapshot | GET | `/api/historical/snapshots/recent-matches` | `limit`, `server` | `/api/historical/snapshots/recent-matches?server=all-servers&limit=20` | `build_recent_historical_matches_snapshot_payload` | displayed snapshots | snapshot | si en Postgres display | no | bajo | historico handles error | produccion | 200 | 48-82 ms | ~24185 B | OK | OK | mantener, quitar init display despues |
| M031 | backend-api | `backend/app/routes.py` | historico match detail | GET | `/api/historical/matches/detail` | `server`, `match` | `/api/historical/matches/detail?server=comunidad-hispana-01&match=comunidad-hispana-01:1781023156:1781028555:purpleheartlanewarfare` | `build_historical_match_detail_payload` | RCON materialized detail; scoreboard fallback | materialized/read-model + fallback legacy | si: `get_materialized_rcon_match_detail` -> `initialize_rcon_materialized_storage` -> `initialize_postgres_rcon_storage`; fallback display init | si | medio | historico-partida muestra error, sin timeout | produccion | 200 | 120.47 ms | 125580 B | hoy OK, deuda de init persiste | OK | hardening posterior read-only estricto |
| M032 | backend-api | `backend/app/routes.py` | historico server summary legacy | GET | `/api/historical/server-summary` | `server` | `/api/historical/server-summary?server=all-servers` | `build_historical_server_summary_payload` | RCON read model | read-model/fallback | posible init en fallback storage | si | bajo | n/a | produccion | 200 | 95.82-145.29 ms | ~2480 B | OK | OK | mantener |
| M033 | backend-api | `backend/app/routes.py` | historico server summary snapshot | GET | `/api/historical/snapshots/server-summary` | `server` | `/api/historical/snapshots/server-summary?server=all-servers` | `build_historical_server_summary_snapshot_payload` | displayed snapshots | snapshot | si en Postgres display | no | bajo | historico handles missing | produccion | 200 | 50.03-62.60 ms | ~1042 B | `fallback_used=true` | WARNING | completar snapshot/read-only |
| M034 | backend-api | `backend/app/routes.py` | historical player profile | GET | `/api/historical/player-profile` | `player` | `/api/historical/player-profile?player=76561198092154180` | `build_historical_player_profile_payload` | legacy historical profile | legacy | si en Postgres display/historical fallback | si | medio | n/a | manual produccion | 200 | 4736.64 ms | no capturado | fallback true | WARNING | no cargar de inicio; optimizar si se mantiene publico |
| M035 | backend-api | `backend/app/routes.py` | Elo/MMR leaderboard | GET | `/api/historical/elo-mmr/leaderboard` | `limit`, `server` | `/api/historical/elo-mmr/leaderboard?server=all-servers&limit=10` | `build_elo_mmr_leaderboard_payload` | Elo/MMR storage | legacy/paused | posible `initialize_elo_mmr_storage` si engine carga | si | bajo | no usado por frontend actual | produccion | 200 | 58.35 ms | 2257 B | fallback/paused | WARNING | no reactivar; mantener fuera de UI |
| M036 | backend-api | `backend/app/routes.py` | Elo/MMR player | GET | `/api/historical/elo-mmr/player` | `player`, `server` | `/api/historical/elo-mmr/player?server=all-servers&player=76561198092154180` | `build_elo_mmr_player_payload` | Elo/MMR storage | legacy/paused | posible `initialize_elo_mmr_storage` si engine carga | si | bajo | no usado por frontend actual | manual produccion | 200 | 46.87 ms | no capturado | fallback true | WARNING | no reactivar; mantener fuera de UI |
| M037 | frontend-fetch | `frontend/assets/js/main.js` | `index.html` | GET | `/health` | ninguno | `${backendBaseUrl}/health` | backend B001 | config status | directo | no | no | bajo | usa `try/catch`; no bloquea pagina completa | codigo + produccion | 200 | 210.37 ms | 264 B | usado para estado backend | OK | mantener |
| M038 | frontend-fetch | `frontend/assets/js/main.js` | `index.html` | GET | `/api/trailer` | ninguno | `${backendBaseUrl}/api/trailer` | backend B003 | estatico | directo | no | no | bajo | error controlado | codigo + produccion | 200 | 33.08 ms | 139 B | OK | OK | mantener |
| M039 | frontend-fetch | `frontend/assets/js/main.js` | `index.html` | GET | `/api/servers` | ninguno | `${backendBaseUrl}/api/servers` | backend B005 | snapshots/live | RCON refresh posible | no DDL, si red live | si | medio | fallback visual; `Promise.allSettled` | codigo + produccion | 200 | 4311.38 ms | 1751 B | puede ralentizar landing | WARNING | no refrescar live en request publica |
| M040 | frontend-fetch | `frontend/assets/js/historico.js` | `historico.html` | GET | `/api/historical/snapshots/server-summary` | `server` | `/api/historical/snapshots/server-summary?server=comunidad-hispana-01` | backend B033 | snapshot | snapshot | si display init | no | bajo | requestId/cache/error | codigo + produccion | 200 | 50-63 ms | ~1042 B | snapshot missing/fallback | WARNING | completar snapshot y read-only |
| M041 | frontend-fetch | `frontend/assets/js/historico.js` | `historico.html` | GET | `/api/historical/snapshots/recent-matches` | `server`, `limit` | `/api/historical/snapshots/recent-matches?server=comunidad-hispana-01&limit=20` | backend B030 | snapshot | snapshot | si display init | no | bajo | requestId/cache/error | codigo + produccion | 200 | 48-82 ms | ~24 KB | OK | OK | mantener |
| M042 | frontend-fetch | `frontend/assets/js/historico.js` | `historico.html` | GET | `/api/historical/snapshots/leaderboard` | `server`, `timeframe`, `metric`, `limit` | `/api/historical/snapshots/leaderboard?server=comunidad-hispana-01&timeframe=weekly&metric=kills&limit=10` | backend B023 | snapshot | snapshot | si display init | no | bajo | requestId/cache/error | codigo + produccion | 200 | 40-110 ms | ~1.6 KB | snapshot missing/fallback | WARNING | completar snapshots |
| M043 | frontend-fetch | `frontend/assets/js/historico-recent-live.js` | `historico.html` | GET | `/api/historical/snapshots/recent-matches` | `server`, `limit` | `/api/historical/snapshots/recent-matches?server=comunidad-hispana-02&limit=20` | backend B030 | snapshot | snapshot | si display init | no | bajo | `try/catch`; cache no-store | codigo + produccion | 200 | 48-82 ms | ~24 KB | duplicable con historico.js | OK | revisar si ambos scripts piden lo mismo |
| M044 | frontend-fetch | `frontend/assets/js/historico-partida.js` | `historico-partida.html` | GET | `/api/historical/matches/detail` | `server`, `match` | `/api/historical/matches/detail?server=...&match=...` | backend B031 | materialized/fallback | materialized RCON | si | si | medio | error visual; sin timeout/abort | codigo + produccion | 200 | 120.47 ms | 125580 B | fallback localhost corregido previamente | OK | hardening read-only despues |
| M045 | frontend-fetch | `frontend/assets/js/partida-actual.js` | `partida-actual.html` | GET | `/api/current-match` | `server` | `/api/current-match?server=comunidad-hispana-01` | backend B012 | RCON live | directo RCON | no | si | medio | in-flight guard; sin timeout | codigo + produccion | 200 | 1242-2155 ms | ~820 B | polling | OK | mover a snapshot |
| M046 | frontend-fetch | `frontend/assets/js/partida-actual.js` | `partida-actual.html` | GET | `/api/current-match/kills` | `server`, `limit`, `since_event_id` | `/api/current-match/kills?server=comunidad-hispana-01&limit=30` | backend B013 | AdminLog | materialized | si | desconocido | alto | in-flight guard; sin timeout | codigo + produccion | timeout/500 | 6269-30025 ms | 0-58 B | polling frecuente | CRITICAL | corregir backend y agregar timeout frontend |
| M047 | frontend-fetch | `frontend/assets/js/partida-actual.js` | `partida-actual.html` | GET | `/api/current-match/players` | `server` | `/api/current-match/players?server=comunidad-hispana-01` | backend B014 | AdminLog | materialized | si | desconocido | alto | in-flight guard; sin timeout | codigo + produccion | timeout/200 | 1090-30097 ms | 0-72 KB | polling frecuente | CRITICAL | corregir backend y agregar timeout frontend |
| M048 | frontend-fetch | `frontend/assets/js/ranking.js` | `ranking.html` | GET | `/api/ranking` | `timeframe`, `server_id`, `metric`, `limit`, `year` | `/api/ranking?timeframe=weekly&server_id=all&metric=kills&limit=100` | backend B011 | ranking snapshots | snapshot | no en fast path | no | bajo | AbortController + requestId + error | codigo + produccion | 200 | 31-130 ms | variable | OK | OK | mantener |
| M049 | frontend-fetch | `frontend/assets/js/stats.js` | `stats.html` | GET | `/health` | ninguno | `${backendBaseUrl}/health` | backend B001 | config status | directo | no | no | bajo | error controlado | codigo + produccion | 200 | 210 ms | 264 B | OK | OK | mantener |
| M050 | frontend-fetch | `frontend/assets/js/stats.js` | `stats.html` | GET | `/api/stats/players/search` | `q`, opcional `server_id`, `limit` | `/api/stats/players/search?q=Medu&server_id=all&limit=10` | backend B009 | player read model | read-model/fallback | si | si | alto | sin abort/timeout; loading puede durar mucho | codigo + produccion | timeout | 30019 ms | 0 B | CRITICAL | CRITICAL | primer fix |
| M051 | frontend-fetch | `frontend/assets/js/stats.js` | `stats.html` | GET | `/api/stats/rankings/annual` | `year`, `metric`, `server_id`, `limit` | `/api/stats/rankings/annual?year=2026&metric=kills&server_id=all&limit=10` | backend B010 | annual snapshot | snapshot | no | no | bajo | error controlado | codigo + produccion | 200 | 60 ms | 5236 B | OK | OK | mantener |
| M052 | frontend-fetch | `frontend/assets/js/stats.js` | `stats.html` | GET | `/api/stats/players/{player_id}` | `player_id`, `timeframe`, `server_id` | `/api/stats/players/76561198092154180?timeframe=weekly&server_id=all` | backend B015 | player period stats | read-model/fallback | si | si | alto | sin abort/timeout; puede quedarse cargando hasta timeout navegador | codigo + manual produccion | timeout | 30046-30094 ms | 0 B | CRITICAL | CRITICAL | primer fix |
| M053 | static-asset | `frontend/*.html`, `frontend/assets/css`, `frontend/assets/js` | paginas publicas | GET | assets estaticos | path estatico | `/assets/js/ranking.js` | servidor estatico | filesystem/web server | n/a | no | no | bajo | navegador gestiona error de asset | no medida HTTP individual | n/a | n/a | n/a | no se tocaron assets | OK | mantener cache headers fuera de esta task |
| M054 | static-asset | `frontend/assets/img/**` | imagenes publicas | GET | assets imagen | path estatico | `/assets/img/...` | servidor estatico | filesystem/web server | n/a | no | no | bajo | navegador gestiona error de asset | no medida HTTP individual | n/a | n/a | n/a | no se tocaron imagenes, SVGs, weapons ni clans | OK | sin cambios |
| M055 | internal-runner | `backend/app/historical_runner.py` | worker historico | n/a | no publico | args CLI/env | n/a | runner | RCON/public scoreboard/storage | ingestion/fallback | si, por diseno de worker | si | n/a | n/a | lectura estatica | n/a | n/a | n/a | fuera de superficie publica | OK | no mezclar con fixes publicos |
| M056 | internal-runner | `backend/app/historical_ingestion.py` | ingestion historica | n/a | no publico | args CLI/env | n/a | runner | public scoreboard/RCON | ingestion/fallback | si, por diseno de worker | si | n/a | n/a | lectura estatica | n/a | n/a | n/a | fuera de superficie publica | OK | no ejecutar desde request publica |
| M057 | internal-runner | `backend/app/database_maintenance.py` | mantenimiento DB | n/a | no publico | args CLI/env | n/a | runner | DB | maintenance | si, por diseno de worker | n/a | n/a | n/a | lectura estatica | n/a | n/a | n/a | fuera de superficie publica | OK | mantener separado de GET |
| M058 | internal-runner | `scripts/audit_public_requests.py` | auditoria publica | GET | endpoints publicos | `--base-url`, `--timeout` | produccion/local | script stdlib | HTTP publico | n/a | no modifica app | no | configurable | n/a | ejecutado | 191 probes | ver JSON | ver JSON | artefacto de auditoria | OK | usar antes/despues de fixes |

## Endpoints OK

| Endpoint/familia | Evidencia |
| --- | --- |
| `/health`, `/api/community`, `/api/trailer`, `/api/discord` | 200, menos de 211 ms |
| `/api/servers/latest`, `/api/servers/history`, `/api/servers/{id}/history` | 200, 40-78 ms |
| `/api/ranking` semanal/mensual/anual, metricas `kills`, `deaths`, `teamkills`, `matches_considered`, `kd_ratio`, `kills_per_match`, scopes `all`, `comunidad-hispana-01`, `comunidad-hispana-02` | 55 probes OK, 31-130 ms |
| `/api/stats/rankings/annual` | 200, 60.07 ms |
| `/api/current-match` | 200, 1.2-2.2 s; OK funcional, riesgo arquitectonico por RCON directo |
| `/api/historical/recent-matches` | 200, 278-1286 ms |
| `/api/historical/snapshots/recent-matches` | 200, 48-82 ms |
| `/api/historical/matches/detail` con match conocido | 200, 120.47 ms |
| `/api/historical/server-summary` | 200, 95-145 ms |

## Endpoints WARNING

| Endpoint/familia | Motivo |
| --- | --- |
| `/api/servers` | 200 pero 4311.38 ms y `source=real-time-rcon-refresh`: red live durante lectura publica |
| `/api/historical/weekly-top-kills` | `fallback_used=true` |
| `/api/historical/leaderboard`, `/weekly-leaderboard`, `/monthly-leaderboard` | `fallback_used=true` y legacy fallback |
| `/api/historical/monthly-mvp`, `/monthly-mvp-v2` | `fallback_used=true` |
| `/api/historical/player-events` | `fallback_used=true` |
| `/api/historical/snapshots/*` salvo recent-matches | `snapshot_status=missing` frecuente, `fallback_used=true` |
| `/api/historical/player-profile` | 200 pero 4736.64 ms manual y fallback |
| `/api/historical/elo-mmr/*` | endpoints expuestos pero fallback/pausados; no reactivar ni poner en UI |
| frontend `data-backend-base-url`/fallback local | 13 referencias a localhost/127.0.0.1 en HTML/JS publico; `config.js` mitiga en produccion pero el residuo existe |

## Endpoints CRITICAL

| Endpoint | Evidencia | Recomendacion |
| --- | --- | --- |
| `/api/stats/players/search?q=Medu&server_id=all&limit=10` | timeout 30019.46 ms | read-only estricto del player search index; no inicializar storage ni fallback runtime en request publica |
| `/api/stats/players/{player_id}?timeframe=weekly&server_id=all` | timeout 30094.15 ms | igual que search; revisar `player_period_stats` |
| `/api/stats/players/{player_id}?timeframe=monthly&server_id=all` | timeout 30046.21 ms | igual que search; revisar `player_period_stats` |
| `/api/current-match/kills?server=comunidad-hispana-01&limit=30` | timeout 30024.86 ms | quitar init de AdminLog en lectura; revisar indices/query |
| `/api/current-match/players?server=comunidad-hispana-01` | timeout 30096.62 ms | quitar init de AdminLog en lectura; revisar ventana actual e indices |
| `/api/current-match/kills?server=comunidad-hispana-02&limit=30` | 500 en 6268.78 ms; repeticion manual hizo timeout | capturar error backend y estabilizar query |

## Inicializacion en lectura publica

Rutas donde una peticion publica puede acabar ejecutando inicializacion, DDL o bootstrap de storage:

| Ruta publica | Cadena | Tiempo observado/potencial | Estado | Recomendacion |
| --- | --- | --- | --- | --- |
| `/api/historical/matches/detail` | `build_historical_match_detail_payload` -> `get_rcon_historical_match_detail` -> `get_materialized_rcon_match_detail` -> `initialize_rcon_materialized_storage` -> `initialize_postgres_rcon_storage` | historico reciente midio 14s antes; esta auditoria 120 ms para match conocido | funcional pero no limpio | mantener como fix posterior: conexion read-only sin init y fallback estricto |
| `/api/stats/players/search` | `build_stats_player_search_payload` -> `search_rcon_materialized_players` -> `_search_player_search_index` -> `initialize_player_search_index_storage` -> `initialize_rcon_materialized_storage` -> `initialize_postgres_rcon_storage`; fallback `_search_rcon_materialized_players_runtime` | 30s timeout | CRITICAL | primer fix |
| `/api/stats/players/{player_id}` | `build_stats_player_profile_payload` -> `get_rcon_materialized_player_stats` -> `_get_player_period_stats_read_model` -> `initialize_player_period_stats_storage` -> `initialize_rcon_materialized_storage` -> `initialize_postgres_rcon_storage`; fallback runtime | 30s timeout | CRITICAL | primer fix junto a search |
| `/api/current-match/kills` | `build_current_match_kill_feed_payload` -> `list_current_match_kill_feed` -> `initialize_rcon_admin_log_storage` -> `initialize_postgres_rcon_storage` | 30s timeout / 500 | CRITICAL | segundo fix |
| `/api/current-match/players` | `build_current_match_player_stats_payload` -> `list_current_match_player_stats` -> `initialize_rcon_admin_log_storage` -> `initialize_postgres_rcon_storage` | 30s timeout en CH01 | CRITICAL | segundo fix |
| `/api/historical/snapshots/*` | snapshot builder -> `get_historical_snapshot` -> Postgres `get_snapshot` -> `initialize_postgres_display_storage` | rapido hoy, 40-116 ms | WARNING | read-only snapshot connection |
| legacy `/api/historical/*` | payloads -> `historical_storage` -> Postgres display fallback functions | rapido hoy salvo player-profile 4.7s | WARNING | snapshot-only o legacy explicit |
| `/api/ranking` | weekly/monthly fast path uses read-only snapshot connection; `initialize_ranking_snapshot_storage` solo deberia ocurrir en generation/fallback. Runtime fallback existe por env | 31-130 ms | OK con condicion | mantener fallback runtime apagado en publico |
| annual ranking | `get_annual_ranking_snapshot` usa read connection | 31-88 ms | OK | mantener |

## Fallbacks pesados detectados

| Endpoint | Fallback | Activacion | Coste estimado | Lo muestra frontend | Recomendacion |
| --- | --- | --- | --- | --- | --- |
| `/api/stats/players/search` | runtime search en `rcon_match_player_stats` | indice vacio/no disponible/error | alto, timeout 30s | no claramente | eliminar fallback runtime en publico o devolver estado `snapshot_missing` rapido |
| `/api/stats/players/{player_id}` | runtime player stats desde materialized matches | `player_period_stats` vacio/no disponible | alto, timeout 30s | no claramente | eliminar fallback runtime publico |
| `/api/current-match/kills/players` | AdminLog init + queries sobre ventana actual | siempre entra por helper actual | alto en CH01 | UI queda esperando | read-only + indices; respuesta vacia rapida si no hay ventana |
| `/api/servers` | RCON live refresh y A2S fallback si snapshots stale | snapshots ausentes/stale | medio, 4.3s medido | no como fallback tecnico | snapshot estricto en publico; refresh asincrono |
| `/api/historical/recent-matches` | merge con public-scoreboard persisted fallback | RCON insuficiente | medio, 1.3s max | no | frontend ya debe preferir snapshot |
| legacy `/api/historical/*` | public-scoreboard/display fallback | RCON no soporta o snapshot missing | bajo hoy pero acoplado | parcialmente por metadata | deprecar o snapshot-only |
| `/api/historical/matches/detail` | public-scoreboard detail fallback | RCON detail no encontrado | potencial alto si display init se repite | no destacado | fallback estricto y rapido |

## Auditoria frontend

Paginas publicas revisadas:

- `frontend/index.html`
- `frontend/historico.html`
- `frontend/historico-partida.html`
- `frontend/partida-actual.html`
- `frontend/ranking.html`
- `frontend/stats.html`

Scripts publicos revisados:

- `frontend/assets/js/config.js`
- `frontend/assets/js/main.js`
- `frontend/assets/js/historico.js`
- `frontend/assets/js/historico-recent-live.js`
- `frontend/assets/js/historico-partida.js`
- `frontend/assets/js/partida-actual.js`
- `frontend/assets/js/ranking.js`
- `frontend/assets/js/stats.js`

Hallazgos frontend:

| Pagina | Fetchs | Loading/error | Timeout/abort/requestId | Riesgo |
| --- | --- | --- | --- | --- |
| `index.html` | `/health`, `/api/trailer`, `/api/servers` | error controlado; no bloquea todo por `Promise.allSettled` | sin timeout | WARNING por `/api/servers` lento |
| `historico.html` | snapshots server-summary/recent/leaderboard y recent-live | requestId/cache/error visual | requestId; sin timeout generico | WARNING por snapshots missing/fallback |
| `historico-partida.html` | `/api/historical/matches/detail` | error visual si falla | sin timeout/abort | OK hoy, deuda si endpoint vuelve lento |
| `partida-actual.html` | current match, kills, players | in-flight guards; no abort | sin timeout; polling frecuente | CRITICAL por endpoints kills/players |
| `ranking.html` | `/api/ranking` | loading/error correcto | AbortController + requestId | OK |
| `stats.html` | `/health`, player search, annual ranking, player profile | errores visibles pero search/profile pueden esperar demasiado | sin AbortController/requestId robusto para search/profile; sin timeout | CRITICAL por search/profile |

Referencias localhost/127.0.0.1 en frontend publico:

- `frontend/assets/js/config.js`: default dev backend y deteccion localhost.
- `frontend/assets/js/historico-recent-live.js`
- `frontend/assets/js/historico.js`
- `frontend/assets/js/main.js`
- `frontend/assets/js/partida-actual.js`
- `frontend/assets/js/ranking.js`
- `frontend/assets/js/stats.js`
- `frontend/historico.html`
- `frontend/index.html`
- `frontend/partida-actual.html`
- `frontend/ranking.html`
- `frontend/stats.html`

`frontend/historico-partida.html` ya no conserva `data-backend-base-url` local. La mitigacion en `config.js` evita que un host no local use el default dev, pero la deuda sigue existiendo porque hay HTML/JS publico con fallback local.

## Top 10 riesgos actuales

1. `/api/stats/players/search` hace inicializacion/read-model/fallback runtime en lectura publica y vence a 30s.
2. `/api/stats/players/{player_id}` hace inicializacion/read-model/fallback runtime en lectura publica y vence a 30s.
3. `/api/current-match/kills` vence a 30s o devuelve 500 segun servidor.
4. `/api/current-match/players` vence a 30s en `comunidad-hispana-01`.
5. `/api/servers` puede hacer refresh RCON en request publica y tarda 4.3s.
6. `get_snapshot` de snapshots historicos ejecuta `initialize_postgres_display_storage` en lectura.
7. Muchos snapshots historicos estan `missing`, generando `fallback_used=true` en 75+ probes.
8. Hay residuos de fallback `127.0.0.1`/`localhost` en HTML/JS publico.
9. `stats.js`, `partida-actual.js` e `historico-partida.js` no tienen timeout HTTP propio.
10. Endpoints legacy historicos siguen expuestos con fallback dinamico aunque el frontend ya usa snapshots para lo principal.

## Top 10 recomendaciones priorizadas

1. Crear task backend para `/api/stats/players/search` y `/api/stats/players/{player_id}`: read-only estricto, sin `initialize_*` ni fallback runtime en GET publico.
2. Crear task backend para `/api/current-match/kills` y `/api/current-match/players`: quitar init de AdminLog en lectura, revisar indices y devolver payload vacio rapido si no hay ventana actual.
3. Crear task backend para `/api/servers`: no hacer refresh RCON/A2S desde GET publico; responder snapshot y dejar refresh a worker.
4. Crear task frontend para `stats.js`: AbortController/requestId/timeout y estado de error rapido para search/profile.
5. Crear task frontend para `partida-actual.js`: timeout/abort por request y backoff si kills/players fallan.
6. Crear task backend para `historical_snapshot_storage`/`postgres_display_storage.get_snapshot`: conexion read-only sin DDL/init en lectura.
7. Crear task de generacion/validacion snapshots historicos faltantes: reducir `snapshot_status=missing`.
8. Crear task de limpieza de fallbacks locales en frontend publico, manteniendo soporte dev explicito sin contaminar produccion.
9. Crear task backend para hardening de `/api/historical/matches/detail`: read-only estricto y fallback rapido aunque hoy responda OK.
10. Crear task de deprecacion/control de endpoints legacy `/api/historical/*` no usados por frontend o exponerlos solo como legacy con limites claros.

## Fixes propuestos como tasks pequenas

1. `TASK-225-stats-player-read-model-public-fast-path`: `/api/stats/players/search` y `/api/stats/players/{player_id}` sin inicializacion ni fallback runtime en lectura publica.
2. `TASK-226-current-match-adminlog-public-fast-path`: `/api/current-match/kills` y `/api/current-match/players` read-only, indices y errores controlados.
3. `TASK-227-servers-public-snapshot-only`: `/api/servers` no refresca RCON/A2S durante request publica.
4. `TASK-228-frontend-stats-request-timeouts`: timeout/abort/requestId para `stats.js`.
5. `TASK-229-frontend-current-match-request-timeouts`: timeout/backoff para `partida-actual.js`.
6. `TASK-230-historical-snapshot-storage-read-only`: quitar `initialize_postgres_display_storage` del path de lectura de snapshots.
7. `TASK-231-historical-snapshot-coverage-refresh`: completar snapshots faltantes usados por `historico.html`.
8. `TASK-232-frontend-public-backend-url-hardening`: eliminar fallbacks locales de HTML/JS publico de produccion.
9. `TASK-233-historical-match-detail-read-only-hardening`: hardening de `/api/historical/matches/detail`.
10. `TASK-234-legacy-historical-endpoint-policy`: inventario/limites/deprecacion de legacy endpoints publicos.

## Comandos de auditoria

Desde host contra produccion:

```powershell
python scripts\audit_public_requests.py --base-url https://comunidadhll.devzamode.es --timeout 30 --output tmp\public_request_audit.json
```

Desde host contra backend local:

```powershell
python scripts\audit_public_requests.py --base-url http://127.0.0.1:8000 --timeout 30 --output tmp\public_request_audit.json
```

Dentro del contenedor backend desde PowerShell, sin copiar archivos al contenedor:

```powershell
Get-Content scripts\audit_public_requests.py | docker compose exec -T backend python - --base-url http://127.0.0.1:8000 --timeout 30 --output /app/data/public_request_audit.json
```

Equivalente shell:

```bash
cat scripts/audit_public_requests.py | docker compose exec -T backend python - --base-url http://127.0.0.1:8000 --timeout 30 --output /app/data/public_request_audit.json
```

Compilacion del script:

```powershell
python -m py_compile scripts\audit_public_requests.py
```

## Notas de alcance

- No se ejecuto `ai-platform run`.
- No se hizo commit.
- No se hizo push.
- No se aplicaron fixes funcionales.
- No se modifico logica productiva backend ni frontend.
- No se tocaron assets, SVGs, imagenes fisicas, `frontend/assets/img/weapons/`, `frontend/assets/img/clans/` ni `ai/system-metrics.md`.
- No se reactivo Elo/MMR.
- No se agrego ningun servidor nuevo.
