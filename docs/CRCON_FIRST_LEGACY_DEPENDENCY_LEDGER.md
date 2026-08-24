# CRCON-first legacy dependency ledger

Evidence date: 2026-08-24. TASK-309 removed the product-approved MVP V1/V2,
player-event compatibility and Elo/MMR application slices. This ledger records
the surviving readers, writers and stored artifacts. It authorizes no runtime
shutdown, deployment action, table change or data deletion.

## Status vocabulary

- `MIGRATED`: selectable CRCON reader exists.
- `ROLLBACK_HOT`: continuous writes are required for the current immediate,
  fresh legacy switch-back requirement.
- `ROLLBACK_COLD`: code/data remain available, but no continuous writer is
  required.
- `NORMAL_REQUIRED`: required by a surviving non-rollback surface.
- `DEAD_WRITER_CANDIDATE`: no reader or rollback responsibility; source may
  remain only until deployment shutdown is coordinated.
- `DEAD_STORAGE_CANDIDATE`: no application reader/writer; rows and tables may
  still exist and require a later controlled storage task.
- `REMOVED`: application code/contract is gone. This does not imply stored
  data was deleted.

## Final public architecture

```text
CURRENT MATCH          -> CRCON REST + CRCON native Log Stream
HISTORICAL LIST/DETAIL -> CRCON REST
PLAYER SEARCH          -> authenticated CRCON REST
SERVER SUMMARY         -> CRCON PostgreSQL SELECT-only
RANKINGS               -> CRCON PostgreSQL SELECT-only
PLAYER PROFILE         -> CRCON PostgreSQL SELECT-only
MVP                    -> REMOVED
PLAYER-EVENT COMPAT    -> REMOVED
ELO/MMR                -> REMOVED
APPLICATION GAMEPLAY STORAGE -> NONE
```

The four source selectors and their legacy rollback paths remain unchanged:
`HLL_SERVER_LIST_SOURCE`, `HLL_CURRENT_MATCH_SOURCE`,
`HLL_HISTORICAL_MATCH_SOURCE` and
`HLL_HISTORICAL_AGGREGATE_SOURCE`.

## TASK-309 product disposition

| Family | Former application chain | Final product status | Code/contract result | Stored artifact result |
| --- | --- | --- | --- | --- |
| MVP V1 | route -> payload -> snapshot -> historical aggregate -> formula | `REMOVED` | route, payload, formula, snapshot builder, frontend helpers and exclusive tests/docs removed | old displayed/filesystem snapshots are `DEAD_STORAGE_CANDIDATE` |
| MVP V2 | route -> payload -> snapshot -> historical stats + rivalry/duel ledger -> formula | `REMOVED` | complete V2 and exclusive rivalry/duel readers removed | old snapshots are `DEAD_STORAGE_CANDIDATE` |
| player-event compatibility | route -> payload -> aggregate reader -> ledger -> worker/provider | `REMOVED` | routes, payloads, aggregate/source/model/storage/worker modules removed | three player-event tables remain `DEAD_STORAGE_CANDIDATE` |
| Elo/MMR | route -> payload -> Elo read model -> rebuild -> historical facts | `REMOVED` | routes, payloads, engine/model/storage modules, rebuild hooks/config and frontend helpers removed | four Elo tables remain `DEAD_STORAGE_CANDIDATE` |

`api/routes/product_features.py` and
`api/payloads/product_features.py` had no surviving domain and were deleted.
The eight removed URLs now use the normal unmatched-route behavior `(None, {})`;
there are no tombstones or compatibility exports.

Current live kills/teamkills remain CRCON Log Stream data. Completed match
encounters/player statistics remain CRCON scoreboard data. Neither is an
application player-event compatibility feature.

## Application storage ownership

