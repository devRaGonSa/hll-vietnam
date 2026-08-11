---
id: TASK-286
title: Finalize GitHub main migration and repository upstream
status: in-progress
type: platform
team: Arquitecto Python
supporting_teams: ["PM"]
roadmap_item: ai-platform-repository-source
priority: critical
---

# TASK-286 - Finalize GitHub main migration and repository upstream

## Goal

Convertir GitHub en la fuente operativa principal de HLL Vietnam, avanzar de
forma segura el `main` local hasta el `origin/main` reconciliado, cambiar su
upstream de `gitea/main` a `origin/main`, conservar Gitea y las ramas de
respaldo y cerrar correctamente las tasks de reconciliación sin ejecutar
ninguna task funcional pendiente.

## Context

La PR #10, `chore/reconcile-gitea-github-history -> main`, ya fue fusionada
mediante un merge commit normal.

- Head reconciliado:
  `a4fa5888bb122fdb5a9959426c0dc7b933e60ca9`.
- Merge commit de GitHub y `origin/main` observado tras la fusión:
  `151866825f0125477308a394f557bd63f32201d8`.
- El `main` local sigue en
  `f52297055ddf76550f48d0d2315ed0232a9670ef` y todavía tiene como upstream
  `gitea/main`.
- La historia local, incluidos `006bfeb`, `5590987`, `3967b01` y `f522970`,
  está incluida como ancestro de `origin/main`; por tanto, el avance de
  `main` debe poder hacerse mediante fast-forward.
- GitHub debe convertirse en la fuente operativa principal y `origin/main`
  debe ser el upstream de `main`.
- El remoto `gitea` debe conservarse con su URL actual como remoto histórico
  y de respaldo, pero debe dejar de ser el upstream de `main`.
- Las ramas de respaldo deben preservarse.
- La rama `chore/reconcile-gitea-github-history` debe preservarse por ahora.
- TASK-284 debe continuar pendiente.
- TASK-272 a TASK-281 deben continuar pendientes e intactas.
- TASK-264, TASK-266, TASK-267 y TASK-268 son artefactos locales
  preexistentes y no pueden modificarse ni ejecutarse.
- Ninguna task de producto debe ejecutarse durante esta operación.

La migración debe completarse sin reset, rebase, cherry-pick, force push ni
reescritura de historia. Si el `main` local ya no puede avanzar a
`origin/main` mediante fast-forward exclusivo, esta task debe bloquearse.

## Steps

### 1. Validar el estado inicial

1. Mover únicamente TASK-286 de `pending` a `in-progress`, actualizar su
   metadata a `status: in-progress` y no seleccionar ninguna otra task.
2. Leer íntegramente todos los archivos de `Files to Read First`.
3. Ejecutar:

   ```powershell
   git status --short --branch
   git branch --show-current
   git branch -vv
   git remote -v
   git worktree list
   git log --graph --decorate --oneline --all -n 50
   ```

4. Actualizar únicamente referencias:

   ```powershell
   git fetch origin
   git fetch gitea
   ```

5. No ejecutar todavía `git pull`.
6. Confirmar:

   ```powershell
   git rev-parse main
   git rev-parse origin/main
   git rev-parse gitea/main
   ```

7. El `origin/main` esperado inicialmente es
   `151866825f0125477308a394f557bd63f32201d8`. Si GitHub ha avanzado desde
   entonces, no asumir que es incorrecto: inspeccionar y documentar todos los
   commits adicionales antes de continuar. Bloquear si alguno invalida el
   alcance o las salvaguardas de esta task.

### 2. Demostrar que el cambio puede ser fast-forward

1. Antes de tocar `main`, ejecutar:

   ```powershell
   git merge-base --is-ancestor main origin/main
   ```

2. El exit code debe ser `0`.
3. Comprobar también:

   ```powershell
   git rev-list --left-right --count main...origin/main
   git log --left-right --oneline main...origin/main
   ```

4. No deben existir commits exclusivos en el `main` local que no estén
   contenidos en `origin/main`.
5. Si `main` ya no es ancestro de `origin/main`, mover TASK-286 a `blocked`,
   documentar la divergencia y detenerse. No hacer reset ni rebase.

