# CRCON 12.0.1 contract verification

## Decision

The seven prioritized HTTP endpoints are supported for HLL on CRCON 12.0.1.
Server-list and current-match REST transport have real HLL runtime evidence;
current-match parity remains `INSUFFICIENT_EVIDENCE` by explicit product-owner
acceptance and is not a prerequisite for local development. Historical
list/detail have real upstream endpoint evidence but not a full application
service run with canonical local ServerTargets. The authenticated Log Stream,
player search and deployed PostgreSQL read paths remain unverified because the
required authorized local configuration is absent. HLLV remains unverified.

TASK-307 performed no CRCON, RCON, PostgreSQL, Redis, service or deployment
mutation. It used existing sanitized evidence, local fixtures/tests and a local
HTTP fail-closed smoke. No real identity was retained.

## TASK-307 runtime-readiness evidence

### Canonical configuration availability

On 2026-08-23 the current process had no non-empty value for
`HLL_SERVER_TARGETS`, `HLL_CRCON_CURRENT_MATCH_BINDINGS`,
`HLL_CRCON_LOG_STREAM_TOKENS` or `HLL_CRCON_DATABASE_URL`. The four public
source selectors were also absent and therefore retained their safe `legacy`
defaults outside the explicit smoke process. Only variable presence was
inspected; no deployment file or alternate credential source was searched.

Consequences:

- no new external REST request was eligible under a configured ServerTarget;
- no authenticated `get_players_history` or `ws/logs` request was eligible;
- no PostgreSQL connection, `SHOW`, schema query or `EXPLAIN` was eligible;
- HLLV had no authorized target and remains entirely `UNVERIFIED`.

### Runtime capability matrix

`CONTRACT_VERIFIED` means the application DTO/service contract is covered by
the pinned v12.0.1 source/fixtures. It is deliberately separate from a real
full-stack runtime result.

| Game | Capability | Implemented | Contract verified | Runtime verified | Auth required | Blocker |
| --- | --- | --- | --- | --- | --- | --- |
| HLL | `server_list` | YES | YES | VERIFIED (TASK-298 real HLL) | NO | none for the reader |
| HLL | `current_match_summary` | YES | YES | VERIFIED transport; parity status retained separately | NO | none for local cutover; parity is `INSUFFICIENT_EVIDENCE`, not a blocker |
| HLL | `current_match_players` | YES | YES | VERIFIED transport; parity status retained separately | NO | same as summary |
| HLL | `current_match_stats` | YES | YES | VERIFIED transport; typed K/D/TK post-fix probe | NO | same as summary |
| HLL | `current_match_killfeed` | YES | YES | CONFIGURATION_REQUIRED | Bearer + `api.can_view_structured_logs` | token and enabled upstream Log Stream absent |
| HLL | `historical_match_list` | YES | YES | UNVERIFIED full application chain | NO on verified targets | canonical ServerTarget/binding absent; upstream endpoint itself was verified |
| HLL | `historical_match_detail` | YES | YES | UNVERIFIED full application chain | NO on verified targets | canonical ServerTarget/binding absent; upstream endpoint itself was verified |
| HLL | `player_search` | YES | YES | AUTH_UNAVAILABLE | Bearer + `api.can_view_player_history` | authorized aligned binding absent |
| HLL | `server_summary` | YES | YES | AUTH_UNAVAILABLE | SELECT-only PostgreSQL role | authorized DSN, target scope and deployed schema absent |
| HLL | `rankings` | YES | YES | AUTH_UNAVAILABLE | SELECT-only PostgreSQL role | same database evidence gap |
| HLL | `player_aggregate_profile` | YES | YES | AUTH_UNAVAILABLE | SELECT-only PostgreSQL role | same database evidence gap |
| HLLV | every capability above | YES where shared implementation applies | NO real HLLV contract | UNVERIFIED | capability-dependent | no real authorized HLLV target or runtime evidence |

### Local complete-stack fail-closed smoke

A temporary backend was started on loopback with all four selectors explicitly
set to `crcon` and with no target, token or DSN configured. No global default
was changed. Sanitized results were:

