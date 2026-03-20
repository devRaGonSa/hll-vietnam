# Historical Domain Model

## Objective

Definir la base minima de dominio y persistencia para historico de partidas y
metricas por jugador obtenidas desde la capa JSON publica de los scoreboards
CRCON de Comunidad Hispana.

## Scope

Esta capa cubre solo historico persistido en backend:

- identidad estable de los 2 servidores historicos
- partidas cerradas o actualizadas desde CRCON
- mapas asociados a esas partidas
- identidad reutilizable de jugadores
- estadisticas de jugador por partida
- trazabilidad de ejecuciones de ingesta

No sustituye ni modifica el flujo actual de snapshots live via A2S.

## Stable Identities

### Server

- tabla: `historical_servers`
- clave estable: `slug`
- ejemplos:
  - `comunidad-hispana-01`
  - `comunidad-hispana-02`
- atributos de soporte:
  - `scoreboard_base_url`
  - `server_number`
  - `source_kind`

### Match

- tabla: `historical_matches`
- clave estable: `(historical_server_id, external_match_id)`
- `external_match_id` corresponde al `id` devuelto por CRCON para cada partida
- razon:
  - el `id` de partida es estable dentro de cada scoreboard
  - se conserva separado por servidor para evitar asumir unicidad global sin
    contrato formal

### Player

- tabla: `historical_players`
- clave estable: `stable_player_key`
- estrategia de identidad:
  1. `steam:{steamid}` cuando existe `steaminfo.profile.steamid`
  2. `steaminfo:{id}` cuando existe `steaminfo.id`
  3. `crcon-player:{player_id}` cuando existe `player_id`
  4. `name:{normalized-name}` como ultimo fallback

La prioridad evita perder continuidad cuando CRCON expone SteamID. Los
fallbacks quedan documentados porque la calidad del origen no es totalmente
uniforme.

### Player Stats Per Match

- tabla: `historical_player_match_stats`
- clave estable: `(historical_match_id, historical_player_id)`
- efecto:
  - la misma partida puede reingestarse sin duplicar filas
  - si una partida cambia despues, la fila se actualiza por `UPSERT`

### Ingestion Run

- tabla: `historical_ingestion_runs`
- registra:
  - tipo de ejecucion (`bootstrap` o `incremental`)
  - inicio y fin
  - estado
  - paginas procesadas
  - matches vistos
  - inserts y updates

## Data Model

### `historical_servers`

Fuente historica por scoreboard CRCON.

### `historical_maps`

Catalogo reutilizable de mapas usando `map.id` cuando existe.

### `historical_matches`

Partida historica persistida con:

- servidor
- identidad externa
- tiempos (`creation_time`, `start`, `end`)
- mapa y metadatos visibles
- resultado axis/allied
- referencia de procedencia

### `historical_players`

Identidad reutilizable del jugador entre partidas y servidores.

### `historical_player_match_stats`

Metricas por jugador y partida con al menos:

- kills
- deaths
- teamkills
- time_seconds
- kills_per_minute
- deaths_per_minute
- kill_death_ratio
- combat
- offense
- defense
- support

### `historical_ingestion_runs`

Trazabilidad operativa para bootstrap y refresh incremental.

## Idempotency Strategy

- servidores sembrados de forma declarativa y actualizables por `slug`
- partidas persistidas con `UPSERT` por `(historical_server_id, external_match_id)`
- jugadores persistidos con `UPSERT` por `stable_player_key`
- estadisticas por jugador actualizadas con `UPSERT` por
  `(historical_match_id, historical_player_id)`
- el refresco incremental usa una ventana de solape temporal para volver a leer
  partidas recientes y absorber cambios tardios sin rehacer todo el historico

## Query Readiness

La estructura soporta ya consultas futuras como:

- top kills de la ultima semana por servidor
- partidas recientes por servidor
- mapas jugados y frecuencia
- agregados por jugador sobre ventanas temporales

## Separation From Live State

- live state actual: `server_snapshots` via A2S
- historico persistido: `historical_*` via CRCON scoreboard JSON

Ambas lineas comparten el mismo SQLite local de desarrollo para reducir
complejidad operativa, pero mantienen tablas y contratos separados.