### 3. Verificar el árbol de trabajo

1. Antes de cambiar de rama, ejecutar:

   ```powershell
   git status --porcelain
   ```

2. No continuar si existen cambios en archivos versionados sin commit o si
   archivos ajenos impiden aislar esta task.
3. Los artefactos locales no rastreados preexistentes deben preservarse byte a
   byte y quedar fuera del índice.
4. No usar automáticamente `stash`, `clean`, checkout destructivo ni
   `restore` sobre archivos ajenos.

### 4. Conservar referencias de seguridad

1. Confirmar que siguen existiendo localmente:

   ```text
   backup/local-main-before-github-reconcile-20260808
   backup/gitea-main-before-github-reconcile-20260808
   chore/reconcile-gitea-github-history
   ```

2. Verificar que ambas ramas backup siguen publicadas en GitHub:

   ```powershell
   git show-ref --verify refs/heads/backup/local-main-before-github-reconcile-20260808
   git show-ref --verify refs/heads/backup/gitea-main-before-github-reconcile-20260808
   git show-ref --verify refs/heads/chore/reconcile-gitea-github-history
   git ls-remote --heads origin refs/heads/backup/local-main-before-github-reconcile-20260808
   git ls-remote --heads origin refs/heads/backup/gitea-main-before-github-reconcile-20260808
   git ls-remote --heads origin refs/heads/chore/reconcile-gitea-github-history
   ```

3. Registrar sus SHAs y no eliminarlas, recrearlas ni moverlas.

### 5. Cambiar a main

1. Ejecutar:

   ```powershell
   git checkout main
   ```

2. No crear un nuevo `main`.

### 6. Avanzar main mediante fast-forward exclusivamente

1. Ejecutar:

   ```powershell
   git merge --ff-only origin/main
   ```

2. No crear un merge commit local.
3. No usar reset, hard reset, rebase, cherry-pick, force ni un `git pull`
   ambiguo.
4. Si `--ff-only` falla, mover TASK-286 a `blocked`, registrar el error y
   detenerse sin intentar una alternativa que reescriba o integre historia.

### 7. Cambiar upstream a GitHub

1. Comprobar primero que `main` y `origin/main` son exactamente el mismo
   commit.
2. Ejecutar:

   ```powershell
   git branch --set-upstream-to=origin/main main
   git branch -vv
   ```

3. El resultado debe mostrar `main [...] [origin/main]`. `main` no debe seguir
   mostrando `[gitea/main]`.

### 8. Conservar Gitea como remoto histórico

1. No eliminar ni renombrar el remoto `gitea`.
2. No modificar su URL.
3. No hacer push a Gitea.
4. Registrar en `Outcome` que:

   - GitHub es la fuente operativa primaria;
   - `origin/main` es el upstream de `main`;
   - Gitea queda preservado únicamente como remoto histórico y de respaldo.

### 9. Verificar identidad exacta de main

1. Ejecutar:

   ```powershell
   git rev-parse main
   git rev-parse origin/main
   git diff --exit-code main origin/main
   ```

2. Ambos SHAs deben ser idénticos y el diff debe devolver exit code `0`.

### 10. Verificar la historia reconciliada

Ejecutar y exigir exit code `0` para cada commit:

```powershell
git merge-base --is-ancestor 006bfeb main
git merge-base --is-ancestor 5590987 main
git merge-base --is-ancestor 3967b01 main
git merge-base --is-ancestor f522970 main
git merge-base --is-ancestor a4fa5888 main
```

Bloquear la task si falla cualquier comprobación.

### 11. Verificar AI Platform

1. Confirmar que existen:

   ```text
   ai/repo-context.md
   ai/architecture-index.md
   ai/task-template.md
   ```

2. Confirmar que `.gitignore` no ignora `/ai/` ni una regla general
   equivalente.
3. Ejecutar:

   ```powershell
   git check-ignore ai\repo-context.md
   ```

4. El archivo no debe quedar ignorado; el exit code esperado es `1`.

### 12. Verificar el backlog

