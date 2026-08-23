# HLL Vietnam code structure

Audit date: 2026-08-23. TASK-304 established the primary packages and TASK-305
split the API payload facade by public domain. Public URLs, payload contracts,
source selectors and runtime behavior remain unchanged.

## Dependency direction

```text
frontend -> api -> services -> domain
                    |    |
                    |    +-> crcon (external integration)
                    +------> rollback/product modules only behind explicit selectors

workers/tools -> services, storage and integrations
```

`domain/` must not import configuration, HTTP clients, database drivers or
legacy storage. Services coordinate use cases and may depend on domain models
and integration interfaces. `crcon/` owns CRCON 12.0.1 transport, DTOs,
capabilities and read-only repositories. API modules validate requests and
preserve the existing public JSON contract.

## Audited pre-refactor tree

Before TASK-304, `backend/app` contained 61 Python files at its root, plus 12
files in `crcon/`, two in `domain/` and three in `providers/`. API, services,
workers, storage, tools and product features were therefore visually mixed.

The other repository areas are:

- `backend/tests`: 27 Python test modules plus CRCON 12.0.1 fixtures; retained
  flat because the suite is still small and filenames are discoverable.
- `frontend`: six page HTML files, 11 page/runtime JavaScript files and one
  Node snapshot test. The page scripts are flat but coherent enough to defer a
  high-churn move.
- `deploy`: root Compose plus JTA and Portainer variants; all dynamic
  `python -m` entrypoints are part of the reachability audit.
- `docs`: architecture, runbooks and migration evidence; operational command
  references count as live evidence, not as dead prose.
- `ai/tasks`: historical task evidence plus pending/in-progress work; task-only
  references do not by themselves make code live, but they explain rollback
  and product decisions.

## Complete backend module classification before moves

Multiple responsibilities are recorded where a module genuinely mixes them.
That is evidence for later extraction, not permission to relabel it as dead.

