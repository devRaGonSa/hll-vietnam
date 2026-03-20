# TASK-029-historical-stats-ingestion-bootstrap

## Goal
Preparar una base de ingesta histórica para los 2 servidores de la comunidad a partir de sus páginas de scoreboard, persistiendo datos suficientes para alimentar rankings semanales posteriores.

## Context
Ya se ha definido o se va a definir el modelo histórico base. El siguiente paso técnico es arrancar la ingesta real desde las páginas de scoreboard de ambos servidores, guardando datos históricos estructurados de forma incremental y reutilizable.

## Steps
1. Revisar el modelo de dominio/documentación histórica ya definida.
2. Implementar una base mínima de ingesta para los 2 scoreboards reales de la comunidad.
3. Extraer y persistir, como mínimo, datos suficientes sobre:
   - servidor
   - partida
   - fecha/hora
   - mapa
   - jugador
   - kills
   - otras métricas disponibles que puedan ser útiles y estables
4. Diseñar la ingesta para poder ejecutarse varias veces sin duplicar datos.
5. Mantener la solución preparada para refresco incremental futuro.
6. Documentar cómo ejecutar la ingesta localmente.
7. No implementar todavía dashboards o UI histórica.
8. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- docs/historical-stats-domain-model.md
- backend/README.md
- backend/app/config.py
- cualquier almacenamiento o capa de persistencia ya existente
- cualquier módulo collector existente
- las URLs reales de scoreboard de ambos servidores

## Expected Files to Modify
- backend/app/config.py
- backend/README.md
- uno o varios archivos nuevos de backend para ingesta histórica, por ejemplo:
  - backend/app/historical_ingestion.py
  - backend/app/historical_storage.py
  - backend/app/historical_parsers.py
- opcionalmente archivos de datos o esquema local si la implementación lo requiere

## Constraints
- No romper el flujo actual de estado en tiempo real.
- No añadir UI histórica en esta task.
- No introducir complejidad innecesaria.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en ingesta, persistencia e idempotencia.

## Validation
- Existe una ingesta histórica mínima para ambos servidores.
- La ingesta persiste datos estructurados.
- La ingesta puede reejecutarse sin duplicación grave.
- La documentación explica cómo ejecutarla localmente.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 8 archivos modificados o creados.
- Preferir menos de 320 líneas cambiadas.

## Outcome
- `backend/app/historical_ingestion.py` implementa una ingesta mínima sobre los 2 scoreboards reales usando `GET /api/get_public_info` y `GET /api/get_live_game_stats`.
- `backend/app/historical_storage.py` añade persistencia idempotente en SQLite para partidas, jugadores y estadísticas por jugador en partida.
- `backend/app/config.py` centraliza las dos fuentes reales de scoreboard.
- `backend/README.md` documenta cómo ejecutar la ingesta localmente y qué tablas/payloads alimenta.

## Validation Result
- Ejecutado desde `backend/`: `python -m app.historical_ingestion`.
- Resultado: `capture_count: 2`, sin errores, con persistencia para `comunidad-hispana-01` y `comunidad-hispana-02`.
- Revisada la SQLite local `backend/data/hll_vietnam_dev.sqlite3`.
- Resultado: existen filas en `historical_matches`, `historical_players` y `historical_player_match_stats`.
- Reejecutada la ingesta tras un ajuste menor de sanitización temporal.
- Resultado: los upserts mantienen idempotencia básica y `time_seconds` queda no negativo en persistencia.

## Decision Notes
- Se usa la API JSON real descubierta detrás del scoreboard en lugar de hacer scraping de la shell SPA.
- La identidad de partida se basa en `server + start timestamp + map slug`, suficiente para la fase actual mientras no aparezca un `match id` público más fuerte.
