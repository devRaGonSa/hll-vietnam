---
id: TASK-208
title: Analyze weapon icons black folder mapping
status: done
type: research
team: Analista
supporting_teams: [Frontend Senior]
roadmap_item: foundation
priority: medium
---

# TASK-208 - Analyze weapon icons black folder mapping

## Goal

Build a reviewable mapping between the pasted RCON weapon universe and the SVG silhouettes currently present in `frontend/assets/img/weapons/black/`, without modifying SVG files or frontend behavior yet.

## Context

The repository already contains a large local set of black weapon silhouettes and an older partial frontend mapping in `frontend/assets/js/partida-actual.js`. Before implementing a new operational resolver, the project needs a full documentary matrix that:

- uses the pasted RCON source as truth for weapon names
- lists every current `black` SVG
- assigns every unique RCON weapon to an icon
- makes every `black` icon appear in the inverse table
- flags fallbacks and doubtful assignments explicitly

This task is analysis/documentation only. No backend, endpoint, JS runtime, image or SVG changes are allowed.

## Steps

1. Inspect the repository context, current weapon icon folder and current frontend alias mapping.
2. Consolidate the pasted RCON weapon lists into one unique weapon universe.
3. Cross-map that universe against the local `black` icon set and document exact/shared/fallback assignments.
4. Validate that no RCON weapon is left without an icon and no `black` icon is left out of the inverse table.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `ai/orchestrator/analyst.md`
- `frontend/assets/js/partida-actual.js`
- `frontend/assets/img/weapons/black/`

## Expected Files to Modify

- `docs/weapon-icon-black-mapping-analysis.md`
- `ai/tasks/done/TASK-208-analyze-weapon-icons-black-folder-mapping.md`

## Constraints

- Do not modify SVGs.
- Do not rename, delete or replace image files.
- Do not touch backend code, endpoints or scripts.
- Do not touch `ai/system-metrics.md`.
- Do not push.
- Keep the result documentary and reviewable.

## Validation

Before completing the task ensure:

- all unique RCON weapons have an assigned icon in the document
- all `frontend/assets/img/weapons/black/` SVGs appear in the inverse table
- `git diff --name-only` matches the expected scope
- `git status --short --untracked-files=all` confirms no SVGs were edited by this task

## Outcome

Files read:

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `ai/orchestrator/analyst.md`
- `frontend/assets/js/partida-actual.js`
- `frontend/assets/img/weapons/black/`
- `ai/tasks/done/TASK-159-current-match-feed-rollback-and-weapon-icons.md`
- `ai/tasks/done/TASK-135-fix-rcon-match-detail-faction-assets.md`
- pasted RCON source provided by the user

Result:

- Created `docs/weapon-icon-black-mapping-analysis.md`.
- Consolidated `220` unique RCON weapon names including `UNKNOWN`.
- Listed and mapped `123` current SVGs from `frontend/assets/img/weapons/black/`.
- Produced a full direct/shared/fallback matrix with no unmapped weapon and no omitted icon in the inverse table.

Key findings:

- `frontend/assets/js/partida-actual.js` only covers a subset of infantry weapons and uses several legacy filename forms such as `browing_m1919`, `flammenwefer41`, `m1_carabine`, `mosing_nagant_*`, `panzerchreck` and `sten_mk_v`.
- Several RCON entries need fallback handling because there is no exact silhouette in the current folder, especially `Daimler`, `GAZ-67`, `MOLOTOV`, `No.77`, towed howitzers and `UNKNOWN`.
- `lee_enfield_jungle_carbine_black.svg` and `rifle_no5_mk_i_black.svg` are identical by file hash and were documented separately because both names still matter at the RCON layer.

Validation performed:

- `git status --short --untracked-files=all` before work and at the end
- `git diff --name-only`
- programmatic validation inside the document generator that:
  - total unique weapons = `220`
  - total icons = `123`
  - mapped weapons = `220`
  - used icons = `123`
  - unused icons = `0`
  - missing weapons = `0`
- final generated counts:
  - direct assignments = `73`
  - shared assignments = `92`
  - fallback assignments = `55`
  - doubtful assignments (`confidence=low`) = `38`
  - shared icons = `46`

Scope confirmation:

- No SVG was modified.
- No backend file was touched.
- No push was made.

## Change Budget

- Modified files: 2
- This task stayed in documentation scope and did not expand into frontend implementation.
