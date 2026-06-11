document.addEventListener("DOMContentLoaded", () => {
  const backendBaseUrl = resolveBackendBaseUrl();
  const params = new URLSearchParams(window.location.search);
  const serverSlug = params.get("server") || "";
  const matchId = params.get("match") || "";
  const nodes = {
    title: document.getElementById("match-detail-title"),
    summary: document.getElementById("match-detail-summary"),
    note: document.getElementById("match-detail-note"),
    state: document.getElementById("match-detail-state"),
    grid: document.getElementById("match-detail-grid"),
    actions: document.getElementById("match-detail-actions"),
    playersSection: document.getElementById("match-detail-players-section"),
    playersNote: document.getElementById("match-detail-players-note"),
    playersState: document.getElementById("match-detail-players-state"),
    playerControls: document.getElementById("match-detail-player-controls"),
    playerSearch: document.getElementById("match-detail-player-search"),
    playerTeamFilters: [...document.querySelectorAll('input[name="match-detail-player-team-filter"]')],
    playerSort: document.getElementById("match-detail-player-sort"),
    playerSortDirection: document.getElementById("match-detail-player-sort-direction"),
    playersTableShell: document.getElementById("match-detail-players-table-shell"),
    playersBody: document.getElementById("match-detail-players-body"),
    timelineSection: document.getElementById("match-detail-timeline-section"),
    timelineNote: document.getElementById("match-detail-timeline-note"),
    timelineState: document.getElementById("match-detail-timeline-state"),
    timelineGrid: document.getElementById("match-detail-timeline-grid"),
    mapHero: document.getElementById("match-detail-map-hero"),
    mapImage: document.getElementById("match-detail-map-image"),
  };

  if (!serverSlug || !matchId) {
    nodes.title.textContent = "Partida no seleccionada";
    nodes.summary.textContent = "Vuelve al historico y abre una partida registrada.";
    nodes.note.textContent = "";
    setState(nodes.state, "No hay una partida seleccionada.", true);
    return;
  }

  void loadMatchDetail({ backendBaseUrl, serverSlug, matchId, nodes });
});

const EXTERNAL_PROFILE_BRANDS = Object.freeze({
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
  steam: Object.freeze({
    label: "Steam",
    logoSrc: "",
  }),
});

async function loadMatchDetail({ backendBaseUrl, serverSlug, matchId, nodes }) {
  try {
    const payload = await fetchJson(
      `${backendBaseUrl}/api/historical/matches/detail?server=${encodeURIComponent(
        serverSlug,
      )}&match=${encodeURIComponent(matchId)}`,
    );
    const data = payload?.data;
    const item = data?.item;
    if (!data?.found || !item) {
      nodes.title.textContent = "Detalle no disponible";
      nodes.summary.textContent =
        "La partida existe como enlace interno, pero todavia no hay detalle suficiente para mostrar.";
      nodes.note.textContent = "";
      setState(nodes.state, "Detalle no disponible para esta partida.");
      return;
    }

    renderMatchDetail(item, nodes);
  } catch (error) {
    nodes.title.textContent = "Detalle no disponible";
    nodes.summary.textContent = "No se pudo cargar el detalle desde el backend.";
    nodes.note.textContent = "";
    setState(nodes.state, "Error al cargar el detalle de la partida.", true);
  }
}

function resolveBackendBaseUrl() {
  const bodyBackendBaseUrl = document.body.dataset.backendBaseUrl;
  if (typeof bodyBackendBaseUrl === "string" && bodyBackendBaseUrl.trim()) {
    return trimTrailingSlash(bodyBackendBaseUrl);
  }

  const configuredBackendBaseUrl = window.HLL_FRONTEND_CONFIG?.backendBaseUrl;
  if (
    typeof configuredBackendBaseUrl === "string" &&
    configuredBackendBaseUrl.trim()
  ) {
    return trimTrailingSlash(configuredBackendBaseUrl);
  }

  return "";
}

function trimTrailingSlash(value) {
  return String(value || "").trim().replace(/\/+$/, "");
}

