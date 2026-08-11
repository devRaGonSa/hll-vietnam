---
id: TASK-288
title: Reproduce historical RCON forensics on production PostgreSQL
status: pending
type: research
team: Analista
supporting_teams: ["Arquitecto de Base de Datos", "Arquitecto Python", "Backend Senior"]
roadmap_item: historical-rcon-correctness
priority: critical
---

# TASK-288 - Reproduce historical RCON forensics on production PostgreSQL

## Goal

Run the reviewed TASK-287 forensic methodology against the actual deployed PostgreSQL database in strictly read-only mode to:

1. determine the production magnitude of historical match-boundary corruption;
2. locate and explain the reported approximately-300-kill materialized match or equivalent production anomalies;
3. quantify production match-count parity against complete persisted CRCON/public-scoreboard history;
4. inspect the effective deployed PostgreSQL constraints and dedupe semantics;
5. measure actual AdminLog acquisition coverage and gaps, including the post-TASK-271 period;
6. confirm, reject or reclassify every TASK-287 hypothesis with production evidence; and
7. produce the evidence required to freeze the canonical match-identity contract before implementation work begins.

This task is production observation only. It must not repair, rematerialize, migrate, restart or otherwise change production state.

## Context

TASK-287 remains in `review`. Its final corrections were merged through PR #12 in GitHub merge commit `23a2cd1bfbed00af5122f26bbc1a3712002777fa`.

The representative local SQLite audit proved:

- #02 has six confirmed inflated partial matches caused by unbounded and overlapping ranges;
- the worst local maximum is 208 kills for one player;
- 10,146 of 12,776 local #02 kill events are selected by more than one materialized match;
- one orphan END creates an upper-only row labelled exact;
- stale/open START rows create lower-only ranges;
- stale partial and fallback rows remain after the currently derivable key set changes;
- map-only fallback suppression leaves 9 distant candidates on #01 and 14 on #02;
- the local newest-100 limit excludes zero windows;
- explicit TEAM KILL is unparsed in 2 #01 rows and 297 #02 rows;
- no locally stored unknown row resembles a missed START/END boundary;
- local all-history disparity is dominated by limited AdminLog source coverage; and
- deployed counts, deployed schema semantics, the approximately-300-kill case and post-TASK-271 acquisition health remain unresolved because production PostgreSQL was unavailable.

TASK-288 exists only to resolve those production-dependent unknowns. It must not implement any repair or execute another task.

## Steps

1. Move only TASK-288 from `pending` to `in-progress` on a dedicated branch such as `research/task-288-production-postgres-forensics`. Leave TASK-287 in `review` and TASK-272 through TASK-281 and TASK-284 untouched.
2. Read every file listed below before connecting to production. Re-verify that the TASK-287 diagnostic uses direct read-only adapters, does not initialize schema or caches, and rejects mutating SQL.
3. Run `python scripts/audit_rcon_match_materialization.py --help` locally and use the actual reviewed interface. Do not pass a DSN value literally on the command line. The current `--from`/`--until` options bound only `requested_range_admin_log_inventory`; do not misrepresent them as a whole-audit cutoff.
4. Discover the real production execution environment from repository/deployment documentation and already-authorized operational access. Identify the host/deployment, PostgreSQL service/container, safe application or administrative execution path, DSN environment-variable name, deployed application version/commit, PostgreSQL version, database and relevant schemas. Never print credentials or the DSN.
5. Prefer an isolated temporary checkout/execution directory at the reviewed diagnostic revision represented by merge commit `23a2cd1bfbed00af5122f26bbc1a3712002777fa`. An existing backend container is acceptable only if the diagnostic can run without changing its filesystem, image, deployment or service state. Do not modify the deployed application checkout.
6. Before analytical queries, enforce and record a PostgreSQL `REPEATABLE READ READ ONLY` transaction and verify `SHOW transaction_read_only` returns `on`. Use direct read-only SQL for any additional catalog evidence. Do not call repository helpers that initialize schema, materialize matches, populate caches or update checkpoints.
7. Establish and record `audit_cutoff_utc` before the first full run. Separate fixed-cutoff evidence from live counters. Because the reviewed CLI does not apply `--until` to every causal section, explicitly document which sections are fixed by query/snapshot semantics and which may advance with live ingestion. Do not invent fixed-cutoff determinism where the interface cannot enforce it.
8. Run the complete production diagnostic at least twice under equivalent read-only conditions with `--postgres-env <actual-environment-variable-name>`, the validated TASK-271 split reference `2026-06-22T13:16:19Z`, no more than five sanitized examples, JSON output and no literal DSN. Hash both sanitized outputs. Investigate fixed-scope differences; report legitimate post-cutoff live growth separately.
9. Use read-only `pg_catalog`/`information_schema` queries to record effective deployed definitions for `rcon_admin_log_events`, `rcon_materialized_matches`, `rcon_match_player_stats` and relevant historical capture/checkpoint tables. Capture primary keys, unique constraints, indexes, `NULLS NOT DISTINCT` behavior, nullability, data types and relevant foreign keys. Compare production with checked-in definitions rather than assuming they match.
10. Measure the required production inventory for trusted Comunidad Hispana #01 and #02 at the declared cutoff:
    - AdminLog: total, kill, TEAM KILL-like unknown, match start/end, unknown, connected, disconnected, team switch, null `server_time`, and min/max `server_time`, `event_timestamp` and `created_at`;
    - materialization: total, both-bound, lower-only, upper-only, no-bound, exact-labelled rows lacking both bounds, admin-log-ended, session fallback and stale/non-derivable rows;
    - player statistics: matches with stats, maximum player kills/deaths, total kills/deaths/teamkills, top anomalies and invariant failures;
    - historical capture: run/capture counts, checkpoint coverage, failed/stale/skipped runs, worker-era coverage, acquisition gaps and post-TASK-271 freshness;
    - competitive windows: total, repeated-map groups, newest-100 allocation per server, excluded windows, cutoff ties, map-only suppression, distant suppression and long/suspicious windows; and
    - complete persisted trusted scoreboard: all-history totals, AdminLog overlap, exact, partial/session-only, missing, ambiguous and RCON-without-scoreboard counts.