| Module | Classification | TASK-304 disposition |
| --- | --- | --- |
| `__init__.py` | API / INFRASTRUCTURE | bootstrap retained |
| `main.py`, `routes.py`, `payloads.py` | API | move dispatcher/facade to `api/`; extract pure serializers |
| `domain/identity.py` | DOMAIN | retained |
| `current_match.py` | SERVICE / DOMAIN | move to `services/current_match.py` |
| `current_match_shadow.py` | SERVICE / TOOL | move beside current-match service; validation remains available |
| `history_service.py` | SERVICE | move to `services/history.py` |
| `server_service.py` | SERVICE | move to `services/servers.py` |
| `crcon/aggregate_service.py` | SERVICE | move to `services/historical_aggregates.py` |
| `crcon/player_search_service.py` | SERVICE | move to `services/player_search.py` |
| `crcon/api.py`, `crcon/dto.py`, `crcon/log_stream.py` | CRCON_INTEGRATION | retain cohesive package |
| `crcon/capabilities.py`, `crcon/cache.py`, `crcon/models.py` | CRCON_INTEGRATION / INFRASTRUCTURE | retain cohesive package |
| `crcon/repository.py`, `crcon/postgres_repository.py` | CRCON_INTEGRATION / STORAGE | retain; PostgreSQL is read-only |
| `crcon/__init__.py` | CRCON_INTEGRATION | retain public integration exports |
| `crcon/database.py` | CRCON_INTEGRATION | compatibility-only module; removed after reference proof |
| `config.py`, `writer_lock.py`, `sqlite_utils.py` | INFRASTRUCTURE | retain |
| `server_targets.py`, `scoreboard_origins.py` | DOMAIN / INFRASTRUCTURE | retained pending cleaner config boundary |
| `normalizers.py`, `snapshots.py` | DOMAIN / LEGACY | rollback snapshot model; retain |
| `a2s_client.py`, `collector.py`, `scheduler.py`, `data_sources.py` | LEGACY / WORKER | active snapshot-history and rollback paths; retain |
| `storage.py`, `postgres_display_storage.py` | STORAGE / LEGACY | active snapshot-history and rollback paths; retain |
| `historical_models.py` | DOMAIN / LEGACY | retain rollback model |
| `historical_storage.py`, `historical_snapshot_storage.py` | STORAGE / LEGACY | rollback plus product dependencies; retain |
| `historical_ingestion.py`, `historical_runner.py` | WORKER / LEGACY | dynamic entrypoints; retain |
| `historical_snapshots.py` | SERVICE / LEGACY / PRODUCT_FEATURE | mixed rollback/MVP/player-event builder; retain |
| `database_maintenance.py` | INFRASTRUCTURE / TOOL | dynamic entrypoint and runner dependency; retain |
| `postgres_rcon_storage.py`, `rcon_admin_log_storage.py`, `rcon_historical_storage.py` | STORAGE / LEGACY | active rollback writers; retain |
| `rcon_client.py`, `rcon_admin_log_parser.py`, `rcon_scoreboard_correlation.py`, `rcon_historical_read_model.py` | LEGACY | rollback implementation; retain |
| `rcon_admin_log_ingestion.py`, `rcon_historical_worker.py`, `rcon_current_match_worker.py` | WORKER / LEGACY | Compose/dynamic entrypoints; retain |
| `rcon_admin_log_materialization.py` | SERVICE / LEGACY | rollback materializer; retain |
| `rcon_historical_backfill.py`, `rcon_historical_backfill_operational.py`, `scoreboard_candidate_backfill.py` | TOOL / LEGACY | documented operational entrypoints; retain |
| `rcon_historical_leaderboards.py`, `rcon_historical_player_stats.py`, `rcon_annual_rankings.py` | SERVICE / LEGACY | rollback read models and jobs; retain |
| `rcon_scoreboard_relink.py`, `scoreboard_correlation_diagnostics.py` | TOOL / LEGACY | move to `tools/`; update documented entrypoints |
| `observe_current_match_parity.py`, `storage_diagnostics.py`, `sqlite_to_postgres_migration.py` | TOOL | parity observer retained in place; move other commands to `tools/` |
| `elo_mmr_engine.py`, `elo_mmr_models.py`, `elo_mmr_storage.py` | PRODUCT_FEATURE / STORAGE | product decision required; do not move to legacy |
| `monthly_mvp.py`, `monthly_mvp_v2.py` | PRODUCT_FEATURE | active routes; product decision required |
| `player_event_models.py`, `player_event_source.py`, `player_event_aggregates.py` | PRODUCT_FEATURE / DOMAIN | product decision required |
| `player_event_storage.py` | PRODUCT_FEATURE / STORAGE | product decision required |
| `player_event_worker.py` | PRODUCT_FEATURE / WORKER | dynamic entrypoint; product decision required |
| `providers/player_event_source_provider.py` | PRODUCT_FEATURE / SERVICE | product decision required |
| `providers/public_scoreboard_provider.py`, `providers/rcon_provider.py` | LEGACY / SERVICE | rollback provider adapters; retain |
| `player_external_profiles.py` | SERVICE | retained shared compatibility mapper |

No module remains `UNKNOWN` after the static, route, frontend, Compose,
documentation and dynamic-entrypoint audit. A known classification does not
imply deletion safety.

## Implemented tree after TASK-305

```text
backend/app/
  main.py                 # HTTP lifecycle
  config.py
  api/
    routes.py             # unchanged URL dispatcher
    payloads/
      __init__.py         # stable compatibility exports only
      common.py           # displayed-snapshot/fallback metadata
      current_match.py    # CRCON/legacy/shadow current-match contracts
      history.py          # recent match/detail/summary contracts
      players.py          # player search/profile contracts
      product_features.py # MVP/player-event/Elo contracts pending decisions
      rankings.py         # ranking/leaderboard/aggregate contracts
      servers.py          # CRCON/legacy server-card and snapshot contracts
      static.py           # health/community/trailer/Discord/error contracts
    serializers.py        # pure shared JSON compatibility mapping
  domain/
    identity.py
  services/
    current_match.py
    current_match_shadow.py
    historical_aggregates.py
    history.py
    player_search.py
    servers.py
  crcon/
    api.py
    cache.py
    capabilities.py
    dto.py
    log_stream.py
    models.py
    postgres_repository.py
    repository.py
  tools/
    scoreboard_correlation_diagnostics.py
    scoreboard_relink.py
    sqlite_to_postgres_migration.py
    storage_diagnostics.py
  providers/
  legacy/product/storage/worker modules (still flat; see rationale below)
```

