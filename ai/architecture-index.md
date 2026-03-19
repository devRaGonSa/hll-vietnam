# Architecture Index

This file gives AI agents a fast overview of HLL Vietnam before they inspect the repository in detail.

## Application Type

Community website repository with a static landing in the current phase and a planned Python backend in later phases.

## Top-Level Structure

### Documentation

- `README.md`
- `AGENTS.md`
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
- There is no active backend runtime yet.
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
