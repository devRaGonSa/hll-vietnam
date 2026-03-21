# TASK-041-historical-resumable-backfill-expansion

## Goal
Ampliar la cobertura historica persistida de ambos servidores de la comunidad lo maximo posible mediante un proceso de backfill reanudable, seguro e idempotente, capaz de continuar sesiones incompletas sin perder progreso cuando la fuente CRCON publica falle intermitentemente.

## Context
La capa historica del proyecto ya esta funcionando y la UI ya muestra cobertura registrada, pero la cobertura actual sigue siendo parcial. La fuente CRCON publica indica archivos mucho mas profundos que lo actualmente persistido, pero las sesiones largas de bootstrap sufren respuestas `502` intermitentes bajo carga. Eso significa que el limite actual de fechas no representa necesariamente el historico real disponible, sino el alcance conseguido hasta ahora por la importacion.

La solucion correcta no es asumir que el historico ya esta completo, sino implementar o consolidar un backfill reanudable por lotes que permita seguir retrocediendo en el tiempo y ampliando la cobertura historica de forma progresiva.

## Steps
1. Revisar la implementacion actual de:
   - bootstrap historico
   - refresh incremental
   - persistencia historica
   - validacion de cobertura
2. Revisar como se manejan actualmente:
   - paginacion
   - progreso de bootstrap
   - reintentos
   - errores upstream tipo `502`
3. Diseñar o consolidar una estrategia de backfill reanudable que permita:
   - continuar desde una pagina o cursor previo
   - guardar progreso util por servidor
   - reintentar sin duplicar datos
   - ampliar cobertura historica por bloques
4. Implementar o reforzar un mecanismo para ejecutar sesiones sucesivas de backfill historico para ambos servidores.
5. Garantizar que el sistema:
   - no pierde progreso util
   - no vuelve a importar innecesariamente lo ya consolidado
   - puede seguir avanzando aunque una sesion concreta falle a mitad
6. Añadir o mejorar metadatos operativos de cobertura y progreso, por ejemplo:
   - ultima pagina procesada por servidor
   - rango temporal cubierto actual
   - numero total de partidas persistidas
   - estado del ultimo intento de backfill
7. Ejecutar o dejar documentado un flujo operativo realista para seguir ampliando cobertura en varias sesiones.
8. Documentar claramente que la cobertura historica puede crecer progresivamente y que el limite actual no debe interpretarse como limite definitivo del origen mientras siga habiendo paginas disponibles.
9. No crear todavia nueva UI historica en esta task salvo ajustes minimos de payload o semantica si fueran imprescindibles para reflejar mejor la cobertura.
10. Al completar la implementacion:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- docs/historical-crcon-source-discovery.md
- docs/historical-domain-model.md
- docs/historical-data-quality-notes.md
- docs/historical-coverage-report.md
- backend/README.md
- backend/app/config.py
- backend/app/historical_ingestion.py
- backend/app/historical_storage.py
- backend/app/historical_models.py
- backend/app/routes.py
- backend/app/payloads.py

## Expected Files to Modify
- backend/README.md
- backend/app/config.py
- backend/app/historical_ingestion.py
- backend/app/historical_storage.py
- backend/app/historical_models.py
- opcionalmente nuevos modulos auxiliares si mejoran claridad del backfill y del checkpoint de progreso, por ejemplo:
  - backend/app/historical_backfill_state.py
  - backend/app/historical_backfill_runner.py
- opcionalmente documentacion tecnica adicional, por ejemplo:
  - docs/historical-coverage-report.md
  - docs/historical-backfill-operations.md

## Constraints
- No basar esta ampliacion historica en A2S.
- No crear paginas frontend nuevas usando la URL de la comunidad.
- No depender del HTML de `/games` como fuente final.
- No romper el flujo actual de live status.
- No romper la persistencia historica ya existente.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en backfill reanudable, idempotencia, resiliencia y ampliacion de cobertura.

## Validation
- Existe un mecanismo reanudable para seguir ampliando el historico por lotes.
- El backfill puede continuar sin duplicar datos ya persistidos.
- El sistema registra progreso util por servidor.
- La cobertura historica puede ampliarse progresivamente con sesiones sucesivas.
- La documentacion deja claro el estado real y las limitaciones operativas.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 7 archivos modificados o creados.
- Preferir menos de 260 lineas cambiadas.

## Outcome
- Se añadio persistencia de checkpoint por servidor y modo en `historical_backfill_progress`.
- El bootstrap ahora reanuda automaticamente desde `next_page` cuando no se pasa `--start-page`.
- Cada pagina completada guarda progreso util (`last_completed_page`, `next_page`, total descubierto y estado del ultimo intento).
- `server-summary` y el reporte de cobertura exponen metadatos operativos de backfill para reflejar mejor la cobertura real importada.
- Se documento el flujo operativo reanudable y los nuevos ajustes de reintentos para errores CRCON intermitentes.

## Validation Notes
- `python -m compileall app`
- validacion local con SQLite de prueba en workspace verificando:
  - reanudacion desde pagina `4` tras completar la pagina `3`
  - persistencia de `last_completed_page`
  - exposicion de `discovered_total_pages` en cobertura y resumen
- no se ejecuto backfill real contra CRCON por las restricciones de red del entorno actual
