# Historical RCON match boundary and stat-inflation audit

## 1. Executive summary

TASK-287 confirms, on the representative local SQLite snapshot, that the two reported symptoms have different causes:

- **Inflated player totals are caused by unbounded and overlapping match ranges.** Comunidad Hispana #02 contains one orphan `MATCH END` row with only an upper bound and stale `MATCH START` rows with only lower bounds. Six partial rows select events from at least two complete matches. The worst three each assign 9,908–10,145 kill events and produce a maximum of 208 kills for one player. No approximately 300-kill row exists in this snapshot; the production example remains unresolved without production PostgreSQL access.
- **The large all-history match-count gap is primarily a source-coverage gap in the available snapshot, then a materialization-quality problem inside the overlap.** The public scoreboard spans 2024-05-17 through 2026-05-25 for #01 and 2025-11-04 through 2026-05-25 for #02, while local AdminLog server time covers only 2026-05-18 through 2026-05-20. Over comparable server-time coverage, the scoreboard contains 7 games versus 5 complete RCON boundary pairs on #01, and 17 versus 16 on #02. Correlation classifies 2 and 7 scoreboard games respectively as having no selected RCON counterpart; several RCON matches also have no selected scoreboard counterpart, so these are not one-for-one missing-match counts.
- **One AdminLog event can be counted by several persisted matches.** On #02, 12,849 of 16,060 eligible events are selected by more than one bounded or partially bounded match; 10,146 of 12,776 kill events are selected more than once, with maximum multiplicity 7. This is a match-assignment defect, not duplicated source rows.
- **Fallback logic loses fidelity.** Map-only suppression rejects 14 of 24 windows on #01 and 23 of 28 on #02. Five and eight respectively overlap an exact match; one #02 suppression is within one hour but does not overlap; the remaining 9 and 14 are temporally distant omission candidates, not independently proven games. The global `limit=100` has no effect locally because only 52 windows exist. The 1,800-second same-normalized-map extension is a confirmed code risk, but server-time comparison finds no local competitive window containing more than one complete AdminLog pair, so local multi-round loss from this mechanism is not proven.
- **Persisted materialization is append/upsert-only.** Seven #01 rows and thirteen #02 rows are no longer derivable. Six stale bounded #02 rows share kills with complete ranges. Their selected-kill sum is 37,995, but that is deliberately not presented as a unique-event count because those stale ranges overlap one another.
- **The local parser did not miss a stored match boundary.** It did classify 2 #01 and 297 #02 explicit `TEAM KILL` rows as `unknown`. Dedupe loss remains unresolved: there are no duplicate identity groups, null `server_time` rows, or legacy canonical drift locally, and rejected observations have no row-level ledger.

Production PostgreSQL was not accessible. Every production-dependent count in this report is therefore **UNRESOLVED — production data not accessible in this run**. No production fix, materialization, migration, or data repair was performed.

## 2. Environment and data coverage

### Method and safety boundary

The audit used the offline repository snapshot `backend/data/hll_vietnam_dev.sqlite3` through the new diagnostic's direct SQLite adapter. Final evidence runs used URI `mode=ro`, `PRAGMA query_only=ON`, a read transaction, and `--sqlite-immutable`; repository storage helpers were intentionally bypassed because several nominal read paths initialize schema or populate caches. Results were written only to temporary JSON/Markdown files outside the repository. Match references in this report are deterministic SHA-256 prefixes; player names, platform IDs, chat, raw messages, payloads, target keys, credentials, hosts, DSNs, and authenticated URLs are excluded.

The first exploratory `mode=ro` connection caused SQLite to refresh the pre-existing `.sqlite3-shm` reader-side metadata timestamp. The main database file, schema/data content, and zero-byte WAL remained unchanged; all final runs used immutable read-only mode and left all three stable. No production database was contacted or mutated.

PostgreSQL execution remains planned, not performed. The diagnostic accepts only the *name* of the DSN environment variable via `--postgres-env`; it begins `REPEATABLE READ READ ONLY`, checks `transaction_read_only`, runs constant parameterized `SELECT`/metadata queries, and rolls back. It does not call `connect_postgres_compat()`, scoreboard candidate correlation, schema initialization, or materialization helpers.

### AdminLog inventory and coverage

`server_time` is the server-supplied ordering value used by the materializer; `event_timestamp` represents the source observation timestamp; `created_at` represents persistence time. They are reported separately and are not interchangeable.

| Server | Total | Kill | Start | End | Unknown | Connect | Disconnect | Team switch | Null `server_time` | `server_time` range | `event_timestamp` UTC | `created_at` UTC |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| #01 | 90 | 0 | 5 | 5 | 2 | 15 | 15 | 6 | 0 | 1779178245–1779311718 (2026-05-19 08:10:45 – 2026-05-20 21:15:18 UTC) | 2026-05-19 11:16:10.281 – 2026-05-20 21:16:46.467 | 2026-05-19 11:16:11 – 2026-05-20 21:16:48 |
| #02 | 21,152 | 12,776 | 17 | 17 | 299 | 888 | 953 | 910 | 0 | 1779108337–1779319250 (2026-05-18 12:45:37 – 2026-05-20 23:20:50 UTC) | 2026-05-19 11:16:10.574 – 2026-05-20 23:21:45.816 | 2026-05-19 11:16:11 – 2026-05-20 23:21:48 |

### Other source coverage

| Server | Materialized rows | Materialized wall-clock coverage | Competitive windows | Window coverage UTC | Persisted scoreboard | Scoreboard full coverage UTC |
| --- | ---: | --- | ---: | --- | ---: | --- |
| #01 | 22 | 2026-03-26 09:19:12 – 2026-05-20 21:16:46 | 24 | 2026-03-26 09:19:12 – 2026-05-21 06:31:36 | 8,730 | starts 2024-05-17 20:20:17 – 2026-05-25 09:50:52; ends 2024-05-17 20:48:40 – 2026-05-25 11:20:52 |
| #02 | 36 | 2026-03-26 17:53:06 – 2026-05-20 23:24:09 | 28 | 2026-03-26 09:19:12 – 2026-05-21 06:31:29 | 832 | starts 2025-11-04 16:01:50 – 2026-05-25 18:56:24; ends 2025-11-04 17:10:19 – 2026-05-25 20:26:24 |

The scoreboard totals and materialized totals above are intentionally not compared as parity figures because their coverage differs radically. Comparable windows are used in section 18.