11. Investigate the approximately-300-kill symptom as a primary acceptance criterion. Order production matches by maximum player kills descending and inspect at least the top 30. For every row around or above 250 kills, and any equivalent extreme anomaly, emit only a sanitized deterministic record containing server, match ref, map, source/confidence, wall and server-time bounds, bound class, maximum and total kills, selected source kills, boundaries and complete intervals crossed, overlap with other materialized rows, derivability/staleness, corresponding complete match and scoreboard correlation. Do not expose player identity.
12. Classify every extreme row as one or more of: `upper-only unbounded range`, `lower-only unbounded range`, `overlapping stale row`, `event-assignment overlap`, `bounded but source-abnormal`, `parser/source issue`, or `unknown`. Do not call the production approximately-300 case solved without direct event-range evidence.
13. Reproduce current production event-assignment semantics as `AdminLog event id -> materialized match keys`. Per server report eligible rows assigned zero, once or multiple times; multiply assigned kill rows; maximum multiplicity; and the materialized rows responsible. Compare percentages with TASK-287 local results.
14. Reconstruct boundaries in `server_time ASC, id ASC`, and separately inspect `event_timestamp, id`, `created_at, id` and possible server-time epochs/resets. Quantify START-to-END, START-to-START, orphan END, final open START, normalized-map mismatch, raw map/layer/mode differences, same-time boundary groups and duplicate identities.
15. For every production match with finite ordered bounds, calculate `K = count(event_type='kill')` in the inclusive interval and verify `SUM(kills)+SUM(teamkills)=K` and `SUM(deaths)=K`. Report every violation and explain why passing invariants do not prove source completeness when TEAM KILL rows remain unknown.
16. Measure production TEAM KILL-like unknown rows by server and time period. Do not fix the parser; preserve this evidence for TASK-274.
17. Audit acquisition around TASK-271. Confirm the actual live/historical worker split and hotfix transition evidence, then compare pre-split, immediate post-split and recent coverage. Report largest gaps, gaps beyond poll/lookback tolerance, worker-run evidence, checkpoints/watermarks and whether coverage improved. Distinguish `observed ingestion silence`, `proven ingestion outage` and `unknown/no game activity`.
18. Audit effective PostgreSQL dedupe semantics: duplicate identity groups, null `server_time`, possible same-second/same-canonical collisions, and reject/duplicate telemetry where available. Do not claim legitimate loss without independent evidence. If `UNIQUE NULLS NOT DISTINCT` is deployed, explain its exact difference from local SQLite behavior.
19. Compare production with local TASK-287 for hypotheses A-J in a table with `Local TASK-287`, `Production`, and `Classification change` columns. Use only `confirmed`, `probable`, `possible`, `rejected` or `unresolved`.
20. Create `docs/HISTORICAL_RCON_PRODUCTION_POSTGRES_FORENSIC_REPRODUCTION.md` without overwriting the local TASK-287 report. Include exactly these numbered sections:
    1. Executive summary.
    2. Production environment identification without secrets.
    3. Safety/read-only proof.
    4. Audit cutoff.
    5. Deployed PostgreSQL schema/constraint comparison.
    6. Per-server source coverage.
    7. Boundary sequence.
    8. Partial/stale materialized rows.
    9. Event-overlap measurement.
    10. Extreme kill rows.
    11. Approximately-300-kill investigation.
    12. Statistical invariants.
    13. TEAM KILL production counts.
    14. Fallback suppression.
    15. Newest-100 impact.
    16. Competitive-window findings.
    17. Acquisition coverage and TASK-271 era comparison.
    18. Dedupe findings.
    19. CRCON/scoreboard parity.
    20. Local-vs-production comparison.
    21. Updated A-J root-cause table.
    22. Production repair prerequisites.
    23. Recommendation for the TASK-272 contract.
    24. Exact next implementation dependency order.
