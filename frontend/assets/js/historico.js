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
    slug: "all-servers",
    label: "Todos los servidores",
  },
]);
const HISTORICAL_SERVER_SLUGS = Object.freeze(
  HISTORICAL_SERVERS.map((server) => server.slug),
);
const DEFAULT_HISTORICAL_SERVER = "all-servers";
const SNAPSHOT_CACHE_TTL_MS = 120000;
const STALE_SNAPSHOT_CACHE_TTL_MS = 30000;
const NEGATIVE_SNAPSHOT_CACHE_TTL_MS = 15000;
const RECENT_MATCHES_LIMIT = 100;
const DEFAULT_RECENT_MATCHES_PAGE_SIZE = 10;
const RECENT_MATCHES_PAGE_SIZES = Object.freeze([10, 25, 50, 100]);
let activeServerSlug = DEFAULT_HISTORICAL_SERVER;
let activeLeaderboardMetric;
let activeLeaderboardTimeframe;
let activeServerRequestId = 0;
let activeLeaderboardRequestId = 0;
let recentMatchesPagination;
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
    ratioHeading: "Kills/partida",
    ratioMode: "kills",
    emptyMessage: "Sin datos historicos suficientes para mostrar este ranking de kills.",
  },
  {
    key: "deaths",
    title: "Top muertes",
    valueHeading: "Muertes",
    ratioHeading: "Muertes/partida",
    ratioMode: "deaths",
    emptyMessage: "Sin datos historicos suficientes para mostrar este ranking de muertes.",
  },
  {
    key: "matches_over_100_kills",
    title: "Partidas 100+ kills",
    valueHeading: "Partidas 100+ kills",
    ratioHeading: null,
    ratioMode: null,
    emptyMessage: "Ningun jugador ha registrado partidas de 100+ kills en esta ventana.",
  },
  {
    key: "support",
    title: "Soporte",
    valueHeading: "Soporte",
    ratioHeading: "Soporte/partida",
    ratioMode: "support",
    emptyMessage: "El ranking de soporte estara disponible cuando tengamos datos de puntuacion de soporte por jugador.",
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
  const weeklyValueHeadingNode = document.getElementById("weekly-leaderboard-value-heading");
  const weeklyRatioHeadingNode = document.getElementById("weekly-leaderboard-ratio-heading");
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
  recentMatchesPagination = initializeRecentMatchesPagination(recentListNode);

  const params = new URLSearchParams(window.location.search);
  activeServerSlug = normalizeServerSlug(params.get("server"));
  activeLeaderboardMetric = normalizeLeaderboardMetric(params.get("metric"));
  activeLeaderboardTimeframe = normalizeLeaderboardTimeframe(
    params.get("timeframe"),
  );

  const summaryCache = new Map();
  const recentMatchesCache = new Map();
  const leaderboardCache = new Map();
  const pendingRequestCache = new Map();

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
      `${backendBaseUrl}/api/historical/snapshots/recent-matches?server=${encodeURIComponent(serverSlug)}&limit=${RECENT_MATCHES_LIMIT}`,
    );

  const getLeaderboardSnapshot = (serverSlug, timeframeKey, metricKey) =>
    getCachedJson(
      leaderboardCache,
      pendingRequestCache,
      buildLeaderboardSnapshotKey(serverSlug, timeframeKey, metricKey),
      `${backendBaseUrl}/api/historical/snapshots/leaderboard?server=${encodeURIComponent(serverSlug)}&timeframe=${encodeURIComponent(timeframeKey)}&metric=${encodeURIComponent(metricKey)}&limit=10`,
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
    summaryNoteNode.textContent = `La vista está leyendo agregados CRCON de solo lectura para ${activeServerLabel}.`;
    setSnapshotMeta(summarySnapshotMetaNode, "Cargando datos de resumen...");
    renderSummaryLoading(summaryNode);
    weeklyWindowNoteNode.textContent = "Cargando datos del ranking activo...";
    setSnapshotMeta(
      weeklySnapshotMetaNode,
      `Preparando datos ${activeTimeframeConfig.shortLabel}...`,
    );
    resetRecentMatchesPagination();
    renderRecentMatchesLoading(recentListNode);
    recentNoteNode.textContent = buildRecentMatchesNote(activeServerSlug);
    setState(recentStateNode, "Cargando partidas recientes...");
    setSnapshotMeta(recentSnapshotMetaNode, "Cargando datos de partidas...");

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
        weeklyRatioHeadingNode,
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
        weeklyRatioHeadingNode,
        weeklyWindowNoteNode,
        weeklySnapshotMetaNode,
        activeMetricConfig,
        targetTimeframe,
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
        weeklyRatioHeadingNode,
        weeklyWindowNoteNode,
        weeklySnapshotMetaNode,
        metricConfig,
        targetTimeframe,
      );
      return;
    }

    weeklyWindowNoteNode.textContent = "Cargando datos del ranking activo...";
    setSnapshotMeta(
      weeklySnapshotMetaNode,
      `Cargando datos ${timeframeConfig.shortLabel}...`,
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
      weeklyRatioHeadingNode,
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
    setRangeBadge(rangeNode, "Resumen no disponible", false);
    noteNode.textContent =
      "No se pudo completar la solicitud del resumen para el alcance seleccionado.";
    setSnapshotMeta(snapshotMetaNode, "Error al leer los datos de resumen.");
    return;
  }

  const payload = result.value?.data;
  const aggregateProblem = describeAggregateProblem(payload);
  preserveAggregateReason(summaryNode, payload);
  if (aggregateProblem) {
    renderSummaryError(summaryNode);
    setRangeBadge(rangeNode, aggregateProblem.title, false);
    noteNode.textContent = aggregateProblem.message;
    setSnapshotMeta(snapshotMetaNode, "Lectura CRCON no disponible.");
    return;
  }
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
        ? buildSnapshotMetaText(payload, "Resumen sin datos de actualización.")
        : "No hay datos en este alcance.",
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
    payload?.summary_basis || "crcon-postgres-read-only",
    7,
    coverage,
    summary.server?.slug,
  );
  setSnapshotMeta(
    snapshotMetaNode,
    buildSnapshotMetaText(payload, "Resumen sin fecha de actualizacion."),
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
  ratioHeadingNode,
  noteNode,
  snapshotMetaNode,
  metricConfig,
  timeframeKey,
) {
  const targetServerSlug = result.value?.data?.server_slug || activeServerSlug;
  const resolvedTimeframeKey = result.value?.data?.timeframe || timeframeKey;
  valueHeadingNode.textContent = metricConfig.valueHeading;
  syncLeaderboardRatioColumn(tableNode, ratioHeadingNode, bodyNode, metricConfig);
  if (result.status !== "fulfilled") {
    titleNode.textContent = buildLeaderboardTitle(
      metricConfig,
      targetServerSlug,
      resolvedTimeframeKey,
    );
    noteNode.textContent =
      "No se pudo completar la solicitud del agregado para esta métrica.";
    setSnapshotMeta(snapshotMetaNode, "Error al leer los datos del ranking.");
    setState(
      stateNode,
      `No se pudo cargar el ranking ${getLeaderboardTimeframeConfig(resolvedTimeframeKey).shortLabel}.`,
      true,
    );
    tableNode.hidden = true;
    return;
  }

  const payload = result.value?.data;
  const aggregateProblem = describeAggregateProblem(payload);
  preserveAggregateReason(stateNode, payload);
  titleNode.textContent = buildLeaderboardTitle(
    metricConfig,
    payload?.server_slug,
    payload?.timeframe || resolvedTimeframeKey,
  );
  noteNode.textContent = buildWeeklyWindowNote(payload);
  setSnapshotMeta(
    snapshotMetaNode,
    buildSnapshotMetaText(payload, "Ranking sin datos de actualización."),
  );
  if (aggregateProblem) {
    setState(stateNode, aggregateProblem.message, true);
    tableNode.hidden = true;
    return;
  }
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
      (item) => {
        const matches = Number(item.matches_considered);
        const ratioValue = formatHistoricalRatio(item, metricConfig, matches);
        const ratioCell = metricConfig.ratioMode
          ? `<td>${escapeHtml(ratioValue)}</td>`
          : "";

        return `
        <tr>
          <td class="historical-table__position">#${escapeHtml(item.ranking_position)}</td>
          <td>${escapeHtml(item.player_name || "Jugador no identificado")}</td>
          <td>${escapeHtml(formatNumber(item.metric_value))}</td>
          <td>${escapeHtml(formatNumber(item.matches_considered))}</td>
          ${ratioCell}
        </tr>
      `;
      },
    )
    .join("");
  stateNode.hidden = true;
  syncLeaderboardRatioColumn(tableNode, ratioHeadingNode, bodyNode, metricConfig);
  tableNode.hidden = false;
}

