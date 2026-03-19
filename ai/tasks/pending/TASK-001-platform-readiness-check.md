# TASK-001-platform-readiness-check

## Goal

Validate that the AI development platform is integrated into HLL Vietnam with the required documentation, task structure and automation entry points.

## Context

This task exists only as a technical readiness reference. It is not a product feature task and should not change the landing or add backend behavior.

## Steps

1. Verify that `AGENTS.md` points to the task workflow.
2. Verify that `ai/` contains context, architecture, prompts and orchestrator role docs.
3. Verify that `scripts/` contains the expected platform scripts.
4. Verify that the repository remains consistent after integration.

## Files to Read First

- `AGENTS.md`
- `ai/README.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `ai/orchestrator/README.md`

## Expected Files to Modify

- None unless a platform consistency issue is found

## Constraints

- Do not modify product-facing files unless a platform integration issue requires it.
- Do not add new product tasks.
- Keep this task as a platform validation reference only.

## Validation

Before completing the task ensure:

- required platform files exist
- task paths are present
- scripts are present
- repository documentation is coherent

## Change Budget

- Prefer zero code changes.
- If any correction is needed, keep it minimal and platform-scoped.
