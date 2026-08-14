# CRCON-first stateless architecture

## 1. Executive decision

HLL Vietnam will become a stateless, read-only presentation layer over CRCON. The selected target is **Target A**: one Python container serves the static frontend and the `/api` BFF, keeps only bounded process-memory caches, and reads the CRCON HTTP API and CRCON PostgreSQL. Direct RCON is not a mandatory target-v1 dependency; it remains an opt-in emergency adapter only if fixture and deployment validation prove that CRCON cannot provide a required live field.

HLL Vietnam will stop owning gameplay ingestion, AdminLog parsing, match materialization, historical snapshots, ranking snapshots and gameplay PostgreSQL. Existing persistence and workers remain intact during an endpoint-by-endpoint strangler migration and are removed only after accepted parity. The public HLL contracts remain stable unless a versioned contract is explicitly introduced.

Evidence was inspected locally at HLL Vietnam commit `9a86fbffb99d8919e1232ae513319426acd6d708` and in the official CRCON repository `https://github.com/MarechJ/hll_rcon_tool`, branch `master`, commit `4cf1e7e2fa691d849eaf85abb7065010e13f28e4`, on 2026-08-14. No production system or database was accessed.

## 2. Architecture goals/non-goals

Goals:

- make CRCON the system of record for live and historical gameplay;
- reduce HLL runtime ownership to one replaceable process with no gameplay disk state;
- retain stable HLL-oriented payloads behind an anti-corruption adapter;
- bound upstream load through short-lived memory caching, request coalescing and timeouts;
- preserve rollback until every consumer is validated; and
- expose freshness, source and degraded state instead of silently mixing data.

Non-goals:

- repairing HLL-owned historical data or reproducing TASK-288 against production;
- changing CRCON, writing to its database, or relying on undocumented tables;
- implementing product behavior in this architecture task;
- preserving every legacy metric regardless of cost or semantics; and
- adding Redis, another database, queues, workers or scheduled materialization.

## 3. Current architecture

```text
browser
  |-- static files ----------------------> frontend container
  `-- JSON ------------------------------> backend container
                                               |-- HLL PostgreSQL
                                               |-- SQLite/files/snapshots
                                               |-- public CRCON scoreboard API
                                               `-- direct RCON

historical-runner ----------------------------> HLL stores/snapshots
rcon-live-adminlog-worker --> RCON AdminLog --> HLL PostgreSQL
rcon-historical-worker ----> RCON/scoreboard -> HLL PostgreSQL
```

The repository root Compose declares `postgres`, `backend`, `frontend` and two advanced-profile workers. The active Portainer definition declares six services: the three core services plus `historical-runner`, `rcon-live-adminlog-worker` and `rcon-historical-worker`. It has `postgres-data` and `backend-data` persistent volumes. The JTA definition declares five services and two named volumes. The backend also contains a local snapshot scheduler. Default profiles start three services; advanced profiles increase the process graph to five or six.

## 4. Target architecture

```text
browser
  `-- same origin --> HLL stateless container
                        |-- static frontend
                        |-- HLL domain/BFF API
                        |-- bounded in-memory cache
                        |-- read-only CRCON API client
                        `-- read-only CRCON PostgreSQL client

CRCON remains owner of RCON ingestion, Redis/live caches and PostgreSQL history.
Optional direct RCON adapter: disabled by default, no persistence, no worker.
```

One process is appropriate because the frontend is static HTML/CSS/JavaScript, the existing backend already uses Python's `ThreadingHTTPServer`, and same-origin static-file routing is a small server responsibility. A separate static container provides no necessary isolation at this scale. If future measured traffic proves otherwise, static assets can move to a CDN without changing the BFF contract.

## 5. Current service inventory

