# TASK-038-historical-player-profile-api-foundation

## Goal
Crear la base de API para perfiles históricos de jugador dentro del proyecto, apoyándose en el histórico propio ya persistido y preparando futuras vistas de detalle sin depender de páginas externas.

## Context
Una vez resueltos rankings y partidas, el siguiente paso natural del histórico es poder profundizar por jugador. Esta task no debe construir todavía la UI completa de perfil, pero sí dejar lista una base de consulta que permita en fases posteriores mostrar el recorrido histórico de un jugador en los servidores de la comunidad.

## Steps
1. Revisar la estructura actual de identidad de jugador validada en la task de calidad histórica.
2. Diseñar una base de endpoint o endpoints para consultar un jugador histórico.
3. Incluir, como mínimo, datos como:
   - identidad de jugador
   - servidor o servidores donde aparece
   - kills agregadas
   - número de partidas
   - rango temporal cubierto
4. Implementar la consulta de forma consistente con la estructura histórica existente.
5. Documentar el endpoint en backend.
6. No crear todavía UI final de perfil.
7. Al completar la implementación:
   - dejar el repositorio consistente
   - hacer commit
   - hacer push al remoto si el entorno lo permite

## Files to Read First
- AGENTS.md
- backend/README.md
- backend/app/historical_storage.py
- backend/app/historical_models.py
- backend/app/routes.py
- backend/app/payloads.py
- docs/historical-data-quality-notes.md

## Expected Files to Modify
- backend/app/routes.py
- backend/app/payloads.py
- backend/README.md
- opcionalmente nuevos módulos de query histórica por jugador

## Constraints
- No usar páginas externas como perfil del producto.
- No crear UI final de perfil todavía.
- No romper endpoints históricos existentes.
- No hacer cambios destructivos.
- Mantener el trabajo centrado en la base de API de perfil.

## Validation
- Existe una base de endpoint para perfil histórico de jugador.
- El endpoint se apoya en la persistencia histórica propia.
- La identidad de jugador usada es consistente con la corrección de calidad ya realizada.
- Los cambios quedan committeados y se hace push al remoto si el entorno lo permite.

## Change Budget
- Preferir menos de 5 archivos modificados o creados.
- Preferir menos de 220 líneas cambiadas.
## Outcome
- Se expuso `GET /api/historical/player-profile?player=...`.
- El endpoint acepta `stable_player_key`, `steam_id` o `source_player_id`.
- La respuesta devuelve identidad de jugador, kills agregadas, nÃºmero de partidas, rango temporal y desglose por servidores.
- No se construyÃ³ UI final de perfil en esta task.

## Validation Notes
- `python -m compileall app`
- comprobaciÃ³n local de payload reutilizando un `stable_player_key` real del ranking semanal