function renderMatchDetail(item, nodes) {
  const mapName = item.map?.pretty_name || item.map?.name || "Mapa no disponible";
  const serverName = item.server?.name || item.server?.slug || "Servidor no disponible";
  nodes.title.textContent = mapName;
  nodes.summary.textContent = serverName;
  nodes.note.textContent = "";
  renderMapHero(item, mapName, nodes);
  nodes.grid.innerHTML = renderScoreboardDetail(item, { mapName, serverName });
  renderPlayerSection(item, nodes);
  hideTimelineSection(nodes);
  renderActions(item, nodes.actions);
  nodes.state.hidden = true;
  nodes.grid.hidden = false;
}

function renderMapHero(item, mapName, nodes) {
  if (!nodes.mapHero || !nodes.mapImage) {
    return;
  }

  const mapImagePath = resolveMapImagePath(item, mapName);
  if (!mapImagePath) {
    nodes.mapImage.removeAttribute("src");
    nodes.mapImage.alt = "";
    nodes.mapHero.hidden = true;
    return;
  }

  nodes.mapImage.src = mapImagePath;
  nodes.mapImage.alt = mapName;
  nodes.mapImage.onerror = () => {
    nodes.mapImage.removeAttribute("src");
    nodes.mapHero.hidden = true;
  };
  nodes.mapHero.hidden = false;
}

function renderScoreboardDetail(item, { mapName, serverName }) {
  const result = item.result || {};
  const alliedScore = Number.isFinite(Number(result.allied_score))
    ? formatNumber(result.allied_score)
    : "-";
  const axisScore = Number.isFinite(Number(result.axis_score))
    ? formatNumber(result.axis_score)
    : "-";
  const winner = String(item.winner || result.winner || "").toLowerCase();
  const isAlliedWinner = winner === "allies" || winner === "allied";
  const isAxisWinner = winner === "axis";
  const factions = resolveMatchFactions(item, mapName);
  const metadata = [
    ["Servidor", serverName],
    ["Mapa", mapName],
    ["Modo", formatGameMode(item.game_mode || item.gamestate?.game_mode)],
    ["Duracion", formatDuration(item.duration_seconds)],
    ["Inicio", formatMatchTimestamp(item, "start")],
  ];
  if (item.ended_at) {
    metadata.push(["Fin", formatMatchTimestamp(item, "end")]);
  }

  return `
    <section class="historical-scoreboard-layout" aria-label="Resumen de marcador de la partida">
      <div class="historical-scoreboard-layout__main">
        ${renderScoreboardSide({
          sideClass: "historical-scoreboard-side--allied",
          emblem: factions.allied.emblem,
          sideLabel: "Aliados",
          factionLabel: factions.allied.label,
          isWinner: isAlliedWinner,
        })}
        <div class="historical-scoreboard-center">
          <span class="historical-scoreboard-center__timer">${escapeHtml(formatDuration(item.duration_seconds))}</span>
          <strong class="historical-scoreboard-center__score">${escapeHtml(alliedScore)} : ${escapeHtml(axisScore)}</strong>
          <span class="historical-scoreboard-center__map">${escapeHtml(mapName)}</span>
          <span class="historical-scoreboard-center__mode">${escapeHtml(formatGameMode(item.game_mode || item.gamestate?.game_mode))}</span>
          <span class="historical-scoreboard-center__winner">${escapeHtml(formatWinner(winner))}</span>
        </div>
        ${renderScoreboardSide({
          sideClass: "historical-scoreboard-side--axis",
          emblem: factions.axis.emblem,
          sideLabel: "Eje",
          factionLabel: factions.axis.label,
          isWinner: isAxisWinner,
        })}
      </div>
      <div class="historical-scoreboard-layout__meta">
        ${metadata.map(([label, value]) => renderCompactMeta(label, value)).join("")}
      </div>
    </section>
  `;
}

function renderScoreboardSide({ sideClass, emblem, sideLabel, factionLabel, isWinner }) {
  const fallbackLabel = factionLabel || sideLabel;
  return `
    <div class="historical-scoreboard-side ${sideClass} ${isWinner ? "is-winner" : ""}">
      <img
        class="historical-scoreboard-side__emblem"
        src="${escapeHtml(emblem)}"
        alt="${escapeHtml(fallbackLabel)}"
        width="128"
        height="128"
        loading="lazy"
        decoding="async"
        onerror="this.hidden = true; this.closest('.historical-scoreboard-side').classList.add('is-emblem-missing');"
      />
      <div class="historical-scoreboard-side__text">
        <strong>${escapeHtml(sideLabel)}</strong>
        ${isWinner ? "<em>Ganador</em>" : ""}
      </div>
    </div>
  `;
}

