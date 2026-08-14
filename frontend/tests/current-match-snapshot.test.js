"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const snapshotRuntime = require("../assets/js/current-match-snapshot.js");

const OBSERVED_AT = "2026-08-14T08:15:00Z";

function kill(cursor, timestamp = OBSERVED_AT, overrides = {}) {
  return {
    cursor,
    timestamp,
    killer: { id: "killer", name: "Alpha", team: "Allies" },
    victim: { id: "victim", name: "Bravo", team: "Axis" },
    weapon: "SYNTHETIC_RIFLE",
    teamkill: false,
    match_id: "cm1.one",
    ...overrides,
  };
}

function snapshot(overrides = {}) {
  return {
    server: "comunidad-hispana-01",
    server_slug: "comunidad-hispana-01",
    match_id: "cm1.one",
    identity_kind: "canonical",
    map: "Synthetic Forest Warfare",
    layer: "synthetic_forest_warfare",
    mode: "warfare",
    started_at: "2026-08-14T08:00:00Z",
    score: { allied: 3, axis: 2 },
    remaining_seconds: 600,
    player_count: 2,
    max_player_count: 100,
    allied_count: 1,
    axis_count: 1,
    players: [
      {
        player_id: "alpha-id",
        name: "Alpha",
        team: "Allies",
        kills: 4,
        deaths: 2,
        teamkills: 0,
        deaths_by_teamkill: 0,
        favorite_weapon: "SYNTHETIC_RIFLE",
        combat: 40,
        offense: 10,
        defense: 20,
        support: 30,
        unit: "Able",
        role: "Rifleman",
        level: 50,
        status: "connected",
      },
    ],
    kills: [kill("kc1.one")],
    killfeed_truncated: false,
    version: "sv1.one",
    observed_at: OBSERVED_AT,
    sources: [{ source: "crcon-api", status: "fresh" }],
    degraded: false,
    degraded_reasons: [],
    ...overrides,
  };
}

test("missing transport configuration defaults to legacy", () => {
  assert.equal(snapshotRuntime.resolveCurrentMatchTransport(), "legacy");
});

test("explicit config transport has precedence over the body dataset", () => {
  assert.equal(
    snapshotRuntime.resolveCurrentMatchTransport({
      config: { currentMatchTransport: "snapshot" },
      dataset: { currentMatchTransport: "legacy" },
    }),
    "snapshot",
  );
});

test("explicit legacy and snapshot body transports are accepted", () => {
  assert.equal(
    snapshotRuntime.resolveCurrentMatchTransport({ dataset: { currentMatchTransport: "legacy" } }),
    "legacy",
  );
  assert.equal(
    snapshotRuntime.resolveCurrentMatchTransport({ dataset: { currentMatchTransport: "snapshot" } }),
    "snapshot",
  );
});

test("invalid transport safely selects legacy and is diagnosable", () => {
  const warnings = [];
  assert.equal(
    snapshotRuntime.resolveCurrentMatchTransport({
      config: { currentMatchTransport: "automatic" },
      dataset: { currentMatchTransport: "snapshot" },
      warn: (message) => warnings.push(message),
    }),
    "legacy",
  );
  assert.equal(warnings.length, 1);
});

test("transport selection starts exactly one owner", () => {
  const starts = [];
  snapshotRuntime.startSelectedTransport({
    transport: "snapshot",
    startLegacy: () => starts.push("legacy"),
    startSnapshot: () => starts.push("snapshot"),
  });
  assert.deepEqual(starts, ["snapshot"]);
});

test("one snapshot cycle performs exactly one snapshot HTTP call", async () => {
  const urls = [];
  const poller = snapshotRuntime.createSnapshotPoller({
    request: async () => {
      urls.push("/api/current-match/snapshot?server=comunidad-hispana-01");
      return snapshot();
    },
    applySnapshot: async () => {},
    schedule: () => 1,
  });
  await poller.start();
  poller.stop();
  assert.deepEqual(urls, ["/api/current-match/snapshot?server=comunidad-hispana-01"]);
  assert.equal(urls.some((url) => /^\/api\/current-match(?:\/kills|\/players)?\?/.test(url)), false);
});

test("legacy transport makes no snapshot request", () => {
  const urls = [];
  snapshotRuntime.startSelectedTransport({
    transport: "legacy",
    startLegacy: () => {
      urls.push(
        "/api/current-match?server=x",
        "/api/current-match/kills?server=x",
        "/api/current-match/players?server=x",
      );
    },
    startSnapshot: () => urls.push("/api/current-match/snapshot?server=x"),
  });
  assert.equal(urls.some((url) => url.includes("/snapshot")), false);
  assert.equal(urls.length, 3);
});

