---
id: TASK-177-harden-annual-ranking-snapshot-operations
title: Harden annual ranking snapshot operations
status: pending
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto de Base de Datos
  - PM
roadmap_item: foundation
priority: medium
---

# TASK-177-harden-annual-ranking-snapshot-operations - Harden annual ranking snapshot operations

## Goal

Improve annual ranking snapshot reliability for production use without recalculating on public requests or changing visible frontend behavior.

## Context

The annual snapshot flow is implemented and documented, but edge cases around missing data, empty years, unsupported years/metrics, and limit normalization should be hardened with small, verifiable backend improvements.

## Steps

1. Read the listed files first.
2. Review generation and read flow for annual ranking snapshots.
3. Apply small validation and response consistency improvements in backend code.
4. Ensure snapshot behavior remains stable for ready/empty/missing and unsupported metric states.
5. Document any follow-up work that should remain a separate task instead of broadening this one.

## Files to Read First

- AGENTS.md
- ai/repo-context.md
- ai/architecture-index.md
- docs/stats-section-functional-plan.md
- docs/annual-ranking-snapshot-runbook.md
- backend/app/routes.py
- backend/app/rcon_annual_rankings.py
- backend/app/rcon_historical_leaderboards.py
- ai/tasks/done/TASK-171-validate-stats-section-with-backend-data.md
- ai/tasks/done/TASK-173-add-annual-ranking-snapshot-runbook.md

## Expected Files to Modify

- backend/app/rcon_annual_rankings.py
- backend/app/routes.py only if endpoint mapping/validation requires changes
- docs/annual-ranking-snapshot-runbook.md only if documented operations change
- ai/tasks/done/TASK-177-harden-annual-ranking-snapshot-operations.md

## Constraints

- No frontend modifications unless a strict critical backend-related bug requires it (and document the reason).
- No new architecture.
- No major migrations.
- Do not re-enable Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Do not use public scoreboard as primary source.
- Do not recalculate annual ranking in each public request.
- Keep changes small and independently verifiable.

## Validation

- Run `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`.
- Test annual ranking endpoint for:
  - current year with `metric=kills`
  - past year with no data
  - future year missing snapshot
  - unsupported metric
  - low limit, e.g. `3`
  - high limit, verifying normalization if applicable
- Run `git diff --name-only` and verify scoped files only.

## Outcome

Document applied hardening, validated responses, known limits, and whether a future task is needed for scheduled/hardening automation.

