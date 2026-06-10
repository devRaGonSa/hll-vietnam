---
id: TASK-219
title: Restore BxB clan logo standard size
status: done
type: frontend
team: Frontend Senior
supporting_teams: []
roadmap_item: foundation
priority: medium
---

# TASK-219 - Restore BxB clan logo standard size

## Goal

Restore the visual size of the BxB logo on the index page so it is equivalent to the other clan logos.

## Context

TASK-210 gave BxB a special larger visual treatment. The current request is to return BxB to the original or equivalent standard clan logo sizing without modifying the physical PNG or unrelated assets.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Inspect the listed files first.
2. Locate the BxB-specific clan card and logo rules.
3. Remove or neutralize only the CSS treatment that makes BxB larger than the standard clan logos.
4. Validate the local index page visually and confirm the change scope.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `ai/orchestrator/frontend-senior.md`
- `frontend/index.html`
- `frontend/assets/css/styles.css`
- `frontend/assets/js/main.js`

## Expected Files to Modify

- `frontend/assets/css/styles.css`
- `ai/tasks/in-progress/TASK-219-restore-bxb-clan-logo-standard-size.md`

## Constraints

- Keep the change minimal.
- Prefer CSS-only.
- Do not modify physical images.
- Do not touch `frontend/assets/img/clans/`.
- Do not touch weapon assets or SVGs.
- Do not touch backend files or endpoints.
- Do not touch `ai/system-metrics.md`.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Do not introduce frameworks or dependencies.

## Validation

Before completing the task ensure:

- Inspect the local `frontend/index.html` page visually.
- Confirm BxB has a standard or equivalent logo size compared with the other clan logos.
- Run `node --check frontend/assets/js/main.js` only if JavaScript changes are made.
- Review `git diff --name-only`.
- Confirm changed files match the expected scope.
- Confirm backend, endpoints, assets, SVGs and `ai/system-metrics.md` were not modified by this task.

## Outcome

Completed.

- Removed the BxB-specific clan brand grid override that gave the logo column a wider range than standard clan cards.
- Removed the BxB-specific logo container and image sizing overrides that increased its visual height.
- Kept the existing BxB classes in JavaScript untouched; they no longer enlarge the logo because there is no matching size override in CSS.
- Validated `frontend/index.html` locally with a Chrome headless screenshot opened from the file system. BxB now appears in a standard-size logo container comparable to the other clan cards.
- JavaScript was not modified, so `node --check frontend/assets/js/main.js` was not required.
- `git diff --name-only` was reviewed. The task change is limited to `frontend/assets/css/styles.css` plus this task file; pre-existing unrelated changes are present in `ai/system-metrics.md`, clan image assets and weapon SVG/assets.
- Confirmed this task did not modify backend files, endpoints, physical images, `frontend/assets/img/clans/`, weapon assets, SVGs or `ai/system-metrics.md`.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
