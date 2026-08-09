# TASK-028-historical-domain-model-and-storage-schema

## Goal
Definir e implementar la base de modelo de dominio y almacenamiento para estadísticas históricas de los 2 servidores reales de la comunidad, preparada para ingerir datos desde la capa JSON pública del scoreboard CRCON y para soportar rankings semanales posteriores.

## Context
La fase de discovery ya confirmó que la fuente histórica correcta para estos servidores no es A2S ni el HTML de `/games`, sino la capa JSON pública del scoreboard CRCON. El siguiente paso técnico es crear una base sólida de dominio y persistencia propia para poder ingerir datos históricos, deduplicarlos y consultarlos más adelante desde nuestra propia API.

Esta task NO debe crear todavía páginas históricas en frontend ni depender de URLs públicas de la comunidad como solución de producto. La capa histórica debe vivir en backend, con persistencia propia y preparada para exponer endpoints internos del proyecto en fases posteriores.

## Steps
1. Revisar la documentación de discovery histórica ya creada y confirmar qué datos están disponibles desde la capa JSON pública del scoreboard CRCON.
2. Definir el modelo de dominio histórico mínimo necesario. Incluir al menos:
   - servidor
   - partida
   - mapa
   - jugador
   - estadísticas de jugador por partida
   - ejecución de ingesta histórica
3. Diseñar el esquema de almacenamiento local inicial para esa información.
4. Definir claves e identidad estables para evitar duplicados. Incluir expresamente:
   - identificación de partida
   - identificación de servidor
   - identificación de jugador
   - estrategia de idempotencia
5. Incluir campos suficientes para soportar futuras consultas como:
   - top kills de la última semana por servidor
   - partidas recientes por servidor
   - mapas jugados
6. Implementar la base de almacenamiento/esquema local de forma coherente con el backend actual del proyecto.
7. Mantener clara la separación entre:
   - estado actual vía A2S
   - histórico persistido vía CRCON scoreboard JSON
8. Documentar la estructura creada y cómo se usará en las siguientes tasks.
9. No implementar todavía:
   - UI histórica
   - páginas nuevas basadas en la URL de la comunidad
   - redirecciones o vistas que repliquen la web de la comunidad
   - rankings finales expuestos al frontend
10. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- docs/decisions.md
- docs/historical-crcon-source-discovery.md
- backend/README.md
- backend/app/config.py
- backend/app/routes.py
- backend/app/payloads.py
- cualquier almacenamiento local o capa de persistencia ya existente en `backend/`
- cualquier módulo collector o snapshot ya existente que pueda influir en la estructura de datos

## Expected Files to Modify
- ai/architecture-index.md
- docs/decisions.md
- backend/README.md
- uno o más archivos nuevos de backend para almacenamiento histórico, por ejemplo:
  - backend/app/historical_models.py
  - backend/app/historical_storage.py
  - backend/app/historical_schema.py
- opcionalmente un documento nuevo, por ejemplo:
  - docs/historical-domain-model.md

## Constraints
- No basar esta capa histórica en A2S.
- No crear páginas frontend nuevas usando la URL de la comunidad.
- No incrustar ni replicar directamente páginas de `scoreboard.comunidadhll.es`.
- No implementar todavía ingesta completa ni UI histórica.
- No romper el flujo actual de estado en tiempo real.
- No introducir complejidad innecesaria.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en dominio, persistencia e idempotencia.

## Validation
- Existe un modelo de dominio histórico claro para los 2 servidores.
- Existe una base de almacenamiento/esquema local coherente con ese modelo.
- La estructura permite futuras consultas como top kills semanales por servidor.
- Queda clara la separación entre live status y histórico persistido.
- No se han creado páginas frontend nuevas ni soluciones basadas en URLs de la comunidad.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 7 archivos modificados o creados.
- Preferir menos de 260 líneas cambiadas.
## Outcome
- Se aÃ±adio `backend/app/historical_models.py` como capa minima de dominio para servidor, mapa, partida, jugador, estadisticas por partida y ejecucion de ingesta.
- Se implemento `backend/app/historical_storage.py` con tablas `historical_*` separadas del flujo live A2S, claves estables e `UPSERT` idempotente para partidas, jugadores y estadisticas por jugador.
- Se documento el modelo e identidad estable en `docs/historical-domain-model.md`, y se alinearon `docs/decisions.md`, `ai/architecture-index.md` y `backend/README.md`.
- La inicializacion de storage incluye migracion segura desde una version legacy ya existente en la base SQLite local, preservando los datos previos en la nueva estructura.

## Validation Result
- Validado con `python -m compileall app` desde `backend/`.
- Validado con una comprobacion local de `initialize_historical_storage()`, `list_historical_servers()` y `list_recent_historical_matches(limit=3)`.
- Revisado `git diff --name-only` para confirmar que el cambio quedo centrado en `ai/`, `docs/`, `backend/` y archivos de task.

## Decision Notes
- El historico CRCON comparte el mismo SQLite local de desarrollo que los snapshots A2S para no introducir infraestructura prematura, pero queda estrictamente separado por tablas `historical_*`.
