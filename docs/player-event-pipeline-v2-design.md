# Player Event Pipeline V2 Design

## Validation Date

- 2026-03-24

## Scope

Diseno tecnico minimo de una futura canalizacion de eventos de jugador para
alimentar una V2 del ranking MVP mensual con metricas avanzadas.

Fuera de alcance:

- implementacion real del pipeline
- nuevas tablas o migraciones
- nuevos endpoints
- cambios de UI

## Inputs Reviewed

- `docs/rcon-data-capability-audit.md`
- `docs/crcon-advanced-metrics-origin-audit.md`
- `docs/monthly-mvp-ranking-scoring-design.md`
- `backend/README.md`
- `backend/app/historical_models.py`
- `backend/app/historical_storage.py`
- `backend/app/rcon_client.py`

## Problem Statement

La capa historica actual persiste bien metricas agregadas por jugador y partida:

- kills
- deaths
- teamkills
- tiempo
- combat
- offense
- defense
- support

Eso basta para un MVP V1. No basta para una V2 que quiera exponer o puntuar:

- killer -> victim
- `most_killed`
- `death_by`
- kills por arma
- `kills_by_type`
- `death_by_weapons`
- distincion infantry / tank / artillery

La auditoria previa deja claro que esas senales no salen del RCON live minimo
implementado hoy.

## Design Goals

La V2 necesita una capa nueva con estos objetivos:

- capturar eventos finos fuera del request path HTTP
- persistir eventos crudos con identidad suficiente para reprocess y auditoria
- derivar agregados reproducibles por partida, jugador y mes
- convivir con el modelo historico actual sin romper V1

## Minimal Architecture

La arquitectura minima propuesta tiene cuatro capas:

1. Source adapter

- un adaptador futuro conectado a eventos, logs o feed equivalente
- responsable solo de leer senales crudas y normalizarlas

2. Event ingestion worker

- proceso batch o loop dedicado, separado de `app.main`
- valida, deduplica y persiste eventos crudos
- nunca calcula ranking dentro del request HTTP

3. Raw event storage

- ledger append-only por evento
- base de auditoria y reproceso

4. Derived aggregates

- jobs posteriores que resumen por partida, jugador y ventana mensual
- capa consumible por un futuro MVP V2

## Proposed Flow

Flujo minimo:

1. El source adapter recibe un evento crudo del servidor o del origen elegido.
2. El worker normaliza el evento a un contrato comun.
3. El evento se persiste en un ledger crudo con claves de deduplicacion.
4. Un agregador por partida resume los eventos cerrados del match.
5. Un agregador mensual construye metricas V2 por jugador y servidor.
6. El ranking MVP V2 consume solo agregados ya cerrados y auditables.

## Minimum Event Types

El subconjunto minimo recomendado es:

- `player_kill`
- `player_death`
- `player_teamkill`
- `player_weapon_usage`

En la practica, `player_death` y `player_weapon_usage` pueden modelarse como
parte del mismo evento de kill si la fuente trae toda la informacion en un solo
registro. Aun asi, conceptualmente la V2 debe capturar estas piezas:

- match id o match scope
- timestamp del evento
- server slug
- killer player key
- victim player key
- killer team
- victim team
- weapon id o nombre de arma
- kill type o damage type
- contexto opcional de vehiculo, artilleria o explosivo
- indicador de teamkill

## Event Contract Proposal

Contrato minimo recomendado para un evento normalizado:

- `event_id`
- `event_type`
- `occurred_at`
- `server_slug`
- `external_match_id`
- `source_kind`
- `source_ref`
- `killer_player_key`
- `victim_player_key`
- `killer_team_side`
- `victim_team_side`
- `weapon_name`
- `weapon_category`
- `kill_category`
- `is_teamkill`
- `raw_event_ref`

Campos opcionales pero utiles desde el inicio:

- `killer_display_name`
- `victim_display_name`
- `vehicle_name`
- `explosive_name`
- `match_phase`

## High-Level Persistence Model

No se crean tablas en esta task, pero la persistencia minima deberia separar:

### 1. Raw player event ledger

Rol:

- guardar cada evento de forma append-only
- permitir reprocess y auditoria

Campos minimos:

- event key estable
- server
- match
- timestamp
- tipo de evento
- actor y target
- arma o categoria
- flags de clasificacion

### 2. Match event aggregates

Rol:

- resumir por partida ya cerrada
- evitar recalcular toda la historia cada vez

