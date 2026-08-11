---
id: TASK-000
title: Verify and switch HLL Vietnam repository source to GitHub
status: done
type: platform
team: Arquitecto Python
supporting_teams: ["PM"]
roadmap_item: ai-platform-repository-source
priority: critical
---

# TASK-000 - Verify and switch HLL Vietnam repository source to GitHub

## Goal

Garantizar que el workspace de HLL Vietnam, Codex App, Codex CLI y los runners de AI Platform trabajan sobre `devRaGonSa/hll-vietnam` en GitHub y no sobre Gitea, `devRaGonSa/ai-dev-platform-template` u otro repositorio.

## Context

Esta task es una puerta de preflight de plataforma y debe completarse antes de procesar cualquier task funcional posterior.

Durante la planificación en Codex App se observó:

- raíz del checkout: `D:/Proyectos/HLL Vietnam`;
- rama activa: `main`;
- `origin`: `https://github.com/devRaGonSa/hll-vietnam.git`;
- remoto adicional `gitea`: `https://rgonsal@git.devzamode.es/rgonsal/comunidadhll.git`;
- upstream configurado para `main`: `gitea/main`;
- worktree detectado: el checkout principal en `D:/Proyectos/HLL Vietnam`;
- `scripts/codex-runner.ps1` selecciona las tasks desde la ruta configurada en `ai-platform.json`;
- no se encontró otro watcher o runner de AI Platform en `scripts/`;
- `ai/tasks/pending` solo contenía `.gitkeep` y no se encontraron localmente archivos `TASK-272` a `TASK-281`.

Estos datos son observaciones de planificación, no una verificación definitiva. Codex CLI debe volver a comprobarlos, obtener referencias remotas y comparar historiales antes de cambiar configuración local, upstreams o archivos versionados. No debe asumir que Gitea y GitHub comparten el mismo historial.

Preserva la identidad del proyecto HLL Vietnam y limita cualquier cambio versionado a infraestructura operativa de AI Platform que contenga una referencia incorrecta confirmada.

## Steps

1. Leer primero los archivos indicados en `Files to Read First` y confirmar que el checkout corresponde a HLL Vietnam.
2. Ejecutar y registrar de forma sanitizada:
   - `git rev-parse --show-toplevel`
   - `git status --short --branch`
   - `git branch --show-current`
   - `git branch -vv`
   - `git remote -v`
   - `git remote get-url origin`
   - `git worktree list`
   - `git log -1 --oneline`
   - `git rev-parse HEAD`
3. Identificar todos los remotos y clasificarlos como GitHub, Gitea u otro proveedor, sin mostrar credenciales, tokens ni URLs autenticadas.
4. Determinar desde qué raíz y worktree se procesaría `ai/tasks/pending` y confirmar que pertenece al checkout de HLL Vietnam.
5. Buscar referencias versionadas a GitHub, Gitea, GTA, JTA, repositorios anteriores, `ai-dev-platform-template` y rutas absolutas que puedan afectar al runner, watcher, pull, push, selección del repositorio o procesamiento de `ai/tasks/pending`.
6. Confirmar que la raíz es el repositorio HLL Vietnam y no `devRaGonSa/ai-dev-platform-template`.
7. Confirmar si `origin` apunta exactamente a `https://github.com/devRaGonSa/hll-vietnam.git`.
8. Si `origin` no apunta al GitHub correcto:
   - conservar el remoto anterior como `gitea` o con otro nombre descriptivo no ocupado;
   - crear o modificar `origin` para que apunte a `https://github.com/devRaGonSa/hll-vietnam.git`;
   - no eliminar el remoto anterior;
   - no sobrescribir credenciales;
   - no imprimir tokens ni URLs autenticadas.
9. Ejecutar `git fetch origin` después de confirmar o corregir `origin`.
10. Obtener de forma segura las referencias necesarias del remoto anterior, si existe, sin modificar historiales locales.
11. Comparar y documentar:
    - `HEAD` local;
    - rama local activa;
    - `origin/main`;
    - la rama equivalente del remoto anterior;
    - commits exclusivos y relación de ancestros entre cada historial.
12. Si los historiales son compatibles y no hay pérdida de commits:
    - conservar todos los commits locales;
    - configurar `main` para utilizar `origin/main` como upstream cuando corresponda;
    - verificar que pull y push actuarán contra el GitHub correcto.
13. Si los historiales divergen, hay commits exclusivos en Gitea, la actualización exige un force push, o la migración es ambigua:
    - no hacer force push;
    - no hacer reset;
    - no hacer rebase automático;
    - no sobrescribir ramas;
    - documentar la divergencia y los commits exclusivos;
    - mover esta task a `ai/tasks/blocked`;
    - indicar con precisión la decisión humana necesaria;
    - detener la ejecución.
