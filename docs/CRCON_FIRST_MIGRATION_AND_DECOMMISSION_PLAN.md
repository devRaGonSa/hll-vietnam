# CRCON-first migration and decommission plan

## 1. Migration principles

Use an endpoint-by-endpoint strangler. For each capability: add a CRCON adapter and pinned local fixtures; implement the new domain mapping behind a switch; compare legacy/new results; switch one endpoint; validate its actual frontend consumer; retain rollback; and delete legacy paths only after all dependants have accepted parity.

CRCON is the gameplay system of record. HLL owns public contracts and presentation logic, not ingestion or gameplay persistence. Migration code reads CRCON only, uses bounded memory caches, exposes freshness/degradation, and never adds another database, Redis, queue, watermark or materializer. No source is chosen solely because it exists: API accuracy, database semantics and optional direct-RCON need fixture evidence.

This plan is based on HLL commit `9a86fbffb99d8919e1232ae513319426acd6d708` and official CRCON `master` commit `4cf1e7e2fa691d849eaf85abb7065010e13f28e4`, inspected 2026-08-14.

## 2. Endpoint-by-endpoint migration matrix

All endpoints are GET. Compatibility means the existing HLL response stays stable while its implementation changes.

| Endpoint(s) | Target | Migration/acceptance gate | Final disposition |
| --- | --- | --- | --- |
| `/health` | local process + CRCON capability state | stable current status plus additive dependency fields; no secrets | KEEP/REWRITE |
| `/api/community`, `/api/trailer`, `/api/discord` | local validated config | golden payload parity | KEEP |
| `/api/servers`, `/api/servers/latest` | CRCON public info | server cards, map/count/availability parity; cache/coalescing test | REWRITE; consider deprecating unused latest |
| `/api/servers/history`, `/api/servers/{server_id}/history` | CRCON `server_counts` | time order, server isolation, limit and gap semantics | REWRITE |
| `/api/current-match` | coherent CRCON snapshot projection | map/score/time/count transition fixtures and freshness flags | REWRITE compatibility view |
| `/api/current-match/kills` | bounded CRCON `log_lines` projection | cursor, ordering, teamkill/weapon, transition and duplicate-time tests | REWRITE compatibility view |
| `/api/current-match/players` | coherent snapshot API/live state + log totals | names/team/scores and K/D/TK disagreement fixtures | REWRITE compatibility view |
| new `/api/current-match/snapshot` | combined domain snapshot | one response/version for summary, players and feed; load/coherence budget | ADD canonical live contract |
| `/api/stats/players/search` | CRCON identity/name tables | exact/prefix/name-history fixtures, privacy and limit checks | REWRITE |
| `/api/stats/players/{player_id}` | CRCON profile/session API + bounded DB stats | weekly/monthly boundaries and recent matches parity | REWRITE |
| `/api/stats/rankings/annual` | common CRCON ranking query | annual kills parity and deterministic ties | KEEP as alias/REWRITE |
| `/api/ranking` | bounded CRCON maps/stats aggregate | every public metric, period/server boundaries and query plan | REWRITE |
| `/api/historical/weekly-top-kills` | common ranking query | legacy response golden; announce alias | DEPRECATE |
| `/api/historical/leaderboard` | common ranking query | weekly/monthly supported metrics | DEPRECATE |
| `/api/historical/weekly-leaderboard` | common ranking query | response golden | DEPRECATE |
| `/api/historical/monthly-leaderboard` | common ranking query | response golden | DEPRECATE |
| `/api/historical/monthly-mvp` | no automatic replacement | product/formula decision | DEPRECATE/REMOVE |
| `/api/historical/monthly-mvp-v2` | bounded CRCON stats if retained | approved formula and fixture parity | DEFER |
| `/api/historical/player-events` | bounded CRCON logs | weapon/teamkill/duel semantics and privacy acceptance | REWRITE or REMOVE per view |
| `/api/historical/snapshots/leaderboard` | same common ranking service | `historico.js` validation | REWRITE compatibility alias |
| `/api/historical/snapshots/monthly-leaderboard` | common ranking service | no remaining consumer | DEPRECATE |
| `/api/historical/snapshots/monthly-mvp` | follow MVP decision | no remaining consumer | DEPRECATE/REMOVE |
| `/api/historical/snapshots/monthly-mvp-v2` | follow MVP-v2 decision | approved product need | DEFER |
| `/api/historical/snapshots/player-events` | same event query if retained | no remaining consumer | DEPRECATE |
| `/api/historical/snapshots/weekly-leaderboard` | common ranking service | no remaining consumer | DEPRECATE |
| `/api/historical/recent-matches` | CRCON `get_scoreboard_maps` | pagination/order/map identity parity | REWRITE |
| `/api/historical/snapshots/recent-matches` | same history service | both history loaders validated and consolidated | REWRITE alias, later deprecate |
| `/api/historical/matches/detail` | CRCON `get_map_scoreboard` | result, teams, player stats, weapons, link identity parity | REWRITE |
| `/api/historical/server-summary` | CRCON maps/counts | totals and date semantics accepted | REWRITE |
| `/api/historical/snapshots/server-summary` | same summary service | `historico.js` validated | REWRITE alias, later deprecate |
| `/api/historical/player-profile` | common stats profile service | no remaining consumer and contract mapping | DEPRECATE in favor of `/api/stats/players/{id}` |
| `/api/historical/elo-mmr/leaderboard` | none verified | explicit product reapproval required | REMOVE/DEFER |
| `/api/historical/elo-mmr/player` | none verified | explicit product reapproval required | REMOVE/DEFER |

