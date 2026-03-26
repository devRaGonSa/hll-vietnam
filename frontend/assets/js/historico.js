const HISTORICAL_SERVERS = Object.freeze([
  {
    slug: "comunidad-hispana-01",
    label: "Comunidad Hispana #01",
  },
  {
    slug: "comunidad-hispana-02",
    label: "Comunidad Hispana #02",
  },
  {
    slug: "comunidad-hispana-03",
    label: "Comunidad Hispana #03",
  },
  {
    slug: "all-servers",
    label: "Todos",
  },
]);
const HISTORICAL_SERVER_SLUGS = Object.freeze(
  HISTORICAL_SERVERS.map((server) => server.slug),
);
const DEFAULT_HISTORICAL_SERVER = "all-servers";
const SNAPSHOT_CACHE_TTL_MS = 120000;
const STALE_SNAPSHOT_CACHE_TTL_MS = 30000;
const NEGATIVE_SNAPSHOT_CACHE_TTL_MS = 15000;
let activeServerSlug = DEFAULT_HISTORICAL_SERVER;
let activeLeaderboardMetric;
let activeLeaderboardTimeframe;
let activeServerRequestId = 0;
let activeLeaderboardRequestId = 0;
const LEADERBOARD_TIMEFRAMES = Object.freeze([
  {
    key: "weekly",
    label: "Semanal",
    shortLabel: "semanal",
  },
  {
    key: "monthly",
    label: "Mensual",
    shortLabel: "mensual",
  },
]);
const LEADERBOARD_METRICS = Object.freeze([
  {
    key: "kills",
    title: "Top kills",
    valueHeading: "Kills",
    emptyMessage: "Sin datos historicos suficientes para mostrar este ranking de kills.",
  },
  {
    key: "deaths",
    title: "Top muertes",
    valueHeading: "Muertes",
    emptyMessage: "Sin datos historicos suficientes para mostrar este ranking de muertes.",
  },
  {
    key: "matches_over_100_kills",
    title: "Top partidas con 100+ kills",
    valueHeading: "Partidas 100+",
    emptyMessage: "Ningun jugador ha registrado partidas de 100+ kills en esta ventana.",
  },
  {
    key: "support",
    title: "Top puntos de soporte",
    valueHeading: "Soporte",
    emptyMessage: "Sin datos historicos suficientes para mostrar este ranking de soporte.",
  },
]);
const DEFAULT_LEADERBOARD_METRIC = LEADERBOARD_METRICS[0].key;
const DEFAULT_LEADERBOARD_TIMEFRAME = LEADERBOARD_TIMEFRAMES[0].key;
activeLeaderboardMetric = DEFAULT_LEADERBOARD_METRIC;
activeLeaderboardTimeframe = DEFAULT_LEADERBOARD_TIMEFRAME;

