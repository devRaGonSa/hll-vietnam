# TASK-035-historical-ui-after-bootstrap-review

## Goal
Revisar y ajustar la UI histórica propia del proyecto una vez que el bootstrap histórico completo y la semántica de cobertura estén resueltos, para asegurar que el resultado final sea visualmente claro, útil y coherente con el resto del producto.

## Context
La UI histórica ya existe, pero fue construida antes de confirmar que la cobertura histórica completa estuviera realmente cargada y antes de clarificar suficientemente la semántica entre resumen y ranking semanal. Una vez el histórico esté bien poblado y la capa semántica corregida, hace falta una pasada de revisión específica sobre la experiencia visual e informativa de la página histórica.

## Steps
1. Revisar la UI histórica actual después del bootstrap completo y de los ajustes de semántica/cobertura.
2. Validar el comportamiento visual y de contenido de:
   - resumen de servidor
   - ranking semanal
   - selector de servidor
   - estado vacío/error/carga
   - cualquier otro bloque histórico ya presente
3. Comprobar si el volumen real de datos cambia la lectura de la interfaz y obliga a reajustar:
   - textos
   - jerarquía
   - espaciado
   - orden de secciones
   - presentación de métricas
4. Corregir defectos pequeños o medianos detectados en esta revisión.
5. Asegurar que la UI histórica:
   - sea comprensible
   - no sobreinterprete los datos
   - mantenga coherencia visual con la landing
6. No abrir todavía nuevas features históricas grandes en esta task.
7. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- docs/historical-data-quality-notes.md
- docs/historical-coverage-report.md
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
- opcionalmente frontend/index.html o frontend/assets/css/styles.css si hace falta un ajuste menor de acceso o coherencia visual
- opcionalmente documentación mínima si algún comportamiento visible necesita quedar reflejado

## Constraints
- No crear nuevas páginas basadas en URLs externas.
- No abrir nuevas grandes features históricas.
- No romper la UI histórica existente.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en revisión final, claridad y pulido después del bootstrap real.

## Validation
- La UI histórica refleja correctamente el histórico ya poblado.
- La presentación del resumen y del ranking es clara.
- La experiencia visual es coherente con el resto del proyecto.
- No se detectan malentendidos graves entre cobertura histórica y ranking semanal.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 5 archivos modificados o creados.
- Preferir menos de 200 líneas cambiadas.
