# CRCON-first legacy dependency ledger

Evidence date: 2026-08-23. Scope: repository readers, writers and declared
Compose jobs after the TASK-307 non-mutating runtime-readiness pass. This is a
local code/configuration and bounded runtime-evidence audit; it is not a
deployment observation and it authorizes no shutdown or deletion.

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
- `ROLLBACK_HOT`: continuous/periodic writes are required to preserve the
  current requirement for an immediate, fresh feature-flag rollback.
- `ROLLBACK_COLD`: code and storage are retained, but no continuously running
  writer is required; a later bounded reactivation/backfill is acceptable.

## Public source selectors

| Family | Canonical selector | CRCON reader | Legacy reader | Audit status |
| --- | --- | --- | --- | --- |
| Server cards | `HLL_SERVER_LIST_SOURCE=legacy\|crcon` | `services/servers.py` / `get_public_info` | `api/payloads/servers.py`, `storage.py`, live collectors | `MIGRATED`, legacy `ROLLBACK_ONLY` |
| Current match | `HLL_CURRENT_MATCH_SOURCE=legacy\|crcon\|shadow` | `services/current_match.py`: single snapshot using public info + live stats + native log stream | `api/payloads/current_match.py`, AdminLog/current-match materializations | `MIGRATED`, legacy `ROLLBACK_ONLY` |
| Match list/detail | `HLL_HISTORICAL_MATCH_SOURCE=legacy\|crcon` | `services/history.py` / scoreboard maps + map scoreboard | `api/payloads/history.py`, `historical_storage.py`, displayed snapshots, materialized matches | `MIGRATED`, legacy `ROLLBACK_ONLY` |
| Summary/rankings/profile/search | `HLL_HISTORICAL_AGGREGATE_SOURCE=legacy\|crcon` | `services/historical_aggregates.py` plus `services/player_search.py`; read-only CRCON PostgreSQL except authenticated REST search | `api/payloads/rankings.py`, `api/payloads/players.py`, ranking/player/snapshot materializations | `MIGRATED`; runtime verification incomplete |

Public route ownership is now explicit under `api/routes/`: `servers.py`,
`current_match.py`, `history.py`, `players.py` and `rankings.py` align with the
reader families above. `product_features.py` owns only the retained
product-decision routes. `routes/__init__.py` remains the sole application
entrypoint and changes no selector or rollback classification.

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

## TASK-307 public-surface runtime status

The complete evidence and source/runtime distinction is in
`CRCON_12_0_1_CONTRACT_VERIFICATION.md`. The shutdown-relevant summary is:

| Public surface | Implementation | Runtime HLL | Runtime HLLV | Legacy needed in normal CRCON-first operation? | Legacy needed only for rollback? |
| --- | --- | --- | --- | --- | --- |
| server list | YES | VERIFIED | UNVERIFIED | NO for cards; YES for explicit snapshot latest/history routes | YES for cards |
| current summary/players/stats | YES | VERIFIED transport; parity `INSUFFICIENT_EVIDENCE` | UNVERIFIED | NO | YES |
| current killfeed | YES | CONFIGURATION_REQUIRED | UNVERIFIED | NO once stream is configured; current runtime evidence absent | YES |
| historical match list/detail | YES | UNVERIFIED full application chain | UNVERIFIED | NO by design | YES |
| player search | YES | AUTH_UNAVAILABLE | UNVERIFIED | NO by design | YES |
| server summary | YES | AUTH_UNAVAILABLE | UNVERIFIED | NO by design | YES |
| rankings | YES | AUTH_UNAVAILABLE | UNVERIFIED | NO by design | YES |
| player aggregate profile | YES | AUTH_UNAVAILABLE | UNVERIFIED | NO by design | YES |
| MVP V1/V2 | NO approved replacement | PRODUCT_DECISION_REQUIRED | PRODUCT_DECISION_REQUIRED | YES pending decision | NO |
| player-event views | NO approved replacement | PRODUCT_DECISION_REQUIRED | PRODUCT_DECISION_REQUIRED | YES pending decision | NO |
| Elo/MMR | NO approved replacement | PRODUCT_DECISION_REQUIRED | PRODUCT_DECISION_REQUIRED | YES pending decision | NO |

