---
id: TASK-123
title: Materialize RCON player match stats
status: pending
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto de Base de Datos
  - Arquitecto Python
roadmap_item: rcon-full-data
priority: high
---

# TASK-123 - Materialize RCON player match stats

## Goal

Build first-pass per-match player statistics from RCON AdminLog kill, team and presence events.

## Background

The internal match detail page should eventually show a simplified scoreboard-like view backed by RCON. AdminLog includes `KILL`, `TEAMSWITCH`, `CONNECTED` and `DISCONNECTED` events that can produce kills, deaths, teamkills, weapon counts and player presence.

## Constraints

- No UI changes.
- Do not expose raw player IDs in frontend work.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Do not store secrets, runtime DB files or `backend/runtime`.
- Keep rematerialization deterministic and idempotent.

## Allowed Changes

- backend materialization/storage code for RCON player match stats
- optional structured event timeline table or read logic
- backend tests and fixtures
- this task file when moving it through the workflow

## Implementation Requirements

- Work from a dedicated branch for this task.
- Read first:
  - `AGENTS.md`
  - `ai/architecture-index.md`
  - `ai/repo-context.md`
  - `ai/orchestrator/backend-senior.md`
  - `ai/orchestrator/database-architect.md`
  - `backend/app/rcon_admin_log_parser.py`
  - `backend/app/rcon_admin_log_storage.py`
  - materialized match code from TASK-122
- Use parsed events from `rcon_admin_log_events`.
- Associate events to matches by target and server-time range between `match_start` and `match_end`.
- Create a table such as `rcon_match_player_stats` with target, match, player identity/display, team, kills, deaths, teamkills, deaths by teamkill, weapon JSON, death-by weapon JSON, most-killed JSON, death-by JSON and first/last seen server time.
- Optionally create `rcon_match_events` for structured timeline rows, or read directly from AdminLog events.
- For `KILL`, add one kill to the killer when teams differ, add one death to the victim, and count same-team kills as teamkills plus victim deaths by teamkill.
- Track weapon counts and killer-victim counts.
- Use connected/disconnected/team switch events to improve presence and team attribution.
- Handle missing or non-Steam-style player IDs robustly.

## Validation Commands

- `python -m compileall backend/app`
- `python -m pytest backend/tests/<new_or_relevant_player_stats_tests>.py`

## Manual Verification Steps

- Validate offline fixtures containing `KILL`, `TEAMSWITCH`, `CONNECTED` and `DISCONNECTED`.
- Confirm kills, deaths, teamkills, weapons, most killed and death-by summaries.
- Confirm repeated materialization does not duplicate or inflate stats.
- Confirm `/health` still works.
- Confirm `git diff --name-only` matches the allowed scope.

## Git Requirements

- Create a dedicated branch for this task, for example `codex/task-123-rcon-player-stats`.
- Run relevant validation before committing.
- Stage only intended files.
- Commit the completed implementation.
- Push the branch to origin.
