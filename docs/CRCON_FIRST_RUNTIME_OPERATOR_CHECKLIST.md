# CRCON-first runtime operator checklist

TASK-310 audit date: 2026-08-24. The canonical local process environment and
project `.env` contain none of the four required runtime inputs. No real CRCON,
WebSocket or PostgreSQL request was eligible, and no secret was discovered or
printed.

TASK-313 production handoff evidence on the same date supersedes that local
configuration result for the deployed environment: all four effective selectors
are `crcon`; the three configured HLL/HLLV targets passed the documented public
route smokes with HTTP 200; and default production Compose contains only
backend, frontend and PostgreSQL. This repository task does not copy or print
the deployed configuration.

## Current sanitized configuration result

| Input | Status | Credential |
| --- | --- | --- |
| `HLL_SERVER_TARGETS` | `NOT_CONFIGURED` | not applicable |
| `HLL_CRCON_CURRENT_MATCH_BINDINGS` | `NOT_CONFIGURED` | Authorization missing |
| `HLL_CRCON_LOG_STREAM_TOKENS` | `NOT_CONFIGURED` | token missing |
| `HLL_CRCON_DATABASE_URL` | `NOT_CONFIGURED` | SELECT-only credential missing |

Set these as environment/secret values for the local backend process. Do not
commit a populated `.env`, token, password or DSN. The examples below are
shape-only placeholders; the second server remains `hll` until its real target
configuration explicitly changes it to `hllv`.

## A. Canonical ServerTargets

Configure `HLL_SERVER_TARGETS` in the backend process environment:

```json
[
  {
    "key": "<SERVER_1_SLUG>",
    "display_name": "<SERVER_1_DISPLAY_NAME>",
    "server_number": 1,
    "game": "hll",
    "crcon_base_url": "https://<CRCON_1_HOST>",
    "enabled": true,
    "capabilities": ["live_state", "historical_maps", "event_logs"]
  },
  {
    "key": "<SERVER_2_SLUG>",
    "display_name": "<SERVER_2_DISPLAY_NAME>",
    "server_number": 2,
    "game": "hll",
    "crcon_base_url": "https://<CRCON_2_HOST>",
    "enabled": true,
    "capabilities": ["live_state", "historical_maps", "event_logs"]
  }
]
```

The URL must be an unauthenticated HTTP(S) origin: no username, password,
query or fragment. After configuration, validation loads the canonical
registry, requires HTTPS/TLS, calls `get_version` and requires exactly
`v12.0.1`, then calls `get_public_info`, `get_live_game_stats`,
`get_scoreboard_maps` and one bounded `get_map_scoreboard(map_id)` per enabled
HLL target. Evidence records only status/shape/count metadata.

## B. Dedicated website API token

In each CRCON 12.0.1 administrative UI:

1. Create one dedicated website/read API user; do not reuse an administrator
   or moderation token.
2. Grant only `api.can_view_player_history` and
   `api.can_view_structured_logs`.
3. Create/rotate one Bearer token for that user and deliver it through the
   backend secret environment. Do not place it in Git, a URL, HTML or browser
   JavaScript.
4. Configure an aligned `HLL_CRCON_CURRENT_MATCH_BINDINGS` object. Target slug,
   origin, server number and game must exactly match `HLL_SERVER_TARGETS`:

```json
{
  "<SERVER_1_SLUG>": {
    "display_name": "<SERVER_1_DISPLAY_NAME>",
    "api_base_url": "https://<CRCON_1_HOST>",
    "server_number": 1,
    "game": "hll",
    "enabled": true,
    "api_headers": {"Authorization": "Bearer <WEBSITE_READ_TOKEN>"},
    "capabilities": ["live_state", "historical_maps", "event_logs"],
    "log_server": "<DEPLOYED_LOG_LINES_SERVER_VALUE>",
    "log_game": 1
  },
  "<SERVER_2_SLUG>": {
    "display_name": "<SERVER_2_DISPLAY_NAME>",
    "api_base_url": "https://<CRCON_2_HOST>",
    "server_number": 2,
    "game": "hll",
    "enabled": true,
    "api_headers": {"Authorization": "Bearer <WEBSITE_READ_TOKEN>"},
    "capabilities": ["live_state", "historical_maps", "event_logs"],
    "log_server": "<DEPLOYED_LOG_LINES_SERVER_VALUE>",
    "log_game": 1
  }
}
```

Afterward, a bounded `get_players_history` name query is run with a small page
size. An exact opaque `player_id` query is attempted only when practical; no
name or ID is logged. Then `/api/stats/players/search` is exercised locally
with `HLL_HISTORICAL_AGGREGATE_SOURCE=crcon` and no legacy fallback.

## C. Log Stream enablement and token delivery

For each CRCON instance, an operator must open the CRCON Log Stream settings,
set **Log Stream enabled** to `true`, save through the normal CRCON operator
workflow, and leave these 12.0.1 defaults unchanged unless later evidence
justifies tuning:

```text
stream_size = 1000
startup_since_mins = 2
refresh_frequency_sec = 1
refresh_since_mins = 2
```

Configure the same least-privilege token in the backend secret environment:

```json
HLL_CRCON_LOG_STREAM_TOKENS={
  "<SERVER_1_SLUG>": "<WEBSITE_READ_TOKEN>",
  "<SERVER_2_SLUG>": "<WEBSITE_READ_TOKEN>"
}
```

The subsequent bounded smoke connects to `wss://<CRCON_HOST>/ws/logs`, verifies
TLS and Bearer authentication, KILL/TEAM KILL filtering, `last_seen_id`,
mapping and target isolation. It does not wait for a full match. If no relevant
event appears, transport/auth can be verified while real-event mapping remains
`INSUFFICIENT_EVIDENCE`.

## D. SELECT-only PostgreSQL DSN

An authorized database administrator must create a dedicated role using
[`CRCON_READ_ONLY_ROLE.sql`](./CRCON_READ_ONLY_ROLE.sql). The current repository
reads only `map_history`, `player_stats`, `steam_id_64`, `player_soldier`,
`player_names` and `log_lines`; it does not require blanket database SELECT.

Configure the resulting secret only in the backend process environment:

```text
HLL_CRCON_DATABASE_URL=postgresql://<ROLE>:<URL_ENCODED_PASSWORD>@<HOST>:<PORT>/<DATABASE>?sslmode=require
```

Afterward, `PostgresCrconRepository` must connect with its own
`default_transaction_read_only=on`, execute `BEGIN READ ONLY`, and verify
`SHOW transaction_read_only = on`. Validation inspects role metadata,
columns/types/indexes/foreign keys/unique constraints, and aggregate game
counts only. It never tests protection with mutation SQL and never dumps player
rows.

Required structural checks include `map_history`, `player_stats`,
`player_sessions`, `steam_id_64`, `player_soldier`, `player_names` and
`log_lines`; `player_stats.map_id -> map_history.id`, historical player/map
uniqueness, integer `map_history.game`, server scoping and nullable explicit
Steam metadata are recorded without data export.

Then bounded service and local-route probes cover server summary, rankings
(`kills`, `kd_ratio`, `combat`, `matches_considered`), and one opaque-ID player
profile. Major aggregate SQL receives `EXPLAIN` (not `EXPLAIN ANALYZE`) and is
classified `INDEX_OK`, `ACCEPTABLE`, `PERFORMANCE_RISK` or
`PERFORMANCE_BLOCKED`.

## CRCON-first local smoke selectors

Only after A-D are configured, launch the local backend with explicit values:

```text
HLL_SERVER_LIST_SOURCE=crcon
HLL_CURRENT_MATCH_SOURCE=crcon
HLL_HISTORICAL_MATCH_SOURCE=crcon
HLL_HISTORICAL_AGGREGATE_SOURCE=crcon
```

Exercise `/api/servers`, `/api/current-match/snapshot`, historical recent
matches/detail, server summary, `/api/ranking`, player search and player
profile. Temporarily select `currentMatchTransport=snapshot` through the
existing frontend runtime configuration or non-committed body dataset override.

Instrument the run so any access to HLL-owned gameplay history, snapshot,
AdminLog materialization, ranking snapshot or player index/profile snapshot
fails the validation. Expected active legacy readers are zero. Do not disable
any writer in this task.

## TASK-313 guarded deployed reader probe

Run this once inside a deployed backend container/process environment after the
normal health and route smokes are green:

```text
python -m app.tools.verify_crcon_first_readers
```

The command refuses to start unless every effective selector is `crcon`. It
starts only its own process-local native Log Stream reader, exercises the real
public route dispatcher and configured CRCON REST/PostgreSQL readers, verifies
that the kills projection selected `crcon-log-stream`, and stops that temporary
reader on exit. It never initializes/migrates storage, starts application
writers, changes deployment state or prints response payloads, match IDs,
player IDs, names, tokens or connection strings.

For the current three-target deployment, success is one sanitized JSON object
with `status=ok`, `enabled_target_count=3`, `route_count=20`,
`detail_route_count=3` and `legacy_reader_access_count=0`. Exact field order is
not significant. Any guarded legacy access, non-200 canonical route, missing
recent match for internal detail discovery, mixed selector or unexpected route
error exits nonzero.

This probe proves application-owned reader dispatch in its one-shot process. It
does not prove a live combat event occurred during the short window and does not
authorize stopping rollback writers.

TASK-313 recorded the production result: `status=ok`,
`enabled_target_count=3`, `route_count=20`, `detail_route_count=3` and
`legacy_reader_access_count=0`, while all four effective source selectors were
`crcon`. Therefore `CRCON_FIRST_ACTIVE_LEGACY_READERS=0` is proven for the
deployed reader cutover. This evidence does not authorize data, PostgreSQL or
volume deletion; automatic shutdown of all legacy writers; or deletion of
rollback images.
