# TASK-107 - Update AI Platform Integration

## Goal

Update the HLL Vietnam AI Platform infrastructure to align with the newer `ai-dev-platform-template` conventions while preserving this repository's product context, workflow discipline and HLL Vietnam-specific documentation.

This is platform infrastructure work only. It must not change product behavior, backend logic, frontend behavior, Docker deployment behavior, Elo/MMR logic or RCON server #03 handling.

## Context

HLL Vietnam currently has a lightweight AI Platform layer under `ai/`, root `AGENTS.md`, task lifecycle folders and local Codex worker support. The next platform update should move the repository toward a controlled development-team workflow where ChatGPT acts as orchestrator between the human client/product owner and the development team, and Codex CLI workers execute only explicit tasks.

Important current direction:

- The Elo/MMR system is paused for now because it is too complex for the current phase.
- Comunidad Hispana / RCON server #03 is obsolete for future planning unless explicitly reintroduced.
- Historical workers and complex ranking/materialization pipelines must not be expanded by this task.
- The priority is to update AI Platform conventions safely and incrementally.

Generic template text must be adapted to HLL Vietnam. Do not overwrite repository-specific context with generic `ai-dev-platform-template` content.

## Steps

1. Inspect the current platform files listed in `Files to Read First`.
2. Compare the current repository conventions conceptually with the newer `ai-dev-platform-template` conventions:
   - root `ai-platform.json`
   - task lifecycle folders:
     - `ai/tasks/pending`
     - `ai/tasks/in-progress`
     - `ai/tasks/review`
     - `ai/tasks/blocked`
     - `ai/tasks/obsolete`
     - `ai/tasks/done`
   - metadata-based task template with front matter:
     - `id`
     - `title`
     - `status`
     - `type`
     - `team`
     - `supporting_teams`
     - `roadmap_item`
     - `priority`
   - config-aware `scripts/codex-runner.ps1`
   - `scripts/run-integration-tests.ps1`
   - optional `.github/workflows/codex-worker.yml`
   - `ai/reports/.gitkeep`
   - generated report ignore rules
3. Add `ai-platform.json` adapted to HLL Vietnam. Include repository-specific task paths, project identity and workflow configuration needed by local platform scripts.
4. Add missing task lifecycle directories with `.gitkeep` files where needed.
5. Add `ai/reports/.gitkeep` if the reports directory is introduced or missing.
6. Update `ai/task-template.md` to the newer metadata-based format while keeping HLL Vietnam-specific instructions, constraints and validation expectations.
7. Update `scripts/codex-runner.ps1` so it reads platform configuration from `ai-platform.json` instead of relying only on hard-coded repository assumptions.
8. Add or update `scripts/run-integration-tests.ps1` with repository-appropriate lightweight validation. The script should fail safely when optional checks are not configured.
9. Add `.github/workflows/codex-worker.yml` only if it is consistent with the current repository automation policy and does not create unintended deployment or product behavior.
10. Update `.gitignore` to ignore local runtime and generated platform artifacts, including:
    - `backend/runtime/`
    - generated `ai/reports/*.md` files
    - keep `ai/reports/.gitkeep` trackable
11. Update `AGENTS.md`, `ai/README.md`, `ai/repo-context.md` and/or `ai/architecture-index.md` only where necessary to reflect the new platform workflow.
12. Document any relevant architectural or process decisions in the task outcome.

## Files to Read First