function hydrateRecentMatches(result, stateNode, listNode, snapshotMetaNode) {
  const emptyState = getHistoricalEmptyState(activeServerSlug);
  if (result.status !== "fulfilled") {
    resetRecentMatchesPagination();
    listNode.innerHTML = "";
    setState(stateNode, "No se pudieron cargar las partidas recientes.", true);
    setSnapshotMeta(snapshotMetaNode, "Error al leer los datos de partidas.");
    return;
  }

  const payload = result.value?.data;
  setSnapshotMeta(
    snapshotMetaNode,
    buildSnapshotMetaText(payload, "Partidas pendientes de generacion."),
  );
  if (!payload?.found) {
    resetRecentMatchesPagination();
    listNode.innerHTML = "";
    setState(stateNode, emptyState.recentMessage);
    return;
  }

  const items = payload?.items;
  if (!Array.isArray(items) || items.length === 0) {
    resetRecentMatchesPagination();
    listNode.innerHTML = "";
    setState(stateNode, emptyState.recentMessage);
    return;
  }

  setRecentMatchesPaginationItems(items.slice(0, RECENT_MATCHES_LIMIT), listNode);
  stateNode.hidden = true;
}

function renderRecentMatchesLoading(listNode) {
  if (!listNode) {
    return;
  }

  listNode.innerHTML = Array.from({ length: 3 }, (_, index) => `
    <article class="historical-match-card historical-match-card--clean" aria-hidden="true">
      <div class="historical-match-card__top historical-match-card__top--clean">
        <h3 class="historical-match-card__title">Cargando partida ${index + 1}</h3>
      </div>
      <div class="historical-match-meta historical-match-meta--clean">
        <article>
          <p class="historical-match-meta__label">Mapa</p>
          <strong>Preparando registro</strong>
        </article>
        <article>
          <p class="historical-match-meta__label">Cierre</p>
          <strong>...</strong>
        </article>
        <article>
          <p class="historical-match-meta__label">Resultado</p>
          <strong>...</strong>
        </article>
      </div>
    </article>
  `).join("");
}

