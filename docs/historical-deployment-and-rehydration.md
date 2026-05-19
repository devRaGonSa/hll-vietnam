# Historical Deployment And Rehydration Runbook

This runbook covers the HLL Vietnam historical pipeline when deploying to a new server or rebuilding a PostgreSQL database from an empty or nearly empty state.

The current production policy is:

- Historical runtime is `rcon-first-with-public-scoreboard-fallback`.
- `comunidad-hispana-03` is a known degraded RCON target, but it is operational through `public-scoreboard` fallback.
- Do not treat the S3 RCON auth failure as a code deployment blocker unless there is new evidence that the failure is caused by our code.
- `recent-sweep` always rereads recent scoreboard pages from page 1 and is independent from historical bootstrap checkpoints.
- The runner owns selective snapshot/materialized postprocessing. A direct `recent-sweep` CLI run is intentionally lightweight.

## 1. Deploying On A New Server

### Recommended Order

1. Put the expected environment in place.

   Required PostgreSQL settings:

   ```powershell
   HLL_BACKEND_POSTGRES_HOST
   HLL_BACKEND_POSTGRES_PORT
   HLL_BACKEND_POSTGRES_DB
   HLL_BACKEND_POSTGRES_USER
   HLL_BACKEND_POSTGRES_PASSWORD
   HLL_BACKEND_POSTGRES_SSLMODE
   ```

   Historical source policy:

   ```powershell
   HLL_BACKEND_HISTORICAL_DATA_SOURCE=rcon
   HLL_BACKEND_RCON_TARGETS=<json array with the configured RCON targets>
   HLL_HISTORICAL_KNOWN_RCON_DEGRADED_TARGETS=comunidad-hispana-03
   HLL_HISTORICAL_RECENT_SWEEP_ENABLED=true
   HLL_HISTORICAL_RECENT_SWEEP_PAGES=5
   HLL_HISTORICAL_RECENT_SWEEP_PAGE_SIZE=10
   ```

   Even when S3 is expected to run through fallback, keep `HLL_BACKEND_RCON_TARGETS`
   configured. The runner still starts from the RCON-primary policy and needs the
   target list in order to record the degraded target status before selecting
   `public-scoreboard` fallback.

2. Build and start database plus backend first.

   ```powershell
   docker compose build backend historical-runner rcon-historical-worker
   docker compose up -d postgres backend
   docker compose ps -a postgres backend
   ```

3. Apply migrations using the project migration runner.

   ```powershell
   docker compose exec -T backend python scripts/run-migrations.py
   ```

4. Verify migration 0006 columns.

   ```powershell
   docker compose exec -T postgres psql -U hll_vietnam -d hll_vietnam -c "
   SELECT column_name
   FROM information_schema.columns
   WHERE table_name = 'historical_matches'
     AND column_name IN (
       'detail_status',
       'detail_quality_reason',
       'detail_last_attempt_at',
       'detail_last_error',
       'detail_retry_count'
     )
   ORDER BY column_name;
   "
   ```

   Expected result:

   ```text
   detail_last_attempt_at
   detail_last_error
   detail_quality_reason
   detail_retry_count
   detail_status
   ```

5. Start workers after the schema is ready.

   ```powershell
   docker compose up -d historical-runner rcon-historical-worker
   docker compose ps -a postgres backend historical-runner rcon-historical-worker
   ```

## 2. Empty Database Rehydration

An empty database needs schema, base historical rows, snapshots, and derived ratings/materializations. The expensive phases are the historical archive import and any full Elo/MMR rebuild.

### Safe Bootstrap Sequence

1. Stop background workers while rehydrating.

   ```powershell
   docker compose stop historical-runner rcon-historical-worker
   ```

2. Apply migrations.

   ```powershell
   docker compose exec -T backend python scripts/run-migrations.py
   ```

3. Bootstrap historical archive per server, preferably one server at a time.

   ```powershell
   docker compose exec -T backend python -u -m app.historical_ingestion bootstrap --server comunidad-hispana-01 --start-page 1 --page-size 50 --detail-workers 8
   docker compose exec -T backend python -u -m app.historical_ingestion bootstrap --server comunidad-hispana-02 --start-page 1 --page-size 50 --detail-workers 8
   docker compose exec -T backend python -u -m app.historical_ingestion bootstrap --server comunidad-hispana-03 --start-page 1 --page-size 50 --detail-workers 8
   ```

   Notes:

   - This is the longest and most provider-sensitive phase.
   - For S3, fallback to `public-scoreboard` is an expected operational path.
   - If a bootstrap fails, inspect the error. Unlike `recent-sweep`, bootstrap is allowed to fail loudly because it is rebuilding deep archive coverage.

