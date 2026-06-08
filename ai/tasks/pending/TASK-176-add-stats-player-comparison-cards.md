---
id: TASK-176-add-stats-player-comparison-cards
title: Add stats player comparison cards
status: pending
type: frontend
team: Frontend Senior
supporting_teams:
  - Experto en interfaz
  - Backend Senior
roadmap_item: foundation
priority: high
---

# TASK-176-add-stats-player-comparison-cards - Add stats player comparison cards

## Goal

Improve the Stats UI with comparison cards that help a selected player quickly understand personal metrics and weekly/monthly position, using already available backend data and without creating new endpoints.

## Context

The Stats page already exposes player lookup and detail payloads. This task should improve clarity and trust by surfacing key performance values in cards, while preserving empty/loading/error behavior and the existing visual identity.

## Steps

1. Read the listed files first.
2. Add UI card components in the existing Stats section for selected-player context.
3. Consume existing fields from current responses only, without changing API contracts.
4. Show explicit states for missing ranking, insufficient ranking depth, or missing player in weekly/monthly snapshots.
5. Keep design aligned with military/Vietnam/tactical sober style and keep existing empty/loading/error states intact.

## Files to Read First

- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- docs/stats-section-functional-plan.md
- frontend/stats.html
- frontend/assets/js/stats.js
- frontend/assets/css/styles.css
- backend/app/rcon_historical_player_stats.py
- ai/tasks/done/TASK-172-polish-stats-section-empty-states-and-copy.md

## Expected Files to Modify

- frontend/stats.html
- frontend/assets/js/stats.js
- frontend/assets/css/styles.css
- ai/tasks/done/TASK-176-add-stats-player-comparison-cards.md

## Constraints

- No backend modifications.
- No new endpoints.
- No database changes.
- Do not change existing API contracts.
- Do not re-enable Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Do not introduce frameworks.
- Keep vanilla HTML/CSS/JS implementation.
- Keep military/Vietnam/tactical/sober visual identity.
- Preserve existing empty/loading/error states and avoid regressions.

## Validation

- Run `node --check frontend/assets/js/stats.js`.
- Run `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`.
- Serve frontend with `python -m http.server` and verify HTTP 200 for `stats.html` and `assets/js/stats.js`.
- If possible, visually validate with local backend.
- Run `git diff --name-only` and verify scope is limited to this task.

## Outcome

Document which comparison cards were added, payload fields consumed, behavior with no data, and any remaining follow-up improvements.

