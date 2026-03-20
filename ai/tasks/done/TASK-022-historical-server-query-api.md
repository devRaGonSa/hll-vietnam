# TASK-022-historical-server-query-api

## Goal
Exponer desde el backend una primera API de consulta historica para snapshots de servidores, permitiendo recuperar el ultimo estado conocido y una evolucion basica a partir de la persistencia local ya preparada.

## Context
Una vez que los snapshots puedan guardarse, el siguiente paso es poder consultarlos de forma estructurada. Esta task debe convertir la persistencia inicial en una API util para comprobar que el flujo de estadisticas ya funciona extremo a extremo.

## Steps
1. Revisar la capa de persistencia de snapshots y el backend actual.
2. Definir endpoints minimos de consulta historica, por ejemplo:
   - `GET /api/servers/latest`
   - `GET /api/servers/history`
   - `GET /api/servers/{id}/history`
3. Alinear el formato de respuesta con las convenciones del backend existente.
4. Hacer que las respuestas devuelvan como minimo:
   - timestamps
   - ultimo estado conocido
   - jugadores
   - capacidad
   - mapa si esta disponible
   - contexto o fuente si aplica
5. Mantener la implementacion simple y enfocada a validacion tecnica.
6. Actualizar la documentacion del backend y del contrato si fuera necesario.
7. No introducir todavia analitica avanzada ni agregaciones pesadas.

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- docs/frontend-backend-contract.md
- docs/current-hll-data-ingestion-plan.md
- docs/stats-database-schema-foundation.md
- backend/README.md
- backend/app/main.py
- backend/app/routes.py
- backend/app/payloads.py
- backend/app/collector.py
- backend/app/snapshots.py
- archivos de persistencia creados en la task anterior

## Expected Files to Modify
- backend/app/main.py
- backend/app/routes.py
- backend/app/payloads.py
- backend/README.md
- opcionalmente documentacion tecnica contractual si requiere alineacion menor

## Constraints
- No tocar frontend en esta task.
- No anadir visualizacion nueva.
- No introducir complejidad innecesaria.
- No hacer cambios destructivos.
- Mantener la API clara, estable y centrada en historico basico.

## Validation
- Existen endpoints historicos minimos funcionales.
- El backend puede devolver ultimo snapshot y una historia basica de snapshots.
- La documentacion refleja correctamente el nuevo estado.
- El resultado prepara el terreno para una primera visualizacion en frontend.

## Change Budget
- Preferir menos de 6 archivos modificados o creados.
- Preferir menos de 240 lineas cambiadas.

## Outcome
- Se anadieron lecturas minimas desde SQLite para ultimo snapshot por servidor, historial agregado e historial por servidor.
- `backend/app/routes.py` resuelve `GET /api/servers/latest`, `GET /api/servers/history` y `GET /api/servers/{id}/history`.
- `backend/app/payloads.py` mantiene el formato JSON del backend y devuelve errores controlados para parametros invalidos.
- `backend/README.md` y `docs/frontend-backend-contract.md` documentan los nuevos endpoints.

## Validation Result
- Ejecutado: `python -c "from app.collector import collect_server_snapshots; from app.routes import resolve_get_payload; collect_server_snapshots(persist=True); ..."`
- Resultado: los tres endpoints historicos devolvieron datos persistidos y `limit=999` respondio con `status: "error"`.

## Decision Notes
- Se mantuvo la API sobre la persistencia SQLite local ya existente, evitando una capa analitica separada hasta que el frontend necesite algo mas que consultas historicas basicas.
