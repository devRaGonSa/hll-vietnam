const CURRENT_MATCH_POLL_INTERVAL_MS = 30 * 1000;
const CURRENT_MATCH_SERVERS = Object.freeze({
  "comunidad-hispana-01": "Comunidad Hispana #01",
  "comunidad-hispana-02": "Comunidad Hispana #02",
});

document.addEventListener("DOMContentLoaded", () => {
  const params = new URLSearchParams(window.location.search);
  const serverSlug = params.get("server") || "";
  const nodes = {
    title: document.getElementById("current-match-title"),
    summary: document.getElementById("current-match-summary"),
    history: document.getElementById("current-match-history"),
    scoreboard: document.getElementById("current-match-scoreboard"),
    note: document.getElementById("current-match-note"),
    state: document.getElementById("current-match-state"),
    grid: document.getElementById("current-match-grid"),
    feedTitle: document.getElementById("current-match-feed-title"),
  };
  const backendBaseUrl =
    document.body.dataset.backendBaseUrl || "http://127.0.0.1:8000";

  if (!CURRENT_MATCH_SERVERS[serverSlug]) {
    renderUnsupportedServer(nodes);
    return;
  }

  nodes.history.href = `./historico.html?server=${encodeURIComponent(serverSlug)}`;
  const killFeedState = initializeKillFeed(nodes);
  let refreshInFlight = false;
  const refresh = async () => {
    if (refreshInFlight) {
      return;
    }
    refreshInFlight = true;
    try {
      await Promise.allSettled([
        loadCurrentMatch({ backendBaseUrl, serverSlug, nodes }),
        loadKillFeed({ backendBaseUrl, serverSlug, nodes, killFeedState }),
      ]);
    } finally {
      refreshInFlight = false;
    }
  };

  void refresh();
  window.setInterval(() => {
    void refresh();
  }, CURRENT_MATCH_POLL_INTERVAL_MS);
});

async function loadCurrentMatch({ backendBaseUrl, serverSlug, nodes }) {
  try {
    const payload = await fetchJson(
      `${backendBaseUrl}/api/current-match?server=${encodeURIComponent(serverSlug)}`,
    );
    renderCurrentMatch(payload?.data || {}, nodes);
  } catch (error) {
    nodes.note.textContent = "Se conserva el ultimo estado visible si estaba disponible.";
    setState(nodes.state, "No se pudo actualizar la partida actual.", true);
  }
}

async function loadKillFeed({ backendBaseUrl, serverSlug, nodes, killFeedState }) {
  try {
    const payload = await fetchJson(
      `${backendBaseUrl}/api/current-match/kills?server=${encodeURIComponent(serverSlug)}&limit=30`,
    );
    renderKillFeed(payload?.data || {}, nodes, killFeedState);
  } catch (error) {
    setState(nodes.feedState, "No se pudo actualizar el feed de combate.", true);
  }
}

function renderCurrentMatch(data, nodes) {
  const serverName = data.server_name || data.server_slug || "Servidor no disponible";
  const mapName = data.map || "Mapa no disponible";
  nodes.title.textContent = serverName;
  nodes.summary.textContent = mapName;
  nodes.note.textContent = data.found
    ? "Snapshot en vivo recibido. La pagina se actualiza cada 30 segundos."
    : "Todavia no hay snapshot live disponible para este servidor.";
  nodes.scoreboard.href = data.public_scoreboard_url;
  nodes.scoreboard.hidden = !data.public_scoreboard_url;
  nodes.grid.innerHTML = [
    renderStat("Estado", formatStatus(data.status)),
    renderStat("Mapa", mapName),
    renderStat("Modo", data.game_mode || "No disponible"),
    renderStat("Inicio", formatTimestamp(data.started_at)),
    renderStat("Jugadores", formatPlayers(data.players, data.max_players)),
    renderStat("Marcador aliado", formatScore(data.allied_score)),
    renderStat("Marcador eje", formatScore(data.axis_score)),
    renderStat("Actualizado", formatTimestamp(data.captured_at || data.updated_at)),
  ].join("");
  nodes.state.hidden = true;
  nodes.grid.hidden = false;
}

function renderUnsupportedServer(nodes) {
  nodes.title.textContent = "Servidor no soportado";
  nodes.summary.textContent =
    "Abre esta vista desde una tarjeta activa de Comunidad Hispana.";
  nodes.note.textContent = "";
  nodes.scoreboard.hidden = true;
  nodes.grid.hidden = true;
  setState(nodes.state, "No se puede consultar la partida solicitada.", true);
}

