---
id: TASK-173
title: Add annual ranking snapshot runbook
status: done
type: documentation
team: PM
supporting_teams: [Backend Senior, Frontend Senior, Arquitecto de Base de Datos]
roadmap_item: foundation
priority: medium
---

# TASK-173 - Add annual ranking snapshot runbook

## Goal

Documentar la operacion del ranking anual top 20 para la seccion Stats: como generar, regenerar y validar usando snapshots precomputados para evitar recalcular anualmente en cada request.

## Context

TASK-173 define el proceso operativo para el bloque anual de Stats que consume:

- `GET /api/stats/rankings/annual?year=<year>&server_id=<server-or-all>&metric=kills&limit=20`

El documento mantiene alcance documentación-only y reitera que la fuente preferente es RCON materializado.

## Steps

1. Revisar archivos obligatorios indicados en la task.
2. Crear/actualizar runbook sin tocar backend ni frontend.
3. Documentar fuente, comandos, validaciones y casos esperados.

## Files to Read First

- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- docs/stats-section-functional-plan.md
- backend/app/rcon_annual_rankings.py
- backend/app/routes.py
- frontend/assets/js/stats.js
- ai/tasks/done/TASK-170-connect-annual-ranking-snapshot-to-stats-frontend.md
- ai/tasks/done/TASK-171-validate-stats-section-with-backend-data.md
- ai/tasks/done/TASK-172-polish-stats-section-empty-states-and-copy.md

## Expected Files to Modify

- `docs/annual-ranking-snapshot-runbook.md`
- `ai/tasks/done/TASK-173-add-annual-ranking-snapshot-runbook.md`

## Constraints

- Documentacion-only.
- No modificar backend.
- No modificar frontend.
- No crear migraciones.
- No cambiar scripts salvo que exista comando explícito y se limite a documentación.
- No tocar:
  - `frontend/assets/js/partida-actual.js`
  - `frontend/assets/img/clans/bxb.png`
- Mantener restricciones funcionales:
  - no reactivar Elo/MMR
  - no reintroducir Comunidad Hispana #03

## Validation

- Confirmar que `docs/annual-ranking-snapshot-runbook.md` existe.
- Ejecutar `git diff --name-only`.
- Validar alcance esperado de archivos modificados.
- Si no hay test automáticos por ser documentación-only, documentarlo en Outcome.

## Outcome

### Status

Done

### Files modified

- `docs/annual-ranking-snapshot-runbook.md`
- `ai/tasks/done/TASK-173-add-annual-ranking-snapshot-runbook.md`

### Documentation created

- Runbook creado en `docs/annual-ranking-snapshot-runbook.md` con:
  - propÃ³sito del snapshot anual top 20,
  - fuente de datos materializada RCON (`rcon_materialized_matches`, `rcon_match_player_stats`) y filtro `source_basis=admin-log-match-ended`,
  - endpoint consumidor `GET /api/stats/rankings/annual?...`,
  - pasos de generacion y regeneracion,
  - validacion de existencia,
  - validacion desde API y desde frontend Stats,
  - casos esperados:
    - `snapshot_status="ready"` con items,
    - `snapshot_status="ready"` vacÃ­o,
    - `snapshot_status="missing"`,
    - metrica no soportada en V1.
  - alertas:
    - no recalcular ranking anual por request público,
    - no usar scoreboard publico como fuente primaria si RCON disponible,
    - no reintroducir Elo/MMR,
    - no reintroducir Comunidad Hispana #03.

### Validacion

- Confirmado que `docs/annual-ranking-snapshot-runbook.md` existe.
- `git diff --name-only` y `git status --short --untracked-files=all` revisados para validar alcance.
- Esta tarea es documentación-only; no aplica tests automáticos.

### Limitaciones conocidas

- No se cambian scripts ni operaciones de mantenimiento en esta tarea.
- No se realizan cambios de backend/frontend.

### Siguiente task recomendada

- Automatizar la ejecucion del generador anual (cron/manual) y capturar artefactos de operador.

## Change Budget

- Prefer < 5 files.
- Prefer cambios acotados y revisables.
- Mantener doc corta y accionable.