No route is deleted until repository search and access telemetry (when available during deployment handoff) confirm no consumer.

## 3. Module KEEP/REWRITE/DELETE matrix

| Area/module | Classification | Reason / removal gate |
| --- | --- | --- |
| `backend/app/main.py`, routes, serializers/payload facade | REWRITE | serve static + API and delegate to domain services while preserving contracts |
| config and trusted server/origin mapping | KEEP/REWRITE | keep non-game config, remove storage/legacy credentials |
| new CRCON API/DB adapters and domain records | KEEP (new) | target anti-corruption boundary |
| `providers/public_scoreboard_provider.py` | REWRITE | becomes primary typed CRCON history adapter, not ingestion fallback |
| other scoreboard origin/correlation/relink/candidate adapters | DELETE AFTER MIGRATION | HLL no longer correlates/materializes duplicate matches |
| `rcon_client.py` | REVIEW | retain only a disabled, read-only emergency adapter if a verified field gap remains |
| AdminLog parser/storage/materializer modules | DELETE AFTER MIGRATION | CRCON owns events and match lifecycle |
| `rcon_current_match_worker.py` | DELETE AFTER MIGRATION | coherent snapshot is request/cache driven |
| `rcon_historical_worker.py`, historical RCON storage | DELETE AFTER MIGRATION | no HLL capture/materialization |
| `historical_storage.py`, `postgres_display_storage.py`, `postgres_rcon_storage.py` | DELETE AFTER MIGRATION | gameplay persistence removed; split any tiny config concern first |
| historical ingestion/backfill and snapshot generators/scheduler | DELETE AFTER MIGRATION | request-time CRCON adapters + memory cache replace artifacts |
| ranking snapshot/generator/read-model modules | DELETE AFTER MIGRATION | bounded CRCON aggregates replace snapshots |
| player search/profile read models | REWRITE | query verified CRCON identities/stats |
| current backend unit tests | REVIEW/REWRITE | keep public-contract tests; replace storage/materializer tests with adapter fixtures |
| worker/materializer/storage tests | DELETE AFTER MIGRATION | delete only with corresponding modules |
| frontend HTML/CSS | KEEP | no visual redesign required |
| frontend current-match polling JS | REWRITE | one coherent snapshot stream |
| frontend history loaders | REWRITE | consolidate duplicate recent-match requests and remove snapshot naming dependency |
| frontend ranking/stats consumers | KEEP/ADAPT | stable payload first; consume only approved additive fields |
| root/JTA/Portainer Compose | REWRITE | final one-service graph; keep legacy deployment rollback until cutover |
| backend/frontend Dockerfiles | REWRITE/MERGE | one image serves both surfaces |
| forensic/audit documents | KEEP as historical record | do not present obsolete stores as target architecture |

