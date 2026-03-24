# Monthly Player Ranking Data Audit

## Validation Date

- 2026-03-24

## Scope

Auditoria tecnica del estado real de datos para un futuro ranking mensual de
"mejores jugadores" usando:

- codigo y esquema historico del backend
- persistencia local en `backend/data/hll_vietnam_dev.sqlite3`
- snapshots historicos ya generados en `backend/data/snapshots/`
- discovery ya documentada de la fuente CRCON/scoreboard

No se implementa todavia ninguna formula de ranking, tabla nueva ni cambio de
UI.

## Evidence Reviewed

- `backend/app/historical_models.py`
- `backend/app/historical_storage.py`
- `backend/app/historical_ingestion.py`
- `backend/app/historical_snapshots.py`
- `backend/app/historical_snapshot_storage.py`
- `backend/app/payloads.py`
- `docs/historical-domain-model.md`
- `docs/historical-data-quality-notes.md`
- `docs/historical-crcon-source-discovery.md`
- `docs/historical-coverage-report.md`

## Current Persisted State

Local SQLite currently contains:

- `historical_servers`: `3`
- `historical_matches`: `9638`
- `historical_players`: `163506`
- `historical_player_match_stats`: `1062244`
- `historical_ingestion_runs`: `32`

Coverage visible in the local database today:

- `comunidad-hispana-01`: `8602` matches, from `2024-05-17T20:48:40Z` to `2026-03-23T16:01:20Z`
- `comunidad-hispana-02`: `753` matches, from `2025-11-04T17:10:19Z` to `2026-03-23T18:58:06Z`
- `comunidad-hispana-03`: `283` matches, from `2026-01-14T22:34:18Z` to `2026-03-08T18:11:52Z`

Important quality notes from the local dataset:

- all `historical_player_match_stats` rows have populated values for kills,
  deaths, teamkills, time, KPM, KDA, combat, offense, defense, support, level
  and team side
- `85,270 / 163,506` players have SteamID; the rest currently depend on
  `crcon-player:*` identity, so identity continuity is usable but not equally
  strong for every player
- all persisted matches have start/end timestamps, map and game mode
- `7,961 / 9,638` persisted matches currently have both allied/axis score

## What Is Persisted Today

### Match level

Persisted per match:

- server
- external match id
- creation/start/end timestamps
- map name, pretty name, game mode, image
- allied score
- axis score

Not persisted at match level:

- raw full CRCON JSON payload
- derived win/loss per player
- any tactical event ledger

### Player identity level

Persisted per player:

- stable player key
- display name
- SteamID when available
- source player id
- first seen / last seen

### Player per match level

Persisted per player-match row:

- level
- team side
- kills
- deaths
- teamkills
- time seconds
- kills per minute
- deaths per minute
- kill/death ratio
- combat
- offense
- defense
- support

## What Exists In CRCON Source But Is Not Persisted

The documented CRCON detail payload already exposes fields that the project does
not currently store:

- `kills_by_type`
- `kills_streak`
- `longest_life_secs`
- `shortest_life_secs`
- `most_killed`
- `death_by`
- `weapons`
- `death_by_weapons`

These fields are visible in the source discovery, but the current upsert logic
only persists the smaller normalized subset listed above.

## What Was Not Confirmed As Available

The current repository evidence does not confirm any stable source fields for:

- garrisons destroyed
- outposts destroyed
- direct duel history in a structured reusable form
- tactical actions such as node building, dismantling or commander abilities

For direct encounters, the source does expose `most_killed` and `death_by`, but
that is not the same thing as a complete duel graph and is not stored today.

## Availability And Reliability Matrix

| Metric / signal | Exists in source | Persisted today | Reliability for ranking | Extra work | V1? |
| --- | --- | --- | --- | --- | --- |
| Kills | Yes | Yes | High | None | Yes |
| Deaths | Yes | Yes | High | None | Yes |
| Support | Yes | Yes | High | None | Yes |
| Combat | Yes | Yes | Medium-High | Query only | Maybe |
| Offense | Yes | Yes | Medium-High | Query only | Maybe |
| Defense | Yes | Yes | Medium-High | Query only | Maybe |
| Teamkills | Yes | Yes | High as penalty signal | Query only | Maybe |
| Match count | Yes | Derivable | High | Query only | Yes |
| Time played | Yes | Yes | High | Query only | Yes |
| KPM | Yes | Yes | Medium-High if computed from totals, lower if averaging raw per-match KPM | Query only | Yes |
| KDA / KD ratio | Yes | Yes | Medium-High if computed from totals, lower if averaging raw per-match KDA | Query only | Yes |
| 100+ kill matches | Derivable | Exposed in leaderboard | Medium | None | No |
| Win/loss context | Partially | Derivable from team side + scores when scores exist | Medium | Query and validation | Maybe |
| Weapons profile | Yes | No | Medium-Low for V1 | New persistence/modeling | No |
| Kill streak / life metrics | Yes | No | Medium-Low for V1 | New persistence/modeling | No |
| Direct encounters / duels | Partial only | No | Low today | New extraction plus modeling | No |
| Garrisons destroyed | Not confirmed | No | Unknown | Source validation first | No |
| OPs destroyed | Not confirmed | No | Unknown | Source validation first | No |
| Tactical impact composite | Partial proxies only | Partial | Medium after design work | Query/design | No for strict V1 |

## Current Product Readiness

The backend is already able to expose monthly leaderboard snapshots, but only
for these metrics:

- `kills`
- `deaths`
- `support`
- `matches_over_100_kills`

This means:

- the project already supports a monthly ranking surface operationally
- the current ranking surface is narrower than the real data persisted in SQLite
- offense, defense, combat, KPM and KDA are available in the database but not
  yet wired as first-class monthly leaderboard metrics

## Recommendation For Ranking V1

A realistic V1 should use only metrics already persisted with strong coverage
and low modeling risk:

- total kills
- total support
- KPM recomputed from `SUM(kills) / SUM(time_seconds)`
- KDA recomputed from `SUM(kills) / NULLIF(SUM(deaths), 0)`
- minimum participation gate based on matches played and/or minutes played
- optional small penalty for teamkills

Why this is the safest V1:

- no new ingestion is required
- all needed raw fields already exist locally
- the ranking can avoid inflated outliers by requiring minimum activity
- KPM and KDA become more defensible when derived from totals, not from average
  of precomputed per-match ratios

## Recommendation For Ranking V2

A stronger V2 can expand the model with already persisted but not yet surfaced
signals:

- offense
- defense
- combat
- win/loss context derived from player side and match result when scores exist

V2 may also evaluate source-only fields if a later task decides to persist them:

- weapons-based detail
- kill streak and life-span signals
- partial rivalry/encounter signals from `most_killed` and `death_by`

## Metrics Not Recommended For Early Use

Not recommended for V1 and not yet defensible for a serious monthly ranking:

- garrisons destroyed
- OPs destroyed
- duel ranking
- generic "impact in match" as a single opaque score

Reason:

- either the source availability is not confirmed
- or the source exists but the project does not yet persist enough structure to
  make the metric auditable and stable

## Final Conclusion

The repository already has enough persisted historical data for a credible
monthly Top 3 V1 without touching ingestion:

- kills
- support
- time played
- deaths
- teamkills
- offense
- defense
- combat

The most realistic first release is a constrained monthly ranking based on
volume plus efficiency, using only persisted fields and explicit participation
thresholds. Tactical metrics such as garrisons, OPs and real duel graphs should
stay out of scope until the source is revalidated and the missing structures are
persisted deliberately.
