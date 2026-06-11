---
id: TASK-235
title: Align current match page top navigation
status: done
type: frontend
team: Frontend Senior
supporting_teams: []
roadmap_item: foundation
priority: low
---

# TASK-235 - Align current match page top navigation

## Goal

Align `partida-actual.html` with the top navigation pattern used by the public pages.

## Context

The current match page had the contextual `VOLVER INICIO` button inside the hero, but it did not include the shared `public-nav` bar used by `index.html`, `historico.html`, `stats.html` and `ranking.html`.

## Files Read First

- `frontend/index.html`
- `frontend/historico.html`
- `frontend/historico-partida.html`
- `frontend/ranking.html`
- `frontend/stats.html`
- `frontend/partida-actual.html`

## Pattern Found

- Public pages use `<nav class="public-nav" aria-label="Navegación pública principal">` before the hero.
- The nav links are `Inicio`, `Histórico`, `Estadísticas` and `Ranking`.
- The detail pages also keep contextual hero actions such as `VOLVER HISTORICO` or `VOLVER INICIO`.

## Changes

1. Added the shared public navigation bar before the hero in `frontend/partida-actual.html`.
2. Kept the existing `VOLVER INICIO` hero button.
3. Kept the existing hero actions `Abrir historico` and `Ver scoreboard publico`.
4. Did not add CSS or JS because the existing `public-nav` classes already cover the layout.

## Validation

- Confirmed `partida-actual.html` keeps `VOLVER INICIO`.
- Confirmed `partida-actual.html` keeps `Marcador en curso`, map hero markup, `Abrir historico` and `Ver scoreboard publico`.
- Confirmed the new top navigation links point to existing public pages:
  - `./index.html`
  - `./historico.html`
  - `./stats.html`
  - `./ranking.html`

## Outcome

The current match page now matches the public top navigation pattern while preserving its current-match-specific hero controls.

No backend, assets, weapon assets, clan assets, SVGs, physical images, `tmp/`, `ai/system-metrics.md`, RCON settings, `27001`, Elo/MMR or Comunidad Hispana #03 handling were changed.
