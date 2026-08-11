---
id: TASK-285
title: Preserve AI Platform history in reconciliation PR
status: done
type: platform
team: Arquitecto Python
supporting_teams: ["PM"]
roadmap_item: ai-platform-repository-source
priority: critical
---

# TASK-285 - Preserve AI Platform history in reconciliation PR

## Goal

Corregir la rama `chore/reconcile-gitea-github-history` para que la PR #10
preserve íntegramente la AI Platform y el historial de tasks de `origin/main`,
manteniendo a la vez los nuevos artefactos legítimos de la reconciliación, sin
reescribir commits ni alterar código de producto.

## Context

La reconciliación Git preservó correctamente las historias de Gitea y GitHub,
pero la revisión de la PR #10 detectó un efecto lateral no aceptable en el
árbol resultante de AI Platform.

La auditoría de planificación del 2026-08-09 observó, frente a
`origin/main` en `cda6d72b4b2ca244ffc5bab7e6289761a5a114eb`:

- rama: `chore/reconcile-gitea-github-history`;
- HEAD: `fd11f8e5548e3ebbb048647b9cc45da8305d571c`;
- PR #10 abierta, no fusionada y mergeable;
- `350` archivos cambiados, `1.156` inserciones y `35.106` eliminaciones;
- estados globales: `4` added, `345` deleted y `1` modified;
- bajo `ai/`: `4` added, `345` deleted y `0` modified;
- las `317` entradas versionadas de `ai/tasks/done/` de `origin/main`
  desaparecen de la PR;
- los `14` archivos versionados de `ai/orchestrator/` desaparecen;
- `.gitignore` es el único cambio fuera de `ai/` y añade `/ai/`, además de
  reglas duplicadas;
- no existe ningún cambio en `backend/`, `frontend/`, `scripts/` o `deploy/`.

Entre las eliminaciones confirmadas están:

- `ai/repo-context.md`;
- `ai/architecture-index.md`;
- `ai/task-template.md`;
- `ai/orchestrator/feature-planner.md`;
- `ai/tasks/done/TASK-271-split-rcon-live-ingestion-from-historical-materialization.md`;
- `ai/README.md`, `ai/system-metrics.md`, `ai/prompts/plan-feature.md` y
  `ai/reports/.gitkeep`;
- los `.gitkeep` preexistentes del lifecycle y reports preexistentes en
  `review`.

La regla `/ai/` hace que el working tree físico no sea una fuente fiable para
decidir qué está versionado: durante la planificación se encontraron archivos
de AI Platform presentes en disco pero ignorados y ausentes de `HEAD`. La
implementación debe usar `git show`, `git ls-tree`, `git diff` y blobs Git para
la comparación canónica, además de inventariar los archivos físicos ignorados
antes de restaurar nada.

Se observaron como preexistentes e ignoradas las tasks en `in-progress`
TASK-264, TASK-266, TASK-267 y TASK-268. Deben conservarse byte a byte y no
pueden ejecutarse, editarse ni moverse. `origin/main` contiene además una
TASK-267 histórica en `done`; esta task no autoriza resolver ni ocultar esa
divergencia de lifecycle y debe preservar ambas rutas, documentándola.

También se observaron TASK-204 y TASK-242 físicas bajo `done`, ignoradas y no
versionadas ni en `HEAD` ni en `origin/main`. No forman parte del allowlist
autorizado para la corrección. No se deben borrar, sobrescribir o añadir
silenciosamente. Deben permanecer físicamente byte-identical, excluirse del
commit y documentarse como archivos preexistentes que pasarán a verse como
untracked cuando `.gitignore` deje de ocultar `ai/`. Si completar TASK-285
exigiera borrarlas, moverlas, editarlas o versionarlas, bloquear antes de esa
acción y solicitar una decisión humana.

La política de contenido es:

**`origin/main` es la fuente canónica para todo contenido preexistente de AI
Platform.**

Las únicas excepciones de reconciliación autorizadas son TASK-000, TASK-282,
TASK-283, TASK-284, esta TASK-285 durante su lifecycle y la preservación exacta
de las tasks preexistentes en `in-progress`. El merge `dfb83d6` y toda su
historia deben permanecer intactos; esta corrección se aplica mediante commits
nuevos encima de la rama actual.

