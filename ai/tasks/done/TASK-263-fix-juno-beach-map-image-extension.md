---
id: TASK-263
title: Fix Juno Beach map image extension
status: done
type: frontend
team: Frontend Senior
supporting_teams: []
roadmap_item: foundation
priority: medium
---

# TASK-263 - Fix Juno Beach map image extension

## Goal

Ensure the Juno Beach day map image resolves to an existing `.webp` asset so `/assets/img/maps/junobeach-day.webp` stops returning 404 after deployment.

## Context

The current match page can resolve Juno Beach day to:

- `./assets/img/maps/junobeach-day.webp`

The reported filesystem mismatch was:

- existing incorrect file: `frontend/assets/img/maps/junobeach-day.web`
- expected file: `frontend/assets/img/maps/junobeach-day.webp`

The map image resolver already emits `.webp` paths, so the scoped correction is the asset extension only.

## Steps

1. Read repository context and frontend role guidance.
2. Inspect the map resolver and current match page references.
3. Confirm the Juno Beach asset extension in `frontend/assets/img/maps`.
4. Search for other `.web` files in the maps directory.
5. Validate the task scope and document the result.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/frontend-senior.md`
- `frontend/assets/js/map-image-resolver.js`
- `frontend/partida-actual.html`

## Expected Files to Modify

- `frontend/assets/img/maps/junobeach-day.web` -> `frontend/assets/img/maps/junobeach-day.webp`
- `ai/tasks/done/TASK-263-fix-juno-beach-map-image-extension.md`

## Constraints

- Do not change the map resolver unless necessary.
- Do not change JavaScript.
- Do not touch other maps unless more `.web` files are detected in `frontend/assets/img/maps`.
- Do not touch weapons, clans, brands or other assets.
- Do not touch backend, scheduler, RCON, TeamKills, server configuration, port `27001`, Elo/MMR, Comunidad Hispana #03 or `ai/system-metrics.md`.
- Do not include `tmp/` or unrelated prior changes.
- Do not commit or push.

## Validation

- `git status --short --untracked-files=all -- frontend/assets/img/maps`
- `Test-Path frontend/assets/img/maps/junobeach-day.webp`
- `Test-Path frontend/assets/img/maps/junobeach-day.web`
- `Get-ChildItem frontend/assets/img/maps -Filter *.web`
- `git diff --name-only`

## Outcome

At execution time, `frontend/assets/img/maps/junobeach-day.web` was already absent and `frontend/assets/img/maps/junobeach-day.webp` was present. No JavaScript or resolver changes were needed.

No other `.web` files were found under `frontend/assets/img/maps`.

Validation results:

- `git status --short --untracked-files=all -- frontend/assets/img/maps` showed untracked map `.webp` assets already present in the worktree, including `frontend/assets/img/maps/junobeach-day.webp`.
- `Test-Path frontend/assets/img/maps/junobeach-day.webp` returned `True`.
- `Test-Path frontend/assets/img/maps/junobeach-day.web` returned `False`.
- `Get-ChildItem frontend/assets/img/maps -Filter *.web` returned no files.
- `git diff --name-only` showed only pre-existing tracked changes outside this task: `ai/system-metrics.md`, `frontend/assets/img/clans/250hispania-shield.png`, and `frontend/assets/img/clans/250hispania.png`.

Deployment/browser validation remains to be performed after the asset changes are deployed:

- `GET https://comunidadhll.devzamode.es/assets/img/maps/junobeach-day.webp` should return `200`.
- `/partida-actual.html?server=comunidad-hispana-01` should not log a 404 for `junobeach-day.webp`.

## Change Budget

- Modified files: 1 documentation file.
- Asset state confirmed in `frontend/assets/img/maps`.
- No backend, scheduler, RCON, server configuration or unrelated assets changed.
