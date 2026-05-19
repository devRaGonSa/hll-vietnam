document.addEventListener("DOMContentLoaded", () => {
  const backendBaseUrl =
    document.body.dataset.backendBaseUrl || "http://127.0.0.1:8000";
  const params = new URLSearchParams(window.location.search);
  const serverSlug = params.get("server") || "";
  const matchId = params.get("match") || "";
  const titleNode = document.getElementById("match-detail-title");
  const summaryNode = document.getElementById("match-detail-summary");
  const noteNode = document.getElementById("match-detail-note");
  const stateNode = document.getElementById("match-detail-state");
  const gridNode = document.getElementById("match-detail-grid");
  const actionsNode = document.getElementById("match-detail-actions");
  const playersSectionNode = document.getElementById("match-detail-players-section");
  const playersNoteNode = document.getElementById("match-detail-players-note");
  const playersStateNode = document.getElementById("match-detail-players-state");
  const playersTableShellNode = document.getElementById("match-detail-players-table-shell");
  const playersBodyNode = document.getElementById("match-detail-players-body");

  if (!serverSlug || !matchId) {
    titleNode.textContent = "Partida no seleccionada";
    summaryNode.textContent = "Vuelve al historico y abre una partida registrada.";
    noteNode.textContent = "Faltan parametros internos para cargar este detalle.";
    setState(stateNode, "No hay una partida seleccionada.", true);
    return;
  }

  void loadMatchDetail({
    backendBaseUrl,
    serverSlug,
    matchId,
    titleNode,
    summaryNode,
    noteNode,
    stateNode,
    gridNode,
    actionsNode,
    playersSectionNode,
    playersNoteNode,
    playersStateNode,
    playersTableShellNode,
    playersBodyNode,
  });
});

async function loadMatchDetail({
  backendBaseUrl,
  serverSlug,
  matchId,
  titleNode,
  summaryNode,
  noteNode,
  stateNode,
  gridNode,
  actionsNode,
  playersSectionNode,
  playersNoteNode,
  playersStateNode,
  playersTableShellNode,
  playersBodyNode,
}) {
  try {
    const payload = await fetchJson(
      `${backendBaseUrl}/api/historical/matches/detail?server=${encodeURIComponent(
        serverSlug,
      )}&match=${encodeURIComponent(matchId)}`,
    );
    const data = payload?.data;
    const item = data?.item;
    if (!data?.found || !item) {
      titleNode.textContent = "Detalle no disponible";
      summaryNode.textContent =
        "La partida existe como enlace interno, pero todavia no hay detalle suficiente para mostrar.";
      noteNode.textContent =
        "El historico local puede tener solo una ventana RCON parcial o ningun registro ampliado.";
      setState(stateNode, "Detalle no disponible para esta partida.");
      return;
    }

    renderMatchDetail(item, {
      titleNode,
      summaryNode,
      noteNode,
      stateNode,
      gridNode,
      actionsNode,
      playersSectionNode,
      playersNoteNode,
      playersStateNode,
      playersTableShellNode,
      playersBodyNode,
    });
  } catch (error) {
    titleNode.textContent = "Detalle no disponible";
    summaryNode.textContent = "No se pudo conectar con el backend local.";
    noteNode.textContent = "Comprueba que el backend este levantado y vuelve a intentarlo.";
    setState(stateNode, "Error al cargar el detalle de la partida.", true);
  }
}

function renderMatchDetail(
  item,
  {
    titleNode,
    summaryNode,
    noteNode,
    stateNode,
    gridNode,
    actionsNode,
    playersSectionNode,
    playersNoteNode,
    playersStateNode,
    playersTableShellNode,
    playersBodyNode,
  },
) {
  const mapName = item.map?.pretty_name || item.map?.name || "Mapa no disponible";
  const serverName = item.server?.name || "Servidor no disponible";
  titleNode.textContent = mapName;
  summaryNode.textContent = `${serverName} | Partida ${item.match_id || "sin id"}`;
  noteNode.textContent = buildDetailNote(item);
  gridNode.innerHTML = [
    renderDetailCard("Servidor", serverName),
    renderDetailCard("Mapa", mapName),
    renderDetailCard("Inicio", formatTimestamp(item.started_at)),
    renderDetailCard("Fin", formatTimestamp(item.closed_at || item.ended_at)),
    renderDetailCard("Duracion", formatDuration(item.duration_seconds)),
    renderDetailCard("Jugadores media", formatNumber(item.player_count)),
    renderDetailCard("Pico jugadores", formatOptionalNumber(item.peak_players)),
    renderDetailCard("Muestras RCON", formatOptionalNumber(item.sample_count)),
    renderDetailCard("Marcador", formatScore(item.result)),
    renderDetailCard("Resultado", formatMatchResult(item.result)),
    renderDetailCard("Base de captura", formatCaptureBasis(item.capture_basis)),
    renderDetailCard("Capacidades", formatCapabilities(item.capabilities)),
  ].join("");
  renderPlayerSection(item, {
    playersSectionNode,
    playersNoteNode,
    playersStateNode,
    playersTableShellNode,
    playersBodyNode,
  });
  renderActions(item, actionsNode);
  stateNode.hidden = true;
  gridNode.hidden = false;
}

