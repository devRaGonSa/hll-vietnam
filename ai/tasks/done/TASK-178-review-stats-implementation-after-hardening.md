---
id: TASK-178
title: Review Stats Implementation After Hardening
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

# TASK-178 - Review Stats Implementation After Hardening

## Goal

Realizar una revisión técnica del bloque Stats tras TASK-175, TASK-176 y TASK-177, sin implementar nuevas funcionalidades, para verificar coherencia funcional, robustez y consistencia entre documentación, contratos y comportamiento real.

## Context

La revisión debe cubrir el estado actual de Stats en frontend y backend con enfoque en comportamiento funcional estable, confiabilidad operativa y ausencia de regresiones en restricciones previas (sin Elo/MMR, sin reintroducir Comunidad Hispana #03).  
Se debe preservar la identidad del repositorio y no ampliar alcance fuera del bloque Stats.

## Steps

1. Leer los archivos listados en “Files to Read First” para ubicar el estado base de la revisión.
2. Auditar los archivos objetivo y verificar los 9 puntos solicitados por el alcance de la task.
3. Ejecutar las validaciones técnicas solicitadas (`node --check`, scripts de stats y de integración).
4. Documentar hallazgos por severidad y marcar follow-up tasks para gaps no triviales.

## Files to Read First

- `ai/task-template.md`
- `ai/tasks/done/TASK-175-add-stats-regression-validation-script.md`
- `ai/tasks/done/TASK-176-add-stats-player-comparison-cards.md`
- `ai/tasks/done/TASK-177-harden-annual-ranking-snapshot-operations.md`
- `frontend/stats.html`
- `frontend/assets/js/stats.js`

## Expected Files to Modify

- `ai/tasks/pending/TASK-178-review-stats-implementation-after-hardening.md`

## Scope

Revisar técnicamente los siguientes archivos:

- `frontend/stats.html`
- `frontend/assets/js/stats.js`
- `frontend/assets/css/styles.css`
- `backend/app/rcon_historical_player_stats.py`
- `backend/app/rcon_annual_rankings.py`
- `backend/app/payloads.py`
- `backend/app/routes.py`
- `scripts/run-stats-validation.ps1`
- `scripts/run-integration-tests.ps1`
- `docs/stats-section-functional-plan.md`
- `docs/annual-ranking-snapshot-runbook.md`

La revisión debe cubrir explícitamente:

1. Consistencia entre contratos documentados y payloads reales.
2. Confirmación de que Stats no depende de Elo/MMR.
3. Confirmación de que no se reintroduce Comunidad Hispana #03.
4. Validación del manejo frontend para:
   - backend offline
   - búsqueda sin resultados
   - jugador sin stats
   - ranking anual missing
   - ranking anual ready vacío
   - métrica inválida
5. Revisión de fetch semanal + mensual en paralelo y análisis de fallo parcial.
6. Revisión de documentación y validación de los nuevos metadatos `requested_limit`, `effective_limit`, `snapshot_limit`, `item_count`.
7. Revisión de fragilidad de `scripts/run-stats-validation.ps1` por comparaciones de strings exactos.
8. Ejecutar validaciones técnicas:
   - `node --check frontend/assets/js/stats.js`
   - `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
   - `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
9. Documentar hallazgos, clasificarlos y, si hay gaps no triviales, crear tareas de seguimiento en vez de ampliar esta task.

## Constraints

- No implementar nuevas funcionalidades.
- No modificar backend salvo bug menor evidente y estrictamente necesario para permitir una revisión correcta.
- No modificar frontend salvo bug menor evidente y estrictamente necesario.
- No crear migraciones.
- No cambiar lógica de ranking.
- No reactivar Elo/MMR.
- No reintroducir Comunidad Hispana #03.

## Validation

- `node --check frontend/assets/js/stats.js`
- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`

Antes de completar, verificar:

- alcance evaluado solo en los archivos de esta task;
- hallazgos priorizados por severidad;
- `git diff --name-only` debe incluir únicamente este archivo de task.
- no se ejecuta ningún cambio de código fuera del objetivo de revisión.

## Outcome

## Outcome

- Hallazgos de calidad funcional y consistencia:
  1. [SEVERIDAD BAJA] Documentación funcional (`docs/stats-section-functional-plan.md`) incluye `timeframe=weekly|monthly|all` en la sección de perfil jugador, pero el contrato real expuesto en `backend/app/routes.py` acepta solo `weekly|monthly` (`/api/stats/players/{id}?timeframe=`). Esto limita la superficie a lo realmente probado.
  2. [SEVERIDAD BAJA] El flujo de perfil en `frontend/assets/js/stats.js` consulta semanal y mensual en paralelo con `Promise.all`. Si una de esas dos peticiones falla (timeout o error puntual), se marca el backend offline y se pierde información parcial del otro periodo. Se recomienda separación con `Promise.allSettled` para degradación parcial.
- Validación de consistencia de contratos vs payloads:
  - `frontend/assets/js/stats.js` consume exactamente los contratos actuales definidos en `backend/app/payloads.py`: 
    - búsqueda en `build_stats_player_search_payload` (`/api/stats/players/search`) con `data.query`, `data.server_id`, `data.items`
    - perfil en `build_stats_player_profile_payload` (`/api/stats/players/{id}`) con `data.matches_considered`, `weekly_ranking`, `monthly_ranking`, metadatos de `source`
    - ranking anual en `build_annual_ranking_snapshot_payload` (`/api/stats/rankings/annual`) con `snapshot_status`, `requested_limit`, `effective_limit`, `snapshot_limit`, `item_count`
  - Los nuevos metadatos de snapshot (`requested_limit`, `effective_limit`, `snapshot_limit`, `item_count`) están documentados en `docs/annual-ranking-snapshot-runbook.md` y aparecen en los payloads.
- Restricciones de producto verificadas:
  - No hay dependencia de Elo/MMR en el bloque Stats revisado (endpoints de Elo/MMR son rutas separadas en `routes.py`).
  - No se detectó reintroducción de `Comunidad Hispana #03` en `frontend/stats.html`, `frontend/assets/js/stats.js`, `docs/stats-section-functional-plan.md`, `docs/annual-ranking-snapshot-runbook.md` ni en los endpoints de Stats revisados.
  - El manejo de estados solicitados en frontend se encuentra cubierto:
    - backend offline -> mensajes de estado y estado de paneles configurados en `markAsBackendUnavailable`
    - búsqueda sin resultados -> `search_empty` con "Sin resultados"
    - jugador sin stats -> aviso `profileNoStats` con bloque de identidad/counters en 0
    - ranking anual `missing` -> `annualMissing`
    - ranking anual `ready` pero vacío -> `annualReadyEmpty`
    - métrica inválida anual -> `annualMetricInvalid`
- Fragilidad de validación script:
  - `scripts/run-stats-validation.ps1` usa múltiples `Assert-Contains` con cadenas exactas para comprobar assets/endpoints/mensajes.
  - Es útil como regresión, pero es sensible a cambios de copy/UI no funcionales; recomendado considerar validación semántica adicional (`toLowerCase`, patrones de forma/falla HTTP) en un follow-up.
- Evidencia de validaciones ejecutadas:
  - `node --check frontend/assets/js/stats.js`
  - `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
  - `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- Riesgos/acciones:
  - No se observan bloqueos funcionales críticos en el estado actual.
  - Riesgo residual de degradación parcial del perfil semanal/mensual por fallo parcial en cargas paralelas.

Tareas de seguimiento:
1. Alinear `docs/stats-section-functional-plan.md` con el contrato real de `timeframe` (o ampliar explícitamente ruta para aceptar `all`) como decisión de producto.
2. Implementar degradación parcial en carga de perfil (semana/mensual) para no degradar ambas tablas por un fallo aislado.
3. Endurecer `scripts/run-stats-validation.ps1` para validar semántica de estados además de string-matches exactos.
