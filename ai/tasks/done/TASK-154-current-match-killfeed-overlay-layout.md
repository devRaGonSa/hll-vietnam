# TASK-154 - Current match killfeed overlay layout

Status: in-progress

## Goal

Redesign the current-match kill feed frontend so it behaves like a compact live killfeed overlay.

## Background

The current-match page already renders a kill feed using:

- `GET /api/current-match/kills?server=...`

The feed currently appears as a vertical list of large historical-style cards. This is not the desired UX.

## Desired UX

The kill feed should look like a compact live FPS-style overlay:

- A rectangular live panel.
- Events rendered as compact rows/chips.
- Each event should show:
  - killer name
  - weapon icon or weapon label fallback
  - victim name
- Events should be arranged in three visual columns inside the panel.
- New events should appear progressively.
- Older events should move left and eventually disappear.
- The feed should feel like a real-time combat screen, not a historical list.

The user explicitly wants:

- "una especie de pantalla en tiempo real"
- "simplemente se muestre el texto, el que mata, el arma y alguien mata"
- "iconos del arma que se utiliza"
- "una pequeña pantalla rectangular"
- "se irá poniendo de arriba abajo en tres columnas"
- "se irá desplazando hacia la izquierda e irán desapareciendo las más antiguas"

## Scope

Replace the current large-card kill feed with a compact live overlay on the current-match page.

Allowed changes:

- `frontend/assets/js/partida-actual.js`
- `frontend/partida-actual.html` if needed
- `frontend/assets/css/historico.css` or the relevant CSS used by `partida-actual.html`
- `frontend/assets/css/styles.css` only if the current-match page depends on it
- `frontend/assets/img/weapons/*` if local weapon icons/placeholders are added
- backend only if a small weapon normalization field is needed, but prefer frontend-side mapping first
- focused tests or node validation

## Constraints - DO NOT BREAK

- Do not break `/api/current-match/kills`.
- Do not expose raw AdminLog lines.
- Do not fabricate kill events.
- Do not show stale kills as live kills.
- Do not break the current-match scoreboard/header.
- Do not break historical match detail pages.
- Do not query RCON directly from the frontend.
- Do not depend on server #03.
- Do not require external/CDN assets at runtime.
- If weapon icons are added, they must be local/static assets or generated lightweight inline/SVG placeholders.
- Keep the UI responsive.

## Files to inspect first

Read:

- `frontend/partida-actual.html`
- `frontend/assets/js/partida-actual.js`
- the CSS currently used by `frontend/partida-actual.html`
- focused current-match kill feed tests or validation scripts if present

Inspect the current kill feed rendering, `event_id` handling, scope copy, and current polling behavior before changing code.

## Implementation requirements

### 1. Compact live panel

Replace the current large-card feed rendering with a compact live killfeed panel.

The panel must be visually rectangular and compact. It should look like a live combat overlay, not a list of historical cards.

### 2. Layout

- Use a three-column visual layout on desktop.
- Events should fill vertically within a column, then continue through the next visual position.
- Newer events should be visually prioritized.
- Older events should shift left and disappear once the maximum number of visible events is exceeded.
- On narrow/mobile widths, fall back to one or two columns without overflow.

### 3. Event content

Each kill event must show:

- killer name
- weapon icon or weapon label
- victim name
- optional timestamp only if it does not make the UI noisy
- teamkill indicator if `is_teamkill` is true

### 4. Weapon icons

Add a safe mapping for common weapons currently seen in AdminLog examples:

- `M1 GARAND`
- `MP40`
- `M1A1 THOMPSON`
- `UNKNOWN`

Prefer local SVG/icon placeholders if real weapon assets are not available.

- Do not hotlink external images.
- Unknown weapons must show a generic weapon icon/label fallback.
- The icon mapping should be easy to extend later.

### 5. Motion and transition

- Use CSS transitions/animations only if they are subtle.
- Avoid layout jumps.
- Respect users with reduced motion if possible.
- The feed should not flicker every poll.

### 6. Deduplication

- Preserve existing `event_id` deduplication.
- Re-rendering must not duplicate rows.
- Repeated polling must keep already visible events stable.

### 7. Maximum visible events

- Limit visible events to a reasonable number, for example 12 or 15.
- Older events should be dropped from the visual panel.
- Do not render an infinitely growing list.

### 8. Copy

Use these messages:

- If there are no events: "Todavía no se han detectado bajas en esta partida."
- If scope is open match window: "Bajas detectadas en la partida actual."
- If scope is `recent-admin-log-window`: "Cobertura parcial desde AdminLog reciente."
- If stale/no current events: "Sin bajas recientes asociadas a la partida actual."

### 9. Accessibility

- Keep `aria-live` polite or equivalent.
- Event text must remain readable even if icons fail.

## Validation

Run:

- `node --check frontend/assets/js/partida-actual.js`
- any existing frontend validation if available

## Manual verification checklist

- Open `http://localhost:8080/partida-actual.html?server=comunidad-hispana-01`.
- Open `http://localhost:8080/partida-actual.html?server=comunidad-hispana-02`.
- Verify kill feed appears as a compact rectangular live overlay.
- Verify events render as killer -> weapon/icon -> victim.
- Verify it uses three columns on desktop.
- Verify old events disappear instead of growing endlessly.
- Verify repeated polling does not duplicate events.
- Verify teamkills are visually distinguishable.
- Verify unknown weapons use a clean fallback.
- Verify no raw AdminLog line is shown.
- Verify no external image URLs are required.

## Expected outcome

The current-match kill feed looks and behaves like a compact live FPS-style killfeed overlay with local/fallback weapon icon support.

## AI Platform lifecycle

After implementation and validation:

- Move this task according to the lifecycle defined in `AGENTS.md`.
- Do not mark unrelated tasks as done automatically.

## Outcome

- Replaced the historical-style kill cards with a capped 15-event rectangular overlay in `partida-actual`.
- Kept `event_id` deduplication and avoided poll flicker by only re-rendering when the visible event-id set changes.
- Rendered older visible events first so they occupy the left side of the three-column desktop panel while newer events remain visually prioritized on the right.
- Added local text-glyph weapon placeholders for `M1 GARAND`, `MP40`, `M1A1 THOMPSON` and unknown/other weapons without external assets.
- Validation run:
  - `node --check frontend/assets/js/partida-actual.js`
  - `scripts/run-historical-ui-regression-tests.ps1`
  - `git diff --check`
  - `git diff --name-only`
- Scope review: changed product files are `frontend/assets/js/partida-actual.js` and `frontend/assets/css/historico.css`.
- Manual/rendered Browser QA remains to be repeated when the Browser automation entry point is exposed; the local frontend and backend current-match endpoints were reachable during validation.
