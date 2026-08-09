# TASK-014-landing-current-hll-servers-panel

## Goal
Añadir a la landing de HLL Vietnam un panel visual de servidores actuales de Hell Let Loose, alimentado por el backend placeholder, dejando claro que se trata de contenido provisional mientras no existan datos reales de HLL Vietnam.

## Context
La landing ya dispone de una mejora progresiva frontend-backend y el backend puede exponer endpoints placeholder. El proyecto necesita empezar a mostrar información más útil y dinámica, pero sin fingir que ya existen servidores de HLL Vietnam. Esta task debe introducir un bloque visual controlado que muestre servidores actuales de HLL como referencia provisional para la comunidad.

## Steps
1. Revisar la landing actual, los estilos y la mejora progresiva ya implementada en frontend.
2. Revisar el payload real o previsto de `GET /api/servers`.
3. Añadir un bloque visual nuevo en la landing para mostrar servidores actuales de Hell Let Loose.
4. Hacer que el frontend consuma `GET /api/servers` de forma progresiva, manteniendo fallback seguro si el backend no está disponible.
5. Mostrar de forma clara y ordenada, como mínimo:
   - nombre del servidor
   - estado
   - jugadores
   - capacidad máxima
   - mapa si está disponible
6. Añadir una etiqueta o texto breve que deje claro que son servidores actuales de Hell Let Loose usados como referencia provisional.
7. Mantener coherencia visual con la identidad militar sobria del proyecto.
8. Asegurar que la landing siga funcionando si el backend no responde o si no hay datos.
9. No tocar todavía integración real de Discord ni fuentes externas reales.

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- docs/frontend-backend-contract.md
- docs/frontend-data-consumption-plan.md
- docs/current-hll-servers-source-plan.md
- frontend/index.html
- frontend/assets/js/main.js
- frontend/assets/css/styles.css
- backend/app/routes.py
- backend/app/payloads.py

## Expected Files to Modify
- frontend/index.html
- frontend/assets/js/main.js
- frontend/assets/css/styles.css
- opcionalmente documentación mínima si fuera necesario reflejar el nuevo bloque

## Constraints
- No rediseñar completamente la landing.
- No añadir librerías nuevas.
- No romper el fallback estático actual.
- No presentar esos servidores como si fueran de HLL Vietnam.
- No integrar fuentes externas reales directamente desde frontend.
- No hacer cambios destructivos.
- Mantener la mejora acotada, clara y coherente con la fase actual.

## Validation
- La landing muestra un panel de servidores actuales de HLL de forma clara.
- El panel obtiene datos desde `GET /api/servers` cuando el backend está disponible.
- Si el backend no está disponible, la landing sigue funcionando sin romperse.
- La UI deja claro que se trata de contenido provisional.
- La integración visual es coherente con el resto de la página.

## Change Budget
- Preferir menos de 4 archivos modificados.
- Preferir menos de 220 líneas cambiadas.
