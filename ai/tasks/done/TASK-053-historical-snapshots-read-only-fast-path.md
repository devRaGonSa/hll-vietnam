# TASK-053-historical-snapshots-read-only-fast-path

## Goal
Asegurar que los endpoints de snapshots históricos se comportan como una capa de lectura rápida y no intentan recomponer o regenerar snapshots costosos durante la solicitud del usuario.

## Context
La página histórica debe sentirse rápida. Para conseguirlo, los snapshots deben existir previamente y leerse de forma casi inmediata. Si una petición a la UI termina provocando una recomposición, una regeneración parcial o una ruta de fallback costosa, el tiempo percibido se degrada mucho. La generación debe vivir en la capa de bootstrap/runner/scheduler, no en la interacción del usuario.

## Steps
1. Revisar la implementación actual de los endpoints de snapshots históricos y la lógica de payload para:
   - resumen
   - weekly leaderboard
   - partidas recientes
2. Identificar si alguna de esas rutas intenta recomponer, regenerar o recalcular snapshots costosos durante la petición.
3. Corregir el comportamiento para que los endpoints de snapshots:
   - lean snapshots ya existentes
   - respondan rápido
   - devuelvan metadatos claros si el snapshot no está listo
   - no bloqueen la solicitud por regeneración pesada
4. Mantener el sistema de generación y refresco de snapshots en la capa operativa adecuada:
   - bootstrap
   - refresh
   - runner periódico
5. Asegurar que cuando un snapshot no exista, la respuesta sea rápida y clara, sin dejar al usuario esperando recomposición pesada.
6. Documentar el contrato operativo esperado: lectura rápida en request path, generación fuera del request path.
7. No cambiar la UI en esta task salvo lo estrictamente necesario para reflejar metadatos ya existentes.
8. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- backend/README.md
- backend/app/routes.py
- backend/app/payloads.py
- backend/app/historical_snapshot_storage.py
- backend/app/historical_snapshots.py
- backend/app/historical_runner.py
- backend/app/historical_ingestion.py

## Expected Files to Modify
- backend/app/routes.py
- backend/app/payloads.py
- backend/app/historical_snapshot_storage.py
- backend/app/historical_snapshots.py
- backend/README.md
- opcionalmente documentación técnica adicional si hace falta dejar la política clara

## Constraints
- No usar A2S para esta capa.
- No volver a agregados on-demand pesados como estrategia principal.
- No crear páginas nuevas.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en un fast read path para snapshots.

## Validation
- Los endpoints de snapshots responden como lectura rápida.
- No hay recomposición pesada o regeneración costosa en el request path del usuario.
- Si un snapshot no existe, la respuesta es rápida y clara.
- La documentación deja clara la política operativa.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 5 archivos modificados o creados.
- Preferir menos de 220 líneas cambiadas.

## Outcome
- Los endpoints `/api/historical/snapshots/*` ya no intentan recomponer ni regenerar snapshots durante la petición del usuario.
- Cuando un snapshot no existe, la API responde rápido con metadata explícita de fast path: `snapshot_status`, `missing_reason`, `request_path_policy` y `generation_policy`.
- La política operativa queda documentada en `backend/README.md`: lectura rápida en request path y generación solo en `historical_ingestion` o `historical_runner`.
- Validación local:
- import y ejecución de `build_historical_server_summary_snapshot_payload(server_slug='comunidad-hispana-01')`
- `py_compile` sobre `backend/app/payloads.py`, `backend/app/routes.py` y `backend/app/historical_snapshot_storage.py`