The current local process had no configured ServerTargets/bindings, Log Stream
token or SELECT-only CRCON DSN. A local HTTP smoke with every selector forced to
`crcon` returned explicit empty/degraded/unverified states and `fallback_used`
never became true. This proves source isolation only; it does not close the
missing external-runtime evidence.

## TASK-307 writer-shutdown matrix

`CAN DISABLE NOW` answers the evidence gate, not whether a process happens to
be absent from the default Compose profile. Manual tools are marked `N/A`
because there is no continuous service to stop. The hot/cold classification is
functional and does not assert what is currently deployed.

| Writer | Writes | Current readers | CRCON replacement | Runtime verified? | Rollback class | Product feature dependency | Can disable now? | Why / why not |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| local collector / `app.scheduler` server refresh | `game_sources`, `servers`, `server_snapshots` | legacy `/api/servers`; explicit latest/history routes | `get_public_info` for cards only | YES for HLL cards | `ROLLBACK_HOT` plus active non-migrated routes | snapshot-history surface | NO | explicit snapshot-history readers remain; immediate card rollback expects fresh rows |
| `historical_ingestion` refresh/bootstrap | classic `historical_*`, ingestion runs/progress | legacy history, aggregate and MVP inputs | REST list/detail + DB aggregates | PARTIAL; DB/auth evidence absent | `ROLLBACK_HOT` | MVP | NO | fresh legacy rollback and MVP still consume the family |
| `historical_runner` | classic history, displayed snapshots, ranking/search/profile read models, Elo; invokes maintenance/capture work | legacy Historical/Ranking/Stats plus derived products | split across CRCON REST/API/DB | PARTIAL | `ROLLBACK_HOT` | MVP, player-events, Elo/MMR | NO | authenticated/DB readers are unverified and three product decisions remain |
| `player_event_worker` | player-event ledger, runs and progress | player-event views and MVP V2 builders | none approved | NO | not rollback-only | player-events, MVP V2 | NO | `PRODUCT_DECISION_REQUIRED` |
| `rcon_current_match_worker` / live AdminLog worker | `rcon_admin_log_events`, profile snapshots and downstream materializations | legacy current summary/player/kill paths | public info + live stats + Log Stream | summary/stats YES; Log Stream CONFIGURATION_REQUIRED | `ROLLBACK_HOT` | player-event facts may consume AdminLog | NO | fresh immediate current-match rollback and unverified Log Stream remain |
| `rcon_historical_worker` | targets, runs, samples, checkpoints, windows, AdminLog and materialized facts | legacy history/aggregates, materializers and derived features | REST list/detail + DB aggregates | PARTIAL | `ROLLBACK_HOT` | player-events, MVP, Elo/MMR | NO | DB runtime is unavailable and derived-product dependencies remain |
| `rcon_historical_backfill*` | historical samples/checkpoints/windows and materialized facts | legacy remediation/rebuild paths | CRCON-owned REST/DB history | implementation only | `ROLLBACK_COLD` | possible Elo rebuild input | N/A (manual) | no continuous writer to stop; retain until product and rollback decisions close |
| scoreboard candidate/backfill/relink tools | `rcon_scoreboard_match_candidates`, trusted match links | legacy match-link correlation | canonical CRCON map IDs/detail | upstream detail verified; application runtime unverified | `ROLLBACK_COLD` | none | N/A (manual) | no scheduled writer; retained for cold legacy repair only |
| AdminLog materialization | `rcon_materialized_matches`, `rcon_match_player_stats`, profile snapshots | legacy history/detail/rank/profile and derived products | REST/API/DB by surface | PARTIAL | `ROLLBACK_HOT` | MVP, player-events, Elo/MMR | NO | immediate fresh rollback and product facts still require materialization |
| historical snapshot writers | `displayed_historical_snapshots`, filesystem snapshots | legacy snapshot routes and Historical UI; MVP/player-event snapshots | CRCON REST/DB payloads with TTL cache | PARTIAL | `ROLLBACK_HOT` | MVP, player-events | NO | migrated DB families lack runtime proof and product snapshot contracts remain |
| ranking snapshot writers | `ranking_snapshots`, `ranking_snapshot_items` | legacy Ranking/Stats/leaderboards | direct CRCON DB timeframe ranking | AUTH_UNAVAILABLE | `ROLLBACK_HOT` | none beyond rollback | NO | immediate fresh rollback plus missing DB schema/query-plan evidence |
| annual ranking snapshot writers | annual snapshot/header and item tables | legacy annual Ranking/Stats | direct CRCON DB annual timeframe | AUTH_UNAVAILABLE | `ROLLBACK_HOT` | none beyond rollback | NO | same DB evidence and rollback freshness gap |
| player index/profile refreshers | `player_search_index`, `player_period_stats` | legacy Stats search/profile | authenticated REST search + DB profile | AUTH_UNAVAILABLE | `ROLLBACK_HOT` | none beyond rollback | NO | both API auth and DB runtime evidence are absent |
| Elo rebuild writer | all `elo_mmr_*` tables | explicit Elo endpoints/checkpoint logic | none approved | NO | not rollback-only | Elo/MMR | NO | `PRODUCT_DECISION_REQUIRED` |
| database maintenance scheduler | bounded deletes from retained legacy gameplay tables | storage health for every retained writer/reader | none; lifecycle support only | N/A | not a rollback replacement | all retained writer families | NO | remains necessary while bounded retained stores continue to receive writes |