| Service/process | Current purpose and dependencies | Persistence | Resource role | Target |
| --- | --- | --- | --- | --- |
| `postgres` | HLL-owned gameplay/history, materialized matches and ranking/read models | `postgres-data`/JTA PostgreSQL volume | Stateful baseline | REMOVE after parity |
| `backend` | Public JSON API; reads local stores, CRCON/scoreboard and RCON | Reads DB, SQLite and snapshot files | Request-serving plus synchronous aggregation | REWRITE as stateless combined service |
| `frontend` | Python static HTTP server | Image assets only | Separate always-on process | MERGE into backend image/process |
| `historical-runner` | Scheduled ingestion and snapshot regeneration | HLL DB/files | Periodic CPU/network load | REMOVE |
| `rcon-live-adminlog-worker` | Polls AdminLog and persists live events | HLL PostgreSQL | Continuous polling/write load | REMOVE; CRCON owns ingestion |
| `rcon-historical-worker` | Captures/materializes RCON history and competitive windows | HLL PostgreSQL | Continuous/periodic polling and writes | REMOVE |
| local `scheduler.py` loop | Refreshes historical snapshot artifacts | Snapshot files/DB | Scheduled process | REMOVE |
| CRCON API | External live/public/history capability | CRCON-owned Redis/DB | External dependency | KEEP external |
| CRCON PostgreSQL | External canonical history/log/player data | CRCON-owned | External dependency | KEEP read-only external |
| direct RCON client | Current fallback/live capability | None by itself | Server load and operational coupling | REVIEW; disabled optional fallback |

Target counts: one HLL service, zero HLL gameplay volumes, zero HLL workers and zero HLL scheduled jobs. External dependencies are CRCON API and CRCON PostgreSQL; direct RCON is conditional.

## 6. Persistence inventory

| HLL-owned family | Principal tables/files | Owners/readers | Disposition and prerequisite |
| --- | --- | --- | --- |
| Source/server catalog | `game_sources`, `servers` | `postgres_display_storage`, server payloads | TEMPORARILY KEEP; replace small trusted-server catalog with validated environment/static configuration, then REMOVE |
| Server sampling | `server_snapshots` | snapshot writers, landing/history payloads | TEMPORARILY KEEP; migrate to CRCON public info and `server_counts`, then REMOVE |
| Imported historical core | `historical_servers`, `historical_maps`, `historical_matches`, `historical_players`, `historical_player_match_stats` | historical import/storage and payloads | TEMPORARILY KEEP; migrate list/detail/profile/ranking surfaces, then REMOVE |
| Display snapshots | `displayed_historical_snapshots`, snapshot JSON under backend data | generators/scheduler, snapshot endpoints | TEMPORARILY KEEP; migrate consumers and caching, then REMOVE |
| Raw player ledger | `player_event_raw_ledger` | event/duel/weapon generation | TEMPORARILY KEEP; validate CRCON `log_lines` semantics, then REMOVE |
| SQLite historical store | `historical_servers`, `historical_maps`, `historical_matches`, `historical_players`, `historical_player_match_stats`, `ingestion_runs`, `backfill_progress` | `historical_storage` and runners | TEMPORARILY KEEP; remove after PostgreSQL legacy rollback window closes |
| Historical RCON capture | `rcon_historical_targets`, `rcon_historical_capture_runs`, `rcon_historical_samples`, `rcon_historical_checkpoints`, `rcon_historical_competitive_windows` | historical worker/storage | TEMPORARILY KEEP; remove worker and all migrated dependants first |
| AdminLog/materialization | `rcon_admin_log_events`, `rcon_player_profile_snapshots`, `rcon_materialized_matches`, `rcon_match_player_stats` | AdminLog worker/parser/materializer, live/history payloads | TEMPORARILY KEEP; migrate current match and history, then REMOVE |
| Ranking/read models | `rcon_annual_ranking_snapshots/items`, `ranking_snapshots/items`, `player_search_index`, `player_period_stats`, `rcon_scoreboard_match_candidates` | snapshot generators, ranking/profile/search payloads | TEMPORARILY KEEP; replace with bounded CRCON reads plus TTL cache, then REMOVE |
| Named volumes | `postgres-data`, `backend-data`, `jta-postgres-data`, `jta-backend-data` | Compose services | REMOVE only after export/retention decision and rollback expiry |

No genuinely database-owned non-game product configuration was found. Community, trailer and Discord values are code/config payloads. The trusted server catalog may remain HLL-owned, but it does not justify a database and should become validated configuration.

## 7. Full endpoint inventory

All routes are GET. `A` means CRCON API, `B` CRCON PostgreSQL, and `C` optional direct RCON. Builder names refer to `backend/app/payloads.py`.