test("summary, players and killfeed adapt from the same snapshot", () => {
  const result = snapshotRuntime.processCurrentMatchSnapshot(
    snapshotRuntime.createSnapshotTransportState(),
    snapshot(),
    { nowMs: Date.parse(OBSERVED_AT) },
  );
  assert.equal(result.summary.match_id, "cm1.one");
  assert.equal(result.summary.allied_score, 3);
  assert.equal(result.summary.players, 2);
  assert.equal(result.players.scope, "cm1.one");
  assert.equal(result.players.items[0].player_name, "Alpha");
  assert.equal(result.killFeed.scope, "cm1.one");
  assert.equal(result.killFeed.items[0].event_id, "kc1.one");
});

test("missing snapshot values remain unavailable rather than fake zeroes", () => {
  const summary = snapshotRuntime.adaptSnapshotSummary(
    snapshot({ score: {}, player_count: null, max_player_count: null }),
  );
  assert.equal(summary.allied_score, null);
  assert.equal(summary.axis_score, null);
  assert.equal(summary.players, null);
  assert.equal(summary.player_count_quality, null);
});

test("a degraded same-match snapshot preserves trustworthy non-empty values", () => {
  const first = snapshotRuntime.processCurrentMatchSnapshot(
    snapshotRuntime.createSnapshotTransportState(),
    snapshot(),
    { nowMs: Date.parse(OBSERVED_AT) },
  );
  const second = snapshotRuntime.processCurrentMatchSnapshot(
    first.state,
    snapshot({
      version: "sv1.degraded",
      score: { allied: null, axis: null },
      remaining_seconds: null,
      player_count: null,
      players: [],
      kills: [],
      degraded: true,
      degraded_reasons: ["crcon-api-unavailable"],
    }),
    { nowMs: Date.parse(OBSERVED_AT) + 2000 },
  );
  assert.equal(second.summary.allied_score, 3);
  assert.equal(second.summary.players, 2);
  assert.equal(second.players.items[0].player_name, "Alpha");
  assert.equal(second.killFeed.items[0].event_id, "kc1.one");
  assert.equal(second.countdownSeconds, 598);
});

test("same snapshot version does not duplicate kills", () => {
  const first = snapshotRuntime.processCurrentMatchSnapshot(
    snapshotRuntime.createSnapshotTransportState(),
    snapshot(),
  );
  const second = snapshotRuntime.processCurrentMatchSnapshot(first.state, snapshot());
  assert.equal(second.unchangedVersion, true);
  assert.equal(second.killFeed.items.length, 1);
});

test("a new kill is added once", () => {
  const first = snapshotRuntime.processCurrentMatchSnapshot(
    snapshotRuntime.createSnapshotTransportState(),
    snapshot(),
  );
  const nextSnapshot = snapshot({
    version: "sv1.two",
    kills: [kill("kc1.one"), kill("kc1.two", "2026-08-14T08:15:01Z")],
  });
  const second = snapshotRuntime.processCurrentMatchSnapshot(first.state, nextSnapshot);
  const third = snapshotRuntime.processCurrentMatchSnapshot(second.state, nextSnapshot);
  assert.deepEqual(second.killFeed.items.map((event) => event.event_id), ["kc1.one", "kc1.two"]);
  assert.equal(third.killFeed.items.length, 2);
});

test("equal timestamps with different cursors remain distinct", () => {
  const result = snapshotRuntime.processCurrentMatchSnapshot(
    snapshotRuntime.createSnapshotTransportState(),
    snapshot({ kills: [kill("kc1.one"), kill("kc1.two")] }),
  );
  assert.deepEqual(result.killFeed.items.map((event) => event.event_id), ["kc1.one", "kc1.two"]);
});

test("a true match transition clears old event state", () => {
  const first = snapshotRuntime.processCurrentMatchSnapshot(
    snapshotRuntime.createSnapshotTransportState(),
    snapshot(),
  );
  const second = snapshotRuntime.processCurrentMatchSnapshot(
    first.state,
    snapshot({
      match_id: "cm1.two",
      started_at: "2026-08-14T09:00:00Z",
      map: "Synthetic Desert Warfare",
      layer: "synthetic_desert_warfare",
      kills: [kill("kc1.new", "2026-08-14T09:01:00Z", { match_id: "cm1.two" })],
    }),
  );
  assert.equal(second.trueMatchChanged, true);
  assert.deepEqual(second.killFeed.items.map((event) => event.event_id), ["kc1.new"]);
});

