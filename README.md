# HLL Vietnam

HLL Vietnam es la base inicial del repositorio para una futura web de comunidad enfocada en la comunidad hispana de Discord del juego HLL Vietnam.

En esta primera fase, el proyecto se centra en una landing sencilla, limpia y profesional que sirva como punto de entrada para la comunidad. La implementación actual utiliza HTML, CSS y JavaScript sin frameworks pesados para mantener una base fácil de mantener y ampliar.

## Estado actual

- Landing inicial de comunidad.
- Estructura de repositorio preparada para crecer.
- Carpeta de backend reservada para una futura implementación en Python.
- Carpeta `ai/` ya integrada como capa operativa para orquestación por tasks y trabajo con Codex.

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
|   `-- assets/
|       |-- css/
|       |   `-- styles.css
|       |-- js/
|       |   `-- main.js
|       `-- img/
|           `-- .gitkeep
|-- backend/
|   |-- README.md
|   |-- requirements.txt
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
|       |   `-- .gitkeep
|       |-- in-progress/
|       |   `-- .gitkeep
|       `-- done/
|           `-- .gitkeep
`-- scripts/
    |-- codex-runner.ps1
    `-- run-integration-tests.ps1
```

## Backend futuro

El backend principal está previsto en Python, pero en esta fase no se incluye lógica funcional ni dependencias de servidor. La estructura queda preparada para incorporar esa capa más adelante sin reorganizar el repositorio.

## Cómo abrir el frontend localmente

1. Ve a la carpeta `frontend/`.
2. Abre `index.html` directamente en el navegador.

No hace falta servidor para esta primera versión.

## Evolución prevista

La capa inspirada en `ai-dev-platform-template` ya está integrada y adaptada al contexto real de HLL Vietnam. Las siguientes iteraciones deben centrarse en usarla para planificar y ejecutar tasks reales del producto sin ampliar alcance fuera de ese flujo.
