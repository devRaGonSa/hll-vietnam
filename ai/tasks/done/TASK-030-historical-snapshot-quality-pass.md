# TASK-030-historical-snapshot-quality-pass

## Goal
Revisar y ajustar la calidad de los snapshots persistidos tras la primera captura A2S real, asegurando consistencia de datos, timestamps, procedencia y utilidad de cara a historico y visualizacion.

## Context
Una vez incorporado el target real y validada una primera captura, el siguiente paso es comprobar la calidad del dato persistido. No basta con guardar snapshots; deben ser consistentes y utiles para construir historico, estadisticas y visualizacion sin ruido innecesario.

## Steps
1. Revisar snapshots persistidos a partir de la captura real de Comunidad Hispana #01.
2. Verificar consistencia de campos clave:
   - nombre del servidor
   - host o referencia de origen
   - timestamp
   - mapa actual
   - jugadores
   - capacidad
   - fuente efectiva
3. Revisar si hay problemas de calidad como:
   - duplicados innecesarios
   - timestamps incoherentes
   - normalizacion deficiente
   - mezcla poco clara entre fallback y captura real
4. Ajustar la capa de persistencia, normalizacion o payloads si fuera necesario para mejorar claridad.
5. Revisar el impacto en endpoints historicos existentes:
   - `/api/servers/latest`
   - `/api/servers/history`
   - `/api/servers/{id}/history`
6. Mantener el cambio centrado en calidad y coherencia del historico, no en nuevas visualizaciones.
7. Actualizar documentacion minima si el modelo efectivo de snapshot cambia ligeramente.

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- backend/README.md
- backend/app/collector.py
- backend/app/normalizers.py
- backend/app/storage.py
- backend/app/routes.py
- backend/app/payloads.py
- datos persistidos generados en la task anterior

## Expected Files to Modify
- backend/app/normalizers.py
- backend/app/storage.py
- backend/app/routes.py
- backend/app/payloads.py
- backend/README.md
- opcionalmente documentacion tecnica relacionada si la claridad del historico necesita ajuste

## Constraints
- No tocar frontend en esta task.
- No anadir nuevas fuentes externas.
- No introducir complejidad analitica alta.
- No hacer cambios destructivos.
- Mantener el resultado centrado en calidad de datos historicos.

## Validation
- Los snapshots reales persistidos son consistentes y utiles.
- Los endpoints historicos reflejan correctamente el dato real almacenado.
- La distincion entre captura real y fallback queda razonablemente clara.
- El backend queda listo para una siguiente task de mejora visual o estadistica sobre datos reales.

## Change Budget
- Preferir menos de 5 archivos modificados.
- Preferir menos de 180 lineas cambiadas.

## Outcome
- `backend/app/normalizers.py` anade `snapshot_origin` y `source_ref` al modelo normalizado para que la procedencia no se infiera de forma ambigua en historico.
- `backend/app/snapshots.py` conserva esos campos en cada snapshot persistible.
- `backend/app/storage.py` migra la tabla SQLite sin destruir datos, serializa ambos campos en las consultas historicas y backfilla referencias A2S registradas para snapshots ya existentes.
- `backend/README.md` documenta los nuevos metadatos historicos y el valor esperado para la captura real de Comunidad Hispana #01.

## Validation Result
- Ejecutado: lectura de `list_latest_snapshots()`, `list_snapshot_history()` y `list_server_history('comunidad-hispana-01')` desde Python.
- Resultado: los snapshots historicos exponen `snapshot_origin` con `real-a2s` o `controlled-fallback` y `source_ref` coherente.
- Ejecutado fuera del sandbox: `python -m app.collector --source a2s --no-fallback`.
- Resultado: nuevo snapshot real persistido con `source_ref=a2s://152.114.195.174:7778`, `current_map=Remagen`, `players=0`, `max_players=100`.
- Endpoints verificados: `/api/servers/latest`, `/api/servers/history` y `/api/servers/{id}/history` devuelven el snapshot real mas reciente con la nueva metadata de procedencia.

## Decision Notes
- No se tocaron `routes.py` ni `payloads.py` porque ya reutilizan directamente los registros serializados de almacenamiento y heredaron la mejora sin cambios de contrato adicionales.
- No se introdujo deduplicacion agresiva de snapshots porque dos capturas reales con distinto `captured_at` siguen siendo historico valido; el ajuste se centro en claridad y consistencia de procedencia.
