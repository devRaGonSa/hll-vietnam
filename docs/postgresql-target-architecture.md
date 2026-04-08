# PostgreSQL Target Architecture

## Purpose

This document defines the staged destination state for the `TASK-131` to
`TASK-138` migration batch. Its purpose is to make PostgreSQL the primary
durable backend store without turning the repository into an indefinite
mixed-storage system.

## Current Persistence Boundary

The backend currently persists product data across three different storage
surfaces:

- SQLite under `backend/data/` or `/app/data/`:
  - live server snapshot metadata in `server_snapshots`
  - core historical relational data in `historical_*`
  - RCON historical capture data in `rcon_historical_*`
  - player-event ledgers and progress tables in `player_event_*`
  - Elo/MMR ratings, rankings, checkpoints, and rebuild state in `elo_mmr_*`
- Filesystem JSON snapshots under `/app/data/snapshots`:
  - precomputed historical endpoint payloads and metadata
- Local file lock state beside the SQLite file:
  - single-writer coordination via `*.writer.lock`

This split was acceptable for local SQLite development, but it is not the
approved long-term architecture for multi-process or multi-container runtime.

## Target Durable Store

PostgreSQL becomes the primary durable store for all backend product data.
After final cutover, product persistence must be owned by PostgreSQL rather
than by `.sqlite3` files or filesystem JSON payloads.

Approved PostgreSQL ownership categories:

- Primary PostgreSQL domain data:
  - live snapshot metadata and server identity
  - historical matches, maps, players, and player-match facts
  - RCON historical samples, windows, targets, and checkpoints
  - player-event raw ledger, ingestion runs, and backfill progress
  - Elo/MMR ratings, match results, monthly rankings, and checkpoints
- PostgreSQL materialized or snapshot read models:
  - precomputed historical endpoint payloads and fast-read metadata
  - explicit materialization tables or snapshot payload tables using `JSONB`
- Transitional compatibility surface:
  - controlled read/write coexistence needed only during migration and backfill
- No longer product storage after cutover:
  - `.sqlite3` files as runtime primary persistence
  - `/app/data/snapshots` as source of truth
  - file-based writer locks

## Ownership Mapping By Concern

### Live Snapshot Metadata

Future role: primary PostgreSQL domain data.

PostgreSQL owns:

- source identity
- server identity
- captured live snapshot rows
- relational indexes needed for latest and recent-history reads

Not approved long-term:

- SQLite file creation as initialization trigger
- SQLite `PRAGMA` assumptions

### Historical Matches And Player Stats

Future role: primary PostgreSQL domain data.

PostgreSQL owns:

- historical servers
- historical matches and maps
- normalized player identity
- player-match stats
- ingestion runs and progress state

Compatibility note:
During migration, SQLite may temporarily coexist as a source for backfill and
validation only. It is not allowed to remain the primary writer after cutover.

### RCON Historical Persistence

Future role: primary PostgreSQL domain data.

PostgreSQL owns:

- RCON targets
- capture runs
- persisted samples
- derived competitive windows
- resumable checkpoints

### Player Event Persistence

Future role: primary PostgreSQL domain data.

PostgreSQL owns:

- append-only event ledger
- ingestion runs
- resumable progress markers

### Elo/MMR Persistence

Future role: primary PostgreSQL domain data plus explicit PostgreSQL-backed
read models where needed.

PostgreSQL owns:

- player ratings
- match results
- monthly rankings
- rebuild checkpoints

Formula semantics remain outside this task. This migration changes storage
ownership, not the scoring model itself.

### Snapshot Payloads And Snapshot Metadata

Future role: PostgreSQL fast-read storage, not filesystem product storage.

Approved direction:

- explicit snapshot tables with identity columns plus `JSONB` payloads, or
- narrowly justified hybrid materialization where some snapshots are relational
  tables and some are `JSONB` payload records

Rejected direction:

- plain SQL views as the universal solution for all fast-read payloads

Reason:
the current snapshot layer stores endpoint-ready payloads with `generated_at`,
source-range metadata, and stale markers. Those concerns require explicit
materialization ownership, refresh policy, and traceable metadata rather than
relying on generic views alone.

