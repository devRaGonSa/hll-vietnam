# TASK-108-elo-mmr-pdf-gap-analysis

## Goal
Auditar en detalle la diferencia entre la implementación Elo/MMR actual de la repo y el diseño formal del sistema descrito en el PDF, dejando un mapa claro de convergencias, divergencias, proxies actuales y señales ausentes.

## Context
La repo ya tiene:
- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_models.py`
- `backend/app/elo_mmr_storage.py`
- payloads y exposición mínima de Elo/MMR
Además, existe un diseño formal en PDF para:
- Persistent MMR
- MatchScore mensual
- MonthlyRankScore
- Quality factor Q
- OutcomeScore / ImpactScore
- Strength of Schedule
- role weighting
- discipline / penalties
- criterios de elegibilidad

Hoy la implementación parece funcional, pero no necesariamente alineada al 100% con ese diseño.

## Scope
Auditoría y documentación técnica. Sin cambios de frontend.

## Steps
1. Auditar:
   - `backend/app/elo_mmr_engine.py`
   - `backend/app/elo_mmr_models.py`
   - `backend/app/elo_mmr_storage.py`
   - `backend/app/payloads.py`
   - `docs/elo-mmr-monthly-ranking-design.md`
   - el PDF del sistema Elo/MMR mensual
2. Construir una matriz comparativa entre:
   - diseño del PDF
   - implementación actual
3. Clasificar cada componente del diseño como:
   - implemented_exact
   - implemented_approximate
   - partially_implemented
   - not_implemented
4. Identificar de forma explícita:
   - fórmulas coincidentes
   - fórmulas divergentes
   - thresholds de elegibilidad
   - señales reales disponibles
   - señales que hoy solo existen como proxy
   - señales todavía no disponibles en la repo
5. Proponer una secuencia razonable de alineación V2 del motor sin romper compatibilidad operativa.
6. Dejar recomendaciones explícitas sobre qué partes pueden alinearse ya y cuáles dependen de telemetría futura.

## Constraints
- No reescribir el motor en esta task.
- No vender como exacto lo que hoy es proxy.
- No tocar frontend.
- No cerrar huecos de telemetría de forma ficticia.

## Validation
- Existe un documento/auditoría clara de gap analysis entre PDF y código real.
- Cada componente importante del sistema queda clasificado.
- Queda clara una secuencia viable para la implementación posterior.

## Expected Files
- `docs/elo-mmr-monthly-ranking-design.md` o documento técnico adicional si hace falta
- referencias a `backend/app/elo_mmr_engine.py`, `backend/app/elo_mmr_models.py`, `backend/app/elo_mmr_storage.py`

## Outcome
- Se amplió `docs/elo-mmr-monthly-ranking-design.md` con una sección explícita
  de `PDF Gap Analysis`.
- La auditoría deja documentado que el PDF original no está presente en el
  workspace y que la comparativa se apoya en los artefactos del repositorio que
  ya resumían ese diseño.
- Quedó construida una matriz por componente con clasificación:
  - `implemented_exact`
  - `implemented_approximate`
  - `partially_implemented`
  - `not_implemented`
- También quedaron documentados:
  - inventario de señales reales actuales
  - proxies actuales
  - señales ausentes
  - secuencia razonable de alineación V2 sin inventar telemetría

## Validation Notes
- Revisión manual de:
  - `docs/elo-mmr-monthly-ranking-design.md`
  - `backend/app/elo_mmr_engine.py`
  - `backend/app/elo_mmr_models.py`
  - `backend/app/elo_mmr_storage.py`
  - `backend/app/payloads.py`
  - `backend/README.md`
- `git diff --name-only`