function renderCompactMeta(label, value) {
  return `
    <article>
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value || "No disponible")}</strong>
    </article>
  `;
}

function hideTimelineSection(nodes) {
  if (!nodes.timelineSection) {
    return;
  }
  nodes.timelineSection.hidden = true;
  nodes.timelineNote.textContent = "";
  nodes.timelineState.hidden = true;
  nodes.timelineGrid.hidden = true;
  nodes.timelineGrid.innerHTML = "";
}

function renderPlayerSection(item, nodes) {
  const players = Array.isArray(item.players) ? item.players : [];
  nodes.playersSection.hidden = false;
  if (players.length === 0) {
    nodes.playersNote.textContent =
      "Esta partida no tiene estadisticas por jugador disponibles en el detalle interno.";
    setState(
      nodes.playersState,
      "No hay filas de jugador registradas para esta partida.",
    );
    nodes.playerControls.hidden = true;
    nodes.playersTableShell.hidden = true;
    nodes.playersBody.innerHTML = "";
    return;
  }

  const state = {
    search: "",
    team: "all",
    sort: "kills",
    direction: "desc",
    isDefaultSort: true,
  };
  const renderRows = () => renderPlayerTable(item, players, state, nodes);

  nodes.playerSearch.value = "";
  nodes.playerTeamFilters.forEach((control) => {
    control.checked = control.value === state.team;
  });
  nodes.playerSort.value = state.sort;
  nodes.playerSortDirection.value = state.direction;
  bindPlayerTableControls(nodes, state, renderRows);
  renderRows();
  nodes.playerControls.hidden = false;
  nodes.playersTableShell.hidden = false;
}

function bindPlayerTableControls(nodes, state, renderRows) {
  nodes.playerControls.onsubmit = (event) => {
    event.preventDefault();
  };
  nodes.playerSearch.oninput = () => {
    closePlayerDetailRows(nodes.playersBody);
    state.search = nodes.playerSearch.value;
    renderRows();
  };
  nodes.playerTeamFilters.forEach((control) => {
    control.onchange = () => {
      closePlayerDetailRows(nodes.playersBody);
      state.team = control.value;
      renderRows();
    };
  });
  nodes.playerSort.onchange = () => {
    state.sort = nodes.playerSort.value;
    state.isDefaultSort = false;
    renderRows();
  };
  nodes.playerSortDirection.onchange = () => {
    state.direction = nodes.playerSortDirection.value;
    state.isDefaultSort = false;
    renderRows();
  };
}

function renderPlayerTable(item, players, state, nodes) {
  const visiblePlayers = getVisiblePlayers(players, item, state);
  nodes.playersNote.textContent =
    visiblePlayers.length === players.length
      ? `${formatNumber(players.length)} jugadores con estadisticas locales.`
      : `${formatNumber(visiblePlayers.length)} de ${formatNumber(players.length)} jugadores visibles.`;
  nodes.playersState.hidden = visiblePlayers.length > 0;
  if (!visiblePlayers.length) {
    nodes.playersState.textContent = "No hay jugadores que coincidan con los controles activos.";
  }
  nodes.playersBody.innerHTML = visiblePlayers
    .map((entry, index) => renderPlayerRows(entry.player, item, index, entry.inactive))
    .join("");
  bindPlayerDetailRows(nodes.playersBody);
}

function getVisiblePlayers(players, item, state) {
  const normalizedSearch = normalizeLookupText(state.search);
  return players
    .map((player) => ({
      player,
      inactive: isInactiveMatchPlayer(player),
      team: getTeamSideDisplay(player.team || player.team_side),
    }))
    .filter((entry) => {
      const matchesTeam = state.team === "all" || entry.team.key === state.team;
      const matchesName =
        !normalizedSearch ||
        normalizeLookupText(entry.player.player_name).includes(normalizedSearch);
      return matchesTeam && matchesName;
    })
    .sort((a, b) => comparePlayerEntries(a, b, item, state));
}

