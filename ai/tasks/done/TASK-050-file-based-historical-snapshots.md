# TASK-050-file-based-historical-snapshots

## Goal
Migrar la capa de snapshots históricos orientados a UI desde almacenamiento SQLite a archivos JSON independientes en disco, manteniendo SQLite para el histórico bruto y dejando los snapshots como artefactos rápidos, inspeccionables y fáciles de servir.

## Context
El proyecto ya usa snapshots precalculados, pero actualmente se almacenan en SQLite. Se quiere cambiar el enfoque para que cada snapshot UI exista como archivo JSON independiente, actualizado periódicamente por backend y consumido a través de la API propia. La razón es reducir complejidad percibida, facilitar inspección/depuración y reforzar una carga rápida y estable del frontend.

El histórico bruto persistido en SQLite debe mantenerse. Lo que cambia en esta task es solo la capa de snapshots precalculados de UI.

## Steps
1. Revisar la capa actual de snapshots precalculados en SQLite.
2. Diseñar una nueva estructura de archivos para snapshots en disco, por ejemplo:
   - `backend/data/snapshots/comunidad-hispana-01/server-summary.json`
   - `backend/data/snapshots/comunidad-hispana-01/weekly-kills.json`
   - `backend/data/snapshots/comunidad-hispana-01/weekly-deaths.json`
   - `backend/data/snapshots/comunidad-hispana-01/weekly-support.json`
   - `backend/data/snapshots/comunidad-hispana-01/weekly-matches-over-100-kills.json`
   - `backend/data/snapshots/comunidad-hispana-01/recent-matches.json`
   - y equivalentes para `comunidad-hispana-02`, `comunidad-hispana-03` y `all-servers`
3. Implementar almacenamiento y lectura de snapshots en JSON.
4. Migrar la generación de snapshots para que escriba estos archivos.
5. Mantener metadatos útiles dentro de cada snapshot, como:
   - generated_at
   - source_range_start
   - source_range_end
   - freshness / is_stale
   - found
   - política semanal usada si aplica
6. Mantener SQLite para histórico bruto y no mezclar ambas capas.
7. Documentar claramente la nueva arquitectura:
   - histórico bruto en SQLite
   - snapshots UI en archivos JSON
8. No romper todavía la UI actual.
9. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- backend/README.md
- backend/app/historical_storage.py
- backend/app/historical_snapshot_storage.py
- backend/app/historical_snapshots.py
- backend/app/historical_runner.py
- backend/app/payloads.py
- backend/app/routes.py
- docs/historical-domain-model.md

## Expected Files to Modify
- backend/README.md
- backend/app/historical_snapshot_storage.py
- backend/app/historical_snapshots.py
- backend/app/historical_runner.py
- backend/app/payloads.py
- backend/app/routes.py
- opcionalmente nuevos módulos auxiliares, por ejemplo:
  - backend/app/historical_file_snapshots.py
- opcionalmente documentación técnica adicional

## Constraints
- No eliminar SQLite del histórico bruto.
- No romper la API histórica existente salvo para adaptarla a la nueva fuente de snapshots.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en pasar snapshots UI a JSON en disco.

## Validation
- Los snapshots UI se generan y guardan como archivos JSON independientes en disco.
- El histórico bruto sigue persistiendo en SQLite.
- La API histórica puede servir esos snapshots correctamente.
- La estructura es inspeccionable y mantenible.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 7 archivos modificados o creados.
- Preferir menos de 260 líneas cambiadas.

## Outcome
- La persistencia de snapshots históricos orientados a UI se migró de SQLite a archivos JSON bajo `backend/data/snapshots/<server_key>/`.
- `historical_snapshot_storage.py` conserva la misma interfaz pública (`persist_*`, `get_*`, `list_*`) pero ahora escribe y lee archivos como `server-summary.json`, `weekly-kills.json` y `recent-matches.json`.
- SQLite se mantiene exclusivamente para el histórico bruto (`historical_*`) y ya no es la fuente de lectura de snapshots UI.
- Validación local:
- `generate_and_persist_historical_snapshots(server_key='comunidad-hispana-03')` y `generate_and_persist_historical_snapshots(server_key='all-servers')` escribieron su lote de `6` archivos JSON cada uno
- verificado el árbol `backend/data/snapshots/` con `24` archivos JSON esperados para `comunidad-hispana-01`, `comunidad-hispana-02`, `comunidad-hispana-03` y `all-servers`
- los payloads `build_historical_server_summary_snapshot_payload(server_slug='comunidad-hispana-02')`, `build_weekly_leaderboard_snapshot_payload(server_id='all-servers', metric='kills')` y `build_recent_historical_matches_snapshot_payload(server_slug='comunidad-hispana-03')` devolvieron `found: true`
