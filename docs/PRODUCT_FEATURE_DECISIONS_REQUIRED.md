# Product feature decisions required

Evidence date: 2026-08-23. These are product/API compatibility decisions, not
runtime or database decisions. No current HTML or active JavaScript flow uses
any of the features below, but their public routes, tests, docs and backend
entrypoints still exist. Local evidence cannot prove that external API clients
do not use them.

## 1. MVP V1 and V2

- **Current behavior:** two monthly formulas are exposed through live and
  snapshot API routes; both are hidden from the public Historical UI.
- **Technical cost:** V1 keeps historical snapshot computation; V2 also keeps
  the player-event ledger/worker. Keeping both has no documented product reason.
- **If removed:** the four MVP route/payload variants, their snapshot jobs and
  unreachable frontend helpers can be removed. Stored rows remain untouched
  until a later lifecycle task.
- **If retained:** approve exactly one formula. Prefer V1 because CRCON
  `player_stats` contains every input; calculate it on demand with a short TTL
  and no application gameplay persistence. V2 must use CRCON completed-match
  encounters, not the legacy raw ledger.
- **Recommended option:** remove both paused experiments. Reintroduce one
  CRCON-derived formula later only with an explicit visible product use case.

Decision needed: may the documented MVP API compatibility routes be removed?

## 2. Monthly player-event aggregate views

- **Current behavior:** API-only `most-killed`, `death-by`, `duels`,
  `weapon-kills` and `teamkills` views; there is no historical event timeline.
- **Technical cost:** generalized ledger, ingestion metadata, worker, snapshots
  and route surface built from match-summary rows rather than true events.
- **If removed:** current-match killfeed and completed match detail remain
  unchanged because they already use CRCON-native sources.
- **If retained:** derive completed facts from `get_map_scoreboard`; use Log
  Stream for live events and bounded `log_lines` only for an explicitly scoped
  raw-log product. Do not keep an application raw-event ledger.
- **Recommended option:** remove the monthly aggregate API feature and its
  worker/ledger dependency.

Decision needed: may these documented player-event compatibility routes be
removed, or which exact views and retention contract must remain?

## 3. Elo/MMR

- **Current behavior:** paused API-only leaderboard/player profiles, no current
  frontend consumer; rebuilds can still run from the historical runner or CLI.
- **Technical cost:** four application tables plus duplicated match/player facts
  and scheduled rebuild work for an approximate model.
- **If removed:** only the paused Elo API/jobs disappear; normal Ranking/Stats,
  match history and player profiles are unaffected.
- **If retained:** CRCON owns completed gameplay facts. Persist only same-game
  opaque player rating state and an idempotency cursor/checkpoint; do not merge
  HLL/HLLV IDs or infer Steam/EOS identity.
- **Recommended option:** remove Elo/MMR. A future reapproval can implement the
  documented minimum-state design without restoring legacy ingestion.

Decision needed: may the documented Elo/MMR routes and rebuild entrypoints be
removed?
