# Monthly MVP V2 Scoring Design

## Validation Date

- 2026-03-24

## Objective

Definir una formula V2 precisa, explicable e implementable para el MVP mensual
usando la base V1 ya aprobada y solo las senales avanzadas V2 que hoy tienen
soporte real en la repo.

## Evidence Base

This proposal is based on:

- `docs/monthly-mvp-ranking-scoring-design.md`
- `docs/monthly-player-ranking-data-audit.md`
- `docs/player-event-pipeline-v2-design.md`
- `backend/app/monthly_mvp.py`
- `backend/app/player_event_aggregates.py`
- `backend/app/historical_snapshots.py`
- `backend/app/payloads.py`

## Design Position

V2 should not replace the V1 logic with a radically different opaque model.

The correct direction is:

- keep V1 as the stable baseline
- preserve the same monthly UTC window and closed-match policy
- add a small set of advanced event-derived signals with limited weight
- avoid weapon-type or kill-type complexity until the source is richer

## Meaning Of MVP In V2

V2 still means "best monthly player", not "best fragger only".

Compared with V1, V2 should reward:

- sustained offensive output
- team contribution
- efficiency over the month
- cleaner player-vs-player control in repeated encounters
- better discipline through a stricter teamkill penalty

## Signals Included In V2

V2 keeps these V1 signals:

- total kills
- total support
- KPM recomputed from monthly totals
- KDA recomputed from monthly totals
- participation based on monthly time played
- monthly teamkills as penalty input

V2 adds these advanced signals:

- `most_killed`
- `death_by`
- net duel summaries

These signals are used only as modest scoring components, not as the core of
the ranking.

## Signals Explicitly Excluded From V2 Formula

Do not score these yet:

- weapon-type weighting
- kill-category weighting
- weapon variety bonus
- `death_by_weapons`
- combat, offense and defense
- win/loss context

Reason:

- the current CRCON-derived V2 layer is partial and summary-based
- weapon and type semantics are not robust enough for a serious weighted score
- adding too many low-confidence knobs would make V2 harder to defend than V1

Weapon kills remain useful for product readouts and future analysis, but not as
a weighted scoring factor in this phase.

## Eligibility Rules

Player eligibility for V2 should remain identical to V1:

- at least `6` closed matches in the selected month and scope
- at least `21600` seconds (`6` hours) played in the selected month and scope
- non-null monthly totals for kills, deaths, support and time

Additional publication gate for the ranking itself:

- publish V2 only when the selected month and scope have matching player-event
  coverage for that same `month_key`

This avoids ranking a month with V1 totals but missing V2 event coverage.

## Derived Advanced Metrics

For each eligible player-month, derive:

- `most_killed_count`
  - kills against the player most often killed by this player in the month
- `death_by_count`
  - deaths suffered from the player that killed this player most often in the
    month
- `rivalry_edge_raw = max(0, most_killed_count - death_by_count)`
- `duel_control_raw`
  - sum of positive `net_duel_value` across the player's top `3` duel pairs in
    the selected month and scope

Then normalize:

- `rivalry_edge_score = 100 * ln(1 + rivalry_edge_raw) / ln(1 + max_rivalry_edge_raw_eligible)`
- `duel_control_score = 100 * ln(1 + duel_control_raw) / ln(1 + max_duel_control_raw_eligible)`

## Small-Sample Treatment

Advanced event signals should be damped on low-volume months.

Use:

- `advanced_confidence = min(1, total_kills / 35)`

Effect:

- under `35` kills, advanced components contribute only partially
- at `35+` kills, the full advanced weight is available

This keeps V2 from overreacting to tiny rivalry samples.

## Normalized Core Component Scores

V2 keeps the same V1 normalization style on a `0..100` scale:

- `kills_score = 100 * ln(1 + total_kills) / ln(1 + max_total_kills_eligible)`
- `support_score = 100 * ln(1 + total_support) / ln(1 + max_total_support_eligible)`
- `kpm_score = 100 * ln(1 + kpm) / ln(1 + max_kpm_eligible)`
- `kda_score = 100 * ln(1 + kda) / ln(1 + max_kda_eligible)`
- `participation_score = 100 * min(1, total_time_seconds / 28800)`

## V2 Teamkill Penalty

V2 should be slightly stricter than V1 on discipline.

Use:

- `teamkill_penalty_v2 = min(8, total_teamkills * 0.75)`

Effect:

- `1` teamkill subtracts `0.75`
- `4` teamkills subtract `3`
- penalty caps at `8`

## V2 Scoring Formula

Recommended V2 monthly MVP score:

`mvp_v2_score = 0.30 * kills_score + 0.18 * support_score + 0.18 * kpm_score + 0.12 * kda_score + 0.10 * participation_score + advanced_confidence * (0.07 * rivalry_edge_score + 0.05 * duel_control_score) - teamkill_penalty_v2`

Weight rationale:

- `30%` kills keeps offense as the main visible driver
- `18%` support preserves MVP rather than pure frag logic
- `18%` KPM rewards productive time
- `12%` KDA rewards cleaner performance without dominating the table
- `10%` participation keeps monthly presence relevant
- `7%` rivalry edge rewards players who repeatedly finish ahead in their
  strongest recurring encounter
- `5%` duel control adds a second advanced signal but keeps it clearly bounded

## Why Weapon Kills Are Not Weighted Yet

The repository can already expose kills by weapon, but the current source layer:

- is summary-based, not a full raw kill feed
- does not yet prove a stable weapon taxonomy for competitive weighting
- would invite fragile distinctions such as tank vs infantry vs artillery too
  early

Decision:

- do not weight kills by weapon in V2
- do not assign bonus or penalty by weapon type
- keep weapon-kill outputs as audit and UI-facing data only

## Tie-Break Rules

If two players have the same `mvp_v2_score`, resolve ties in this order:

1. higher `advanced_confidence`
2. higher `participation_score`
3. higher `kills_score`
4. higher `rivalry_edge_score`
5. lower `total_teamkills`
6. alphabetical `display_name`
7. stable player key as final deterministic fallback

## Coexistence With V1

V1 and V2 should coexist explicitly:

- `V1` remains the stable default ranking
- `V2` is a separate ranking version with its own `ranking_version`
- both versions should use the same month and scope selectors
- V2 should never overwrite or reinterpret the V1 payload contract

## Implementation Guidance For Next Task

The backend task should compute V2 from:

- the same monthly player totals already used by V1
- direct player-event monthly aggregates derived from the raw ledger

Required per-player V2 outputs:

- `mvp_v2_score`
- `advanced_confidence`
- `rivalry_edge_raw`
- `duel_control_raw`
- `component_scores`
- `teamkill_penalty_v2`

Recommended `ranking_version`:

- `v2`

## Final Recommendation

The correct V2 for the current repository is an incremental evolution of V1:

- keep the same explainable weighted-score structure
- add only `most_killed` / `death_by` / duel-derived pressure signals
- make discipline stricter
- refuse weapon-type weighting until the signal quality improves

This yields a V2 that is materially richer than V1 without becoming speculative.
