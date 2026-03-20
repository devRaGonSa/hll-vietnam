# TASK-021-server-status-periodic-query-and-display

## Goal
Implementar una base funcional para consultar periódicamente el estado de los servidores y mostrar esos datos en la página, realizando snapshots de datos cada 2 minutos, sin usar capturas de imagen ni elementos manuales equivalentes.

## Context
Queda descartada cualquier idea de “captura manual” o de imagen estática para representar el estado de los servidores. Lo que se necesita es mostrar en la web la situación actual de los servidores mediante consultas de datos reales o semirrealistas desde backend. En esta fase, la web debe evolucionar hacia un modelo donde el backend consulta periódicamente la información de servidores, conserva el último snapshot útil y el frontend lo muestra de forma clara.

## Steps
1. Revisar el endpoint actual `GET /api/servers` y su implementación placeholder.
2. Revisar cómo se muestra actualmente el bloque de servidores en la landing.
3. Diseñar e implementar una base de consulta periódica de datos de servidores con una frecuencia objetivo de 2 minutos.
4. Hacer que el backend obtenga y conserve snapshots de datos con los campos necesarios para la UI. Incluir al menos:
   - nombre del servidor
   - estado online/offline
   - jugadores actuales
   - capacidad máxima
   - mapa actual si está disponible
   - región o etiqueta útil si existe
   - timestamp real del último snapshot de datos
5. Dejar claro en la implementación y en la UI que se trata de datos de estado de servidores, no de capturas de imagen.
6. Hacer que `GET /api/servers` devuelva el último snapshot útil con una estructura estable y preparada para frontend.
7. Ajustar el frontend para mostrar esos datos de forma clara en la landing.
8. Si el backend no puede obtener datos nuevos temporalmente, mantener el último snapshot válido o un fallback coherente sin romper la página.
9. Mostrar en la UI una referencia honesta del momento de actualización basada en datos reales del snapshot, no en texto ficticio.
10. Mantener el alcance razonable: consultas periódicas y presentación de datos, sin abrir todavía automatizaciones más complejas de observabilidad o infraestructura.

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- docs/frontend-backend-contract.md
- docs/discord-and-server-data-plan.md
- docs/current-hll-servers-source-plan.md
- backend/README.md
- backend/app/__init__.py
- backend/app/main.py
- backend/app/routes.py
- backend/app/payloads.py
- backend/app/config.py
- frontend/index.html
- frontend/assets/js/main.js
- frontend/assets/css/styles.css

## Expected Files to Modify
- backend/app/main.py
- backend/app/routes.py
- backend/app/payloads.py
- backend/app/config.py
- opcionalmente uno o más archivos nuevos de servicio dentro de `backend/app/`, por ejemplo:
  - backend/app/server_status_service.py
  - backend/app/server_queries.py
- frontend/index.html
- frontend/assets/js/main.js
- frontend/assets/css/styles.css
- backend/README.md
- opcionalmente documentación técnica si fuera necesario alinear el comportamiento real

## Constraints
- No usar capturas de imagen para representar el estado de servidores.
- No introducir texto temporal ficticio.
- No consultar fuentes externas directamente desde frontend.
- Mantener la arquitectura frontend → backend → fuente de datos.
- No romper el fallback actual si no hay datos disponibles.
- No hacer cambios destructivos.
- Mantener la solución clara, trazable y coherente con la fase del proyecto.

## Validation
- Existe una base de consulta periódica con objetivo de refresco cada 2 minutos.
- `GET /api/servers` devuelve un snapshot de datos de servidores con timestamp real del snapshot.
- La landing muestra esos datos en lugar de una “captura” manual o ficticia.
- Si falla la actualización, la web no se rompe.
- La UI muestra de forma honesta la actualización real del estado de servidores.
- No se introducen capturas de imagen como solución del problema.

## Change Budget
- Preferir menos de 8 archivos modificados o creados.
- Preferir menos de 320 líneas cambiadas.

## Outcome
- `backend/app/payloads.py` hace que `GET /api/servers` devuelva un snapshot coherente preparado para frontend: prioriza el ultimo snapshot A2S real persistido cuando existe y, si no existe ninguno, responde un respaldo controlado con `last_snapshot_at`.
- `backend/app/config.py` alinea la frecuencia objetivo de refresco local a `120` segundos.
- `frontend/assets/js/main.js` deja de depender de una segunda llamada a `/api/servers/latest` para el bloque principal y pinta directamente el snapshot devuelto por `/api/servers`, mostrando un estado honesto con timestamp real del snapshot.
- `frontend/index.html` ajusta el polling por defecto a `120000` ms y aclara que el bloque muestra snapshots de estado consultados desde backend.
- `backend/README.md` documenta el nuevo comportamiento de `/api/servers` y el intervalo de `120` segundos.

## Validation Result
- Validado con `python -m py_compile backend/app/config.py backend/app/payloads.py backend/app/routes.py backend/app/main.py`.
- Validado con `node --check frontend/assets/js/main.js`.
- Validado con `python -m app.collector --source controlled`, que persistio un snapshot controlado en `backend/data/hll_vietnam_dev.sqlite3`.
- Validado inspeccionando `build_servers_payload()` desde Python para confirmar que `/api/servers` devuelve `last_snapshot_at` e `items` listos para frontend.
- Revisado en diff: la task queda limitada a `backend/README.md`, `backend/app/config.py`, `backend/app/payloads.py`, `frontend/assets/js/main.js`, `frontend/index.html`, este archivo de task y la actualizacion de `backend/data/hll_vietnam_dev.sqlite3` causada por la validacion persistente.

## Decision Notes
- Se reutilizo la infraestructura de snapshots ya existente en lugar de introducir otro scheduler o un segundo endpoint principal para el estado visible en landing.
- `/api/servers` devuelve un unico conjunto coherente de items para evitar mezclar timestamps de fallback con tarjetas reales A2S en la UI.