Ejemplos de campos:

- kills por jugador
- deaths por jugador
- teamkills por jugador
- kills por arma
- kills por categoria
- tabla de killer -> victim mas frecuente
- tabla de victim <- killer mas frecuente

### 3. Monthly player advanced aggregates

Rol:

- dejar lista la capa consumible por el ranking V2

Ejemplos de campos:

- total kills por arma
- total kills por categoria
- rival mas matado (`most_killed`)
- rival que mas le mata (`death_by`)
- teamkills mensuales
- pesos o subscores avanzados V2

## Relationship With Current Historical Model

La propuesta no sustituye el modelo existente `historical_player_match_stats`.

Relacion recomendada:

- `historical_*` sigue guardando el resumen estable V1 por partida
- el nuevo ledger de eventos guarda granularidad que hoy no existe
- los agregados V2 se derivan del ledger y se pueden unir despues al dominio
  mensual existente

Esto evita dos errores:

- inflar `historical_player_match_stats` con JSON opaco o columnas prematuras
- mezclar captura cruda y vistas derivadas en la misma tabla

## How Advanced Metrics Would Be Derived

### `most_killed`

Derivacion:

- agrupar eventos de kill por `killer_player_key` y `victim_player_key`
- contar ocurrencias
- elegir el victim con mayor conteo por jugador y ventana

### `death_by`

Derivacion:

- agrupar eventos de kill por `victim_player_key` y `killer_player_key`
- contar ocurrencias
- elegir el killer con mayor conteo recibido por jugador y ventana

### Kills por arma

Derivacion:

- agrupar kills por `killer_player_key` y `weapon_name`

### `kills_by_type`

Derivacion:

- clasificar cada kill en una categoria normalizada
- agrupar por `killer_player_key` y `kill_category`

Categorias minimas sugeridas:

- `infantry`
- `vehicle`
- `artillery`
- `explosive`
- `unknown`

### `death_by_weapons`

Derivacion:

- agrupar eventos por `victim_player_key` y `weapon_name`

### Distincion infantry / tank / artillery

Solo es viable si el origen del evento trae senales suficientes para clasificar:

- arma
- vehiculo
- damage type
- o una taxonomia equivalente ya normalizada

Si la fuente no trae esa precision, la categoria debe quedarse en `unknown` y
la V2 no debe inventar inferencias fragiles.

## Recommended Processing Policy

Politica minima recomendada:

- ingesta continua o semi-continua fuera de HTTP
- deduplicacion por `event_id` o hash determinista
- agregacion solo sobre partidas cerradas
- recomputacion idempotente por partida y por ventana mensual
- capacidad de rehidratar agregados desde el ledger crudo

## Integration Point With Monthly MVP V2

La V2 mensual deberia seguir la misma forma general de la V1:

- elegibilidad explicita
- componentes normalizados
- pesos auditables
- tie-breaks deterministas

La diferencia es la entrada:

- V1 consume agregados simples ya persistidos por partida
- V2 consumiria un agregado mensual enriquecido derivado del ledger de eventos

Componentes plausibles para una futura V2:

- kills totales
- support total
- eficiencia base
- variedad o efectividad por arma
- penalizacion por teamkills
- subscore de encounters a partir de killer/victim
- categoria de impacto por tipo de kill si la fuente lo soporta

## Minimal Rollout Path

Secuencia minima recomendada para futuras tasks:

1. Validar la fuente real de eventos/logs reutilizable.
2. Definir el contrato normalizado del evento.
3. Implementar ledger crudo con deduplicacion.
4. Implementar agregador por partida cerrada.
5. Implementar agregado mensual avanzado por jugador.
6. Disenar formula MVP V2 sobre esos agregados.
7. Exponer lectura API solo cuando los agregados sean estables.

## Main Risks

- la fuente real puede no exponer todas las senales necesarias
- clasificar kills por tipo puede requerir un mapa de armas adicional
- sin deduplicacion robusta, los agregados V2 serian poco fiables
- mezclar eventos abiertos con partidas no cerradas inflaria metricas

## Final Recommendation

La arquitectura minima correcta para una V2 no es ampliar el snapshot live ni
sobrecargar `historical_player_match_stats`. Es anadir una capa separada de
eventos crudos, con agregacion derivada por partida y por mes, para producir de
forma auditable metricas como `most_killed`, `death_by`, kills por arma y
clasificaciones avanzadas.
