---
id: TASK-170
title: Connect annual ranking snapshot to Stats frontend
status: done
type: frontend
team: Frontend Senior
supporting_teams: []
roadmap_item: foundation
priority: medium
---

# TASK-170 - Connect annual ranking snapshot to Stats frontend

## Goal

Conectar el bloque anual top 20 del módulo Stats con la API pública ya creada:

- `GET /api/stats/rankings/annual?year=<year>&server_id=<server-or-all>&metric=kills&limit=20`

## Context

Después de implementar el endpoint anual en backend y diseñar la integración frontend de Stats, esta tarea conecta el bloque de placeholder con datos reales de snapshots precomputados y mantiene el comportamiento por estados sin romper la sección actual.

No se implementan cambios de backend ni migraciones en esta tarea.

## Steps

1. Revisar los archivos obligatorios antes de iniciar cambios:
   - `AGENTS.md`
   - `ai/repo-context.md`
   - `ai/architecture-index.md`
   - `docs/stats-section-functional-plan.md`
   - `docs/stats-frontend-integration-plan.md`
   - `docs/annual-ranking-snapshot-schema-plan.md`
   - `frontend/stats.html`
   - `frontend/assets/js/stats.js`
   - `frontend/assets/css/styles.css`
   - `backend/app/routes.py`
   - `backend/app/payloads.py`
   - `backend/app/rcon_annual_rankings.py`
2. Mantener el placeholder de ranking anual en el HTML, reemplazándolo por estados y tabla dinámica del endpoint.
3. Implementar consumo del endpoint anual con estado por:
   - ready
   - missing
   - error/backend no disponible
4. Mantener `metric=kills` y `limit=20` fijos en V1.
5. Validar carga/estado con `node --check` y pruebas de endpoint si hay backend.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `docs/stats-section-functional-plan.md`
- `docs/stats-frontend-integration-plan.md`
- `docs/annual-ranking-snapshot-schema-plan.md`
- `frontend/stats.html`
- `frontend/assets/js/stats.js`
- `frontend/assets/css/styles.css`
- `backend/app/routes.py`
- `backend/app/payloads.py`
- `backend/app/rcon_annual_rankings.py`

## Expected Files to Modify

- `frontend/stats.html`
- `frontend/assets/js/stats.js`
- `frontend/assets/css/styles.css` (solo si se requiere ajuste visual para el bloque anual)
- `ai/tasks/pending/TASK-170-connect-annual-ranking-snapshot-to-stats-frontend.md` (estado + outcome)

## Constraints

- Mantener frontend vanilla sin frameworks ni cambios de backend.
- No crear migraciones.
- No modificar `frontend/assets/js/partida-actual.js`.
- No modificar `frontend/assets/img/clans/bxb.png`.
- No reintroducir Comunidad Hispana #03.
- Mantener el bloque anual como consumo de snapshot (`ready`, `missing` o backend no disponible).
- No implementar generador anual desde frontend.

## Validation

Antes de cerrar:

- `node --check frontend/assets/js/stats.js`
- (si aplica) `python -m http.server` y comprobar HTTP 200 para `frontend/stats.html` y `frontend/assets/js/stats.js`.
- Consumir `GET /api/stats/rankings/annual` desde la UI cuando backend local esté disponible.
- Verificar caso con snapshot existente y caso sin snapshot (`snapshot_status="missing"`).
- `scripts/run-integration-tests.ps1` si aplica.
- `git diff --name-only` y validar que el alcance no excede la task.
- `git status --short --untracked-files=all` y confirmar que no se tocó `partida-actual.js` ni `img/clans/bxb.png`.

## Outcome

- Archivos modificados:
  - `frontend/stats.html`
  - `frontend/assets/js/stats.js`
  - `frontend/assets/css/styles.css` (ajustes del bloque anual)
  - `ai/tasks/done/TASK-170-connect-annual-ranking-snapshot-to-stats-frontend.md`
- Endpoint consumido:
  - `GET /api/stats/rankings/annual?year=<year>&server_id=<server-or-all>&metric=kills&limit=20`
- Comportamiento `snapshot_status=ready`:
  - Muestra el bloque de ranking anual con filas del top (`ranking_position`, `player_name`, `metric_value`, `matches_considered`, `kills`, `deaths`, `teamkills`, `kd_ratio`), metadatos de servidor, fuente y fecha.
- Comportamiento `snapshot_status=missing`:
  - Muestra estado informativo de no disponibilidad de ranking para el año seleccionado.
  - No lanza error ni bloquea el resto del flujo.
- Comportamiento con backend no disponible:
  - El estado general y anual muestran error (`Backend no disponible...`) y no se hacen cambios de UI inconsistentes.
- Validaciones ejecutadas:
  - `node --check frontend/assets/js/stats.js`
  - `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
  - Servido local con `python -m http.server` y comprobación HTTP 200 de `frontend/stats.html` y `frontend/assets/js/stats.js`
  - `git status --short --untracked-files=all`
  - `git diff --name-only`
- Limitaciones conocidas:
  - No se pudo validar integración real contra backend porque `http://127.0.0.1:8000` no estaba disponible en este entorno.
  - Los textos en este bloque se mantienen en ASCII para evitar cambios de encoding.
- Siguiente tarea recomendada:
  - Conectar la vista de `Stats` con `frontend/index.html`/`frontend/historico.html` si aplica y/o añadir mejoras visuales en el bloque anual.


## Change Budget

- Preferir cambios < 5 archivos y < 200 líneas.
- Mantener cambio pequeño y verificable.