The refactor intentionally stops before mechanically moving every RCON,
historical, storage and worker module into `legacy/`. The TASK-303 ledger shows
that those modules are interconnected with active snapshot-history routes,
rollback selectors and undecided product features. A mass rename would make
the tree look cleaner while obscuring those mixed ownership boundaries.

## API and frontend contracts

`api/routes.py` remains a URL dispatcher with no SQL, CRCON parsing or
historical reconstruction. All existing URLs remain unchanged. Routes now
import canonical builders from the domain payload modules. Existing consumers
may continue to use `from app.api.payloads import ...` through the 98-line
`payloads/__init__.py` compatibility surface.

TASK-305 replaced the 2,904-line `api/payloads.py` monolith with domain modules.
`current_match.py` depends one-way on the legacy server-card helper;
`history.py` depends one-way on the ranking server-summary contract; and both
history/ranking/product modules share only the focused `common.py` snapshot
metadata helpers. No reverse dependency or circular import is present.

Legacy fallback helpers remain private and visibly named in the public domain
that selects them. A separate `legacy.py` was rejected because it would split
each selector from its paired public contract and introduce avoidable cross-
module coupling. Undecided MVP, player-event and Elo routes are isolated in
`product_features.py` and remain `PRODUCT_DECISION_REQUIRED`.

`api/serializers.py` remains a cohesive 107-line module for pure timestamps,
opaque server IDs, ranking values and source display. Splitting it would create
trivial files without improving dependency direction. Player IDs are passed
through as opaque strings in all extracted modules.

The frontend already has one script per page plus small shared current-match
and map helpers. A future low-risk grouping could use `pages/` and `utils/`, but
moving all scripts would change every HTML import for little backend benefit.

## Adding code

- Add pure identity/value rules to `domain/` only when they have no runtime or
  persistence dependency.
- Add application orchestration to `services/`.
- Add CRCON endpoint/DTO/repository behavior to `crcon/`; never modify CRCON
  itself from this repository.
- Add URL parsing and request validation to `api/routes.py`; add public contract
  assembly to the owning `api/payloads/<domain>.py` module; add only pure shared
  compatibility mapping to `api/serializers.py`; keep use-case logic in
  `services/` and CRCON transport/schema behavior in `crcon/`.
- Keep one-off diagnostics as explicit documented module entrypoints.
- Do not add new application-owned persistence for CRCON-first readers.
- Do not place MVP, player-events or Elo/MMR under `legacy/` until a product
  decision defines their final source and state requirements.

## Remaining dependency violations and follow-ups

- `services/current_match.py` still contains domain dataclasses next to the
  use-case service. They do not import infrastructure themselves, but a future
  extraction to `domain/current_match.py` should be behavior-neutral.
- `services/history.py` uses the legacy `ALL_SERVERS_SLUG` constant. TASK-304
  removes that reverse dependency by making the canonical scope local/shared.
- Payload modules still invoke legacy storage on explicit rollback paths.
  CRCON-first execution remains selector-gated; isolating the underlying mixed
  storage/workers is deferred until rollback and product decisions permit it.
- `server_targets.py` combines target value objects with environment-backed
  loading. Splitting it is deferred to avoid a one-file micro-package and broad
  configuration churn.

## Dead-code evidence and classifications

TASK-304 checked static imports, public exports, route registration, frontend
requests, scheduler/worker calls, every Compose variant, scripts, documented
`python -m` commands and tests before deletion.

