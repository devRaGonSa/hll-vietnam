# Historical CRCON Source Discovery

## Objective

Documentar la fuente historica real y mas estable para los 2 servidores de la comunidad a partir de sus scoreboards publicos basados en CRCON, dejando claro que el historico reutilizable debe venir de esa capa y no de A2S ni de una implementacion previa ya descartada.

## Discovery Date

- Verificado el 2026-03-20 contra:
  - `https://scoreboard.comunidadhll.es/games`
  - `https://scoreboard.comunidadhll.es:5443/games`

## Main Finding

La fuente historica reutilizable mas estable disponible hoy es una API JSON publica expuesta por cada scoreboard, no el HTML renderizado de `/games`.

Las dos URLs de historial cargan una SPA con el mismo bundle frontend. Ese bundle usa `axios` con `baseURL: "/api"` y consulta endpoints JSON concretos:

- `GET /api/get_public_info`
- `GET /api/get_live_scoreboard`
- `GET /api/get_live_game_stats`
- `GET /api/get_scoreboard_maps?page={page}&limit={limit}`
- `GET /api/get_map_scoreboard?map_id={map_id}`

Por tanto, la estrategia recomendada no es parsear HTML de `/games`, sino consumir la capa JSON que alimenta ese frontend.

## Server Mapping

Cada scoreboard representa un servidor distinto:

- `https://scoreboard.comunidadhll.es`
  - `GET /api/get_public_info` identifica `#01 [ESP] Comunidad Hispana - discord.comunidadhll.es - Spa Onl`
  - `public_stats_port`: `7010`
  - `public_stats_port_https`: `7011`
- `https://scoreboard.comunidadhll.es:5443`
  - `GET /api/get_public_info` identifica `#02 [ESP] Comunidad Hispana - discord.comunidadhll.es - Spa Onl`
  - `public_stats_port`: `7012`
  - `public_stats_port_https`: `7013`

## How Historical Data Is Loaded

### 1. History list

`GET /api/get_scoreboard_maps?page=1&limit=5`

Devuelve una lista paginada de partidas finalizadas con estructura JSON. Campos verificados:

- `page`
- `page_size`
- `total`
- `maps[]`

Cada item de `maps[]` incluye al menos:

- `id`
- `creation_time`
- `start`
- `end`
- `server_number`
- `map.id`
- `map.pretty_name`
- `map.image_name`
- `map.game_mode`
- `result.axis`
- `result.allied`

Observacion importante:

- `player_stats` aparece vacio en la lista. Para metricas de jugadores hay que ir al endpoint de detalle.

### 2. Match detail

`GET /api/get_map_scoreboard?map_id={map_id}`

Devuelve el detalle historico de una partida concreta. Ejemplos verificados:

- servidor `#01`: `map_id=1561077`
- servidor `#02`: `map_id=1561076`

Campos verificados a nivel de partida:

- `id`
- `creation_time`
- `start`
- `end`
- `server_number`
- `map_name`
- `map.pretty_name`
- `result.axis`
- `result.allied`
- `player_stats[]`

Campos verificados a nivel de jugador dentro de `player_stats[]`:

- `id`
- `player_id`
- `player`
- `steaminfo.id`
- `steaminfo.profile.steamid` cuando existe
- `map_id`
- `kills`
- `kills_by_type`
- `kills_streak`
- `deaths`
- `deaths_by_type`
- `teamkills`
- `time_seconds`
- `kills_per_minute`
- `deaths_per_minute`
- `kill_death_ratio`
- `longest_life_secs`
- `shortest_life_secs`
- `combat`
- `offense`
- `defense`
- `support`
- `most_killed`
- `death_by`
- `weapons`
- `death_by_weapons`
- `team.side`
- `level`

Esto confirma que el scoreboard ya expone la base necesaria para rankings semanales por servidor como "top kills", junto con otras metricas reutilizables.

## Detail URLs And IDs

- La UI publica usa rutas tipo `/games/{id}`.
- `GET https://scoreboard.comunidadhll.es/games/1561077` responde `200`.
- `GET https://scoreboard.comunidadhll.es:5443/games/1561076` responde `200`.

Inferencia razonable:

