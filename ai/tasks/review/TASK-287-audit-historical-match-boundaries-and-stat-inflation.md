---
id: TASK-287
title: Audit historical match boundaries and player-stat inflation
status: review
type: research
team: Analista
supporting_teams: ["Backend Senior", "Arquitecto de Base de Datos", "Arquitecto Python"]
roadmap_item: historical-rcon-correctness
priority: critical
---

# TASK-287 - Audit historical match boundaries and player-stat inflation

## Goal

Produce a forensic, quantitative explanation for:

1. why HLL Vietnam materializes fewer historical matches than CRCON and the real server history;
2. why some materialized matches contain impossible per-player kill totals, including values around 300;
3. which boundary, materialization, fallback, parser or data-quality mechanisms are responsible; and
4. how much each confirmed cause affects each trusted server over comparable date coverage.

This task is diagnostic only. Do not implement the production fix, mutate stored data or create follow-up tasks.

## Context

HLL Vietnam persists RCON AdminLog events, historical competitive windows, materialized matches, per-match player statistics and public-scoreboard data. The historical model currently produces substantially fewer matches than the real/CRCON history, while some match rows contain implausibly high player kills. Before any repair or rematerialization, the repository needs an evidence-based audit that separates proven production causes from code risks, inferences and unknowns.

Repository inspection has identified the following hypotheses. A-H are mandatory hypotheses supplied for this audit; I-J are additional repository-derived hypotheses. Treat every one as a hypothesis to prove, quantify or reject with data rather than as an assumed root cause:

- **A - orphan `MATCH END` creates an upper-only range.** `_derive_admin_log_matches()` can emit a match with no start bound, and `_derive_player_stats_for_match()` can then select every earlier event for the target through that end time. Audit the additional nuance that an end-only row may currently receive `confidence_mode='exact'` merely because an end row exists.
- **B - unclosed `MATCH START` creates a lower-only range.** A consecutive start or the final open start can emit a match with no end bound, allowing later events and real matches to be included.
- **C - overlapping partial ranges count one event more than once.** Stats are derived independently for each match, so one `rcon_admin_log_events.id` may contribute to multiple `match_key` rows.
- **D - map-only session fallback suppresses repeated matches.** Fallback eligibility uses only `(target_key, normalized_map_name)`, irrespective of session or time.
- **E - fallback history is truncated to 100 windows.** The materializer requests `list_rcon_historical_competitive_windows(limit=100)`.
- **F - 30-minute normalized-map windows can merge rounds.** `COMPETITIVE_WINDOW_GAP_SECONDS=1800`, while map normalization may discard layer or game-mode identity that distinguishes real rounds.
- **G - the parser misses real boundary or team-kill variants.** Current regexes are strict; boundary-like or explicit `TEAM KILL` messages may persist as `event_type='unknown'`.
- **H - persistence dedupe can collapse legitimate same-second events.** The effective identity `(target_key, server_time, canonical_message)` may represent either polling duplicates or distinct legitimate events.
- **I - obsolete partial or fallback rows can remain materialized.** Partial keys use an `open` end component; a later complete match has a different key, and the materializer upserts currently derived rows without pruning rows that are no longer derivable. A fallback inserted before an authoritative match can likewise remain persisted. Subsequent runs recalculate stats for persisted bounded rows, including stale ones.
- **J - historical acquisition cadence can leave source gaps.** Before/around the live-versus-historical worker split, AdminLog lookback and poll cadence may not have covered every interval. Missing source events would cap what any boundary materializer can reconstruct and must be separated from downstream materialization loss.

The audit must distinguish PostgreSQL production behavior from SQLite/local-fallback behavior where their schemas, queries or evidence differ. Existing storage read helpers may initialize schemas as a side effect; do not call any helper until its read-only behavior has been verified.

## Steps

