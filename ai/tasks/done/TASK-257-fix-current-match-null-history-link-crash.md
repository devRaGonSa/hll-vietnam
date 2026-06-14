---
id: TASK-257
title: Fix current match null history link crash
status: done
type: frontend
team: Frontend Senior
supporting_teams: []
roadmap_item: foundation
priority: high
---

# TASK-257 - Fix current match null history link crash

## Goal

Correct the JavaScript crash in the current match page when the optional historical link node is absent from the HTML.

## Context

Production showed this error on `/partida-actual.html?server=comunidad-hispana-01`:

`Uncaught TypeError: can't access property "href", nodes.history is null`

The crash happened before the page initialized the main current-match, kill-feed and player-stat requests, leaving the UI stuck in loading states.

## Steps

1. Inspect current-match HTML and JavaScript.
2. Confirm where `nodes.history` is defined and whether the matching HTML node exists.
3. Review similar `nodes.*` accesses for optional link or dynamically inserted nodes.
4. Make optional link initialization null-safe without global try/catch.
5. Validate syntax, static access patterns and current-match public endpoints.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/frontend-senior.md`
- `frontend/partida-actual.html`
- `frontend/assets/js/partida-actual.js`

## Expected Files to Modify

- `frontend/assets/js/partida-actual.js`
- `ai/tasks/done/TASK-257-fix-current-match-null-history-link-crash.md`

## Constraints

- Do not touch backend, scheduler, RCON, server config or port `27001`.
- Do not touch TeamKills behavior.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Do not touch physical assets, maps, weapons, clans or brands.
- Do not touch `ai/system-metrics.md`.
- Do not include `tmp/`, `TASK-204` or unrelated previous changes.
- Do not commit or push.

## Validation

- `node --check frontend/assets/js/partida-actual.js` passed.
- Static search confirmed there are no direct `nodes.history.href`, `nodes.scoreboard.href` or `nodes.scoreboard.hidden` patterns left outside null-safe helpers.
- DOM simulation with `current-match-history` absent completed without TypeError and reached controlled current-match, kill-feed and player-stat states.
- Chrome headless validation of `/partida-actual.html?server=comunidad-hispana-01` from a local static frontend server reported `uncaughtExceptionCount: 0` and `typeErrorCount: 0`. With no local backend running, the page reached controlled empty/error states instead of blocking in loading text.
- Public audit command executed:
  `python .\scripts\audit_public_requests.py --base-url https://comunidadhll.devzamode.es --timeout 30 --output tmp\task257_full_audit_after.json`
- Audit summary: `CRITICAL: 0`.
- Required current-match endpoints returned `OK 200`:
  `current-match-comunidad-hispana-01`,
  `current-match-comunidad-hispana-02`,
  `current-match-kills-comunidad-hispana-01`,
  `current-match-kills-comunidad-hispana-02`,
  `current-match-players-comunidad-hispana-01`,
  `current-match-players-comunidad-hispana-02`.

## Outcome

`nodes.history` pointed to `#current-match-history`, but `frontend/partida-actual.html` no longer contains that element. The node was removed from the current page markup in `d6f1739 Adjust countdown and page navigation`; only the top navigation historical link remains.

The fix makes optional link handling null-safe through dedicated helpers. If the history or scoreboard nodes exist, their attributes are updated. If they do not exist, initialization continues and the main data loaders still run.

Dynamic feed and player-stat containers are also guarded before rendering so missing optional/dynamic nodes do not cascade into TypeError failures.

No backend, endpoint, scheduler, RCON, server configuration, assets, maps, weapons, clans, brands, TeamKills, Elo/MMR, Comunidad Hispana #03 or `ai/system-metrics.md` changes were made by this task.
