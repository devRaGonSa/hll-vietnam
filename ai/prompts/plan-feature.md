# Plan Feature Prompt

Use this prompt when the orchestrator needs to transform a repository request into implementation-ready tasks.

## Prompt

Analyze the HLL Vietnam repository before proposing any implementation work.

Required behavior:

1. Read `AGENTS.md`.
2. Read `ai/repo-context.md`.
3. Read `ai/architecture-index.md`.
4. Review only the files directly related to the request.
5. Produce a small, safe task breakdown.
6. Do not invent product features outside the request.
7. Keep branding, frontend stack and planned Python backend consistent with the repository rules.

Task output rules:

- Use `ai/task-template.md`.
- Keep tasks small and verifiable.
- Prefer one task when the work is very small.
- Add clear `Files to Read First`.
- Add clear `Expected Files to Modify`.
- Include explicit validation steps.
