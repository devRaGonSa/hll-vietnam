---
id: TASK-294
title: Verify real CRCON 12.0.1 contracts
status: review
type: research
team: Backend Senior
supporting_teams:
  - Arquitecto de Base de Datos
  - Arquitecto Python
roadmap_item: crcon-first-migration
priority: high
---

# TASK-294 - Verify real CRCON 12.0.1 contracts

## Goal

Promote only CRCON API and PostgreSQL contracts demonstrated by authorized,
read-only evidence from `UNVERIFIED` to `SUPPORTED`, and mark demonstrated
incompatibilities explicitly without changing any public HLL Vietnam endpoint.

## Context

TASK-293 introduced a dormant CRCON-first adapter foundation using synthetic,
unverified fixtures. This task verifies the deployed version and API contracts
against the two already trusted public community scoreboards. PostgreSQL
contracts may only be promoted when an authorized read-only DSN is available.

## Steps

1. Verify `GET /api/get_version` before using any response.
2. Inspect `GET /api/get_api_documentation` and the seven prioritized GETs.
3. Record only sanitized structure/type evidence and never player data.
4. Verify PostgreSQL metadata only if an authorized read-only connection exists.
5. Update DTOs, fixtures, capability evidence and contract tests conservatively.
6. Preserve every legacy source, worker, default, route and frontend consumer.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `docs/CRCON_FIRST_STATELESS_ARCHITECTURE.md`
- `backend/app/crcon/api.py`
- `backend/app/crcon/dto.py`
- `backend/app/crcon/capabilities.py`

## Expected Files to Modify

- `backend/app/crcon/api.py`
- `backend/app/crcon/dto.py`
- `backend/app/crcon/capabilities.py`
- `backend/app/crcon/models.py`
- `backend/tests/fixtures/crcon_12_0_1/`
- `backend/tests/test_crcon_1201_contracts.py`
- `docs/CRCON_12_0_1_CONTRACT_VERIFICATION.md`
- `ai/tasks/in-progress/TASK-294-verify-real-crcon-1201-contracts.md`

The evidence matrix, seven endpoint fixtures and contract tests justify
exceeding the normal five-file change preference. Product, Compose, deployment,
legacy persistence and frontend files remain out of scope.

## Constraints

- GET and metadata-only database reads exclusively.
- Never persist real names, IDs, IPs, private URLs, credentials or cookies.
- Do not infer Steam/EOS identity from player ID shape or table names.
- Do not claim HLLV support from HLL evidence.
- Do not activate CRCON, change data-source defaults or migrate consumers.
- Do not modify CRCON, RCON, PostgreSQL, Redis, services or deployment.

## Validation

- Contract tests parse sanitized real wrappers and observed null/empty variants.
- TASK-293 tests remain green.
- Python compilation and relevant integration checks pass or are qualified.
- `git diff --name-only` remains within the expected scope plus TASK-293 changes
  already present on the parent branch.

## Outcome

Verified on 2026-08-21 using anonymous read-only GETs against the two trusted
public HLL targets. Both reported `v12.0.1` before contract responses were used.
The official `v12.0.1` tag at commit
`17c5880684cc419b27ef2bcca0dc439dfd623eae` was inspected read-only for bounded
history, empty previous-map behavior and expected schema semantics.

Results:

- all seven prioritized HTTP contracts are `SUPPORTED` for HLL;
- all seven remain `UNVERIFIED` for HLLV;
- wrappers, effective query arguments, empty states, nullability and timestamp
  variants are represented by sanitized fixtures;
- live game stats are explicitly match-scoped while live scoreboard rows are
  connected-session scoped;
- `get_scoreboard_maps` pagination works with empty `player_stats` and
  `get_map_scoreboard` supplies full player/weapon/encounter detail;
- `get_map_history` is modeled as recent Redis history with default maximum 500,
  never as permanent history;
- opaque `player_id` and explicit `platform` are supported for HLL; explicit
  top-level `steam_id`/`eos_id` are unsupported in the seven verified payloads;
- no authorized CRCON PostgreSQL DSN was configured, so every deployed database
  contract and log-server mapping remains `UNVERIFIED`;
- tagged source proves `log_lines.game` is integer, making the previous string
  filter unsupported; log reads now fail closed without explicit text server and
  integer game discriminators;
- no data-source default, route, worker, Compose file, frontend file or legacy
  adapter was migrated or removed.

Validation:

- 105 focused CRCON/current-match/profile tests: passed;
- 58 legacy worker/backfill/admin-log/snapshot tests: passed;
- 37 frontend current-match snapshot tests: passed;
- Python compilation: passed;
- `git diff --check`: passed, with repository LF/CRLF conversion warnings only;
- integration script: historical UI validation passed, then stopped on the
  pre-existing stats validator expectation that the annual ranking form exists;
  this task did not modify the frontend or that validator.

Decision for the combined next phase: **NO-GO**. `/api/servers` has sufficient
HLL-only evidence for a separate reversible switch, but `/api/current-match`
still lacks deployed PostgreSQL/log-discriminator evidence and canonical kill
accuracy. See `docs/CRCON_12_0_1_CONTRACT_VERIFICATION.md`.

## Change Budget

- Prefer contract-only changes and fixtures over product integration.
- Split PostgreSQL verification into a follow-up if no authorized DSN exists.
