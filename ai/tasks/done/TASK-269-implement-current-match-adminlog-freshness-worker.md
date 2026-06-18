---
id: TASK-269
title: Implement current match AdminLog freshness worker
status: done
type: backend
team: Backend Senior
supporting_teams: ["Arquitecto Python"]
roadmap_item: current-match
priority: high
---

# TASK-269 - Implement current match AdminLog freshness worker

## Goal

Add an explicit lightweight worker path that keeps current-match AdminLog data fresh for the public current-match page without changing the heavy historical worker cadence globally.

## Context

TASK-268 confirmed that `/api/current-match/kills` and `/api/current-match/players` do not read live RCON directly. They read persisted `rcon_admin_log_events`, and those rows are refreshed by the historical AdminLog worker path. The checked-in default worker configuration still points to a `600` second historical interval with a `10` minute AdminLog lookback, which explains observed public lag growing from roughly `333s` to `651s` while CRCON live already showed newer kills.

The fix for this task must remain operationally conservative:

- do not change RCON hosts, ports, passwords or trusted target definitions
- do not reduce the heavy historical worker interval globally without separate approval
- do not change frontend polling unless backend freshness proves insufficient
- do not reintroduce server `#03`

## Steps

1. Review the existing historical AdminLog ingestion and persistence path.
2. Implement a dedicated lightweight current-match AdminLog worker or runner using the same storage path.
3. Keep the worker opt-in and deployment-disabled by default.
4. Add focused tests for trusted target selection, failure isolation, persistence reuse and config defaults.
5. Document deployment and validation without changing production deployment automatically.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/backend-senior.md`
- `backend/app/rcon_historical_worker.py`
- `backend/app/rcon_admin_log_ingestion.py`
- `backend/app/rcon_admin_log_storage.py`
- `backend/app/config.py`
- `backend/app/rcon_client.py`
- `backend/app/postgres_rcon_storage.py`
- `docker-compose.yml`

## Expected Files to Modify

- `ai/tasks/in-progress/TASK-269-implement-current-match-adminlog-freshness-worker.md`
- `backend/app/config.py`
- `backend/app/rcon_admin_log_ingestion.py`
- `backend/app/rcon_current_match_worker.py`
- `backend/tests/test_rcon_current_match_worker.py`
- `docs/current-match-adminlog-freshness.md`

## Constraints

- Do not run `ai-platform run`.
- Do not commit or push.
- Do not touch physical assets or `frontend/assets/img/`.
- Do not touch maps, weapons, clans or brands.
- Do not change RCON hosts, RCON ports, `27001` or other server configuration without explicit approval.
- Do not reduce the default historical worker interval globally in this task.
- Do not reactivate Elo/MMR.
- Do not reintroduce `comunidad-hispana-03`.
- Do not touch `ai/system-metrics.md`.
- Do not include `tmp/`, TASK-204 or unrelated pending changes.
- Do not use `git add .`.

## Validation

Before completing the task ensure:

- `python -m compileall backend/app`
- `cd backend; python -m unittest tests.test_current_match_payload`
- `cd backend; python -m unittest tests.test_rcon_current_match_worker`
- `git diff --name-only` matches the expected scope
- documentation reflects that deployment remains opt-in

## Outcome

Implemented a dedicated lightweight worker entry point in `backend/app/rcon_current_match_worker.py`.

Final scope delivered:

- trusted-target filtering limited to `comunidad-hispana-01` and `comunidad-hispana-02`
- reuse of the existing AdminLog fetch/parsing/persistence path
- persistence into the same `rcon_admin_log_events` table
- overlap-safe defaults using existing idempotent dedupe
- explicit opt-in activation only
- deployment documentation without Compose activation changes

Validation completed:

- `python -m compileall backend/app`
- `cd backend; python -m unittest tests.test_current_match_payload`
- `cd backend; python -m unittest tests.test_rcon_current_match_worker`

Operational decisions recorded:

- default interval: `10s`
- default lookback: `180s`
- enabled default: `false`
- `docker-compose.yml` not changed
- deployment activation documented only in docs

## Change Budget

- Prefer fewer than 6 modified files.
- Prefer tightly scoped backend-only changes.
- Split follow-up deployment automation into a separate task if approval is required.
