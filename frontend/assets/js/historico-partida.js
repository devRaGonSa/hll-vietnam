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
  { titleNode, summaryNode, noteNode, stateNode, gridNode, actionsNode },
) {
  const mapName = item.map?.pretty_name || item.map?.name || "Mapa no disponible";
  const serverName = item.server?.name || "Servidor no disponible";
  titleNode.textContent = mapName;
  summaryNode.textContent = `${serverName} | Partida ${item.match_id || "sin id"}`;
  noteNode.textContent = buildDetailNote(item);
  gridNode.innerHTML = [
    renderDetailCard("Servidor", serverName),
    renderDetailCard("Inicio", formatTimestamp(item.started_at)),
    renderDetailCard("Cierre", formatTimestamp(item.closed_at || item.ended_at)),
    renderDetailCard("Duracion", formatDuration(item.duration_seconds)),
    renderDetailCard("Jugadores", formatPlayerCount(item)),
    renderDetailCard("Marcador", formatScore(item.result)),
    renderDetailCard("Resultado", formatMatchResult(item.result)),
    renderDetailCard("Base de captura", formatCaptureBasis(item.capture_basis)),
  ].join("");
  renderActions(item, actionsNode);
  stateNode.hidden = true;
  gridNode.hidden = false;
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
