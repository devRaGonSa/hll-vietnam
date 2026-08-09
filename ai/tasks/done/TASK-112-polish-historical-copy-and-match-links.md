---
id: TASK-112
title: Polish historical copy and add recent match links
status: pending
type: frontend
team: Frontend Senior
supporting_teams: [Backend Senior, PM]
roadmap_item: historical-ui
priority: high
---

# TASK-112 - Polish historical copy and add recent match links

## Goal

Polish the public historical page copy so implementation words stay hidden from users, and add source links to recent match cards when a safe persisted match URL is available.

## Context

HLL Vietnam has hidden the paused MVP/Elo UI from the public historical page. Manual visual review found three remaining issues:

- The ranking note includes this awkward fallback sentence: "Se muestra el ultimo periodo cerrado porque el actual todavia solo suma 0 cierres."
- Public UI copy still exposes the technical word "snapshot".
- Recent match cards show match IDs but do not link to the original match detail page.

Current product decisions remain unchanged:

- Keep historical ingestion active.
- Keep historical policy RCON-first, with public-scoreboard fallback only where RCON fails, lacks coverage or lacks parity for a specific historical operation.
- Keep Elo/MMR and advanced MVP UI paused.
- Hide technical implementation wording from public users.
- Add match links only when a persisted or safely derivable source URL is available.

Use branch:

- `chore/polish-historical-copy-and-match-links`

## Steps

1. Work on branch `chore/polish-historical-copy-and-match-links`.
2. Inspect the listed files before changing anything.
3. Remove the public sentence:
   "Se muestra el ultimo periodo cerrado porque el actual todavia solo suma 0 cierres."
   from the ranking note/copy.
4. Keep the ranking note useful if needed, but do not expose the awkward fallback explanation.
5. Remove the word "snapshot" from public UI copy.
6. Keep internal function names unchanged if renaming them would increase risk.
7. Use Spanish, product-friendly public alternatives where needed, such as:
   - "datos precalculados"
   - "datos actualizados"
   - "registro"
   - "ultima actualizacion"
   - "datos disponibles"
8. Avoid "snapshot" in visible text, loading states, errors and metadata.
9. Add match links for the recent matches section ("Ultimas partidas registradas") when a safe URL exists:
   - Backend recent matches payload should expose a safe URL field such as `match_url` or `source_url`.
   - Prefer using the persisted `raw_payload_ref` from `historical_matches` if available.
   - If `raw_payload_ref` is unavailable, derive the URL only if the server source/base URL and external match id are available and already trusted by existing historical server configuration.
   - Do not expose credentials or internal filesystem paths.
   - Frontend recent match cards should render a visible link/button such as "Ver partida" when the URL exists.
   - The link must open in a new tab with `target="_blank"` and `rel="noopener noreferrer"`.
   - If no URL exists, keep the current card layout without a broken link.
10. Preserve existing normal historical UI:
    - summary
    - basic historical rankings
    - recent matches
    - server selector with only Todos, Comunidad Hispana #01, Comunidad Hispana #02
11. Keep these paused/hidden:
    - MVP mensual V1
    - MVP mensual V2
    - Comparativa V1 vs V2
    - Elo/MMR mensual
12. Do not change the historical ingestion policy or reintroduce Comunidad Hispana #03.
13. Update `docs/decisions.md` only if the implementation changes a documented contract or public historical UI assumption.
14. Validate the result.
15. Move this task file to `ai/tasks/done/` after validation is complete and the outcome is documented.
16. Commit and push the completed work to origin. Do not leave completed work only in local.

## Files to Read First

- `frontend/historico.html`
- `frontend/assets/js/historico.js`
- `frontend/assets/css/historico.css`
- `backend/app/historical_storage.py`
- `backend/app/historical_snapshots.py`
- `backend/app/payloads.py`
- `backend/app/routes.py`
- `backend/tests/` if present
- `docs/decisions.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`

Rules:

- Read these files before implementation.
- Keep the implementation scoped to public historical page copy, recent match payload shape and recent match card rendering.
- Do not change backend historical ingestion policy.

## Expected Files to Modify

- `frontend/assets/js/historico.js`
- possibly `frontend/assets/css/historico.css`
- possibly `backend/app/historical_storage.py`
- possibly `backend/app/historical_snapshots.py`
- possibly `backend/app/payloads.py`
- possibly backend tests if present
- possibly `docs/decisions.md`
- `ai/tasks/done/TASK-112-polish-historical-copy-and-match-links.md`

