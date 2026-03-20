# TASK-031-weekly-top-kills-api

## Goal
Exponer una primera API histórica útil que devuelva el ranking de jugadores con más kills de la última semana para cada uno de los 2 servidores reales de la comunidad.

## Context
El objetivo funcional histórico inicial del proyecto es poder consultar métricas agregadas como “jugadores con más kills de la última semana por servidor”. Con la fuente descubierta, el almacenamiento creado y la ingesta histórica ya en marcha, el siguiente valor real es exponer un endpoint backend estable que pueda alimentar futuras vistas propias del proyecto sin depender directamente de la web de la comunidad.

## Steps
1. Revisar el modelo de dominio histórico y la persistencia ya creada.
2. Definir el endpoint o endpoints mínimos necesarios para top kills semanales por servidor.
3. Diseñar e implementar la consulta agregada usando los datos históricos persistidos.
4. Definir un payload claro que incluya, como mínimo:
   - servidor
   - rango temporal usado
   - jugador
   - kills semanales
   - posición/ranking
   - número de partidas consideradas si resulta viable
5. Asegurar que la definición de “última semana” queda clara y consistente.
6. Documentar el endpoint en el backend.
7. No crear todavía páginas frontend nuevas usando la URL de la comunidad.
8. No incrustar ni duplicar scoreboard externos.
9. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- docs/historical-domain-model.md
- backend/README.md
- backend/app/routes.py
- backend/app/payloads.py
- backend/app/historical_storage.py
- backend/app/historical_models.py
- backend/app/historical_ingestion.py

## Expected Files to Modify
- backend/app/routes.py
- backend/app/payloads.py
- backend/README.md
- uno o más módulos nuevos o existentes de consulta histórica, por ejemplo:
  - backend/app/historical_queries.py
  - backend/app/historical_payloads.py

## Constraints
- No basar este endpoint en A2S.
- No consultar directamente la web de la comunidad desde el frontend.
- No crear todavía UI histórica.
- No romper endpoints actuales.
- No introducir complejidad innecesaria.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en la primera API histórica útil y estable.

## Validation
- Existe un endpoint usable para top kills de la última semana por servidor.
- El endpoint funciona para los 2 servidores reales de la comunidad.
- El payload es claro y reutilizable.
- La documentación backend queda alineada.
- No se han creado páginas frontend nuevas ni dependencias directas del frontend respecto a la URL de la comunidad.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 6 archivos modificados o creados.
- Preferir menos de 240 líneas cambiadas.
## Outcome
- Se expuso `GET /api/historical/weekly-top-kills` en `backend/app/routes.py`.
- La agregacion vive en `backend/app/historical_storage.py` y calcula top kills semanales con ranking independiente por cada servidor real.
- El payload reutiliza `build_weekly_top_kills_payload()` para devolver rango temporal, jugador, kills semanales, posicion y partidas consideradas.
- `backend/README.md` documenta el endpoint y sus parametros `limit` y `server`.

## Validation Result
- Validado con `python -m compileall app`.
- Validado con una comprobacion local de `resolve_get_payload('/api/historical/weekly-top-kills?limit=3')`, que devolvio `200`, `status: "ok"` y resultados para ambos servidores.
- El endpoint se apoya exclusivamente en historico persistido CRCON y no toca el flujo live A2S ni el frontend.

## Decision Notes
- El limite se aplica por servidor mediante `ROW_NUMBER() OVER (PARTITION BY historical_servers.slug ...)` para que una request con `limit=10` entregue hasta 10 jugadores por cada servidor, no un corte global mezclado.