function initializeRecentMatchesPagination(listNode) {
  if (!listNode) {
    return null;
  }

  listNode.insertAdjacentHTML(
    "afterend",
    `
      <div class="historical-pagination" id="recent-matches-pagination" hidden>
        <label class="historical-pagination__size">
          <span>Partidas por pagina</span>
          <select id="recent-matches-page-size" aria-label="Partidas por pagina">
            ${RECENT_MATCHES_PAGE_SIZES.map(
              (pageSize) => `
                <option value="${pageSize}"${pageSize === DEFAULT_RECENT_MATCHES_PAGE_SIZE ? " selected" : ""}>
                  ${pageSize}
                </option>
              `,
            ).join("")}
          </select>
        </label>
        <div class="historical-pagination__nav">
          <button class="historical-tab" id="recent-matches-page-prev" type="button">
            Anterior
          </button>
          <p id="recent-matches-page-status">Pagina 1 de 1</p>
          <button class="historical-tab" id="recent-matches-page-next" type="button">
            Siguiente
          </button>
        </div>
      </div>
    `,
  );
  const pagination = {
    items: [],
    page: 1,
    pageSize: DEFAULT_RECENT_MATCHES_PAGE_SIZE,
    root: document.getElementById("recent-matches-pagination"),
    pageSizeSelect: document.getElementById("recent-matches-page-size"),
    previousButton: document.getElementById("recent-matches-page-prev"),
    nextButton: document.getElementById("recent-matches-page-next"),
    status: document.getElementById("recent-matches-page-status"),
  };
  pagination.previousButton?.addEventListener("click", () => {
    if (pagination.page <= 1) {
      return;
    }
    pagination.page -= 1;
    renderRecentMatchesPage(listNode);
  });
  pagination.nextButton?.addEventListener("click", () => {
    if (pagination.page >= getRecentMatchesPageCount(pagination)) {
      return;
    }
    pagination.page += 1;
    renderRecentMatchesPage(listNode);
  });
  pagination.pageSizeSelect?.addEventListener("change", () => {
    pagination.pageSize = normalizeRecentMatchesPageSize(
      pagination.pageSizeSelect.value,
    );
    pagination.page = 1;
    renderRecentMatchesPage(listNode);
  });
  return pagination;
}