The full persisted scoreboard inventory is 9,845 rows: 9,562 belong to the trusted #01/#02 servers shown above and 283 belong to other/#03 server history excluded from this audit's trusted-server parity calculation.

### Production status

No `HLL_BACKEND_DATABASE_URL` was available locally and no running container exposed the deployed PostgreSQL database. Consequently, deployed constraint/index introspection, production A–J counts, the production approximately 300-kill row, and post-TASK-271 era coverage are **UNRESOLVED — production data not accessible in this run**.

## 3. Current materialization algorithm

Code inspection establishes the following behavior without changing it:

1. `backend/app/rcon_admin_log_materialization.py:489-512` walks boundary rows ordered by `target_key, server_time, id`. A second start emits the previous start as lower-only; an end without an open start emits upper-only; a final open start emits lower-only.
2. `backend/app/rcon_admin_log_materialization.py:1044-1054` embeds `missing` or `open` in the `match_key`. When the missing boundary later arrives, the completed match receives a different key.
3. `backend/app/rcon_admin_log_materialization.py:660-697` recalculates every persisted row with either bound. The event predicate includes `server_time >= lower` only when a lower exists and `server_time <= upper` only when an upper exists. It therefore treats either missing side as infinity and evaluates each row independently.
4. Upsert updates current keys but never deletes keys no longer derived. Old partials and fallbacks remain and continue participating in stat recalculation.
5. `backend/app/rcon_admin_log_materialization.py:515-562` asks for only the newest 100 competitive windows, then suppresses a window if *any* `admin-log-match-ended` row has the same `(target, normalized display map)`, without temporal/session identity.
6. `backend/app/rcon_historical_storage.py:1016-1058,1125-1133` extends the latest competitive window when the normalized map is unchanged and the gap is `<= 1800` seconds. Layer/mode identity is not part of this decision.

These mechanisms are sufficient to explain how a source event can be counted in several rows and why session candidates can disappear. They do not by themselves prove production frequency; local measurements follow.

## 4. Match-count discrepancy

### Persisted/materialized inventory

| Server | Total | Both bounds | Lower only | Upper only | No bounds | `admin-log-match-ended` total | Ended both-bound | Ended orphan | Start-source | Session fallback |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| #01 | 22 | 5 | 2 | 0 | 15 | 5 | 5 | 0 | 2 | 15 |
| #02 | 36 | 16 | 7 | 1 | 12 | 17 | 16 | 1 | 7 | 12 |

### Comparable scoreboard/RCON count

| Server | Explicit overlap UTC | Scoreboard games | Complete RCON pairs | Simple count deficit | Scoreboard games classified without selected RCON counterpart |
| --- | --- | ---: | ---: | ---: | ---: |
| #01 | 2026-05-19 08:10:45 – 2026-05-20 21:15:18 | 7 | 5 | 2 | 2 |
| #02 | 2026-05-18 12:45:37 – 2026-05-20 23:18:18 | 17 | 16 | 1 | 7 |

The overlap is the intersection between plausible Unix `server_time` bounds and complete scoreboard coverage, not the AdminLog observation/batch timestamp. Correlation accepts only mutual unique-best one-to-one pairs and leaves the rest unmatched rather than forcing a link: #01 has one complete RCON match without a selected scoreboard counterpart, and #02 has six. The audit therefore does not claim that the 2/7 classifications equal definitely lost AdminLog matches. The defensible local finding is: source coverage explains almost all of the all-history discrepancy; within the overlap there are real parity gaps requiring boundary/fallback repair plus CRCON reconciliation.

## 5. Boundary-sequence analysis

Events were reconstructed per target in the materializer's canonical order `server_time ASC, id ASC`, then checked in `event_timestamp, id` and `created_at, id` order.

| Server | START→END | START→START | Orphan END | Final open START | Normalized map mismatch | Raw map identity difference | `server_time` decrease in alternate wall-clock order |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| #01 | 5 | 0 | 0 | 0 | 1 | 4 | 1 by `event_timestamp`; 1 by `created_at` |
| #02 | 16 | 0 | 1 | 1 | 1 | 15 | 0 detected |

Both servers have zero duplicate-boundary identity groups/extra rows and zero same-`server_time` boundary groups/extra rows. Sanitized representative evidence is:

| Observation | Server | Event refs | Server times |
| --- | --- | --- | --- |
| normalized-map mismatch | #01 | `event-bb668ca95563` → `event-9ae2bdd7beed` | 1779267776 → 1779270761 |
| alternate wall-clock ordering decrease | #01 | `event-9ae2bdd7beed` → `event-bb668ca95563` | 1779270761 → 1779267776 |
| raw-map identity difference | #01 | `event-6b86b273ff34` → `event-785f3ec7eb32` | 1779178245 → 1779183644 |
| orphan END | #02 | `event-c6a99dc9b0b6` | 1779229516 |
| final open START | #02 | `event-374488f43bc5` | 1779319208 |
| normalized-map mismatch | #02 | `event-939d830ab955` → `event-8b0f03858cd0` | 1779229620 → 1779235020 |
| raw-map identity difference | #02 | `event-535fa30d7e25` → `event-86e501496586` | 1779108337 → 1779111786 |

#01's non-monotonic evidence means wall-clock timestamps cannot safely replace `server_time` without an explicit epoch/reset model. Several wall timestamps are batch-like (multiple boundaries share the same observation time), while their server-time bounds remain distinct. The raw-versus-normalized identity differences also show why normalized display map alone is not a match identity.

## 6. Partial/unbounded match analysis

#01 persists two lower-only rows and no upper-only row. They select eligible events beyond their starts but the snapshot has no #01 kill events, so neither meets the audit's inflation rule.

#02 persists seven lower-only rows and one upper-only row. Five lower-only rows and the upper-only row span at least two currently derivable complete matches and contain stats, so all six are confirmed inflated. Their current effective queries cross 5–19 boundary rows and 2–9 complete ranges. One additional lower-only row selects 39 kills but crosses only one complete range, and another does not meet the multi-match rule.

The upper-only row is particularly dangerous: it selects 2,705 eligible events / 2,288 kills from the beginning of stored target history through its end and crosses 13 boundaries / 6 complete matches. It is persisted with `confidence_mode='exact'` merely because an end row exists, even though the start bound is absent.

Every lower-/upper-only persisted row is reproduced below. The event refs identify the earliest/latest selected source rows without exposing content or player identity.

