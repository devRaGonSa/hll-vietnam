---
id: TASK-116
title: Correlate RCON windows with scoreboard matches
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto Python
  - Analista
  - PM
roadmap_item: historical
priority: high
---

# TASK-116 - Correlate RCON windows with scoreboard matches

## Goal

Resolve external scoreboard URLs for RCON competitive-window synthetic matches only when there is strong evidence.

## Context

RCON competitive-window matches can have synthetic IDs such as `31:2026-04-12T16:28:55.761810Z`. Those IDs must stay internal and must never be used to fabricate external scoreboard URLs.

Known validation reference from the user:

- Internal RCON match:
  - server: Comunidad Hispana #01
  - synthetic match id: `31:2026-04-12T16:28:55.761810Z`
  - map shown: St. Mere Eglise
  - UI start/end around 12/4/26 18:28 to 18:43 local time
  - players: 94 average / 98 peak
- Equivalent real scoreboard game known by the user:
  - game id: `1561515`
  - external scoreboard page exists under the server #01 scoreboard origin

This task must use that example as a fixture/reference without hardcoding a one-off special case.

Use branch:

- `plan/scoreboard-match-linking-tasks`

## Steps

1. Work from this task only after moving it to `ai/tasks/in-progress/`.
2. Inspect the listed files before changing anything.
3. Build a resolver that takes server, synthetic session key, map, `started_at`, `ended_at`, duration and player counts.
4. Search existing persisted scoreboard data first.
5. If existing provider code can query recent scoreboard data without credentials, use it carefully; otherwise document the limitation and keep the resolver local-only.
6. Match by server, normalized map and time proximity at minimum.
7. Use additional evidence such as duration and player counts when available.
8. Avoid false positives; return no URL when confidence is low.
9. Return only URLs that pass trusted origin validation.
10. Ensure the match detail endpoint exposes `match_url` for RCON matches only when resolver confidence is sufficient.
11. Add a focused unit or fixture test for the correlation logic if feasible.
12. Validate the result.
13. Move this task to `ai/tasks/done/` only after validation is complete and document the outcome in this file.
14. Commit and push the completed implementation branch.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/backend-senior.md`
- `ai/orchestrator/analyst.md`
- `backend/app/rcon_historical_read_model.py`
- `backend/app/rcon_historical_storage.py`
- `backend/app/historical_storage.py`
- `backend/app/historical_snapshots.py`
- `backend/app/routes.py`
- `backend/app/providers/public_scoreboard_provider.py`
- backend trusted scoreboard origin helper/config from TASK-114
- `backend/tests/` if present
- `scripts/run-integration-tests.ps1`

## Expected Files to Modify

- likely a new or existing backend resolver module
- possibly `backend/app/rcon_historical_read_model.py`
- possibly `backend/app/historical_storage.py`
- possibly `backend/app/routes.py`
- possibly backend tests or fixtures
- this task file, moved to `ai/tasks/done/`

If additional files become necessary, explain why in the task outcome and commit message.

## Expected Files Not to Modify

- `frontend/**`
- local `.env`
- database migrations unless absolutely required and justified
- persisted data
- Docker/Compose config
- Elo/MMR implementation files
- historical ingestion policy/config

## Constraints

- Do not reintroduce Comunidad Hispana #03.
- Do not reintroduce paused MVP/Elo UI.
- Do not change historical ingestion policy.
- Do not add real credentials.
- Do not modify local `.env`.
- Do not delete persisted data, migrations, backend endpoints or historical ingestion code.
- Do not use the public word "snapshot" in user-facing UI.
- Do not fabricate unsafe URLs from synthetic RCON IDs.
- Prefer no link over a low-confidence or ambiguous link.

## Validation

Before completing the task, run and document:

- `git status`
- Python compile checks for touched backend modules
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- focused unit or fixture test for correlation logic if feasible
- endpoint check confirming `match_url` appears only when confidence is sufficient
- negative test/check confirming low-confidence or ambiguous candidates return no URL
- check using the user reference example when data or fixture setup allows it
- check confirming generated/exposed URLs pass trusted origin validation
- `git diff --name-only` and confirmation that changed files match the expected scope

If a configured validation command cannot be run, document the exact reason in the outcome.

## Commit And Push Requirements

- Run validation before committing.
- Run `git status`.
- Stage only intended files.
- Commit with message: `feat: correlate rcon matches with scoreboard links`
- Push the branch to origin.
- Do not leave completed work only in local.

## Outcome

Completed.

Implementation decisions:

- Added `backend/app/rcon_scoreboard_correlation.py` as a local-only resolver over already persisted public-scoreboard matches.
- The resolver does not query the public provider or network during request handling. It searches persisted `historical_matches` first and returns no URL when no strong local match exists.
- `backend/app/rcon_historical_read_model.py` now calls the resolver for RCON match-detail payloads and keeps the synthetic RCON session key internal.
- No URL is built from a synthetic RCON ID. Returned URLs must come from persisted `raw_payload_ref` and pass the trusted origin validation from TASK-114.

Confidence rules chosen:

- Required evidence: same server, normalized map match, parseable RCON and scoreboard time windows, and a trusted persisted `raw_payload_ref`.
- Scored evidence: time overlap, RCON midpoint inside the scoreboard match, endpoint proximity, duration compatibility, and optional player-count compatibility.
- Minimum score: `5`.
- Ambiguity handling: if two candidates tie for the best score, the resolver returns no URL.
- Preference: no link over a low-confidence or ambiguous link.

Validation performed:

- `git status --short --branch` confirmed branch `plan/scoreboard-match-linking-tasks`.
- `$env:PYTHONPATH='backend'; python -m unittest backend.tests.test_scoreboard_match_links` passed.
- The focused test includes the user reference shape: `comunidad-hispana-01`, RCON synthetic session `1:2026-04-12T16:28:55.761810Z`, map `St. Mere Eglise`, and correlated scoreboard game `1561515`.
- The focused test confirms `match_url` appears only with strong evidence.
- The focused test confirms low-confidence/wrong-map candidates return no URL.
- The focused tests confirm exposed URLs pass trusted origin validation because only persisted trusted `raw_payload_ref` values are returned.
- `python -m compileall backend/app backend/tests` passed.
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1` passed.
- `git diff --name-only` and `git status --short` were reviewed. Changed files match the expected scope: new resolver module, RCON read model integration, focused backend tests and this task file.

Note:

- The focused unittest still emits existing SQLite `ResourceWarning` messages from the repository connection helper pattern during forced cleanup, but all assertions pass and cleanup is not blocked.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split follow-up work into a new task if the scope grows.