21. Prefer zero changes to the reviewed diagnostic. If an actual PostgreSQL compatibility defect prevents execution, make the smallest diagnostic-only fix in the allowed files, add focused tests, explain why local tests missed it, rerun local validation, and then repeat the production audit. Do not modify `backend/app/**`.
22. Record production-write protection evidence in the report and Outcome: read-only transaction verified, no DDL, no materialization, no cache population, no worker restart, no deployment change and no intentional row mutation. Do not use global row-count stability as proof because legitimate live workers may write concurrently.
23. Analyze TASK-272 through TASK-281 only for dependency recommendations. Do not edit or execute them. Keep TASK-284 independent and untouched.
24. After validation, move only TASK-288 from `in-progress` to `review`; do not move it to `done`. Stage only intended files, commit, push the dedicated branch and open a draft PR to `main`. Do not merge automatically.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `ai/orchestrator/analyst.md`
- `ai/orchestrator/database-architect.md`
- `ai/orchestrator/python-architect.md`
- `ai/tasks/review/TASK-287-audit-historical-match-boundaries-and-stat-inflation.md`
- `docs/HISTORICAL_RCON_MATCH_BOUNDARY_AND_STAT_INFLATION_AUDIT.md`
- `scripts/audit_rcon_match_materialization.py`
- `backend/tests/test_audit_rcon_match_materialization.py`
- `backend/app/rcon_admin_log_materialization.py`
- `backend/app/rcon_admin_log_storage.py`
- `backend/app/rcon_admin_log_parser.py`
- `backend/app/postgres_rcon_storage.py`
- `backend/app/rcon_historical_worker.py`
- `backend/app/rcon_current_match_worker.py`
- `deploy/portainer/docker-compose.nas.yml`
- `ai/tasks/done/TASK-271-split-rcon-live-ingestion-from-historical-materialization.md`

Read TASK-272 through TASK-281 only for final dependency analysis. Do not execute or edit them.

## Expected Files to Modify

- The single TASK-288 lifecycle file, moving only through:
  - `ai/tasks/pending/TASK-288-reproduce-historical-forensics-on-production-postgres.md`
  - `ai/tasks/in-progress/TASK-288-reproduce-historical-forensics-on-production-postgres.md`
  - `ai/tasks/review/TASK-288-reproduce-historical-forensics-on-production-postgres.md`
- `docs/HISTORICAL_RCON_PRODUCTION_POSTGRES_FORENSIC_REPRODUCTION.md`

Only if a proven PostgreSQL compatibility defect blocks the reviewed diagnostic:

- `scripts/audit_rcon_match_materialization.py`
- `backend/tests/test_audit_rcon_match_materialization.py`

Do not modify production application code, frontend, deployment, Compose, migrations, runtime configuration, secrets or database files.

## Constraints

