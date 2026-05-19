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
    nodes.note.textContent = "Faltan parametros internos para cargar este detalle.";
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
      nodes.note.textContent =
        "El historico local puede tener solo una ventana RCON parcial o ningun registro ampliado.";
      setState(nodes.state, "Detalle no disponible para esta partida.");
      return;
    }

    renderMatchDetail(item, nodes);
  } catch (error) {
    nodes.title.textContent = "Detalle no disponible";
    nodes.summary.textContent = "No se pudo conectar con el backend local.";
    nodes.note.textContent = "Comprueba que el backend este levantado y vuelve a intentarlo.";
    setState(nodes.state, "Error al cargar el detalle de la partida.", true);
  }
}

function renderMatchDetail(item, nodes) {
  const mapName = item.map?.pretty_name || item.map?.name || "Mapa no disponible";
  const serverName = item.server?.name || item.server?.slug || "Servidor no disponible";
  nodes.title.textContent = mapName;
  nodes.summary.textContent = `${serverName} - ${formatDetailSubtitle(item)}`;
  nodes.note.textContent = buildDetailNote(item);
  nodes.grid.innerHTML = [
    renderDetailCard("Servidor", serverName),
    renderDetailCard("Mapa", mapName),
    renderDetailCard("Modo", formatGameMode(item.game_mode || item.gamestate?.game_mode)),
    renderDetailCard("Marcador", formatScore(item.result)),
    renderDetailCard("Ganador", formatWinner(item.winner || item.result?.winner)),
    renderDetailCard("Resultado", formatMatchResult(item.result)),
    renderDetailCard("Inicio", formatMatchTimestamp(item, "start")),
    renderDetailCard("Fin", formatMatchTimestamp(item, "end")),
    renderDetailCard("Duracion", formatDuration(item.duration_seconds)),
    renderDetailCard("Confianza", formatConfidence(item.confidence)),
    renderDetailCard(
      "Fuente",
      formatSourceBasis(item.source_basis || item.result_source) || "No disponible",
    ),
    renderDetailCard("Base", formatCaptureBasis(item.capture_basis)),
  ].join("");
  renderPlayerSection(item, nodes);
  renderTimelineSection(item, nodes);
  renderActions(item, nodes.actions);
  nodes.state.hidden = true;
  nodes.grid.hidden = false;
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

function renderTimelineSection(item, nodes) {
  const eventCounts = Array.isArray(item.timeline?.event_counts)
    ? item.timeline.event_counts
    : [];
  nodes.timelineSection.hidden = false;
  if (eventCounts.length === 0) {
    nodes.timelineNote.textContent =
      "No hay resumen de eventos disponible para esta partida.";
    setState(nodes.timelineState, "Sin eventos agregados para mostrar.");
    nodes.timelineGrid.hidden = true;
    nodes.timelineGrid.innerHTML = "";
    return;
  }

  nodes.timelineNote.textContent = `${formatNumber(eventCounts.length)} tipos de evento registrados.`;
  nodes.timelineState.hidden = true;
  nodes.timelineGrid.innerHTML = eventCounts.map((event) => renderTimelineCard(event)).join("");
  nodes.timelineGrid.hidden = false;
}

function renderTimelineCard(event) {
  const label =
    event.event_type ||
    event.type ||
    event.name ||
    event.label ||
    "Evento registrado";
  const count = event.count ?? event.total ?? event.event_count ?? 0;
  return renderDetailCard(formatEventType(label), formatNumber(count));
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
  const source = formatSourceBasis(item.source_basis || item.result_source);
  if (source) {
    return `Detalle servido desde ${source}. Los campos sin cobertura fiable se muestran como no disponibles.`;
  }
  return "Detalle servido desde el historico local disponible para esta partida.";
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

function formatCaptureBasis(value) {
  if (value === "rcon-materialized-admin-log") {
    return "Registro RCON materializado";
  }
  if (value === "rcon-competitive-window") {
    return "Ventana competitiva RCON";
  }
  if (value === "public-scoreboard-match") {
    return "Scoreboard persistido";
  }
  return value ? String(value).replaceAll("-", " ") : "Historico local";
}

function formatSourceBasis(value) {
  if (value === "admin-log-match-ended") {
    return "cierre RCON confirmado";
  }
  if (value === "rcon-session") {
    return "sesion RCON registrada";
  }
  if (value === "public-scoreboard-match") {
    return "scoreboard externo";
  }
  return value ? String(value).replaceAll("-", " ") : "";
}

function formatConfidence(value) {
  if (value === "exact") {
    return "Exacta";
  }
  if (value === "approximate") {
    return "Aproximada";
  }
  if (value === "partial") {
    return "Parcial";
  }
  return value ? String(value).replaceAll("-", " ") : "No disponible";
}

function formatTeamSide(value) {
  const normalized = String(value || "").toLowerCase();
  if (normalized === "allies" || normalized === "allied") {
    return "Aliados";
  }
  if (normalized === "axis") {
    return "Axis";
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

function formatMatchResult(result) {
  if (hasMatchScore(result)) {
    return `${formatWinner(result.winner)} (${formatScore(result)})`;
  }
  return result?.winner ? formatWinner(result.winner) : "Resultado no disponible";
}

function formatWinner(value) {
  const normalized = String(value || "").toLowerCase();
  if (normalized === "allies" || normalized === "allied") {
    return "Aliados";
  }
  if (normalized === "axis") {
    return "Axis";
  }
  if (normalized === "draw") {
    return "Empate";
  }
  return "No disponible";
}

function formatScore(result) {
  if (!hasMatchScore(result)) {
    return "Resultado no disponible";
  }
  return `${Number(result.allied_score)} - ${Number(result.axis_score)}`;
}

function hasMatchScore(result) {
  return (
    Number.isFinite(Number(result?.allied_score)) &&
    Number.isFinite(Number(result?.axis_score))
  );
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

function formatEventType(value) {
  const normalized = String(value || "").replaceAll("_", " ").replaceAll("-", " ");
  if (!normalized) {
    return "Evento";
  }
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
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
  if (item.timestamp_confidence === "server-time-only") {
    return "No disponible";
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
