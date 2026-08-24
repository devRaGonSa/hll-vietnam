# VIP rewards public-rule audit

TASK-315 verified the public home-page rules against the deployed VPS on
2026-08-24. This document records public semantics only; it intentionally omits
credentials, endpoints, webhooks, private identifiers and raw player data.

## Operator-provided policy

Annual VIP is an operator-provided product policy, not a bot-derived rule. A
player requests it by opening a ticket through the community's existing
official Discord invite. It uses an annual contribution/payment model. No price
was provided or published.

## Active automatic systems

### VIP Rewards weekly engine

`comunidadhll-vip-rewards.service` was enabled and active. Its canonical runtime
was `/opt/comunidadhll/bots/vip-rewards/rewards_runtime.py`; the sanitized rule
sources were `config.yml`, `weekly_rewards.py`, `vip_delivery_writer.py` and the
dated files under `missions/`. Runtime configuration confirmed non-dry-run live
delivery with its explicit write guard satisfied, scoped to HLL #1 and HLL #2.

The active `2026-08-24.yml` period covers 24–31 August 2026. Every challenge is
rewarded once per player in that weekly period and grants four VIP hours:

- 1,000 kills;
- 15,000 support points;
- 10,000 offense points;
- 12,000 defense points;
- 50 vehicles destroyed;
- 10 melee kills using the configured knife/shovel weapon family.

The player with the greatest combined playtime for the completed weekly period
receives 24 VIP hours. Distinct challenge rewards may stack. Delivery protects
indefinite VIP and unknown expiration states rather than overwriting them.

The standalone melee reward in `config.yml` is disabled. Its configured
24-hour value is therefore not advertised. The dated weekly melee challenge is
a separate, active rule and is advertised with its four-hour reward.
The `2026-08-17.yml` period is already closed, while `2026-08-31.yml` contains
template placeholder dates and is not the current runtime period; neither file
is used as current public copy.

### CRCON Seed VIP

The built-in CRCON `seed_vip` process was running on all three targets. The
effective configuration was read through
`rcon.user_config.seed_vip.SeedVIPUserConfig`, and behavior was checked against
`rcon/seed_vip/service.py` and `rcon/seed_vip/utils.py`. All targets were enabled,
non-dry-run and forwarding real VIP grants.

Eligibility requires at least 10 minutes of current-session play and being
online when both teams reach 25 players. HLL #1 and HLL #2 grant 24 hours per
completed seeding cycle; HLL Vietnam grants 12 hours. Temporary expiration is
cumulative. Existing indefinite VIP is excluded from extension.

`comunidadhll-disconnect-seed-vip.timer` was enabled and active. It starts Seed
VIP at 09:30 and stops it at 21:30 Europe/Madrid for three configured CRCON
targets. Its oneshot service is normally inactive between timer executions.

The separate `comunidadhll-custom-seed@1.service` and `@2.service` processes
were running but their unit description and environment identify them as
dry-run seeding-rule enforcement. They do not implement the public VIP reward
grant and are not presented as a separate reward mechanism.

## Unverified or inactive memories

- No CDO VIP reward was found.
- CDE occurred only as an unrelated commander-role translation in CRCON source;
  no CDE VIP reward was found.
- Knife and shovel are verified only as weapons in the active weekly 10-melee-
  kill challenge. The separate 24-hour melee path is disabled.
- `comunidadhll-vip-for-play.service` is named as a conflicting legacy service
  in configuration but is not installed, loaded or active. It is not advertised.

Future mission/configuration changes require a new read-only audit and a static
copy update; the website does not read host bot configuration dynamically.
