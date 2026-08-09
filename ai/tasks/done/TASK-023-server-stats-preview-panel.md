# TASK-023-server-stats-preview-panel

## Goal
Anadir a la web una primera visualizacion de estadisticas de servidores basada en datos persistidos, mostrando una vista previa util y controlada del historico sin convertir todavia la landing en una aplicacion compleja.

## Context
La landing ya dispone de un panel provisional de servidores y el backend va a disponer de persistencia local y consultas historicas minimas. Esta task debe conectar ambos mundos con una primera visualizacion ligera que confirme que el pipeline completo funciona.

## Steps
1. Revisar el frontend actual, el panel de servidores existente y el plan de consumo de datos.
2. Revisar los nuevos endpoints historicos del backend.
3. Disenar una mejora progresiva en frontend que pueda mostrar una vista previa de estadisticas sin romper la landing actual.
4. Mostrar como minimo algunos indicadores utiles, por ejemplo:
   - ultimo snapshot por servidor
   - hora de ultima actualizacion
   - evolucion basica de poblacion o actividad reciente
5. Mantener fallback seguro si el backend o los endpoints historicos no estan disponibles.
6. Integrar visualmente el bloque con el diseno actual sin redisenar toda la pagina.
7. No anadir todavia dashboards complejos, graficas pesadas ni navegacion nueva.

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- docs/frontend-data-consumption-plan.md
- docs/frontend-backend-contract.md
- frontend/index.html
- frontend/assets/js/main.js
- frontend/assets/css/styles.css
- backend/app/routes.py
- backend/app/payloads.py
- documentacion de endpoints historicos creada en la task anterior

## Expected Files to Modify
- frontend/index.html
- frontend/assets/js/main.js
- frontend/assets/css/styles.css
- opcionalmente documentacion minima si fuera necesario reflejar el nuevo bloque o comportamiento

## Constraints
- No redisenar completamente la landing.
- No anadir librerias nuevas.
- No romper el fallback actual.
- No introducir analitica visual compleja.
- No hacer cambios destructivos.
- Mantener la mejora contenida, clara y alineada con la fase actual.

## Validation
- La web puede mostrar una primera vista previa de estadisticas de servidores usando datos persistidos.
- El frontend sigue funcionando si el backend no esta disponible.
- La mejora visual se integra con la landing actual.
- El resultado demuestra que el flujo captura -> persistencia -> consulta -> visualizacion ya funciona.

## Change Budget
- Preferir menos de 4 archivos modificados.
- Preferir menos de 220 lineas cambiadas.

## Outcome
- El panel de servidores ahora puede mostrar una vista previa historica con resumen, ultima actualizacion y tendencia reciente por servidor.
- `frontend/assets/js/main.js` mantiene el bloque estatico como fallback y solo sustituye el contenido cuando los endpoints historicos responden correctamente.
- `frontend/index.html` anade un contenedor ligero para el resumen historico.
- `frontend/assets/css/styles.css` integra la nueva vista previa con el lenguaje visual tactico existente.

## Validation Result
- Ejecutado: `node --check frontend/assets/js/main.js`
- Resultado: sintaxis valida en el script principal del frontend.

## Decision Notes
- Se mantuvo la mejora dentro del panel de servidores ya existente para evitar una nueva seccion o un dashboard separado en esta fase.
