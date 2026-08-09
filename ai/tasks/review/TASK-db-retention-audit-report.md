---
id: TASK-db-retention-audit-report
source_task: TASK-db-retention-audit
status: review
type: report
---

# Database Retention Audit

## Scope

This report audits the current storage model used by HLL Vietnam for:

- live server snapshots;
- public-scoreboard historical matches and player stats;
- RCON AdminLog events and materialized matches;
- displayed historical snapshots;
- player event raw ledger;
- paused Elo/MMR storage surfaces.

Confirmed facts below are based on the current repository code, not on assumptions.

## Files Inspected

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `backend/app/config.py`
- `backend/app/historical_runner.py`
- `backend/app/historical_storage.py`
- `backend/app/historical_snapshot_storage.py`
- `backend/app/player_event_aggregates.py`
- `backend/app/player_event_storage.py`
- `backend/app/postgres_display_storage.py`
- `backend/app/postgres_rcon_storage.py`
- `backend/app/rcon_admin_log_materialization.py`
- `backend/app/rcon_admin_log_storage.py`
- `backend/app/rcon_historical_backfill.py`
- `backend/app/rcon_historical_leaderboards.py`
- `backend/app/rcon_historical_read_model.py`
- `backend/app/rcon_historical_worker.py`
- `backend/app/writer_lock.py`

## Confirmed Storage Areas

### Live and displayed data

- `server_snapshots`
  - Present in SQLite live storage and PostgreSQL displayed storage.
  - Used for live/current server status history.
- `displayed_historical_snapshots`
  - PostgreSQL primary key is `(server_key, snapshot_type, metric, snapshot_window)`.
  - Persistence uses upsert semantics, so normal operation is already bounded by logical identity.

### Public-scoreboard historical fallback

- `historical_servers`
- `historical_maps`
- `historical_matches`
- `historical_players`
- `historical_player_match_stats`
- `historical_ingestion_runs`
- `historical_backfill_progress`

These remain part of the displayed historical fallback/read path.

### RCON historical primary path

- `rcon_historical_targets`
- `rcon_historical_capture_runs`
- `rcon_historical_samples`
- `rcon_historical_checkpoints`
- `rcon_historical_competitive_windows`
- `rcon_admin_log_events`
- `rcon_player_profile_snapshots`
- `rcon_materialized_matches`
- `rcon_match_player_stats`
- `rcon_scoreboard_match_candidates`

### Player-event ledger

- `player_event_raw_ledger`
- `player_event_ingestion_runs`
- `player_event_backfill_progress`

### Elo/MMR paused surfaces

Confirmed in backend documentation and runtime payloads as preserved but paused.
This audit did not find cleanup code or explicit retention logic for Elo/MMR tables in the task’s read-first files, so they should stay out of cleanup scope.

## Snapshot Boundedness Findings

### `displayed_historical_snapshots`

Confirmed bounded in PostgreSQL by primary key plus upsert:

- same logical snapshot identity overwrites previous payload;
- normal scheduled refresh does not append unlimited rows;
- routine cleanup is not required for healthy records.

Safe policy:

- do not bulk-delete this table in the first maintenance command;
- only report suspicious legacy/corrupt rows if found later.

### File-based snapshots

Confirmed bounded by deterministic file paths under `backend/data/snapshots/<server>/...`.
Normal writes replace files in place.

Safe policy:

- do not add file cleanup in the first database-maintenance command.

## Retention Windows Confirmed In Runtime Code

Two different historical paths currently exist, and they do not use identical monthly rules.

### Public-scoreboard fallback (`historical_*`)

Confirmed in `backend/app/historical_storage.py`:

- weekly fallback can use previous week when current-week sample is insufficient;
- monthly fallback uses previous month only when current month has zero closed matches;
- `is_early_month` is computed with `current_time.day <= 3`, but selection still depends on zero current-month matches.

### RCON materialized leaderboards (`rcon_materialized_matches`)

Confirmed in `backend/app/rcon_historical_leaderboards.py`:

- monthly leaderboard selection uses previous month through day 7 inclusive;
- weekly selection falls back to previous week when current week lacks the configured minimum closed matches.

## Cleanup Policy Recommendation

Because the new maintenance task explicitly requires:

- latest 100 materialized matches;
- current month;
- previous month during first 7 days of a new month;
- current week;
- previous week when weekly fallback may need it;

the cleanup command should implement the stricter policy directly instead of copying the older `historical_storage.py` month fallback behavior.

## Safe-To-Delete Areas

### 1. `server_snapshots`

Safe to delete old rows by `captured_at` age once outside retention.

Why:

- live UI only needs recent history;
- no dependent child tables were found;
- latest snapshot queries use recent rows only.

Recommended initial retention:

- keep last 14 days by default.

### 2. Non-critical `rcon_admin_log_events`

Safe to delete by event age after retention.