document.addEventListener("DOMContentLoaded", () => {
  const backendBaseUrl =
    document.body.dataset.backendBaseUrl || "http://127.0.0.1:8000";
  const selectorButtons = Array.from(
    document.querySelectorAll("[data-server-slug]"),
  );
  const leaderboardTimeframeButtons = Array.from(
    document.querySelectorAll("[data-leaderboard-timeframe]"),
  );
  const leaderboardTabButtons = Array.from(
    document.querySelectorAll("[data-leaderboard-metric]"),
  );
  const summaryNode = document.getElementById("historical-summary");
  const rangeNode = document.getElementById("historical-range");
  const summaryNoteNode = document.getElementById("historical-summary-note");
  const summarySnapshotMetaNode = document.getElementById(
    "historical-summary-snapshot-meta",
  );
  const weeklyTitleNode = document.getElementById("weekly-ranking-title");
  const weeklyStateNode = document.getElementById("weekly-leaderboard-state");
  const weeklyTableNode = document.getElementById("weekly-leaderboard-table");
  const weeklyBodyNode = document.getElementById("weekly-leaderboard-body");
  const monthlyMvpTitleNode = document.getElementById("monthly-mvp-title");
  const monthlyMvpStateNode = document.getElementById("monthly-mvp-state");
  const monthlyMvpListNode = document.getElementById("monthly-mvp-list");
  const monthlyMvpNoteNode = document.getElementById("monthly-mvp-note");
  const monthlyMvpSnapshotMetaNode = document.getElementById(
    "monthly-mvp-snapshot-meta",
  );
  const monthlyMvpV2TitleNode = document.getElementById("monthly-mvp-v2-title");
  const monthlyMvpV2StateNode = document.getElementById("monthly-mvp-v2-state");
  const monthlyMvpV2ListNode = document.getElementById("monthly-mvp-v2-list");
  const monthlyMvpV2NoteNode = document.getElementById("monthly-mvp-v2-note");
  const monthlyMvpV2SnapshotMetaNode = document.getElementById(
    "monthly-mvp-v2-snapshot-meta",
  );
  const comparisonStateNode = document.getElementById("mvp-comparison-state");
  const comparisonListNode = document.getElementById("mvp-comparison-list");
  const comparisonNoteNode = document.getElementById("mvp-comparison-note");
  const eloMmrStateNode = document.getElementById("elo-mmr-state");
  const eloMmrListNode = document.getElementById("elo-mmr-list");
  const eloMmrNoteNode = document.getElementById("elo-mmr-note");
  const eloMmrMetaNode = document.getElementById("elo-mmr-meta");
  const weeklyValueHeadingNode = document.getElementById("weekly-leaderboard-value-heading");
  const weeklyWindowNoteNode = document.getElementById("weekly-window-note");
  const weeklySnapshotMetaNode = document.getElementById(
    "weekly-leaderboard-snapshot-meta",
  );
  const recentStateNode = document.getElementById("recent-matches-state");
  const recentListNode = document.getElementById("recent-matches-list");
  const recentNoteNode = document.getElementById("recent-matches-note");
  const recentSnapshotMetaNode = document.getElementById(
    "recent-matches-snapshot-meta",
  );

  const params = new URLSearchParams(window.location.search);
  activeServerSlug = normalizeServerSlug(params.get("server"));
  activeLeaderboardMetric = normalizeLeaderboardMetric(params.get("metric"));
  activeLeaderboardTimeframe = normalizeLeaderboardTimeframe(
    params.get("timeframe"),
  );

  const summaryCache = new Map();
  const recentMatchesCache = new Map();
  const leaderboardCache = new Map();
  const monthlyMvpCache = new Map();
  const monthlyMvpV2Cache = new Map();
  const eloMmrCache = new Map();
  const pendingRequestCache = new Map();
  let latestMonthlyMvpResult = null;
  let latestMonthlyMvpV2Result = null;

  const getSummarySnapshot = (serverSlug) =>
    getCachedJson(
      summaryCache,
      pendingRequestCache,
      buildSummarySnapshotKey(serverSlug),
      `${backendBaseUrl}/api/historical/snapshots/server-summary?server=${encodeURIComponent(serverSlug)}`,
    );

  const getRecentMatchesSnapshot = (serverSlug) =>
    getCachedJson(
      recentMatchesCache,
      pendingRequestCache,
      buildRecentMatchesSnapshotKey(serverSlug),
      `${backendBaseUrl}/api/historical/snapshots/recent-matches?server=${encodeURIComponent(serverSlug)}&limit=10`,
    );

  const getLeaderboardSnapshot = (serverSlug, timeframeKey, metricKey) =>
    getCachedJson(
      leaderboardCache,
      pendingRequestCache,
      buildLeaderboardSnapshotKey(serverSlug, timeframeKey, metricKey),
      `${backendBaseUrl}/api/historical/snapshots/leaderboard?server=${encodeURIComponent(serverSlug)}&timeframe=${encodeURIComponent(timeframeKey)}&metric=${encodeURIComponent(metricKey)}&limit=10`,
    );

  const getMonthlyMvpSnapshot = (serverSlug) =>
    getCachedJson(
      monthlyMvpCache,
      pendingRequestCache,
      buildMonthlyMvpSnapshotKey(serverSlug),
      `${backendBaseUrl}/api/historical/snapshots/monthly-mvp?server=${encodeURIComponent(serverSlug)}&limit=3`,
    );

  const getMonthlyMvpV2Snapshot = (serverSlug) =>
    getCachedJson(
      monthlyMvpV2Cache,
      pendingRequestCache,
      buildMonthlyMvpV2SnapshotKey(serverSlug),
      `${backendBaseUrl}/api/historical/snapshots/monthly-mvp-v2?server=${encodeURIComponent(serverSlug)}&limit=3`,
    );

  const getEloMmrLeaderboard = (serverSlug) =>
    getCachedJson(
      eloMmrCache,
      pendingRequestCache,
      buildEloMmrSnapshotKey(serverSlug),
      `${backendBaseUrl}/api/historical/elo-mmr/leaderboard?server=${encodeURIComponent(serverSlug)}&limit=5`,
    );

  const refreshServerContent = async () => {
    const requestId = activeServerRequestId + 1;
    const leaderboardRequestId = activeLeaderboardRequestId + 1;
    activeServerRequestId = requestId;
    activeLeaderboardRequestId = leaderboardRequestId;
    const activeMetricConfig = getLeaderboardMetricConfig(activeLeaderboardMetric);
    const activeTimeframeConfig = getLeaderboardTimeframeConfig(
      activeLeaderboardTimeframe,
    );
    const activeServerLabel = getHistoricalServerLabel(activeServerSlug);

    syncActiveButtons(selectorButtons, activeServerSlug);
    syncLeaderboardTimeframes(
      leaderboardTimeframeButtons,
      activeLeaderboardTimeframe,
    );
    syncLeaderboardTabs(leaderboardTabButtons, activeLeaderboardMetric);
    weeklyTitleNode.textContent = buildLeaderboardTitle(
      activeMetricConfig,
      activeServerSlug,
      activeLeaderboardTimeframe,
    );
    weeklyValueHeadingNode.textContent = activeMetricConfig.valueHeading;
    setRangeBadge(rangeNode, "Cargando rango temporal", false);
    summaryNoteNode.textContent = `La vista esta leyendo snapshots precalculados del historico local para ${activeServerLabel}.`;
    setSnapshotMeta(summarySnapshotMetaNode, "Cargando snapshot de resumen...");
    renderSummaryLoading(summaryNode);
    monthlyMvpTitleNode.textContent = `Top 3 MVP mensual V1 - ${activeServerLabel}`;
    monthlyMvpNoteNode.textContent = "Cargando periodo del MVP mensual V1...";
    setState(monthlyMvpStateNode, "Cargando Top 3 MVP mensual V1...");
    monthlyMvpListNode.innerHTML = "";
    setSnapshotMeta(
      monthlyMvpSnapshotMetaNode,
      "Cargando snapshot del MVP mensual V1...",
    );
    monthlyMvpV2TitleNode.textContent = `Top 3 MVP mensual V2 - ${activeServerLabel}`;
    monthlyMvpV2NoteNode.textContent = "Cargando lectura avanzada del MVP mensual V2...";
    setState(monthlyMvpV2StateNode, "Cargando Top 3 MVP mensual V2...");
    monthlyMvpV2ListNode.innerHTML = "";
    setSnapshotMeta(
      monthlyMvpV2SnapshotMetaNode,
      "Cargando snapshot del MVP mensual V2...",
    );
    latestMonthlyMvpResult = null;
    latestMonthlyMvpV2Result = null;
    comparisonListNode.innerHTML = "";
    comparisonNoteNode.textContent =
      "Cargando comparativa entre los rankings mensuales V1 y V2...";
    setState(comparisonStateNode, "Preparando comparativa V1 vs V2...");
    eloMmrListNode.innerHTML = "";
    eloMmrNoteNode.textContent = "Cargando lectura del rating persistente y score mensual...";
    setState(eloMmrStateNode, "Cargando leaderboard Elo/MMR...");
    setSnapshotMeta(eloMmrMetaNode, "Cargando metadata de Elo/MMR...");
    weeklyWindowNoteNode.textContent = "Cargando snapshot del ranking activo...";
    setSnapshotMeta(
      weeklySnapshotMetaNode,
      `Preparando snapshot ${activeTimeframeConfig.shortLabel}...`,
    );
    recentListNode.innerHTML = "";
    recentNoteNode.textContent = buildRecentMatchesNote(activeServerSlug);
    setState(recentStateNode, "Cargando partidas recientes...");
    setSnapshotMeta(recentSnapshotMetaNode, "Cargando snapshot de partidas...");

    const cachedSummaryPayload = readCachedPayload(
      summaryCache,
      buildSummarySnapshotKey(activeServerSlug),
    );
    if (cachedSummaryPayload) {
      hydrateSummary(
        { status: "fulfilled", value: cachedSummaryPayload },
        summaryNode,
        rangeNode,
        summaryNoteNode,
        summarySnapshotMetaNode,
      );
    }

    const cachedMonthlyMvpPayload = readCachedPayload(
      monthlyMvpCache,
      buildMonthlyMvpSnapshotKey(activeServerSlug),
    );
    if (cachedMonthlyMvpPayload) {
      latestMonthlyMvpResult = { status: "fulfilled", value: cachedMonthlyMvpPayload };
      hydrateMonthlyMvp(
        { status: "fulfilled", value: cachedMonthlyMvpPayload },
        monthlyMvpStateNode,
        monthlyMvpListNode,
        monthlyMvpTitleNode,
        monthlyMvpNoteNode,
        monthlyMvpSnapshotMetaNode,
      );
      hydrateMvpComparison(
        latestMonthlyMvpResult,
        latestMonthlyMvpV2Result,
        comparisonStateNode,
        comparisonListNode,
        comparisonNoteNode,
      );
    }

    const cachedMonthlyMvpV2Payload = readCachedPayload(
      monthlyMvpV2Cache,
      buildMonthlyMvpV2SnapshotKey(activeServerSlug),
    );
    if (cachedMonthlyMvpV2Payload) {
      latestMonthlyMvpV2Result = { status: "fulfilled", value: cachedMonthlyMvpV2Payload };
      hydrateMonthlyMvpV2(
        { status: "fulfilled", value: cachedMonthlyMvpV2Payload },
        monthlyMvpV2StateNode,
        monthlyMvpV2ListNode,
        monthlyMvpV2TitleNode,
        monthlyMvpV2NoteNode,
        monthlyMvpV2SnapshotMetaNode,
      );
      hydrateMvpComparison(
        latestMonthlyMvpResult,
        latestMonthlyMvpV2Result,
        comparisonStateNode,
        comparisonListNode,
        comparisonNoteNode,
      );
    }

    const cachedEloMmrPayload = readCachedPayload(
      eloMmrCache,
      buildEloMmrSnapshotKey(activeServerSlug),
    );
    if (cachedEloMmrPayload) {
      hydrateEloMmr(
        { status: "fulfilled", value: cachedEloMmrPayload },
        eloMmrStateNode,
        eloMmrListNode,
        eloMmrNoteNode,
        eloMmrMetaNode,
      );
    }

    const cachedLeaderboardPayload = readCachedPayload(
      leaderboardCache,
      buildLeaderboardSnapshotKey(
        activeServerSlug,
        activeLeaderboardTimeframe,
        activeLeaderboardMetric,
      ),
    );
    if (cachedLeaderboardPayload) {
      hydrateWeeklyLeaderboard(
        { status: "fulfilled", value: cachedLeaderboardPayload },
        weeklyStateNode,
        weeklyTableNode,
        weeklyBodyNode,
        weeklyTitleNode,
        weeklyValueHeadingNode,
        weeklyWindowNoteNode,
        weeklySnapshotMetaNode,
        activeMetricConfig,
        activeLeaderboardTimeframe,
      );
    } else {
      setState(
        weeklyStateNode,
        `Cargando ranking ${activeTimeframeConfig.shortLabel}...`,
      );
      weeklyTableNode.hidden = true;
    }

    const cachedRecentMatchesPayload = readCachedPayload(
      recentMatchesCache,
      buildRecentMatchesSnapshotKey(activeServerSlug),
    );
    if (cachedRecentMatchesPayload) {
      hydrateRecentMatches(
        { status: "fulfilled", value: cachedRecentMatchesPayload },
        recentStateNode,
        recentListNode,
        recentSnapshotMetaNode,
      );
    }

    const targetServerSlug = activeServerSlug;
    const targetTimeframe = activeLeaderboardTimeframe;
    const targetMetric = activeLeaderboardMetric;
    void settlePromise(getSummarySnapshot(targetServerSlug)).then((summaryResult) => {
      if (
        !isActiveServerRequest(
          requestId,
          targetServerSlug,
          targetTimeframe,
          targetMetric,
        )
      ) {
        return;
      }

      hydrateSummary(
        summaryResult,
        summaryNode,
        rangeNode,
        summaryNoteNode,
        summarySnapshotMetaNode,
      );
    });

    void settlePromise(getRecentMatchesSnapshot(targetServerSlug)).then((recentMatchesResult) => {
      if (
        !isActiveServerRequest(
          requestId,
          targetServerSlug,
          targetTimeframe,
          targetMetric,
        )
      ) {
        return;
      }

      hydrateRecentMatches(
        recentMatchesResult,
        recentStateNode,
        recentListNode,
        recentSnapshotMetaNode,
      );
    });

    void settlePromise(
      getLeaderboardSnapshot(targetServerSlug, targetTimeframe, targetMetric),
    ).then((leaderboardResult) => {
      if (
        !isActiveLeaderboardRequest(
          requestId,
          leaderboardRequestId,
          targetServerSlug,
          targetTimeframe,
          targetMetric,
        )
      ) {
        return;
      }

      hydrateWeeklyLeaderboard(
        leaderboardResult,
        weeklyStateNode,
        weeklyTableNode,
        weeklyBodyNode,
        weeklyTitleNode,
        weeklyValueHeadingNode,
        weeklyWindowNoteNode,
        weeklySnapshotMetaNode,
        activeMetricConfig,
        targetTimeframe,
      );
    });

    void settlePromise(getMonthlyMvpSnapshot(targetServerSlug)).then((monthlyMvpResult) => {
      if (
        !isActiveServerRequest(
          requestId,
          targetServerSlug,
          targetTimeframe,
          targetMetric,
        )
      ) {
        return;
      }

      latestMonthlyMvpResult = monthlyMvpResult;
      hydrateMonthlyMvp(
        monthlyMvpResult,
        monthlyMvpStateNode,
        monthlyMvpListNode,
        monthlyMvpTitleNode,
        monthlyMvpNoteNode,
        monthlyMvpSnapshotMetaNode,
      );
      hydrateMvpComparison(
        latestMonthlyMvpResult,
        latestMonthlyMvpV2Result,
        comparisonStateNode,
        comparisonListNode,
        comparisonNoteNode,
      );
    });

    void settlePromise(getMonthlyMvpV2Snapshot(targetServerSlug)).then((monthlyMvpV2Result) => {
      if (
        !isActiveServerRequest(
          requestId,
          targetServerSlug,
          targetTimeframe,
          targetMetric,
        )
      ) {
        return;
      }

      latestMonthlyMvpV2Result = monthlyMvpV2Result;
      hydrateMonthlyMvpV2(
        monthlyMvpV2Result,
        monthlyMvpV2StateNode,
        monthlyMvpV2ListNode,
        monthlyMvpV2TitleNode,
        monthlyMvpV2NoteNode,
        monthlyMvpV2SnapshotMetaNode,
      );
      hydrateMvpComparison(
        latestMonthlyMvpResult,
        latestMonthlyMvpV2Result,
        comparisonStateNode,
        comparisonListNode,
        comparisonNoteNode,
      );
    });

    void settlePromise(getEloMmrLeaderboard(targetServerSlug)).then((eloMmrResult) => {
      if (
        !isActiveServerRequest(
          requestId,
          targetServerSlug,
          targetTimeframe,
          targetMetric,
        )
      ) {
        return;
      }

      hydrateEloMmr(
        eloMmrResult,
        eloMmrStateNode,
        eloMmrListNode,
        eloMmrNoteNode,
        eloMmrMetaNode,
      );
    });
  };

  const refreshLeaderboardContent = async () => {
    const requestId = activeLeaderboardRequestId + 1;
    activeLeaderboardRequestId = requestId;
    const metricConfig = getLeaderboardMetricConfig(activeLeaderboardMetric);
    const timeframeConfig = getLeaderboardTimeframeConfig(
      activeLeaderboardTimeframe,
    );
    const targetServerSlug = activeServerSlug;
    const targetTimeframe = activeLeaderboardTimeframe;
    const targetMetric = activeLeaderboardMetric;

    syncLeaderboardTimeframes(
      leaderboardTimeframeButtons,
      activeLeaderboardTimeframe,
    );
    syncLeaderboardTabs(leaderboardTabButtons, activeLeaderboardMetric);
    weeklyTitleNode.textContent = buildLeaderboardTitle(
      metricConfig,
      activeServerSlug,
      activeLeaderboardTimeframe,
    );
    weeklyValueHeadingNode.textContent = metricConfig.valueHeading;

    const cachedPayload = readCachedPayload(
      leaderboardCache,
      buildLeaderboardSnapshotKey(
        targetServerSlug,
        targetTimeframe,
        targetMetric,
      ),
    );
    if (cachedPayload) {
      hydrateWeeklyLeaderboard(
        { status: "fulfilled", value: cachedPayload },
        weeklyStateNode,
        weeklyTableNode,
        weeklyBodyNode,
        weeklyTitleNode,
        weeklyValueHeadingNode,
        weeklyWindowNoteNode,
        weeklySnapshotMetaNode,
        metricConfig,
        targetTimeframe,
      );
      return;
    }

    weeklyWindowNoteNode.textContent = "Cargando snapshot del ranking activo...";
    setSnapshotMeta(
      weeklySnapshotMetaNode,
      `Cargando snapshot ${timeframeConfig.shortLabel}...`,
    );
    setState(
      weeklyStateNode,
      `Cargando ranking ${timeframeConfig.shortLabel}...`,
    );
    weeklyTableNode.hidden = true;

    const leaderboardResult = await settlePromise(
      getLeaderboardSnapshot(targetServerSlug, targetTimeframe, targetMetric),
    );

    if (
      requestId !== activeLeaderboardRequestId ||
      targetServerSlug !== activeServerSlug ||
      targetTimeframe !== activeLeaderboardTimeframe ||
      targetMetric !== activeLeaderboardMetric
    ) {
      return;
    }

    hydrateWeeklyLeaderboard(
      leaderboardResult,
      weeklyStateNode,
      weeklyTableNode,
      weeklyBodyNode,
      weeklyTitleNode,
      weeklyValueHeadingNode,
      weeklyWindowNoteNode,
      weeklySnapshotMetaNode,
      metricConfig,
      targetTimeframe,
    );
  };

  selectorButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const nextServerSlug = normalizeServerSlug(button.dataset.serverSlug);
      if (nextServerSlug === activeServerSlug) {
        return;
      }

      activeServerSlug = nextServerSlug;
      params.set("server", activeServerSlug);
      params.set("timeframe", activeLeaderboardTimeframe);
      params.set("metric", activeLeaderboardMetric);
      window.history.replaceState({}, "", `?${params.toString()}`);
      void refreshServerContent();
    });
  });

  leaderboardTimeframeButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const nextTimeframe = normalizeLeaderboardTimeframe(
        button.dataset.leaderboardTimeframe,
      );
      if (nextTimeframe === activeLeaderboardTimeframe) {
        return;
      }

      activeLeaderboardTimeframe = nextTimeframe;
      params.set("server", activeServerSlug);
      params.set("timeframe", activeLeaderboardTimeframe);
      params.set("metric", activeLeaderboardMetric);
      window.history.replaceState({}, "", `?${params.toString()}`);
      void refreshLeaderboardContent();
    });
  });

  leaderboardTabButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const nextMetric = normalizeLeaderboardMetric(button.dataset.leaderboardMetric);
      if (nextMetric === activeLeaderboardMetric) {
        return;
      }

      activeLeaderboardMetric = nextMetric;
      params.set("server", activeServerSlug);
      params.set("timeframe", activeLeaderboardTimeframe);
      params.set("metric", activeLeaderboardMetric);
      window.history.replaceState({}, "", `?${params.toString()}`);
      void refreshLeaderboardContent();
    });
  });

  void refreshServerContent();
});