1. Establish a read-only evidence plan before accessing any database.
   - When execution begins, move this one lifecycle file from `pending` to `in-progress` and change its frontmatter `status` to `in-progress`; do not touch another task.
   - Record the environment/source, backend, server targets, timezone assumptions and inclusive/exclusive date bounds used by every query.
   - Use least-privilege, read-only access and sanitized output. Prefer read-only SQL and already-proven side-effect-free Python functions.
   - For PostgreSQL, begin an explicitly read-only transaction before audit queries; for SQLite, open the database in read-only mode. Do not use storage/correlation helpers that initialize schemas, populate caches or upsert candidates as part of a nominal read.
   - If production data is unavailable, continue with code and representative local-data findings, but label every production-dependent question as unresolved. Never invent production counts.

2. Build an inventory for every trusted server and source.
   - Count total AdminLog events, `match_start`, `match_end`, `unknown`, `kill`, `team_switch`, `connected` and `disconnected` events.
   - Count events with null `server_time`, coverage gaps and ingestion/persistence duplicate counters where independently recorded.
   - Count all rows with `source_basis='admin-log-match-ended'`, then split that total into authoritative rows with both bounds and orphan/end-only rows that share the source label. Also count all materialized matches, partial start-only matches, end-only matches, session fallback matches, competitive windows and persisted public-scoreboard/scoreboard matches.
   - Compare the currently derivable match-key set with persisted rows and count stale partials, stale fallbacks and other no-longer-derivable matches separately.
   - Report three separate AdminLog coverage/lag views where available: minimum/maximum `server_time`, `event_timestamp` and `created_at`, documenting their different event, source and ingestion semantics. Report the equivalent earliest/latest timestamps for every other source.
   - Segment AdminLog coverage and gaps by relevant ingestion era, especially before and after TASK-271's live/historical worker split, and distinguish missing source acquisition from materialization loss.
   - Compare counts only over explicit overlapping date ranges; show non-overlapping coverage separately.

3. Reconstruct every target's boundary sequence in `server_time ASC, id ASC` order.
   - Classify normal `START -> END`, consecutive `START -> START`, orphan `END`, final open `START`, start/end map mismatch, and non-monotonic or duplicate boundary evidence.
   - Report counts by server plus sanitized representative event/match IDs for every observed category.
   - Compare the materializer's effective `server_time, id` order with `event_timestamp, id` and `created_at, id` ordering, identify server-time resets or epochs, and avoid equating an unbounded server-time predicate with all earlier/later real-world events when the counter resets.
   - Preserve raw-map, normalized-map, layer and game-mode evidence separately when available.

4. Classify and measure materialized match bounds.
   - Classify each match as both bounds, lower only, upper only or no server-time bounds.
   - For every lower-only and upper-only match, reproduce the current materializer's effective selection without writing data.
   - Calculate selected AdminLog events, selected kills, earliest/latest included event, crossed boundary count, and earlier/later real matches overlapped.
   - Determine directly whether unbounded selections explain the reported 200-300+ kill rows; do not infer causation from an implausible total alone.
   - Measure obsolete persisted partial/fallback rows separately from rows still produced by the current derivation, including whether stale rows duplicate or inflate a later complete match.

5. Detect event-to-match overlap using current semantics.
   - Build a read-only diagnostic mapping from each eligible AdminLog event ID to the materialized `match_key` or keys whose effective interval selects it, using the current inclusive bounds and eligible event types (`kill`, `team_switch`, `connected`, `disconnected`, `chat`).
   - Report events assigned to zero, one and more than one match; report kill events assigned to more than one match and the maximum number of matches sharing one kill event.
   - Report boundary and other ineligible event types separately so they do not distort the unassigned-event result. Audit same-`server_time` boundary collisions and counter resets explicitly.
   - Include sanitized representative event and match IDs and distinguish intentional/explainable overlap from corrupting overlap.

6. Validate per-match statistical invariants for matches with both server-time bounds (the definition of `materially bounded` for this audit).
   - Let `K` be the count of AdminLog `event_type='kill'` rows in the intended bounded interval.
   - Check `SUM(player.kills) + SUM(player.teamkills) == K` and `SUM(player.deaths) == K`, reporting each violation independently.
   - Calculate total kills, deaths and teamkills; maximum player kills and deaths; player count; duration; whole-match kills per minute; and maximum player kills per minute where the denominator is meaningful.
   - Flag outliers for investigation, but do not treat an arbitrary threshold as proof of corruption. Cross-reference every outlier with boundary quality and event overlap.
   - Treat these invariants as internal consistency checks, not proof of source completeness: parser-missed kill/team-kill rows are absent from `K` and require a separate candidate count.

