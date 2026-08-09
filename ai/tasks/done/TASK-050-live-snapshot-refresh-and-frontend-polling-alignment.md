# TASK-050-live-snapshot-refresh-and-frontend-polling-alignment

## Goal
Alinear la captura periodica de snapshots y el consumo del frontend para que la web muestre datos mucho mas cercanos al estado real actual de los servidores, evitando que se queden estancados durante horas.

## Context
La pagina ya consume datos reales A2S, pero en la practica estaba mostrando snapshots demasiado antiguos, con mapas y poblacion desactualizados. Esto degrada la percepcion de fiabilidad del producto. El sistema necesitaba una politica mas util de refresco local y una lectura periodica razonable desde frontend.

## Steps
1. Revisar como se ejecuta actualmente el scheduler local de snapshots.
2. Revisar la frecuencia de captura actual o la ausencia de ejecucion continua.
3. Definir una frecuencia de refresco razonable para entorno local de desarrollo y demo, por ejemplo:
   - captura backend cada 60 segundos
   - refresco frontend cada 60-90 segundos
4. Ajustar el scheduler o su configuracion para facilitar un refresco frecuente y controlado.
5. Revisar el frontend para que vuelva a consultar el backend periodicamente sin necesidad de recargar la pagina.
6. Asegurar que el refresco no rompa la UI ni genere comportamiento agresivo.
7. Mantener el sistema simple y apropiado para la fase actual.
8. Documentar claramente como arrancar el backend y el refresco para ver datos vivos.

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- backend/README.md
- backend/app/config.py
- backend/app/scheduler.py
- backend/app/collector.py
- frontend/assets/js/main.js
- frontend/index.html

## Expected Files to Modify
- backend/README.md
- backend/app/config.py
- backend/app/scheduler.py
- frontend/assets/js/main.js
- opcionalmente frontend/index.html si requiere una alineacion minima

## Constraints
- No introducir infraestructura pesada.
- No anadir librerias nuevas.
- No hacer cambios destructivos.
- No abrir nuevas fuentes de datos.
- Mantener la solucion simple, local y util para producto actual.

## Validation
- El sistema puede refrescar snapshots reales con una frecuencia razonable.
- El frontend actualiza la vista sin depender de recarga manual.
- Los mapas y jugadores cambian cuando cambian realmente en los servidores.
- La documentacion deja claro como usar este flujo en local.

## Change Budget
- Preferir menos de 5 archivos modificados.
- Preferir menos de 180 lineas cambiadas.

## Outcome
- `backend/app/config.py` baja el intervalo por defecto del scheduler local a `60` segundos para acercar la persistencia a una demo viva.
- `backend/app/scheduler.py` alinea la ayuda del comando con ese nuevo comportamiento orientado a desarrollo y demo.
- `frontend/index.html` expone `data-server-refresh-ms=\"60000\"` y `frontend/assets/js/main.js` reutiliza ese valor para relanzar `hydrateServers()` cada `60` segundos sin recargar la pagina y sin solapar peticiones.
- `backend/README.md` documenta el flujo local recomendado con backend, scheduler y polling del frontend.

## Validation Result
- Validado con `node --check frontend/assets/js/main.js`.
- Validado con `python -m py_compile backend/app/config.py backend/app/scheduler.py backend/app/collector.py`.
- Revisado en diff: la task queda limitada a `backend/README.md`, `backend/app/config.py`, `backend/app/scheduler.py`, `frontend/assets/js/main.js`, `frontend/index.html` y este archivo de task.

## Decision Notes
- Se mantuvo el polling solo sobre el bloque de servidores para no convertir toda la landing en una pagina con refresco agresivo. Salud del backend y trailer siguen siendo una hidratacion inicial simple.
