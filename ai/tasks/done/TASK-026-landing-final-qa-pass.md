# TASK-026-landing-final-qa-pass

## Goal
Realizar una pasada final de QA funcional y visual sobre la landing actual de HLL Vietnam para detectar y corregir pequenos defectos de presentacion, consistencia o comportamiento antes de pasar a una nueva linea de trabajo mas analitica e historica.

## Context
La landing ya dispone de:
- hero estable
- CTA principal a Discord
- trailer
- panel de servidores con 2 servidores reales de la comunidad
- snapshots actuales con polling backend
- boton `Historico` funcional por servidor

Antes de entrar en la siguiente fase del proyecto (estadisticas e historico), conviene hacer una revision final de calidad sobre la version actual para corregir detalles pequenos de UX, responsive, textos, alineacion visual y funcionamiento de enlaces.

## Steps
1. Revisar la landing completa en su estado actual.
2. Validar el comportamiento y acabado de:
   - hero
   - CTA principal de Discord
   - trailer
   - panel de servidores
   - badges de actualizacion
   - botones `Historico`
3. Revisar posibles problemas pequenos como:
   - textos cortados o saltos raros
   - alineaciones inconsistentes
   - spacing irregular
   - badges o chips descompensados
   - estados visuales poco claros
   - fallback estatico vs UI hidratada con diferencias no deseadas
4. Revisar que los 2 botones `Historico` apunten correctamente a:
   - `https://scoreboard.comunidadhll.es/games`
   - `https://scoreboard.comunidadhll.es:5443/games`
5. Revisar que el badge de actualizacion use datos reales y no texto ficticio.
6. Revisar el comportamiento responsive basico de la landing.
7. Corregir unicamente defectos pequenos o medianos detectados en esta pasada.
8. No abrir redisenos grandes ni nuevos bloques funcionales.
9. Al completar la implementacion:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- frontend/index.html
- frontend/assets/css/styles.css
- frontend/assets/js/main.js
- backend/app/payloads.py
- backend/app/routes.py
- docs/frontend-backend-contract.md
- ai/repo-context.md

## Expected Files to Modify
- frontend/index.html
- frontend/assets/css/styles.css
- frontend/assets/js/main.js
- opcionalmente documentacion minima si se detecta que algun comportamiento visible necesita quedar reflejado

## Constraints
- No redisenar la landing completa.
- No cambiar la arquitectura backend actual.
- No introducir nuevas features grandes.
- No anadir librerias nuevas.
- No romper polling, snapshot o hidratacion actual.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en QA final y correcciones concretas.

## Validation
- La landing queda mas consistente y pulida.
- No hay defects visibles relevantes en el flujo principal.
- Los 2 servidores correctos siguen mostrandose.
- Los enlaces de `Historico` funcionan correctamente.
- El badge de actualizacion sigue reflejando un dato real.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 4 archivos modificados.
- Preferir menos de 180 lineas cambiadas.

## Outcome
- `frontend/index.html` alinea el polling visible de la landing con el backend a `120000` ms y aclara que el panel usa snapshots consultados desde backend.
- `frontend/assets/js/main.js` deja de insertar una segunda rejilla dentro de `#servers-list`, con lo que el fallback estatico y la UI hidratada comparten la misma estructura visual.
- El badge de actualizacion distingue snapshot fresco frente a snapshot stale usando el dato real `last_snapshot_at` y el flag `is_stale`.
- Se mantiene la ruta correcta de ambos botones `Historico` hacia los dos scoreboards de la comunidad.
- `frontend/assets/css/styles.css` corrige un detalle menor de consistencia en el bloque del CTA secundario de tarjetas.

## Validation Result
- Validado con `node --check frontend/assets/js/main.js`.
- Verificadas en codigo las URLs `https://scoreboard.comunidadhll.es/games` y `https://scoreboard.comunidadhll.es:5443/games` tanto en el fallback HTML como en el mapeo dinamico de `SERVER_HISTORY_URLS`.
- Verificado en fuente que `data-server-refresh-ms="120000"` queda alineado con el intervalo por defecto documentado para snapshots.
- Revisado `git diff --name-only`: el alcance queda limitado a `frontend/index.html`, `frontend/assets/js/main.js`, `frontend/assets/css/styles.css` y este archivo de task.

## Decision Notes
- La pasada de QA se limita a consistencia visual y semantica del estado visible; no abre nuevas features ni cambia el contrato backend.
- Para evitar otra divergencia entre fallback y estado hidratado, el contenedor `#servers-list` se mantiene como rejilla unica y la hidratacion solo reemplaza sus tarjetas internas.
