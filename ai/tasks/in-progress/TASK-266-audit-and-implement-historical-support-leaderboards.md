---
id: TASK-266
title: Audit and implement historical support leaderboards
status: in-progress
type: backend
team: Backend Senior
supporting_teams: ["Frontend Senior"]
roadmap_item: foundation
priority: high
---

# TASK-266 - Audit and implement historical support leaderboards

## Goal

Determine why the Historico page support tab shows no data and implement support leaderboards only if a reliable historical support source exists.

## Context

The Historico page weekly/monthly "Soporte" tab currently shows:

> Sin datos historicos suficientes para mostrar este ranking de soporte.

The expected UX is to have support leaderboards comparable to kills, deaths and 100+ kill matches, but the implementation must not invent support data or use kills/deaths as a proxy.

## Steps

1. Inspect frontend Historico tab configuration and rendering.
2. Inspect backend payloads, leaderboard storage, snapshots and materialized RCON models.
3. Run read-only DB/source checks for support-related fields.
4. Probe current support endpoints.
5. Classify the issue before changing code.
6. Apply only the justified scoped change, if any.
7. Validate and document the result.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/frontend-senior.md`
- `ai/orchestrator/backend-senior.md`
- `frontend/assets/js/historico.js`
- `frontend/historico.html`
- `backend/app/payloads.py`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/historical_snapshots.py`
- `backend/app/historical_snapshot_storage.py`

## Expected Files to Modify

- `ai/tasks/in-progress/TASK-266-audit-and-implement-historical-support-leaderboards.md`

Additional files may be changed only after the source classification proves that a backend or frontend bug can be fixed safely.

## Constraints

- Do not execute `ai-platform run`.
- Do not commit or push.
- Do not touch assets, maps, weapons, clans or brands.
- Do not touch scheduler, RCON config, RCON hosts/ports, port `27001`, server configuration, TeamKills, Elo/MMR or Comunidad Hispana #03.
- Do not touch `ai/system-metrics.md`.
- Do not include `tmp/`, `TASK-204` or unrelated prior changes.
- Do not use `git add .`.

## Validation

Investigation validation:

- Frontend support tab route/key/rendering audit.
- Backend support source audit.
- Read-only DB/source checks for support, score, offense, defense and combat fields.
- Current support endpoint probes for weekly/monthly and all/#01/#02.
- `git diff --name-only`.

If backend code is changed:

- `python -m compileall backend/app`
- `cd backend; python -m unittest tests.test_current_match_payload`
- relevant leaderboard/snapshot tests
- support-specific backend test if support is implemented

If frontend code is changed:

- `node --check frontend/assets/js/historico.js`

## Findings

### Frontend

- The Historico support tab is configured in `frontend/assets/js/historico.js` under `LEADERBOARD_METRICS`.
- The selected metric key is `support`.
- The tab calls `GET /api/historical/snapshots/leaderboard?server=<server>&timeframe=<weekly|monthly>&metric=support&limit=10`.
- The frontend expects `data.items`.
- If `items` is missing or empty, the table is hidden and the metric empty message is rendered.
- No frontend key mismatch was found: support uses `metric_value`, `matches_considered` and `ratioMode: "support"`.
- The support table headers are already support-specific: `Soporte`, `Partidas`, `Soporte/partida`.

### Backend

- `/api/historical/snapshots/leaderboard` is routed in `backend/app/routes.py` to `build_leaderboard_snapshot_payload(...)`.
- `build_leaderboard_snapshot_payload(...)` reads persisted historical snapshots through `get_historical_snapshot(...)`; it does not query RCON live.
- Snapshot generation uses `backend/app/historical_snapshots.py`.
- In `historical_data_source_kind=rcon`, weekly/monthly leaderboard snapshots call `list_rcon_materialized_leaderboard(...)`.
- `list_rcon_materialized_leaderboard(...)` explicitly returns an empty payload for `metric=support` with reason `rcon-materialized-stats-do-not-include-support-score`.
- The materialized RCON leaderboard query reads `rcon_match_player_stats` joined with `rcon_materialized_matches`.
- That query supports kills/deaths/teamkills/matches/kd/kills-per-match/100+ kills, but not support.

