document.addEventListener("DOMContentLoaded", () => {
  const backendBaseUrl = document.body.dataset.backendBaseUrl || "http://127.0.0.1:8000";
  const form = document.getElementById("ranking-form");
  const timeframeSelect = document.getElementById("ranking-timeframe");
  const serverSelect = document.getElementById("ranking-server");
  const metricSelect = document.getElementById("ranking-metric");
  const limitSelect = document.getElementById("ranking-limit");
  const yearWrap = document.getElementById("ranking-year-wrap");
  const yearInput = document.getElementById("ranking-year");
  const backendStateNode = document.getElementById("ranking-backend-state");
  const stateNode = document.getElementById("ranking-state");
  const titleNode = document.getElementById("ranking-title");
  const metaNode = document.getElementById("ranking-meta");
  const tableNode = document.getElementById("ranking-table");
  const tableBodyNode = document.getElementById("ranking-table-body");
  const emptyNode = document.getElementById("ranking-empty");

  const currentYear = new Date().getUTCFullYear();
  let isBackendOnline = false;

  if (yearInput) {
    yearInput.value = String(currentYear);
  }

  toggleYearField();
  setBackendState("Comprobando disponibilidad del backend", false);
  setRankingState("neutral", "Esperando filtros para cargar el ranking global.");
  clearRankingSurface();
  refreshBackendHealth();

  if (timeframeSelect) {
    timeframeSelect.addEventListener("change", () => {
      toggleYearField();
      void loadRanking();
    });
  }

  [serverSelect, metricSelect, limitSelect].forEach((node) => {
    if (!node) {
      return;
    }
    node.addEventListener("change", () => {
      void loadRanking();
    });
  });

  if (form) {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      void loadRanking();
    });
  }

  function setBackendState(label, online) {
    isBackendOnline = online;
    if (!backendStateNode) {
      return;
    }
    backendStateNode.textContent = label;
    backendStateNode.classList.toggle("status-chip--ok", online);
    backendStateNode.classList.toggle("status-chip--fallback", !online);
  }

  function setRankingState(state, message) {
    if (!stateNode) {
      return;
    }
    stateNode.textContent = message;
    stateNode.className = `stats-state stats-state--${state}`;
  }

  function toggleYearField() {
    const isAnnual = timeframeSelect?.value === "annual";
    if (yearWrap) {
      yearWrap.hidden = !isAnnual;
    }
    if (yearInput) {
      yearInput.disabled = !isAnnual;
    }
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

  async function refreshBackendHealth() {
    try {
      const response = await fetch(`${backendBaseUrl}/health`);
      if (!response.ok) {
        throw new Error(`Health request failed with ${response.status}`);
      }
      const payload = await response.json();
      if (!payload || payload.status !== "ok") {
        throw new Error("Unexpected health payload");
      }
      setBackendState("Backend operativo", true);
      setRankingState("neutral", "Backend disponible. Ajusta filtros o usa la lectura inicial.");
      void loadRanking();
    } catch (error) {
      console.warn("Ranking health check failed", error);
      setBackendState("Backend no disponible", false);
      setRankingState("error", "Backend no disponible. El ranking queda en estado offline.");
      renderEmptyState(
        "No fue posible contactar el backend. Cuando vuelva a estar disponible podras consultar semanal, mensual o anual.",
      );
    }
  }

  async function loadRanking() {
    const timeframe = String(timeframeSelect?.value || "weekly");
    const serverId = String(serverSelect?.value || "all");
    const metric = String(metricSelect?.value || "kills");
    const limit = String(limitSelect?.value || "20");

    if (!isBackendOnline) {
      setRankingState("error", "Backend no disponible. El ranking queda en estado offline.");
      renderEmptyState(
        "No fue posible contactar el backend. Reintenta cuando el servicio vuelva a estar operativo.",
      );
      return;
    }

    let year = null;
    if (timeframe === "annual") {
      year = Number.parseInt(String(yearInput?.value || "").trim(), 10);
      if (!Number.isFinite(year) || year <= 0) {
        setRankingState("error", "El ano solicitado no es valido.");
        renderEmptyState("Corrige el ano y vuelve a consultar el ranking anual.");
        return;
      }
    }

    setRankingState("loading", "Cargando ranking global...");
    clearRankingSurface();

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

      const response = await fetch(`${backendBaseUrl}/api/ranking?${searchParams.toString()}`);
      if (!response.ok) {
        const errorPayload = await safeParseJson(response);
        const errorMessage = String(errorPayload?.message || errorPayload?.detail || "").toLowerCase();
        handleRequestError(response.status, errorMessage, timeframe);
        return;
      }

      const payload = await response.json();
      if (!payload || payload.status !== "ok") {
        throw new Error(payload?.message || "Respuesta de ranking invalida");
      }

      renderRanking(payload.data || {});
    } catch (error) {
      console.warn("Ranking request failed", error);
      setBackendState("Backend no disponible", false);
      setRankingState("error", "Error controlado al cargar el ranking.");
      renderEmptyState(
        "La lectura del ranking fallo en este intento. Revisa el backend o actualiza la pagina.",
      );
    }
  }

  function handleRequestError(statusCode, errorMessage, timeframe) {
    const normalizedMessage = String(errorMessage || "");
    if (statusCode === 400 && normalizedMessage.includes("metric")) {
      setRankingState("warning", "La metrica solicitada no esta soportada en V1.");
      renderEmptyState(
        "Solo la metrica kills esta disponible en esta primera version del ranking global.",
      );
      return;
    }
    if (statusCode === 400 && normalizedMessage.includes("year")) {
      setRankingState("warning", "El ranking anual requiere un ano valido.");
      renderEmptyState("Define un ano valido para consultar la lectura anual.");
      return;
    }
    if (statusCode === 400 && normalizedMessage.includes("timeframe")) {
      setRankingState("warning", "El periodo solicitado no esta soportado.");
      renderEmptyState("Usa una ventana semanal, mensual o anual.");
      return;
    }
    if (timeframe === "annual") {
      setRankingState("error", "Error controlado al cargar el ranking anual.");
    } else {
      setRankingState("error", "Error controlado al cargar el ranking.");
    }
    renderEmptyState(
      "La consulta devolvio un error controlado. Ajusta los filtros y vuelve a intentarlo.",
    );
  }

  function renderRanking(data) {
    const items = Array.isArray(data.items) ? data.items : [];
    const timeframe = String(data.timeframe || "weekly");
    const serverId = String(data.server_id || "all");
    const metric = String(data.metric || "kills");
    const snapshotStatus = String(data.snapshot_status || "").toLowerCase();

    if (titleNode) {
      titleNode.textContent =
        timeframe === "annual" ? "Top anual activo" : "Tabla activa del alcance seleccionado";
    }

    if (metaNode) {
      metaNode.innerHTML = buildMetaMarkup(data);
    }

    if (timeframe === "annual" && snapshotStatus === "missing") {
      setRankingState("warning", "El snapshot anual solicitado aun no fue generado.");
      renderEmptyState(
        "No existe snapshot anual para el ano y servidor elegidos. Este estado es informativo y no implica caida del backend.",
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
          : "No se encontraron jugadores con actividad suficiente en esta ventana.",
      );
      return;
    }

    setRankingState(
      "ready",
      `Ranking ${labelForTimeframe(timeframe)} listo para ${labelForServer(serverId)} por ${metric}.`,
    );

    if (tableBodyNode) {
      tableBodyNode.innerHTML = items.map(renderRow).join("");
    }
    if (tableNode) {
      tableNode.hidden = false;
    }
    if (emptyNode) {
      emptyNode.hidden = true;
    }
  }

  function buildMetaMarkup(data) {
    const source = data.source && typeof data.source === "object" ? data.source : {};
    const parts = [
      `<article class="ranking-meta-card"><p>Servidor</p><strong>${escapeHtml(labelForServer(data.server_id))}</strong></article>`,
      `<article class="ranking-meta-card"><p>Ventana</p><strong>${escapeHtml(labelForWindow(data))}</strong></article>`,
      `<article class="ranking-meta-card"><p>Fuente</p><strong>${escapeHtml(String(source.read_model || "No disponible"))}</strong></article>`,
      `<article class="ranking-meta-card"><p>Actualizado</p><strong>${escapeHtml(formatDateTime(source.generated_at))}</strong></article>`,
    ];

    if (String(data.timeframe || "") === "annual") {
      parts.push(
        `<article class="ranking-meta-card"><p>Snapshot</p><strong>${escapeHtml(String(data.snapshot_status || "missing"))}</strong></article>`,
      );
    }

    return parts.join("");
  }

  function renderRow(item) {
    return `
      <tr>
        <td>#${safeInt(item.ranking_position, 0)}</td>
        <td>
          <div class="ranking-player">
            <strong>${escapeHtml(String(item.player_name || "Jugador sin nombre"))}</strong>
            <span>${escapeHtml(String(item.player_id || "Sin ID"))}</span>
          </div>
        </td>
        <td>${safeInt(item.metric_value, 0)}</td>
        <td>${safeInt(item.matches_considered, 0)}</td>
        <td>${safeInt(item.deaths, 0)}</td>
        <td>${safeInt(item.teamkills, 0)}</td>
        <td>${safeDecimal(item.kd_ratio, 2, "0.00")}</td>
      </tr>
    `;
  }

  function labelForWindow(data) {
    if (String(data.timeframe || "") === "annual") {
      return `Ano ${safeInt(data.year, currentYear)}`;
    }
    return String(data.window_label || data.window_kind || "Ventana activa");
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

  function safeInt(value, fallback) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) {
      return fallback;
    }
    return parsed;
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