1. Inventariar sin mover ni editar archivos:

   ```text
   ai/tasks/pending
   ai/tasks/in-progress
   ai/tasks/review
   ai/tasks/blocked
   ai/tasks/done
   ```

2. Confirmar que TASK-272 a TASK-281 siguen una vez cada una en `pending`, con
   `status: pending` y contenido intacto.
3. Confirmar que TASK-284 sigue en `pending` y no ha sido modificada.
4. Confirmar que TASK-264, TASK-266, TASK-267 y TASK-268 no han sido
   modificadas, movidas ni añadidas al índice.
5. No ejecutar ninguna task funcional ni preexistente.

### 13. Cerrar el lifecycle de la reconciliación

Solo después de validar correctamente la migración:

1. Actualizar el `Outcome` y mover, sin recrearlas:

   ```text
   TASK-282: review -> done
   TASK-283: review -> done
   TASK-285: review -> done
   ```

2. TASK-000 puede pasar de `blocked` a `done` únicamente si su `Outcome` final
   deja claramente documentado que:

   - la migración bloqueada fue resuelta por TASK-282, TASK-283, TASK-285 y
     TASK-286;
   - GitHub es ahora el upstream operativo;
   - Gitea queda como remoto histórico.

3. No eliminar ni recrear estas tasks.
4. No tocar TASK-284.

### 14. Lifecycle de TASK-286

1. Mover TASK-286 de `pending` a `in-progress` al comenzar la ejecución y
   actualizar `status: in-progress`.
2. Tras completar todas las validaciones y documentar el `Outcome`, moverla de
   `in-progress` a `review` y actualizar `status: review`.
3. No mover TASK-286 todavía a `done`; la revisión humana final debe confirmar
   que GitHub quedó como fuente principal.

### 15. Commit de lifecycle y documentación

1. Limitar los cambios versionados fundamentalmente al lifecycle y `Outcome`
   de TASK-000, TASK-282, TASK-283, TASK-285 y TASK-286.
2. No incluir archivos de producto ni artefactos locales preexistentes.
3. Añadir al índice cada ruta autorizada de forma explícita. No usar `git add
   .` ni `git add -A`.
4. Antes del commit, ejecutar:

   ```powershell
   git diff --cached --name-status
   git diff --cached --check
   ```

5. Crear un commit descriptivo únicamente si el índice contiene exactamente
   el alcance autorizado.

### 16. Push a GitHub

1. Después del commit, ejecutar:

   ```powershell
   git push origin main
   ```

2. Como `main` ya debe estar basado en `origin/main`, este push solo debe
   publicar los cambios documentales y de lifecycle posteriores a la
   migración.
3. No hacer force push ni push a Gitea.

### 17. Validación final

Ejecutar:

```powershell
git status --short --branch
git branch -vv
git remote -v
git rev-parse main
git rev-parse origin/main
git diff --exit-code main origin/main
git diff --check
git fsck --full
```

Resultado requerido:

```text
main -> origin/main
main == origin/main
working tree sin cambios versionados ni staged pendientes
```

Gitea, las ramas backup y la rama de reconciliación deben seguir existiendo.
Los artefactos locales no rastreados preexistentes pueden seguir visibles si
mantienen su contenido y estado previos; no deben añadirse, editarse ni
eliminarse para obtener un estado engañosamente limpio.

### 18. Detenerse

No ejecutar TASK-284, TASK-272 a TASK-281, ninguna task preexistente en
`in-progress` ni trabajo funcional. No usar `ai-platform run` ni iniciar
desarrollo adicional.

## Files to Read First

- `AGENTS.md`
- `ai-platform.json`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `ai/tasks/blocked/TASK-000-verify-and-switch-hll-vietnam-repository-to-github.md`
- `ai/tasks/review/TASK-282-reconcile-gitea-and-github-histories.md`
- `ai/tasks/review/TASK-283-qualify-baseline-validation-and-complete-reconciliation.md`
- `ai/tasks/review/TASK-285-preserve-ai-platform-history-in-reconciliation-pr.md`
- `ai/tasks/pending/TASK-284-repair-baseline-validation-debt.md`
- `.git/config` como configuración local no versionada

