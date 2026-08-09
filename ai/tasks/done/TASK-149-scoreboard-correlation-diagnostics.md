---
id: TASK-149
title: Add scoreboard correlation diagnostics
status: done
type: backend
team: Backend Senior
supporting_teams:
  - PM
roadmap_item: rcon-full-data
priority: medium
---

# TASK-149 - Add scoreboard correlation diagnostics

## Goal

Make missing scoreboard links diagnosable without exposing debug clutter in the
normal UI.

## Background

When the Foy match had `match_url` null, investigation required manual
inspection of public pages, candidate tables, and historical tables. Backend
diagnostics should explain whether:

- no candidates exist
- candidates exist but map/time/score mismatch
- candidates were ambiguous
- candidate URL was unsafe
- relink was not run

The known Foy diagnostic target is:

- server: `comunidad-hispana-02`
- RCON match key:
  `comunidad-hispana-02:1779310451:1779315851:foywarfare`
- expected candidate when available: external match id `1562115`

## Constraints / DO NOT BREAK

- Do not add visible debug text to `historico-partida.html`.
- Do not add timeline/source/debug metadata back to normal UI.
- Do not change recent card layout.
- Do not require internet for unit tests.
- Use fixtures/mocks for tests.

## Allowed Changes

- A focused backend scoreboard correlation diagnostic command.
- Existing backend correlation/read helpers only when needed to reuse safe
  candidate selection output.
- Focused backend tests using fixtures or mocks.
- Documentation explaining the missing-scoreboard-button debug sequence.
- This task file when it moves through the task workflow.

## Implementation Requirements

1. Add backend diagnostic capability for a given RCON match:
   - preferred command:
     `python -m app.scoreboard_correlation_diagnostics --server comunidad-hispana-02 --match comunidad-hispana-02:1779310451:1779315851:foywarfare`
   - optional alternative: also expose it inside `storage_diagnostics`, but
     never in normal frontend payloads
2. Diagnostic output must be JSON.
3. Include:
   - `rcon_match_key`
   - `server`
   - `map`
   - `started_at` / `ended_at` / `closed_at` / `duration_seconds`
   - score
   - candidate search window
   - `candidate_count`
   - top candidate summaries:
     - `external_match_id`
     - `started_at`
     - `ended_at`
     - map
     - score
     - `match_url`
     - `correlation_score`
     - `rejection_reason` if rejected
   - `selected_candidate` if any
   - `final_reason`
4. Add a specific diagnostic for the known Foy case.
5. Add docs explaining how to debug a missing scoreboard button:
   - run `scoreboard_candidate_backfill`
   - run relink
   - run `scoreboard_correlation_diagnostics`
   - inspect detail endpoint
6. Keep diagnostics out of normal UI.
7. Do not emit raw sensitive data.
8. Do not emit unsafe URLs.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/backend-senior.md`
- `backend/app/rcon_historical_read_model.py`
- Backend correlation/relink code delivered by TASK-148.

## Expected Files to Modify

- One backend diagnostic command module or the existing diagnostics module.
- Existing safe correlation/read helper files only if necessary.
- Focused backend diagnostic tests using fixtures/mocks.
- One focused documentation file for the debug workflow.
- This task file after moving it through the workflow.

Do not add frontend debug surfaces or widen the normal detail payload for this
task.

## Validation

- `python -m compileall backend/app`
- `python -m app.scoreboard_correlation_diagnostics --server comunidad-hispana-02 --match comunidad-hispana-02:1779310451:1779315851:foywarfare`
- `python -m app.storage_diagnostics`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- `node --check frontend/assets/js/historico-partida.js`
- `node --check frontend/assets/js/historico.js`
- `node --check frontend/assets/js/historico-recent-live.js`
- Review `git diff --name-only` and confirm the changed files match this task.

## Manual Verification

1. Run diagnostics for Foy and verify it explains why `1562115` is selected or
   why no candidate is selected.
2. Run diagnostics for a match without public candidate and verify it explains
   no candidates found.
3. Normal frontend pages do not show diagnostics.

## Commit Message

`chore: add scoreboard correlation diagnostics`

## Outcome

Document diagnostic fields, known Foy output behavior, documentation added,
validation performed, and any follow-up task instead of expanding normal UI
payloads.

- Added `python -m app.scoreboard_correlation_diagnostics` for one
  materialized RCON match. JSON output includes match key, server, map,
  timestamps, duration, score, candidate search window, safe top candidates,
  selected candidate and `final_reason`.
- Candidate summaries expose trusted public `match_url` values only. Untrusted
  URLs are omitted and receive `unsafe-url`; non-scoring candidates report
  `map-or-window-mismatch` where applicable.
- Kept diagnostics out of normal detail and frontend payloads. The command
  reuses the materialized correlation window and safe candidate scoring that
  relink/detail use.
- Added `docs/scoreboard-correlation-debugging.md` with the missing-button
  sequence: candidate backfill, relink scan, diagnostics command and detail
  endpoint check.
- Extended focused Foy coverage so diagnostics select external match id
  `1562115` with the expected Foy candidate summary.
- Validation:
  - `python -m compileall backend/app`
  - `python -m unittest discover -s tests -p "*scoreboard*"` from `backend/`
    passed with existing SQLite `ResourceWarning` output in the scoreboard
    regression file.
  - `python -m app.scoreboard_correlation_diagnostics --server
    comunidad-hispana-02 --match
    comunidad-hispana-02:1779310451:1779315851:foywarfare` from `backend/`
    returned `final_reason: linked` and selected candidate `1562115`.
  - `python -m app.storage_diagnostics`
  - `node --check frontend/assets/js/historico-partida.js`
  - `node --check frontend/assets/js/historico.js`
  - `node --check frontend/assets/js/historico-recent-live.js`
  - `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
    exited successfully after reporting its platform checks. Its later local
    route probe printed a SQLite `database disk image is malformed` traceback
    from `historical_storage`; this task did not alter or repair runtime DB
    files.
- Scope review used `git diff --name-only`; diagnostics changes stay in the
  correlation command/test/doc path and this task file.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split follow-up work into a new task if the scope grows.