## Steps

### 1. Preflight y rama de trabajo

1. Leer todos los archivos de `Files to Read First` antes de modificar nada.
2. Ejecutar:

   ```powershell
   git branch --show-current
   git status --short --branch
   git remote -v
   git rev-parse HEAD
   git log -1 --oneline
   git worktree list
   ```

3. Trabajar exclusivamente sobre
   `chore/reconcile-gitea-github-history`. Si no es la rama actual, cambiar a
   ella de forma segura. No trabajar sobre `main`.
4. Exigir un árbol versionado limpio. Si existen cambios ajenos, detenerse sin
   descartarlos ni mezclarlos.
5. Confirmar mediante GitHub que la PR #10 sigue abierta, no fusionada, con
   head `chore/reconcile-gitea-github-history` y base `main`.
6. Confirmar que TASK-285 existe una sola vez en `pending` y que TASK-000,
   TASK-282, TASK-283 y TASK-284 están en los estados documentados.
7. Mover únicamente TASK-285 a `ai/tasks/in-progress/`, cambiar su metadata a
   `status: in-progress` y crear un checkpoint de lifecycle antes de cualquier
   restauración amplia. Registrar ese SHA como `PRESERVATION_HEAD` para
   recuperar blobs exactos sin reconstrucción manual.

### 2. Actualizar referencias sin integrar de nuevo

1. Ejecutar:

   ```powershell
   git fetch origin
   ```

2. No hacer `pull`, merge adicional, rebase ni nueva reconciliación.
3. Registrar `origin/main`, el merge-base de la PR y el SHA del head remoto.
4. Bloquear si la base o el head de la PR han cambiado de forma que invalide
   la auditoría y no pueda actualizarse de forma inequívoca.

### 3. Auditar el diff real antes de corregir

1. Ejecutar y conservar la salida completa:

   ```powershell
   git diff --name-status origin/main...HEAD
   git diff --stat origin/main...HEAD
   git diff --shortstat origin/main...HEAD
   git diff --name-status origin/main...HEAD -- ai
   git diff --name-status origin/main...HEAD -- backend frontend scripts deploy
   ```

2. Clasificar cada cambio como:

   - artefacto legítimo de la reconciliación;
   - eliminación heredada de AI Platform;
   - modificación inesperada.

3. Registrar expresamente:

   - total de archivos, inserciones y eliminaciones;
   - archivos `ai/` added, modified y deleted;
   - eliminaciones bajo `ai/tasks/done/`, `ai/orchestrator/` y cada carpeta de
     lifecycle;
   - cualquier cambio de producto, que debe ser cero.

### 4. Inventariar Git y los archivos ignorados

1. No confiar solo en `git status`, porque `/ai/` oculta archivos físicos.
2. Ejecutar:

   ```powershell
   git ls-tree -r --name-only origin/main -- ai
   git ls-tree -r --name-only HEAD -- ai
   git status --ignored --short -- ai
   git check-ignore -v --no-index ai/repo-context.md
   Get-ChildItem ai/tasks -Recurse -File
   ```

3. Comparar el inventario físico con ambos árboles Git y calcular hashes de
   los archivos locales ignorados antes de modificar `.gitignore` o `ai/`.
4. Preservar sin cambios las tasks preexistentes en `in-progress`, en
   particular TASK-264, TASK-266, TASK-267 y TASK-268. No ejecutar ninguna.
5. Mantener tanto la TASK-267 histórica de `origin/main` en `done` como la
   preexistente en `in-progress`; documentar el ID duplicado como divergencia
   anterior a TASK-285, sin resolver lifecycle en esta task.
6. Mantener TASK-204 y TASK-242 byte-identical en sus rutas físicas, fuera del
   índice y del commit. Documentar sus hashes y aceptar que queden visibles
   como untracked al retirar `/ai/`; no añadir reglas nuevas para volver a
   ocultarlas.
7. Si aparece cualquier otro archivo físico local-only fuera del conjunto
   autorizado, no borrarlo ni añadirlo. Bloquear antes de una restauración que
   pudiera sobrescribirlo y documentar su ruta y hash.

### 5. Restaurar la AI Platform canónica

Solo si el inventario anterior no contiene una ambigüedad bloqueante:

