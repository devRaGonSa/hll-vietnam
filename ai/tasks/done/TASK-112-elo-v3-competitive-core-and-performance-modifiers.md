# TASK-112-elo-v3-competitive-core-and-performance-modifiers

## Goal
Implementar una V3 del motor de rating que combine:
- un Elo persistente competitivo mas parecido a un ranking tipo ajedrez
- con moduladores de rendimiento especificos de HLL
sin romper la persistencia ni la operativa actual.

## Context
Tras la auditoria de `TASK-111`, el sistema debe evolucionar desde el modelo actual hacia una estructura con tres capas:
1. Elo persistente competitivo
2. modificadores de rendimiento HLL
3. limites explicitos entre senal exacta, aproximada y no disponible

## Scope
Backend solamente.

## Steps
1. Auditar el resultado de `TASK-111`.
2. Revisar e implementar ajustes en:
   - `backend/app/elo_mmr_engine.py`
   - `backend/app/elo_mmr_models.py`
   - `backend/app/elo_mmr_storage.py`
3. Introducir un nucleo de Elo competitivo real, con elementos como:
   - baseline inicial por jugador
   - expectativa frente a Elo rival / Elo medio rival
   - delta positivo o negativo segun victoria/empate/derrota
   - sensibilidad a rival mas fuerte o mas debil
4. Mantener moduladores HLL acotados, usando senales disponibles como:
   - impacto
   - KDA
   - kills por minuto
   - soporte
   - disciplina
   - calidad del match
   - confidence
5. Definir limites claros para que los moduladores no destruyan el comportamiento base del Elo competitivo.
6. Si la telemetria lo permite, incorporar logica de presion/oponente o bonus/malus de enfrentamiento.
7. Si la telemetria no permite duelos o death-type fiables, dejar esa parte explicitamente fuera o aproximada, nunca fingida.
8. Mantener metadata suficiente para exponer:
   - que parte del rating fue Elo puro
   - que parte fue performance modifier
   - que parte fue proxy aproximado
9. Mantener compatibilidad razonable con el almacenamiento persistente existente o migrarlo de forma controlada.

## Constraints
- No inventar senales.
- No fingir exclusion exacta de redeploy/self/menu deaths si la telemetria no lo soporta.
- No romper el read-model actual sin plan claro.
- No tocar frontend en esta task.

## Validation
- El motor queda mas parecido a un Elo competitivo real.
- Existen perdidas y ganancias de rating coherentes con rival superior/inferior y resultado.
- Los moduladores HLL quedan acotados y observables.
- La repo queda consistente.

## Expected Files
- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_models.py`
- `backend/app/elo_mmr_storage.py`
- otros archivos backend solo si son estrictamente necesarios

## Outcome
- Se consolido el nucleo Elo competitivo en `backend/app/elo_mmr_engine.py` sobre:
  - `expected_result` frente a MMR medio rival
  - `delta_mmr` con ganancias y perdidas coherentes
  - gating por calidad de match y participacion individual
- El motor ahora persiste metadata adicional para separar:
  - `elo_core_delta`
  - `performance_modifier_delta`
  - `proxy_modifier_delta`
  - `expected_result`
  - `actual_result`
- `backend/app/elo_mmr_storage.py` se amplio para soportar esa V3 sin romper bases SQLite ya existentes:
  - nuevas columnas en `elo_mmr_match_results`
  - migracion controlada via `ALTER TABLE` solo cuando faltan columnas
  - `avg_participation_ratio` persistido en `elo_mmr_monthly_rankings`
- El ranking mensual mantiene visibles en `component_scores`:
  - `elo_core_gain`
  - `performance_modifier_gain`
  - `proxy_modifier_gain`
  - `avg_participation_ratio`
- No se implementaron duelos exactos ni exclusion exacta de redeploy/self/menu deaths; esa frontera se mantiene fuera o aproximada segun `TASK-111`.

## Validation Notes
- `python -m py_compile backend\\app\\elo_mmr_engine.py backend\\app\\elo_mmr_models.py backend\\app\\elo_mmr_storage.py`
- Validacion funcional acotada con muestra real del SQLite historico:
  - carga de filas cerradas desde `backend/data/hll_vietnam_dev.sqlite3`
  - scoring de una muestra real de matches
  - escritura del estado Elo/MMR en un SQLite temporal mediante `replace_elo_mmr_state()`
- El rebuild completo `python -m app.elo_mmr_engine rebuild` supero el timeout local disponible por el tamano del dataset, por lo que no se uso como validacion final de esta task.
- `git diff --name-only`
