# TASK-021-snapshot-persistence-bootstrap

## Goal
Preparar una persistencia local minima para snapshots de servidores en el backend Python, de forma que los datos recogidos durante las pruebas con HLL actual puedan guardarse y reutilizarse para consultas historicas posteriores.

## Context
El proyecto ya dispone de plan de ingesta, modelo logico de almacenamiento y bootstrap de colector. El siguiente paso es dejar de depender exclusivamente de estructuras temporales o payloads controlados y empezar a guardar snapshots de forma persistente para validar el circuito real de estadisticas.

## Steps
1. Revisar la documentacion actual de ingesta, esquema logico y colector.
2. Definir una estrategia de persistencia local minima adecuada para esta fase de pruebas.
3. Implementar una capa pequena de persistencia alineada con las entidades ya definidas logicamente:
   - game_sources
   - servers
   - server_snapshots
4. Mantener la implementacion simple, reutilizable y desacoplada de una base de datos de produccion futura.
5. Hacer que el colector pueda guardar snapshots reales o controlados en esa persistencia local.
6. Documentar como inicializar y usar esta persistencia en desarrollo.
7. No introducir todavia consultas historicas complejas ni visualizacion en frontend.
8. Mantener el alcance centrado en almacenamiento basico funcional.

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- docs/current-hll-data-ingestion-plan.md
- docs/stats-database-schema-foundation.md
- backend/README.md
- backend/app/__init__.py
- backend/app/config.py
- backend/app/collector.py
- backend/app/normalizers.py
- backend/app/snapshots.py

## Expected Files to Modify
- backend/README.md
- backend/app/__init__.py
- backend/app/config.py
- backend/app/collector.py
- backend/app/snapshots.py
- opcionalmente archivos nuevos dentro de backend/app/ si mejoran la separacion de persistencia, por ejemplo:
  - backend/app/storage.py
  - backend/app/repository.py

## Constraints
- No implementar todavia integraciones reales complejas de terceros.
- No tocar frontend.
- No anadir una infraestructura de produccion sobredimensionada.
- No hacer cambios destructivos.
- Mantener la persistencia simple y util para desarrollo local.

## Validation
- El backend puede guardar snapshots de servidores en una persistencia local real.
- La persistencia sigue el modelo logico documentado.
- La documentacion explica como usar esta base minima en local.
- El resultado prepara el terreno para consultas historicas inmediatas.

## Change Budget
- Preferir menos de 7 archivos modificados o creados.
- Preferir menos de 260 lineas cambiadas.

## Outcome
- Se anadio `backend/app/storage.py` con una persistencia SQLite minima basada en libreria estandar.
- El colector puede persistir snapshots controlados en `game_sources`, `servers` y `server_snapshots`.
- La configuracion local expone `HLL_BACKEND_STORAGE_PATH` para cambiar la ruta del archivo SQLite sin fijar una decision de produccion.
- `backend/README.md` documenta la inicializacion y uso de la persistencia local.

## Validation Result
- Ejecutado: `python -m app.collector`
- Resultado: lote de 3 snapshots persistido correctamente en SQLite local de desarrollo.

## Decision Notes
- Se eligio SQLite porque cubre persistencia local real con dependencias cero y mantiene abierta la migracion futura a otra tecnologia de almacenamiento.
