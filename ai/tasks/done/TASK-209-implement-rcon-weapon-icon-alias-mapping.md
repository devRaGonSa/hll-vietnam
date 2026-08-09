---
id: TASK-209
title: Implement RCON weapon icon alias mapping
status: done
type: frontend
team: Frontend Senior
supporting_teams: [Analista]
roadmap_item: foundation
priority: high
---

# TASK-209 - Implement RCON weapon icon alias mapping

## Goal

Implement the full RCON weapon-to-icon mapping in frontend JavaScript using explicit aliases and the `frontend/assets/img/weapons/black/` icon set, without modifying SVG files.

## Context

`TASK-208` produced the reviewable mapping matrix between the pasted RCON weapon universe and the local `black` silhouettes. The runtime still uses an older partial `white/` mapping in `frontend/assets/js/partida-actual.js`, with legacy filenames and incomplete coverage.

This task applies the documented mapping in frontend code only:

- cover the 220 documented RCON weapons plus `UNKNOWN`
- use actual `black` SVG filenames
- preserve legacy/ambiguous cases through explicit aliases
- keep SVG files untouched

## Steps

1. Inspect the analysis document, current runtime resolver and actual `black` icon filenames.
2. Replace the partial runtime weapon mapping with the documented full alias mapping.
3. Add local validation that checks mapping coverage and that assigned icon filenames exist in `frontend/assets/img/weapons/black/`.
4. Update documentation with implementation notes and validation results.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `docs/weapon-icon-black-mapping-analysis.md`
- `ai/tasks/done/TASK-208-analyze-weapon-icons-black-folder-mapping.md`
- `frontend/assets/js/partida-actual.js`

## Expected Files to Modify

- `frontend/assets/js/current-match-weapon-icons.js`
- `frontend/assets/js/partida-actual.js`
- `frontend/partida-actual.html`
- `docs/weapon-icon-black-mapping-analysis.md`
- `ai/tasks/done/TASK-209-implement-rcon-weapon-icon-alias-mapping.md`

## Constraints

- Do not modify, rename, delete, replace or move SVG files.
- Do not touch backend code, endpoints or scripts.
- Do not touch `ai/system-metrics.md`.
- Do not push.
- Keep aliases explicit and reviewable.
- Use existing `black` filenames even when they are legacy or inconsistent.

## Validation

Before completing the task ensure:

- `node --check frontend/assets/js/partida-actual.js`
- a local script confirms all documented RCON names resolve to an existing `black` SVG or to the documented fallback UI path
- `git diff --name-only` matches the expected scope
- `git status --short --untracked-files=all` confirms no SVGs were modified by this task

## Outcome

Document:

- the JS file modified
- alias strategy used
- number of covered weapons
- implemented fallback cases
- validation results
- confirmation that no SVG or backend file was touched

Result:

- Added `frontend/assets/js/current-match-weapon-icons.js` with:
  - `123` real `black` filenames
  - `220` explicit RCON `weapon -> svg` entries
  - `120` legacy/colloquial aliases for runtime lookup
- Updated `frontend/partida-actual.html` to load the new runtime mapping before `partida-actual.js`.
- Updated `frontend/assets/js/partida-actual.js` so killfeed weapon resolution now prefers the complete `black` runtime mapping and falls back to the old local resolver only if the new asset is unavailable.
- Updated `docs/weapon-icon-black-mapping-analysis.md` with an `Implementación aplicada` section.

Validation performed:

- PASS: `node --check frontend/assets/js/partida-actual.js`
- PASS: `node --check frontend/assets/js/current-match-weapon-icons.js`
- PASS: local Node validation against the analysis document and runtime mapping:
  - `totalWeapons = 220`
  - `mappedWeapons = 220`
  - `totalIcons = 123`
  - `usedIcons = 123`
  - `aliasCount = 120`
  - `missingWeapons = 0`
  - `brokenIcons = 0`
  - `missingAliases = 0`
  - `unusedIcons = 0`
- PASS: reviewed `git diff --name-only`
- PASS: reviewed `git status --short --untracked-files=all`

Main implemented fallbacks:

- `UNKNOWN -> precision_strike_black.svg`
- `MOLOTOV -> rg42_grenade_black.svg`
- `No.77 -> no82_grenade_black.svg`
- `Daimler` and `QF 2-POUNDER [Daimler]` / `COAXIAL BESA [Daimler] -> m8_greyhound_black.svg`
- `GAZ-67 -> jeep_black.svg`
- `122MM HOWITZER [M1938 (M-30)] -> zis2_57mm_cannon_black.svg`
- `155MM HOWITZER [M114] -> m1_57mm_cannon_black.svg`
- `150MM HOWITZER [sFH 18] -> pak_40_75mm_black.svg`
- `FLAMETHROWER -> m2_flamethrower_black.svg`
- `FairbairnSykes -> m3_knife_black.svg`

Scope confirmation:

- No SVG was modified, renamed, deleted or replaced.
- No backend file, endpoint or backend script was touched.
- No push was made.

## Change Budget

- Prefer fewer than 5 modified files.
- Split follow-up cleanups, visual tuning or future icon creation into separate tasks.
