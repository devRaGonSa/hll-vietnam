# PostgreSQL Cutover Runbook

## Purpose

This runbook closes the `TASK-131` to `TASK-138` migration batch by defining
the approved backfill path, validation gates, cutover order, rollback limits,
and the point where SQLite-era runtime assumptions stop being primary.

## Approved Strategy

The approved migration strategy is hybrid, with an explicit reason per domain:

- Relational product data:
  direct read from the legacy SQLite file into PostgreSQL.
- Historical snapshot payloads:
  regenerate from PostgreSQL after relational backfill instead of treating the
  JSON files as the new source of truth.
- Legacy snapshot JSON files under `backend/data/snapshots/`:
  keep only as temporary rollback artifacts until cutover sign-off is complete.

Why this split:

- The repository already has PostgreSQL-native storage modules for live,
  historical, RCON, player-event, Elo/MMR, and snapshot payload persistence.
- Rebuilding snapshot payloads from PostgreSQL validates the new read models and
  avoids preserving filesystem JSON as a long-term product dependency.

## Backfill Command

From `backend/`:

```powershell
python scripts/postgresql-backfill.py plan
python scripts/postgresql-backfill.py execute --truncate-target-first
python scripts/postgresql-backfill.py validate
```

What the script does:

- `plan`: inspects the SQLite source file and reports the cutover strategy.
- `execute`: applies PostgreSQL migrations, copies approved relational tables
  from SQLite to PostgreSQL in batches, commits table by table, and records a
  validation manifest for the copied row counts.
- `validate`: compares SQLite counts against exact PostgreSQL counts for small
  tables and against the execute manifest for large tables, returning a
  non-zero exit code on mismatches.

Validated operational notes from the final runtime pass:

- PostgreSQL must run with `UTF8` encoding so legacy player names and other
  Unicode values survive the backfill without client-encoding failures.
- `execute` was validated with the default batch size of `5000` rows per insert
  batch and completed successfully against the real legacy dataset.
- `validate` is intentionally separated from `execute`; it is no longer folded
  into the execute step.

## Validation Gates Before Cutover

All of the following must pass before steady-state runtime is switched to the
PostgreSQL-primary mode:

1. `python scripts/run-migrations.py`
2. `python scripts/postgresql-backfill.py execute --truncate-target-first`
3. `python scripts/postgresql-backfill.py validate`
4. `python -m app.historical_runner run --phase snapshots`
5. `python -m app.rcon_historical_worker capture --target comunidad-hispana-01`
6. `python -m app.player_event_worker refresh --server comunidad-hispana-01 --max-pages 1`
7. `python -m app.elo_mmr_engine rebuild`
8. Backend API parity checks against PostgreSQL-backed responses:
   - `/health`
   - `/api/servers`
   - `/api/historical/server-summary`
   - `/api/historical/recent-matches`
   - `/api/historical/snapshots/server-summary`
   - `/api/historical/snapshots/weekly-leaderboard`
   - `/api/historical/snapshots/leaderboard`
   - `/api/historical/snapshots/recent-matches`

Expected parity rule:

- API contracts, response keys, and endpoint paths remain unchanged.
- Differences are allowed only in provenance metadata such as
  `primary_source`, `selected_source`, `fallback_used`, or refresh timestamps.

## Cutover Order

Apply the cutover in this exact order:

1. PostgreSQL migrations and connectivity probe.
2. SQLite relational backfill into PostgreSQL.
3. Row-count validation between SQLite and PostgreSQL.
4. Snapshot regeneration into PostgreSQL from the backfilled relational store.
5. Backend API runtime using PostgreSQL-backed reads.
6. Historical runner using PostgreSQL-backed writes and snapshot regeneration.
7. RCON historical worker using PostgreSQL-backed writes.
8. Player event worker using PostgreSQL-backed writes.
9. Elo/MMR rebuild plus PostgreSQL-backed read verification.
10. Legacy SQLite file and filesystem snapshot paths moved to rollback-only
    status.

## Rollback Expectations And Limits

Rollback is phase-bounded, not indefinite:

- Before step 4:
  rollback is allowed by discarding PostgreSQL data and rerunning the old
  SQLite/file-backed read path for inspection only.
- After step 4 but before step 9 sign-off:
  rollback is allowed only as a short-lived operator action while the legacy
  SQLite file and JSON snapshots are still preserved as read-only artifacts.
- After step 9 sign-off:
  SQLite and filesystem snapshots are no longer approved as the primary runtime
  store. Rollback means restoring PostgreSQL from backup, not re-promoting the
  legacy filesystem path.

Rollback limits:

- Do not continue mixed mode after sign-off.
- Do not resume normal writes against SQLite once PostgreSQL cutover is signed
  off.
- Do not treat stale `backend/data/snapshots/` payloads as authoritative after
  PostgreSQL snapshot regeneration is validated.

## Retirement Of SQLite-Era Assumptions

These assumptions become deprecated or removed at final cutover:

- `HLL_BACKEND_STORAGE_PATH`:
  legacy backfill/archive pointer only, not the primary runtime store.
- SQLite WAL and `busy_timeout` tuning:
  legacy archive-tooling concerns only.
- Filesystem JSON snapshots:
  rollback artifacts only until sign-off, then removable.
- Local file-based writer locks:
  already replaced by PostgreSQL advisory locks in `TASK-137`.

## `/app/data` Narrowing

After cutover, `/app/data` is no longer the primary durable product store.

Approved post-cutover uses:

- imported SQLite archive kept temporarily for rollback inspection
- operator-generated exports
- one-off migration artifacts

Not approved after cutover:

- primary backend relational persistence
- primary historical snapshot payload ownership
- primary coordination state

Recommended runtime convention:

- use `/app/runtime/legacy/` for temporary SQLite archives if they must still be
  mounted into containers
- treat PostgreSQL as the only steady-state durable product store

## Push Policy

The PostgreSQL migration batch is complete only when this runbook, the backfill
script, Compose, and backend documentation are aligned.

Batch push policy:

- push is blocked while any sibling task from `TASK-131` to `TASK-138` remains
  pending
- once `TASK-138` is completed, push is allowed, but it remains an explicit
  operator choice rather than an automatic task side effect
