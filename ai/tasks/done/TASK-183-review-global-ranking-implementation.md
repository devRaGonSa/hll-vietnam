---
id: TASK-183-review-global-ranking-implementation
title: Review global ranking implementation
status: done
type: research
team: Analista
supporting_teams:
  - PM
  - Backend Senior
  - Frontend Senior
  - Arquitecto Python
  - Experto en interfaz
roadmap_item: foundation
priority: high
---

# TASK-183-review-global-ranking-implementation - Review global ranking implementation

## Goal

Review the current technical implementation of the new `Ranking global` section after TASK-180, TASK-181 and TASK-182, and document whether the delivered backend/frontend behavior matches the approved contract without implementing new functionality.

## Context

`Ranking` was introduced as a dedicated public leaderboard flow separate from `Stats`. Before any follow-up changes, HLL Vietnam needs one focused technical review task that confirms the real route contract, the actual data sources, the frontend failure handling, the validation coverage and the navigation impact on the landing.

Preserve the current product identity: Spanish-speaking HLL Vietnam community, military/Vietnam/tactical/sober visual direction and controlled repository evolution.

## Steps

1. Read the listed files first.
2. Compare `docs/global-ranking-page-plan.md` against the implemented backend/frontend behavior.
3. Verify the real global ranking endpoint contract:
   - exact route
   - supported parameters
   - supported timeframes
   - supported metric
   - normalized limit behavior
4. Confirm weekly and monthly ranking reads use the RCON materialized read model.
5. Confirm annual ranking reads use persisted annual snapshots and do not recalculate on each public request.
6. Verify Elo/MMR is not required by this flow and that Comunidad Hispana #03 was not reintroduced.
7. Review frontend handling for:
   - backend offline
   - no data
   - annual snapshot missing
   - unsupported metric
   - unsupported timeframe
   - invalid limit
8. Review whether `frontend/assets/js/ranking.js` duplicates logic from `frontend/assets/js/stats.js` in a risky way or only reuses patterns safely.
9. Review whether `scripts/run-stats-validation.ps1` covers `Ranking global` sufficiently or whether a future dedicated validation task is justified.
10. Confirm navigation from `frontend/index.html` to `frontend/ranking.html` does not break the landing flow.
11. Document findings, validation executed, open risks and any follow-up tasks instead of expanding scope.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `docs/global-ranking-page-plan.md`
- `frontend/ranking.html`
- `frontend/assets/js/ranking.js`
- `backend/app/routes.py`
- `backend/app/payloads.py`
- `scripts/run-stats-validation.ps1`

## Expected Files to Modify

- `ai/tasks/pending/TASK-183-review-global-ranking-implementation.md`

## Constraints

- Create findings only; do not implement fixes in this task.
- Do not execute product changes beyond the scoped technical review.
- Do not modify backend files.
- Do not modify frontend files.
- Do not modify docs outside the task outcome if a follow-up is needed.
- Do not create new features.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Keep the review aligned with the existing RCON-first architecture and the approved separation between `Stats` and `Ranking`.

## Validation

Before completing the task ensure:

- the implementation was reviewed against `docs/global-ranking-page-plan.md`
- the real route contract for `GET /api/ranking` was documented from code, not assumed
- weekly/monthly vs annual source behavior was verified from implementation files
- frontend error-state handling was reviewed from `ranking.html` and `ranking.js`
- validation-script coverage was reviewed from `scripts/run-stats-validation.ps1`
- landing navigation impact was checked from `frontend/index.html`
- no unrelated files were modified
- `git diff --name-only` matches the expected scope
- if no integration tests apply beyond the existing validation script, that limitation is documented explicitly

## Outcome

Review result:

- The real reviewed endpoint is `GET /api/ranking`.
- Supported parameters confirmed from `backend/app/routes.py`:
  - `timeframe`: optional, defaults to `weekly`; allowed values `weekly`, `monthly`, `annual`
  - `server_id`: optional, defaults effectively to `all`; accepted values for Ranking are `all`, `all-servers`, `comunidad-hispana-01`, `comunidad-hispana-02`
  - `metric`: optional, defaults to `kills`; V1 only supports `kills`
  - `limit`: optional, defaults to `20`; validated as `1..100`
  - `year`: required only when `timeframe=annual`
