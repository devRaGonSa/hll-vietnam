# TASK-030-historical-crcon-incremental-refresh

## Goal
Añadir un mecanismo de refresco incremental para la ingesta histórica CRCON que permita mantener actualizados los datos de ambos servidores de la comunidad sin reimportar todo el histórico completo en cada ejecución.

## Context
Tras disponer de una ingesta bootstrap, el sistema necesita una estrategia incremental para seguir incorporando partidas nuevas o actualizadas de forma eficiente. Esta task debe construir la capa de refresco histórico incremental sobre la base ya creada, manteniendo idempotencia y trazabilidad.

## Steps
1. Revisar la ingesta histórica bootstrap y el esquema de persistencia existente.
2. Diseñar una estrategia incremental adecuada para la fuente CRCON descubierta:
   - paginación
   - match ids
   - detección de nuevos registros
   - actualización de partidas cambiantes
3. Implementar el refresco incremental para ambos servidores.
4. Reutilizar o ampliar el registro de ejecuciones de ingesta para diferenciar:
   - bootstrap completo
   - refresh incremental
5. Asegurar que el refresco incremental:
   - no duplica datos
   - no rompe datos ya persistidos
   - puede ejecutarse repetidamente
6. Documentar cómo ejecutar este refresco incremental en local.
7. No implementar todavía UI histórica.
8. No acoplar el frontend a las URLs públicas de la comunidad.
9. Al completar la implementación:
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
- backend/app/historical_ingestion.py
- backend/app/historical_storage.py
- backend/app/historical_models.py

## Expected Files to Modify
- backend/README.md
- backend/app/config.py
- backend/app/historical_ingestion.py
- backend/app/historical_storage.py
- opcionalmente nuevos módulos auxiliares si mejoran claridad del refresco incremental

## Constraints
- No basar el refresco histórico en A2S.
- No crear páginas frontend nuevas usando la URL de la comunidad.
- No introducir complejidad innecesaria.
- No romper el flujo actual de live status.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en refresco incremental, coherencia y trazabilidad.

## Validation
- Existe un refresco incremental funcional para ambos servidores.
- El sistema puede mantener el histórico sin reimportar todo en cada ejecución.
- La persistencia sigue siendo idempotente.
- La documentación explica el flujo incremental.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 6 archivos modificados o creados.
- Preferir menos de 240 líneas cambiadas.
## Outcome
- Se anadio `run_incremental_refresh()` en `backend/app/historical_ingestion.py` reutilizando la misma persistencia y el registro de ejecuciones.
- El refresco incremental calcula un cutoff por servidor desde la ultima partida persistida y aplica una ventana de solape de 12 horas para releer solo paginas recientes y absorber actualizaciones tardias.
- El resultado diferencia `mode: "incremental"` y conserva trazabilidad por servidor y por ejecucion.

## Validation Result
- Validado con `python -m app.historical_ingestion refresh --max-pages 1`.
- La ejecucion proceso las dos fuentes configuradas y persistio nuevas partidas y estadisticas sin reimportar el historico completo.
- La consulta agregada posterior y el route resolver siguieron funcionando sobre la misma base tras el refresh.

## Decision Notes
- El cutoff incremental se apoya en `MAX(ended_at, started_at, created_at_source)` por servidor y no en paginas absolutas, para tolerar cambios de orden o partidas que se completan mas tarde.
