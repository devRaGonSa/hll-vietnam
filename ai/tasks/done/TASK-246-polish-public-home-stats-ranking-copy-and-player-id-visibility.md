---
id: TASK-246
title: Polish public home stats ranking copy and player id visibility
status: done
type: frontend
team: Frontend Senior
supporting_teams:
  - Experto en interfaz
roadmap_item: foundation
priority: medium
---

# TASK-246 - Polish public home stats ranking copy and player id visibility

## Goal

Refine public frontend copy in home, stats and ranking, and stop showing player IDs in the public stats and ranking tables.

## Context

The scheduler and backend public reads were already validated. This task only adjusts visible frontend UI and copy:

- make the home countdown capsule more noticeable without widening it
- remove explanatory helper copy that adds noise in public panels
- remove the initial empty search state box in stats
- keep `all-servers` as an internal slug while presenting `Todos los servidores`
- stop rendering player IDs in public table rows

## Steps

1. Reviewed the real HTML and JS used by home, stats, ranking and the visible recent matches section.
2. Removed noisy helper copy from the relevant public sections.
3. Hid the initial stats search state box while preserving validation and error states.
4. Normalized annual stats server labels for visible output.
5. Removed player ID rendering from the public annual stats table and the ranking table.
6. Polished the countdown capsule styling with a stronger but still compact warm accent.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `frontend/index.html`
- `frontend/stats.html`
- `frontend/ranking.html`
- `frontend/assets/js/stats.js`
- `frontend/assets/js/ranking.js`
- `frontend/assets/css/styles.css`

## Expected Files to Modify

- `frontend/index.html`
- `frontend/stats.html`
- `frontend/historico.html`
- `frontend/assets/js/historico-recent-live.js`
- `frontend/assets/js/stats.js`
- `frontend/assets/js/ranking.js`
- `frontend/assets/css/styles.css`

## Constraints

- No backend changes.
- No docker-compose or scheduler changes.
- No asset or image changes.
- Keep search by name or ID working internally.
- Keep `all` and `all-servers` as internal values only.

## Validation

- `node --check frontend/assets/js/stats.js`
- `node --check frontend/assets/js/ranking.js`
- Search frontend for the removed visible copy strings.
- Search frontend for `Objetivo:` regression.
- Check that stats and ranking table rows no longer render player IDs.

## Outcome

- Home countdown label is visually stronger without stretching full width.
- The extra helper copy under public servers is gone.
- The redundant recent matches note was removed from the visible panel where it was actually rendered.
- Stats no longer shows the initial search status box before any search.
- Annual stats visible server output now uses `Todos los servidores`.
- Stats annual rows and ranking rows no longer render player IDs in the public tables.