| Route family | Result | Legacy fallback |
| --- | --- | --- |
| `/api/servers` | HTTP 200 compatibility envelope, zero items, CRCON selected | `false` |
| current-match snapshot | HTTP 503 explicit CRCON unavailable error | none |
| historical recent list | HTTP 200, `found=false`, degraded reason `historical-target-not-configured` | `false` |
| historical detail | HTTP 200, `found=false`, explicit `historical-target-not-configured` reason | `false` |
| player search | HTTP 200, `UNAVAILABLE`, zero items, no enabled CRCON player-history target | none |
| ranking | HTTP 200, `UNVERIFIED_SCHEMA`, `server-target-not-configured` | `false` |
| server summary | HTTP 200 compatibility envelope with `UNVERIFIED_SCHEMA` | none |
| player profile | HTTP 200, `UNVERIFIED_SCHEMA`, `server-target-not-configured` | none |

This proves selector isolation and explicit non-success states, not upstream
runtime availability. No legacy reader was invoked to turn a CRCON failure into
a success.

### PostgreSQL runtime, schema and query plans

`CRCON_DB_SCHEMA_SOURCE=VERIFIED_12_0_1` remains supported by the pinned models.
`CRCON_DB_DEPLOYED_SCHEMA=UNVERIFIED` and `CRCON_DB_RUNTIME=AUTH_UNAVAILABLE`.
Without an explicitly authorized SELECT-only DSN, TASK-307 did not execute
`SHOW transaction_read_only`, role/privilege metadata, schema metadata,
aggregate data, `map_history.game` queries or `EXPLAIN`.

The following distinctions therefore remain mandatory:

| Concern | Source/code evidence | Deployed runtime evidence |
| --- | --- | --- |
| role is SELECT-only | deployment requirement documented | UNVERIFIED |
| transaction is read-only | repository executes `BEGIN READ ONLY` then `SHOW transaction_read_only` | UNVERIFIED |
| tables, columns, types and nullability | verified against pinned v12.0.1 models | UNVERIFIED |
| indexes, FKs and unique constraints | verified against pinned v12.0.1 models | UNVERIFIED |
| `player_stats.map_id -> map_history.id` | VERIFIED_SOURCE | UNVERIFIED_DEPLOYED |
| unique player+map relation | VERIFIED_SOURCE | UNVERIFIED_DEPLOYED |
| `map_history.server_number` and integer `game` | VERIFIED_SOURCE (`1=HLL`, `2=HLLV`) | UNVERIFIED_DEPLOYED_VALUES |
| opaque canonical `player_id`, nullable explicit `steam_id` | VERIFIED_SOURCE | UNVERIFIED_DEPLOYED |

No deployed query-plan classification can honestly be issued without
`EXPLAIN`. The source unique index makes exact opaque-ID lookup
`INDEX_OK_SOURCE_ONLY`; source indexes make bounded server summary, ranking and
player aggregate queries plausible, but their deployed status remains
`UNVERIFIED`, not `INDEX_OK` or `ACCEPTABLE`.

### Load-protection verification

The application safeguards are locally verified by code and focused tests:

| Safeguard | Verified local behavior |
| --- | --- |
| database pool | default 2 connections; validated range 1-8 |
| transaction safety | every repository checkout starts `BEGIN READ ONLY` and verifies read-only state |
| timeouts | default connect 5s, statement 5000ms, lock 1000ms |
| public bounds | route limit 1-100; page 1-1000; player search 1-100 |
| caches | server list 2s; current match 1.5s; history list 30s/detail 3600s; aggregates bounded 60s/300s TTL |
| load behavior | no load test, full-table export or stress test performed |

### Final TASK-307 status matrix

