# TASK-054-historical-snapshots-prewarm-and-cache-policy

## Goal
Preparar una política operativa de prewarm y refresco de snapshots históricos para que los servidores y métricas más visibles ya estén listos antes de que el usuario abra la página, reduciendo tiempos de espera al cambiar de servidor o pestaña.

## Context
Aunque la UI deje de precargar agresivamente en el navegador, sigue siendo útil que el backend mantenga calientes y listos los snapshots más importantes. Esto debe hacerse de forma controlada y periódica, sin volver a un modelo de recomposición bajo demanda. Además, conviene definir mejor la política de caché frontend para que ayude sin dejar resultados vacíos obsoletos demasiado tiempo.

## Steps
1. Revisar la generación actual de snapshots y el runner periódico.
2. Definir qué snapshots deben considerarse prioritarios para prewarm, como mínimo:
   - server-summary para #01, #02, #03 y all-servers
   - leaderboard semanal de la métrica por defecto para #01, #02, #03 y all-servers
   - recent-matches para #01, #02, #03 y all-servers
3. Diseñar e implementar una estrategia de prewarm ligera y razonable para esos snapshots prioritarios.
4. Mantener la generación de otras métricas de leaderboard de forma periódica o diferida, según convenga, pero sin penalizar la primera carga de la UI.
5. Revisar y ajustar la política de caché frontend para:
   - aprovechar respuestas recientes
   - no mantener indefinidamente respuestas vacías antiguas
   - permitir que el usuario vea mejoras sin necesidad de comportamientos raros
6. Documentar la estrategia operativa de prewarm y caché.
7. No convertir esta task en una optimización prematura excesiva; mantener el alcance claro y pragmático.
8. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- backend/README.md
- backend/app/config.py
- backend/app/historical_runner.py
- backend/app/historical_snapshots.py
- backend/app/historical_snapshot_storage.py
- frontend/assets/js/historico.js
- docs/historical-coverage-report.md

## Expected Files to Modify
- backend/app/config.py
- backend/app/historical_runner.py
- backend/app/historical_snapshots.py
- frontend/assets/js/historico.js
- backend/README.md
- opcionalmente documentación técnica adicional si ayuda a dejar la política operativa clara

## Constraints
- No volver a recomposición pesada en request path.
- No crear páginas nuevas.
- No romper la UI histórica existente.
- No introducir frameworks nuevos.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en snapshots listos antes de la interacción del usuario.

## Validation
- Existe una estrategia clara de prewarm de snapshots prioritarios.
- Cambiar de servidor o entrar en la página es más rápido que antes.
- La política de caché frontend es más sana y coherente con el uso real.
- La documentación refleja la nueva operativa.
- Los cambios quedan committeados y se hace push si el entorno lo permite.

## Change Budget
- Preferir menos de 5 archivos modificados o creados.
- Preferir menos de 220 líneas cambiadas.

## Outcome
- El runner histórico ya no duplica una recomposición completa de snapshots tras cada refresh incremental.
- La operativa periódica hace prewarm en cada ciclo para `server-summary`, `weekly-leaderboard` de `kills` y `recent-matches` en `comunidad-hispana-01`, `comunidad-hispana-02`, `comunidad-hispana-03` y `all-servers`.
- La matriz completa de métricas queda en una cadencia separada configurable con `HLL_HISTORICAL_FULL_SNAPSHOT_EVERY_RUNS`, evitando penalizar cada refresh.
- La caché frontend ahora distingue snapshots frescos, stale y missing para conservar respuestas útiles más tiempo sin retener vacíos antiguos indefinidamente.
- Validación local:
- `py_compile` sobre `config.py`, `historical_snapshots.py`, `historical_ingestion.py`, `historical_runner.py` y `payloads.py`
- `node --check frontend/assets/js/historico.js`
- validación funcional con SQLite temporal: `priority-prewarm -> 12 snapshots` y `full-matrix -> 6 snapshots` para un servidor
- la generación contra el dataset histórico real superó el timeout local de la consola, por lo que la validación operativa completa quedó acotada a la ruta temporal
