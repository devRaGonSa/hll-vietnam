---
id: TASK-176-add-stats-player-comparison-cards
title: Add stats player comparison cards
status: done
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

Implemented comparison cards:

- Added a dedicated comparison-card grid inside the selected-player profile panel.
- Added weekly and monthly window cards using only existing profile payload fields.
- Added a comparison card that contrasts weekly vs monthly KPM, K/D, kills delta, and matches delta.

Payload fields consumed:

- `player_id`
- `player_name`
- `matches_considered`
- `kills`
- `deaths`
- `teamkills`
- `kd_ratio`
- `kills_per_match`
- `deaths_per_match`
- `weekly_ranking`
- `monthly_ranking`
- `window_kind`
- `window_start`
- `window_end`

Behavior with no data or limited ranking:

- If both weekly and monthly windows have zero matches, the existing warning state remains and the comparison cards show explicit "Sin actividad" messaging.
- If a ranking block is absent, the cards show `Ranking ausente`.
- If a ranking exists but `ranking_position` is empty and the active window is a fallback `previous-*` window, the cards show `Profundidad insuficiente`.
- If a ranking exists but the player is not positioned in the visible ranking, the cards show `Fuera del ranking visible`.

Implementation notes:

- The frontend now fetches the existing player profile endpoint twice in parallel, once for `weekly` and once for `monthly`, without adding endpoints or changing backend contracts.
- The tactical visual style stays within the current Stats surface and reuses the existing palette and panel language.

Validation run:

- `node --check frontend/assets/js/stats.js`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- Local static server:
  - `http://127.0.0.1:8091/stats.html` -> 200
  - `http://127.0.0.1:8091/assets/js/stats.js` -> 200

Known limitations:

- Visual validation against a live local backend was not possible because `http://127.0.0.1:8000` was unavailable during this task.
- The Browser plugin surface was not available as `iab` in this session, so browser-level visual inspection could not be completed through the in-app browser.

Immediate follow-up improvements:

- Continue with `TASK-177-harden-annual-ranking-snapshot-operations` so the annual ranking endpoint behavior around effective limits and missing years is better defined and easier for the Stats UI to explain.
