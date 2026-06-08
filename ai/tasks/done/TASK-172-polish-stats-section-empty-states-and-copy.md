---
id: TASK-172
title: Pulir estados UX de la sección Stats
status: done
type: frontend
team: Frontend Senior
supporting_teams: [Backend Senior, Disenador grafico, Experto en interfaz]
roadmap_item: foundation
priority: medium
---

# TASK-172 - Pulir estados UX de la sección Stats

## Goal

Pulir la experiencia de usuario de la sección Stats en estados vacíos y errores, manteniendo la funcionalidad actual y el contrato backend existente.

Preservar la identidad: comunidad hispana de HLL Vietnam con tono militar/Vietnam/táctico/sobrio y cambios progresivos del frontend.

## Context

Tras TASK-171, la sección Stats debe comunicar mejor:
- estados de backend no disponible,
- búsqueda sin resultados,
- jugador sin estadísticas,
- ranking anual listo pero vacío,
- ranking anual sin generar,
- y soporte inválido para métrica no soportada.

No se modifica la lógica de datos ni se crean nuevos endpoints.

## Steps

1. Confirmar la lectura de los archivos listados en "Files to Read First".
2. Revisar textos de estado actuales y su trazabilidad UX en `frontend/stats.html` y `frontend/assets/js/stats.js`.
3. Ajustar mensajes para que sean claros, consistentes y diferenciados entre:
   - backend no disponible
   - búsqueda sin resultados
   - jugador sin estadísticas
   - ranking anual listo sin items
   - ranking anual missing
   - métrica anual no soportada
4. Mantener HTML/CSS/JS vanilla y la estética actual.
5. Mantener cualquier cambio de texto o estado dentro de los ficheros de Scope.
6. Ejecutar validaciones mínimas de task: sintaxis, tests de integración y carga de frontend.

## Files to Read First

- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- docs/stats-section-functional-plan.md
- frontend/stats.html
- frontend/assets/js/stats.js
- frontend/assets/css/styles.css
- ai/tasks/done/TASK-171-validate-stats-section-with-backend-data.md

## Expected Files to Modify

- frontend/stats.html
- frontend/assets/js/stats.js
- frontend/assets/css/styles.css

## Constraints

- No crear endpoints.
- No modificar backend.
- No modificar base de datos.
- No cambiar la lógica de ranking.
- No reactivar Elo/MMR.
- No reintroducir Comunidad Hispana #03.
- No tocar:
  - frontend/assets/img/clans/bxb.png
  - frontend/assets/js/partida-actual.js

## Validation

Antes de completar la task, validar:
- `node --check frontend/assets/js/stats.js`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- servir frontend con `python -m http.server` y comprobar:
  - `stats.html` -> 200
  - `assets/js/stats.js` -> 200
- revisar `git diff --name-only` y confirmar scope.

## Outcome

### Status

Done

### Files modified

- frontend/stats.html
- frontend/assets/js/stats.js

### Estados y textos mejorados

1. Estado inicial:
   - Mensaje de inicio del buscador, ranking semanal/mensual y estado anual clarifica el flujo.
2. Backend no disponible:
   - Mensajes específicos para búsqueda/perfil y ranking anual.
3. Busqueda sin resultados:
   - Mensaje textual objetivo y sin ambiguedad.
4. Jugador sin estadisticas:
   - Mensaje de estado explicito y panel de resumen con warning.
5. Ranking anual ready pero vacio:
   - Distinguido de snapshot missing.
6. Ranking anual missing:
   - Mensaje que indica ausencia de snapshot y estado pendiente.
7. Metrica anual no soportada:
   - Detectada por 400 + mensaje de soporte invalid.

### Mensajes de ayuda

- Se agrega ayuda explicita para:
  - resumen semanal,
  - resumen mensual,
  - ranking anual pre-computado.

### Accesibilidad y usabilidad

- Botones con `aria-label`.
- Estados con role/status y mensajes persistentes en bloques dedicados.

### Validaciones realizadas

- `node --check frontend/assets/js/stats.js` (ok).
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1` (ok).
- Servidor local levantado con `python -m http.server` en 8080:
  - `http://127.0.0.1:8080/stats.html` -> 200
  - `http://127.0.0.1:8080/assets/js/stats.js` -> 200
- `git diff --name-only` revisado para confirmar alcance de cambios.

### Limitaciones detectadas

- Mensajes y UI se mantienen en ASCII en algunos textos para evitar regresiones de encoding existente en entorno.
- No se modificaron ni se revalidaron flujos visuales de backend offline via navegador.

### Follow ups

-- Revisar posibles mejoras tipograficas de textos de apoyo para corregir
  errores menores de copy en futuras iteraciones.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Mantener cambios acotados y revisables.