7. Examine the worst inflated or malformed matches.
   - Produce at least the top 20 by maximum player kills, top 20 by total player kills and top 20 by duration anomaly.
   - Define and document the duration-anomaly ranking before inspecting outcomes. Prefer a deterministic robust deviation from a relevant per-server/mode baseline where sample size permits; otherwise report deterministic longest/shortest extremes. State the formula, population and `match_key` tie-break, and do not use the ranking alone as proof of corruption.
   - For each row include server, `match_key`, map, `source_basis`, `confidence_mode`, match timestamps, server-time bounds, maximum player kills, selected kill-event count, crossed boundaries, partial/unbounded classification, and CRCON/scoreboard correlation when available.
   - Explicitly identify any direct examples of the reported approximately 300-kill symptom.

8. Quantify session-fallback suppression and the 100-window limit.
   - Count all competitive windows, those inside the newest 100 and those excluded by the current limit for each server and coverage period. Reconstruct the current newest-100 selection globally across servers, show its per-server allocation, and distinguish per-run truncation from historical accumulation of previously inserted fallback rows.
   - Reproduce map-only suppression by time/session and count fallback candidates skipped solely because any authoritative match shares `(target_key, normalized_map_name)`.
   - Report repeated normalized-map occurrences and repeated-map windows with distinct time/session ranges.
   - Estimate potentially omitted legitimate matches without presenting every suppressed window as a confirmed match.

9. Audit 30-minute competitive-window merging.
   - Identify same-normalized-map samples separated by at most 1800 seconds that may represent distinct rounds.
   - Find cases where raw map, layer or mode differs even though the normalized display map matches.
   - Inspect original samples for score resets, intermediate boundary evidence, negative/out-of-order gaps and transitions that sampling may have missed.
   - Find unusually long windows and windows that cross known AdminLog boundaries.
   - Classify evidence strength; do not automatically label every qualifying window corrupt.

10. Audit parser coverage and persistence dedupe.
    - Count and sample sanitized `event_type='unknown'` rows whose raw or canonical message resembles `MATCH`, `START`, `ENDED` or `TEAM KILL` variants.
    - Reparse relevant rows in memory only and classify misses by signature, including case, punctuation, backticks, score labels/layout, mode suffix, prefix format/empty relative time and leading whitespace. Compare raw versus canonical messages, especially boundary-like unknown rows with null `server_time`.
    - Determine whether parser misses contribute materially to missing boundaries, and audit explicit team-kill variants separately without fixing them.
    - Compare SQLite and PostgreSQL canonicalization/uniqueness behavior where relevant.
    - Inspect the effective production constraint/index rather than assuming the checked-in DDL is deployed unchanged.
    - Inventory null `server_time` rows and determine how backend-specific null equality affects dedupe across otherwise separate observations.
    - For SQLite/legacy data, detect canonical-message migration drift by comparing stored canonical values with an in-memory recanonicalization; quantify possible duplicate coexistence separately from possible collision loss.
    - Estimate whether `(target_key, server_time, canonical_message)` can collapse distinct legitimate same-second events. Separate polling duplicates, plausible legitimate collisions and cases that persisted data cannot resolve.
    - Do not use different polling timestamps alone as proof of distinct events because `event_timestamp` is intentionally outside the current identity. Do not claim that an event was lost unless independent pre-persistence/raw-batch or log evidence demonstrates it.
    - Raw messages, payloads and entries can contain player names, platform IDs or chat. Report internal event/match IDs and redacted patterns; do not dump raw JSON or private text.