| Path; query | Frontend | Current builder/source | Target; cache | Compatibility / decision / difficulty |
| --- | --- | --- | --- | --- |
| `/health` | `main.js`, `stats.js` | `build_health_payload`; local dependencies | local readiness plus CRCON capability probes; 5 s | retain, extend fields compatibly; low |
| `/api/community` | none found | static `build_community_payload` | local config; immutable | retain; low |
| `/api/trailer` | `main.js` | static `build_trailer_payload` | local config; immutable | retain; low |
| `/api/discord` | none found | static `build_discord_payload` | local config; 60 s | retain; low |
| `/api/servers` | `main.js` | `build_servers_payload`; source catalog/snapshots/providers | A `get_public_info` per configured server; 5 s | retain payload; medium |
| `/api/servers/latest` | none found | `build_server_latest_payload`; server snapshots | A public info; 5 s | retain/deprecate if unused; low |
| `/api/servers/history?limit` | none found | `build_server_history_payload`; snapshots | B `server_counts`; 60 s | retain; medium |
| `/api/servers/{server_id}/history?limit` | none found | `build_server_detail_history_payload`; snapshots | B `server_counts` filtered by server; 60 s | retain; medium |
| `/api/current-match?server` | `partida-actual.js`, 30 s | `build_current_match_payload`; public scoreboard/RCON/materialized live state | A public info plus B map/log identity; 2 s | compatibility view over snapshot; medium |
| `/api/current-match/kills?server&limit&since_event_id` | `partida-actual.js`, 1.5 s | `build_current_match_kill_feed_payload`; AdminLog store/read model | B bounded `log_lines`; 1 s, cursor-aware | compatibility view; high |
| `/api/current-match/players?server` | `partida-actual.js`, 3 s | `build_current_match_player_stats_payload`; live/read models | A live stats/player state plus B bounded log aggregation; 2 s | compatibility view; high |
| `/api/stats/players/search?q&limit&server_id|server` | `stats.js` | `build_stats_player_search_payload`; search index | B `player_soldier`, `player_names`, `player_ids`; 15 s | retain; medium |
| `/api/stats/players/{player_id}?timeframe&server_id|server` | `stats.js` | `build_stats_player_profile_payload`; period/read models | A profile/history plus B bounded stats; 30 s | retain; high |
| `/api/stats/rankings/annual?metric=kills&year&limit&server_id|server` | `stats.js` | annual snapshot builder/tables | B `player_stats` + `map_history`; 5 min | retain alias, route through common ranking; medium |
| `/api/ranking?timeframe&metric&limit&server&year` | `ranking.js` | global ranking builder/snapshots | B bounded aggregate; 1-5 min by period | retain; high |
| `/api/historical/weekly-top-kills?limit&server` | none found | legacy ranking builder | B bounded aggregate; 2 min | deprecate in favor of `/api/ranking`; medium |
| `/api/historical/leaderboard?limit&server&metric&timeframe` | none found | historical leaderboard/read models | B bounded aggregate; 2 min | deprecate after aliases; medium |
| `/api/historical/weekly-leaderboard?limit&server&metric` | none found | weekly builder | B bounded aggregate; 2 min | deprecate after aliases; medium |
| `/api/historical/monthly-leaderboard?limit&server&metric` | none found | monthly builder | B bounded aggregate; 5 min | deprecate after aliases; medium |
| `/api/historical/monthly-mvp?server&limit` | none found | MVP snapshot/read model | B `player_stats`; 5 min | DEFER pending product value/semantic definition; high |
| `/api/historical/monthly-mvp-v2?server&limit` | none found | MVP-v2 snapshot/read model | B `player_stats`; 5 min | keep only v2 if accepted, deprecate v1; high |
| `/api/historical/player-events?server&view&limit` | none found | raw ledger/event models | B bounded `log_lines`; 1-5 min | keep weapon/duel views if semantics validate; high |
| `/api/historical/snapshots/leaderboard?server&timeframe&metric&limit` | `historico.js` | snapshot file/table | B aggregate via cache; 2 min | retain path during migration, remove snapshot semantics later; medium |
| `/api/historical/snapshots/monthly-leaderboard?server&metric&limit` | none found | snapshot generator/store | B aggregate via cache; 5 min | deprecate duplicate; medium |
| `/api/historical/snapshots/monthly-mvp?server&limit` | none found | snapshot generator/store | B aggregate via cache; 5 min | follow MVP decision; high |
| `/api/historical/snapshots/monthly-mvp-v2?server&limit` | none found | snapshot generator/store | B aggregate via cache; 5 min | follow MVP-v2 decision; high |
| `/api/historical/snapshots/player-events?server&view&limit` | none found | snapshot generator/store | B bounded logs via cache; 1-5 min | deprecate duplicate after consumer audit; high |
| `/api/historical/snapshots/weekly-leaderboard?server&metric&limit` | none found | snapshot generator/store | B aggregate via cache; 2 min | deprecate duplicate; medium |
| `/api/historical/recent-matches?server&limit` | none found | historical storage/provider | A `get_scoreboard_maps`; 15 s | retain; medium |
| `/api/historical/snapshots/recent-matches?server&limit` | `historico.js`, `historico-recent-live.js` | displayed snapshot | A `get_scoreboard_maps`; 15 s | compatibility alias then consolidate; medium |
| `/api/historical/matches/detail?server&match` | `historico-partida.js` | historical/read-model/detail builders | A `get_map_scoreboard`; 30 s/immutable after end | retain; medium |
| `/api/historical/server-summary?server` | none found | historical aggregate | A/B maps + counts; 60 s | retain; medium |
| `/api/historical/snapshots/server-summary?server` | `historico.js` | displayed snapshot | A/B maps + counts; 60 s | compatibility alias then consolidate; medium |
| `/api/historical/player-profile?player` | none found | historical player/profile models | A player profile/history plus B stats; 30 s | deprecate in favor of stats profile; high |
| `/api/historical/elo-mmr/leaderboard?server&limit` | none found | HLL Elo snapshot/read models | no verified CRCON equivalent | REMOVE/DEFER while feature is paused; high |
| `/api/historical/elo-mmr/player?server&player` | none found | HLL Elo read models | no verified CRCON equivalent | REMOVE/DEFER while feature is paused; high |

