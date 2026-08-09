# TASK-035-historical-recent-matches-api

## Goal
Exponer una API histórica para consultar partidas recientes por servidor usando el histórico persistido propio del proyecto.

## Context
Tras tener almacenamiento histórico y validación de datos, la siguiente métrica útil además del ranking semanal es la consulta de partidas recientes. Esto permitirá construir después vistas más completas del histórico sin depender de la web externa de la comunidad.

## Steps
1. Revisar el modelo histórico persistido y los datos realmente disponibles por partida.
2. Diseñar un endpoint o conjunto mínimo de endpoints para devolver partidas recientes por servidor.
3. Incluir en el payload, como mínimo:
   - servidor
   - match_id o identificador interno/externo útil
   - fecha/hora
   - mapa
   - resultado o metadato de cierre si está disponible
   - total de jugadores o metadatos útiles si existen
4. Definir orden, límites y paginación básica si encaja con la fase actual.
5. Documentar el endpoint en backend.
6. No crear todavía UI nueva en esta task.
7. Al completar la implementación:
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
- opcionalmente nuevos módulos de query histórica, por ejemplo:
  - backend/app/historical_queries.py
  - backend/app/historical_payloads.py

## Constraints
- No usar A2S para esta API.
- No crear UI en esta task.
- No depender del HTML de la comunidad.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en una API histórica propia y clara.

## Validation
- Existe un endpoint usable de partidas recientes por servidor.
- El payload es claro y reutilizable.
- No se rompe la capa histórica existente.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 5 archivos modificados o creados.
- Preferir menos de 220 líneas cambiadas.
## Outcome
- Se expuso `GET /api/historical/recent-matches`.
- El payload devuelve servidor, `match_id`, cierre temporal, mapa, marcador, ganador y conteo de jugadores.
- La consulta se apoya solo en la persistencia histÃ³rica propia (`historical_*`).
- La documentaciÃ³n del endpoint quedÃ³ actualizada en `backend/README.md`.

## Validation Notes
- `python -m compileall app`
- comprobaciÃ³n local de payload con `build_recent_historical_matches_payload(limit=3, server_slug='comunidad-hispana-01')`
