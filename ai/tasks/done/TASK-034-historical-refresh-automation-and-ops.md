# TASK-034-historical-refresh-automation-and-ops

## Goal
Automatizar y documentar el refresco periódico del histórico CRCON para ambos servidores de la comunidad, dejando el sistema preparado para mantenerse actualizado sin intervención manual constante.

## Context
Ya existe ingesta bootstrap, refresco incremental y validación de calidad histórica. El siguiente paso técnico es estabilizar la operativa del histórico con un flujo repetible y documentado que permita mantener actualizados los datos históricos de forma consistente.

## Steps
1. Revisar la ingesta histórica actual y el refresco incremental ya implementado.
2. Diseñar la estrategia operativa de refresco histórico:
   - frecuencia recomendada
   - modo de ejecución local
   - modo de ejecución automatizada
   - control de errores y reintentos básicos
3. Implementar un mecanismo razonable para lanzar el refresco histórico periódicamente o dejarlo listo para ello.
4. Registrar metadatos mínimos de operación:
   - último refresco ejecutado
   - resultado
   - errores básicos si ocurren
5. Documentar claramente cómo ejecutar y mantener esta capa histórica.
6. No crear todavía dashboards de operaciones complejos.
7. No romper el flujo actual de live status.
8. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- backend/README.md
- backend/app/config.py
- backend/app/historical_ingestion.py
- backend/app/historical_storage.py
- docs/historical-domain-model.md
- docs/historical-data-quality-notes.md

## Expected Files to Modify
- backend/README.md
- backend/app/config.py
- backend/app/historical_ingestion.py
- opcionalmente nuevos módulos/entrypoints si mejoran la automatización, por ejemplo:
  - backend/app/historical_jobs.py
  - backend/app/historical_runner.py
- opcionalmente documentación técnica adicional

## Constraints
- No crear UI histórica en esta task.
- No romper la ingesta actual.
- No introducir complejidad operativa excesiva.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en automatización y operativa del histórico.

## Validation
- Existe una estrategia clara y ejecutable de refresco periódico histórico.
- La documentación explica cómo ejecutar el refresco.
- La capa histórica queda operativamente más estable.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 5 archivos modificados o creados.
- Preferir menos de 220 líneas cambiadas.
## Outcome
- Se aÃ±adiÃ³ `backend/app/historical_runner.py` para ejecutar refresh incremental periÃ³dico.
- Se incorporaron variables de configuraciÃ³n para intervalo, reintentos y espera entre reintentos.
- La operativa queda documentada en `backend/README.md`.
- El registro operativo sigue apoyÃ¡ndose en `historical_ingestion_runs` para dejar Ãºltimo refresh, resultado y errores bÃ¡sicos.

## Validation Notes
- `python -m compileall app`
- validaciÃ³n estÃ¡tica del runner y de los getters de configuraciÃ³n
- no se ejecutÃ³ refresh real contra red externa por las restricciones del entorno actual