function isActiveServerRequest(requestId, serverSlug, timeframeKey, metricKey) {
  return (
    requestId === activeServerRequestId &&
    serverSlug === activeServerSlug &&
    timeframeKey === activeLeaderboardTimeframe &&
    metricKey === activeLeaderboardMetric
  );
}

function isActiveLeaderboardRequest(
  serverRequestId,
  leaderboardRequestId,
  serverSlug,
  timeframeKey,
  metricKey,
) {
  return (
    isActiveServerRequest(serverRequestId, serverSlug, timeframeKey, metricKey) &&
    leaderboardRequestId === activeLeaderboardRequestId
  );
}

function hydrateSummary(result, summaryNode, rangeNode, noteNode, snapshotMetaNode) {
  const emptyState = getHistoricalEmptyState(activeServerSlug);
  if (result.status !== "fulfilled") {
    renderSummaryError(summaryNode);
    setRangeBadge(rangeNode, "Snapshot de resumen no disponible", false);
    noteNode.textContent =
      "No se pudo leer el resumen precalculado para el alcance seleccionado.";
    setSnapshotMeta(snapshotMetaNode, "Error al leer el snapshot de resumen.");
    return;
  }

  const payload = result.value?.data;
  const summary = payload?.item;
  const hasHistoricalData =
    Number(summary?.imported_matches_count ?? summary?.matches_count ?? 0) > 0;
  if (!payload?.found || !summary || !hasHistoricalData) {
    renderSummaryEmpty(summaryNode, emptyState.summaryMessage);
    setRangeBadge(rangeNode, emptyState.rangeLabel, false);
    noteNode.textContent = emptyState.summaryNote;
    setSnapshotMeta(
      snapshotMetaNode,
      payload?.generated_at
        ? buildSnapshotMetaText(payload, "Snapshot de resumen pendiente de generacion.")
        : "Snapshot de resumen pendiente de generacion.",
    );
    return;
  }

  const coverage = summary.coverage || {};
  const timeRange = summary.time_range || {};
  const rangeLabel = buildCoverageBadgeLabel(coverage, {
    start: payload?.source_range_start || timeRange.start,
    end: payload?.source_range_end || timeRange.end,
  }, summary.server?.slug);
  setRangeBadge(
    rangeNode,
    rangeLabel || "Cobertura historica disponible",
    coverage.status === "week-plus" && !payload?.is_stale,
  );
  noteNode.textContent = buildSummaryNote(
    "snapshot-precomputed",
    7,
    coverage,
    summary.server?.slug,
  );
  setSnapshotMeta(
    snapshotMetaNode,
    buildSnapshotMetaText(payload, "Snapshot de resumen sin timestamp."),
  );
  summaryNode.innerHTML = [
    renderSummaryCard("Servidor", summary.server?.name || "Servidor no disponible"),
    renderSummaryCard(
      "Partidas registradas",
      formatNumber(summary.imported_matches_count ?? summary.matches_count),
    ),
    renderSummaryCard("Jugadores unicos", formatNumber(summary.unique_players)),
    renderSummaryCard(
      "Cobertura historica",
      buildCoveragePeriodLabel(coverage, timeRange, summary.server?.slug),
    ),
    renderSummaryCard("Inicio de registro", formatTimestamp(coverage.first_match_at)),
    renderSummaryCard("Ultimo cierre", formatTimestamp(coverage.last_match_at)),
    renderSummaryCard(
      "Mapas frecuentes",
      formatTopMaps(summary.top_maps),
    ),
  ].join("");
}

