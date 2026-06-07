---
id: TASK-162
title: Add Stats player search endpoint (RCON materialized backend V1)
status: pending
type: backend
team: Backend Senior
supporting_teams: [Arquitecto de Base de Datos, Arquitecto Python]
roadmap_item: foundation
priority: medium
---

# TASK-162 - Add Stats player search endpoint (RCON materialized backend V1)

## Goal

Implement a backend V1 endpoint to support player search for the future Stats section:
`GET /api/stats/players/search?q=<query>`.

The endpoint must use existing RCON materialized tables and return search matches that include:

- `status`
- `query`
- `items`
- `player_id`
- `player_name`
- `matches_considered`
- `last_seen_at`
- optional `servers_seen` only if it can be added with low scope cost

No frontend work, no migrations, no yearly ranking, no Elo/MMR workarounds, no Comunidad Hispana #03 reactivation.

## Context

The repository already has a RCON materialized model (`rcon_match_player_stats` + `rcon_materialized_matches`) used by leaderboard reads.
The new endpoint is the first part of the Stats backend contract defined in `docs/stats-section-functional-plan.md`.
It should reuse existing routing/payload conventions in the current backend bootstrap.

## Steps

1. Inspect required files first (mandatory before implementation):
   - `AGENTS.md`
   - `ai/repo-context.md`
   - `ai/architecture-index.md`
   - `docs/stats-section-functional-plan.md`
   - `backend/app/rcon_historical_leaderboards.py`
   - `backend/app/main.py`
   - `backend/app/rcon_admin_log_materialization.py` (for table/schema context)
2. Reuse the existing `routes.py` + `payloads.py` endpoint/payload pattern.
3. Implement one new endpoint: `GET /api/stats/players/search`.
4. Validate `q` parameter and optional `server` or `server_id` and `limit` handling using current project conventions.
5. Query existing RCON materialized tables with read-only logic (preferably `rcon_match_player_stats` joined with `rcon_materialized_matches`).
6. Keep response shape aligned with existing backend payload conventions.
7. Add a minimal, self-contained module if needed (preferably `backend/app/rcon_historical_player_stats.py`).
8. Run backend validation/checks and document outcome.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `docs/stats-section-functional-plan.md`
- `backend/app/main.py`
- `backend/app/routes.py`
- `backend/app/payloads.py`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/rcon_admin_log_materialization.py`

## Expected Files to Modify

- `backend/app/rcon_historical_player_stats.py` (new module preferred)
- `backend/app/payloads.py`
- `backend/app/routes.py`
- `backend/app/main.py` (solo si se detecta una dependencia de export explícita o import requerido)

## Constraints

- Keep the change small and verifiable.
- Keep frontend untouched.
- No migrations.
- No annual ranking implementation.
- No Elo/MMR reactivation.
- No Comunidad Hispana #03 behavior reintroduction.
- No historical worker changes.
- Do not modify `frontend/assets/js/partida-actual.js`.
- Do not create unnecessary abstractions beyond this endpoint.
- If `/ai/` is partially ignored by git-exclude, document traceability impact only.

## Validation

Before considering the task complete:

- Run `scripts/run-integration-tests.ps1`.
- Run relevant backend tests if they exist for stats/player or historical materialized reads.
- If no dedicated tests exist for this endpoint, run manual validation with `curl` or `Invoke-WebRequest`.
- Validate `git diff --name-only` and check that only expected files were changed.
- Move task to `ai/tasks/done` on completion, or to `ai/tasks/review` if human validation is required.

## Outcome (for worker)

Document:

- endpoint contract implemented and observed behavior
- SQL/search strategy used (scope, match logic, ordering, fallback behavior)
- validation command results
- whether `servers_seen` was included and why
- any schema/data limitations found
- any blocker from git tracking (`/ai/` ignore behavior) and impact on traceability if relevant

## Change Budget

- Prefer <5 modified files.
- Prefer <200 added/changed lines per file when feasible.
- Split into follow-up tasks if the scope starts expanding.