| Table/artifact | Current application readers | Current application writer | Ownership/status | Later action |
| --- | --- | --- | --- | --- |
| `player_event_raw_ledger` | none | none; worker source removed | `DEAD_STORAGE_CANDIDATE`; data may still exist | forward storage cleanup only after inspection |
| `player_event_ingestion_runs` | none | none | `DEAD_STORAGE_CANDIDATE` | same |
| `player_event_backfill_progress` | none | none | `DEAD_STORAGE_CANDIDATE` | same |
| `elo_mmr_player_ratings` | none | none; rebuild removed | `DEAD_STORAGE_CANDIDATE` | same |
| `elo_mmr_match_results` | none | none | `DEAD_STORAGE_CANDIDATE` | same |
| `elo_mmr_monthly_rankings` | none | none | `DEAD_STORAGE_CANDIDATE` | same |
| `elo_mmr_monthly_checkpoints` | none | none | `DEAD_STORAGE_CANDIDATE` | same |
| old MVP/player-event displayed or filesystem snapshots | none | normal snapshot generator no longer emits them | `DEAD_STORAGE_CANDIDATE` | remove artifacts in controlled storage cleanup |
| classic `historical_*` gameplay facts | legacy History/Ranking/Stats rollback | classic ingestion | CRCON duplicate, `ROLLBACK_HOT` | retain until rollback policy/runtime gates close |
| RCON AdminLog/materialized gameplay facts | legacy current/history/ranking/profile rollback | RCON capture/materialization | CRCON duplicate, `ROLLBACK_HOT` | same |
| ranking/player read-model snapshots | legacy Ranking/Stats rollback | historical runner refreshers | CRCON duplicate, `ROLLBACK_HOT` | same |

The PostgreSQL display initializer, migration diagnostic and storage diagnostic
still know the player-event table name solely so existing stored data remains
observable/migratable until the later storage-lifecycle task. No surviving
product reader or writer calls the removed player-event model.

`APPLICATION_GAMEPLAY_STORAGE_TARGET = NONE`. Existing rollback and dead
storage is retained physical state, not a target application-owned gameplay
domain.

## Writer ownership after TASK-310 configuration audit

No runtime replacement can be marked verified until the canonical target,
Bearer, Log Stream and SELECT-only database configuration is supplied. The
active-reader column therefore remains `UNVERIFIED`; this is not evidence that
a legacy reader executed.

| Writer/job | Classification | CRCON replacement runtime verified? | Normal-path active readers | Rollback-only proven? | Safe to stop in next task? |
| --- | --- | --- | --- | --- | --- |
| local collector / scheduler | `NORMAL_REQUIRED` plus `ROLLBACK_HOT` | no; ServerTargets absent | `UNVERIFIED` | no | no |
| classic historical ingestion | `ROLLBACK_HOT` | no; REST/DB runtime absent | `UNVERIFIED` | no | no |
| historical runner | `ROLLBACK_HOT` | no; aggregate runtime absent | `UNVERIFIED` | no | no |
| current/live AdminLog worker | `ROLLBACK_HOT` | no; REST/Log Stream runtime absent | `UNVERIFIED` | no | no |
| RCON historical worker | `ROLLBACK_HOT` | no; history/aggregate runtime absent | `UNVERIFIED` | no | no |
| AdminLog materialization | `ROLLBACK_HOT` | no; current/aggregate runtime absent | `UNVERIFIED` | no | no |
| normal historical snapshot writers | `ROLLBACK_HOT` | no; history/aggregate runtime absent | `UNVERIFIED` | no | no |
| ranking and annual ranking refreshers | `ROLLBACK_HOT` | no; database runtime absent | `UNVERIFIED` | no | no |
| player index/profile refreshers | `ROLLBACK_HOT` | no; API/database runtime absent | `UNVERIFIED` | no | no |
| manual RCON historical backfills | `ROLLBACK_COLD` | not required for normal path | `UNVERIFIED` | no | no |
| scoreboard candidate/relink tools | `ROLLBACK_COLD` | not required for normal path | `UNVERIFIED` | no | no |
| database maintenance scheduler | `NORMAL_REQUIRED` | not applicable while retained stores are hot | `UNVERIFIED` | no | no |
| former player-event worker | `REMOVED` | not applicable | 0 | yes | already removed |
| former Elo rebuild CLI/runner job | `REMOVED` | not applicable | 0 | yes | already removed |

Remaining `APPLICATION_FEATURE_REQUIRED` writers: **none**.

Remaining `DEAD_WRITER_CANDIDATE` implementations: **none**. The two exclusive
candidates were not referenced by Compose/systemd/CI/startup, so TASK-309
removed them rather than leaving broken or dead commands.

## TASK-310 sanitized runtime status

