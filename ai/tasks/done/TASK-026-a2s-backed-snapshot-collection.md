# TASK-026-a2s-backed-snapshot-collection

## Goal
Hacer que el colector de snapshots del backend pueda capturar datos reales desde servidores HLL consultables por A2S y persistir esos snapshots en la base local ya preparada.

## Context
El proyecto ya tiene persistencia local, consultas históricas mínimas y un bootstrap de colector. Tras introducir un cliente A2S y una configuración de targets, el siguiente paso es cerrar el primer flujo real de captura y persistencia sobre servidores actuales de HLL.

## Steps
1. Revisar el colector actual, la persistencia local y el cliente A2S.
2. Integrar el cliente A2S dentro del flujo de colecta de snapshots.
3. Hacer que el colector capture datos desde los targets configurados y los normalice al modelo interno.
4. Persistir los snapshots reales usando la capa de almacenamiento ya existente.
5. Manejar de forma controlada los casos de timeout, servidor inaccesible o respuesta inválida.
6. Mantener la posibilidad de usar datos controlados o fallback de desarrollo si la fuente real no responde.
7. Actualizar la documentación backend para explicar el flujo de captura real en esta fase.
8. Mantener el alcance centrado en captura y persistencia, no en nuevas visualizaciones.

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
- backend/app/a2s_client.py
- backend/app/server_targets.py si existe

## Expected Files to Modify
- backend/README.md
- backend/app/collector.py
- backend/app/normalizers.py
- backend/app/storage.py
- opcionalmente archivos auxiliares nuevos si son estrictamente necesarios para mantener claridad

## Constraints
- No tocar frontend en esta task.
- No introducir todavía estadísticas complejas.
- No añadir scraping de terceros.
- No hacer cambios destructivos.
- Mantener el pipeline claro, comprobable y pequeño.

## Validation
- El colector puede capturar snapshots reales desde al menos un target A2S configurado.
- Los snapshots se persisten en la base local actual.
- Los errores de consulta quedan manejados de forma razonable.
- La documentación backend refleja cómo ejecutar esta captura en local.

## Change Budget
- Preferir menos de 6 archivos modificados o creados.
- Preferir menos de 240 líneas cambiadas.

## Outcome
- `backend/app/collector.py` ahora puede ejecutar captura en modo `a2s`, `controlled` o `auto`, persistiendo snapshots reales cuando las consultas A2S tienen exito.
- El colector registra errores por target sin abortar todo el lote y usa fallback controlado cuando no obtiene respuestas reales y el fallback esta habilitado.
- `backend/app/storage.py` persiste `source_name` por snapshot para conservar la procedencia efectiva de cada captura.
- `backend/README.md` documenta como ejecutar captura real, captura controlada y captura automatica con fallback en local.

## Validation Result
- Ejecutado: `python -m compileall backend/app`
- Resultado: compilacion correcta de los modulos del backend.
- Ejecutado: validacion con `collect_server_snapshots(source_mode="a2s", persist=True, probe_target=stub_probe)` sobre SQLite temporal.
- Resultado: flujo A2S simulado persistio 1 snapshot y `list_snapshot_history()` devolvio 1 registro.
- Ejecutado: validacion con `collect_server_snapshots(source_mode="auto", timeout=0.1, persist=True)` usando el target local por defecto.
- Resultado: el colector registro 1 error de consulta, activo fallback controlado y persistio 3 snapshots de desarrollo.

## Decision Notes
- Se mantuvo un fallback explicito de desarrollo para no romper el flujo local mientras los targets A2S reales siguen siendo configurables y potencialmente inestables.
