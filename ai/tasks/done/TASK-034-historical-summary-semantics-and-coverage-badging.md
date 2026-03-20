# TASK-034-historical-summary-semantics-and-coverage-badging

## Goal
Corregir la semántica del resumen histórico y de los indicadores visibles para que la UI y la API distingan claramente entre cobertura histórica importada y ventana temporal semanal, evitando interpretaciones erróneas como asumir que un número bajo de partidas representa una semana completa de actividad.

## Context
La UI histórica actual puede llevar a confusión porque el usuario puede interpretar ciertos resúmenes como si describieran una semana completa, cuando en realidad reflejan solo la cobertura actualmente persistida en base. Aunque el ranking semanal y el resumen de servidor son conceptos distintos, hoy esa diferencia no queda visual ni semánticamente lo bastante clara.

## Steps
1. Revisar el payload y la lógica actual del resumen histórico por servidor.
2. Revisar qué información muestra hoy la UI histórica sobre:
   - cobertura temporal
   - número de partidas
   - rango de fechas
   - ranking semanal
3. Definir una semántica clara para distinguir:
   - cobertura histórica importada
   - ventana semanal usada para rankings
   - resumen agregado del servidor
4. Ajustar el backend para exponer, si hace falta, campos más claros sobre cobertura histórica real, por ejemplo:
   - first_match_at
   - last_match_at
   - imported_matches_count
   - coverage_status
   - cualquier otro metadato útil y honesto
5. Ajustar la UI para que el usuario entienda correctamente:
   - qué parte es “últimos 7 días”
   - qué parte es “cobertura total importada”
   - cuándo la cobertura es parcial o insuficiente
6. Eliminar formulaciones ambiguas o visualmente engañosas.
7. Mantener la estética y coherencia de la UI histórica.
8. No abrir todavía nuevas grandes vistas históricas.
9. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- docs/historical-data-quality-notes.md
- docs/historical-coverage-report.md
- backend/README.md
- backend/app/routes.py
- backend/app/payloads.py
- backend/app/historical_storage.py
- frontend/historico.html
- frontend/assets/js/historico.js
- frontend/assets/css/historico.css

## Expected Files to Modify
- backend/app/routes.py
- backend/app/payloads.py
- backend/app/historical_storage.py
- frontend/historico.html
- frontend/assets/js/historico.js
- frontend/assets/css/historico.css
- opcionalmente backend/README.md o documentación técnica mínima si hace falta reflejar la nueva semántica

## Constraints
- No crear páginas usando la URL de la comunidad.
- No depender de HTML externo.
- No romper la UI histórica existente.
- No romper el ranking semanal.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en claridad semántica, payload y UI.

## Validation
- La UI ya no induce a interpretar mal la cobertura histórica.
- Queda clara la diferencia entre cobertura importada y ranking de la última semana.
- El resumen del servidor es más honesto y comprensible.
- El backend expone metadatos suficientes para soportar esa claridad.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 6 archivos modificados o creados.
- Preferir menos de 220 líneas cambiadas.
