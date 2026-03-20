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
- `HLL_HISTORICAL_CRCON_PAGE_SIZE`
- `HLL_HISTORICAL_CRCON_TIMEOUT_SECONDS`

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

## Criterio de estructura

- `__init__.py` declara el paquete `app` y reexporta las utilidades publicas
  minimas del bootstrap.
- `collector.py` define el flujo minimo de captura para desarrollo usando una
  fuente controlada.
- `a2s_client.py` encapsula una consulta minima A2S_INFO por UDP para probar
  servidores reales sin acoplar todavia el backend a una fuente mas compleja.
- `config.py` centraliza host, puerto y allowlist minima de origenes locales.
- `historical_ingestion.py` consulta la capa JSON publica de CRCON para bootstrap y refresh incremental.
- `historical_models.py` fija las entidades historicas minimas del dominio.
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

Variable opcional:

- `HLL_BACKEND_STORAGE_PATH`
- `HLL_BACKEND_A2S_TARGETS`

La base logica sigue documentada en
`docs/stats-database-schema-foundation.md` para snapshots live y en
`docs/historical-domain-model.md` para el historico CRCON. Esta implementacion
no introduce ORM, migraciones ni una decision de almacenamiento productivo.

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

La primera consulta agregada sobre historico CRCON es:

- `/api/historical/weekly-top-kills`

Parametros opcionales:

- `limit` entre `1` y `100`
- `server` con slug historico como `comunidad-hispana-01`

La ventana temporal es siempre la ultima semana movil respecto al momento de la
request y solo considera partidas cerradas con `ended_at` para no mezclar
partidas aun en curso ni filas historicas transitorias. El payload devuelve
servidor, rango temporal, jugador, kills semanales, posicion y numero de
partidas consideradas.

## Ingesta historica CRCON

La ingesta historica no usa A2S ni scraping del HTML de `/games`. Consume la
capa JSON publica detectada en los scoreboards CRCON de Comunidad Hispana y
persiste el resultado en las tablas `historical_*`.

Fuentes configuradas:

- `https://scoreboard.comunidadhll.es`
- `https://scoreboard.comunidadhll.es:5443`

Comandos manuales desde `backend/`:

```powershell
python -m app.historical_ingestion bootstrap
python -m app.historical_ingestion refresh
```

Flags utiles:

- `--server comunidad-hispana-01` para limitar a un servidor
- `--max-pages 2` para validacion local acotada
- `--page-size 25` para ajustar paginacion

La ejecucion `bootstrap` recorre paginas historicas hasta agotar resultados.
La ejecucion `refresh` usa una ventana de solape sobre la ultima partida
persistida por servidor para releer solo paginas recientes y absorber updates
tardios sin reimportar todo el historico.

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
