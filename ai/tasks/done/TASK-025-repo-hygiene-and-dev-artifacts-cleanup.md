# TASK-025-repo-hygiene-and-dev-artifacts-cleanup

## Goal
Dejar el repositorio HLL Vietnam en un estado mas limpio y consistente eliminando o regularizando artefactos locales de desarrollo, ficheros de lock y residuos de workflow que no deberian quedar como ruido permanente en el worktree.

## Context
Despues de varias tasks ejecutadas por el workflow, siguen apareciendo residuos locales o inconsistencias de higiene del repositorio, entre ellos:
- `ai/worker.lock`
- `backend/data/hll_vietnam_dev.sqlite3`
- `ai/tasks/done/TASK-021-server-status-periodic-query-and-display.md` como untracked o no regularizado
- posibles cambios locales en `backend/app/config.py`

Estos elementos no forman parte directa del valor de producto visible, pero si afectan a la salud del repositorio, al flujo del worker y a la claridad del estado git. Hace falta una pasada de limpieza controlada para dejar reglas claras sobre que debe versionarse y que debe considerarse artefacto local de desarrollo.

## Steps
1. Revisar el estado actual del repositorio y confirmar que archivos siguen quedando como ruido local o inconsistencias.
2. Analizar especificamente:
   - `ai/worker.lock`
   - `backend/data/hll_vietnam_dev.sqlite3`
   - `ai/tasks/done/TASK-021-server-status-periodic-query-and-display.md`
   - `backend/app/config.py`
3. Determinar para cada uno de ellos si debe:
   - versionarse
   - ignorarse
   - regenerarse localmente
   - moverse o regularizarse
4. Ajustar `.gitignore` u otros mecanismos de higiene si hace falta.
5. Asegurar que los artefactos locales de desarrollo no sigan ensuciando el worktree innecesariamente.
6. Regularizar el estado de la task `TASK-021` si quedo fuera del flujo esperado.
7. Documentar de forma minima, si hace falta, el tratamiento esperado de snapshots persistidos, locks locales y otros artefactos de runtime.
8. No tocar logica funcional de producto salvo que sea estrictamente necesario para dejar el repo coherente.
9. Al completar la implementacion:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- .gitignore
- ai/README.md
- ai/orchestrator/README.md
- backend/README.md
- backend/app/config.py
- cualquier documentacion existente sobre snapshots o runtime local
- salida actual de `git status`

## Expected Files to Modify
- .gitignore
- backend/README.md
- opcionalmente ai/README.md o documentacion minima si hace falta aclarar el tratamiento de artefactos locales
- opcionalmente regularizacion de archivos en `ai/tasks/done/`
- opcionalmente eliminacion o exclusion de artefactos locales no deseados

## Constraints
- No romper el workflow actual del proyecto.
- No eliminar informacion util sin justificarlo.
- No tocar frontend salvo que fuera completamente imprescindible.
- No introducir cambios funcionales de producto.
- No hacer cambios destructivos fuera del objetivo de higiene del repo.
- Mantener el resultado claro, pequeno y seguro.

## Validation
- El worktree queda sensiblemente mas limpio.
- Los artefactos de desarrollo local quedan tratados de forma explicita.
- `ai/worker.lock` no queda como ruido permanente si no debe versionarse.
- El tratamiento de `backend/data/hll_vietnam_dev.sqlite3` queda resuelto.
- `TASK-021` queda regularizada si estaba fuera del flujo.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 6 archivos modificados.
- Preferir menos de 180 lineas cambiadas.

## Outcome
- `.gitignore` pasa a tratar `ai/worker.lock` y `backend/data/*.sqlite3` como artefactos locales de runtime en lugar de ruido permanente versionado.
- `backend/data/.gitkeep` mantiene el directorio de datos en el repositorio sin forzar que la base SQLite de desarrollo quede commiteada.
- `ai/tasks/done/TASK-021-server-status-periodic-query-and-display.md` queda regularizada dentro del historial versionado de tasks completadas.
- El cambio pendiente de `backend/app/config.py` queda absorbido como parte de la regularizacion de `TASK-021`, en lugar de seguir apareciendo como residuo suelto.

## Validation Result
- Revisado `git status --short` para confirmar que el ruido original del worktree quedaba centrado en `ai/worker.lock`, `backend/data/hll_vietnam_dev.sqlite3`, `backend/app/config.py` y la task `TASK-021`.
- Revisadas las referencias de runtime en `scripts/codex-runner.ps1`, `backend/app/config.py` y `backend/README.md` para confirmar que el lock y la SQLite son artefactos regenerables de desarrollo local.
- Validacion final prevista: `git diff --name-only` debe reflejar solo la higiene de ignores, la regularizacion de archivos versionados y la task cerrada.

## Decision Notes
- `ai/worker.lock` se trata como lock efimero del runner local y no aporta valor historico en git.
- `backend/data/hll_vietnam_dev.sqlite3` se mantiene como persistencia local regenerable; el contrato util esta en codigo y documentacion, no en una base SQLite concreta del worktree.