function comparePlayerEntries(a, b, item, state) {
  void item;
  if (state.isDefaultSort) {
    return (
      compareInactivePriority(a, b) ||
      compareNumericStat(b.player.kills, a.player.kills) ||
      compareNumericStat(a.player.deaths, b.player.deaths) ||
      comparePlayerNames(a.player, b.player)
    );
  }

  if (state.sort === "kpm") {
    const readyPriority = compareReadyKpmPriority(a.player, b.player);
    if (readyPriority) {
      return readyPriority;
    }
    const direction = state.direction === "asc" ? 1 : -1;
    const compared = compareNumericStat(
      getReadyKpmValue(a.player),
      getReadyKpmValue(b.player),
    );
    return compared * direction || comparePlayerNames(a.player, b.player);
  }

  if (!["name", "team"].includes(state.sort)) {
    const inactivePriority = compareInactivePriority(a, b);
    if (inactivePriority) {
      return inactivePriority;
    }
  }

  const direction = state.direction === "asc" ? 1 : -1;
  const compared = comparePlayerSortValue(a, b, item, state.sort);
  return compared * direction || comparePlayerNames(a.player, b.player);
}

function comparePlayerSortValue(a, b, item, sort) {
  void item;
  if (sort === "name") {
    return comparePlayerNames(a.player, b.player);
  }
  if (sort === "team") {
    return compareText(a.team.label, b.team.label);
  }
  if (sort === "deaths" || sort === "teamkills" || sort === "kills") {
    return compareNumericStat(a.player[sort], b.player[sort]);
  }
  if (sort === "kd") {
    return compareNumericStat(getKdRatioValue(a.player), getKdRatioValue(b.player));
  }
  return compareNumericStat(a.player.kills, b.player.kills);
}

function compareReadyKpmPriority(leftPlayer, rightPlayer) {
  const leftReady = leftPlayer?.kpm_status === "ready";
  const rightReady = rightPlayer?.kpm_status === "ready";
  if (leftReady === rightReady) {
    return 0;
  }
  return leftReady ? -1 : 1;
}

function compareInactivePriority(a, b) {
  return Number(a.inactive) - Number(b.inactive);
}

function comparePlayerNames(a, b) {
  return compareText(getPlayerName(a), getPlayerName(b));
}

function compareText(a, b) {
  return String(a || "").localeCompare(String(b || ""), "es", {
    sensitivity: "base",
  });
}

function compareNumericStat(a, b) {
  return toSortableNumber(a) - toSortableNumber(b);
}

function renderPlayerRows(player, item, index, inactive = false) {
  const team = getTeamSideDisplay(player.team || player.team_side);
  const rowId = `match-player-row-${index}`;
  const panelId = `match-player-panel-${index}`;
  const playerName = getPlayerName(player);
  return `
    <tr
      class="historical-player-row historical-player-row--${team.key} ${inactive ? "is-inactive" : ""}"
      id="${escapeHtml(rowId)}"
    >
      <td>
        <button
          class="historical-player-row__details-button"
          type="button"
          aria-controls="${escapeHtml(panelId)}"
          aria-expanded="false"
          aria-label="Ver estadisticas ampliadas de ${escapeHtml(playerName)}"
        >
          <span>${escapeHtml(playerName)}</span>
          <span aria-hidden="true">i</span>
        </button>
      </td>
      <td class="historical-player-team-cell">
        <span class="historical-player-team-badge historical-player-team-badge--${team.key}">
          ${escapeHtml(team.label)}
        </span>
      </td>
      <td>${escapeHtml(formatOptionalNumber(player.kills))}</td>
      <td>${escapeHtml(formatOptionalNumber(player.deaths))}</td>
      <td>${escapeHtml(formatOptionalNumber(player.teamkills))}</td>
      <td>${escapeHtml(formatKdRatio(player))}</td>
      <td>${escapeHtml(formatReadyKpmValue(player))}</td>
    </tr>
    <tr
      class="historical-player-detail-row"
      id="${escapeHtml(panelId)}"
      aria-labelledby="${escapeHtml(rowId)}"
    >
      <td colspan="7">
        ${renderPlayerStatsPanel(player, item, { team, playerName })}
      </td>
    </tr>
  `;
}

