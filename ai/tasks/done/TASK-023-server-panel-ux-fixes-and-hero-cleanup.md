# TASK-023-server-panel-ux-fixes-and-hero-cleanup

## Goal
Corregir la UX del bloque de servidores y limpiar elementos visuales del hero de la landing, eliminando mensajes innecesarios, arreglando el CTA roto de conexion y dejando visible una referencia honesta de actualizacion del snapshot.

## Context
La landing ya muestra datos actuales de los 2 servidores reales de la comunidad, pero todavia hay varios problemas de UX y acabado:
- aparece un texto largo e innecesario bajo el titulo del bloque de servidores indicando que el backend no pudo refrescar y que muestra el ultimo snapshot valido
- el boton `Conectar` no funciona correctamente y muestra errores de conexion como los observados en Steam
- el badge superior derecho del bloque de servidores debe pasar a mostrar una referencia limpia tipo `Actualizado ...` con el momento real correspondiente
- en el hero deben eliminarse los pills `BACKEND OPERATIVO` y `COMUNIDAD TACTICA HISPANA`

La tarea debe dejar la UI mas limpia, mas honesta y sin CTAs rotos.

## Steps
1. Revisar la implementacion actual del bloque de servidores en frontend y el payload real de `/api/servers`.
2. Eliminar del bloque de servidores el texto:
   - `El backend no pudo refrescar ahora mismo y muestra el ultimo snapshot valido.`
   - `Captura: ...`
   o cualquier variante equivalente que recargue innecesariamente la UI.
3. Mantener la referencia temporal del snapshot unicamente en el badge superior derecho del bloque, sustituyendo el texto actual por un formato limpio tipo:
   - `Actualizado 20/3/26, 19:37`
   o equivalente coherente con el estilo visual actual.
4. Asegurar que el momento mostrado en ese badge viene de datos reales del snapshot/backend y no de texto ficticio.
5. Revisar la implementacion del boton `Conectar` de cada servidor.
6. Investigar por que el CTA actual produce el error observado y corregirlo si existe una forma fiable de conexion directa compatible con el flujo actual del proyecto.
7. Si la conexion directa no puede garantizarse de forma robusta con el comportamiento actual del juego/cliente, no dejar un boton roto:
   - sustituirlo por una accion segura y util
   - priorizar una UX que siempre funcione, por ejemplo `Copiar IP`, `Copiar direccion` o una variante equivalente basada en los datos reales del servidor
   - si se conserva una accion de conexion, debe quedar realmente funcional
8. Mantener el comportamiento de los 2 servidores reales de la comunidad y no reintroducir servidores ficticios.
9. En el hero, eliminar visualmente:
   - `BACKEND OPERATIVO`
   - `COMUNIDAD TACTICA HISPANA`
10. Mantener intactos:
   - logo
   - CTA principal de Discord
   - trailer
   - estructura general de la landing
11. Asegurar que los cambios funcionan tanto en la UI estatica como en la UI hidratada por JS.
12. Al completar la implementacion:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- docs/frontend-backend-contract.md
- frontend/index.html
- frontend/assets/js/main.js
- frontend/assets/css/styles.css
- backend/app/payloads.py
- backend/app/routes.py
- backend/README.md

## Expected Files to Modify
- frontend/index.html
- frontend/assets/js/main.js
- frontend/assets/css/styles.css
- opcionalmente backend/app/payloads.py si hace falta exponer mejor datos utiles para la UX del boton de servidor
- opcionalmente backend/README.md si cambia el comportamiento esperado del CTA de servidor

## Constraints
- No volver a introducir mensajes largos y tecnicos en la UI principal del bloque de servidores.
- No dejar CTAs rotos o engañosos.
- No presentar datos no reales.
- No añadir librerias nuevas.
- No romper el polling ni la hidratacion actual del bloque.
- No romper el fallback actual.
- No hacer cambios destructivos.
- Mantener la solucion clara, visualmente limpia y coherente con la landing.

## Validation
- Ya no aparece el texto largo bajo el titulo del bloque de servidores sobre fallo de refresh.
- El badge superior derecho muestra `Actualizado ...` con el momento real correspondiente al snapshot.
- El CTA de servidor deja de fallar:
  - o conecta correctamente
  - o se sustituye por una accion segura que si funciona
- Los 2 servidores reales de la comunidad siguen siendo los unicos mostrados.
- En el hero ya no aparecen `BACKEND OPERATIVO` ni `COMUNIDAD TACTICA HISPANA`.
- La landing mantiene coherencia visual y funcional.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 5 archivos modificados.
- Preferir menos de 220 lineas cambiadas.

## Outcome
- `frontend/index.html` elimina los pills del hero, retira el texto secundario bajo el bloque de servidores y alinea el fallback estatico con los 2 servidores reales de Comunidad Hispana.
- `frontend/assets/js/main.js` deja la referencia temporal del snapshot solo en el badge superior derecho usando `last_snapshot_at` real del backend y sustituye la CTA rota `Conectar` por una accion segura de `Copiar IP`.
- `frontend/assets/css/styles.css` adapta las tarjetas al nuevo CTA, elimina estilos ya innecesarios del layout anterior y mantiene la presentacion limpia en desktop y movil.

## Validation Result
- Validado con `node --check frontend/assets/js/main.js`.
- Verificado con busqueda en `frontend/` que ya no queda el texto largo del snapshot fallido ni `steam://connect`.
- Revisado con `git diff --name-only`: los cambios de esta task quedan limitados a `frontend/index.html`, `frontend/assets/js/main.js`, `frontend/assets/css/styles.css` y este archivo de task; permanecen sin tocar otros cambios locales ajenos.

## Decision Notes
- La conexion directa por `steam://connect/<host>:<game_port>` se retira de la UI porque no podia garantizarse como CTA robusta en el flujo actual; se prioriza una accion segura y util basada en los datos reales del backend.
