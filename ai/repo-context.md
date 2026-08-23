# Repository Context

## Project Overview

HLL Vietnam is a community website repository for a Spanish-speaking Discord community centered on the future game HLL Vietnam.

The implementation began as a small foundation and now includes:

- a static landing page in `frontend/`
- a functional Python backend in `backend/` with selectable CRCON-first readers
  and legacy rollback
- documentation in `docs/`
- an AI task orchestration layer in `ai/`

This repository is in foundation stage. The objective is to grow in a controlled way without losing clarity or overwriting project identity with generic template content.

## Current Product State

- Frontend: static HTML, CSS and vanilla JavaScript
- Backend: Python HTTP API with explicit `api/`, `services/`, `crcon/`,
  `domain/` and `tools/` package boundaries
- AI Platform: integrated to coordinate planning and task execution
- Product goal in current phase: maintain a clean landing and repository structure
- Default deployment: `backend` + `frontend`; historical workers are advanced/manual only.
- Live and historical defaults are RCON-first, with public-scoreboard kept only as historical fallback.
- Comunidad Hispana #03 is not part of default RCON targets. Historical/Elo code and persisted data are preserved, while Elo/MMR remains paused and decoupled from backend startup.
- RCON historical data flow is session capture plus AdminLog ingestion, parsed event storage, materialized matches/player stats and optional player profile snapshot enrichment.
- Public scoreboard may enrich links or fill unsupported historical gaps, but it is not the primary historical source when RCON coverage exists.
- A CRCON 12.0.1 anti-corruption layer now provides selectable server-list,
  current-match, historical match, aggregate and authenticated player-search
  readers while preserving legacy rollback. Runtime credentials/schema remain
  unverified locally, so writers and storage are retained.

## Repository Areas

### Root documentation

- `README.md`
- `AGENTS.md`

These files define the repository purpose and operating rules.

### Docs

- `docs/project-overview.md`
- `docs/roadmap.md`
- `docs/decisions.md`

These files describe scope, phased evolution and technical decisions.

### Frontend

- `frontend/index.html`
- `frontend/assets/css/styles.css`
- `frontend/assets/js/main.js`

This is the live product surface in the current phase. Keep changes conservative unless a task explicitly targets the landing.

### Backend

- `backend/README.md`
- `backend/requirements.txt`
- `backend/app/__init__.py`
- `backend/app/api/`
- `backend/app/services/`
- `backend/app/crcon/`
- `backend/app/domain/`
- `backend/app/tools/`

This is the functional backend. New public use cases belong in `services/`,
request/JSON compatibility in `api/`, and CRCON transport/schema code in
`crcon/`. The mixed flat historical/RCON/storage modules remain rollback or
product-decision code until a dedicated task can isolate them safely. See
`docs/CODE_STRUCTURE.md`.

### AI Platform

- `ai/task-template.md`
- `ai-platform.json`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `ai/system-metrics.md`
- `ai/reports/`
- `ai/prompts/`
- `ai/orchestrator/`
- `ai/tasks/`

This area supports planning, orchestration and execution discipline.

## Working Rules For Agents

- Always work from tasks, except for repository inspection or explicitly requested platform integration.
- Prefer small, focused, reviewable changes.
- Preserve the military and Vietnam-inspired visual tone.
- Avoid introducing new technologies without clear reason.
- Treat Python as the planned backend baseline.

## AI Workflow

`Request -> Orchestrator review -> Scoped task -> Execution -> Validation -> Documentation -> Commit`

Tasks move through:

- `ai/tasks/pending`
- `ai/tasks/in-progress`
- `ai/tasks/review`
- `ai/tasks/blocked`
- `ai/tasks/obsolete`
- `ai/tasks/done`