- Production access is strictly read-only and must coexist with live operation.
- Never print or commit a DSN, password, credential, authenticated URL, raw chat, player name, platform ID or raw payload.
- Do not put secrets in command arguments or shell history where avoidable. Resolve credentials through the existing environment and pass only the DSN environment-variable name to `--postgres-env`.
- Do not execute `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `MERGE`, `CREATE`, `ALTER`, `DROP`, `VACUUM`, `REINDEX`, `REFRESH MATERIALIZED VIEW`, `CALL`, schema initialization, migrations, materialization, snapshot refresh, cache population, repair, cleanup, backfill or checkpoint advancement.
- Do not stop, pause, rebuild, restart or recreate workers, backend, PostgreSQL, RCON services, containers, images, services or volumes.
- Do not modify environment variables, Compose, credentials, RCON connectivity, deployment or the deployed application checkout.
- Do not use any read helper until its absence of initialization/cache/materialization side effects is proven. Prefer direct parameterized catalog/data `SELECT` queries.
- Do not downgrade to SQLite or call TASK-288 complete without production PostgreSQL evidence.
- Stop and block with exact operational evidence rather than guessing if the production host cannot be identified, authorized connectivity is unavailable, read-only mode cannot be enforced, safe execution would require deployed-code changes, required schema is incompatible beyond an isolated diagnostic fix, or access would expose secrets.
- TASK-287 stays in `review`. TASK-272 through TASK-281 and TASK-284 remain unmodified and unexecuted.
- Do not create follow-up tasks. Document implementation recommendations only.
- Use a dedicated research branch; do not work directly on `main` during execution.
- Never use `git add .`, `git add -A`, force push, reset, rebase or automatic merge.
- Stage only intended paths and open a draft PR. Do not delete the source branch automatically.

## Validation

- Run `python -m compileall scripts`.
- Run `python -m pytest backend/tests/test_audit_rcon_match_materialization.py -q`.
- Complete two equivalent read-only PostgreSQL diagnostics, hash both sanitized JSON artifacts and distinguish fixed-cutoff reproducibility from legitimate live changes.
- Verify runtime evidence shows `transaction_read_only = on` and a repeatable-read read-only transaction.
- Inspect every executed diagnostic/catalog SQL path and confirm no mutating statement, schema initializer, cache population or materialization helper ran.
- Verify all required per-server inventories, top-30 extreme rows, approximately-300-kill investigation, A-J classification, schema comparison, acquisition eras, overlap metrics and scoreboard parity appear in the report.
- Run `git diff --check` and `git diff --name-only`.
- Verify the final diff contains no `backend/app/**`, frontend, deploy, Compose, migration, runtime configuration, secret or database file unless the only extra files are the explicitly allowed diagnostic/test pair for a proven compatibility defect.
- Review `git status --short`, preserve unrelated local files, and confirm TASK-287, TASK-272 through TASK-281 and TASK-284 are untouched.
- Before commit, inspect `git diff --cached --name-status` and `git diff --cached --check` after staging only explicit paths.
- Integration tests are not required unless a diagnostic compatibility change reaches an existing integration surface; document the decision.

## Outcome

Record:

- production environment reached and deployed application revision;
- PostgreSQL version, database/schema identifiers without secrets, and effective deployed constraints;
- audit cutoff and fixed-versus-live reproducibility semantics;
- read-only transaction enforcement evidence;
- trusted servers and exact source coverage;
- materialized/boundary/stale counts and event overlap;
- maximum player kills and the approximately-300-kill investigation result;
- invariant failures and TEAM KILL counts;
- fallback suppression, newest-100 impact and competitive-window findings;
- acquisition gaps and pre/post-TASK-271 comparison;
- deployed dedupe semantics and any independent collision evidence;
- complete scoreboard parity;
- production A-J classifications and local-vs-production differences;
- sanitized artifact hashes and commands/validation;
- proof that the TASK-288 session ran no DDL, materialization, worker/deployment change or intentional row mutation;
- exact unresolved issues and stop/block evidence where applicable; and
- the recommended TASK-272 contract changes and next implementation dependency order without executing or editing those tasks.

TASK-288 must finish in `review`, not `done`. TASK-287 must remain in `review` until a separate orchestrator closure decision.

## Change Budget

- Prefer only the lifecycle file and the production forensic report.
- Permit the existing diagnostic and its focused test file only for a proven PostgreSQL compatibility defect.
- Do not expand into production fixes, data repair, deployment changes or task refinement.