function hydrateWeeklyLeaderboard(
  result,
  stateNode,
  tableNode,
  bodyNode,
  titleNode,
  valueHeadingNode,
  noteNode,
  snapshotMetaNode,
  metricConfig,
  timeframeKey,
) {
  const targetServerSlug = result.value?.data?.server_slug || activeServerSlug;
  const resolvedTimeframeKey = result.value?.data?.timeframe || timeframeKey;
  valueHeadingNode.textContent = metricConfig.valueHeading;
  if (result.status !== "fulfilled") {
    titleNode.textContent = buildLeaderboardTitle(
      metricConfig,
      targetServerSlug,
      resolvedTimeframeKey,
    );
    noteNode.textContent =
      "No se pudo leer los datos precalculados para esta metrica.";
    setSnapshotMeta(snapshotMetaNode, "Error al leer el snapshot del ranking.");
    setState(
      stateNode,
      `No se pudo cargar el ranking ${getLeaderboardTimeframeConfig(resolvedTimeframeKey).shortLabel}.`,
      true,
    );
    tableNode.hidden = true;
    return;
  }

  const payload = result.value?.data;
  titleNode.textContent = buildLeaderboardTitle(
    metricConfig,
    payload?.server_slug,
    payload?.timeframe || resolvedTimeframeKey,
  );
  noteNode.textContent = buildWeeklyWindowNote(payload);
  setSnapshotMeta(
    snapshotMetaNode,
    buildSnapshotMetaText(payload, "Snapshot del ranking pendiente de generacion."),
  );
  if (!payload?.found) {
    setState(
      stateNode,
      buildLeaderboardEmptyMessage(
        metricConfig,
        targetServerSlug,
        payload?.timeframe || resolvedTimeframeKey,
      ),
    );
    tableNode.hidden = true;
    return;
  }

  const items = payload?.items;
  if (!Array.isArray(items) || items.length === 0) {
    setState(
      stateNode,
      buildLeaderboardEmptyMessage(
        metricConfig,
        targetServerSlug,
        payload?.timeframe || resolvedTimeframeKey,
      ),
    );
    tableNode.hidden = true;
    return;
  }

  bodyNode.innerHTML = items
    .map(
      (item) => `
        <tr>
          <td class="historical-table__position">#${escapeHtml(item.ranking_position)}</td>
          <td>${escapeHtml(item.player?.name || "Jugador no identificado")}</td>
          <td>${escapeHtml(formatNumber(item.metric_value))}</td>
          <td>${escapeHtml(formatNumber(item.matches_considered))}</td>
          <td>${escapeHtml(formatPlaytimeHours(item.total_time_seconds))}</td>
        </tr>
      `,
    )
    .join("");
  stateNode.hidden = true;
  tableNode.hidden = false;
}

function hydrateRecentMatches(result, stateNode, listNode, snapshotMetaNode) {
  const emptyState = getHistoricalEmptyState(activeServerSlug);
  if (result.status !== "fulfilled") {
    setState(stateNode, "No se pudieron cargar las partidas recientes.", true);
    setSnapshotMeta(snapshotMetaNode, "Error al leer el snapshot de partidas.");
    return;
  }

  const payload = result.value?.data;
  setSnapshotMeta(
    snapshotMetaNode,
    buildSnapshotMetaText(payload, "Snapshot de partidas pendiente de generacion."),
  );
  if (!payload?.found) {
    setState(stateNode, emptyState.recentMessage);
    return;
  }

  const items = payload?.items;
  if (!Array.isArray(items) || items.length === 0) {
    setState(stateNode, emptyState.recentMessage);
    return;
  }

  listNode.innerHTML = items.map((item) => renderRecentMatchCard(item)).join("");
  stateNode.hidden = true;
}

function hydrateMonthlyMvp(
  result,
  stateNode,
  listNode,
  titleNode,
  noteNode,
  snapshotMetaNode,
) {
  if (result.status !== "fulfilled") {
    titleNode.textContent = `Top 3 MVP mensual V1 - ${getHistoricalServerLabel(activeServerSlug)}`;
    noteNode.textContent = "No se pudo leer el snapshot mensual del MVP V1.";
    setSnapshotMeta(snapshotMetaNode, "Error al leer el snapshot del MVP mensual V1.");
    setState(stateNode, "No se pudo cargar el Top 3 MVP mensual V1.", true);
    listNode.innerHTML = "";
    return;
  }

  const payload = result.value?.data;
  titleNode.textContent = `Top 3 MVP mensual V1 - ${getHistoricalServerLabel(
    payload?.server_slug || activeServerSlug,
  )}`;
  noteNode.textContent = buildMonthlyMvpNote(payload);
  setSnapshotMeta(
    snapshotMetaNode,
    buildSnapshotMetaText(payload, "Snapshot del MVP mensual V1 pendiente de generacion."),
  );

  if (!payload?.found) {
    setState(
      stateNode,
      "Todavia no hay un Top 3 MVP mensual V1 listo para el alcance activo.",
    );
    listNode.innerHTML = "";
    return;
  }

  const items = payload?.items;
  if (!Array.isArray(items) || items.length === 0) {
    setState(
      stateNode,
      "No hay jugadores elegibles para el MVP mensual en el periodo activo.",
    );
    listNode.innerHTML = "";
    return;
  }

  listNode.innerHTML = items.map((item) => renderMonthlyMvpCard(item, payload)).join("");
  stateNode.hidden = true;
}

function hydrateMonthlyMvpV2(
  result,
  stateNode,
  listNode,
  titleNode,
  noteNode,
  snapshotMetaNode,
) {
  if (result.status !== "fulfilled") {
    titleNode.textContent = `Top 3 MVP mensual V2 - ${getHistoricalServerLabel(activeServerSlug)}`;
    noteNode.textContent = "No se pudo leer el snapshot mensual del MVP V2.";
    setSnapshotMeta(snapshotMetaNode, "Error al leer el snapshot del MVP mensual V2.");
    setState(stateNode, "No se pudo cargar el Top 3 MVP mensual V2.", true);
    listNode.innerHTML = "";
    return;
  }

  const payload = result.value?.data;
  titleNode.textContent = `Top 3 MVP mensual V2 - ${getHistoricalServerLabel(
    payload?.server_slug || activeServerSlug,
  )}`;
  noteNode.textContent = buildMonthlyMvpV2Note(payload);
  setSnapshotMeta(
    snapshotMetaNode,
    buildSnapshotMetaText(payload, "Snapshot del MVP mensual V2 pendiente de generacion."),
  );

  if (!payload?.found) {
    setState(
      stateNode,
      "Todavia no hay un Top 3 MVP mensual V2 listo para el alcance activo.",
    );
    listNode.innerHTML = "";
    return;
  }

  const items = payload?.items;
  if (!Array.isArray(items) || items.length === 0) {
    setState(
      stateNode,
      "No hay jugadores elegibles para el MVP mensual V2 en el periodo activo.",
    );
    listNode.innerHTML = "";
    return;
  }

  listNode.innerHTML = items.map((item) => renderMonthlyMvpV2Card(item, payload)).join("");
  stateNode.hidden = true;
}

