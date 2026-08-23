---
id: TASK-298
title: Collect sufficient CRCON current-match parity evidence
status: done
type: research
team: Backend Senior
supporting_teams: [Analista, Arquitecto Python]
roadmap_item: crcon-migration
priority: high
---

# TASK-298 - Collect sufficient CRCON current-match parity evidence

## Goal

Use the existing bounded observer against both authorized HLL CRCON 12.0.1
targets to collect real, sanitized live-to-final parity evidence without
performing the current-match cutover.

## Context

TASK-297 confirmed normal TLS connectivity after local AVG interception was
disabled. Both targets are runtime reachable, but no complete match ended in
the first five-minute observation, leaving HLL current-match evidence
insufficient.

## Steps

1. Inspect current match timing using only sanitized read-only CRCON metadata.
2. Run one or more bounded sessions with the existing TASK-296 observer.
3. Retain only sanitized diagnostic JSON under `tmp/parity-evidence/`.
4. Aggregate completed-match results across runs only if existing output is
   sufficient; change code solely for a proven collection defect.
5. Apply server-specific and aggregate GO criteria and document the evidence.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/backend-senior.md`
- `backend/app/observe_current_match_parity.py`
- `backend/app/current_match_shadow.py`

## Expected Files to Modify

- `backend/app/observe_current_match_parity.py`
- `backend/tests/test_current_match_parity_observer.py`
- `docs/CRCON_CURRENT_MATCH_PARITY_VALIDATION.md`
- `ai/tasks/review/TASK-298-collect-sufficient-crcon-current-match-parity-evidence.md`

## Constraints

- Observation only: no cutover, deploy, SSH or remote writes.
- Do not modify TLS behavior, add CA bundles or weaken certificate validation.
- Reuse the existing observer and CRCON live/final evidence hierarchy.
- Do not persist raw responses, player names, real IDs or credentials.
- Diagnostic JSON must not become gameplay/application/historical storage.
- Stale legacy samples remain excluded from STAT conclusions.

## Validation

- Existing TASK-293–297 focused tests pass.
- `python -m compileall -q app tests` passes.
- `git diff --check` passes.
- Changed files match the observation/documentation scope.

## Outcome

Collection was stopped by explicit product-owner direction on 2026-08-23.
The extended real-match parity run is no longer a prerequisite for local
current-match development. No additional complete matches will be awaited and
the parity observer remains unchanged and available for later validation.

One 2,400-second bounded observer run covered both authorized targets and wrote
only sanitized diagnostic JSON under `tmp/parity-evidence/`. It completed 230
polls per target (460 aggregate), with 100% snapshot availability, zero
unavailable polls and seven partial `CrconApiError` observations that never
became false match endings.

Both targets produced a real map transition. Target 1 converged to `NEXT_MATCH`
in 10.379 seconds, but its prior old/empty identity had no matching final map and
was not counted. Target 2 converged in 10.361 seconds and associated one Utah
Beach warfare final scoreboard (3:2) using server, layer and start time. The
final comparison matched 21 players, with no only-live or only-final players.

The real run exposed a collection defect: the shared production snapshot
intentionally emits `None` for live kills/deaths/teamkills when database combat
aggregation is disabled even though typed `get_live_game_stats` supplies those
values. That prevented K/D/TK comparison for the captured match. The observer
now overlays only the three typed API counters from the exact live response in
its diagnostic snapshot. Production mapping, TLS and database behavior remain
unchanged. A post-fix real probe confirmed K/D/TK presence for every live player
on both targets.

The captured final match produced 21/21 exact comparisons for each of combat,
offense, defense and support, zero player-set differences and no stat deltas.
Kills, deaths and teamkills had zero valid comparisons, so zero expected or
unexplained deltas cannot support an accuracy conclusion. No systematic live
kill undercount can yet be accepted or rejected. Legacy remained temporally
invalid and was excluded.

Both new matches had more than an hour remaining after the run, so the bounded
session could not provide the two additional valid completed matches. Final
statuses:

- `SERVER_LIST_HLL_CONTRACT = GO`
- `SERVER_LIST_HLL_RUNTIME = GO`
- `CURRENT_MATCH_HLL = INSUFFICIENT_EVIDENCE`
- `CURRENT_MATCH_HLLV = UNVERIFIED`

Validation:

- focused TASK-293–298 suite: 137 tests passed;
- `python -m compileall -q app tests`: passed;
- `git diff --check`: passed with only pre-existing line-ending warnings;
- no frontend or deploy files changed;
- no cutover, deploy, commit or remote mutation occurred.

## Change Budget

Prefer documentation-only changes. Any implementation change requires a real
observed collection defect and focused regression coverage.
