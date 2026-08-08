---
id: TASK-283
title: Qualify baseline validation failures and complete repository reconciliation
status: review
type: platform
team: Arquitecto Python
supporting_teams: ["Backend Senior", "Frontend Senior", "PM"]
roadmap_item: ai-platform-repository-source
priority: critical
---

# TASK-283 - Qualify baseline validation failures and complete repository reconciliation

## Goal

Determinar mediante comparación reproducible si los fallos de validación que
bloquearon TASK-282 son preexistentes en `f522970`. Si la firma de fallos es
idéntica y el merge no introduce regresiones, completar de forma controlada la
publicación y Pull Request de la reconciliación sin corregir deuda funcional
fuera de alcance.

## Context

TASK-282 dejó una reconciliación local preservada, pero quedó bloqueada porque
las validaciones obligatorias no terminaron en verde:

- rama local: `chore/reconcile-gitea-github-history`;
- `main` inicial: `f52297055ddf76550f48d0d2315ed0232a9670ef`;
- `gitea/main` inicial: `006bfeba7d1a80b3b326e365e12ccdb9d107dc7d`;
- `origin/main` inicial: `cda6d72b4b2ca244ffc5bab7e6289761a5a114eb`;
- merge-base: `1f4bba38b1b11a354af7e7a7c8045882350ab964`;
- commit de merge sin conflictos:
  `dfb83d6f7f5732879446b9b441aede7473c9db8e`;
- commit que documentó el bloqueo:
  `339e59a43ca8e8dd3751025fd5aec874aae2cb17`;
- respaldos ya publicados:
  `backup/local-main-before-github-reconcile-20260808` en `f522970` y
  `backup/gitea-main-before-github-reconcile-20260808` en `006bfeb`.

La evidencia de TASK-282 indica que `backend`, `frontend` y `scripts` no
cambiaron entre `f522970` y el merge. `compileall` pasó, Historical UI pasó,
`unittest` ejecutó 130 tests con un fallo y dos errores, y Stats falló con
`Stats page no longer exposes the annual ranking form.`

Los tests señalados fueron:

- `test_historical_runner_maintenance.HistoricalRunnerMaintenanceTests.test_cleanup_exception_is_logged_and_runner_continues`;
- `test_rcon_materialization_pipeline.RconMaterializationPipelineTests.test_recent_matches_prefer_materialized_rcon_over_scoreboard_fallback`;
- `test_rcon_materialization_pipeline.RconMaterializationPipelineTests.test_public_scoreboard_fallback_used_only_without_rcon_activity`.

Estos nombres son evidencia inicial, no una conclusión. Esta task debe
descubrir y comparar la firma real de todos los fallos en ambas revisiones. No
puede calificarlos como deuda baseline sin reproducirlos en `f522970`.

TASK-282 permanece en
`ai/tasks/blocked/TASK-282-reconcile-gitea-and-github-histories.md`. La rama de
integración no está publicada y no existe Pull Request. `TASK-272` a
`TASK-281` permanecen intactas en `pending`.

## Steps

### 1. Preflight

1. Leer todos los archivos de `Files to Read First`.
2. Confirmar rama, HEAD y árbol limpio:

   ```powershell
   git status --short --branch
   git rev-parse HEAD
   git branch -vv
   git worktree list
   ```

3. Confirmar que existen `f522970`, `dfb83d6` y `339e59a` como commits.
4. Ejecutar:

   ```powershell
   git diff --name-status f522970..dfb83d6 -- backend frontend scripts
   git diff --stat f522970..dfb83d6 -- backend frontend scripts
   ```

5. Ambos diffs deben quedar vacíos. Si aparece cualquier diferencia de
   producto o validación, mover TASK-283 a `blocked`, documentar las rutas y
   detenerse.
6. Registrar sin secretos el entorno común que se utilizará en ambas
   revisiones: `python -VV`, `sys.executable`, plataforma, directorio de
   trabajo y variables `HLL_*` relevantes sanitizadas.
7. No continuar si el árbol contiene cambios ajenos que impidan aislar esta
   task.

### 2. Aislar las revisiones

