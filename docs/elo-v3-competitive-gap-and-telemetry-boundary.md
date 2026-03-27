# Elo V3 Competitive Gap And Telemetry Boundary

## Validation Date

- 2026-03-26

## Scope

Auditoria tecnica del estado real del Elo/MMR competitivo en la repo,
centrada en:

- que hace hoy `backend/app/elo_mmr_engine.py`
- que persistencia y payloads sostienen ese calculo
- que telemetria real existe para HLL competitivo
- que parte del objetivo V3 puede implementarse ya
- que parte solo puede aproximarse con proxies honestos
- que parte sigue bloqueada por falta de telemetria

Sin cambios funcionales. Sin frontend.

Important naming boundary after the latest practical alignment work:

- implemented branch model:
  - `elo-pdf-v3-practical`
- deferred evolution:
  - telemetry-complete `v3`

This repo can keep evolving contracts and formulas without claiming that the
implemented telemetry model is already `v3`.

## Evidence Reviewed

- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_models.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/payloads.py`
- `backend/app/player_event_worker.py`
- `backend/app/player_event_source.py`
- `backend/app/providers/player_event_source_provider.py`
- `backend/app/rcon_historical_read_model.py`
- `backend/app/historical_storage.py`
- `docs/elo-mmr-monthly-ranking-design.md`
- `docs/crcon-advanced-metrics-origin-audit.md`
- `docs/rcon-data-capability-audit.md`
- `backend/README.md`

## Current Repository Boundary

La repo ya no esta en un Elo "flat" puramente lineal. El estado actual ya
mezcla tres capas:

1. rating persistente por jugador y scope en `elo_mmr_player_ratings`
2. scoring por match en `elo_mmr_match_results`
3. ranking mensual separado en `elo_mmr_monthly_rankings`

La persistencia de esa frontera esta en `backend/app/elo_mmr_storage.py`.

El motor actual en `backend/app/elo_mmr_engine.py` ya introduce elementos de un
Elo competitivo V3:

- baseline inicial `DEFAULT_BASE_MMR`
- expectativa contra rating medio rival con formula tipo Elo
- deltas positivos y negativos
- sensibilidad a rival mas fuerte o mas debil via `expected_result`
- `quality_factor` para acotar peso competitivo del match
- gating por validez de match y por participacion individual

Pero sigue siendo un sistema hibrido, no un Elo competitivo puro:

- el resultado real no sale solo de win/draw/loss
- `actual_result` depende de `OutcomeScore`, `ImpactScore`,
  `StrengthOfScheduleMatch` y participacion
- `ImpactScore`, `ObjectiveIndex`, `role_bucket` y parte de disciplina siguen
  apoyandose en proxies de scoreboard

Conclusion practica:

- hoy ya existe un nucleo Elo-like usable
- no existe todavia una paridad exacta con un ranking competitivo ideal basado
  en telemetria tactica o eventos raw de HLL
- la implementacion actual debe describirse como alineacion practica PDF
  `v3`, no como culminacion telemetry-complete de `v3`

## How Elo/MMR Works Today

`backend/app/elo_mmr_engine.py` calcula hoy, por jugador y por match:

- validez global del match:
  - duracion minima `900` segundos
  - al menos `20` filas de jugador persistidas
- elegibilidad individual del jugador:
  - al menos `600` segundos jugados
  - al menos `35%` de participacion sobre la duracion del match
- `OutcomeScore`:
  - exacto desde `team_side`, `allied_score` y `axis_score`
- `CombatIndex`:
  - exacto usando `kills`, `deaths`, `combat`
- `UtilityIndex`:
  - exacto usando `support`
- `ObjectiveIndex`:
  - aproximado con `offense + defense`
- `DisciplineIndex`:
  - aproximado, mezcla `teamkills` exactos con proxy de participacion
- `role_bucket`:
  - aproximado, inferido desde el eje dominante de scoreboard
- `StrengthOfScheduleMatch`:
  - aproximado, usa media de MMR rival y `quality_factor`
- `delta_mmr`:
  - tipo Elo, con `K = 28`, `expected_result` y `actual_result`
- `monthly_rank_score`:
  - capa separada del rating persistente para la superficie mensual

`backend/app/payloads.py` ya expone esta frontera con:

- `accuracy_mode`
- `capabilities`
- `accuracy_contract`

## Real Telemetry Available Today

Senales reales ya persistidas y reutilizables para Elo competitivo:

- resultado final del match
- lado del jugador (`team_side`)
- `kills`
- `deaths`
- `teamkills`
- `combat`
- `offense`
- `defense`
- `support`
- `time_seconds`
- timestamps de inicio y cierre del match
- identidad persistente del jugador
- duracion canonica resuelta por match
- bucket de duracion por match
- bucket de participacion por jugador y match
- ritmos por minuto derivados del scoreboard ya persistido

Senales reales parciales adicionales fuera del nucleo Elo:

- `most_killed`
- `death_by`
- `weapons`
- `death_by_weapons`
- teamkills agregados por match

Pero esa capa viene del detalle CRCON resumido y del pipeline V2 de
`backend/app/player_event_worker.py` y
`backend/app/providers/player_event_source_provider.py`, no de un feed raw por
evento. Su frontera real es:

- resumen por match
- timestamp del match, no timestamp exacto de cada kill
- contadores agregados, no ledger raw por encounter

## Telemetry That Is Approximate Or Proxy Today

Estas piezas ya pueden participar en V3, pero solo como aproximacion honesta:

- rol del jugador
  - proxy por eje dominante `combat/offense/defense/support`
- objetivo/tactica
  - proxy por `offense + defense`
- fuerza del rival
  - proxy por MMR medio rival y calidad del match
- disciplina mas alla de teamkills
  - proxy por participacion y abandono implicito
- pressure / duel logic
  - solo aproximable desde `most_killed` y `death_by` agregados

## Telemetry Missing Today

La repo no persiste hoy telemetria suficiente para afirmar exactitud en:

- clase o rol real del jugador
- liderazgo real de commander / squad lead
- eventos tacticos finos de objetivo
- feed raw kill -> victim por instante exacto
- tipo exacto de muerte competitivo frente a no competitivo
- AFK, disconnect o abandono explicito
- grafo completo de presion rival por roster

## Redeploy, Suicide And Menu-Death Boundary

La pregunta critica de esta task es si la repo puede excluir hoy, de forma
fiable, muertes no competitivas como:

- redeploy deaths
- suicidios propios
- muertes por menu / self-inflicted no competitivas

Conclusion corta: no, no puede hacerlo de forma fiable hoy.

Motivo por capa:

- `backend/app/elo_mmr_engine.py` solo ve `deaths` agregadas por jugador y
  match; no ve tipo de muerte
- `backend/app/player_event_source.py` con fallback a
  `PublicScoreboardPlayerEventSource` no recibe un feed raw por kill
- `backend/app/providers/player_event_source_provider.py` normaliza
  `most_killed`, `death_by`, `weapons`, `death_by_weapons` y `teamkills`, pero
  no distingue death reasons como redeploy, menu o self-kill no competitivo
- `backend/app/rcon_historical_read_model.py` declara `player_stats:
  unavailable` para la capa competitiva RCON actual

Clasificacion especifica:

| Requirement | Current status | Why |
| --- | --- | --- |
| Distinguir redeploy deaths | `blocked_by_missing_telemetry` | No existe death-reason raw ni evento especifico persistido |
| Distinguir suicidio propio exacto | `blocked_by_missing_telemetry` | No hay causa exacta de muerte ni source raw por evento |
| Distinguir menu / self-inflicted no competitiva | `blocked_by_missing_telemetry` | La repo no ve death types ni razon de cierre/respawn |
| Penalizar muertes con heuristica general | `implementable_now_approximate` | Solo via `deaths` agregadas o participacion, nunca exclusiones exactas |

La regla correcta para V3 es:

- no excluir esas muertes como si la repo las identificara exactamente
- como maximo, dejar esa frontera marcada como no disponible o aproximada

## Requirement Classification

| Requisito V3 objetivo | Clasificacion | Base actual |
| --- | --- | --- |
| Rating persistente por jugador | `implementable_now_exact` | Ya existe en `elo_mmr_player_ratings` |
| Baseline inicial de rating | `implementable_now_exact` | `DEFAULT_BASE_MMR` ya operativo |
| Expectativa frente a Elo rival | `implementable_now_exact` | `expected_result` ya usa media MMR rival |
| Ganancias y perdidas segun rival fuerte/debil | `implementable_now_exact` | `delta_mmr` ya depende de `expected_result` |
| Derrotas que bajen Elo | `implementable_now_exact` | Ya ocurre cuando `actual_result < expected_result` |
| Match validity y calidad competitiva | `implementable_now_exact` | Con datos ya persistidos, aunque `quality_factor` simplifica |
| Participacion minima por jugador | `implementable_now_exact` | Ya operativa con `time_seconds` y ratio |
| Combat performance | `implementable_now_exact` | `kills`, `deaths`, `combat` existen |
| Utility / support performance | `implementable_now_exact` | `support` existe |
| Objective performance HLL | `implementable_now_approximate` | Solo via `offense + defense` |
| Discipline HLL | `implementable_now_approximate` | `teamkills` exactos, leave/AFK no |
| Strength of schedule avanzada | `implementable_now_approximate` | Sin grafo completo de roster |
| Duel / opponent pressure logic | `implementable_now_approximate` | Solo desde summaries `most_killed` / `death_by` |
| Confidence por cobertura y calidad | `implementable_now_exact` | Puede basarse en match count, playtime y accuracy ratios |
| Excluir redeploy/self/menu deaths exactos | `blocked_by_missing_telemetry` | No hay death-type persistido |
| Leadership index exacto | `blocked_by_missing_telemetry` | No hay rol/liderazgo persistido |
| Tactical event weighting exacta | `blocked_by_missing_telemetry` | No hay event stream tactico |

## Reasonable V3 Architecture

Una V3 razonable y honesta en esta repo deberia separar:

### 1. Competitive Elo Core

Responsabilidad:

- mantener rating persistente
- calcular expectativa rival
- mover rating por resultado competitivo
- limitar el impacto por `quality_factor` y elegibilidad

Inputs defendibles hoy:

- `mmr_before`
- `team_outcome`
- marcador final
- rating medio rival
- calidad del match
- participacion individual

### 2. HLL Performance Modifiers

Responsabilidad:

- modular el `actual_result` o un `performance_modifier`
- no reescribir por completo el comportamiento base Elo

Inputs defendibles hoy:

- `CombatIndex`
- `UtilityIndex`
- `ObjectiveIndex` aproximado
- `DisciplineIndex` aproximado
- `StrengthOfScheduleMatch` aproximado

Regla de seguridad:

- los moduladores deben ser acotados
- Elo base debe seguir explicando la mayor parte del movimiento

### 3. Accuracy And Capability Contract

Responsabilidad:

- explicar exact / approximate / blocked
- impedir que producto o frontend vendan exactitud falsa

Superficie minima:

- `accuracy_mode`
- ratios exact / approximate / not_available
- estado por componente

### 3.5. Practical V1-V2 Foundation Already Materialized

La repo ya materializa una base mas cercana a `player_match_fact` sin inventar
telemetria nueva:

- `elo_mmr_canonical_matches`
  - duracion resuelta
  - bucket de duracion
  - player count
- `elo_mmr_canonical_player_match_facts`
  - `participation_ratio`
  - `participation_bucket`
  - `participation_quality_score`
  - `objective_score_proxy`
  - tasas por minuto derivadas de stats reales ya persistidas
- `elo_mmr_match_results`
  - arrastra esa linea de fact lineage hacia el rating por match
- `elo_mmr_monthly_rankings`
  - persiste inputs mensuales mas explicitos para actividad, calidad y
    consistencia

### 4. Optional Duel Layer

Responsabilidad:

- bonus o malus pequeno por presion rival
- nunca convertirse en dependencia dura del rating

Estado actual:

- viable solo como capa aproximada usando summaries CRCON
- no viable como logica exacta de encounter-by-encounter

## Recommended Implementation Phases

### Phase 1

Implementable now without fictional telemetry:

1. consolidar el Elo core persistente competitivo
2. mantener `OutcomeScore` como driver principal del resultado
3. acotar moduladores HLL a un rango pequeno y observable
4. mantener gating por validez y participacion
5. exponer claramente pure Elo vs modifiers vs proxy

### Phase 2

Implementable now but only as approximation:

1. refinar `StrengthOfScheduleMatch`
2. introducir pressure/rivalry signal pequeno desde `most_killed` y `death_by`
3. hacer mas explicita la parte proxy de disciplina y objetivo

### Phase 3

Blocked until new telemetry exists:

1. exclusiones exactas de redeploy/self/menu deaths
2. `LeadershipIndex` exacto
3. objetivo tactico exacto
4. duel logic exacta por evento
5. roster-strength graph completo

## Final Conclusion

La repo ya puede sostener una V3 competitiva honesta si se define asi:

- Elo persistente real como nucleo
- moduladores HLL pequenos y acotados
- frontera explicita entre exacto, aproximado y bloqueado

La repo no puede sostener hoy, de forma exacta:

- exclusion de redeploy deaths
- exclusion de suicidios propios no competitivos
- exclusion de muertes por menu o self-inflicted no competitivas

Esa parte no debe implementarse como exacta hasta que exista una fuente nueva
de telemetria raw o un death-type persistido y auditable.