11. Compare RCON materialization with CRCON/public-scoreboard history.
    - For each server and explicit overlapping date range, compare scoreboard games, AdminLog boundary pairs, materialized RCON matches and competitive windows.
    - Correlate by server, map, timestamp and duration when available.
    - Classify scoreboard matches as matched to an exact RCON materialized match, matched only to a partial/session window, without an RCON counterpart, or ambiguous.
    - Classify RCON matches without a scoreboard counterpart.
    - Use scoreboard data as an independent forensic reference, not as the implementation source of truth.
    - Query the complete persisted scoreboard tables through an explicitly read-only path. Do not invoke a correlation helper that may backfill/upsert a candidate cache, and do not mistake its bounded candidate list for complete parity coverage.
    - Report total persisted scoreboard games and the subset linkable to trusted servers separately.

12. Quantify and rank root causes.
    - Provide per-server affected counts, missing-match contribution, inflated-match contribution and confidence for hypotheses A-J and any newly discovered cause.
    - Use `confirmed` only when direct evidence demonstrates the mechanism and impact; otherwise use `probable`, `possible`, `rejected` or `unresolved`, with the evidence gap stated.
    - Include a table with at least this shape:

      | Root cause | Server #01 affected | Server #02 affected | Missing matches | Inflated matches | Confidence |
      | --- | ---: | ---: | ---: | ---: | --- |
      | orphan END unbounded stats | ... | ... | ... | ... | confirmed/probable/... |
      | open START unbounded stats | ... | ... | ... | ... | ... |
      | map-only fallback suppression | ... | ... | ... | n/a | ... |
      | fallback limit 100 | ... | ... | ... | n/a | ... |
      | 30-minute repeated-map merge | ... | ... | ... | ... | ... |
      | parser missed boundaries | ... | ... | ... | ... | ... |
      | dedupe collision | ... | ... | ... | ... | ... |
      | obsolete persisted match rows | ... | ... | ... | ... | ... |
      | AdminLog acquisition gaps | ... | ... | ... | ... | ... |

13. Produce the required report and remediation assessment.
    - Create `docs/HISTORICAL_RCON_MATCH_BOUNDARY_AND_STAT_INFLATION_AUDIT.md` with all sections listed under **Required Report**.
    - Assess, but do not implement, the remediation options listed under **Remediation Recommendations**.
    - Recommend an implementation and data-repair task sequence without creating those tasks.
    - Determine the dependency ordering with TASK-272 through TASK-281 after reading their current definitions. Keep TASK-284 explicitly separate as unrelated baseline-validation debt.

14. Validate the audit artifacts and hand off for review.
    - Run the checks under **Validation**, record commands/results and review the complete diff.
    - Move TASK-287 from `ai/tasks/in-progress/` to `ai/tasks/review/` and change frontmatter `status` to `review` only after the evidence and report satisfy this task. Do not mark it `done`.
    - Complete the Outcome with actual evidence, coverage and unresolved access limitations.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `ai/orchestrator/analyst.md`
- `ai/orchestrator/backend-senior.md`
- `ai/orchestrator/database-architect.md`
- `ai/orchestrator/python-architect.md`
- `backend/app/rcon_admin_log_parser.py`
- `backend/app/rcon_admin_log_ingestion.py`
- `backend/app/rcon_admin_log_storage.py`
- `backend/app/rcon_admin_log_materialization.py`
- `backend/app/rcon_historical_storage.py`
- `backend/app/postgres_rcon_storage.py`
- `backend/app/rcon_historical_worker.py`
- `backend/app/rcon_current_match_worker.py`
- `backend/app/rcon_scoreboard_correlation.py`
- `backend/app/historical_storage.py`
- `backend/app/postgres_display_storage.py`
- `backend/app/sqlite_utils.py`
- `backend/app/normalizers.py`
- `backend/tests/test_rcon_materialization_pipeline.py`
- `backend/tests/test_rcon_admin_log_storage.py`
- `deploy/portainer/docker-compose.nas.yml`
- `ai/tasks/done/TASK-116-correlate-rcon-windows-with-scoreboard-matches.md`
- `ai/tasks/done/TASK-122-materialize-rcon-matches-from-adminlog-events.md`
- `ai/tasks/done/TASK-123-materialize-rcon-player-match-stats.md`
- `ai/tasks/done/TASK-271-split-rcon-live-ingestion-from-historical-materialization.md`

