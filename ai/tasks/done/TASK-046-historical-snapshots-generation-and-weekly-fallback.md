# TASK-046-historical-snapshots-generation-and-weekly-fallback

## Goal
Completar la capa operativa de snapshots históricos para que la página histórica deje de mostrar estados vacíos cuando ya existe histórico bruto persistido, y añadir una regla de fallback semanal que use la semana cerrada anterior cuando la semana actual todavía no tenga muestra suficiente, especialmente a principio de semana.

## Context
La página histórica ya consume endpoints de snapshots precalculados, pero en el estado actual del proyecto esos snapshots no están generados o no se están persistiendo de forma efectiva para el servidor activo. Como resultado, la UI muestra mensajes como “Sin snapshot de resumen” o “Sin datos históricos suficientes” aunque el bootstrap histórico ya haya cargado datos crudos en SQLite.

Además, la experiencia esperada para los rankings semanales requiere una regla adicional: si la semana actual aún no tiene muestra suficiente —por ejemplo, en lunes o muy al inicio de la semana— debe mostrarse temporalmente la semana cerrada anterior hasta que la actual tenga datos suficientes.

## Steps
1. Revisar la implementación actual de:
   - histórico bruto persistido
   - capa de snapshots
   - API de snapshots
   - UI histórica que consume snapshots
2. Identificar por qué, tras el bootstrap histórico, no se están generando o persistiendo snapshots disponibles para la UI.
3. Completar o corregir el flujo de generación de snapshots para:
   - resumen de servidor
   - weekly leaderboard
   - recent matches
4. Asegurar que exista una forma clara de generar snapshots después del bootstrap y de refrescarlos periódicamente.
5. Validar que, una vez existe histórico bruto suficiente, la UI deje de mostrar mensajes de “sin snapshot” para el servidor activo.
6. Implementar en backend una regla de selección de leaderboard semanal con fallback:
   - si la semana actual no tiene muestra suficiente
   - y estamos en los primeros días de la semana o en una condición equivalente definida por el proyecto
   - devolver la semana cerrada anterior como snapshot activo
7. Definir y documentar claramente qué significa “muestra suficiente” para este fallback semanal.
8. Hacer que el payload del snapshot semanal exponga de forma clara:
   - el rango temporal real usado
   - si el snapshot pertenece a la semana actual o a la semana cerrada anterior
   - cualquier metadato útil para que la UI no engañe al usuario
9. Ajustar la UI solo en lo mínimo necesario para reflejar correctamente el rango real que se está mostrando.
10. Mantener intacta la separación entre:
   - histórico bruto
   - snapshots precalculados
   - live status A2S
11. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- backend/README.md
- backend/app/config.py
- backend/app/historical_storage.py
- backend/app/historical_models.py
- backend/app/historical_runner.py
- backend/app/historical_snapshots.py
- backend/app/historical_snapshot_storage.py
- backend/app/payloads.py
- backend/app/routes.py
- frontend/historico.html
- frontend/assets/js/historico.js
- frontend/assets/css/historico.css

## Expected Files to Modify
- backend/README.md
- backend/app/config.py
- backend/app/historical_runner.py
- backend/app/historical_snapshots.py
- backend/app/historical_snapshot_storage.py
- backend/app/payloads.py
- backend/app/routes.py
- opcionalmente frontend/assets/js/historico.js si hace falta reflejar el rango semanal real usado
- opcionalmente documentación técnica adicional

## Constraints
- No usar A2S para esta lógica histórica.
- No volver a queries pesadas on-demand como solución principal.
- No crear páginas nuevas.
- No romper la UI histórica existente.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en generación real de snapshots y fallback semanal coherente.

## Validation
- La página histórica deja de mostrar “sin snapshot” cuando ya existe histórico bruto suficiente.
- Se generan snapshots de resumen, leaderboard semanal y partidas recientes.
- El leaderboard semanal puede usar la semana anterior cuando la actual aún no tiene muestra suficiente.
- El payload expone claramente el rango temporal real mostrado.
- La UI deja claro qué semana está viendo el usuario.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 7 archivos modificados o creados.
- Preferir menos de 260 líneas cambiadas.

## Outcome
- La generacion de snapshots historicos deja de depender solo del runner periodico: `bootstrap` y `refresh` regeneran y persisten snapshots al terminar correctamente.
- Se consolidaron snapshots reales para `server-summary`, `weekly-leaderboard` y `recent-matches`.
- El ranking semanal paso de una ventana movil de 7 dias a una semana calendario UTC con fallback explicito a la semana cerrada anterior.
- Se definio "muestra suficiente" como minimo `3` partidas cerradas en la semana actual; el fallback puede aplicarse entre lunes y miercoles UTC si esa muestra aun no existe.
- El payload semanal ahora expone `window_start`, `window_end`, `window_kind`, `window_label`, `uses_fallback`, `selection_reason`, `current_week_closed_matches`, `previous_week_closed_matches` y `sufficient_sample`.
- La UI historica ajusta el texto de la ventana semanal para reflejar el rango real mostrado y avisar cuando se esta viendo temporalmente la semana cerrada anterior.
- Se supero ligeramente el presupuesto orientativo de lineas por mantener la logica de seleccion semanal y la documentacion operativa en un mismo cambio acotado.

## Validation Notes
- `python -m py_compile backend/app/config.py backend/app/historical_storage.py backend/app/historical_snapshots.py backend/app/historical_runner.py backend/app/historical_ingestion.py backend/app/payloads.py`
- `generate_and_persist_historical_snapshots(server_key='comunidad-hispana-01')` persistio `6` snapshots para el servidor activo.
- Los builders de payload devolvieron `found: True` para `server-summary`, `weekly-leaderboard` y `recent-matches` en `comunidad-hispana-01`.
- Con la base SQLite local actual, el snapshot semanal activo devuelve `window_kind: previous-closed-week-fallback`, `uses_fallback: True`, `current_week_closed_matches: 0` y `previous_week_closed_matches: 44`, lo que valida el fallback real a fecha `2026-03-23`.
- Se valido el nuevo encadenado de ingesta -> regeneracion de snapshots con una ejecucion local stubbeada de `run_incremental_refresh(...)` sin depender de red; el resultado incluyo `snapshot_result.snapshot_count = 6`.
- `git diff --name-only` confirma que solo cambiaron archivos del backend historico, la documentacion backend y el JS minimo de la pagina historica.
