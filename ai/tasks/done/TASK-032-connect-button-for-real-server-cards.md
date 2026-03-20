# TASK-032-connect-button-for-real-server-cards

## Goal
Añadir en la web un botón de conexión directa `steam://connect/...` para tarjetas de servidores reales, usando el game port correcto y manteniendo el comportamiento actual del panel de servidores.

## Context
La landing ya muestra snapshots reales A2S y distingue entre datos reales, históricos y fallback. Además, ya se han verificado servidores reales de Comunidad Hispana con separación entre game port y query port. El siguiente paso útil para producto es añadir un botón Connect en las tarjetas de servidores reales para permitir una acción directa desde la web.

## Steps
1. Revisar el frontend actual y cómo se renderizan las tarjetas de servidores.
2. Revisar el backend y comprobar si el frontend dispone actualmente del `game_port` necesario para construir `steam://connect/...`.
3. Si el dato no está disponible en los payloads actuales, ajustar la capa backend mínima necesaria para exponerlo de forma clara y estable.
4. Añadir un botón Connect solo cuando la tarjeta represente un servidor real con datos suficientes.
5. Usar siempre el `game_port`, nunca el `query_port`.
6. Mantener el botón visualmente coherente con la landing actual.
7. Preservar el fallback actual si un servidor no tiene datos reales o no dispone de `game_port`.
8. Validar que los enlaces queden correctos al menos para:
   - Comunidad Hispana #01 → `steam://connect/152.114.195.174:7777`
   - Comunidad Hispana #02 → `steam://connect/152.114.195.150:7877`

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- frontend/index.html
- frontend/assets/js/main.js
- frontend/assets/css/styles.css
- backend/app/routes.py
- backend/app/payloads.py
- backend/app/server_targets.py
- backend/README.md

## Expected Files to Modify
- frontend/index.html
- frontend/assets/js/main.js
- frontend/assets/css/styles.css
- backend/app/routes.py
- backend/app/payloads.py
- opcionalmente backend/app/server_targets.py si hace falta alinear metadata

## Constraints
- No rediseñar toda la landing.
- No romper el fallback actual.
- No usar `query_port` para el enlace de conexión.
- No añadir librerías nuevas.
- No hacer cambios destructivos.
- Mantener la mejora centrada en el panel de servidores y acción de conexión.

## Validation
- Las tarjetas de servidores reales muestran un botón Connect cuando corresponde.
- El enlace de conexión usa `steam://connect/<host>:<game_port>`.
- Los placeholders o tarjetas sin datos reales no rompen el render.
- La mejora visual se integra con la landing actual.

## Change Budget
- Preferir menos de 5 archivos modificados.
- Preferir menos de 180 líneas cambiadas.
## Outcome
- `backend/app/payloads.py` enriquece los snapshots reales con `host`, `query_port` y `game_port` a partir del registro A2S ya verificado, sin tocar la persistencia.
- `frontend/assets/js/main.js` muestra un boton `Connect` solo para tarjetas `real-a2s` que dispongan de `host` y `game_port`, generando `steam://connect/<host>:<game_port>`.
- `frontend/assets/css/styles.css` integra visualmente la nueva accion sin redisenar el panel ni afectar placeholders.

## Validation Result
- Ejecutado desde `backend/`: comprobacion de `build_server_latest_payload()` sobre `comunidad-hispana-01` y `comunidad-hispana-02`.
- Resultado: ambos snapshots reales exponen `host`, `query_port` y `game_port`, conservando `snapshot_origin=real-a2s`.
- Ejecutado desde `backend/`: validacion de enlaces esperados `steam://connect/152.114.195.174:7777` y `steam://connect/152.114.195.150:7877`.
- Resultado: los enlaces calculados coinciden exactamente con los valores requeridos para `#01` y `#02`.

## Decision Notes
- Se evita duplicar `host` y `game_port` en SQLite porque ya existen como metadata estable del target A2S y basta con enriquecer el payload de lectura.