| Status | Decision |
| --- | --- |
| `CRCON_REST_RUNTIME_HLL` | `PARTIAL` |
| `CRCON_LOG_STREAM_RUNTIME_HLL` | `CONFIGURATION_REQUIRED` |
| `CRCON_DB_SCHEMA_SOURCE` | `VERIFIED_12_0_1` |
| `CRCON_DB_DEPLOYED_SCHEMA` | `UNVERIFIED` |
| `CRCON_DB_RUNTIME` | `AUTH_UNAVAILABLE` |
| `SERVER_SUMMARY_RUNTIME` | `UNVERIFIED` |
| `RANKINGS_RUNTIME` | `UNVERIFIED` |
| `PLAYER_PROFILE_RUNTIME` | `UNVERIFIED` |
| `PLAYER_SEARCH_RUNTIME` | `AUTH_UNAVAILABLE` |
| `CURRENT_MATCH_HLL` | `INSUFFICIENT_EVIDENCE` (retained; non-blocking for local development) |
| `CURRENT_MATCH_HLLV` | `UNVERIFIED` |
| `LEGACY_WRITER_DISABLE_READINESS` | `NOT_READY` |

## Verified version and targets

| UTC timestamp | ServerTarget | Server number | Game | `get_version` |
| --- | --- | ---: | --- | --- |
| 2026-08-21T12:47:03.9258216Z | `comunidad-hispana-01` | 1 | `hll` | `v12.0.1` |
| 2026-08-21T12:47:04.4742245Z | `comunidad-hispana-02` | 2 | `hll` | `v12.0.1` |

The origins are the public trusted origins already present in
`backend/app/scoreboard_origins.py`. No credential, token, cookie, IP or
private URL was recorded.

The official source reference is tag `v12.0.1`, commit
`17c5880684cc419b27ef2bcca0dc439dfd623eae`.

## Endpoint matrix

| Contract | HLL | HLLV | Evidence |
| --- | --- | --- | --- |
| `get_public_info` | SUPPORTED | UNVERIFIED | HTTP 200 on both HLL targets; real nested map/config wrapper |
| `get_live_game_stats` | SUPPORTED | UNVERIFIED | HTTP 200; match-scoped stats; tagged source and autodoc agree |
| `get_live_scoreboard` | SUPPORTED | UNVERIFIED | HTTP 200; connected-player stats; one real empty result observed |
| `get_scoreboard_maps` | SUPPORTED | UNVERIFIED | HTTP 200; `page`/`limit` pagination and empty `player_stats` observed |
| `get_map_scoreboard` | SUPPORTED | UNVERIFIED | HTTP 200 using an ID from the list; full match/player detail observed |
| `get_map_history` | SUPPORTED | UNVERIFIED | HTTP 200; direct list wrapper; Redis recent-history semantics verified in tagged source |
| `get_previous_map` | SUPPORTED | UNVERIFIED | HTTP 200; object observed; `null` empty behavior verified in tagged source |

All responses used the real wrapper keys `result`, `command`, `arguments`,
`failed`, `error`, `forwards_results` and `version`. No observable rate-limit
headers were returned. Both targets accepted the seven GETs without an
authentication header. This is evidence for these deployed public targets,
not a claim that every CRCON installation is anonymously accessible.

## Autodocumentation

`GET /api/get_api_documentation` returned 309 endpoint entries. For all seven
prioritized endpoints it reported:

- allowed method: `GET`;
- permissions required: empty list;
- return type: `null`;
- documented arguments: empty object.

The introspection output does not expose the query arguments that the handlers
actually consume. Tagged source plus successful GETs establish:

| Endpoint | Effective query arguments |
| --- | --- |
| `get_scoreboard_maps` | `page`, `limit`, `server_number`; limit capped at 1000 |
| `get_map_scoreboard` | required `map_id` |
| `get_map_history` | optional `pretty` |
| other prioritized endpoints | none |

The autodoc description explicitly distinguishes:

- `get_live_game_stats`: statistics for the currently playing match;
- `get_live_scoreboard`: currently connected players, reset on disconnect and
  not at match start.

The application must not substitute the connected-player scoreboard for the
complete current-match statistics.

## Observed HTTP shapes

### `get_public_info`

The game is at `result.config.game`, not at `result.game`. `current_map.map`
and `next_map.map` are structured layer objects. Current-map `start` is a Unix
timestamp, next-map `start` may be null, and `time_remaining` may be a float.
The result also contains counts, score, cap flips, match time, vote status,
public name metadata and sanitized server config metadata.

### Live endpoints