1. No modificar `main` ni usar reset.
2. Verificar que las rutas temporales están libres y resuelven dentro del
   repositorio:

   - `tmp/worktrees/task-283-baseline`;
   - `tmp/worktrees/task-283-reconciled`.

3. Crear worktrees detached:

   ```powershell
   git worktree add --detach tmp/worktrees/task-283-baseline f522970
   git worktree add --detach tmp/worktrees/task-283-reconciled dfb83d6
   ```

4. Usar exactamente el mismo ejecutable Python y el mismo entorno para ambos.
5. Guardar logs y artefactos solo bajo rutas temporales ignoradas. No
   añadirlos a Git.
6. Al terminar, retirar los worktrees con `git worktree remove` después de
   comprobar sus rutas exactas. No borrar ni mover el checkout principal.

### 3. Ejecutar las mismas validaciones completas

Ejecutar desde la raíz de cada worktree, en el mismo orden:

```powershell
python -m compileall backend/app

Push-Location backend
python -m unittest discover -s tests
Pop-Location

powershell -ExecutionPolicy Bypass -File scripts/run-historical-ui-regression-tests.ps1
powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1
powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1
```

No seleccionar solo tests que pasan. Para cada comando y revisión capturar:

- comando exacto y revisión;
- exit code;
- duración;
- número total de tests y skipped;
- failures y errors;
- nombre completamente cualificado de cada test;
- excepción, assertion, archivo/línea y salida funcional principal;
- stdout y stderr suficientes para reproducir la firma, sin credenciales.

### 4. Comparar firmas de fallo

Construir en el Outcome esta tabla:

| Validation | `f522970` | `dfb83d6` | Same failure signature? |
| --- | --- | --- | --- |
| Python compileall | | | |
| Full unittest suite | | | |
| Historical UI | | | |
| Stats | | | |
| Integration wrapper | | | |

Para cada fallo comparar nombre, excepción, assertion, archivo/línea, salida
funcional y exit code. Clasificar cada resultado como una de:

- `IDENTICAL_BASELINE_FAILURE`;
- `NEW_RECONCILIATION_FAILURE`;
- `RESOLVED_BY_RECONCILIATION`;
- `ENVIRONMENTAL_OR_NONDETERMINISTIC`.

No considerar equivalentes dos resultados únicamente porque ambos tengan exit
code distinto de cero.

### 5. Repetición mínima

1. Después de las suites completas, repetir al menos una vez en cada revisión
   cada test fallido mediante `unittest -k` o su nombre cualificado.
2. Repetir al menos una vez en cada revisión `run-stats-validation.ps1` y
   cualquier otra validación fallida o sensible a timing.
3. Mantener el mismo entorno e intérprete entre repeticiones.
4. Si cambia la firma entre ejecuciones, clasificarla como
   `ENVIRONMENTAL_OR_NONDETERMINISTIC` y no aprobar automáticamente la
   reconciliación.

### 6. Decisión

#### Caso A - Todos los fallos son baseline idénticos

Solo aprobar si:

- no hay diferencias en `backend`, `frontend` o `scripts`;
- `compileall` pasa en ambas revisiones;
- las dos suites completas ejecutan `130` tests y muestran exactamente
  `1 failure` y `2 errors`, con los mismos tests y firmas;
- Historical UI pasa en ambas revisiones;
- Stats falla en ambas con
  `Stats page no longer exposes the annual ranking form.` y la misma firma;
- el wrapper de integración tiene la misma firma en ambas revisiones;
- las repeticiones son estables;
- no existe ninguna regresión nueva.

Entonces:

1. Documentar los fallos como `baseline validation debt` sin corregirlos.
2. Actualizar el Outcome de TASK-282 y moverla de `blocked` a `review`,
   explicando que TASK-283 descartó una regresión del merge.
3. Actualizar esta task y moverla de `in-progress` a `review`.
4. Conservar `dfb83d6` y todos sus ancestros; no recrear ni repetir el merge.
5. Crear commits pequeños y explícitos solo para los cambios de lifecycle y
   documentación.
6. Si la deuda realmente requiere seguimiento, crear como máximo una task
   `pending` independiente usando un ID libre y `ai/task-template.md`. No
   ejecutarla dentro de TASK-283.
