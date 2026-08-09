---
id: TASK-233
title: Add HLL Vietnam release countdown
status: done
type: frontend
team: Frontend Senior
supporting_teams: []
roadmap_item: foundation
priority: medium
---

# TASK-233 - Add HLL Vietnam release countdown

## Goal

Add a visible frontend-only countdown to the public home page for the Hell Let Loose Vietnam release date.

## Context

The home page is `frontend/index.html` and it loads `frontend/assets/js/main.js`, not `frontend/assets/js/index.js`. The countdown should work without backend support and should not affect other pages if the markup is absent.

## Files Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/frontend-senior.md`
- `frontend/index.html`
- `frontend/assets/js/main.js`
- `frontend/assets/css/styles.css`

## Expected Files Modified

- `frontend/index.html`
- `frontend/assets/js/main.js`
- `frontend/assets/css/styles.css`
- this task file

## Changes

1. Added a semantic countdown block below the main trailer video.
2. Added `data-hll-vietnam-countdown` and `data-countdown-target`.
3. Used target date `2026-08-13T00:00:00+02:00`.
4. Added frontend-only countdown logic in `main.js`.
5. Rendered days, hours, minutes and seconds every second.
6. Stopped the interval when the target date is reached.
7. Prevented negative values by clamping remaining time to zero.
8. Added a final available state message: `Hell Let Loose Vietnam ya esta disponible.`
9. Added responsive CSS integrated with the existing tactical panel style.

## Design Decision

The countdown is placed below the video. This keeps it visually tied to the HLL Vietnam trailer while avoiding changes to the public hero or server sections.

## Validation

Passed:

```powershell
node --check frontend/assets/js/main.js
```

The implementation is guarded by `if (!root) return;`, so pages without the countdown block do not throw errors if they load the same JS.

Manual logic review:

- Target date parsed from `data-countdown-target`.
- Days, hours, minutes and seconds are calculated from remaining seconds.
- Values are clamped with `Math.max(0, ...)`.
- After the target date, the UI shows the available message and the interval is cleared.

## Outcome

The public home now shows a responsive countdown below the main video for `2026-08-13T00:00:00+02:00`. No backend file or backend configuration was changed.
