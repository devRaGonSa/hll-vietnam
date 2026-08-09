---
id: TASK-260
title: Normalize weapon icon asset heights
status: done
type: frontend
team: Disenador grafico
supporting_teams: []
roadmap_item: foundation
priority: medium
---

# TASK-260 - Normalize weapon icon asset heights

## Goal

Register the manual normalization of weapon icon assets so they render more consistently in the combat feed.

## Context

Weapon icons under `frontend/assets/img/weapons/` were manually normalized with a target maximum height of 250px. This keeps the combat feed visuals more predictable without changing frontend logic, CSS, backend behavior, RCON behavior, server configuration or unrelated assets.

## Steps

1. Inspect repository context and the graphic design role guidance.
2. Review the current Git status and isolate weapon asset changes from unrelated working tree changes.
3. Validate a representative SVG sample for reasonable `height` and `viewBox` values.
4. Stage only the normalized weapon assets and this task record.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/graphic-designer.md`
- `ai/task-template.md`

## Expected Files to Modify

- `frontend/assets/img/weapons/**`
- `ai/tasks/done/TASK-260-normalize-weapon-icon-asset-heights.md`

## Constraints

- Target maximum weapon icon height is 250px.
- Do not touch backend, RCON, scheduler, TeamKills, Elo/MMR, server configuration or port 27001.
- Do not touch assets outside weapons, including clans, maps or brands.
- Do not touch frontend JavaScript or CSS.
- Do not include `tmp/`, `ai/system-metrics.md`, `TASK-204` or unrelated tasks.

## Validation

- Ran `git status --short --untracked-files=all`.
- Ran `git status --short --untracked-files=all -- frontend/assets/img/weapons`.
- Ran `git diff --stat -- frontend/assets/img/weapons`.
- Reviewed representative SVG headers for:
  - `m1_garand_black.svg`
  - `kar98k_black.svg`
  - `gewehr_black.svg`
  - `mg42_black.svg`
  - `mp40_black.svg`
  - `m2_ap_mine_black.svg`
  - `panzerschreck_black.svg`
  - `pak_40_75mm_black.svg`
- Confirmed the staged scope contains only weapon assets and this task record.

## Outcome

The manually normalized weapon icon assets are documented with a 250px maximum target height. No assets outside weapons were included. Backend, RCON and server configuration were not touched.

Definitive visual validation remains pending in the current live match context with the real combat feed.
