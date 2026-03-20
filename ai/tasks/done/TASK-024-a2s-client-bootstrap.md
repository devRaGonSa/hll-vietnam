# TASK-024-a2s-client-bootstrap

## Goal
Preparar un cliente A2S mínimo en el backend Python para consultar servidores de Hell Let Loose actual mediante query pública, obteniendo metadata básica reutilizable por el colector de snapshots.

## Context
El proyecto ya dispone de colector bootstrap, persistencia local y consultas históricas mínimas. El siguiente paso es introducir una fuente real de datos en vivo. Hell Let Loose usa Steam A2S para metadata de servidor a través del query port, por lo que esta task debe preparar la base técnica para consultar servidores reales sin depender todavía de integraciones administrativas o scoreboards avanzados.

## Steps
1. Revisar el backend actual, especialmente el colector y las funciones de normalización.
2. Revisar la documentación técnica de ingesta y el modelo de snapshots.
3. Preparar un cliente A2S mínimo capaz de consultar al menos la información equivalente a:
   - nombre del servidor
   - mapa actual
   - jugadores actuales
   - capacidad máxima
4. Mantener la implementación desacoplada para que futuras consultas de players o rules puedan añadirse después sin romper la base.
5. Normalizar la salida del cliente A2S hacia el modelo interno ya usado por el proyecto.
6. Asegurar que la implementación maneje fallos básicos de red o timeouts de forma controlada.
7. Actualizar la documentación backend para reflejar que existe una fuente A2S real de prueba.
8. Mantener el alcance centrado en bootstrap del cliente, no en pipeline completo.

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
- backend/app/storage.py

## Expected Files to Modify
- backend/README.md
- backend/app/__init__.py
- backend/app/normalizers.py
- backend/app/collector.py
- opcionalmente archivos nuevos dentro de backend/app/ si mejoran claridad, por ejemplo:
  - backend/app/a2s_client.py
  - backend/app/a2s_protocol.py

## Constraints
- No implementar todavía scraping de terceros.
- No tocar frontend.
- No añadir base de datos nueva.
- No hacer cambios destructivos.
- Mantener la implementación pequeña, clara y orientada a desarrollo local.

## Validation
- Existe un cliente A2S mínimo reutilizable desde el backend.
- El cliente puede obtener metadata básica de servidor.
- La salida se normaliza al modelo interno del proyecto.
- La documentación backend refleja el nuevo estado.

## Change Budget
- Preferir menos de 6 archivos modificados o creados.
- Preferir menos de 260 líneas cambiadas.

## Outcome
- Se anadio un cliente A2S minimo en `backend/app/a2s_client.py` usando solo libreria estandar para consultar `A2S_INFO`.
- `backend/app/normalizers.py` ahora puede convertir una respuesta A2S al modelo interno de snapshots ya usado por el proyecto.
- `backend/app/collector.py` expone `fetch_a2s_probe()` como adaptador pequeno reutilizable para la siguiente task de integracion del pipeline.
- `backend/app/__init__.py` mantiene acceso ligero a `query_server_info()` y `fetch_a2s_probe()` sin acoplar la carga del paquete al CLI del cliente.
- `backend/README.md` documenta el nuevo estado y una prueba manual local del cliente.

## Validation Result
- Ejecutado: `python -m compileall backend/app`
- Resultado: compilacion correcta de los modulos del backend.
- Ejecutado: `python -m app.a2s_client --help`
- Resultado: CLI disponible sin warnings y con los argumentos esperados.

## Decision Notes
- Se mantuvo la implementacion en libreria estandar con UDP directo para evitar introducir dependencias antes de validar targets y configuracion en las siguientes tasks.
