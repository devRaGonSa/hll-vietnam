---
id: TASK-132
title: Document RCON-first historical architecture
status: pending
type: documentation
team: PM
supporting_teams:
  - Backend Senior
  - Arquitecto Python
roadmap_item: rcon-full-data
priority: medium
---

# TASK-132 - Document RCON-first historical architecture

## Goal

Document the new RCON-first historical architecture and update AI context so future tasks preserve the intended data-source policy.

## Background

HLL Vietnam is building a historical/live data platform for Comunidad Hispana servers with RCON as the primary source. AdminLog ingestion, parsing, event storage, materialized matches/player stats and optional public-scoreboard enrichment should be documented clearly for future workers.

## Constraints

- Documentation-only task.
- Do not change product behavior.
- Do not modify backend/frontend/Docker code.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Do not store secrets, runtime DB files or `backend/runtime`.
- Public scoreboard must be described only as optional enrichment/link source or fallback.

## Allowed Changes

- `README.md` or backend README/docs as appropriate
- `docs/decisions.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- this task file when moving it through the workflow

## Implementation Requirements

- Work from a dedicated branch for this task.
- Read first:
  - `AGENTS.md`
  - `ai/architecture-index.md`
  - `ai/repo-context.md`
  - `ai/orchestrator/pm.md`
  - `ai/orchestrator/backend-senior.md`
  - `README.md`
  - `backend/README.md`
  - `docs/decisions.md`
- Document:
  - RCON session capture
  - AdminLog ingestion
  - AdminLog parser
  - event storage
  - materialized matches/player stats
  - public scoreboard only as optional enrichment/link source or fallback
  - Elo/MMR paused
  - Comunidad Hispana #03 disabled
- Include manual commands:
  - `docker compose exec backend python -m app.rcon_admin_log_ingestion --minutes 1440`
  - `docker compose exec backend python -m app.rcon_historical_worker capture`
- Keep wording repository-specific and avoid generic platform-template replacement.

## Validation Commands

- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`

## Manual Verification Steps

- Review docs for no secrets or credentials.
- Confirm docs consistently preserve RCON-first policy.
- Confirm Elo/MMR remains documented as paused.
- Confirm Comunidad Hispana #03 remains documented as disabled from defaults.
- Confirm `git diff --name-only` matches the allowed scope.

## Git Requirements

- Create a dedicated branch for this task, for example `codex/task-132-rcon-architecture-docs`.
- Run relevant validation before committing.
- Stage only intended files.
- Commit the completed implementation.
- Push the branch to origin.
