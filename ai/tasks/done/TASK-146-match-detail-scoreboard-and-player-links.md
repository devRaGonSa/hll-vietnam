---
id: TASK-146
title: Recover match scoreboard and player external links
status: done
type: backend
team: Backend Senior
supporting_teams: [Frontend Senior]
roadmap_item: foundation
priority: high
---

# TASK-146 - Recover match scoreboard and player external links

## Goal

Restore the safe public scoreboard action on the internal match detail page and
expose player external profile links only when captured player identifiers make
that reliable.

## Context

The internal `historico-partida.html` detail payload can carry a safe
`match_url`, but users do not currently see the detail-page scoreboard action.
The same detail page has click-open player panels that can link to Steam and
SteamID64-based third-party profiles when the RCON/profile or reliable
historical data path already holds a valid SteamID64.

## Steps

1. Inspect the listed files and captured identifier path first.
2. Keep scoreboard actions detail-page only and add profile links only from
   reliable identifiers.
3. Validate backend diagnostics, frontend syntax, integration/container checks
   and rendered detail-page behavior.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/backend-senior.md`
- `ai/orchestrator/frontend-senior.md`
- `backend/app/rcon_historical_read_model.py`
- `frontend/assets/js/historico-partida.js`

## Expected Files to Modify

- Relevant backend read-model, storage helper, diagnostics and tests for exposed
  external player identifiers and profile links.
- `frontend/assets/js/historico-partida.js`
- Relevant detail-page CSS when profile links need styling.
- `ai/tasks/done/TASK-146-match-detail-scoreboard-and-player-links.md`

## Constraints

- Do not invent SteamIDs or use player names to build external links.
- Do not call Steam Web API or require new external credentials.
- Keep public scoreboard actions off recent match cards.
- Allow only safe Comunidad Hispana scoreboard match URLs in the detail page.
- Preserve click-open player panels and existing expanded stat sections.

## Validation

- `python -m compileall backend/app`
- `python -m app.storage_diagnostics`
- `node --check frontend/assets/js/historico-partida.js`
- `node --check frontend/assets/js/historico.js`
- `node --check frontend/assets/js/historico-recent-live.js`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- `docker compose --profile advanced up -d --build backend frontend`
- Inspect the provided match-detail API response with `Invoke-WebRequest`.
- Render-check the detail-page scoreboard action, player panel profile state and
  recent-match-card absence of public scoreboard links.
- Review `git diff --name-only` against task scope.

## Outcome

Implemented.

- The internal match detail scoreboard action now sits immediately after the
  summary block and before the potentially long player table. It still uses the
  existing detail-page safe scoreboard allowlist and keeps the established
  `Ver en Scoreboard` regression-checked label.
- RCON detail rows derive `platform`, `steam_id_64` and Steam/Hellor/HLL Records
  URLs from captured `player_id` only when it is a valid numeric 17-digit
  SteamID64. Raw RCON `player_id` is still not exposed.
- Trusted public-scoreboard detail rows derive the same profile fields from
  persisted `historical_players.steam_id`.
- Epic-style hex RCON IDs resolve to `platform: epic` with no Steam-only links;
  other missing or unsupported IDs return `platform: unknown` with no external
  link fields.
- Click-open player panels now include `Perfiles externos`. Steam-backed players
  get the three external links with new-tab noopener rel attributes; missing-ID
  panels show a clear unavailable state without using player names to build
  URLs.
- PostgreSQL storage diagnostics now report SteamID64 availability counts for
  RCON match rows, RCON profile snapshots and trusted scoreboard player rows.

Validation passed:

- `python -m compileall backend/app`
- `python -m app.storage_diagnostics` from `backend/` in local SQLite fallback
  mode. It reports PostgreSQL external-ID diagnostics as inactive when the
  PostgreSQL env is not configured locally.
- `docker compose exec backend python -m app.storage_diagnostics` after the
  advanced stack build. PostgreSQL diagnostics reported:
  - `rcon_match_steam_id64_rows`: `2554`
  - `rcon_profile_steam_id64_rows`: `462`
  - `scoreboard_player_steam_id64_rows`: `87369`
- `node --check frontend/assets/js/historico-partida.js`
- `node --check frontend/assets/js/historico.js`
- `node --check frontend/assets/js/historico-recent-live.js`
- Targeted backend tests from `backend/`:
  `python -m unittest tests.test_rcon_materialization_pipeline tests.test_scoreboard_match_links`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- `docker compose --profile advanced up -d --build backend frontend`
- The provided `Invoke-WebRequest` match-detail API check returned the safe
  Carentan scoreboard URL plus validated external profile links for captured
  SteamID64-backed players.
- Rendered local Chrome/Selenium fallback QA verified:
  - detail scoreboard action appears before the player table and opens
    `https://scoreboard.comunidadhll.es:5443/games/1562094`
  - Steam-backed player panel shows Steam, Hellor and HLL Records links
  - a no-SteamID64 player panel shows `Perfiles externos no disponibles`
  - recent `historico.html` match cards show no public scoreboard links
  - mobile detail layout keeps the scoreboard action readable

Notes:

- Browser plugin runtime tools were not exposed by tool discovery in this
  session, so rendered QA used temporary headless Chrome/Selenium checks and
  screenshots outside the repository.
- Targeted backend unittest output still includes existing SQLite resource
  warnings from the current test suite while tests pass.
- Browser console output on rendered checks only reported the existing missing
  `favicon.ico` request.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
