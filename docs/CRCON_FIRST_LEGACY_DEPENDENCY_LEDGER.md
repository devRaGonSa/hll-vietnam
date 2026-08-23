# CRCON-first legacy dependency ledger

Evidence date: 2026-08-23. Scope: repository readers, writers and declared
Compose jobs after the TASK-305 API facade extraction. This is a
code/configuration audit; it is not a deployment observation and it authorizes
no shutdown or deletion.

## Status vocabulary

- `ACTIVE_REQUIRED`: still needed by a current writer/control path.
- `MIGRATED`: a selectable CRCON replacement exists for the public reader.
- `ROLLBACK_ONLY`: retained for the immediate `legacy` selector path.
- `DEAD_CANDIDATE`: no production reader found, but runtime evidence is still
  required before removal.
- `PRODUCT_DECISION_REQUIRED`: supports MVP, Elo/MMR or player-event behavior
  with no approved CRCON replacement.
- `SHUTDOWN_READY`: every reader is replaced and runtime zero-dependency has
  been proved. No row currently has this status.
- `DECOMMISSIONED`: stopped and removed. No row currently has this status.

## Public source selectors

| Family | Canonical selector | CRCON reader | Legacy reader | Audit status |
| --- | --- | --- | --- | --- |
| Server cards | `HLL_SERVER_LIST_SOURCE=legacy\|crcon` | `services/servers.py` / `get_public_info` | `api/payloads/servers.py`, `storage.py`, live collectors | `MIGRATED`, legacy `ROLLBACK_ONLY` |
| Current match | `HLL_CURRENT_MATCH_SOURCE=legacy\|crcon\|shadow` | `services/current_match.py`: single snapshot using public info + live stats + native log stream | `api/payloads/current_match.py`, AdminLog/current-match materializations | `MIGRATED`, legacy `ROLLBACK_ONLY` |
| Match list/detail | `HLL_HISTORICAL_MATCH_SOURCE=legacy\|crcon` | `services/history.py` / scoreboard maps + map scoreboard | `api/payloads/history.py`, `historical_storage.py`, displayed snapshots, materialized matches | `MIGRATED`, legacy `ROLLBACK_ONLY` |
| Summary/rankings/profile/search | `HLL_HISTORICAL_AGGREGATE_SOURCE=legacy\|crcon` | `services/historical_aggregates.py` plus `services/player_search.py`; read-only CRCON PostgreSQL except authenticated REST search | `api/payloads/rankings.py`, `api/payloads/players.py`, ranking/player/snapshot materializations | `MIGRATED`; runtime verification incomplete |

## Application-owned storage

SQLite and application PostgreSQL adapters can implement the same logical
tables. The row below covers both where both exist.

