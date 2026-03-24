# RCON Data Capability Audit

## Validation Date

- 2026-03-24

## Scope

Auditoria tecnica del alcance real de RCON en esta repo, separando con claridad:

- RCON directo implementado hoy en el backend
- historico CRCON / scoreboard publico
- metricas que solo serian posibles con captura propia de eventos o logs

No se implementa ninguna tabla, ruta, scoring ni captura adicional.

## Evidence Reviewed

- `backend/app/rcon_client.py`
- `backend/app/providers/rcon_provider.py`
- `backend/app/data_sources.py`
- `backend/app/payloads.py`
- `backend/README.md`
- `docs/historical-crcon-source-discovery.md`
- `docs/monthly-player-ranking-data-audit.md`
- `docs/monthly-mvp-ranking-scoring-design.md`

## Current RCON Surface In This Repository

La implementacion RCON actual es minima y solo cubre estado live.

Capacidades confirmadas en codigo hoy:

- handshake `ServerConnect`
- autenticacion `Login`
- consulta `GetServerInformation`

No hay evidencia en la repo de otros comandos RCON ya integrados para:

- eventos de kill
- detalle por arma
- relaciones killer -> victim
- teamkills por evento
- destruccion de garrisons u OPs
- historico de partidas cerradas

## What The Current Live Provider Exposes Today

El proveedor `RconLiveDataSource` solo normaliza estos campos para `/api/servers`:

- `external_server_id`
- `server_name`
- `status`
- `players`
- `max_players`
- `current_map`
- `region`
- `source_name`
- `snapshot_origin`
- `source_ref`

Esto significa que RCON directo hoy ya alimenta de forma confirmada:

- disponibilidad online del servidor
- nombre del servidor
- numero de jugadores actual
- capacidad maxima
- mapa actual
- metadata de procedencia del snapshot

## Data That Is Not Exposed By Direct RCON Today

Aunque la task pide revisar equipos, scoreboard actual y otros campos live, la
repo no confirma que el proveedor actual los este devolviendo hoy.

No quedan expuestos en el snapshot live actual:

- composicion por equipos
- scoreboard de jugadores en tiempo real
- kills por jugador en la partida en curso
- deaths por jugador en la partida en curso
- support/combat/offense/defense live
- teamkills live

Importante:

- esto no prueba que el protocolo HLL RCON no pueda ofrecer mas cosas
- solo prueba que la implementacion actual de esta repo no las consulta ni las
  serializa

## Historical Boundary

La separacion entre live e historico queda clara en la repo:

- `get_live_data_source()` puede resolver `rcon`
- `get_historical_data_source()` devuelve un placeholder `RconHistoricalDataSource`
- ese proveedor historico lanza `RuntimeError("Historical RCON provider is not implemented yet.")`

Conclusion operativa:

- RCON esta operativo hoy para estado live de `/api/servers`
- RCON no esta operativo hoy para ingesta historica
- el historico reutilizable del proyecto sigue viniendo de CRCON / scoreboard publico

## Capability Matrix For Future MVP V2 Metrics

| Metrica / senal | RCON directo hoy en esta repo | Requeriria eventos/logs + persistencia | Estado actual |
| --- | --- | --- | --- |
| Estado del servidor | Si | No | Disponible |
| Jugadores actuales totales | Si | No | Disponible |
| Capacidad maxima | Si | No | Disponible |
| Mapa actual | Si | No | Disponible |
| Equipos live | No confirmado | Posiblemente no, depende de ampliar cliente | No expuesto hoy |
| Scoreboard live por jugador | No confirmado | Posiblemente no, depende de ampliar cliente | No expuesto hoy |
| Kills por arma | No | Si | Requiere pipeline nuevo |
| Distincion artillery / tank / infantry | No | Si | Requiere pipeline nuevo |
| Killer -> victim | No | Si | Requiere pipeline nuevo |
| `most_killed` | No | Si | Requiere pipeline nuevo |
| `death_by` | No | Si | Requiere pipeline nuevo |
| Teamkills por evento | No | Si | Requiere pipeline nuevo |
| Teamkills agregados por partida/mes | No desde RCON actual | Si | Requiere pipeline nuevo |
| Garrisons destruidos | No confirmado | Si como minimo | No confirmado |
| OPs destruidos | No confirmado | Si como minimo | No confirmado |
| Otras metricas tacticas finas | No | Si | Requiere pipeline nuevo |
| Partidas cerradas historicas | No | Si | No disponible hoy via RCON |

## What Can Feed An MVP V2 From RCON

Subset viable usando solo RCON directo ya implementado:

- ninguno de los componentes avanzados de scoring MVP
- solo datos de presencia live del servidor, utiles para panel operativo pero no
  para ranking mensual

Subset viable si se amplia solo el cliente RCON pero sin pipeline historico:

- quiza mas detalle live si el protocolo ofrece comandos adicionales
- aun asi no bastaria para un ranking mensual auditable, porque faltaria
  persistencia por evento o por partida cerrada

Subset viable si se construye una linea nueva de eventos/logs RCON:

- kills por arma
- killer/victim
- teamkills por evento
- clasificacion artillery/tank/infantry
- senales tacticas si el origen real las emite

Condiciones minimas para que eso sirva a un MVP V2:

- ampliar el cliente RCON con comandos o feeds adicionales reales
- capturar eventos de forma continua fuera del request path HTTP
- persistir historico propio por partida, jugador y evento
- definir agregados reproducibles para mes y servidor

## Separation From CRCON / Public Scoreboard

La repo ya confirma que ciertas metricas avanzadas existen en CRCON publico,
pero eso no debe confundirse con RCON directo.

La evidencia actual de CRCON/scoreboard publico incluye campos como:

- `kills_by_type`
- `most_killed`
- `death_by`
- `weapons`
- `death_by_weapons`

Eso pertenece al historico JSON publico ya documentado y no a la superficie
RCON hoy implementada en `rcon_client.py`.

## Practical Conclusion

Para esta repo, la respuesta precisa hoy es:

- RCON directo sirve para estado live de servidores
- RCON directo no sirve todavia para alimentar un MVP mensual V2
- cualquier MVP V2 con armas, duelos, teamkills por evento o tacticas requiere
  una canalizacion nueva de eventos/logs y persistencia historica propia
- garrisons y OPs siguen sin evidencia confirmada en la repo como metrica
  disponible por RCON

## Recommended Next Step

Antes de disenar scoring V2 sobre RCON, la siguiente decision tecnica correcta
seria una task separada de discovery para definir:

- si el origen RCON real del servidor expone mas comandos aparte de `GetServerInformation`
- si existe flujo de eventos reutilizable
- que granularidad y frecuencia tendria la persistencia de esos eventos
- que subset minimo merece convertirse en modelo historico propio
