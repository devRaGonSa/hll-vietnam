# TASK-101-remove-false-rcon-first-claims-and-fix-operational-visibility

## Goal
Alinear documentación, outputs operativos y visibilidad de progreso con el comportamiento real del sistema, evitando afirmaciones engañosas sobre histórico RCON-first y mejorando la operativa del refresh manual.

## Context
Actualmente el operador puede pensar que la ingesta histórica ya va por RCON cuando en realidad el writer path sigue cayendo a scoreboard.
Además, el comando de refresh es demasiado opaco: tarda mucho y no ofrece progreso útil.

## Steps
1. Auditar:
   - `backend/README.md`
   - `backend/app/historical_ingestion.py`
   - outputs/logs relevantes
2. Corregir cualquier copy/documentación que sugiera que la ingesta histórica completa ya está en RCON si no es cierto.
3. Añadir progreso operativo útil al refresh manual:
   - servidor actual
   - página actual
   - número de match ids a detallar
   - fuente realmente seleccionada
4. Hacer que, cuando haya fallback a scoreboard, eso quede visible para el operador en tiempo real o en el payload final.
5. Mantener la salida usable, sin inundar de logs innecesarios.
6. Actualizar runbook con recomendaciones reales para pasadas manuales y límites razonables.

## Constraints
- No convertir el comando en un spam de logs.
- No ocultar fallbacks reales.
- No mezclar esta task con grandes cambios de UI frontend.

## Validation
- El operador puede ver progreso útil durante un refresh.
- La fuente usada de verdad queda visible.
- La documentación ya no induce a error.
- El repositorio queda consistente.

## Expected Files
- `backend/app/historical_ingestion.py`
- `backend/README.md`
