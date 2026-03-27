# Elo Discipline Leave And Death Classification Model

## Scope

This document records the discipline and death-type boundary implemented in
TASK-119.

## Persisted Exact Inputs

- `teamkill_exact_count`
  - source: canonical scoreboard fact `teamkills`
  - status: exact for caused teamkills per player-match

## Persisted Proxy Inputs

- `combat_death_proxy_count`
  - source: summary-backed canonical `death_classification_events`
  - status: approximate
- `friendly_fire_proxy_count`
  - source: summary-backed teamkill event lineage
  - status: approximate

## Persisted Unavailable Inputs

- `leave_disconnect_exact_count`
- `kick_or_ban_exact_count`
- `admin_action_exact_count`
- `redeploy_death_exact_count`
- `suicide_death_exact_count`
- `menu_exit_death_exact_count`

These remain zero-valued with explicit capability fields set to
`not_available`. They do not mean the event count was observed as zero.

## Capability Fields

- `discipline_capability_status`
- `leave_admin_capability_status`
- `death_type_capability_status`
- `discipline_lineage_status`

Current meanings:

- discipline is `partial` or `approximate`
  - exact for caused teamkills
  - proxy-only for broader leave/discipline behavior
- leave/admin lineage is `not_available`
- death-type lineage is `approximate` when summary-backed death classification
  coverage exists for the match, otherwise `not_available`

## Boundary

Implemented now:

- exact caused teamkill count
- approximate combat and friendly-fire summary lineage

Still not implemented as exact:

- redeploy deaths
- suicide deaths
- menu-exit deaths
- disconnect before end
- explicit leave without return
- kick, ban or admin removal attribution

## Audit Rule

Later tasks must distinguish:

- exact zero from supported exact capture
- approximate zero from summary-backed proxy coverage
- `not_available` from unsupported telemetry
