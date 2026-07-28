---
id: TASK-274
title: Normalize AdminLog combat and match-boundary events
status: pending
type: backend
team: Backend Senior
supporting_teams: ["Arquitecto Python"]
roadmap_item: current-match-crcon-parity
priority: high
---

# TASK-274 - Normalize AdminLog combat and match-boundary events

## Goal

Make AdminLog parsing reliable enough to support CRCON-parity lifecycle and combat statistics without silently dropping valid match, kill or teamkill events.

## Context

The current parser recognizes one `KILL:` format and infers teamkills by comparing team values. It does not model `TEAM KILL` as an explicit event and uses narrow regular expressions for `MATCH START` and `MATCH ENDED`.

Lost or misclassified boundaries cause whole matches to be reconstructed incorrectly. Lost teamkills cause player totals to diverge from CRCON.

## Steps

1. Build sanitized fixtures from real AdminLog variants already observed in production and CRCON-compatible logs.
2. Extend the normalized event model to distinguish combat semantics explicitly, including `is_teamkill` and the original event label.
3. Parse both `KILL:` and `TEAM KILL:` variants while preserving killer, victim, teams, IDs and weapon.
4. Harden `MATCH START` and `MATCH ENDED` parsing for known quoting, spacing, map/layer and mode variants without accepting arbitrary malformed text.
5. Preserve unknown events losslessly for diagnostics.
6. Add parser-version or parser-quality metadata when useful for future remediation.
7. Add regression tests covering:
   - normal kill
   - explicit teamkill
   - inferred same-team kill
   - missing/None team
   - Steam and non-Steam IDs
   - special characters in names/weapons
   - duplicate boundary lines
   - malformed near-matches that must remain unknown
8. Update downstream serialization tests to consume the normalized teamkill field instead of re-deriving it inconsistently.

## Files to Read First

- `AGENTS.md`
- `docs/current-match-crcon-parity-contract.md`
- `backend/app/rcon_admin_log_parser.py`
- `backend/app/rcon_admin_log_storage.py`
- `backend/tests/test_rcon_admin_log_parser.py`
- `backend/tests/test_rcon_admin_log_storage.py`

## Expected Files to Modify

- `ai/tasks/in-progress/TASK-274-normalize-adminlog-combat-and-boundary-events.md`
- `backend/app/rcon_admin_log_parser.py`
- `backend/app/rcon_admin_log_storage.py`
- `backend/tests/test_rcon_admin_log_parser.py`
- `backend/tests/test_rcon_admin_log_storage.py`
- optional sanitized fixtures under `backend/tests/fixtures/adminlog/`

## Constraints

- Do not fabricate unsupported AdminLog formats.
- Preserve raw messages and canonical deduplication behavior.
- Do not change public frontend layout or polling.
- Do not convert unknown events into kills or boundaries without strong evidence.
- Keep parser behavior deterministic and independently testable.
- Do not expose player/private data beyond existing repository test conventions.

## Validation

Before completing the task ensure:

- explicit `TEAM KILL` lines are not classified as unknown
- downstream kill/player totals use normalized `is_teamkill`
- existing supported log formats remain compatible
- malformed lines remain losslessly available as unknown events
- all parser and storage regression tests pass
- `python -m compileall backend/app` passes
- `git diff --name-only` matches the parser/test scope

## Outcome

Document supported AdminLog formats, rejected variants and any remaining source ambiguity that requires production fixture collection.

## Change Budget

- Keep this task parser-focused.
- Do not add lifecycle persistence, CRCON calls or snapshot materialization here.
