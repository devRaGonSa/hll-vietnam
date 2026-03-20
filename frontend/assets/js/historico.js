const HISTORICAL_SERVER_SLUGS = Object.freeze([
  "comunidad-hispana-01",
  "comunidad-hispana-02",
]);
const DEFAULT_HISTORICAL_SERVER = HISTORICAL_SERVER_SLUGS[0];

document.addEventListener("DOMContentLoaded", () => {
  const backendBaseUrl =
    document.body.dataset.backendBaseUrl || "http://127.0.0.1:8000";
  const selectorButtons = Array.from(
    document.querySelectorAll("[data-server-slug]"),
  );
  const summaryNode = document.getElementById("historical-summary");
  const rangeNode = document.getElementById("historical-range");
  const weeklyStateNode = document.getElementById("weekly-top-kills-state");
  const weeklyTableNode = document.getElementById("weekly-top-kills-table");
  const weeklyBodyNode = document.getElementById("weekly-top-kills-body");
  const recentStateNode = document.getElementById("recent-matches-state");
  const recentListNode = document.getElementById("recent-matches-list");

  const params = new URLSearchParams(window.location.search);
  let activeServerSlug = normalizeServerSlug(params.get("server"));

  const refreshHistoricalView = async () => {
    syncActiveButtons(selectorButtons, activeServerSlug);
    setRangeBadge(rangeNode, "Cargando rango temporal", false);
    renderSummaryLoading(summaryNode);
    setState(weeklyStateNode, "Cargando ranking semanal...");
    setState(recentStateNode, "Cargando partidas recientes...");
    weeklyTableNode.hidden = true;
    recentListNode.innerHTML = "";

    const [summaryResult, topKillsResult, recentMatchesResult] =
      await Promise.allSettled([
        fetchJson(
          `${backendBaseUrl}/api/historical/server-summary?server=${encodeURIComponent(activeServerSlug)}`,
        ),
        fetchJson(
          `${backendBaseUrl}/api/historical/weekly-top-kills?server=${encodeURIComponent(activeServerSlug)}&limit=10`,
        ),
        fetchJson(
          `${backendBaseUrl}/api/historical/recent-matches?server=${encodeURIComponent(activeServerSlug)}&limit=6`,
        ),
      ]);

    hydrateSummary(summaryResult, summaryNode, rangeNode);
    hydrateWeeklyTopKills(
      topKillsResult,
      weeklyStateNode,
      weeklyTableNode,
      weeklyBodyNode,
    );
    hydrateRecentMatches(recentMatchesResult, recentStateNode, recentListNode);
  };

  selectorButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const nextServerSlug = normalizeServerSlug(button.dataset.serverSlug);
      if (nextServerSlug === activeServerSlug) {
        return;
      }

      activeServerSlug = nextServerSlug;
      params.set("server", activeServerSlug);
      window.history.replaceState({}, "", `?${params.toString()}`);
      void refreshHistoricalView();
    });
  });

  void refreshHistoricalView();
});

function hydrateSummary(result, summaryNode, rangeNode) {
  if (result.status !== "fulfilled") {
    renderSummaryError(summaryNode);
    setRangeBadge(rangeNode, "Resumen historico no disponible", false);
    return;
  }

  const items = result.value?.data?.items;
  if (!Array.isArray(items) || items.length === 0) {
    renderSummaryEmpty(summaryNode);
    setRangeBadge(rangeNode, "Sin cobertura historica", false);
    return;
  }

  const summary = items[0];
  const timeRange = summary.time_range || {};
  const rangeLabel = buildRangeLabel(timeRange.start, timeRange.end);
  setRangeBadge(
    rangeNode,
    rangeLabel || "Cobertura parcial disponible",
    Boolean(rangeLabel),
  );
  summaryNode.innerHTML = [
    renderSummaryCard("Servidor", summary.server?.name || "Servidor no disponible"),
    renderSummaryCard("Partidas", formatNumber(summary.matches_count)),
    renderSummaryCard("Jugadores unicos", formatNumber(summary.unique_players)),
    renderSummaryCard("Kills agregadas", formatNumber(summary.total_kills)),
    renderSummaryCard(
      "Mapas dominantes",
      formatTopMaps(summary.top_maps),
    ),
  ].join("");
}

function hydrateWeeklyTopKills(
  result,
  stateNode,
  tableNode,
  bodyNode,
) {
  if (result.status !== "fulfilled") {
    setState(stateNode, "No se pudo cargar el ranking semanal.", true);
    tableNode.hidden = true;
    return;
  }

  const items = result.value?.data?.items;
  if (!Array.isArray(items) || items.length === 0) {
    setState(
      stateNode,
      "Sin datos historicos suficientes para construir el ranking semanal.",
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
          <td>${escapeHtml(formatNumber(item.weekly_kills))}</td>
          <td>${escapeHtml(formatNumber(item.matches_considered))}</td>
          <td>${escapeHtml(item.server?.name || "Servidor no disponible")}</td>
        </tr>
      `,
    )
    .join("");
  stateNode.hidden = true;
  tableNode.hidden = false;
}

function hydrateRecentMatches(result, stateNode, listNode) {
  if (result.status !== "fulfilled") {
    setState(stateNode, "No se pudieron cargar las partidas recientes.", true);
    return;
  }

  const items = result.value?.data?.items;
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

function syncActiveButtons(buttons, activeServerSlug) {
  buttons.forEach((button) => {
    button.classList.toggle(
      "is-active",
      button.dataset.serverSlug === activeServerSlug,
    );
  });
}

function normalizeServerSlug(rawValue) {
  const normalized = typeof rawValue === "string" ? rawValue.trim() : "";
  if (HISTORICAL_SERVER_SLUGS.includes(normalized)) {
    return normalized;
  }

  return DEFAULT_HISTORICAL_SERVER;
}

function buildRangeLabel(start, end) {
  if (!start && !end) {
    return "";
  }

  return `${formatTimestamp(start)} a ${formatTimestamp(end)}`;
}

function formatTopMaps(topMaps) {
  if (!Array.isArray(topMaps) || topMaps.length === 0) {
    return "Sin mapas dominantes";
  }

  return topMaps
    .map((item) => `${item.map_name} (${formatNumber(item.matches_count)})`)
    .join(" / ");
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
