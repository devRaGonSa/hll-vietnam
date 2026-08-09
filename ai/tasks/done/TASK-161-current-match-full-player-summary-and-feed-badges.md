---
id: TASK-161
title: Current match full player summary and feed badges
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Frontend Senior
  - Experto en interfaz
roadmap_item: foundation
priority: medium
---

# TASK-161 - Current match full player summary and feed badges

## Goal

Ampliar el resumen de jugadores de `/api/current-match/players` para incluir a todos los participantes detectados de la partida actual y ajustar el feed de combate para mostrar nombre + facción en una sola línea sin cambiar su lógica funcional.

## Context

`frontend/partida-actual.html` ya expone feed de combate y tabla de estadísticas en vivo. El payload actual de jugadores depende solo de eventos `kill`, por lo que deja fuera jugadores conectados o vistos en la ventana de partida actual sin bajas registradas.

## Steps

1. Revisar parser, storage y payloads actuales de `current match`.
2. Ampliar la agregación backend usando eventos AdminLog y muestra live cuando exista.
3. Ajustar el render del feed para reutilizar el patrón visual de cápsulas de facción.
4. Validar el alcance con tests y checks pedidos.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `backend/app/rcon_admin_log_storage.py`
- `backend/app/payloads.py`
- `frontend/assets/js/partida-actual.js`

## Expected Files to Modify

- `backend/app/rcon_admin_log_storage.py`
- `backend/app/payloads.py`
- `backend/tests/test_current_match_payload.py`
- `backend/tests/test_rcon_admin_log_storage.py`
- `frontend/assets/js/partida-actual.js`
- `frontend/assets/css/historico.css`

## Constraints

- No tocar histórico, rankings, retención, mantenimiento BDD ni export Gitea.
- No cambiar endpoints ni contratos incompatibles del frontend.
- No cambiar la lógica funcional del feed de combate.
- Mantener la derivación principal de estadísticas desde AdminLog y ampliarla.

## Validation

- `python -m compileall backend/app`
- `$env:PYTHONPATH = "backend"`
- `python -m unittest backend.tests.test_current_match_payload`
- `python -m unittest discover -s backend/tests -p "*current*"`
- `python -m unittest discover -s backend/tests -p "*rcon*"`
- `node --check frontend/assets/js/partida-actual.js`
- `git diff --check`

## Outcome

- `backend/app/rcon_admin_log_storage.py` ahora construye el resumen vivo de participantes de la ventana actual combinando eventos `kill`, `connected`, `disconnected`, `team_switch`, `chat` y `message`, manteniendo las estadísticas de bajas derivadas desde `kill`.
- `frontend/assets/js/partida-actual.js` y `frontend/assets/css/historico.css` ajustan solo el render visual del feed para mostrar nombre + cápsula en la misma línea reutilizando el badge de equipo de la tabla.
- Validación ejecutada:
  - `python -m compileall backend/app`
  - `node --check frontend/assets/js/partida-actual.js`
  - `git diff --check`
  - Arnes Python local que ejecuta directamente las funciones `test_*` de `backend/tests/test_current_match_payload.py` y `backend/tests/test_rcon_admin_log_storage.py`
- Observaciones de validación:
  - `python -m unittest backend.tests.test_current_match_payload` y `python -m unittest discover -s backend/tests -p "*current*"` no detectan tests porque esos módulos usan estilo `pytest`.
  - `python -m unittest discover -s backend/tests -p "*rcon*"` falla por un problema ajeno y preexistente en `test_rcon_materialization_pipeline`.
- Limitación conocida: el helper live actual del repositorio expone conteos y marcador (`GetServerInformation`), pero no un roster nominal de jugadores; por tanto el resumen usa todas las señales nominales ya persistidas en AdminLog y no puede inventar jugadores silenciosos si nunca fueron vistos por ningún evento.

## Change Budget

- Preferir menos de 5 archivos si es viable; si no, mantener el cambio concentrado en current match.
- Preferir cambios pequeños y verificables por tests.