## Expected Files to Modify

- `.git/config`, solo localmente para cambiar el upstream de `main`; nunca
  incluirlo en el commit.
- lifecycle y `Outcome` de
  `ai/tasks/blocked/TASK-000-verify-and-switch-hll-vietnam-repository-to-github.md`.
- lifecycle y `Outcome` de
  `ai/tasks/review/TASK-282-reconcile-gitea-and-github-histories.md`.
- lifecycle y `Outcome` de
  `ai/tasks/review/TASK-283-qualify-baseline-validation-and-complete-reconciliation.md`.
- lifecycle y `Outcome` de
  `ai/tasks/review/TASK-285-preserve-ai-platform-history-in-reconciliation-pr.md`.
- esta TASK-286 al pasar de `pending` a `in-progress` y terminar en `review`.

Las rutas cambiarán al mover las tasks entre estados. No modificar archivos de
producto ni ninguna otra task.

## Constraints

- No reset ni hard reset.
- No rebase.
- No cherry-pick.
- No squash ni reescritura de historia.
- No force push.
- No eliminar ni modificar Gitea.
- No eliminar ni mover las ramas backup.
- No eliminar todavía la rama de reconciliación.
- No ejecutar tasks funcionales.
- No modificar ni ejecutar TASK-284.
- No modificar, mover ni ejecutar TASK-272 a TASK-281.
- No modificar, mover, añadir al índice ni ejecutar TASK-264, TASK-266,
  TASK-267 o TASK-268.
- No tocar backend, frontend, scripts, deploy, configuración RCON, CRCON, base
  de datos ni archivos de producto.
- No usar `ai-platform run` ni `ai-platform watch`.
- No usar `git add .` ni `git add -A`.
- No hacer push a Gitea.
- Bloquear TASK-286 si `main` no puede avanzar mediante fast-forward
  exclusivo.

## Validation

TASK-286 solo puede quedar en `review` si:

- `main` es exactamente igual a `origin/main`;
- `main` sigue `origin/main`;
- `gitea` permanece configurado con la misma URL;
- las ramas backup permanecen localmente y en GitHub;
- la rama de reconciliación permanece;
- la historia reconciliada es ancestro de `main`;
- AI Platform está versionada y no ignorada;
- TASK-272 a TASK-281 y TASK-284 permanecen pendientes e intactas;
- las tasks locales preexistentes permanecen intactas y fuera del índice;
- no se ejecutó ninguna task funcional;
- no existen cambios de producto;
- `git diff --check` pasa;
- `git fsck --full` no informa errores de integridad;
- el árbol no contiene cambios versionados o staged pendientes;
- no hubo force push, reset, rebase ni reescritura.

No son relevantes las suites de producto porque esta operación solo cambia
metadatos Git y documentación/lifecycle. Documentar expresamente que no se
ejecutaron tests de producto si el diff confirma que no hubo cambios de
producto.

## Outcome

Pendiente. Debe registrar como mínimo:

- SHA inicial del `main` local;
- SHA inicial y final de `origin/main`;
- resultado del ancestor check;
- resultado de `git rev-list --left-right --count`;
- resultado de `git merge --ff-only origin/main`;
- upstream anterior;
- upstream final;
- URL del remoto Gitea preservada de forma sanitizada;
- SHAs de las ramas backup y confirmación de su presencia en GitHub;
- SHA y presencia de la rama de reconciliación;
- tasks cerradas;
- backlog pendiente preservado;
- artefactos locales preexistentes preservados;
- commit creado;
- push realizado exclusivamente a GitHub;
- resultado de `git diff --check`;
- resultado de `git fsck --full`;
- estado Git final;
- confirmación de ausencia de cambios y tests de producto;
- confirmación de que no se ejecutó ninguna otra task.

## Change Budget

- Limitar los cambios versionados a TASK-000, TASK-282, TASK-283, TASK-285 y
  TASK-286.
- No modificar más de cinco archivos lógicos de task.
- No modificar archivos de producto.
- Bloquear y documentar cualquier necesidad de ampliar este alcance.