| Status key | Result |
| --- | --- |
| `CRCON_REST_RUNTIME_HLL` | `CONFIGURATION_REQUIRED` |
| `PLAYER_SEARCH_RUNTIME` | `CONFIGURATION_REQUIRED` (Bearer also unavailable) |
| `CRCON_LOG_STREAM_RUNTIME_HLL` | `CONFIGURATION_REQUIRED` |
| `CRCON_DB_DEPLOYED_SCHEMA` | `VERIFIED` (TASK-314 metadata-only inspection) |
| `CRCON_DB_RUNTIME` | `VERIFIED_READ_ONLY` (existing `hll_web_ro` role) |
| `SERVER_SUMMARY_RUNTIME` | `UNVERIFIED` |
| `RANKINGS_RUNTIME` | `UNVERIFIED` |
| `PLAYER_PROFILE_RUNTIME` | `UNVERIFIED` |
| `CURRENT_MATCH_RUNTIME_HLL` | `BLOCKED` |
| `CURRENT_MATCH_PARITY_EVIDENCE` | `INSUFFICIENT_EVIDENCE` |
| `CURRENT_MATCH_HLLV` | `UNVERIFIED` |
| `CRCON_FIRST_ACTIVE_LEGACY_READERS` | `0` (TASK-313 deployed probe) |
| `LEGACY_WRITER_DISABLE_READINESS` | `NOT_READY` |

The canonical local audit found `HLL_SERVER_TARGETS`,
`HLL_CRCON_CURRENT_MATCH_BINDINGS`, `HLL_CRCON_LOG_STREAM_TOKENS` and
`HLL_CRCON_DATABASE_URL` all `NOT_CONFIGURED`. Exact non-secret operator
requirements and the least-privilege SQL template live in
`docs/CRCON_FIRST_RUNTIME_OPERATOR_CHECKLIST.md` and
`docs/CRCON_READ_ONLY_ROLE.sql`.

## TASK-313 reader-boundary inventory and proof

The production cutover handoff reports all four effective selectors as `crcon`,
HTTP 200 smoke results for the three deployed HLL/HLLV targets across server
list, current match, history and ranking, and a default production Compose graph
containing only backend, frontend and PostgreSQL. TASK-313 treats those as
established operator evidence; it did not redeploy or independently repeat the
production probe.

| Canonical surface | Effective selector | Normal CRCON reader | Guarded legacy/rollback boundary |
| --- | --- | --- | --- |
| `/api/servers` | `HLL_SERVER_LIST_SOURCE` | CRCON public-info server-list service | persisted snapshots plus A2S/RCON legacy refresh |
| current snapshot, kills and players | `HLL_CURRENT_MATCH_SOURCE` | CRCON REST snapshot plus native Log Stream | trusted-scoreboard/RCON sample and AdminLog materialized readers |
| recent matches and detail | `HLL_HISTORICAL_MATCH_SOURCE` | CRCON scoreboard maps/detail REST service | classic history, historical snapshots and RCON materialized detail |
| server summary and ranking | `HLL_HISTORICAL_AGGREGATE_SOURCE` | CRCON PostgreSQL SELECT-only aggregate service | historical/ranking snapshots and RCON materialized leaderboard |
| player search and opaque profile | `HLL_HISTORICAL_AGGREGATE_SOURCE` | authenticated CRCON REST search plus CRCON PostgreSQL SELECT-only profile | player index/profile snapshots and classic historical profile |

The inventory classifications are:

- **CRCON normal:** the five services in the table above. They own canonical
  dispatch when the effective selector is `crcon`.
- **Legacy rollback:** payload-level aliases for snapshot/history/AdminLog,
  ranking and player read models. They remain reachable only through explicit
  legacy/shadow or compatibility routes and are patched at their actual use
  sites by the TASK-313 guard.
- **Unrelated:** canonical `ServerTarget` validation, trusted-scoreboard URL
  enrichment, static community payloads, and legacy transport-policy metadata.
  These are not gameplay legacy reads.
- **Dead:** removed MVP, player-event and Elo/MMR readers remain absent. Their
  retained rows/files are storage-lifecycle candidates, not active readers.

