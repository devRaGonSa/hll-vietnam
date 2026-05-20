---
id: TASK-135
title: Fix RCON match detail faction assets and icon display
status: done
type: frontend
team: Frontend Senior
supporting_teams:
  - Experto en interfaz
roadmap_item: rcon-full-data
priority: high
---

# TASK-135 - Fix RCON Match Detail Faction Assets And Icon Display

## Goal

Polish faction presentation in the historical RCON match detail scoreboard so faction icons load reliably, are visibly larger, and no longer show long descriptive faction subtitles.

## Context

The historical match detail page already renders a RCON/materialized match detail view with a scoreboard-like result block, player table, local faction image paths, and local map/faction assets being added by the user.

The current direction is acceptable, especially the central result with score, map, Warfare and winner. Remaining rough details are visual and asset-related:

- German/Eje icon is not visible, likely due to wrong asset path or name.
- Faction icons are too small.
- Faction subtitles such as `Fuerzas estadounidenses` and `Ejército alemán` should be removed.
- Event timeline must remain hidden.
- Confidence/source/base must remain hidden.
- No `snapshot` wording.
- No Elo/MVP blocks.
- No Comunidad Hispana #03.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/frontend-senior.md`
- `frontend/historico-partida.html`
- `frontend/assets/js/historico-partida.js`
- relevant CSS used by `historico-partida.html`

## Expected Files to Modify

- `frontend/assets/js/historico-partida.js`
- relevant CSS used by `historico-partida.html`
- this task file when moving it from `ai/tasks/pending` to `ai/tasks/done`

If additional files are necessary, document why in the task outcome.

## Implementation Requirements

1. Work from a dedicated branch: `codex/task-135-faction-assets`.
2. Verify faction assets exist in `frontend/assets/img/factions`.
3. Use `.webp` paths, not `.svg`, for faction icons:
   - `frontend/assets/img/factions/us.webp`
   - `frontend/assets/img/factions/germany.webp`
   - `frontend/assets/img/factions/soviets.webp`
   - `frontend/assets/img/factions/britain.webp`
4. Fix the German/Eje icon not displaying.
5. Add graceful fallback if any faction image is missing.
6. Increase faction icon size in the scoreboard layout.
7. Remove long faction subtitle text such as:
   - `Fuerzas estadounidenses`
   - `Ejército alemán`
   - `Fuerzas británicas`
   - `Ejército soviético`
8. Keep only main side/faction labels:
   - `Aliados`
   - `Eje`
   - `Soviéticos`, `Británicos` or `USA` only if needed
9. Do not show long descriptive subtitles under faction labels.
10. Keep the winner marker if it remains visually subtle.
11. Preserve the player table.
12. Keep the event timeline hidden.
13. Keep confidence/source/base hidden.
14. Do not add implementation/debug text to the UI.

## Constraints

- Keep the change small and focused.
- Preserve the dark HLL Vietnam visual identity.
- Do not introduce frameworks or dependencies.
- Do not modify backend behavior unless a minimal fallback contract issue is discovered and documented.
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
- German/Eje icon is visible.
- Faction icons are larger than before.
- Long faction descriptions are gone.
- AntonioPruna still shows 1 kill, 0 deaths, `M1 GARAND`.
- Victim row still shows `death_by` AntonioPruna.
- No timeline/events section is visible.
- No confidence/source/base cards are visible.
- No `snapshot`, Elo/MVP block or Comunidad Hispana #03 appears.

## Git Requirements

- Use branch `codex/task-135-faction-assets`.
- Move only this task from `ai/tasks/pending` to `ai/tasks/done` when complete.
- Add `Outcome` and `Validation Result` sections before completing the task.
- Stage only intended files.
- Commit and push the branch.
- Final git status must be clean.

## Outcome

- Updated `frontend/assets/js/historico-partida.js` to use the required local `.webp` faction paths for USA, Germany, Soviets and Britain.
- Renamed the user-provided faction assets in `frontend/assets/img/factions/` from short names to the required contract names: `germany.webp`, `soviets.webp` and `britain.webp`.
- Removed visible long faction subtitles from the scoreboard side blocks while preserving the main `Aliados` and `Eje` labels and the subtle winner marker.
- Increased faction emblem sizing in `frontend/assets/css/historico-scoreboard-detail.css` and added a silent missing-image fallback class so a broken image does not show a visible broken icon.
- Event timeline, confidence/source/base cards, snapshot wording, Elo/MVP blocks and Comunidad Hispana #03 were not reintroduced.

## Validation Result

- PASS: `node --check frontend/assets/js/historico-partida.js`
- PASS: `node --check frontend/assets/js/historico.js`
- PASS: `node --check frontend/assets/js/historico-recent-live.js`
- PASS: `python -m compileall backend/app`
- PASS: `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- PASS: `powershell -ExecutionPolicy Bypass -File scripts/run-rcon-data-pipeline-tests.ps1`
  - Note: the script completed successfully but emitted existing `ResourceWarning` messages from backend unittest sqlite connections.
- PASS: `docker compose up -d --build backend frontend`
- PASS: `Invoke-WebRequest "http://localhost:8000/health" | Select-Object -ExpandProperty Content`
- PASS after stopping already-running advanced historical workers: `Invoke-WebRequest "http://localhost:8000/api/historical/recent-matches?server=all-servers&limit=10" | Select-Object -ExpandProperty Content`
  - The first attempt failed because the backend could not set SQLite journal mode while the historical worker services were active against the mounted DB. `docker compose stop historical-runner rcon-historical-worker` cleared the validation conflict.
- Manual/rendered verification: Browser plugin was listed, but the required Node runtime tool was not exposed in this session; used local Chrome headless fallback.
  - Verified DOM contains `3 : 2`, `Ganador: Aliados`, `Carentan`, `1 h 30 min`, `AntonioPruna`, `M1 GARAND`, `us.webp` and `germany.webp`.
  - Verified long faction descriptions are absent from rendered DOM.
  - Verified timeline section remains hidden.
  - Captured desktop and mobile screenshots outside the repository at `C:\Temp\task-135-match-detail.png` and `C:\Temp\task-135-match-detail-mobile.png`.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split follow-up work into separate tasks if scope grows.