1. Verificar con `git cat-file -e` que `PRESERVATION_HEAD` contiene los blobs
   exactos de TASK-000, TASK-282, TASK-283, TASK-284 y TASK-285 en su estado
   `in-progress`.
2. Guardar temporalmente, bajo una ruta verificada dentro de `tmp/`, copias
   byte-identical y hashes de las tasks preexistentes en `in-progress` que no
   estén versionadas en `PRESERVATION_HEAD`. No editar esas copias ni
   incluirlas en commits.
3. Restaurar mecánicamente desde `origin/main`, sin reconstruir archivos a
   mano:

   ```powershell
   git restore --source=origin/main --staged --worktree -- .gitignore ai
   ```

4. Reaplicar exclusivamente desde `PRESERVATION_HEAD`:

   ```text
   ai/tasks/blocked/TASK-000-verify-and-switch-hll-vietnam-repository-to-github.md
   ai/tasks/review/TASK-282-reconcile-gitea-and-github-histories.md
   ai/tasks/review/TASK-283-qualify-baseline-validation-and-complete-reconciliation.md
   ai/tasks/pending/TASK-284-repair-baseline-validation-debt.md
   ai/tasks/in-progress/TASK-285-preserve-ai-platform-history-in-reconciliation-pr.md
   ```

5. Reponer mecánicamente las tasks preexistentes en `in-progress` desde sus
   copias verificadas y exigir hashes idénticos antes y después. Su inclusión
   como adiciones de preservación debe quedar explícitamente justificada en el
   Outcome y la PR; no cambiar metadata ni contenido.
6. No reaplicar ningún otro archivo local por conveniencia. Ante un archivo
   adicional que no pueda clasificarse con la política anterior, bloquear.

### 6. Corregir `.gitignore`

1. La preferencia obligatoria es dejar `.gitignore` exactamente igual a
   `origin/main`:

   ```powershell
   git diff --exit-code origin/main -- .gitignore
   ```

2. Confirmar que no contiene `/ai/`, `ai/` ni otra regla general equivalente
   que impida versionar AI Platform.
3. Verificar con `git check-ignore --no-index` que un archivo normativo como
   `ai/repo-context.md` ya no está ignorado. El exit code esperado es `1`.
4. No reparar workflows ni introducir nuevas reglas de ignore en esta task.

### 7. Verificar la conservación del árbol AI Platform

1. Antes del commit correctivo, comprobar la restauración que está en el
   índice y el working tree:

   ```powershell
   git diff --cached --name-status origin/main --
   git diff --cached --stat origin/main --
   git diff --cached --shortstat origin/main --
   git diff --cached --diff-filter=D --name-only origin/main -- ai
   git diff --cached --name-status origin/main -- ai
   git diff --name-status origin/main -- ai
   ```

2. El diff staged con filtro `D` bajo `ai/` debe quedar vacío.
3. No debe quedar ninguna modificación de contenido preexistente de
   `origin/main` bajo `ai/`; solo adiciones autorizadas y byte-identical pueden
   diferir.
4. Deben existir y ser idénticos a `origin/main`:

   - `ai/repo-context.md`;
   - `ai/architecture-index.md`;
   - `ai/task-template.md`;
   - `ai/orchestrator/feature-planner.md`;
   - todos los demás archivos de `ai/orchestrator/**`;
   - `ai/prompts/**`;
   - `ai/reports/**` preexistentes;
   - `ai/tasks/done/**` completo;
   - los `.gitkeep` del lifecycle;
   - cualquier otro blob preexistente de AI Platform.

5. Confirmar específicamente que
   `ai/tasks/done/TASK-271-split-rcon-live-ingestion-from-historical-materialization.md`
   existe y coincide con `origin/main`.

### 8. Verificar todas las tasks protegidas

1. Comparar contra `origin/main`:

   ```powershell
   git diff --name-status origin/main -- ai/tasks/done
   git diff --name-status origin/main -- ai/tasks/in-progress
   git diff --name-status origin/main -- ai/tasks/blocked
   git diff --name-status origin/main -- ai/tasks/review
   git diff --name-status origin/main -- ai/tasks/pending
   ```

