# HLL Vietnam

HLL Vietnam es la base inicial del repositorio para una futura web de comunidad enfocada en la comunidad hispana de Discord del juego HLL Vietnam.

En esta primera fase, el proyecto se centra en una landing sencilla, limpia y profesional que sirva como punto de entrada para la comunidad. La implementacion actual utiliza HTML, CSS y JavaScript sin frameworks pesados para mantener una base facil de mantener y ampliar.

## Estado actual

- Landing inicial de comunidad.
- Estructura de repositorio preparada para crecer.
- Carpeta de backend reservada para una futura implementacion en Python.
- Carpeta `ai/` ya integrada como capa operativa para orquestacion por tasks y trabajo con Codex.

## Estructura del repositorio

```text
/
|-- README.md
|-- .gitignore
|-- AGENTS.md
|-- docs/
|   |-- project-overview.md
|   |-- roadmap.md
|   `-- decisions.md
|-- frontend/
|   |-- index.html
|   |-- historico.html
|   |-- Dockerfile
|   |-- .dockerignore
|   `-- assets/
|       |-- css/
|       |-- js/
|       `-- img/
|-- backend/
|   |-- README.md
|   |-- requirements.txt
|   |-- Dockerfile
|   |-- .dockerignore
|   |-- .env.example
|   `-- app/
|       `-- __init__.py
|-- ai/
|   |-- README.md
|   |-- architecture-index.md
|   |-- repo-context.md
|   |-- system-metrics.md
|   |-- task-template.md
|   |-- prompts/
|   |   `-- plan-feature.md
|   |-- orchestrator/
|   |   `-- README.md
|   `-- tasks/
|       |-- pending/
|       |-- in-progress/
|       `-- done/
|-- docker-compose.yml
`-- scripts/
```

## Backend futuro

El backend principal esta previsto en Python, pero en esta fase no se introduce infraestructura final de produccion. La base actual prioriza un bootstrap pequeno, una persistencia local clara y una evolucion controlada.

## Como abrir el frontend localmente

1. Ve a la carpeta `frontend/`.
2. Abre `index.html` directamente en el navegador.

No hace falta servidor para esta primera version.

## Ejecucion con Docker

El repositorio ya incluye:

- `backend/Dockerfile`
- `frontend/Dockerfile`
- `docker-compose.yml`
- `backend/.env.example`

Seleccion de proveedor por entorno hoy:

- desarrollo:
  - `HLL_BACKEND_LIVE_DATA_SOURCE=rcon`
  - `HLL_BACKEND_HISTORICAL_DATA_SOURCE=rcon`
- produccion realista en esta fase:
  - `HLL_BACKEND_LIVE_DATA_SOURCE=rcon`
  - `HLL_BACKEND_HISTORICAL_DATA_SOURCE=rcon`

Esto refleja la politica operativa actual: RCON es la fuente primaria para
live e historico. El scoreboard publico queda como fallback historico cuando
RCON falla, no cubre una operacion concreta o aun no tiene cobertura suficiente.

Modo normal recomendado:

- levantar solo `backend` + `frontend`
- mantener `historical-runner` y `rcon-historical-worker` como servicios
  avanzados bajo demanda
- mantener Comunidad Hispana #03 fuera de los targets RCON por defecto
- dejar Elo/MMR y la materializacion historica compleja en pausa operativa
  hasta una reintroduccion explicita

Primer arranque:

```powershell
docker compose up --build
```

Con la configuracion actual, ese comando levanta solo `backend` y `frontend`.
Los workers historicos estan en el perfil Compose `advanced` y no forman parte
del arranque normal.

Accesos locales esperados:

- frontend: `http://localhost:8080`
- backend: `http://localhost:8000`
- health del backend: `http://localhost:8000/health`

Persistencia:

- el SQLite historico se conserva en `backend/data/hll_vietnam_dev.sqlite3`
- los snapshots JSON se conservan en `backend/data/snapshots/`
- `docker-compose.yml` monta `./backend/data` dentro del contenedor en `/app/data`

Reinicio normal:

```powershell
docker compose up -d
```

Parada:

```powershell
docker compose down
```

Recreacion de imagenes tras cambios:

```powershell
docker compose up --build
```

## Runbook de proveedores

Verificacion minima del proveedor activo:

```powershell
Invoke-WebRequest http://localhost:8000/health | Select-Object -Expand Content
```

