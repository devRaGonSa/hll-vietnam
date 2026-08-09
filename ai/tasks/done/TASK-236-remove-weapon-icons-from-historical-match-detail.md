---
id: TASK-236
title: Remove weapon icons from historical match detail
status: done
type: frontend
team: Frontend Senior
supporting_teams:
  - Analista
roadmap_item: foundation
priority: low
---

# TASK-236 - Remove weapon icons from historical match detail

## Goal

Remove weapon icon rendering from `historico-partida.html` while keeping the textual player-detail stats intact.

## Context

The historical match detail page was loading `current-match-weapon-icons.js` and rendering weapon images inside the expanded player panel for `Armas`, `Mas abatido` and `Muere por`. The requirement for this page is text-only historical detail.

## Files Read First

- `frontend/historico-partida.html`
- `frontend/assets/js/historico-partida.js`
- `frontend/assets/css/historico.css`
- `frontend/partida-actual.html`

## Changes

1. Removed the `current-match-weapon-icons.js` script include from `frontend/historico-partida.html`.
2. Removed historical weapon icon rendering from `frontend/assets/js/historico-partida.js`.
3. Kept textual name and count rendering for weapon-related sections.
4. Removed now-unused historical weapon icon CSS from `frontend/assets/css/historico.css`.
5. Kept live current-match weapon icons untouched because they belong to `partida-actual.html`.

## Validation

- `node --check frontend/assets/js/historico-partida.js`
- Confirmed `historico-partida.html` no longer loads `current-match-weapon-icons.js`.
- Confirmed the historical player detail still renders `Armas`, `Mas abatido` and `Muere por` as text-only lists.
- Confirmed no SVG, weapon asset, clan asset or physical image file was modified.

## Outcome

The historical match detail page no longer renders weapon images at any point, but it preserves the textual stats and expandable player detail workflow.
