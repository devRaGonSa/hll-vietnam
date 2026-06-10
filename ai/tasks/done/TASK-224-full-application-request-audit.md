---
id: TASK-224
title: Full application request audit
status: done
type: research
team: Analista
supporting_teams:
  - Backend Senior
  - Frontend Senior
  - Arquitecto Python
  - Arquitecto de Base de Datos
roadmap_item: foundation
priority: high
---

# TASK-224 - Full application request audit

## Goal

Discover, classify, measure and document all relevant public application requests across frontend and backend/API without applying functional fixes.

## Context

Recent public ranking/snapshot optimizations were followed by a regression in `historico-partida.html` and `/api/historical/matches/detail`. Production profiling showed the real bottleneck was storage initialization during a public read path:

- `get_rcon_historical_match_detail()`: 14.193s
- `get_materialized_rcon_match_detail()`: 14.167s
- `initialize_postgres_rcon_storage()`: 14.147s
- `initialize_rcon_materialized_storage()`: 14.133s
- storage read after initialization: 0.224s
- payload build: 0.014s

This task audits the complete public request surface to find other endpoints with similar cold-read initialization, DDL/bootstrap, direct live network calls or heavyweight fallback behavior.

## Steps

1. Inspect repository context, architecture notes and relevant orchestrator role guidance.
2. Review `backend/app/routes.py` and extract all public GET routes.
3. Review `backend/app/payloads.py` and storage/read-model modules reached by payload builders.
4. Search backend for `initialize_*`, `ensure_*`, DDL, migration, bootstrap, fallback, direct RCON and external HTTP paths.
5. Review public frontend HTML and JavaScript request construction.
6. Create an executable public request audit script using stdlib only.
7. Run the audit against production when available and document measured results.
8. Write the full request matrix and prioritized follow-up tasks.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/analyst.md`
- `ai/orchestrator/backend-senior.md`
- `ai/orchestrator/frontend-senior.md`
- `backend/app/routes.py`
- `backend/app/payloads.py`
- `frontend/*.html`
- `frontend/assets/js/*.js`

## Expected Files to Modify

- `ai/tasks/done/TASK-224-full-application-request-audit.md`
- `docs/FULL_APPLICATION_REQUEST_AUDIT.md`
- `scripts/audit_public_requests.py`
- `tmp/public_request_audit.json`
- `tmp/audit_prod_stdout.txt`
- `tmp/audit_prod_stderr.txt`

## Constraints

- Do not run `ai-platform run`.
- Do not commit.
- Do not push.
- Do not apply functional fixes.
- Do not optimize production code except for audit tooling.
- Do not touch weapon assets, clan assets, SVGs or physical images.
- Do not modify `ai/system-metrics.md`.
- Do not reactivate Elo/MMR.
- Do not add unrelated prior changes.

## Validation

Executed:

```powershell
python -m compileall backend\app
python -m py_compile scripts\audit_public_requests.py
cd backend
python -m unittest tests.test_rcon_materialization_pipeline
```

Results:

- `python -m compileall backend\app`: passed.
- `python -m py_compile scripts\audit_public_requests.py`: passed.
- `python -m unittest tests.test_rcon_materialization_pipeline`: passed, 9 tests in 0.588s. Existing tests emitted `ResourceWarning` for unclosed SQLite connections but did not fail.

Runtime audit:

- Local backend health check against `http://127.0.0.1:8000/health`: unavailable from host, so local endpoint matrix was not launched.
- Production audit against `https://comunidadhll.devzamode.es`: launched 191 probes and wrote `tmp/public_request_audit.json`.
- Manual player-dependent probes launched after deriving `player_id=76561198092154180` from ranking data.

Production automatic summary:

- OK: 77
- WARNING: 110
- CRITICAL: 4
- HTTP 200: 187
- HTTP 500: 1
- timeout/error without HTTP status: 3

Manual player-dependent summary:

- OK: 0
- WARNING: 2
- CRITICAL: 2

Combined measured summary:

- OK: 77
- WARNING: 112
- CRITICAL: 6

## Outcome

Created `docs/FULL_APPLICATION_REQUEST_AUDIT.md` with:

- Executive summary.
- Backend route inventory.
- Frontend fetch inventory.
- Full request matrix with public backend routes, frontend fetches, static assets and internal runners.
- Endpoint severity tables.
- Initialization-in-read detection.
- Heavy fallback detection.
- Frontend loading/error/timeout audit.
- Top risks and prioritized recommendations.
- Proposed follow-up tasks.
- Exact commands to rerun the audit locally, in production and from the backend container.

Created `scripts/audit_public_requests.py` with:

- Configurable base URL and timeout.
- Representative public GET probes.
- HTTP status, elapsed time, response size and JSON metadata extraction.
- Non-fatal endpoint failures.
- JSON output to `tmp/public_request_audit.json` by default.
- Static discovery for backend routes, frontend API literals, `fetch(` occurrences and localhost references.

Key findings:

1. `/api/stats/players/search` times out at 30s in production.
2. `/api/stats/players/{player_id}` weekly/monthly times out at 30s in production.
3. `/api/current-match/kills` times out or returns 500.
4. `/api/current-match/players` times out for `comunidad-hispana-01`.
5. `/api/servers` can spend 4.3s refreshing RCON live data during a public GET.
6. `/api/historical/matches/detail` responded OK for the known real match in this audit, but still has a static initialization-in-read chain and needs later hardening.
7. 13 frontend localhost/127.0.0.1 references remain in public HTML/JS, mitigated by `config.js` but still worth hardening.

Next recommended fix:

1. Fix `/api/stats/players/search` and `/api/stats/players/{player_id}` first by making the public read path strict read-only, without `initialize_*` or runtime fallback.
2. Fix `/api/current-match/kills` and `/api/current-match/players` next.
3. Harden `/api/historical/matches/detail` after those, unless new profiling shows it regressed again.

## Change Budget

Files changed by this task are audit/documentation/support files only. No product logic files were modified.
