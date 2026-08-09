# AI Platform Workspace

This directory contains the AI Development Platform support layer integrated into HLL Vietnam.

Its purpose is operational, not product-facing. It exists to help the project plan work through tasks, preserve repository context, coordinate specialist roles and keep changes small, reviewable and documented.

## Included areas

- `../ai-platform.json`: repository-specific platform configuration for local workers and validation
- `task-template.md`: standard structure for every task
- `repo-context.md`: repository and product context for planners and workers
- `architecture-index.md`: quick map of the repository structure
- `system-metrics.md`: lightweight log for platform execution metrics
- `reports/`: generated local platform reports; Markdown reports are ignored except `.gitkeep`
- `prompts/`: reusable planning prompts
- `orchestrator/`: role guidance and orchestration documents
- `tasks/`: task queue split by status

## Task lifecycle

- `tasks/pending/`: scoped tasks ready for a worker
- `tasks/in-progress/`: tasks currently being executed
- `tasks/review/`: completed work waiting for human or orchestrator review
- `tasks/blocked/`: tasks that cannot continue without a decision or missing input
- `tasks/obsolete/`: tasks intentionally retired without execution
- `tasks/done/`: validated and completed tasks

## HLL Vietnam usage rules

- The platform must reflect the real state of HLL Vietnam, not generic sample content.
- Tasks should be created only when there is a justified change to perform.
- This integration does not add product features by itself.
- The current product stack remains HTML, CSS and JavaScript on the frontend, with Python reserved for the future backend.
- Codex workers must process explicit tasks only and use `ai-platform.json` for local platform paths where scripts support it.