function bindPlayerDetailRows(playersBody) {
  const playerRows = [...playersBody.querySelectorAll(".historical-player-row")];
  const collapseRow = (row) => {
    const button = row.querySelector(".historical-player-row__details-button");
    const detailRow = row.nextElementSibling;
    if (!button || !detailRow?.classList.contains("historical-player-detail-row")) {
      return;
    }
    row.classList.remove("is-expanded");
    detailRow.classList.remove("is-open");
    button.setAttribute("aria-expanded", "false");
  };

  playerRows.forEach((row) => {
    const button = row.querySelector(".historical-player-row__details-button");
    const detailRow = row.nextElementSibling;
    if (!button || !detailRow?.classList.contains("historical-player-detail-row")) {
      return;
    }
    const setExpanded = (expanded) => {
      if (expanded) {
        playerRows.filter((candidate) => candidate !== row).forEach(collapseRow);
      }
      row.classList.toggle("is-expanded", expanded);
      detailRow.classList.toggle("is-open", expanded);
      button.setAttribute("aria-expanded", String(expanded));
    };
    const toggleExpanded = () => setExpanded(!detailRow.classList.contains("is-open"));

    button.addEventListener("click", () => {
      toggleExpanded();
    });
  });
}

function closePlayerDetailRows(playersBody) {
  [...playersBody.querySelectorAll(".historical-player-row")].forEach((row) => {
    const button = row.querySelector(".historical-player-row__details-button");
    const detailRow = row.nextElementSibling;
    if (!button || !detailRow?.classList.contains("historical-player-detail-row")) {
      return;
    }
    row.classList.remove("is-expanded");
    detailRow.classList.remove("is-open");
    button.setAttribute("aria-expanded", "false");
  });
}

function getPlayerName(player) {
  return player.player_name || player.name || "Jugador no identificado";
}

function isInactiveMatchPlayer(player) {
  const team = getTeamSideDisplay(player.team || player.team_side);
  return (
    team.key === "unknown" &&
    toSortableNumber(player.kills) === 0 &&
    toSortableNumber(player.deaths) === 0 &&
    toSortableNumber(player.teamkills) === 0 &&
    getKdRatioValue(player) === 0 &&
    !hasNamedCounts(player.top_weapons) &&
    !hasNamedCounts(player.most_killed) &&
    !hasNamedCounts(player.death_by)
  );
}

function renderPlayerStatsPanel(player, item, context) {
  const matchups = buildPlayerDirectMatchups(player);
  const kpmChip =
    player?.kpm_status === "ready"
      ? renderPlayerStatChip("KPM", formatDecimal(player.kpm, 2))
      : "";
  const hasExpandedStats =
    hasNamedCounts(player.top_weapons) ||
    hasNamedCounts(player.most_killed) ||
    hasNamedCounts(player.death_by) ||
    matchups.length > 0;

  return `
    <section class="historical-player-stats-panel" aria-label="Estadisticas ampliadas de ${escapeHtml(context.playerName)}">
      <div class="historical-player-stats-panel__header">
        <div>
          <p>${escapeHtml(context.team.label)}</p>
          <h4>${escapeHtml(context.playerName)}</h4>
        </div>
        <div class="historical-player-stats-panel__summary">
          ${renderPlayerStatChip("Kills", formatOptionalNumber(player.kills))}
          ${renderPlayerStatChip("Muertes", formatOptionalNumber(player.deaths))}
          ${renderPlayerStatChip("TK", formatOptionalNumber(player.teamkills))}
          ${renderPlayerStatChip("KD", formatKdRatio(player))}
          ${kpmChip}
        </div>
      </div>
      ${renderExternalProfilesSection(player)}
      ${
        hasExpandedStats
          ? `
            <div class="historical-player-stats-panel__grid">
              ${renderNamedCountSection("Armas", player.top_weapons)}
              ${renderNamedCountSection("Mas abatido", player.most_killed)}
              ${renderNamedCountSection("Muere por", player.death_by)}
              ${renderDirectMatchupsSection(matchups)}
            </div>
          `
          : `<p class="historical-player-stats-panel__empty">Sin estadisticas ampliadas disponibles.</p>`
      }
    </section>
  `;
}