- Weekly and monthly Ranking reads are confirmed to use the RCON materialized read model through `list_rcon_materialized_leaderboard(...)` in `backend/app/rcon_historical_leaderboards.py`.
- Annual Ranking is confirmed to use persisted annual snapshots through `get_annual_ranking_snapshot(...)` in `backend/app/rcon_annual_rankings.py`, and the public request path does not call `generate_annual_ranking_snapshot(...)`.
- No Elo/MMR dependency was found in the Ranking flow. Elo/MMR routes still exist elsewhere, but `GET /api/ranking`, `build_global_ranking_payload(...)` and `frontend/assets/js/ranking.js` do not rely on them.
- Comunidad Hispana #03 was not reintroduced:
  - frontend server selector exposes only `all`, `comunidad-hispana-01`, `comunidad-hispana-02`
  - backend Ranking validation rejects unsupported server ids
- Navigation added in `frontend/index.html` does not break the landing in the reviewed static flow; `index.html`, `ranking.html`, `stats.html` and `assets/js/ranking.js` were served locally with HTTP `200`.

Consistency against `docs/global-ranking-page-plan.md`:

- The implementation matches the main contract direction:
  - dedicated `GET /api/ranking`
  - weekly/monthly from RCON materialized leaderboard reads
  - annual from snapshots
  - V1 metric limited to `kills`
  - no Elo/MMR
  - no Comunidad Hispana #03
  - frontend handles offline, empty, annual missing and controlled errors
- The route contract is slightly broader than the documented plan because backend also accepts `server_id=all-servers` as an alias.
- The frontend implementation is slightly narrower than the broadest possible contract because the UI only exposes limit options `10`, `20` and `30`, even though backend accepts `1..100`.

Frontend state review:

- `backend offline`: explicitly handled in `refreshBackendHealth()` and in guarded calls when backend state is offline.
- `sin datos`: explicitly handled in `renderRanking(...)` when `items=[]`.
- `annual snapshot missing`: explicitly handled when `timeframe=annual` and `snapshot_status="missing"`.
- `metric no soportada`: explicitly handled on HTTP `400` with `metric` in the error message.
- `timeframe no soportado`: explicitly handled on HTTP `400` with `timeframe` in the error message.
- `limit invalido`: handled only through the generic controlled-error branch; there is no dedicated invalid-limit message in `ranking.js`.

`ranking.js` versus `stats.js`:

- There is duplication of helper patterns such as backend health checks, state setters, JSON-safe parsing, formatting and HTML escaping.
- The duplication is not currently dangerous because the flows are separated and the duplicated logic is simple.
- It is still a maintainability risk if future endpoint/error handling changes need to stay synchronized across both files.

Validation coverage review:

- `scripts/run-stats-validation.ps1` already covers the global Ranking route contract well enough for the current backend scope:
  - weekly/monthly/annual happy paths
  - unsupported metric
  - unsupported timeframe
  - invalid high limit
  - annual missing year
- It does not directly validate frontend rendering states for `ranking.html`.
- A future dedicated Ranking frontend regression task is still advisable if UI-state coverage becomes important.

Risks detected:

- `ranking.js` does not provide a dedicated user-facing message for invalid `limit`; it falls back to the generic controlled-error state.
- Shared helper logic between `ranking.js` and `stats.js` may drift over time because it is duplicated rather than centralized.
- Live backend HTTP verification at `http://127.0.0.1:8000` was not available during validation, so successful HTTP checks for Ranking were confirmed through local route-contract execution instead of a running backend.

Validation executed:

- `node --check frontend/assets/js/ranking.js`
- `node --check frontend/assets/js/stats.js`
- `powershell -ExecutionPolicy Bypass -File scripts/run-stats-validation.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- Local static serving with `python -m http.server`
- HTTP `200` confirmed for:
  - `ranking.html`
  - `assets/js/ranking.js`
  - `index.html`
  - `stats.html`

Change scope:

- No backend or frontend code changes were needed.
- This task completed as review/documentation only.

Recommended follow-up tasks:

- Add a dedicated Ranking frontend regression validation task covering offline, empty, annual-missing and controlled-error UI states.
- Evaluate whether shared frontend helpers between `stats.js` and `ranking.js` should be consolidated if more stateful pages are added.

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
