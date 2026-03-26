# TASK-104-landing-loading-state-and-stale-lock-hardening

## Goal
Corregir dos problemas de producto/operación ya detectados:
1. la landing muestra primero datos fake estáticos antes de hidratar
2. los stale locks entre contenedores Docker siguen bloqueando pasadas manuales aunque los workers ya estén parados

## Context
Se ha confirmado que:
- la homepage renderiza cards estáticas fake y luego las sustituye al hidratar
- eso genera un flash de datos falsos
- además, el lock compartido puede quedar huérfano entre contenedores y requiere borrado manual

## Steps
1. Para la landing:
   - auditar `frontend/index.html`, `frontend/assets/js/main.js`, `frontend/assets/css/styles.css`
   - aplicar la opción A:
     - no mostrar cards fake iniciales
     - dejar contenedor vacío o skeleton/loading state
     - renderizar solo datos reales al hidratar
     - degradar limpio si falla la API
2. Para el stale lock:
   - auditar `backend/app/writer_lock.py`
   - mejorar la detección/recuperación de locks huérfanos entre contenedores Docker
   - no depender únicamente del hostname si eso bloquea recuperación válida
   - mantener seguridad para no liberar locks activos por error
3. Documentar el comportamiento actualizado en README/runbook.

## Constraints
- No rehacer la landing completa.
- No romper el single-writer lock.
- No volver al comportamiento sin coordinación.
- No introducir riesgo de liberar locks válidos sin comprobación suficiente.

## Validation
- La landing ya no muestra datos fake antes de hidratar.
- Los locks huérfanos entre contenedores se recuperan mejor o quedan claramente resueltos.
- La repo queda consistente.

## Expected Files
- `frontend/index.html`
- `frontend/assets/js/main.js`
- `frontend/assets/css/styles.css`
- `backend/app/writer_lock.py`
- `backend/README.md`