function hydrateMvpComparison(
  monthlyMvpResult,
  monthlyMvpV2Result,
  stateNode,
  listNode,
  noteNode,
) {
  if (!monthlyMvpResult || !monthlyMvpV2Result) {
    setState(stateNode, "Preparando comparativa V1 vs V2...");
    return;
  }

  if (
    monthlyMvpResult.status !== "fulfilled" ||
    monthlyMvpV2Result.status !== "fulfilled"
  ) {
    noteNode.textContent = "No se pudo completar la lectura conjunta de V1 y V2.";
    setState(stateNode, "No se pudo cargar la comparativa V1 vs V2.", true);
    listNode.innerHTML = "";
    return;
  }

  const v1Payload = monthlyMvpResult.value?.data;
  const v2Payload = monthlyMvpV2Result.value?.data;
  const v1Items = Array.isArray(v1Payload?.items) ? v1Payload.items : [];
  const v2Items = Array.isArray(v2Payload?.items) ? v2Payload.items : [];

  if (!v1Payload?.found || !v2Payload?.found || !v1Items.length || !v2Items.length) {
    noteNode.textContent =
      "La comparativa se activara cuando existan rankings V1 y V2 listos para el mismo alcance.";
    setState(stateNode, "Todavia no hay una comparativa V1 vs V2 lista para este alcance.");
    listNode.innerHTML = "";
    return;
  }

  const comparisonItems = buildMvpComparisonItems(v1Items, v2Items);
  if (!comparisonItems.length) {
    noteNode.textContent =
      "No se encontraron jugadores coincidentes o relevantes para comparar entre V1 y V2.";
    setState(stateNode, "Sin diferencias comparables entre V1 y V2 para el alcance activo.");
    listNode.innerHTML = "";
    return;
  }

  noteNode.textContent = buildMvpComparisonNote(v1Payload, v2Payload, comparisonItems.length);
  listNode.innerHTML = comparisonItems
    .map((item) => renderMvpComparisonCard(item))
    .join("");
  stateNode.hidden = true;
}

function renderRecentMatchCard(item) {
  const mapName = item.map?.pretty_name || item.map?.name || "Mapa no disponible";
  return `
    <article class="historical-match-card">
      <div class="historical-match-card__top">
        <div>
          <p class="historical-match-meta__label">Partida ${escapeHtml(item.match_id || "sin id")}</p>
          <h3 class="historical-match-card__title">${escapeHtml(mapName)}</h3>
        </div>
        <span class="historical-match-card__result">${escapeHtml(formatMatchResult(item.result))}</span>
      </div>
      <div class="historical-match-meta">
        <article>
          <p class="historical-match-meta__label">Servidor</p>
          <strong>${escapeHtml(item.server?.name || "Servidor no disponible")}</strong>
        </article>
        <article>
          <p class="historical-match-meta__label">Cierre</p>
          <strong>${escapeHtml(formatTimestamp(item.closed_at))}</strong>
        </article>
        <article>
          <p class="historical-match-meta__label">Jugadores</p>
          <strong>${escapeHtml(formatNumber(item.player_count))}</strong>
        </article>
        <article>
          <p class="historical-match-meta__label">Marcador</p>
          <strong>${escapeHtml(formatScore(item.result))}</strong>
        </article>
      </div>
    </article>
  `;
}

function renderSummaryLoading(summaryNode) {
  summaryNode.innerHTML = renderSummaryCard("Estado", "Cargando datos historicos");
}

function renderSummaryError(summaryNode) {
  summaryNode.innerHTML = renderSummaryCard("Estado", "Error al cargar el resumen");
}

function renderSummaryEmpty(summaryNode, message = "Sin datos historicos suficientes") {
  summaryNode.innerHTML = renderSummaryCard("Estado", message);
}

function renderSummaryCard(label, value) {
  return `
    <article class="historical-stat-card">
      <p>${escapeHtml(label)}</p>
      <strong>${escapeHtml(value)}</strong>
    </article>
  `;
}

function renderMonthlyMvpCard(item, payload) {
  const scoreValue = Number(item?.mvp_score);
  return `
    <article class="historical-mvp-card historical-mvp-card--rank-${escapeHtml(item?.ranking_position || "x")}">
      <div class="historical-mvp-card__top">
        <div>
          <span class="historical-mvp-card__rank">#${escapeHtml(item?.ranking_position || "-")}</span>
        </div>
        <div>
          <p class="historical-mvp-card__score-label">Puntuacion MVP</p>
          <strong class="historical-mvp-card__score-value">${escapeHtml(
            Number.isFinite(scoreValue) ? scoreValue.toFixed(1) : "0.0",
          )}</strong>
        </div>
      </div>
      <div>
        <strong class="historical-mvp-card__player">${escapeHtml(
          item?.player?.name || "Jugador no identificado",
        )}</strong>
      </div>
      <div class="historical-mvp-card__meta">
        <article>
          <span>Kills</span>
          <strong>${escapeHtml(formatNumber(item?.totals?.kills))}</strong>
        </article>
        <article>
          <span>Soporte</span>
          <strong>${escapeHtml(formatNumber(item?.totals?.support))}</strong>
        </article>
        <article>
          <span>KPM</span>
          <strong>${escapeHtml(formatDecimal(item?.derived?.kpm, 2))}</strong>
        </article>
        <article>
          <span>KDA</span>
          <strong>${escapeHtml(formatDecimal(item?.derived?.kda, 2))}</strong>
        </article>
      </div>
      <p class="historical-mvp-card__footer">
        ${escapeHtml(buildMonthlyMvpFooter(item, payload))}
      </p>
    </article>
  `;
}

function renderMonthlyMvpV2Card(item, payload) {
  const scoreValue = Number(item?.mvp_v2_score);
  return `
    <article class="historical-mvp-card historical-mvp-card--v2 historical-mvp-card--rank-${escapeHtml(item?.ranking_position || "x")}">
      <div class="historical-mvp-card__top">
        <div>
          <span class="historical-mvp-card__rank">#${escapeHtml(item?.ranking_position || "-")}</span>
        </div>
        <div>
          <p class="historical-mvp-card__score-label">Puntuacion MVP V2</p>
          <strong class="historical-mvp-card__score-value">${escapeHtml(
            Number.isFinite(scoreValue) ? scoreValue.toFixed(1) : "0.0",
          )}</strong>
        </div>
      </div>
      <div>
        <span class="historical-mvp-card__version">V2 avanzado</span>
      </div>
      <div>
        <strong class="historical-mvp-card__player">${escapeHtml(
          item?.player?.name || "Jugador no identificado",
        )}</strong>
      </div>
      <div class="historical-mvp-card__signals">
        <p class="historical-mvp-card__signal-summary">${escapeHtml(
          buildMonthlyMvpV2SignalSummary(item),
        )}</p>
        <div class="historical-mvp-card__signal-grid">
          <article>
            <span>Penalty TK</span>
            <strong>${escapeHtml(formatDecimal(item?.teamkill_penalty_v2, 2))}</strong>
          </article>
          <article>
            <span>Confidence</span>
            <strong>${escapeHtml(formatPercent(item?.advanced_confidence))}</strong>
          </article>
          <article>
            <span>Most killed</span>
            <strong>${escapeHtml(formatNumber(item?.advanced?.most_killed_count))}</strong>
          </article>
          <article>
            <span>Duel control</span>
            <strong>${escapeHtml(formatNumber(item?.advanced?.duel_control_raw))}</strong>
          </article>
        </div>
      </div>
      <p class="historical-mvp-card__footer">
        ${escapeHtml(buildMonthlyMvpV2Footer(item, payload))}
      </p>
    </article>
  `;
}

function renderMvpComparisonCard(item) {
  return `
    <article class="historical-comparison-card">
      <div class="historical-comparison-card__top">
        <div>
          <p class="historical-comparison-card__eyebrow">Jugador comparado</p>
          <h3 class="historical-comparison-card__title">${escapeHtml(item.playerName)}</h3>
        </div>
        <div>
          <p class="historical-comparison-card__delta-label">Delta puesto</p>
          <strong class="historical-comparison-card__delta-value">${escapeHtml(item.positionDeltaLabel)}</strong>
        </div>
      </div>
      <div class="historical-comparison-card__scores">
        <div class="historical-comparison-card__score-block">
          <p class="historical-comparison-card__delta-label">Score V1</p>
          <strong>${escapeHtml(item.v1ScoreLabel)}</strong>
        </div>
        <div class="historical-comparison-card__score-block">
          <p class="historical-comparison-card__delta-label">Score V2</p>
          <strong>${escapeHtml(item.v2ScoreLabel)}</strong>
        </div>
      </div>
      <div class="historical-comparison-card__meta">
        <article>
          <span>Posicion V1</span>
          <strong>${escapeHtml(item.v1PositionLabel)}</strong>
        </article>
        <article>
          <span>Posicion V2</span>
          <strong>${escapeHtml(item.v2PositionLabel)}</strong>
        </article>
        <article>
          <span>Delta score</span>
          <strong>${escapeHtml(item.scoreDeltaLabel)}</strong>
        </article>
        <article>
          <span>Penalty TK</span>
          <strong>${escapeHtml(item.teamkillPenaltyLabel)}</strong>
        </article>
      </div>
      <p class="historical-comparison-card__summary">${escapeHtml(item.summary)}</p>
    </article>
  `;
}

