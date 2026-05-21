---
id: TASK-160
title: Home server card bottom actions
status: done
type: frontend
team: Frontend Senior
supporting_teams: [Experto en interfaz]
roadmap_item: foundation
priority: high
---

# TASK-160 - Home server card bottom actions

## Goal

Cleanly restructure the home server card action layout so only Historico and Partida actual render, positioned bottom-right aligned with the map card, without changing unrelated UI.

## Background

The home page server cards are rendered from `frontend/assets/js/main.js`.

Current user feedback:

- The home card buttons are still too high.
- The user wants the buttons moved "dos pasos al div de abajo con el mapa".
- The buttons must be located at the far right in the lower area, aligned with the map card.
- The layout should be more compact.
- Do not touch anything else.

Current known issue:

- `renderServerAction(server)` in `frontend/assets/js/main.js` still renders "Scoreboard publico".
- CSS/HTML workarounds have been used to hide/rename buttons.
- The user wants only:
  - Historico
  - Partida actual

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `frontend/index.html`
- `frontend/assets/js/main.js`
- `frontend/assets/css/styles.css`

Inspect the rendered server card structure, quickfact/map markup, trusted action URL mapping, and any existing inline or stylesheet button workarounds before changing code.

## Expected Files to Modify

Allowed changes:

- `frontend/assets/js/main.js`
- `frontend/assets/css/styles.css`
- `frontend/index.html` only to remove previous inline CSS workarounds if present
- no backend changes
- no tests unless needed
- node validation

## Constraints - DO NOT BREAK

- Do not change backend.
- Do not change current-match page.
- Do not change historical page behavior.
- Do not change server polling logic.
- Do not reintroduce Scoreboard publico on home server cards.
- Do not remove trusted URL mappings if used elsewhere unless unused.
- Do not alter the rest of the home page layout/content.
- Preserve responsive behavior.
- Commit and push after implementation.

## Implementation Requirements

### 1. Remove structural rendering of Scoreboard publico

`renderServerAction(server)` should only output:

- Historico
- Partida actual

### 2. Rename the rendered history action

Rename "Nuestro historico" to "Historico" in the rendered markup.

### 3. Avoid CSS-only hide/rename hacks

- Remove old CSS workarounds that hide first button or replace text through pseudo-elements if present.
- Make the JS markup itself correct.

### 4. Move buttons to the lower-right area

- The map quickfact card remains lower-left.
- The action buttons should be in the same lower row/block, aligned far right.
- Avoid large empty bottom-right space.
- Keep card height compact.

### 5. Suggested structure

- Card top: eyebrow, server name, status/population.
- Card bottom row: map card left, action buttons right.
- Do not make the map card huge.
- Buttons should not float in the middle of the card.

### 6. Responsive behavior

- On desktop, bottom row is two columns:
  - map left
  - actions right
- On mobile/narrow widths, stack safely:
  - map
  - actions

## Validation

Run:

- `node --check frontend/assets/js/main.js`
- `git diff --check`
- rebuild frontend

Before completing the task also confirm that `git diff --name-only` matches the expected scope.

## Manual Verification Steps

- Open `http://localhost:8080/`.
- Verify each server card shows only:
  - Historico
  - Partida actual
- Verify Scoreboard publico is not rendered.
- Verify buttons are bottom-right aligned with the map card.
- Verify map card remains compact.
- Verify card layout is not broken on narrow viewport.
- Verify Historico opens:
  - `historico.html?server=comunidad-hispana-01`
  - `historico.html?server=comunidad-hispana-02`
- Verify Partida actual opens:
  - `partida-actual.html?server=comunidad-hispana-01`
  - `partida-actual.html?server=comunidad-hispana-02`

## Expected Outcome

The home server cards have a clean structural layout with only Historico and Partida actual positioned at the lower-right aligned with the map card.

## Outcome

Structural cleanup:

- Home server card actions now live in a dedicated bottom row beside the map quickfact rather than inside the status column.
- The rendered card action markup keeps only `Historico` and `Partida actual`; trusted URL mappings stay intact for those actions.
- Removed the inline server-card layout workaround from `frontend/index.html` and moved the bottom-row layout rules into `frontend/assets/css/styles.css`, with a stacked narrow layout.

Validation performed:

- `node --check frontend/assets/js/main.js`
- `git diff --check`
- `docker compose build frontend`
- Checked the existing local frontend and backend endpoints were serving on `127.0.0.1:8080` and `127.0.0.1:8000`.
- Rendered Browser verification was attempted through the required Browser workflow but blocked because the Browser JavaScript execution tool was not exposed in this session after tool discovery.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
