---
id: TASK-147
title: Persist public scoreboard list matches as RCON candidates
status: pending
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto Python
roadmap_item: rcon-full-data
priority: high
---

# TASK-147 - Persist public scoreboard list matches as RCON candidates

## Goal

Make `scoreboard_candidate_backfill` persist safe rows into
`rcon_scoreboard_match_candidates` directly from `/api/get_scoreboard_maps`
list payloads, so public scoreboard URLs are available for RCON correlation
even if `/api/get_map_scoreboard` detail fetching fails, returns a different
shape, or lacks fields.

## Background

A real Foy match existed in the scoreboard public list:

- scoreboard id: `1562115`
- server_number: `2`
- server slug: `comunidad-hispana-02`
- map: Foy Warfare
- start: `2026-05-20T20:54:11+00:00`
- end: `2026-05-20T22:24:11+00:00`
- score: allied `4` / axis `1`
- expected URL: `https://scoreboard.comunidadhll.es:5443/games/1562115`

But it was not available as an RCON scoreboard candidate until manually
inserted. After manual insert and materialization, the match detail page
correctly showed `Ver en Scoreboard`.

The backfill currently reads `/api/get_scoreboard_maps`, collects IDs, fetches
detail payloads, and calls `upsert_historical_match` from detail payloads. The
list payload already contains enough trusted data for a safe candidate:
`id`, `start`, `end`, `map.id`, `map.pretty_name`, `result.allied`,
`result.axis`, and `server_number`.

## Constraints / DO NOT BREAK

- Do not remove PostgreSQL migration logic.
- Do not switch back to SQLite.
- Do not break recent match cards.
- Do not show `Ver partida` in recent cards.
- Do not change detail-page scoreboard button behavior except enabling it when
  `match_url` exists.
- Do not expose unsafe URLs.
- Do not generate scoreboard URLs from player names.
- Do not commit runtime DB files.

## Allowed Changes

- `backend/app/scoreboard_candidate_backfill.py`
- Existing backend storage/read-model helpers needed for the safe candidate
  upsert path.
- Existing trusted scoreboard origin helpers needed to preserve URL safety.
- Focused backend scoreboard tests and fixtures/mocks.
- This task file when it moves through the task workflow.

## Implementation Requirements

1. Inspect:
   - `backend/app/scoreboard_candidate_backfill.py`
   - `backend/app/postgres_rcon_storage.py`
   - `backend/app/postgres_display_storage.py`
   - `backend/app/historical_storage.py`
   - `backend/app/rcon_admin_log_materialization.py`
   - `backend/app/rcon_historical_read_model.py`
   - `backend/app/scoreboard_origins.py`
2. Add or reuse a safe upsert function for
   `rcon_scoreboard_match_candidates`.
3. During `scoreboard_candidate_backfill`, for every list match inside the
   requested window:
   - build a candidate from the list payload
   - validate `server_number` / `server_slug` mapping
   - build `match_url` only from trusted scoreboard base URL and numeric
     external match id
   - persist candidate idempotently into
     `rcon_scoreboard_match_candidates`
4. This candidate upsert must happen before `fetch_match_details`.
5. `fetch_match_details` must remain only for historical match/player stat
   enrichment.
6. If `fetch_match_details` fails, the candidate row must still exist.
7. Add counters to the JSON report:
   - `list_candidates_inserted`
   - `list_candidates_updated`
   - `list_candidates_skipped`
   - detail candidate/detail match counters if useful
8. Keep existing historical upsert behavior.
9. Preserve trusted URL allowlist behavior.
10. Do not create candidates for untrusted origins.
11. Do not reintroduce Comunidad Hispana #03 as an active visible target.
12. Add tests covering a list payload equivalent to Foy `1562115`.
13. The test must prove:
   - list payload alone persists candidate
   - `match_url` is
     `https://scoreboard.comunidadhll.es:5443/games/1562115`
   - failure of detail fetch does not prevent candidate persistence
   - operation is idempotent

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/backend-senior.md`
- `backend/app/scoreboard_candidate_backfill.py`
- `backend/app/postgres_rcon_storage.py`

## Expected Files to Modify

- Backfill/storage helper files needed for the safe list-candidate upsert.
- Focused scoreboard tests covering list-only persistence and detail failure.
- This task file after moving it through the workflow.

Keep the task within the allowed changes. If a storage boundary requires an
additional backend file from the inspected list, document why in the task
outcome.

## Validation

- `python -m compileall backend/app`
- `python -m unittest discover -s tests -p "*scoreboard*"`
- `python -m app.storage_diagnostics`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- `docker compose --profile advanced up -d --build backend frontend postgres`
- `docker compose exec backend python -m app.scoreboard_candidate_backfill --server comunidad-hispana-02 --from 2026-05-20T00:00:00Z --to 2026-05-21T23:59:59Z --max-pages 5 --page-size 100`
- Query `rcon_scoreboard_match_candidates` and verify external match id
  `1562115` exists for `comunidad-hispana-02`.
- Invoke the detail endpoint for
  `comunidad-hispana-02:1779310451:1779315851:foywarfare` and verify
  `match_url` is present.
- Review `git diff --name-only` and confirm the changed files match this task.

## Manual Verification

1. Open:
   `http://localhost:8080/historico-partida.html?server=comunidad-hispana-02&match=comunidad-hispana-02%3A1779310451%3A1779315851%3Afoywarfare`
2. Verify `Ver en Scoreboard` appears.
3. Verify it opens:
   `https://scoreboard.comunidadhll.es:5443/games/1562115`
4. Verify recent cards still do not show the public scoreboard button.

## Commit Message

`fix: persist scoreboard list matches as rcon candidates`

## Outcome

Document validation, candidate upsert decisions, counters added to the JSON
report, and any follow-up task instead of widening this task.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split follow-up work into a new task if the scope grows.