Confirmed critical event types:

- `kill`
- `match_start`
- `match_end`

Everything else should be treated as non-critical for first-pass cleanup:

- `chat`
- `message`
- `connected`
- `disconnected`
- `team_switch`
- `unknown`
- `kick`
- `ban`
- any other non-materialization event type.

Recommended initial retention:

- non-critical: 30 days.

### 3. Critical `rcon_admin_log_events`

Conditionally safe to delete only when both are true:

- older than the critical retention threshold;
- not needed by protected materialized matches/windows.

Recommended initial retention:

- critical: 90 days.

### 4. Old `rcon_materialized_matches`

Conditionally safe to delete when all of the following are true:

- not in latest N closed matches;
- not in current month;
- not in previous month during the first 7 days of a new month;
- not in current week;
- not in previous week when weekly fallback may still be needed.

### 5. Child rows in `rcon_match_player_stats`

Safe to delete only as a dependent delete for non-protected materialized matches.

Delete these before deleting parent matches because no cascade constraint was found.

## Areas That Must Be Protected

### RCON materialized read path

Protect:

- latest 100 closed `rcon_materialized_matches`;
- all `rcon_match_player_stats` for protected matches;
- `kill`, `match_start`, `match_end` events that still support protected matches or currently relevant windows.

### Live/current match surfaces

Protect recent/current RCON data:

- recent `rcon_admin_log_events` still used by current-match kill feed and current-match player stats;
- recent `server_snapshots`.

Reason:

- current-match pages read recent AdminLog windows directly;
- premature deletion would break kill feed or partial player stats.

### Displayed snapshots

Protect:

- `displayed_historical_snapshots` as a bounded read cache;
- file-based snapshots under `backend/data/snapshots/`.

### Public-scoreboard `historical_*`

Do not delete in the first cleanup command.

Reason:

- these tables still back visible historical endpoints and fallback behavior;
- the task’s cleanup requirements are expressed around materialized matches and AdminLog, not around legacy scoreboard imports;
- deleting this domain now would widen scope materially.

### Player-event ledger

Do not delete in the first cleanup command.

Reason:

- it feeds visible player-event snapshots and monthly MVP V2 support;
- no task requirement currently defines safe retention windows for this ledger;
- deleting it without product retention rules is risky.

### Elo/MMR paused data

Do not delete.

Reason:

- task explicitly warns against unrelated Elo/MMR deletions;
- runtime is paused, but persisted surfaces are intentionally preserved.

## Foreign Keys, Cascades, and Orphan Risk

### Confirmed foreign keys

Public-scoreboard historical tables have foreign keys:

- `historical_matches.historical_server_id -> historical_servers.id`
- `historical_matches.historical_map_id -> historical_maps.id`
- `historical_player_match_stats.historical_match_id -> historical_matches.id`
- `historical_player_match_stats.historical_player_id -> historical_players.id`

RCON/postgres tables also define references for some capture-oriented tables.

### Missing cascade behavior relevant to cleanup

No `ON DELETE CASCADE` behavior was found for:

- `rcon_materialized_matches`
- `rcon_match_player_stats`

The materialization code explicitly deletes/rebuilds child player rows itself, which is another signal that cleanup must manage delete order manually.

### Required delete order

For materialized RCON cleanup:

1. identify protected match keys;
2. identify candidate old matches outside protected windows;
3. delete `rcon_match_player_stats` for candidate match keys;
4. delete candidate rows from `rcon_materialized_matches`;
5. delete eligible `rcon_admin_log_events`;
6. delete eligible `server_snapshots`.

This order avoids orphaned player-stat rows.

## Risks and Edge Cases

### Timestamp parsing risk

Some match rows may have:

- missing `started_at`;
- missing `ended_at`;
- only server-time fields;
- malformed or non-ISO timestamps.

Safe rule:

- if a materialized match timestamp cannot be interpreted safely, protect it and skip deletion.

### Cross-path monthly rule mismatch

There is a confirmed mismatch today:

- public-scoreboard fallback code does not strictly use previous month through day 7;
- RCON leaderboard code does.

Cleanup should follow the task requirement, not the older fallback implementation.

### Current-match dependency on recent AdminLog

Current match pages query recent AdminLog rows directly, not only materialized matches.
Deleting recent critical events too aggressively could break live/current-match UI even if historical leaderboards still work.

### Optional table presence

Some environments may not have every migrated or optional table yet.
Maintenance code should treat absent tables as controlled skips, not hard failures.

### SQLite versus PostgreSQL

The repo still supports SQLite fallback when `HLL_BACKEND_DATABASE_URL` is unset.
Maintenance code should either:

- support SQLite safely for the targeted tables; or
- emit a clear unsupported message.

Given the codebase still keeps local SQLite testability, SQLite support is preferable for the cleanup command and its tests.

