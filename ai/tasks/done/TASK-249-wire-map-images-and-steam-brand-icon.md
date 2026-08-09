# TASK-249 - Wire map images and Steam brand icon

## Summary

This task connects the new local map images to current match and historical match detail using a shared frontend resolver, and wires the new Steam brand icon into the external profile buttons.

No map or brand asset files were modified.

## Files Read First

- `frontend/partida-actual.html`
- `frontend/assets/js/partida-actual.js`
- `frontend/historico-partida.html`
- `frontend/assets/js/historico-partida.js`
- `frontend/assets/css/historico.css`
- `frontend/assets/img/maps/`
- `frontend/assets/img/brands/`

## Problem

The frontend was still using narrow map-name heuristics and did not know how to resolve the new map image naming pattern consistently across:

- current match
- historical match detail

The Steam external profile button also had no brand icon wired even though the asset already existed locally.

## Decision

Create one shared client-side resolver instead of duplicating ad hoc logic in each page.

Rules:

- normalize map ids, layer ids and pretty names aggressively
- resolve to local assets using the `mapid-environment.webp` pattern when possible
- keep a safe fallback image path
- do not modify physical assets

## Asset Coverage Detected

Detected local coverage in `frontend/assets/img/maps/`:

- `carentan`: day, dusk, night, rain
- `driel`: dawn, day, night
- `elalamein`: day, dusk
- `elsenbornridge`: dawn, day, dusk, night
- `foy`: day, night
- `hill400`: day, dusk, night
- `hurtgenforest`: day, night
- `junobeach`: dawn, day, night
- `kharkov`: day, night
- `kursk`: day, night
- `mortain`: day, dusk, night, overcast
- `omahabeach`: day, dusk
- `purpleheartlane`: dawn, day, night, rain
- `remagen`: day, night
- `smolensk`: day, dusk, night
- `stalingrad`: day, dusk, night, overcast
- `stmariedumont`: day, night, rain
- `stmereeglise`: dawn, day, night
- `tobruk`: dawn, day, dusk
- `utahbeach`: day, night
- fallback assets: `unknown-day.webp`, `unknown.webp`

## Implementation

### Shared map resolver

Added `frontend/assets/js/map-image-resolver.js` with:

- canonical map aliases
- environment aliases
- compact normalization of layer ids and display names
- deterministic fallback selection

Examples resolved correctly:

- `junobeachwarfare` -> `./assets/img/maps/junobeach-day.webp`
- `Juno Beach Warfare` -> `./assets/img/maps/junobeach-day.webp`
- `utahbeach` -> `./assets/img/maps/utahbeach-day.webp`
- `Driel` -> `./assets/img/maps/driel-day.webp`
- `st marie du mont warfare` -> `./assets/img/maps/stmariedumont-day.webp`

### Current match

- `partida-actual.html` now loads the shared resolver before the page script.
- `partida-actual.js` now resolves map assets from layer id, map id and pretty names instead of a short hardcoded map list.

### Historical match detail

- `historico-partida.html` now loads the shared resolver.
- `historico-partida.js` now resolves map images from `match_id`, `map.id`, `map.name` and `map.pretty_name`.
- It keeps the existing fallback behavior if no match is found.

### Steam brand icon

- Wired the Steam profile button to `./assets/img/brands/steam.png`.
- Added `onerror="this.remove();"` to brand icons so a missing file does not leave a broken image.

## Validation

Executed:

- `node --check frontend/assets/js/map-image-resolver.js`
- `node --check frontend/assets/js/partida-actual.js`
- `node --check frontend/assets/js/historico-partida.js`

Static/runtime validation performed:

- confirmed `historico-partida.html` does not load `current-match-weapon-icons.js`
- confirmed `partida-actual.html` still loads `current-match-weapon-icons.js`
- confirmed resolver maps `junobeachwarfare` to `junobeach-day.webp`
- confirmed resolver maps `utahbeach`, `driel` and `st marie du mont warfare` to existing local assets
- confirmed Steam button now points to the brand icon asset when present

## Notes

- No backend changes were required for this task.
- No asset files were moved, renamed or modified.
- No weapon or clan asset path was touched.
