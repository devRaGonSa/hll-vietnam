# TASK-115

## Goal

Align the current Elo/MMR branch more closely with the PDF target design at the
practical v1-v2 level by strengthening the canonical player-match fact
foundation and persisting richer per-match and monthly-ready derived inputs,
without pretending that v3 telemetry already exists.

## Context

This branch already closed the foundational Elo work for:

- canonical Elo facts
- persistent MMR contracts and versioning
- monthly ranking materialization and versioning

The most important remaining pre-merge gap is not a full redesign. It is to
make the persisted Elo data model look more like a real `player_match_fact`
foundation and to carry forward more honest, auditable competitive inputs that
the current repository can really support now.

This task must improve internal Elo/MMR data alignment with the PDF v1-v2
design while keeping the repo honest about telemetry boundaries:

- exact
- approximate / proxy
- not_available

It must not fake tactical telemetry or claim that the repository already has the
v3 event-rich model.

## Steps

1. Inspect the current canonical Elo fact layer, persistent match-result model
   and monthly ranking materialization.
2. Add richer canonical or persisted derived inputs that better represent a
   `player_match_fact` style foundation for Elo/MMR.
3. Persist match-context, participation-quality and normalization-ready fields
   that are supported by existing repository data.
4. Improve lineage between canonical facts, per-match rating outputs and monthly
   ranking inputs.
5. Keep every new field honest about whether it is exact, approximate or
   unavailable.
6. Update repository documentation so the implemented v1-v2 model and deferred
   telemetry-rich v3 model remain clearly separated.
7. Validate the rebuild and prove the new persisted Elo data exists and is
   populated before closing the task.

## Files to Read First

- `AGENTS.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_storage.py`
- `docs/elo-mmr-monthly-ranking-design.md`

## Expected Files to Modify

- `backend/app/elo_mmr_storage.py`
- `backend/app/elo_mmr_engine.py`
- `backend/app/payloads.py`
- `docs/elo-mmr-monthly-ranking-design.md`
- `docs/elo-v3-competitive-gap-and-telemetry-boundary.md`

## Constraints

- Keep the task focused on Elo/MMR pre-merge alignment only.
- Target better alignment with the PDF v1-v2 model, not a fake completion of
  v3 telemetry ambitions.
- Do not fabricate garrisons, OPs, revives, supplies, nodes, strongpoint
  occupancy or any unsupported tactical feed.
- Do not introduce new runtime artifacts, lock files or SQLite files into the
  commit unless explicitly required and justified.
- Preserve reasonable backward compatibility for existing Elo payload consumers
  where practical.
- Keep exact, proxy and unavailable boundaries explicit in storage, docs and
  payload wording.
- If final validation passes, commit and push before marking the task complete.

## Validation

Before completing the task ensure:

- `python -m compileall app` passes
- the Elo/MMR rebuild succeeds on the validation SQLite DB
- SQLite checks prove the new or updated persisted Elo fact and derived-input
  fields exist and are populated
- leaderboard and player payload smoke checks still resolve
- focused checks demonstrate improved v1-v2 alignment without overclaiming
  unsupported telemetry
- no unrelated files were modified
- document explicitly that no integration test script exists for this scope if
  that remains true

## Change Budget

- Prefer fewer than 5 modified files when feasible.
- Prefer a narrow, mergeable pre-merge alignment change.
- Split later telemetry-rich work into follow-up tasks instead of expanding this
  task into a full v3 refactor.

## Outcome

- Status: completed on 2026-03-27
- Closure summary:
  - canonical Elo facts now persist stronger `player_match_fact` style context
    with resolved duration, duration buckets, player counts, participation
    buckets, participation quality and per-minute derived rates from existing
    stored metrics
  - persisted match results now carry richer lineage and monthly-ready
    competitive inputs without inventing unsupported tactical telemetry
  - monthly ranking component scores now persist explicit v1-v2 practical inputs
    for quality mix, participation mix, per-time rates and canonical fact
    lineage
  - model/version wording now identifies the implemented system as
    `elo-pdf-v1-v2-practical` and keeps telemetry-rich `v3` explicitly deferred

### Modified Files

- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_models.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/payloads.py`
- `docs/elo-mmr-monthly-ranking-design.md`
- `docs/elo-v3-competitive-gap-and-telemetry-boundary.md`

### Validations Run

- `py -3 -m compileall app`
- `HLL_BACKEND_STORAGE_PATH=D:\Proyectos\HLL Vietnam\backend\data\elo_mmr_task001_validation.sqlite3 py -3 -m app.elo_mmr_engine rebuild`
- SQLite checks on the validation DB for:
  - canonical player-match fact enrichment
  - persisted match-result lineage and populated derived inputs
  - monthly ranking component-score lineage and populated monthly inputs
- Elo leaderboard and player payload smoke checks on the validation DB
- `git diff --name-only`

### Validation Results

- compile passed
- scoped rebuild succeeded with:
  - canonical players: `1515`
  - canonical matches: `30`
  - canonical player-match facts: `3611`
  - persisted match results: `7222`
  - persisted monthly rankings: `3030`
- canonical fact enrichment populated on validation DB:
  - enriched canonical fact rows with duration and participation values: `3340`
  - distinct canonical duration buckets: `3`
  - distinct participation buckets: `3`
- persisted match-result enrichment populated on validation DB:
  - match-result rows with enriched duration and participation foundation: `6978`
  - rows with canonical fact lineage status present: `6704`
- monthly ranking component-score enrichment populated on validation DB:
  - rows with canonical fact lineage fields: `3030`
  - rows with participation-quality input: `3030`
  - rows with quality-mix counts: `3030`
- payload smoke checks passed and exposed the new fact-foundation metadata for
  leaderboard and player responses

### Notes

- `python` was not available on PATH in this shell, so validation used
  `py -3`.
- A full rebuild against the default development DB exceeded interactive
  timeout, so the required rebuild validation was completed on the scoped
  validation SQLite DB.
- `scripts/run-integration-tests.ps1` exists in the repository, but it was not
  relevant to this Elo/MMR scope and no dedicated integration test coverage was
  configured for these storage/model changes.
- The pre-existing runtime artifact `backend/data/hll_vietnam_dev.writer.lock`
  was left out of scope and should not be included in the commit.
