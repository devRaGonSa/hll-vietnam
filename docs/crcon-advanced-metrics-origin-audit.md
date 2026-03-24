# CRCON Advanced Metrics Origin Audit

## Validation Date

- 2026-03-24

## Scope

Auditoria tecnica del origen probable de metricas avanzadas visibles en
ecosistemas tipo CRCON / HLL Records, separando:

- RCON directo implementado hoy en esta repo
- campos historicos ya visibles en la capa publica tipo scoreboard
- metricas que solo resultan plausibles con eventos/logs y agregacion propia

No se implementa captura nueva, tablas nuevas ni cambios de producto.

## Evidence Reviewed

- `docs/rcon-data-capability-audit.md`
- `docs/monthly-player-ranking-data-audit.md`
- `docs/historical-crcon-source-discovery.md`
- `backend/README.md`
- `backend/app/rcon_client.py`
- `backend/app/providers/rcon_provider.py`
- `backend/app/data_sources.py`

## Confirmed Boundary In This Repository

La evidencia local confirma dos superficies distintas:

- RCON live directo para estado actual del servidor
- historico CRCON / scoreboard publico para partidas cerradas y metricas ricas

El cliente RCON implementado en `backend/app/rcon_client.py` solo usa:

- `ServerConnect`
- `Login`
- `GetServerInformation`

El proveedor `RconLiveDataSource` solo convierte eso en:

- nombre del servidor
- estado online
- jugadores actuales
- capacidad maxima
- mapa actual
- metadata de procedencia del snapshot

La repo no contiene hoy evidencia de comandos RCON integrados para:

- killer -> victim
- kills por arma
- teamkills por evento
- duelos jugador contra jugador
- ledger tactico de acciones
- reconstruccion historica de partidas cerradas

## What The Historical Source Already Exposes

La discovery historica local ya documenta que el detalle CRCON / scoreboard
publico expone campos avanzados como:

- `kills_by_type`
- `most_killed`
- `death_by`
- `weapons`
- `death_by_weapons`

Ademas, `docs/monthly-player-ranking-data-audit.md` confirma que esos campos
existen en el origen, aunque la persistencia actual del proyecto todavia no los
guarda.

## Technical Interpretation

La mejor lectura tecnica basada en la repo es esta:

- RCON puro hoy solo cubre estado live operativo
- metricas como `most_killed` y `death_by` no salen del cliente RCON actual
- esas metricas ya existen en una capa historica enriquecida externa al cliente
  RCON local
- para reproducirlas dentro del proyecto haria falta una persistencia propia o
  una fuente historica equivalente que conserve eventos o agregados avanzados

Esto no demuestra por si solo el mecanismo interno exacto de CRCON o HLL
Records, pero si permite descartar algo importante: en esta repo no hay base
para afirmar que esas metricas provengan de RCON directo ya listo para usar.

## Plausible Origin Paths

### 1. Direct RCON Commands

Plausibilidad en esta repo: baja para metricas avanzadas.

Motivo:

- no hay comandos RCON avanzados integrados en codigo
- no hay provider historico RCON operativo
- `RconHistoricalDataSource` es solo un placeholder que falla con
  `Historical RCON provider is not implemented yet.`

Conclusion:

- RCON directo es plausible para live state
- no hay evidencia local suficiente para atribuirle `most_killed`,
  `death_by`, killer/victim o kills por arma

### 2. Event Stream Or Server Logs

Plausibilidad en esta repo: alta como origen tecnico necesario si el proyecto
quisiera reconstruir esas metricas por cuenta propia.

Motivo:

- killer/victim requiere granularidad por evento o al menos por encounter
- kills por arma requieren capturar el arma asociada al kill
- teamkills por evento requieren distinguir el evento individual
- clasificaciones como infantry / tank / artillery requieren una senal por tipo
  de kill o contexto del evento

Conclusion:

- para producir estas metricas dentro de HLL Vietnam, un pipeline de eventos o
  logs es la hipotesis tecnica mas consistente

