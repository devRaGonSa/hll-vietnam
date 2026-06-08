---
id: TASK-163
title: Add player personal stats endpoint
status: done
type: backend
team: Backend Senior
supporting_teams: [Arquitecto de Base de Datos, Arquitecto Python]
roadmap_item: foundation
priority: medium
---

# TASK-163 - Add player personal stats endpoint

## Goal

Implementar únicamente el endpoint backend de estadísticas personales:
`GET /api/stats/players/{player_id}`.

Use existing RCON materialized data for weekly/monthly context.

## Files modified

- `backend/app/rcon_historical_player_stats.py` (nuevo)
- `backend/app/payloads.py`
- `backend/app/routes.py`

## Endpoint created

- `GET /api/stats/players/{player_id}`
  - Parámetros:
    - `server_id` (opcional, alias `server`)
    - `timeframe` (`weekly` | `monthly`, validación en ruta)
  - Respuesta:
    - `status`
    - `data.player_id`
    - `data.player_name`
    - `data.matches_considered`
    - `data.kills`
    - `data.deaths`
    - `data.teamkills`
    - `data.kd_ratio`
    - `data.kills_per_match`
    - `data.deaths_per_match`
    - `data.window_start`
    - `data.window_end`
    - `data.window_kind`
    - `data.weekly_ranking`
    - `data.monthly_ranking`
    - `data.source`

## Validaciones realizadas

- `python -m compileall backend/app`
- `scripts/run-integration-tests.ps1`
- Endpoint manual con backend levantado y `Invoke-WebRequest`:
  - Query corta: `/api/stats/players/a?timeframe=weekly` => `200 OK`
  - Query normal: `/api/stats/players/valid-player-uuid?timeframe=monthly` => `200 OK`
  - Sin resultados: `/api/stats/players/nonexistent-9999?timeframe=weekly` => `200 OK` con métricas en cero
  - Rechazo de timeframe inválido: `/api/stats/players/a?timeframe=yearly` => `400 Bad Request`

## Limitaciones conocidas

- El ranking semanal/mensual incluye solo jugadores con `kills > 0`.
- `source_range` puede ir en `null` cuando no hay datos materializados.
- `player_name` se resuelve al `player_id` si no hay nombre persistido en el rango solicitado.

## Siguiente task recomendada

- Endpoint de vista inicial de estadísticas personales del jugador en frontend (consumo del contrato `GET /api/stats/players/{player_id}`).
