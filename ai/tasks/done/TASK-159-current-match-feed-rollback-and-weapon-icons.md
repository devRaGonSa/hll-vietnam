---
id: TASK-159
title: Current match feed rollback and weapon icons
status: done
type: frontend
team: Frontend Senior
supporting_teams: [Disenador grafico, Experto en interfaz]
roadmap_item: foundation
priority: high
---

# TASK-159 - Current match feed rollback and weapon icons

## Goal

Rollback/refactor the current killfeed visual layout to the previous accepted live feed style and integrate local weapon icons where available.

## Background

The latest compact three-column killfeed implementation is not accepted visually. The user wants to return to the previous live feed screen direction and then improve it.

User feedback:

- "Quiero volver a la pantalla de feed de la partida en vivo de antes, esta no me convence"
- The desired feed should still be a live combat screen, but not the current overly table/grid-like layout.
- Weapon icons were manually added to the repository for testing and should be reused.

Current issue:

The current killfeed visually feels too much like a table/grid and not enough like a readable live combat feed. The user wants the previous feed visual style back, then use weapon icons.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `frontend/partida-actual.html`
- `frontend/assets/js/partida-actual.js`
- relevant current-match CSS and `frontend/assets/img/weapons/`

Inspect git history/diff around the feed changes before choosing whether to restore prior markup or intentionally recreate the previous direction.

## Expected Files to Modify

Allowed changes:

- `frontend/assets/js/partida-actual.js`
- `frontend/partida-actual.html` if needed
- `frontend/assets/css/historico.css` or relevant CSS
- `frontend/assets/img/weapons/*` only if renaming/organizing existing local icons is necessary
- no backend changes unless weapon normalization is strictly needed

## Constraints - DO NOT BREAK

- Do not break `/api/current-match/kills`.
- Do not expose raw AdminLog lines.
- Do not fabricate kill events.
- Do not show stale kills as live kills.
- Do not query RCON directly from the frontend.
- Do not break the current-match scoreboard/header.
- Do not break the player stats section.
- Do not break historical pages.
- Do not depend on server #03.
- Do not hotlink external weapon images.
- Use local weapon icon assets only.
- Unknown weapons must have a clean fallback.
- Commit and push after implementation.

## Implementation Requirements

### 1. RCA first

- Identify the previous feed layout/style before TASK-156/TASK-157 changes using git history/diff.
- Identify what parts of the previous style the user likely preferred:
  - card readability
  - vertical event readability
  - less table/grid feel
- Document this in TASK done notes.

### 2. Rollback/refactor visual style

- Restore the previous feed screen style or recreate it intentionally.
- It should be readable and live-oriented.
- It should not look like the current table-like three-column grid.
- Keep the feed bounded and capped; do not allow infinite growth.
- Keep deduplication.

### 3. Event content

Each event should show:

- killer
- weapon icon
- victim

Optional timestamp may be shown only if visually subtle.

### 4. Weapon icon discovery

- Inspect `frontend/assets/img/weapons` or any newly added weapon icon folder.
- Reuse local icons the user added.
- Do not create external dependencies.
- If filenames are inconsistent, add a safe mapping instead of renaming unless renaming is clearly cleaner.

### 5. Weapon icon mapping

Add mapping for at least:

- `M1 GARAND`
- `MP40`
- `M1A1 THOMPSON`
- `GEWEHR 43`
- `MG42`
- `UNKNOWN`
- generic fallback

Also support simple normalization:

- uppercase/lowercase differences
- spaces/hyphens
- common AdminLog weapon strings

### 6. Visual behavior

- Events should appear as compact readable live-feed entries.
- Avoid the current big empty table-like columns.
- Avoid full panel flicker.
- Limit visible entries, for example 10-15.
- Older events should disappear when the cap is exceeded.

### 7. Empty states

- If no current events: "Todavía no se han detectado bajas en esta partida."
- If stale/no current events: "Sin bajas recientes asociadas a la partida actual."

## Validation

Run:

- `node --check frontend/assets/js/partida-actual.js`
- `git diff --check`
- rebuild frontend

Before completing the task also confirm that `git diff --name-only` matches the expected scope.

## Manual Verification Steps

- Open `http://localhost:8080/partida-actual.html?server=comunidad-hispana-01`.
- Open `http://localhost:8080/partida-actual.html?server=comunidad-hispana-02`.
- Verify the feed no longer looks like the current table/grid.
- Verify it resembles the previous live feed screen direction.
- Verify each event shows killer, weapon icon, victim.
- Verify unknown weapons use fallback.
- Verify local weapon icons load correctly.
- Verify repeated updates do not duplicate rows.
- Verify stale events are not shown as live.
- Verify the player stats section still works.

## Expected Outcome

The current-match feed returns to the previous preferred live-feed visual direction while using the newly added local weapon icons.

## Outcome

Visual RCA:

- Git history before the compact feed change showed a vertical `historical-match-card` list with one readable event per row/card. The rejected version introduced a fixed multi-column killfeed surface that reads like a grid/table.
- The feed was refactored back to a vertical card-like list while keeping the current live buffer, deduplication and no-flicker signature guard.

Weapon icon decision:

- Reused local assets already present under `frontend/assets/img/weapons/`.
- `partida-actual.js` maps normalized AdminLog weapon names for `M1 GARAND`, `MP40`, `M1A1 THOMPSON`, `GEWEHR 43`, `MG42` and aliases to local PNGs.
- Unknown/unmapped weapons keep their label for tooltip/accessibility and render a compact local fallback marker instead of hotlinking assets.

Validation performed:

- `node --check frontend/assets/js/partida-actual.js`
- `git diff --check`
- `docker compose build frontend`
- Reviewed the history diff for the prior accepted feed direction and inspected local weapon asset filenames.
- Rendered Browser verification was attempted through the required Browser workflow but blocked because the Browser JavaScript execution tool was not exposed in this session after tool discovery.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