- `AGENTS.md`
- `README.md`
- `.gitignore`
- `ai/README.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `ai/task-template.md`
- `scripts/codex-runner.ps1`
- `docker-compose.yml`
- `.github/workflows/*` if present

Rules:

- Read these files before implementation.
- Keep product behavior unchanged.
- Use the existing HLL Vietnam context as the source of truth.
- Treat template conventions as a reference, not content to copy blindly.

## Expected Files to Modify

Likely files:

- `ai-platform.json`
- `.gitignore`
- `AGENTS.md`
- `ai/README.md`
- `ai/repo-context.md`
- `ai/architecture-index.md`
- `ai/task-template.md`
- `scripts/codex-runner.ps1`
- `scripts/run-integration-tests.ps1`
- `ai/tasks/review/.gitkeep`
- `ai/tasks/blocked/.gitkeep`
- `ai/tasks/obsolete/.gitkeep`
- `ai/reports/.gitkeep`

Possible file, only if consistent with the repository automation policy:

- `.github/workflows/codex-worker.yml`

Rules:

- Do not modify product files unless there is a platform-only reason and it is documented.
- Do not modify unrelated files.
- If additional files become necessary, explain why in the task outcome.

## Expected Files Not To Modify

- `backend/**` product logic
- `frontend/**`
- `docker-compose.yml`
- Elo/MMR implementation files
- RCON server #03 implementation or configuration

## Constraints

- This task is platform infrastructure work, not product work.
- Do not change frontend behavior.
- Do not change backend behavior.
- Do not change Docker deployment behavior.
- Do not change Elo/MMR code or expand Elo/MMR pipelines.
- Do not remove, rename or alter RCON server #03 in this task.
- Do not expand historical workers or complex ranking/materialization pipelines.
- Preserve HLL Vietnam-specific project context, Spanish-speaking community identity and current repository direction.
- Adapt template conventions to this repository instead of blindly copying generic template text.
- Keep the change narrow, reviewable and implementation-ready.

## Validation

Before completing the task ensure:

- `git status` has been reviewed.
- `git diff --name-only` shows only expected platform files.
- `ai-platform.json` exists and is valid JSON.
- The task lifecycle folders exist:
  - `ai/tasks/pending`
  - `ai/tasks/in-progress`
  - `ai/tasks/review`
  - `ai/tasks/blocked`
  - `ai/tasks/obsolete`
  - `ai/tasks/done`
- Required empty platform directories contain `.gitkeep` files where needed.
- Generated reports such as `ai/reports/*.md` are ignored by Git.
- `ai/reports/.gitkeep` remains trackable.
- `backend/runtime/` is ignored by Git.
- No local runtime data is committed.
- A lightweight repository validation command has been run if available.
- If `scripts/run-integration-tests.ps1` exists after the change, run it.
- If no integration tests are configured for the affected scope, document that explicitly in the task outcome.
- Frontend, backend and Docker behavior remain unchanged.

## Change Budget

- Prefer fewer than 10 modified files for this platform update.
- Prefer small documentation and script changes over broad rewrites.
- Split follow-up work into separate tasks if the scope grows beyond platform integration.

## Outcome

- Added repository-specific `ai-platform.json` for task paths, worker settings and HLL Vietnam constraints.
- Added missing lifecycle folders: `review`, `blocked` and `obsolete`.
- Added `ai/reports/.gitkeep` and ignored generated `ai/reports/*.md` files while keeping `.gitkeep` trackable.
- Updated the task template to include metadata front matter and HLL Vietnam-specific constraints.
- Updated `scripts/codex-runner.ps1` to read local worker paths and prompts from `ai-platform.json`.
- Updated `scripts/run-integration-tests.ps1` to perform lightweight platform validation only.
- Updated platform documentation in `AGENTS.md`, `ai/README.md`, `ai/repo-context.md` and `ai/architecture-index.md`.
- No frontend, backend product logic, Docker behavior, Elo/MMR logic or RCON server #03 handling was changed.

Validation performed:

- Parsed `ai-platform.json` with `ConvertFrom-Json`.
- Ran `powershell -ExecutionPolicy Bypass -File scripts/run-integration-tests.ps1`.
- Parsed both PowerShell scripts with the PowerShell language parser.
- Confirmed `ai/reports/example.md` is ignored and `ai/reports/.gitkeep` is trackable.
- Reviewed `git diff --name-only` and `git status --short`.

No product integration tests are configured for this platform-only scope.
