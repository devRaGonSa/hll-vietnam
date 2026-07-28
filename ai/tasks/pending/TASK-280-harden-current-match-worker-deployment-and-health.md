---
id: TASK-280
title: Harden current-match worker deployment and health
status: pending
type: platform
team: Backend Senior
supporting_teams: ["Arquitecto Python", "Arquitecto de Base de Datos"]
roadmap_item: current-match-crcon-parity
priority: high
---

# TASK-280 - Harden current-match worker deployment and health

## Goal

Make live current-match ingestion and snapshot refresh mandatory, independently observable and isolated per trusted server in every supported deployment path.

## Context

The Portainer compose currently places `rcon-live-adminlog-worker` under the optional `advanced` profile and also hardcodes interval/lookback CLI arguments while defining overlapping environment settings. The worker processes targets sequentially, so one slow target may delay the other.

CRCON runs its live log/stat processes as supervised core services. HLL Vietnam must provide equivalent operational guarantees for its current-match pipeline.

## Steps

1. Make the live ingestion/snapshot worker a core service rather than an optional advanced service.
2. Align root/local and Portainer compose files so supported deployments start the same current-match services.
3. Choose one authoritative configuration path for interval, recovery limits and enablement; remove conflicting CLI/environment values.
4. Isolate targets through separate workers or bounded concurrency so a timeout on one server does not delay the other.
5. Add health checks based on persisted heartbeat/snapshot freshness rather than process existence alone.
6. Expose a safe operational health payload containing per-server:
   - last poll attempt/success
   - last source event
   - latest snapshot
   - source age
   - consecutive failures
   - gap/degraded status
7. Add structured logs for lifecycle transitions, recovered events, gaps, snapshot versions, CRCON mismatch and stale thresholds.
8. Define restart policy, startup ordering and database readiness behavior.
9. Update deployment documentation with exact validation and rollback commands.
10. Add configuration/deployment regression checks where feasible.

## Files to Read First

- `AGENTS.md`
- `docs/current-match-adminlog-freshness.md`
- `backend/app/rcon_current_match_worker.py`
- `backend/app/config.py`
- `deploy/portainer/docker-compose.nas.yml`
- root `docker-compose.yml`
- current health/route modules and tests

## Expected Files to Modify

- `ai/tasks/in-progress/TASK-280-harden-current-match-worker-deployment-and-health.md`
- `backend/app/rcon_current_match_worker.py`
- `backend/app/config.py`
- health payload/route modules and focused tests
- `deploy/portainer/docker-compose.nas.yml`
- root `docker-compose.yml`
- `docs/current-match-adminlog-freshness.md`

## Constraints

- Do not start heavy historical materialization more frequently.
- Keep live ingestion independent from historical worker locks and schema initialization.
- Do not expose credentials or raw internal exception details in health responses.
- Do not alter RCON target hosts, ports or passwords.
- Do not reintroduce server #03.
- Preserve existing Postgres volumes and non-destructive deployment behavior.
- Do not bundle frontend feature changes into this task.

## Validation

Before completing the task ensure:

- a normal compose/Portainer deployment starts the live current-match pipeline without an optional profile
- root and Portainer compose behavior is consistent
- one target timeout does not postpone the healthy target beyond its configured cadence
- health becomes stale when heartbeats/snapshots stop advancing
- process-running with stale data is reported unhealthy/degraded
- configuration values have one effective source of truth
- restart and database-unavailable recovery are documented and tested where feasible
- compose config validation and focused backend tests pass
- `git diff --name-only` matches deployment/health scope

## Outcome

Document final service topology, health thresholds, configuration ownership, production verification commands and rollback procedure.

## Change Budget

- Deployment consistency may require more than five files; keep every change current-match-specific.
- Do not refactor unrelated workers.
