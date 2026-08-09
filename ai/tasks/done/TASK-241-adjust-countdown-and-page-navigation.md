---
id: TASK-241
title: Adjust countdown and page navigation
status: done
type: frontend
team: Frontend Senior
supporting_teams:
  - Experto en interfaz
roadmap_item: foundation
priority: medium
---

# TASK-241 - Adjust countdown and page navigation

## Goal

Apply the requested visual cleanup to the home countdown and align `partida-actual.html` and `historico-partida.html` with the existing public navigation pattern.

## Context

The countdown copy needed to move into the green capsule without duplicating the heading below it. The current-match page still had redundant hero buttons after the shared top navigation was added. The historical match detail page still lacked the shared top navigation and kept a local back button.

## Steps

1. Reviewed the existing public nav markup and countdown block.
2. Updated the home countdown markup and capsule styling.
3. Removed redundant hero buttons from current match and added the shared nav to historical match detail.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `frontend/index.html`
- `frontend/partida-actual.html`
- `frontend/historico-partida.html`

## Expected Files to Modify

- `frontend/index.html`
- `frontend/assets/css/styles.css`
- `frontend/partida-actual.html`
- `frontend/historico-partida.html`

## Constraints

- No backend changes for this task.
- No assets, weapons, SVGs or clan images.
- Do not touch the weapon icon system.
- Keep the countdown target at `2026-08-13T00:00:00+02:00`.

## Validation

- `node --check frontend/assets/js/main.js` if touched
- `node --check frontend/assets/js/partida-actual.js` if touched
- `node --check frontend/assets/js/historico-partida.js` if touched
- `git diff --name-only`

## Outcome

- The countdown capsule now contains the full launch text and the duplicate white heading was removed.
- `partida-actual.html` keeps the shared top navigation and the public scoreboard button, but no longer repeats `VOLVER INICIO` or `ABRIR HISTORICO` inside the hero.
- `historico-partida.html` now uses the same shared top navigation and no longer shows `VOLVER HISTORICO`.
- No weapon icons, weapon assets or backend code were touched for this task.

## Change Budget

- Stayed within a small, HTML/CSS-only frontend scope.