function hydrateEloMmr(result, stateNode, listNode, noteNode, metaNode) {
  if (result?.status !== "fulfilled") {
    setState(stateNode, "No se pudo cargar el leaderboard Elo/MMR.", true);
    listNode.innerHTML = "";
    noteNode.textContent =
      "El sistema Elo/MMR sigue disponible solo cuando existe rebuild persistido.";
    setSnapshotMeta(metaNode, "Error al cargar metadata de Elo/MMR.");
    return;
  }

  const payload = result.value?.data;
  const items = Array.isArray(payload?.items) ? payload.items : [];
  if (!payload?.found || !items.length) {
    setState(
      stateNode,
      "Todavia no hay leaderboard Elo/MMR mensual listo para este alcance.",
    );
    listNode.innerHTML = "";
    noteNode.textContent =
      "El bloque aparece cuando existe un rebuild persistido con jugadores elegibles.";
    setSnapshotMeta(
      metaNode,
      buildEloMmrMeta(payload),
    );
    return;
  }

  stateNode.hidden = true;
  noteNode.textContent = buildEloMmrNote(payload);
  setSnapshotMeta(metaNode, buildEloMmrMeta(payload));
  listNode.innerHTML = items.map((item) => renderEloMmrCard(item, payload)).join("");
}

function renderEloMmrCard(item, payload) {
  return `
    <article class="historical-elo-card">
      <div class="historical-elo-card__top">
        <div>
          <span class="historical-elo-card__rank">#${escapeHtml(item?.ranking_position || "-")}</span>
        </div>
        <div>
          <span class="historical-elo-card__accuracy">${escapeHtml(formatAccuracyMode(item?.accuracy_mode))}</span>
        </div>
      </div>
      <div>
        <strong class="historical-mvp-card__player">${escapeHtml(
          item?.player?.name || "Jugador no identificado",
        )}</strong>
      </div>
      <div class="historical-elo-card__scores">
        <article>
          <span>Score mensual</span>
          <strong>${escapeHtml(formatDecimal(item?.monthly_rank_score, 2))}</strong>
        </article>
        <article>
          <span>MMR persistente</span>
          <strong>${escapeHtml(formatDecimal(item?.persistent_rating?.mmr, 1))}</strong>
        </article>
      </div>
      <div class="historical-elo-card__meta">
        <article>
          <span>MMR gain</span>
          <strong>${escapeHtml(formatSignedDecimal(item?.persistent_rating?.mmr_gain, 1))}</strong>
        </article>
        <article>
          <span>Elegibilidad</span>
          <strong>${escapeHtml(item?.eligible ? "Elegible" : "Parcial")}</strong>
        </article>
        <article>
          <span>Partidas validas</span>
          <strong>${escapeHtml(formatNumber(item?.valid_matches))}</strong>
        </article>
        <article>
          <span>Confidence</span>
          <strong>${escapeHtml(formatDecimal(item?.components?.confidence, 1))}</strong>
        </article>
      </div>
      <p class="historical-elo-card__summary">${escapeHtml(buildEloMmrSummary(item))}</p>
      <p class="historical-elo-card__footer">${escapeHtml(buildEloMmrFooter(item, payload))}</p>
    </article>
  `;
}

function setState(node, message, isError = false) {
  node.textContent = message;
  node.hidden = false;
  node.classList.toggle("is-error", isError);
}

function setRangeBadge(node, label, isFresh) {
  node.textContent = label;
  node.classList.toggle("status-chip--ok", isFresh);
  node.classList.toggle("status-chip--fallback", !isFresh);
}

function setSnapshotMeta(node, message) {
  node.textContent = message;
}

function syncActiveButtons(buttons, activeServerSlug) {
  buttons.forEach((button) => {
    button.classList.toggle(
      "is-active",
      button.dataset.serverSlug === activeServerSlug,
    );
  });
}

function syncLeaderboardTabs(buttons, activeMetric) {
  buttons.forEach((button) => {
    const isActive = button.dataset.leaderboardMetric === activeMetric;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-selected", String(isActive));
  });
}

function syncLeaderboardTimeframes(buttons, activeTimeframe) {
  buttons.forEach((button) => {
    const isActive = button.dataset.leaderboardTimeframe === activeTimeframe;
    button.classList.toggle("is-active", isActive);
    button.setAttribute("aria-selected", String(isActive));
  });
}

function normalizeServerSlug(rawValue) {
  const normalized = typeof rawValue === "string" ? rawValue.trim() : "";
  if (HISTORICAL_SERVER_SLUGS.includes(normalized)) {
    return normalized;
  }

  return DEFAULT_HISTORICAL_SERVER;
}

function getHistoricalServerLabel(serverSlug) {
  return (
    HISTORICAL_SERVERS.find((server) => server.slug === serverSlug)?.label ||
    HISTORICAL_SERVERS[0].label
  );
}

function normalizeLeaderboardMetric(rawValue) {
  const normalized = typeof rawValue === "string" ? rawValue.trim() : "";
  if (LEADERBOARD_METRICS.some((metric) => metric.key === normalized)) {
    return normalized;
  }

  return DEFAULT_LEADERBOARD_METRIC;
}

function normalizeLeaderboardTimeframe(rawValue) {
  const normalized = typeof rawValue === "string" ? rawValue.trim() : "";
  if (LEADERBOARD_TIMEFRAMES.some((timeframe) => timeframe.key === normalized)) {
    return normalized;
  }

  return DEFAULT_LEADERBOARD_TIMEFRAME;
}

function getLeaderboardMetricConfig(metricKey) {
  return (
    LEADERBOARD_METRICS.find((metric) => metric.key === metricKey) ||
    LEADERBOARD_METRICS[0]
  );
}

function getLeaderboardTimeframeConfig(timeframeKey) {
  return (
    LEADERBOARD_TIMEFRAMES.find((timeframe) => timeframe.key === timeframeKey) ||
    LEADERBOARD_TIMEFRAMES[0]
  );
}

function buildSummarySnapshotKey(serverSlug) {
  return `summary:${serverSlug}`;
}

function buildRecentMatchesSnapshotKey(serverSlug) {
  return `recent:${serverSlug}`;
}

function buildLeaderboardSnapshotKey(serverSlug, timeframeKey, metricKey) {
  return `leaderboard:${serverSlug}:${timeframeKey}:${metricKey}`;
}

function buildMonthlyMvpSnapshotKey(serverSlug) {
  return `monthly-mvp:${serverSlug}`;
}

function buildMonthlyMvpV2SnapshotKey(serverSlug) {
  return `monthly-mvp-v2:${serverSlug}`;
}

function buildEloMmrSnapshotKey(serverSlug) {
  return `elo-mmr:${serverSlug}`;
}

function buildRangeLabel(start, end) {
  if (!start && !end) {
    return "";
  }

  return `${formatTimestamp(start)} a ${formatTimestamp(end)}`;
}

function buildCoverageBadgeLabel(coverage, timeRange, serverSlug) {
  const rangeStart = coverage?.first_match_at || timeRange?.start;
  const rangeEnd = coverage?.last_match_at || timeRange?.end;
  if (!rangeStart && !rangeEnd) {
    return "Sin cobertura registrada";
  }
  if (coverage?.status === "under-week") {
    return "Cobertura inicial";
  }
  if (coverage?.status === "week-plus") {
    return "Cobertura historica";
  }
  return "Periodo registrado";
}

function buildCoveragePeriodLabel(coverage, timeRange, serverSlug) {
  const start = coverage?.first_match_at || timeRange?.start;
  const end = coverage?.last_match_at || timeRange?.end;
  if (start && end) {
    return `Desde ${formatDateOnly(start)} hasta ${formatDateOnly(end)}`;
  }
  if (start) {
    return `Desde ${formatDateOnly(start)}`;
  }
  if (end) {
    return `Hasta ${formatDateOnly(end)}`;
  }
  return "Sin cobertura registrada";
}