Both live results contain `snapshot_timestamp`, `refresh_interval_sec` and a
`stats` list. Real HLL observations included explicit `player_id` and
`platform`; the verified payloads did not contain top-level `steam_id` or
`eos_id`. `steaminfo.id` is an internal row identifier and is not a Steam ID.

At one observation target #01 returned one match-stat row and zero connected
rows, while target #02 returned eight rows in both. This demonstrates that the
two endpoints are not interchangeable.

### Historical list and detail

`get_scoreboard_maps?page=1&limit=2` and page 2 returned the requested page and
page size on both targets. Every listed map had `player_stats: []`. List rows
contain structured map/layer data, numeric ID, creation/start/end timestamps,
server number, result and the empty stats list. They do not contain a `game`
field.

`get_map_scoreboard` contains the complete map row plus `game_layout`,
`cap_flips`, `match_time` and player statistics. Verified player fields include
kills/deaths/teamkills, time, score dimensions, vehicle metrics, weapons,
teams, units and encounters. An encounter contains `action`, opaque
`player_id`, player name, relative `ts` and weapon. After sanitization this
endpoint is structurally sufficient for the `historico-partida` detail page.

### Recent map history

`get_map_history` returns a list directly, not `{maps: [...]}`. Its entries use
Unix timestamps and may have `end: null`. Player stats are a mapping keyed by
opaque player IDs. In the tagged 12.0.1 source `MapsHistory` is a Redis
`FixedLenList` with default `max_len=500`. It is suitable only for recent
transitions, previous-map assistance and current-match support.

Permanent history must use `get_scoreboard_maps` + `get_map_scoreboard`, or an
authorized read-only PostgreSQL repository.

## Identity semantics

| Contract | HLL | HLLV |
| --- | --- | --- |
| opaque string `player_id` | SUPPORTED | UNVERIFIED |
| explicit `platform` | SUPPORTED (`steam` and `epic` observed) | UNVERIFIED |
| explicit top-level `steam_id` in the seven endpoints | UNSUPPORTED | UNVERIFIED |
| explicit top-level `eos_id` in the seven endpoints | UNSUPPORTED | UNVERIFIED |

The tagged source confirms that the physical
`steam_id_64.steam_id_64` column is mapped as opaque `player_id`. A separate
nullable `steam_id` column exists specifically for future identity linking,
and `player_soldier.eos_id`/`platform` are separate metadata. Table or column
names never justify inferring Steam/EOS identity.

## PostgreSQL matrix

No `HLL_CRCON_DATABASE_URL` or other authorized CRCON read-only DSN was
available locally. No SQL was executed against a deployed CRCON database.

| Table/capability | Deployed columns/types/nullability | Deployed constraints/indexes | Status |
| --- | --- | --- | --- |
| `map_history` | not inspected | not inspected | UNVERIFIED |
| `player_stats` | not inspected | not inspected | UNVERIFIED |
| `player_sessions` | not inspected | not inspected | UNVERIFIED |
| `steam_id_64` | not inspected | not inspected | UNVERIFIED |
| `log_lines` | not inspected | not inspected | UNVERIFIED |

The tagged 12.0.1 SQLAlchemy models provide an expected-source reference, not
deployed-schema evidence:

- `map_history`: unique `(start,end,server_number,map_name)`; indexes on
  `start`, `end`, `server_number`, `map_name`;
- `player_stats`: unique `(playersteamid_id,map_id)`; both FKs indexed;
- `log_lines`: unique `(event_time,raw)`; event time and player FKs indexed;
- `steam_id_64.steam_id_64`: unique indexed opaque player ID;
- `player_sessions.playersteamid_id`: indexed.

The expected source columns are sufficient for `COUNT(DISTINCT ps.map_id)`,
`MAX(ps.kills)` and the requested `SUM` aggregates, scoped through
`map_history.server_number`. They remain runtime UNVERIFIED until the deployed
schema and query plan are inspected with `BEGIN READ ONLY`.

## TASK-302 aggregate schema and access-path decision