`DELETE AFTER MIGRATION` is not authorization to delete in TASK-289.

## 4. Service decommission matrix

| Current service/job | During strangler | Removal prerequisites | Target |
| --- | --- | --- | --- |
| HLL PostgreSQL | keep unchanged, legacy endpoints only | every table reader/writer mapped; endpoints switched; rollback expiry; retention decision | REMOVE |
| backend | host old/new switches | all adapters and combined static serving validated | REPLACE with stateless HLL service |
| frontend | keep during API migration | same-origin combined image smoke test and rollback | MERGE |
| historical-runner | keep while snapshot endpoints depend on it | history/ranking/profile/event consumers switched | REMOVE |
| rcon-live-adminlog-worker | keep while old current-match paths depend on it | snapshot plus compatibility views accepted | REMOVE |
| rcon-historical-worker | keep while history/materialized stats depend on it | all history/ranking/profile dependants switched | REMOVE |
| local scheduler/snapshot invocation | keep only where deployed/used | no snapshot file/table readers remain | REMOVE |
| HLL volumes | retain and freeze after writers stop | backup/retention approval and rollback window complete | REMOVE |

Current Portainer maximum is six HLL services, two named volumes and three advanced workers. Final is one service, no HLL named volume, no worker and no scheduled job.

## 5. Database/table decommission strategy

Create a read/write dependency ledger for every family from the architecture document. Migration does not alter tables. When the final dependant for a family switches, stop only that family's legacy writer under an approved deployment change, observe rollback, and prevent new HLL reads. Do not drop tables incrementally while a shared PostgreSQL rollback is active.

Order:

1. replace source/server catalog reads with validated configuration;
2. switch live snapshots, then stop AdminLog/current-live writes;
3. switch recent/detail history, then stop historical capture/materialization;
4. switch rankings/search/profiles/events, then stop snapshot/read-model generation;
5. run repository and runtime dependency checks;
6. freeze HLL PostgreSQL read-only for a defined rollback/retention period;
7. export or securely retain what policy requires; and
8. remove the database service and HLL volumes in a separately authorized deployment task.

Families covered: source/server catalog; server snapshots; imported historical tables; displayed snapshot rows/files; raw player ledger; SQLite history/ingestion progress; RCON targets/runs/samples/checkpoints/windows; AdminLog events/profile snapshots/materialized matches/player stats; annual/general ranking snapshots/items; search and period-stat read models; scoreboard correlation candidates. None is `NON-GAME CONFIG THAT MAY STILL BE NEEDED` as a database family.

## 6. Frontend compatibility strategy

Keep URLs and fields stable during source migration. First make the new domain serializers pass golden legacy payloads. Add source/freshness/version fields without making consumers depend on them. Then add the combined current-match snapshot and adapt `partida-actual.js`; leave three compatibility views backed by the same snapshot until the new page is stable.

Consolidate `historico.js` and `historico-recent-live.js` so only one owner loads recent matches. Preserve existing loading/empty/error states, but distinguish stale from empty. Move snapshot-named paths to compatibility aliases, then update callers to canonical paths. Ranking/stats pages need no source-aware rewrite if contracts remain stable. Deprecations require repository search, optional usage evidence and an announced window.

## 7. TASK-272 through TASK-281 classification

| Task | Decision | Required reinterpretation |
| --- | --- | --- |
| TASK-272 | REWRITE | freeze a CRCON-first public/domain contract using verified API/schema evidence, not HLL materialization repair |
| TASK-273 | OBSOLETE | HLL-owned persistent match lifecycle is removed |
| TASK-274 | SUPERSEDED | AdminLog parsing belongs to CRCON; create a narrow parser task only if optional direct-RCON fallback is later proven necessary |
| TASK-275 | OBSOLETE | no HLL ingestion watermark or persisted correlation state exists in target |
| TASK-276 | REWRITE | coherent current-match snapshot is request-driven and memory-cached |
| TASK-277 | REWRITE | CRCON is primary source, not a reconciliation input to HLL history |
| TASK-278 | REWRITE | keep unified endpoint concept, replace its source and add coherent metadata |
| TASK-279 | REWRITE | retain UX objective against the new snapshot contract and one polling stream |
| TASK-280 | OBSOLETE | worker hardening is unnecessary once workers are removed; target BFF health belongs in deployment validation |
| TASK-281 | REWRITE | CRCON-first parity, phased switches, load protection, rollback and decommission validation |

