---
id: TASK-138
title: Polish RCON match detail final scoreboard UI
status: pending
type: frontend
team: Experto en interfaz
supporting_teams:
  - Frontend Senior
  - Disenador grafico
roadmap_item: rcon-full-data
priority: high
---

# TASK-138 - Polish RCON Match Detail Final Scoreboard UI

## Goal

Perform a final focused visual polish pass on the historical RCON match detail page so it more closely resembles the public scoreboard style while preserving the HLL Vietnam dark tactical theme.

## Context

The match detail page already renders the important RCON/materialized match data. The central result direction is good, but the page still needs a final scoreboard-style polish and removal of rough labels.

The user likes the central result:

- score
- map
- Warfare
- winner

The page should avoid implementation/source noise and should not expose event timeline, confidence/source/base, snapshot wording, Elo/MVP blocks or Comunidad Hispana #03.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/frontend-senior.md`
- `ai/orchestrator/ui-expert.md`
- `ai/orchestrator/graphic-designer.md`
- `frontend/historico-partida.html`
- `frontend/assets/js/historico-partida.js`
- relevant CSS used by `historico-partida.html`

## Expected Files to Modify

- `frontend/historico-partida.html`
- `frontend/assets/js/historico-partida.js`
- relevant CSS used by `historico-partida.html`
- this task file when moving it from `ai/tasks/pending` to `ai/tasks/done`

If additional files are necessary, document why in the task outcome.

## Implementation Requirements

1. Work from a dedicated branch: `codex/task-138-final-scoreboard-polish`.
2. Make the match detail page resemble the public scoreboard style more closely:
   - large central score
   - side labels left/right
   - bigger faction icons
   - map/mode/winner around the central score
   - compact metadata below
3. Remove `Partida RCON materializada` from the hero subtitle.
4. Replace the hero subtitle with only the server name or server + match date if available.
5. Keep `Datos disponibles` only if it still makes sense.
6. If `Datos disponibles` no longer fits the polished direction, use a more scoreboard-like heading.
7. Ensure these are not visible:
   - `Confianza`
   - `Fuente`
   - `Base`
   - `Eventos`
   - `Línea de tiempo`
   - `MESSAGE`
   - `TEAM SWITCH`
   - `CONNECTED`
   - `KILL`
   - `MATCH START`
   - `MATCH END`
   - `snapshot`
   - Elo/MVP blocks
   - Comunidad Hispana #03
8. Preserve the player table.
9. Preserve known match values for the Carentan detail page:
   - Map: `Carentan`
   - Score: `3 : 2`
   - Winner: `Aliados`
   - Duration: `1 h 30 min`
   - AntonioPruna: 1 kill, 0 deaths, `M1 GARAND`
   - victim row: `death_by` AntonioPruna
10. Keep visual consistency with the dark HLL Vietnam theme.
11. Keep the layout responsive.
12. Do not show implementation/debug text in the UI.

## Constraints

- Keep the change small and focused.
- Preserve the dark HLL Vietnam visual identity.
- Do not introduce frameworks or dependencies.
- Do not modify backend unless a tiny presentation contract issue is strictly necessary and documented.
- Do not modify unrelated files.
- Do not add Elo/MVP blocks.
- Do not add Comunidad Hispana #03.
- Do not reintroduce event timeline, confidence/source/base cards or `snapshot` wording.

## Validation Commands

Run the relevant checks before marking this task done:

- `node --check frontend/assets/js/historico-partida.js`
- `node --check frontend/assets/js/historico.js`
- `node --check frontend/assets/js/historico-recent-live.js`
- `python -m compileall backend/app`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-rcon-data-pipeline-tests.ps1`
- `docker compose up -d --build backend frontend`
- `Invoke-WebRequest "http://localhost:8000/health" | Select-Object -ExpandProperty Content`
- `Invoke-WebRequest "http://localhost:8000/api/historical/recent-matches?server=all-servers&limit=10" | Select-Object -ExpandProperty Content`

## Manual Verification

Open:

- `http://localhost:8080/historico.html`
- `http://localhost:8080/historico-partida.html?server=comunidad-hispana-02&match=comunidad-hispana-02%3A1779178461%3A1779183861%3Acarentanwarfare`

Then hard refresh with `Ctrl+F5` and verify:

- Score remains `3 : 2`.
- Winner remains `Aliados`.
- Map remains `Carentan`.
- Duration remains `1 h 30 min`.
- Hero does not show `Partida RCON materializada`.
- The scoreboard area has a large central score, left/right sides, larger faction icons, and compact metadata.
- AntonioPruna still shows 1 kill, 0 deaths, `M1 GARAND`.
- Victim row still shows `death_by` AntonioPruna.
- No timeline/events section is visible.
- No confidence/source/base cards are visible.
- No event labels such as `MESSAGE`, `TEAM SWITCH`, `CONNECTED`, `KILL`, `MATCH START` or `MATCH END` appear.
- No `snapshot`, Elo/MVP block or Comunidad Hispana #03 appears.
- Player table is preserved and readable.
- Layout remains responsive on desktop and mobile.

## Git Requirements

- Use branch `codex/task-138-final-scoreboard-polish`.
- Move only this task from `ai/tasks/pending` to `ai/tasks/done` when complete.
- Add `Outcome` and `Validation Result` sections before completing the task.
- Stage only intended files.
- Commit and push the branch.
- Final git status must be clean.

## Outcome

To be completed by AI Platform Run / Codex CLI.

## Validation Result

To be completed by AI Platform Run / Codex CLI.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split follow-up work into separate tasks if scope grows.
