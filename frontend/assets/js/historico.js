const HISTORICAL_SERVER_SLUGS = Object.freeze([
  "comunidad-hispana-01",
  "comunidad-hispana-02",
]);
const DEFAULT_HISTORICAL_SERVER = HISTORICAL_SERVER_SLUGS[0];
const LEADERBOARD_METRICS = Object.freeze([
  {
    key: "kills",
    title: "Top kills de los ultimos 7 dias",
    valueHeading: "Kills",
    emptyMessage: "Sin datos historicos suficientes para mostrar el top de kills semanal.",
  },
  {
    key: "deaths",
    title: "Top muertes de los ultimos 7 dias",
    valueHeading: "Muertes",
    emptyMessage: "Sin datos historicos suficientes para mostrar el top de muertes semanal.",
  },
  {
    key: "matches_over_100_kills",
    title: "Top partidas con 100+ kills",
    valueHeading: "Partidas 100+",
    emptyMessage: "Ningun jugador ha registrado partidas de 100+ kills en esta ventana semanal.",
  },
  {
    key: "support",
    title: "Top puntos de soporte de los ultimos 7 dias",
    valueHeading: "Soporte",
    emptyMessage: "Sin datos historicos suficientes para mostrar el top de soporte semanal.",
  },
]);
const DEFAULT_LEADERBOARD_METRIC = LEADERBOARD_METRICS[0].key;

document.addEventListener("DOMContentLoaded", () => {
  const backendBaseUrl =
    document.body.dataset.backendBaseUrl || "http://127.0.0.1:8000";
  const selectorButtons = Array.from(
    document.querySelectorAll("[data-server-slug]"),
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
  const weeklyWindowNoteNode = document.getElementById("weekly-window-note");
  const weeklySnapshotMetaNode = document.getElementById(
    "weekly-leaderboard-snapshot-meta",
  );
  const recentStateNode = document.getElementById("recent-matches-state");
  const recentListNode = document.getElementById("recent-matches-list");
  const recentSnapshotMetaNode = document.getElementById(
    "recent-matches-snapshot-meta",
  );

  const params = new URLSearchParams(window.location.search);
  let activeServerSlug = normalizeServerSlug(params.get("server"));
  let activeLeaderboardMetric = normalizeLeaderboardMetric(params.get("metric"));
  let activeServerRequestId = 0;
  let activeLeaderboardRequestId = 0;

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
      `${backendBaseUrl}/api/historical/snapshots/recent-matches?server=${encodeURIComponent(serverSlug)}&limit=6`,
    );

  const getLeaderboardSnapshot = (serverSlug, metricKey) =>
    getCachedJson(
      leaderboardCache,
      pendingRequestCache,
      buildLeaderboardSnapshotKey(serverSlug, metricKey),
      `${backendBaseUrl}/api/historical/snapshots/weekly-leaderboard?server=${encodeURIComponent(serverSlug)}&metric=${encodeURIComponent(metricKey)}&limit=10`,
    );

  const prefetchLeaderboardSnapshots = (serverSlug) => {
    LEADERBOARD_METRICS.forEach((metric) => {
      void getLeaderboardSnapshot(serverSlug, metric.key).catch(() => {});
    });
  };

  const refreshServerContent = async () => {
    const requestId = activeServerRequestId + 1;
    activeServerRequestId = requestId;
    const activeMetricConfig = getLeaderboardMetricConfig(activeLeaderboardMetric);

    syncActiveButtons(selectorButtons, activeServerSlug);
    syncLeaderboardTabs(leaderboardTabButtons, activeLeaderboardMetric);
    weeklyTitleNode.textContent = activeMetricConfig.title;
    weeklyValueHeadingNode.textContent = activeMetricConfig.valueHeading;
    setRangeBadge(rangeNode, "Cargando rango temporal", false);
    summaryNoteNode.textContent =
      "La vista esta leyendo snapshots precalculados del historico local.";
    setSnapshotMeta(summarySnapshotMetaNode, "Cargando snapshot de resumen...");
    renderSummaryLoading(summaryNode);
    weeklyWindowNoteNode.textContent =
      "Cargando snapshot semanal del servidor activo...";
    setSnapshotMeta(weeklySnapshotMetaNode, "Preparando snapshot semanal...");
    recentListNode.innerHTML = "";
    setState(recentStateNode, "Cargando partidas recientes...");
    setSnapshotMeta(recentSnapshotMetaNode, "Cargando snapshot de partidas...");

    const cachedLeaderboardPayload = leaderboardCache.get(
      buildLeaderboardSnapshotKey(activeServerSlug, activeLeaderboardMetric),
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
      );
    } else {
      setState(weeklyStateNode, "Cargando ranking semanal...");
      weeklyTableNode.hidden = true;
    }

    const targetServerSlug = activeServerSlug;
    const targetMetric = activeLeaderboardMetric;
    const [summaryResult, recentMatchesResult, leaderboardResult] =
      await Promise.allSettled([
        getSummarySnapshot(targetServerSlug),
        getRecentMatchesSnapshot(targetServerSlug),
        getLeaderboardSnapshot(targetServerSlug, targetMetric),
      ]);

    if (
      requestId !== activeServerRequestId ||
      targetServerSlug !== activeServerSlug ||
      targetMetric !== activeLeaderboardMetric
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
    hydrateRecentMatches(
      recentMatchesResult,
      recentStateNode,
      recentListNode,
      recentSnapshotMetaNode,
    );
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
    );

    prefetchLeaderboardSnapshots(targetServerSlug);
  };

  const refreshLeaderboardContent = async () => {
    const requestId = activeLeaderboardRequestId + 1;
    activeLeaderboardRequestId = requestId;
    const metricConfig = getLeaderboardMetricConfig(activeLeaderboardMetric);
    const targetServerSlug = activeServerSlug;
    const targetMetric = activeLeaderboardMetric;

    syncLeaderboardTabs(leaderboardTabButtons, activeLeaderboardMetric);
    weeklyTitleNode.textContent = metricConfig.title;
    weeklyValueHeadingNode.textContent = metricConfig.valueHeading;

    const cachedPayload = leaderboardCache.get(
      buildLeaderboardSnapshotKey(targetServerSlug, targetMetric),
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
      );
      return;
    }

    weeklyWindowNoteNode.textContent =
      "Cargando snapshot semanal del servidor activo...";
    setSnapshotMeta(weeklySnapshotMetaNode, "Cargando snapshot semanal...");
    setState(weeklyStateNode, "Cargando ranking semanal...");
    weeklyTableNode.hidden = true;

    const leaderboardResult = await settlePromise(
      getLeaderboardSnapshot(targetServerSlug, targetMetric),
    );

    if (
      requestId !== activeLeaderboardRequestId ||
      targetServerSlug !== activeServerSlug ||
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
      params.set("metric", activeLeaderboardMetric);
      window.history.replaceState({}, "", `?${params.toString()}`);
      void refreshServerContent();
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
      params.set("metric", activeLeaderboardMetric);
      window.history.replaceState({}, "", `?${params.toString()}`);
      void refreshLeaderboardContent();
    });
  });

  prefetchLeaderboardSnapshots(activeServerSlug);
  void refreshServerContent();
});