function resetRecentMatchesPagination() {
  if (!recentMatchesPagination) {
    return;
  }

  recentMatchesPagination.items = [];
  recentMatchesPagination.page = 1;
  recentMatchesPagination.pageSize = DEFAULT_RECENT_MATCHES_PAGE_SIZE;
  if (recentMatchesPagination.pageSizeSelect) {
    recentMatchesPagination.pageSizeSelect.value = String(
      DEFAULT_RECENT_MATCHES_PAGE_SIZE,
    );
  }
  if (recentMatchesPagination.root) {
    recentMatchesPagination.root.hidden = true;
  }
}

function setRecentMatchesPaginationItems(items, listNode) {
  if (!recentMatchesPagination) {
    listNode.innerHTML = items.map((item) => renderRecentMatchCard(item)).join("");
    return;
  }

  recentMatchesPagination.items = items;
  recentMatchesPagination.page = 1;
  renderRecentMatchesPage(listNode);
}

function renderRecentMatchesPage(listNode) {
  const pagination = recentMatchesPagination;
  if (!pagination) {
    return;
  }

  const pageCount = getRecentMatchesPageCount(pagination);
  pagination.page = Math.min(Math.max(1, pagination.page), pageCount);
  const pageStart = (pagination.page - 1) * pagination.pageSize;
  const visibleItems = pagination.items.slice(pageStart, pageStart + pagination.pageSize);
  listNode.innerHTML = visibleItems.map((item) => renderRecentMatchCard(item)).join("");
  if (pagination.status) {
    pagination.status.textContent = `Pagina ${pagination.page} de ${pageCount}`;
  }
  if (pagination.previousButton) {
    pagination.previousButton.disabled = pagination.page <= 1;
  }
  if (pagination.nextButton) {
    pagination.nextButton.disabled = pagination.page >= pageCount;
  }
  if (pagination.root) {
    pagination.root.hidden = pagination.items.length <= DEFAULT_RECENT_MATCHES_PAGE_SIZE;
  }
}

function getRecentMatchesPageCount(pagination) {
  return Math.max(1, Math.ceil(pagination.items.length / pagination.pageSize));
}

function normalizeRecentMatchesPageSize(rawValue) {
  const pageSize = Number(rawValue);
  return RECENT_MATCHES_PAGE_SIZES.includes(pageSize)
    ? pageSize
    : DEFAULT_RECENT_MATCHES_PAGE_SIZE;
}

function renderRecentMatchCard(item) {
  const mapName = item.map?.pretty_name || item.map?.name || "Mapa no disponible";
  const detailUrl = buildInternalMatchDetailUrl(item);
  const actionLinks = [
    `<span class="historical-match-card__result">${escapeHtml(formatMatchResult(item.result))}</span>`,
    detailUrl
      ? `
        <a
          class="historical-match-card__link"
          href="${escapeHtml(detailUrl)}"
        >
          Ver detalles
        </a>
      `
      : "",
  ].join("");
  return `
    <article class="historical-match-card historical-match-card--clean">
      <div class="historical-match-card__top historical-match-card__top--clean">
        <h3 class="historical-match-card__title">${escapeHtml(mapName)}</h3>
      </div>

      <div class="historical-match-meta historical-match-meta--clean">
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
          <strong>${escapeHtml(formatPlayerCount(item.player_count, item.player_count_status))}</strong>
        </article>
        <article>
          <p class="historical-match-meta__label">Marcador</p>
          <strong>${escapeHtml(formatScore(item.result))}</strong>
        </article>
        <article class="historical-match-card__actions-cell" aria-label="Acciones de la partida">
          <div class="historical-match-card__actions">
            ${actionLinks}
          </div>
        </article>
      </div>
    </article>
  `;
}

