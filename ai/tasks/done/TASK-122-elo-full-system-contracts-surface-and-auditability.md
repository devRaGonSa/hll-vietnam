# TASK-122

## Goal

Finalize the full Elo/MMR system surface so contracts, payloads, docs and audit
outputs accurately describe the implemented model, the exact/proxy boundaries,
the deferred tactical dependencies, and the lineage from facts to rating to
monthly ranking.

## Context

Once the earlier backlog tasks are completed, the repository will need one final
coherence pass so there are no contradictions across:

- storage
- engine
- payloads
- docs
- validation outputs
- capability wording

This task is the auditability and surface-alignment pass for the full Elo/MMR
system. It should make sure the final product and internal surfaces do not hide
versioning, do not hide capability transitions, and do not claim unavailable
telemetry as implemented truth.

Execution status: depends_on_previous_tasks

## Steps

1. Audit model contracts across storage, engine and payloads.
2. Audit exact / proxy / unavailable wording across all Elo surfaces.
3. Add or refine audit metadata that lets a reviewer trace:
   - canonical facts
   - event lineage
   - persistent rating lineage
   - monthly ranking lineage
4. Align docs with the implemented system and its remaining blocked
   dependencies.
5. Ensure the public/internal model surface never claims unavailable telemetry
   as implemented truth.
6. Leave visible and auditable, at minimum:
   - canonical fact schema version
   - source input version
   - event lineage availability
   - model version
   - formula version
   - contract version
   - capability summary
   - fact-foundation summary
   - persistent delta lineage
   - monthly checkpoint lineage
   - blocked/deferred telemetry families if still missing
7. Audit whether every major Elo surface can be understood without external
   documents, including:
   - storage tables
   - rebuild outputs
   - payload contracts
   - design documentation
8. Ensure the final wording clearly distinguishes:
   - implemented exact signals
   - implemented proxy signals
   - unavailable signals
   - deferred tactical dependencies
9. Add or refine audit helpers if needed so a reviewer can inspect lineage from:
   - canonical event or canonical fact
   - match-result rating movement
   - monthly ranking aggregation
10. Reconcile naming consistency across all Elo surfaces so the same concept is
    not described differently in storage, payloads and docs.

## Files to Read First

- `AGENTS.md`
- `backend/app/elo_mmr_engine.py`
- `backend/app/elo_mmr_storage.py`
- `backend/app/payloads.py`
- all outputs from TASK-116 to TASK-121
- `docs/elo-mmr-monthly-ranking-design.md`
- `docs/elo-v3-competitive-gap-and-telemetry-boundary.md`

## Expected Files to Modify

- `backend/app/payloads.py`
- docs for Elo/MMR model contracts
- audit or observability helpers if needed
- storage/model files only if required for missing lineage exposure

## Constraints

- Do not introduce misleading wording about unavailable telemetry.
- Do not leave hidden versioning or hidden capability transitions.
- The final Elo surface must be explainable to a reviewer without requiring
  external documents.
- Keep this task focused on contracts, docs, surface wording and auditability.
- Do not turn this task into another major engine rewrite.
- If lineage exposure is missing, add only the minimal storage/model changes
  required to make it auditable.

Push policy for future execution:

* If this task is implemented and other pending tasks from the same Elo backlog batch still remain open, the worker must not push yet.
* In that case, the worker may commit locally if the repo workflow requires it, but final push must wait until the last pending task of the same backlog batch is completed.
* If this task is the last remaining pending task in the same Elo backlog batch and final validation passes, the worker must commit and push.
* The final implementation response must always state:

  * modified files
  * validations run
  * validation results
  * branch name
  * final commit SHA
  * whether push was executed or intentionally deferred because more pending tasks from the same batch remain
* No task should claim final backlog completion without the required final push, unless a blocking error is documented.

## Validation

- end-to-end auditability review of storage -> engine -> payloads -> docs
- proof that versioning is visible
- proof that exact/proxy/unavailable boundaries are visible
- proof that deferred tactical dependencies are explicit if still unresolved
- payload smoke checks and documentation consistency checks
- proof that a reviewer can trace lineage from facts to rating to monthly
  ranking without relying on external documents

## Change Budget

- Keep this task focused on contracts, docs, surface and auditability.
- Do not use it for another large engine rewrite.
