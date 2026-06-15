---
id: TASK-258
title: Normalize current match weapon icon rendering
status: done
type: frontend
team: Frontend Senior
supporting_teams: []
roadmap_item: foundation
priority: medium
---

# TASK-258 - Normalize current match weapon icon rendering

## Goal

Normalize weapon icon rendering in the current match combat feed without modifying physical weapon assets.

## Context

The current match kill feed renders multiple weapon families with very different SVG proportions. The previous CSS used a flexible icon frame with `min-height` and forced image width, so rifles, MGs, mines, tanks/cannons and pistols could occupy inconsistent visual space across combat rows.

## Steps

1. Inspect the generated kill-feed markup in `frontend/assets/js/partida-actual.js`.
2. Inspect current CSS for `.current-match-killfeed__weapon*`.
3. Apply a layout-only fix with a fixed visual box, centered image and contained object fitting.
4. Validate syntax, static CSS rules, local visual behavior and public current-match endpoints.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/frontend-senior.md`
- `frontend/partida-actual.html`
- `frontend/assets/js/partida-actual.js`
- `frontend/assets/css/historico.css`

## Expected Files to Modify

- `frontend/assets/css/historico.css`
- `ai/tasks/done/TASK-258-normalize-current-match-weapon-icon-rendering.md`

## Constraints

- Do not run `ai-platform run`.
- Do not commit or push.
- Do not touch backend, scheduler, RCON, server config or port `27001`.
- Do not touch TeamKills behavior.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Do not touch physical weapon assets, weapon SVG/PNG files or `frontend/assets/img/weapons/`.
- Do not touch maps, clans, brands or `ai/system-metrics.md`.
- Do not include `tmp/`, `TASK-204` or unrelated previous changes.

## Validation

- `node --check frontend/assets/js/partida-actual.js` passed; the JS file was not modified by this task.
- Static CSS review confirmed the current match weapon icon now uses a fixed frame, centered grid placement and `object-fit: contain`.
- Chrome headless local validation ran against:
  `/partida-actual.html?server=comunidad-hispana-01`
  `/partida-actual.html?server=comunidad-hispana-02`
- Visual test events covered rifle, MG, mine, tank/cannon, pistol and long artillery labels.
- Chrome metrics for both servers:
  icon frame `96px x 36px`,
  weapon column `112px`,
  row height `72px`,
  all test images loaded,
  all images stayed inside the frame,
  `object-fit: contain`,
  labels used one-line ellipsis and stayed inside the weapon card.
- Public audit command executed:
  `python .\scripts\audit_public_requests.py --base-url https://comunidadhll.devzamode.es --timeout 30 --output tmp\task258_full_audit_after.json`
- Audit summary: `CRITICAL: 0`.
- Required current-match endpoints returned `OK 200`:
  `current-match-comunidad-hispana-01`,
  `current-match-comunidad-hispana-02`,
  `current-match-kills-comunidad-hispana-01`,
  `current-match-kills-comunidad-hispana-02`,
  `current-match-players-comunidad-hispana-01`,
  `current-match-players-comunidad-hispana-02`.

## Outcome

The visual inconsistency came from rendering different weapon asset aspect ratios inside a flexible frame and forcing image width instead of fitting each image inside a fixed visual box.

The fix is CSS-only in `frontend/assets/css/historico.css`, because `partida-actual.html` loads that stylesheet for the current match feed. The generated HTML already had stable classes, so `frontend/assets/js/partida-actual.js` did not need changes.

Final desktop icon box: `96px x 36px`. The weapon card column is `112px`; mobile uses a reduced `72px x 32px` icon frame inside a `92px` weapon column.

No physical weapon assets, SVGs, PNGs, backend files, scheduler, RCON, server configuration, maps, clans, brands, TeamKills, Elo/MMR, Comunidad Hispana #03 or `ai/system-metrics.md` were changed.