7. Continuar con las secciones 7 a 10.

#### Caso B - Existe una regresión nueva o evidencia no determinista

1. No publicar la rama de integración como válida.
2. Mantener TASK-282 en `blocked`.
3. Documentar la diferencia exacta y mover TASK-283 a `blocked`.
4. No corregir producto ni ampliar alcance.
5. No crear PR y detenerse.

### 7. Validación Git previa a publicación

Solo en Caso A ejecutar y exigir exit code cero:

```powershell
git merge-base --is-ancestor 006bfeb HEAD
git merge-base --is-ancestor 5590987 HEAD
git merge-base --is-ancestor 3967b01 HEAD
git merge-base --is-ancestor f522970 HEAD
git merge-base --is-ancestor origin/main HEAD
git diff --check
git fsck --full
```

Confirmar además que `dfb83d6` sigue siendo un merge con los padres
`b333d3d` y `cda6d72`, y que no se reescribió historia.

### 8. Preservar backlog

1. Verificar que `TASK-272` a `TASK-281` siguen una vez cada una en `pending`,
   con contenido idéntico al incorporado desde `origin/main`.
2. No ejecutarlas, editarlas ni moverlas.
3. Inventariar y no modificar las tasks preexistentes en `in-progress`, en
   particular `TASK-264`, `TASK-266`, `TASK-267` y `TASK-268`.

### 9. Publicación

Solo en Caso A:

1. Publicar `chore/reconcile-gitea-github-history` en `origin` sin force push.
2. No modificar directamente `origin/main`.
3. No cambiar el upstream de `main`, que debe seguir en `gitea/main`.
4. No eliminar `gitea` ni las ramas backup existentes.
5. Comprobar los workflows disparados por el push. Si un Codex worker intenta
   procesar tasks pendientes, cancelarlo inmediatamente y documentarlo.

### 10. Pull Request

Solo en Caso A, crear una Pull Request para revisión humana:

- head: `chore/reconcile-gitea-github-history`;
- base: `main`;
- título: `chore: reconcile preserved Gitea history with GitHub main`.

La descripción debe incluir:

- SHAs iniciales de `main`, `gitea/main` y `origin/main`;
- merge-base `1f4bba3` y merge `dfb83d6`;
- ausencia de conflictos y preservación de commits;
- resultado de `git fsck --full`;
- tabla baseline frente a reconciled;
- sección `Known pre-existing validation failures` con tests y firmas exactas;
- comandos que reproducen los fallos en `f522970`;
- confirmación de que el merge no los introdujo;
- confirmación de que no cambió producto;
- confirmación de que `TASK-272` a `TASK-281` no se ejecutaron;
- confirmación de que `main` sigue `gitea/main`;
- confirmación de que no hubo reset, rebase, cherry-pick, squash o force push.

No fusionar la PR.

### 11. Estado final

- Caso A: TASK-282 y TASK-283 quedan en `review` y la reconciliación queda
  disponible mediante PR para revisión humana.
- Caso B: TASK-282 y TASK-283 quedan en `blocked` y no se publica la
  reconciliación como válida.
- En ambos casos, limpiar solo los worktrees temporales verificados, registrar
  el estado Git final y detenerse sin procesar otra task.

## Files to Read First

- `AGENTS.md`
- `ai-platform.json`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `ai/orchestrator/python-architect.md`
- `ai/tasks/blocked/TASK-282-reconcile-gitea-and-github-histories.md`
- `scripts/run-integration-tests.ps1`
- `scripts/run-historical-ui-regression-tests.ps1`
- `scripts/run-stats-validation.ps1`
- `backend/tests/test_historical_runner_maintenance.py`
- `backend/tests/test_rcon_materialization_pipeline.py`

## Expected Files to Modify

- esta task al moverse entre `pending`, `in-progress` y `review` o `blocked`;
- TASK-282, únicamente en Caso A para actualizar su Outcome y moverla de
  `blocked` a `review`;
- como máximo una nueva task `pending` de deuda baseline, solo si Caso A
  demuestra que hace falta seguimiento.

No modificar `backend`, `frontend` ni `scripts`. Los worktrees, logs y
artefactos temporales no deben incluirse en commits.

