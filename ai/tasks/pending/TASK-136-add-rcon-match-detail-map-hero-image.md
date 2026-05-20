---
id: TASK-136
title: Add RCON match detail map hero image
status: pending
type: frontend
team: Frontend Senior
supporting_teams:
  - Experto en interfaz
  - Disenador grafico
roadmap_item: rcon-full-data
priority: high
---

# TASK-136 - Add RCON Match Detail Map Hero Image

## Goal

Add local map image support to the historical RCON match detail page and show the current match map image prominently in the top hero/header area.

## Context

The historical match detail page currently shows the central result data well enough, but the top hero/header area should include the match map image, preferably on the right side. The community logo can stay where it is or be reduced if needed, but the map image should become a clear first-viewport visual element.

For the known Carentan match, the UI must map the displayed map to:

- `frontend/assets/img/maps/carentan-day.webp`

The implementation should use local map assets under `frontend/assets/img/maps` and hide the image area gracefully when no asset is available.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/frontend-senior.md`
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

1. Work from a dedicated branch: `codex/task-136-map-hero-image`.
2. Add map image support on `historico-partida.html` / `historico-partida.js`.
3. Display the current map image in the top hero/header area, preferably on the right side.
4. Keep the community logo where it is or reduce it if needed, while adding a prominent map image to the right.
5. Use map assets from `frontend/assets/img/maps`.
6. Add a robust JavaScript mapper from map name / `pretty_name` to asset path.
7. For the known Carentan match, map to `frontend/assets/img/maps/carentan-day.webp`.
8. Account for likely available asset names:
   - `carentan-day.webp`
   - `stmereeglise-day.webp`
   - `stmariedumont-day.webp`
   - `utahbeach-day.webp`
   - `omahabeach-day.webp`
   - `purpleheartlane-rain.webp`
   - `hurtgenforest-day.webp`
   - `foy-day.webp`
   - `kursk-day.webp`
   - `kharkov-day.webp`
   - `driel-day.webp`
   - `elalamein-day.webp`
   - `tobruk-day.webp`
   - `tobruk-dawn.webp`
   - `mortain-day.webp`
   - `hill400-day.webp`
   - `elsenbornridge-day.webp`
   - `smolensk-day.webp`
9. If no map image is found, hide the image area gracefully.
10. Keep the layout responsive.
11. Do not show implementation/debug text in the UI.
12. Preserve the player table.
13. Keep event timeline hidden.
14. Keep confidence/source/base hidden.

## Constraints

- Keep the change small and focused.
- Preserve the dark HLL Vietnam visual identity.
- Do not introduce frameworks or dependencies.
- Do not modify backend unless a minimal API field issue is strictly necessary and documented.
- Do not modify unrelated files.
- Do not show `snapshot` wording, Elo/MVP blocks or Comunidad Hispana #03.

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
- Map image appears in the hero/right area.
- For the known Carentan match, the image uses `frontend/assets/img/maps/carentan-day.webp`.
- Layout remains responsive on desktop and mobile.
- AntonioPruna still shows 1 kill, 0 deaths, `M1 GARAND`.
- Victim row still shows `death_by` AntonioPruna.
- No implementation/debug text appears.
- No timeline/events section is visible.
- No confidence/source/base cards are visible.
- No `snapshot`, Elo/MVP block or Comunidad Hispana #03 appears.

## Git Requirements

- Use branch `codex/task-136-map-hero-image`.
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
