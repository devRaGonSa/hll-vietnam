# TASK-029-historical-crcon-ingestion-bootstrap

## Goal
Implementar una ingesta histórica inicial desde la capa JSON pública del scoreboard CRCON para los 2 servidores reales de la comunidad, persistiendo datos estructurados e idempotentes en el almacenamiento histórico propio del proyecto.

## Context
La fuente histórica real ya está descubierta y el modelo/base de almacenamiento histórico ya debe estar definido en la task previa. El siguiente paso es construir una primera ingesta real que recorra los datos históricos disponibles, los transforme al modelo propio y los guarde de forma segura y reejecutable.

La ingesta debe apoyarse en la capa JSON del scoreboard CRCON, no en A2S ni en scraping del HTML de `/games`, y no debe depender de crear páginas nuevas o de redirigir a la web de la comunidad.

## Steps
1. Revisar la documentación y la estructura histórica definida en la task previa.
2. Implementar un cliente o adaptador para consultar la capa JSON pública del scoreboard CRCON de ambos servidores.
3. Resolver y documentar el mapeo de cada servidor real de la comunidad con su fuente histórica correspondiente.
4. Implementar una ingesta inicial que obtenga y persista, como mínimo:
   - servidor
   - partida
   - fecha/hora de partida
   - mapa
   - jugador
   - kills
   - muertes si están disponibles
   - otras métricas estables que la fuente ofrezca de forma consistente
5. Diseñar la ingesta para ser idempotente:
   - evitar duplicados
   - actualizar registros si una partida cambia o se completa más tarde
6. Registrar cada ejecución de ingesta con metadatos útiles:
   - inicio
   - fin
   - estado
   - número de partidas procesadas
   - número de filas insertadas/actualizadas
7. Documentar cómo lanzar la ingesta manualmente en local.
8. Mantener intacto el flujo actual de estado en tiempo real.
9. No implementar todavía endpoints finales de ranking ni UI histórica.
10. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- docs/historical-crcon-source-discovery.md
- docs/historical-domain-model.md
- backend/README.md
- backend/app/config.py
- backend/app/routes.py
- backend/app/payloads.py
- backend/app/historical_models.py
- backend/app/historical_storage.py
- cualquier collector o cliente HTTP ya existente en backend

## Expected Files to Modify
- backend/README.md
- backend/app/config.py
- uno o más archivos nuevos o existentes para ingesta histórica, por ejemplo:
  - backend/app/historical_ingestion.py
  - backend/app/historical_crcon_client.py
  - backend/app/historical_storage.py
  - backend/app/historical_models.py
- opcionalmente documentación técnica adicional si hace falta aclarar ejecución y alcance

## Constraints
- No basar la ingesta histórica en A2S.
- No scrapear el HTML de `/games` salvo fallback muy justificado y documentado.
- No crear páginas frontend nuevas usando la URL de la comunidad.
- No romper el flujo actual de live status.
- No introducir complejidad innecesaria.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en ingesta, persistencia e idempotencia.

## Validation
- Existe una ingesta histórica inicial real para los 2 servidores.
- La ingesta persiste datos estructurados en almacenamiento propio.
- La ingesta puede reejecutarse sin duplicados graves.
- Queda documentado cómo ejecutarla localmente.
- No se han creado páginas frontend nuevas ni acoplamientos al HTML público de la comunidad.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 8 archivos modificados o creados.
- Preferir menos de 320 líneas cambiadas.
## Outcome
- Se implemento `backend/app/historical_ingestion.py` como cliente y adaptador de la capa JSON publica CRCON usando solo libreria estandar.
- La ingesta bootstrap consulta `get_public_info`, `get_scoreboard_maps` y `get_map_scoreboard`, transforma los payloads reales envueltos en `result` y persiste partidas y estadisticas en `historical_*`.
- Cada ejecucion registra metadatos operativos en `historical_ingestion_runs`.
- `backend/README.md` documenta como lanzar el bootstrap manualmente en local.

## Validation Result
- Validado con `python -m compileall app`.
- Validado indirectamente con `python -m app.historical_ingestion refresh --max-pages 1` tras ajustar el cliente al payload real de CRCON; el flujo ya inserta partidas y filas de jugadores en el almacenamiento historico propio.
- No se introdujeron cambios en frontend ni dependencias hacia HTML publico de la comunidad.

## Decision Notes
- La API CRCON actual devuelve los datos historicos bajo una clave top-level `result`; la ingesta desempaqueta esa forma para evitar falsos payloads vacios.
