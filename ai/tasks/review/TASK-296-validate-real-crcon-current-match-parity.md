---
id: TASK-296
title: Validate real CRCON current-match parity
status: review
type: backend
team: Backend Senior
supporting_teams: [Analista, Arquitecto Python]
roadmap_item: crcon-migration
priority: high
---

# TASK-296 - Validate real CRCON current-match parity

## Goal

Create and exercise a bounded local observer that measures HLL legacy live data, CRCON live data, and CRCON final scoreboards without performing the current-match cutover.

## Context

TASK-295 left HLL current-match `SHADOW READY`. Promotion requires complete-match evidence rather than endpoint availability or upstream issue assumptions. HLLV remains an independent unverified target class.

## Steps

1. Preserve the TASK-293–295 stack and existing selectors.
2. Add a reusable CLI observer with bounded polling and sanitized optional output.
3. Model match lifecycle, timing alignment, stabilized player churn, stat convergence, transitions, and live-to-final reconciliation.
4. Test the observer and keep TASK-293–295 checks green.
5. Run a short authorized read-only observation when targets are reachable; do not wait indefinitely.
6. Document evidence and emit HLL/HLLV decisions without changing defaults.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/backend-senior.md`
- `backend/app/current_match.py`
- `backend/app/current_match_shadow.py`

## Expected Files to Modify

- `backend/app/current_match_shadow.py`
- `backend/app/observe_current_match_parity.py`
- `backend/tests/test_current_match_parity_observer.py`
- `docs/CRCON_CURRENT_MATCH_PARITY_VALIDATION.md`
- `ai/tasks/review/TASK-296-validate-real-crcon-current-match-parity.md`

## Constraints

- No deployment, SSH, external writes, mutable RCON commands, production environment changes, or frontend default changes.
- CRCON access is limited to authorized GET endpoints; no PostgreSQL or Redis access.
- No gameplay database, reusable gameplay snapshots, background worker, or raw response archive.
- Optional output must be fully sanitized and contain no player names or raw player IDs.
- Legacy is a regression comparator, not the truth oracle; final CRCON scoreboard is highest evidence.
- Bounded execution only; zero completed matches must produce `INSUFFICIENT EVIDENCE`.

## Validation

- Observer lifecycle and parity tests pass.
- TASK-293–295 focused suites remain green.
- Python compilation and `git diff --check` pass.
- Existing integration debt is documented without expanding scope.
- No frontend/deploy/Compose files change.

## Outcome

- Added `python -m app.observe_current_match_parity` with repeatable `--server`, conservative polling, bounded duration, synchronization/transition tolerances, stabilization window, and optional sanitized JSON output.
- The observer resolves existing `ServerTarget` mechanisms, builds API-only current-match services, and uses only the four authorized CRCON GET endpoints. CRCON PostgreSQL access is explicitly impossible.
- Added lifecycle handling for pre-match, running, transition, ended, next match, and transport outage. Player count never creates match identity and outages never create false match ends.
- Added per-target and aggregate match/player/stat metrics, per-execution salted aliases, transient/persistent player churn, timing exclusion, eventual/systematic convergence, transition duration, and close-live/final reconciliation.
- Enhanced the final verifier to retain last-live observations per match and classify final deltas as expected-window or unexplained using poll distance and later encounter evidence when available.
- Real bounded run: both authorized HLL targets, three polls each, zero synchronized polls, zero completed matches, zero stat/final comparisons. Both public/live API calls were unavailable; a read-only version probe identified `SSLCertVerificationError` on both certificate chains. No insecure TLS bypass was added.
- Legacy returned old persisted fallback timestamps, so the observer correctly excluded them from STAT parity.
- Focused TASK-293–296 validation: 136 tests passed; Python compilation, `git diff --check`, and historical UI regression passed.
- The integration script still stops at the pre-existing annual-ranking-form validator after the UI regression passes. No unrelated repair was attempted.
- Decisions: HLL server list GO; HLL current match INSUFFICIENT EVIDENCE; HLLV current match UNVERIFIED.
- TASK-297 must restore standards-compliant TLS reachability or supply an authorized CA bundle, then observe at least three complete HLL matches across both targets. It must not cut over until the encoded thresholds pass.

## Change Budget

The observer, diagnostics, tests, evidence report, and task record form one explicit validation scope. No unrelated application feature is included.
