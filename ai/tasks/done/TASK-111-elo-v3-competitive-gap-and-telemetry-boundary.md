# TASK-111-elo-v3-competitive-gap-and-telemetry-boundary

## Goal
Auditar el sistema Elo/MMR actual frente al objetivo de un Elo competitivo real con moduladores de rendimiento HLL, dejando clara la frontera entre:
- lo que ya existe
- lo que puede implementarse ya
- lo que solo puede hacerse con proxies
- lo que no puede implementarse todavia por falta de telemetria

## Context
La repo ya dispone de:
- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_models.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/payloads.py`
- pipeline de historico y eventos V2
- exposicion de Elo/MMR en `historico.html`

Pero el objetivo nuevo es mas ambicioso:
- rating persistente mas parecido a Elo ajedrez/ranking competitivo
- expectativa frente a Elo rival
- ganancias y perdidas mas sensibles a rival mas fuerte o mas debil
- derrotas que puedan bajar Elo
- mantenimiento de senales de rendimiento HLL
- exclusion de redeploy/self/menu deaths solo si la telemetria real lo permite

## Scope
Auditoria tecnica y de telemetria. Sin cambios funcionales.

## Steps
1. Auditar:
   - `backend/app/elo_mmr_engine.py`
   - `backend/app/elo_mmr_models.py`
   - `backend/app/elo_mmr_storage.py`
   - `backend/app/payloads.py`
   - `backend/app/player_event_worker.py`
   - `backend/app/player_event_source.py`
   - cualquier storage o read-model relacionado con eventos y rankings
2. Documentar con precision:
   - como se calcula hoy el Elo/MMR
   - que parte se parece a un Elo real y que parte no
   - que senales reales existen hoy para kills, deaths, discipline, support, combat, offense, defense, time played, match quality y confidence
3. Evaluar especificamente si la repo puede distinguir hoy de forma fiable:
   - redeploy deaths
   - suicidios propios
   - deaths por menu/self-inflicted no competitivas
4. Clasificar cada requisito del objetivo nuevo como:
   - implementable_now_exact
   - implementable_now_approximate
   - blocked_by_missing_telemetry
5. Proponer una arquitectura V3 razonable para:
   - Elo persistente competitivo
   - performance modifiers HLL
   - optional duel/opponent-pressure logic
6. Dejar explicito que parte del requisito de excluir redeploy/self/menu deaths puede o no puede resolverse hoy.
7. Dejar secuencia de implementacion por fases sin romper compatibilidad operativa.

## Constraints
- No implementar nada en esta task.
- No fingir telemetria inexistente.
- No vender como exacto lo que hoy no lo es.
- No tocar frontend.

## Validation
- Existe una auditoria clara del gap entre sistema actual y Elo V3 objetivo.
- Queda clara la frontera de telemetria real.
- Queda clara la secuencia de implementacion posterior.

## Expected Files
- documento tecnico o actualizacion de documentacion relacionada
- referencias explicitas a `backend/app/elo_mmr_engine.py`, `backend/app/player_event_worker.py`, `backend/app/player_event_source.py`

## Outcome
- Se anadio `docs/elo-v3-competitive-gap-and-telemetry-boundary.md` como auditoria especifica del gap entre el Elo/MMR actual y una V3 competitiva honesta.
- La auditoria deja explicito que la repo ya dispone de un nucleo Elo-like persistente en `backend/app/elo_mmr_engine.py`, pero que sigue dependiendo de proxies para:
  - `ObjectiveIndex`
  - `DisciplineIndex`
  - `role_bucket`
  - `StrengthOfScheduleMatch`
- Tambien clasifica cada requisito V3 como:
  - `implementable_now_exact`
  - `implementable_now_approximate`
  - `blocked_by_missing_telemetry`
- Quedo documentada la frontera critica sobre redeploy/self/menu deaths:
  - la repo no puede distinguirlas hoy de forma fiable
  - no deben venderse como exclusiones exactas
- La secuencia de implementacion posterior quedo dividida en:
  - Elo core competitivo
  - moduladores HLL acotados
  - contrato de exactitud/capabilities
  - capa opcional de duel/opponent pressure solo aproximada

## Validation Notes
- Revision manual de:
  - `backend/app/elo_mmr_engine.py`
  - `backend/app/elo_mmr_models.py`
  - `backend/app/elo_mmr_storage.py`
  - `backend/app/payloads.py`
  - `backend/app/player_event_worker.py`
  - `backend/app/player_event_source.py`
  - `backend/app/providers/player_event_source_provider.py`
  - `backend/app/rcon_historical_read_model.py`
  - `docs/elo-v3-competitive-gap-and-telemetry-boundary.md`
- `git diff --name-only`
