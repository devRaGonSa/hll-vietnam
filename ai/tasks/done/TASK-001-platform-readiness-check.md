# TASK-001-platform-readiness-check

## Goal
Validar que la integración de AI Development Platform en el repositorio HLL Vietnam está completa, coherente y lista para ejecutar tasks de forma segura con Codex.

## Context
El repositorio ya tiene una estructura base de producto y se ha integrado la capa operativa inspirada en ai-dev-platform-template. Antes de generar tasks funcionales del producto, hay que verificar que el flujo por tasks, documentación, scripts y estructura están realmente alineados y no contienen inconsistencias.

## Steps
1. Revisar la estructura de carpetas del repositorio.
2. Verificar que existen y son coherentes:
   - AGENTS.md
   - ai/task-template.md
   - ai/repo-context.md
   - ai/architecture-index.md
   - ai/system-metrics.md
   - ai/prompts/plan-feature.md
   - ai/orchestrator/*
   - ai/tasks/pending
   - ai/tasks/in-progress
   - ai/tasks/done
   - scripts/codex-runner.ps1
   - scripts/run-integration-tests.ps1
3. Confirmar que AGENTS.md refleja el flujo correcto:
   - el orquestador analiza código y redacta tasks
   - Codex no actúa fuera de tasks salvo mantenimiento o inspección explícita
   - backend previsto en Python
   - frontend actual en HTML/CSS/JS
4. Revisar que la documentación de contexto no contradice el proyecto HLL Vietnam.
5. Revisar que la task actual y la plantilla de task usan una estructura coherente con el template.
6. Si detectas incoherencias pequeñas, corrígelas.
7. Dejar un breve resumen en ai/system-metrics.md o en la documentación correspondiente si el flujo del repo ya lo contempla.

## Files to Read First
- AGENTS.md
- README.md
- docs/project-overview.md
- docs/decisions.md
- ai/task-template.md
- ai/repo-context.md
- ai/architecture-index.md
- ai/orchestrator/README.md
- scripts/codex-runner.ps1
- scripts/run-integration-tests.ps1

## Expected Files to Modify
- Solo los estrictamente necesarios si se detectan inconsistencias menores.
- No modificar archivos de producto salvo documentación mínima si es imprescindible.

## Constraints
- No implementar features del producto.
- No tocar la landing salvo que haya una inconsistencia documental o estructural.
- No añadir dependencias nuevas.
- No hacer cambios destructivos.
- Mantener el cambio pequeño y verificable.

## Validation
- La estructura AI Platform existe y es navegable.
- AGENTS.md refleja correctamente el flujo de trabajo del proyecto.
- No hay referencias obsoletas a .NET como arquitectura del producto.
- Los scripts clave existen.
- La plantilla de task es usable para futuras tasks.
- El repo queda listo para que el siguiente paso sea crear una task funcional real.

## Change Budget
- Preferir menos de 8 archivos modificados.
- Preferir menos de 250 líneas cambiadas.

## Outcome
- Verificada la existencia y coherencia de `AGENTS.md`, `ai/task-template.md`, `ai/repo-context.md`, `ai/architecture-index.md`, `ai/system-metrics.md`, `ai/prompts/plan-feature.md`, `ai/orchestrator/*`, `ai/tasks/*`, `scripts/codex-runner.ps1` y `scripts/run-integration-tests.ps1`.
- Confirmado que `AGENTS.md` refleja correctamente el flujo por tasks, el alcance de Codex y la dirección técnica actual: frontend en HTML/CSS/JS y backend futuro en Python.
- Corregidas dos incoherencias documentales menores:
  - `README.md` ya no presenta la plataforma AI como integración futura.
  - `docs/roadmap.md` ahora trata la orquestación como capacidad existente que debe evolucionar, no incorporarse desde cero.
- Validación manual completada. El script `scripts/run-integration-tests.ps1` existe, pero actualmente solo documenta que no hay tests de integración configurados para este alcance.
