---
id: TASK-282
title: Reconcile Gitea and GitHub histories without rewriting commits
status: blocked
type: platform
team: Arquitecto Python
supporting_teams: ["PM"]
roadmap_item: ai-platform-repository-source
priority: critical
---

# TASK-282 - Reconcile Gitea and GitHub histories without rewriting commits

## Goal

Reconciliar de forma no destructiva la rama local y la historia de Gitea con `origin/main` de GitHub mediante ramas de respaldo, una rama de integración y un merge normal, preservando todos los commits, sin cambiar todavía el upstream de `main` y sin ejecutar las tasks funcionales incorporadas desde GitHub.

## Context

- `origin` ya apunta a `https://github.com/devRaGonSa/hll-vietnam.git`.
- `main` sigue actualmente `gitea/main`.
- Existe una base común en `1f4bba3`.
- La historia local contiene `006bfeb` y `5590987`.
- `origin/main` contiene diez commits adicionales con `TASK-272` a `TASK-281`.
- `43ca469` y el hotfix `e18177f` ya son anteriores a la divergencia y están compartidos.
- Existen tasks anteriores en `in-progress` que deben conservarse intactas.
- La reconciliación debe realizarse con una rama y Pull Request.
- No deben ejecutarse tasks funcionales durante esta operación.

## Steps

1. Ejecutar el preflight Git:
   - `git status --short --branch`
   - `git branch -vv`
   - `git remote -v`
   - `git worktree list`
   - `git fetch --all --prune`
   - `git log --graph --decorate --oneline --all -n 80`
   - `git merge-base main origin/main`
   - `git rev-list --left-right --count main...origin/main`
   - `git log --left-right --cherry-pick --oneline main...origin/main`
   - No ejecutar `git pull`.
2. Verificar los commits que deben preservarse:
   - `git merge-base --is-ancestor 006bfeb main`
   - `git merge-base --is-ancestor 5590987 main`
   - `git merge-base --is-ancestor e18177f main`
   - `git merge-base --is-ancestor e18177f origin/main`
   - Bloquear la task si cualquier resultado contradice la topología documentada.
3. Inventariar y no modificar los archivos existentes en `ai/tasks/in-progress`, `ai/tasks/review`, `ai/tasks/blocked` y `ai/tasks/done`.
   - En particular, no tocar `TASK-264`, `TASK-266`, `TASK-267` ni `TASK-268`.
4. Crear ramas de respaldo con la fecha real:
   - `backup/local-main-before-github-reconcile-YYYYMMDD`
   - `backup/gitea-main-before-github-reconcile-YYYYMMDD`
   - Publicarlas en `origin` sin force push.
5. Crear la rama de integración `chore/reconcile-gitea-github-history` desde el `main` local.
   - No trabajar directamente en `main`.
6. Mover únicamente `TASK-282` desde `pending` a `in-progress`.
7. En la rama de integración, fusionar GitHub:
   - `git merge --no-ff origin/main`
   - Mensaje: `Merge GitHub main into preserved HLL Vietnam history`
   - No usar `reset`, `rebase`, `cherry-pick`, `squash`, force push ni `--allow-unrelated-histories`.
8. Resolver conflictos individualmente.
   - Conservar `006bfeb`, `5590987`, `TASK-000` bloqueada, todas las tasks preexistentes y `TASK-272` a `TASK-281`.
   - No usar globalmente `ours` ni `theirs`.
   - Bloquear la task ante cualquier conflicto funcional ambiguo.
9. Verificar la historia resultante:
   - `git merge-base --is-ancestor 006bfeb HEAD`
   - `git merge-base --is-ancestor 5590987 HEAD`
   - `git merge-base --is-ancestor origin/main HEAD`
   - `git diff --check`
   - `git fsck --full`
10. Validar el proyecto:
   - `python -m compileall backend/app`
   - `Push-Location backend`
   - `python -m unittest discover -s tests`
   - `Pop-Location`
   - Ejecutar otras validaciones configuradas cuando sean pertinentes.
11. Mantener intacto el backlog.
   - Verificar que aparecen `TASK-272` a `TASK-281` en `pending`.
   - No ejecutarlas, no moverlas y no editar su contenido.
12. Actualizar `Outcome` y mover `TASK-282` a `ai/tasks/review/TASK-282-reconcile-gitea-and-github-histories.md`.
   - No moverla directamente a `done`.
13. Publicar ramas de respaldo y `chore/reconcile-gitea-github-history`.
   - Crear PR hacia `main` con título `chore: reconcile preserved Gitea history with GitHub main`.
   - No fusionar la PR ni cambiar el upstream.
