document.addEventListener("DOMContentLoaded", () => {
  const backendBaseUrl = document.body.dataset.backendBaseUrl || "http://127.0.0.1:8000";
  const form = document.getElementById("ranking-form");
  const timeframeSelect = document.getElementById("ranking-timeframe");
  const serverSelect = document.getElementById("ranking-server");
  const metricSelect = document.getElementById("ranking-metric");
  const limitSelect = document.getElementById("ranking-limit");
  const stateNode = document.getElementById("ranking-state");
  const titleNode = document.getElementById("ranking-title");
  const metaNode = document.getElementById("ranking-meta");
  const tableNode = document.getElementById("ranking-table");
  const tableBodyNode = document.getElementById("ranking-table-body");
  const metricHeadingNode = document.getElementById("ranking-metric-heading");
  const kppHeadingNode = document.getElementById("ranking-kpp-heading");
  const emptyNode = document.getElementById("ranking-empty");

  const annualYear = 2026;
  const defaultMetric = "kills";
  const defaultLimit = "20";
  const defaultTimeframe = "weekly";
  const defaultServerId = "all";
  const supportedMetrics = [
    "kills",
    "deaths",
    "teamkills",
    "matches_considered",
    "kd_ratio",
    "kills_per_match",
  ];
  const supportedTimeframes = ["weekly", "monthly", "annual"];
  const supportedServerIds = [
    "all",
    "comunidad-hispana-01",
    "comunidad-hispana-02",
  ];
  const supportedLimits = ["5", "10", "20", "30", "50", "100"];

  let currentRequestId = 0;
  let activeController = null;

  applyInitialUrlState();
  syncMetricState();
  clearRankingSurface();
  void loadRanking();

  if (timeframeSelect) {
    timeframeSelect.addEventListener("change", () => {
      syncMetricState();
      updateUrlState();
      void loadRanking();
    });
  }

  [serverSelect, metricSelect, limitSelect].forEach((node) => {
    if (!node) {
      return;
    }
    node.addEventListener("change", () => {
      syncMetricState();
      updateUrlState();
      void loadRanking();
    });
  });

  if (form) {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
    });
  }

  function setRankingState(state, message) {
    if (!stateNode) {
      return;
    }
    const normalizedMessage = String(message || "").trim();
    stateNode.hidden = !normalizedMessage;
    stateNode.textContent = normalizedMessage;
    stateNode.className = `stats-state stats-state--${state}`;
  }

  function applyInitialUrlState() {
    const params = new URLSearchParams(window.location.search);
    const timeframe = params.get("timeframe");
    const serverId = params.get("server_id") || params.get("server");
    const metric = params.get("metric");
    const limit = params.get("limit");
    const year = params.get("year");

    if (timeframeSelect) {
      timeframeSelect.value = supportedTimeframes.includes(timeframe || "")
        ? String(timeframe)
        : defaultTimeframe;
    }
    if (serverSelect) {
      serverSelect.value = supportedServerIds.includes(serverId || "")
        ? String(serverId)
        : defaultServerId;
    }
    if (metricSelect) {
      metricSelect.value = supportedMetrics.includes(metric || "")
        ? String(metric)
        : defaultMetric;
    }
    if (limitSelect) {
      limitSelect.value = supportedLimits.includes(limit || "")
        ? String(limit)
        : defaultLimit;
    }

    if (params.has("limit") && !supportedLimits.includes(limit || "")) {
      setRankingState(
        "warning",
        "El limite del URL no es valido para esta interfaz. Se restauro el valor permitido por defecto.",
      );
    }
    if (params.has("year")) {
      const normalizedYear = Number.parseInt(year || "", 10);
      if (Number.isFinite(normalizedYear) && normalizedYear !== annualYear) {
        setRankingState(
          "warning",
          `El ranking anual de esta vista usa ${annualYear}. Se ajusto el a\u00f1o del URL.`,
        );
      }
    }
  }

  function syncMetricState() {
    const isAnnual = timeframeSelect?.value === "annual";
    if (!metricSelect) {
      return;
    }

    Array.from(metricSelect.options).forEach((option) => {
      option.disabled = isAnnual && !supportedMetrics.includes(option.value);
    });

    if (isAnnual && !supportedMetrics.includes(metricSelect.value)) {
      metricSelect.value = defaultMetric;
    }
  }

  function updateUrlState() {
    const searchParams = new URLSearchParams({
      timeframe: String(timeframeSelect?.value || defaultTimeframe),
      server_id: String(serverSelect?.value || defaultServerId),
      metric: String(metricSelect?.value || defaultMetric),
      limit: String(limitSelect?.value || defaultLimit),
    });
    if (searchParams.get("timeframe") === "annual") {
      searchParams.set("year", String(annualYear));
    }
    window.history.replaceState({}, "", `?${searchParams.toString()}`);
  }

  function clearRankingSurface() {
    if (metaNode) {
      metaNode.innerHTML = "";
    }
    if (tableBodyNode) {
      tableBodyNode.innerHTML = "";
    }
    if (tableNode) {
      tableNode.hidden = true;
    }
    if (emptyNode) {
      emptyNode.hidden = true;
      emptyNode.textContent = "";
    }
  }

  function renderEmptyState(message) {
    clearRankingSurface();
    if (!emptyNode) {
      return;
    }
    emptyNode.hidden = false;
    emptyNode.textContent = message;
  }

  async function loadRanking() {
    const requestId = currentRequestId + 1;
    currentRequestId = requestId;
    const timeframe = String(timeframeSelect?.value || defaultTimeframe);
    const serverId = String(serverSelect?.value || defaultServerId);
    const metric = String(metricSelect?.value || defaultMetric);
    const limit = String(limitSelect?.value || defaultLimit);

    let year = null;
    if (timeframe === "annual") {
      year = annualYear;
    }

    setRankingState("loading", "Cargando ranking global...");

    if (activeController) {
      activeController.abort();
    }
    activeController = new AbortController();

    try {
      const searchParams = new URLSearchParams({
        timeframe,
        server_id: serverId,
        metric,
        limit,
      });
      if (timeframe === "annual" && year !== null) {
        searchParams.set("year", String(year));
      }

      const response = await fetch(`${backendBaseUrl}/api/ranking?${searchParams.toString()}`, {
        signal: activeController.signal,
      });
      if (requestId !== currentRequestId) {
        return;
      }
      if (!response.ok) {
        const errorPayload = await safeParseJson(response);
        const errorMessage = String(
          errorPayload?.message || errorPayload?.detail || "",
        ).toLowerCase();
        handleRequestError(response.status, errorMessage, timeframe);
        return;
      }

      const payload = await response.json();
      if (!payload || payload.status !== "ok") {
        throw new Error(payload?.message || "Respuesta de ranking invalida");
      }

      renderRanking(payload.data || {});
    } catch (error) {
      if (error?.name === "AbortError") {
        return;
      }
      if (requestId !== currentRequestId) {
        return;
      }
      console.warn("Ranking request failed", error);
      setRankingState("error", "Error controlado al cargar el ranking.");
      renderEmptyState(
        "La lectura del ranking fall\u00f3 en este intento. Revisa el backend o vuelve a intentarlo.",
      );
    } finally {
      if (requestId === currentRequestId) {
        activeController = null;
      }
    }
  }

  function handleRequestError(statusCode, errorMessage, timeframe) {
    const normalizedMessage = String(errorMessage || "");
    if (statusCode === 400 && normalizedMessage.includes("limit")) {
      setRankingState("warning", "El limite solicitado no es valido.");
      renderEmptyState(
        "Usa un limite permitido por la interfaz o por el backend. Esta vista admite Top 5, 10, 20, 30, 50 y 100.",
      );
      return;
    }
    if (
      statusCode === 400 &&
      normalizedMessage.includes("metric") &&
      normalizedMessage.includes("annual")
    ) {
      setRankingState("warning", "La metrica anual solicitada no esta disponible.");
      renderEmptyState(
        "La consulta anual devolvio una metrica sin snapshot seguro para esta vista.",
      );
      return;
    }
    if (statusCode === 400 && normalizedMessage.includes("metric")) {
      setRankingState("warning", "La m\u00e9trica solicitada no est\u00e1 soportada.");
      renderEmptyState(
        "Usa Kills, Muertes, TK, Partidas, KD o Kills/partida.",
      );
      return;
    }
    if (statusCode === 400 && normalizedMessage.includes("timeframe")) {
      setRankingState("warning", "El periodo solicitado no esta soportado.");
      renderEmptyState("Usa un periodo semanal, mensual o anual.");
      return;
    }
    setRankingState(
      "error",
      timeframe === "annual"
        ? "Error controlado al cargar el ranking anual."
        : "Error controlado al cargar el ranking.",
    );
    renderEmptyState(
      "La consulta devolvio un error controlado. Ajusta los filtros y vuelve a intentarlo.",
    );
  }

  function renderRanking(data) {
    const items = Array.isArray(data.items) ? data.items : [];
    const timeframe = String(data.timeframe || defaultTimeframe);
    const serverId = String(data.server_id || defaultServerId);
    const metric = String(data.metric || defaultMetric);
    const snapshotStatus = String(data.snapshot_status || "").toLowerCase();

    if (titleNode) {
      titleNode.textContent =
        timeframe === "annual"
          ? `Top anual por ${labelForMetric(metric)}`
          : `Tabla activa por ${labelForMetric(metric)}`;
    }
    if (metricHeadingNode) {
      metricHeadingNode.textContent = labelForMetric(metric);
    }
    if (metaNode) {
      metaNode.innerHTML = buildMetaMarkup(data);
    }

    if (timeframe === "annual" && snapshotStatus === "missing") {
      setRankingState("warning", "Snapshot anual no disponible para esta metrica.");
      renderEmptyState(
        "Genera el snapshot anual para esta combinacion de metrica, servidor y a\u00f1o antes de publicarlo.",
      );
      return;
    }

    if (!items.length) {
      setRankingState(
        "neutral",
        timeframe === "annual"
          ? "Snapshot anual listo pero sin filas visibles para este filtro."
          : "No hay datos visibles para el periodo y servidor seleccionado.",
      );
      renderEmptyState(
        timeframe === "annual"
          ? "La lectura anual existe pero no devolvio filas para este filtro."
          : "No se encontraron jugadores con actividad suficiente en este periodo.",
      );
      return;
    }

    setRankingState("ready", "");

    if (tableBodyNode) {
      tableBodyNode.innerHTML = items.map((item) => renderRow(item, metric)).join("");
    }
    syncKppColumn(metric);
    if (tableNode) {
      tableNode.hidden = false;
    }
    if (emptyNode) {
      emptyNode.hidden = true;
    }
  }

  function buildMetaMarkup(data) {
    const source = data.source && typeof data.source === "object" ? data.source : {};
    const timeframe = String(data.timeframe || defaultTimeframe);
    const metric = String(data.metric || defaultMetric);
    const cards = [
      { label: "Periodo activo", value: labelForTimeframe(timeframe), active: true },
      { label: "Servidor activo", value: labelForServer(data.server_id), active: true },
      { label: "M\u00e9trica activa", value: labelForMetric(metric), active: true },
      { label: "L\u00edmite", value: `Top ${safeInt(data.limit, safeInt(defaultLimit, 20))}` },
      { label: "Periodo", value: labelForWindow(data) },
      { label: "Actualizado", value: formatDateTime(source.generated_at) },
    ];

    if (timeframe === "annual") {
      cards.push({
        label: "Snapshot",
        value: String(data.snapshot_status || "missing"),
      });
    }

    return cards
      .map(
        (card) => `
          <article class="ranking-meta-card${card.active ? " ranking-meta-card--active" : ""}">
            <p>${escapeHtml(card.label)}</p>
            <strong>${escapeHtml(String(card.value || "No disponible"))}</strong>
          </article>
        `,
      )
      .join("");
  }

  function renderRow(item, metric) {
    const killsPerMatch = formatKillsPerMatch(
      item.kills_per_match,
      item.kills,
      item.matches_considered,
    );
    const hideKppColumn = metric === "kills_per_match";

      return `
        <tr>
          <td>#${safeInt(item.ranking_position, 0)}</td>
          <td>
            <div class="ranking-player">
              <strong>${escapeHtml(String(item.player_name || "Jugador sin nombre"))}</strong>
            </div>
          </td>
        <td class="ranking-table__metric">${formatMetricValue(item.metric_value, metric)}</td>
        <td>${safeInt(item.matches_considered, 0)}</td>
        <td>${safeInt(item.kills, 0)}</td>
        <td>${safeInt(item.deaths, 0)}</td>
        <td>${safeInt(item.teamkills, 0)}</td>
        <td>${safeDecimal(item.kd_ratio, 2, "0.00")}</td>
        ${hideKppColumn ? "" : `<td>${killsPerMatch}</td>`}
      </tr>
    `;
  }

  function syncKppColumn(metric) {
    if (!tableNode || !kppHeadingNode) {
      return;
    }

    const kppColumnIndex = kppHeadingNode.cellIndex + 1;
    const hideKppColumn = metric === "kills_per_match";
    kppHeadingNode.hidden = hideKppColumn;

    tableNode.querySelectorAll("tbody tr").forEach((row) => {
      const cell = row.children[kppColumnIndex - 1];
      if (cell) {
        cell.hidden = hideKppColumn;
      }
    });
  }

  function labelForWindow(data) {
    if (String(data.timeframe || "") === "annual") {
      return `A\u00f1o ${safeInt(data.year, annualYear)}`;
    }
    return String(data.window_label || data.window_kind || "Periodo activo");
  }

  function labelForServer(serverId) {
    if (serverId === "comunidad-hispana-01") {
      return "Comunidad Hispana #01";
    }
    if (serverId === "comunidad-hispana-02") {
      return "Comunidad Hispana #02";
    }
    return "Todos los servidores";
  }

  function labelForTimeframe(timeframe) {
    if (timeframe === "monthly") {
      return "mensual";
    }
    if (timeframe === "annual") {
      return "anual";
    }
    return "semanal";
  }

  function labelForMetric(metric) {
    const labels = {
      kills: "Kills",
      deaths: "Muertes",
      teamkills: "TK",
      matches_considered: "Partidas",
      kd_ratio: "KD",
      kills_per_match: "Kills/partida",
    };
    return labels[metric] || "Kills";
  }

  function formatMetricValue(value, metric) {
    if (metric === "kd_ratio" || metric === "kills_per_match") {
      return safeDecimal(value, 2, "0.00");
    }
    return safeInt(value, 0).toLocaleString("es-ES");
  }

  function safeInt(value, fallback) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) {
      return fallback;
    }
    return Math.trunc(parsed);
  }

  function safeDecimal(value, maximumFractionDigits, fallback) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) {
      return fallback;
    }
    return parsed.toLocaleString("es-ES", {
      minimumFractionDigits: maximumFractionDigits,
      maximumFractionDigits,
    });
  }

  function formatKillsPerMatch(rawKillsPerMatch, rawKills, rawMatches) {
    const directValue = Number(rawKillsPerMatch);
    if (Number.isFinite(directValue)) {
      return safeDecimal(directValue, 2, "0.00");
    }

    const kills = Number(rawKills);
    const matches = Number(rawMatches);
    if (!Number.isFinite(kills) || !Number.isFinite(matches) || matches <= 0) {
      return "-";
    }

    return safeDecimal(kills / matches, 2, "0.00");
  }

  function safeParseJson(response) {
    if (!response) {
      return null;
    }
    return response
      .json()
      .then((parsed) => parsed)
      .catch(() => null);
  }

  function formatDateTime(value) {
    if (!value) {
      return "No disponible";
    }
    const parsedDate = new Date(String(value));
    if (Number.isNaN(parsedDate.getTime())) {
      return "No disponible";
    }
    return new Intl.DateTimeFormat("es-ES", {
      dateStyle: "short",
      timeStyle: "short",
    }).format(parsedDate);
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }
});

