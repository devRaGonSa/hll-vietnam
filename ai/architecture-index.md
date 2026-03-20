# Architecture Index

This file gives AI agents a fast overview of HLL Vietnam before they inspect the repository in detail.

## Application Type

Community website repository with a static landing in the current phase and a planned Python backend in later phases.

## Top-Level Structure

### Documentation

- `README.md`
- `AGENTS.md`
- `docs/current-hll-servers-source-plan.md`
- `docs/`

### Frontend

- `frontend/index.html`
- `frontend/assets/css/`
- `frontend/assets/js/`
- `frontend/assets/img/`

### Backend

- `backend/`
- `backend/app/`

### AI Platform

- `ai/`
- `ai/orchestrator/`
- `ai/prompts/`
- `ai/tasks/`

### Automation And Support

- `scripts/`
- `.github/workflows/`

## Current Technical Baseline

- Frontend runtime is plain browser-loaded HTML, CSS and JavaScript.
- Backend runtime is a minimal Python bootstrap with `GET /health` and room for placeholder API routes.
- Python is the expected backend language for future development.
- GitHub Actions and local PowerShell scripts may support the AI task workflow.

## Editing Priorities

- Product-facing changes usually start in `frontend/`.
- Process and coordination changes usually start in `ai/`, `AGENTS.md` and `scripts/`.
- Backend changes must remain preparatory unless a task explicitly changes that scope.

## Validation Expectations

- Frontend changes should remain compatible with local browser opening where applicable.
- AI platform changes should keep task paths and documentation aligned.
- Script changes should fail safely when optional tools or tests are not configured.

## Current Integration Direction

- Discord and game server data remain in planning phase until sources, limits and security are validated.
- Initial dynamic data should come from controlled backend placeholders, not direct frontend calls to external services.
- The technical plan for these integrations is documented in `docs/discord-and-server-data-plan.md`.
- Current Hell Let Loose servers may be exposed as a clearly marked provisional reference block before HLL Vietnam-specific data exists.
- The phased source strategy for that provisional block is documented in `docs/current-hll-servers-source-plan.md`.
- The ingestion strategy for converting that provisional block into normalized server snapshots is documented in `docs/current-hll-data-ingestion-plan.md`.
- The logical storage foundation for persisting server snapshots is documented in `docs/stats-database-schema-foundation.md`.
- The historical domain model for scoreboard-based player and match statistics is documented in `docs/historical-stats-domain-model.md`.
- Frontend data consumption should remain progressive, endpoint by endpoint, with static fallbacks preserved during migration.
- The frontend integration strategy is documented in `docs/frontend-data-consumption-plan.md`.
