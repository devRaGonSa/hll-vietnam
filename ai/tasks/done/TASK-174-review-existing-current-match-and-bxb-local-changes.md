---
id: TASK-174
title: Review existing current-match and bxb local changes
status: done
type: documentation
team: PM
supporting_teams: [Frontend Senior, Backend Senior]
roadmap_item: foundation
priority: medium
---

# TASK-174 - Review existing current-match and bxb local changes

## Goal

Analizar y decidir cómo tratar los cambios locales existentes en:

- `frontend/assets/img/clans/bxb.png`
- `frontend/assets/js/partida-actual.js`

sin tocar Stats ni backend, y sin descartar cambios sin confirmación humana.

## Context

Se detectaron cambios locales preexistentes fuera del flujo Stats que deben resolverse de forma controlada y trazable:

- asset de clan `bxb.png`
- mejoras funcionales sobre `partida-actual.js`

## Steps

1. Confirmar estado local actual y alcance de cambios.
2. Mover esta tarea a `ai/tasks/in-progress`.
3. Revisar los archivos indicados en `Files to Read First`.
4. Revisar `git diff frontend/assets/js/partida-actual.js` y resumir cambios exactos.
5. Revisar cambio binario de `frontend/assets/img/clans/bxb.png` (tamaño/tipo/posible finalidad como reemplazo de asset).
6. Decidir si ambos cambios son relacionados o deben tratarse por separado.
7. Ejecutar validaciones básicas solo si procede conservar y no hay dudas:
   - `node --check frontend/assets/js/partida-actual.js`
   - `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
8. Definir decisión:
   - commitear juntos si ambos cambios son relacionados y correctos,
   - separar en commits si ambos son correctos pero no relacionados,
   - mover a `ai/tasks/review` si hay dudas o requeriría confirmación humana.

## Files to Read First

- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- frontend/assets/js/partida-actual.js
- frontend/stats.html
- frontend/assets/js/stats.js
- docs/annual-ranking-snapshot-runbook.md
- ai/tasks/done/TASK-173-add-annual-ranking-snapshot-runbook.md

## Expected Files to Modify

- `ai/tasks/in-progress/TASK-174-review-existing-current-match-and-bxb-local-changes.md` (actualización de outcome)
- `ai/tasks/done/TASK-174-review-existing-current-match-and-bxb-local-changes.md` o
- `ai/tasks/review/TASK-174-review-existing-current-match-and-bxb-local-changes.md`

## Constraints

- No implementar nuevas features.
- No tocar backend.
- No tocar Stats (más allá de verificación pasiva de que no se rompe).
- No tocar endpoints.
- No reactivar Elo/MMR.
- No reintroducir Comunidad Hispana #03.
- No cambiar workers históricos.
- No descartar cambios sin confirmación humana.
- No mezclar estos cambios con futuras tareas de Stats.

## Validation

- Revisar que `git status --short --untracked-files=all` refleje únicamente estos cambios de producto.
- `git diff --name-only` dentro del scope de esta tarea.
- Si se ejecutan validaciones, registrar resultados (check JS, tests, estado HTTP de assets/página relacionada si aplica).

## Outcome

### Resultados de revisión

- En `frontend/assets/js/partida-actual.js` cambia exclusivamente la etiqueta visible del arma para aliases de Kar98k:
  - `kar98k`
  - `kar 98k`
  - `kar98`
  - `k98`
  - `k98k`
  
  El valor pasó de `"Kar98k"` a `"KARABINER 98K"` en esas cinco entradas.
- `frontend/assets/js/partida-actual.js` mantiene funcionalidad intacta y no afecta a rutas de API, backend ni Stats.
- `frontend/assets/img/clans/bxb.png` es un cambio binario de imagen.
  - Tipo detectado: `PNG`.
  - Tamaño en HEAD: `370262` bytes.
  - Tamaño actual: `1148813` bytes.
  - Dimensiones HEAD: `1145x691`.
  - Dimensiones actuales: `1376x752`.
- La evidencia sugiere que `bxb.png` es un reemplazo de asset de clan (resolución y peso mayores), no una edición de código.

### Relación y resolución

- Los cambios no están relacionados entre sí:
  - `partida-actual.js`: ajuste de texto de etiqueta visual de arma.
  - `bxb.png`: sustitución de asset gráfico de clan.
- Se conservarán por separado y se commitean de forma independiente para mantener trazabilidad.

### Validaciones ejecutadas

- `node --check frontend/assets/js/partida-actual.js` (sin errores).
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1` (exit 0, validación de plataforma e historial OK; sin tests de integración de producto necesarios para este scope).
- `python -m http.server 8080` validado contra `frontend`:
  - `http://127.0.0.1:8080/partida-actual.html` → HTTP 200.
  - `http://127.0.0.1:8080/assets/js/partida-actual.js` → HTTP 200.

### Decisión final

- Mantener ambos cambios y no descartarlos.
- Ejecutar commits separados por no estar relacionados.
- Se deja marcada como completa y se prepara para mover a `done`.