Classification summary: static/local routes remain local; live surfaces combine A+B; history detail prefers A; server samples, rankings, search, profiles and event analytics use verified bounded B reads; C is not required for the base design.

## 8. Frontend consumer inventory

| Page/component | Endpoint and expected contract | Current interval/fan-out | Migration impact |
| --- | --- | --- | --- |
| global `main.js` health | `/health`: status | startup | retain |
| home trailer | `/api/trailer`: trailer metadata | startup | none |
| home servers | `/api/servers`: configured server cards/live state | initial plus 300 s | retain; cache shared public info |
| current-match summary | `/api/current-match`: identity/map/score/timing | 30 s | replace with snapshot |
| current-match feed | `/api/current-match/kills`: cursor/events | 1.5 s | replace with snapshot delta/version |
| current-match players | `/api/current-match/players`: teams/player totals | 3 s | replace with snapshot |
| history shell summary | snapshot server-summary | page load | alias to non-snapshot source |
| history recent list | snapshot recent-matches | page load | alias to CRCON scoreboard maps |
| history recent-live helper | same recent list | retries at 150/1000/3000/6000 ms, then 60 s | remove duplicate initial fetch and coalesce |
| history leaderboard | snapshot leaderboard | page/filter changes | route to cached CRCON aggregate |
| match detail | `/api/historical/matches/detail` | page load | CRCON map scoreboard |
| ranking | `/api/ranking` | page/filter changes | CRCON bounded aggregate |
| stats health/search/annual/profile | health, player search, annual ranking, player profile | page load and user actions | preserve contracts over adapters |

The current-match page creates three independently timed streams and can observe three source instants. Replace them with `GET /api/current-match/snapshot?server=...&since_version=...` every 2 seconds; one response carries summary, players and recent feed. Compatibility endpoints project the same cached snapshot during rollout. History code should have one owner for recent-match loading.

## 9. CRCON capability matrix

