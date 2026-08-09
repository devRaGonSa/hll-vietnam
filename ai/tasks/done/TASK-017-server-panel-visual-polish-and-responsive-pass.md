# TASK-017-server-panel-visual-polish-and-responsive-pass

## Goal
Pulir visualmente el panel de servidores actuales de Hell Let Loose y mejorar su comportamiento responsive para que se integre mejor con el resto de la landing y se vea claro, ordenado y fiable.

## Context
El panel de servidores ya existe y consume datos del backend placeholder con fallback estatico. Ahora hace falta una pasada especifica de UI para que las tarjetas o elementos del panel tengan una presentacion mas clara y mas profesional, sin tocar todavia estrategia de copy ni fuentes reales de datos.

## Steps
1. Revisar el marcado actual del panel de servidores en la landing.
2. Revisar como se renderizan los datos desde frontend.
3. Mejorar visualmente:
   - tarjetas o filas de servidor
   - jerarquia de nombre, estado, jugadores y mapa
   - badges o indicadores de estado
   - separacion entre items
   - integracion con el resto de la landing
4. Mejorar el comportamiento responsive del panel:
   - anchuras
   - apilado
   - legibilidad en movil
   - consistencia de espaciados
5. Mantener claro que se trata de un bloque provisional sin tocar todavia el copy estrategico en profundidad.
6. Respetar el fallback actual si el backend no responde.
7. No cambiar el alcance funcional del panel.

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- frontend/index.html
- frontend/assets/css/styles.css
- frontend/assets/js/main.js
- backend/app/payloads.py

## Expected Files to Modify
- frontend/index.html
- frontend/assets/css/styles.css
- frontend/assets/js/main.js

## Constraints
- No cambiar el contrato del backend.
- No tocar payloads backend.
- No anadir librerias nuevas.
- No romper el fallback estatico.
- No presentar estos servidores como si fueran de HLL Vietnam.
- No hacer cambios destructivos.
- Mantener el ajuste centrado en UI y responsive.

## Validation
- El panel de servidores se ve mas limpio y claro.
- La lectura de estado, jugadores y mapa mejora.
- El panel responde bien en movil y escritorio.
- El fallback sigue funcionando.
- La integracion visual con la landing es mejor que antes.

## Change Budget
- Preferir menos de 3 archivos modificados.
- Preferir menos de 200 lineas cambiadas.

## Outcome
- Se mejoro la jerarquia visual de cada servidor con identidad, estado mas legible y mejor separacion entre bloques de datos.
- Se anadio un indicador visual de ocupacion basado en los datos ya disponibles sin cambiar el contrato del backend.
- Se alineo el markup estatico de `index.html` con el render dinamico de `main.js` para mantener el mismo acabado cuando el backend esta disponible o no.

## Validation Notes
- `git diff --name-only -- frontend/index.html frontend/assets/css/styles.css frontend/assets/js/main.js` devuelve solo los archivos esperados por la task.
- `node --check frontend\\assets\\js\\main.js` se ejecuto correctamente.
- No se modifico `backend/app/payloads.py` ni el contrato del backend.
- El fallback estatico se conserva porque el HTML base y el render dinamico usan la misma estructura visual del panel.