Read the current TASK-272 through TASK-281 definitions only when determining dependency order. TASK-287 may read additional files only when directly required by the audit; do not scan unrelated product areas.

## Expected Files to Modify

- The single TASK-287 lifecycle file: start at `ai/tasks/pending/TASK-287-audit-historical-match-boundaries-and-stat-inflation.md`, move it to `ai/tasks/in-progress/TASK-287-audit-historical-match-boundaries-and-stat-inflation.md` with `status: in-progress` when execution starts, then to `ai/tasks/review/TASK-287-audit-historical-match-boundaries-and-stat-inflation.md` with `status: review` when ready for review. Only one path may exist at a time.
- `docs/HISTORICAL_RCON_MATCH_BOUNDARY_AND_STAT_INFLATION_AUDIT.md`.
- Optional `scripts/audit_rcon_match_materialization.py` only if reusable diagnostics are necessary.
- Optional focused tests for the diagnostic script itself.

Do not modify production materialization, parser, storage, worker, frontend or deployment modules.

## Data Safety

All production and database analysis must be read-only.

Do not execute or cause:

- `DELETE`, `UPDATE`, `INSERT`, `TRUNCATE` or other data mutation;
- production rematerialization, repair, backfill or cleanup;
- migrations, schema initialization, schema creation/drop or table creation/drop;
- persisted-database file changes;
- RCON/CRCON configuration or credential changes.

Do not print RCON passwords, PostgreSQL passwords, tokens, authenticated URLs, `.env` secrets or other private data. Pseudonymize or redact player names, Steam/platform/player IDs and chat; never include raw chat messages. Sanitize examples and generated artifacts. Verify that every reused storage/correlation helper is side-effect-free before calling it; if a nominal read helper initializes storage, populates a cache or upserts candidates, replace that diagnostic path with explicitly read-only SQL/connection handling.

If a reusable script is necessary, `scripts/audit_rcon_match_materialization.py` must:

- perform SELECT/read-only operations only;
- avoid schema initialization and materialization entry points;
- sanitize output;
- accept configurable target and date bounds;
- support JSON and/or Markdown summary output; and
- add no framework or dependency.

## Required Report

`docs/HISTORICAL_RCON_MATCH_BOUNDARY_AND_STAT_INFLATION_AUDIT.md` must contain:

1. Executive summary.
2. Data sources and coverage.
3. Current materialization algorithm.
4. Match-count discrepancy.
5. Boundary-sequence audit.
6. Inflated-stat audit.
7. Event overlap audit.
8. Session fallback suppression.
9. Competitive-window merging.
10. Parser/dedupe findings.
11. CRCON comparison.
12. Root-cause ranking.
13. Exact affected counts.
14. Representative examples.
15. Recommended remediation architecture.
16. Proposed implementation task breakdown.
17. Data repair/backfill strategy.
18. Validation criteria for declaring historical data trustworthy.

Every quantitative section must identify its server, source, date coverage and unavailable evidence. Keep confirmed fact, inference and unknown separate.

## Remediation Recommendations

Assess at least the following without implementing them:

- refuse to compute exact player statistics without both match bounds;
- bind persisted events to an explicit match instance;
- recover or infer missing boundaries safely;
- constrain partial ranges with adjacent boundaries and map transitions;
- replace map-only fallback suppression with temporal/session correlation;
- remove arbitrary historical fallback limits;
- preserve raw layer/mode identity separately from normalized display map;
- rematerialize affected historical data only after the production fix is validated;
- reconcile against CRCON historical games; and
- add integrity checks that prevent impossible overlapping event assignments.

Explain which work must occur before or after current-match TASK-272 through TASK-281. Confirm or revise this expected direction from evidence: canonical match identity/boundaries, historical materialization fix, controlled historical repair/rematerialization, then current-match lifecycle alignment on the same match-instance semantics.

## Constraints

