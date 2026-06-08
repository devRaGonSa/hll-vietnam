document.addEventListener("DOMContentLoaded", () => {
  const backendBaseUrl = document.body.dataset.backendBaseUrl || "http://127.0.0.1:8000";
  const searchForm = document.getElementById("stats-search-form");
  const searchInput = document.getElementById("stats-search-input");
  const searchStateNode = document.getElementById("stats-search-state");
  const searchHelpNode = document.getElementById("stats-search-help");
  const resultListNode = document.getElementById("stats-result-list");
  const backendStateNode = document.getElementById("stats-backend-state");
  const profilePanel = document.getElementById("stats-profile-panel");
  const profileTitle = document.getElementById("stats-profile-title");
  const profileStateNode = document.getElementById("stats-profile-state");
  const summaryGrid = document.getElementById("stats-summary-grid");
  const weeklySummaryNode = document.getElementById("stats-weekly-summary");
  const monthlySummaryNode = document.getElementById("stats-monthly-summary");

  let isBackendOnline = false;

  setBackendState("Comprobando disponibilidad del backend", false);
  refreshBackendHealth();

  if (searchForm && searchInput) {
    searchForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const query = (searchInput.value || "").trim();
      if (!query) {
        setSearchState("error", "Escribe un nombre o ID para buscar.");
        return;
      }
      void searchPlayers(query);
    });
  }

  function setBackendState(label, isOnline) {
    isBackendOnline = isOnline;
    if (!backendStateNode) {
      return;
    }
    backendStateNode.textContent = label;
    backendStateNode.classList.toggle("status-chip--ok", isOnline);
    backendStateNode.classList.toggle("status-chip--fallback", !isOnline);
  }

  function markAsBackendUnavailable() {
    setBackendState("Backend no disponible", false);
    if (searchStateNode) {
      searchStateNode.textContent = "Backend no disponible. Reintenta en unos segundos.";
      searchStateNode.className = "stats-state stats-state--error";
    }
  }

  async function refreshBackendHealth() {
    try {
      const response = await fetch(`${backendBaseUrl}/health`);
      if (!response.ok) {
        throw new Error(`Health request failed with ${response.status}`);
      }
      const payload = await response.json();
      if (payload && payload.status === "ok") {
        setBackendState("Backend operativo", true);
        return;
      }
      throw new Error("Unexpected health payload");
    } catch (error) {
      markAsBackendUnavailable();
      console.warn("Backend health check failed", error);
    }
  }

  async function searchPlayers(query) {
    if (!resultListNode) {
      return;
    }

    if (!isBackendOnline) {
      markAsBackendUnavailable();
      return;
    }

    setSearchState("loading", "Buscando jugadores...");
    clearProfilePanel();
    resultListNode.innerHTML = "";

    try {
      const searchResponse = await fetch(
        `${backendBaseUrl}/api/stats/players/search?q=${encodeURIComponent(query)}`,
      );
      if (!searchResponse.ok) {
        throw new Error(`Search request failed with ${searchResponse.status}`);
      }

      const payload = await searchResponse.json();
      if (!payload || payload.status !== "ok") {
        throw new Error(payload?.message || "Respuesta de búsqueda inválida");
      }

      const items = normalizeArray(payload.data?.items);
      if (!items.length) {
        setSearchState("empty", "Sin resultados.");
        return;
      }

      setSearchState("ready", `Se encontraron ${items.length} jugadores.`);
      resultListNode.innerHTML = items.map(renderResultItem).join("");
      resultListNode.querySelectorAll("[data-player-id]").forEach((button) => {
        button.addEventListener("click", () => {
          const playerId = button.getAttribute("data-player-id");
          if (playerId) {
            void loadPlayerProfile(playerId);
          }
        });
      });
    } catch (error) {
      console.warn("Player search failed", error);
      markAsBackendUnavailable();
      setSearchState("error", "Error al buscar. Verifica backend y reintenta.");
    }
  }

  function renderResultItem(item) {
    const playerId = escapeHtml(String(item.player_id || ""));
    const playerName = escapeHtml(String(item.player_name || "Jugador sin nombre"));
    const matches = Number.isFinite(Number(item.matches_considered))
      ? Number(item.matches_considered)
      : 0;
    const lastSeen = formatDateTime(item.last_seen_at);
    const serversSeen = Array.isArray(item.servers_seen)
      ? item.servers_seen
          .filter(Boolean)
          .map((server) => escapeHtml(String(server)))
          .join(", ")
      : "";

    return `
      <article class="stats-result-item">
        <button class="stats-result-item__button" type="button" data-player-id="${playerId}">
          <div class="stats-result-item__main">
            <p class="stats-result-item__name">${playerName}</p>
            <p class="stats-result-item__meta">ID: ${playerId}</p>
          </div>
          <p class="stats-result-item__metrics">
            Partidas: ${matches} · Última aparición: ${lastSeen}
          </p>
          ${serversSeen ? `<p class="stats-result-item__meta">Servidores: ${serversSeen}</p>` : ""}
        </button>
      </article>
    `;
  }

  async function loadPlayerProfile(playerId) {
    if (!isBackendOnline) {
      markAsBackendUnavailable();
      return;
    }

    setProfileState("loading", "Cargando estadísticas personales...");
    clearProfilePanel();

    try {
      const response = await fetch(
        `${backendBaseUrl}/api/stats/players/${encodeURIComponent(playerId)}?timeframe=weekly`,
      );
      if (!response.ok) {
        throw new Error(`Profile request failed with ${response.status}`);
      }

      const payload = await response.json();
      if (!payload || payload.status !== "ok") {
        throw new Error(payload?.message || "Respuesta de perfil inválida");
      }

      const data = payload.data || {};
      profilePanel.hidden = false;
      profileTitle.textContent = `Perfil personal`;
      const playerName = String(data.player_name || "Sin nombre");
      const playerIdText = String(data.player_id || playerId);
      const hasStats = Number(data.matches_considered || 0) > 0;

      profileStateNode.textContent = hasStats
        ? `${playerName} (${playerIdText})`
        : `Jugador sin estadísticas registradas: ${playerName} (${playerIdText})`;
      profileStateNode.className = hasStats
        ? "stats-state stats-state--neutral"
        : "stats-state stats-state--warning";

      summaryGrid.innerHTML = `
        <article class="stats-summary-card">
          <p class="stats-summary-title">Identidad</p>
          <p><strong>Jugador:</strong> ${escapeHtml(playerName)}</p>
          <p><strong>ID:</strong> ${escapeHtml(playerIdText)}</p>
          <p><strong>Partidas:</strong> ${safeInt(data.matches_considered, 0)}</p>
        </article>
        <article class="stats-summary-card">
          <p class="stats-summary-title">Totales</p>
          <p><strong>Kills:</strong> ${safeInt(data.kills, 0)}</p>
          <p><strong>Deaths:</strong> ${safeInt(data.deaths, 0)}</p>
          <p><strong>Teamkills:</strong> ${safeInt(data.teamkills, 0)}</p>
        </article>
        <article class="stats-summary-card">
          <p class="stats-summary-title">Ratios</p>
          <p><strong>K/D:</strong> ${safeDecimal(data.kd_ratio, 2, "0.00")}</p>
          <p><strong>Kills/partida:</strong> ${safeDecimal(data.kills_per_match, 2, "0.00")}</p>
          <p><strong>Deaths/partida:</strong> ${safeDecimal(data.deaths_per_match, 2, "0.00")}</p>
        </article>
      `;

      weeklySummaryNode.innerHTML = formatRankingSummary(
        data.weekly_ranking,
        "Semanal",
      );
      monthlySummaryNode.innerHTML = formatRankingSummary(
        data.monthly_ranking,
        "Mensual",
      );

      setBackendState("Backend operativo", true);
      isBackendOnline = true;
    } catch (error) {
      console.warn("Player profile failed", error);
      markAsBackendUnavailable();
      profilePanel.hidden = false;
      profileTitle.textContent = "Perfil personal";
      profileStateNode.textContent = "No fue posible cargar las estadísticas del jugador.";
      profileStateNode.className = "stats-state stats-state--error";
      summaryGrid.innerHTML = "";
      weeklySummaryNode.textContent = "Sin datos de semana disponibles.";
      monthlySummaryNode.textContent = "Sin datos de mes disponibles.";
    }
  }

  function setSearchState(state, message) {
    if (!searchStateNode) {
      return;
    }
    searchStateNode.textContent = message;
    searchStateNode.className = `stats-state stats-state--${state}`;
  }

  function setProfileState(state, message) {
    if (!profileStateNode || !profilePanel) {
      return;
    }
    profilePanel.hidden = false;
    profileStateNode.textContent = message;
    profileStateNode.className = `stats-state stats-state--${state}`;
    summaryGrid.innerHTML = "";
    weeklySummaryNode.textContent = "Cargando...";
    monthlySummaryNode.textContent = "Cargando...";
  }

  function clearProfilePanel() {
    if (!profilePanel || !summaryGrid || !profileStateNode) {
      return;
    }
    profilePanel.hidden = true;
    summaryGrid.innerHTML = "";
    if (weeklySummaryNode) {
      weeklySummaryNode.textContent = "Sin datos de semana disponibles.";
    }
    if (monthlySummaryNode) {
      monthlySummaryNode.textContent = "Sin datos de mes disponibles.";
    }
    profileStateNode.textContent = "Selecciona un jugador para ver sus estadisticas.";
    profileStateNode.className = "stats-state stats-state--neutral";
  }

  function formatRankingSummary(ranking, timeframeLabel) {
    if (!ranking || !Number.isFinite(safeParseNumber(ranking.ranking_position))) {
      return `Sin ranking ${timeframeLabel} registrado para este jugador.`;
    }

    const rank = safeInt(ranking.ranking_position, 0);
    const metric = escapeHtml(String(ranking.metric || "kills"));
    const windowLabel = escapeHtml(String(ranking.window_kind || ""));
    const windowStart = formatDateTime(ranking.window_start);
    const windowEnd = formatDateTime(ranking.window_end);
    const windowRange = windowLabel
      ? `${windowLabel}: ${windowStart} - ${windowEnd}`
      : `Ventana: ${windowStart} - ${windowEnd}`;

    return `
      <p><strong>Posición:</strong> ${rank}</p>
      <p><strong>Metric:</strong> ${metric}</p>
      <p>${windowRange}</p>
    `;
  }

  function safeInt(value, fallback = 0) {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) {
      return fallback;
    }
    return parsed;
  }

  function safeDecimal(value, maximumFractionDigits, fallback = "0") {
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) {
      return fallback;
    }
    return parsed.toLocaleString("es-ES", {
      minimumFractionDigits: maximumFractionDigits,
      maximumFractionDigits,
    });
  }

  function safeParseNumber(value) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : Number.NaN;
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

  function normalizeArray(items) {
    return Array.isArray(items) ? items : [];
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

