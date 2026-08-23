---
id: TASK-300
title: Restore current-match killfeed from CRCON Log Stream
status: done
type: backend
team: Backend Senior
supporting_teams: [Arquitecto Python, Frontend Senior]
roadmap_item: crcon-migration
priority: critical
---

# TASK-300 - Restore current-match killfeed from CRCON Log Stream

## Goal

Restore the ordered current-match killfeed in selectable CRCON mode by
consuming the authenticated CRCON 12.0.1 `ws/logs` stream for `KILL` and
`TEAM KILL`, while keeping the existing snapshot contract and immediate
legacy rollback.

## Context

TASK-299 made `get_public_info` plus `get_live_game_stats` the API-only CRCON
source for current-match summary and player statistics. Those endpoints do not
contain an ordered event sequence, so the CRCON kill window is intentionally
empty. CRCON 12.0.1 provides that missing live sequence through its native
bounded Log Stream websocket.

The browser continues to poll only HLL Vietnam's snapshot endpoint. The
backend owns authentication and a bounded process-local event window. The
stream is disabled by default upstream, so disabled, denied and unavailable
states are normal degradations rather than reasons to mix legacy events into a
CRCON snapshot.

## Exact Implementation Plan

1. Add a small synchronous CRCON websocket client compatible with the current
   `ThreadingHTTPServer` process. Subscribe only to the verified action values
   `KILL` and `TEAM KILL` and send `Authorization: Bearer <token>` only from the
   backend.
2. Configure credentials separately through
   `HLL_CRCON_LOG_STREAM_TOKENS`, keyed by server slug. Never store a token in a
   `ServerTarget`, URL, response, diagnostic or frontend asset.
3. Maintain one background consumer and one lock-protected `deque(maxlen=18)`
   per enabled CRCON target. Preserve stream order, deduplicate by CRCON stream
   ID and retain each target's `last_seen_id` for reconnect.
4. Classify each target as `AVAILABLE`, `DISABLED`, `AUTH_FAILED` or
   `UNAVAILABLE`. Reconnect with bounded exponential backoff. On an invalid
   stream cursor, clear the cursor, flag an event gap and re-establish from the
   current upstream tail without fabricating events.
5. Map sanitized stream rows into the existing `KillEvent` and compatibility
   payload shapes. Keep `player_id` opaque and optional; tolerate missing
   weapon and player IDs.
6. Use current-match identity/start time to reset and filter the visible
   window on a real match transition, while retaining the websocket connection
   and cursor. Never reset because player count reaches zero.
7. Add a `crcon-log-stream` source state and killfeed capability metadata to
   snapshots. If the stream is degraded, retain valid CRCON summary/player
   stats with an empty or partial killfeed and never call the legacy event path.
8. Start/stop consumers with the backend process. Keep lifecycle idempotent,
   bounded and inactive in explicit legacy mode.
9. Validate contract parsing, auth, actions, ordering, cursors, duplicate
   replay, reconnect/backoff, target isolation, match boundaries, compatibility
   mapping and degraded no-fallback behavior with local fakes.

## Files to Read First

- `AGENTS.md`
- `ai/architecture-index.md`
- `ai/repo-context.md`
- `ai/orchestrator/backend-senior.md`
- `ai/orchestrator/python-architect.md`
- `backend/app/current_match.py`
- `backend/app/main.py`

## Expected Files to Modify

- `backend/app/crcon/log_stream.py`
- `backend/app/config.py`
- `backend/app/current_match.py`
- `backend/app/main.py`
- `backend/requirements.txt`
- `backend/tests/test_crcon_log_stream.py`
- `backend/tests/test_crcon_current_match.py`
- `ai/tasks/done/TASK-300-restore-current-match-killfeed-from-crcon-log-stream.md`

The websocket boundary and its focused tests justify exceeding the usual
five-file preference; frontend, persistence, deployment and upstream CRCON
files remain outside scope.

## Constraints

- Local implementation only; do not deploy or mutate remote CRCON.
- Use only CRCON 12.0.1 `ws/logs` for current-match events.
- Do not add direct RCON, `GetAdminLog`, persistence or browser credentials.
- Preserve `HLL_CURRENT_MATCH_SOURCE=legacy|crcon|shadow` and never silently
  mix legacy kills into a CRCON snapshot.
- Keep historical, ranking, stats, workers and storage unchanged.
- Preserve all frontend markup, styling and snapshot compatibility contracts.
- Treat all player IDs as opaque strings without platform inference.

## Validation

- Focused CRCON log-stream and current-match backend tests pass.
- Existing TASK-293 through TASK-299 focused backend tests remain green.
- Frontend snapshot transport tests remain green without frontend changes.
- `python -m compileall -q app tests` passes.
- Relevant integration checks are run when configured.
- `git diff --check` passes and the task outcome records the scoped file list.

## Outcome