`test_crcon_first_reader_boundaries.py` runs the public route dispatcher with
two synthetic HLL targets and one HLLV target. Fake CRCON API/repository objects
serve all normal reads while every known application-owned legacy payload
boundary raises `LegacyReaderAccessError`. It covers 20 route invocations,
including three internally discovered historical details, and proves zero
legacy accesses under all-CRCON selection. Separate tests prove the guard fails
closed, mixed selection is refused, and legacy/shadow selector values remain
valid rollback configuration.

`/health` now exposes `server_list_source`, `current_match_source`,
`historical_match_source` and `historical_aggregate_source`. The older live and
historical runtime-policy fields remain for compatibility and are explicitly
labelled `legacy-rollback-transport-metadata`; they do not describe canonical
CRCON-first route ownership.

`CRCON_FIRST_ACTIVE_LEGACY_READERS = 0` is established for both the
deterministic all-CRCON dispatch contract and the deployed reader process. The
recorded production probe reported `enabled_target_count=3`, `route_count=20`,
`detail_route_count=3`, `legacy_reader_access_count=0` and `status=ok`, with
`HLL_SERVER_LIST_SOURCE`, `HLL_CURRENT_MATCH_SOURCE`,
`HLL_HISTORICAL_MATCH_SOURCE` and `HLL_HISTORICAL_AGGREGATE_SOURCE` all set to
`crcon`.

This proves production reader cutover only. It does not authorize deleting
data, PostgreSQL databases or volumes; stopping every legacy writer; or deleting
rollback images. No writer shutdown follows from the proof.

## TASK-314 CRCON history enrichment relationships

TASK-314 verified the deployed CRCON 12.0.1 schema through the existing
`hll_web_ro` role with both `default_transaction_read_only` and
`transaction_read_only` set to `on`. Historical participant counts use the
following declared relationship:

`map_history.id <- player_stats.map_id`, with the participant identity FK
`player_stats.playersteamid_id -> steam_id_64.id`. The deployed
`unique_map_player (playersteamid_id, map_id)` constraint prevents duplicate
statistics rows per player and map. The implementation nevertheless uses
`COUNT(DISTINCT player_stats.playersteamid_id)` because the product semantics
are canonical participants, not physical rows. The bounded query also verifies
`map_history.server_number` and numeric `map_history.game` for every requested
map and uses the existing `player_stats(map_id)` index.

Explicit external-profile metadata uses the same participant FK. The opaque
CRCON player key is `steam_id_64.steam_id_64`; an explicit SteamID64, when
present, is `steam_id_64.steam_id`. EOS and platform metadata come from
`player_soldier.eos_id` and `player_soldier.platform` through the declared FK
`player_soldier.playersteamid_id -> steam_id_64.id` and its unique
`playersteamid_id` constraint. These values are fetched in one bounded query for
the selected completed map. No identity type is inferred from the opaque key,
its characters, or the game.

## Runtime evidence still required from TASK-307/TASK-310

Product features no longer block runtime migration. The outstanding operational
evidence remains:

1. canonical HLL ServerTargets/bindings for a full HistoryService list/detail
   application run;
2. a server-side Bearer credential with `api.can_view_player_history` for
   bounded player-search validation;
3. a Log Stream token with `api.can_view_structured_logs` and an enabled
   upstream stream for a short sanitized smoke;
4. the explicitly authorized SELECT-only CRCON DSN and target scope, followed
   by role, `transaction_read_only`, deployed-schema/game-value and bounded
   `EXPLAIN` verification;
5. guarded one-shot zero-active-reader proof in the deployed backend process.

TASK-298 remains `INSUFFICIENT_EVIDENCE`; no further complete-match wait is
required for local development.

## Readiness

`LEGACY_FEATURE_BLOCKERS = NONE`.

`LEGACY_WRITER_DISABLE_READINESS = NOT_READY`.

There is no product-feature blocker. Production selectors and smokes establish
the cutover, and deterministic route instrumentation establishes zero legacy
reads for the all-CRCON dispatch contract. Writer-disable readiness remains
blocked on the separate deployed-process operator probe and rollback-policy
decision. The currently hot rollback writers stay enabled; no shutdown task is
eligible yet.

No writer was stopped, no deployment file changed, no table/schema/data was
deleted, and no remote CRCON, PostgreSQL or Redis state was touched.