function normalizeExternalMatchUrl(value) {
  if (typeof value !== "string" || !value.trim()) {
    return "";
  }
  try {
    const url = new URL(value.trim());
    return ["http:", "https:"].includes(url.protocol) ? url.href : "";
  } catch (error) {
    return "";
  }
}

function buildInternalMatchDetailUrl(item) {
  const serverSlug = item?.server?.slug;
  const matchId = item?.internal_detail_match_id || item?.match_id;
  if (typeof serverSlug !== "string" || !serverSlug.trim()) {
    return "";
  }
  if (typeof matchId !== "string" && typeof matchId !== "number") {
    return "";
  }
  const normalizedMatchId = String(matchId).trim();
  if (!normalizedMatchId) {
    return "";
  }
  return `./historico-partida.html?server=${encodeURIComponent(
    serverSlug.trim(),
  )}&match=${encodeURIComponent(normalizedMatchId)}`;
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
      : summaryBasis === "crcon-postgres-read-only"
        ? "CRCON PostgreSQL en modo solo lectura"
      : "el historico persistido disponible";
  const status = coverage?.status;
  void weeklyWindowDays;
  void serverSlug;
  if (status === "under-week") {
    return `Este bloque resume ${basisLabel}. La cobertura registrada todavia es inicial y puede crecer en los proximos dias.`;
  }
  if (serverSlug === "all-servers") {
    return `Resumen de los servidores desde ${basisLabel}, combinado solo con los servidores actuales de la comunidad.`;
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
    return `${windowLabel}: ${start} a ${end}.`;
  }
  return `${windowLabel}: ${start} a ${end}.`;
}

function buildLeaderboardTitle(metricConfig, serverSlug, timeframeKey) {
  const safeMetricConfig = metricConfig?.key
    ? metricConfig
    : getLeaderboardMetricConfig(metricConfig?.key);
  const timeframeLabel = getLeaderboardTimeframeConfig(timeframeKey).label;
  const titleLabel = safeMetricConfig?.title || LEADERBOARD_METRICS[0].title;
  return `${titleLabel} ${timeframeLabel} - ${getHistoricalServerLabel(serverSlug)}`;
}

