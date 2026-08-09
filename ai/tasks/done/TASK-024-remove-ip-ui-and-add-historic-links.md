# TASK-024-remove-ip-ui-and-add-historic-links

## Goal
Eliminar de la landing toda referencia visible a IP o direccion de servidor y sustituir el boton actual por un boton `Historico` que lleve a la pagina de historial correcta de cada uno de los 2 servidores reales de la comunidad.

## Context
La UI actual del bloque de servidores sigue mostrando informacion relacionada con IP/direccion y un CTA heredado que ya no encaja con el comportamiento deseado. A partir de ahora no debe mostrarse nada relacionado con IP en la pagina. En su lugar, cada card de servidor debe incluir un boton `Historico` que abra la pagina de historial correspondiente al servidor real de la comunidad.

Los destinos correctos son:
- Servidor `#01 [ESP] Comunidad Hispana - discord.comunidadhll.es - Spa Onl` -> `https://scoreboard.comunidadhll.es/games`
- Servidor `#02 [ESP] Comunidad Hispana - discord.comunidadhll.es - Spa Onl` -> `https://scoreboard.comunidadhll.es:5443/games`

La solucion debe usar una asignacion estable basada en la identidad real de cada servidor de la comunidad y no depender de mostrar IP en la UI.

## Steps
1. Revisar la implementacion actual del bloque de servidores en:
   - HTML estatico/fallback
   - renderizado hidratado desde JS
   - payload y campos expuestos desde backend si afectan a la UI
2. Eliminar de la UI cualquier referencia visible a:
   - IP
   - direccion
   - host:puerto
   - textos como `Direccion`
   - acciones tipo `Copiar IP`
3. Sustituir el CTA actual de cada card por un boton `Historico`.
4. Hacer que el boton `Historico` abra el destino correcto segun el servidor:
   - servidor #01 -> `https://scoreboard.comunidadhll.es/games`
   - servidor #02 -> `https://scoreboard.comunidadhll.es:5443/games`
5. Asegurar que la asignacion se basa en la identidad estable del servidor de comunidad y no en una logica fragil o dependiente del orden accidental.
6. Mantener la compatibilidad entre:
   - fallback estatico
   - renderizado dinamico por JS
7. Si la UI actual necesita un campo alternativo donde antes estaba la IP, reorganizar la card para que siga viendose equilibrada sin exponer datos de red.
8. Mantener visibles solo los 2 servidores reales de la comunidad.
9. No reintroducir servidores ficticios ni CTAs rotos.
10. Verificar que los enlaces abren correctamente las paginas de historico en una nueva pestana o de la forma UX mas segura/coherente con la landing.
11. Al completar la implementacion:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- frontend/index.html
- frontend/assets/js/main.js
- frontend/assets/css/styles.css
- backend/app/payloads.py
- backend/app/routes.py
- docs/frontend-backend-contract.md

## Expected Files to Modify
- frontend/index.html
- frontend/assets/js/main.js
- frontend/assets/css/styles.css
- opcionalmente backend/app/payloads.py si hace falta exponer un identificador mas limpio para mapear cada servidor a su historico
- opcionalmente documentacion minima si cambia el comportamiento esperado del CTA del panel

## Constraints
- No mostrar IP, direccion o datos equivalentes en la UI.
- No dejar botones rotos.
- No cambiar los 2 servidores reales de la comunidad.
- No anadir librerias nuevas.
- No romper el polling ni la hidratacion actual.
- No romper el fallback estatico.
- No hacer cambios destructivos.
- Mantener la solucion visualmente coherente con la landing.

## Validation
- Ya no aparece ningun dato de IP/direccion en la UI del bloque de servidores.
- El boton `Copiar IP` desaparece por completo.
- Cada servidor muestra un boton `Historico`.
- El boton del servidor #01 abre `https://scoreboard.comunidadhll.es/games`.
- El boton del servidor #02 abre `https://scoreboard.comunidadhll.es:5443/games`.
- La asignacion es estable tanto en fallback estatico como en renderizado dinamico.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 5 archivos modificados.
- Preferir menos de 200 lineas cambiadas.

## Outcome
- `frontend/index.html` elimina la IP visible del fallback estatico y sustituye el CTA por enlaces `Historico` hacia el scoreboard correcto de cada servidor real.
- `frontend/assets/js/main.js` deja de renderizar direccion o acciones de copiado y asigna cada enlace de historico mediante `external_server_id` estable.
- `frontend/assets/css/styles.css` adapta el estilo del CTA para mantener la tarjeta equilibrada sin exponer datos de red.

## Validation Result
- Validado con `node --check frontend/assets/js/main.js`.
- Verificado con `rg` que ya no quedan en `frontend/` textos o atributos de `Copiar IP`, `Direccion`, `data-copy-address`, `server-copy-button` ni las IPs de los servidores.
- Revisado con `git diff --name-only`: el cambio de esta task queda acotado a `frontend/index.html`, `frontend/assets/js/main.js`, `frontend/assets/css/styles.css` y este archivo de task.

## Decision Notes
- La asignacion del enlace `Historico` en renderizado dinamico se resuelve unicamente con `external_server_id` para evitar dependencia del orden accidental o de datos de red expuestos en UI.
