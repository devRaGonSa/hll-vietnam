---
id: TASK-242
title: Match countdown label capsule style
status: done
type: frontend
team: Frontend Senior
supporting_teams:
  - Experto en interfaz
roadmap_item: foundation
priority: low
---

# TASK-242 - Match countdown label capsule style

## Goal

Make the countdown label capsule in the home page reuse the same visual pattern as the `SERVIDORES PÚBLICOS` section capsule.

## Context

The countdown text already replaced the old duplicated heading, but its capsule styling had diverged from the section eyebrow component used elsewhere on the landing. The request was to align width, height, border, radius, padding and typography with the existing section capsule style.

## Steps

1. Reviewed the countdown markup and the `eyebrow eyebrow--section` pattern used in the home sections.
2. Replaced the countdown custom heading block with the shared capsule pattern.
3. Reduced CSS to preserve spacing while letting the shared eyebrow component own the capsule visuals.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `frontend/index.html`
- `frontend/assets/css/styles.css`

## Expected Files to Modify

- `frontend/index.html`
- `frontend/assets/css/styles.css`

## Constraints

- No backend changes.
- No asset, SVG or image changes.
- No countdown logic changes.
- Keep the target date `2026-08-13T00:00:00+02:00`.

## Validation

- Confirm the countdown capsule matches the `SERVIDORES PÚBLICOS` visual pattern.
- Confirm `Objetivo:` does not return.
- Confirm no duplicate white title exists below the capsule.
- Confirm the counter remains below the capsule and keeps working.
- Review `git diff --name-only`.

## Outcome

- The countdown label now uses the shared `eyebrow eyebrow--section` component.
- The capsule width and visual treatment now match the public sections instead of using a custom full-width block.
- No JS, backend, navigation, weapon icons or assets were touched.

## Change Budget

- Stayed within a two-file frontend adjustment plus task documentation.
