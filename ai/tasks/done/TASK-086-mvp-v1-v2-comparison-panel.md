# TASK-086-mvp-v1-v2-comparison-panel

## Goal
Añadir una comparación ligera y comprensible entre MVP V1 y MVP V2 para facilitar validación de producto antes de decidir sustitución o convergencia.

## Context
La V2 ya calcula y sirve rankings distintos. Antes de reemplazar la V1, interesa poder comparar visualmente diferencias de forma controlada.

## Steps
1. Revisar la UI resultante tras la task anterior.
2. Diseñar un panel simple de comparación V1 vs V2.
3. Mostrar diferencias comprensibles, por ejemplo:
   - posición V1 vs posición V2
   - teamkill penalty
   - cambio relativo de score
4. Mantener la comparación ligera y orientada a validación, no a saturar la página.
5. No fusionar todavía V1 y V2 en una sola fórmula visible.
6. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- frontend/historico.html
- frontend/assets/js/historico.js
- frontend/assets/css/historico.css
- docs/monthly-mvp-ranking-scoring-design.md
- docs/monthly-mvp-v2-scoring-design.md

## Expected Files to Modify
- frontend/historico.html
- frontend/assets/js/historico.js
- frontend/assets/css/historico.css

## Constraints
- No eliminar todavía la V1.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en comparación y validación de producto.

## Validation
- Existe una comparación ligera V1 vs V2 entendible.
- No se rompe la UI histórica.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 4 archivos modificados o creados.
- Preferir menos de 180 líneas cambiadas.
