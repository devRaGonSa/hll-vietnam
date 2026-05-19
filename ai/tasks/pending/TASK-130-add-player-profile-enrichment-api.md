---
id: TASK-130
title: Add player profile enrichment API
status: pending
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto Python
roadmap_item: rcon-full-data
priority: medium
---

# TASK-130 - Add player profile enrichment API

## Goal

Expose optional player profile summaries from RCON profile snapshots for future UI use without coupling them to per-match stats.

## Background

Profile MESSAGE snapshots can enrich player rows later, but they are historical profile snapshots rather than authoritative match facts. The API should expose safe display summaries and remain resilient when no snapshot exists.

## Constraints

- No mandatory frontend changes.
- Do not return raw full `MESSAGE` content by default.
- Do not make match detail fail if no profile snapshot exists.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Do not store secrets, runtime DB files or `backend/runtime`.

## Allowed Changes

- backend read model/route code for profile enrichment
- API tests
- this task file when moving it through the workflow

## Implementation Requirements

- Work from a dedicated branch for this task.
- Read first:
  - `AGENTS.md`
  - `ai/architecture-index.md`
  - `ai/repo-context.md`
  - `ai/orchestrator/backend-senior.md`
  - `backend/app/routes.py`
  - profile snapshot code from TASK-129
  - match detail API code from TASK-124
- Add a backend read-model endpoint or include optional `profile_summary` in match detail player rows if available.
- Return only safe display data.
- Keep no-data behavior empty or omitted, not failing.
- Keep implementation deterministic and testable offline where possible.

## Validation Commands

- `python -m compileall backend/app`
- `python -m pytest backend/tests/<new_or_relevant_profile_api_tests>.py`

## Manual Verification Steps

- Make a manual request against a known stored profile snapshot.
- Confirm missing snapshots do not break match detail or profile responses.
- Confirm raw full MESSAGE content is absent by default.
- Confirm `/health` still works.
- Confirm `git diff --name-only` matches the allowed scope.

## Git Requirements

- Create a dedicated branch for this task, for example `codex/task-130-profile-enrichment-api`.
- Run relevant validation before committing.
- Stage only intended files.
- Commit the completed implementation.
- Push the branch to origin.