function renderPlayerSection(
  item,
  {
    playersSectionNode,
    playersNoteNode,
    playersStateNode,
    playersTableShellNode,
    playersBodyNode,
  },
) {
  const players = Array.isArray(item.players) ? item.players : [];
  playersSectionNode.hidden = false;
  if (players.length === 0) {
    playersNoteNode.textContent =
      "Esta partida no tiene estadisticas por jugador disponibles en el detalle interno.";
    setState(
      playersStateNode,
      item.capture_basis === "rcon-competitive-window"
        ? "Las ventanas RCON actuales no incluyen desglose por jugador."
        : "No hay filas de jugador registradas para esta partida.",
    );
    playersTableShellNode.hidden = true;
    playersBodyNode.innerHTML = "";
    return;
  }

  playersNoteNode.textContent = `${formatNumber(players.length)} jugadores con estadisticas locales.`;
  playersStateNode.hidden = true;
  playersBodyNode.innerHTML = players.map((player) => renderPlayerRow(player)).join("");
  playersTableShellNode.hidden = false;
}

function renderPlayerRow(player) {
  return `
    <tr>
      <td>${escapeHtml(player.name || "Jugador no identificado")}</td>
      <td>${escapeHtml(formatTeamSide(player.team_side))}</td>
      <td>${escapeHtml(formatOptionalNumber(player.level))}</td>
      <td>${escapeHtml(formatOptionalNumber(player.kills))}</td>
      <td>${escapeHtml(formatOptionalNumber(player.deaths))}</td>
      <td>${escapeHtml(formatOptionalNumber(player.teamkills))}</td>
      <td>${escapeHtml(formatOptionalNumber(player.combat))}</td>
      <td>${escapeHtml(formatOptionalNumber(player.support))}</td>
      <td>${escapeHtml(formatDuration(player.time_seconds))}</td>
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

function renderDetailCard(label, value) {
  return `
    <article class="historical-stat-card">
      <p>${escapeHtml(label)}</p>
      <strong>${escapeHtml(value)}</strong>
    </article>
  `;
}

function buildDetailNote(item) {
  if (item.capture_basis === "rcon-competitive-window") {
    return "Detalle interno generado desde ventanas competitivas RCON. Algunos datos pueden estar limitados.";
  }
  return "Detalle servido desde el historico local disponible para esta partida.";
}

function formatCaptureBasis(value) {
  if (value === "rcon-competitive-window") {
    return "Ventana competitiva RCON";
  }
  if (value === "public-scoreboard-match") {
    return "Scoreboard persistido";
  }
  return "Historico local";
}

function formatPlayerCount(item) {
  if (Number.isFinite(Number(item.peak_players))) {
    return `${formatNumber(item.player_count)} media / ${formatNumber(item.peak_players)} pico`;
  }
  return formatNumber(item.player_count);
}

function formatOptionalNumber(value) {
  return value === null || value === undefined ? "No disponible" : formatNumber(value);
}

function formatCapabilities(capabilities) {
  if (!capabilities || typeof capabilities !== "object") {
    return "No disponibles";
  }
  const labels = Object.entries(capabilities)
    .filter(([, value]) => value !== null && value !== undefined)
    .map(([key, value]) => `${formatCapabilityKey(key)}: ${formatCapabilityValue(value)}`);
  return labels.length > 0 ? labels.join(" | ") : "No disponibles";
}

function formatCapabilityKey(key) {
  return String(key).replaceAll("_", " ");
}

function formatCapabilityValue(value) {
  if (value === "exact") {
    return "exacto";
  }
  if (value === "approximate") {
    return "aproximado";
  }
  if (value === "partial") {
    return "parcial";
  }
  if (value === "unavailable") {
    return "no disponible";
  }
  return String(value);
}

function formatTeamSide(value) {
  if (value === "allies") {
    return "Aliados";
  }
  if (value === "axis") {
    return "Axis";
  }
  return value || "No disponible";
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
  const axisScore = Number.isFinite(result?.axis_score) ? result.axis_score : "-";
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
