# TASK-057-server-03-historical-bootstrap-and-snapshots

## Goal
Cargar histórico real para `comunidad-hispana-03` desde su fuente CRCON configurada, persistirlo en la base histórica del proyecto y generar los snapshots necesarios para que la UI deje de mostrarlo como pendiente de bootstrap.

## Context
El servidor `comunidad-hispana-03` ya existe en la configuración del proyecto, pero actualmente la UI lo muestra con un estado honesto de “pendiente de histórico” porque todavía no se ha ejecutado bootstrap/backfill real para ese servidor. El objetivo de esta task es convertir ese servidor en un origen histórico real dentro del producto, dejándolo operativo igual que `#01` y `#02`.

## Steps
1. Revisar la configuración actual del servidor `comunidad-hispana-03`.
2. Confirmar que la fuente histórica configurada sigue siendo válida y accesible.
3. Ejecutar bootstrap/backfill real para `comunidad-hispana-03` con un enfoque operativo seguro y reanudable.
4. Persistir en SQLite:
   - matches
   - players
   - stats por match
   - progreso/backfill
5. Generar snapshots JSON para `comunidad-hispana-03`, al menos de:
   - server-summary
   - weekly-kills
   - weekly-deaths
   - weekly-matches-over-100-kills
   - weekly-support
   - recent-matches
6. Verificar que la UI deja de mostrar el estado de “pendiente de bootstrap” si ya existe histórico real.
7. Documentar el resultado del bootstrap de `#03`, incluyendo cobertura alcanzada si es posible.
8. No tocar la semántica de #01, #02 ni Totales salvo lo estrictamente necesario.
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
- backend/app/historical_snapshots.py
- backend/app/historical_snapshot_storage.py
- backend/app/historical_runner.py
- backend/app/payloads.py
- frontend/assets/js/historico.js
- docs/historical-coverage-report.md

## Expected Files to Modify
- backend/README.md
- backend/app/historical_ingestion.py
- backend/app/historical_snapshots.py
- backend/app/historical_snapshot_storage.py
- opcionalmente docs/historical-coverage-report.md
- y los snapshots generados bajo:
  - backend/data/snapshots/comunidad-hispana-03/

## Constraints
- No usar A2S para esta carga histórica.
- No crear páginas nuevas.
- No romper #01, #02 ni Totales.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en dejar #03 con histórico real y snapshots útiles.

## Validation
- `comunidad-hispana-03` deja de aparecer como pendiente de bootstrap si hay histórico suficiente.
- Existen snapshots JSON no vacíos para `#03` cuando la fuente devuelve datos.
- El histórico bruto de `#03` queda persistido en SQLite.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 6 archivos modificados o creados, sin contar los snapshots generados.
- Preferir menos de 240 líneas cambiadas.