- `/games/{id}` es la URL publica de detalle de partida.
- el dato real se resuelve desde frontend llamando a `GET /api/get_map_scoreboard?map_id={id}`.

## Stable Historical Data Actually Available

A dia 2026-03-20, la capa JSON permite obtener de forma estable:

- servidor
  - por host del scoreboard
  - por `server_number`
  - por `get_public_info.name`
- partida
  - `id`
  - `start`
  - `end`
  - `creation_time`
- mapa
  - `map.id`
  - `map.pretty_name`
  - `game_mode`
  - `environment`
- jugador
  - `player_id`
  - `player`
  - `steaminfo` parcial cuando existe
- metricas
  - `kills`
  - `deaths`
  - `teamkills`
  - `kills_per_minute`
  - `kill_death_ratio`
  - `combat`
  - `offense`
  - `defense`
  - `support`
  - desglose por armas y tipos cuando aparece

## Pagination And Historical Depth

- La lista historica es paginada mediante `page` y `limit`.
- El bundle observado usa por defecto `page=1` y `limit=50`.
- En la verificacion:
  - servidor `#01` reporto `total: 23027`
  - servidor `#02` reporto `total: 18219`

Esto sugiere una profundidad historica amplia y apta para ingesta incremental paginada.

## Risks And Limits

- La fuente es publica, pero no hay contrato formal versionado publicado; sigue siendo una API no documentada externamente.
- El frontend depende de rutas `/api/...` observadas en el bundle actual `v11.9.0`; una actualizacion futura podria renombrarlas.
- `player_id` no parece homogeneo al 100%:
  - a veces coincide con SteamID
  - a veces aparece como hash o identificador alternativo
- `steaminfo` puede venir completo, parcial o `null`; no debe asumirse como obligatorio.
- Existen valores de calidad irregular en algunas partidas:
  - `shortest_life_secs` negativos
  - jugadores con tiempos atipicos
  - campos vacios o `unknown`
- El HTML de `/games` no debe tomarse como base tecnica porque solo sirve la SPA shell y es mas fragil que consumir el JSON directo.
- A2S sigue siendo util para estado actual, no para reconstruir historico de partidas ni ranking semanal retroactivo.

## Recommended Strategy For Following Tasks

### Ideal historical source

Usar directamente la API JSON publica de cada scoreboard CRCON:

- listar partidas con `GET /api/get_scoreboard_maps`
- obtener detalle por partida con `GET /api/get_map_scoreboard`

### Realistic initial operating plan

1. Mantener separados los 2 orígenes:
   - `https://scoreboard.comunidadhll.es/api`
   - `https://scoreboard.comunidadhll.es:5443/api`
2. Registrar por servidor:
   - host base del scoreboard
   - nombre publico devuelto por `get_public_info`
   - `server_number`
3. Ingerir paginas historicas de forma incremental.
4. Persistir una entidad de partida externa con `match_id = id`.
5. Persistir filas de estadistica por jugador asociadas a `match_id` y servidor.
6. Calcular agregados semanales desde esos datos persistidos, no consultando el scoreboard en cada request de frontend.

### Fallback if the JSON layer changes

- primer fallback: revalidar el bundle SPA para localizar las nuevas rutas `/api`
- segundo fallback: parsear HTML solo como ultimo recurso y solo si el JSON deja de ser accesible

## Explicitly Not Recommended

- No basar el historico en A2S.
- No reutilizar como base de arquitectura una implementacion historica previa ya descartada.
- No tomar el HTML de `/games` como fuente principal.
- No disenar todavia la UI historica final.

## Repository Impact

El repositorio ya tenia una pista correcta en la landing al enlazar ambos scoreboards, pero no existia documentacion tecnica del origen real de historico.

Tambien se detecto un rastro de implementacion previa no reutilizable:

- `backend/app/payloads.py` importa `.historical_storage` para un flujo de `weekly_top_kills`
- el archivo `backend/app/historical_storage.py` no existe

Ese estado confirma que cualquier intento previo de ranking historico no debe considerarse base valida para la siguiente fase. La nueva fase debe reconstruirse desde la fuente CRCON JSON documentada aqui.
