# TASK-035-real-a2s-capture-validation-comunidad-hispana-02

## Goal
Validar una captura A2S real extremo a extremo contra Comunidad Hispana #02, confirmando que el colector puede consultar el servidor, normalizar la respuesta y persistir snapshots útiles junto a los ya existentes de Comunidad Hispana #01.

## Context
El proyecto ya ha validado el flujo real A2S con Comunidad Hispana #01. Ahora se ha verificado un segundo servidor real de Comunidad Hispana con:
- Host/IP: `152.114.195.150`
- Query Port: `7878`
- Game Port: `7877`

El objetivo es confirmar que el pipeline soporta múltiples targets reales y que la persistencia y los endpoints históricos siguen siendo coherentes.

## Steps
1. Revisar la configuración actual de targets A2S y el target recién añadido para Comunidad Hispana #02.
2. Ejecutar el colector o flujo equivalente contra este target real.
3. Confirmar que el backend consulta correctamente el host `152.114.195.150` con query port `7878`.
4. Validar que la respuesta A2S obtenida se normaliza al modelo interno.
5. Persistir al menos un snapshot real de Comunidad Hispana #02 en la base local actual.
6. Verificar que los endpoints históricos reflejan este nuevo servidor junto al ya existente.
7. Revisar el comportamiento si la consulta falla, timeout o devuelve datos parciales.
8. Actualizar la documentación mínima necesaria sobre cómo repetir esta validación en local.
9. Mantener el alcance centrado en validación del flujo real, no en nuevas features.

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
- backend/app/routes.py
- backend/app/payloads.py

## Expected Files to Modify
- backend/README.md
- backend/app/collector.py
- backend/app/normalizers.py
- backend/app/storage.py
- backend/app/routes.py
- backend/app/payloads.py
- opcionalmente otros archivos backend si son estrictamente necesarios para soportar mejor múltiples targets reales

## Constraints
- No tocar frontend salvo que una referencia mínima fuera imprescindible para mostrar el nuevo target una vez persistido.
- No añadir analítica avanzada.
- No añadir scraping de terceros.
- No introducir complejidad innecesaria.
- No hacer cambios destructivos.
- Mantener la validación centrada en Comunidad Hispana #02 y coexistencia con #01.

## Validation
- Se realiza una captura real A2S sobre Comunidad Hispana #02.
- Se persiste al menos un snapshot real en la base local.
- El flujo real queda documentado y es repetible en local.
- Los endpoints históricos reflejan ambos targets reales cuando existan snapshots.
- Los errores de consulta están razonablemente manejados.

## Change Budget
- Preferir menos de 6 archivos modificados.
- Preferir menos de 180 líneas cambiadas.
## Outcome
- `backend/app/a2s_client.py` eleva el timeout A2S por defecto de `3.0s` a `6.0s` para reducir timeouts transitorios al consultar varios targets reales seguidos.
- `backend/README.md` documenta la validacion local extremo a extremo con ambos targets reales por defecto y el resultado esperado cuando responden `#01` y `#02`.
- No fue necesario cambiar `collector.py`, `normalizers.py`, `storage.py`, `routes.py` ni `payloads.py` porque el pipeline ya normalizaba, persistia y exponia historico multi-target correctamente.

## Validation Result
- Ejecutado desde `backend/`: `python -m app.a2s_client 152.114.195.150 7878 --timeout 6`.
- Resultado: respuesta valida de `Comunidad Hispana #02` con `server_name=#02 [ESP] Comunidad Hispana - discord.comunidadhll.es - Spa Onl`, `map_name=StMarie`, `players=0`, `max_players=100`.
- Ejecutado desde `backend/`: `python -m app.collector --source a2s --no-fallback`.
- Resultado: `target_count: 2`, `success_count: 2`, snapshots persistidos para `comunidad-hispana-01` y `comunidad-hispana-02` en `backend/data/hll_vietnam_dev.sqlite3`.
- Ejecutado desde `backend/`: `python -c "from app.payloads import build_server_history_payload, build_server_detail_history_payload; ..."` para revisar historico.
- Resultado: `/api/servers/history` refleja ambos targets reales y `/api/servers/comunidad-hispana-02/history` devuelve el snapshot persistido de `#02`.

## Decision Notes
- Se ajusta el timeout por defecto en lugar de introducir reintentos o complejidad adicional porque la captura ya era funcional y el problema observado fue de sensibilidad temporal, no de arquitectura.
