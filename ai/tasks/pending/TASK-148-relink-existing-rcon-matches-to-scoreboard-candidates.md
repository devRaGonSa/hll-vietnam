---
id: TASK-148
title: Relink existing RCON matches to scoreboard candidates
status: pending
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto Python
roadmap_item: rcon-full-data
priority: high
---

# TASK-148 - Relink existing RCON matches to scoreboard candidates

## Goal

Add a deterministic relink flow that can update or resolve scoreboard URLs for
already-materialized RCON matches after new scoreboard candidates are inserted.

## Background

After manually inserting the Foy `1562115` candidate, the match detail page
showed the expected scoreboard button. Future backfills may insert candidates
after RCON matches already exist, so the system must relink existing RCON
matches with null or missing `match_url` dynamically or via materialization.

Known Foy regression target:

- RCON match key:
  `comunidad-hispana-02:1779310451:1779315851:foywarfare`
- candidate external match id: `1562115`
- expected URL: `https://scoreboard.comunidadhll.es:5443/games/1562115`

## Constraints / DO NOT BREAK

- Do not relax trusted scoreboard URL allowlist.
- Do not link to unsafe origins.
- Do not choose ambiguous candidates silently.
- Do not break old Carentan match:
  `comunidad-hispana-02:1779178461:1779183861:carentanwarfare`
- Do not break Kharkov:
  `comunidad-hispana-02:1779315955:1779319098:kharkovwarfare`
- Do not re-add public scoreboard buttons to recent match cards.
- Do not expose correlation debug text in normal UI.

## Allowed Changes

- Existing RCON materialization, historical read-model, and RCON storage
  modules needed for deterministic candidate relinking.
- `backend/app/scoreboard_candidate_backfill.py` only when needed to trigger
  or document the relink sequence.
- A focused backend relink command module or a narrowly scoped command option
  on existing materialization CLI.
- Focused backend scoreboard correlation tests and fixtures/mocks.
- This task file when it moves through the task workflow.

## Implementation Requirements

1. Inspect current correlation logic:
   - `backend/app/rcon_admin_log_materialization.py`
   - `backend/app/rcon_historical_read_model.py`
   - `backend/app/postgres_rcon_storage.py`
   - `backend/app/scoreboard_candidate_backfill.py`
2. Add or improve a function that matches RCON materialized matches to
   `rcon_scoreboard_match_candidates` using:
   - same server slug / external server id
   - normalized map identity
   - overlapping or close time window
   - score allied/axis where present
   - winner where present
3. Tolerances:
   - allow reasonable time drift between RCON and scoreboard, at least
     +/- 15 minutes, preferably configurable or centralized
   - for matches with null `started_at` / `ended_at` but `closed_at` plus
     `duration_seconds`, derive a correlation window
4. When a best safe candidate is found, make `match_url` available in detail
   payload.
5. Prefer deterministic scoring:
   - exact map match
   - close end time
   - score match
   - same server
   - reject ambiguous ties unless one candidate is clearly better
6. Add a command or option to relink existing matches without needing new
   ingestion:
   - acceptable command module:
     `python -m app.rcon_scoreboard_relink`
   - acceptable alternative: an option inside
     `app.rcon_admin_log_materialization`
7. The relink command must print JSON summary:
   - `matches_scanned`
   - `candidates_scanned`
   - `matches_linked`
   - `matches_skipped_no_candidate`
   - `matches_skipped_ambiguous`
   - `errors`
8. Ensure `scoreboard_candidate_backfill` can optionally trigger relink at the
   end, or document the command sequence.
9. Add regression coverage for the Foy case:
   - RCON match key
     `comunidad-hispana-02:1779310451:1779315851:foywarfare`
   - candidate external match id `1562115`
   - expected `match_url`
     `https://scoreboard.comunidadhll.es:5443/games/1562115`
10. Ensure the detail endpoint returns `match_url` after relink.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/backend-senior.md`
- `backend/app/rcon_admin_log_materialization.py`
- `backend/app/rcon_historical_read_model.py`

## Expected Files to Modify

- Existing RCON correlation/materialization/storage code needed for relinking.
- One relink CLI entry point or one existing CLI option.
- Focused scoreboard correlation regression tests.
- This task file after moving it through the workflow.

Keep correlation diagnostics out of this task except the JSON relink summary
required here. Use TASK-149 for detailed diagnostic output and docs.

## Validation

- `python -m compileall backend/app`
- `python -m unittest discover -s tests -p "*scoreboard*"`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- `docker compose --profile advanced up -d --build backend frontend postgres`
- `docker compose exec backend python -m app.scoreboard_candidate_backfill --server comunidad-hispana-02 --from 2026-05-20T00:00:00Z --to 2026-05-21T23:59:59Z --max-pages 5 --page-size 100`
- Run the new relink command.
- Use `Invoke-WebRequest` for the Foy detail payload and verify `found` is
  true and `match_url` is present.
- Use `Invoke-WebRequest` for the Carentan detail payload and verify the
  existing `match_url` is still present.
- Review `git diff --name-only` and confirm the changed files match this task.

## Manual Verification

1. Foy detail page shows `Ver en Scoreboard`.
2. Scoreboard button opens the `1562115` public URL.
3. Recent match cards still do not show public scoreboard links.
4. No `Detalle no disponible` state appears for the validated detail page.
5. Player filters and external profile links still work.

## Commit Message

`fix: relink rcon matches to scoreboard candidates`

## Outcome

Document correlation scoring choices, time-window derivation, ambiguity
handling, relink command output, validation, and any follow-up task instead of
expanding scope.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split follow-up work into a new task if the scope grows.
