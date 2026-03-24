# Backend

Esta carpeta contiene el bootstrap minimo del futuro backend principal en Python para HLL Vietnam.

## Objetivo en esta fase

- dejar un punto de entrada claro para la aplicacion
- validar que el backend puede arrancar localmente
- exponer rutas placeholder coherentes con el contrato frontend-backend

## Stack actual del bootstrap

- Python 3
- libreria estandar de Python (`http.server`, sin frameworks ni dependencias externas)

## Estructura minima

```text
backend/
|-- README.md
|-- requirements.txt
`-- app/
    |-- a2s_client.py
    |-- __init__.py
    |-- collector.py
    |-- main.py
    |-- historical_ingestion.py
    |-- historical_models.py
    |-- historical_runner.py
    |-- historical_storage.py
    |-- normalizers.py
    |-- payloads.py
    |-- routes.py
    |-- server_targets.py
    `-- snapshots.py
```

La persistencia local de desarrollo se crea bajo `backend/data/` cuando el
colector la necesita por primera vez.

`app` es el paquete Python del backend. El archivo correcto del paquete es
`backend/app/__init__.py`; no debe existir una variante `init.py`.

## Punto de entrada

El entrypoint real del backend es el modulo `app.main`, ubicado en
`backend/app/main.py`.

Desde la carpeta `backend/`, se puede arrancar localmente con:

```powershell
python -m app.main
```

Ese comando usa imports relativos de paquete (`from .routes import ...`), por lo
que la forma soportada de arranque es por modulo y no ejecutando el archivo como
script suelto.

Por defecto escuchara en `127.0.0.1:8000`.

Variables opcionales:

- `HLL_BACKEND_HOST`
- `HLL_BACKEND_PORT`
- `HLL_BACKEND_ALLOWED_ORIGINS`
- `HLL_BACKEND_REFRESH_INTERVAL_SECONDS`
- `HLL_BACKEND_LIVE_DATA_SOURCE`
- `HLL_BACKEND_HISTORICAL_DATA_SOURCE`
- `HLL_BACKEND_RCON_TIMEOUT_SECONDS`
- `HLL_BACKEND_RCON_TARGETS`
- `HLL_HISTORICAL_CRCON_PAGE_SIZE`
- `HLL_HISTORICAL_CRCON_TIMEOUT_SECONDS`
- `HLL_HISTORICAL_CRCON_DETAIL_WORKERS`
- `HLL_HISTORICAL_CRCON_REQUEST_RETRIES`
- `HLL_HISTORICAL_CRCON_RETRY_DELAY_SECONDS`
- `HLL_HISTORICAL_REFRESH_INTERVAL_SECONDS`
- `HLL_HISTORICAL_SNAPSHOT_REFRESH_INTERVAL_SECONDS`
- `HLL_HISTORICAL_FULL_SNAPSHOT_EVERY_RUNS`
- `HLL_HISTORICAL_REFRESH_MAX_RETRIES`
- `HLL_HISTORICAL_REFRESH_RETRY_DELAY_SECONDS`
- `HLL_HISTORICAL_WEEKLY_FALLBACK_MIN_MATCHES`
- `HLL_HISTORICAL_WEEKLY_FALLBACK_MAX_WEEKDAY`

Variables especialmente relevantes para Docker y Compose:

- `HLL_BACKEND_HOST`
- `HLL_BACKEND_PORT`
- `HLL_BACKEND_STORAGE_PATH`
- `HLL_BACKEND_ALLOWED_ORIGINS`
- `HLL_BACKEND_LIVE_DATA_SOURCE`
- `HLL_BACKEND_HISTORICAL_DATA_SOURCE`
- `HLL_BACKEND_RCON_TIMEOUT_SECONDS`
- `HLL_BACKEND_RCON_TARGETS`
- `HLL_HISTORICAL_CRCON_PAGE_SIZE`
- `HLL_HISTORICAL_CRCON_TIMEOUT_SECONDS`
- `HLL_HISTORICAL_CRCON_DETAIL_WORKERS`
- `HLL_HISTORICAL_CRCON_REQUEST_RETRIES`
- `HLL_HISTORICAL_CRCON_RETRY_DELAY_SECONDS`
- `HLL_HISTORICAL_SNAPSHOT_REFRESH_INTERVAL_SECONDS`
- `HLL_HISTORICAL_FULL_SNAPSHOT_EVERY_RUNS`
- `HLL_HISTORICAL_REFRESH_MAX_RETRIES`
- `HLL_HISTORICAL_REFRESH_RETRY_DELAY_SECONDS`

Para ejecucion containerizada, el repositorio incluye tambien:

- `backend/Dockerfile`
- `backend/.dockerignore`
- `backend/.env.example`

El contenedor usa el mismo entrypoint real del proyecto:

```powershell
python -m app.main
```

Dentro del contenedor arranca por defecto con:

- `HLL_BACKEND_HOST=0.0.0.0`
- `HLL_BACKEND_PORT=8000`
- `HLL_BACKEND_STORAGE_PATH=/app/data/hll_vietnam_dev.sqlite3`