function buildSummaryNote(summaryBasis, weeklyWindowDays, coverage, serverSlug) {
  const basisLabel =
    summaryBasis === "snapshot-precomputed"
      ? "el historico local"
      : "el historico persistido disponible";
  const status = coverage?.status;
  void weeklyWindowDays;
  void serverSlug;
  if (status === "under-week") {
    return `Este bloque resume ${basisLabel}. La cobertura registrada todavia es inicial y puede crecer en los proximos dias.`;
  }
  if (serverSlug === "all-servers") {
    return `Resumen de los servidore desde ${basisLabel} y combinado solo los servidores actuales de la comunidad.`;
  }
  return `Resumen servido desde ${basisLabel}.`;
}

function buildWeeklyWindowNote(payload) {
  if (!payload?.found) {
    const timeframeLabel = getLeaderboardTimeframeConfig(
      payload?.timeframe || activeLeaderboardTimeframe,
    ).shortLabel;
    return `No existen datos en ${timeframeLabel} suficientes para esta metrica en el rango activo.`;
  }

  const start = formatTimestamp(payload?.window_start);
  const end = formatTimestamp(payload?.window_end);
  const windowLabel =
    payload?.window_label ||
    (payload?.timeframe === "monthly" ? "Mes activo" : "Semana activa");
  if (payload?.uses_fallback) {
    const currentPeriodMatches =
      payload?.current_week_closed_matches ??
      payload?.current_month_closed_matches ??
      payload?.sufficient_sample?.current_week_closed_matches ??
      payload?.sufficient_sample?.current_month_closed_matches ??
      0;
    return `${windowLabel}: ${start} a ${end}. Se muestra el ultimo periodo cerrado porque el actual todavia solo suma ${formatNumber(currentPeriodMatches)} cierres.`;
  }
  return `${windowLabel}: ${start} a ${end}.`;
}

function buildLeaderboardTitle(metricConfig, serverSlug, timeframeKey) {
  const timeframeLabel = getLeaderboardTimeframeConfig(timeframeKey).label;
  return `${metricConfig.title} ${timeframeLabel} - ${getHistoricalServerLabel(serverSlug)}`;
}

function buildRecentMatchesNote(serverSlug) {
  if (serverSlug === "all-servers") {
    return "Lista de cierres ya registrados para los servidores con historico disponible.";
  }
  return `Lista de cierres ya registrados para ${getHistoricalServerLabel(serverSlug)}.`;
}

function buildMonthlyMvpNote(payload) {
  if (!payload?.found) {
    return "El Top 3 mensual V1 aparecera cuando exista un snapshot MVP listo para este alcance.";
  }
  const periodLabel =
    payload?.window_label && payload?.month_key
      ? `${payload.window_label} (${formatMonthKey(payload.month_key)})`
      : formatMonthKey(payload?.month_key);
  const eligiblePlayers = formatNumber(payload?.eligible_players_count);
  return `${periodLabel || "Periodo mensual activo"}. ${eligiblePlayers} jugadores cumplen los umbrales base de la version V1.`;
}

function buildMonthlyMvpFooter(item, payload) {
  const hoursPlayed = Number(item?.totals?.time_seconds) / 3600;
  const monthLabel = formatMonthKey(payload?.month_key);
  return `${monthLabel || "Mes activo"} · ${formatNumber(
    item?.matches_considered,
  )} partidas · ${formatDecimal(hoursPlayed, 1)} h jugadas`;
}

function buildMonthlyMvpV2Note(payload) {
  if (!payload?.found) {
    return "El Top 3 mensual V2 aparecera cuando exista un snapshot alineado con la cobertura de eventos.";
  }
  const periodLabel =
    payload?.window_label && payload?.month_key
      ? `${payload.window_label} (${formatMonthKey(payload.month_key)})`
      : formatMonthKey(payload?.month_key);
  const eligiblePlayers = formatNumber(payload?.eligible_players_count);
  const eventCount = formatNumber(payload?.event_coverage?.event_count);
  return `${periodLabel || "Periodo mensual activo"}. ${eligiblePlayers} jugadores elegibles y ${eventCount} eventos V2 cubiertos para este alcance.`;
}

function buildMonthlyMvpV2SignalSummary(item) {
  const rivalryEdge = formatNumber(item?.advanced?.rivalry_edge_raw);
  const deathBy = formatNumber(item?.advanced?.death_by_count);
  return `Ventaja de rivalidad ${rivalryEdge} y ${deathBy} muertes frente a su rival mas repetido.`;
}

function buildMonthlyMvpV2Footer(item, payload) {
  const hoursPlayed = Number(item?.totals?.time_seconds) / 3600;
  const monthLabel = formatMonthKey(payload?.month_key);
  return `${monthLabel || "Mes activo"} · ${formatNumber(
    item?.matches_considered,
  )} partidas · ${formatDecimal(hoursPlayed, 1)} h jugadas`;
}

function buildEloMmrNote(payload) {
  const monthLabel = formatMonthKey(payload?.month_key);
  const exactRatio = Number(payload?.accuracy_contract?.exact_ratio || 0);
  const approximateRatio = Number(payload?.accuracy_contract?.approximate_ratio || 0);
  const blockedComponents = Array.isArray(payload?.accuracy_contract?.blocked_components)
    ? payload.accuracy_contract.blocked_components.length
    : 0;
  return `${monthLabel || "Mes activo"}. Rating persistente competitivo + score mensual. ${formatPercent(exactRatio)} de senal exacta, ${formatPercent(approximateRatio)} aproximada y ${formatNumber(blockedComponents)} componentes bloqueados por telemetria.`;
}

function buildEloMmrMeta(payload) {
  const sourceLabel = payload?.selected_source || payload?.source || "origen no disponible";
  const fallbackLabel = payload?.fallback_used
    ? `fallback ${payload?.fallback_reason || "activo"}`
    : "sin fallback";
  return `Generado ${formatTimestamp(payload?.generated_at)} · fuente ${sourceLabel} · ${fallbackLabel}`;
}

function buildEloMmrSummary(item) {
  return `Elo core ${formatSignedDecimal(item?.rating_breakdown?.delta_sources?.elo_core_gain, 1)}, modificadores HLL ${formatSignedDecimal(item?.rating_breakdown?.delta_sources?.performance_modifier_gain, 1)} y tramo proxy ${formatSignedDecimal(item?.rating_breakdown?.delta_sources?.proxy_modifier_gain, 1)}.`;
}

function buildEloMmrFooter(item, payload) {
  const monthLabel = formatMonthKey(payload?.month_key);
  const hoursPlayed = Number(item?.total_time_seconds) / 3600;
  return `${monthLabel || "Mes activo"} · ${formatNumber(item?.valid_matches)} validas / ${formatNumber(item?.total_matches)} totales · ${formatDecimal(hoursPlayed, 1)} h`;
}

function buildMvpComparisonItems(v1Items, v2Items) {
  const v1TopItems = v1Items.slice(0, 3);
  const v2TopItems = v2Items.slice(0, 3);
  const v1Index = new Map(
    v1Items.map((item) => [item?.player?.stable_player_key, item]),
  );
  const v2Index = new Map(
    v2Items.map((item) => [item?.player?.stable_player_key, item]),
  );
  const comparisonKeys = [];

  [...v1TopItems, ...v2TopItems].forEach((item) => {
    const stableKey = item?.player?.stable_player_key;
    if (!stableKey || comparisonKeys.includes(stableKey)) {
      return;
    }
    comparisonKeys.push(stableKey);
  });

  return comparisonKeys.map((stableKey) => {
    const v1Item = v1Index.get(stableKey);
    const v2Item = v2Index.get(stableKey);
    const v1Position = Number(v1Item?.ranking_position);
    const v2Position = Number(v2Item?.ranking_position);
    const v1Score = Number(v1Item?.mvp_score);
    const v2Score = Number(v2Item?.mvp_v2_score);
    const scoreDelta = Number.isFinite(v1Score) && Number.isFinite(v2Score)
      ? v2Score - v1Score
      : null;
    return {
      playerName:
        v2Item?.player?.name ||
        v1Item?.player?.name ||
        "Jugador no identificado",
      v1PositionLabel: Number.isFinite(v1Position) ? `#${v1Position}` : "Fuera del Top V1",
      v2PositionLabel: Number.isFinite(v2Position) ? `#${v2Position}` : "Fuera del Top V2",
      positionDeltaLabel: buildPositionDeltaLabel(v1Position, v2Position),
      v1ScoreLabel: Number.isFinite(v1Score) ? formatDecimal(v1Score, 1) : "Sin entrada",
      v2ScoreLabel: Number.isFinite(v2Score) ? formatDecimal(v2Score, 1) : "Sin entrada",
      scoreDeltaLabel: buildScoreDeltaLabel(scoreDelta),
      teamkillPenaltyLabel: buildTeamkillPenaltyComparisonLabel(v1Item, v2Item),
      summary: buildMvpComparisonSummary(v1Item, v2Item, scoreDelta),
    };
  });
}

