# RCON Historical Ingestion Design

## Validation Date

- 2026-03-25

## Scope

Definir si la repo puede soportar historico por RCON con la implementacion
actual y, si no puede hacerlo de forma retroactiva, dejar una arquitectura
minima y defendible para una primera captura prospectiva.

Este documento se limita a la evidencia local de la repo. No asume comandos
RCON no integrados ni capacidades externas no demostradas aqui.

## Evidence Reviewed

- `backend/app/data_sources.py`
- `backend/app/providers/rcon_provider.py`
- `backend/app/rcon_client.py`
- `backend/app/historical_ingestion.py`
- `backend/app/historical_storage.py`
- `backend/app/player_event_worker.py`
- `backend/app/player_event_storage.py`
- `backend/README.md`
- `docs/rcon-data-capability-audit.md`
- `docs/crcon-advanced-metrics-origin-audit.md`

## Current State In Code

La separacion entre live e historico ya existe en la seleccion de proveedores:

- `get_live_data_source()` puede resolver `rcon`
- `get_historical_data_source()` puede resolver `rcon`, pero hoy devuelve un
  placeholder que falla

La implementacion RCON real disponible en la repo es minima y esta concentrada
en `backend/app/rcon_client.py`.

Comandos soportados hoy en codigo:

- `ServerConnect`
- `Login`
- `GetServerInformation`

No hay evidencia local de otros comandos ya integrados para:

- scoreboards por jugador
- detalle de partida cerrada
- eventos kill por kill
- logs tacticos
- historico retroactivo de matches cerrados

## Payload Available Today

La salida efectiva que la repo consume desde RCON hoy es la normalizada por
`query_live_server_state()`:

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

Inferencia basada en `rcon_client.py`:

- el payload remoto de `GetServerInformation` contiene como minimo
  `serverName`, `playerCount`, `maxPlayerCount` y `mapId` o `mapName`
- la repo no persiste hoy el payload crudo ni deriva entidades historicas de
  match o jugador a partir de RCON

## Operational Frequency Assessment

Inferencia basada en la implementacion actual:

- cada pasada por target abre una conexion TCP
- realiza handshake `ServerConnect`
- autentica con `Login`
- ejecuta una consulta `GetServerInformation`

Con este alcance, una frecuencia inicial razonable para captura prospectiva es:

- cada `60` a `300` segundos para operativa normal
- `30` segundos solo como validacion o monitoreo puntual

No hay evidencia en la repo para defender un polling mas agresivo de forma
sostenida ni para asegurar que aportaria historico competitivo util.

## Viability Decision

Conclusion principal:

- no viable hoy para historico real retroactivo de partidas cerradas con el
  cliente actual
- viable solo para captura prospectiva

Motivos:

- el cliente actual solo consulta estado live puntual
- no existe base local para reconstruir partidas ya cerradas
- no existe feed raw de eventos ni logs persistidos
- `RconHistoricalDataSource` sigue siendo un placeholder y no puede sustituir a
  `public-scoreboard`

Conclusion secundaria:

- una capa historica parcial por RCON si es defendible, pero solo si se define
  como captura prospectiva de muestras live y no como backfill de matches ya
  perdidos

## Recommended Minimal Architecture

### Storage

Separar completamente la persistencia prospectiva RCON del historico actual
`historical_*`.

Tablas minimas recomendadas:

- `rcon_historical_targets`
  - identidad estable del target configurado
  - ultimo estado conocido de configuracion
- `rcon_historical_capture_runs`
  - una fila por ejecucion del worker
  - estado, inicio, fin, errores y target scope
- `rcon_historical_samples`
  - una fila por muestra y target
  - `captured_at`
  - identidad de target
  - payload normalizado
  - payload crudo opcional de `GetServerInformation`

Si se quiere checkpoint explicito desde la primera version:

- `rcon_historical_checkpoints`
  - `target_key`
  - `last_successful_capture_at`
  - `last_sample_at`
  - `last_error`

### Workers

Worker dedicado fuera del request path HTTP:

- `python -m app.rcon_historical_worker capture`
- `python -m app.rcon_historical_worker loop --interval 120`

Responsabilidades:

- cargar `HLL_BACKEND_RCON_TARGETS`
- consultar cada target con el cliente RCON actual
- persistir run tracking
- persistir muestras idempotentes por target y timestamp
- actualizar checkpoints

### Checkpoints

Como no existe backfill retroactivo real, el checkpoint no debe modelarse como
pagina o offset de archivo historico. Debe modelarse como tiempo de captura.

Checkpoint minimo defendible:

- ultimo `captured_at` exitoso por target
- ultimo error por target
- ultimo run exitoso global

### Compatibility With `public-scoreboard`

Politica recomendada:

- `public-scoreboard` sigue siendo la fuente historica principal para:
  - leaderboards semanales y mensuales
  - MVP V1 y V2
  - recent matches cerrados
  - player events derivados de la capa publica actual
- RCON prospectivo convive en una linea paralela para:
  - cobertura temporal hacia delante
  - disponibilidad del servidor
  - actividad reciente
  - trazabilidad de frescura por target

## Recommended Degradation Policy

Si en una fase posterior se habilita `HLL_BACKEND_HISTORICAL_DATA_SOURCE=rcon`,
la degradacion minima correcta es esta:

- solo exponer endpoints o bloques claramente soportados por la persistencia
  prospectiva RCON
- no simular leaderboards completos cuando no existan
- devolver metadata de cobertura y frescura antes que rankings vacios

Contratos defendibles en una primera lectura minima:

- resumen de cobertura por servidor
- actividad reciente por servidor
- estado de frescura
- rango temporal disponible

Contratos que deben seguir dependiendo de `public-scoreboard` hasta nueva
evidencia:

- weekly leaderboards completos
- monthly leaderboards completos
- monthly MVP V1
- monthly MVP V2
- player profiles competitivos
- equivalencia completa con `historico.html`

## Recommended Phases

### Phase 1: Prospective Capture

Objetivo:

- empezar a guardar muestras live RCON hacia delante

Incluye:

- storage separado
- worker dedicado
- run tracking
- checkpoints temporales
- ejecucion manual y en loop

No incluye:

- backfill retroactivo
- paridad con `public-scoreboard`
- endpoints competitivos nuevos

### Phase 2: Minimal Operational Read Model

Objetivo:

- leer la persistencia prospectiva RCON sin consultar RCON on-demand en HTTP

Incluye:

- resumen por servidor
- ultima muestra
- cobertura disponible
- actividad reciente

### Phase 3: Competitive Metrics Only If Signal Improves

Objetivo:

- evaluar si aparecen comandos, eventos o logs suficientes para enriquecer la
  capa historica RCON

Solo deberia abrirse si existe evidencia real de:

- eventos reutilizables
- scoreboards historificables
- granularidad por jugador o por encounter

## Final Recommendation

La decision tecnica correcta para esta repo es:

- mantener `public-scoreboard` como fuente historica por defecto
- tratar RCON historico como una linea prospectiva separada
- no prometer reconstruccion retroactiva con el cliente actual
- abrir implementacion incremental en dos tasks:
  - captura prospectiva persistida
  - lectura minima sobre persistencia local
