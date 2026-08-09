---
id: TASK-180-define-global-ranking-page-contract
title: Define global ranking page contract
status: done
type: documentation
team: Analista
supporting_teams:
  - PM
  - Backend Senior
  - Frontend Senior
  - Experto en interfaz
roadmap_item: foundation
priority: high
---

# TASK-180-define-global-ranking-page-contract - Define global ranking page contract

## Goal

Define a separate, explicit global ranking page contract that is clearly distinct from Stats, so product and engineering can execute backend and frontend ranking work independently.

## Context

Stats focuses on one player workflow (search and personal performance), while Ranking exposes public top lists. This task formalizes the Ranking contract, filters, payload shape and UI states needed for an incremental, RCON-first implementation.

## Steps

1. Read the listed files first.
2. Draft a concise, implementation-ready contract for Ranking.
3. Document how Ranking and Stats are separated and where they can share frontend patterns safely.
4. Define API expectations for weekly/monthly vs annual reads, including missing/ready/error behavior.
5. Keep constraints explicit.
6. Capture follow-up items and a clear next-task suggestion.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `docs/stats-section-functional-plan.md`
- `docs/annual-ranking-snapshot-runbook.md`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/rcon_annual_rankings.py`
- `frontend/stats.html`
- `frontend/assets/js/stats.js`

## Expected Files to Modify

- `docs/global-ranking-page-plan.md`
- `ai/tasks/done/TASK-180-define-global-ranking-page-contract.md`

## Constraints

- Documentation-only task.
- No backend implementation changes.
- No frontend implementation changes.
- No migrations or schema modifications.
- Keep the contract aligned with RCON-first architecture.
- No Elo/MMR reactivation.
- No reintroduction of Comunidad Hispana #03.
- No public-scoreboard as primary source when RCON coverage is available.

## Validation

- Confirm `docs/global-ranking-page-plan.md` exists.
- Confirm no backend/frontend files were modified.
- Run `git diff --name-only` within task scope.
- Document explicitly that no automated tests apply.

## Outcome

- Created `docs/global-ranking-page-plan.md`.
- Documented a dedicated `Ranking` page contract separate from `Stats`.
- Defined dedicated endpoint direction as `GET /api/ranking`.
- Documented timeframe behavior:
  - weekly/monthly from RCON materialized leaderboard reads
  - annual from persisted annual snapshots
- Documented required payload fields:
  - `ranking_position`
  - `player_id`
  - `player_name`
  - `metric_value`
  - `matches_considered`
  - `kills`
  - `deaths`
  - `teamkills`
  - `kd_ratio`
  - `window_start`
  - `window_end`
  - `snapshot_status`
- Documented required UI states:
  - loading
  - backend offline
  - no data
  - annual snapshot missing
  - unsupported metric
  - controlled error
- Explicitly preserved constraints:
  - no Elo/MMR
  - no Comunidad Hispana #03
  - no public-scoreboard primary path while RCON exists

Validation performed:

- Confirmed documentation file creation.
- Kept changes out of `backend/` and `frontend/`.
- Automated tests do not apply to this documentation-only task.

Recommended next task:

- `TASK-181-add-global-ranking-backend-support`
