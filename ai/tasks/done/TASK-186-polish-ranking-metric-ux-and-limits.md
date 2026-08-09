---
id: TASK-186-polish-ranking-metric-ux-and-limits
title: Polish ranking metric UX and limits
status: done
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

Metrics exposed in Ranking UI:

- `kills`
- `deaths`
- `teamkills`
- `matches_considered`
- `kd_ratio`
- `kills_per_match`

Frontend UX changes delivered:

- `frontend/ranking.html` now exposes the expanded metric selector and wider limit options.
- the ranking table now highlights the active metric dynamically while still showing the core supporting stats (`kills`, `deaths`, `teamkills`, `matches_considered`, `kd_ratio`, `kills_per_match`)
- the metadata strip now shows the active timeframe, active server, active metric, limit, window and source more explicitly
- `frontend/assets/js/ranking.js` now restores filter state from URL parameters and keeps the URL synced as filters change
- `frontend/stats.html` now includes a minimal direct link back to `Ranking`

Annual behavior in the UX:

- annual keeps `kills` as the only selectable active metric
- when the user switches to annual, non-snapshot-safe metrics are disabled in the selector
- the page shows an explicit note that annual remains `kills`-only until additional safe snapshots exist
- annual unsupported-metric and missing-snapshot states remain clearly differentiated

UI limit choices:

- `Top 5`
- `Top 10`
- `Top 20`
- `Top 50`
- `Top 100`

Error and state coverage improved:

- dedicated invalid-limit message for manual URL or parameter manipulation
- dedicated annual kills-only warning
- preserved unsupported metric message
- preserved unsupported timeframe message
- preserved backend offline fallback path
- preserved annual snapshot missing state
- preserved empty-ready states

Validation updates:

- `scripts/run-stats-validation.ps1` now asserts the new Ranking metric options, annual kills-only guidance, URL-state handling and the Stats-to-Ranking link

Validations executed:

- `node --check frontend/assets/js/ranking.js`
- `node --check frontend/assets/js/stats.js`
- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- temporary static serving with `python -m http.server 8081`
- confirmed HTTP `200` for:
  - `ranking.html`
  - `assets/js/ranking.js`
  - `stats.html`
  - `index.html`

Validation notes:

- local backend HTTP validation at `http://127.0.0.1:8000` was unavailable during the run
- offline fallback behavior was therefore validated through the existing frontend logic plus route-contract checks from the shared validation script

Scope notes:

- task-owned frontend changes stayed within:
  - `frontend/ranking.html`
  - `frontend/assets/js/ranking.js`
  - `frontend/assets/css/styles.css`
  - `frontend/stats.html`
  - `scripts/run-stats-validation.ps1`
- `git diff --name-only` also shows previous-task backend/docs changes and an unrelated existing workspace change:
  - moved task files from `TASK-184` / `TASK-185` / `TASK-186`
  - `backend/app/*` and `docs/global-ranking-page-plan.md` from prior tasks in this run
  - `frontend/assets/img/weapons/black/gewehr_black.svg`
- those files were not modified as part of this frontend task.

Recommended follow-ups:

- if a live backend session becomes available, run an explicit browser-side validation pass for every supported metric against real responses
- if annual extra metrics are introduced later, keep the current UX branch but switch from disabled options to active snapshot-backed support only when backend snapshots exist.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