| Server | Match ref | Bounds | Server-time range | Events / kills | First selected event @ time | Last selected event @ time | Boundaries / complete ranges | Max K / max D / players | Inflation |
| --- | --- | --- | --- | ---: | --- | --- | ---: | ---: | --- |
| #01 | `match-bd1b31a8adf2` | lower only | 1779306318 → open | 2 / 0 | `event-d5be9d4e5687` @ 1779306318 | `event-06db9e111858` @ 1779306333 | 2 / 1 | 0 / 0 / 1 | not confirmed |
| #01 | `match-e88a6c4c6374` | lower only | 1779285573 → open | 10 / 0 | `event-9622b0acb1ca` @ 1779285573 | `event-06db9e111858` @ 1779306333 | 6 / 3 | 0 / 0 / 4 | not confirmed |
| #02 | `match-0035e811528a` | lower only | 1779301729 → open | 7,063 / 5,388 | `event-bdbd33440a14` @ 1779301732 | `event-2f30d0c88dd1` @ 1779319250 | 11 / 5 | 137 / 84 / 427 | confirmed |
| #02 | `match-217a5c391462` | upper only | missing → 1779229516 | 2,705 / 2,288 | `event-c2356069e9d1` @ 1779108337 | `event-5bb844a8a792` @ 1779229516 | 13 / 6 | 93 / 41 / 180 | confirmed |
| #02 | `match-2d63a3461812` | lower only | 1779276689 → open | 12,793 / 10,145 | `event-f69b0e3717c3` @ 1779276689 | `event-2f30d0c88dd1` @ 1779319250 | 19 / 9 | 208 / 117 / 608 | confirmed |
| #02 | `match-82f68fab9cc8` | lower only | 1779310451 → open | 2,970 / 2,370 | `event-a66a5366bf70` @ 1779310460 | `event-2f30d0c88dd1` @ 1779319250 | 5 / 2 | 81 / 50 / 192 | confirmed |
| #02 | `match-99de224345eb` | lower only | 1779285619 → open | 12,787 / 10,145 | `event-87b4d74dba97` @ 1779285619 | `event-2f30d0c88dd1` @ 1779319250 | 17 / 8 | 208 / 117 / 607 | confirmed |
| #02 | `match-cb9cdd24c924` | lower only | 1779315955 → open | 146 / 39 | `event-d51d98838905` @ 1779315957 | `event-2f30d0c88dd1` @ 1779319250 | 3 / 1 | 8 / 5 / 62 | not confirmed |
| #02 | `match-e3eee55a6498` | lower only | 1779291122 → open | 12,456 / 9,908 | `event-53b1751856e3` @ 1779291131 | `event-2f30d0c88dd1` @ 1779319250 | 15 / 7 | 208 / 101 / 595 | confirmed |
| #02 | `match-e6b8d8bafadc` | lower only | 1779319208 → open | 1 / 0 | `event-2f30d0c88dd1` @ 1779319250 | `event-2f30d0c88dd1` @ 1779319250 | 1 / 0 | 0 / 0 / 1 | not confirmed |

## 7. Inflated-stat analysis

The confirmation rule is conservative: a partial row is called inflated only when its current selection spans at least two derived complete matches. Six #02 rows satisfy that rule; #01 has zero. This proves interval leakage independently of any subjective “high kill” threshold.

| Match ref | Server | Bounds | Map | Selected events | Selected kills | Complete ranges crossed | Boundaries | Max player kills | Players |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `match-2d63a3461812` | #02 | lower only | Mortain | 12,793 | 10,145 | 9 | 19 | 208 | 608 |
| `match-99de224345eb` | #02 | lower only | Utah Beach | 12,787 | 10,145 | 8 | 17 | 208 | 607 |
| `match-e3eee55a6498` | #02 | lower only | St. Marie Du Mont | 12,456 | 9,908 | 7 | 15 | 208 | 595 |
| `match-0035e811528a` | #02 | lower only | Utah Beach | 7,063 | 5,388 | 5 | 11 | 137 | 427 |
| `match-82f68fab9cc8` | #02 | lower only | Foy | 2,970 | 2,370 | 2 | 5 | 81 | 192 |
| `match-217a5c391462` | #02 | upper only | Carentan | 2,705 | 2,288 | 6 | 13 | 93 | 180 |

No row near 300 maximum player kills is present locally; the worst is 208. Thus the mechanism is confirmed and capable of generating extreme totals, but the concrete production ~300 example and its exact event range remain unresolved.

## 8. Event-to-match overlap

The diagnostic built an in-memory event-ID-to-active-match sweep using the exact inclusive range rules. Boundary rows were excluded from the eligible-event denominator, matching the stat query. For each materialized row, the diagnostic also records the deterministic selected count and sanitized first/last source-event references and server times; this defines the exact raw selection without exposing messages or player identity. For example, `match-2d63a3461812` selects all 12,793 eligible rows satisfying `server_time >= 1779276689` through the snapshot tail at `1779319250`, from `event-f69b0e3717c3` to `event-2f30d0c88dd1`.

| Server | Eligible events | Assigned 0 | Assigned exactly 1 | Assigned >1 | Kill events | Kills assigned >1 | Maximum multiplicity |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| #01 | 38 | 2 | 26 | 10 | 0 | 0 | 3 |
| #02 | 16,060 | 71 | 3,140 | 12,849 | 12,776 | 10,146 | 7 |

The #01 maximum-overlap example is `event-d5be9d4e5687` at 1779306318, selected by `match-81825f178805`, `match-bd1b31a8adf2`, and `match-e88a6c4c6374`. The #02 example is `event-d51d98838905` at 1779315957, selected by `match-0035e811528a`, `match-2d63a3461812`, `match-4f6a7be66803`, `match-82f68fab9cc8`, `match-99de224345eb`, `match-cb9cdd24c924`, and `match-e3eee55a6498`.

The 12,849 and 10,146 figures count unique source event rows that satisfy multiple match predicates; they are not duplicated database rows. This confirms hypothesis C on #02 and confirms non-kill overlap on #01.

## 9. Statistical invariants

For every both-bound row, the diagnostic computed `K = count(event_type='kill')` and checked:

```text
SUM(kills) + SUM(teamkills) == K
SUM(deaths) == K
```

| Server | Both-bound matches checked | Kill/TK invariant passed | Death invariant passed | Violations |
| --- | ---: | ---: | ---: | ---: |
| #01 | 5 | 5 | 5 | 0 |
| #02 | 16 | 16 | 16 | 0 |

