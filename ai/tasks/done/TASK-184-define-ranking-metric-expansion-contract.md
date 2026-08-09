---
id: TASK-184-define-ranking-metric-expansion-contract
title: Define ranking metric expansion contract
status: done
type: documentation
team: Analista
supporting_teams:
  - PM
  - Backend Senior
  - Frontend Senior
  - Arquitecto de Base de Datos
  - Experto en interfaz
roadmap_item: foundation
priority: high
---

# TASK-184-define-ranking-metric-expansion-contract - Define ranking metric expansion contract

## Goal

Define the functional and technical contract for expanding `Ranking global` with additional metrics in V1.1 without reactivating Elo/MMR or introducing a new architecture.

## Context

The current Ranking implementation is limited to `kills`. The repository already has a dedicated Ranking route, an RCON materialized weekly/monthly read path, and an annual snapshot read path. Before backend or frontend expansion, HLL Vietnam needs explicit documentation that defines which extra metrics are safe, how they are calculated, what timeframes they support, and where annual support must remain constrained.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Read the listed files first.
2. Update the Ranking contract documentation for V1.1 metric expansion only.
3. Define the supported metrics and the formula or aggregation rule for each one.
4. Define expected ordering for each metric and clarify tie-break behavior.
5. Define supported timeframes per metric:
   - `weekly`
   - `monthly`
   - `annual`
6. Clarify the difference between weekly/monthly runtime reads and annual snapshot reads.
7. Clarify whether annual remains limited to `kills` or only allows additional metrics when a safe snapshot-backed read path already exists.
8. Define payload expectations and controlled error behavior for unsupported metrics.
9. Keep non-goals and source-policy restrictions explicit.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `docs/global-ranking-page-plan.md`
- `docs/stats-section-functional-plan.md`
- `docs/annual-ranking-snapshot-runbook.md`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/rcon_annual_rankings.py`
- `backend/app/routes.py`
- `backend/app/payloads.py`
- `ai/tasks/done/TASK-183-review-global-ranking-implementation.md`

## Expected Files to Modify

- `docs/global-ranking-page-plan.md`
- `ai/tasks/done/TASK-184-define-ranking-metric-expansion-contract.md`

## Constraints

- Documentation-only task.
- Do not modify backend files.
- Do not modify frontend files.
- Do not create migrations.
- Do not change scripts.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Do not define public scoreboard as the normal primary source while RCON is available.
- Do not expand annual behavior into runtime full-year recalculation on public requests.

## Validation

Before completing the task ensure:

- `docs/global-ranking-page-plan.md` explicitly documents V1.1 supported Ranking metrics
- the contract defines formulas for:
  - `kills`
  - `deaths`
  - `teamkills`
  - `matches_considered`
  - `kd_ratio`
  - `kills_per_match`
- the contract defines safe handling for:
  - `deaths=0`
  - `matches_considered=0`
- the contract defines expected ordering for each metric
- the contract defines timeframe support per metric and annual limitations explicitly
- unsupported-metric error behavior is documented
- non-goals remain explicit:
  - Elo/MMR
  - public scoreboard as primary source
  - large new tables
  - advanced charts
  - authentication
  - Comunidad Hispana #03
- `git diff --name-only` stays within task scope
- if automated tests do not apply because the task is documentation-only, that limitation is documented in the task outcome

## Outcome

Supported Ranking V1.1 metrics documented in `docs/global-ranking-page-plan.md`:

- `kills`
- `deaths`
- `teamkills`
- `matches_considered`
- `kd_ratio`
- `kills_per_match`

Formula and aggregation rules documented:

- `kills = SUM(kills)`
- `deaths = SUM(deaths)`
- `teamkills = SUM(teamkills)`
- `matches_considered = COUNT(DISTINCT match_key)`
- `kd_ratio = SUM(kills) / SUM(deaths)`
- `kills_per_match = SUM(kills) / COUNT(DISTINCT match_key)`

Safety rules documented:

- `deaths=0` returns finite display-safe `kd_ratio` using kills as the fallback value
- `matches_considered=0` returns `kills_per_match = 0`

Ordering and tie-break expectations documented:

- totals metrics sort by active metric desc, then stable tie-break fields
- `matches_considered` ties break on `kills` desc, then `player_name` asc
- ratio metrics tie-break on `kills` desc, `matches_considered` desc, `player_name` asc

Supported timeframes by metric documented:

- weekly: all V1.1 metrics through the materialized RCON runtime leaderboard
- monthly: all V1.1 metrics through the materialized RCON runtime leaderboard
- annual: snapshot-safe path only; `kills` required, extra metrics only if an explicit snapshot-backed read path exists

Annual snapshot limitations and safety rules documented:

- no runtime annual recomputation on public requests
- unsupported annual metrics must return controlled `400`
- until extra annual snapshots exist, annual remains effectively `kills`-only

Expected payload adjustments documented:

- `metric_value` remains the active display/sort field
- weekly/monthly payloads may include rounded ratio fields and `kills_per_match`
- annual payload shape remains stable and only expands when snapshot-backed safely

Controlled error behavior documented:

- unsupported metric, unsupported timeframe and unsupported annual metric must fail with controlled request-validation errors
- backend must not silently downgrade unsupported requests to `kills`

Validation performed:

- reviewed `docs/global-ranking-page-plan.md`
- reviewed `docs/stats-section-functional-plan.md`
- reviewed `docs/annual-ranking-snapshot-runbook.md`
- reviewed `backend/app/rcon_historical_leaderboards.py`
- reviewed `backend/app/rcon_annual_rankings.py`
- reviewed `backend/app/routes.py`
- reviewed `backend/app/payloads.py`
- reviewed `ai/tasks/done/TASK-183-review-global-ranking-implementation.md`
- confirmed `git diff --name-only` scope stays documentation-only for this task

Automated tests:

- No automated tests apply because this task remained documentation-only.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
