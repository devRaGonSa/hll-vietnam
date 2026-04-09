# Technical Decisions

## Decision 001: frontend simple HTML/CSS/JS

Se adopta una base estatica con HTML, CSS y JavaScript puro para priorizar simplicidad, velocidad de arranque y compatibilidad total al abrir el frontend directamente en navegador.

## Decision 002: backend previsto en Python

La estructura del repositorio reserva desde el inicio una carpeta de backend porque la implementacion futura se realizara en Python.

## Decision 003: estructura preparada para orquestacion por agentes

Se incluye una carpeta `ai/` y un documento `AGENTS.md` para facilitar una futura organizacion del trabajo por roles, tareas y orquestacion.

## Decision 004: branding militar Vietnam

La direccion visual inicial se alinea con una estetica sobria, tactica y militar inspirada en el contexto Vietnam para mantener coherencia tematica desde la primera iteracion.

## Decision 005: AI Development Platform integrada de forma adaptada

Se integra una capa de orquestacion por tasks inspirada en la plantilla de AI Development Platform, pero adaptada al contexto real de HLL Vietnam y sin arrastrar supuestos genericos de otros stacks. La plataforma se usa como soporte operativo del repositorio, no como funcionalidad del producto.

## Decision 006: contrato API pequeno antes de integraciones reales

Antes de implementar endpoints de comunidad o integraciones externas, se fija un contrato JSON minimo entre frontend y backend para evitar que la landing y el backend evolucionen con supuestos incompatibles.

La unica ruta implementada hoy es `GET /health`. Las rutas `/api/community`, `/api/trailer`, `/api/discord` y `/api/servers` quedan definidas como contrato previsto o placeholder en `docs/frontend-backend-contract.md`, manteniendo el backend en Python y sin introducir todavia Discord real, servidores reales ni base de datos.

## Decision 007: estrategia por fases para Discord y servidores

Los datos de Discord y de servidores de juego se incorporaran por fases para evitar dependencias prematuras de credenciales, APIs externas o consultas de red todavia no validadas.

La fase inicial debe usar datos manuales o placeholder controlados por el backend para mantener estable el contrato del frontend. Una fase intermedia podra anadir una integracion limitada con fuentes publicas o consultas tecnicas de bajo riesgo. Solo una fase posterior evaluara integraciones mas reales, siempre que queden claras las restricciones de seguridad, disponibilidad, latencia y mantenimiento.

La estrategia detallada de bloques de datos, fuentes posibles, riesgos y orden recomendado de implementacion queda documentada en `docs/discord-and-server-data-plan.md`.

## Decision 008: consumo frontend progresivo con fallback estatico

El frontend no debe depender de datos dinamicos para renderizar la landing base mientras el proyecto siga en fase fundacional.

Cuando se incorporen endpoints del backend, el consumo debe hacerse con `fetch` y JavaScript simple, priorizando bloques independientes y manteniendo contenido estatico o placeholders visuales si falla una llamada. `GET /health` queda reservado para comprobaciones tecnicas y no debe bloquear el render principal.

La estrategia detallada de prioridades de endpoints, estados de carga, errores y orden de migracion queda en `docs/frontend-data-consumption-plan.md`.

## Decision 009: servidores actuales de HLL como referencia provisional

Mientras no existan datos reales o representativos de HLL Vietnam, la web puede
mostrar un bloque provisional con servidores actuales de Hell Let Loose siempre
que quede claramente etiquetado como referencia temporal.

La primera version de ese bloque debe salir de un payload controlado del backend
Python, no de una integracion directa desde frontend ni de scraping prematuro.
Esto permite fijar campos utiles, preservar el tono del producto y evitar que la
landing dependa de una fuente externa aun no validada.

La estrategia de campos, riesgos, fases y sustitucion futura queda documentada
en `docs/current-hll-servers-source-plan.md`.

## Decision 010: ingesta por snapshots y adaptadores desacoplados

La evolucion desde payloads placeholder hacia datos mas realistas debe hacerse
con una arquitectura de snapshots de servidor, no conectando el frontend a una
fuente externa ni acoplando el backend a una integracion unica desde el inicio.

La unidad tecnica base sera un snapshot con `captured_at` y campos normalizados
como estado, jugadores, capacidad y mapa actual cuando exista. La lectura de
fuente, la normalizacion y la produccion del snapshot deben quedar separadas
para poder sustituir mocks por una fuente publica o consulta tecnica posterior
sin romper el contrato interno.

La estrategia detallada de fuentes, riesgos, fases y limites queda documentada
en `docs/current-hll-data-ingestion-plan.md`.

## Decision 011: modelo de almacenamiento logico antes de fijar tecnologia

Antes de introducir una base de datos concreta, el proyecto debe fijar un
modelo logico minimo para identidad de servidores y snapshots historicos.

