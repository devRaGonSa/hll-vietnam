---
id: TASK-POSTGRES-HISTORICAL-PHASE-2
title: Migrate displayed historical data to PostgreSQL
status: done
type: backend
team: Backend Senior
supporting_teams:
  - Arquitecto de Base de Datos
  - Arquitecto Python
roadmap_item: foundation
priority: high
---

# TASK-POSTGRES-HISTORICAL-PHASE-2 - Migrate displayed historical data to PostgreSQL

## Goal

Make PostgreSQL authoritative for historical and server data currently displayed
by the frontend, add an idempotent SQLite/file migration command, and close the
phase-1 datetime serialization and materialized detail lookup regressions.

## Context

Phase 1 moved the live RCON historical write path to PostgreSQL, but historical
frontend pages still read older SQLite and file-backed data for ranking,
scoreboard fallback, snapshots, server cache, and some match-detail continuity.
PostgreSQL reads also expose native datetime values that can terminate JSON API
responses. The phase-2 migration must preserve existing historical URLs and safe
scoreboard links without making SQLite the active source of truth again.

## Steps

1. Inspect the PostgreSQL RCON schema, SQLite historical schema, snapshot/server
   reads, and affected API routes.
2. Add PostgreSQL-backed displayed read models plus deterministic migration from
   existing SQLite/files.
3. Fix JSON-safe datetime handling and recent/detail materialized match
   consistency with focused regression tests.
4. Update diagnostics and docs, then run the requested local and Docker checks
   where available.

## Files to Read First

- `ai/architecture-index.md`
- `ai/repo-context.md`
- `backend/app/postgres_rcon_storage.py`
- `backend/app/historical_api.py`
- `backend/app/historical_snapshots.py`
- `backend/app/storage_diagnostics.py`

## Expected Files to Modify

- `backend/app/postgres_rcon_storage.py`
- `backend/app/sqlite_to_postgres_migration.py`
- `backend/app/storage_diagnostics.py`
- backend historical/server storage and API modules needed to move displayed
  SQLite/file reads to PostgreSQL
- focused backend tests for datetime and detail lookup regressions
- `backend/README.md`
- `docs/decisions.md`

## Constraints

- Do not return displayed historical data to SQLite as the main fix.
- Preserve old match ids, match keys, public scoreboard safe URLs, and existing
  historical data where present.
- Do not re-enable Comunidad Hispana #03 as an active configured target.
- Keep Elo/MMR out of phase 2 unless a visible API requires its PostgreSQL data.
- Do not modify unrelated frontend behavior or commit runtime database files.

## Validation

- Run the requested compile, diagnostics, migration, Node syntax, RCON pipeline,
  integration, Docker Compose, container diagnostics, materialization, and HTTP
  smoke commands where the local environment permits them.
- Review `git diff --name-only` and confirm changed files match this task.

## Outcome

Implemented PostgreSQL phase 2 for the displayed historical surface. The new
displayed PostgreSQL schema stores migrated public-scoreboard match/player
tables, historical snapshot payloads, live server cache rows and player-event
ledger rows alongside the phase-1 RCON tables. API storage facades now read
those PostgreSQL stores when `HLL_BACKEND_DATABASE_URL` is configured; SQLite
and snapshot JSON remain migration inputs or explicit local fixtures.

`python -m app.sqlite_to_postgres_migration` now discovers legacy SQLite files
and historical snapshot JSON under the configured backend data directory, copies
stable IDs/keys with idempotent conflict handling, advances PostgreSQL
sequences, skips visible `comunidad-hispana-03` legacy scope, preserves safe
scoreboard URLs and prints JSON row counts/errors. A repeat container run read
the existing source rows and reported zero inserted rows with no errors.

Required fixes included global HTTP JSON encoding for PostgreSQL `date` and
`datetime` values, a materialized detail lookup guard for match keys that embed
the requested server key, reduced repeated RCON PostgreSQL read-time DDL to
avoid schema-lock chains during materialization/diagnostics, and focused tests
for JSON encoding plus recent/detail match-id consistency.

Post-migration container diagnostics showed PostgreSQL counts including:

- `admin_log_events=21242`
- `materialized_matches=58`
- `player_stats=3824`
- `public_scoreboard_historical_matches=10030`
- ranking source stats `1090704`
- displayed snapshots `51`
- player-event ledger `14715`
- safe scoreboard candidates `400`

Remaining SQLite/file-backed boundaries are non-visible phase-3 scope only:
public-scoreboard import run/backfill bookkeeping and paused Elo/MMR tables.

Validation completed:

- `python -m compileall backend/app`
- `python -m unittest discover -s tests -p test_json_serialization.py`
  from `backend/`
- `python -m app.storage_diagnostics` locally and in the backend container
- `node --check` for the four requested frontend JavaScript files
- `powershell -ExecutionPolicy Bypass -File scripts/run-rcon-data-pipeline-tests.ps1`
- `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`
- requested advanced Docker Compose down/up/build/ps flow
- container migration, diagnostics, AdminLog ingestion and materialization
- requested HTTP probes for `/health`, recent matches and both known detail keys
- direct PostgreSQL-backed snapshot and direct monthly leaderboard HTTP probes

The RCON pipeline script still prints existing SQLite `ResourceWarning` noise
from its unittest fallback suites, but the script and suites passed.

## Change Budget

This migration intentionally crosses backend schema, read models, diagnostics,
tests, and docs. Keep each change tied to displayed data ownership or the
required migration/serialization/detail consistency fixes.