| HLL capability | CRCON API candidate | CRCON DB candidate | Direct RCON candidate | Chosen source | Reason |
| --- | --- | --- | --- | --- | --- |
| Live map/layer/mode/start/score/time | `get_public_info` | current `map_history` row | game state | API | Lightweight, public, current RCON-backed fields |
| Slots/online/team counts | `get_public_info` | `server_counts` is sampled history | slots/player list | API | Directly exposed live |
| Player names/team/state | `get_live_game_stats` / `get_live_scoreboard` | identities plus current logs | player list | API with freshness flags | CRCON owns live state; DB identities supplement |
| Stable match identity | scoreboard map APIs | `map_history.id`, start/server | derived tuple | DB `map_history.id` | Durable canonical CRCON identity |
| Killfeed/teamkills/weapons | historical/recent logs API | `log_lines` bounded by map/server | AdminLog | DB | Indexed durable events and cursor; avoids HLL worker |
| Live player K/D/TK | live stats (accuracy caveat) | bounded `log_lines` aggregation | player stats/log | DB aggregation | Upstream issue #1186 makes live kill totals unsafe without validation |
| Live combat/support scores | live game stats | `player_stats` where current row is available | player stats | API | Scores are not reconstructible from kills; mark stale/degraded |
| Match transitions | public info/map list | open/closed `map_history` | game state | API + DB | Change in canonical map id/version invalidates cache |
| Recent/paginated matches | `get_scoreboard_maps` | `map_history` | none | API | Existing pagination and scoreboard payload |
| Match detail/result/player stats | `get_map_scoreboard` | `map_history` + `player_stats` + logs | none | API | Existing normalized detail; immutable cache after end |
| Historical kill encounters | map scoreboard enriches KILL logs | bounded `log_lines` | none | API, DB for special views | Avoid duplicate reconstruction |
| Rankings | no verified general ranking endpoint | `player_stats` + `map_history` + identities | none | DB | Indexed, bounded period aggregation with TTL |
| Player search/name history | player-history/profile APIs | `player_soldier`, `player_names`, `player_ids` | none | DB | Explicit identity/name tables support deterministic search |
| Player profile/sessions | player profile/history APIs | identities + `player_sessions` + stats/maps | none | API + DB | API identity/session, DB bounded product aggregates |
| Server availability/current | `get_public_info` | latest `server_counts` | slots | API | Canonical live status |
| Displayed server history | no required API | `server_counts`, `player_at_count` | none | DB | CRCON-owned samples |

## 10. Verified CRCON API contracts

Verified at the pinned upstream commit:

