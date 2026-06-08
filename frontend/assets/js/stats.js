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
  const comparisonGrid = document.getElementById("stats-comparison-grid");
  const summaryGrid = document.getElementById("stats-summary-grid");
  const weeklySummaryNode = document.getElementById("stats-weekly-summary");
  const monthlySummaryNode = document.getElementById("stats-monthly-summary");
  const annualForm = document.getElementById("stats-annual-form");
  const annualYearInput = document.getElementById("stats-annual-year");
  const annualStateNode = document.getElementById("stats-annual-state");
  const annualContentNode = document.getElementById("stats-annual-content");

  const annualDefaultYear = new Date().getUTCFullYear();
  const annualMetric = "kills";
  const annualMetricSupportedOnly = "kills";
  const annualLimit = 20;
  const annualServerId = "all";

  const messages = {
    backendChecking: "Comprobando disponibilidad del backend",
    backendOnline: "Backend operativo",
    backendUnavailable: "Backend no disponible. Reintenta en unos segundos.",
    backendUnavailableForSearch:
      "Backend no disponible. No se pueden buscar jugadores ni cargar su perfil.",
    backendUnavailableForAnnual:
      "Backend no disponible. No se puede consultar el ranking anual.",
    searchNoInput: "Escribe un nombre o ID para buscar.",
    searchLoading: "Buscando jugadores...",
    searchEmpty: "Sin resultados. Prueba con otro texto o ID.",
    searchError:
      "Error al buscar jugadores. Verifica backend y reintenta.",
    searchReadyPrefix: "Se encontraron ",
    searchReadySuffix:
      " jugador(es). Selecciona uno para ver sus estadisticas.",
    searchShortQueryHelp:
      "Usa al menos 1 caracter para iniciar la busqueda.",
    profileLoading: "Cargando estadisticas personales...",
    profileNoStats:
      "Jugador sin estadisticas suficientes para mostrar datos personales.",
    profileError: "No fue posible cargar las estadisticas del jugador.",
    annualLoading: "Cargando ranking anual...",
    annualMissing:
      "No hay snapshot generado para el ano solicitado. Mostrara estado missing hasta que exista.",
    annualReadyEmpty:
      "Snapshot anual listo pero sin datos para el ano y servidor seleccionado.",
    annualUnsupportedMetric:
      "La metrica anual solicitada no esta soportada en V1.",
    annualMetricInvalid:
      "Parametro de ranking anual invalido. Usa metric=kills en V1.",
    annualReadyPrefix: "Ranking anual listo para",
    weeklyPlaceholder:
      "Sin datos semanales. El ranking semanal se actualiza al cargar un jugador.",
    monthlyPlaceholder:
      "Sin datos mensuales. El ranking mensual se actualiza al cargar un jugador.",
    weeklyWindowUnavailable:
      "No se pudo cargar el bloque semanal; se muestran los datos mensuales.",
    monthlyWindowUnavailable:
      "No se pudo cargar el bloque mensual; se muestran los datos semanales.",
    weeklyWindowUnavailableSummary:
      "Resumen semanal no disponible temporalmente.",
    monthlyWindowUnavailableSummary:
      "Resumen mensual no disponible temporalmente.",
    profileReadyTitle: "Perfil personal",
    profileEmptyTitle: "Selecciona un jugador para ver sus estadisticas.",
    partialProfileLoadWarning:
      "Algunos bloques de ranking no se cargaron; se mantienen los disponibles.",
  };

  let isBackendOnline = false;

  if (searchHelpNode) {
    searchHelpNode.textContent =
      "Usa el buscador para encontrar un jugador. Al seleccionar uno veras resumen semanal y mensual. " +
      "El ranking anual se consulta por separado con el ano indicado.";
  }

  setBackendState(messages.backendChecking, false);
  if (annualYearInput) {
    annualYearInput.value = String(annualDefaultYear);
  }
  clearProfilePanel(false);
  refreshBackendHealth();

  if (annualForm && annualYearInput) {
    annualForm.addEventListener("submit", (event) => {
      event.preventDefault();
      void loadAnnualRanking();
    });
  }

  if (searchForm && searchInput) {
    searchForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const query = (searchInput.value || "").trim();
      if (!query) {
        setSearchState("error", messages.searchNoInput);
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
    setBackendState(messages.backendUnavailable, false);
    if (searchStateNode) {
      searchStateNode.textContent = messages.backendUnavailableForSearch;
      searchStateNode.className = "stats-state stats-state--error";
    }
    setAnnualState("error", messages.backendUnavailableForAnnual);
  }

  function setSearchState(state, message) {
    if (!searchStateNode) {
      return;
    }
    searchStateNode.textContent = message;
    searchStateNode.className = `stats-state stats-state--${state}`;
  }

  function setAnnualState(state, message) {
    if (!annualStateNode) {
      return;
    }
    annualStateNode.textContent = message;
    annualStateNode.className = `stats-state stats-state--${state}`;
  }

  function setProfileState(state, message) {
    if (!profileStateNode || !profilePanel) {
      return;
    }
    profilePanel.hidden = false;
    profileStateNode.textContent = message;
    profileStateNode.className = `stats-state stats-state--${state}`;
    if (comparisonGrid) {
      comparisonGrid.innerHTML = "";
    }
    summaryGrid.innerHTML = "";
    if (weeklySummaryNode) {
      weeklySummaryNode.textContent = "Cargando ...";
    }
    if (monthlySummaryNode) {
      monthlySummaryNode.textContent = "Cargando ...";
    }
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

      setBackendState(messages.backendOnline, true);
      setAnnualState(
        "neutral",
        "Backend disponible. Selecciona un ano para cargar el ranking anual (kills).",
      );
      void loadAnnualRanking();
    } catch (error) {
      markAsBackendUnavailable();
      console.warn("Backend health check failed", error);
    }
  }

  async function searchPlayers(query) {
    if (!resultListNode) {
      return;
    }
    if (!query) {
      setSearchState("error", messages.searchShortQueryHelp);
      return;
    }
    if (!isBackendOnline) {
      markAsBackendUnavailable();
      return;
    }

    setSearchState("loading", messages.searchLoading);
    clearProfilePanel(true);
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
        throw new Error(payload?.message || "Respuesta de busqueda invalida");
      }

      const items = normalizeArray(payload.data?.items);
      if (!items.length) {
        setSearchState("empty", messages.searchEmpty);
        return;
      }

      setSearchState(
        "ready",
        `${messages.searchReadyPrefix}${items.length}${messages.searchReadySuffix}`,
      );
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
      setSearchState("error", messages.searchError);
    }
  }

  async function loadAnnualRanking() {
    if (!annualForm || !annualYearInput || !annualContentNode) {
      return;
    }
    if (!isBackendOnline) {
      markAsBackendUnavailable();
      return;
    }

    const year = resolveAnnualYear();
    if (year === null) {
      setAnnualState("error", "El ano ingresado no es valido.");
      return;
    }

    setAnnualState("loading", messages.annualLoading);
    annualContentNode.innerHTML = "";

    try {
      const annualUrl =
        `${backendBaseUrl}/api/stats/rankings/annual?` +
        `year=${encodeURIComponent(year)}&` +
        `server_id=${encodeURIComponent(annualServerId)}&` +
        `metric=${encodeURIComponent(annualMetric)}&` +
        `limit=${encodeURIComponent(annualLimit)}`;

      const annualResponse = await fetch(annualUrl);
      if (!annualResponse.ok) {
        const annualErrorPayload = await safeParseJson(annualResponse);
        const annualErrorMessage = String(
          annualErrorPayload?.message || annualErrorPayload?.detail || "",
        ).toLowerCase();

        if (isAnnualMetricUnsupportedError(annualResponse.status, annualErrorMessage)) {
          setAnnualState("warning", messages.annualUnsupportedMetric);
          return;
        }

        if (annualResponse.status === 400 && annualErrorMessage.includes("metric")) {
          setAnnualState("warning", messages.annualMetricInvalid);
          return;
        }

        throw new Error(`Annual ranking request failed with ${annualResponse.status}`);
      }

      const payload = await annualResponse.json();
      if (!payload || payload.status !== "ok") {
        throw new Error(payload?.message || "Respuesta de ranking anual invalida");
      }

      renderAnnualRanking(payload.data || {});
    } catch (error) {
      console.warn("Annual ranking failed", error);
      markAsBackendUnavailable();
      setAnnualState("error", "Error al cargar ranking anual.");
      annualContentNode.innerHTML = "";
    }
  }

  function isAnnualMetricUnsupportedError(statusCode, message) {
    const normalized = String(message || "").toLowerCase();
    return (
      statusCode === 400 &&
      normalized.includes("metric") &&
      normalized.includes("unsupported") &&
      annualMetric.toLowerCase() === annualMetricSupportedOnly
    );
  }

  function resolveAnnualYear() {
    const normalized = Number.parseInt(String(annualYearInput?.value || "").trim(), 10);
    if (!Number.isFinite(normalized) || normalized <= 0) {
      return null;
    }
    return normalized;
  }

  function renderAnnualRanking(data) {
    if (!annualContentNode || !annualStateNode) {
      return;
    }

    const snapshotStatus = String(data.snapshot_status || "").toLowerCase();
    const items = normalizeArray(data.items);
    const limit = safeInt(data.limit, 0);
    const serverId = String(data.server_id || annualServerId);
    const sourceMatches = safeInt(data.source_matches_count, 0);
    const generatedAt = formatDateTime(data.generated_at);
    const year = safeInt(data.year, annualDefaultYear);
    const metric = escapeHtml(String(data.metric || annualMetric));

    if (snapshotStatus !== "ready" || !items.length) {
      const isReadyButEmpty = snapshotStatus === "ready" && !items.length;
      setAnnualState(
        "neutral",
        isReadyButEmpty ? messages.annualReadyEmpty : messages.annualMissing,
      );
      annualContentNode.innerHTML = "";
      return;
    }

    setAnnualState(
      "neutral",
      `${messages.annualReadyPrefix} ${serverId}, ano ${year}, metrica ${metric}`,
    );

    annualContentNode.innerHTML = `
      <article class="stats-summary-card">
        <p class="stats-summary-title">Top ${limit} anual</p>
        <div class="stats-annual-meta">
          <p><strong>Servidor:</strong> ${escapeHtml(serverId)}</p>
          <p><strong>Metrica:</strong> ${escapeHtml(metric)}</p>
          <p><strong>Partidas fuente:</strong> ${safeInt(sourceMatches, 0)}</p>
          <p><strong>Actualizado:</strong> ${escapeHtml(generatedAt || "No disponible")}</p>
        </div>
        ${renderAnnualRows(items)}
      </article>
    `;
  }

  function renderAnnualRows(items) {
    return items
      .map((item) => {
        const rank = safeInt(item.ranking_position, 0);
        const playerId = escapeHtml(String(item.player_id || ""));
        const playerName = escapeHtml(String(item.player_name || "Jugador sin nombre"));
        const metricValue = safeInt(item.metric_value, 0);
        const matches = safeInt(item.matches_considered, 0);
        const kills = safeInt(item.kills, 0);
        const deaths = safeInt(item.deaths, 0);
        const teamkills = safeInt(item.teamkills, 0);
        const kd = safeDecimal(item.kd_ratio, 2, "0.00");

        return `
          <article class="stats-annual-item">
            <p><strong>#${rank}</strong> ${playerName} <span class="stats-annual-sub">(ID: ${playerId})</span></p>
            <p><strong>Valor:</strong> ${metricValue} - <strong>Partidas:</strong> ${matches}</p>
            <p><strong>Kills:</strong> ${kills} - <strong>Deaths:</strong> ${deaths} - <strong>Teamkills:</strong> ${teamkills} - <strong>K/D:</strong> ${kd}</p>
          </article>
        `;
      })
      .join("");
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
        <button
          class="stats-result-item__button"
          type="button"
          data-player-id="${playerId}"
          aria-label="Cargar perfil de ${playerName}"
        >
          <div class="stats-result-item__main">
            <p class="stats-result-item__name">${playerName}</p>
            <p class="stats-result-item__meta">ID: ${playerId}</p>
          </div>
          <p class="stats-result-item__metrics">
            Partidas: ${matches} - Ultima aparicion: ${lastSeen}
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

    setProfileState("loading", messages.profileLoading);
    if (!profilePanel) {
      return;
    }

    try {
      const [weeklyProfileResult, monthlyProfileResult] = await Promise.allSettled([
        fetchPlayerProfile(playerId, "weekly"),
        fetchPlayerProfile(playerId, "monthly"),
      ]);

      const weeklyData =
        weeklyProfileResult.status === "fulfilled" ? weeklyProfileResult.value : null;
      const monthlyData =
        monthlyProfileResult.status === "fulfilled" ? monthlyProfileResult.value : null;
      const weeklyFailed = weeklyProfileResult.status === "rejected";
      const monthlyFailed = monthlyProfileResult.status === "rejected";

      if (!weeklyData && !monthlyData) {
        throw new Error("Both weekly and monthly profile windows failed.");
      }

      profilePanel.hidden = false;
      profileTitle.textContent = messages.profileReadyTitle;
      const playerName = String(
        (weeklyData?.player_name || monthlyData?.player_name || "Sin nombre"),
      );
      const playerIdText = String(weeklyData?.player_id || monthlyData?.player_id || playerId);
      const hasWeeklyStats = Number(weeklyData?.matches_considered || 0) > 0;
      const hasMonthlyStats = Number(monthlyData?.matches_considered || 0) > 0;
      const hasStats = hasWeeklyStats || hasMonthlyStats;
      const partialLoadWarning = weeklyFailed || monthlyFailed;

      profileStateNode.textContent = hasStats
        ? `${playerName} (${playerIdText})`
        : `${messages.profileNoStats} (${playerIdText})`;
      profileStateNode.className = hasStats
        ? "stats-state stats-state--neutral"
        : "stats-state stats-state--warning";

      summaryGrid.innerHTML = renderProfileSummaryCards({
        playerName,
        playerIdText,
        weeklyData,
        monthlyData,
        weeklyFailed,
        monthlyFailed,
      });

      if (partialLoadWarning) {
        profileStateNode.textContent += ` ${messages.partialProfileLoadWarning}`;
      }

      if (comparisonGrid) {
        comparisonGrid.innerHTML = renderComparisonCards({
          weeklyData,
          weeklyFailed,
          monthlyData,
          monthlyFailed,
        });
      }

      if (weeklySummaryNode) {
        weeklySummaryNode.innerHTML = weeklyFailed
          ? `<p>${escapeHtml(messages.weeklyWindowUnavailableSummary)}</p>`
          : formatRankingSummary(
              weeklyData?.weekly_ranking,
              "Semanal",
              weeklyData?.matches_considered,
            );
      }
      if (monthlySummaryNode) {
        monthlySummaryNode.innerHTML = monthlyFailed
          ? `<p>${escapeHtml(messages.monthlyWindowUnavailableSummary)}</p>`
          : formatRankingSummary(
              monthlyData?.monthly_ranking,
              "Mensual",
              monthlyData?.matches_considered,
            );
      }

      setBackendState(messages.backendOnline, true);
      isBackendOnline = true;
    } catch (error) {
      console.warn("Player profile failed", error);
      markAsBackendUnavailable();
      if (profilePanel) {
        profilePanel.hidden = false;
      }
      profileTitle.textContent = messages.profileReadyTitle;
      profileStateNode.textContent = messages.profileError;
      profileStateNode.className = "stats-state stats-state--error";
      if (comparisonGrid) {
        comparisonGrid.innerHTML = "";
      }
      summaryGrid.innerHTML = "";
      if (weeklySummaryNode) {
        weeklySummaryNode.textContent = messages.weeklyPlaceholder;
      }
      if (monthlySummaryNode) {
        monthlySummaryNode.textContent = messages.monthlyPlaceholder;
      }
    }
  }

  function renderProfileSummaryCards({
    playerName,
    playerIdText,
    weeklyData,
    monthlyData,
    weeklyFailed,
    monthlyFailed,
  }) {
    const weeklySummary = weeklyFailed
      ? `
          <article class="stats-summary-card">
            <p class="stats-summary-title">Ventana semanal</p>
            <p>${escapeHtml(messages.weeklyWindowUnavailable)}</p>
          </article>
        `
      : `
          <article class="stats-summary-card">
            <p class="stats-summary-title">Ventana semanal</p>
            <p><strong>Kills:</strong> ${safeInt(weeklyData?.kills, 0)}</p>
            <p><strong>Deaths:</strong> ${safeInt(weeklyData?.deaths, 0)}</p>
            <p><strong>Teamkills:</strong> ${safeInt(weeklyData?.teamkills, 0)}</p>
          </article>
        `;

    const monthlySummary = monthlyFailed
      ? `
          <article class="stats-summary-card">
            <p class="stats-summary-title">Ventana mensual</p>
            <p>${escapeHtml(messages.monthlyWindowUnavailable)}</p>
          </article>
        `
      : `
          <article class="stats-summary-card">
            <p class="stats-summary-title">Ventana mensual</p>
            <p><strong>Kills:</strong> ${safeInt(monthlyData?.kills, 0)}</p>
            <p><strong>Deaths:</strong> ${safeInt(monthlyData?.deaths, 0)}</p>
            <p><strong>Teamkills:</strong> ${safeInt(monthlyData?.teamkills, 0)}</p>
          </article>
        `;

    return `
      <article class="stats-summary-card">
        <p class="stats-summary-title">Identidad</p>
        <p><strong>Jugador:</strong> ${escapeHtml(playerName)}</p>
        <p><strong>ID:</strong> ${escapeHtml(playerIdText)}</p>
        <p><strong>Partidas semanales:</strong> ${safeInt(weeklyData?.matches_considered, 0)}</p>
        <p><strong>Partidas mensuales:</strong> ${safeInt(monthlyData?.matches_considered, 0)}</p>
      </article>
      ${weeklySummary}
      ${monthlySummary}
    `;
  }

  function clearProfilePanel(openPanel) {
    if (!profilePanel || !summaryGrid || !profileStateNode) {
      return;
    }
    if (openPanel) {
      profilePanel.hidden = true;
    }
    if (comparisonGrid) {
      comparisonGrid.innerHTML = "";
    }
    summaryGrid.innerHTML = "";
    if (weeklySummaryNode) {
      weeklySummaryNode.textContent = messages.weeklyPlaceholder;
    }
    if (monthlySummaryNode) {
      monthlySummaryNode.textContent = messages.monthlyPlaceholder;
    }
    profileStateNode.textContent = messages.profileEmptyTitle;
    profileStateNode.className = "stats-state stats-state--neutral";
  }

  async function fetchPlayerProfile(playerId, timeframe) {
    const response = await fetch(
      `${backendBaseUrl}/api/stats/players/${encodeURIComponent(playerId)}?timeframe=${encodeURIComponent(timeframe)}`,
    );
    if (!response.ok) {
      throw new Error(`Profile request failed with ${response.status}`);
    }

    const payload = await response.json();
    if (!payload || payload.status !== "ok") {
      throw new Error(payload?.message || "Respuesta de perfil invalida");
    }

    return payload.data || {};
  }

  function renderComparisonCards({
    weeklyData,
    weeklyFailed,
    monthlyData,
    monthlyFailed,
  }) {
    const cards = [
      renderWindowComparisonCard(
        "Semanal",
        weeklyData,
        weeklyData?.weekly_ranking,
        weeklyFailed,
      ),
      renderWindowComparisonCard(
        "Mensual",
        monthlyData,
        monthlyData?.monthly_ranking,
        monthlyFailed,
      ),
    ];

    if (!weeklyFailed && !monthlyFailed) {
      cards.push(renderDeltaComparisonCard(weeklyData, monthlyData));
    }
    return cards.join("");
  }

  function renderWindowComparisonCard(label, data, ranking, failed) {
    const rankingState = describeRankingState(ranking, data?.matches_considered, label, failed);
    const matches = safeInt(data?.matches_considered, 0);
    const kills = safeInt(data?.kills, 0);
    const deaths = safeInt(data?.deaths, 0);
    const kdRatio = safeDecimal(data?.kd_ratio, 2, "0.00");
    const killsPerMatch = safeDecimal(data?.kills_per_match, 2, "0.00");

    return `
      <article class="stats-comparison-card">
        <p class="stats-comparison-card__eyebrow">Comparativa ${label.toLowerCase()}</p>
        <h3 class="stats-comparison-card__title">Ventana ${label.toLowerCase()}</h3>
        <span class="stats-comparison-card__badge stats-comparison-card__badge--${rankingState.tone}">
          ${escapeHtml(rankingState.title)}
        </span>
        <div class="stats-comparison-card__grid">
          <div class="stats-comparison-card__metric">
            <span class="stats-comparison-card__metric-label">Partidas</span>
            <span class="stats-comparison-card__metric-value">${matches}</span>
          </div>
          <div class="stats-comparison-card__metric">
            <span class="stats-comparison-card__metric-label">Kills</span>
            <span class="stats-comparison-card__metric-value">${kills}</span>
          </div>
          <div class="stats-comparison-card__metric">
            <span class="stats-comparison-card__metric-label">Deaths</span>
            <span class="stats-comparison-card__metric-value">${deaths}</span>
          </div>
          <div class="stats-comparison-card__metric">
            <span class="stats-comparison-card__metric-label">K/D</span>
            <span class="stats-comparison-card__metric-value">${kdRatio}</span>
          </div>
        </div>
        <p class="stats-comparison-card__detail">
          <strong>Kills por partida:</strong> ${killsPerMatch}
        </p>
        <p class="stats-comparison-card__note">${escapeHtml(rankingState.detail)}</p>
      </article>
    `;
  }

  function renderDeltaComparisonCard(weeklyData, monthlyData) {
    const weeklyKpm = safeParseNumber(weeklyData?.kills_per_match);
    const monthlyKpm = safeParseNumber(monthlyData?.kills_per_match);
    const weeklyKd = safeParseNumber(weeklyData?.kd_ratio);
    const monthlyKd = safeParseNumber(monthlyData?.kd_ratio);
    const killsDelta = safeInt(monthlyData?.kills, 0) - safeInt(weeklyData?.kills, 0);
    const matchesDelta =
      safeInt(monthlyData?.matches_considered, 0) - safeInt(weeklyData?.matches_considered, 0);

    return `
      <article class="stats-comparison-card">
        <p class="stats-comparison-card__eyebrow">Lectura comparada</p>
        <h3 class="stats-comparison-card__title">Pulso semanal vs mensual</h3>
        <span class="stats-comparison-card__badge stats-comparison-card__badge--ok">
          ${escapeHtml(buildDeltaHeadline(killsDelta, matchesDelta))}
        </span>
        <div class="stats-comparison-card__grid">
          <div class="stats-comparison-card__metric">
            <span class="stats-comparison-card__metric-label">KPM semanal</span>
            <span class="stats-comparison-card__metric-value">${safeDecimal(weeklyKpm, 2, "0.00")}</span>
          </div>
          <div class="stats-comparison-card__metric">
            <span class="stats-comparison-card__metric-label">KPM mensual</span>
            <span class="stats-comparison-card__metric-value">${safeDecimal(monthlyKpm, 2, "0.00")}</span>
          </div>
          <div class="stats-comparison-card__metric">
            <span class="stats-comparison-card__metric-label">K/D semanal</span>
            <span class="stats-comparison-card__metric-value">${safeDecimal(weeklyKd, 2, "0.00")}</span>
          </div>
          <div class="stats-comparison-card__metric">
            <span class="stats-comparison-card__metric-label">K/D mensual</span>
            <span class="stats-comparison-card__metric-value">${safeDecimal(monthlyKd, 2, "0.00")}</span>
          </div>
        </div>
        <p class="stats-comparison-card__detail">
          <strong>Delta de kills:</strong> ${formatSignedNumber(killsDelta)}
        </p>
        <p class="stats-comparison-card__detail">
          <strong>Delta de partidas:</strong> ${formatSignedNumber(matchesDelta)}
        </p>
        <p class="stats-comparison-card__note">
          La lectura compara solo datos existentes del backend actual, sin recalcular rankings ni pedir nuevos endpoints.
        </p>
      </article>
    `;
  }

  function formatRankingSummary(ranking, timeframeLabel, matchesConsidered) {
    const rankingState = describeRankingState(ranking, matchesConsidered, timeframeLabel);
    if (!ranking) {
      return escapeHtml(rankingState.detail);
    }

    if (!Number.isFinite(safeParseNumber(ranking.ranking_position))) {
      return `
        <p><strong>Estado:</strong> ${escapeHtml(rankingState.title)}</p>
        <p>${escapeHtml(rankingState.detail)}</p>
        <p>${escapeHtml(formatWindowRange(ranking))}</p>
      `;
    }

    const rank = safeInt(ranking.ranking_position, 0);
    const metric = escapeHtml(String(ranking.metric || annualMetric));

    return `
      <p><strong>Posicion:</strong> ${rank}</p>
      <p><strong>Metric:</strong> ${metric}</p>
      <p>${escapeHtml(formatWindowRange(ranking))}</p>
    `;
  }

  function describeRankingState(ranking, matchesConsidered, timeframeLabel, requestFailed = false) {
    const matches = safeInt(matchesConsidered, 0);
    const label = String(timeframeLabel || "ranking").toLowerCase();
    if (requestFailed) {
      return {
        tone: "warning",
        title: "Bloque no disponible",
        detail: `No fue posible cargar los datos de la ventana ${label} en este intento.`,
      };
    }

    if (!ranking) {
      return {
        tone: "error",
        title: "Ranking ausente",
        detail: `No se recibio bloque de ranking ${label} desde el backend.`,
      };
    }

    if (Number.isFinite(safeParseNumber(ranking.ranking_position))) {
      return {
        tone: "ok",
        title: `Posicion #${safeInt(ranking.ranking_position, 0)}`,
        detail: `Jugador posicionado en el ranking ${label} activo por kills.`,
      };
    }

    if (matches <= 0) {
      return {
        tone: "warning",
        title: "Sin actividad",
        detail: `No hay actividad cerrada del jugador en la ventana ${label} actual.`,
      };
    }

    const windowKind = String(ranking.window_kind || "").toLowerCase();
    if (windowKind.startsWith("previous-")) {
      return {
        tone: "warning",
        title: "Profundidad insuficiente",
        detail: `La ventana ${label} activa usa fallback previo y el jugador no aparece posicionado.`,
      };
    }

    return {
      tone: "warning",
      title: "Fuera del ranking visible",
      detail: `El jugador tiene actividad en la ventana ${label}, pero no figura en el ranking visible actual.`,
    };
  }

  function buildDeltaHeadline(killsDelta, matchesDelta) {
    if (killsDelta === 0 && matchesDelta === 0) {
      return "Ritmo estable";
    }
    if (killsDelta > 0 || matchesDelta > 0) {
      return "Presion mensual superior";
    }
    return "Ventana corta mas intensa";
  }

  function formatSignedNumber(value) {
    const parsed = safeInt(value, 0);
    if (parsed > 0) {
      return `+${parsed}`;
    }
    return String(parsed);
  }

  function formatWindowRange(ranking) {
    const windowLabel = String(ranking?.window_kind || "").trim();
    const windowStart = formatDateTime(ranking?.window_start);
    const windowEnd = formatDateTime(ranking?.window_end);
    if (windowLabel) {
      return `${windowLabel}: ${windowStart} - ${windowEnd}`;
    }
    return `Ventana: ${windowStart} - ${windowEnd}`;
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