La base inicial se apoya en entidades genericas como `game_sources`, `servers`
y `server_snapshots`. Las metricas iniciales deben derivarse primero de esos
snapshots en vez de materializar agregados prematuros. Esto mantiene el diseno
reutilizable para HLL actual y para futuras fuentes mas cercanas a HLL Vietnam.

El modelo base y las preguntas abiertas quedan documentados en
`docs/stats-database-schema-foundation.md`.

## Decision 012: historico de partidas desde CRCON scoreboard JSON

El historico reutilizable para estadisticas por partida y por jugador debe
salir de la capa JSON publica expuesta por los scoreboards CRCON de la
comunidad, no de A2S ni del HTML renderizado de `/games`.

La discovery tecnica confirma que ambos scoreboards sirven una SPA cuya fuente
real de datos usa `baseURL: "/api"` y endpoints como
`/get_scoreboard_maps` y `/get_map_scoreboard`. Esa capa permite obtener listas
de partidas, detalle por `map_id` y metricas por jugador suficientes para una
futura agregacion semanal por servidor.

A2S se mantiene como fuente de estado actual de servidores. El historico de
partidas y rankings debe construirse en una linea separada basada en CRCON. La
discovery detallada queda en `docs/historical-crcon-source-discovery.md`.

## Decision 013: persistencia historica local separada del flujo live

El backend mantiene el estado live de servidores y el historico CRCON en el
mismo SQLite local de desarrollo para no introducir infraestructura prematura,
pero ambas lineas quedan separadas por tablas y contratos distintos.

El flujo live sigue usando `server_snapshots` via A2S. El flujo historico usa
tablas `historical_*` para:

- servidores historicos configurados
- partidas
- mapas
- jugadores
- estadisticas por jugador y partida
- ejecuciones de ingesta

Las claves estables son:

- servidor: `historical_servers.slug`
- partida: `(historical_server_id, external_match_id)`
- jugador: `stable_player_key`
- estadistica por partida: `(historical_match_id, historical_player_id)`

Esto permite bootstrap, refresco incremental e idempotencia sin mezclar
semanticas de estado actual con historico persistido. El modelo detallado queda
en `docs/historical-domain-model.md`.

## Decision 014: PostgreSQL como destino primario del backend y cutover por fases

La persistencia SQLite local y los snapshots JSON en filesystem dejan de ser el
destino objetivo de largo plazo para los datos de producto del backend.

El estado de destino aprobado para la migracion `TASK-131` a `TASK-138` fija:

- PostgreSQL como primary durable store
- tablas relacionales PostgreSQL para live snapshots, historico base, RCON,
  player events y Elo/MMR
- fast-read snapshots persistidos en PostgreSQL mediante tablas explicitas y
  `JSONB` o una hibridacion estrecha y justificada
- rechazo explicito de vistas SQL simples como solucion universal de snapshot
- sustitucion de locks por fichero y supuestos WAL/busy-timeout de SQLite por
  coordinacion compatible con PostgreSQL

La migracion debe hacerse por fases, con mixed mode solo como frontera
transicional de backfill y validacion. `.sqlite3`, `/app/data/snapshots` y los
file locks no pueden sobrevivir como dependencias runtime primarias una vez
completado el cutover final. La arquitectura y el orden de dependencias quedan
definidos en `docs/postgresql-target-architecture.md`.

## Decision 015: backfill directo desde SQLite y regeneracion de snapshots desde PostgreSQL

El cierre operativo de la migracion a PostgreSQL se hace con una estrategia
hibrida y acotada:

- los datos relacionales legacy se copian directamente desde el SQLite
  existente hacia PostgreSQL
- los snapshots JSON historicos no se promueven como nueva fuente de verdad:
  se regeneran desde PostgreSQL despues del backfill relacional
- `backend/data/` y `/app/data` pasan a ser superficies auxiliares de archivo,
  export o rollback temporal, no almacenamiento primario del producto

Esto evita conservar dependencias runtime sobre SQLite, WAL, `busy_timeout` o
snapshots JSON en filesystem una vez firmado el cutover. El runbook completo de
backfill, validacion, orden de cutover y limites de rollback queda en
`docs/postgresql-cutover-runbook.md`.

La secuencia operativa validada para el cierre real del cutover es:

- `python scripts/postgresql-backfill.py plan`
- `python scripts/postgresql-backfill.py execute --truncate-target-first`
- `python scripts/postgresql-backfill.py validate`

El backfill aprobado queda endurecido con:

- batches de insercion en PostgreSQL
- commits por tabla
- sesion `UTF8` para datos Unicode legacy
- manifest exacto de la corrida `execute` persistido en PostgreSQL para validar
  tablas grandes sin depender de un nuevo `COUNT(*)` completo sobre todos los
  conjuntos multimillonarios
