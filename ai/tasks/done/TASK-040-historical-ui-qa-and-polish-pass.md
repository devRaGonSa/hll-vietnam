# TASK-040-historical-ui-qa-and-polish-pass

## Goal
Realizar una pasada final de QA y pulido sobre la nueva capa histórica del proyecto, tanto en backend como en la UI histórica propia, antes de abrir futuras métricas más avanzadas.

## Context
Tras añadir varias capas históricas de API y UI, conviene consolidar la calidad del resultado antes de seguir creciendo. Esta task debe centrarse en detectar pequeños defectos de presentación, consistencia, navegación, payload o comportamiento.

## Steps
1. Revisar la UI histórica completa y los endpoints históricos ya expuestos.
2. Validar:
   - weekly top kills
   - partidas recientes
   - resumen histórico si existe
   - navegación histórica
3. Revisar:
   - estados de loading/error/empty
   - consistencia de servidor seleccionado
   - consistencia de naming
   - legibilidad de tablas/listados
   - responsive básico
4. Corregir pequeños defectos o inconsistencias detectadas.
5. No abrir rediseños grandes en esta task.
6. Al completar la implementación:
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
- frontend/index.html
- frontend/assets/css/styles.css

## Expected Files to Modify
- frontend/historico.html
- frontend/assets/js/historico.js
- frontend/assets/css/historico.css
- backend/app/routes.py
- backend/app/payloads.py
- opcionalmente documentación mínima si alguna parte visible necesita quedar reflejada

## Constraints
- No abrir nuevas grandes features históricas en esta task.
- No depender de UI externa.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en QA y acabado.

## Validation
- La capa histórica propia funciona con consistencia suficiente.
- La UI histórica está pulida y usable.
- No hay defectos relevantes en el flujo principal.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 6 archivos modificados.
- Preferir menos de 220 líneas cambiadas.
## Outcome
- Se revisÃ³ la consistencia entre selector de servidor, resumen, ranking semanal y partidas recientes.
- Se ajustaron estados visibles de loading, error y vacÃ­o en la vista histÃ³rica.
- Se aÃ±adieron ajustes responsive bÃ¡sicos en `frontend/assets/css/historico.css`.
- No se abrieron features histÃ³ricas grandes fuera del alcance de QA y acabado.

## Validation Notes
- `python -m compileall app`
- `node --check frontend/assets/js/historico.js`
- comprobaciÃ³n local de payloads histÃ³ricos: weekly top kills, recent matches, server summary y player profile
