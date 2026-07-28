---
id: TASK-281
title: Validate current-match CRCON parity and production rollout
status: pending
type: platform
team: Analista
supporting_teams: ["Backend Senior", "Frontend Senior", "Arquitecto de Base de Datos", "Arquitecto Python"]
roadmap_item: current-match-crcon-parity
priority: high
---

# TASK-281 - Validate current-match CRCON parity and production rollout

## Goal

Prove that the rebuilt current-match pipeline no longer loses or mixes events, matches CRCON within documented tolerances and can be rolled out safely to both trusted servers.

## Context

The feature is complete only when match transitions, live totals, recovery and degraded states work under real operational conditions. Unit tests alone cannot prove parity with the running CRCON instances or correctness during worker/network restarts.

This task is the release gate for TASK-272 through TASK-280.

## Steps

1. Review outcomes and validation evidence for TASK-272 through TASK-280.
2. Build an automated integration scenario suite covering:
   - normal match start and first kill
   - multiple kills in the same second
   - explicit and inferred teamkills
   - player connect/disconnect/team switch
   - match end and between-matches state
   - new match with no kills yet
   - consecutive identical maps
   - duplicate AdminLog delivery
   - missed boundary with CRCON reconciliation
   - worker restart inside recovery window
   - outage beyond recovery window with partial/gap status
   - CRCON timeout/malformed response
   - one server failing while the other remains healthy
3. Add production-safe comparison tooling that samples HLL Vietnam and trusted CRCON data without storing credentials or excessive personal data.
4. Define tolerances for event arrival and aggregate parity, including expected CRCON polling delay.
5. Run a shadow-validation period where the new snapshot is compared against existing public output before switching the frontend.
6. Verify at least several real map transitions on both servers.
7. Record discrepancies by category: parser loss, ingestion gap, identity mismatch, CRCON lag, local projection bug or upstream inconsistency.
8. Define go/no-go criteria, rollback procedure and database compatibility checks.
9. Update current-match architecture, operations and frontend/backend contract documentation.
10. Move obsolete fallback behavior/documentation to an explicit deprecation note after successful rollout.

## Files to Read First

- `AGENTS.md`
- `docs/current-match-crcon-parity-contract.md`
- `docs/current-match-adminlog-freshness.md`
- implementation outcomes for TASK-273 through TASK-280
- `scripts/run-integration-tests.ps1` if configured
- current-match backend/frontend test suites

## Expected Files to Modify

- `ai/tasks/in-progress/TASK-281-validate-current-match-crcon-parity-and-rollout.md`
- focused current-match integration test scripts/fixtures
- safe CRCON comparison/audit script under `scripts/`
- `docs/current-match-adminlog-freshness.md`
- `docs/current-match-crcon-parity-contract.md`
- `docs/frontend-backend-contract.md`
- optional rollout checklist under `docs/`

## Constraints

- Do not mutate CRCON, RCON or live match state during validation.
- Do not store credentials, raw private headers or unnecessary player-identifying data.
- Comparison tooling must use only trusted configured servers.
- Do not declare parity from a single quiet snapshot.
- Do not hide mismatches by widening tolerances without technical justification.
- Do not activate unrelated Elo/MMR, ranking, historical or server #03 functionality.
- Keep rollback possible without deleting captured AdminLog or lifecycle audit data.

## Validation

Before completing the task ensure:

- all automated current-match tests pass
- both servers complete real start/live/end/new-start transitions without old data leakage
- a new match with zero kills displays empty combat data immediately
- aggregate kills/deaths/teamkills match CRCON within the documented refresh tolerance
- no known recoverable events are lost during a controlled worker restart
- unrecoverable gaps are visible as partial/degraded rather than exact
- one server failure does not stale the other
- frontend and all compatibility endpoints expose one match identity/version
- rollback commands and production verification queries are documented
- `git diff --name-only` matches validation/documentation scope

## Outcome

Record final parity evidence, measured latencies, remaining upstream limitations, rollout decision and any narrowly scoped follow-up tasks.

## Change Budget

- This is a validation/release task, not an opportunity for broad refactoring.
- Any implementation defect discovered should be fixed in the owning prior task or a new focused follow-up.