2. Confirmar:

   - ninguna task `done` de `origin/main` ha desaparecido o cambiado;
   - ninguna task preexistente en `in-progress` ha desaparecido, cambiado o
     sido ejecutada;
   - TASK-272 a TASK-281 están una sola vez en `pending` y sus blobs son
     byte-identical a `origin/main`;
   - TASK-000 permanece `blocked`;
   - TASK-282 y TASK-283 permanecen `review`;
   - TASK-284 permanece `pending` y no se ejecuta;
   - TASK-285 es la única task movida durante esta ejecución.

3. No resolver en esta task la coexistencia preexistente de TASK-267 en
   `done` y `in-progress`; conservar ambas y documentarla.

### 9. Confirmar ausencia de cambios de producto

Ejecutar:

```powershell
git diff --cached --name-only origin/main -- backend frontend scripts deploy
git diff --name-only origin/main -- backend frontend scripts deploy
git diff --cached --name-only $PRESERVATION_HEAD -- backend frontend scripts deploy
```

Ambos resultados deben estar vacíos. Si aparece cualquier cambio, analizarlo;
TASK-285 no puede introducir ni corregir producto, RCON, CRCON, base de datos o
despliegue.

### 10. Validación Git e historia preservada

Antes del commit correctivo, ejecutar y exigir exit code `0`:

```powershell
git diff --cached --check
git diff --check
git fsck --full
git merge-base --is-ancestor 006bfeb HEAD
git merge-base --is-ancestor 5590987 HEAD
git merge-base --is-ancestor origin/main HEAD
```

Confirmar además:

- `dfb83d6` sigue siendo un merge con sus padres originales;
- no se recreó el merge ni se reescribió ningún commit;
- los objetos dangling de `git fsck --full` no se consideran error si no hay
  errores de integridad.

### 11. Outcome y lifecycle de TASK-285

1. Documentar en `Outcome`:

   - SHAs comparados y comandos exactos;
   - cantidad de archivos, inserciones y eliminaciones antes y después;
   - número de archivos AI Platform added, modified y deleted antes y después;
   - lista de archivos normativos restaurados;
   - cantidad y lista de tasks históricas recuperadas;
   - estado final de `.gitignore`;
   - inventario y hashes de las tasks locales preservadas;
   - cualquier divergencia de lifecycle preexistente;
   - ancestor checks;
   - `git diff --check`;
   - `git fsck --full`;
   - confirmación de ausencia de cambios de producto;
   - confirmación de que no se ejecutó ninguna otra task.

2. Mover TASK-285 a
   `ai/tasks/review/TASK-285-preserve-ai-platform-history-in-reconciliation-pr.md`
   y actualizar `status: review` solo si todas las validaciones pasan.
3. Si cualquier ambigüedad impide cumplir simultáneamente la conservación de
   `origin/main` y de los artefactos locales protegidos, moverla a `blocked`,
   documentar la decisión humana necesaria y detenerse sin publicar la
   corrección como válida.

### 12. Commit correctivo

1. Revisar el diff completo y confirmar que se limita a restauración mecánica
   de AI Platform, `.gitignore` y lifecycle de TASK-285.
2. Crear un commit nuevo encima de la rama existente:

   ```text
   fix(platform): preserve AI Platform history in reconciliation
   ```

3. No squash ni amend de los commits de reconciliación.
4. Después del commit, repetir contra el nuevo `HEAD`:

   ```powershell
   git diff --name-status origin/main...HEAD
   git diff --stat origin/main...HEAD
   git diff --shortstat origin/main...HEAD
   git diff --diff-filter=D --name-only origin/main...HEAD -- ai
   git diff --name-only origin/main...HEAD -- backend frontend scripts deploy
   git diff --check
   git fsck --full
   git merge-base --is-ancestor 006bfeb HEAD
   git merge-base --is-ancestor 5590987 HEAD
   git merge-base --is-ancestor origin/main HEAD
   ```

5. No publicar si cualquiera de estas comprobaciones posteriores al commit
   contradice la validación del índice.

### 13. Push y revisión de PR #10

Solo con TASK-285 en `review` y todas las validaciones correctas:

1. Hacer push normal, nunca force push, a:

   ```text
   origin/chore/reconcile-gitea-github-history
   ```

