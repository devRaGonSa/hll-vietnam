(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = api;
  }
  root.HLL_VIETNAM_CURRENT_MATCH_SNAPSHOT = Object.freeze(api);
})(typeof globalThis === "object" ? globalThis : this, function () {
  "use strict";

  const LEGACY_TRANSPORT = "legacy";
  const SNAPSHOT_TRANSPORT = "snapshot";
  const SNAPSHOT_POLL_INTERVAL_MS = 2000;
  const CURRENT_MATCH_IDENTITY_START_TOLERANCE_MS = 180 * 1000;

  function resolveCurrentMatchTransport({ config, dataset, warn } = {}) {
    const configured = config || {};
    const bodyDataset = dataset || {};
    const hasConfiguredValue = Object.prototype.hasOwnProperty.call(
      configured,
      "currentMatchTransport",
    );
    const value = hasConfiguredValue
      ? configured.currentMatchTransport
      : bodyDataset.currentMatchTransport;
    const normalized = String(value || LEGACY_TRANSPORT).trim().toLowerCase();
    if (normalized === LEGACY_TRANSPORT || normalized === SNAPSHOT_TRANSPORT) {
      return normalized;
    }
    if (typeof warn === "function") {
      warn(`Transporte de partida actual no valido: ${String(value)}. Se usara legacy.`);
    }
    return LEGACY_TRANSPORT;
  }

  function startSelectedTransport({ transport, startLegacy, startSnapshot }) {
    if (transport === SNAPSHOT_TRANSPORT) {
      return startSnapshot();
    }
    return startLegacy();
  }

  function createSnapshotTransportState() {
    return {
      matchId: "",
      identityKind: "",
      logicalMatchFingerprint: "",
      version: "",
      observedAt: "",
      lastEventCursor: "",
      knownKills: [],
      countdownBasis: null,
      lastGoodSnapshot: null,
      lastFailureAt: null,
      lastFailureStatus: null,
    };
  }

  function getLogicalMatchFingerprint(snapshot) {
    const server = normalizeValue(snapshot?.server_slug || snapshot?.server);
    const startedAt = normalizeValue(snapshot?.started_at);
    const map = normalizeValue(snapshot?.layer || snapshot?.map);
    return server && startedAt && map ? `${server}|${startedAt}|${map}` : "";
  }

  function classifySnapshotTransition(previousSnapshot, nextSnapshot) {
    if (!previousSnapshot) {
      return "initial";
    }
    if (previousSnapshot.match_id === nextSnapshot?.match_id) {
      return "same-match";
    }
    if (isIdentityStabilization(previousSnapshot, nextSnapshot)) {
      return "identity-stabilized";
    }
    return "new-match";
  }

  function isIdentityStabilization(previousSnapshot, nextSnapshot) {
    if (
      previousSnapshot?.identity_kind !== "ephemeral" ||
      nextSnapshot?.identity_kind !== "canonical"
    ) {
      return false;
    }
    const previousServer = normalizeValue(
      previousSnapshot.server_slug || previousSnapshot.server,
    );
    const nextServer = normalizeValue(nextSnapshot.server_slug || nextSnapshot.server);
    const previousMap = normalizeValue(previousSnapshot.layer || previousSnapshot.map);
    const nextMap = normalizeValue(nextSnapshot.layer || nextSnapshot.map);
    const previousStartedAt = Date.parse(previousSnapshot.started_at || "");
    const nextStartedAt = Date.parse(nextSnapshot.started_at || "");
    return Boolean(
      previousServer &&
        previousServer === nextServer &&
        previousMap &&
        previousMap === nextMap &&
        Number.isFinite(previousStartedAt) &&
        Number.isFinite(nextStartedAt) &&
        Math.abs(previousStartedAt - nextStartedAt) <=
          CURRENT_MATCH_IDENTITY_START_TOLERANCE_MS,
    );
  }

  function processCurrentMatchSnapshot(
    previousState,
    snapshot,
    { nowMs = Date.now(), killLimit = 18 } = {},
  ) {
    const state = previousState || createSnapshotTransportState();
    const transition = classifySnapshotTransition(state.lastGoodSnapshot, snapshot);
    const displaySnapshot = preserveDegradedSnapshotFields(
      state.lastGoodSnapshot,
      snapshot,
      transition,
    );
    const incomingKills = normalizeSnapshotKills(snapshot?.kills);
    const incomingKeys = new Set(incomingKills.map(getSnapshotKillKey));
    const continuityLost = Boolean(
      transition === "same-match" &&
        snapshot?.killfeed_truncated &&
        state.lastEventCursor &&
        !incomingKeys.has(state.lastEventCursor),
    );
    const resetWindow = transition !== "same-match" || continuityLost;
    const reconciledKills = (resetWindow
      ? incomingKills
      : mergeSnapshotKills(state.knownKills, incomingKills)
    )
      .sort(compareSnapshotKills)
      .slice(-killLimit);
    const countdownBasis = rebaseCountdown(
      state.countdownBasis,
      snapshot,
      nowMs,
      transition !== "same-match",
    );
    const nextState = {
      ...state,
      matchId: String(snapshot?.match_id || ""),
      identityKind: String(snapshot?.identity_kind || ""),
      logicalMatchFingerprint: getLogicalMatchFingerprint(snapshot),
      version: String(snapshot?.version || ""),
      observedAt: String(snapshot?.observed_at || ""),
      lastEventCursor: getSnapshotKillKey(reconciledKills[reconciledKills.length - 1]),
      knownKills: reconciledKills,
      countdownBasis,
      lastGoodSnapshot: displaySnapshot,
      lastFailureAt: null,
      lastFailureStatus: null,
    };
    return {
      state: nextState,
      transition,
      identityStabilized: transition === "identity-stabilized",
      trueMatchChanged: transition === "new-match",
      resynchronized: continuityLost,
      unchangedVersion: Boolean(
        transition === "same-match" && state.version && state.version === snapshot?.version,
      ),
      summary: adaptSnapshotSummary(displaySnapshot),
      players: adaptSnapshotPlayers(displaySnapshot),
      killFeed: adaptSnapshotKillFeed(snapshot, reconciledKills),
      countdownSeconds: getCountdownSeconds(countdownBasis, nowMs),
    };
  }

  function recordSnapshotFailure(previousState, { nowMs = Date.now(), status = null } = {}) {
    return {
      ...(previousState || createSnapshotTransportState()),
      lastFailureAt: nowMs,
      lastFailureStatus: status,
    };
  }

  function preserveDegradedSnapshotFields(previousSnapshot, snapshot, transition) {
    if (!snapshot?.degraded || transition !== "same-match" || !previousSnapshot) {
      return snapshot;
    }
    const previousScore = previousSnapshot.score || {};
    const nextScore = snapshot.score || {};
    return {
      ...snapshot,
      map: snapshot.map ?? previousSnapshot.map ?? null,
      layer: snapshot.layer ?? previousSnapshot.layer ?? null,
      mode: snapshot.mode ?? previousSnapshot.mode ?? null,
      started_at: snapshot.started_at ?? previousSnapshot.started_at ?? null,
      score: {
        allied: nextScore.allied ?? previousScore.allied ?? null,
        axis: nextScore.axis ?? previousScore.axis ?? null,
      },
      remaining_seconds:
        snapshot.remaining_seconds ?? previousSnapshot.remaining_seconds ?? null,
      player_count: snapshot.player_count ?? previousSnapshot.player_count ?? null,
      max_player_count:
        snapshot.max_player_count ?? previousSnapshot.max_player_count ?? null,
      allied_count: snapshot.allied_count ?? previousSnapshot.allied_count ?? null,
      axis_count: snapshot.axis_count ?? previousSnapshot.axis_count ?? null,
      players:
        Array.isArray(snapshot.players) && snapshot.players.length > 0
          ? snapshot.players
          : previousSnapshot.players || [],
    };
  }

  function adaptSnapshotSummary(snapshot) {
    const score = snapshot?.score || {};
    return {
      found: true,
      server_slug: snapshot?.server_slug || snapshot?.server || "",
      server_name: snapshot?.server || snapshot?.server_slug || "",
      status: snapshot?.degraded ? "degraded" : "online",
      map: snapshot?.map ?? null,
      map_pretty_name: snapshot?.map ?? null,
      map_id: snapshot?.layer ?? null,
      layer_id: snapshot?.layer ?? null,
      game_mode: snapshot?.mode ?? null,
      started_at: snapshot?.started_at ?? null,
      allied_score: score.allied ?? null,
      axis_score: score.axis ?? null,
      allied_players: snapshot?.allied_count ?? null,
      axis_players: snapshot?.axis_count ?? null,
      players: snapshot?.player_count ?? null,
      max_players: snapshot?.max_player_count ?? null,
      player_count_quality: snapshot?.player_count == null ? null : "reliable",
      remaining_match_time_seconds: snapshot?.remaining_seconds ?? null,
      captured_at: snapshot?.observed_at ?? null,
      updated_at: snapshot?.observed_at ?? null,
      match_id: snapshot?.match_id || "",
      identity_kind: snapshot?.identity_kind || "",
      version: snapshot?.version || "",
      sources: Array.isArray(snapshot?.sources) ? snapshot.sources : [],
      degraded: Boolean(snapshot?.degraded),
      degraded_reasons: Array.isArray(snapshot?.degraded_reasons)
        ? snapshot.degraded_reasons
        : [],
    };
  }

  function adaptSnapshotPlayers(snapshot) {
    const observedAt = snapshot?.observed_at ?? null;
    const items = Array.isArray(snapshot?.players)
      ? snapshot.players.map((player) => ({
          player_id: player?.player_id ?? null,
          player_name: player?.name || "",
          team: player?.team ?? null,
          kills: player?.kills ?? null,
          deaths: player?.deaths ?? null,
          teamkills: player?.teamkills ?? null,
          deaths_by_teamkill: player?.deaths_by_teamkill ?? null,
          favorite_weapon: player?.favorite_weapon ?? null,
          combat: player?.combat ?? null,
          offense: player?.offense ?? null,
          defense: player?.defense ?? null,
          support: player?.support ?? null,
          unit: player?.unit ?? null,
          role: player?.role ?? null,
          level: player?.level ?? null,
          status: player?.status ?? null,
          last_seen_at: observedAt,
        }))
      : [];
    return {
      server_slug: snapshot?.server_slug || snapshot?.server || "",
      scope: snapshot?.match_id || "",
      confidence: snapshot?.degraded ? "degraded" : "fresh",
      updated_at: observedAt,
      items,
      version: snapshot?.version || "",
      degraded: Boolean(snapshot?.degraded),
    };
  }

  function adaptSnapshotKillFeed(snapshot, kills = normalizeSnapshotKills(snapshot?.kills)) {
    return {
      server_slug: snapshot?.server_slug || snapshot?.server || "",
      scope: snapshot?.match_id || "",
      confidence: snapshot?.degraded ? "degraded" : "fresh",
      truncated_before: Boolean(snapshot?.killfeed_truncated),
      items: kills.map((event) => {
        const timestampMs = Date.parse(event.timestamp || "");
        return {
          event_id: event.cursor,
          event_timestamp: event.timestamp || null,
          server_time: Number.isFinite(timestampMs) ? Math.floor(timestampMs / 1000) : null,
          killer_id: event.killer?.id ?? null,
          killer_name: event.killer?.name ?? null,
          killer_team: event.killer?.team ?? null,
          victim_id: event.victim?.id ?? null,
          victim_name: event.victim?.name ?? null,
          victim_team: event.victim?.team ?? null,
          weapon: event.weapon ?? null,
          is_teamkill: Boolean(event.teamkill),
          match_id: event.match_id || snapshot?.match_id || "",
          _snapshot_event: true,
          _snapshot_order: event._snapshot_order,
        };
      }),
      version: snapshot?.version || "",
      degraded: Boolean(snapshot?.degraded),
    };
  }

  function rebaseCountdown(previousBasis, snapshot, nowMs, force = false) {
    if (
      snapshot?.remaining_seconds === null ||
      snapshot?.remaining_seconds === undefined ||
      snapshot?.remaining_seconds === ""
    ) {
      return force ? null : previousBasis;
    }
    const remainingSeconds = Number(snapshot?.remaining_seconds);
    if (!Number.isFinite(remainingSeconds) || remainingSeconds < 0) {
      return force ? null : previousBasis;
    }
    const observedAtMs = Date.parse(snapshot?.observed_at || "");
    const referenceMs = Number.isFinite(observedAtMs) ? observedAtMs : nowMs;
    const nextBasis = {
      deadlineMs: referenceMs + remainingSeconds * 1000,
      observedAtMs: referenceMs,
    };
    if (
      !force &&
      previousBasis &&
      Math.abs(previousBasis.deadlineMs - nextBasis.deadlineMs) <= 2000
    ) {
      return previousBasis;
    }
    return nextBasis;
  }

  function getCountdownSeconds(basis, nowMs = Date.now()) {
    if (!basis || !Number.isFinite(basis.deadlineMs)) {
      return null;
    }
    return Math.max(0, Math.ceil((basis.deadlineMs - nowMs) / 1000));
  }

  function createSnapshotPoller({
    request,
    applySnapshot,
    handleError,
    intervalMs = SNAPSHOT_POLL_INTERVAL_MS,
    schedule = (callback, delay) => setTimeout(callback, delay),
    clearSchedule = (timer) => clearTimeout(timer),
  }) {
    let stopped = true;
    let timer = null;
    let inFlight = null;

    async function runCycle() {
      if (stopped) {
        return null;
      }
      if (inFlight) {
        return inFlight;
      }
      inFlight = (async () => {
        try {
          const snapshot = await request();
          if (!stopped) {
            await applySnapshot(snapshot);
          }
          return snapshot;
        } catch (error) {
          if (!stopped && typeof handleError === "function") {
            await handleError(error);
          }
          return null;
        } finally {
          inFlight = null;
          if (!stopped) {
            timer = schedule(() => {
              timer = null;
              void runCycle();
            }, intervalMs);
          }
        }
      })();
      return inFlight;
    }

    function start() {
      if (!stopped) {
        return inFlight;
      }
      stopped = false;
      return runCycle();
    }

    function stop() {
      stopped = true;
      if (timer !== null) {
        clearSchedule(timer);
        timer = null;
      }
    }

    return {
      start,
      stop,
      runCycle,
      isInFlight: () => Boolean(inFlight),
    };
  }

  function normalizeSnapshotKills(kills) {
    return Array.isArray(kills)
      ? kills
          .filter((event) => Boolean(getSnapshotKillKey(event)))
          .map((event, index) => ({ ...event, _snapshot_order: index }))
      : [];
  }

  function mergeSnapshotKills(current, incoming) {
    const byCursor = new Map();
    [...(current || []), ...(incoming || [])].forEach((event) => {
      const key = getSnapshotKillKey(event);
      if (key) {
        byCursor.set(key, event);
      }
    });
    return [...byCursor.values()];
  }

  function getSnapshotKillKey(event) {
    return String(event?.cursor || "").trim();
  }

  function compareSnapshotKills(left, right) {
    const timestampOrder = String(left?.timestamp || "").localeCompare(
      String(right?.timestamp || ""),
    );
    if (timestampOrder !== 0) {
      return timestampOrder;
    }
    return Number(left?._snapshot_order) - Number(right?._snapshot_order);
  }

  function compareAdaptedSnapshotKillOrder(left, right) {
    if (!left?._snapshot_event || !right?._snapshot_event) {
      return null;
    }
    const leftOrder = Number(left._snapshot_order);
    const rightOrder = Number(right._snapshot_order);
    if (!Number.isFinite(leftOrder) || !Number.isFinite(rightOrder)) {
      return 0;
    }
    return leftOrder - rightOrder;
  }

  function compareKillFeedEvents(left, right) {
    const leftTime = Number(left?.server_time);
    const rightTime = Number(right?.server_time);
    if (Number.isFinite(leftTime) && Number.isFinite(rightTime) && leftTime !== rightTime) {
      return leftTime - rightTime;
    }
    const timestampOrder = String(left?.event_timestamp || "").localeCompare(
      String(right?.event_timestamp || ""),
    );
    if (timestampOrder !== 0) {
      return timestampOrder;
    }
    const snapshotOrder = compareAdaptedSnapshotKillOrder(left, right);
    return snapshotOrder === null
      ? String(left?.event_id || "").localeCompare(String(right?.event_id || ""))
      : snapshotOrder;
  }

  function formatStatNumber(value, missingValue = "0") {
    if (value === null || value === undefined || value === "") {
      return missingValue;
    }
    return Number.isFinite(Number(value)) ? String(Number(value)) : missingValue;
  }

  function normalizeValue(value) {
    return String(value || "").trim().toLowerCase();
  }

  return {
    LEGACY_TRANSPORT,
    SNAPSHOT_TRANSPORT,
    SNAPSHOT_POLL_INTERVAL_MS,
    CURRENT_MATCH_IDENTITY_START_TOLERANCE_MS,
    resolveCurrentMatchTransport,
    startSelectedTransport,
    createSnapshotTransportState,
    getLogicalMatchFingerprint,
    classifySnapshotTransition,
    isIdentityStabilization,
    processCurrentMatchSnapshot,
    recordSnapshotFailure,
    preserveDegradedSnapshotFields,
    adaptSnapshotSummary,
    adaptSnapshotPlayers,
    adaptSnapshotKillFeed,
    compareAdaptedSnapshotKillOrder,
    compareKillFeedEvents,
    formatStatNumber,
    rebaseCountdown,
    getCountdownSeconds,
    createSnapshotPoller,
  };
});
