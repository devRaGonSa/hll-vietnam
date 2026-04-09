# TASK-136-postgresql-rcon-player-events-and-elo-storage-migration

## Goal

Migrate the remaining advanced persistence domains to PostgreSQL in an explicit and bounded way:

- RCON historical storage
- player event storage
- Elo/MMR storage

## Context

Beyond the core live and historical relational foundation, the repository contains additional persistence-heavy domains that still depend on SQLite and local storage assumptions:

- `backend/app/rcon_historical_storage.py`
- `backend/app/player_event_storage.py`
- `backend/app/elo_mmr_storage.py`

These modules also interact with:

- `backend/app/elo_mmr_engine.py`
- the shared config layer
- batch workers and rebuild flows that currently inherit SQLite semantics

Because these domains have their own state, checkpoints, append-only or rebuild-style workflows, and read-model expectations, they must be migrated as first-class work instead of being hidden inside a generic storage rewrite.

## Steps

1. Inspect the listed files first and map the PostgreSQL migration boundary for each advanced storage domain separately.
2. Define or add PostgreSQL table mappings for:
   - RCON historical persistence
   - player event ledger and checkpoints
   - Elo/MMR ratings, results, rankings, and checkpoints
3. Migrate these modules to the PostgreSQL connection layer and schema framework introduced earlier in the batch.
4. Replace SQLite-only SQL, placeholder syntax, conflict handling, and row-access assumptions with PostgreSQL-native equivalents.
5. Define how checkpoint and state tables migrate for each domain so refreshes and rebuilds remain resumable.
6. Define how rebuild and materialization flows behave under PostgreSQL, especially where current modules persist JSON fragments or calculated state.
7. Preserve read-model compatibility for current callers and operational commands.
8. Keep formulas and product semantics unchanged in this task:
   - no Elo/MMR scoring redesign
   - no player-event semantic redesign
   - no RCON capture semantic redesign
9. Document any domain-specific migration caveats, such as append-only ingestion, idempotent event ingestion, competitive window upserts, or monthly ranking rebuild behavior.
10. Do not change unrelated storage domains in this task.

## Files to Read First

- `AGENTS.md`
- `backend/app/rcon_historical_storage.py`
- `backend/app/player_event_storage.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/elo_mmr_engine.py`
- `backend/app/config.py`

## Expected Files to Modify

- `backend/app/rcon_historical_storage.py`
- `backend/app/player_event_storage.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/elo_mmr_engine.py`
- `backend/db/migrations/`

## Constraints

- Keep the task focused on persistence migration of these advanced domains.
- Do not redesign Elo/MMR formulas in this task.
- Do not redesign player-event semantics in this task.
- Do not redesign RCON capture semantics in this task.
- The task must explicitly define:
  - PostgreSQL table mapping for each domain
  - how checkpoint and state tables are migrated
  - how rebuild and materialization paths change under PostgreSQL
  - how read-model compatibility is preserved
- Preserve functional behavior while changing the storage backend.
- Keep the migration explicit by domain so any defect can be traced to one storage area instead of one large rewrite.
- When this task is implemented later, no push may be executed while any sibling PostgreSQL migration task in the `TASK-131` to `TASK-138` batch still remains in `ai/tasks/pending/`.
- When this task is implemented later, push is allowed only if this task completes as the last remaining pending task of the batch.
- The final implementation response for this task must explicitly report:
  - modified files
  - validations run
  - validation results
  - branch
  - commit SHA
  - push executed or intentionally deferred

## Validation

Before completing the task ensure:

- the migration clearly scopes these advanced storage modules and no unrelated domains
- PostgreSQL table mapping exists for RCON history, player events, and Elo/MMR persistence
- checkpoint and state migration is explicit for each domain
- rebuild or materialization paths behave correctly under PostgreSQL
- formulas and product semantics were not redesigned
- current read-model compatibility is preserved for callers and operators
- no unrelated files were modified
- future implementation push policy is explicit:
  - no push while sibling PostgreSQL migration tasks in this batch remain pending
  - push only when the final pending task of this batch is completed
- future implementation reporting requirements are explicit:
  - modified files
  - validations run
  - validation results
  - branch
  - commit SHA
  - push executed or intentionally deferred

## Change Budget

- Prefer fewer than 5 modified files.
- Prefer changes under 200 lines when feasible.
- Split the work into follow-up tasks if limits are exceeded.