The diagnostic's `match_statistics` collection contains these fields for every persisted match. Aggregate ranges for the 21 both-bound rows are:

| Server | Matches | Total K / D / TK | Max player K / D | Max players | Duration range | Max whole-match KPM | Max player KPM |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| #01 | 5 | 0 / 0 / 0 | 0 / 0 | 5 | 2,985–5,400s | 0.000 | 0.000 |
| #02 | 16 | 10,489 / 10,489 / 0 | 137 / 56 | 226 | 1,123–5,400s | 29.868 | 1.522 |

This proves internal arithmetic consistency for the stored `kill` rows. It does not prove source completeness: 299 explicit `TEAM KILL` rows are outside `K` because the current parser stored them as `unknown`. Whole-match and player KPM are reported only where both bounds provide a meaningful duration; partial rows deliberately have no KPM.

## 10. Worst affected matches

All references are sanitized hashes. The persisted `confidence_mode` is shown even when it conflicts with the structural bounds. The table is ordered by maximum player kills; the diagnostic also emits a separate deterministic top 20 by total player kills.

| Rank | Server | Match ref | Map | Basis / persisted confidence | Bounds | Start → end UTC | Server-time bounds | Max K | Event/total K | Boundaries | Scoreboard |
| ---: | --- | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | --- |
| 1 | #02 | `match-2d63a3461812` | Mortain | start / partial | lower only | 2026-05-20 12:45:16 → open | 1779276689 → open | 208 | 10,145 / 10,145 | 19 | unavailable: partial |
| 2 | #02 | `match-99de224345eb` | Utah Beach | start / partial | lower only | 2026-05-20 14:05:18 → open | 1779285619 → open | 208 | 10,145 / 10,145 | 17 | unavailable: partial |
| 3 | #02 | `match-e3eee55a6498` | St. Marie Du Mont | start / partial | lower only | 2026-05-20 15:38:40 → open | 1779291122 → open | 208 | 9,908 / 9,908 | 15 | unavailable: partial |
| 4 | #02 | `match-0035e811528a` | Utah Beach | start / partial | lower only | 2026-05-20 18:41:59 → open | 1779301729 → open | 137 | 5,388 / 5,388 | 11 | unavailable: partial |
| 5 | #02 | `match-48c6a13a9cb1` | Utah Beach | ended / exact | both | 2026-05-20 18:41:59 → 20:56:31 | 1779301729 → 1779307129 | 137 | 2,570 / 2,570 | 2 | exact |
| 6 | #02 | `match-8056b1224e3e` | St. Marie Du Mont | ended / exact | both | 2026-05-20 15:38:40 → 17:04:24 | 1779291122 → 1779296521 | 99 | 2,031 / 2,031 | 2 | exact |
| 7 | #02 | `match-9a642726a437` | Carentan | ended / exact | both | 2026-05-20 17:04:24 → 18:41:59 | 1779296626 → 1779301626 | 98 | 2,489 / 2,489 | 2 | exact |
| 8 | #02 | `match-217a5c391462` | Carentan | ended / exact | upper only | missing → 2026-05-20 12:45:16 | missing → 1779229516 | 93 | 2,288 / 2,288 | 13 | unavailable: partial |
| 9 | #02 | `match-60b89246d95c` | Foy | ended / exact | both | 2026-05-20 20:56:31 → 22:30:50 | 1779310451 → 1779315851 | 81 | 2,331 / 2,331 | 2 | exact |
| 10 | #02 | `match-82f68fab9cc8` | Foy | start / partial | lower only | 2026-05-20 20:56:31 → open | 1779310451 → open | 81 | 2,370 / 2,370 | 5 | unavailable: partial |
| 11 | #02 | `match-e0c707448100` | Tobruk Warfare | ended / exact | both | 2026-05-20 12:45:16 → 12:45:16 | 1779229620 → 1779235020 | 38 | 343 / 343 | 2 | exact |
| 12 | #02 | `match-e7e9307a560f` | Utah Beach | ended / exact | both | 2026-05-20 14:05:18 → 15:38:40 | 1779285619 → 1779291018 | 29 | 237 / 237 | 2 | exact |
| 13 | #02 | `match-35059e43a329` | St. Marie Du Mont | ended / exact | both | 2026-05-20 20:56:31.781 → 20:56:31.782 | 1779308695 → 1779310348 | 20 | 322 / 322 | 2 | exact |
| 14 | #02 | `match-c213ba0a4fde` | Purple Heart Lane | ended / exact | both | 2026-05-20 20:56:31.781 → 20:56:31.781 | 1779307233 → 1779308591 | 20 | 126 / 126 | 2 | exact |
| 15 | #02 | `match-4f6a7be66803` | Kharkov | ended / exact | both | 2026-05-20 22:30:50 → 23:21:45 | 1779315955 → 1779319098 | 8 | 39 / 39 | 2 | no counterpart |
| 16 | #02 | `match-cb9cdd24c924` | Kharkov | start / partial | lower only | 2026-05-20 22:30:50 → open | 1779315955 → open | 8 | 39 / 39 | 3 | unavailable: partial |
| 17 | #02 | `match-9dc374320263` | Carentan | ended / exact | both | 2026-05-19 11:16:10 → 11:16:10 | 1779178461 → 1779183861 | 1 | 1 / 1 | 2 | exact |
| 18 | #02 | `match-01c2293147ed` | Foy | session / partial | none | 2026-03-27 11:59:36 → 12:20:15 | none | 0 | 0 / 0 | 0 | session-only |
| 19 | #01 | `match-039560fb4d1d` | Tobruk Warfare Morning | session / partial | none | 2026-03-31 09:58:14 → 10:08:23 | none | 0 | 0 / 0 | 0 | session-only |
| 20 | #02 | `match-0faf5ecce539` | St. Marie Du Mont | ended / exact | both | 2026-05-19 11:16:10 → 11:16:10 | 1779108337 → 1779111786 | 0 | 0 / 0 | 2 | no counterpart |

The separate ranking by total player kills is below. Its membership is identical to the preceding top-20 table, where every row's map, basis/confidence, timestamps, server-time bounds, event-kill count, boundary count, partial classification, and scoreboard correlation are reported; `match_ref` provides the exact cross-reference.

