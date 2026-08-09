---
id: TASK-225
title: Stabilize critical public API endpoints
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Analista
  - Arquitecto Python
  - Arquitecto de Base de Datos
roadmap_item: foundation
priority: high
---

# TASK-225 - Stabilize critical public API endpoints

## Goal

Apply focused functional fixes from `docs/FULL_APPLICATION_REQUEST_AUDIT.md` to stabilize the highest-priority public API endpoints that timed out or paid storage initialization/fallback cost during public reads.

## Context

`TASK-224` found critical public request issues:

- `/api/stats/players/search` timed out at 30s.
- `/api/stats/players/{player_id}` weekly/monthly timed out at 30s.
- `/api/current-match/kills` timed out or returned 500.
- `/api/current-match/players` timed out for `comunidad-hispana-01`.
- `/api/servers` could spend about 4.3s refreshing RCON from a public GET.
- `/api/historical/matches/detail` responded OK in the production probe but still had a static `initialize_*` public read path.

This task prioritizes safe fixes that do not change RCON connection configuration, server hosts, ports, credentials, Docker networking or frontend assets.

## Steps

1. Inspect the listed files first.
2. Implement Phase 1 only unless the remaining phases are clearly small and safe.
3. Add focused tests proving public read paths do not initialize storage or fall back to heavy runtime scans.
4. Validate backend compile/tests.
5. Document implemented and deferred phases.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `docs/FULL_APPLICATION_REQUEST_AUDIT.md`
- `backend/app/rcon_historical_player_stats.py`
- `backend/app/rcon_admin_log_materialization.py`
- `backend/app/rcon_historical_read_model.py`
- `backend/app/payloads.py`
- `backend/tests/test_rcon_materialization_pipeline.py`

## Expected Files to Modify

- `backend/app/rcon_historical_player_stats.py`
- `backend/app/rcon_admin_log_materialization.py`
- `backend/app/rcon_historical_read_model.py`
- `backend/app/postgres_rcon_storage.py`
- `backend/app/payloads.py`
- `backend/tests/test_rcon_materialization_pipeline.py`
- `scripts/audit_public_requests.py`
- `docs/FULL_APPLICATION_REQUEST_AUDIT.md`
- `docs/PERFORMANCE_PUBLIC_QUERY_AUDIT.md`
- `ai/tasks/done/TASK-225-stabilize-critical-public-api-endpoints.md`

## Constraints

- Do not run `ai-platform run`.
- Do not commit or push.
- Do not touch RCON hosts, ports, credentials, environment variables, Docker networking or server connection configuration.
- Do not change `27001` or backend/RCON `127.0.0.1`.
- Do not touch frontend assets, weapon assets, clan assets, SVGs or physical images.
- Do not modify `ai/system-metrics.md`.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.

## Validation

Required before completion:

- `python -m compileall backend/app`
- `python -m unittest tests.test_rcon_materialization_pipeline`
- Relevant focused tests for player search, player detail and historical match detail read-only behavior
- Partial runtime measurement if a backend is available

## Outcome

Completed Phase 1 only. Phase 2 and Phase 3 were deferred because they touch RCON-live behavior, `/api/servers`, or public frontend references and should be handled separately after the non-RCON public read paths are redeployed and measured.

Implemented:

- `/api/stats/players/search` now reads `player_search_index` strictly. It no longer initializes player search storage or falls back to runtime scans in the public helper. Missing/empty read model returns a controlled empty payload with `fallback_used: false`.
- `/api/stats/players/{player_id}` weekly/monthly now reads `player_period_stats` strictly. Missing read model or missing player-period data returns a controlled zero-stat payload with `fallback_used: false`.
- `/api/historical/matches/detail` now uses `get_materialized_rcon_match_detail(..., ensure_storage=False)` in the public RCON read path. The materialized detail helper can read without calling `initialize_rcon_materialized_storage()` or `initialize_postgres_rcon_storage()`. Missing storage/tables return `None`, and the RCON public payload returns `found: false`, `fallback_used: false` instead of falling through to legacy fallback.
- `connect_postgres_compat()` now accepts `initialize=False` for read-only public paths while preserving the previous initializing default for existing write/materialization callers.
- `scripts/audit_public_requests.py` now supports `--filter` and `--player-id` for partial endpoint measurement.
- Documentation was updated in `docs/FULL_APPLICATION_REQUEST_AUDIT.md` and `docs/PERFORMANCE_PUBLIC_QUERY_AUDIT.md`.

Not implemented:

- Phase 2A `/api/current-match/kills` and `/api/current-match/players`: deferred. These depend on RCON-live behavior and must be hardened without changing RCON host/port/configuration.
- Phase 2B `/api/servers`: deferred. It needs a separate read/cache change to avoid mixing server freshness decisions into the stats/read-model fix.
- Phase 3 frontend localhost cleanup: deferred because the user requested no frontend changes in this implementation pass.
- Phase 3B historical snapshot missing/fallback generation: deferred because it likely belongs to scheduler/generation design, not this hot-path stabilization.

Validation performed:

- `python -m compileall backend\app`: OK.
- `python -m py_compile scripts\audit_public_requests.py`: OK.
- `cd backend; python -m unittest tests.test_rcon_materialization_pipeline`: OK, 12 tests. The suite still emits pre-existing SQLite `ResourceWarning` messages.
- `cd backend; python -m unittest tests.test_current_match_payload tests.test_rcon_admin_log_storage tests.test_historical_snapshot_refresh`: OK, 13 tests.
- Partial audit script selection against `http://127.0.0.1:8000`:
  - `--filter stats-player-search`: selected 1 probe, failed because no local backend was listening.
  - `--player-id 76561198092154180 --filter stats-player-profile`: selected weekly/monthly probes, failed because no local backend was listening.
  - `--filter historical-match-detail`: selected 1 probe, failed because no local backend was listening.

Commands to run after redeploy:

```powershell
python scripts\audit_public_requests.py --base-url https://comunidadhll.devzamode.es --timeout 30 --filter stats-player-search --output tmp\task225_prod_player_search_audit.json
python scripts\audit_public_requests.py --base-url https://comunidadhll.devzamode.es --timeout 30 --player-id 76561198092154180 --filter stats-player-profile --output tmp\task225_prod_player_profile_audit.json
python scripts\audit_public_requests.py --base-url https://comunidadhll.devzamode.es --timeout 30 --filter historical-match-detail --output tmp\task225_prod_match_detail_audit.json
```

Restrictions confirmed:

- Did not run `ai-platform run`.
- Did not commit or push.
- Did not modify frontend files.
- Did not touch weapon assets, clan assets, SVGs or physical images.
- Did not modify `ai/system-metrics.md`.
- Did not change `27001`.
- Did not change RCON hosts, ports, credentials, environment variables, Docker networking or server configuration.
- Did not reactivate Elo/MMR.
- Did not reintroduce Comunidad Hispana #03.

## Change Budget

Prefer Phase 1 only if Phase 2/3 would increase production risk or require touching frontend/configuration.