Implemented locally on 2026-08-23 without deployment, remote CRCON mutation or
commits.

- Verified the exact upstream CRCON 12.0.1 contract at tag `v12.0.1`: route
  `ws/logs`, APIToken Bearer middleware, permission
  `api.can_view_structured_logs`, subscription cursor/action fields, response
  batches and exact action values `KILL` / `TEAM KILL`.
- Added `app.crcon.log_stream.CrconLogStreamManager`. It owns one daemon
  consumer per configured credential target and no request-scoped consumers.
  `app.main` starts consumers in `crcon`/`shadow` mode and closes connections,
  joins threads and closes the HTTP server during shutdown. Legacy mode does
  not start the manager.
- Added private environment-only credential configuration through
  `HLL_CRCON_LOG_STREAM_TOKENS`, a JSON object keyed by server slug. Tokens are
  absent from `ServerTarget`, URLs, frontend assets, response metadata and
  logs; the private target dataclass also suppresses the token from `repr`.
- The manager subscribes only to `KILL` and `TEAM KILL`, parses sanitized typed
  events and preserves every optional `player_id` as an opaque string. Missing
  player IDs and weapons are accepted without Steam/EOS inference.
- Each target owns an isolated lock-protected `deque(maxlen=18)`, matching the
  frontend's actual useful killfeed window. Events remain process-local only,
  preserve upstream order and deduplicate by the CRCON Redis stream ID.
- The last CRCON `last_seen_id` resumes each reconnect. Transient failures,
  disabled streams and auth failures retry with bounded exponential backoff.
  An invalid/stale cursor clears only the upstream resume cursor, records a
  visible gap, reconnects from the current CRCON tail and never fabricates
  missing events.
- The current match identity and start time filter the visible window. A true
  identity transition drops previous-match rows while preserving the active
  websocket/cursor; player count is not used as a reset signal.
- `CurrentMatchSnapshotService` maps stream rows into the existing `KillEvent`
  and compatibility payload contracts. The public opaque `kc2` cursor contains
  match plus canonical stream identity. Compatibility kill metadata now names
  `crcon-log-stream` accurately.
- Snapshot metadata now includes a `killfeed` capability object with source,
  exact operational status, availability, degradation and gap state, plus a
  `crcon-log-stream` source state. `AVAILABLE`, `DISABLED`, `AUTH_FAILED` and
  `UNAVAILABLE` remain distinguishable.
- A degraded/missing stream returns valid CRCON summary and player statistics
  with an empty or retained partial feed. It never switches kills to legacy
  AdminLog and never switches the complete snapshot to legacy implicitly.
- Added `websocket-client>=1.8,<2`; local validation used installed version
  `1.8.0`. No async framework or server migration was added.
- No configured current-match binding or token exists in the local process.
  No live connection was attempted and the honest validation result is
  `REAL_CRCON_LOG_STREAM = UNAVAILABLE_FOR_VALIDATION`.

Validation:

- TASK-293 through TASK-300 focused backend suite: 153 tests passed.
- CRCON Log Stream-focused suite: 14 tests passed, covering Bearer auth,
  actions, KILL/TK parsing, ordering, cursor resume, reconnect, replay and ID
  dedupe, stale cursor/gap, disabled/auth/unavailable states, backoff,
  per-target isolation, bounded window, match transition, opaque/optional IDs,
  snapshot mapping, stats preservation, no fallback and clean shutdown.
- Frontend snapshot transport/page suite: 37 tests passed; no frontend source
  file changed.
- `python -m compileall -q app tests`: passed.
- `git diff --check`: passed with only existing CRLF conversion warnings.
- Full backend discovery ran 271 tests. It retains four unrelated pre-existing
  failures: missing `pytest`, two historical materialization/read-model tests
  with Windows SQLite cleanup locks, and one historical runner maintenance
  expectation.
- `scripts/run-integration-tests.ps1`: historical UI validation passed; the
  unrelated pre-existing stats validation still fails because the annual
  ranking form is absent.

Scoped TASK-300 files:

- `backend/app/crcon/log_stream.py`
- `backend/app/config.py`
- `backend/app/current_match.py`
- `backend/app/main.py`
- `backend/requirements.txt`
- `backend/tests/test_crcon_log_stream.py`
- `backend/tests/test_crcon_current_match.py`
- this task lifecycle document

Operational follow-up before a deployment GO:

1. Enable Log Stream independently on each remote CRCON server.
2. Create a dedicated API token with only the required
   `api.can_view_structured_logs` permission.
3. Supply the token per server through secret environment configuration and
   perform an authorized real-match smoke/soak validation.

Local code recommendation: GO. Production functional-completeness declaration:
NO-GO until the operational enablement and real `ws/logs` validation above are
completed.

## Change Budget

- The websocket boundary, lifecycle integration and focused test module are a
  deliberate exception to the usual five-file preference.
- No unrelated refactor is authorized.