### Immediate rollback decision

Under the stated immediate feature-flag rollback requirement, collector,
current AdminLog, historical ingestion/materialization, displayed snapshot,
ranking, annual ranking and player index/profile refresh writers are
`ROLLBACK_HOT`: stopping them would make the rollback progressively stale.
They can become `ROLLBACK_COLD` only after an explicit acceptable-staleness or
reactivation window is approved. Manual historical and scoreboard backfills
are already `ROLLBACK_COLD`; keeping their code/storage does not require a
continuously running process.

This does not blur product dependencies: `player_event_worker` is blocked by
player-events/MVP V2, Elo rebuild is blocked by Elo/MMR, and the shared
historical/AdminLog/materialization writers remain blocked by the exact product
features named in their rows even if rollback policy changes.

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

## Writer-disable gate after TASK-307

`LEGACY_WRITER_DISABLE_READINESS=NOT_READY`. TASK-307 did not disable any
writer and does not authorize a shutdown specification. The exact blockers
are:

1. provide canonical HLL ServerTargets/bindings for the full HistoryService
   list/detail application run;
2. provide an aligned server-side Bearer credential with
   `api.can_view_player_history` for bounded sanitized search validation;
3. provide a Log Stream token with `api.can_view_structured_logs` and confirm
   that the upstream stream is enabled for a short smoke;
4. provide the explicitly authorized SELECT-only CRCON DSN and target scope,
   then verify role privileges, `transaction_read_only`, deployed schema/game
   values and bounded `EXPLAIN` plans;
5. decide MVP V1/V2, player-event and Elo/MMR product disposition;
6. decide whether immediate rollback requires hot freshness or permits a
   documented cold/stale reactivation window;
7. prove zero active readers per candidate writer/table in the intended
   runtime configuration.

The next task should first supply the four authorized runtime inputs above and
repeat the non-mutating full-stack probes. Only after they are sufficient
should a product-decision task resolve MVP, player-events and Elo/MMR and
classify their minimum remaining storage.

No writer was stopped, no table, gameplay database or snapshot artifact was
deleted, and no Compose or deployment runtime behavior was changed by TASK-307.
