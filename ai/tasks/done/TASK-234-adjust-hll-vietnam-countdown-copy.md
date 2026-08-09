---
id: TASK-234
title: Adjust HLL Vietnam countdown copy
status: done
type: frontend
team: Frontend Senior
supporting_teams: []
roadmap_item: foundation
priority: low
---

# TASK-234 - Adjust HLL Vietnam countdown copy

## Goal

Adjust the public home countdown copy without changing the countdown target, position or behavior.

## Context

The home countdown already exists below the main trailer video. The visible copy needed to remove the extra objective line and make the section title explicit.

## Files Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/frontend-senior.md`
- `frontend/index.html`
- `frontend/assets/js/main.js`

## Changes

1. Changed the countdown heading to `Fecha de lanzamiento de Hell Let Loose Vietnam (13 de agosto)`.
2. Removed the visible `Objetivo: 13 de agosto de 2026.` line from the countdown block.
3. Updated the countdown JS so it no longer restores `Objetivo:` into a status node before the target date.
4. Preserved the target date `2026-08-13T00:00:00+02:00`.
5. Preserved the days, hours, minutes and seconds counter.

## Validation

- `node --check frontend/assets/js/main.js`
- Confirmed `Objetivo:` no longer appears in `frontend/index.html` or `frontend/assets/js/main.js`.
- Confirmed the exact heading appears in `frontend/index.html`.
- Confirmed the countdown still uses `window.setInterval(..., 1000)`.

## Outcome

The home countdown now presents the release date as the main section title and keeps the existing frontend-only countdown logic.

No backend, assets, weapon assets, clan assets, SVGs, physical images, `tmp/`, `ai/system-metrics.md`, RCON settings, `27001`, Elo/MMR or Comunidad Hispana #03 handling were changed.