## Constraints

- No corregir tests baseline dentro de esta task.
- No modificar producto para obtener un resultado verde.
- No incluir instrumentación temporal en commits.
- No usar reset, rebase, cherry-pick, squash, force push ni
  `--allow-unrelated-histories`.
- No recrear ni repetir innecesariamente `dfb83d6`.
- No modificar `origin/main` ni cambiar el upstream de `main`.
- No eliminar el remoto `gitea` ni las ramas backup.
- No ejecutar, editar ni mover `TASK-272` a `TASK-281`.
- No modificar las tasks preexistentes en `in-progress`.
- No ejecutar `ai-platform run` ni `ai-platform watch`.
- No ocultar fallos ni calificarlos como baseline sin reproducirlos en
  `f522970`.
- No mostrar credenciales o variables sensibles.
- No ejecutar ninguna task de deuda creada como seguimiento.

## Validation

Resultado aprobatorio únicamente si existe evidencia completa, estable y
equivalente entre `f522970` y `dfb83d6`, sin ninguna regresión nueva.

Antes de cerrar:

- verificar que la tabla comparativa incluye todos los comandos y fallos;
- revisar `git diff --name-only` y confirmar el alcance documental;
- comprobar el lifecycle final de TASK-282 y TASK-283;
- verificar backlog, ancestros, `git diff --check` y `git fsck --full`;
- en Caso A, verificar rama remota y URL de PR;
- en Caso B, verificar que no se publicó la reconciliación como válida.

## Outcome

Caso A aprobado el 2026-08-08: todos los fallos se reprodujeron con firma
estable e idéntica en la baseline y en el merge. No existe ninguna regresión
nueva atribuible a la reconciliación.

### Revisiones, preflight y entorno

- baseline: `f52297055ddf76550f48d0d2315ed0232a9670ef`;
- reconciled: `dfb83d6f7f5732879446b9b441aede7473c9db8e`;
- checkout operativo inicial: `f6d724ed1c1a8bceab114f81fd2954cefa1d70e4`
  en `chore/reconcile-gitea-github-history`, con árbol limpio;
- `f522970`, `dfb83d6` y `339e59a` existen como commits;
- `git diff --name-status f522970..dfb83d6 -- backend frontend scripts`:
  vacío;
- `git diff --stat f522970..dfb83d6 -- backend frontend scripts`: vacío;
- worktrees detached:
  `tmp/worktrees/task-283-baseline` y
  `tmp/worktrees/task-283-reconciled`;
- Python:
  `3.13.14 (tags/v3.13.14:fd17997, Jun 10 2026, 13:03:48)` 64-bit;
- intérprete común:
  `C:/Users/Raúl/AppData/Local/Programs/Python/Python313/python.exe`;
- plataforma: `Windows-10-10.0.19045-SP0`;
- Git: `2.54.0.windows.1`;
- no había entorno virtual del proyecto, variables `HLL_*` ni listener en
  `127.0.0.1:8000` durante las validaciones.

### Comparación completa

Los comandos se ejecutaron en el mismo orden, con el mismo intérprete y sin
paralelizar ambas revisiones:

```powershell
python -m compileall backend/app
Push-Location backend
python -m unittest discover -s tests
Pop-Location
powershell -ExecutionPolicy Bypass -File scripts/run-historical-ui-regression-tests.ps1
powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1
powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1
```

| Validation | `f522970` | `dfb83d6` | Same failure signature? |
| --- | --- | --- | --- |
| Python compileall | exit `0`, `0.362s` | exit `0`, `0.312s` | Sí; salida y archivos compilados idénticos |
| Full unittest suite, run 1 | exit `1`; `130`, skipped `0`, failures `1`, errors `2`; `4.526s` internos | exit `1`; `130`, skipped `0`, failures `1`, errors `2`; `4.408s` internos | Sí; las tres firmas son idénticas |
| Full unittest suite, run 2 | exit `1`; `130`, skipped `0`, failures `1`, errors `2`; `4.262s` internos | exit `1`; `130`, skipped `0`, failures `1`, errors `2`; `4.402s` internos | Sí; idéntica además a run 1 |
| Historical UI | exit `0`, `0.524s`; passed | exit `0`, `0.518s`; passed | Sí; ambos pasan |
| Stats, run 1 | exit `1`, `0.444s` | exit `1`, `0.442s` | Sí; `IDENTICAL_BASELINE_FAILURE` |
| Stats, run 2 | exit `1`, `0.413s` | exit `1`, `0.408s` | Sí; idéntica además a run 1 |
| Integration wrapper normalizado | exit `1`, `1.477s`; Historical pasa y Stats falla | exit `1`, `1.474s`; Historical pasa y Stats falla | Sí; `IDENTICAL_BASELINE_FAILURE` |