14. Revisar que `ai-platform.json` utiliza rutas relativas y específicas de HLL Vietnam.
15. Revisar que `scripts/codex-runner.ps1` carga `ai-platform.json`, procesa `ai/tasks/pending` desde el checkout correcto y no contiene rutas o repositorios ajenos.
16. Revisar cualquier otro runner o watcher realmente activo que se descubra, aunque no estuviera presente durante la planificación.
17. Verificar que no existen rutas absolutas hacia otro proyecto que puedan controlar pull, push, ejecución del runner o selección de tasks.
18. Modificar archivos versionados únicamente cuando contengan una referencia incorrecta real al proveedor, repositorio o checkout.
19. Ejecutar la validación final indicada en esta task.
20. Revisar `git diff --name-only` y confirmar que el diff se limita al alcance de plataforma.
21. Si existen cambios versionados validados, crear un commit descriptivo y hacer push explícitamente al GitHub correcto.
22. Si no existen cambios versionados, documentar que solo cambió la configuración local de `.git/config`, si aplica, y comprobar la conectividad segura con GitHub.
23. Mover esta task a `ai/tasks/done` únicamente si el repositorio queda verificado, el upstream es coherente y cualquier push necesario a GitHub termina correctamente.
24. No iniciar ni implementar ninguna otra task después de cerrar o bloquear esta task.

## Files to Read First

- `AGENTS.md`
- `ai-platform.json`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `ai/orchestrator/feature-planner.md`
- `scripts/codex-runner.ps1`
- `.git/config` como configuración local no versionada

Si durante la inspección se descubre otro runner o watcher de AI Platform realmente activo, leerlo antes de modificar cualquier configuración.

## Expected Files to Modify

- `.git/config`, solo localmente y únicamente si es seguro corregir remotos o upstreams; nunca incluirlo en un commit.
- `ai-platform.json`, solo si contiene una referencia incorrecta confirmada.
- `scripts/codex-runner.ps1`, solo si contiene una referencia incorrecta confirmada.
- otro runner o watcher realmente utilizado, solo si contiene una referencia incorrecta confirmada.
- documentación operativa relacionada, solo si debe corregirse para reflejar el repositorio real.
- esta task, al moverse a `ai/tasks/done` o `ai/tasks/blocked` y al documentar su resultado.

No asumir que todos estos archivos necesitan cambios. No modificar archivos de producto.

## Constraints

- No implementar ninguna `TASK-272` a `TASK-281`.
- No procesar ninguna otra task pendiente.
- No modificar backend, frontend, base de datos, RCON, CRCON ni despliegue de producto.
- No ejecutar `git reset --hard`.
- No ejecutar `git clean`.
- No hacer force push.
- No borrar ramas.
- No eliminar el remoto antiguo.
- No perder commits locales.
- No hacer rebase o merge automático entre historiales divergentes.
- No mostrar credenciales, tokens ni URLs autenticadas.
- No cambiar el repositorio `devRaGonSa/ai-dev-platform-template`.
- No sobrescribir archivos específicos de HLL Vietnam con archivos genéricos de la plantilla.
- No asumir que Gitea y GitHub tienen el mismo historial.
- No cambiar remotos o upstreams hasta comparar los historiales relevantes.
- No incluir `.git/config` en ningún commit.
- Detenerse y bloquear la task ante una migración ambigua o destructiva.
- Mantener los cambios pequeños, verificables y limitados a infraestructura de plataforma.

## Validation

Ejecutar y documentar como mínimo:

```text
git rev-parse --show-toplevel
git remote -v
git remote get-url origin
git branch -vv
git status --short --branch
git log -1 --oneline
git ls-remote origin
git worktree list
git diff --check
git diff --name-only
```

Confirmar además:

- `origin` apunta exactamente a `https://github.com/devRaGonSa/hll-vietnam.git`;
- la rama de trabajo tiene un upstream coherente con `origin/main`;
- `ai/tasks/pending` pertenece al checkout correcto;
- Codex CLI y los runners se ejecutan desde HLL Vietnam;
- `git pull` y `git push` resolverán contra el GitHub correcto;
- no existe una ruta absoluta operativa hacia otro proyecto;
- no se ha modificado ningún archivo de producto;
- no se ha ejecutado ni modificado ninguna `TASK-272` a `TASK-281`;
- el diff coincide con el alcance de plataforma;
- los historiales local, GitHub y remoto anterior se han comparado sin operaciones destructivas;
- el commit y el push a GitHub terminan correctamente cuando existen cambios versionados;
- si no hay tests de integración relevantes para este cambio de configuración, queda documentado explícitamente en el resultado.

## Outcome

Resultado del preflight del 2026-07-29:

- Repositorio y proveedor iniciales/finales: checkout HLL Vietnam en Git, con
  `origin` en GitHub y el remoto conservado `gitea` en Gitea. No se cambiaron
  remotos porque `origin` ya apunta exactamente a
  `https://github.com/devRaGonSa/hll-vietnam.git`.
