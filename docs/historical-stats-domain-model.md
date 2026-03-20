# Historical Stats Domain Model

## Objective

Definir la fuente real y el modelo de dominio minimo para construir una capa
historica propia sobre los 2 servidores reales de Comunidad Hispana, sin
implementar todavia la ingesta completa ni comprometer una base de datos
productiva distinta de la base local ya usada en desarrollo.

## Real Historical Sources

Los 2 servidores reales ya exponen historico publico en:

- `https://scoreboard.comunidadhll.es/games`
- `https://scoreboard.comunidadhll.es:5443/games`

Observaciones verificadas sobre ambas fuentes:

- ambas responden con una SPA publica titulada `Hell Let Loose Stats`
- la descripcion publica indica `Hell Let Loose Statistics and Game History`
- ambas cargan el mismo bundle frontend, por lo que la estructura funcional
  observable parece comun y cambia solo el dataset servido por cada dominio
- en el bundle publico aparecen referencias a conceptos como `games`,
  `players`, `kills`, `deaths`, `matches` y `server`

Inferencia operativa:

- la fuente real no debe modelarse como una tabla HTML estable
- la primera opcion tecnica futura debe ser descubrir y consumir un endpoint
  estructurado del scoreboard si existe
- si no existe un endpoint publico reutilizable, la alternativa seria un parser
  controlado de HTML renderizado o del payload que hidrate la SPA

## Scope Of Historical Analytics Phase 1

La primera capacidad historica util del proyecto sera:

- top kills de la ultima semana por servidor

Por tanto, la ingesta base debe capturar como minimo:

- servidor
- partida
- fecha/hora de partida
- duracion si esta disponible
- mapa
- modo
- jugador
- kills
- muertes si estan disponibles

## Proposed Domain Entities

### `historical_servers`

Proposito:
representar cada servidor real de la comunidad como origen de historico.

Campos minimos:

- `server_id`
- `external_server_id`
- `display_name`
- `scoreboard_base_url`
- `is_active`

Notas:

- esta entidad reutiliza la identidad ya establecida en `servers` cuando la
  implementacion llegue a persistencia
- `scoreboard_base_url` permite mantener separado el origen historico por
  servidor sin hardcodear rutas dispersas

### `historical_matches`

Proposito:
representar una partida individual extraida del scoreboard.

Campos minimos:

- `match_id`
- `server_id`
- `source_match_ref`
- `started_at`
- `ended_at` nullable
- `duration_seconds` nullable
- `map_id`
- `mode_id` nullable
- `source_fingerprint`

Notas:

- `source_match_ref` debe conservar el identificador nativo del scoreboard si
  la fuente lo expone
- `source_fingerprint` cubre el caso en que no exista un id perfecto y haya que
  deduplicar por combinacion de campos observables

### `historical_maps`

Proposito:
mantener identidad y nombre normalizado de mapa.

Campos minimos:

- `map_id`
- `map_slug`
- `display_name`
- `raw_map_name`

Notas:

- el pipeline debe conservar el valor crudo y tambien un nombre normalizado
- esto evita que los rankings historicos mezclen variantes tecnicas del mismo
  mapa

### `historical_modes`

Proposito:
normalizar el modo de partida si la fuente lo ofrece.

Campos minimos:

- `mode_id`
- `mode_slug`
- `display_name`
- `raw_mode_name`

### `historical_players`

Proposito:
mantener una identidad de jugador lo bastante estable para consultas agregadas.

Campos minimos:

- `player_id`
- `identity_kind`
- `canonical_name`
- `last_seen_name`
- `source_player_ref` nullable
- `identity_fingerprint`

Notas:

- si el scoreboard no da un id perfecto, la identidad inicial puede basarse en
  una huella controlada por servidor y nombre normalizado
- la identidad debe ser revisable porque el nombre visible puede cambiar

### `historical_player_participations`

Proposito:
representar que un jugador participo en una partida concreta.

Campos minimos:

- `participation_id`
- `match_id`
- `player_id`
- `team` nullable
- `joined_at` nullable
- `left_at` nullable

Notas:

- esta capa separa la presencia del jugador de sus metricas
- deja espacio para futuras metricas por equipo o duracion de participacion

### `historical_player_match_stats`

Proposito:
guardar las metricas observadas por jugador dentro de una partida.

Campos minimos:

- `participation_id`
- `kills`
- `deaths` nullable
- `assists` nullable
- `score` nullable
- `rank_in_match` nullable
- `captured_at`

Notas:

- `kills` es la metrica obligatoria de la primera fase
- `deaths` se persiste solo si la fuente la ofrece de forma estable

## Identity And Deduplication Strategy

### Match identity

Orden preferido:

1. `source_match_ref` del scoreboard si existe y es estable
2. huella derivada de `server_id + started_at + map + mode + duration`

Regla:

- no insertar una partida nueva si ya existe la misma referencia nativa o la
  misma huella derivada

### Player identity

Orden preferido:

1. `source_player_ref` del scoreboard si existe
2. identidad derivada de `server_id + normalized_player_name`

Riesgo:

- esto no resuelve por completo renombres o colisiones entre jugadores con el
  mismo nombre

Mitigacion inicial:

- conservar siempre `canonical_name`, `last_seen_name` y la referencia nativa
  cuando exista
- documentar que los rankings de fase 1 pueden tener precision limitada si el
  scoreboard no expone un id fuerte

### Ingestion deduplication

Para poder reejecutar la ingesta sin duplicacion grave:

- upsert por `source_match_ref` o `source_fingerprint` en partidas
- upsert por `source_player_ref` o `identity_fingerprint` en jugadores
- unicidad por `match_id + player_id` en participaciones
- unicidad por `participation_id` en metricas de partida por jugador

## Initial Query Shape

Consulta prioritaria:

- top kills de la ultima semana por servidor

Agrupacion minima necesaria:

- filtrar partidas del servidor cuya ventana temporal caiga dentro de los
  ultimos 7 dias segun `started_at` o `ended_at`
- sumar `kills` por `player_id`
- devolver nombre canonico del jugador, kills agregadas y rango

Definicion inicial de ventana:

- ventana rodante de 7 dias hacia atras desde el momento de consulta
- usar UTC en backend para evitar ambiguedades

## Risks And Limits

- la estructura visible hoy es la de una SPA; el contrato interno del scoreboard
  puede cambiar sin aviso
- no se ha fijado todavia un endpoint JSON publico y estable del scoreboard
- si solo existe HTML cliente, el scraping sera mas fragil que una API
- la identidad de jugador puede ser imperfecta si la fuente no expone un id
- una misma partida podria aparecer con informacion parcial durante una captura
- la disponibilidad del scoreboard no debe bloquear el backend principal

## Recommended Technical Direction For Following Tasks

1. Descubrir primero el endpoint estructurado o payload interno usado por la SPA.
2. Implementar un parser backend desacoplado por servidor de scoreboard.
3. Persistir solo entidades y metricas necesarias para top kills semanal.
4. Mantener la ingesta idempotente antes de abrir endpoints historicos nuevos.
