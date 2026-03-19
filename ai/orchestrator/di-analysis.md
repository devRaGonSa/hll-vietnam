# Dependency Analysis

## Purpose

Analyze dependencies and execution assumptions before changing scripts, automation or future backend design notes.

## Rules

- Identify whether the task affects frontend-only, documentation-only or platform-only areas.
- Avoid importing template assumptions from unrelated stacks.
- When in doubt, preserve the current lightweight structure and document the dependency instead of implementing it.
