---
id: TASK-122
title: Materialize RCON matches from AdminLog events
status: pending
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto de Base de Datos
  - Arquitecto Python
roadmap_item: rcon-full-data
priority: high
---

# TASK-122 - Materialize RCON matches from AdminLog events

## Goal

Create a materialization layer that converts RCON AdminLog and useful session/gamestate data into durable RCON match records.

## Background

Recent matches need consistent RCON-first scores. AdminLog contains `MATCH START` and `MATCH ENDED` records, while session/gamestate capture can provide partial in-progress scores. A materialized read model should make this data reliable and idempotent before UI changes consume it.

## Constraints

- Do not delete or replace existing competitive-window logic.
- No UI changes.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Do not store secrets, runtime DB files or `backend/runtime`.
- Preserve RCON as the source of truth; public scoreboard is optional enrichment/fallback only.

## Allowed Changes

- backend storage/model modules for materialized RCON matches
- backend tests for materialization
- small wiring needed to initialize/read the new table
- this task file when moving it through the workflow

## Implementation Requirements

- Work from a dedicated branch for this task.
- Read first:
  - `AGENTS.md`
  - `ai/architecture-index.md`
  - `ai/repo-context.md`
  - `ai/orchestrator/backend-senior.md`
  - `ai/orchestrator/database-architect.md`
  - `backend/app/rcon_admin_log_storage.py`
  - `backend/app/rcon_admin_log_parser.py`
  - `backend/app/rcon_historical_read_model.py`
  - existing historical storage modules
- Derive RCON matches from:
  - `match_start`
  - `match_end`
  - session/gamestate samples where useful
- Store materialized records in SQLite, using a table such as `rcon_materialized_matches`.
- Include fields for `id`, `target_key`, `external_server_id`, `match_key` or `session_key`, `map_name`, `map_pretty_name`, `game_mode`, server/event start/end times, scores, winner, `confidence_mode`, `source_basis`, `created_at` and `updated_at`.
- Make materialization idempotent.
- Treat `MATCH ENDED` as authoritative result when present.
- Treat session/gamestate scores as partial or in-progress when no `MATCH ENDED` exists.
- Parse and test results including 5-0, 2-2 and 0-5.

## Validation Commands

- `python -m compileall backend/app`
- `python -m pytest backend/tests/<new_or_relevant_materialized_match_tests>.py`

## Manual Verification Steps

- Confirm repeated materialization does not duplicate matches.
- Confirm a sample `MATCH ENDED \`ST MARIE DU MONT Warfare\` ALLIED (5 - 0) AXIS` produces the expected score and winner.
- Confirm existing competitive-window reads still work.
- Confirm `/health` still works.
- Confirm `git diff --name-only` matches the allowed scope.

## Git Requirements

- Create a dedicated branch for this task, for example `codex/task-122-rcon-match-materialization`.
- Run relevant validation before committing.
- Stage only intended files.
- Commit the completed implementation.
- Push the branch to origin.
