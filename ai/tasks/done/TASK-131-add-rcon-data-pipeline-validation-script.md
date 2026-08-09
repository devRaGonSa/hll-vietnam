---
id: TASK-131
title: Add RCON data pipeline validation script
status: done
type: platform
team: Backend Senior
supporting_teams:
  - Arquitecto Python
  - Frontend Senior
roadmap_item: rcon-full-data
priority: medium
---

# TASK-131 - Add RCON data pipeline validation script

## Goal

Add one lightweight validation script for the full RCON data pipeline.

## Background

The RCON data pipeline now spans parsing, storage, AdminLog ingestion, materialized matches, player stats and backend APIs. A focused script should help implementation workers and reviewers validate the pipeline without requiring real RCON for unit tests.

## Constraints

- Do not require real RCON for unit tests.
- Do not modify Docker behavior.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Do not store secrets, runtime DB files or `backend/runtime`.
- Document when real RCON or Docker smoke checks are skipped.

## Allowed Changes

- `scripts/run-rcon-data-pipeline-tests.ps1`
- possibly `scripts/run-integration-tests.ps1` only if wiring the new script is appropriate and low risk
- documentation only if needed for the new command
- this task file when moving it through the workflow

## Implementation Requirements

- Work from a dedicated branch for this task.
- Read first:
  - `AGENTS.md`
  - `ai/architecture-index.md`
  - `ai/repo-context.md`
  - `ai/orchestrator/backend-senior.md`
  - `scripts/run-integration-tests.ps1`
  - existing backend tests for AdminLog/parser/materialization
- Add `scripts/run-rcon-data-pipeline-tests.ps1`.
- Validate Python compile.
- Run parser tests.
- Run storage/materialization tests.
- Include optional backend endpoint smoke checks if Docker is already running.
- Skip real RCON-dependent checks gracefully with a clear message.

## Validation Commands

- `powershell -ExecutionPolicy Bypass -File scripts/run-rcon-data-pipeline-tests.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`

## Manual Verification Steps

- Confirm the script can run without real RCON credentials.
- Confirm skipped Docker/RCON smoke checks explain why they were skipped.
- Confirm existing integration script still passes.
- Confirm no product behavior changed.
- Confirm `git diff --name-only` matches the allowed scope.

## Git Requirements

- Create a dedicated branch for this task, for example `codex/task-131-rcon-pipeline-validation`.
- Run relevant validation before committing.
- Stage only intended files.
- Commit the completed implementation.
- Push the branch to origin.

## Outcome

- Added `scripts/run-rcon-data-pipeline-tests.ps1`.
- The script compiles backend modules, runs RCON parser/storage/materialization/link checks without real RCON credentials, and performs an optional backend health smoke check only when Docker Compose already has `backend` running.
- The script prefers `pytest` when available and falls back to deterministic offline checks plus unittest suites when `pytest` is absent.
- Validation: `powershell -ExecutionPolicy Bypass -File scripts/run-rcon-data-pipeline-tests.ps1` passed.
- Validation: `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1` returned exit code 0, but its nested historical UI regression check emitted an existing frontend assertion about the missing recent-match external action label. No frontend files were changed in this platform task.
- Real RCON checks were skipped by design because the script must run without RCON credentials.
