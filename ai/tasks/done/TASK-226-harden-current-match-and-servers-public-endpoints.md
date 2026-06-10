---
id: TASK-226
title: Harden current-match and servers public endpoints
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Analista
  - Arquitecto Python
roadmap_item: foundation
priority: high
---

# TASK-226 - Harden current-match and servers public endpoints

## Goal

Harden the public endpoints still affected by RCON/live dependencies after `TASK-225`:

- `/api/current-match/kills`
- `/api/current-match/players`
- `/api/servers`

The objective is not to redesign RCON connectivity. Public HTTP reads must not hang indefinitely or return uncontrolled 500 responses when live RCON/AdminLog data is slow, unavailable or missing.

## Context

`TASK-225` stabilized:

- `/api/stats/players/search`
- `/api/stats/players/{player_id}`
- `/api/historical/matches/detail`

Production validation after `TASK-225` showed those endpoints responding OK without fallback. Remaining audit debt was RCON/live:

- `/api/current-match/kills` timed out or returned 500.
- `/api/current-match/players` timed out for `comunidad-hispana-01`.
- `/api/servers` could spend about 4.3s refreshing RCON from a public GET.

RCON timeout in the current test environment must not be interpreted automatically as wrong configuration. Backend/RCON `127.0.0.1`, hosts, ports and `27001` may be correct in final production and must not be changed in this task.

## Steps

1. Inspect public route and payload chains.
2. Make current-match AdminLog reads public read-only and controlled.
3. Make `/api/servers` return configuration/cache/snapshot data without live refresh in the request.
4. Add focused tests for controlled degradation and no public live refresh.
5. Validate and document the outcome.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/backend-senior.md`
- `backend/app/routes.py`
- `backend/app/payloads.py`
- `backend/app/rcon_admin_log_storage.py`
- `backend/app/rcon_client.py`
- `backend/app/providers/rcon_provider.py`
- `docs/FULL_APPLICATION_REQUEST_AUDIT.md`
- `docs/PERFORMANCE_PUBLIC_QUERY_AUDIT.md`

## Expected Files to Modify

- `backend/app/payloads.py`
- `backend/app/rcon_admin_log_storage.py`
- `backend/tests/test_current_match_payload.py`
- `docs/FULL_APPLICATION_REQUEST_AUDIT.md`
- `docs/PERFORMANCE_PUBLIC_QUERY_AUDIT.md`
- `ai/tasks/done/TASK-226-harden-current-match-and-servers-public-endpoints.md`

## Constraints

- Do not run `ai-platform run`.
- Do not commit or push.
- Do not touch RCON hosts, ports, credentials, environment variables, Docker networking or server connection configuration.
- Do not change `27001`.
- Do not replace backend/RCON `127.0.0.1`; it may be correct in production.
- Do not touch frontend assets, weapon assets, clan assets, SVGs or physical images.
- Do not modify `frontend/assets/img/weapons/` or `frontend/assets/img/clans/`.
- Do not modify `ai/system-metrics.md`.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.

## Validation

Required:

- `python -m compileall backend/app`
- `python -m unittest tests.test_current_match_payload`
- current-match related tests if present
- payload related tests if present
- partial production audit if possible:
  - `python scripts/audit_public_requests.py --base-url https://comunidadhll.devzamode.es --timeout 30 --filter current-match --output tmp/task226_current_match_audit.json`
  - `python scripts/audit_public_requests.py --base-url https://comunidadhll.devzamode.es --timeout 30 --filter servers --output tmp/task226_servers_audit.json`

## Outcome

Implemented:

- `/api/current-match/kills` now calls AdminLog storage in read-only mode with `ensure_storage=False`. If the AdminLog read model is missing, slow or raises, the public payload returns `status: ok`, `items: []`, `confidence: unavailable`, and source metadata with `fallback_used: true` and an `admin-log-*` reason.
- `/api/current-match/players` uses the same read-only/degrade pattern and returns an empty controlled current-match player stats payload instead of propagating storage exceptions as uncontrolled 500s.
- `rcon_admin_log_storage` gained read-only SQLite opening for current-match public reads so missing local storage does not create files or initialize schemas during GET handling.
- `/api/servers` no longer calls `_try_collect_real_time_snapshot()` from the public payload builder. It serves persisted snapshots only, marks stale/fresh state, and returns `refresh_status: "cache-only"`.
- Focused unit tests were added under `backend/tests/test_current_match_payload.py` for kill feed degradation, player stats degradation, and ensuring `/api/servers` does not trigger live refresh in a public GET.

Not changed:

- RCON hosts, ports, credentials, environment variables and server configuration.
- `27001`.
- Frontend JS, because existing `partida-actual.js` catches endpoint errors and clears loading states for kills/players.
- Assets, SVGs and physical images.
- Elo/MMR and Comunidad Hispana #03.

Validation performed:

- `python -m compileall backend/app`: OK.
- `cd backend; python -m unittest tests.test_current_match_payload`: OK, 3 tests from `CurrentMatchPublicEndpointHardeningTests`.
- Related current-match tests: no previous test modules were present in this repo checkout.
- Related payload tests: no previous payload-specific test modules were present in this repo checkout.
- `python scripts/audit_public_requests.py --base-url https://comunidadhll.devzamode.es --timeout 30 --filter current-match --output tmp/task226_current_match_audit.json`: executed against current production deployment. It still shows the pre-deploy failures: kills CH01 timeout 30054.96 ms, players CH01 timeout 30024.09 ms, kills CH02 timeout 30068.39 ms, players CH02 500 in 7497.46 ms. Re-run after deployment is required.
- `python scripts/audit_public_requests.py --base-url https://comunidadhll.devzamode.es --timeout 30 --filter servers --output tmp/task226_servers_audit.json`: executed against current production deployment. `/api/servers` still measured 200 in 4249.71 ms, consistent with pre-deploy live refresh behavior. Re-run after deployment is required.

Risks:

- `/api/current-match` still has direct RCON sample behavior by design and remains separate architectural debt.
- `/api/servers` freshness now depends on an external runner/cache refresh path being active.
- Production latency must be confirmed after deploy because local tests validate behavior, not live infrastructure timing.

## Recovery Note

During recovery, an accidental root-level `tests/` package left by the interrupted session was folded into the existing backend test module and removed from the task scope. The repository convention for this coverage is `backend/tests`.

## Change Budget

The task intentionally exceeds five files only because it includes required tests, documentation and the done-task record. Product/frontend assets and configuration remain untouched.