| Candidate | Classification | Evidence / action |
| --- | --- | --- |
| `crcon/database.py` | `SAFE_DELETE` | temporary re-export only; all consumers now import `repository.py` or `postgres_repository.py`; no route, frontend, worker, Compose or documented command; deleted |
| `CrconDatabase` alias | `SAFE_DELETE` | test-only compatibility name after direct imports were updated; no production or operational reference; deleted |
| PostgreSQL `PLAYER_NAME_SEARCH_SQL`, name-index probe, exact-ID wrapper and related escape helper | `SAFE_DELETE` | removed from `CrconReadRepository` in TASK-303; no production caller, route, frontend, rollback path, worker, Compose or docs; REST `get_players_history` is canonical; deleted with tests that only asserted the obsolete surface |
| Three private payload helpers (`_leaderboard_snapshot_items_need_playtime_enrichment`, `_load_runtime_leaderboard_items`, `_is_snapshot_stale`) | `SAFE_DELETE` | no production, route, frontend, worker, dynamic-entrypoint or documentation caller after extraction; the runtime leaderboard loader was referenced only by a test asserting it was not called; removed in TASK-305 |
| A2S/collector/snapshot stack | `LEGACY_ROLLBACK_REQUIRED` | `/api/servers` legacy selector and explicit latest/history routes still read it |
| historical/RCON materializers and stores | `MIGRATED_BUT_ROLLBACK_ONLY` plus mixed product dependencies | immediate selectors and active derived features still require them; retained |
| parity observer | `DYNAMIC_ENTRYPOINT` | bounded documented tool retained at `app.observe_current_match_parity`; no waiting or behavioral change performed |
| MVP, player-event and Elo/MMR backend modules | `PRODUCT_DECISION_REQUIRED` | active routes and application state exist; no approved final CRCON source; retained |
| unused MVP/Elo renderer helpers and CSS in `historico.js`/`historico.css` | `PRODUCT_DECISION_REQUIRED` | no active fetch/DOM surface found, but paired backend feature disposition is undecided; retained |
| all other no-incoming-import CLI modules | `DYNAMIC_ENTRYPOINT` or `UNKNOWN` only after command review | documented/Compose commands were found; none deleted |

## Configuration audit

All `HLL_*` names in application code, Compose/deploy and current runbooks were
cross-checked. No application variable is proven `UNUSED`.

- `CURRENT`: HTTP bind/CORS, `HLL_SERVER_TARGETS`, CRCON API/database/binding/log
  settings, and the four public source selectors.
- `LEGACY_ROLLBACK`: A2S/live-source, SQLite/storage/lock, classic historical
  ingestion, RCON capture/AdminLog, ranking snapshot, maintenance and retention
  settings.
- `PRODUCT_DECISION_REQUIRED`: player-event, Elo/MMR and related public refresh
  cadence settings.
- `DEPRECATED`: JTA Compose accepts
  `HLL_BACKEND_RCON_HISTORICAL_INTERVAL_SECONDS` only as an outer substitution
  alias for canonical `HLL_RCON_HISTORICAL_CAPTURE_INTERVAL_SECONDS`. Do not
  remove it until deployed environment values are checked.
- `UNKNOWN`: none after repository reference tracing. `HLL_PUBLIC` was only a
  search-token false positive, not an environment variable.

No deployment variable was removed in this task.

## Duplication and snapshot-history audit

- CRCON PostgreSQL server/game scope continues to use
  `crcon.repository.resolve_server_scope`; REST target selection is distinct
  because it resolves configured API bindings, so the two were not conflated.
- CRCON auth remains centralized in configuration/bindings. Player IDs remain
  opaque strings; no format inference was introduced.
- Timeframe and pagination checks exist at API and service boundaries for
  different error contracts; no equivalence-safe deletion was found.
- The obsolete database compatibility alias and player-search SQL were the only
  proven duplicate surfaces removed.
- The frontend does not call `/api/servers/latest`, `/api/servers/history` or
  per-server snapshot history, but those public routes remain active. The
  current `/api/servers` legacy selector still reads server snapshots.
- `historico.js` calls the historical `snapshots/*` URLs. In CRCON aggregate or
  match mode the backend bypasses application snapshot storage for migrated
  families; legacy mode still reads displayed/filesystem snapshots. Writers
  therefore remain `NOT_READY` for shutdown.
