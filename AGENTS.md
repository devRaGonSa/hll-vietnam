# HLL Vietnam Agent Operating Rules

This repository uses an AI-driven task workflow adapted to HLL Vietnam.

## Project Context

- Product: HLL Vietnam
- Product type: community website
- Current frontend: HTML, CSS and vanilla JavaScript
- Planned backend: Python
- Current product scope: simple landing page and repository foundation
- Visual identity: military, Vietnam, tactical, sober

## Task System

Task locations:

- Pending: `ai/tasks/pending`
- In progress: `ai/tasks/in-progress`
- Done: `ai/tasks/done`

Every new task must follow:

- `ai/task-template.md`

## Core Workflow

1. The orchestrator reviews repository context and relevant code.
2. The orchestrator writes or refines a task in `ai/tasks/pending`.
3. A worker moves the selected task to `ai/tasks/in-progress`.
4. The worker reads the files listed in `Files to Read First`.
5. The worker performs only the scoped change defined by the task.
6. The worker validates the change with the documented checks.
7. The worker moves the completed task to `ai/tasks/done`.
8. The worker documents any relevant architectural or process decision.

Codex must not act freely outside tasks except for repository inspection, platform maintenance, or explicitly requested integration work like this one.

## Roles Used In This Repository

- PM
- Analista
- Backend Senior
- Frontend Senior
- Arquitecto de Base de Datos
- Arquitecto Python
- Disenador grafico
- Experto en interfaz

Role guidance is stored in:

- `ai/orchestrator/`

## Rules

- Do not break repository structure without explicit technical justification.
- Do not make destructive changes without explicit justification.
- Keep changes small, verifiable and documented.
- Do not overwrite existing project context with generic template content.
- Preserve HLL Vietnam branding and product identity.
- Do not introduce unnecessary frameworks in the current phase.
- Do not build backend functionality until a task explicitly requires it.
- Do not modify unrelated files.

## Technical Constraints

- Frontend changes must remain compatible with direct browser opening when applicable.
- Backend architecture decisions must assume Python as the primary backend language.
- AI platform files are support infrastructure, not product features.
- If a template utility is copied from the platform template, it must remain clearly identified as platform infrastructure.

## Planning Rules

Before drafting or executing a task:

1. Read `ai/architecture-index.md`.
2. Read `ai/repo-context.md`.
3. Read the relevant role file in `ai/orchestrator/`.
4. Read the small set of project files directly related to the requested change.

When no pending product task exists:

1. Do not invent a large backlog.
2. Only create a minimal technical validation task if needed to verify platform readiness.
3. Avoid feature planning that changes product scope without instruction.

## Change Budget

- Prefer fewer than 5 modified files per task.
- Prefer changes under 200 lines when feasible.
- Split work into follow-up tasks if the scope grows.

## Validation

Before marking a task as done:

1. Run the validation listed in the task.
2. Review `git diff --name-only`.
3. Confirm that changed files match the expected scope.
4. Update documentation if the task changed workflow or architecture assumptions.

If integration tests are relevant and `scripts/run-integration-tests.ps1` exists, use it.
If no integration tests are configured for the affected scope, document that explicitly in the task outcome.
