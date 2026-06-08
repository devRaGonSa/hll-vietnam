---
id: TASK-186-polish-ranking-metric-ux-and-limits
title: Polish ranking metric UX and limits
status: pending
type: frontend
team: Frontend Senior
supporting_teams:
  - Experto en interfaz
  - Disenador grafico
  - Backend Senior
roadmap_item: foundation
priority: high
---

# TASK-186-polish-ranking-metric-ux-and-limits - Polish ranking metric UX and limits

## Goal

Update the `Ranking` page UX so it exposes the backend-supported metric set clearly, improves limit handling and error messaging, and preserves the separation between global tops and player-specific Stats.

## Context

The current Ranking UI is limited to `kills`, only exposes a small set of limits, and handles invalid `limit` through a generic error path. If backend metric expansion is delivered, the frontend must expose the new metric set safely, keep annual constraints clear, and improve the explanatory UX without changing backend architecture.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Read the listed files first.
2. Update `ranking.html`, `ranking.js` and styling only as needed to expose the supported Ranking metric set.
3. Allow selecting:
   - `kills`
   - `deaths`
   - `teamkills`
   - `matches_considered`
   - `kd_ratio`
   - `kills_per_match`
4. Make the UI clearly show:
   - the active metric
   - the active timeframe
   - the active server
5. If annual remains `kills`-only, hide, disable or clearly message unsupported annual metrics without breaking the flow.
6. Improve limit UX so the available UI limits are reasonable and aligned with backend constraints.
7. Add a clearer message for invalid `limit` if it arrives from manual URL or parameter manipulation.
8. Keep or improve the message for unsupported metric and unsupported timeframe.
9. Preserve the guidance that `Stats` is for one-player lookup and `Ranking` is for global tops.
10. Add only minimal cross-linking between `Ranking` and `Stats` if helpful and already aligned with existing page patterns.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `docs/global-ranking-page-plan.md`
- `frontend/ranking.html`
- `frontend/assets/js/ranking.js`
- `frontend/assets/css/styles.css`
- `frontend/stats.html`
- `frontend/assets/js/stats.js`
- `backend/app/routes.py`
- `ai/tasks/done/TASK-185-add-ranking-extra-metrics-backend-support.md`

## Expected Files to Modify

- `frontend/ranking.html`
- `frontend/assets/js/ranking.js`
- `frontend/assets/css/styles.css`
- `frontend/stats.html`
- `scripts/run-stats-validation.ps1`
- `ai/tasks/done/TASK-186-polish-ranking-metric-ux-and-limits.md`

## Constraints

- Do not modify backend files.
- Do not create endpoints.
- Do not modify the database.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Do not introduce frameworks.
- Keep HTML/CSS/JS vanilla.
- Maintain the military/Vietnam/tactical/sober visual identity.
- Do not break Stats.
- Do not duplicate complex logic unnecessarily.

## Validation

Before completing the task ensure:

- `node --check frontend/assets/js/ranking.js`
- `node --check frontend/assets/js/stats.js`
- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- serve frontend with `python -m http.server` and confirm HTTP `200` for:
  - `ranking.html`
  - `assets/js/ranking.js`
  - `stats.html`
  - `index.html`
- if local backend is available, validate real metric selection against the supported backend contract
- if backend is unavailable, validate the offline fallback path explicitly
- confirm `git diff --name-only` stays within scope

## Outcome

Document:

- metrics exposed in UI
- annual behavior in the UX
- UI limit choices
- error states covered
- validations executed
- recommended follow-ups, if any

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