4. Run recent sweep after bootstrap.

   ```powershell
   docker compose exec -T backend python -u -m app.historical_ingestion recent-sweep --page-size 10 --max-pages 5 --detail-workers 8
   ```

   This rereads page `1..N` for configured servers and repairs recent partial detail. It does not trigger heavy rebuild directly.

5. Generate snapshots and derived materializations through the runner.

   ```powershell
   docker compose exec -T backend python -u -m app.historical_runner run --phase full --max-pages 1 --page-size 10 --full-elo-rebuild
   ```

   Use `--full-elo-rebuild` only when rebuilding a fresh database or when you intentionally need a full derived rating refresh.

6. Restart workers.

   ```powershell
   docker compose start historical-runner rcon-historical-worker
   docker compose ps -a postgres backend historical-runner rcon-historical-worker
   ```

## 3. Rehydration Strategies

### Option 1: Restore PostgreSQL Dump

Use when you have a recent trusted backup.

Pros:

- Fastest path for a large or mature historical dataset.
- Avoids re-requesting unstable public provider pages.
- Preserves repair state, snapshots, ratings, and migration history.

Cons:

- Requires reliable backup discipline.
- May restore stale snapshots if the dump is old.
- Must still run a recent sweep after restore.

Recommended follow-up after restore:

```powershell
docker compose exec -T backend python scripts/run-migrations.py
docker compose exec -T backend python -u -m app.historical_ingestion recent-sweep --page-size 10 --max-pages 5 --detail-workers 8
docker compose exec -T backend python -u -m app.historical_runner run --phase full --max-pages 1 --page-size 10
```

### Option 2: Rebuild From Historical Providers

Use when no trusted dump exists.

Pros:

- Reconstructs from source providers.
- Good disaster recovery fallback when backup is unavailable.

Cons:

- Slow.
- Provider availability and `HTTP 500` responses can stretch recovery time.
- Deep historical pages may change or become temporarily inaccessible.
- Derived ratings/snapshots must be recomputed.

Recommended only when a dump cannot be restored.

### Option 3: Hybrid Restore

Restore a reasonably recent dump, then run recent sweep and snapshots.

Pros:

- Best operational balance for HLL Vietnam.
- Avoids expensive full historical re-import.
- Handles late-arriving or repaired recent matches.
- Keeps S3 robust while RCON remains degraded externally.

Cons:

- Requires at least one viable dump.
- If the dump is very old, recent sweep may not cover all missing time; use targeted bootstrap for the missing servers/date range.

Recommended command sequence:

```powershell
docker compose stop historical-runner rcon-historical-worker
# Restore dump using the hosting-specific PostgreSQL restore mechanism.
docker compose exec -T backend python scripts/run-migrations.py
docker compose exec -T backend python -u -m app.historical_ingestion recent-sweep --page-size 10 --max-pages 5 --detail-workers 8
docker compose exec -T backend python -u -m app.historical_runner run --phase full --max-pages 1 --page-size 10
docker compose start historical-runner rcon-historical-worker
```

## 4. Recommendation For Current HLL Vietnam

Use the hybrid strategy by default.

Reasoning:

- The database is large enough that full historical recomputation is wasteful.
- Historical provider calls are slower and occasionally return transient failures.
- S3 is intentionally degraded-but-operable through `public-scoreboard`.
- Recent gaps are the highest operational risk, and `recent-sweep` directly mitigates that risk.
- Dumps preserve repair state, snapshots, and derived data that are expensive to rebuild.

Keep full provider rebuild as disaster recovery only.

## 5. Backup And Restore Policy

### Recommended Production Strategy

Use a hybrid restore strategy:

1. Restore a recent PostgreSQL dump.
2. Apply any new SQL migrations.
3. Run `recent-sweep` to recover late-arriving or recently repaired matches.
4. Run the historical runner once so snapshots and selective postprocessing are current.
5. Start background workers only after validation passes.

This avoids an expensive full provider rebuild while still covering recent gaps and degraded-but-operable S3 fallback.

### Backup Format

Prefer PostgreSQL custom-format dumps:

```powershell
pg_dump --format=custom --compress=9 --file hll_vietnam_YYYYMMDD_HHMM.dump hll_vietnam
```

Why:

- It restores with `pg_restore`.
- It is compressed.
- It is safer for large databases than plain SQL when restore ordering or parallel restore matters.
- It preserves schema and data in one operational artifact.

Keep a plain SQL schema-only export only as a secondary diagnostic artifact if the hosting platform makes that easy. Do not rely on schema-only exports for disaster recovery.

### Frequency And Retention

Suggested baseline:

- Daily full custom dump.
- Extra manual dump before risky migrations or broad historical rebuilds.
- Retain 7 daily dumps.
- Retain 4 weekly dumps.
- Retain 3 monthly dumps if storage cost is acceptable.

Adjust upward if the historical dataset grows faster or provider availability becomes less reliable.

### Periodic Restore Test

At least monthly, run a restore test into an isolated database or server:

1. Restore the latest dump into a non-production PostgreSQL database.
2. Run migrations.
3. Run a bounded recent sweep.
4. Regenerate snapshots through the runner.
5. Execute the validation checklist below.

The restore test is the only reliable proof that backups are usable. A successful `pg_dump` file is not enough.

### Exact Restore Sequence

Keep workers stopped while restoring:

```powershell
docker compose stop historical-runner rcon-historical-worker
```

Restore the dump using the hosting-specific mechanism. For a local container, the shape is:

```powershell
docker compose exec -T postgres pg_restore --clean --if-exists --no-owner --dbname hll_vietnam /path/in/container/hll_vietnam_YYYYMMDD_HHMM.dump
```

Then run the recovery tail:

```powershell
docker compose exec -T backend python scripts/run-migrations.py
docker compose exec -T backend python -u -m app.historical_ingestion recent-sweep --page-size 10 --max-pages 5 --detail-workers 8
docker compose exec -T backend python -u -m app.historical_runner run --phase full --max-pages 1 --page-size 10
docker compose start historical-runner rcon-historical-worker
```

Use `--full-elo-rebuild` only when the restored dump does not contain trustworthy Elo/MMR derived tables or when a deliberate full rating rebuild is part of the maintenance window.

### Validate After Restore

Run the checklist in the next section, with special attention to:

- `schema_migrations` includes the latest migration.
- Migration 0006 columns exist on `historical_matches`.
- `comunidad-hispana-03` has recent April coverage after `recent-sweep`.
- Partial rows have `detail_status`, `detail_quality_reason`, `detail_last_attempt_at`, `detail_last_error`, and `detail_retry_count`.
- Snapshot endpoints parse with `Invoke-RestMethod`.
- Logs contain S3 fallback policy events, not global runner failures.

### What Not To Do

- Do not start `historical-runner` or `rcon-historical-worker` during dump restore.
- Do not restore into the production database before confirming the dump source and target.
- Do not treat S3 RCON auth failure as a restore blocker while `public-scoreboard` fallback is operational.
- Do not run a deep full provider bootstrap if a recent trusted dump exists.
- Do not run full Elo/MMR rebuild repeatedly unless the rebuild is required and scheduled.
- Do not use the current production Postgres volume for restore tests.

## 6. Validation Checklist

### Services

```powershell
docker compose ps -a postgres backend historical-runner rcon-historical-worker
```

Expected:

- `postgres` healthy
- `backend` healthy
- `historical-runner` up
- `rcon-historical-worker` up

### Runtime Policy

```powershell
docker compose exec -T backend python -c "from app.data_sources import describe_historical_runtime_policy, describe_historical_rcon_target_health; import json; print(json.dumps({'policy': describe_historical_runtime_policy(), 's3': describe_historical_rcon_target_health(server_key='comunidad-hispana-03')}, indent=2, default=str))"
```

Expected:

- `mode = rcon-first-with-public-scoreboard-fallback`
- `operational_degraded_targets` includes `comunidad-hispana-03`
- S3 `fallback_eligible = true`
- S3 reason is `rcon-target-known-operational-degraded`

### Recent Coverage For S3

