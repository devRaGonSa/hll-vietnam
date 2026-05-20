document.addEventListener("DOMContentLoaded", () => {
  const backendBaseUrl =
    document.body.dataset.backendBaseUrl || "http://127.0.0.1:8000";
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
    playersTableShell: document.getElementById("match-detail-players-table-shell"),
    playersBody: document.getElementById("match-detail-players-body"),
    timelineSection: document.getElementById("match-detail-timeline-section"),
    timelineNote: document.getElementById("match-detail-timeline-note"),
    timelineState: document.getElementById("match-detail-timeline-state"),
    timelineGrid: document.getElementById("match-detail-timeline-grid"),
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
    nodes.summary.textContent = "No se pudo conectar con el backend local.";
    nodes.note.textContent = "";
    setState(nodes.state, "Error al cargar el detalle de la partida.", true);
  }
}

function renderMatchDetail(item, nodes) {
  const mapName = item.map?.pretty_name || item.map?.name || "Mapa no disponible";
  const serverName = item.server?.name || item.server?.slug || "Servidor no disponible";
  nodes.title.textContent = mapName;
  nodes.summary.textContent = `${serverName} - ${formatDetailSubtitle(item)}`;
  nodes.note.textContent = "";
  nodes.grid.innerHTML = renderScoreboardDetail(item, { mapName, serverName });
  renderPlayerSection(item, nodes);
  hideTimelineSection(nodes);
  renderActions(item, nodes.actions);
  nodes.state.hidden = true;
  nodes.grid.hidden = false;
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
    nodes.playersTableShell.hidden = true;
    nodes.playersBody.innerHTML = "";
    return;
  }

  nodes.playersNote.textContent = `${formatNumber(players.length)} jugadores con estadisticas locales.`;
  nodes.playersState.hidden = true;
  nodes.playersBody.innerHTML = players.map((player) => renderPlayerRow(player)).join("");
  nodes.playersTableShell.hidden = false;
}

function renderPlayerRow(player) {
  return `
    <tr>
      <td>${escapeHtml(player.player_name || player.name || "Jugador no identificado")}</td>
      <td>${escapeHtml(formatTeamSide(player.team || player.team_side))}</td>
      <td>${escapeHtml(formatOptionalNumber(player.kills))}</td>
      <td>${escapeHtml(formatOptionalNumber(player.deaths))}</td>
      <td>${escapeHtml(formatOptionalNumber(player.teamkills))}</td>
      <td>${escapeHtml(formatKdRatio(player))}</td>
      <td>${escapeHtml(formatNamedCounts(player.top_weapons))}</td>
      <td>${escapeHtml(formatNamedCounts(player.most_killed))}</td>
      <td>${escapeHtml(formatNamedCounts(player.death_by))}</td>
    </tr>
  `;
}

function renderActions(item, actionsNode) {
  const matchUrl = normalizeExternalMatchUrl(item.match_url);
  if (!matchUrl) {
    actionsNode.innerHTML = "";
    actionsNode.hidden = true;
    return;
  }
  actionsNode.innerHTML = `
    <a
      class="historical-match-card__link"
      href="${escapeHtml(matchUrl)}"
      target="_blank"
      rel="noopener noreferrer"
    >
      Abrir en scoreboard
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

function normalizeLookupText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function formatDetailSubtitle(item) {
  if (item.capture_basis === "rcon-materialized-admin-log") {
    return "Partida RCON materializada";
  }
  if (item.capture_basis === "rcon-competitive-window") {
    return "Partida RCON registrada";
  }
  if (item.result_source === "public-scoreboard-match") {
    return "Partida del scoreboard";
  }
  return "Partida historica";
}

function formatTeamSide(value) {
  const normalized = String(value || "").toLowerCase();
  if (normalized === "allies" || normalized === "allied") {
    return "Aliados";
  }
  if (normalized === "axis") {
    return "Eje";
  }
  return value || "No disponible";
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
  if (Number.isFinite(Number(player.kd_ratio))) {
    return formatDecimal(player.kd_ratio, 2);
  }
  const kills = Number(player.kills);
  const deaths = Number(player.deaths);
  if (!Number.isFinite(kills) || !Number.isFinite(deaths)) {
    return "No disponible";
  }
  return deaths > 0 ? formatDecimal(kills / deaths, 2) : formatDecimal(kills, 2);
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