test("ephemeral to canonical stabilization replaces cursor state without a new-match signal", () => {
  const ephemeral = snapshot({
    match_id: "em1.same",
    identity_kind: "ephemeral",
    kills: [kill("kc1.ephemeral", OBSERVED_AT, { match_id: "em1.same" })],
  });
  const first = snapshotRuntime.processCurrentMatchSnapshot(
    snapshotRuntime.createSnapshotTransportState(),
    ephemeral,
  );
  const canonical = snapshot({
    match_id: "cm1.same",
    identity_kind: "canonical",
    kills: [kill("kc1.canonical", OBSERVED_AT, { match_id: "cm1.same" })],
  });
  const second = snapshotRuntime.processCurrentMatchSnapshot(first.state, canonical);
  assert.equal(second.identityStabilized, true);
  assert.equal(second.trueMatchChanged, false);
  assert.deepEqual(second.killFeed.items.map((event) => event.event_id), ["kc1.canonical"]);
});

test("identity stabilization accepts an identical start time", () => {
  const previous = snapshot({ match_id: "em1.same", identity_kind: "ephemeral" });
  const next = snapshot({ match_id: "cm1.same", identity_kind: "canonical" });
  assert.equal(snapshotRuntime.isIdentityStabilization(previous, next), true);
});

test("identity stabilization accepts a one-second start difference", () => {
  const previous = snapshot({ match_id: "em1.same", identity_kind: "ephemeral" });
  const next = snapshot({
    match_id: "cm1.same",
    identity_kind: "canonical",
    started_at: "2026-08-14T08:00:01Z",
  });
  assert.equal(snapshotRuntime.isIdentityStabilization(previous, next), true);
});

test("identity stabilization accepts TASK-291 map-history start tolerance", () => {
  const previous = snapshot({ match_id: "em1.same", identity_kind: "ephemeral" });
  for (const startedAt of ["2026-08-14T08:02:59Z", "2026-08-14T08:03:00Z"]) {
    const next = snapshot({
      match_id: "cm1.same",
      identity_kind: "canonical",
      started_at: startedAt,
    });
    assert.equal(snapshotRuntime.isIdentityStabilization(previous, next), true);
    assert.equal(snapshotRuntime.classifySnapshotTransition(previous, next), "identity-stabilized");
  }
  assert.equal(snapshotRuntime.CURRENT_MATCH_IDENTITY_START_TOLERANCE_MS, 180000);
});

test("identity stabilization rejects a start difference above 180 seconds", () => {
  const previous = snapshot({ match_id: "em1.same", identity_kind: "ephemeral" });
  const next = snapshot({
    match_id: "cm1.same",
    identity_kind: "canonical",
    started_at: "2026-08-14T08:03:01Z",
  });
  assert.equal(snapshotRuntime.isIdentityStabilization(previous, next), false);
  assert.equal(snapshotRuntime.classifySnapshotTransition(previous, next), "new-match");
});

test("identity stabilization rejects a different layer", () => {
  const previous = snapshot({ match_id: "em1.same", identity_kind: "ephemeral" });
  const next = snapshot({
    match_id: "cm1.same",
    identity_kind: "canonical",
    layer: "synthetic_desert_warfare",
  });
  assert.equal(snapshotRuntime.isIdentityStabilization(previous, next), false);
});

test("identity stabilization rejects a different server", () => {
  const previous = snapshot({ match_id: "em1.same", identity_kind: "ephemeral" });
  const next = snapshot({
    server: "comunidad-hispana-02",
    server_slug: "comunidad-hispana-02",
    match_id: "cm1.same",
    identity_kind: "canonical",
  });
  assert.equal(snapshotRuntime.isIdentityStabilization(previous, next), false);
});

test("identity stabilization rejects missing or malformed starts", () => {
  for (const [previousStartedAt, nextStartedAt] of [
    ["2026-08-14T08:00:00Z", null],
    ["2026-08-14T08:00:00Z", "not-a-timestamp"],
    [null, "2026-08-14T08:00:00Z"],
    ["not-a-timestamp", "2026-08-14T08:00:00Z"],
  ]) {
    const previous = snapshot({
      match_id: "em1.same",
      identity_kind: "ephemeral",
      started_at: previousStartedAt,
    });
    const next = snapshot({
      match_id: "cm1.same",
      identity_kind: "canonical",
      started_at: nextStartedAt,
    });
    assert.equal(snapshotRuntime.isIdentityStabilization(previous, next), false);
  }
});