Build local:

```powershell
docker build -t hll-vietnam-backend ./backend
```

Ejecucion local con persistencia bind-mounted:

```powershell
docker run --rm `
  -p 8000:8000 `
  --env-file backend/.env.example `
  -v ${PWD}\backend\data:/app/data `
  hll-vietnam-backend
```

Si se prefiere no usar `--env-file`, el contenedor puede arrancar solo con sus
defaults para host, puerto y path de SQLite. El bind mount de `/app/data` sigue
siendo la forma recomendada de no perder persistencia al recrear el contenedor.

El `frontend/index.html` viene preparado para volver a consultar el bloque de
servidores cada `120000` ms (`120s`) sin recargar la pagina completa. La landing
lee ese valor desde `data-server-refresh-ms`, por lo que puede ajustarse en el
HTML si una demo local necesita un intervalo distinto.

Valor por defecto de `HLL_BACKEND_ALLOWED_ORIGINS`:

- `null`
- `http://127.0.0.1:5500`
- `http://127.0.0.1:8080`
- `http://localhost:5500`
- `http://localhost:8080`

Esto cubre el caso de abrir `frontend/index.html` directamente desde `file://`
y los puertos locales mas habituales cuando el frontend se sirve con un
servidor sencillo.

Prueba local recomendada para validar frontend y backend juntos:

1. En una terminal, desde `backend/`, arrancar el backend:

   ```powershell
   python -m app.main
   ```

2. En otra terminal, desde `frontend/`, servir la landing:

   ```powershell
   python -m http.server 8080
   ```

3. Abrir `http://localhost:8080`.

Si se necesita otra combinacion de origenes locales, puede sobrescribirse
`HLL_BACKEND_ALLOWED_ORIGINS` con una lista separada por comas. El backend
normaliza espacios y barras finales para mantener la comparacion con el header
`Origin` del navegador.

## Endpoints placeholder disponibles

- `GET /health`
- `GET /api/community`
- `GET /api/trailer`
- `GET /api/discord`
- `GET /api/servers`
- `GET /api/servers/latest`
- `GET /api/servers/history?limit=20`
- `GET /api/servers/{id}/history?limit=20`
- `GET /api/historical/weekly-top-kills?limit=10&server=comunidad-hispana-01`
- `GET /api/historical/weekly-leaderboard?metric=kills&limit=10&server=comunidad-hispana-01`
- `GET /api/historical/leaderboard?timeframe=monthly&metric=kills&limit=10&server=comunidad-hispana-01`
- `GET /api/historical/monthly-mvp?limit=10&server=comunidad-hispana-01`
- `GET /api/historical/recent-matches?limit=20&server=comunidad-hispana-01`
- `GET /api/historical/server-summary?server=comunidad-hispana-01`
- `GET /api/historical/snapshots/server-summary?server=comunidad-hispana-01`
- `GET /api/historical/snapshots/weekly-leaderboard?metric=kills&limit=10&server=comunidad-hispana-01`
- `GET /api/historical/snapshots/leaderboard?timeframe=monthly&metric=kills&limit=10&server=comunidad-hispana-01`
- `GET /api/historical/snapshots/monthly-mvp?limit=10&server=comunidad-hispana-01`
- `GET /api/historical/snapshots/recent-matches?limit=6&server=comunidad-hispana-01`
- `GET /api/historical/player-profile?player=steam%3A76561198000000000`

`GET /health` expone tambien:

- `live_data_source`
- `historical_data_source`

`GET /api/servers` trata el ultimo snapshot persistido como cache local y lo
reutiliza solo si sigue dentro del objetivo de `120` segundos. Si ese snapshot
esta vencido, el endpoint intenta una consulta A2S real inmediata contra los 2
servidores configurados antes de responder.

La respuesta incluye metadata de frescura pensada para frontend:

- `last_snapshot_at`
- `snapshot_age_seconds`
- `snapshot_age_minutes`
- `max_snapshot_age_seconds`
- `is_stale`
- `freshness`
- `source`
- `refresh_attempted`
- `refresh_status`

Si la consulta real falla, `/api/servers` devuelve el ultimo snapshot valido
disponible marcado como stale. Si no existe ningun snapshot valido, responde
`items: []` en lugar de reintroducir servidores de respaldo ajenos a la
comunidad.

Los endpoints historicos leen la persistencia local SQLite creada por el
colector. Si todavia no hay snapshots guardados, responden `status: "ok"` con
`items: []` para mantener un contrato simple en desarrollo.

## Seleccion de fuente de datos

El backend separa ahora la fuente de datos del contrato HTTP del producto.
Esto permite cambiar proveedores por entorno sin tocar `routes.py`, payloads de
UI ni el formato consumido por frontend.

Variables nuevas:

- `HLL_BACKEND_LIVE_DATA_SOURCE`
- `HLL_BACKEND_HISTORICAL_DATA_SOURCE`

Valores soportados en esta fase:

- live:
  - `a2s` como modo actual de desarrollo
  - `rcon` como modo productivo para estado live via acceso directo al servidor
- historico:
  - `public-scoreboard` como modo actual de desarrollo
  - `rcon` seleccionado pero todavia sin ingesta historica operativa en esta repo

Defaults actuales:

- `HLL_BACKEND_LIVE_DATA_SOURCE=a2s`
- `HLL_BACKEND_HISTORICAL_DATA_SOURCE=public-scoreboard`

La seleccion efectiva se resuelve en `app/data_sources.py` y en adapters
dedicados dentro de `app/providers/`:

- `get_live_data_source()` entrega el proveedor usado por `payloads.py`
  cuando `/api/servers` necesita un refresh real
- `get_historical_data_source()` entrega el proveedor usado por
  `historical_ingestion.py` para bootstrap y refresh incremental
- `providers/public_scoreboard_provider.py` encapsula la semantica actual del
  scoreboard/CRCON publico bajo el contrato historico
- `providers/rcon_provider.py` encapsula el proveedor live basado en comandos
  RCON HLL v2 mediante `ServerConnect`, `Login` y `GetServerInformation`

Proveedores operativos en esta fase:

- live `a2s`
- live `rcon`
- historico `public-scoreboard`

Limitacion actual de `rcon`:

- el backend puede usar `rcon` para `/api/servers`
- la ingesta historica por `historical_ingestion.py` sigue requiriendo
  `public-scoreboard`, porque la repo todavia no incluye una canalizacion
  persistente de eventos o logs RCON para reconstruir partidas cerradas

Variables especificas de RCON live:

- `HLL_BACKEND_RCON_TIMEOUT_SECONDS`
- `HLL_BACKEND_RCON_TARGETS`

`HLL_BACKEND_RCON_TARGETS` acepta un array JSON con:

- `name`
- `host`
- `port`
- `password`
- `external_server_id` opcional
- `region` opcional
- `game_port` opcional
- `query_port` opcional
- `source_name` opcional

Ejemplo:

```powershell
$env:HLL_BACKEND_RCON_TARGETS='[
  {
    "name": "Comunidad Hispana #01",
    "host": "203.0.113.10",
    "port": 28015,
    "password": "replace-me",
    "external_server_id": "comunidad-hispana-01",
    "region": "ES",
    "game_port": 7777,
    "query_port": 7778,
    "source_name": "community-hispana-rcon"
  }
]'
```

Runbook operativo minimo:

- desarrollo:
  - `HLL_BACKEND_LIVE_DATA_SOURCE=a2s`
  - `HLL_BACKEND_HISTORICAL_DATA_SOURCE=public-scoreboard`
- produccion live con RCON:
  - `HLL_BACKEND_LIVE_DATA_SOURCE=rcon`
  - `HLL_BACKEND_HISTORICAL_DATA_SOURCE=public-scoreboard`
  - definir `HLL_BACKEND_RCON_TARGETS` fuera de la repo