| Rank | Server | Match ref | Total K | Max K | Bounds | Scoreboard |
| ---: | --- | --- | ---: | ---: | --- | --- |
| 1 | #02 | `match-2d63a3461812` | 10,145 | 208 | lower only | unavailable: partial |
| 2 | #02 | `match-99de224345eb` | 10,145 | 208 | lower only | unavailable: partial |
| 3 | #02 | `match-e3eee55a6498` | 9,908 | 208 | lower only | unavailable: partial |
| 4 | #02 | `match-0035e811528a` | 5,388 | 137 | lower only | unavailable: partial |
| 5 | #02 | `match-48c6a13a9cb1` | 2,570 | 137 | both | exact |
| 6 | #02 | `match-9a642726a437` | 2,489 | 98 | both | exact |
| 7 | #02 | `match-82f68fab9cc8` | 2,370 | 81 | lower only | unavailable: partial |
| 8 | #02 | `match-60b89246d95c` | 2,331 | 81 | both | exact |
| 9 | #02 | `match-217a5c391462` | 2,288 | 93 | upper only | unavailable: partial |
| 10 | #02 | `match-8056b1224e3e` | 2,031 | 99 | both | exact |
| 11 | #02 | `match-e0c707448100` | 343 | 38 | both | exact |
| 12 | #02 | `match-35059e43a329` | 322 | 20 | both | exact |
| 13 | #02 | `match-e7e9307a560f` | 237 | 29 | both | exact |
| 14 | #02 | `match-c213ba0a4fde` | 126 | 20 | both | exact |
| 15 | #02 | `match-4f6a7be66803` | 39 | 8 | both | no counterpart |
| 16 | #02 | `match-cb9cdd24c924` | 39 | 8 | lower only | unavailable: partial |
| 17 | #02 | `match-9dc374320263` | 1 | 1 | both | exact |
| 18 | #02 | `match-01c2293147ed` | 0 | 0 | none | session-only |
| 19 | #01 | `match-039560fb4d1d` | 0 | 0 | none | session-only |
| 20 | #02 | `match-0faf5ecce539` | 0 | 0 | both | no counterpart |

Duration anomalies use the population of positive-duration, both-bound rows grouped per server, with `match_ref` as the final deterministic tie-break. All 20 rows below have persisted confidence `exact`. The score is `abs(duration - median) / max(MAD, 1)`; a zero MAD makes some scores numerically large, so it is a ranking device rather than proof of corruption. Wall-clock timestamps can be batch timestamps and can even be reversed relative to server-time order.

| Rank | Server | Match ref | Map | Bounds / basis | Wall start → end UTC | Server-time bounds | Duration s | MAD score | Max K | Event K | Boundaries | Scoreboard |
| ---: | --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | #02 | `match-7b259c196b3b` | Carentan | both / ended | 2026-05-19 11:16:10 → same | 1779129266 → 1779130389 | 1,123 | 8,553 | 0 | 0 | 2 | no counterpart |
| 2 | #02 | `match-c213ba0a4fde` | Purple Heart Lane | both / ended | 2026-05-20 20:56:31.781 → same | 1779307233 → 1779308591 | 1,358 | 8,083 | 20 | 126 | 2 | exact |
| 3 | #02 | `match-35059e43a329` | St. Marie Du Mont | both / ended | 2026-05-20 20:56:31.781 → 20:56:31.782 | 1779308695 → 1779310348 | 1,653 | 7,493 | 20 | 322 | 2 | exact |
| 4 | #02 | `match-4f6a7be66803` | Kharkov | both / ended | 2026-05-20 22:30:50 → 23:21:45 | 1779315955 → 1779319098 | 3,143 | 4,513 | 8 | 39 | 2 | no counterpart |
| 5 | #02 | `match-0faf5ecce539` | St. Marie Du Mont | both / ended | 2026-05-19 11:16:10 → same | 1779108337 → 1779111786 | 3,449 | 3,901 | 0 | 0 | 2 | no counterpart |
| 6 | #01 | `match-1649c8a8e294` | Sainte Mère Église Warfare | both / ended | 2026-05-20 12:45:15 → 10:30:01 | 1779267776 → 1779270761 | 2,985 | 2,415 | 0 | 0 | 2 | no counterpart |
| 7 | #02 | `match-9a642726a437` | Carentan | both / ended | 2026-05-20 17:04:24 → 18:41:59 | 1779296626 → 1779301626 | 5,000 | 799 | 98 | 2,489 | 2 | exact |
| 8 | #02 | `match-2cc1f38a4e49` | Mortain | both / ended | 2026-05-20 12:45:16 → 13:05:09 | 1779276689 → 1779282089 | 5,400 | 1 | 0 | 0 | 2 | exact |
| 9 | #02 | `match-48c6a13a9cb1` | Utah Beach | both / ended | 2026-05-20 18:41:59 → 20:56:31 | 1779301729 → 1779307129 | 5,400 | 1 | 137 | 2,570 | 2 | exact |
| 10 | #01 | `match-52d9de02db96` | Utah Beach | both / ended | 2026-05-19 11:16:10 → same | 1779178245 → 1779183644 | 5,399 | 1 | 0 | 0 | 2 | exact |
| 11 | #02 | `match-60b89246d95c` | Foy | both / ended | 2026-05-20 20:56:31 → 22:30:50 | 1779310451 → 1779315851 | 5,400 | 1 | 81 | 2,331 | 2 | exact |
| 12 | #02 | `match-7b2b7d2a7f99` | Utah Beach | both / ended | 2026-05-19 11:16:10 → same | 1779140535 → 1779145935 | 5,400 | 1 | 0 | 0 | 2 | no counterpart |
| 13 | #02 | `match-8056b1224e3e` | St. Marie Du Mont | both / ended | 2026-05-20 15:38:40 → 17:04:24 | 1779291122 → 1779296521 | 5,399 | 1 | 99 | 2,031 | 2 | exact |
| 14 | #02 | `match-9dc374320263` | Carentan | both / ended | 2026-05-19 11:16:10 → same | 1779178461 → 1779183861 | 5,400 | 1 | 1 | 1 | 2 | exact |
| 15 | #02 | `match-a2265a9767f0` | Utah Beach | both / ended | 2026-05-19 11:16:10 → same | 1779118879 → 1779124279 | 5,400 | 1 | 0 | 0 | 2 | no counterpart |
| 16 | #02 | `match-e07ef971eb68` | St. Marie Du Mont | both / ended | 2026-05-19 11:16:10 → same | 1779130494 → 1779135894 | 5,400 | 1 | 0 | 0 | 2 | no counterpart |
| 17 | #02 | `match-e0c707448100` | Tobruk Warfare | both / ended | 2026-05-20 12:45:16 → same | 1779229620 → 1779235020 | 5,400 | 1 | 38 | 343 | 2 | exact |
| 18 | #02 | `match-e7e9307a560f` | Utah Beach | both / ended | 2026-05-20 14:05:18 → 15:38:40 | 1779285619 → 1779291018 | 5,399 | 1 | 29 | 237 | 2 | exact |
| 19 | #01 | `match-24d1cc75efa1` | Utah Beach | both / ended | 2026-05-20 14:05:17 → 15:38:39 | 1779285573 → 1779290973 | 5,400 | 0 | 0 | 0 | 2 | exact |
| 20 | #01 | `match-81825f178805` | St. Marie Du Mont | both / ended | 2026-05-20 19:46:26 → 21:16:46 | 1779306318 → 1779311718 | 5,400 | 0 | 0 | 0 | 2 | exact |

