# TASK-022-real-time-server-snapshot-refresh

## Goal
Hacer que `GET /api/servers` devuelva datos realmente actuales de los 2 servidores de la comunidad, refrescando el snapshot cuando el último estado persistido esté vencido respecto al objetivo de 120 segundos.

## Context
La implementación actual ya tiene snapshots persistidos y polling desde frontend, pero el backend está sirviendo datos antiguos desde almacenamiento local (`local-snapshot-storage`) incluso cuando el snapshot tiene varias horas de antigüedad. Eso rompe el objetivo de mostrar la situación actual de los servidores. El frontend no debe depender de un snapshot viejo si el backend puede consultar el estado real de los servidores en ese momento.

## Steps
1. Revisar la implementación actual de:
   - `GET /api/servers`
   - carga de snapshots persistidos
   - lógica de refresco objetivo a 120 s
   - consulta real A2S o equivalente que ya exista en el backend
2. Identificar por qué el backend está devolviendo snapshots antiguos sin forzar actualización.
3. Ajustar la lógica para que:
   - si el snapshot actual tiene menos de 120 s, pueda reutilizarse
   - si el snapshot actual supera 120 s, el backend intente una consulta real inmediata de los 2 servidores antes de responder
4. Si la consulta real tiene éxito:
   - persistir el nuevo snapshot
   - devolver ese snapshot fresco al frontend
5. Si la consulta real falla:
   - devolver el último snapshot válido disponible
   - marcar claramente en el payload que el dato es stale o desactualizado
6. Asegurar que el payload de `/api/servers` incluya campos claros para frontend, como por ejemplo:
   - `last_snapshot_at`
   - indicador de stale/fresh
   - edad del snapshot en segundos o minutos
   - origen real del dato devuelto
7. Ajustar el frontend solo si hace falta para que:
   - no presente como “actual” un snapshot viejo
   - pueda mostrar una nota honesta si el dato está desactualizado
8. Mantener el alcance centrado en datos actuales de los 2 servidores reales de la comunidad.
9. No reintroducir servidores ficticios o de referencia ajenos a la comunidad.
10. Al completar la implementación, dejar el repositorio en estado consistente y preparado para integración.
11. Hacer commit de los cambios realizados y hacer push al repositorio remoto siguiendo el workflow del proyecto, siempre que el entorno tenga permisos y configuración git disponibles.

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- docs/frontend-backend-contract.md
- docs/current-hll-servers-source-plan.md
- backend/README.md
- backend/app/__init__.py
- backend/app/main.py
- backend/app/routes.py
- backend/app/payloads.py
- backend/app/config.py
- cualquier servicio o módulo de collector/query ya existente en `backend/app/`
- frontend/index.html
- frontend/assets/js/main.js
- frontend/assets/css/styles.css

## Expected Files to Modify
- backend/app/routes.py
- backend/app/payloads.py
- backend/app/config.py
- backend/app/main.py
- opcionalmente uno o más archivos de servicio existentes del backend si ahí vive la lógica de snapshots o de consulta real
- frontend/assets/js/main.js
- opcionalmente frontend/index.html y frontend/assets/css/styles.css si hace falta ajustar el estado visual stale/fresh
- backend/README.md si el comportamiento operativo cambia

## Constraints
- No reintroducir servidores ficticios.
- No usar datos viejos como si fueran datos actuales.
- No consultar fuentes externas directamente desde frontend.
- Mantener la arquitectura frontend → backend → consulta real/persistencia.
- No romper el fallback si la consulta real falla.
- No hacer cambios destructivos.
- Mantener la solución centrada en los 2 servidores reales de la comunidad.
- Si el entorno no permite push, dejar el commit local realizado e informar claramente de ello en el resumen final.

## Validation
- Si el snapshot persistido tiene más de 120 s, `/api/servers` intenta refrescarlo antes de responder.
- Si la consulta real tiene éxito, el frontend recibe datos actuales de los 2 servidores reales.
- Si la consulta real falla, el backend devuelve el último snapshot válido con una indicación clara de dato stale.
- La UI no presenta como actual un snapshot antiguo.
- No aparecen servidores ajenos a la comunidad.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 8 archivos modificados o creados.
- Preferir menos de 320 líneas cambiadas.
## Outcome
- `backend/app/payloads.py` deja de servir `/api/servers` como simple lectura del ultimo snapshot persistido: ahora reutiliza cache solo si sigue dentro del objetivo de `120` segundos y, si no, intenta un refresco A2S inmediato antes de responder.
- El payload principal de `/api/servers` ahora expone `last_snapshot_at`, `snapshot_age_seconds`, `snapshot_age_minutes`, `max_snapshot_age_seconds`, `is_stale`, `freshness`, `source`, `refresh_attempted`, `refresh_status` y `refresh_errors`.
- Si el refresco real falla, backend devuelve el ultimo snapshot valido con marca clara de dato stale; si no existe snapshot valido, responde `items: []` en vez de reintroducir servidores ficticios o de referencia.
- `frontend/assets/js/main.js` usa la metadata de frescura del backend para no presentar un snapshot viejo como si fuera actual y muestra una nota honesta cuando el dato esta desactualizado.
- `backend/README.md` y `docs/frontend-backend-contract.md` quedan alineados con el comportamiento real del endpoint.

## Validation Result
- Validado con `python -m py_compile backend/app/config.py backend/app/payloads.py backend/app/routes.py backend/app/main.py`.
- Validado con `node --check frontend/assets/js/main.js`.
- Validado con una comprobacion local desde Python que cubre tres rutas de `build_servers_payload()`: refresco real exitoso, fallo de refresco con fallback stale al ultimo snapshot valido y ausencia total de snapshot valido.
- Validado ejecutando `build_servers_payload()` contra el entorno actual: el backend devolvio `source: "real-time-a2s-refresh"`, `freshness: "fresh"` e `item_count: 2`.
- Revisado en `git diff --name-only`: el alcance queda limitado a la task, documentacion del contrato/backend, frontend del panel de servidores y backend de payload/config, ademas de archivos ya presentes en el worktree (`ai/worker.lock` y `backend/data/hll_vietnam_dev.sqlite3`).

## Decision Notes
- `/api/servers` se mantiene como endpoint principal para la landing y pasa a tratar la persistencia local como cache, no como fuente autoritativa cuando el snapshot ya vencio.
- Se elimina el uso de respaldo controlado en este endpoint cuando no hay snapshot valido disponible para cumplir la restriccion de no reintroducir servidores ajenos a la comunidad.