Verificacion minima del proveedor activo:

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health | Select-Object -Expand Content
```

La respuesta incluye `live_data_source` y `historical_data_source`, util para
confirmar si la instancia esta usando `a2s` o `rcon` para live.

## Criterio de estructura

- `__init__.py` declara el paquete `app` y reexporta las utilidades publicas
  minimas del bootstrap.
- `collector.py` define el flujo minimo de captura para desarrollo usando una
  fuente controlada.
- `a2s_client.py` encapsula una consulta minima A2S_INFO por UDP para probar
  servidores reales sin acoplar todavia el backend a una fuente mas compleja.
- `rcon_client.py` encapsula una conexion minima HLL RCON v2 por TCP con
  `ServerConnect`, XOR key base64, `authToken` y `GetServerInformation` para
  consultas live de produccion.
- `config.py` centraliza host, puerto y allowlist minima de origenes locales.
- `data_sources.py` define los contratos y la seleccion por entorno para live e historico.
- `historical_ingestion.py` consulta la capa JSON publica de CRCON para bootstrap y refresh incremental.
- `historical_models.py` fija las entidades historicas minimas del dominio.
- `historical_snapshots.py` fija los tipos y selectores validos de snapshots historicos precalculados.
- `historical_snapshot_storage.py` persiste snapshots historicos precalculados listos para lectura rapida.
- `historical_runner.py` ejecuta refresh incremental periodico con reintentos basicos.
- `historical_storage.py` prepara la persistencia `historical_*` y las consultas agregadas iniciales.
- `main.py` contiene el entrypoint HTTP y la creacion del servidor.
- `normalizers.py` transforma registros crudos o respuestas A2S a un modelo
  comun del colector.
- `routes.py` resuelve las rutas GET soportadas.
- `payloads.py` centraliza respuestas placeholder y mock.
- `server_targets.py` registra targets A2S de prueba de forma desacoplada del
  flujo principal del colector.
- `snapshots.py` construye snapshots consistentes con timestamp comun de
  captura.
- `storage.py` prepara una persistencia local minima en SQLite para
  `game_sources`, `servers` y `server_snapshots`.

## Persistencia local minima

El backend ya puede guardar snapshots en un SQLite local de desarrollo usando
solo libreria estandar de Python. Esta base minima sigue el modelo logico de:

- `game_sources`
- `servers`
- `server_snapshots`
- `historical_servers`
- `historical_maps`
- `historical_matches`
- `historical_players`
- `historical_player_match_stats`
- `historical_ingestion_runs`

Por defecto el archivo se crea en:

```text
backend/data/hll_vietnam_dev.sqlite3
```

En Docker, ese mismo rol de persistencia debe montarse fuera del contenedor en:

```text
/app/data/hll_vietnam_dev.sqlite3
```

Variable opcional:

- `HLL_BACKEND_STORAGE_PATH`
- `HLL_BACKEND_A2S_TARGETS`

La base logica sigue documentada en
`docs/stats-database-schema-foundation.md` para snapshots live y en
`docs/historical-domain-model.md` para el historico CRCON. Esta implementacion
no introduce ORM, migraciones ni una decision de almacenamiento productivo.

## Snapshots historicos precalculados

La capa historica persiste ahora los snapshots precalculados orientados a UI
como archivos JSON independientes en disco, separados del SQLite del historico
bruto. Esta capa esta preparada para guardar:

- `server-summary`
- `weekly-leaderboard` con metricas `kills`, `deaths`, `support` y `matches_over_100_kills`
- `monthly-leaderboard` con las mismas metricas semanticas
- `monthly-mvp`
- `recent-matches`

Por defecto se escriben bajo:

```text
backend/data/snapshots/<server_key>/
```

En Docker, estos snapshots deben persistirse bajo:

```text
/app/data/snapshots/<server_key>/
```

Ejemplos:

- `backend/data/snapshots/comunidad-hispana-01/server-summary.json`
- `backend/data/snapshots/comunidad-hispana-01/weekly-kills.json`
- `backend/data/snapshots/comunidad-hispana-03/recent-matches.json`
- `backend/data/snapshots/all-servers/weekly-support.json`
- `backend/data/snapshots/all-servers/monthly-mvp.json`

Cada archivo conserva metadatos operativos minimos:

- `server_key`
- `snapshot_type`
- `metric`
- `window`
- `payload`
- `generated_at`
- `source_range_start`
- `source_range_end`
- `is_stale`

La persistencia usa una identidad de archivo estable por combinacion de
servidor, tipo y metrica para que cada refresh reemplace el artefacto anterior
sin mezclarlo con el historico bruto.

Resumen de persistencia recomendada para contenedor:

- montar `/app/data`
- conservar el SQLite historico en `/app/data/hll_vietnam_dev.sqlite3`
- conservar los snapshots JSON en `/app/data/snapshots/`

Con `docker compose`, esa persistencia ya queda montada desde:

- `./backend/data -> /app/data`

## Bootstrap del colector

El backend incluye un bootstrap minimo para el futuro flujo de snapshots:

- `fetch_controlled_server_source()` obtiene datos controlados de desarrollo
- `query_server_info()` permite consultar metadata basica real por A2S_INFO
- `fetch_a2s_probe()` adapta una consulta A2S real al modelo interno del colector
- `fetch_configured_a2s_probes()` consulta la lista configurada de targets A2S
- `normalize_server_record()` reduce los registros a una forma comun
- `normalize_a2s_server_info()` reduce una respuesta A2S al mismo contrato interno
- `build_server_snapshot()` y `build_snapshot_batch()` generan snapshots con
  `captured_at`
- `collect_server_snapshots()` orquesta captura, normalizacion, ensamblado y
  persistencia opcional
- `persist_snapshot_batch()` escribe el lote en SQLite y mantiene identidad de
  servidor separada del historico

Ejecucion manual desde `backend/`:

```powershell
python -m app.collector --source auto
```

Ese comando intenta consultar primero los targets A2S configurados. Si ninguno
responde y no se ha desactivado el fallback, usa la fuente controlada de
desarrollo para no romper el flujo local. El resultado imprime el modo usado,
los errores de consulta y el lote de snapshots persistido en SQLite.

Si se quiere forzar solo A2S real:

```powershell
python -m app.collector --source a2s --no-fallback
```

Ese flujo es la validacion local minima extremo a extremo para los targets
reales configurados de Comunidad Hispana. El timeout por defecto del cliente
A2S es `6.0s` para tolerar mejor latencia puntual entre multiples consultas
reales consecutivas. Cuando responden ambos targets por defecto, el comando
debe devolver:

- `collection_mode: "a2s"`
- `target_count: 2`
- `success_count: 2`
- un snapshot con `external_server_id: "comunidad-hispana-01"`
- un snapshot con `external_server_id: "comunidad-hispana-02"`
- `source_name: "community-hispana-a2s"`
- `snapshot_origin: "real-a2s"` en ambos
- `source_ref: "a2s://152.114.195.174:7778"`
- `source_ref: "a2s://152.114.195.150:7878"`
- persistencia en `backend/data/hll_vietnam_dev.sqlite3`

Si la consulta se ejecuta desde un entorno con red restringida, sin salida UDP
o con latencia puntual alta, el cliente puede devolver timeout aunque el target
este sano. En ese caso el resultado conserva errores controlados por target y
puede acabar con `success_count` parcial o `0` segun cuantas consultas fallen.

Los snapshots persistidos y los endpoints historicos exponen ademas:

- `snapshot_origin` para distinguir `real-a2s` frente a `controlled-fallback`
- `source_ref` para conservar una referencia de procedencia util en historico

Si se quiere seguir usando solo datos controlados:

```powershell
python -m app.collector --source controlled
```

## Refresco local periodico de snapshots

Para evitar lanzar el colector manualmente en cada captura, el backend incluye
un bucle local de refresco periodico pensado solo para desarrollo:

```powershell
python -m app.scheduler
```

Ese comando ejecuta capturas persistidas de forma repetida usando el mismo
flujo del colector y la base SQLite local. Por defecto:

- usa `--source auto`
- espera `120` segundos entre ejecuciones
- permite fallback controlado si A2S no responde
- sigue en ejecucion hasta que se detiene manualmente

Se puede detener de forma segura con `Ctrl+C`.

Variables y flags utiles:

- `HLL_BACKEND_REFRESH_INTERVAL_SECONDS` para cambiar el intervalo por defecto
- `--interval 120` para fijar el intervalo en segundos en una ejecucion concreta
- `--source a2s --no-fallback` para forzar solo capturas reales
- `--max-runs 3` para limitar el numero de ciclos y evitar un bucle indefinido

Ejemplos:

```powershell
python -m app.scheduler --interval 120
python -m app.scheduler --source a2s --no-fallback --max-runs 2
```

Flujo local recomendado para ver datos vivos en la landing:

1. Desde `backend/`, arrancar la API:

   ```powershell
   python -m app.main
   ```

2. En otra terminal, dejar el scheduler corriendo:

   ```powershell
   python -m app.scheduler
   ```

3. Servir `frontend/` con un servidor local sencillo y abrir la landing. El
   frontend volvera a pedir `/api/servers` cada `120` segundos, por lo que los
   cambios de mapa o poblacion apareceran sin recarga manual cuando existan
   snapshots nuevos.

Este mecanismo deja el refresco desacoplado del servidor HTTP y es facil de
reemplazar mas adelante por un scheduler mas serio sin rehacer el colector.

Prueba manual minima de A2S desde `backend/`:

```powershell
python -m app.a2s_client 203.0.113.10 27015
```

Ese comando lanza una consulta `A2S_INFO` por UDP y devuelve JSON con nombre de
servidor, mapa, jugadores y capacidad maxima cuando el query port responde.
Tambien puede reutilizarse desde Python con `query_server_info()` o
`fetch_a2s_probe()`. Si el servidor no responde o el puerto es incorrecto, el
cliente eleva errores controlados de timeout o protocolo para que la siguiente
task pueda integrarlo en el pipeline de snapshots sin romper el backend.

## Registro local de targets A2S

La lista de targets A2S vive en `app/server_targets.py`. Por defecto el backend
registra solo el primer target real verificado del proyecto:

- `Comunidad Hispana #01`
- host/IP: `152.114.195.174`
- `query_port`: `7778`
- `game_port`: `7777`
- `source_name`: `community-hispana-a2s`
- `external_server_id`: `comunidad-hispana-01`