TASK-302 rechecked the pinned source at commit
`17c5880684cc419b27ef2bcca0dc439dfd623eae` before implementing SQL. This is
source-contract evidence, not a claim about a deployed database:

| Model/table | Required 12.0.1 contract | Source indexes/constraints | Local decision |
| --- | --- | --- | --- |
| `map_history` | PK `id`; finalized timestamp `end`; integer `game`; `server_number`; `map_name`; `start` | unique `(start,end,server_number,map_name)`; individual indexes on `start`, `end`, `server_number`, `map_name` | Aggregate through `player_stats.map_id`; always filter server, game and `end IS NOT NULL` |
| `player_stats` | indexed FKs `map_id`, `playersteamid_id`; kills/deaths/TK/deaths-by-TK/time and score/vehicle dimensions | unique `(playersteamid_id,map_id)`; individual indexes on both FKs | `COUNT(DISTINCT map_id)` is matches; `SUM(kills)` is total; `MAX(kills)` is record |
| `steam_id_64` | unique opaque `steam_id_64`; separate nullable `steam_id` | unique index on opaque ID | Exact opaque-ID lookup is safe; Steam link only from the separate field |
| `player_soldier` | one-to-one `playersteamid_id`; nullable `eos_id`, `platform`, `name` | unique indexed player FK | EOS/platform are explicit metadata only |
| `player_names` | player FK, name, created, last-seen | player FK indexed; **name is not indexed** | Canonical case-insensitive substring search is `PERFORMANCE_BLOCKED` |
| `player_sessions` | player FK, start/end, server metadata | player FK indexed | May describe play sessions; never used as match count |
| `player_account` | one-to-one player FK and account metadata | unique indexed player FK | Not required for the public aggregate MVP |

The game discriminator is `1=hll`, `2=hllv`. Cross-server aggregation is
explicit and permitted only when every selected target has the same game.
Cross-game reads fail closed. Timeframes filter finalized `map_history.end`
with half-open `[start,end)` bounds. Weekly begins Monday 00:00 UTC, monthly at
the first day 00:00 UTC, annual at January 1 through the following January 1,
and all-time omits only the bounds (never server/game/finalized filters).

The canonical 12.0.1 models do not provide a trigram/expression index on
`player_names.name`. TASK-303 supersedes the TASK-302 public-search decision:
the PostgreSQL fuzzy helper remains deprecated diagnostic code and has no
production caller. Public player search in CRCON mode no longer probes or
queries that index.

Runtime configuration was checked by variable name only on 2026-08-23:
`HLL_CRCON_DATABASE_URL`, `HLL_SERVER_TARGETS` and
`HLL_HISTORICAL_AGGREGATE_SOURCE` were not configured. No credential source
was searched and no real SQL was executed. Consequently deployed column/type/
nullability evidence, the SELECT-only role and real query plans remain
`UNVERIFIED_SCHEMA`; local implementation and synthetic contract tests are
complete, while real performance validation is intentionally not claimed.

### TASK-302 selectable architecture

`HLL_HISTORICAL_AGGREGATE_SOURCE=legacy|crcon` selects the aggregate family as
one coherent unit and defaults to `legacy`. CRCON mode uses a bounded read-only
connection pool and repository methods only. Every checkout executes
`BEGIN READ ONLY`, verifies `transaction_read_only=on`, applies connection,
statement and lock timeouts, rolls back, and exposes no arbitrary SQL or write
API. Deployment must additionally supply a PostgreSQL role granted `SELECT`
only, so database privileges remain an independent safety layer. Aggregate
cache keys include family, game, server numbers, timeframe and
window, metric, pagination and opaque player ID as applicable.

The migrated family is server summary, historical weekly/monthly leaderboards,
global weekly/monthly/annual rankings, exact-ID/index-gated player search and
weekly/monthly player profiles. Annual rankings are direct timeframe queries;
no annual snapshot is persisted. Historical match list/detail remains on
TASK-301 REST. MVP V1/V2 and Elo/MMR were separate derived legacy products;
TASK-309 subsequently removed those application slices. Existing stored data
was not deleted;
workers and storage remain available for rollback and unmigrated domains.