- Rama y upstream: `main` en
  `5590987c0f441101059b9db54de15ff57964646d`, todavía con upstream
  `gitea/main`. No se cambió a `origin/main` porque los historiales divergen.
- Raíz y worktrees: `D:/Proyectos/HLL Vietnam`; solo se detectó el worktree
  principal en esa ruta. `ai/tasks/pending` resuelve dentro de ese checkout.
- Runner: `scripts/codex-runner.ps1` carga `ai-platform.json` y obtiene de él
  la ruta relativa `ai/tasks/pending`. `ai-platform.json` usa rutas relativas
  específicas de HLL Vietnam. Se observaron activos `ai-platform.exe run` y
  `powershell -File scripts/codex-runner.ps1`; no se modificaron.
- Referencias encontradas: `.git/config` conserva el remoto `gitea` hacia el
  repositorio anterior `comunidadhll`, configura `origin` hacia
  `devRaGonSa/hll-vietnam` y mantiene `main` siguiendo `gitea/main`. La propia
  task contiene las referencias de auditoría a Gitea, GitHub y
  `ai-dev-platform-template`. No se confirmó ninguna referencia incorrecta en
  `ai-platform.json` ni en `scripts/codex-runner.ps1`.
- Cambios en `.git/config`: ninguno. Los `fetch` solo actualizaron referencias
  remotas.
- Comparación después de `git fetch origin --prune` y
  `git fetch gitea --prune`:
  - `HEAD...origin/main`: 2 commits exclusivos locales y 10 exclusivos de
    GitHub.
  - `HEAD...gitea/main`: 1 commit exclusivo local y 0 exclusivos de Gitea.
  - `origin/main...gitea/main`: 10 commits exclusivos de GitHub y 1 exclusivo
    de Gitea.
  - merge base de GitHub y Gitea:
    `1f4bba38b1b11a354af7e7a7c8045882350ab964`.
  - exclusivo de Gitea respecto de GitHub:
    `006bfeba7d1a80b3b326e365e12ccdb9d107dc7d` (`HLL Vietnam V2`).
  - exclusivo local adicional:
    `5590987c0f441101059b9db54de15ff57964646d`
    (`docs(tasks): add GitHub repository preflight gate`).
  - exclusivos de GitHub: `06a8903`, `2d20d25`, `b0aad90`, `68eff3d`,
    `b199fc2`, `efd8f76`, `c88a590`, `ef5c0d3`, `feea8dc` y `cda6d72`.
- Archivos versionados modificados: únicamente esta task para registrar el
  bloqueo y moverla de estado. No se modificaron archivos de producto.
- Commit y push: no se creó commit ni se hizo push, porque cualquier
  integración automática sería ambigua y está prohibida por esta task.
- Validación ejecutada: raíz, estado, rama, upstream, remotos sanitizados,
  URL exacta de `origin`, worktrees, `HEAD`, fetch de ambos remotos, conteos
  left/right, relaciones de ancestros, merge bases y commits exclusivos.
  `git ls-remote origin` terminó correctamente y confirmó `origin/main` en
  `cda6d72b4b2ca244ffc5bab7e6289761a5a114eb`. `git diff --check` terminó
  correctamente. `git diff --name-only` solo muestra la retirada de la task
  de `ai/tasks/pending`; su copia bloqueada existe bajo `ai/tasks/blocked`,
  ruta ignorada por la regla local `/ai/` de `.gitignore`.
  Los tests de integración no son relevantes para este bloqueo de
  configuración y no se ejecutaron.
- Decisión humana necesaria: elegir cómo preservar e integrar en GitHub los
  commits `006bfeb` y `5590987` frente a los 10 commits exclusivos de
  `origin/main` (por ejemplo, mediante una integración revisada o una
  reconstrucción explícita de la rama). Después de esa decisión se podrá
  configurar `main` con upstream `origin/main`. No se debe hacer force push,
  reset, rebase ni merge automático.

La migración no puede garantizarse sin pérdida o sobrescritura de historia,
por lo que la task queda bloqueada y no se procesa ninguna task posterior.

### Resolución final mediante TASK-286

El bloqueo anterior queda resuelto. TASK-282 reconcilió las historias
preservadas sin reescribir commits; TASK-283 calificó los fallos como deuda
baseline preexistente; TASK-285 restauró y preservó AI Platform; y la PR #10
se integró en GitHub `main` mediante el merge commit normal
`151866825f0125477308a394f557bd63f32201d8`.

TASK-286 sincronizó el `main` local exclusivamente mediante fast-forward y
cambió su upstream de `gitea/main` a `origin/main`. GitHub queda como upstream
operativo y `gitea` se conserva sin cambios como remoto histórico y de
respaldo. TASK-000 finaliza en `done`.

## Change Budget

- Preferir menos de 5 archivos versionados modificados.
- Preferir menos de 200 líneas de cambios fuera de la propia task cuando sea viable.
- Crear una task de seguimiento en lugar de ampliar el alcance si se descubre otro problema independiente.