2. Comprobar cualquier workflow disparado. No reparar el workflow en esta
   task y detener cualquier worker que intentara procesar tasks pendientes.
3. Verificar en PR #10:

   - estado abierto y no fusionado;
   - head/base correctos;
   - changed files, additions y deletions finales;
   - estado mergeable;
   - cero eliminaciones masivas de AI Platform;
   - ausencia de cambios de producto introducidos por TASK-285.

4. Actualizar el Outcome con el SHA del commit correctivo y las métricas reales
   observadas después del push. Crear un segundo commit exclusivamente
   documental, por ejemplo
   `docs(tasks): record TASK-285 PR verification`, y publicarlo mediante push
   normal. No modificar en este cierre el árbol restaurado ni otras tasks.
5. Volver a comprobar que la PR sigue abierta, no fusionada y con el head
   remoto igual al nuevo `HEAD`; registrar el workflow del segundo push sin
   repararlo.
6. No fusionar la PR y no cambiar el upstream de `main`.

### 14. Detenerse

No ejecutar TASK-284, TASK-272 a TASK-281, ninguna task preexistente en
`in-progress` ni cualquier otra task. No continuar con trabajo funcional.

## Files to Read First

- `AGENTS.md`
- `ai-platform.json`
- `ai/repo-context.md` desde `origin/main` mediante Git
- `ai/architecture-index.md` desde `origin/main` mediante Git
- `ai/task-template.md` desde `origin/main` mediante Git
- `ai/orchestrator/feature-planner.md` desde `origin/main` mediante Git
- `ai/tasks/blocked/TASK-000-verify-and-switch-hll-vietnam-repository-to-github.md`
- `ai/tasks/review/TASK-282-reconcile-gitea-and-github-histories.md`
- `ai/tasks/review/TASK-283-qualify-baseline-validation-and-complete-reconciliation.md`
- `ai/tasks/pending/TASK-284-repair-baseline-validation-debt.md`
- `.gitignore`
- diff completo de la PR #10 contra `origin/main`

Aunque determinados archivos existan físicamente, inspeccionar siempre sus
versiones canónicas con `git show origin/main:<path>` y su presencia versionada
con `git ls-tree`.

## Expected Files to Modify

- `.gitignore`, restaurado preferentemente de forma exacta desde
  `origin/main`;
- archivos versionados bajo `ai/` que deban restaurarse mecánicamente desde
  `origin/main`;
- TASK-000, TASK-282, TASK-283 y TASK-284 solo como re-aplicación exacta de
  sus blobs actuales, sin editar contenido ni lifecycle;
- tasks preexistentes en `in-progress` solo para preservarlas byte-identical,
  sin ejecutarlas, editarlas ni moverlas;
- esta TASK-285 al pasar por `in-progress` y terminar en `review` o `blocked`.

La restauración masiva desde `origin/main` está autorizada porque neutraliza
una eliminación masiva accidental. No editar manualmente cientos de archivos.

## Constraints

- No perder historia ni archivos locales protegidos.
- No recrear `dfb83d6` ni repetir la reconciliación.
- No usar reset, rebase, cherry-pick, squash, amend o force push.
- No modificar `origin/main`.
- No trabajar directamente sobre `main`.
- No cambiar el upstream de `main`.
- No eliminar ni modificar el remoto `gitea` o las ramas backup.
- No modificar backend, frontend, scripts de producto o deploy.
- No tocar RCON, CRCON, base de datos o despliegue.
- No ejecutar TASK-284, TASK-272 a TASK-281 ni ninguna otra task.
- No modificar el contenido o lifecycle de las tasks preexistentes en
  `in-progress`.
- No reparar workflows en esta task.
- No ocultar eliminaciones bajo reglas de `.gitignore`.
- No reconstruir manualmente archivos que deban restaurarse desde Git.
- No borrar, sobrescribir o añadir artefactos ignored/local-only no
  autorizados; bloquear ante ambigüedad.
- No fusionar la PR #10.

## Validation

TASK-285 solo puede terminar en `review` si:

- las eliminaciones masivas de AI Platform han desaparecido;
- no queda ningún `D` no intencionado bajo `ai/` en el diff de la PR;
- `ai/repo-context.md`, `ai/architecture-index.md`, `ai/task-template.md` y
  `ai/orchestrator/feature-planner.md` existen y son idénticos a
  `origin/main`;