La respuesta incluye `live_data_source` y `historical_data_source`.

Modo desarrollo recomendado:

```powershell
docker compose up --build
```

Modo live con RCON en Docker Compose:

```powershell
$env:HLL_BACKEND_LIVE_DATA_SOURCE='rcon'
$env:HLL_BACKEND_HISTORICAL_DATA_SOURCE='rcon'
$env:HLL_BACKEND_RCON_TARGETS='[
  {
    "name": "Comunidad Hispana #01",
    "host": "203.0.113.10",
    "port": 28015,
    "password": "replace-me",
    "external_server_id": "comunidad-hispana-01",
    "region": "ES",
    "game_port": 7777,
    "query_port": 7778
  }
]'
docker compose up -d backend frontend
```

Buenas practicas:

- no versionar credenciales reales en `backend/.env.example`
- preferir exportarlas como variables de entorno del host o del secreto del
  despliegue
- mantener `HLL_BACKEND_HISTORICAL_DATA_SOURCE=rcon` como valor normal y usar
  `public-scoreboard` solo como fallback historico controlado
- no reintroducir Comunidad Hispana #03 en `HLL_BACKEND_RCON_TARGETS` salvo que
  una task nueva valide su disponibilidad

## Operaciones historicas avanzadas con Docker

Estas operaciones quedan disponibles para uso explicito, pero no son parte del
arranque recomendado. La ruta normal de despliegue es `backend` + `frontend`.
El codigo, las migraciones, los snapshots historicos y Elo/MMR se conservan en
la repo, pero Elo/MMR y la materializacion historica compleja quedan pausados
operativamente en esta fase.

Refresh historico puntual dentro del contenedor backend:

```powershell
docker compose exec backend python -m app.historical_ingestion refresh
```

Bootstrap o backfill historico:

```powershell
docker compose exec backend python -m app.historical_ingestion bootstrap
```

Regeneracion puntual de snapshots mediante refresh controlado:

```powershell
docker compose exec backend python -m app.historical_runner --max-runs 1
```

Automatizacion horaria avanzada:

```powershell
docker compose --profile advanced up -d backend historical-runner frontend
```

`historical-runner` es un servicio Compose separado que ejecuta
`python -m app.historical_runner --hourly`. Sigue disponible para tareas
historicas explicitas, pero no se recomienda como requisito normal de
despliegue. Los targets RCON por defecto solo incluyen `comunidad-hispana-01`
y `comunidad-hispana-02`; `comunidad-hispana-03` queda deshabilitado en la
configuracion por defecto porque ya no es una fuente operativa vigente.

Verificacion minima:

- `docker compose ps historical-runner`
- `docker compose logs -f historical-runner`
- revisar `generated_at` en `backend/data/snapshots/`

## Arquitectura historica RCON-first

La linea historica actual usa RCON como fuente primaria. El flujo previsto es:

- captura de sesiones RCON para cobertura, frescura y ventanas competitivas
- ingesta de AdminLog mediante `app.rcon_admin_log_ingestion`
- parsing de eventos AdminLog hacia eventos normalizados
- almacenamiento en tablas `rcon_admin_log_*` y `rcon_historical_*`
- materializacion de partidas cerradas y estadisticas de jugador desde eventos RCON
- enriquecimiento opcional con snapshots de perfil de jugador, sin tratarlos
  como hechos autoritativos de una partida

El scoreboard publico queda limitado a enriquecimiento, links confiables o
fallback historico cuando RCON falla, no tiene cobertura suficiente o no cubre
una operacion concreta. Elo/MMR sigue pausado y Comunidad Hispana #03 permanece
fuera de los targets RCON por defecto.

Comandos manuales RCON dentro del contenedor backend:

```powershell
docker compose exec backend python -m app.rcon_admin_log_ingestion --minutes 1440
docker compose exec backend python -m app.rcon_historical_worker capture
```

Si se prefiere operar fuera de Docker, el backend sigue pudiendo arrancar localmente con `python -m app.main` desde `backend/`.

## Evolucion prevista

La capa inspirada en `ai-dev-platform-template` ya esta integrada y adaptada al contexto real de HLL Vietnam. Las siguientes iteraciones deben centrarse en usarla para planificar y ejecutar tasks reales del producto sin ampliar alcance fuera de ese flujo.
