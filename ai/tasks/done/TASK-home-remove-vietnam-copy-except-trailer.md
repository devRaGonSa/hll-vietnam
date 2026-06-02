---
id: TASK-home-remove-vietnam-copy-except-trailer
title: Remove Vietnam copy from home except trailer
status: pending
type: frontend
team: Frontend Senior
supporting_teams: [Experto en interfaz]
roadmap_item: frontend-copy-adjustments
priority: medium
---

# TASK-home-remove-vietnam-copy-except-trailer - Remove Vietnam copy from home except trailer

## Goal

Temporarily remove “Vietnam” from the home page branding copy, except in the trailer block.

## Context

The home page should no longer show “HLL Vietnam” in the main community branding. The trailer section must continue to refer to HLL Vietnam because the trailer itself is still about HLL Vietnam.

This is a small frontend copy-only change.

## Steps

1. Inspect the listed files first.
2. Modify only the required home page copy.
3. Preserve trailer copy.
4. Validate diff and encoding.
5. Commit and push the task branch.

## Files to Read First

- `AGENTS.md`
- `frontend/index.html`
- `frontend/assets/css/styles.css`
- `frontend/assets/css/hero-header-compact.css`

## Expected Files to Modify

- `frontend/index.html`

Do not modify CSS unless the copy change causes an actual layout issue. If CSS is needed, explain why in the outcome.

## Exact Required Changes

In `frontend/index.html`, change:

`content="Comunidad hispana de HLL Vietnam. Accede al Discord oficial y descubre el trailer del proyecto."`

to:

`content="Comunidad hispana de HLL. Accede al Discord oficial y descubre el trailer del proyecto."`

Change:

`<title>Comunidad Hispana - HLL Vietnam</title>`

to:

`<title>Comunidad Hispana - HLL</title>`

Change:

`alt="Logo oficial de la comunidad HLL Vietnam"`

to:

`alt="Logo oficial de la comunidad HLL"`

Change:

`<span class="hero__title-accent">HLL Vietnam</span>`

to:

`<span class="hero__title-accent">HLL</span>`

Do not change:

`Primer vistazo a HLL Vietnam`

Do not change:

`Trailer HLL Vietnam`

Do not change the trailer iframe URL.

## Constraints

- Do not change backend.
- Do not change JS.
- Do not change layout unless required by the shorter title.
- Do not corrupt UTF-8.
- Do not introduce BOM if the existing file does not require one.
- Do not touch unrelated pages.

## Validation

Run:

```powershell
git diff -- frontend/index.html
git diff --check
```

Manual check:

`http://localhost:8080/?v=home-copy`

Expected:

- hero title says Comunidad Hispana HLL;
- page title says Comunidad Hispana - HLL;
- trailer still says Primer vistazo a HLL Vietnam;
- iframe title still says Trailer HLL Vietnam.

## Outcome

Document:

- exact copy changed;
- validation commands run;
- whether local visual check was performed.

Codex CLI must commit and push the completed task branch.

Suggested implementation branch:

`task/home-remove-vietnam-copy-except-trailer`

Suggested commit message:

`fix: remove Vietnam copy from home except trailer`

## Change Budget

- One modified file expected.
- No runtime logic changes.
