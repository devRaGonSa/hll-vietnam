---
id: TASK-262
title: Dedupe current match live player stats
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Frontend Senior
roadmap_item: foundation
priority: high
---

# TASK-262 - Dedupe current match live player stats

## Goal

Ensure `/partida-actual.html`, section "Estadisticas en vivo", displays at most one row per player while preserving AdminLog-derived live stats.

## Context

Real observations showed duplicated player rows in the live stats table, for example:

- `chino kudeiro | ALIADOS`
- `chino kudeiro | ALIADOS`
- `[LCM] acuario7 | NO DISPONIBLE`
- `[LCM] acuario7 | ALIADOS`
- `D-ibiz | NO DISPONIBLE`
- `D-ibiz | EJE`

This section must not be confused with the combat feed. The combat feed uses `/api/current-match/kills`; live player stats use `/api/current-match/players`.

The server population, for example `17/100`, is not the same as this table. The table is derived from recent AdminLog events and may contain fewer rows than the live online population. It still must not contain duplicates.

## Mandatory Analysis

### Frontend

Files reviewed:

- `frontend/assets/js/partida-actual.js`
- `frontend/partida-actual.html`

Confirmed behavior:

- Current match scoreboard refreshes every `30000` ms.
- Combat feed refreshes every `1500` ms.
- Live player stats refresh every `3000` ms.
- Current match scoreboard uses `/api/current-match?server={server}`.
- Combat feed uses `/api/current-match/kills?server={server}&limit=18`.
- Live player stats uses `/api/current-match/players?server={server}`.
- `renderPlayerStats(...)` currently sorts and renders `data.items` without a player-level dedupe guard.
- The visible counter currently says `Jugadores detectados: N`, which can be confused with online server population.

### Backend

Files reviewed:

- `backend/app/payloads.py`
- `backend/app/rcon_admin_log_storage.py`
- `backend/app/rcon_admin_log_parser.py`
- `backend/app/routes.py`
- `backend/tests/test_current_match_payload.py`

Confirmed behavior:

- `/api/current-match/players` is routed to `build_current_match_player_stats_payload(server_slug=...)`.
- The payload delegates to `list_current_match_player_stats(server_key=..., ensure_storage=False)`.
- The endpoint represents players detected from safe AdminLog evidence in the current or recent match window, not a complete online roster.
- AdminLog event types used for player stats are `kill`, `team_switch`, `connected`, `disconnected`, `chat` and `message`.
- `connected` and `disconnected` events can create a player row with unknown team.
- `kill`, `team_switch` and `chat` can later provide `Allies` or `Axis`.
- Current aggregation keys by `player_id` when present, otherwise by `player_name.casefold()`.
- The endpoint currently exposes `player_id` and `player_name`; it does not expose separate `steam_id_64` or `epic_id` fields in this payload.
- `last_seen_at` exists in serialized items and is derived from event timestamps.

## Root Cause

The duplicate can happen when an early AdminLog event creates an id-less player bucket keyed by normalized name, and a later event for the same visible player includes a `player_id` and known team. The current aggregation treats those as separate keys (`name:{name}` and `id:{player_id}`), so the frontend receives two rows and renders them directly.

## Functional Rules

1. Live player stats must display at most one row per player.
2. Dedupe identity preference:
   - `player_id` when available.
   - `steam_id_64` when available.
   - `epic_id` when available.
   - normalized `player_name` fallback.
3. Unknown/no disponible plus allies or axis must collapse to the known team.
4. Stats split across duplicate buckets must be preserved.
5. Same display name with different `player_id` values must remain distinct.
6. If no reliable temporal team choice exists, known team wins over unknown.
7. `favorite_weapon` should prefer available weapon evidence over no data.
8. Counter copy must make clear that this is recent-event coverage, not online population.
9. Do not touch TeamKills except as needed to preserve existing aggregation.

## Expected Files to Modify

- `ai/tasks/in-progress/TASK-262-dedupe-current-match-live-player-stats.md`
- `backend/app/rcon_admin_log_storage.py`
- `backend/app/rcon_historical_storage.py`
- `backend/tests/test_current_match_payload.py`
- `frontend/assets/js/partida-actual.js`
- `frontend/partida-actual.html`