### 3. CRCON Internal Storage / Enriched Aggregation

Plausibilidad en esta repo: alta para explicar lo que ya se observa en el
scoreboard publico.

Motivo:

- la fuente publica ya devuelve campos agregados que el proyecto no calcula
- esos campos no se derivan del snapshot live RCON implementado hoy
- `most_killed` y `death_by` parecen vistas agregadas de encounters, no simples
  contadores live del servidor

Conclusion:

- CRCON / HLL Records probablemente sirve esos campos desde una capa historica
  propia ya enriquecida y persistida, no desde la llamada live minima que esta
  repo usa por RCON

## Origin Matrix By Metric

| Metrica | RCON directo hoy en esta repo | Requiere eventos/logs para reproducirla | Requiere agregacion/persistencia propia | Origen probable segun evidencia local |
| --- | --- | --- | --- | --- |
| Estado live del servidor | Si | No | No | RCON directo |
| Jugadores actuales | Si | No | No | RCON directo |
| Mapa actual | Si | No | No | RCON directo |
| Scoreboard live basico por jugador | No confirmado | Posiblemente no siempre | Posiblemente no | No confirmado en la repo |
| `most_killed` | No | Si o fuente historica equivalente | Si | Capa historica enriquecida |
| `death_by` | No | Si o fuente historica equivalente | Si | Capa historica enriquecida |
| killer -> victim | No | Si | Si | Eventos/logs + persistencia |
| kills por arma | No | Si | Si | Eventos/logs + persistencia |
| `kills_by_type` | No | Si | Si | Eventos/logs + persistencia |
| `death_by_weapons` | No | Si | Si | Eventos/logs + persistencia |
| teamkills por evento | No | Si | Si | Eventos/logs + persistencia |
| teamkills agregados historicos | No desde RCON actual | Si | Si | Agregacion historica |
| duelos reutilizables | No | Si | Si | Eventos/logs + persistencia |
| distincion infantry / tank / artillery | No | Si | Si | Eventos/logs + clasificacion propia |
| acciones tacticas finas | No confirmadas | Si | Si | No confirmadas, pero no salen del RCON actual |

## What RCON Purely Can Plausibly Provide

Con evidencia local, RCON puro queda limitado a:

- estado actual del servidor
- jugadores presentes
- capacidad maxima
- mapa actual
- metadata live util para un panel operativo

Eso sirve para monitoreo live, no para un MVP mensual V2 con rivalidades,
armas, killers, victims o taxonomias tacticas.

## What Seems To Require Event Capture Or Logs

Las metricas siguientes solo son defendibles si el proyecto capta eventos o
logs con granularidad suficiente:

- killer -> victim
- `most_killed`
- `death_by`
- kills por arma
- `kills_by_type`
- `death_by_weapons`
- teamkills por evento
- segmentacion infantry / tank / artillery

La razon comun es que todas dependen de relaciones o atributos de eventos
individuales, no solo de un snapshot agregado del servidor.

## What Seems To Require Historical Aggregation

Incluso con eventos capturados, haria falta una capa propia de persistencia y
agregacion para exponer de forma estable:

- rivales mas frecuentes
- resumen `most_killed`
- resumen `death_by`
- perfiles de armas por jugador
- acumulados mensuales auditables por servidor

Sin esa capa, la señal estaria dispersa en eventos crudos y no seria operativa
para un ranking MVP V2.

## Final Conclusion

La conclusion mas solida que soporta esta repo es:

- `most_killed`, `death_by`, killer/victim y kills por arma no salen del RCON
  directo implementado hoy
- esas metricas ya son visibles en una fuente historica enriquecida externa al
  cliente RCON local
- para reproducirlas dentro del proyecto haria falta una canalizacion nueva de
  eventos/logs y una persistencia historica propia con agregados derivados

## Recommended Follow-Up

La siguiente task tecnica correcta es disenar el pipeline minimo de eventos de
jugador necesario para alimentar una V2 del ranking mensual sin asumir que RCON
directo ya entrega esas metricas listas.
