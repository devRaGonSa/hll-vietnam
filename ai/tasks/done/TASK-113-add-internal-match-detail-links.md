---
id: TASK-113
title: Add internal match detail links
status: pending
type: frontend
team: Frontend Senior
supporting_teams:
  - Backend Senior
roadmap_item: historical
priority: high
---

# TASK-113 - Add internal match detail links

## Goal

Add implementation support so every card in "Ultimas partidas registradas" links to available match data without fabricating unsafe external scoreboard URLs for synthetic RCON competitive-window match IDs.

## Context

The historical page now renders recent matches, but the latest backend response for `/api/historical/snapshots/recent-matches?server=all-servers&limit=5` can return `selected_source: "rcon"` and items with `capture_basis: "rcon-competitive-window"` and no `match_url`.

The previous implementation correctly renders external "Ver partida" links only when a safe source URL exists. However, current RCON competitive-window matches can use synthetic IDs such as `31:2026-04-13T13:59:26.174488Z`, which are not direct scoreboard `/games/{id}` URLs.

Product decision:

- Keep using a safe external `match_url` when one exists.
- For matches without a safe external URL, provide an internal match detail page/link.
- Do not invent external scoreboard URLs for synthetic RCON match IDs.
- Preserve HLL Vietnam's military, Vietnam, tactical and sober visual identity.
- Do not reintroduce paused MVP/Elo UI.
- Do not reintroduce Comunidad Hispana #03.

## Steps

1. Move this task from `ai/tasks/pending/` to `ai/tasks/in-progress/`.
2. Inspect the listed files first.
3. Confirm the recent matches response shape for `/api/historical/snapshots/recent-matches?server=all-servers&limit=5`, including RCON competitive-window items without `match_url`.
4. Keep the existing safe external `match_url` behavior:
   - If a recent match item has a safe external `match_url`, render "Ver partida" or "Abrir en scoreboard".
   - Keep `target="_blank"` and `rel="noopener noreferrer"`.
5. Add internal match detail links for recent matches without an external URL:
   - Render a visible link/button, for example "Ver detalles".
   - Point it to an internal frontend route/page, for example `historico-partida.html?server={serverSlug}&match={encodedMatchId}`.
   - URL-encode the match ID.
6. Add a simple internal match detail frontend page:
   - Suggested file: `frontend/historico-partida.html`.
   - Preserve the current visual identity.
   - Read `server` and `match` from the query string.
   - Call a backend endpoint to get available match details.
   - Show a graceful unavailable or partial-data state if only limited RCON data exists.
7. Add or reuse a backend endpoint for match details:
   - Prefer `/api/historical/matches/detail?server={serverSlug}&match={matchId}`.
   - Return available data for both persisted scoreboard matches and RCON competitive-window matches when available.
   - At minimum return `server`, `match_id`, `map`, `started_at`, `ended_at` or `closed_at`, `duration_seconds` if available, `player_count` or `peak_players` if available, `result` or `score` if available, `capture_basis` or `capabilities` if available, and external `match_url` if a safe one exists.
   - Do not fabricate external scoreboard URLs for synthetic RCON IDs.
8. Preserve the existing historical page sections and selector behavior:
   - summary
   - basic rankings
   - recent matches
   - server selector with only Todos, Comunidad Hispana #01 and Comunidad Hispana #02
9. Keep these blocks paused or hidden:
   - MVP mensual V1
   - MVP mensual V2
   - Comparativa V1 vs V2
   - Elo/MMR mensual
