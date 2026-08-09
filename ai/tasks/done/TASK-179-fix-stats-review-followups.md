---
id: TASK-179
title: Fix Stats Review Follow-ups
status: done
type: documentation
team: Analista
supporting_teams:
  - Frontend Senior
  - Backend Senior
  - PM
roadmap_item: foundation
priority: medium
---

# TASK-179 - Fix Stats Review Follow-ups

## Goal

Resolver los hallazgos no bloqueantes detectados en TASK-178 sobre el bloque Stats después del hardening.

## Context

Tras la revisión de TASK-178 quedaron pendientes 3 correcciones de consistencia y resiliencia:  
- documentación desincronizada en `timeframe`,  
- fallo total de perfil al fallar en paralelo una ventana semanal/mensual,  
- validación de regresión demasiado dependiente de texto literal en UI.

El objetivo es cerrar estos puntos sin ampliar el alcance funcional del bloque Stats ni de ranking.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `ai/tasks/done/TASK-178-review-stats-implementation-after-hardening.md`
- `docs/stats-section-functional-plan.md`
- `frontend/stats.html`
- `frontend/assets/js/stats.js`
- `scripts/run-stats-validation.ps1`
- `scripts/run-integration-tests.ps1`
- `backend/app/routes.py`

## Steps

1. Leer los archivos listados arriba.
2. Corregir únicamente los cambios de alcance identificados:
   - actualizar documentación para reflejar `timeframe=weekly|monthly`,
   - tolerar fallo parcial entre `weekly` y `monthly` en el frontend,
   - endurecer el script de validación para no depender de textos literales cuando no sea necesario.
3. Ejecutar validaciones:
   - `node --check frontend/assets/js/stats.js`
   - `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
   - `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
   - Servidor HTTP local para validar HTTP 200 de `stats.html` y `assets/js/stats.js`.
4. Documentar resultado en el apartado Outcome y cerrar la task.

## Expected Files to Modify

- `docs/stats-section-functional-plan.md`
- `frontend/assets/js/stats.js`
- `scripts/run-stats-validation.ps1`
- `ai/tasks/done/TASK-179-fix-stats-review-followups.md`

## Constraints

- Corregir sin agregar nuevas funcionalidades.
- No cambiar la lógica de ranking.
- No introducir o reactivar Elo/MMR.
- No reintroducir `Comunidad Hispana #03`.
- No crear migraciones.
- No modificar backend salvo bug menor estrictamente necesario.
- Mantener estilos y comportamiento existente salvo el mensaje mínimo necesario para fallo parcial.
- No ampliar la sección Stats con nuevas funcionalidades.

## Validation

- `node --check frontend/assets/js/stats.js`
- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- Servir frontend y confirmar HTTP 200 para `stats.html` y `assets/js/stats.js`.
- `git diff --name-only` y verificación de scope.

## Outcome

- Cambios aplicados:
  - `docs/stats-section-functional-plan.md`:
    - Se actualizó la especificación de `timeframe` en
      `/api/stats/players/{player_id}` a `weekly|monthly`.
    - Se explicitó que `timeframe=all` no está soportado en el contrato actual.
  - `frontend/assets/js/stats.js`:
    - Se reemplazó `Promise.all` por `Promise.allSettled` para carga semanal/mensual.
    - Se añadio render parcial para escenarios de éxito parcial por ventana.
    - Se mantiene fallback de error total si ambas ventanas fallan.
  - `scripts/run-stats-validation.ps1`:
    - Se reforzaron validaciones de IDs, endpoints y shape de payload.
    - Se quitaron chequeos frágiles dependientes de texto visible de UI.
    - Se añadieron verificaciones para `requested_limit`, `effective_limit`, `snapshot_limit` y `item_count`.
- Modo de fallo parcial semanal/mensual:
  - Si una ventana responde y la otra falla:
    - se muestran sus datos y estado disponible.
    - la otra muestra aviso de bloque no disponible y se evita degradar todo el panel.
    - se agrega aviso global de carga parcial.
  - Si ambas fallan:
    - se conserva el estado de error completo y backend-inusable para ese perfil.
- Validaciones endurecidas:
  - Validación de contrato en JS y HTML basada en funciones/rutas/IDs.
  - Validación de forma de payload y metadatos de snapshot en bloque anual.
- Validaciones ejecutadas:
  - `node --check frontend/assets/js/stats.js`
  - `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
  - `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
  - `python -m http.server` (servido desde `frontend/`) con `HTTP 200` para:
    - `stats.html`
    - `assets/js/stats.js`
- Limitaciones o follow-ups:
  - No se identificaron follow-ups de producto inmediatos dentro del alcance de TASK-179.