function renderExternalProfilesSection(player) {
  const links = [
    "steam",
    "hellor",
    "hll_records",
    "helo",
  ]
    .map((key) => ({
      key,
      brand: EXTERNAL_PROFILE_BRANDS[key] || { label: key, logoSrc: "" },
      href: player.external_profile_links?.[key],
    }))
    .filter((entry) => typeof entry.href === "string" && entry.href.trim());

  return `
    <article class="historical-player-stats-panel__section historical-player-stats-panel__profiles">
      <h5>Perfiles externos</h5>
      ${
        links.length
          ? `
            <div class="historical-player-profile-links">
              ${links
                .map(
                  ({ brand, href }) => `
                    <a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">
                      ${
                        brand.logoSrc
                          ? `<img class="historical-player-profile-link__brand" src="${escapeHtml(brand.logoSrc)}" alt="" aria-hidden="true" decoding="async" loading="lazy" />`
                          : ""
                      }
                      <span>${escapeHtml(brand.label)}</span>
                    </a>
                  `,
                )
                .join("")}
            </div>
          `
          : renderExternalProfilesUnavailable(player)
      }
    </article>
  `;
}


function renderExternalProfilesUnavailable(player) {
  const platform = String(player.platform || "").toLowerCase();
  const epicId = typeof player.epic_id === "string" ? player.epic_id.trim() : "";

  if (platform === "epic") {
    return epicId
      ? `<p>Jugador detectado como Epic. ID capturado: <code>${escapeHtml(epicId)}</code>. Sin enlaces externos compatibles confirmados para este proveedor.</p>`
      : "<p>Jugador detectado como Epic. Sin enlaces externos compatibles confirmados para este proveedor.</p>";
  }

  return "<p>Perfiles externos no disponibles.</p>";
}

function renderPlayerStatChip(label, value) {
  return `
    <article>
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </article>
  `;
}

function renderNamedCountSection(title, items) {
  if (!hasNamedCounts(items)) {
    return `
      <article class="historical-player-stats-panel__section">
        <h5>${escapeHtml(title)}</h5>
        <p>No disponible</p>
      </article>
    `;
  }
  return `
    <article class="historical-player-stats-panel__section">
      <h5>${escapeHtml(title)}</h5>
      <ol class="historical-weapon-stat-list">
        ${items
          .map((stat) => {
            const name = stat.name || stat.label || "Sin nombre";
            const count = stat.count ?? stat.total ?? 0;
            return `
              <li>
                <span>${escapeHtml(name)}</span>
                <strong>${escapeHtml(formatNumber(count))}</strong>
              </li>
            `;
          })
          .join("")}
      </ol>
    </article>
  `;
}

function renderDirectMatchupsSection(matchups) {
  if (!matchups.length) {
    return `
      <article class="historical-player-stats-panel__section historical-player-stats-panel__section--wide">
        <h5>Duelo directo</h5>
        <p>No disponible</p>
      </article>
    `;
  }
  return `
    <article class="historical-player-stats-panel__section historical-player-stats-panel__section--wide">
      <h5>Duelo directo</h5>
      <div class="historical-player-matchups" role="table" aria-label="Duelos directos">
        <div role="row">
          <span role="columnheader">Rival</span>
          <span role="columnheader">Abatidos</span>
          <span role="columnheader">Muertes</span>
          <span role="columnheader">Balance</span>
        </div>
        ${matchups
          .map(
            (matchup) => `
              <div role="row">
                <span role="cell">${escapeHtml(matchup.name)}</span>
                <strong role="cell">${escapeHtml(formatNumber(matchup.kills))}</strong>
                <strong role="cell">${escapeHtml(formatNumber(matchup.deaths))}</strong>
                <strong role="cell">${escapeHtml(formatSignedNumber(matchup.balance))}</strong>
              </div>
            `,
          )
          .join("")}
      </div>
    </article>
  `;
}