function hydrateSummary(result, summaryNode, rangeNode, noteNode, snapshotMetaNode) {
  if (result.status !== "fulfilled") {
    renderSummaryError(summaryNode);
    setRangeBadge(rangeNode, "Snapshot de resumen no disponible", false);
    noteNode.textContent =
      "No se pudo leer el resumen precalculado para este servidor.";
    setSnapshotMeta(snapshotMetaNode, "Error al leer el snapshot de resumen.");
    return;
  }

  const payload = result.value?.data;
  const summary = payload?.item;
  if (!payload?.found || !summary) {
    renderSummaryEmpty(summaryNode);
    setRangeBadge(rangeNode, "Sin snapshot de resumen", false);
    noteNode.textContent =
      "Todavia no existe un snapshot de resumen listo para este servidor.";
    setSnapshotMeta(snapshotMetaNode, "Snapshot de resumen pendiente de generacion.");
    return;
  }

  const coverage = summary.coverage || {};
  const timeRange = summary.time_range || {};
  const rangeLabel = buildCoverageBadgeLabel(coverage, {
    start: payload?.source_range_start || timeRange.start,
    end: payload?.source_range_end || timeRange.end,
  });
  setRangeBadge(
    rangeNode,
    rangeLabel || "Cobertura registrada parcial",
    coverage.status === "week-plus" && !payload?.is_stale,
  );
  noteNode.textContent = buildSummaryNote(
    "snapshot-precomputed",
    7,
    coverage,
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
      "Periodo registrado",
      formatCoverageDays(coverage.coverage_days),
    ),
    renderSummaryCard("Primera partida", formatTimestamp(coverage.first_match_at)),
    renderSummaryCard("Ultima partida", formatTimestamp(coverage.last_match_at)),
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
) {
  titleNode.textContent = metricConfig.title;
  valueHeadingNode.textContent = metricConfig.valueHeading;
  if (result.status !== "fulfilled") {
    noteNode.textContent =
      "No se pudo leer el snapshot semanal precalculado para esta metrica.";
    setSnapshotMeta(snapshotMetaNode, "Error al leer el snapshot semanal.");
    setState(stateNode, "No se pudo cargar el ranking semanal.", true);
    tableNode.hidden = true;
    return;
  }

  const payload = result.value?.data;
  noteNode.textContent = buildWeeklyWindowNote(payload);
  setSnapshotMeta(
    snapshotMetaNode,
    buildSnapshotMetaText(payload, "Snapshot semanal pendiente de generacion."),
  );
  if (!payload?.found) {
    setState(stateNode, metricConfig.emptyMessage);
    tableNode.hidden = true;
    return;
  }

  const items = payload?.items;
  if (!Array.isArray(items) || items.length === 0) {
    setState(stateNode, metricConfig.emptyMessage);
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
        </tr>
      `,
    )
    .join("");
  stateNode.hidden = true;
  tableNode.hidden = false;
}

function hydrateRecentMatches(result, stateNode, listNode, snapshotMetaNode) {
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
    setState(stateNode, "Todavia no hay snapshot de partidas recientes disponible.");
    return;
  }

  const items = payload?.items;
  if (!Array.isArray(items) || items.length === 0) {
    setState(stateNode, "Todavia no hay partidas recientes disponibles.");
    return;
  }

  listNode.innerHTML = items.map((item) => renderRecentMatchCard(item)).join("");
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

function renderSummaryEmpty(summaryNode) {
  summaryNode.innerHTML = renderSummaryCard("Estado", "Sin datos historicos suficientes");
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

function normalizeServerSlug(rawValue) {
  const normalized = typeof rawValue === "string" ? rawValue.trim() : "";
  if (HISTORICAL_SERVER_SLUGS.includes(normalized)) {
    return normalized;
  }

  return DEFAULT_HISTORICAL_SERVER;
}

function normalizeLeaderboardMetric(rawValue) {
  const normalized = typeof rawValue === "string" ? rawValue.trim() : "";
  if (LEADERBOARD_METRICS.some((metric) => metric.key === normalized)) {
    return normalized;
  }

  return DEFAULT_LEADERBOARD_METRIC;
}

function getLeaderboardMetricConfig(metricKey) {
  return (
    LEADERBOARD_METRICS.find((metric) => metric.key === metricKey) ||
    LEADERBOARD_METRICS[0]
  );
}

function buildSummarySnapshotKey(serverSlug) {
  return `summary:${serverSlug}`;
}

function buildRecentMatchesSnapshotKey(serverSlug) {
  return `recent:${serverSlug}`;
}

function buildLeaderboardSnapshotKey(serverSlug, metricKey) {
  return `leaderboard:${serverSlug}:${metricKey}`;
}

function buildRangeLabel(start, end) {
  if (!start && !end) {
    return "";
  }

  return `${formatTimestamp(start)} a ${formatTimestamp(end)}`;
}

function buildCoverageBadgeLabel(coverage, timeRange) {
  const coverageDays = formatCoverageDays(coverage?.coverage_days);
  const rangeLabel = buildRangeLabel(
    coverage?.first_match_at || timeRange?.start,
    coverage?.last_match_at || timeRange?.end,
  );
  if (coverageDays !== "Cobertura no disponible" && rangeLabel) {
    return `${coverageDays} registrados`;
  }
  return rangeLabel;
}

function buildSummaryNote(summaryBasis, weeklyWindowDays, coverage) {
  const basisLabel =
    summaryBasis === "snapshot-precomputed"
      ? "el snapshot precalculado del historico local"
      : "el historico persistido disponible";
  const weeklyWindowLabel = Number.isFinite(Number(weeklyWindowDays))
    ? `${weeklyWindowDays} dias`
    : "la ultima semana";
  const status = coverage?.status;
  if (status === "under-week") {
    return `Este bloque resume ${basisLabel}. Ahora mismo esa cobertura todavia no alcanza ${weeklyWindowLabel}.`;
  }
  return `Resumen servido desde ${basisLabel}.`;
}

function buildWeeklyWindowNote(payload) {
  if (!payload?.found) {
    return "No existe un snapshot semanal listo para esta metrica en el servidor activo.";
  }

  const start = formatTimestamp(payload?.window_start);
  const end = formatTimestamp(payload?.window_end);
  const windowDays = Number(payload?.window_days);
  const daysLabel = Number.isFinite(windowDays) ? `${windowDays} dias` : "7 dias";
  return `Ranking servido desde snapshot semanal de ${daysLabel}: ${start} a ${end}.`;
}

function buildSnapshotMetaText(payload, missingMessage) {
  if (!payload?.generated_at) {
    return missingMessage;
  }

  const parts = [
    payload.is_stale
      ? `Snapshot posiblemente desactualizado: ${formatTimestamp(payload.generated_at)}`
      : `Snapshot generado: ${formatTimestamp(payload.generated_at)}`,
  ];
  const sourceRangeLabel = buildRangeLabel(
    payload?.source_range_start,
    payload?.source_range_end,
  );
  if (sourceRangeLabel) {
    parts.push(`Fuente: ${sourceRangeLabel}`);
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

function formatCoverageDays(value) {
  const parsedValue = Number(value);
  if (!Number.isFinite(parsedValue) || parsedValue <= 0) {
    return "Cobertura no disponible";
  }
  return `${new Intl.NumberFormat("es-ES", {
    maximumFractionDigits: 1,
    minimumFractionDigits: parsedValue < 10 ? 1 : 0,
  }).format(parsedValue)} dias`;
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
  if (cache.has(key)) {
    return cache.get(key);
  }
  if (pendingCache.has(key)) {
    return pendingCache.get(key);
  }

  const request = fetchJson(url)
    .then((payload) => {
      cache.set(key, payload);
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
