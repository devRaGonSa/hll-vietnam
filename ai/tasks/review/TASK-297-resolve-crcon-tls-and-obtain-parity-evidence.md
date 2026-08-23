---
id: TASK-297
title: Resolve CRCON TLS trust and obtain parity evidence
status: review
type: backend
team: Backend Senior
supporting_teams: [Analista, Arquitecto Python]
roadmap_item: crcon-migration
priority: high
---

# TASK-297 - Resolve CRCON TLS trust and obtain parity evidence

## Goal

Diagnose the TLS trust failure for both authorized HLL CRCON targets without weakening verification, and run parity observation only if secure HTTPS becomes available.

## Context

TASK-296 built the bounded observer but both targets failed Python TLS verification. The server-list implementation remains contract-ready while runtime status depends on secure connectivity.

## Steps

1. Reproduce with Python, normal curl, and certificate-chain inspection with SNI.
2. Classify the evidence and assign the remediation boundary.
3. Recheck both targets after the authorized local interceptor is disabled.
4. Run secure read-only probes and the bounded observer only after TLS succeeds.
5. Record sanitized parity evidence without changing application TLS behavior.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/backend-senior.md`
- `backend/app/crcon/api.py`
- `docs/CRCON_CURRENT_MATCH_PARITY_VALIDATION.md`

## Expected Files to Modify

- `docs/CRCON_CURRENT_MATCH_PARITY_VALIDATION.md`
- `ai/tasks/review/TASK-297-resolve-crcon-tls-and-obtain-parity-evidence.md`

## Constraints

- Never disable certificate or hostname verification and never add insecure flags.
- No remote certificate, proxy, CRCON, RCON, database, deploy, frontend-default, or cutover changes.
- Do not commit certificates, private origins, raw responses, credentials, or player data.
- An explicit CA bundle is allowed only if evidence proves an intentional private CA requirement; invalid configuration must fail closed.
- Stop live parity observation when secure TLS cannot be established.

## Validation

- Standard Python, typed-client and normal `curl` TLS checks pass.
- TASK-293–297 focused tests remain green.
- Python compile and `git diff --check` pass.
- No frontend/deploy files change.

## Outcome

The first diagnostic pass proved that AVG Web/Mail Shield was intercepting both
authorized targets. After AVG was temporarily disabled locally, standard Python
TLS, `urllib`, the real `CrconApiClient` transport and normal `curl` all
succeeded for both targets. Each target presented a Let's Encrypt / YE1 leaf,
negotiated TLS 1.3, passed hostname/SAN verification and returned exactly
`v12.0.1`. The problem was environmental local interception.

No TLS-related application code, CA bundle or verification option is required
or retained. Certificate and hostname validation remain at their standard
fail-closed defaults.

The existing observer then ran for 300 seconds over both HLL targets. It
completed 29 polls per target (58 aggregate), with CRCON available in every poll
and no transport errors. Both targets remained in `MATCH_RUNNING`; no match
completed and no transition occurred. Therefore no final map scoreboard, map or
mode coverage, comparable live/final player stats, kill accuracy percentage or
final-window classification was available. The zero unexplained-delta count
represents no comparisons, not proof of parity.

Legacy snapshots were millions of seconds stale. All 58 legacy comparisons were
timing mismatches and correctly excluded from gameplay/stat conclusions.

Final statuses:

- `SERVER_LIST_HLL_CONTRACT = GO`
- `SERVER_LIST_HLL_RUNTIME = GO`
- `CURRENT_MATCH_HLL = INSUFFICIENT_EVIDENCE`
- `CURRENT_MATCH_HLLV = UNVERIFIED`

Validation:

- focused TASK-293–297 suite: 136 tests passed;
- `python -m compileall -q app tests`: passed;
- `git diff --check`: passed (only pre-existing line-ending warnings);
- no frontend or deploy files changed;
- no unrelated integration failure was addressed.

## Change Budget

Documentation-only outcome. Do not retain an application workaround for the
environmental interceptor defect.
