---
id: TASK-190-design-weekly-monthly-ranking-snapshots
title: Design weekly monthly ranking snapshots
status: pending
type: documentation
team: Arquitecto de Base de Datos
supporting_teams:
  - Backend Senior
  - PM
roadmap_item: foundation
priority: high
---

# TASK-190 - Design weekly monthly ranking snapshots

## Goal

Design a weekly/monthly ranking snapshot read model, equivalent in philosophy to the annual snapshot model, so public ranking requests do not depend on expensive runtime aggregation.

## Context

Annual ranking already follows a snapshot-backed read path, but weekly/monthly public ranking still depends on runtime aggregation over materialized match stats. HLL Vietnam needs a documented snapshot model for weekly and monthly ranking windows that preserves the current RCON-first policy, keeps annual behavior intact and defines a controlled fallback strategy during transition.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Read the listed files first.
2. Use the performance audit and the annual snapshot runbook as reference points.
3. Define the proposed tables, keys, metadata and item payload needed for weekly/monthly ranking snapshots.
4. Define refresh cadence and lifecycle rules for current and closed windows.
5. Define the public fallback policy without reintroducing heavy recomputation on every request.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `docs/ranking-stats-performance-audit.md`
- `docs/global-ranking-page-plan.md`
- `docs/annual-ranking-snapshot-runbook.md`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/rcon_annual_rankings.py`

## Expected Files to Modify

- `docs/ranking-snapshot-read-model-plan.md`
- `ai/tasks/done/TASK-190-design-weekly-monthly-ranking-snapshots.md`

## Constraints

- Documentación-only.
- No modificar backend.
- No modificar frontend.
- No crear migraciones.
- No implementar snapshots todavía.
- No reactivar Elo/MMR.
- No reintroducir Comunidad Hispana #03.
- Mantener el diseño alineado con Python backend y con el snapshot anual existente.

## Validation

Before completing the task ensure:

- the plan defines `ranking_snapshots`
- the plan defines `ranking_snapshot_items`
- the model covers:
  - `timeframe` weekly/monthly/annual
  - `server_id`
  - `metric`
  - `window_start` and `window_end`
  - `generated_at`
  - `source`
  - `snapshot_status`
  - `item_count`
  - `limit_size`
  - `ranking_position`
  - `player_id`
  - `player_name`
  - `metric_value`
  - `matches_considered`
  - `kills`
  - `deaths`
  - `teamkills`
  - `kd_ratio`
  - `kills_per_match`
- the refresh policy is explicit:
  - weekly current every 5-15 minutes
  - monthly current every 15-30 minutes
  - previous week/month closed and stable
  - annual manual or daily
- the fallback policy is explicit:
  - serve snapshot if present
  - return controlled missing or use runtime fallback only by configuration if missing
  - never recalculate by default on every public request
- the plan names impacted endpoints and expected response metadata
- `git diff --name-only` stays within scope

## Outcome

Document:

- the proposed read-model schema
- refresh policy
- fallback policy
- transition notes for implementation in `TASK-191`

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
