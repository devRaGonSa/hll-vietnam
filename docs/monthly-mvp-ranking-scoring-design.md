# Monthly MVP Ranking Scoring Design

## Validation Date

- 2026-03-24

## Objective

Definir una formula V1 precisa y auditable para un ranking mensual de mejores
jugadores usando solo metricas ya persistidas y suficientemente fiables en el
repositorio.

## Evidence Base

This proposal is based on:

- `docs/monthly-player-ranking-data-audit.md`
- `docs/historical-domain-model.md`
- `docs/historical-data-quality-notes.md`
- `backend/app/historical_models.py`
- `backend/app/historical_storage.py`
- `backend/app/payloads.py`

The design assumes the existing monthly window already used by the backend:

- UTC calendar month
- closed matches only
- fallback to the previous closed month only when the current month has no
  closed matches at all

## V1 Meaning Of "Best Player Of The Month"

V1 should not mean "highest raw kills only" and should not pretend to measure
full tactical impact that the project does not persist yet.

For this project, "monthly MVP" in V1 means:

- sustained offensive contribution across the month
- meaningful team contribution through support
- good efficiency without rewarding one or two short outlier matches
- enough participation to make the result credible

This is therefore a balanced MVP model with a light offensive bias.

## Metrics Included In V1

Included metrics:

- total kills
- total support
- total time played
- KPM derived from monthly totals
- KDA derived from monthly totals
- optional teamkill penalty
- matches played as an eligibility guard

Derived metrics must be recomputed from monthly totals, not from the average of
per-match ratios:

- `kpm = total_kills / max(total_time_minutes, 1)`
- `kda = total_kills / max(total_deaths, 1)`

## Metrics Explicitly Out Of Scope For V1

Do not include in V1:

- combat
- offense
- defense
- matches over 100 kills
- win/loss context
- weapons profile
- kill streaks or life-span fields
- duels, `most_killed`, `death_by`
- garrisons, OPs or tactical events not confirmed as persisted

Reason:

- some are useful but would complicate the first release without improving
  reliability enough
- others are not persisted today or are not confirmed with stable semantics

## Eligibility Rules

A player is eligible for the monthly MVP ranking only if all conditions hold:

- played at least `6` closed matches in the selected month and scope
- accumulated at least `21600` seconds (`6` hours) of play time in that month
- has non-null persisted stats for kills, deaths, support and time

These gates are intentionally dual:

- match count blocks one-match outliers
- time played blocks short-session inflation

## Scope Recommendation

V1 should be computed in both scopes from the same formula:

- per server
- global aggregate using `all-servers`

Publication recommendation:

- default visible ranking: per server
- secondary comparable view: global aggregate

Why:

- per-server ranking is easier to interpret and fairer for each community shard
- the repository already supports the logical aggregate `all-servers`
- using one formula for both scopes avoids redesign later

## Normalized Component Scores

For each month and scope, first aggregate one row per eligible player.

Then calculate these normalized component scores on a `0..100` scale:

- `kills_score = 100 * ln(1 + total_kills) / ln(1 + max_total_kills_eligible)`
- `support_score = 100 * ln(1 + total_support) / ln(1 + max_total_support_eligible)`
- `kpm_score = 100 * ln(1 + kpm) / ln(1 + max_kpm_eligible)`
- `kda_score = 100 * ln(1 + kda) / ln(1 + max_kda_eligible)`
- `participation_score = 100 * min(1, total_time_seconds / 28800)`

Implementation notes:

- `ln(1 + x)` dampens extreme leaders without hiding real advantage
- participation reaches full score at `8` hours
- all `max_*_eligible` references are calculated inside the same month and scope

## V1 Scoring Formula

Recommended V1 monthly MVP score:

`mvp_score = 0.35 * kills_score + 0.20 * support_score + 0.20 * kpm_score + 0.15 * kda_score + 0.10 * participation_score - teamkill_penalty`

Weight rationale:

- `35%` kills: offensive impact should matter most in a first public ranking
- `20%` support: keeps the model closer to MVP than to a pure frag ranking
- `20%` KPM: rewards productive time, not only volume
- `15%` KDA: rewards cleaner performance but keeps it below kills volume
- `10%` participation: favors sustained monthly presence without turning the
  ranking into a pure grind chart

## Teamkill Penalty

Use a small optional penalty in V1:

- `teamkill_penalty = min(6, total_teamkills * 0.5)`

Effect:

- `1` teamkill subtracts `0.5`
- `4` teamkills subtract `2`
- penalty caps at `6`

This keeps the penalty visible without letting it dominate the ranking.

## Tie-Break Rules

If two players have the same `mvp_score`, resolve ties in this order:

1. higher `participation_score`
2. higher `kills_score`
3. higher `support_score`
4. lower `total_teamkills`
5. alphabetical `display_name`
6. stable player key as final deterministic fallback

## Why This V1 Is Reasonable

This design is defendable for a first release because it:

- uses only metrics already persisted with strong coverage
- recomputes efficiency from totals instead of averaging noisy per-match ratios
- blocks absurd winners from tiny samples with explicit eligibility gates
- stays interpretable enough to explain in product copy
- can be implemented from current monthly aggregates without new ingestion or
  schema work

## V2 Expansion Path

V2 can extend the same structure without redesigning the whole ranking:

- add combat, offense and defense as extra weighted components
- add win/loss context only where team scores are present and validated
- review whether teamkill penalty should become rate-based instead of absolute
- later add tactical metrics only after deliberate persistence work

The important constraint for V2 is to preserve the same shape:

- explicit eligibility
- normalized component scores
- weighted sum
- deterministic tie-breaks