test("canonical-to-canonical changes never count as identity stabilization", () => {
  const previous = snapshot({ match_id: "cm1.old", identity_kind: "canonical" });
  const next = snapshot({ match_id: "cm1.new", identity_kind: "canonical" });
  assert.equal(snapshotRuntime.isIdentityStabilization(previous, next), false);
});

test("opaque equal-time cursors retain authoritative server order", () => {
  const result = snapshotRuntime.processCurrentMatchSnapshot(
    snapshotRuntime.createSnapshotTransportState(),
    snapshot({
      kills: [kill("kc1.zulu"), kill("kc1.alpha"), kill("kc1.middle")],
    }),
  );
  assert.deepEqual(
    result.killFeed.items.map((event) => event.event_id),
    ["kc1.zulu", "kc1.alpha", "kc1.middle"],
  );
  assert.deepEqual(
    [...result.killFeed.items]
      .sort(snapshotRuntime.compareKillFeedEvents)
      .map((event) => event.event_id),
    ["kc1.zulu", "kc1.alpha", "kc1.middle"],
  );
  assert.equal(new Set(result.killFeed.items.map((event) => event.event_id)).size, 3);
});

test("a later poll does not reorder opaque equal-time cursors", () => {
  const orderedKills = [kill("kc1.zulu"), kill("kc1.alpha"), kill("kc1.middle")];
  const first = snapshotRuntime.processCurrentMatchSnapshot(
    snapshotRuntime.createSnapshotTransportState(),
    snapshot({ kills: orderedKills }),
  );
  const second = snapshotRuntime.processCurrentMatchSnapshot(
    first.state,
    snapshot({ version: "sv1.two", kills: orderedKills }),
  );
  assert.deepEqual(
    second.killFeed.items.map((event) => event.event_id),
    ["kc1.zulu", "kc1.alpha", "kc1.middle"],
  );
});

test("a new equal-time event appends in authoritative server order", () => {
  const first = snapshotRuntime.processCurrentMatchSnapshot(
    snapshotRuntime.createSnapshotTransportState(),
    snapshot({ kills: [kill("kc1.zulu"), kill("kc1.alpha")] }),
  );
  const second = snapshotRuntime.processCurrentMatchSnapshot(
    first.state,
    snapshot({
      version: "sv1.two",
      kills: [kill("kc1.zulu"), kill("kc1.alpha"), kill("kc1.able")],
    }),
  );
  assert.deepEqual(
    second.killFeed.items.map((event) => event.event_id),
    ["kc1.zulu", "kc1.alpha", "kc1.able"],
  );
});

test("a truncated window without the previous cursor resynchronizes deterministically", () => {
  const first = snapshotRuntime.processCurrentMatchSnapshot(
    snapshotRuntime.createSnapshotTransportState(),
    snapshot({ kills: [kill("kc1.old")] }),
  );
  const second = snapshotRuntime.processCurrentMatchSnapshot(
    first.state,
    snapshot({
      version: "sv1.new-window",
      killfeed_truncated: true,
      kills: [kill("kc1.retained", "2026-08-14T08:16:00Z")],
    }),
  );
  assert.equal(second.resynchronized, true);
  assert.deepEqual(second.killFeed.items.map((event) => event.event_id), ["kc1.retained"]);
});

test("a truncated resync preserves authoritative equal-time server order", () => {
  const first = snapshotRuntime.processCurrentMatchSnapshot(
    snapshotRuntime.createSnapshotTransportState(),
    snapshot({ kills: [kill("kc1.old")] }),
  );
  const second = snapshotRuntime.processCurrentMatchSnapshot(
    first.state,
    snapshot({
      version: "sv1.new-window",
      killfeed_truncated: true,
      kills: [kill("kc1.zulu"), kill("kc1.alpha"), kill("kc1.middle")],
    }),
  );
  assert.equal(second.resynchronized, true);
  assert.deepEqual(
    second.killFeed.items.map((event) => event.event_id),
    ["kc1.zulu", "kc1.alpha", "kc1.middle"],
  );
});

test("legacy missing statistics retain the historical zero display", () => {
  for (const value of [null, undefined, "", "invalid"]) {
    assert.equal(snapshotRuntime.formatStatNumber(value), "0");
  }
});

