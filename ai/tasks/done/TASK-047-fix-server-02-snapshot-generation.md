# TASK-047-fix-server-02-snapshot-generation

## Goal
Diagnosticar y corregir por qué `comunidad-hispana-02` sigue apareciendo sin snapshots válidos en la UI histórica, asegurando que resumen, tops y partidas recientes se generen y queden disponibles igual que en `comunidad-hispana-01`.

## Context
La capa histórica ya genera snapshots funcionales para al menos uno de los servidores, pero en la práctica `comunidad-hispana-02` sigue mostrando estados vacíos o “sin snapshot” en la interfaz. El problema no parece ser la ausencia de soporte de servidor en el código, sino un fallo de generación, persistencia, selección o consumo de snapshots. Antes de seguir ampliando la plataforma histórica, hay que dejar corregida la paridad entre ambos servidores actuales.

## Steps
1. Revisar la configuración histórica actual de `comunidad-hispana-01` y `comunidad-hispana-02`.
2. Revisar la ruta completa de snapshots para ambos servidores:
   - histórico bruto
   - generación de snapshots
   - persistencia de snapshots
   - lectura de snapshots
   - consumo frontend
3. Identificar por qué `comunidad-hispana-02` no devuelve snapshots válidos aunque exista histórico bruto o soporte parcial.
4. Corregir la causa raíz, ya sea en:
   - mapeo de servidor
   - generación
   - persistencia
   - recuperación
   - cache frontend
5. Asegurar que para `comunidad-hispana-02` queden disponibles snapshots de:
   - resumen
   - leaderboard semanal por métrica
   - partidas recientes
6. Verificar que ambos servidores actuales se comportan de forma equivalente.
7. Documentar brevemente la causa detectada y la corrección.
8. No añadir todavía el servidor #03 en esta task.
9. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- backend/README.md
- backend/app/config.py
- backend/app/historical_ingestion.py
- backend/app/historical_storage.py
- backend/app/historical_snapshot_storage.py
- backend/app/historical_snapshots.py
- backend/app/payloads.py
- backend/app/routes.py
- frontend/historico.html
- frontend/assets/js/historico.js
- frontend/assets/css/historico.css
- docs/historical-coverage-report.md
- docs/historical-data-quality-notes.md

## Expected Files to Modify
- backend/app/historical_ingestion.py
- backend/app/historical_storage.py
- backend/app/historical_snapshot_storage.py
- backend/app/historical_snapshots.py
- backend/app/payloads.py
- backend/app/routes.py
- frontend/assets/js/historico.js
- backend/README.md
- opcionalmente documentación técnica adicional si ayuda a dejar trazabilidad

## Constraints
- No usar A2S para esta corrección.
- No crear páginas nuevas.
- No romper el flujo actual de `comunidad-hispana-01`.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en que `comunidad-hispana-02` tenga snapshots funcionales.

## Validation
- `comunidad-hispana-02` deja de mostrar estados vacíos si existe histórico suficiente.
- Resumen, tops y partidas recientes funcionan también para `comunidad-hispana-02`.
- No se rompe `comunidad-hispana-01`.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 7 archivos modificados o creados.
- Preferir menos de 260 líneas cambiadas.

## Outcome
- Causa detectada: `comunidad-hispana-02` ya tenía histórico bruto persistido, pero la API de snapshots devolvía `found: false` cuando faltaba la fila precalculada en `historical_precomputed_snapshots`, sin recomponerla desde `historical_*`.
- Corrección aplicada: los builders de payload histórico ahora regeneran automáticamente el lote de snapshots del servidor solicitado cuando falta una fila precalculada y luego reintentan la lectura.
- Validación realizada:
- simulación sobre una copia del SQLite eliminando las filas de snapshot de `comunidad-hispana-02`
- la API recompuso `6` snapshots del servidor y devolvió `found: true` para resumen, ranking semanal y partidas recientes
- verificado también el SQLite real: `comunidad-hispana-02` queda con `6` snapshots persistidos
