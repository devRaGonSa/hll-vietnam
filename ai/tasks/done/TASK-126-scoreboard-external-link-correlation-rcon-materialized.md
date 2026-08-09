---
id: TASK-126
title: Correlate scoreboard links with RCON materialized matches
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto Python
roadmap_item: rcon-full-data
priority: medium
---

# TASK-126 - Correlate scoreboard links with RCON materialized matches

## Goal

Safely correlate materialized RCON matches with public scoreboard game URLs when a high-confidence match exists.

## Background

Match cards should link to the public scoreboard only when safe correlation exists. RCON remains the primary data source; public scoreboard links are optional enrichment and should never open arbitrary domains.

## Constraints

- No UI changes.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Do not store secrets, runtime DB files or `backend/runtime`.
- Do not treat public scoreboard as source of truth for RCON data.
- If correlation fails, internal detail links must still work.

## Allowed Changes

- existing scoreboard origin catalog/correlation code if present
- backend safe URL/correlation storage or cache code
- backend tests
- this task file when moving it through the workflow

## Implementation Requirements

- Work from a dedicated branch for this task.
- Read first:
  - `AGENTS.md`
  - `ai/architecture-index.md`
  - `ai/repo-context.md`
  - `ai/orchestrator/backend-senior.md`
  - `backend/app/scoreboard_origin_catalog.py` if present
  - existing scoreboard link correlation modules
  - materialized match code from TASK-122
- Correlate by server, map, end time/server time where possible, duration where possible and player count/peak players where available.
- Support known origins:
  - Comunidad Hispana #01: `https://scoreboard.comunidadhll.es`
  - Comunidad Hispana #02: `https://scoreboard.comunidadhll.es:5443`
- Only return external `match_url` for expected origins and `/games/<id>` paths.
- Store or cache correlation result if appropriate.
- Include a manual check for `https://scoreboard.comunidadhll.es/games/1561515`.

## Validation Commands

- `python -m compileall backend/app`
- `python -m pytest backend/tests/<new_or_relevant_scoreboard_correlation_tests>.py`

## Manual Verification Steps

- Confirm safe URL allowlist rejects arbitrary domains and paths.
- Confirm #01 and #02 origin selection works.
- Confirm no server #03 is added to catalogs, defaults or tests.
- Confirm failed correlation still leaves internal detail links available.
- Confirm `git diff --name-only` matches the allowed scope.

## Git Requirements

- Create a dedicated branch for this task, for example `codex/task-126-rcon-scoreboard-correlation`.
- Run relevant validation before committing.
- Stage only intended files.
- Commit the completed implementation.
- Push the branch to origin.

## Outcome

Kept scoreboard correlation as optional enrichment over RCON-backed match data. Materialized RCON recent/detail payloads call the existing correlation path and only expose `match_url` when the persisted public scoreboard candidate belongs to the trusted origin for the active server.

Hardened trusted scoreboard URL validation so only the known #01 and #02 origins and `/games/<id>` paths are accepted. Arbitrary domains, wrong ports, non-game paths, credentials, query strings and fragments are rejected. Comunidad Hispana #03 was not reintroduced.

If correlation fails, the internal materialized detail payload still works and simply returns `match_url: null`.

## Validation Result

- Passed: `python -m compileall backend/app`
- Pytest was not installed in the local Python environment.
- Passed deterministic fallback: `$env:PYTHONPATH='backend'; python -m unittest backend.tests.test_rcon_materialization_pipeline backend.tests.test_scoreboard_match_links`
- Passed safe URL allowlist coverage for Comunidad Hispana #01 and #02 in `backend.tests.test_rcon_materialization_pipeline`.
- Passed existing scoreboard correlation regression suite in `backend.tests.test_scoreboard_match_links`.
