# CRCON current-match parity validation

## Decision

| Scope | Decision |
| --- | --- |
| HLL server-list contract / implementation | **GO** |
| HLL server-list runtime connectivity | **GO** |
| HLL current match | **INSUFFICIENT EVIDENCE** |
| HLLV current match | **UNVERIFIED** |

No current-match cutover was made. Legacy remains the default and no frontend,
deployment, CRCON, RCON, PostgreSQL or Redis state was changed.

## Evidence boundary

CRCON issue `#1186` is unrelated to kill accuracy. Issue `#1170` was the
historically related report, but its author later withdrew the initial live
stats diagnosis and associated the observed loss with historical/AdminLog
collection. Neither issue is evidence that the deployed 12.0.1 live endpoint
is correct or incorrect. Only local measurements produced by the observer may
support promotion.

## Observer

The reusable bounded observer is:

```powershell
cd backend
python -m app.observe_current_match_parity `
  --server comunidad-hispana-01 `
  --server comunidad-hispana-02 `
  --poll-seconds 3 `
  --max-duration 300 `
  --output ..\tmp\current-match-parity.json
```

The output is diagnostic only. It contains server keys, sanitized match hashes,
aggregate counts/deltas, timestamps and execution-salted player aliases. It
never contains raw player IDs, player names, raw CRCON responses, credentials,
origins or gameplay snapshots reusable by the application.

The observer:

- resolves canonical `ServerTarget` configuration first and can reuse the two
  already trusted HLL public origins when local target configuration is absent;
- uses only `get_public_info`, `get_live_game_stats`, `get_scoreboard_maps` and
  `get_map_scoreboard` from the typed client;
- creates API-only current-match bindings and makes CRCON PostgreSQL access
  impossible;
- reads the existing legacy current-match projections as regression evidence;
- uses a three-second default interval, existing 1.5-second cache/single-flight,
  per-request timestamps and a five-second synchronization tolerance;
- excludes temporally misaligned player stats from STAT conclusions;
- identifies matches from layer/start-derived current-match identity, never
  from player count;
- models `PRE_MATCH`, `MATCH_RUNNING`, `MAP_TRANSITION`, `MATCH_ENDED` and
  `NEXT_MATCH` and records transition convergence time;
- treats one-poll player-set differences as transient and differences surviving
  two polls as persistent;
- measures kills, deaths, teamkills, combat, offense, defense and support,
  including exact percentage, maximum/summed absolute delta, eventual
  convergence and systematic differences;
- retains the latest live observation per match only in memory and reconciles
  a completed match with list/detail scoreboard APIs;
- distinguishes an expected final-window delta from an unexplained delta only
  when the live poll is outside the configured close-final window or a matching
  later encounter supports the delta.

## Explicit promotion criteria

The starting criteria are deliberately conservative and encoded in the report:

1. At least three complete HLL matches in aggregate.
2. Both HLL targets observed, preferably across multiple maps/modes.
3. Map/layer convergence is 100% outside bounded transitions.
4. CRCON live observations sufficiently close to the final scoreboard provide
   at least 99% exact kill values for comparable players.
5. No unexplained relevant final deltas remain.
6. Player churn is transient or explained; persistent set differences are
   investigated.
7. The existing mapper preserves the public current-match contracts.

Legacy is not the oracle. Evidence priority is final CRCON scoreboard, close
CRCON live state, then legacy live state. A legacy/CRCON difference favorable
to CRCON live-to-final agreement is not a CRCON failure.

Runs with fewer than three complete matches are `INSUFFICIENT EVIDENCE` unless
they reveal a deterministic contract failure. Once sufficient evidence exists,
failure of the criteria is `NO-GO`; passing all criteria is `GO`.

## Bounded real run on 2026-08-21

The observer ran for a requested nine seconds at a three-second interval over:

- `comunidad-hispana-01`, HLL, server number 1;
- `comunidad-hispana-02`, HLL, server number 2.

It completed three cycles per target. Results:

| Metric | Target 1 | Target 2 | Aggregate |
| --- | ---: | ---: | ---: |
| polls | 3 | 3 | 6 |
| synchronized polls | 0 | 0 | 0 |
| CRCON unavailable polls | 3 | 3 | 6 |
| complete matches | 0 | 0 | 0 |
| unique comparable players | 0 | 0 | 0 |
| kill comparisons | 0 | 0 | 0 |
| final comparisons | 0 | 0 | 0 |
| transitions | 0 | 0 | 0 |
| unexplained deltas | 0 | 0 | 0 |

The typed client returned sanitized `CrconApiError` failures for public info and
live game stats on both targets. A separate read-only version probe identified
`SSLCertVerificationError` on both origins. TASK-297 subsequently established
that this was caused by local HTTPS inspection, not by an evidenced defect in
the CRCON origin certificate. TLS validation must not be disabled to manufacture
evidence.

Legacy returned old persisted fallback timestamps, not temporally comparable
live evidence, so no live-vs-legacy STAT conclusion was recorded. The observer
correctly excluded those samples.

## Available non-real test evidence

Synthetic and sanitized CRCON 12.0.1 fixtures validate the mechanics only:

- exact live values yield zero deltas;
- a delayed legacy kill that converges is classified eventually consistent;
- a repeated two-poll difference is systematic;
- a kill added after the last live poll is expected only when a later final
  encounter supports it;
- the same close-final delta without supporting evidence is unexplained;
- temporally separated polls produce TIMING evidence and no false STAT delta.

These tests do not count toward the real-match promotion threshold.

## TASK-297 TLS diagnosis on 2026-08-21

The two already authorized HLL targets were resolved from canonical local
configuration and inspected with SNI. Hostnames and private origins were
redacted from all retained diagnostics. Both targets produced the same facts:

| Check | Target 1 | Target 2 |
| --- | --- | --- |
| Python standard TLS | rejected, verify code 89 | rejected, verify code 89 |
| Python reason | CA Basic Constraints not marked critical | CA Basic Constraints not marked critical |
| normal `curl` verification | rejected, exit 35 | rejected, exit 35 |
| `curl` reason | revocation check unavailable | revocation check unavailable |
| OS/.NET policy and hostname | accepted / SAN match | accepted / SAN match |
| certificate validity | 2026-08-19 to 2026-11-17 UTC | 2026-08-19 to 2026-11-17 UTC |
| visible chain | leaf plus self-issued local inspection CA | leaf plus self-issued local inspection CA |
| negotiated protocol | TLS 1.2 | TLS 1.2 |

The visible issuer identifies AVG Web/Mail Shield and states that the
certificate was generated by AVG Antivirus for SSL/TLS scanning. The leaf has
a critical, non-CA Basic Constraints extension. The locally generated AVG CA
has `CA=true`, but its Basic Constraints extension is not critical. Python
3's OpenSSL 3.0.21-backed default context therefore rejects the intercepted
chain under its normal strict verification behavior. Normal Schannel `curl`
also rejects it because its revocation function cannot check the generated
certificate. The OS/.NET chain inspection reported no policy or SAN error, but
that does not override either secure client failure.

The `openssl` command-line executable was not installed in the local
environment. Python's standard OpenSSL-backed context supplied the independent
OpenSSL verification result, while .NET `SslStream` supplied the SNI chain,
protocol, validity, extension and hostname facts without accepting policy
errors. No complete certificate was retained or committed.

Evidence-backed classification for each target:

- `TLS_INTERCEPTION` because both visible leaf certificates are issued by the
  local AVG HTTPS scanner rather than exposing the origin chain;
- `TLS_OTHER` because that interception CA is rejected for non-critical Basic
  Constraints and normal `curl` cannot complete its revocation check;
- remediation boundary: `LOCAL_TLS_INTERCEPTION_FIX`;
- runtime result: `BLOCKED_BY_TLS`.

This evidence does not support `TLS_SERVER_CHAIN_INCOMPLETE`,
`TLS_HOSTNAME_MISMATCH`, `TLS_CERT_EXPIRED`, `TLS_PRIVATE_CA`,
`TLS_LOCAL_CA_STORE` or `TLS_PYTHON_CA_BUNDLE`. In particular, the interceptor
hides the CRCON origin chain, so no server-side origin-certificate conclusion
can be made from this environment.

No application CA-bundle option was added. An endpoint-specific CA bundle is
not a legitimate repair for a local inspection CA whose certificate profile is
rejected by strict verification, and treating the interceptor CA as an
application-owned private CA would cross the trust boundary. The local endpoint
security configuration must instead be repaired or its HTTPS inspection must
be adjusted by an authorized administrator so that all standard clients receive
a standards-compliant, revocation-checkable chain. Application certificate and
hostname verification remain unchanged and fail closed.

Because secure TLS was not established, TASK-297 stopped before further live
CRCON probes or parity observation, as required. It therefore observed zero
additional complete matches, maps, modes, lifecycle transitions, comparable
players, live/final stat samples or unexplained kill deltas. The stale legacy
snapshots remain excluded from STAT parity. Zero measured deltas in this run
would mean absence of evidence, not parity.

## TASK-297 secure TLS recheck after disabling AVG

AVG was temporarily disabled on the local development PC and both authorized
targets were rechecked without changing application trust configuration:

| Check | Target 1 | Target 2 |
| --- | --- | --- |
| Python standard TLS | accepted | accepted |
| `urllib` `/api/get_version` | `v12.0.1` | `v12.0.1` |
| typed `CrconApiClient.get_version` | `v12.0.1` | `v12.0.1` |
| normal `curl` | accepted, exit 0 | accepted, exit 0 |
| certificate issuer | Let's Encrypt / YE1 | Let's Encrypt / YE1 |
| AVG issuer visible | no | no |
| hostname/SAN | matched | matched |
| negotiated protocol | TLS 1.3 | TLS 1.3 |

The leaf validity dates remained 2026-08-19 through 2026-11-17 UTC. The
subject hostname was redacted and no certificate was retained. This confirms
that the previous TLS failure was environmental local AVG interception. No TLS
client, CA-bundle, hostname-validation or certificate-verification change is
required or retained in the application.

## TASK-297 bounded parity run after TLS recovery

The existing observer then ran over both authorized HLL targets for 300 seconds
with a requested three-second poll interval. It completed normally and retained
only its sanitized report:

| Metric | Target 1 | Target 2 | Aggregate |
| --- | ---: | ---: | ---: |
| polls | 29 | 29 | 58 |
| CRCON available polls | 29 | 29 | 58 |
| CRCON unavailable polls | 0 | 0 | 0 |
| `MATCH_RUNNING` observations | 29 | 29 | 58 |
| complete matches | 0 | 0 | 0 |
| transitions | 0 | 0 | 0 |
| synchronized legacy polls | 0 | 0 | 0 |
| live/final kill comparisons | 0 | 0 | 0 |
| unexplained final deltas | 0 | 0 | 0 |

Both live CRCON sources remained available throughout the run and no transport
errors were recorded. Neither active match ended during the bounded window, so
there was no completed map ID for `get_map_scoreboard`, no final scoreboard
sample and no legitimate map/mode coverage to claim. Consequently no player or
stat exactness percentage can be calculated. Zero unexplained deltas here means
no final comparisons existed; it is not evidence of parity.

The locally available legacy snapshots remained millions of seconds older than
the CRCON observations. All 58 comparisons were classified as timing mismatches
and excluded from STAT percentages. No lifecycle transition occurred, so
transition convergence remains unmeasured.

The TLS blocker is resolved for the current environment and server-list runtime
connectivity is `GO`. Current-match HLL returns to `INSUFFICIENT EVIDENCE`
because the required three complete matches and live/final comparisons were not
available. A later bounded run should reuse the same observer until it captures
at least three complete matches across both targets; no cutover task is
justified yet.

## TASK-298 bounded evidence run

One 2,400-second bounded run reused the existing observer over both authorized
HLL targets with a requested three-second interval. Its sanitized report is
stored locally under `tmp/parity-evidence/` and is not application or gameplay
storage.

| Metric | Target 1 | Target 2 | Aggregate |
| --- | ---: | ---: | ---: |
| polls | 230 | 230 | 460 |
| snapshot availability | 100% | 100% | 100% |
| unavailable polls | 0 | 0 | 0 |
| partial `CrconApiError` observations | 4 | 3 | 7 |
| detected map transitions | 1 | 1 | 2 |
| matched final scoreboards | 0 | 1 | 1 |

Target 1 moved from an old empty St. Marie Du Mont warfare identity to a new
identity on the same layer. The observer recorded `MAP_TRANSITION` followed by
`NEXT_MATCH` after 10.379 seconds, but no matching completed scoreboard was
available for the old identity, so it is not counted as a complete match.

Target 2 completed Utah Beach warfare with final score 3:2. CRCON recorded the
match from 14:08:48Z to 15:38:48Z; the observer detected the identity change at
15:40:32Z and recorded `NEXT_MATCH` 10.361 seconds later. The approximately
105-second gap between the final timestamp and visible identity rollover is a
server-specific transition observation, not a transport outage. The final map
association used server number, layer and start time and matched 21 players,
with zero only-live and zero only-final players.

The comparison exposed a real diagnostic collection defect. The typed
`get_live_game_stats` DTO and the typed final scoreboard both contained
kills/deaths/teamkills for every player, but the shared product snapshot
intentionally replaced those API counters with `None` whenever CRCON database
combat aggregation was disabled. As a result, the first completed match
produced no K/D/TK comparisons. It did produce 21 comparisons each for combat,
offense, defense and support, all 21 exact in every field (100%).

The observer now restores kills/deaths/teamkills from the same typed live API
response in its diagnostic snapshot only. The production current-match mapper,
TLS behavior and PostgreSQL boundary are unchanged. A real post-fix probe
confirmed K/D/TK presence for every current live player on both targets. No
player names, real IDs or raw responses are persisted.

The completed-match metrics are therefore:

| Field | Compared | Exact | Exact % | Max delta | Sum delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| kills | 0 | 0 | unavailable | 0 | 0 |
| deaths | 0 | 0 | unavailable | 0 | 0 |
| teamkills | 0 | 0 | unavailable | 0 | 0 |
| combat | 21 | 21 | 100% | 0 | 0 |
| offense | 21 | 21 | 100% | 0 | 0 |
| defense | 21 | 21 | 100% | 0 | 0 |
| support | 21 | 21 | 100% | 0 | 0 |

There were zero expected final-window deltas and zero unexplained deltas because
K/D/TK had no valid comparisons in this run. Those zeroes cannot support a kill
accuracy conclusion, and no systematic live kill undercount can yet be accepted
or rejected. Legacy remained too stale for STAT or player-set comparison.

At the end of the run, both newly started matches still had more than an hour
remaining. Extending the interactive observation would not guarantee the two
additional valid completed matches required for promotion. TASK-298 therefore
remains `INSUFFICIENT EVIDENCE`; a later bounded run must collect at least two
additional complete matches with post-fix K/D/TK comparisons before any GO
decision or cutover task is justified.