`query_port` es el puerto usado para `A2S_INFO`; `game_port` se conserva por
separado para documentar el puerto de juego real sin mezclar ambos conceptos en
la configuracion.

El registro por defecto incluye dos targets reales verificados:

- `Comunidad Hispana #01`
  - host/IP: `152.114.195.174`
  - `query_port`: `7778`
  - `game_port`: `7777`
  - `external_server_id`: `comunidad-hispana-01`
- `Comunidad Hispana #02`
  - host/IP: `152.114.195.150`
  - `query_port`: `7878`
  - `game_port`: `7877`
  - `external_server_id`: `comunidad-hispana-02`

Si se quiere cambiar la lista sin editar codigo, puede definirse
`HLL_BACKEND_A2S_TARGETS` como un array JSON:

```powershell
$env:HLL_BACKEND_A2S_TARGETS='[
  {
    "name": "Comunidad Hispana #01",
    "host": "152.114.195.174",
    "query_port": 7778,
    "game_port": 7777,
    "source_name": "community-hispana-a2s",
    "external_server_id": "comunidad-hispana-01",
    "region": "ES"
  },
  {
    "name": "Comunidad Hispana #02",
    "host": "152.114.195.150",
    "query_port": 7878,
    "game_port": 7877,
    "source_name": "community-hispana-a2s",
    "external_server_id": "comunidad-hispana-02",
    "region": "ES"
  }
]'
```

Cada target soporta:

- `name`
- `host`
- `query_port`
- `game_port` opcional
- `source_name`
- `external_server_id` opcional
- `region` opcional