14. Detenerse sin procesar ninguna otra task.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/tasks/blocked/TASK-000-verify-and-switch-hll-vietnam-repository-to-github.md`
- `ai/orchestrator/pm.md`
- `.git/config` como configuración local no versionada

## Expected Files to Modify

- `ai/tasks/pending/TASK-282-reconcile-gitea-and-github-histories.md`
- `ai/tasks/in-progress/TASK-282-reconcile-gitea-and-github-histories.md`
- `ai/tasks/review/TASK-282-reconcile-gitea-and-github-histories.md`

Solo cuando la ejecución de la task lo requiera y siempre dentro del alcance de reconciliación Git/documentación.

## Constraints

- No modificar producto durante la creación o ejecución de esta task.
- No ejecutar `TASK-282` desde Codex App durante su creación.
- No ejecutar `ai-platform run`.
- No modificar las tasks en `in-progress`.
- No cambiar remotos ni upstream dentro de esta preparación inicial.
- No usar reset, rebase, cherry-pick, squash ni force push.
- No borrar commits, ramas ni remotos.
- No mostrar credenciales.
- No hacer push desde la ejecución que crea esta task.

## Validation

Antes de dar por terminada la futura ejecución de esta task:

- `git diff --check`
- `git fsck --full`
- `python -m compileall backend/app`
- `Push-Location backend; python -m unittest discover -s tests; Pop-Location`
- `git diff --name-only`

Confirmar además:

- que `006bfeb`, `5590987` y `origin/main` son ancestros de `HEAD` tras el merge;
- que `TASK-272` a `TASK-281` quedan presentes pero intactas;
- que no se ejecutó ninguna task funcional;
- que no se cambió el upstream de `main`;
- que la reconciliación queda publicada mediante PR y no mediante cambios destructivos de historia.

## Outcome

Ejecución bloqueada durante la puerta de validación del 2026-08-08.

- Estado inicial verificado después de `git fetch --all --prune`:
  - `main`: `f52297055ddf76550f48d0d2315ed0232a9670ef`;
  - `gitea/main`: `006bfeba7d1a80b3b326e365e12ccdb9d107dc7d`;
  - `origin/main`: `cda6d72b4b2ca244ffc5bab7e6289761a5a114eb`;
  - merge-base: `1f4bba38b1b11a354af7e7a7c8045882350ab964`;
  - divergencia: cuatro commits exclusivos locales y diez exclusivos de
    GitHub.
- La topología coincidía con la documentada. `006bfeb`, `5590987`,
  `3967b01`, `f522970` y `e18177f` eran ancestros de `main` cuando
  correspondía; `e18177f` también era ancestro de `origin/main`.
- Ramas de respaldo creadas y publicadas sin force push:
  - `backup/local-main-before-github-reconcile-20260808` en `f522970`;
  - `backup/gitea-main-before-github-reconcile-20260808` en `006bfeb`.
- Rama de integración creada desde el `main` preservado:
  `chore/reconcile-gitea-github-history`.
- La transición de esta task a `in-progress` quedó registrada en
  `b333d3d27b8e2603994ab185ade6ec86e092a61c`.
- El merge normal `git merge --no-ff origin/main` terminó sin conflictos.
  Commit de merge:
  `dfb83d6f7f5732879446b9b441aede7473c9db8e`, con padres `b333d3d` y
  `cda6d72`.
- Comprobaciones posteriores de ancestros: `006bfeb`, `5590987`, `3967b01`,
  `f522970` y `origin/main` devolvieron exit code `0` frente a `HEAD`.
- `TASK-272` a `TASK-281` quedaron presentes una vez cada una en `pending`,
  con `status: pending` y contenido idéntico a `origin/main`. No se ejecutaron,
  editaron ni movieron.
- `TASK-264`, `TASK-266`, `TASK-267` y `TASK-268`, y el resto de archivos
  preexistentes en `in-progress`, `review`, `blocked` y `done`, conservaron su
  contenido. Solo esta task cambió de estado.
- Auditoría Git:
  - `git diff --check`: exit code `0`;
  - `git diff --check f522970..HEAD`: exit code `0`;
  - `git fsck --full`: exit code `0`; solo informó objetos colgantes, sin
    errores de integridad;
  - la diferencia exclusiva local respecto de `origin/main` se limita a
    `.gitignore` y a infraestructura/documentación bajo `ai/**`; no aporta
    cambios en `backend`, `frontend` ni `scripts`.
- Validación de proyecto:
  - `python -m compileall backend/app`: correcta;
  - `python -m unittest discover -s tests`: `130` tests en `17.820s`, con
    `1` fallo y `2` errores;
  - fallos reproducidos de forma aislada:
    `test_cleanup_exception_is_logged_and_runner_continues`,
    `test_public_scoreboard_fallback_used_only_without_rcon_activity` y
    `test_recent_matches_prefer_materialized_rcon_over_scoreboard_fallback`;
  - `scripts/run-integration-tests.ps1`: la validación historical UI pasó y
    la validación Stats falló porque no encontró el formulario de ranking
    anual esperado.
- `git diff f522970..HEAD -- backend frontend scripts` no muestra cambios;
  corregir estos fallos de la línea base ampliaría el alcance a producto y
  está prohibido por esta task.
- Los pushes de las ramas de respaldo dispararon dos runs del workflow
  `codex-worker.yml`, pero ambos terminaron con `jobs: []`; no se ejecutó
  Codex ni ninguna task.
- No se usó reset, rebase, cherry-pick, squash, force push ni
  `--allow-unrelated-histories`. No se cambiaron remotos ni el upstream de
  `main`, que continúa en `gitea/main`.
- Debido a que las validaciones obligatorias no están en verde, la rama de
  integración no se publica y no se crea Pull Request. La reconciliación queda
  preservada localmente y la task se bloquea para no ocultar los fallos ni
  modificar producto fuera de alcance.

## Change Budget

- Prefer fewer than 5 modified files during task creation.
- Prefer documentation and Git metadata changes only until the reconciliation run begins.
- Split any new ambiguity into a follow-up blocked/review decision instead of widening the task.