Rules:

- Prefer modifying only these files.
- If additional files become necessary, explain why in the task outcome and commit message.
- The task file should be moved from `ai/tasks/pending/` to `ai/tasks/done/` only after validation is complete.

## Expected Files Not to Modify

- `frontend/index.html`
- Docker/Compose configuration
- local `.env`
- database migrations
- persisted data
- Elo/MMR backend implementation files
- historical ingestion policy/config
- unrelated backend modules
- unrelated frontend pages

## Constraints

- Keep the change minimal and verifiable.
- Preserve HLL Vietnam project identity: military, Vietnam, tactical, sober.
- Do not reintroduce paused MVP/Elo UI.
- Do not reintroduce Comunidad Hispana #03.
- Do not change historical ingestion policy.
- Do not delete backend code, migrations, snapshots/data or endpoints.
- Do not add real credentials, secrets, passwords or tokens.
- Do not expose credentials or internal filesystem paths through match URLs.
- Do not introduce unnecessary frameworks or dependencies.
- Keep frontend changes compatible with direct browser opening where applicable.
- Confirm `backend/runtime/` is not created or committed.

## Validation

Before completing the task:

1. Run `git status`.
2. Run `node --check frontend/assets/js/historico.js`.
3. Run `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`.
4. Run `docker compose down`.
5. Run `docker compose up -d --build`.
6. Run `docker compose ps`.
7. Run `Invoke-WebRequest http://localhost:8000/health | Select-Object -ExpandProperty Content`.
8. Run `Invoke-WebRequest http://localhost:8080 | Select-Object -ExpandProperty StatusCode`.
9. Verify served `historico.html`/JS output or manual browser:
   - no visible word "snapshot"
   - no visible sentence "Se muestra el ultimo periodo cerrado porque el actual todavia solo suma 0 cierres."
   - recent match cards still render
   - when a match URL exists, a "Ver partida" link appears
   - server #03 is not visible
   - paused MVP/Elo blocks remain hidden
10. Confirm no database migrations or persisted data changed.
11. Confirm `backend/runtime/` is not created or committed.
12. Review `git diff --name-only` and confirm changed files match the expected scope.

If a configured validation command cannot be run, document the exact reason in the outcome.

## Commit And Push Requirements

1. Run validation before committing.
2. Run `git status`.
3. Stage only intended files.
4. Commit with a clear message, for example:
   `chore: polish historical copy and match links`
5. Push the branch to origin.
6. Do not leave completed work only in local.

## Outcome

Completed.

- Validation performed:
  - `git status --short`
  - `node --check frontend/assets/js/historico.js`
  - `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
  - `docker compose down`
  - `docker compose up -d --build`
  - `docker compose ps`
  - `Invoke-WebRequest http://localhost:8000/health | Select-Object -ExpandProperty Content`
  - `Invoke-WebRequest http://localhost:8080 | Select-Object -ExpandProperty StatusCode`
  - served `historico.html` and `historico.js` copy checks for removed public fallback/snapshot wording
  - focused temporary-storage check confirming `match_url` is exposed from a safe persisted match reference
- Public copy changes made:
  - Removed the fallback sentence about showing the previous closed period because the current one had 0 closures.
  - Replaced visible `snapshot` wording in loading states, errors, metadata and empty copy with product-facing Spanish alternatives such as `datos`, `datos precalculados`, `registro` and `resumen`.
  - Corrected the all-servers summary note copy.
- Backend payload field used for match links: `match_url`.
- URL source: persisted `historical_matches.raw_payload_ref`, accepted only when it is an HTTP(S) `/games/` URL on the configured historical server `scoreboard_base_url`.
- No credentials or internal filesystem paths are exposed through `match_url`; unsafe or off-origin values resolve to no link.
- Normal historical UI still renders through the served frontend and backend health checks.
- Comunidad Hispana #03 remains absent from the public selector, and paused MVP/Elo blocks were not reintroduced to `historico.html`.
- No migrations, persisted data, or `backend/runtime/` were changed or committed.
- Browser plugin note: the Browser plugin's Node execution tool was not exposed in this session after discovery, so rendered-page acceptance was verified through served frontend/API checks instead.
- Commit hash and push result: pending commit/push step.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into a follow-up task if the scope grows beyond public copy, recent match URL payloads and recent match card rendering.