Los primeros intentos del wrapper en worktrees nuevos encontraron diferencias
solo de materialización local: en baseline faltaba primero
`ai/tasks/in-progress`, en reconciled faltaba primero `ai/tasks/review` y,
después, ambos necesitaron el marcador ignorado `ai/reports/.gitkeep`. Se
registró la incidencia, se garantizó el mismo conjunto de seis carpetas del
lifecycle y el mismo marcador vacío en ambos worktrees, sin cambios
versionados, y se repitió el wrapper. La ejecución comparable alcanzó
Historical y Stats con la misma firma en ambas revisiones.

### Firmas exactas y repeticiones aisladas

1. `FAIL` —
   `test_historical_runner_maintenance.HistoricalRunnerMaintenanceTests.test_cleanup_exception_is_logged_and_runner_continues`:
   `backend/tests/test_historical_runner_maintenance.py:112`,
   `AssertionError: 'partial' != 'ok'`. La repetición aislada ejecutó un test,
   terminó con exit `1` y reprodujo la misma firma en ambas revisiones.
2. `ERROR` —
   `test_rcon_materialization_pipeline.RconMaterializationPipelineTests.test_recent_matches_prefer_materialized_rcon_over_scoreboard_fallback`:
   assertion funcional en
   `backend/tests/test_rcon_materialization_pipeline.py:637`,
   `AssertionError: 'public-scoreboard' != 'rcon'`, seguida durante el cleanup
   del `TemporaryDirectory` iniciado en la línea `617` por
   `PermissionError: [WinError 32]` sobre `historical.sqlite3`. La repetición
   aislada ejecutó un test, terminó con exit `1` y reprodujo la misma firma.
3. `ERROR` —
   `test_rcon_materialization_pipeline.RconMaterializationPipelineTests.test_public_scoreboard_fallback_used_only_without_rcon_activity`:
   `backend/tests/test_rcon_materialization_pipeline.py:682`,
   `IndexError: list index out of range`, seguida durante el cleanup del
   `TemporaryDirectory` iniciado en la línea `667` por el mismo
   `PermissionError: [WinError 32]` sobre `historical.sqlite3`. La repetición
   aislada ejecutó un test, terminó con exit `1` y reprodujo la misma firma.
4. Stats — `scripts/run-stats-validation.ps1` comprueba en las líneas `64-65`
   que `frontend/stats.html` contenga `id="stats-annual-form"`; el helper de la
   línea `24` lanza `RuntimeException` con
   `Stats page no longer exposes the annual ranking form.`. El fallo ocurre
   antes del Python embebido, SQLite y el sondeo HTTP, y fue idéntico en las
   cuatro ejecuciones comparadas.
5. Wrapper — después de que Historical UI pasa, conserva el fallo Stats
   anterior y añade en `scripts/run-integration-tests.ps1:9`
   `Stats regression validation failed.`. Exit `1` y firma idéntica.

Solo se normalizaron raíz del worktree, nombres aleatorios de `tempfile`,
direcciones de objetos y duración. No se normalizaron nombre de test,
excepción, assertion, línea, valores funcionales, `WinError` ni exit code.
Todos los fallos quedan clasificados como `IDENTICAL_BASELINE_FAILURE`; no se
observó `NEW_RECONCILIATION_FAILURE`, `RESOLVED_BY_RECONCILIATION` ni
`ENVIRONMENTAL_OR_NONDETERMINISTIC` en la evidencia comparable.

### Decisión y lifecycle