function buildRecentMatchesNote(serverSlug) {
  if (serverSlug === "all-servers") {
    return "Lista de cierres ya registrados para los servidores con historico disponible.";
  }
  return `Lista de cierres ya registrados para ${getHistoricalServerLabel(serverSlug)}.`;
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

function preserveAggregateReason(node, payload) {
  if (!node) {
    return;
  }
  const reason = String(payload?.state_reason || "").trim();
  if (reason) {
    node.dataset.aggregateReason = reason;
  } else {
    delete node.dataset.aggregateReason;
  }
}

function describeAggregateProblem(payload) {
  const state = String(payload?.aggregate_state || "").toUpperCase();
  if (!state || state === "AVAILABLE") {
    return null;
  }
  if (state === "UNVERIFIED_SCHEMA") {
    return {
      title: "Alcance no compatible",
      message: "Este alcance no está soportado por la lectura histórica actual.",
    };
  }
  return {
    title: "Datos no disponibles",
    message: "El agregado CRCON no está disponible temporalmente. Vuelve a intentarlo más tarde.",
  };
}

function formatTopMaps(topMaps) {
  if (!Array.isArray(topMaps) || topMaps.length === 0) {
    return "Sin mapas frecuentes";
  }

  return topMaps
    .map((item) => `${item.map_name} (${formatNumber(item.matches_count)})`)
    .join(" / ");
}

function resolveHistoricalKills(item, metricConfig) {
  const directKills = Number(item?.kills);
  if (Number.isFinite(directKills)) {
    return directKills;
  }

  if (metricConfig?.key === "kills") {
    const metricValue = Number(item?.metric_value);
    if (Number.isFinite(metricValue)) {
      return metricValue;
    }
  }

  return Number.NaN;
}

function syncLeaderboardRatioColumn(tableNode, ratioHeadingNode, bodyNode, metricConfig) {
  if (!tableNode || !ratioHeadingNode || !bodyNode) {
    return;
  }
  const showRatio = shouldShowLeaderboardRatioColumn(metricConfig, bodyNode);
  ratioHeadingNode.hidden = !showRatio;
  ratioHeadingNode.textContent = metricConfig?.ratioHeading || "";
  const ratioColumnIndex = ratioHeadingNode.cellIndex;
  bodyNode.querySelectorAll("tr").forEach((row) => {
    const ratioCell = row.children[ratioColumnIndex];
    if (ratioCell) {
      ratioCell.hidden = !showRatio;
    }
  });
}

function shouldShowLeaderboardRatioColumn(metricConfig, bodyNode) {
  if (!metricConfig?.ratioMode) {
    return false;
  }
  if (metricConfig.ratioMode === "support") {
    return bodyNode.children.length > 0;
  }
  return true;
}

function formatHistoricalRatio(item, metricConfig, matches) {
  if (!metricConfig?.ratioMode) {
    return "";
  }
  if (metricConfig.ratioMode === "kills") {
    const kills = resolveHistoricalKills(item, metricConfig);
    return formatHistoricalPerMatch(item?.kills_per_match, kills, matches);
  }
  if (metricConfig.ratioMode === "deaths" || metricConfig.ratioMode === "support") {
    return formatHistoricalPerMatch(null, Number(item?.metric_value), matches);
  }
  return "";
}

function formatHistoricalPerMatch(rawDirectValue, rawTotalValue, rawMatches) {
  const directValue =
    rawDirectValue === null || rawDirectValue === undefined || rawDirectValue === ""
      ? Number.NaN
      : Number(rawDirectValue);
  if (Number.isFinite(directValue)) {
    return formatDecimal(directValue, 2);
  }

  const totalValue =
    rawTotalValue === null || rawTotalValue === undefined || rawTotalValue === ""
      ? Number.NaN
      : Number(rawTotalValue);
  const matches = Number(rawMatches);
  if (!Number.isFinite(totalValue) || !Number.isFinite(matches) || matches <= 0) {
    return "";
  }

  return formatDecimal(totalValue / matches, 2);
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
  if (winner === "allies" || winner === "allied") {
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
  if (!hasMatchScore(result)) {
    return "Resultado no disponible";
  }
  const alliedScore = Number(result.allied_score);
  const axisScore = Number(result.axis_score);
  return `${alliedScore} - ${axisScore}`;
}

function hasMatchScore(result) {
  return (
    result?.allied_score !== null &&
    result?.allied_score !== undefined &&
    result?.axis_score !== null &&
    result?.axis_score !== undefined &&
    Number.isFinite(Number(result?.allied_score)) &&
    Number.isFinite(Number(result?.axis_score))
  );
}

function formatRecentMatchStatus(item) {
  if (hasMatchScore(item?.result)) {
    const sourceLabel = formatResultSource(item?.result_source || item?.source_basis);
    return sourceLabel ? `Resultado confirmado (${sourceLabel})` : "Resultado confirmado";
  }
  if (item?.capture_basis === "rcon-competitive-window") {
    return "En curso";
  }
  if (item?.result_source || item?.source_basis || item?.capture_basis) {
    return formatResultSource(item.result_source || item.source_basis || item.capture_basis);
  }
  return "Resultado no disponible";
}

function formatResultSource(value) {
  if (value === "admin-log-match-ended") {
    return "cierre RCON";
  }
  if (value === "rcon-session") {
    return "sesion RCON";
  }
  if (value === "rcon-materialized-admin-log") {
    return "registro RCON";
  }
  if (value === "public-scoreboard-match") {
    return "scoreboard externo";
  }
  if (value === "rcon-competitive-window") {
    return "ventana RCON";
  }
  return value ? String(value).replaceAll("-", " ") : "";
}

function formatNumber(value) {
  const parsedValue = Number(value);
  if (!Number.isFinite(parsedValue)) {
    return "0";
  }

  return new Intl.NumberFormat("es-ES").format(parsedValue);
}

function formatPlayerCount(value, status) {
  const normalizedStatus = typeof status === "string" ? status.trim().toLowerCase() : "";
  if (value === null || value === undefined || normalizedStatus.startsWith("unknown")) {
    return "No disponible";
  }
  const parsedValue = Number(value);
  if (!Number.isInteger(parsedValue) || parsedValue < 0) {
    return "No disponible";
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
      "Todavia no existe un resumen listo para el alcance seleccionado.",
    recentMessage: "Todavia no hay partidas recientes disponibles.",
  };
}
