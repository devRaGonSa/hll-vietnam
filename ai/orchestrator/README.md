# Orchestrator

The orchestrator is responsible for turning repository context into safe, scoped and verifiable tasks for HLL Vietnam.

## What it does

- Reviews repository structure and current documentation
- Identifies the smallest useful unit of work
- Assigns the most suitable role guidance for the task
- Keeps tasks aligned with HLL Vietnam constraints and branding
- Prevents uncontrolled work outside the task system

## How it collaborates

- Reads `ai/architecture-index.md` and `ai/repo-context.md` first
- Uses `ai/task-template.md` to draft tasks
- Sends execution to the appropriate role document in this folder
- Keeps completed work traceable through `ai/tasks/` and `ai/system-metrics.md`

## Current scope

At this stage the orchestrator supports repository setup, documentation alignment, planning hygiene and future implementation flow. It does not define product roadmap beyond explicit project instructions.
