document.addEventListener("DOMContentLoaded", () => {
  const backendBaseUrl = document.body.dataset.backendBaseUrl || "http://127.0.0.1:8000";
  const searchForm = document.getElementById("stats-search-form");
  const searchInput = document.getElementById("stats-search-input");
  const searchSubmitButton = document.getElementById("stats-search-submit");
  const searchStateNode = document.getElementById("stats-search-state");
  const searchHelpNode = document.getElementById("stats-search-help");
  const resultListNode = document.getElementById("stats-result-list");
  const profilePanel = document.getElementById("stats-profile-panel");
  const profileTitle = document.getElementById("stats-profile-title");
  const profileStateNode = document.getElementById("stats-profile-state");
  const profileLinksBarNode = document.getElementById("stats-profile-links-bar");
  const comparisonGrid = document.getElementById("stats-comparison-grid");
  const summaryGrid = document.getElementById("stats-summary-grid");
  const weeklySummaryNode = document.getElementById("stats-weekly-summary");
  const monthlySummaryNode = document.getElementById("stats-monthly-summary");
  const annualStateNode = document.getElementById("stats-annual-state");
  const annualContentNode = document.getElementById("stats-annual-content");

  const annualDefaultYear = 2026;
  const minimumSearchQueryLength = 4;
  const annualMetric = "kills";
  const annualMetricSupportedOnly = "kills";
  const annualLimit = 20;
  const annualServerId = "all";
  const externalProfileBrands = Object.freeze({
    steam: Object.freeze({
      label: "Steam",
      logoSrc: "./assets/img/brands/steam.png",
    }),
    hellor: Object.freeze({
      label: "Hellor",
      logoSrc: "./assets/img/brands/hllor.webp",
    }),
    hll_records: Object.freeze({
      label: "HLL Records",
      logoSrc: "./assets/img/brands/hllrecords.png",
    }),
    helo: Object.freeze({
      label: "Helo",
      logoSrc: "./assets/img/brands/helo-system.png",
    }),
  });

  const messages = {
    backendUnavailableForSearch:
      "Servicio no disponible. No se pueden buscar jugadores ni cargar su perfil.",
    backendUnavailableForAnnual:
      "Servicio no disponible. No se puede consultar el ranking anual.",
    searchNoInput: "Introduce al menos 4 caracteres para buscar un jugador.",
    searchLoading: "Buscando jugadores...",
    searchEmpty: "Sin resultados. Prueba con otro texto o ID.",
    searchError:
      "Error al buscar jugadores. Intentalo de nuevo en unos segundos.",
    searchReadyPrefix: "Se encontraron ",
    searchReadySuffix:
      " jugador(es). Selecciona uno para ver sus estad\u00edsticas.",
    searchShortQueryHelp:
      "Introduce al menos 4 caracteres para buscar un jugador.",
    profileLoading: "Cargando estad\u00edsticas personales...",
    profileNoStats:
      "Todavia no hay estadisticas suficientes para este jugador.",
    profileError: "No fue posible cargar las estad\u00edsticas del jugador.",
    annualLoading: "Cargando ranking anual...",
    annualMissing:
      "Todavia no hay ranking anual publicado para el a\u00f1o solicitado.",
    annualReadyEmpty:
      "El ranking anual ya esta disponible, pero no muestra filas para ese filtro.",
    annualUnsupportedMetric:
      "La m\u00e9trica anual solicitada no est\u00e1 soportada en V1.",
    annualMetricInvalid:
      "Par\u00e1metro de ranking anual inv\u00e1lido. Usa metric=kills en V1.",
    annualReadyPrefix: "Ranking anual disponible para",
    weeklyPlaceholder:
      "Sin datos semanales. El ranking semanal se actualiza al cargar un jugador.",
    monthlyPlaceholder:
      "Sin datos mensuales. El ranking mensual se actualiza al cargar un jugador.",
    weeklyWindowUnavailable:
      "No se pudieron cargar los datos semanales; se muestran los datos mensuales.",
    monthlyWindowUnavailable:
      "No se pudieron cargar los datos mensuales; se muestran los datos semanales.",
    weeklyWindowUnavailableSummary:
      "Resumen semanal no disponible temporalmente.",
    monthlyWindowUnavailableSummary:
      "Resumen mensual no disponible temporalmente.",
    profileReadyTitle: "Perfil personal",
    profileEmptyTitle: "Selecciona un jugador para ver sus estad\u00edsticas.",
    partialProfileLoadWarning:
      "Algunas lecturas no se cargaron; se mantienen las disponibles.",
  };

  let isBackendOnline = false;

  if (searchHelpNode) {
    searchHelpNode.textContent =
      "Usa al menos 4 caracteres para encontrar un jugador. Al seleccionar uno ver\u00e1s resumen semanal y mensual. " +
      "El ranking anual visible corresponde a la temporada 2026.";
  }

  clearProfilePanel(false);
  syncSearchFormState();
  refreshBackendHealth();

  if (searchForm && searchInput) {
    searchInput.addEventListener("input", () => {
      syncSearchFormState();
    });

    searchForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const query = (searchInput.value || "").trim();
      if (!isValidSearchQuery(query)) {
        syncSearchFormState();
        return;
      }
      void searchPlayers(query);
    });
  }

  function markAsBackendUnavailable() {
    isBackendOnline = false;
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
    const normalizedMessage = String(message || "").trim();
    searchStateNode.hidden = !normalizedMessage;
    if (!normalizedMessage) {
      searchStateNode.textContent = "";
      searchStateNode.className = "stats-state stats-state--neutral";
      return;
    }
    searchStateNode.textContent = normalizedMessage;
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
    if (profileLinksBarNode) {
      profileLinksBarNode.innerHTML = "";
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

      isBackendOnline = true;
      setAnnualState(
        "neutral",
        "Servicio disponible. Cargando ranking anual 2026.",
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
    if (!isValidSearchQuery(query)) {
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
          const playerName = button.getAttribute("data-player-name");
          if (playerId) {
            void loadPlayerProfile(playerId, playerName);
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
    if (!annualContentNode) {
      return;
    }
    if (!isBackendOnline) {
      markAsBackendUnavailable();
      return;
    }

    const year = annualDefaultYear;

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

  function renderAnnualRanking(data) {
    if (!annualContentNode || !annualStateNode) {
      return;
    }

    const snapshotStatus = String(data.snapshot_status || "").toLowerCase();
    const items = normalizeArray(data.items);
    const limit = safeInt(data.limit, 0);
    const serverId = String(data.server_id || annualServerId);
    const serverLabel = labelForStatsServer(serverId);
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
      `${messages.annualReadyPrefix} ${serverLabel}, a\u00f1o ${year}.`,
    );

    annualContentNode.innerHTML = `
      <article class="stats-annual-card">
        <p class="stats-summary-title">Top ${limit} anual</p>
        <div class="stats-annual-meta">
          <article class="stats-annual-meta-item">
            <p>Servidor</p>
            <strong>${escapeHtml(serverLabel)}</strong>
          </article>
          <article class="stats-annual-meta-item">
            <p>A\u00f1o</p>
            <strong>${year}</strong>
          </article>
          <article class="stats-annual-meta-item">
            <p>Lectura</p>
            <strong>${escapeHtml(metric)}</strong>
          </article>
          <article class="stats-annual-meta-item">
            <p>Partidas base</p>
            <strong>${safeInt(sourceMatches, 0)}</strong>
          </article>
          <article class="stats-annual-meta-item">
            <p>Actualizado</p>
            <strong>${escapeHtml(generatedAt || "No disponible")}</strong>
          </article>
        </div>
        ${renderAnnualRows(items)}
      </article>
    `;
  }

  function renderAnnualRows(items) {
    const rowsMarkup = items
      .map((item) => {
        const rank = safeInt(item.ranking_position, 0);
        const playerName = escapeHtml(resolveVisiblePlayerName(item.player_name, null, null));
        const matches = safeInt(item.matches_considered, 0);
        const kills = safeInt(firstFiniteValue(item.kills, item.metric_value), 0);
        const killsPerMatch = formatKillsPerMatch(
          item.kills_per_match,
          kills,
          matches,
        );
        const deaths = safeInt(item.deaths, 0);
        const teamkills = safeInt(item.teamkills, 0);
        const kd = safeDecimal(item.kd_ratio, 2, "0.00");

        return `
          <tr>
            <td class="stats-annual-rank">#${rank}</td>
            <td>
              <div class="stats-annual-player">
                <strong>${playerName}</strong>
              </div>
            </td>
            <td>${matches}</td>
            <td class="stats-annual-metric">${kills}</td>
            <td>${deaths}</td>
            <td>${teamkills}</td>
            <td>${kd}</td>
            <td>${killsPerMatch}</td>
          </tr>
        `;
      })
      .join("");

    return `
      <div class="stats-annual-table-shell">
        <table class="stats-annual-table">
          <thead>
            <tr>
              <th>Posici\u00f3n</th>
              <th>Jugador</th>
              <th>Partidas</th>
              <th>Kills</th>
              <th>Muertes</th>
              <th>TK</th>
              <th>KD</th>
              <th>Kills/partida</th>
            </tr>
          </thead>
          <tbody>${rowsMarkup}</tbody>
        </table>
      </div>
    `;
  }

  function renderResultItem(item) {
    const playerId = escapeHtml(String(item.player_id || ""));
    const playerName = escapeHtml(resolveVisiblePlayerName(item.player_name, null, null));
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
          data-player-name="${playerName}"
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

  async function loadPlayerProfile(playerId, selectedPlayerName = "") {
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
      const playerName = resolveVisiblePlayerName(
        weeklyData?.player_name || monthlyData?.player_name,
        selectedPlayerName,
        searchInput?.value,
      );
      const profileIdentityData =
        weeklyData?.player_id || weeklyData?.external_profile_links
          ? weeklyData
          : monthlyData;
      const hasWeeklyStats = Number(weeklyData?.matches_considered || 0) > 0;
      const hasMonthlyStats = Number(monthlyData?.matches_considered || 0) > 0;
      const hasStats = hasWeeklyStats || hasMonthlyStats;
      const partialLoadWarning = weeklyFailed || monthlyFailed;

      profileStateNode.textContent = hasStats
        ? playerName
        : messages.profileNoStats;
      profileStateNode.className = hasStats
        ? "stats-state stats-state--neutral"
        : "stats-state stats-state--warning";

      summaryGrid.innerHTML = renderProfileSummaryCards({
        playerName,
        profileIdentityData,
        weeklyData,
        monthlyData,
        weeklyFailed,
        monthlyFailed,
      });
      if (profileLinksBarNode) {
        profileLinksBarNode.innerHTML = renderStatsExternalProfilesBar(
          profileIdentityData,
          externalProfileBrands,
        );
      }

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
      if (profileLinksBarNode) {
        profileLinksBarNode.innerHTML = "";
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
            <p><strong>Muertes:</strong> ${safeInt(weeklyData?.deaths, 0)}</p>
            <p><strong>TK:</strong> ${safeInt(weeklyData?.teamkills, 0)}</p>
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
            <p><strong>Muertes:</strong> ${safeInt(monthlyData?.deaths, 0)}</p>
            <p><strong>TK:</strong> ${safeInt(monthlyData?.teamkills, 0)}</p>
          </article>
        `;

    return `
      <article class="stats-summary-card">
        <p class="stats-summary-title">Identidad</p>
        <p><strong>Jugador:</strong> ${escapeHtml(playerName)}</p>
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
    const kpmMetric = renderStatsKpmMetric(data);

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
            <span class="stats-comparison-card__metric-label">Muertes</span>
            <span class="stats-comparison-card__metric-value">${deaths}</span>
          </div>
          <div class="stats-comparison-card__metric">
            <span class="stats-comparison-card__metric-label">KD</span>
            <span class="stats-comparison-card__metric-value">${kdRatio}</span>
          </div>
          ${kpmMetric}
        </div>
        <p class="stats-comparison-card__detail">
          <strong>Kills/partida:</strong> ${killsPerMatch}
        </p>
        <p class="stats-comparison-card__note">${escapeHtml(rankingState.detail)}</p>
      </article>
    `;
  }

  function renderDeltaComparisonCard(weeklyData, monthlyData) {
    const weeklyKillsPerMatch = safeParseNumber(weeklyData?.kills_per_match);
    const monthlyKillsPerMatch = safeParseNumber(monthlyData?.kills_per_match);
    const weeklyKd = safeParseNumber(weeklyData?.kd_ratio);
    const monthlyKd = safeParseNumber(monthlyData?.kd_ratio);
    const weeklyKpm = safeParseNumber(weeklyData?.kpm);
    const monthlyKpm = safeParseNumber(monthlyData?.kpm);
    const hasReadyKpm =
      weeklyData?.kpm_status === "ready" &&
      monthlyData?.kpm_status === "ready" &&
      Number.isFinite(weeklyKpm) &&
      Number.isFinite(monthlyKpm);
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
            <span class="stats-comparison-card__metric-label">Kills/partida semanal</span>
            <span class="stats-comparison-card__metric-value">${safeDecimal(weeklyKillsPerMatch, 2, "0.00")}</span>
          </div>
          <div class="stats-comparison-card__metric">
            <span class="stats-comparison-card__metric-label">Kills/partida mensual</span>
            <span class="stats-comparison-card__metric-value">${safeDecimal(monthlyKillsPerMatch, 2, "0.00")}</span>
          </div>
          <div class="stats-comparison-card__metric">
            <span class="stats-comparison-card__metric-label">KD semanal</span>
            <span class="stats-comparison-card__metric-value">${safeDecimal(weeklyKd, 2, "0.00")}</span>
          </div>
          <div class="stats-comparison-card__metric">
            <span class="stats-comparison-card__metric-label">KD mensual</span>
            <span class="stats-comparison-card__metric-value">${safeDecimal(monthlyKd, 2, "0.00")}</span>
          </div>
          ${
            hasReadyKpm
              ? `
                <div class="stats-comparison-card__metric">
                  <span class="stats-comparison-card__metric-label">KPM semanal</span>
                  <span class="stats-comparison-card__metric-value">${safeDecimal(weeklyKpm, 2, "0.00")}</span>
                </div>
                <div class="stats-comparison-card__metric">
                  <span class="stats-comparison-card__metric-label">KPM mensual</span>
                  <span class="stats-comparison-card__metric-value">${safeDecimal(monthlyKpm, 2, "0.00")}</span>
                </div>
              `
              : ""
          }
        </div>
        <p class="stats-comparison-card__detail">
          <strong>Delta de kills:</strong> ${formatSignedNumber(killsDelta)}
        </p>
        <p class="stats-comparison-card__detail">
          <strong>Delta de partidas:</strong> ${formatSignedNumber(matchesDelta)}
        </p>
        <p class="stats-comparison-card__note">
          Comparativa basada en los datos disponibles actualmente.
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
    const metric = escapeHtml(labelForStatsMetric(ranking.metric || annualMetric));

    return `
      <p><strong>Posici\u00f3n:</strong> ${rank}</p>
      <p><strong>M\u00e9trica:</strong> ${metric}</p>
      <p>${escapeHtml(formatWindowRange(ranking))}</p>
    `;
  }

  function describeRankingState(ranking, matchesConsidered, timeframeLabel, requestFailed = false) {
    const matches = safeInt(matchesConsidered, 0);
    const label = String(timeframeLabel || "ranking").toLowerCase();
    if (requestFailed) {
      return {
        tone: "warning",
        title: "Datos no disponibles",
        detail: `No fue posible cargar los datos de la ventana ${label} en este intento.`,
      };
    }

    if (!ranking) {
      return {
        tone: "error",
        title: "Sin posicion",
        detail: `Aun no hay datos de la ventana ${label} suficientes para calcular su posicion.`,
      };
    }

    if (Number.isFinite(safeParseNumber(ranking.ranking_position))) {
      return {
        tone: "ok",
        title: `Posici\u00f3n #${safeInt(ranking.ranking_position, 0)}`,
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
    const windowLabel = labelForStatsWindowKind(ranking?.window_kind);
    const windowStart = formatDateTime(ranking?.window_start);
    const windowEnd = formatDateTime(ranking?.window_end);
    if (windowLabel) {
      return `${windowLabel}: ${windowStart} - ${windowEnd}`;
    }
    return `Ventana: ${windowStart} - ${windowEnd}`;
  }

  function labelForStatsMetric(metric) {
    const labels = {
      kills: "Kills",
      deaths: "Muertes",
      teamkills: "TK",
      matches_considered: "Partidas",
      kd_ratio: "KD",
      kills_per_match: "Kills/partida",
    };
    return labels[String(metric || "").trim()] || "Kills";
  }

  function resolveVisiblePlayerName(primaryName, selectedName, queryText) {
    const candidates = [primaryName, selectedName, queryText];
    for (const candidate of candidates) {
      const normalized = String(candidate || "").trim();
      if (isDisplayablePlayerName(normalized)) {
        return normalized;
      }
    }
    return "Jugador seleccionado";
  }

  function isDisplayablePlayerName(value) {
    if (!value) {
      return false;
    }
    if (/^\d{17}$/.test(value)) {
      return false;
    }
    if (/^[0-9a-f]{32}$/i.test(value)) {
      return false;
    }
    return true;
  }

  function labelForStatsWindowKind(windowKind) {
    const labels = {
      "current-week": "Semana actual",
      "current-month": "Mes actual",
      "previous-closed-week-fallback": "Semana cerrada anterior",
      "previous-closed-month-fallback": "Mes cerrado anterior",
      "previous-week": "Semana anterior",
      "previous-month": "Mes anterior",
    };
    const normalized = String(windowKind || "").trim();
    return labels[normalized] || normalized;
  }

  function renderStatsKpmMetric(data) {
    if (data?.kpm_status !== "ready") {
      return "";
    }
    const kpmValue = safeParseNumber(data?.kpm);
    if (!Number.isFinite(kpmValue)) {
      return "";
    }
    return `
      <div class="stats-comparison-card__metric">
        <span class="stats-comparison-card__metric-label">KPM</span>
        <span class="stats-comparison-card__metric-value">${safeDecimal(kpmValue, 2, "0.00")}</span>
      </div>
    `;
  }

  function renderStatsExternalProfilesBar(profileData, brands) {
    const links = resolveStatsExternalProfileLinks(profileData, brands);
    if (!links.length) {
      return "";
    }
    return `
      <div class="stats-profile-links-strip">
        <span class="stats-profile-links-strip__label">Perfiles externos</span>
        <div class="stats-profile-links" aria-label="Perfiles externos">
          ${links
            .map(
              ({ href, label, logoSrc }) => `
                <a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">
                  ${
                    logoSrc
                      ? `<img class="stats-profile-links__brand" src="${escapeHtml(logoSrc)}" alt="" aria-hidden="true" decoding="async" loading="lazy" onerror="this.remove();" />`
                      : ""
                  }
                  <span>${escapeHtml(label)}</span>
                </a>
              `,
            )
            .join("")}
        </div>
      </div>
    `;
  }

  function resolveStatsExternalProfileLinks(profileData, brands) {
    const links = [];
    const fallbackLinks = buildFallbackExternalProfileLinks(profileData);
    const payloadLinks =
      profileData?.external_profile_links && typeof profileData.external_profile_links === "object"
        ? profileData.external_profile_links
        : {};
    const candidateLinks = {
      ...fallbackLinks,
      ...payloadLinks,
    };
    ["steam", "hellor", "hll_records", "helo"].forEach((key) => {
      const href = candidateLinks?.[key];
      if (typeof href !== "string" || !href.trim()) {
        return;
      }
      const brand = brands[key];
      links.push({
        href,
        label: brand?.label || key,
        logoSrc: brand?.logoSrc || "",
      });
    });
    return links;
  }

  function buildFallbackExternalProfileLinks(profileData) {
    const playerId = String(profileData?.player_id || "").trim();
    const steamId = String(profileData?.steam_id_64 || playerId).trim();
    if (/^\d{17}$/.test(steamId)) {
      return {
        steam: `https://steamcommunity.com/profiles/${steamId}`,
        hellor: `https://hellor.pro/player/${steamId}`,
        hll_records: `https://hllrecords.com/profiles/${steamId}`,
        helo: `https://helo-system.de/statistics/players/${steamId}?series=2024`,
      };
    }
    const epicId = String(profileData?.epic_id || playerId).trim().toLowerCase();
    if (/^[0-9a-f]{32}$/i.test(epicId)) {
      return {
        hellor: `https://hellor.pro/player/${epicId}`,
        hll_records: `https://hllrecords.com/profiles/${epicId}`,
      };
    }
    return {};
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

  function firstFiniteValue(...values) {
    for (const value of values) {
      const parsed = Number(value);
      if (Number.isFinite(parsed)) {
        return parsed;
      }
    }
    return Number.NaN;
  }

  function formatKillsPerMatch(rawKillsPerMatch, rawKills, rawMatches) {
    const directValue = safeParseNumber(rawKillsPerMatch);
    if (Number.isFinite(directValue)) {
      return safeDecimal(directValue, 2, "0.00");
    }

    const kills = safeParseNumber(rawKills);
    const matches = safeParseNumber(rawMatches);
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

  function normalizeArray(items) {
    return Array.isArray(items) ? items : [];
  }

  function isValidSearchQuery(query) {
    return String(query || "").trim().length >= minimumSearchQueryLength;
  }

  function syncSearchFormState() {
    const query = String(searchInput?.value || "").trim();
    const isValid = isValidSearchQuery(query);

    if (searchSubmitButton) {
      searchSubmitButton.disabled = !isValid;
    }

    if (!searchStateNode) {
      return;
    }

    if (!query) {
      setSearchState("neutral", "");
      return;
    }

    if (!isValid) {
      setSearchState("warning", messages.searchShortQueryHelp);
    }
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function labelForStatsServer(serverId) {
    const normalized = String(serverId || "").trim().toLowerCase();
    if (normalized === "comunidad-hispana-01") {
      return "Comunidad Hispana #01";
    }
    if (normalized === "comunidad-hispana-02") {
      return "Comunidad Hispana #02";
    }
    if (normalized === "all" || normalized === "all-servers") {
      return "Todos los servidores";
    }
    return String(serverId || "Todos los servidores");
  }
});