function buildPlayerDirectMatchups(player) {
  const byName = new Map();
  const addStats = (items, key) => {
    if (!Array.isArray(items)) {
      return;
    }
    items.forEach((item) => {
      const name = item.name || item.label;
      if (!name) {
        return;
      }
      const normalizedName = String(name);
      const current = byName.get(normalizedName) || {
        name: normalizedName,
        kills: 0,
        deaths: 0,
      };
      current[key] += Number(item.count ?? item.total ?? 0) || 0;
      byName.set(normalizedName, current);
    });
  };

  addStats(player.most_killed, "kills");
  addStats(player.death_by, "deaths");
  return [...byName.values()]
    .map((matchup) => ({
      ...matchup,
      balance: matchup.kills - matchup.deaths,
      involvement: matchup.kills + matchup.deaths,
    }))
    .sort((a, b) => b.involvement - a.involvement || a.name.localeCompare(b.name, "es"))
    .slice(0, 8);
}

function renderActions(item, actionsNode) {
  const matchUrl = normalizeSafePublicScoreboardMatchUrl(item.match_url);
  if (!matchUrl) {
    actionsNode.innerHTML = "";
    actionsNode.hidden = true;
    return;
  }
  actionsNode.innerHTML = `
    <a
      class="historical-match-card__link"
      data-match-detail-scoreboard-link
      href="${escapeHtml(matchUrl)}"
      target="_blank"
      rel="noopener noreferrer"
    >
      Ver en Scoreboard
    </a>
  `;
  actionsNode.hidden = false;
}

function resolveMatchFactions(item, mapName) {
  const normalizedMap = normalizeLookupText(
    `${item.map?.name || ""} ${item.map?.pretty_name || ""} ${mapName || ""}`,
  );

  if (/(kursk|stalingrad|kharkov)/.test(normalizedMap)) {
    return {
      allied: {
        label: "Sovieticos",
        emblem: "./assets/img/factions/soviets.webp",
      },
      axis: {
        label: "Eje",
        emblem: "./assets/img/factions/germany.webp",
      },
    };
  }

  if (/(driel|elalamein|el alamein|tobruk)/.test(normalizedMap)) {
    return {
      allied: {
        label: "Britanicos",
        emblem: "./assets/img/factions/britain.webp",
      },
      axis: {
        label: normalizedMap.includes("tobruk") || normalizedMap.includes("elalamein")
          ? "Afrika Korps"
          : "Eje",
        emblem: "./assets/img/factions/germany.webp",
      },
    };
  }

  return {
    allied: {
      label: "USA",
      emblem: "./assets/img/factions/us.webp",
    },
    axis: {
      label: "Eje",
      emblem: "./assets/img/factions/germany.webp",
    },
  };
}

function resolveMapImagePath(item, mapName) {
  const normalizedMap = normalizeLookupText(
    `${item.map?.name || ""} ${item.map?.pretty_name || ""} ${mapName || ""}`,
  ).replaceAll(" ", "");
  const mapAssetByKey = {
    carentan: "carentan-day.webp",
    driel: "driel-day.webp",
    elalamein: "elalamein-day.webp",
    elsenbornridge: "elsenbornridge-day.webp",
    foy: "foy-day.webp",
    hill400: "hill400-day.webp",
    hurtgenforest: "hurtgenforest-day.webp",
    kharkov: "kharkov-day.webp",
    kursk: "kursk-day.webp",
    mortain: "mortain-day.webp",
    omahabeach: "omahabeach-day.webp",
    purpleheartlane: "purpleheartlane-rain.webp",
    smolensk: "smolensk-day.webp",
    stmariedumont: "stmariedumont-day.webp",
    stmereeglise: "stmereeglise-day.webp",
    tobrukdawn: "tobruk-dawn.webp",
    tobruk: "tobruk-day.webp",
    utahbeach: "utahbeach-day.webp",
  };
  const matchedKey = Object.keys(mapAssetByKey).find((key) =>
    normalizedMap.includes(key),
  );
  return matchedKey ? `./assets/img/maps/${mapAssetByKey[matchedKey]}` : "";
}

function normalizeLookupText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function formatTeamSide(value) {
  return getTeamSideDisplay(value).label;
}

function getTeamSideDisplay(value) {
  const normalized = String(value || "")
    .trim()
    .toLowerCase();
  if (normalized === "allies" || normalized === "allied" || normalized === "aliados") {
    return { key: "allies", label: "Aliados" };
  }
  if (normalized === "axis" || normalized === "eje") {
    return { key: "axis", label: "Eje" };
  }
  return { key: "unknown", label: "No disponible" };
}