- Los fallos son `baseline validation debt`; no se corrigieron dentro de esta
  task.
- TASK-282 deja de estar bloqueada por una supuesta regresión del merge y pasa
  a `review` junto con TASK-283.
- Se creó TASK-284 en `pending` como único seguimiento para corregir la deuda;
  no se ejecutó.
- `TASK-272` a `TASK-281` permanecen intactas y sin ejecutar en `pending`.
- Las tasks preexistentes en `in-progress`, incluidas TASK-264, TASK-266,
  TASK-267 y TASK-268, no se modificaron.
- No se modificó `backend`, `frontend` ni `scripts`, ni se ejecutó ninguna task
  funcional.
- Commit de inicio de lifecycle: `42dda20202eb54726a12686d7e785a03ad04b400`.

### Puerta Git, publicación y revisión humana

Después de `git fetch origin --prune`, `origin/main` continuó exactamente en
`cda6d72b4b2ca244ffc5bab7e6289761a5a114eb`. La puerta previa a publicación
terminó así:

- `git merge-base --is-ancestor` devolvió exit `0` para `006bfeb`, `5590987`,
  `3967b01`, `f522970` y `origin/main` frente a `HEAD`;
- `dfb83d6` conservó los padres `b333d3d` y `cda6d72`, por lo que sigue siendo
  el merge normal ya auditado y no se recreó;
- `git diff --check` y `git diff --check f522970..HEAD` devolvieron exit `0`;
- `git fsck --full` devolvió exit `0`; informó únicamente objetos dangling y
  ningún error de integridad;
- los diffs de producto `f522970..dfb83d6` y `f522970..HEAD` siguieron vacíos;
- TASK-272 a TASK-281 continuaron una vez cada una en `pending`, con blobs
  idénticos a `origin/main`, y las tasks preexistentes en `in-progress`
  permanecieron sin cambios.

La rama `chore/reconcile-gitea-github-history` se publicó por primera vez en
`origin` mediante push normal, sin force, en
`560dd033f7f1e968015135e6601d955ee5253c09`. El commit documental que contiene
este cierre avanza esa misma rama únicamente mediante fast-forward.

El push disparó el run
[`31269263769`](https://github.com/devRaGonSa/hll-vietnam/actions/runs/31269263769)
de `.github/workflows/codex-worker.yml`. Terminó inmediatamente en `failure`
al validar el workflow, con `jobs: 0`; no se inició Codex CLI, no se ejecutó
ningún worker y no se procesó ninguna task pendiente.

Se creó, sin fusionarla, la Pull Request lista para revisión humana:

- URL: https://github.com/devRaGonSa/hll-vietnam/pull/10;
- head: `chore/reconcile-gitea-github-history`;
- base: `main`;
- título: `chore: reconcile preserved Gitea history with GitHub main`;
- estado observado: `open`, `draft: false`, `auto_merge: null`.

La PR contiene la comparación baseline/reconciled, las firmas exactas bajo
`Known pre-existing validation failures`, los comandos de reproducción y las
salvaguardas de la reconciliación. `origin/main` no se modificó. El `main`
local permanece en `f522970` y sigue `gitea/main`; el remoto `gitea` y las
ramas de respaldo en `f522970` y `006bfeb` no se eliminaron ni modificaron.

Los worktrees detached se retiraron con `git worktree remove` después de
verificar sus rutas y estado limpio. Los logs quedaron solo bajo `tmp/`
ignorado. Los commits creados antes de este cierre fueron:

- `42dda20202eb54726a12686d7e785a03ad04b400` — inicio de TASK-283;
- `560dd033f7f1e968015135e6601d955ee5253c09` — calificación de deuda baseline,
  lifecycle de TASK-282/TASK-283 y creación pendiente de TASK-284.

Decisión final: Caso A. TASK-282 y TASK-283 terminan en `review`; TASK-284
permanece en `pending` sin ejecutar. No se ejecutó ninguna task distinta de
TASK-283 ni ninguna task funcional.

## Change Budget

- Preferir cambios de lifecycle y documentación en un máximo de tres archivos.
- No modificar archivos de producto.
- Crear como máximo una task posterior de deuda y no ejecutarla.
