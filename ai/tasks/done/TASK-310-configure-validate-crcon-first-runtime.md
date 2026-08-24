---
id: TASK-310
title: Configure and validate the real CRCON-first runtime read paths
status: done
type: validation
team: Backend Senior
supporting_teams:
  - Arquitecto Python
  - Arquitecto de Base de Datos
roadmap_item: CRCON-first migration
priority: high
---

# TASK-310 - Configure and validate CRCON-first runtime

## Goal

Audit canonical local configuration and validate the already implemented real
CRCON REST, authenticated player-history, Log Stream and SELECT-only PostgreSQL
read paths wherever credentials are legitimately available.

## Constraints

- Do not discover or print secrets outside canonical project configuration.
- Do not modify CRCON, deployment, databases, parity observer, writers or
  stored data.
- Do not fabricate credentials or broaden permissions.
- Keep runtime probes bounded and evidence sanitized.

## Validation

- Classify canonical runtime configuration without exposing values.
- Run real capability probes only for configured valid capabilities.
- Exercise local routes with explicit CRCON selectors where possible.
- Document exact operator requirements for unavailable capabilities.
- Update the legacy dependency ledger and runtime status matrix.

## Outcome

- Canonical process/project configuration audit found `HLL_SERVER_TARGETS`,
  `HLL_CRCON_CURRENT_MATCH_BINDINGS`, `HLL_CRCON_LOG_STREAM_TOKENS` and
  `HLL_CRCON_DATABASE_URL` all `NOT_CONFIGURED`; no value was printed and no
  alternate secret location was searched.
- No real REST, authenticated player-history, WebSocket, PostgreSQL, schema,
  aggregate, `EXPLAIN` or configured end-to-end route probe was eligible.
- Added an exact placeholder-only operator checklist and a least-privilege
  PostgreSQL role template covering the six tables currently read by
  `PostgresCrconRepository`. No credential, deployment or product code changed.
- Updated the legacy writer matrix: runtime replacements and active-reader
  counts remain `UNVERIFIED`; no writer is safe to stop in the next task.
- Final readiness is `LEGACY_WRITER_DISABLE_READINESS = NOT_READY` solely
  because authorized runtime configuration and zero-reader proof are absent.
- Forty-four focused configuration, selector-isolation, read-only, REST,
  Log Stream, history, player-search, aggregate and current-match tests pass.
  The no-configuration local route smoke remained fail-closed and did not
  establish real runtime availability.