| Table or artifact | Current readers | Current writers / initializer | CRCON-first replacement | Status and reason |
| --- | --- | --- | --- | --- |
| `game_sources` | server snapshot storage joins | collector / `storage.py`, `postgres_display_storage.py` | CRCON target registry + public info | `ROLLBACK_ONLY` for server cards |
| `servers` | server snapshot history/latest | collector / display storage | CRCON target registry | `ROLLBACK_ONLY` |
| `server_snapshots` | `/api/servers` legacy and `/api/servers/latest`, `/api/servers/history` | collector, request-time legacy refresh | `get_public_info` for current cards; no migration approved for explicit snapshot-history endpoints | `ACTIVE_REQUIRED` until those endpoints are retired or migrated |
| `historical_servers` | legacy history list/detail/aggregates | classic scoreboard ingestion | `ServerTarget` + CRCON REST/DB | `ROLLBACK_ONLY` |
| `historical_maps` | legacy match normalization/joins | classic scoreboard ingestion | CRCON scoreboard maps/detail | `ROLLBACK_ONLY` |
| `historical_matches` | legacy match list/detail, summaries, MVP inputs | classic scoreboard ingestion | CRCON REST list/detail; DB aggregates | `ROLLBACK_ONLY` plus `PRODUCT_DECISION_REQUIRED` for MVP |
| `historical_players` | legacy profiles/leaderboards/MVP | classic scoreboard ingestion | CRCON DB aggregates; API identity search | `ROLLBACK_ONLY` plus `PRODUCT_DECISION_REQUIRED` |
| `historical_player_match_stats` | legacy profiles/leaderboards/MVP | classic scoreboard ingestion | CRCON DB aggregates and map detail | `ROLLBACK_ONLY` plus `PRODUCT_DECISION_REQUIRED` |
| `historical_ingestion_runs` | ingestion diagnostics | classic ingestion | none needed for CRCON-owned history | `ROLLBACK_ONLY` |
| `historical_backfill_progress` | classic resume logic | classic ingestion/backfill | CRCON owns collection | `ROLLBACK_ONLY` |
| `displayed_historical_snapshots` | legacy snapshot endpoints via `historical_snapshot_storage.py` | `historical_snapshots.py` / historical runner | CRCON REST/DB selectable readers | `ROLLBACK_ONLY` plus `PRODUCT_DECISION_REQUIRED` for MVP/player events |
| filesystem `data/snapshots/**` | SQLite snapshot adapter / same public snapshot endpoints | historical runner | same as displayed snapshots | `ROLLBACK_ONLY` plus `PRODUCT_DECISION_REQUIRED` |
| `player_event_raw_ledger` | player-event and MVP V2 snapshot builders | `player_event_worker.py`, display storage | no approved CRCON replacement | `PRODUCT_DECISION_REQUIRED` |
| `player_event_ingestion_runs` | player-event worker diagnostics | player-event worker | none approved | `PRODUCT_DECISION_REQUIRED` |
| `player_event_backfill_progress` | player-event resume logic | player-event worker | none approved | `PRODUCT_DECISION_REQUIRED` |
| `rcon_historical_targets` | capture scope/checkpoint joins | RCON historical storage/worker | CRCON target registry for migrated reads | `ACTIVE_REQUIRED` while legacy capture continues |
| `rcon_historical_capture_runs` | capture diagnostics | RCON historical worker / historical runner | CRCON operational telemetry is out of scope | `ACTIVE_REQUIRED` |
| `rcon_historical_samples` | materialization and Elo rebuild thresholds | RCON historical worker | CRCON REST/DB for migrated public data | `PRODUCT_DECISION_REQUIRED` because Elo uses sample cadence |
| `rcon_historical_checkpoints` | RCON capture resume | RCON historical worker | CRCON-owned collection | `ACTIVE_REQUIRED` while worker remains |
| `rcon_historical_competitive_windows` | competitive-window materialization | RCON historical worker/materializer | CRCON history/aggregates | `ROLLBACK_ONLY` |
| `rcon_admin_log_events` | legacy kill feed/player stats, materializer, maintenance | live and historical AdminLog workers | native CRCON Log Stream for current match; CRCON history/DB elsewhere | `ROLLBACK_ONLY` plus `PRODUCT_DECISION_REQUIRED` for event-derived products |
| `rcon_player_profile_snapshots` | legacy identity/profile materializer | AdminLog capture | API player history + CRCON DB profile | `ROLLBACK_ONLY` |
| `rcon_materialized_matches` | legacy history list/detail/aggregates, maintenance | AdminLog materializer | CRCON REST/DB | `ROLLBACK_ONLY` plus `PRODUCT_DECISION_REQUIRED` |
| `rcon_match_player_stats` | legacy rankings/profiles/MVP/Elo inputs | AdminLog materializer | CRCON DB aggregates | `ROLLBACK_ONLY` plus `PRODUCT_DECISION_REQUIRED` |
| `rcon_scoreboard_match_candidates` | legacy correlation/backfill | scoreboard candidate backfill and historical storage | canonical CRCON map IDs/detail | `ROLLBACK_ONLY` |
| `ranking_snapshots` | legacy Ranking/Stats/leaderboard routes | historical runner / leaderboard refresher | direct CRCON DB timeframe query | `ROLLBACK_ONLY` |
| `ranking_snapshot_items` | same legacy ranking reads | same refresher | direct CRCON DB timeframe query | `ROLLBACK_ONLY` |
| `rcon_annual_ranking_snapshots` | legacy annual Ranking/Stats | annual ranking generator | direct CRCON DB annual query | `ROLLBACK_ONLY` |
| `rcon_annual_ranking_snapshot_items` | same annual readers | annual ranking generator | direct CRCON DB annual query | `ROLLBACK_ONLY` |
| `player_search_index` | only `search_rcon_materialized_players` on legacy selector | historical runner / `refresh_player_search_index` | authenticated `get_players_history` | `ROLLBACK_ONLY`; no CRCON-mode production reader |
| `player_period_stats` | legacy player profile | historical runner / `refresh_player_period_stats` | read-only CRCON DB profile aggregates | `ROLLBACK_ONLY` |
| deprecated CRCON DB player-search helpers (`PLAYER_NAME_SEARCH_SQL`, exact-ID helper) | none after complete TASK-304 reference audit | none | authenticated `get_players_history` | `DECOMMISSIONED` locally as `SAFE_DELETE`; no storage was changed |
| `elo_mmr_player_ratings` | Elo leaderboard/player endpoints | Elo rebuild | none approved | `PRODUCT_DECISION_REQUIRED` |
| `elo_mmr_match_results` | Elo rebuild/checkpoint logic | Elo rebuild | none approved | `PRODUCT_DECISION_REQUIRED` |
| `elo_mmr_monthly_rankings` | Elo public endpoints | Elo rebuild | none approved | `PRODUCT_DECISION_REQUIRED` |
| `elo_mmr_monthly_checkpoints` | Elo rebuild resume | Elo rebuild | none approved | `PRODUCT_DECISION_REQUIRED` |

## Jobs and schedules

