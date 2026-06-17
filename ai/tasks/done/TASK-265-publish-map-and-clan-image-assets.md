---
id: TASK-265
title: Publish map and clan image assets
status: done
type: frontend
team: Frontend Senior
supporting_teams: []
roadmap_item: foundation
priority: high
---

# TASK-265 - Publish map and clan image assets

## Goal

Publish the map and clan image assets that the public frontend is already trying to load, so production stops returning 404 for known image URLs such as `/assets/img/maps/junobeach-day.webp`.

## Context

The frontend map resolver builds `.webp` paths under `./assets/img/maps/`. Several resolver variants were present in the working tree but not yet tracked. The current landing clan list also references `./assets/img/clans/250hispania-shield.png`.

This task is a publishing task only. It does not change frontend JavaScript, backend code, scheduler behavior, RCON configuration, server configuration, Elo/MMR, TeamKills or `Comunidad Hispana #03`.

## Steps

1. Audit pending map and clan image changes.
2. Check frontend references for maps and clans.
3. Confirm whether `250hispania.png` is still referenced.
4. Publish only scoped map/clan assets and related task docs.
5. Validate the staged commit scope before committing.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/frontend-senior.md`
- `frontend/assets/js/map-image-resolver.js`
- `frontend/assets/js/main.js`

## Expected Files to Modify

- `frontend/assets/img/maps/*.webp`
- `frontend/assets/img/clans/250hispania-shield.png`
- `frontend/assets/img/clans/250hispania.png`
- `ai/tasks/done/TASK-263-fix-juno-beach-map-image-extension.md`
- `ai/tasks/done/TASK-265-publish-map-and-clan-image-assets.md`

## Constraints

- Do not execute `ai-platform run`.
- Do not touch backend, scheduler, RCON, port `27001`, server configuration, TeamKills, Elo/MMR or Comunidad Hispana #03.
- Do not touch `ai/system-metrics.md`.
- Do not include `tmp/`.
- Do not include `TASK-204` or `TASK-242`.
- Do not include `frontend/assets/img/weapons/` or `frontend/assets/img/brands/`.
- Do not use `git add .`.
- Do not include unrelated prior changes.

## Audit

Frontend map references:

- `frontend/historico-partida.html` loads `./assets/js/map-image-resolver.js`.
- `frontend/partida-actual.html` loads `./assets/js/map-image-resolver.js`.
- `frontend/assets/js/map-image-resolver.js` resolves map images to `./assets/img/maps/${mapId}-${environment}.webp` and `./assets/img/maps/unknown-${environment}.webp`.

Frontend clan references:

- `frontend/assets/js/main.js` references `./assets/img/clans/250hispania-shield.png`.
- No frontend reference to `./assets/img/clans/250hispania.png` was found.

Decision for `250hispania.png`:

- Delete `frontend/assets/img/clans/250hispania.png` from the published set because the frontend now references `250hispania-shield.png` and no remaining frontend references to the old filename were found.
- Publish the modified `frontend/assets/img/clans/250hispania-shield.png`.

## Maps Added

42 new map assets were pending and should be published:

- `frontend/assets/img/maps/carentan-dusk.webp`
- `frontend/assets/img/maps/carentan-night.webp`
- `frontend/assets/img/maps/carentan-rain.webp`
- `frontend/assets/img/maps/driel-dawn.webp`
- `frontend/assets/img/maps/driel-night.webp`
- `frontend/assets/img/maps/elalamein-dusk.webp`
- `frontend/assets/img/maps/elsenbornridge-dawn.webp`
- `frontend/assets/img/maps/elsenbornridge-dusk.webp`
- `frontend/assets/img/maps/elsenbornridge-night.webp`
- `frontend/assets/img/maps/foy-night.webp`
- `frontend/assets/img/maps/hill400-dusk.webp`
- `frontend/assets/img/maps/hill400-night.webp`
- `frontend/assets/img/maps/hurtgenforest-night.webp`
- `frontend/assets/img/maps/junobeach-dawn.webp`
- `frontend/assets/img/maps/junobeach-day.webp`
- `frontend/assets/img/maps/junobeach-night.webp`
- `frontend/assets/img/maps/kharkov-night.webp`
- `frontend/assets/img/maps/kursk-night.webp`
- `frontend/assets/img/maps/main-menu.webp`
- `frontend/assets/img/maps/mortain-dusk.webp`
- `frontend/assets/img/maps/mortain-night.webp`
- `frontend/assets/img/maps/mortain-overcast.webp`
- `frontend/assets/img/maps/omahabeach-dusk.webp`
- `frontend/assets/img/maps/purpleheartlane-dawn.webp`
- `frontend/assets/img/maps/purpleheartlane-day.webp`
- `frontend/assets/img/maps/purpleheartlane-night.webp`
- `frontend/assets/img/maps/remagen-day.webp`
- `frontend/assets/img/maps/remagen-night.webp`
- `frontend/assets/img/maps/smolensk-dusk.webp`
- `frontend/assets/img/maps/smolensk-night.webp`
- `frontend/assets/img/maps/stalingrad-day.webp`
- `frontend/assets/img/maps/stalingrad-dusk.webp`
- `frontend/assets/img/maps/stalingrad-night.webp`
- `frontend/assets/img/maps/stalingrad-overcast.webp`
- `frontend/assets/img/maps/stmariedumont-night.webp`
- `frontend/assets/img/maps/stmariedumont-rain.webp`
- `frontend/assets/img/maps/stmereeglise-dawn.webp`
- `frontend/assets/img/maps/stmereeglise-night.webp`
- `frontend/assets/img/maps/tobruk-dusk.webp`
- `frontend/assets/img/maps/unknown-day.webp`
- `frontend/assets/img/maps/unknown.webp`
- `frontend/assets/img/maps/utahbeach-night.webp`

## Clan Assets

Clan asset changes to publish:

- Modified: `frontend/assets/img/clans/250hispania-shield.png`
- Deleted: `frontend/assets/img/clans/250hispania.png`

No other clan files were pending in the initial scoped status.

## Validation

Pre-commit checks:

- `git status --short --untracked-files=all -- frontend/assets/img/maps frontend/assets/img/clans`
- `Get-ChildItem frontend/assets/img/maps -Recurse -Filter *.webp`
- `Get-ChildItem frontend/assets/img/clans -Recurse -Force`
- `rg -n "assets/img/maps|junobeach-day\.webp|map-image-resolver|frontend/assets/js/map-image-resolver\.js" frontend -S`
- `rg -n "assets/img/clans|250hispania\.png|250hispania-shield\.png|clan|shield" frontend -S`
- `Test-Path frontend/assets/img/maps/junobeach-day.webp`
- `Get-ChildItem frontend/assets/img/maps -Filter *.web`
- sample path checks for `junobeach-day.webp`, `junobeach-dawn.webp`, `junobeach-night.webp`, `stmariedumont-night.webp`, `purpleheartlane-day.webp`, `remagen-day.webp`, and `unknown.webp`
- `git diff --name-status -- frontend/assets/img/maps frontend/assets/img/clans`
- `git diff --cached --name-only`

Post-deploy public validation:

- `GET https://comunidadhll.devzamode.es/assets/img/maps/junobeach-day.webp` should return `200`.
- Open `/partida-actual.html?server=comunidad-hispana-01` and confirm map images no longer 404.
- Open the landing page and confirm the 250 Hispania clan shield loads from `assets/img/clans/250hispania-shield.png`.

## Outcome

The scoped publish set includes only map assets, clan assets and related task documentation. Weapons, brands, backend, scheduler, RCON, server configuration, `ai/system-metrics.md`, `tmp/`, `TASK-204` and `TASK-242` are excluded.

`TASK-263` is included because it directly documents the `junobeach-day.webp` extension fix included in this publish set.

## Change Budget

This task intentionally exceeds the usual small file count because it publishes a batch of static binary assets required by existing frontend URLs. No code behavior changes are included.