## 11. Session fallback suppression

| Server | All windows | Repeated-map groups | Windows in repeated groups | Suppressed by `(server,map)` | Temporally overlap exact | Temporally distant candidate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| #01 | 24 | 6 | 24 | 14 | 5 | 9 |
| #02 | 28 | 6 | 25 | 23 | 8 | 14 |

The suppression mechanism is confirmed. One additional #02 window is within one hour of, but does not overlap, the exact row sharing its normalized map. The 9 and 14 distant windows are stronger omission candidates because their session times do not overlap the exact row that caused suppression, but a competitive window is not independently equivalent to one real match. They remain probable missing-match candidates pending CRCON/time correlation.

## 12. 100-window truncation

There are 52 windows globally: all 24 #01 and all 28 #02 windows fall inside the deterministic newest-100 selection. Zero are excluded, and there is no cutoff tie. Hypothesis E is rejected for this local snapshot. It remains a confirmed code risk and production impact is unresolved because production has not been counted.

The limit is global rather than per target, so any production execution must report both total exclusion and server distribution at the cutoff, including ties in the production `ORDER BY` fields.

## 13. Competitive-window merging

| Server | Same-map sample pairs with gap ≤1,800s | Max window duration | Windows >2h | Windows with boundary | Windows with ≥2 boundaries | Windows with ≥4 | Max boundaries / complete pairs | Minimum extra rounds evidenced |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| #01 | 851 | 21,188s (5.89h) | 5 | 4 | 1 | 0 | 2 / 1 | 0 |
| #02 | 838 | 21,188s (5.89h) | 5 | 1 | 0 | 0 | 1 / 0 | 0 |

The code mechanism is confirmed: same-normalized-map observations within 1,800 seconds extend the stored window. The audited merge signals were explicitly zero on both servers for negative gaps, raw-map identity changes, mode changes, score-reset candidates, windows with raw-map changes, windows with mode changes, windows with score resets, and windows with multiple merge signals. Separate layer identity was unavailable as a source field. Local multi-round impact is not proven. Using AdminLog `server_time`, #01 has one window with two boundaries / one complete pair and #02 has no window with two or more boundaries. The earlier batch-timestamp comparison was invalid because many historical rows share observation timestamps despite distinct server times.

## 14. Parser findings

`backend/app/rcon_admin_log_parser.py:25-49,135-171` uses strict, case-sensitive boundary expressions and recognizes only `KILL:` for combat. The parser prefix expression and storage canonicalizer also differ: the parser does not strip leading whitespace and requires a non-empty relative segment, while canonicalization strips and accepts a broader prefix (`backend/app/rcon_admin_log_storage.py:279-285`). This is a code-level risk for boundary-like rows with null `server_time`.

Local evidence:

| Server | Unknown total | Boundary-like candidates | Missed START/END | Explicit `TEAM KILL` unknown | Null-time candidates | Reparse became non-unknown |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| #01 | 2 | 2 | 0 | 2 | 0 | 0 |
| #02 | 299 | 297 | 0 | 297 | 0 | 0 |

Thus parser-missed match boundaries are rejected locally, while the explicit team-kill variant gap is confirmed. Reparse remains `unknown` because the audit intentionally uses current parser behavior and does not patch it. The two remaining #02 unknown rows do not match the requested sanitized signatures. No raw content or player identity was emitted.

## 15. Dedupe findings

The persisted identity is `(target_key, server_time, canonical_message)`, excluding `event_timestamp`. SQLite ingestion performs `WHERE NOT EXISTS` with `server_time IS ?`; its checked effective index exists but is **not unique** (`backend/app/rcon_admin_log_storage.py:138-176,279-307`). Checked-in PostgreSQL DDL uses `UNIQUE NULLS NOT DISTINCT` (`backend/app/postgres_rcon_storage.py:119-123,401-405`), but the deployed production constraint was not accessible.

| Server | Duplicate identity groups | Extra persisted rows | Max group | Null `server_time` | Possible legacy raw-canonical drift |
| --- | ---: | ---: | ---: | ---: | ---: |
| #01 | 0 | 0 | 0 | 0 | 0 |
| #02 | 0 | 0 | 0 | 0 | 0 |

Exact in-memory recanonicalization matched all 90 #01 and 21,152 #02 stored rows; canonical drift, legacy raw-canonical signatures, and null-`server_time` rows were all zero. The SQLite migration path backfills old canonical values with `raw_message`, rather than recanonicalizing, but this snapshot has no detected drift signature. There is no row-level ledger of observations rejected by dedupe. Different polling timestamps are explicitly not treated as proof of distinct events; repository tests intentionally expect a changed poll timestamp with the same server time/body to dedupe. Legitimate collision loss therefore remains unresolved and needs a raw pre-persistence batch, independent AdminLog capture, or aggregate reject telemetry with sufficient dimensions.

## 16. Stale materialized rows

The diagnostic reconstructed current boundary/fallback keys and compared them with persisted keys.

| Server | Persisted | Currently derivable | Not currently derivable | Stale start-only | Stale end-only | Other stale | Not-derivable fallback | Derived now but missing persisted | Stale bounded rows sharing kills | Stale fallback overlapping exact |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| #01 | 22 | 15 | 7 | 2 | 0 | 0 | 5 | 0 | 0 | 2 |
| #02 | 36 | 23 | 13 | 6 | 0 | 0 | 7 | 0 | 6 | 3 |

