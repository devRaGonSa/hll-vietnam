---
id: TASK-183-review-global-ranking-implementation
title: Review global ranking implementation
status: pending
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

Document:

- whether implementation matches the documented contract
- exact mismatches, if any
- whether the route contract is narrower or broader than the plan
- whether annual ranking is safely snapshot-backed
- whether any frontend failure state is missing or only partially handled
- whether validation coverage is sufficient for now
- any follow-up tasks required, keeping them small and technical

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
