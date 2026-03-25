# TASK-085-monthly-mvp-v2-ui

## Goal
Exponer en la UI histórica el Top MVP mensual V2 y sus señales avanzadas básicas, manteniéndolo explícitamente separado del MVP V1.

## Context
El backend ya tiene:
- monthly-mvp-v2 por servidor y global
- snapshots V2 player-events
- scoring V2 operativo
- señales útiles para teamkills, most-killed, death-by, duels y weapon-kills

Ahora hace falta llevar esa V2 a la página histórica sin sustituir todavía la V1.

## Steps
1. Revisar:
   - frontend/historico.html
   - frontend/assets/js/historico.js
   - frontend/assets/css/historico.css
   - backend endpoints ya disponibles
2. Añadir una sección o bloque claro de MVP mensual V2.
3. Mantener convivencia explícita entre:
   - MVP V1
   - MVP V2
4. Mostrar al menos:
   - Top 3 o Top N V2
   - score V2
   - teamkill penalty
   - una o dos señales avanzadas resumidas (por ejemplo most_killed_count, duel_control_raw o arma destacada si el payload ya la ofrece)
5. Diseñar estados vacíos, loading y error correctos.
6. No eliminar ni romper la UI V1 existente.
7. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- backend/README.md
- backend/app/routes.py
- backend/app/payloads.py
- frontend/historico.html
- frontend/assets/js/historico.js
- frontend/assets/css/historico.css
- docs/monthly-mvp-v2-scoring-design.md

## Expected Files to Modify
- frontend/historico.html
- frontend/assets/js/historico.js
- frontend/assets/css/historico.css
- opcionalmente backend/README.md si conviene documentar el consumo UI

## Constraints
- No romper el MVP V1.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en la UI del MVP V2.
- Evitar mezclar V1 y V2 en un único bloque confuso.

## Validation
- La UI muestra correctamente MVP V2 por servidor y all-servers.
- Convive con V1.
- Los estados vacíos y de carga están resueltos.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 5 archivos modificados o creados.
- Preferir menos de 220 líneas cambiadas.
