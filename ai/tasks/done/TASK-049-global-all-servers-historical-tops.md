# TASK-049-global-all-servers-historical-tops

## Goal
Añadir soporte para rankings históricos globales agregando los tres servidores de la comunidad, de forma que el proyecto pueda mostrar tops totales además de tops por servidor.

## Context
Actualmente los rankings históricos están organizados por servidor. El siguiente paso es poder consultar tops globales, por ejemplo:
- top kills total
- top muertes total
- top soporte total
- top partidas con más de 100 kills total

La forma más limpia es tratar este agregado como una entidad lógica propia, por ejemplo `all-servers`, compatible con la capa de snapshots y con la futura UI.

## Steps
1. Revisar la estructura actual de rankings históricos por servidor.
2. Diseñar una estrategia clara para soportar rankings totales agregados, preferiblemente mediante una clave lógica como:
   - `all-servers`
3. Implementar el agregado global para:
   - top kills
   - top muertes
   - top soporte
   - top partidas con más de 100 kills
4. Asegurar que estos rankings globales:
   - no mezclan mal identidades de jugador
   - respetan la ventana semanal o política temporal definida
   - son compatibles con snapshots
5. Integrar el agregado global en resumen y metadatos cuando aplique.
6. Documentar la semántica de `all-servers`.
7. No crear todavía una UI nueva compleja en esta task si no es estrictamente necesario.
8. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- backend/README.md
- backend/app/historical_storage.py
- backend/app/historical_snapshot_storage.py
- backend/app/historical_snapshots.py
- backend/app/payloads.py
- backend/app/routes.py
- docs/historical-domain-model.md
- docs/historical-data-quality-notes.md

## Expected Files to Modify
- backend/app/historical_storage.py
- backend/app/historical_snapshot_storage.py
- backend/app/historical_snapshots.py
- backend/app/payloads.py
- backend/app/routes.py
- backend/README.md
- opcionalmente documentación técnica adicional

## Constraints
- No romper rankings por servidor existentes.
- No usar A2S para rankings globales históricos.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en el agregado global de tops y snapshots.

## Validation
- Existe soporte histórico para tops globales `all-servers`.
- Los rankings globales funcionan para las métricas ya soportadas.
- Los rankings por servidor siguen funcionando.
- La documentación backend refleja la nueva capacidad.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 6 archivos modificados o creados.
- Preferir menos de 240 líneas cambiadas.

## Outcome
- Se añadió la clave lógica `all-servers` para la capa histórica agregada sin crear una fila física adicional en `historical_servers`.
- `list_weekly_leaderboard()` y los payloads/snapshots asociados ya devuelven rankings globales para `kills`, `deaths`, `support` y `matches_over_100_kills`.
- `list_historical_server_summaries(server_slug='all-servers')` devuelve un resumen agregado con identidad estable `all-servers`.
- `list_snapshot_server_keys()` ya incluye `all-servers`, por lo que la capa de snapshots queda compatible con el agregado global.
- Validación local:
- `list_weekly_leaderboard(server_id='all-servers', metric='kills', limit=5)` devolvió resultados agregados con servidor lógico `all-servers`
- `build_historical_server_snapshots(server_key='all-servers')` devolvió `6` snapshots
- `build_weekly_leaderboard_snapshot_payload(server_id='all-servers', metric='kills')` devolvió `found: true`
