# TASK-113-elo-v3-accuracy-contract-and-surface

## Goal
Alinear la superficie de producto y los payloads del Elo/MMR V3 para explicar de forma clara:
- rating persistente
- score mensual
- Elo puro vs modificadores HLL
- exact / approximate / blocked-by-telemetry

## Context
Una vez exista el motor V3, la UI y los payloads deben dejar claro que representa cada numero y con que grado de fiabilidad se calcula.

## Scope
Backend principalmente. Frontend solo si hiciera falta exposicion minima muy localizada.

## Steps
1. Auditar:
   - `backend/app/payloads.py`
   - `backend/app/routes.py`
   - `frontend/assets/js/historico.js`
   - `frontend/historico.html`
2. Revisar como se exponen hoy:
   - `monthly_rank_score`
   - `persistent_rating.mmr`
   - `mmr_gain`
   - `valid_matches`
   - `confidence`
   - `accuracy_mode`
   - `capabilities`
3. Hacer que el payload explique mejor:
   - que parte es Elo competitivo base
   - que parte es ajuste por rendimiento HLL
   - que partes son aproximadas
   - que partes no pueden calcularse todavia
4. Ajustar el contrato de exactitud/capabilities del bloque Elo/MMR.
5. Mantener la salida usable para frontend sin sobrecargarla innecesariamente.
6. Actualizar documentacion/runbook si hace falta.

## Constraints
- No afirmar exactitud falsa.
- No rehacer visualmente toda la pagina.
- No romper endpoints existentes.
- Mantener claridad de producto.

## Validation
- Payloads y/o UI dejan mas claro que representa Elo/MMR.
- La metadata de exactitud queda alineada con el motor real.
- La repo queda consistente.

## Expected Files
- `backend/app/payloads.py`
- `backend/app/routes.py` si hace falta
- `frontend/assets/js/historico.js` y/o `frontend/historico.html` solo si es necesario
- `backend/README.md`

## Outcome
- `backend/app/payloads.py` mantiene los endpoints actuales y aade una capa explicativa aditiva:
  - `model_contract` en el payload de leaderboard y de perfil
  - `rating_breakdown` por item/perfil
  - `blocked_components` dentro de `accuracy_contract`
- Ese contrato separa mejor:
  - rating persistente competitivo
  - `monthly_rank_score`
  - `elo_core_gain`
  - `performance_modifier_gain`
  - `proxy_modifier_gain`
- `frontend/assets/js/historico.js` se ajusto de forma localizada para reutilizar esa metadata:
  - la nota del bloque Elo/MMR ya menciona componentes bloqueados por telemetria
  - el resumen por jugador ya distingue Elo core, modificadores HLL y tramo proxy
- `backend/README.md` se actualizo para dejar visible el nuevo contrato aditivo sin cambiar endpoints.
- No hizo falta tocar `routes.py` ni rehacer la UI.

## Validation Notes
- `python -m py_compile backend\\app\\payloads.py`
- Validacion de lectura del payload real:
  - `build_elo_mmr_leaderboard_payload(limit=1, server_id='all-servers')`
  - comprobado que el resultado incluye:
    - `accuracy_contract`
    - `model_contract`
    - `rating_breakdown` en items
- `git diff --name-only`