### DB / Source Checks

Local DB: `backend/data/hll_vietnam_dev.sqlite3`.

Relevant schema results:

- `rcon_match_player_stats`: has `kills`, `deaths`, `teamkills`, weapon JSON and active-time fields; no `support`, `combat`, `offense` or `defense`.
- `rcon_materialized_matches`: match metadata and scores; no player support.
- `rcon_player_profile_snapshots`: aggregate profile fields and `averages_json`; no reliable per-match support leaderboard source found.
- `rcon_admin_log_events`: admin log events; no reliable player support score source.
- `historical_player_match_stats`: legacy public-scoreboard table has `combat`, `offense`, `defense`, `support`.
- `ranking_snapshots`: no local snapshots with `metric='support'`.
- `ranking_snapshot_items`: stores generic `metric_value`, but no support-specific materialized source.
- `elo_mmr_*` tables contain support-derived fields, but Elo/MMR is excluded by task constraints and must not be reactivated.

Read-only counts:

- `historical_player_match_stats`: 1,076,025 rows; 562,770 rows with positive `support`; max support 12,065.
- `rcon_match_player_stats`: 3,824 rows; no support column.
- `ranking_snapshots WHERE metric='support'`: 0 rows locally.

Legacy public-scoreboard support can calculate monthly support rankings in local data, but the public UI endpoint currently uses RCON snapshot/read-model paths, not that legacy source. Mixing the legacy source into the RCON snapshot endpoint would be a backend/data-source decision and is outside this task's "no backend" constraint.

### Endpoint Checks

Read-only production probes with cache buster:

- Weekly all support: HTTP 200, `found=true`, `count=0`, `selection_reason=rcon-materialized-stats-do-not-include-support-score`.
- Monthly all support: HTTP 200, `found=true`, `count=0`, `selection_reason=rcon-materialized-stats-do-not-include-support-score`.
- Weekly `comunidad-hispana-01` support: HTTP 200, `found=true`, `count=0`, same reason.
- Monthly `comunidad-hispana-01` support: HTTP 200, `found=true`, `count=0`, same reason.
- Weekly `comunidad-hispana-02` support: HTTP 200, `found=true`, `count=0`, same reason.
- Monthly `comunidad-hispana-02` support: HTTP 200, `found=true`, `count=0`, same reason.

The non-snapshot `/api/historical/leaderboard` support route also returns 200 with `count=0` in production RCON mode.

### Decision

Classification: case 3 / case 2 boundary.

- For the active RCON historical read model used by the public endpoint, there is no reliable per-player support field.
- A legacy public-scoreboard table has support, but that is not the active snapshot/read-model source for the UI.
- Do not fabricate a support leaderboard from kills/deaths or Elo/MMR.
- Do not touch backend, scheduler, RCON, ports or server configuration.
- Apply only a frontend copy change so the empty state explains that support will appear when per-player support score data exists.

## Changes Applied

- Updated the support empty state in `frontend/assets/js/historico.js` from a generic insufficient-data message to:
  - `El ranking de soporte estara disponible cuando tengamos datos de puntuacion de soporte por jugador.`

## Validation Executed

- Audited frontend route/key/rendering for support.
- Audited backend route, snapshot payload builder, historical snapshot generation and RCON materialized leaderboard behavior.
- Ran read-only SQLite schema checks for support/score/offense/defense/combat fields.
- Ran read-only endpoint probes for weekly/monthly support across all/#01/#02.
- Ran `node --check frontend/assets/js/historico.js`.
- Ran `git diff --name-only`.

## Follow-Up Recommendation

Create a separate backend/data task to choose one of these options:

- Materialize per-player support into the active RCON historical read model and generate support snapshots from that source.
- Or explicitly switch/support selected historical support rankings from the legacy public-scoreboard source, with clear data-source policy and backfill/deploy validation.

## Outcome

No support leaderboard was implemented in backend because the active RCON read model does not contain reliable support score data and backend changes were explicitly excluded. The user-visible empty copy now states the real availability condition.

## Change Budget

- Prefer documentation-only unless the audit identifies a reliable source or a clear frontend/backend bug.
- Do not expand scope into data backfill, scheduler, RCON configuration or asset changes.
