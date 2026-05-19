---
id: TASK-134
title: Redesign RCON match detail scoreboard layout
status: pending
type: frontend
team: Frontend Senior
supporting_teams:
  - UX/UI Specialist
  - Backend Senior
roadmap_item: rcon-full-data
priority: high
---

# TASK-134 - Redesign RCON Match Detail Scoreboard Layout

## Goal

Redesign the internal RCON match detail page so the match result is presented like a simplified scoreboard, not as many independent summary cards.

The current page technically works, but the layout feels too fragmented because server, map, mode, marker, winner, result, start, end, confidence, source, base and timeline are all shown as separate cards. The user wants a cleaner scoreboard-like match header with the score centered and each faction/team shown on either side.

## Background

HLL Vietnam now has a RCON-first materialized match pipeline. The internal match detail page already renders materialized RCON match data for known matches such as:

- server: `comunidad-hispana-02`
- match: `comunidad-hispana-02:1779178461:1779183861:carentanwarfare`
- encoded match: `comunidad-hispana-02%3A1779178461%3A1779183861%3Acarentanwarfare`

Current data is valid:

- map: Carentan
- score: 3 - 2
- winner: Aliados
- duration: 1 h 30 min
- players include AntonioPruna with 1 kill, 0 deaths and M1 GARAND
- victim row includes death_by AntonioPruna

The user has requested a visual redesign:

- The score must appear centered, similar to the public scoreboard.
- Each side/team/faction must be displayed on each side of the score.
- The separate cards for confidence, source and base must not be shown.
- The event timeline/counts section must not be shown at all.
- Start can remain visible.
- Do not show misleading unavailable technical data prominently.

## Constraints

- Frontend-focused task.
- Do not change the RCON materialization model unless absolutely necessary.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Do not show `snapshot` wording.
- Do not show paused MVP/Elo blocks.
- Do not add charts.
- Do not break recent match cards.
- Do not break direct opening of `historico-partida.html?server=...&match=...`.
- Keep the visual style consistent with the existing HLL Vietnam theme.
- Do not expose raw player ids.
- Public scoreboard remains optional link/enrichment only.

## Allowed Changes

- `frontend/historico-partida.html`
- `frontend/assets/js/historico-partida.js`
- `frontend/assets/css/historico.css`
- `frontend/assets/js/historico.js` only if needed to preserve navigation into detail.
- Backend read model only if the frontend is missing a small field needed for team/faction display, but avoid backend changes if possible.
- This task file when moving it through the workflow.

## Implementation Requirements

1. Work from branch `codex/task-134-rcon-match-scoreboard-layout`.
2. Redesign the match detail summary area into a scoreboard-style header/score strip.
3. The central area must show the result prominently, for example:

   ```text
   Aliados        3 - 2        Eje
   ```

   If the API only provides winner/result and not factions, use default side labels:

   - `Aliados`
   - `Eje`

   If faction/team names are later available, use them safely.

4. The score must be visually central and more prominent than the surrounding metadata.
5. Place map, mode, server and duration as secondary metadata below or around the scoreboard header, not as many separate large cards.
6. Keep `Inicio` visible, but if it is unavailable show `Inicio: No disponible` in a compact metadata row.
7. Do not show `Fin` if it is unavailable. If it is available and reliable, it may be shown in the compact metadata row.
8. Remove/hide the visible cards for:
   - `Confianza`
   - `Fuente`
   - `Base`
9. Remove/hide the whole timeline/event-count section from the public detail page:
   - no `Eventos` heading
   - no `Línea de tiempo`
   - no event count tiles such as MESSAGE, TEAM SWITCH, CONNECTED, KILL, MATCH START, MATCH END
10. Keep the player stats table visible and readable.
11. Keep columns or equivalent visible information for:
    - Jugador
    - Equipo
    - K
    - D
    - TK
    - K/D
    - Armas
    - Más abatido
    - Muere por
12. If a cell has no data, continue to show a controlled text such as `No disponible`.
13. Preserve known match values:
    - Score 3 - 2
    - Winner Aliados
    - Duration 1 h 30 min
    - AntonioPruna 1/0 and M1 GARAND
    - victim row death_by AntonioPruna
14. Keep layout responsive for desktop and reasonable mobile widths.
15. Avoid showing implementation-heavy labels to normal users.
16. If any technical/debug detail remains, it must be visually secondary and not in the hero/header.

## Validation Commands

Run:

```powershell
node --check frontend/assets/js/historico.js
node --check frontend/assets/js/historico-partida.js
node --check frontend/assets/js/historico-recent-live.js
python -m compileall backend/app
powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1
powershell -ExecutionPolicy Bypass -File scripts/run-rcon-data-pipeline-tests.ps1
docker compose up -d --build backend frontend
```

Check backend endpoints:

```powershell
Invoke-WebRequest "http://localhost:8000/health" | Select-Object -ExpandProperty Content
Invoke-WebRequest "http://localhost:8000/api/historical/recent-matches?server=all-servers&limit=10" | Select-Object -ExpandProperty Content
```

Open the known detail page:

```powershell
$matchId = [uri]::EscapeDataString("comunidad-hispana-02:1779178461:1779183861:carentanwarfare")
Start-Process "http://localhost:8080/historico-partida.html?server=comunidad-hispana-02&match=$matchId"
```

## Manual Verification Steps

Verify visually:

- Match detail result is no longer shown as separated summary cards for marker/winner/result.
- The score is centered and prominent.
- Aliados and Eje/team sides are shown around the score.
- Server, map, mode, duration and start are compact secondary metadata.
- `Confianza` is not visible.
- `Fuente` is not visible.
- `Base` is not visible.
- The event timeline section is completely absent.
- No event count tiles are visible.
- Player table remains visible.
- AntonioPruna still shows 1 kill, 0 deaths and M1 GARAND.
- Victim row still shows 1 death and `Muere por AntonioPruna`.
- No `snapshot` wording.
- No Elo/MVP blocks.
- No Comunidad Hispana #03.
- Recent matches page still links to the detail page.

## Git Requirements

- Create/use branch `codex/task-134-rcon-match-scoreboard-layout`.
- Run the validations above.
- Stage only intended files.
- Move this task file from `ai/tasks/pending` to `ai/tasks/done` when completed.
- Add `Outcome` and `Validation Result` sections to the completed task.
- Commit with message:

  ```text
  feat: redesign rcon match detail scoreboard layout
  ```

- Push branch to origin.
- Final git status must be clean.

## Notes

This task intentionally removes some currently visible diagnostic data from the user-facing detail page. The data can remain available in API responses or future admin/debug views, but the public match detail UI should focus on scoreboard-style readability and player stats.