test("snapshot missing statistics use the explicit unavailable display", () => {
  for (const value of [null, undefined, "", "invalid"]) {
    assert.equal(snapshotRuntime.formatStatNumber(value, "No disponible"), "No disponible");
  }
});

test("normal numeric statistics render identically for both transports", () => {
  for (const value of [0, 4, "12"]) {
    assert.equal(
      snapshotRuntime.formatStatNumber(value),
      snapshotRuntime.formatStatNumber(value, "No disponible"),
    );
  }
});

test("countdown initializes, progresses locally and preserves small drift", () => {
  const observedMs = Date.parse(OBSERVED_AT);
  const basis = snapshotRuntime.rebaseCountdown(null, snapshot(), observedMs, true);
  assert.equal(snapshotRuntime.getCountdownSeconds(basis, observedMs), 600);
  assert.equal(snapshotRuntime.getCountdownSeconds(basis, observedMs + 5000), 595);
  const smallCorrection = snapshotRuntime.rebaseCountdown(
    basis,
    snapshot({ remaining_seconds: 599, observed_at: "2026-08-14T08:15:01Z" }),
    observedMs + 1000,
  );
  assert.equal(smallCorrection, basis);
});

test("true match change forces a new countdown basis", () => {
  const first = snapshotRuntime.processCurrentMatchSnapshot(
    snapshotRuntime.createSnapshotTransportState(),
    snapshot(),
    { nowMs: Date.parse(OBSERVED_AT) },
  );
  const second = snapshotRuntime.processCurrentMatchSnapshot(
    first.state,
    snapshot({
      match_id: "cm1.two",
      started_at: "2026-08-14T09:00:00Z",
      observed_at: "2026-08-14T09:00:00Z",
      remaining_seconds: 3600,
    }),
    { nowMs: Date.parse("2026-08-14T09:00:00Z") },
  );
  assert.equal(second.countdownSeconds, 3600);
  assert.notEqual(second.state.countdownBasis, first.state.countdownBasis);
});

test("transient failure retains bounded last-good state", () => {
  const good = snapshotRuntime.processCurrentMatchSnapshot(
    snapshotRuntime.createSnapshotTransportState(),
    snapshot(),
  );
  const failed = snapshotRuntime.recordSnapshotFailure(good.state, {
    nowMs: 1234,
    status: 503,
  });
  assert.equal(failed.lastGoodSnapshot.match_id, "cm1.one");
  assert.equal(failed.lastFailureAt, 1234);
  assert.equal(failed.lastFailureStatus, 503);
});

test("HTTP 503 is handled without starting legacy transport", async () => {
  let legacyStarts = 0;
  let handledStatus = null;
  const poller = snapshotRuntime.startSelectedTransport({
    transport: "snapshot",
    startLegacy: () => {
      legacyStarts += 1;
    },
    startSnapshot: () => {
      const controller = snapshotRuntime.createSnapshotPoller({
        request: async () => {
          const error = new Error("unavailable");
          error.status = 503;
          throw error;
        },
        applySnapshot: async () => {},
        handleError: (error) => {
          handledStatus = error.status;
        },
        schedule: () => 1,
      });
      return controller;
    },
  });
  await poller.start();
  poller.stop();
  assert.equal(handledStatus, 503);
  assert.equal(legacyStarts, 0);
});

test("an unresolved request prevents overlapping snapshot requests", async () => {
  let requestCount = 0;
  let resolveRequest;
  const pending = new Promise((resolve) => {
    resolveRequest = resolve;
  });
  const poller = snapshotRuntime.createSnapshotPoller({
    request: async () => {
      requestCount += 1;
      return pending;
    },
    applySnapshot: async () => {},
    schedule: () => 1,
  });
  const first = poller.start();
  const second = poller.runCycle();
  assert.equal(requestCount, 1);
  assert.equal(poller.isInFlight(), true);
  resolveRequest(snapshot());
  await Promise.all([first, second]);
  poller.stop();
  assert.equal(requestCount, 1);
});

test("a failed request releases the poller for a future retry", async () => {
  let requestCount = 0;
  const poller = snapshotRuntime.createSnapshotPoller({
    request: async () => {
      requestCount += 1;
      if (requestCount === 1) {
        throw new Error("temporary");
      }
      return snapshot();
    },
    applySnapshot: async () => {},
    handleError: async () => {},
    schedule: () => 1,
  });
  await poller.start();
  assert.equal(poller.isInFlight(), false);
  await poller.runCycle();
  poller.stop();
  assert.equal(requestCount, 2);
});
