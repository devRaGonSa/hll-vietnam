# TASK-032-historical-data-quality-and-ranking-validation

## Goal
Validar la calidad del historico ingerido y la correccion del ranking semanal de kills para los 2 servidores reales de la comunidad, detectando y corrigiendo problemas de integridad, duplicados, naming o rango temporal antes de construir UI historica propia.

## Context
El proyecto ya dispone de:
- estado actual en vivo via A2S
- capa historica separada via CRCON scoreboard JSON
- persistencia historica propia
- ingesta historica funcional
- endpoint `GET /api/historical/weekly-top-kills`

Antes de exponer estos datos en una UI propia del proyecto, hay que asegurar que la base historica tiene calidad suficiente y que el ranking semanal devuelve resultados coherentes, consistentes y trazables.

## Steps
1. Revisar la implementacion actual de:
   - almacenamiento historico
   - ingesta historica
   - modelos historicos
   - endpoint `GET /api/historical/weekly-top-kills`
2. Verificar la calidad de los datos historicos persistidos para ambos servidores. Comprobar al menos:
   - numero de partidas ingeridas
   - numero de jugadores ingeridos
   - presencia de datos relevantes por partida
   - distribucion por servidor
3. Detectar posibles duplicados o inconsistencias en:
   - partidas
   - jugadores
   - estadisticas por jugador y partida
4. Revisar la estrategia actual de identidad y deduplicacion:
   - ids de partida
   - ids de jugador o claves degradadas
   - relacion entre servidor y match
5. Validar que el calculo de "ultima semana" usado por el ranking sea correcto y consistente.
6. Validar que el ranking de kills:
   - sume correctamente kills por jugador
   - no mezcle datos entre servidores
   - no use partidas fuera del rango temporal esperado
   - no devuelva duplicados de jugador por mala consolidacion
7. Revisar si los nombres de jugador y nombres de mapa se almacenan y devuelven de forma suficientemente limpia.
8. Si se detectan problemas, corregir unicamente lo necesario en:
   - almacenamiento
   - consultas
   - normalizacion
   - endpoint historico
9. Anadir validaciones o utilidades minimas si ayudan a reforzar la fiabilidad del historico.
10. Documentar brevemente los hallazgos y el estado final de calidad historica.
11. No crear todavia paginas o bloques UI historicos.
12. Al completar la implementacion:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- docs/decisions.md
- docs/historical-crcon-source-discovery.md
- docs/historical-domain-model.md
- backend/README.md
- backend/app/historical_models.py
- backend/app/historical_storage.py
- backend/app/historical_ingestion.py
- backend/app/routes.py
- backend/app/payloads.py
- cualquier consulta o helper historico adicional ya creado

## Expected Files to Modify
- backend/README.md
- backend/app/historical_storage.py
- backend/app/historical_ingestion.py
- backend/app/routes.py
- backend/app/payloads.py
- opcionalmente nuevos modulos auxiliares si mejoran validacion o normalizacion, por ejemplo:
  - backend/app/historical_queries.py
  - backend/app/historical_validation.py
- opcionalmente un documento tecnico breve, por ejemplo:
  - docs/historical-data-quality-notes.md

## Constraints
- No crear todavia UI historica.
- No basar correcciones historicas en A2S.
- No acoplar el frontend a URLs de la comunidad.
- No introducir complejidad innecesaria.
- No romper el flujo actual de live status.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en calidad, consistencia y fiabilidad del historico.

## Validation
- Se ha revisado la calidad del historico para ambos servidores.
- Se han detectado y corregido, si existen, duplicados o inconsistencias relevantes.
- El endpoint `GET /api/historical/weekly-top-kills` devuelve resultados coherentes.
- El rango temporal de "ultima semana" queda validado.
- Los datos no se mezclan entre servidores.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 7 archivos modificados o creados.
- Preferir menos de 260 lineas cambiadas.

## Outcome
- Se corrigio la estrategia de identidad historica en `backend/app/historical_storage.py` para priorizar SteamID real y usar `player_id` como clave `crcon-player:*` cuando no existe SteamID.
- La inicializacion del storage ahora fusiona jugadores duplicados y partidas duplicadas persistidas con id sintetico frente a id CRCON final.
- El ranking `GET /api/historical/weekly-top-kills` paso a usar solo partidas cerradas con `ended_at`, evitando contar sesiones en curso o duplicadas.
- Se documentaron los hallazgos y el estado final en `docs/historical-data-quality-notes.md` y se alineo `backend/README.md`.

## Validation Result
- Validado con inicializacion real sobre `backend/data/hll_vietnam_dev.sqlite3`.
- Tras la correccion, el dataset local quedo en `12` partidas, `510` jugadores y `914` filas de estadisticas por jugador y partida.
- Comprobado que no quedan duplicados por `steam_id`, `source_player_id`, nombre normalizado ni por la combinacion `(servidor, started_at, mapa)`.
- Comprobado que ya no quedan partidas abiertas (`ended_at IS NULL`) en el dataset local actual.
- Validado con `list_weekly_top_kills()` para ambos servidores, confirmando separacion por servidor y uso exclusivo de partidas cerradas dentro de la ventana movil de 7 dias.

## Decision Notes
- `steaminfo.id` deja de tratarse como `steam_id` real porque en los datos observados funcionaba como identificador corto auxiliar y fragmentaba la identidad del jugador.
- Para resolver duplicados de partida se usa una heuristica conservadora por `(historical_server_id, started_at, mapa normalizado)`, priorizando la fila cerrada, numerica y con mas jugadores.
- No se eliminaron partidas con muy pocos jugadores porque eso es una decision de calidad de producto futura, no un problema de integridad estructural.
