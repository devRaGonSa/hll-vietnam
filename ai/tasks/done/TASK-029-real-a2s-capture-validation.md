# TASK-029-real-a2s-capture-validation

## Goal
Validar una captura A2S real extremo a extremo contra Comunidad Hispana #01, confirmando que el colector puede consultar el servidor, normalizar la respuesta y persistir snapshots utiles en la base local.

## Context
El proyecto ya tiene:
- cliente A2S
- targets configurables
- persistencia local
- endpoints historicos
- primer target real verificado para Comunidad Hispana #01

Ahora hay que comprobar que el flujo real funciona de verdad con ese servidor:
A2S -> colector -> persistencia local

## Steps
1. Revisar el target real configurado para Comunidad Hispana #01.
2. Ejecutar el colector o flujo equivalente contra ese target real.
3. Confirmar que el backend consulta correctamente el host `152.114.195.174` con query port `7778`.
4. Validar que la respuesta A2S obtenida se normaliza al modelo interno del proyecto.
5. Persistir al menos un snapshot real en la base local actual.
6. Verificar que se registran de forma razonable:
   - nombre del servidor
   - timestamp de captura
   - mapa actual si esta disponible
   - jugadores actuales
   - capacidad maxima
   - procedencia efectiva del snapshot
7. Verificar el comportamiento si la consulta falla, timeout o devuelve datos parciales.
8. Actualizar la documentacion minima necesaria sobre como ejecutar esta validacion en local.
9. Mantener el alcance centrado en validacion del flujo real, no en nuevas features.

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- backend/README.md
- backend/app/a2s_client.py
- backend/app/server_targets.py
- backend/app/collector.py
- backend/app/normalizers.py
- backend/app/snapshots.py
- backend/app/storage.py

## Expected Files to Modify
- backend/README.md
- backend/app/collector.py
- backend/app/normalizers.py
- backend/app/storage.py
- opcionalmente otros archivos backend si son estrictamente necesarios para una captura real robusta

## Constraints
- No tocar frontend.
- No anadir analitica avanzada.
- No anadir scraping de terceros.
- No introducir complejidad innecesaria.
- No hacer cambios destructivos.
- Mantener la validacion centrada en Comunidad Hispana #01.

## Validation
- Se realiza una captura real A2S sobre Comunidad Hispana #01.
- Se persiste al menos un snapshot real en la base local.
- El flujo real queda documentado y es repetible en local.
- Los errores de consulta estan razonablemente manejados.

## Change Budget
- Preferir menos de 5 archivos modificados.
- Preferir menos de 180 lineas cambiadas.

## Outcome
- `backend/README.md` documenta el comando exacto de validacion A2S real y el resultado esperado cuando `Comunidad Hispana #01` responde.
- No fue necesario cambiar `collector.py`, `normalizers.py` ni `storage.py` porque el flujo real ya normaliza y persiste correctamente.
- La validacion tambien dejo ver el comportamiento de error: en entorno sandbox con UDP restringido el colector devuelve timeout controlado y `success_count: 0`.

## Validation Result
- Ejecutado en sandbox: `python -m app.collector --source a2s --no-fallback`.
- Resultado en sandbox: timeout controlado hacia `152.114.195.174:7778`, `success_count: 0`, sin snapshots reales persistidos.
- Ejecutado fuera del sandbox: `python -m app.collector --source a2s --no-fallback`.
- Resultado fuera del sandbox: `success_count: 1`, un snapshot persistido para `comunidad-hispana-01` en `backend/data/hll_vietnam_dev.sqlite3`.
- Snapshot validado en SQLite: `server_name=#01 [ESP] Comunidad Hispana - discord.comunidadhll.es - Spa Onl`, `current_map=Remagen`, `players=0`, `max_players=100`, `source_name=community-hispana-a2s`, `captured_at=2026-03-20T11:23:08.431142Z`.
- Endpoints revisados desde Python: `/api/servers/latest`, `/api/servers/history` y `/api/servers/{id}/history` ya exponen el snapshot real persistido.

## Decision Notes
- El timeout observado en sandbox no se trato como bug de backend porque la misma consulta funciono fuera del sandbox sin cambios de codigo.
- La procedencia efectiva del snapshot queda reflejada en `source_name=community-hispana-a2s`, mientras que el payload superior del colector mantiene `collection_mode=a2s`.