The six stale #02 bounded rows select a summed 37,995 kills under current predicates and share kills with current complete ranges. Because the stale ranges overlap, 37,995 is a repeated-selection sum, not a unique-kill count. A fallback outside today's top-100 is not automatically obsolete; the report uses the cautious label “not currently derivable” unless temporal overlap establishes stronger evidence.

## 17. Acquisition gaps

All local AdminLog rows predate the TASK-271 live/historical split reference `2026-06-22T13:16:19Z`; there are zero post-split events in the snapshot. Therefore a pre/post causal comparison is unavailable.

| Server | Distinct `created_at` batches | Gaps >600s | >900s | >3,600s | Maximum gap | Pre-split events | Post-split events |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| #01 | 10 | 9 | 8 | 7 | 83,632s, 2026-05-19 11:16:11 → 2026-05-20 10:30:03 UTC | 90 | 0 |
| #02 | 87 | 40 | 5 | 2 | 91,738s, 2026-05-19 11:16:11 → 2026-05-20 12:45:09 UTC | 21,152 | 0 |

No durable worker-run/poll checkpoint ledger exists in the snapshot. An interval without stored events does not prove a failed poll, so these are gap signals rather than lost-event counts. Code/config history nevertheless makes acquisition loss possible: the production-style historical cadence was 900 seconds after TASK-271 while configured lookback was 10 minutes, and the pre-split heavy cycle was documented at 15–30 minutes. A single `GetAdminLog` call has no durable cursor/pagination checkpoint. Production run history or an independent raw capture is required to confirm missing source intervals.

## 18. CRCON/public-scoreboard parity

The comparison reads full persisted `historical_matches` joined to `historical_servers`, not the bounded correlation-candidate cache. The global inventory is 9,845 persisted rows: 9,562 trusted #01/#02 rows and 283 excluded other/#03 rows. It restricts comparison to explicit AdminLog overlap, requires the same normalized map, applies the repository-style temporal score, and accepts only mutual unique-best one-to-one assignments; ties remain ambiguous.

| Server | Overlap UTC | Scoreboard | Complete RCON | Competitive windows ended in range / overlapping | Exact correlation | Partial/session-only | Scoreboard missing RCON | Ambiguous | RCON without selected scoreboard |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| #01 | 2026-05-19 08:10:45 – 2026-05-20 21:15:18 | 7 | 5 | 7 / 8 | 4 | 1 | 2 | 0 | 1 |
| #02 | 2026-05-18 12:45:37 – 2026-05-20 23:18:18 | 17 | 16 | 11 / 11 | 10 | 0 | 7 | 0 | 6 |

“Ended in range” counts windows whose `last_seen_at` is inside the inclusive overlap; “overlapping” counts any interval intersecting it. Both are shown because competitive windows are observation-time evidence while RCON bounds use server time.

Parity is **not achieved**. These are local public-scoreboard correlations, not a live CRCON API assertion. The results show both missing/partial RCON coverage and RCON rows without a confident scoreboard partner, so repair must improve identity and preserve ambiguity rather than forcing links.

## 19. Root-cause table

Counts and confidence in this table apply only to the representative local SQLite snapshot. Every production count is unresolved.

| Root cause | #01 affected | #02 affected | Missing matches | Inflated matches | Confidence |
| --- | ---: | ---: | ---: | ---: | --- |
| orphan END unbounded stats | 0 rows | 1 row | 0 evidenced | 0 / 1 | confirmed |
| open/stale START unbounded stats | 2 stale rows | 7 rows (6 stale, 1 current open) | 0 evidenced | 0 / 5 | confirmed |
| overlapping partial ranges | 10 eligible events | 12,849 eligible / 10,146 kills | n/a | 0 / 6 partial rows | confirmed |
| map-only fallback suppression | 14 windows (9 distant) | 23 windows (14 distant, 1 within 1h) | 9 / 14 candidates | n/a | probable |
| fallback limit 100 | 0 | 0 | 0 / 0 | n/a | rejected |
| 30-minute map merge | 1 window with 2 boundaries / 1 pair | 0 multi-boundary windows | unresolved contribution | 0 directly attributed | possible |
| parser missed boundaries | 0 | 0 | 0 / 0 | 0 / 0 | rejected |
| dedupe collision | unknown | unknown | unknown | unknown | unresolved |
| stale materialized rows | 7 | 13 | 0 directly | 5 confirmed inflated; 6 stale bounded rows share kills | confirmed |
| AdminLog acquisition gaps | 9 gaps >600s | 40 gaps >600s | unknown | unknown | possible |

“Probable” map suppression means the code definitely suppresses the listed windows and temporal separation makes omission likely, but no independent match ledger proves every candidate. The 30-minute extension mechanism is confirmed in code, while local multi-round loss is not evidenced after comparing on server time. Explicit `TEAM KILL` parser loss is confirmed but is not a boundary/match-count cause in this snapshot.

## 20. Confirmed vs probable vs unresolved causes

### Confirmed locally

- A: one #02 orphan END creates an upper-only range and one confirmed inflated row.
- B: stale lower-only starts remain; five #02 rows span multiple complete matches and inflate stats.
- C: independent inclusive predicates assign 12,849 #02 eligible events, including 10,146 kills, to multiple rows.
- G (team-kill subcase): 2 #01 and 297 #02 explicit team kills are `unknown`.
- I: 7 #01 and 13 #02 persisted rows are no longer derivable; six #02 bounded rows reuse kills.
- Complete scoreboard history greatly exceeds AdminLog coverage; source coverage is the dominant all-history limitation in this snapshot.

### Probable or possible locally

- D is probable: 9 #01 and 14 #02 map-suppressed windows are temporally distant candidates.
- J is possible: long batch gaps plus cadence/lookback design expose an acquisition gap, but there is no poll ledger.
- F is a confirmed code mechanism but only a possible local cause: no window holds more than one complete server-time boundary pair.

### Rejected locally

- E: zero windows fall beyond the global newest 100.
- G boundary subcase: zero stored unknown rows resemble missed START/END boundaries.
- Statistical-arithmetic corruption in both-bound rows: all 21 checked rows pass both invariants.

### Unresolved

- All production counts and the concrete approximately 300-kill row.
- H legitimate dedupe collision loss and deployed PostgreSQL constraint semantics.
- Exact number of source events/matches lost to acquisition gaps.
- Whether every temporally distant fallback candidate is a real match.
- Post-TASK-271 source coverage and improvement/regression.

## 21. Recommended remediation architecture

