# TASK-109-elo-mmr-pdf-aligned-core-v2

## Goal
Alinear el core del motor Elo/MMR con el diseño del PDF, en una V2 controlada, manteniendo compatibilidad con las señales realmente disponibles y usando proxies honestos cuando sea necesario.

## Context
Una vez auditadas las diferencias entre el diseño formal y la implementación actual, hace falta evolucionar el motor para acercarlo al sistema objetivo:
- Persistent MMR
- DeltaMMR
- MatchScore mensual
- MonthlyRankScore
- Quality factor Q
- elegibilidad mínima por match y por leaderboard
- penalizaciones y disciplina
- weighting por rol
- Strength of Schedule

## Scope
Backend solamente.

## Steps
1. Auditar el resultado de `TASK-108`.
2. Revisar e implementar ajustes en:
   - `backend/app/elo_mmr_engine.py`
   - `backend/app/elo_mmr_models.py`
   - `backend/app/elo_mmr_storage.py`
3. Alinear, como mínimo donde sea viable, estos bloques:
   - `Q`
   - `OutcomeScore`
   - `ImpactScore`
   - `StrengthOfScheduleMatch`
   - `DisciplineIndex`
   - `DeltaMMR`
   - `MatchScore`
   - `MonthlyRankScore`
4. Alinear también:
   - criterios de match válido
   - criterios de elegibilidad para aparecer en rankings
   - baseline / persistent MMR behavior
5. Cuando falten señales exactas, usar proxies explícitos y documentados.
6. Mantener metadata suficiente para saber qué parte del score es exacta y cuál es aproximada.
7. No romper el almacenamiento persistente actual salvo cambios estrictamente necesarios y controlados.

## Constraints
- No inventar señales que no existen.
- No romper la persistencia actual de Elo/MMR sin plan claro.
- No eliminar fallback/compatibilidad con la telemetría actual.
- No tocar frontend en esta task.

## Validation
- El motor queda más alineado con el PDF.
- La elegibilidad y las fórmulas principales reflejan mejor el diseño objetivo.
- Los proxies quedan explícitos y honestos.
- La repo queda consistente.

## Expected Files
- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_models.py`
- `backend/app/elo_mmr_storage.py`
- otros archivos backend solo si son estrictamente necesarios

## Outcome
- Se alineó el core Elo/MMR hacia una V2 más cercana al diseño objetivo sin
  inventar telemetría inexistente.
- Cambios principales implementados en `backend/app/elo_mmr_engine.py`:
  - elegibilidad por match con umbral mínimo de participación por jugador
  - `OutcomeScore` con sensibilidad al margen real del resultado
  - `StrengthOfScheduleMatch` aproximado desde MMR medio rival y calidad de
    partida
  - `DeltaMMR` con patrón más Elo-like basado en expected vs actual result
  - `MatchScore` y `MonthlyRankScore` reponderados con señales y proxies
    explícitos
  - `DisciplineIndex` más honesto al mezclar teamkills exactos con proxy de
    participación para riesgo de leave/AFK
- `backend/app/elo_mmr_models.py` añade constantes explícitas para participación
  mínima y `K-factor`.
- No se cambió el esquema de `backend/app/elo_mmr_storage.py` porque la
  persistencia existente ya soportaba los nuevos metadatos a través de los JSON
  de capabilities y component scores sin romper compatibilidad.

## Validation Notes
- `python -m py_compile backend\\app\\elo_mmr_engine.py backend\\app\\elo_mmr_models.py`
- `git diff --name-only`