These tasks were read only; their files and lifecycle were not changed.

## 8. Local TASK-264/266/267/268 classification

| Local task | Decision | Post-migration disposition |
| --- | --- | --- |
| TASK-264 AdminLog killfeed staleness | SUPERSEDED | new snapshot/log adapter owns freshness and cursor acceptance |
| TASK-266 historical support leaderboards | REWRITE | CRCON `player_stats.support` supports a bounded cached ranking if product value is confirmed |
| TASK-267 live staleness/copy | SUPERSEDED | snapshot freshness/degraded metadata resolves the architectural cause; retain copy acceptance in frontend migration |
| TASK-268 AdminLog ingestion latency | SUPERSEDED | HLL AdminLog ingestion is removed; validate CRCON event lag instead |

All four remain unmodified and unstaged because they are unrelated local worktree files.

## 9. TASK-284 assessment

TASK-284 remains independent and unmodified. The migration removes several legacy storage/materialization failure surfaces, so its baseline-debt scope must be re-read after phases 2-5. Continue only checks that still apply to the stateless BFF, frontend contracts or repository platform; supersede checks whose sole subject is deleted HLL gameplay persistence/workers. Do not execute it as part of this plan.

## 10. Phased implementation sequence

Recommended backlog for ChatGPT review; no task files or IDs are created here.

| Phase / proposed title | Type, owner, dependencies | Areas | Acceptance and risk |
| --- | --- | --- | --- |
| 1. CRCON adapter foundation and local fixtures | architecture/backend; Arquitecto Python + DB + Backend Senior; none | new domain/API/DB clients, config, tests | pinned fixtures, read-only role/transactions, schema probe, redaction, timeouts; **high** schema/auth risk |
| 2. CRCON-first coherent current-match snapshot | backend; Backend Senior; phase 1 | live adapters, routes/payloads, compatibility tests | canonical/ephemeral identity, one snapshot, cursor, issue-#1186 disagreement tests, no local writes; **high** freshness risk |
| 3. Current-match frontend consolidation | frontend; Frontend Senior; phase 2 | `partida-actual.js` and page tests | one polling stream, transition/stale/error UX, compatibility views retained; **medium** UX risk |
| 4. Historical list/detail CRCON migration | backend; Backend Senior; phase 1 | history adapters/routes/detail tests | pagination, identity/result/stats/weapons parity, bounded caches; **medium-high** auth/shape risk |
| 5. Rankings, player search/profiles and metric decisions | backend/product; Backend Senior + Analista + PM; phases 1/4 | ranking/profile/event services/tests | bounded query plans, all retained metrics, explicit MVP/Elo/event decisions; **high** query/semantic risk |
| 6. Frontend history/stats contract cleanup | frontend; Frontend Senior; phases 4/5 | history loaders, ranking/stats pages | duplicate request removed, canonical paths, stale/empty distinction; **medium** compatibility risk |
| 7. Stop legacy writers and prove zero dependants | platform/research; Arquitecto Python + DB; phases 2-6 | process commands, dependency audits, runbooks | repository/runtime dependency ledger clear, rollback defined, no deletion; **high** operational risk |
| 8. One-service deployment and decommission | platform; Arquitecto Python + Backend Senior; phase 7 | Dockerfiles, Compose/Portainer, runbook | static+API smoke, no HLL DB/volumes/workers, external load/security validation, reversible cutover; **high** deployment risk |
| 9. Delete dead modules/tests/docs and obsolete baseline debt | cleanup; relevant seniors; phase 8 + rollback expiry | legacy storage/workers/tests/docs/tasks | `rg` proves no references, full tests pass, retention approval, scoped deletions; **medium-high** irreversibility risk |

