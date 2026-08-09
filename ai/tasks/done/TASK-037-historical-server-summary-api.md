# TASK-037-historical-server-summary-api

## Goal
Exponer una API de resumen histórico por servidor que sirva como base para futuros bloques de overview y comparativas.

## Context
Además de rankings y partidas recientes, el proyecto necesitará una capa resumida de datos por servidor para poder mostrar actividad agregada y métricas de alto nivel sin recalcularlas en el frontend.

## Steps
1. Revisar el histórico persistido y las métricas disponibles de forma fiable.
2. Diseñar un endpoint de resumen por servidor con métricas agregadas útiles. Incluir, si es viable:
   - número de partidas históricas
   - número de jugadores únicos
   - kills agregadas
   - mapas más jugados o conteo de mapas
   - rango temporal cubierto
3. Implementar el endpoint de forma clara y reutilizable.
4. Documentar el endpoint en backend.
5. No crear UI nueva en esta task.
6. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- backend/README.md
- backend/app/routes.py
- backend/app/payloads.py
- backend/app/historical_storage.py
- backend/app/historical_models.py
- docs/historical-domain-model.md

## Expected Files to Modify
- backend/app/routes.py
- backend/app/payloads.py
- backend/README.md
- opcionalmente nuevos módulos de query histórica

## Constraints
- No usar A2S para resumen histórico.
- No crear UI en esta task.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en una API agregada estable.

## Validation
- Existe un endpoint de resumen histórico por servidor.
- El payload es claro y reutilizable.
- El endpoint se basa en el histórico propio persistido.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 5 archivos modificados o creados.
- Preferir menos de 220 líneas cambiadas.
## Outcome
- Se expuso `GET /api/historical/server-summary`.
- El endpoint agrega partidas histÃ³ricas, jugadores Ãºnicos, kills, conteo de mapas, mapas dominantes y rango temporal cubierto.
- La consulta se resuelve desde la persistencia histÃ³rica propia y queda documentada en `backend/README.md`.

## Validation Notes
- `python -m compileall app`
- comprobaciÃ³n local de payload con `build_historical_server_summary_payload(server_slug='comunidad-hispana-01')`