## Recommended Cleanup Scope For First Implementation

Implement only:

- `server_snapshots`;
- `rcon_admin_log_events`;
- `rcon_materialized_matches`;
- `rcon_match_player_stats`.

Explicitly skip in first implementation:

- `displayed_historical_snapshots`;
- `historical_*`;
- `player_event_raw_ledger` and related worker tables;
- Elo/MMR tables;
- `rcon_historical_samples`, `rcon_historical_competitive_windows`, `rcon_player_profile_snapshots`, `rcon_scoreboard_match_candidates`.

Reason:

- keeps scope aligned to the task;
- avoids deleting sources still needed for visible history fallback or paused domains;
- stays within the repository’s change-budget expectations.

## Implementation Plan For `app.database_maintenance`

1. Add maintenance config accessors for all retention values and batch size.
2. Add a CLI with `cleanup --dry-run` and `cleanup --apply`.
3. Build one plan phase that calculates:
   - protected materialized match keys;
   - candidate match keys;
   - candidate admin-log rows by criticality and age;
   - candidate server snapshots by age.
4. Log the plan in structured JSON before any deletes.
5. On apply:
   - acquire the shared backend writer lock;
   - delete `rcon_match_player_stats` in batches for candidate match keys;
   - delete `rcon_materialized_matches` in batches;
   - delete `rcon_admin_log_events` in batches;
   - delete `server_snapshots` in batches;
   - optionally run `VACUUM ANALYZE` only when explicitly requested.
6. Treat missing optional tables as logged skips.
7. Keep dry-run as default behavior.

## Recommended SQL Audit Commands

### Table-size audit

```sql
select
  schemaname,
  relname as table_name,
  pg_size_pretty(pg_total_relation_size(relid)) as total_size,
  pg_size_pretty(pg_relation_size(relid)) as table_size,
  pg_size_pretty(pg_total_relation_size(relid) - pg_relation_size(relid)) as indexes_size,
  n_live_tup as estimated_rows,
  n_dead_tup as estimated_dead_rows
from pg_stat_user_tables
order by pg_total_relation_size(relid) desc;
```

### AdminLog by type and age

```sql
select
  event_type,
  count(*) as row_count,
  min(event_timestamp) as first_event_timestamp,
  max(event_timestamp) as last_event_timestamp,
  min(server_time) as first_server_time,
  max(server_time) as last_server_time
from rcon_admin_log_events
group by event_type
order by row_count desc, event_type asc;
```

### Materialized matches by server and closure time

```sql
select
  target_key,
  source_basis,
  count(*) as matches,
  min(coalesce(ended_at, started_at)) as first_closed_at,
  max(coalesce(ended_at, started_at)) as last_closed_at
from rcon_materialized_matches
group by target_key, source_basis
order by target_key asc, source_basis asc;
```

### Materialized player stats coverage

```sql
select
  target_key,
  count(*) as player_stat_rows,
  count(distinct match_key) as match_count
from rcon_match_player_stats
group by target_key
order by target_key asc;
```

### Live server snapshots by age

```sql
select
  server_id,
  min(captured_at) as first_captured_at,
  max(captured_at) as last_captured_at,
  count(*) as snapshot_rows
from server_snapshots
group by server_id
order by last_captured_at desc;
```

### Displayed snapshot coverage

```sql
select
  snapshot_type,
  metric,
  snapshot_window,
  count(*) as snapshot_rows,
  min(generated_at) as first_generated_at,
  max(generated_at) as last_generated_at
from displayed_historical_snapshots
group by snapshot_type, metric, snapshot_window
order by snapshot_type asc, metric asc, snapshot_window asc;
```

### Public-scoreboard fallback historical matches

```sql
select
  hs.slug as server_slug,
  count(*) as matches,
  min(coalesce(hm.ended_at, hm.started_at, hm.created_at_source)) as first_match_at,
  max(coalesce(hm.ended_at, hm.started_at, hm.created_at_source)) as last_match_at
from historical_matches hm
join historical_servers hs on hs.id = hm.historical_server_id
group by hs.slug
order by hs.slug asc;
```

### Player-event ledger age

```sql
select
  event_type,
  count(*) as row_count,
  min(occurred_at) as first_occurred_at,
  max(occurred_at) as last_occurred_at
from player_event_raw_ledger
group by event_type
order by row_count desc, event_type asc;
```

## Summary

The first cleanup command can be implemented safely if it stays narrow:

- clean `server_snapshots`;
- clean aged `rcon_admin_log_events`;
- clean non-protected `rcon_materialized_matches`;
- delete `rcon_match_player_stats` first for those matches;
- skip bounded snapshot caches and broader fallback domains for now.

The main correctness risk is not delete syntax. It is retention-window selection and preserving current/live dependencies. The cleanup command should therefore be plan-first, dry-run-first, and lock-protected.