- Diagnostic/research only; do not implement a production fix.
- Do not mutate, repair, clean or rematerialize production data.
- Do not change backend or frontend behavior.
- Do not change worker/deployment behavior, credentials or CRCON configuration.
- Do not execute or modify TASK-272 through TASK-281.
- Do not execute or modify TASK-284 or mix baseline-validation debt into this audit.
- Do not create or execute follow-up tasks automatically.
- Do not fabricate conclusions or production counts.
- Distinguish confirmed fact, inference and unknown.
- Preserve HLL Vietnam repository structure and modify no unrelated files.

## Validation

Before moving TASK-287 to review:

- run `python -m compileall` for any new diagnostic Python;
- run focused unit tests if a diagnostic helper is added;
- run the diagnostic against an available representative dataset and record the dataset/source/date coverage;
- inspect all SQL and code paths used by the diagnostic and verify they are read-only and have no schema-initialization side effects;
- verify hypotheses A-J are explicitly confirmed, rejected or left unresolved with quantified evidence or a documented evidence gap;
- verify every required audit dimension and all 18 report sections are present;
- run `git diff --check`;
- run `git diff --name-only` and confirm the diff matches the expected scope;
- verify no production module, persisted database file, secret or generated private-data dump was modified or committed; and
- document exactly which findings were proven from code/local data and which still require read-only production execution if production access was unavailable.

The task must not be marked complete with invented production counts. Integration tests are not required unless a diagnostic helper touches an existing integration surface; document that decision in the Outcome.

## Outcome

### Audit result

The forensic report is `docs/HISTORICAL_RCON_MATCH_BOUNDARY_AND_STAT_INFLATION_AUDIT.md`. A deterministic, aggregate-only read-only diagnostic and focused tests were added at `scripts/audit_rcon_match_materialization.py` and `backend/tests/test_audit_rcon_match_materialization.py`.

#### Sources and coverage

Production PostgreSQL was not accessible, so every production count and the reported approximately 300-kill production example remain **UNRESOLVED — production data not accessible in this run**. The representative local SQLite snapshot was examined directly with `mode=ro`, `PRAGMA query_only=ON`, a read transaction, and immutable mode for final runs; schema-initializing repository helpers were not used.

- Comunidad Hispana #01: 90 AdminLog events from `2026-05-19T11:16:10.281Z` through `2026-05-20T21:16:46.467Z` by `event_timestamp`; server-time range `1779178245..1779311718`; created-at range `2026-05-19T11:16:11Z..2026-05-20T21:16:48Z`. The snapshot has 22 materialized rows, 24 competitive windows, and 8,730 complete persisted scoreboard windows spanning 2024-05-17 through 2026-05-25.
- Comunidad Hispana #02: 21,152 AdminLog events from `2026-05-19T11:16:10.574Z` through `2026-05-20T23:21:45.816Z`; server-time range `1779108337..1779319250`; created-at range `2026-05-19T11:16:11Z..2026-05-20T23:21:48Z`. The snapshot has 36 materialized rows, 28 competitive windows, and 832 complete persisted scoreboard windows spanning 2025-11-04 through 2026-05-25.

The full scoreboard totals and materialized totals are not directly comparable because coverage differs. Within explicit plausible-`server_time` overlap, #01 has 7 scoreboard games versus 5 complete RCON pairs; classifications are 4 exact, 1 partial/session-only, 2 without a selected RCON counterpart, 0 ambiguous, and 1 RCON pair without a selected scoreboard counterpart. #02 has 17 versus 16; classifications are 10 exact, 0 partial/session-only, 7 without a selected RCON counterpart, 0 ambiguous, and 6 RCON pairs without a selected scoreboard counterpart.

#### Confirmed, rejected, and unresolved causes

