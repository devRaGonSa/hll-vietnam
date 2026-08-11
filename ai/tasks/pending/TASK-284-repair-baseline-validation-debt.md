---
id: TASK-284
title: Repair pre-existing baseline validation debt
status: pending
type: platform
team: Arquitecto Python
supporting_teams: ["Backend Senior", "Frontend Senior", "PM"]
roadmap_item: ai-platform-validation-debt
priority: high
---

# TASK-284 - Repair pre-existing baseline validation debt

## Goal

Corregir la deuda de validación demostrada por TASK-283, recuperando una suite
y validaciones de integración coherentes con el comportamiento funcional
intencionado, sin ocultar fallos, debilitar assertions ni alterar la historia
de reconciliación.

## Context

TASK-283 comparó de forma aislada la baseline `f522970` y el merge reconciliado
`dfb83d6`. En ambas revisiones y en ejecuciones repetidas obtuvo exactamente:

- `130` tests, skipped `0`, `1 failure` y `2 errors`;
- Historical UI correcto;
- Stats fallando con
  `Stats page no longer exposes the annual ranking form.`;
- wrapper de integración fallando después de Historical por la misma
  validación Stats.

Las firmas idénticas quedaron clasificadas como `IDENTICAL_BASELINE_FAILURE`:

- `HistoricalRunnerMaintenanceTests.test_cleanup_exception_is_logged_and_runner_continues`:
  `AssertionError: 'partial' != 'ok'`;
- `RconMaterializationPipelineTests.test_recent_matches_prefer_materialized_rcon_over_scoreboard_fallback`:
  se obtiene `public-scoreboard` donde el test espera `rcon`, seguido por
  `PermissionError: [WinError 32]` durante el cleanup SQLite;
- `RconMaterializationPipelineTests.test_public_scoreboard_fallback_used_only_without_rcon_activity`:
  `IndexError: list index out of range`, seguido por el mismo error de cleanup;
- `scripts/run-stats-validation.ps1` espera `id="stats-annual-form"` en
  `frontend/stats.html`, aunque la UI actual separa superficies de Stats y
  Ranking.

Estos fallos no fueron introducidos por el merge. Esta task debe determinar el
contrato correcto para cada caso y aplicar la corrección mínima de producto,
test o validación que refleje ese contrato. No debe modificar ni reescribir la
reconciliación Git.

## Steps

1. Leer todos los archivos de `Files to Read First` y el Outcome completo de
   TASK-283.
2. Ejecutar desde una rama propia la suite completa y los scripts Historical,
   Stats e integración; registrar la firma inicial.
3. Determinar el comportamiento intencionado del runner cuando maintenance
   falla y las demás fases continúan. Ajustar implementación o test según el
   contrato documentado, no solo según el resultado actual.
4. Diagnosticar la selección RCON/public-scoreboard de los dos tests de
   materialización, incluyendo estado persistido, resolución de fuente y cierre
   explícito de conexiones SQLite. Corregir la causa funcional y el cleanup sin
   suprimir `ResourceWarning` o `PermissionError`.
5. Revisar el contrato visual actual entre `stats.html` y `ranking.html`.
   Decidir si el formulario anual debe restaurarse en Stats o si la validación
   debe comprobar la navegación/superficie Ranking vigente; documentar la
   decisión y preservar cobertura equivalente.
6. Añadir o ajustar tests focalizados para evitar que las tres firmas y la
   divergencia de Stats reaparezcan.
7. Ejecutar de nuevo la suite completa, cada test afectado de forma aislada,
   Historical UI, Stats y el wrapper de integración.
8. Exigir `0 failures`, `0 errors` y exit code `0` en las validaciones. No
   aceptar skips nuevos sin justificación explícita.
9. Revisar `git diff --check` y `git diff --name-only`, documentar el Outcome y
   mover esta task a `review`; no ejecutar otras tasks pendientes.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/tasks/review/TASK-283-qualify-baseline-validation-and-complete-reconciliation.md`
- `backend/tests/test_historical_runner_maintenance.py`
- `backend/tests/test_rcon_materialization_pipeline.py`
- `scripts/run-stats-validation.ps1`

## Expected Files to Modify

- `backend/tests/test_historical_runner_maintenance.py`, si el contrato exige
  corregir o completar su assertion;
- `backend/tests/test_rcon_materialization_pipeline.py`, para conservar la
  cobertura correcta y cerrar recursos de forma determinista;
- los módulos de `backend/app/` directamente responsables de las firmas, solo
  si el comportamiento actual contradice el contrato confirmado;
- `scripts/run-stats-validation.ps1` y, únicamente si el contrato lo exige,
  `frontend/stats.html`, `frontend/ranking.html` o sus scripts asociados;
- esta task al documentar el Outcome y cambiar de lifecycle.

No asumir de antemano que todos estos archivos deben cambiar. Mantener cada
corrección vinculada a una de las cuatro firmas reproducidas.

## Constraints

- No modificar, recrear ni reescribir `dfb83d6` ni la reconciliación.
- No usar reset, rebase, cherry-pick, squash ni force push.
- No convertir fallos en skips ni relajar assertions sin justificar el contrato
  funcional correcto.
- No ocultar `ResourceWarning`, `PermissionError` ni errores de cleanup.
- No ampliar Elo/MMR, RCON server #03 ni el alcance funcional de Stats/Ranking.
- No ejecutar ni modificar TASK-272 a TASK-281.
- No ejecutar ninguna otra task pendiente.

## Validation

```powershell
python -m compileall backend/app
Push-Location backend
python -m unittest discover -s tests
Pop-Location
powershell -ExecutionPolicy Bypass -File scripts/run-historical-ui-regression-tests.ps1
powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1
powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1
git diff --check
git diff --name-only
```

Resultado aprobatorio: suite completa sin failures/errors, Historical UI,
Stats y wrapper con exit code `0`, sin skips nuevos ni cambios ajenos.

## Outcome

Pendiente. Debe registrar causa raíz, contrato decidido para cada firma,
archivos modificados, comandos, conteo total/skipped/failures/errors y
confirmación de que la reconciliación no fue alterada.

## Change Budget

- Preferir menos de 8 archivos modificados.
- Mantener cada corrección bajo 200 líneas cuando sea viable.
- Bloquear y documentar cualquier conflicto de contrato funcional que requiera
  decisión humana antes de cambiar producto.
