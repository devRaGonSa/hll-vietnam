---
id: TASK-120
title: Integrate AdminLog ingestion into RCON historical worker
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto Python
roadmap_item: rcon-full-data
priority: high
---

# TASK-120 - Integrate AdminLog ingestion into RCON historical worker

## Goal

Automatically ingest RCON AdminLog events during the periodic RCON historical worker capture flow.

## Background

HLL Vietnam is moving to an RCON-first historical/live data platform. Manual AdminLog ingestion already exists and has been validated with duplicate-safe canonical message storage. The periodic worker should keep collecting this data automatically after or alongside existing session/gamestate capture.

## Constraints

- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Do not store secrets, runtime DB files or `backend/runtime`.
- Do not modify Docker behavior.
- Do not change frontend files.
- Preserve existing writer lock behavior.
- If AdminLog ingestion fails for one target, normal session capture for other targets must continue.
- Public scoreboard remains optional enrichment/fallback only.

## Allowed Changes

- `backend/app/rcon_historical_worker.py`
- tests only if needed for worker payload behavior
- this task file when moving it through the workflow

## Implementation Requirements

- Work from a dedicated branch for this task.
- Read first:
  - `AGENTS.md`
  - `ai/architecture-index.md`
  - `ai/repo-context.md`
  - `ai/orchestrator/backend-senior.md`
  - `backend/app/rcon_historical_worker.py`
  - `backend/app/rcon_admin_log_ingestion.py`
  - `backend/app/rcon_admin_log_storage.py`
- Reuse existing AdminLog ingestion and storage modules.
- Add a configurable AdminLog lookback window, defaulting to 60 minutes.
- Prefer project-consistent naming such as `HLL_BACKEND_RCON_ADMIN_LOG_LOOKBACK_MINUTES=60`.
- Do not hardcode `1440` for the periodic worker.
- Keep the manual backfill command able to support `--minutes 1440`.
- Extend worker results with:
  - `admin_log_events_seen`
  - `admin_log_events_inserted`
  - `admin_log_duplicate_events`
  - `admin_log_failed_targets`
- Keep changes deterministic and idempotent.

## Validation Commands

- `python -m compileall backend/app`
- `docker compose up -d --build backend rcon-historical-worker`
- `docker compose exec backend python -m app.rcon_historical_worker capture`
- Run AdminLog ingestion twice and confirm dedupe still reports duplicates on the second run.

## Manual Verification Steps

- Confirm worker capture returns normal session/gamestate data plus AdminLog metrics.
- Confirm an AdminLog failure for one target is reported without breaking all target capture.
- Confirm `/health` still works.
- Confirm `git diff --name-only` matches the allowed scope.

## Git Requirements

- Create a dedicated branch for this task, for example `codex/task-120-adminlog-worker-ingestion`.
- Run relevant validation before committing.
- Stage only intended files.
- Commit the completed implementation.
- Push the branch to origin.

## Outcome

- Integrated AdminLog ingestion into the RCON historical capture worker using the existing ingestion/storage path.
- Added `HLL_BACKEND_RCON_ADMIN_LOG_LOOKBACK_MINUTES`, defaulting to 60 minutes.
- Added worker result totals for AdminLog events seen, inserted, duplicated and failed targets.
- Verified a temporary bad RCON target reports one session failure and one AdminLog failure while a valid target still captures successfully.

## Validation Result

- `python -m compileall backend/app` passed.
- `docker compose up -d --build backend rcon-historical-worker` passed.
- `docker compose exec backend python -m app.rcon_historical_worker capture` passed and returned AdminLog metrics.
- `docker compose exec backend python -m app.rcon_admin_log_ingestion --minutes 1440` run twice; second run reported 143 duplicate events and 0 inserted events.
- `/health` returned `status: ok`.
- `git diff --name-only` matched the expected task scope.
