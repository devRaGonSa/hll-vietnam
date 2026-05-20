---
id: TASK-137
title: Add public scoreboard link to match detail
status: pending
type: frontend
team: Frontend Senior
supporting_teams:
  - Backend Senior
  - Arquitecto Python
roadmap_item: rcon-full-data
priority: high
---

# TASK-137 - Add Public Scoreboard Link To Match Detail

## Goal

Show a safe public scoreboard action on the historical match detail page when the current match has a valid public `match_url`.

## Context

The historical detail page should let users open the public scoreboard match page for the same match when a safe link is available. The button should not appear for broken, missing or unsafe URLs.

Known constraints:

- Use the existing backend `match_url` field when available.
- If a materialized RCON detail has no `match_url`, use existing scoreboard correlation/link resolver if already present.
- If correlation requires backend changes, keep them minimal and covered by tests.
- Keep allowlist safety for scoreboard URLs:
  - `https://scoreboard.comunidadhll.es/`
  - `https://scoreboard.comunidadhll.es:5443/`
- Recent match cards must keep their current behavior.
- Detail page must still work without the external link.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/frontend-senior.md`
- `ai/orchestrator/backend-senior.md`
- `frontend/historico-partida.html`
- `frontend/assets/js/historico-partida.js`
- backend historical/read-model modules that expose match detail and `match_url`

## Expected Files to Modify

- `frontend/historico-partida.html`
- `frontend/assets/js/historico-partida.js`
- relevant CSS used by `historico-partida.html`
- minimal backend historical/read-model or tests only if required for existing `match_url` correlation
- this task file when moving it from `ai/tasks/pending` to `ai/tasks/done`

If additional files are necessary, document why in the task outcome.

## Implementation Requirements

1. Work from a dedicated branch: `codex/task-137-scoreboard-link`.
2. Show a visible button/link in the match detail page with one of these labels:
   - `Ver en Scoreboard`
   - `Ver detalles completos`
3. The button must open the public scoreboard match page in a new tab.
4. Only show the button when a safe `match_url` exists.
5. Do not show broken links.
6. Use the existing backend `match_url` field when available.
7. If materialized RCON detail has no `match_url`, use existing scoreboard correlation/link resolver if already present.
8. If correlation requires backend changes, keep them minimal and covered by tests.
9. Preserve allowlist safety for scoreboard URLs:
   - `https://scoreboard.comunidadhll.es/`
   - `https://scoreboard.comunidadhll.es:5443/`
10. Recent match cards must keep their current behavior.
11. Detail page must still work without the external link.
12. Preserve the player table.
13. Keep event timeline hidden.
14. Keep confidence/source/base hidden.
15. Do not show implementation/debug text in the UI.

## Constraints

- Keep the change minimal and focused.
- Preserve the dark HLL Vietnam visual identity.
- Do not introduce frameworks or dependencies.
- Do not create a broad backend refactor.
- Do not modify unrelated files.
- Do not reintroduce event timeline, confidence/source/base cards, `snapshot` wording, Elo/MVP blocks or Comunidad Hispana #03.

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
- `Ver en Scoreboard` or equivalent only appears when a valid `match_url` exists.
- The scoreboard action opens a safe public scoreboard URL in a new tab.
- No broken or unsafe link is shown when `match_url` is absent or invalid.
- Recent match cards keep their current behavior.
- AntonioPruna still shows 1 kill, 0 deaths, `M1 GARAND`.
- Victim row still shows `death_by` AntonioPruna.
- No timeline/events section is visible.
- No confidence/source/base cards are visible.
- No `snapshot`, Elo/MVP block or Comunidad Hispana #03 appears.

## Git Requirements

- Use branch `codex/task-137-scoreboard-link`.
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