El colector puede resolver esos targets con `load_a2s_targets()` o
`fetch_configured_a2s_probes()` sin depender de constantes dispersas.

## Consulta historica minima

Una vez existen snapshots persistidos, el backend expone una primera capa de
consulta historica:

- `/api/servers/latest` devuelve el ultimo snapshot conocido por servidor
- `/api/servers/history` devuelve snapshots recientes agregados
- `/api/servers/{id}/history` devuelve el historial reciente de un servidor

`{id}` acepta el `server_id` numerico interno o el `external_server_id`
persistido por el colector. El parametro opcional `limit` acepta valores entre
`1` y `100`.

La capa historica propia expone:

- `/api/historical/weekly-top-kills`
- `/api/historical/weekly-leaderboard`
- `/api/historical/leaderboard`
- `/api/historical/recent-matches`
- `/api/historical/server-summary`
- `/api/historical/snapshots/server-summary`
- `/api/historical/snapshots/weekly-leaderboard`
- `/api/historical/snapshots/leaderboard`
- `/api/historical/snapshots/recent-matches`
- `/api/historical/player-profile`

Parametros opcionales:

- `limit` entre `1` y `100`
- `server` con slug historico como `comunidad-hispana-01`
- `player` en `/api/historical/player-profile` aceptando `stable_player_key`,
  `steam_id` o `source_player_id`

Ademas de los slugs fisicos de cada scoreboard, la capa historica acepta la
clave logica `all-servers` para devolver agregados globales sobre los tres
servidores de Comunidad Hispana sin tratarla como un origen CRCON real aparte.

La ventana temporal usa semana calendario UTC y solo considera partidas
cerradas con `ended_at` para no mezclar partidas aun en curso ni filas
historicas transitorias. El payload devuelve servidor, rango temporal,
jugador, kills semanales, posicion y numero de partidas consideradas.

`weekly-leaderboard` generaliza ese bloque para varias metricas semanales por
servidor usando el mismo filtro de partidas cerradas. Si la semana actual cae
entre lunes y miercoles UTC y todavia no acumula al menos `3` partidas
cerradas, el backend activa un fallback temporal a la semana cerrada anterior.
Metricas soportadas:

- `kills`
- `deaths`
- `support`
- `matches_over_100_kills`

El endpoint legacy `/api/historical/weekly-top-kills` se conserva como alias
compatible para la metrica `kills`.

`/api/historical/leaderboard` y `/api/historical/snapshots/leaderboard`
generalizan ese mismo contrato con `timeframe=weekly|monthly`. Para `monthly`,
la politica temporal usa el mes natural UTC en curso y hace fallback al mes
cerrado anterior solo cuando el mes actual todavia no tiene ningun cierre.
Ambas variantes exponen el rango real usado mediante `window_start`,
`window_end`, `window_kind`, `window_label` y `selection_reason`.

`recent-matches` devuelve cierres recientes por servidor con marcador, mapa y
conteo de jugadores. `server-summary` agrega volumen historico, jugadores
unicos, kills, mapas dominantes y rango temporal cubierto. `player-profile`
deja lista la base de consulta agregada por jugador para futuras vistas.

La familia `/api/historical/snapshots/*` lee directamente los archivos JSON
precalculados bajo `backend/data/snapshots/` y evita recalcular agregados
pesados en cada request. Estos endpoints devuelven payloads ligeros listos para
frontend con:

- `snapshot_status`
- `missing_reason`
- `request_path_policy`
- `generation_policy`
- `generated_at`
- `source_range_start`
- `source_range_end`
- `is_stale`
- `freshness`
- `found`
- `window_start`
- `window_end`
- `window_kind`
- `window_label`
- `uses_fallback`
- `selection_reason`
- `current_week_closed_matches`
- `previous_week_closed_matches`
- `sufficient_sample`

Si un snapshot todavia no existe en `backend/data/snapshots/`, la API responde
rapido con `found: false`, `snapshot_status: "missing"` y
`missing_reason: "snapshot-not-generated"`. La generacion y refresco de esos
artefactos debe ocurrir fuera del request path mediante `historical_ingestion`
o `historical_runner`; la lectura HTTP se mantiene como fast path de solo
lectura.

`/api/historical/snapshots/server-summary` devuelve `item` con el resumen del
servidor. `/api/historical/snapshots/weekly-leaderboard` devuelve `items` ya
precalculados para una metrica semanal y acepta `limit` para recortar el
payload ya persistido sin recalcularlo. `/api/historical/snapshots/recent-matches`
devuelve `items` de cierres recientes ya preparados y tambien acepta `limit`
para servir solo una parte del snapshot persistido.

La misma capa de snapshots guarda tambien `monthly-leaderboard` por servidor y
por agregado `all-servers`, con archivos como `monthly-kills.json` y
`monthly-support.json`.

Tambien persiste `monthly-mvp.json` por servidor y para `all-servers`, listo
para lectura rapida desde `/api/historical/monthly-mvp` y
`/api/historical/snapshots/monthly-mvp` sin recalculo pesado en request.

