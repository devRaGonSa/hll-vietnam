---
id: TASK-238
title: Localize all servers visible labels
status: done
type: frontend
team: Frontend Senior
supporting_teams:
  - Analista
roadmap_item: foundation
priority: low
---

# TASK-238 - Localize all servers visible labels

## Goal

Remove visible `all servers` style labels from the public UI and standardize them as `Todos los servidores` without changing internal slugs or query parameters.

## Files Read First

- `frontend/assets/js/ranking.js`
- `frontend/assets/js/historico.js`
- `frontend/historico.html`
- `frontend/ranking.html`

## Changes

1. Updated the historical selector label for `all-servers` to `Todos los servidores`.
2. Updated the ranking server select option for `all` to `Todos los servidores`.
3. Updated the shared historical server label map so titles and summaries use `Todos los servidores`.
4. Kept internal technical values untouched:
   - `all-servers`
   - `all`

## Validation

- Reviewed visible frontend labels for:
  - `all servers`
  - `All servers`
  - `all-servers`
- Confirmed the updated UI copy is Spanish-facing only.
- Confirmed no endpoint, slug or query parameter changed.

## Outcome

The aggregate scope is still represented internally by `all-servers` / `all`, but the user-facing UI now uses `Todos los servidores`.