## Fate Of SQLite-Era Runtime Assumptions

### `.sqlite3` Files

- Transitional only during backfill and output validation
- Not allowed as long-term primary runtime persistence
- Removed from normal steady-state backend runtime after `TASK-138`

### SQLite WAL And Busy Timeout

- Transitional only while SQLite remains part of the backfill path
- Not part of the final PostgreSQL-primary runtime contract
- Replaced later by PostgreSQL transaction, locking, and statement timeout
  behavior where needed

### Local File-Based Writer Locks

- Transitional only during mixed mode
- Replaced long-term by PostgreSQL-native coordination
- Preferred long-term model: session-scoped advisory locks, with explicit lock
  keys per job class and operator-visible conflict diagnostics

### `/app/data/snapshots`

- Not approved as long-term primary product storage
- May temporarily exist as a cache or migration source during the batch
- Must stop being the source of truth after snapshot migration cutover

## Approved Fast-Read Strategy

The approved PostgreSQL fast-read strategy is:

- primary: explicit snapshot or materialization tables refreshed outside hot
  request paths
- storage format: `JSONB` payloads when the endpoint consumes pre-shaped data,
  relational materialization tables when the read model benefits from indexed
  relational querying
- metadata stored beside the payload:
  - `generated_at`
  - `source_range_start`
  - `source_range_end`
  - `is_stale`
  - source policy or provenance when needed

Plain SQL views are explicitly rejected as the only general solution because
they do not replace snapshot identity, refresh orchestration, staleness
tracking, or endpoint-ready payload ownership.

## Cutover Boundary

### Transitional Mixed Mode

Allowed temporarily during the batch:

- PostgreSQL runtime foundation exists while some domains still read from SQLite
- PostgreSQL schema exists before every storage domain is ported
- SQLite data is read for backfill and parity validation
- filesystem snapshots may remain as transitional cache or migration input until
  the PostgreSQL snapshot layer is active
- file locks may continue only until PostgreSQL-native job coordination lands

Not allowed even in mixed mode:

- new PostgreSQL migration work that reintroduces SQLite-specific assumptions
- new product features depending on filesystem snapshots as primary storage
- indefinite coexistence without a documented cutover owner per domain

### Final PostgreSQL-Primary Mode

Required end state after `TASK-138`:

- PostgreSQL is the only primary durable product store
- API reads and background writers use PostgreSQL-backed storage
- snapshot reads come from PostgreSQL materialization or `JSONB` snapshot tables
- SQLite paths, WAL settings, busy-timeout tuning, and file lock behavior are
  removed or retained only for one-off archival tooling
- `/app/data` is narrowed to non-primary runtime concerns such as optional local
  exports, temporary artifacts, or operator-managed backups

## Migration Sequence Dependency

Execution order for the batch:

1. `TASK-131`: define target architecture and cutover boundary
2. `TASK-132`: add PostgreSQL runtime foundation, configuration contract, and
   connection bootstrap
3. `TASK-133`: add stable migration location, schema bootstrap, and migration
   runner
4. `TASK-134`: migrate live snapshot relational storage and core historical
   relational storage
5. `TASK-135`: migrate snapshot materialization and fast-read models into
   PostgreSQL
6. `TASK-136`: migrate RCON historical, player-event, and Elo/MMR persistence
7. `TASK-137`: replace file-based writer coordination with PostgreSQL-native
   locking and operator diagnostics
8. `TASK-138`: run backfill, parity validation, cutover, rollback rules, and
   decommission SQLite-era runtime assumptions

Dependency rule:
no later task should redefine the architecture boundary established here unless
the follow-up task explicitly updates this document and `docs/decisions.md`.

## Push Policy For The Batch

Implementation policy for `TASK-131` to `TASK-138`:

- no push may be executed while any sibling task in this PostgreSQL migration
  batch still remains in `ai/tasks/pending/`
- push is allowed only when the last remaining pending task of this batch is
  completed

Implementation reporting requirement for every task in this batch:

- modified files
- validations run
- validation results
- branch
- commit SHA
- push executed or intentionally deferred
