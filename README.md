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