- Confirmed locally: one #02 orphan END/upper-only range; stale/open START lower-only ranges; independent overlapping range assignment; 2 #01 and 297 #02 explicit `TEAM KILL` rows classified `unknown`; and 7 #01 / 13 #02 persisted rows no longer derivable. Six stale bounded #02 rows share kills with complete ranges.
- Probable/possible locally: map-only fallback suppression leaves 9 #01 and 14 #02 temporally distant omission candidates; acquisition loss is possible because of observed gaps and cadence/lookback design, but there is no worker poll ledger. The 1,800-second same-map extension is confirmed in code, but local multi-round loss is not proven: no competitive window contains more than one complete server-time boundary pair.
- Rejected locally: the newest-100 limit excludes zero of the 52 windows; no unknown row resembles a missed START/END; all 5 #01 and 16 #02 both-bound matches pass both kill/death invariants.
- Unresolved: all production frequencies, the concrete approximately 300-kill row, legitimate dedupe collision loss, deployed PostgreSQL constraint semantics, exact acquisition-loss counts, post-TASK-271 coverage, and whether every distant fallback candidate is one real match.

#### Inflation, overlap, and stale rows

Six #02 partial rows are confirmed inflated under the conservative rule “the current partial range spans at least two derived complete matches”; #01 has zero. The worst sanitized examples are `match-2d63a3461812`, `match-99de224345eb`, and `match-e3eee55a6498`, each with maximum player kills 208 and respectively 10,145, 10,145, and 9,908 selected kill events. No local row reaches approximately 300.

#01 streams 38 eligible events: 2 map to zero ranges, 26 to exactly one, and 10 to multiple ranges (maximum multiplicity 3; no kill events). #02 streams 16,060: 71 to zero, 3,140 to one, and 12,849 to multiple ranges. Of 12,776 #02 kill events, 10,146 map to multiple rows; maximum multiplicity is 7. These counts are unique source event rows satisfying several predicates, not duplicate stored rows.

Persisted/currently derivable/not-currently-derivable counts are 22/15/7 on #01 and 36/23/13 on #02. The six stale bounded #02 rows have a summed 37,995 selected kills, explicitly not a unique-kill count because the stale ranges overlap.

#### Recommended order

Review/reproduce TASK-287 on production read-only; incorporate canonical identity, epoch, degraded-state, and exclusive-assignment requirements into TASK-272; implement a dedicated historical boundary/match-instance repair; coordinate TASK-274 parser normalization; implement bounded materialization, temporal fallback, stale reconciliation, and acquisition checkpoints; perform a separately authorized shadow rebuild/rematerialization plus CRCON reconciliation; then continue TASK-273 and TASK-275 through TASK-281. TASK-273 and TASK-275–281 should wait for the historical boundary/identity decision. TASK-284 remains unrelated.

#### Validation

- `python -m compileall scripts`: passed.
- Focused diagnostic tests: `17 passed`.
- Two final read-only JSON runs were byte-identical with SHA-256 `5d5066e76269b9cdd962964f29e81653fa356399d7ce54a7498b85c7c9da0044`.
- SQL allowlisting/rejection, explicit read-only transactions, privacy sanitation, target/date filtering, and unchanged temporary SQLite database hash/size/mtime are covered by focused tests.
- Integration tests were not run because the diagnostic is isolated and does not modify an existing integration surface.
- The main local SQLite database and WAL data/schema state did not change. The first exploratory read-only WAL connection refreshed only the pre-existing `.sqlite3-shm` reader metadata timestamp; final immutable runs left all database artifacts stable. No production data was contacted or mutated.
- `git diff --check`: passed. `git diff --name-only` and `git status --short` were inspected; the task scope is limited to this lifecycle file, the audit report, the isolated diagnostic, and its focused tests.
- No production module, persisted database, or secret was modified. TASK-272–281 and TASK-284 were neither modified nor executed. The six pre-existing untracked TASK-204/242/264/266/267/268 files remained unstaged and byte-identical to their recorded pre-task hashes.

TASK-287 finishes in `review`, not `done`, for orchestrator evaluation. No follow-up task was created or executed.

## Change Budget

- Prefer the task lifecycle file, the required report and at most one optional read-only diagnostic plus focused tests.
- Do not let audit convenience expand into production changes.
- If the investigation uncovers implementation work, document it as a recommendation instead of expanding this task.