function formatGameMode(value) {
  if (!value) {
    return "Modo no disponible";
  }
  const normalized = String(value).replaceAll("_", " ").replaceAll("-", " ");
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function formatDuration(value) {
  const seconds = Number(value);
  if (!Number.isFinite(seconds) || seconds <= 0) {
    return "Duracion no disponible";
  }
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) {
    return `${formatNumber(minutes)} min`;
  }
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${formatNumber(hours)} h ${formatNumber(remainingMinutes)} min`;
}

function formatWinner(value) {
  const normalized = String(value || "").toLowerCase();
  if (normalized === "allies" || normalized === "allied") {
    return "Ganador: Aliados";
  }
  if (normalized === "axis") {
    return "Ganador: Eje";
  }
  if (normalized === "draw") {
    return "Empate";
  }
  return "Resultado no disponible";
}

function formatOptionalNumber(value) {
  return value === null || value === undefined ? "No disponible" : formatNumber(value);
}

function formatKdRatio(player) {
  if (
    !Number.isFinite(Number(player.kd_ratio)) &&
    (!Number.isFinite(Number(player.kills)) || !Number.isFinite(Number(player.deaths)))
  ) {
    return "No disponible";
  }
  return formatDecimal(getKdRatioValue(player), 2);
}

function getReadyKpmValue(player) {
  if (player?.kpm_status !== "ready") {
    return Number.NaN;
  }
  const value = Number(player.kpm);
  return Number.isFinite(value) ? value : Number.NaN;
}

function formatReadyKpmValue(player) {
  const value = getReadyKpmValue(player);
  if (!Number.isFinite(value)) {
    return "";
  }
  return formatDecimal(value, 2);
}

function getKdRatioValue(player) {
  if (Number.isFinite(Number(player.kd_ratio))) {
    return Number(player.kd_ratio);
  }
  const kills = Number(player.kills);
  const deaths = Number(player.deaths);
  if (!Number.isFinite(kills) || !Number.isFinite(deaths)) {
    return 0;
  }
  return deaths > 0 ? kills / deaths : kills;
}

function formatNamedCounts(items) {
  if (!Array.isArray(items) || items.length === 0) {
    return "No disponible";
  }
  return items
    .slice(0, 3)
    .map((item) => {
      const name = item.name || item.label || "Sin nombre";
      const count = item.count ?? item.total ?? 0;
      return `${name} (${formatNumber(count)})`;
    })
    .join(" / ");
}

function hasNamedCounts(items) {
  return Array.isArray(items) && items.length > 0;
}

function formatNumber(value) {
  const parsedValue = Number(value);
  if (!Number.isFinite(parsedValue)) {
    return "0";
  }
  return new Intl.NumberFormat("es-ES").format(parsedValue);
}

function toSortableNumber(value) {
  const parsedValue = Number(value);
  return Number.isFinite(parsedValue) ? parsedValue : 0;
}

function formatSignedNumber(value) {
  const parsedValue = Number(value);
  if (!Number.isFinite(parsedValue) || parsedValue === 0) {
    return "0";
  }
  return `${parsedValue > 0 ? "+" : ""}${formatNumber(parsedValue)}`;
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

function formatMatchTimestamp(item, kind) {
  const timestamp = kind === "start" ? item.started_at : item.ended_at;
  if (timestamp) {
    return formatTimestamp(timestamp);
  }
  return "No disponible";
}

function normalizeSafePublicScoreboardMatchUrl(value) {
  if (typeof value !== "string" || !value.trim()) {
    return "";
  }
  try {
    const url = new URL(value.trim());
    const allowedOrigins = new Set([
      "https://scoreboard.comunidadhll.es",
      "https://scoreboard.comunidadhll.es:5443",
    ]);
    const isAllowedPath = url.pathname === "/games" || url.pathname.startsWith("/games/");
    return allowedOrigins.has(url.origin) && isAllowedPath ? url.href : "";
  } catch (error) {
    return "";
  }
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed with ${response.status}`);
  }
  return response.json();
}

function setState(node, message, isError = false) {
  node.textContent = message;
  node.hidden = false;
  node.classList.toggle("is-error", isError);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
