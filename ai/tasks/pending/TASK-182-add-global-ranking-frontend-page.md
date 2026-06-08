---
id: TASK-182-add-global-ranking-frontend-page
title: Add global ranking frontend page
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

# TASK-182-add-global-ranking-frontend-page - Add global ranking frontend page

## Goal

Create a dedicated Ranking page/section that displays global top lists by timeframe, server, metric, and limit, consuming the backend support built in TASK-181.

## Context

This page must be separated from Stats and focused on list-level ranking discovery (global leaders), while clearly linking to Stats for individual player lookup.

## Steps

1. Read the listed files first.
2. Add `frontend/ranking.html` with controls for timeframe, server, metric, and limit.
3. Implement `frontend/assets/js/ranking.js` to call the global ranking endpoint and render rows.
4. Update shared styles in `frontend/assets/css/styles.css` as needed, preserving the project visual direction.
5. Wire ranking access from existing navigation (`frontend/index.html`) only if needed.
6. Add a minimal cross-link to Stats if useful and safe.
7. Document covered UI states and fallback behavior when backend is unavailable.

## Files to Read First

- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- docs/global-ranking-page-plan.md
- frontend/index.html
- frontend/historico.html
- frontend/stats.html
- frontend/assets/js/stats.js
- frontend/assets/css/styles.css
- backend/app/routes.py
- ai/tasks/done/TASK-181-add-global-ranking-backend-support.md

## Expected Files to Modify

- frontend/ranking.html
- frontend/assets/js/ranking.js
- frontend/assets/css/styles.css
- frontend/index.html, only if navigation needs update
- frontend/stats.html, only if minimal cross-link is required
- scripts/run-stats-validation.ps1 or new ranking validation script
- ai/tasks/done/TASK-182-add-global-ranking-frontend-page.md

## Constraints

- No backend modifications.
- No new endpoints.
- No database migrations.
- No Elo/MMR reactivation.
- No reintroduction of Comunidad Hispana #03.
- No frameworks; continue with vanilla HTML/CSS/JS.
- Preserve military/Vietnam/tactical/sober visual identity.
- Do not regress Stats behavior.
- Avoid duplicating complex Stats logic; reuse patterns where practical.

## Outcome

- Global ranking page created and consumable.
- Endpoint consumed and documented.
- Validation of UI states:
  - loading
  - backend offline
  - no data
  - annual snapshot missing
  - unsupported metric
  - controlled error
- Validation list and known limitations recorded.
- Recommended follow-up tasks (if any).

## Validation

- Run `node --check frontend/assets/js/ranking.js`.
- Run `node --check frontend/assets/js/stats.js`.
- Run `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`.
- Serve frontend with `python -m http.server` and verify HTTP 200 for:
  - `ranking.html`
  - `assets/js/ranking.js`
  - `stats.html`
- If backend is available, validate ranking calls against live endpoint.
- If backend is unavailable, validate UI offline state.
- Run `git diff --name-only` and verify scoped changes.