| Public aggregate surface | Local implementation | Real schema/data | Decision |
| --- | --- | --- | --- |
| Server summary | PASS | UNVERIFIED_SCHEMA | LOCAL_GO / RUNTIME_NO_GO |
| Weekly/monthly leaderboards | PASS | UNVERIFIED_SCHEMA | LOCAL_GO / RUNTIME_NO_GO |
| Global weekly/monthly/annual ranking | PASS | UNVERIFIED_SCHEMA | LOCAL_GO / RUNTIME_NO_GO |
| Exact opaque-ID search | PASS | UNVERIFIED_SCHEMA | LOCAL_GO / RUNTIME_NO_GO |
| Case-insensitive name search | Indexed path implemented | canonical index absent | PERFORMANCE_BLOCKED |
| Player profile/aggregates | PASS | UNVERIFIED_SCHEMA | LOCAL_GO / RUNTIME_NO_GO |
| HLL target scoping | Synthetic PASS | no configured target/DSN | UNVERIFIED_SCHEMA |
| HLLV target scoping | Synthetic PASS | no real HLLV evidence | UNVERIFIED_SCHEMA |

## TASK-303 authenticated player-history contract

Pinned v12.0.1 source evidence:

- handler: `rcon.api_commands.get_players_history`;
- implementation: `rcon.player_history.get_players_by_appearance`;
- permission: `api.can_view_player_history`;
- methods: GET and POST; HLL Vietnam uses GET only;
- safe arguments used: exactly one of `player_name` or `player_id`, plus
  `page`, `page_size` and `exact_name_match` for name search;
- authentication: `Authorization: Bearer <api-key>`; CRCON accepts the
  case-insensitive `BEARER` scheme and hashes the raw key before resolving its
  Django user/permissions.

The response envelope contains `total`, `players`, `page` and `page_size`.
Each upstream player row also carries moderation, watchlist, blacklist,
session and account data. The HLL Vietnam DTO deliberately discards those
fields and retains only opaque `player_id`, historical names, explicit
Steam/EOS/platform metadata and first/last-seen timestamps. Millisecond
timestamps are converted to UTC. No raw response crosses the backend boundary.

`player_id` filtering in upstream v12.0.1 is a substring `ILIKE`; therefore the
HLL Vietnam opaque-ID fallback additionally retains only literal-equality IDs.
The fallback happens only after an empty name page and does not inspect the
identifier's characters. Name search is one bounded call per selected target;
the empty-result ID fallback makes the maximum two bounded calls per target.

Credentials reuse `api_headers` in the existing per-target
`HLL_CRCON_CURRENT_MATCH_BINDINGS` server-side secret configuration. They are
matched to the canonical target slug, origin, server number and game. No token
registry, browser credential or persistence was added. HTTP 401/403 is
`AUTH_REQUIRED`; transport/shape failure is `UNAVAILABLE`; successful HLL is
`SUPPORTED`; HLLV is `UNVERIFIED_HLLV` and is not queried.

No `HLL_SERVER_TARGETS`, `HLL_CRCON_CURRENT_MATCH_BINDINGS`,
`HLL_CRCON_DATABASE_URL` or aggregate selector was configured in the local
process or `.env.example` on 2026-08-23. The code contract is locally verified,
but deployed authenticated search remains runtime `AUTH_REQUIRED`/
`UNVERIFIED`. `PLAYER_NAME_SEARCH_CRCON_DB=NOT_REQUIRED`.

## Log discriminator finding

The deployed values of `log_lines.server` and `log_lines.game` were not
available. Their mapping to `ServerTarget` remains UNVERIFIED.

The tagged source does prove that `log_lines.server` is text while
`log_lines.game` is an integer enum (`1=hll`, `2=hllv`). TASK-293's string
filter using `"hll"`/`"hllv"` is therefore UNSUPPORTED for the 12.0.1 source
contract. The repository now fails closed unless both an explicit text
`log_server` and integer `log_game` discriminator are configured. No mapping is
derived from `server_number` or `ServerTarget.game`.

## Differences from TASK-293 fixtures

- all endpoint contracts changed from global UNVERIFIED to SUPPORTED for HLL
  and remained UNVERIFIED for HLLV;