El backend incluye ademas el calculo interno de `monthly MVP V1` en
`app/monthly_mvp.py`, separado de los leaderboards mensuales simples por
metrica. Ese calculo:

- usa solo `kills`, `support`, `time_seconds`, `deaths` y `teamkills`
  persistidos
- recompone `KPM` y `KDA` desde totales mensuales
- aplica elegibilidad minima de `6` partidas cerradas y `6` horas
- soporta servidor individual y el agregado logico `all-servers`

En esta fase el ranking MVP queda listo para serializar en snapshots o payloads
sin reemplazar los leaderboards mensuales ya existentes por `kills`, `deaths`,
`support` y `matches_over_100_kills`.

## Ingesta historica CRCON

La ingesta historica no usa A2S ni scraping del HTML de `/games`. Consume la
capa JSON publica detectada en los scoreboards CRCON de Comunidad Hispana y
persiste el resultado en las tablas `historical_*`.

Fuentes configuradas:

- `https://scoreboard.comunidadhll.es`
- `https://scoreboard.comunidadhll.es:5443`
- `https://scoreboard.comunidadhll.es:3443`

Comandos manuales desde `backend/`:

```powershell
python -m app.historical_ingestion bootstrap
python -m app.historical_ingestion refresh
python -m app.historical_runner --interval 1800
```

Los mismos flujos desde Docker Compose:

```powershell
docker compose exec backend python -m app.historical_ingestion bootstrap
docker compose exec backend python -m app.historical_ingestion refresh
docker compose exec backend python -m app.historical_runner --interval 1800
```

Flags utiles:

- `--server comunidad-hispana-01` para limitar a un servidor
- `--server comunidad-hispana-03` para validar solo el tercer scoreboard historico
- `--max-pages 2` para validacion local acotada
- `--page-size 25` para ajustar paginacion
- `--start-page 4` para forzar una pagina concreta en bootstraps largos
- `--detail-workers 16` para paralelizar el detalle por partida

La ejecucion `bootstrap` recorre paginas historicas hasta agotar resultados.
La ejecucion `refresh` usa una ventana de solape sobre la ultima partida
persistida por servidor para releer solo paginas recientes y absorber updates
tardios sin reimportar todo el historico. Cuando una ejecucion termina
correctamente, tambien recompone los snapshots historicos precalculados para el
servidor afectado o para todos los servidores si la ingesta fue global.
Si la recomposicion se lanza para un servidor fisico concreto, el backend
rehace tambien el agregado logico `all-servers` para mantener `Todos`
alineado con `#01` y `#02` aunque `#03` siga sin bootstrap.

El comando devuelve ademas un resumen de cobertura persistida por servidor. Esto
ayuda a validar rapidamente cuantos matches reales quedaron importados, el rango
temporal cubierto y si la carga ya supera la ultima semana movil que usa la UI.
Ese resumen incluye tambien checkpoint y estado operativo de backfill por
servidor:

- `next_page`
- `last_completed_page`
- `discovered_total_matches`
- `discovered_total_pages`
- `archive_exhausted`
- `last_run`

Como la fuente CRCON publica expone un archivo muy profundo y puede devolver
errores `502` intermitentes bajo carga sostenida, el bootstrap completo debe
tratarse como una operacion reanudable. Flujo recomendado:

```powershell
python -m app.historical_ingestion bootstrap --detail-workers 16
python -m app.historical_ingestion bootstrap --detail-workers 16
```

La segunda invocacion reutiliza automaticamente el checkpoint persistido en
`historical_backfill_progress` y continua desde la siguiente pagina pendiente si
la sesion anterior se corta por tiempo disponible o por inestabilidad puntual
del origen. `--start-page` queda como override manual cuando se quiera
reprocesar o inspeccionar un tramo concreto.

Los reintentos de cada request JSON pueden ajustarse sin tocar codigo con:

- `HLL_HISTORICAL_CRCON_REQUEST_RETRIES`
- `HLL_HISTORICAL_CRCON_RETRY_DELAY_SECONDS`

El runner `python -m app.historical_runner` deja ese refresh incremental listo
para ejecucion local repetida sin depender de infraestructura externa y
mantiene calientes los snapshots historicos mas visibles tras cada refresh
correcto. Por defecto:

- refresca cada `900` segundos
- prewarmea en cada ciclo:
  - `server-summary` para `comunidad-hispana-01`, `comunidad-hispana-02`, `comunidad-hispana-03` y `all-servers`
  - `weekly-leaderboard` de la metrica por defecto `kills` para esos mismos alcances
  - `monthly-leaderboard` de la metrica por defecto `kills` para esos mismos alcances
  - `recent-matches` para esos mismos alcances
- recompone la matriz completa de snapshots cada `4` ciclos para mantener el resto de metricas al dia sin penalizar todos los refresh
- reintenta hasta `2` veces tras un fallo
- espera `30` segundos entre reintentos
- reutiliza el registro de `historical_ingestion_runs` para dejar trazabilidad
  de ultimo refresh, resultado y errores basicos
