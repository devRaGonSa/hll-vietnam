---
id: TASK-232
title: Audit and fix weapon icon assets and RCON mapping
status: done
type: frontend
team: Frontend Senior
supporting_teams: []
roadmap_item: foundation
priority: high
---

# TASK-232 - Audit and fix weapon icon assets and RCON mapping

## Goal

Use the current local SVG files from `frontend/assets/img/weapons/black/` for weapon icons shown in current match and historical weapon views, avoid broken/legacy asset references, and document covered and pending RCON names.

## Context

The local `black/` weapon icon folder changed substantially: new SVGs were added and several old typo filenames were deleted or renamed. The frontend needed to keep using the local black SVG set and avoid legacy bad-quality or missing paths.

## Files Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/frontend-senior.md`
- `frontend/assets/js/current-match-weapon-icons.js`
- `frontend/assets/js/partida-actual.js`
- `frontend/assets/js/historico-partida.js`
- `frontend/partida-actual.html`
- `frontend/historico-partida.html`

## Expected Files Modified

- `frontend/assets/js/current-match-weapon-icons.js`
- `frontend/assets/js/partida-actual.js`
- `frontend/assets/js/historico-partida.js`
- `frontend/historico-partida.html`
- `frontend/assets/css/historico.css`
- `scripts/validate-weapon-icon-mapping.js`
- `docs/WEAPON_ICON_MAPPING_AUDIT.md`
- this task file

## Changes

1. Removed the operational `weapons/white/` fallback map from `partida-actual.js`.
2. Kept current match kill feed resolution on the shared `black/` runtime resolver.
3. Added aliases for `FG42 x4` variants and `MP 40`.
4. Removed legacy typo alias strings from runtime JS: `flammenwefer41`, `m1 carabine`, `panzerchreck`.
5. Loaded `current-match-weapon-icons.js` in `historico-partida.html`.
6. Rendered local black weapon icons in historical player detail sections for `top_weapons` and `death_by`.
7. Added CSS for historical weapon icon rows.
8. Added `scripts/validate-weapon-icon-mapping.js` to validate declared SVGs, mapped SVGs and forbidden legacy terms.
9. Created `docs/WEAPON_ICON_MAPPING_AUDIT.md`.

## Asset Inventory

- Current local SVG count in `frontend/assets/img/weapons/black/`: 123.
- Modified tracked SVGs: 29 existing files.
- Deleted tracked typo/obsolete SVGs: 9 files.
- New/untracked local SVGs: 94 files.
- Duplicate by hash: `lee_enfield_jungle_carbine_black.svg` and `rifle_no5_mk_i_black.svg`.

Corrected local filenames now used include:

- `browning_m1919_black.svg`
- `m1_carbine_black.svg`
- `panzerschreck_black.svg`
- `flammenwerfer41_black.svg`
- `mosin_nagant_1891_black.svg`
- `mosin_nagant_9130_black.svg`
- `mosin_nagant_m38_black.svg`

## RCON/API Names Reviewed

Production endpoints sampled:

- `/api/current-match/kills` for `comunidad-hispana-01`
- `/api/current-match/kills` for `comunidad-hispana-02`
- `/api/current-match/players` for `comunidad-hispana-01`
- `/api/current-match/players` for `comunidad-hispana-02`
- `/api/historical/matches/detail?server=comunidad-hispana-01&match=1781023156:1781028555:purpleheartlanewarfare`

The endpoints responded but did not expose weapon names in the sampled payloads at audit time. Coverage is therefore based on the repository RCON universe already implemented in `CURRENT_MATCH_RCON_WEAPON_ICON_ENTRIES`.

Representative covered names include `GEWEHR 43`, `KARABINER 98K`, `KARABINER 98K x8`, `FG42`, `FG42 x4`, `M1 GARAND`, `M1 CARBINE`, `BROWNING M1919`, `STG44`, `MP40`, `MG42`, `BAZOOKA`, `PANZERSCHRECK`, `PIAT`, `BOMBING RUN`, `STRAFING RUN`, `SATCHEL`, `PRECISION STRIKE`, `UNKNOWN`, common mines, grenades, trucks, jeeps, half-tracks, tanks and mounted cannons.

## Pending Without Dedicated Icon

These names are covered by controlled fallback mappings but still lack dedicated icons:

- `UNKNOWN`
- `MOLOTOV`
- `No.77`
- `Daimler`
- `GAZ-67`
- `DP-27`
- `FairbairnSykes`
- `122MM HOWITZER [M1938 (M-30)]`
- `150MM HOWITZER [sFH 18]`
- `155MM HOWITZER [M114]`

## Validation

Passed:

```powershell
node --check frontend/assets/js/current-match-weapon-icons.js
node --check frontend/assets/js/partida-actual.js
node --check frontend/assets/js/historico-partida.js
node scripts/validate-weapon-icon-mapping.js
```

Also reviewed:

```powershell
git status --short --untracked-files=all
git diff --name-only
```

## Outcome

The current match kill feed and historical match detail weapon lists now use the shared local black SVG resolver. No runtime mapping points to missing SVGs. The old white-path fallback and legacy typo asset filenames are no longer used by frontend JS.

No backend, RCON configuration, server ports, `27001`, Elo/MMR, Comunidad Hispana #03, clan assets, `tmp/`, `black - copia/`, `black.zip` or `ai/system-metrics.md` were touched by this task.