| Job | Declaration / cadence | Writes | Remaining reader dependency | Status |
| --- | --- | --- | --- | --- |
| Local server collector/scheduler | manual `app.collector`; `app.scheduler` interval | server snapshot family | explicit snapshot-history endpoints and legacy server cards | `ACTIVE_REQUIRED` |
| `historical-runner` | advanced Compose; once/hourly plus internal public refresh slots | classic history, displayed snapshots, player indexes, ranking snapshots, Elo; can run maintenance | rollback plus MVP/Elo/player-event-derived products | `PRODUCT_DECISION_REQUIRED` |
| `rcon-historical-worker` | advanced Compose; 600/900s historical or 5s current-live by stack | RCON samples/checkpoints/AdminLog/materializations | rollback and derived products | `PRODUCT_DECISION_REQUIRED` |
| `rcon-live-adminlog-worker` | NAS advanced Compose, 5s | AdminLog/profile snapshots | current-match legacy rollback | `ROLLBACK_ONLY` |
| `player-event-worker` | manual/independently schedulable loop | player-event ledger/run/progress | player-event and MVP V2 endpoints | `PRODUCT_DECISION_REQUIRED` |
| ranking refreshers | invoked by historical runner, 15min/weekly/monthly slots | ranking and annual snapshots | legacy Ranking/Stats rollback | `ROLLBACK_ONLY` |
| player index/profile refreshers | every historical-runner primary cycle | `player_search_index`, `player_period_stats` | legacy Stats rollback | `ROLLBACK_ONLY` |
| Elo rebuild | historical runner, useful-data threshold/cadence | all `elo_mmr_*` | explicit Elo endpoints | `PRODUCT_DECISION_REQUIRED` |
| database maintenance | historical runner when enabled; default 12h in JTA config | deletes bounded old materialized/AdminLog/server snapshots | retained tables | `ACTIVE_REQUIRED`; it is not a replacement writer |
| scoreboard candidate backfill | manual bounded CLI | candidate table | legacy match correlation only | `ROLLBACK_ONLY` |
| CRCON native Log Stream consumers | backend startup only in current-match `crcon|shadow` | process memory only | CRCON current-match kill feed | `MIGRATED`; not a legacy writer |
| TASK-298 parity observer | manual bounded `app.observe_current_match_parity` CLI only | optional sanitized evidence file | no product reader | preserved in place for later validation; TASK-298 remains `INSUFFICIENT_EVIDENCE` and TASK-304 performs no waiting |

## Readiness matrix

`READY` here means a later task may propose stopping the listed legacy writer;
it does not mean deployment is authorized.

| Family | Local replacement | Required runtime evidence | Rollback/product dependency | Decision |
| --- | --- | --- | --- | --- |
| Server cards | implemented | no canonical target config in this process | legacy and explicit history endpoints | `NOT_READY` |
| Current summary/players | implemented | TASK-298 accepted as `INSUFFICIENT_EVIDENCE`; no new wait required | immediate rollback | `NOT_READY` to stop writer |
| Current kill feed | native stream implemented | no configured binding/token in this process | immediate rollback | `NOT_READY` |
| Historical list/detail | implemented | verified v12.0.1 contract; local runtime not configured | immediate rollback | `NOT_READY` |
| Summary/rankings/player profile | implemented read-only | deployed CRCON schema/role/query plans remain unverified | immediate rollback | `NOT_READY` |
| Player search | implemented with authenticated REST | API key with `api.can_view_player_history` not configured/tested here | immediate rollback | `NOT_READY`; PostgreSQL name performance is no longer a blocker |
| MVP V1/V2 | not migrated | product equivalence decision | active derived feature | `PRODUCT_DECISION_REQUIRED` |
| Player-event views | not migrated | product equivalence decision | active derived feature | `PRODUCT_DECISION_REQUIRED` |
| Elo/MMR | not migrated | retain/replace/retire decision | active explicit endpoints | `PRODUCT_DECISION_REQUIRED` |
| All legacy writers/storage | partial replacements only | zero-reader runtime proof absent | multiple rollback/product readers | `NOT_READY` |

## Writer-disable gate after TASK-305

The audit is **not READY** for a writer-disable task. TASK-305 reorganized only
the API contract facade and removed three proven-unreferenced private helpers;
it does not authorize a shutdown specification. The exact blockers
are:

1. configure canonical targets/bindings and a server-side Bearer API key with
   `api.can_view_player_history`, then run sanitized player-search samples;
2. configure the authorized SELECT-only CRCON DSN and verify deployed schema,
   scope and bounded query plans for aggregate families;
3. decide MVP V1/V2, player-event and Elo/MMR product disposition;
4. decide whether immediate rollback requires continued writer freshness or a
   documented stale-data rollback window;
5. prove zero active readers per candidate writer/table in the intended runtime
   configuration.

No writer was stopped, no table, gameplay database or snapshot artifact was
deleted, and no Compose or deployment runtime behavior was changed by TASK-304.
