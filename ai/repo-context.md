# Repository Context

## Project Overview

HLL Vietnam is a community website repository for a Spanish-speaking Discord community centered on the future game HLL Vietnam.

The current implementation is intentionally small:

- a static landing page in `frontend/`
- a reserved Python backend space in `backend/`
- documentation in `docs/`
- an AI task orchestration layer in `ai/`

This repository is in foundation stage. The objective is to grow in a controlled way without losing clarity or overwriting project identity with generic template content.

## Current Product State

- Frontend: static HTML, CSS and vanilla JavaScript
- Backend: not implemented yet, but planned in Python
- AI Platform: integrated to coordinate planning and task execution
- Product goal in current phase: maintain a clean landing and repository structure

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

This area is a reserved foundation for the future Python backend. Do not add functional services unless explicitly requested by task.

### AI Platform

- `ai/task-template.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `ai/system-metrics.md`
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
- `ai/tasks/done`