- `/api/get_public_info` is a GET, CSRF-exempt public endpoint with a 60/minute rate limit. Its result includes current map/start, next map, player/max counts, counts by team, Allied/Axis score, cap flips, match time, remaining time, vote status and configured name.
- `/api/get_scoreboard_maps` is stats-authenticated, rate-limited to 60/minute, accepts `page`, `limit` (maximum 1000) and `server_number`, orders maps newest-first and returns map identity, creation/start/end, server number, player stats and result.
- `/api/get_map_scoreboard` is stats-authenticated, rate-limited to 60/minute, accepts `map_id`, returns a map with player stats and enriches encounters from bounded historical KILL logs.
- `/api/get_live_scoreboard` returns Redis-backed session statistics. Upstream explicitly notes that these statistics reset on disconnect rather than match start.
- `/api/get_live_game_stats` returns Redis-cached current statistics. The current implementation builds a time-window from the current map start and recent persisted logs, then enriches unit/player data. Upstream issue [#1186](https://github.com/MarechJ/hll_rcon_tool/issues/1186) reports inaccurate kill data, so HLL must not use its K/D/TK values as canonical until contract tests pass.
- API registration also exposes RconAPI calls including player profile/history and historical/recent log queries. Authentication and deployed permission grants for these calls remain a handoff question.

Source anchors: [API URLs](https://github.com/MarechJ/hll_rcon_tool/blob/4cf1e7e2fa691d849eaf85abb7065010e13f28e4/rconweb/api/urls.py), [public info](https://github.com/MarechJ/hll_rcon_tool/blob/4cf1e7e2fa691d849eaf85abb7065010e13f28e4/rconweb/api/views.py), and [scoreboard API](https://github.com/MarechJ/hll_rcon_tool/blob/4cf1e7e2fa691d849eaf85abb7065010e13f28e4/rconweb/api/scoreboards.py).

## 11. Verified CRCON DB schema contracts

The contract is read-only and capability-probed at startup. Names below are verified in upstream [`rcon/models.py`](https://github.com/MarechJ/hll_rcon_tool/blob/4cf1e7e2fa691d849eaf85abb7065010e13f28e4/rcon/models.py).

| Table/model | Verified fields and constraints | Join/query shape and risk |
| --- | --- | --- |
| `steam_id_64` / `PlayerID` | PK `id`; unique/indexed non-null game `player_id` column; optional Steam ID; created | identity root; upstream attribute/column naming differs, probe actual column |
| `player_soldier` / `PlayerSoldier` | unique/indexed FK `playersteamid_id`; `eos_id`, `name`, `level`, `platform`, `clan_tag`, `updated` | join identity 1:1; nullable profile fields |
| `player_names` / `PlayerName` | unique `(playersteamid_id,name)`; indexed FK; `name`, `created`, `last_seen` | prefix/exact search ordered by last seen; bound results |
| `player_sessions` / `PlayerSession` | indexed player FK; `start`, `end`, `server_number`, `server_name`, `created` | player/server/date range, order start desc; open `end` nullable |
| `log_lines` / `LogLine` | unique `(event_time,raw)`; indexed `event_time`, type/player FKs; player names/IDs, `weapon`, `server`, `game`, raw/content | filter `event_time >= map.start AND < coalesce(map.end, now)` plus server/game discriminator; order `(event_time,id)` and keyset page; raw/content never exposed |
| `map_history` / `Maps` | unique `(start,end,server_number,map_name)`; indexed `start`, `end`, `server_number`, `map_name`; JSON result/layout/cap flips, match time/game | list by server and `(start,id)` descending; current row may have nullable end/result |
| `player_stats` / `PlayerStats` | unique `(playersteamid_id,map_id)`; indexed player/map FKs; name, kills/deaths/teamkills, streak/life/time/KPM/DPM/KD, combat/offense/defense/support, vehicle/assist/redeploy, JSON weapons/encounters/units, level | join map and identity; bound by map start/server; JSON compatibility must be fixture-tested |
| `server_counts` / `ServerCount` | unique `(server_number,datapoint_time)`; indexed unique datapoint time and indexed map FK; count/vip_count | server/time range, descending keyset; confirm composite/selectivity in target schema |
| `player_at_count` / `PlayerAtCount` | unique `(playersteamid_id,servercount_id)`; both FKs indexed; vip | optional membership drill-down; never required for landing summary |

Bounded ranking template: select completed maps for one configured server with `start >= period_start AND start < period_end`, join `player_stats`, group by canonical player, order by a whitelisted aggregate plus canonical ID, and enforce a hard limit. Do not interpolate metric names except from a static whitelist. Current-match log queries use the canonical map start and server discriminator; inclusive/exclusive end semantics must be fixed by fixtures. Schema names, actual DB types, privileges and migration compatibility are unresolved until a local CRCON fixture or authorized deployment handoff is available.

## 12. Internal BFF/domain model

CRCON rows never cross the adapter boundary. HLL owns stable domain records:

- `CurrentMatch`: HLL server slug, CRCON map ID, map/layer/mode, start, score, remaining seconds, slots/counts, players, recent kills, version, observed-at and freshness/degraded metadata.
- `CurrentPlayer`: canonical player ID, display name, team/unit/role/status, kills/deaths/teamkills, combat/offense/defense/support and source timestamps.
- `KillEvent`: opaque cursor, event time, killer/victim domain refs, teams, weapon, teamkill flag and match ID.
- `HistoricalMatch`: canonical CRCON map ID, server, start/end, map/layer/mode, result and completeness.
- `HistoricalPlayerStat`: match/player identity, duration, kills/deaths/teamkills, score dimensions and weapons.
- `PlayerSummary`: canonical ID, current/historical display names, sessions, period aggregates and recent matches.
- `RankingRow`: rank, player identity, selected metric, component counts and period.
- `ServerSummary`: configured identity, availability, player/slot/queue/map data, observed-at and history summary.

Adapters map API JSON and SQL rows into these records; serializers map records into current or versioned HLL payloads. Source-specific nulls and enums are normalized once.

## 13. Current-match architecture

Introduce `GET /api/current-match/snapshot?server=...&since_version=...`. One request coalesces:

1. CRCON `get_public_info` for current map/game state and counts;
2. the current/open `map_history` record for stable `match_id` and time bounds;
3. bounded `log_lines` for cursor-based feed and live K/D/TK aggregation; and
4. CRCON live game/player state for teams, roles and score dimensions that logs cannot provide.

The response includes `match_id`, `version`, `observed_at`, per-source timestamps, `freshness`, `degraded`, `sources`, summary, players and kills. Version changes on canonical match ID or material content. A match change evicts that server's live keys. `/current-match`, `/kills` and `/players` remain compatibility projections of the same cached snapshot, eliminating three independent source instants.

No HLL event watermark is persisted. Kill cursors are opaque encodings of the canonical match ID plus ordered CRCON event position; a cursor from another match yields a reset marker. If `map_history` lags, use a deterministic temporary identity from configured server + public-info start + canonical map, label it `ephemeral`, and replace it when the CRCON ID appears. Direct RCON is invoked only by an explicitly enabled adapter after a proven CRCON gap; it never writes locally.

## 14. Historical architecture

Recent and paginated history uses `get_scoreboard_maps`; detail uses `get_map_scoreboard`. Completed detail responses are immutable-cache candidates. CRCON `map_history.id` is the public opaque match identity; HLL must not reconstruct matches from AdminLog boundaries.

Special bounded event views may query `log_lines` between the selected map's start/end and server discriminator. Player stats come from the scoreboard response or `player_stats`, not HLL materialization. Server history uses `server_counts`. API authentication/rate limits and DB query plans are validated before switching. Snapshot-named HLL endpoints become compatibility aliases and stop implying persisted HLL snapshots.

## 15. Ranking/profile architecture

Weekly, monthly and annual kills, deaths, teamkills, K/D, kills per match and matches considered are bounded aggregates over completed `map_history` + `player_stats`. `support` is kept with CRCON source because it is a verified `player_stats` field. Results are cached by server/period/metric/limit and return a common ranking contract.

Player search reads identity, soldier and name-history tables with strict limits. Profile identity/sessions prefer CRCON player APIs; period totals and recent matches may use bounded SQL. Monthly MVP v1 is deprecated; MVP v2 is deferred until its formula and product value are approved. Weapon/duel/teamkill views are kept only after `log_lines` fixture semantics pass. HLL Elo/MMR remains removed/deferred because no verified CRCON equivalent exists and the UI is paused.

## 16. In-memory caching

| Capability | TTL / maximum | Key and invalidation |
| --- | --- | --- |
| server/public info | 3-5 s / 2 per configured server | server; expire or observed match change |
| live snapshot | 1-2 s / 4 per server | server + match/version; evict on match ID change |
| kill delta | 1 s / 4 per server | match ID + cursor bucket; match change |
| recent matches | 15 s / 20 pages | server + page + limit; newest map ID change |
| completed detail | 1 h, then bounded LRU 200 | server + map ID; immutable when ended |
| server history | 60 s / 20 | server + range/limit |
| rankings | weekly 2 min, monthly/annual 5 min / 200 | server + exact period + metric + limit |
| player search/profile | 15 s / 200 and 30 s / 500 | normalized query or player + period |

Use per-key request coalescing, bounded LRU size, monotonic expiries, up to one stale value and no disk serialization. Apply hard upstream timeouts, at most one retry for idempotent reads with jitter, exponential circuit backoff and per-server isolation. Never cache credentials, raw logs or CRCON rows.

## 17. Connection/security model

The CRCON DB role is dedicated and read-only: `CONNECT`, `USAGE` on the selected schema and `SELECT` only on allowlisted tables. The client uses a small pool (initial recommendation 2-5 connections), `application_name=hll-vietnam-bff`, read-only transactions, no write-capable autocommit, server-side `statement_timeout` (2 s live, 5 s bounded analytics), lock/connection timeouts and rollback-on-return. Startup probes table/column/index capabilities without creating schema. An unsupported required capability makes the affected endpoint unavailable with `CRCON_SCHEMA_INCOMPATIBLE`; it never runs migrations.

API credentials and DB DSNs are injected secrets, redacted from logs and never returned. SQL uses parameters; selectable metrics/order expressions use a fixed whitelist. The BFF exposes no raw rows, player platform IDs beyond the existing approved contract, raw log text or upstream authenticated URLs.

## 18. Failure/degraded behavior

- API down, DB healthy: history/rankings continue; current snapshot uses DB-derived fields and marks API-dependent timing/team/score fields degraded.
- DB down, API healthy: public server state and scoreboard history continue; kill cursor, log-derived K/D and DB rankings fail or serve bounded stale cache with explicit flags.
- both down: local static pages and health respond; gameplay endpoints return `503` with stable machine code and last successful observation metadata, never fabricated zeroes.
- one server failing: its circuit opens independently; other servers remain healthy.
- schema mismatch: only capabilities requiring missing columns/tables fail; readiness reports the capability name without schema secrets.
- slow upstream: deadline cancellation, one limited retry, stale-if-error within a documented maximum (live 10 s, history 5 min, rankings 30 min).

`fresh`, `stale` and `unavailable` are explicit states. A stale response retains original `observed_at`. Partial player/live-stat data never silently replaces canonical log-derived totals.

## 19. Target deployment

The single HLL image contains backend code and frontend assets. One unprivileged process binds the public port and serves `/api/*` JSON plus static routes/assets. It has a read-only root filesystem, temporary memory-backed scratch if required, no named volume, no Docker socket, no scheduler and no worker command. Liveness checks local event-loop/process health; readiness checks configuration and capability-probe state without requiring every upstream call to succeed at every instant.

External network policy allows only the configured CRCON API and PostgreSQL endpoints (and direct RCON only when the optional adapter is explicitly enabled). Deployment must support secret injection, graceful connection draining and rollback to the legacy stack during migration.

## 20. Performance/resource expectations

Structurally, HLL always-on services fall from three core/up to six advanced services to one; HLL persistent volumes fall from two to zero; HLL workers/schedulers fall from up to three workers plus a scheduler path to zero. This removes local PostgreSQL memory/disk/backup cost, polling loops, materialization CPU and snapshot I/O. These are architectural expectations, not measured savings.

The main new risk is load transferred to CRCON. Coalescing converts all clients polling a live server into at most one upstream refresh per TTL. Bounded/keyset SQL, strict limits, pool caps and circuit breakers prevent expensive fan-out. Load and latency budgets must be measured against a local/sanitized CRCON fixture before production handoff.

## 21. Compatibility/versioning strategy

Keep existing endpoint paths and JSON fields during the strangler migration. New fields (`match_id`, `version`, freshness/source metadata) are additive. The snapshot endpoint starts as an additive contract; compatibility endpoints serialize from the same domain object. Query defaults and error shapes remain stable.

Pin a `CRCON_CONTRACT_REVISION` to the inspected model/API capability set, but probe capabilities rather than assuming the Git SHA deployed remotely. Contract fixtures cover accepted older/newer payload variants. Breaking HLL changes require `/api/v2` or an explicit deprecation window; CRCON schema mismatch never leaks as a changed public shape.

## 22. Testing strategy

- adapter unit tests from pinned, sanitized API/DB fixtures, including null/unknown fields;
- schema-contract tests against a disposable local CRCON PostgreSQL fixture, including indexes/constraints and read-only enforcement;
- current-match coherence tests for transition, delayed map row, cursor reset, duplicate timestamps and issue-#1186 disagreement;
- ranking SQL tests for time boundaries, server isolation, pagination, deterministic ties and query budgets;
- compatibility golden tests comparing legacy and new HLL JSON contracts;
- frontend tests proving one snapshot stream and no duplicate history request;
- cache/circuit tests for coalescing, eviction, stale-if-error and per-server isolation;
- deployment smoke tests for static routes, API, secret redaction, read-only filesystem and zero HLL volumes/workers.

No integration tests were run for TASK-289 because it changes documentation and task lifecycle only.

## 23. Security constraints

Never grant HLL write privileges to CRCON, embed authenticated URLs in frontend code, log DSNs/tokens/raw player logs, or expose a generic SQL/query proxy. Enforce configured server allowlists, metric/view allowlists, pagination ceilings, input length limits, output minimization, CORS/same-origin policy and request rate limits. Use TLS for API and database transport where supported, validate certificates, rotate secrets outside images and separate health detail visible to operators from public status.

## 24. Open questions

1. Which CRCON API authentication/permission grants are available for scoreboard, player and log endpoints in the eventual deployment?
2. What CRCON schema revision is deployed, and do its actual columns/indexes match the pinned upstream models?
3. Is `server_number` sufficient and stable as the discriminator across all required tables and multiple configured HLL servers?
4. How quickly do `map_history` and `log_lines` reflect live transitions, and what is the observed maximum lag?
5. Do live combat/offense/defense/support scores from the API remain match-scoped across reconnects?
6. Does CRCON issue #1186 affect only `get_live_game_stats` kills or other fields required by HLL?
7. Are queue counts available in the verified public-info contract in the deployed revision? If not, omit or explicitly degrade rather than infer.
8. What retention, backup or legal decision is required before deleting HLL volumes after rollback expiry?
9. Are monthly MVP, event/duel views and paused Elo/MMR valuable enough to retain or redesign?
10. What measured rate, latency and connection limits can the CRCON owner support?