function initializeKillFeed(nodes) {
  const feedShell = nodes.feedTitle?.closest(".panel__shell");
  if (feedShell) {
    feedShell.insertAdjacentHTML(
      "beforeend",
      `
        <p class="historical-state" id="current-match-feed-state" aria-live="polite">
          Cargando feed de combate...
        </p>
        <div class="historical-match-list" id="current-match-feed-list"></div>
      `,
    );
  }
  nodes.feedState = document.getElementById("current-match-feed-state");
  nodes.feedList = document.getElementById("current-match-feed-list");
  return {
    byId: new Map(),
  };
}

function renderKillFeed(data, nodes, state) {
  const incoming = Array.isArray(data.items) ? data.items : [];
  incoming.forEach((event) => {
    if (event?.event_id) {
      state.byId.set(event.event_id, event);
    }
  });
  const events = [...state.byId.values()].sort(compareKillFeedEvents).slice(0, 30);
  if (events.length === 0) {
    nodes.feedList.innerHTML = "";
    setState(nodes.feedState, "Todavia no se han detectado bajas en esta partida.");
    return;
  }
  nodes.feedList.innerHTML = events.map(renderKillFeedRow).join("");
  nodes.feedState.textContent =
    data.scope === "open-admin-log-match-window"
      ? "Bajas del tramo abierto detectado por AdminLog."
      : "Bajas recientes de AdminLog con cobertura parcial.";
  nodes.feedState.classList.remove("historical-state--error");
}

function compareKillFeedEvents(left, right) {
  const rightTime = Number(right.server_time);
  const leftTime = Number(left.server_time);
  if (Number.isFinite(rightTime) && Number.isFinite(leftTime) && rightTime !== leftTime) {
    return rightTime - leftTime;
  }
  return String(right.event_timestamp || "").localeCompare(String(left.event_timestamp || ""));
}

function renderKillFeedRow(event) {
  const teamkillBadge = event.is_teamkill
    ? '<span class="status-chip status-chip--fallback">TK</span>'
    : "";
  const eventTime = formatEventTime(event);
  return `
    <article class="historical-match-card">
      <div class="historical-match-card__top">
        <div class="historical-match-card__title">
          <p>${escapeHtml(eventTime)}</p>
          <strong>${escapeHtml(event.killer_name || "Jugador no disponible")}</strong>
        </div>
        ${teamkillBadge}
      </div>
      <p>
        ${escapeHtml(event.weapon || "Arma no disponible")}
        -> ${escapeHtml(event.victim_name || "Objetivo no disponible")}
      </p>
    </article>
  `;
}

function formatEventTime(event) {
  const timestamp = formatTimestamp(event.event_timestamp);
  if (timestamp !== "No disponible") {
    return timestamp;
  }
  return Number.isFinite(Number(event.server_time))
    ? `Tiempo servidor ${Number(event.server_time)}`
    : "Tiempo no disponible";
}

function renderStat(label, value) {
  return `
    <article class="historical-stat-card">
      <p>${escapeHtml(label)}</p>
      <strong>${escapeHtml(value)}</strong>
    </article>
  `;
}

function formatStatus(value) {
  if (value === "online") {
    return "Online";
  }
  if (value === "offline") {
    return "Offline";
  }
  return "No disponible";
}

function formatPlayers(players, maxPlayers) {
  if (!Number.isFinite(Number(players)) || !Number.isFinite(Number(maxPlayers))) {
    return "No disponible";
  }
  return `${Number(players)} / ${Number(maxPlayers)}`;
}

function formatScore(value) {
  return Number.isFinite(Number(value)) ? String(Number(value)) : "No disponible";
}

function formatTimestamp(value) {
  if (!value) {
    return "No disponible";
  }
  const timestamp = new Date(value);
  if (Number.isNaN(timestamp.getTime())) {
    return "No disponible";
  }
  return new Intl.DateTimeFormat("es-ES", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(timestamp);
}

function setState(node, message, isError = false) {
  node.textContent = message;
  node.hidden = false;
  node.classList.toggle("historical-state--error", isError);
}

async function fetchJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed with ${response.status}`);
  }
  return response.json();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