```powershell
docker compose exec -T postgres psql -U hll_vietnam -d hll_vietnam -c "
SELECT
  hs.slug,
  hm.external_match_id,
  hm.map_name,
  hm.started_at,
  hm.ended_at,
  hm.axis_score,
  hm.allied_score
FROM historical_matches hm
JOIN historical_servers hs
  ON hs.id = hm.historical_server_id
WHERE hs.slug = 'comunidad-hispana-03'
  AND hm.ended_at >= '2026-04-13 00:00:00+00'
  AND hm.ended_at <  '2026-04-16 00:00:00+00'
ORDER BY hm.ended_at DESC;
"
```

Expected:

- Rows for April 13, April 14, and April 15.
- Known partial rows may still exist, but they must have repair state.

### Repair State

```powershell
docker compose exec -T postgres psql -U hll_vietnam -d hll_vietnam -c "
SELECT
  hs.slug,
  hm.external_match_id,
  hm.started_at,
  hm.ended_at,
  hm.axis_score,
  hm.allied_score,
  hm.detail_status,
  hm.detail_quality_reason,
  hm.detail_retry_count,
  hm.detail_last_attempt_at,
  hm.detail_last_error
FROM historical_matches hm
JOIN historical_servers hs
  ON hs.id = hm.historical_server_id
WHERE hs.slug = 'comunidad-hispana-03'
  AND hm.ended_at >= '2026-04-01 00:00:00+00'
  AND (
    hm.axis_score IS NULL
    OR hm.allied_score IS NULL
    OR hm.started_at IS NULL
    OR hm.ended_at IS NULL
    OR hm.started_at >= hm.ended_at
    OR hm.detail_status IN ('partial', 'retry', 'failed')
  )
ORDER BY hm.ended_at DESC NULLS LAST;
"
```

Expected:

- Partial rows are visible and explain why they need retry.
- `detail_retry_count` and `detail_last_attempt_at` move when recent repair retries run.
- `detail_last_error` is populated for provider failures.

### Snapshots

```powershell
$r1 = Invoke-RestMethod -UseBasicParsing "http://127.0.0.1:8000/api/historical/snapshots/recent-matches?limit=20&server=comunidad-hispana-03"
$r2 = Invoke-RestMethod -UseBasicParsing "http://127.0.0.1:8000/api/historical/snapshots/leaderboard?timeframe=monthly&metric=kills&limit=20&server=comunidad-hispana-03"
$r3 = Invoke-RestMethod -UseBasicParsing "http://127.0.0.1:8000/api/historical/snapshots/leaderboard?timeframe=monthly&metric=deaths&limit=20&server=comunidad-hispana-03"

[pscustomobject]@{
  recentStatus = $r1.status
  recentCount = @($r1.data.items).Count
  recentHas13 = @(($r1.data.items | Where-Object { $_.ended_at -like '2026-04-13*' })).Count
  killsStatus = $r2.status
  killsCurrentMonthClosedMatches = $r2.data.current_month_closed_matches
  deathsStatus = $r3.status
  deathsCurrentMonthClosedMatches = $r3.data.current_month_closed_matches
} | ConvertTo-Json -Depth 6
```

Expected:

- All statuses are `ok`.
- `recentHas13` is greater than zero after the known April recovery.
- Monthly kills/deaths have coherent `current_month_closed_matches`.

### Logs To Expect

Healthy degraded S3 operation should include:

```text
historical-ingestion-rcon-targets-degraded-but-operable
operational_degraded_rcon_targets
selected_source=public-scoreboard
fallback_used=true
historical-ingestion-run-started mode=recent-sweep start_page=1
historical-ingestion-run-completed mode=recent-sweep
```

Provider failures that should not abort the whole lot:

```text
historical-ingestion-server-failed ... next_step=continuing-with-next-server
historical-ingestion-detail-batch-failed ... next_step=retrying-details-individually
historical-ingestion-detail-fetch-failed ... detail_status=failed
```

Problematic logs that need attention:

```text
Traceback
TypeError: Object of type datetime is not JSON serializable
UniqueViolation
historical-runner root status=error
backend-writer-lock timeout
```

## 6. Why There Is No Rehydration Helper Script Yet

The safest current operational path is explicit commands in this runbook.

A wrapper script could hide long-running or destructive behavior such as restoring dumps, bootstrapping deep provider pages, or forcing Elo/MMR rebuilds. Those actions should remain visible until the team agrees on production backup locations, restore permissions, and expected maintenance windows.

A future helper is reasonable once those deployment details are stable. It should default to dry-run, print every command before execution, never restore or drop a database implicitly, and require explicit flags for full bootstrap or full Elo/MMR rebuild.
