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

SelecciÃ³n de proveedor por entorno hoy:

- desarrollo:
  - `HLL_BACKEND_LIVE_DATA_SOURCE=a2s`
  - `HLL_BACKEND_HISTORICAL_DATA_SOURCE=public-scoreboard`
- producciÃ³n realista en esta fase:
  - `HLL_BACKEND_LIVE_DATA_SOURCE=rcon`
  - `HLL_BACKEND_HISTORICAL_DATA_SOURCE=public-scoreboard`

Esto refleja el estado real de la repo: el proveedor RCON ya existe para el
estado live de `/api/servers`, pero el histÃ³rico sigue dependiendo del
scoreboard pÃºblico porque no hay todavÃ­a una canalizaciÃ³n persistente basada
en eventos/logs RCON.

Primer arranque:

```powershell
docker compose up --build
```

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
$env:HLL_BACKEND_HISTORICAL_DATA_SOURCE='public-scoreboard'
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
- mantener `HLL_BACKEND_HISTORICAL_DATA_SOURCE=public-scoreboard` hasta tener
  una ingesta historica RCON realmente persistida

## Operaciones historicas con Docker

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

Automatizacion horaria recomendada:

```powershell
docker compose up -d backend historical-runner frontend
```

`historical-runner` es un servicio Compose separado que ejecuta
`python -m app.historical_runner --hourly`, refresca el historico de
`comunidad-hispana-01`, `comunidad-hispana-02` y `comunidad-hispana-03`, y
regenera snapshots al terminar cada refresh correcto sin acoplar ese bucle al
proceso HTTP del backend.

Verificacion minima:

- `docker compose ps historical-runner`
- `docker compose logs -f historical-runner`
- revisar `generated_at` en `backend/data/snapshots/`

Si se prefiere operar fuera de Docker, el backend sigue pudiendo arrancar localmente con `python -m app.main` desde `backend/`.

## Evolucion prevista

La capa inspirada en `ai-dev-platform-template` ya esta integrada y adaptada al contexto real de HLL Vietnam. Las siguientes iteraciones deben centrarse en usarla para planificar y ejecutar tasks reales del producto sin ampliar alcance fuera de ese flujo.