- persiste por servidor:
  - `server-summary`
  - `weekly-leaderboard` para `kills`, `deaths`, `support` y `matches_over_100_kills`
  - `monthly-leaderboard` para `kills`, `deaths`, `support` y `matches_over_100_kills`
  - `recent-matches`

Flags utiles del runner:

- `--server comunidad-hispana-01` para limitar a un servidor
- `--interval 900` para fijar la frecuencia recomendada de snapshots
- `--hourly` para fijar directamente un ciclo horario de `3600` segundos
- `--retries 1` para reducir reintentos
- `--retry-delay 10` para bajar la espera entre fallos
- `--max-runs 1` para una validacion puntual sin bucle indefinido

Para dejar automatizado el refresh historico horario de los tres servidores del
proyecto en local, el comando recomendado es:

```powershell
python -m app.historical_runner --hourly
```

Sin `--server`, ese runner refresca:

- `comunidad-hispana-01`
- `comunidad-hispana-02`
- `comunidad-hispana-03`

Despues de cada refresh correcto, recompone snapshots para los servidores
afectados y vuelve a alinear el agregado `all-servers`.

Para regenerar snapshots de forma puntual dentro del contenedor sin dejar un
bucle permanente, la validacion operativa minima es:

```powershell
docker compose exec backend python -m app.historical_runner --max-runs 1
```

Operativa local minima:

1. Desde `backend/`, arrancar la API con `python -m app.main`.
2. En otra terminal, dejar corriendo `python -m app.historical_runner --hourly`.
3. Verificar el proceso revisando la salida del runner: al arrancar imprime un
   bloque JSON con `event: "historical-refresh-loop-started"`, `server_scope`
   y `snapshot_scope`.
4. Confirmar que los snapshots siguen actualizandose revisando `generated_at`
   en archivos bajo `backend/data/snapshots/`, por ejemplo:
   - `backend/data/snapshots/comunidad-hispana-01/server-summary.json`
   - `backend/data/snapshots/comunidad-hispana-02/recent-matches.json`
   - `backend/data/snapshots/comunidad-hispana-03/weekly-kills.json`
   - `backend/data/snapshots/all-servers/monthly-kills.json`

Operativa minima con Docker Compose:

```powershell
docker compose up -d backend historical-runner frontend
```

El servicio `historical-runner` usa el mismo volumen persistente `./backend/data`
y ejecuta `python -m app.historical_runner --hourly` como bucle operativo
dedicado, sin mezclar el scheduler con el proceso HTTP principal.

Comprobaciones utiles con Compose:

- `docker compose ps historical-runner`
- `docker compose logs -f historical-runner`
- `docker compose exec backend python -m app.historical_runner --max-runs 1`

Variables utiles del runner:

- `HLL_HISTORICAL_SNAPSHOT_REFRESH_INTERVAL_SECONDS`
- `HLL_HISTORICAL_FULL_SNAPSHOT_EVERY_RUNS`
- `HLL_HISTORICAL_REFRESH_MAX_RETRIES`
- `HLL_HISTORICAL_REFRESH_RETRY_DELAY_SECONDS`
- `HLL_HISTORICAL_WEEKLY_FALLBACK_MIN_MATCHES`
- `HLL_HISTORICAL_WEEKLY_FALLBACK_MAX_WEEKDAY`

Al inicializar la persistencia local, el backend normaliza tambien la identidad
historica ya guardada:

- prioriza `steaminfo.profile.steamid` cuando existe
- si `player_id` ya parece un SteamID real, lo promueve igualmente a `steam:*`
- si no hay SteamID, usa `player_id` como clave `crcon-player:*`
- deja `steaminfo.id` como ultimo fallback cuando faltan las claves anteriores

La misma inicializacion fusiona filas duplicadas si una partida abierta quedo
guardada con un id sintetico y mas tarde CRCON la expone con un id numerico
definitivo. Esto evita que el ranking semanal cuente dos veces la misma sesion.

## CORS local minimo

El backend responde con `Access-Control-Allow-Origin` solo si la peticion llega
desde uno de los origenes permitidos en desarrollo local. No se habilita un
comodin global ni configuracion de produccion en esta fase.

La allowlist por defecto cubre `file://` mediante el origen `null` y los flujos
locales mas comunes del proyecto:

- `http://127.0.0.1:5500`
- `http://localhost:5500`
- `http://127.0.0.1:8080`
- `http://localhost:8080`

Las respuestas `GET` y `OPTIONS` incluyen `Access-Control-Allow-Origin` cuando
el origen esta permitido, suficiente para probar la landing contra la API local
sin tocar endpoints ni payloads.

Esta separacion mantiene el backend simple y deja una base clara para futuras tasks sin introducir integraciones reales todavia.

## Alcance

Esta fase no implementa:

- logica real de Discord
- integraciones con servidores de juego
- base de datos
- autenticacion
- dependencias nuevas

La idea es dejar un esqueleto funcional, pequeno y coherente con `docs/frontend-backend-contract.md`.
