# TASK-008-frontend-data-consumption-plan

## Goal
Definir cómo consumirá el frontend de HLL Vietnam los futuros endpoints del backend, dejando documentada una estrategia clara de integración de datos sin implementar todavía lógica real de consumo.

## Context
Ya existe una landing mínima y se ha definido un contrato inicial entre frontend y backend. Además, se va a preparar un esqueleto API en backend. Antes de introducir JavaScript de consumo real o secciones dinámicas, conviene dejar documentado cómo deberá organizarse la integración en frontend para mantener simplicidad, claridad y consistencia con la evolución del proyecto.

## Steps
1. Revisar el frontend actual y el contrato frontend-backend.
2. Identificar qué bloques del frontend actual o futuro podrán depender de datos dinámicos del backend.
3. Definir una estrategia mínima de consumo de datos adecuada al proyecto en esta fase, por ejemplo:
   - `fetch`
   - JavaScript simple
   - módulos ligeros si fueran necesarios más adelante
4. Documentar cómo deberían gestionarse:
   - estados de carga
   - errores
   - ausencia de datos
   - placeholders
   - fallback visual
5. Documentar qué endpoints podrían ser consumidos primero y con qué prioridad:
   - `/health`
   - `/api/community`
   - `/api/trailer`
   - `/api/discord`
   - `/api/servers`
6. Proponer una estrategia progresiva para pasar de landing estática a bloques dinámicos sin romper simplicidad.
7. Añadir o actualizar documentación técnica del frontend o del proyecto con esta estrategia.
8. Mantener el alcance documental: no implementar todavía fetch real ni renderizado dinámico.

## Files to Read First
- AGENTS.md
- README.md
- docs/project-overview.md
- docs/frontend-backend-contract.md
- docs/decisions.md
- ai/repo-context.md
- ai/architecture-index.md
- frontend/index.html
- frontend/assets/js/main.js
- frontend/assets/css/styles.css

## Expected Files to Modify
- docs/project-overview.md
- docs/decisions.md
- ai/architecture-index.md
- opcionalmente un nuevo documento técnico si encaja mejor, por ejemplo:
  - docs/frontend-data-consumption-plan.md

## Constraints
- No implementar consumo real de API.
- No cambiar comportamiento visible del frontend.
- No añadir librerías nuevas.
- No rediseñar la landing.
- No tocar backend salvo referencias documentales mínimas si son imprescindibles.
- No hacer cambios destructivos.
- Mantener la solución centrada en planificación de integración.

## Validation
- Existe una estrategia documentada para el consumo de datos en frontend.
- Quedan definidos criterios para loading, error, empty state y fallback.
- Se identifican prioridades de consumo de endpoints.
- El frontend queda preparado conceptualmente para evolucionar sin improvisación.

## Change Budget
- Preferir menos de 5 archivos modificados o creados.
- Preferir menos de 220 líneas cambiadas.