## 11. Rollback strategy

Every migrated endpoint has an independent configuration switch and the legacy implementation remains deployable. New adapters are additive until parity acceptance. A failed endpoint switch rolls back that route, not the whole site. Cache failure always falls back to uncached bounded reads or explicit degraded behavior, never legacy persistence implicitly.

Before stopping a worker, record which legacy endpoints still require it and preserve the previous image/config. After writers stop, keep HLL PostgreSQL and volumes unchanged through the approved rollback window. One-service cutover retains the previous multi-service stack definition and images. Re-enabling legacy services is authorized only if schema/data remain intact and operational owners approve; after volumes are deleted, rollback is forward-fix or backup restore and therefore requires a separate irreversible-change approval.

## 12. Definition of done for each phase

- Foundation: verified/pinned fixtures; supported capability manifest; read-only DB enforcement; API auth proven locally/safely; timeouts, redaction and schema-incompatible tests pass.
- Live backend: snapshot and three compatibility endpoints use one domain object; transition/cursor/freshness/degraded tests pass; no HLL persistence call occurs.
- Live frontend: only one current-match polling loop remains; page handles match reset, stale and unavailable data; load budget passes.
- History: list/detail/server summary use CRCON; pagination and completed match detail golden tests pass; snapshot aliases share the new service.
- Rankings/profiles: retained metrics have documented semantics, bounded plans and deterministic results; removed/deferred metrics have product approval.
- Frontend cleanup: every `/api/` call maps to an active canonical/compatibility route; duplicate fetches are absent.
- Legacy stop: dependency search and runtime observation show no migrated reader; workers stop without changing CRCON or deleting data; rollback drill is documented.
- Deployment: one unprivileged HLL service, zero HLL gameplay volumes/workers/jobs, readiness/degraded behavior and secret redaction validated; legacy stack rollback tested.
- Cleanup: rollback period/retention approval complete; dead code/tests/config/docs removed in scoped changes; full applicable validation passes.

## 13. Final cleanup phase

After deployment acceptance and rollback expiry, delete in small reviewable groups: AdminLog/current workers and tests; historical capture/materialization and tests; snapshot/ranking generators and tests; HLL gameplay storage/schema/bootstrap code; duplicate scoreboard correlation/fallback layers; legacy Compose services/volumes; duplicate frontend compatibility code; and documentation that instructs operators to run retired workers. Preserve forensic documents as historical decisions with an obsolete-architecture banner if needed.

Run `rg` for every removed table, environment variable, command and endpoint; inspect the complete diff; run backend/frontend/platform validations; confirm no secrets/data artifacts are staged; and obtain explicit retention approval before removing volumes. Do not combine data deletion with unrelated product work.

## 14. Deployment handoff requirements

The implementation handoff must provide:

- actual CRCON API base URL through secret/config injection, authentication mode and granted endpoints;
- dedicated read-only PostgreSQL role, TLS settings, allowlisted schema/tables, DSN secret name and verified absence of writes;
- deployed CRCON capability/schema probe results without secrets, including server discriminator and observed live lag;
- measured API rate limits, DB connection/query budgets, cache sizing and per-server load;
- same-origin routing/TLS, health/readiness definitions, unprivileged/read-only container settings and network egress policy;
- feature-switch defaults, previous images/stack, rollback window and owner/on-call contacts;
- retention/export decision for HLL PostgreSQL, SQLite/snapshot files and named volumes;
- smoke/parity checklist for all 36 endpoint surfaces and 16 explicit frontend
  HTTP call sites (14 endpoint patterns);
- explicit decisions for MVP, event/duel views, Elo/MMR, queue display and optional direct RCON; and
- approval that old workers, database service and volumes may be stopped/removed in separate changes.

TASK-289 performed architecture research only: no SSH, Portainer, production access, database connection, deployment, runtime configuration or product-code mutation occurred. Integration tests are not applicable to these documentation and lifecycle-only changes.