10. Validate the result with all checks listed below.
11. Move this task to `ai/tasks/done/` only after validation is complete and document the outcome in this file.
12. Commit and push the completed implementation branch.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/frontend-senior.md`
- `ai/orchestrator/backend-senior.md`
- `frontend/historico.html`
- `frontend/assets/js/historico.js`
- `frontend/assets/css/historico.css`
- `backend/app/routes.py`
- `backend/app/payloads.py`
- `backend/app/historical_storage.py`
- `backend/app/historical_snapshots.py`
- any RCON competitive/recent match read model modules
- `scripts/run-integration-tests.ps1`
- `docs/decisions.md`

## Expected Files to Modify

- `frontend/historico.html`
- `frontend/assets/js/historico.js`
- `frontend/assets/css/historico.css`
- possibly new `frontend/historico-partida.html`
- possibly new `frontend/assets/js/historico-partida.js`
- possibly `backend/app/routes.py`
- possibly `backend/app/payloads.py`
- possibly `backend/app/historical_storage.py`
- possibly historical snapshot/read model modules
- possibly tests under `backend/tests/`
- this task file, moved to `ai/tasks/done/`

If additional files become necessary, explain why in the task outcome and commit message.

## Expected Files Not to Modify

- Docker/Compose config
- local `.env`
- database migrations unless absolutely required and justified
- persisted data
- Elo/MMR backend implementation files
- unrelated frontend pages

## Constraints

- Keep the change focused on internal detail links and match detail data.
- Do not delete backend code, migrations, persisted data, snapshots or endpoints.
- Do not change historical ingestion policy.
- Do not reintroduce Comunidad Hispana #03.
- Do not reintroduce MVP/Elo UI.
- Do not add real credentials.
- Do not introduce unnecessary frontend frameworks or dependencies.
- Preserve direct browser compatibility where applicable.
- Preserve HLL Vietnam branding and product identity.
- Do not use public "snapshot" wording in user-facing copy.
- Confirm `backend/runtime/` is not created or committed.

## Validation

Before completing the task, run:

- `git status`
- `node --check frontend/assets/js/historico.js`
- If a new frontend JS file is added, run `node --check` on it too.
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- `docker compose down`
- `docker compose up -d --build`
- `docker compose ps`
- `Invoke-WebRequest http://localhost:8000/health | Select-Object -ExpandProperty Content`
- `Invoke-WebRequest http://localhost:8080 | Select-Object -ExpandProperty StatusCode`
- `Invoke-WebRequest "http://localhost:8000/api/historical/snapshots/recent-matches?server=all-servers&limit=5" | Select-Object -ExpandProperty Content`
- Validate the new match detail endpoint for at least one recent match ID.

Manual or served HTML verification:

- Recent match cards show either external "Ver partida" or internal "Ver detalles".
- The internal detail page opens and displays available data.
- No server #03 appears.
- No paused MVP/Elo blocks appear.
- No public "snapshot" wording appears.
- No migrations or persisted data changed unless explicitly justified.
- `backend/runtime/` is not created or committed.

Before committing, also review:

- `git diff --name-only`
- changed files match the expected scope

## Commit And Push Requirements

- Run validation before committing.
- Run `git status`.
- Stage only intended files.
- Commit with a clear message, for example `feat: add internal match detail links`.
- Push the branch to origin.
- Do not leave completed work only in local.

## Outcome

Document the validation performed, notable implementation decisions, and any follow-up task that should be created instead of expanding this task.

Completed.

Validation performed:

- Confirmed `/api/historical/snapshots/recent-matches?server=all-servers&limit=5` returns `selected_source: "rcon"` with RCON competitive-window items such as `31:2026-04-13T13:59:26.174488Z`, `capture_basis: "rcon-competitive-window"` and no `match_url`.
- Ran `node --check frontend/assets/js/historico.js`.
- Ran `node --check frontend/assets/js/historico-partida.js`.
- Ran Python syntax compilation for the touched backend modules.
- Ran `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`; the script reports no product integration tests are configured for this platform-only scope and passed the backend startup import check.
- Ran `docker compose down`.
- Ran `docker compose up -d --build`.
- Ran `docker compose ps`; backend and frontend were up on ports 8000 and 8080.
- Verified `http://localhost:8000/health`.
- Verified `http://localhost:8080`.
- Verified `http://localhost:8000/api/historical/snapshots/recent-matches?server=all-servers&limit=5`.
- Verified `http://localhost:8000/api/historical/matches/detail?server=comunidad-hispana-01&match=31%3A2026-04-13T13%3A59%3A26.174488Z` returns the RCON detail internally with `match_url: null`.
- Used headless Chrome against `http://localhost:8080/historico.html`; recent RCON cards render `Ver detalles`.
- Used headless Chrome against `http://localhost:8080/historico-partida.html?...`; the internal detail page renders available RCON data and the `Ventana competitiva RCON` capture basis.
- Confirmed no `backend/runtime/` path exists.

Implementation decisions:

- Preserved the existing safe external `match_url` behavior and added `Ver detalles` only when no safe external URL exists.
- Added `frontend/historico-partida.html` and `frontend/assets/js/historico-partida.js` as a direct-browser-compatible internal detail page.
- Added `/api/historical/matches/detail?server={serverSlug}&match={matchId}`.
- Added persisted public-scoreboard detail lookup and exact RCON competitive-window detail lookup.
- Kept synthetic RCON match IDs internal and did not fabricate external scoreboard URLs.
- Did not reintroduce paused MVP/Elo UI or Comunidad Hispana #03 in the frontend selector.

Scope note:

- The task exceeded the preferred 5-file/200-line budget because it required both a new internal frontend page and a backend detail endpoint/read path for two historical sources. No migrations, persisted data, Docker config, `.env`, Elo/MMR implementation files or unrelated frontend pages were changed.

Follow-up:

- No follow-up task is required from this implementation. A future task could add richer player-level detail if the RCON historical model later exposes player stats.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