function buildMvpComparisonNote(v1Payload, v2Payload, itemCount) {
  const monthLabel = formatMonthKey(v2Payload?.month_key || v1Payload?.month_key);
  return `${monthLabel || "Periodo mensual activo"}. Comparativa ligera de ${formatNumber(itemCount)} jugadores visibles entre el Top V1 y el Top V2 para validar cambios antes de converger rankings.`;
}

function buildPositionDeltaLabel(v1Position, v2Position) {
  if (Number.isFinite(v1Position) && Number.isFinite(v2Position)) {
    const delta = v1Position - v2Position;
    if (delta > 0) {
      return `Sube ${delta}`;
    }
    if (delta < 0) {
      return `Baja ${Math.abs(delta)}`;
    }
    return "Sin cambio";
  }
  if (Number.isFinite(v2Position)) {
    return "Entra en V2";
  }
  if (Number.isFinite(v1Position)) {
    return "Sale en V2";
  }
  return "Sin cruce";
}

function buildScoreDeltaLabel(scoreDelta) {
  if (!Number.isFinite(scoreDelta)) {
    return "Sin cruce";
  }
  const prefix = scoreDelta > 0 ? "+" : "";
  return `${prefix}${formatDecimal(scoreDelta, 1)}`;
}

function buildTeamkillPenaltyComparisonLabel(v1Item, v2Item) {
  const v1Penalty = Number(v1Item?.teamkill_penalty);
  const v2Penalty = Number(v2Item?.teamkill_penalty_v2);
  if (!Number.isFinite(v1Penalty) && !Number.isFinite(v2Penalty)) {
    return "Sin dato";
  }
  return `${formatDecimal(v1Penalty, 1)} -> ${formatDecimal(v2Penalty, 1)}`;
}

function buildMvpComparisonSummary(v1Item, v2Item, scoreDelta) {
  const deltaLabel = Number.isFinite(scoreDelta)
    ? `${scoreDelta > 0 ? "mejora" : scoreDelta < 0 ? "cae" : "mantiene"} ${buildScoreDeltaLabel(scoreDelta)}`
    : "no tiene cruce completo";
  const mostKilled = formatNumber(v2Item?.advanced?.most_killed_count);
  const duelControl = formatNumber(v2Item?.advanced?.duel_control_raw);
  return `En V2 ${deltaLabel}. Senales avanzadas visibles: most killed ${mostKilled} y duel control ${duelControl}.`;
}

function buildSnapshotMetaText(payload, missingMessage) {
  if (!payload?.generated_at) {
    return missingMessage;
  }

  const parts = [
    payload.is_stale
      ? `Actualizado: ${formatTimestamp(payload.generated_at)}`
      : `Actualizado: ${formatTimestamp(payload.generated_at)}`,
  ];
  const sourceRangeLabel = buildRangeLabel(
    payload?.source_range_start,
    payload?.source_range_end,
  );
  if (sourceRangeLabel) {
    parts.push(`Cobertura: ${sourceRangeLabel}`);
  }
  return parts.join(" | ");
}

function formatTopMaps(topMaps) {
  if (!Array.isArray(topMaps) || topMaps.length === 0) {
    return "Sin mapas frecuentes";
  }

  return topMaps
    .map((item) => `${item.map_name} (${formatNumber(item.matches_count)})`)
    .join(" / ");
}

function formatDateOnly(timestamp) {
  if (!timestamp) {
    return "Fecha no disponible";
  }

  const value = new Date(timestamp);
  if (Number.isNaN(value.getTime())) {
    return "Fecha no disponible";
  }

  return new Intl.DateTimeFormat("es-ES", {
    dateStyle: "medium",
  }).format(value);
}

function formatMatchResult(result) {
  const winner = result?.winner;
  if (winner === "allies") {
    return "Victoria Aliada";
  }
  if (winner === "axis") {
    return "Victoria Axis";
  }
  if (winner === "draw") {
    return "Empate";
  }
  return "Resultado parcial";
}

function formatScore(result) {
  const alliedScore = Number.isFinite(result?.allied_score)
    ? result.allied_score
    : "-";
  const axisScore = Number.isFinite(result?.axis_score)
    ? result.axis_score
    : "-";
  return `${alliedScore} - ${axisScore}`;
}

function formatNumber(value) {
  const parsedValue = Number(value);
  if (!Number.isFinite(parsedValue)) {
    return "0";
  }

  return new Intl.NumberFormat("es-ES").format(parsedValue);
}

function formatDecimal(value, fractionDigits = 1) {
  const parsedValue = Number(value);
  if (!Number.isFinite(parsedValue)) {
    return "0";
  }

  return new Intl.NumberFormat("es-ES", {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  }).format(parsedValue);
}

function formatPercent(value) {
  const parsedValue = Number(value);
  if (!Number.isFinite(parsedValue)) {
    return "0 %";
  }

  return `${new Intl.NumberFormat("es-ES", {
    maximumFractionDigits: 0,
  }).format(parsedValue * 100)} %`;
}

function formatSignedDecimal(value, fractionDigits = 1) {
  const parsedValue = Number(value);
  if (!Number.isFinite(parsedValue)) {
    return "0";
  }
  const prefix = parsedValue > 0 ? "+" : "";
  return `${prefix}${formatDecimal(parsedValue, fractionDigits)}`;
}

function formatPlaytimeHours(value) {
  const parsedValue = Number(value);
  if (!Number.isFinite(parsedValue) || parsedValue <= 0) {
    return "0,0 h";
  }
  return `${formatDecimal(parsedValue / 3600, 1)} h`;
}

function formatAccuracyMode(mode) {
  if (mode === "exact") {
    return "Exacto";
  }
  if (mode === "approximate") {
    return "Aproximado";
  }
  if (mode === "partial") {
    return "Parcial";
  }
  return "Mixto";
}

function formatMonthKey(monthKey) {
  if (!monthKey) {
    return "";
  }

  const value = new Date(`${monthKey}-01T00:00:00Z`);
  if (Number.isNaN(value.getTime())) {
    return monthKey;
  }

  return new Intl.DateTimeFormat("es-ES", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(value);
}

function formatTimestamp(timestamp) {
  if (!timestamp) {
    return "Fecha no disponible";
  }

  const value = new Date(timestamp);
  if (Number.isNaN(value.getTime())) {
    return "Fecha no disponible";
  }

  return new Intl.DateTimeFormat("es-ES", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(value);
}

async function getCachedJson(cache, pendingCache, key, url) {
  const cachedPayload = readCachedPayload(cache, key);
  if (cachedPayload) {
    return cachedPayload;
  }
  if (pendingCache.has(key)) {
    return pendingCache.get(key);
  }

  const request = fetchJson(url)
    .then((payload) => {
      writeCachedPayload(cache, key, payload);
      pendingCache.delete(key);
      return payload;
    })
    .catch((error) => {
      pendingCache.delete(key);
      throw error;
    });
  pendingCache.set(key, request);
  return request;
}

function readCachedPayload(cache, key) {
  const entry = cache.get(key);
  if (!entry) {
    return null;
  }

  if (entry.expiresAt <= Date.now()) {
    cache.delete(key);
    return null;
  }

  return entry.payload;
}

function writeCachedPayload(cache, key, payload) {
  cache.set(key, {
    payload,
    expiresAt: Date.now() + resolveSnapshotCacheTtl(payload),
  });
}

function resolveSnapshotCacheTtl(payload) {
  const data = payload?.data;
  if (!data) {
    return NEGATIVE_SNAPSHOT_CACHE_TTL_MS;
  }

  if (data.snapshot_status === "missing" || data.found === false) {
    return NEGATIVE_SNAPSHOT_CACHE_TTL_MS;
  }

  if (data.is_stale) {
    return STALE_SNAPSHOT_CACHE_TTL_MS;
  }

  return SNAPSHOT_CACHE_TTL_MS;
}

async function settlePromise(promise) {
  try {
    const value = await promise;
    return { status: "fulfilled", value };
  } catch (reason) {
    return { status: "rejected", reason };
  }
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed with ${response.status}`);
  }

  return response.json();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function buildLeaderboardEmptyMessage(metricConfig, serverSlug, timeframeKey) {
  void serverSlug;
  const timeframeLabel = getLeaderboardTimeframeConfig(timeframeKey).shortLabel;
  return metricConfig.emptyMessage.replace("esta ventana", `esta ventana ${timeframeLabel}`);
}

function getHistoricalEmptyState(serverSlug) {
  void serverSlug;

  return {
    rangeLabel: "Sin cobertura registrada",
    summaryMessage: "Sin datos historicos suficientes",
    summaryNote:
      "Todavia no existe un snapshot de resumen listo para el alcance seleccionado.",
    recentMessage: "Todavia no hay partidas recientes disponibles.",
  };
}