- todo `ai/tasks/done/**` de `origin/main`, incluida TASK-271, está preservado;
- `.gitignore` es idéntico a `origin/main` y no ignora `ai/`;
- TASK-000, TASK-282, TASK-283 y TASK-284 conservan estado y contenido;
- TASK-272 a TASK-281 siguen byte-identical a `origin/main`;
- las tasks preexistentes en `in-progress` se conservan byte-identical y no se
  ejecutaron;
- los ancestor checks pasan;
- `git diff --check` pasa;
- `git fsck --full` no informa errores de integridad;
- no hay cambios de producto introducidos por TASK-285;
- la PR #10 sigue abierta y sin fusionar.

Las suites de producto no son relevantes para una restauración documental y
de metadata sin cambios de producto. Si el diff final confirma que
`backend/`, `frontend/`, `scripts/` y `deploy/` están intactos, documentar
expresamente que no se ejecutaron tests de producto; la validación aplicable
es Git, árbol canónico, lifecycle y PR.

## Outcome

Caso aprobado: se reparó la pérdida accidental de AI Platform en la rama de
reconciliación sin modificar producto ni reescribir historia.

- Rama: `chore/reconcile-gitea-github-history`.
- HEAD local inicial: `c4bc23f64fe6e94b4d7576f0e5718333952d0f9c`.
- HEAD remoto inicial de la rama de PR: `fd11f8e5548e3ebbb048647b9cc45da8305d571c`.
- `origin/main`: `cda6d72b4b2ca244ffc5bab7e6289761a5a114eb`.
- PR #10 antes de la reparación: 350 archivos, 1.156 inserciones, 35.106
  eliminaciones; 345 eliminaciones accidentales bajo `ai/`.
- Clasificación inicial de la PR: 4 archivos añadidos, 345 borrados y 1
  modificado; bajo `ai/`, 4 añadidos, 345 borrados y 0 modificados.
- Diff local inicial, incluida TASK-285: 351 archivos, 1.675 inserciones,
  35.106 eliminaciones.
- Se restauraron mecánicamente desde `origin/main` los 345 paths borrados de
  `ai/` y se restauró `.gitignore` exactamente desde `origin/main`.
- Commit correctivo: `90664d694b838fbd8e5ac87c6e9493466d234e26`
  (`fix(platform): preserve AI Platform history in reconciliation`).
- Tras el commit correctivo, el diff `origin/main...HEAD` contiene 5 archivos
  añadidos, 1.668 inserciones y 0 eliminaciones; son exclusivamente TASK-000,
  TASK-282, TASK-283, TASK-284 y TASK-285.
- Los 355 blobs versionados bajo `ai/` en `origin/main` son byte-identical en
  índice y worktree. Esto incluye `ai/repo-context.md`,
  `ai/architecture-index.md`, `ai/task-template.md`, los 14 archivos de
  `ai/orchestrator/` y los 317 archivos de `ai/tasks/done/`.
- `ai/tasks/done/TASK-271-split-rcon-live-ingestion-from-historical-materialization.md`
  existe y es byte-identical a `origin/main`.
- TASK-272 a TASK-281 siguen en `pending`, con contenido byte-identical a
  `origin/main`, y no se ejecutaron.
- TASK-284 sigue en `pending`. TASK-000, TASK-282 y TASK-283 conservaron sus
  rutas, estados y blobs de la rama.
- Los seis artefactos locales no versionados (TASK-204, TASK-242 y TASK-264,
  TASK-266, TASK-267, TASK-268) conservaron sus hashes SHA-256, no se
  añadieron al índice y permanecen en el worktree.
- Hashes preservados: TASK-204 `E082F71B07DE1B04DFA6795B56FD12479808AB7ECB494AF40C45B8940F05E00C`;
  TASK-242 `B53AA2C361F90273AE4D77826FCC41AEDE024226DE10374D1DD9C4878A3F80B4`;
  TASK-264 `412C79C59F234B90D50D0800C34C7B8581E3B9882D66ECA22606F8B00D2D8B07`;
  TASK-266 `A8F5FAD01DBCF114179208F6B9AA742ED62DBB3168D6D249A607CCBD500B47A2`;
  TASK-267 `A5DD66C07808C920AEDCE5ED53962E136FC944088707210EB3A7CE754D1F69E1`;
  TASK-268 `0CCA90430F8381E7AFA22CCE4907BA00FA15E48A2A2F7F9FA28E860EE1F8E340`.