- real CRCON wrapper metadata was added;
- `public_info.game` moved to `public_info.config.game`;
- nested map/layer objects replaced invented flat map strings;
- Unix and ISO timestamp variants are both parsed;
- `live_scoreboard` has the same snapshot envelope as live game stats and can
  legitimately have an empty stats list;
- `scoreboard_maps.player_stats` is confirmed empty and no invented `game`
  field remains;
- `map_scoreboard` now models weapons and encounters;
- `map_history` is a direct bounded recent-history list, not a permanent map
  page object;
- `previous_map` is a direct object or null;
- invented top-level `steam_id`/`eos_id` fields were removed from verified API
  fixtures;
- PostgreSQL fixture metadata remains explicitly unverified.

## TASK-295 server-list and shadow architecture

`HLL_SERVER_LIST_SOURCE=legacy|crcon` is the single server-list cutover. It is
separate from `HLL_BACKEND_LIVE_DATA_SOURCE=a2s|rcon`, which continues to choose
the transport inside the legacy collector. CRCON mode iterates enabled
`ServerTarget` entries and calls only typed `get_public_info`. It serializes
the DTO into the existing server-card envelope, uses a two-second process-local
TTL, coalesces concurrent refreshes, and serves only explicit CRCON last-good
state or `unavailable` after failures. It never silently calls legacy.

`HLL_CURRENT_MATCH_SOURCE=legacy|crcon|shadow` remains the one current-match
selector. The CRCON and shadow candidates are API-only:
`get_public_info + get_live_game_stats`. Shadow returns the unmodified legacy
summary/player/kill payloads, keeps the candidate and the latest diagnostic in
memory, and emits only bounded counts/deltas at debug level. Raw opaque IDs and
names are not logged or included in reports; player keys are short SHA-256
diagnostic aliases.

The parity report compares match identity when available, map/layer, mode,
scores, player/max counts, start/time remaining/status, player presence by
opaque ID, identity-adjacent fields, and kills/deaths/teamkills/combat/offense/
defense/support. Differences are classified as `MATCH`, `PLAYER_SET`, `STAT`,
`TIMING`, `EXPECTED_SOURCE_DIFFERENCE`, or `UNKNOWN`. Kill differences include
absolute and meaningful percentage deltas and never fail a public request.

The local final-match verifier retains the last live CRCON observation per
server in memory, selects the corresponding row from `get_scoreboard_maps`,
loads `get_map_scoreboard`, and compares the seven stat dimensions with a
configurable five-minute start-time tolerance. No new table, file history,
ledger, worker, or public diagnostic route exists.

## Accuracy evidence correction

CRCON issue `#1186` is not evidence about live kill statistics and is not used.
Issue `#1170` originally reported inaccurate `get_live_game_stats` kills, but
its author later retracted that diagnosis and associated the observed loss with
historical/AdminLog collection; the issue is closed. Consequently this project
neither presumes live kills incorrect nor promotes them as canonical without
measurement. TASK-295 supplies the shadow and live-to-final measurements.

## GO / NO-GO after TASK-295 local validation

- `/api/servers` with `HLL_SERVER_LIST_SOURCE=crcon`: **GO for the two verified
  HLL targets once their enabled `HLL_SERVER_TARGETS` configuration is present**.
  HLLV DTO behavior is synthetically covered but HLLV must remain disabled
  until a real contract verification exists.
- `/api/current-match` with `HLL_CURRENT_MATCH_SOURCE=crcon`: **SHADOW READY**.
  The API-only direct mode and local fixture comparisons work, but this local
  task did not observe a sufficiently long real match through live polling and
  final closure. Endpoint availability alone is not parity evidence.

TASK-296 should run shadow mode over complete real HLL matches on both targets,
collect only sanitized aggregate diagnostics, execute final-scoreboard
comparisons, define acceptance thresholds (especially for kills and player-set
churn), and then issue the direct-mode GO/NO-GO. It should separately verify
HLLV before enabling an HLLV target. PostgreSQL read-only verification remains
required only for later history/ranking/stats migration, not for this decision.