Do not repair data until the following production behavior is implemented and validated:

1. Introduce a canonical `match_instance_id` whose identity is stable when boundaries arrive. Preserve raw map/layer/mode separately from normalized display map.
2. Require both finite, ordered bounds before emitting “exact” player statistics. Partial rows may exist for observability but must not select an infinite event range or be exposed as exact.
3. Assign each eligible event to at most one trusted match instance. Persist or deterministically derive the association; reject/flag ambiguous overlap instead of independently scanning every row.
4. Infer missing boundaries only within safe adjacent boundaries, explicit map/layer/mode transitions, server-time epochs, and bounded wall-clock limits. Never substitute unbounded history.
5. Replace `(server, normalized_map)` fallback suppression with temporal/session correlation. Remove the arbitrary global 100-window materialization cap; pagination must be deterministic and per-source coverage must be explicit.
6. Split competitive windows on canonical round identity signals: boundary pairs, raw layer/mode transition, score reset, server-time epoch, or a validated maximum gap. Normalized display map alone is insufficient.
7. Make materialization a reconciliation: compute the desired key set, upsert desired rows, and retire obsolete rows transactionally with auditable reasons. A dry-run diff is mandatory before destructive cleanup.
8. Normalize parser prefix/boundary/team-kill variants through one shared parser/canonicalizer contract. Add ingestion dedupe telemetry or a privacy-safe observation ledger sufficient to distinguish poll duplicates from possible collisions.
9. Add durable acquisition watermarks/checkpoints and explicit gap health. The live ingest loop must not rely only on a lookback shorter than a possible scheduling delay.
10. Use persisted full scoreboard/CRCON history as independent reconciliation evidence, not as a silent replacement for RCON identity and not via a bounded candidate cache.

## 22. Historical data repair/rematerialization strategy

After code fixes pass validation, perform a controlled production operation in this order:

1. Take a recoverable database backup and freeze the audited input coverage/watermarks.
2. Run the read-only diagnostic on deployed PostgreSQL and archive only sanitized aggregate output.
3. Build the new canonical boundary/event-assignment result in an isolated shadow namespace or offline export; do not mutate current rows.
4. Compare old/new match keys, event assignments, stats, fallback candidates, and scoreboard correlations. Require explicit review of every ambiguous or partial interval.
5. Reparse raw events with the versioned parser while preserving original rows and parser version/provenance.
6. Backfill canonical match instances and bounded event associations chronologically per server/epoch. Keep unresolvable gaps as degraded, never “exact”.
7. Recompute stats once from exclusive event assignments; enforce invariants and overlap gates.
8. Reconcile against complete scoreboard coverage and quantify exact/partial/missing/ambiguous results.
9. Switch reads only after a reviewed shadow-versus-current report passes the criteria below.
10. Retire stale partial/fallback rows only in a separate authorized migration with rollback, audit records, and backup retention.

TASK-287 performs none of these mutations.

## 23. Dependency ordering with TASK-272–281

Recommended order, without creating or executing any task:

1. Review TASK-287 and reproduce its production counts read-only.
2. Refine/freeze TASK-272 so its current-match contract incorporates canonical historical identity, server-time epochs, partial/degraded states, and exclusive event assignment.
3. Implement a dedicated canonical historical boundary/match-identity repair.
4. Execute TASK-274's shared parser normalization under that contract; coordinate ownership so historical and live paths use one parser/canonicalizer.
5. Implement the bounded historical materializer, temporal fallback, stale-row reconciliation, and acquisition checkpoint/gap observability.
6. Run a separately authorized controlled rematerialization/backfill and CRCON reconciliation.
7. Proceed with live lifecycle work: TASK-273, then TASK-275 → TASK-276 → TASK-277 → TASK-278 → TASK-279 → TASK-280 → TASK-281.

TASK-272 may absorb this evidence now, but should not freeze a contradictory contract. TASK-273 and TASK-275–281 should wait for the historical boundary/identity decisions; TASK-274 can be coordinated earlier but must precede rematerialization. TASK-284 is unrelated baseline-validation debt and remains on an independent path.

## 24. Validation criteria for trustworthy historical data

Historical data should not be declared trustworthy until all of the following pass per server and explicit coverage window:

- 100% of rows exposed as exact have two finite, ordered bounds and a stable canonical match instance.
- Every eligible source event has zero or one trusted match assignment; any zero/ambiguous assignment is counted and explained. No kill event is assigned to more than one exact match.
- For every exact match, `SUM(kills)+SUM(teamkills)=K` and `SUM(deaths)=K`; explicit team-kill fixtures and stored variants are included in `K` under the versioned parser contract.
- Repeated materialization produces the same key set and stats and leaves no stale partial/fallback rows.
- Fallback materialization is paginated without an arbitrary global cutoff and correlates by server, time/session, raw layer/mode, and boundary evidence rather than map alone.
- Competitive windows cannot contain more than one validated boundary pair unless explicitly classified as a multi-round aggregate and excluded from match parity.
- Acquisition has durable per-target watermark/run evidence; all gaps larger than lookback are surfaced and no period is silently called complete.
- Effective PostgreSQL/SQLite dedupe constraints are introspected and tested, null semantics are explicit, and collision/reject telemetry is privacy-safe.
- CRCON/public-scoreboard comparison uses identical coverage and complete persisted history; every game is deterministically classified exact, partial, missing, or ambiguous, with no forced link.
- Production dry-run totals, overlap counts, top-20 anomalies, parser signatures, stale-key diff, and hashes are reproducible across two read-only runs.
- No secrets, raw chat, names, or platform IDs appear in audit artifacts.

The diagnostic command used for local evidence was:

```powershell
python scripts/audit_rcon_match_materialization.py `
  --sqlite backend/data/hll_vietnam_dev.sqlite3 `
  --sqlite-immutable `
  --target-config-env-file .env `
  --task271-split-at 2026-06-22T13:16:19Z `
  --max-sanitized-examples 5 `
  --format json `
  --output $env:TEMP\task287-audit-local.json
```

Two final runs were byte-identical. Their deterministic JSON SHA-256 was `5d5066e76269b9cdd962964f29e81653fa356399d7ce54a7498b85c7c9da0044`. Seventeen focused tests exercise SQL rejection, boundary state, inclusive overlap, duration selection, server-time coverage filtering, date filtering, privacy sanitation, scoreboard scoring, top-100 cutoff ties, and unchanged SQLite hash/size/mtime.
