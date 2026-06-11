---
id: TASK-244
title: Match countdown label width to section eyebrow
status: done
type: frontend
team: Frontend Senior
supporting_teams:
  - Experto en interfaz
roadmap_item: foundation
priority: low
---

# TASK-244 - Match countdown label width to section eyebrow

## Goal

Make the countdown label capsule keep the section eyebrow appearance without stretching to full width.

## Context

The countdown text already reused the same visual component as `SERVIDORES PUBLICOS`, but its wrapper was still stretching across the full width of the countdown container because the parent is a vertical flex layout.

## Steps

1. Reviewed the countdown wrapper and the section eyebrow pattern.
2. Constrained the countdown label wrapper to its content width.
3. Rechecked that the counter remains below the label and no duplicate title returns.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `frontend/index.html`
- `frontend/assets/css/styles.css`

## Expected Files to Modify

- `frontend/assets/css/styles.css`

## Constraints

- No backend changes.
- No asset or image changes.
- No countdown logic changes.
- No navigation changes.

## Validation

- Confirm the label no longer uses full-width layout.
- Confirm it still uses the same section eyebrow pattern.
- Confirm `Objetivo:` does not return.
- Confirm the counter stays below the label.
- Review `git diff --name-only`.

## Outcome

- The countdown label wrapper now uses left-aligned content width instead of stretching across the panel.
- The visible capsule remains the same shared eyebrow component as the `SERVIDORES PUBLICOS` section.

## Change Budget

- One CSS-only adjustment plus task documentation.