- Se conserva la divergencia preexistente TASK-267: la versión histórica de
  `origin/main` está en `done` y la versión local no rastreada sigue en
  `in-progress`; TASK-285 no intentó resolver ese lifecycle.
- `.gitignore` es byte-identical a `origin/main`; no contiene `/ai/` y
  `ai/repo-context.md` ya no queda ignorado.
- `git diff --check` y `git diff --check origin/main...HEAD` pasaron después
  del commit. Antes del commit, `git diff --cached --check` contra el HEAD
  antiguo mostró whitespace ya presente en ocho blobs canónicos de
  `origin/main`; `git diff --cached --check origin/main --` pasó, demostrando
  que TASK-285 no lo introdujo.
- Los checks de ancestros para `006bfeb`, `5590987`, `3967b01`, `f522970` y
  `origin/main` pasaron. Los padres de `dfb83d6` no cambiaron.
- `git fsck --full` terminó con código 0; solo informó 86 objetos `dangling`,
  sin errores de integridad.
- `backend/`, `frontend/`, `scripts/` y `deploy/` no presentan diferencias de
  TASK-285. No se ejecutaron tests de producto porque no hubo cambios de
  producto; las validaciones aplicables fueron Git, árbol canónico, lifecycle
  y PR.
- Commits de lifecycle previos al cierre: `03dc80b2cddbe3e1cfba4f739e4bfcb1d46f5089`
  y `537829778803d732d542e907dff2ceb7194aad52`.
- Commit de paso a review: `3e812ac580b5c4d81628ad91c5a76bbb89dacc40`.
- Comandos de evidencia: `git diff --name-status origin/main...HEAD`,
  `git diff --shortstat origin/main...HEAD`, `git diff --diff-filter=D
  --name-only origin/main...HEAD -- ai`, `git diff --name-only
  origin/main...HEAD -- backend frontend scripts deploy`, `git diff --check`,
  `git fsck --full` y los cinco `git merge-base --is-ancestor` documentados.
- Primer push normal completado: el remoto quedó en
  `3e812ac580b5c4d81628ad91c5a76bbb89dacc40`.
- PR #10 (`https://github.com/devRaGonSa/hll-vietnam/pull/10`) observada abierta,
  no draft, no fusionada y `MERGEABLE`, con base `main`, head correcto, 5
  archivos, 1.714 inserciones y 0 eliminaciones. Su diff final observado tenía
  5 añadidos, 0 modificados y 0 borrados, todos bajo `ai/tasks/` y dentro de
  la allowlist.
- La descripción de PR #10 fue actualizada con la evidencia de preservación.
- El workflow del primer push, run `31335634568`, terminó inmediatamente en
  `failure` con cero jobs y sin logs; ningún worker ejecutó tasks. No se reparó
  el workflow por estar fuera de alcance.
- `main` conserva upstream `gitea/main`; el remoto Gitea y las ramas backup no
  se modificaron. PR #10 no se fusionó.
- No se ejecutó ni modificó ninguna task distinta de TASK-285.

### Resolución final mediante TASK-286

La reparación de preservación fue integrada mediante la PR #10 después de
verificar el head `a4fa5888bb122fdb5a9959426c0dc7b933e60ca9`, cinco paths
autorizados y cero eliminaciones. GitHub `main` conserva la historia
reconciliada y el árbol de AI Platform sin cambios de producto ni reescritura
de commits.

El remoto `gitea`, las ramas de respaldo y la rama de reconciliación
permanecen conservados. TASK-285 finaliza en `done`.

## Change Budget

- La excepción de restauración masiva desde `origin/main` está autorizada por
  el objetivo específico de esta task y puede superar las preferencias
  normales de 5 archivos y 200 líneas.
- Fuera de la restauración mecánica, limitar cambios manuales a `.gitignore`,
  lifecycle/Outcome de TASK-285 y documentación estrictamente necesaria.
- No crear tasks adicionales ni ampliar el alcance a producto o workflows.
