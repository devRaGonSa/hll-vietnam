---
id: TASK-187-review-ranking-metric-expansion
title: Review ranking metric expansion
status: done
type: research
team: Analista
supporting_teams:
  - Backend Senior
  - Frontend Senior
roadmap_item: foundation
priority: medium
---

# TASK-187-review-ranking-metric-expansion - Review ranking metric expansion

## Goal

Review the implemented `Ranking global` metric expansion from `TASK-184`, `TASK-185` and `TASK-186` without adding new functionality.

## Context

The repository already shipped documentation, backend and frontend changes for expanded global ranking metrics. HLL Vietnam now needs a short post-implementation review to confirm that the documented contract, backend behavior, frontend behavior and validation coverage remain aligned before any further follow-up work.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Read the listed files first.
2. Review the documented and implemented ranking metric expansion without broadening scope.
3. Run the listed validations and document the result.
4. Record only review findings, confirmed behavior and follow-up notes if needed.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `docs/global-ranking-page-plan.md`
- `frontend/ranking.html`
- `frontend/assets/js/ranking.js`
- `frontend/assets/css/styles.css`
- `backend/app/routes.py`
- `backend/app/payloads.py`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/rcon_annual_rankings.py`
- `scripts/run-stats-validation.ps1`
- `ai/tasks/done/TASK-184-define-ranking-metric-expansion-contract.md`
- `ai/tasks/done/TASK-185-add-ranking-extra-metrics-backend-support.md`
- `ai/tasks/done/TASK-186-polish-ranking-metric-ux-and-limits.md`

## Expected Files to Modify

- `ai/tasks/done/TASK-187-review-ranking-metric-expansion.md`

## Constraints

- No añadir nuevas métricas.
- No cambiar diseño.
- No crear endpoints.
- No modificar base de datos.
- No cambiar lógica salvo bug menor evidente.
- Si hay hallazgos no triviales, documentarlos como follow-up y no ampliar scope.
- No incluir archivos fuera del scope de revisión.

## Validation

Before completing the task ensure:

- review `docs/global-ranking-page-plan.md` against implemented ranking behavior
- confirm weekly/monthly/annual metric support and annual safety boundaries
- confirm unsupported `metric`, unsupported `timeframe` and invalid `limit` still return controlled errors
- confirm the frontend metric selector, decimal handling, annual limitation messaging and fallback states still align with backend behavior
- confirm `scripts/run-stats-validation.ps1` covers the expanded ranking metrics without breaking Stats validation
- run:
  - `node --check frontend/assets/js/ranking.js`
  - `node --check frontend/assets/js/stats.js`
  - `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
  - `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- if the environment allows it, probe:
  - `/api/ranking?timeframe=weekly&metric=kills&limit=3`
  - `/api/ranking?timeframe=weekly&metric=deaths&limit=3`
  - `/api/ranking?timeframe=weekly&metric=teamkills&limit=3`
  - `/api/ranking?timeframe=weekly&metric=matches_considered&limit=3`
  - `/api/ranking?timeframe=weekly&metric=kd_ratio&limit=3`
  - `/api/ranking?timeframe=weekly&metric=kills_per_match&limit=3`
  - `/api/ranking?timeframe=monthly&metric=kd_ratio&limit=3`
  - `/api/ranking?timeframe=annual&metric=kills&limit=3`
  - `/api/ranking?timeframe=annual&metric=kd_ratio&limit=3`
  - `/api/ranking?timeframe=invalid&metric=kills&limit=3`
  - `/api/ranking?timeframe=weekly&metric=invalid&limit=3`
  - `/api/ranking?timeframe=weekly&metric=kills&limit=101`
- `git diff --name-only` stays within review scope

## Outcome

Review result:

- No blocking findings were identified for the implemented ranking metric expansion scope.
- `docs/global-ranking-page-plan.md` matches the implemented metric set and annual safety boundary.
- The implemented public metric set is confirmed as:
  - weekly: `kills`, `deaths`, `teamkills`, `matches_considered`, `kd_ratio`, `kills_per_match`
  - monthly: `kills`, `deaths`, `teamkills`, `matches_considered`, `kd_ratio`, `kills_per_match`
  - annual: `kills` only through snapshot-backed reads
- Annual requests remain snapshot-only and do not trigger runtime full-year recomputation in the public request path.
- Unsupported `metric`, unsupported `timeframe` and invalid `limit` continue to return controlled `400` responses.

Frontend review:

- `frontend/ranking.html` exposes the supported metric selector options.
- `frontend/assets/js/ranking.js` formats integer metrics through integer rendering and decimal metrics through fixed decimal rendering.
- Annual non-supported metrics are disabled in the selector and explicitly explained in the filter note and error state.
- The limit selector remains aligned with backend constraints through `5`, `10`, `20`, `50`, `100`, all within the backend `1..100` contract.
- Offline, controlled-error, empty-ready and annual-missing states remain explicitly handled.

Validation coverage review:

- `scripts/run-stats-validation.ps1` covers the expanded Ranking metrics, annual guardrail failures, invalid metric/timeframe/limit checks and existing Stats contracts.
- Existing Stats validation remains intact and passed during this review.

Route-resolution probes executed:

- `200`:
  - `/api/ranking?timeframe=weekly&metric=kills&limit=3`
  - `/api/ranking?timeframe=weekly&metric=deaths&limit=3`
  - `/api/ranking?timeframe=weekly&metric=teamkills&limit=3`
  - `/api/ranking?timeframe=weekly&metric=matches_considered&limit=3`
  - `/api/ranking?timeframe=weekly&metric=kd_ratio&limit=3`
  - `/api/ranking?timeframe=weekly&metric=kills_per_match&limit=3`
  - `/api/ranking?timeframe=monthly&metric=kd_ratio&limit=3`
  - `/api/ranking?timeframe=annual&metric=kills&limit=3&year=2026`
- `400`:
  - `/api/ranking?timeframe=annual&metric=kd_ratio&limit=3&year=2026`
  - `/api/ranking?timeframe=invalid&metric=kills&limit=3`
  - `/api/ranking?timeframe=weekly&metric=invalid&limit=3`
  - `/api/ranking?timeframe=weekly&metric=kills&limit=101`

Validations executed:

- `node --check frontend/assets/js/ranking.js`
- `node --check frontend/assets/js/stats.js`
- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`

Validation notes:

- Live backend HTTP validation at `http://127.0.0.1:8000` was not available during this review.
- Route and contract checks passed through local Python imports, so the remaining residual risk is limited to live-environment verification rather than contract drift.

Scope notes:

- The review remained scoped to the task file plus repository inspection and validation commands.
- No product code changes were made.

Follow-up:

- Optional future follow-up only if needed: rerun the same ranking probes against a live backend session to confirm HTTP behavior matches the local route-resolution checks.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
