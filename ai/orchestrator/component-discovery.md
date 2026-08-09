# Component Discovery

## Purpose

Identify the real repository areas affected by a request before any task is executed.

## Repository Areas

- Root docs: repository purpose and rules
- `docs/`: scope, roadmap and decisions
- `frontend/`: current live product surface
- `backend/`: future Python backend foundation
- `ai/`: orchestration and task workflow
- `scripts/`: local platform automation

## Rules

- Read the smallest relevant set of files first.
- Prefer extending existing documents and scripts instead of duplicating them.
- Do not assume framework layers that do not exist in this repository.