## Constraints

- Do not run `ai-platform run`.
- Do not commit.
- Do not push.
- Do not touch physical assets, `frontend/assets/img/`, maps, weapons, clans or brands.
- Do not touch scheduler or RCON server configuration.
- Do not change `27001`.
- Do not reactivate Elo/MMR.
- Do not reintroduce Comunidad Hispana #03.
- Do not touch `ai/system-metrics.md`.
- Do not include `tmp/`.
- Do not include `TASK-204`.
- Do not use `git add .`.
- Do not include unrelated previous changes.

## Implementation Plan

1. Fix backend aggregation so name-key buckets merge into the player-id bucket when later identity evidence arrives.
2. Keep known team when merging unknown and known evidence.
3. Preserve counters, weapon counts, connection state, sources and latest timestamp when merging.
4. Add frontend dedupe as a defensive guard before sorting/rendering.
5. Change player counter copy to "Jugadores con estadisticas recientes: N".
6. Add regression tests for unknown plus known team, same-team duplicates, split stats, distinct players, same name with different IDs and favorite weapon preservation.

## Validation

Required checks:

- `python -m compileall backend/app`
- `cd backend; python -m unittest tests.test_current_match_payload`
- `node --check frontend/assets/js/partida-actual.js`

Endpoint checks:

- `GET /api/current-match/players?server=comunidad-hispana-01`
- `GET /api/current-match/players?server=comunidad-hispana-02`

Visual checks:

- `/partida-actual.html?server=comunidad-hispana-01`
- `/partida-actual.html?server=comunidad-hispana-02`

## Outcome

Implemented.

Backend changes:

- `/api/current-match/players` now merges an id-less name bucket into the stronger `player_id` bucket when later AdminLog evidence identifies the same player.
- Name-only events after one known identity now attach to that known identity when the name is unambiguous.
- Same visible name with different `player_id` values remains distinct.
- Known teams (`Allies`, `Axis`) are kept over unknown/`None`; unknown events no longer overwrite a known team.
- Stats are accumulated with per-event keys for kills, deaths, teamkills, deaths by teamkill and weapon counts, so merging buckets does not double count the same event.
- `favorite_weapon` continues to come from weapon frequency and is preserved when a real weapon exists.
- `rcon_historical_storage.py` was additionally touched because its SQLite connection helper left files locked on Windows during the required tests. The helper now commits/rolls back and closes writer connections explicitly; readonly helpers close as well.

Frontend changes:

- `renderPlayerStats(...)` now applies `dedupeCurrentMatchPlayerStats(items)` before sorting and rendering as a defensive guard.
- Counter copy changed from `Jugadores detectados: N` to `Jugadores con estadisticas recientes: N`.
- The static HTML default copy was updated to the same text.

Endpoint validation:

- `GET /api/current-match/players?server=comunidad-hispana-01`
  - status: `ok`
  - scope: `no-current-match-events`
  - confidence: `stale-filtered`
  - rows: `0`
  - duplicate player names: none
  - unknown plus known duplicates: none
- `GET /api/current-match/players?server=comunidad-hispana-02`
  - status: `ok`
  - scope: `open-admin-log-match-window`
  - confidence: `admin-log-boundary`
  - rows: `1`
  - duplicate player names: none
  - unknown plus known duplicates: none

Validation run:

- Passed: `python -m compileall backend/app`
- Passed: `cd backend; python -m unittest tests.test_current_match_payload`
- Passed: `node --check frontend/assets/js/partida-actual.js`
- Passed fallback HTML checks for:
  - `http://127.0.0.1:8080/partida-actual.html?server=comunidad-hispana-01`
  - `http://127.0.0.1:8080/partida-actual.html?server=comunidad-hispana-02`

Visual validation note:

- The Browser plugin skill was read, but the required `node_repl js` browser control tool was not exposed in this session.
- Local `playwright` was also not installed, so automated screenshot validation could not be completed.
- HTML-served copy was validated with PowerShell as a fallback.

Working tree note:

- Pre-existing unrelated changes remain outside this task, including `ai/system-metrics.md`, clan/map/weapon assets, `tmp/`, `TASK-204` and `TASK-242`.
