---
id: TASK-150
title: Server card history and current match entrypoints
status: pending
type: frontend
team: Frontend Senior
supporting_teams: []
roadmap_item: rcon-full-data
priority: high
---

# TASK-150 - Server card history and current match entrypoints

## Goal

Add server-specific navigation buttons to the home page and make the internal
historical page accept an initial server filter through the URL.

## Background

The home page currently renders live server cards in
`frontend/assets/js/main.js`. Each server card currently has a single
"Historico" action built through `renderServerAction(server)`.

We need clearer per-server actions for the active Comunidad Hispana servers:

- Open the public current scoreboard.
- Open our internal historical page already filtered by that server.
- Open our future internal live/current match page already filtered by that
  server.

Important URL correction:

The current public scoreboard URLs are the base scoreboard URLs, without
`/games`:

- `comunidad-hispana-01` -> `https://scoreboard.comunidadhll.es`
- `comunidad-hispana-02` -> `https://scoreboard.comunidadhll.es:5443`

The `/games` URLs are only for the external public historical scoreboard, if
needed later:

- `comunidad-hispana-01` -> `https://scoreboard.comunidadhll.es/games`
- `comunidad-hispana-02` -> `https://scoreboard.comunidadhll.es:5443/games`

## Constraints / DO NOT BREAK

- Do not change backend storage.
- Do not change RCON ingestion.
- Do not change scoreboard correlation logic.
- Do not depend on server #03.
- Do not expose arbitrary URLs received from API payloads.
- Do not remove existing server card live status rendering.
- Do not implement the full live match page in this task.
- Keep the change frontend-focused and minimal.
- Preserve existing responsive layout.

## Allowed Changes

- `frontend/assets/js/main.js`
- `frontend/assets/css/main.css` or equivalent home CSS file
- historical page JS/CSS/HTML files needed to support `?server=`
- optionally add a minimal placeholder `partida-actual.html` if needed to
  avoid a broken link
- docs only if needed

## Implementation Requirements

1. Replace the current single "Historico" server-card action with a small
   action group.
2. For each active supported server, render these actions:
   - "Scoreboard público"
   - "Nuestro histórico"
   - "Partida actual"
3. "Scoreboard público" must open the current public scoreboard base URL:
   - `comunidad-hispana-01` -> `https://scoreboard.comunidadhll.es`
   - `comunidad-hispana-02` -> `https://scoreboard.comunidadhll.es:5443`
   It must NOT append `/games`.
4. "Nuestro histórico" must open the internal historical page with a server
   query parameter:
   - `historico.html?server=comunidad-hispana-01`
   - `historico.html?server=comunidad-hispana-02`
5. "Partida actual" must open:
   - `partida-actual.html?server=comunidad-hispana-01`
   - `partida-actual.html?server=comunidad-hispana-02`
6. Add trusted frontend mappings for supported active servers only:
   - `comunidad-hispana-01`
   - `comunidad-hispana-02`
   Do not add server #03.
7. The server identifier should be resolved from the server payload using
   `external_server_id` or another already existing stable server slug. If the
   server cannot be resolved to a trusted known server, do not render
   public/current-match actions for it.
8. Update the historical page initialization so that:
   - `?server=comunidad-hispana-01` selects Comunidad Hispana #01 instead of
     defaulting to all servers.
   - `?server=comunidad-hispana-02` selects Comunidad Hispana #02 instead of
     defaulting to all servers.
   - unknown or missing server query values fall back to the current default
     behavior.
9. If `partida-actual.html` does not exist yet, create a minimal placeholder
   page that:
   - reads `?server=`
   - displays "Partida actual"
   - displays the selected server slug/name
   - explains that the live detail view will be implemented in the next task
   - includes a safe link back to the home page and historical page
   Do not implement live data polling yet.
10. Ensure all generated URLs are built from trusted constants, not directly
    from API-provided arbitrary values.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/frontend-senior.md`
- `frontend/assets/js/main.js`
- historical page files used for the existing server filter flow

## Expected Files to Modify

- `frontend/assets/js/main.js`
- home CSS only if the new action group needs layout styling
- historical page files needed for `?server=` initialization
- `partida-actual.html` only if a placeholder is needed

## Validation

- Run `node --check` on every modified frontend JS file.
- Review `git diff --name-only` and confirm the changed files match this task.

## Manual Verification

1. Open the home page.
2. Verify Comunidad Hispana #01 card shows:
   - Scoreboard público
   - Nuestro histórico
   - Partida actual
3. Verify Comunidad Hispana #02 card shows:
   - Scoreboard público
   - Nuestro histórico
   - Partida actual
4. Click "Scoreboard público" for Comunidad Hispana #01 and verify it opens:
   `https://scoreboard.comunidadhll.es`
5. Click "Scoreboard público" for Comunidad Hispana #02 and verify it opens:
   `https://scoreboard.comunidadhll.es:5443`
6. Click "Nuestro histórico" for Comunidad Hispana #01 and verify the
   historical page loads with Comunidad Hispana #01 selected.
7. Click "Nuestro histórico" for Comunidad Hispana #02 and verify the
   historical page loads with Comunidad Hispana #02 selected.
8. Click "Partida actual" for both servers and verify the page opens with the
   correct server query parameter.
9. Verify no server #03 action is introduced.

## Commit Message

`feat: add current match server entrypoints`

## Expected Outcome

The home page exposes clear per-server navigation actions, and the internal
historical page can open directly filtered by server.

## Outcome

Document the validation performed, URL trust boundary decisions, historical
filter initialization behavior, and any follow-up task instead of expanding
scope.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if the scope grows.
