# TASK-037-scheduled-local-snapshot-refresh

## Goal
Preparar una forma simple, clara y repetible de refrescar snapshots A2S reales de forma periódica en entorno local, reduciendo la dependencia de ejecución manual del colector.

## Context
El proyecto ya dispone de cliente A2S, targets reales verificados, colector funcional, persistencia SQLite y visualización en frontend. Actualmente el flujo depende de lanzar manualmente el colector para actualizar snapshots. El siguiente paso útil es dejar preparado un mecanismo sencillo de refresco periódico local que permita validar mejor el comportamiento histórico y la evolución de los datos.

## Steps
1. Revisar el flujo actual de captura manual de snapshots.
2. Definir una estrategia simple de refresco local, adecuada al estado actual del proyecto.
3. Preparar una forma clara de ejecutar capturas periódicas sin introducir infraestructura compleja de producción.
4. Mantener el diseño desacoplado para que en el futuro pueda reemplazarse por un scheduler más serio si hiciera falta.
5. Documentar cómo arrancar este refresco local y cómo detenerlo.
6. Si hace falta, añadir un modo seguro o flags para evitar comportamiento inesperado en desarrollo.
7. Mantener el alcance en refresco local y desarrollo, no en despliegue productivo.

## Files to Read First
- AGENTS.md
- ai/repo-context.md
- backend/README.md
- backend/app/config.py
- backend/app/collector.py
- backend/app/server_targets.py
- backend/app/storage.py

## Expected Files to Modify
- backend/README.md
- backend/app/config.py
- backend/app/collector.py
- opcionalmente archivos nuevos si mejoran claridad, por ejemplo:
  - backend/app/scheduler.py
  - backend/scripts/run_local_refresh.py

## Constraints
- No tocar frontend.
- No introducir un sistema de colas o infraestructura pesada.
- No añadir complejidad innecesaria.
- No hacer cambios destructivos.
- Mantener la solución simple y enfocada a entorno local.

## Validation
- Existe una forma documentada y funcional de refrescar snapshots periódicamente en local.
- El flujo sigue siendo controlable y fácil de detener.
- La solución encaja con el backend actual sin sobredimensionarlo.
- El sistema queda preparado para capturas más frecuentes y validación histórica.

## Change Budget
- Preferir menos de 5 archivos modificados o creados.
- Preferir menos de 180 líneas cambiadas.
## Outcome
- `backend/app/scheduler.py` aÃ±ade un bucle local de refresco periÃ³dico reutilizando el colector existente, sin introducir infraestructura de producciÃ³n ni dependencias nuevas.
- `backend/app/config.py` centraliza el intervalo por defecto mediante `HLL_BACKEND_REFRESH_INTERVAL_SECONDS`.
- `backend/README.md` documenta cÃ³mo arrancar el refresco local, cÃ³mo detenerlo con `Ctrl+C` y quÃ© flags de seguridad usar (`--interval`, `--no-fallback`, `--max-runs`).

## Validation Result
- Ejecutado: `python -m app.scheduler --source controlled --interval 1 --max-runs 1` desde `backend/`.
- Resultado: se ejecutÃ³ un ciclo persistido correctamente sobre `backend/data/hll_vietnam_dev.sqlite3` y el proceso terminÃ³ al alcanzar el lÃ­mite seguro de ejecuciones.
- Revisado en cÃ³digo: el refresco local queda desacoplado del servidor HTTP y reutiliza `collect_server_snapshots(...)` sin duplicar lÃ³gica del colector.

## Decision Notes
- El refresco periÃ³dico se resolviÃ³ como un bucle local explÃ­cito y controlable para desarrollo, en lugar de introducir un scheduler embebido en el backend HTTP o infraestructura mÃ¡s pesada.
