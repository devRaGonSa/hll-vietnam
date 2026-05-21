const CURRENT_MATCH_POLL_INTERVAL_MS = 30 * 1000;
const CURRENT_MATCH_SERVERS = Object.freeze({
  "comunidad-hispana-01": "Comunidad Hispana #01",
  "comunidad-hispana-02": "Comunidad Hispana #02",
});
const CURRENT_MATCH_SCOREBOARDS = Object.freeze({
  "comunidad-hispana-01": "https://scoreboard.comunidadhll.es",
  "comunidad-hispana-02": "https://scoreboard.comunidadhll.es:5443",
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
    mapHero: document.getElementById("current-match-map-hero"),
    mapImage: document.getElementById("current-match-map-image"),
    mapPlaceholder: document.getElementById("current-match-map-placeholder"),
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
  const rawServerName = data.server_name || data.server_slug || "Servidor no disponible";
  const serverName = formatServerDisplayName(data, rawServerName);
  const mapName = data.map_pretty_name || data.map || "Mapa no disponible";
  const scoreboardUrl = resolveTrustedScoreboardUrl(data);
  nodes.title.textContent = mapName;
  nodes.summary.textContent = serverName;
  nodes.note.textContent = data.found
    ? "Lectura en vivo recibida. La pagina se actualiza cada 30 segundos."
    : "Todavia no hay snapshot live disponible para este servidor.";
  nodes.scoreboard.href = scoreboardUrl || "./index.html";
  nodes.scoreboard.hidden = !scoreboardUrl;
  renderMapHero(data, mapName, nodes);
  nodes.grid.innerHTML = renderLiveScoreboard(data, { mapName, serverName });
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
  renderMapHero({}, "Mapa no disponible", nodes);
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
  if (data.scope === "no-current-match-events") {
    state.byId.clear();
  }
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
  nodes.feedState.textContent = formatKillFeedCoverage(data.scope);
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

function renderCompactMeta(label, value) {
  return `
    <article>
      <span>${escapeHtml(label)}</span>
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
  if (!isNumericValue(players) || !isNumericValue(maxPlayers)) {
    return "No disponible";
  }
  return `${Number(players)} / ${Number(maxPlayers)}`;
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

function renderLiveScoreboard(data, { mapName, serverName }) {
  const scoreKnown = hasKnownScore(data);
  const scoreMarkup = scoreKnown
    ? `${Number(data.allied_score)} : ${Number(data.axis_score)}`
    : "Marcador no disponible";
  const scoreClass = scoreKnown ? "" : " current-match-scoreboard-message";
  const metadata = [
    ["Servidor", serverName],
    ["Mapa", mapName],
    ["Modo", formatGameMode(data.game_mode)],
  ];
  if (data.started_at) {
    metadata.push(["Inicio", formatTimestamp(data.started_at)]);
  }
  const remainingTime = Number(data.remaining_match_time_seconds);
  if (Number.isFinite(remainingTime) && remainingTime > 0) {
    metadata.push(["Tiempo restante", formatDuration(remainingTime)]);
  }
  const matchTime = Number(data.match_time_seconds);
  if (Number.isFinite(matchTime) && matchTime > 0) {
    metadata.push(["Tiempo de partida", formatDuration(matchTime)]);
  }
  metadata.push(["Jugadores", formatPlayerCount(data)]);
  metadata.push(["Actualizado", formatTimestamp(data.captured_at || data.updated_at)]);

  return `
    <section class="historical-scoreboard-layout" aria-label="Marcador en vivo">
      <div class="historical-scoreboard-layout__main">
        ${renderLiveSide("historical-scoreboard-side--allied", "Aliados", "./assets/img/factions/us.webp")}
        <div class="historical-scoreboard-center">
          <span class="historical-scoreboard-center__timer">${escapeHtml(formatStatus(data.status))}</span>
          <strong class="historical-scoreboard-center__score${scoreClass}">${escapeHtml(scoreMarkup)}</strong>
          <span class="historical-scoreboard-center__map">${escapeHtml(mapName)}</span>
          <span class="historical-scoreboard-center__mode">${escapeHtml(formatGameMode(data.game_mode))}</span>
        </div>
        ${renderLiveSide("historical-scoreboard-side--axis", "Eje", "./assets/img/factions/germany.webp")}
      </div>
      <div class="historical-scoreboard-layout__meta">
        ${metadata.map(([label, value]) => renderCompactMeta(label, value)).join("")}
      </div>
    </section>
  `;
}

function renderLiveSide(sideClass, label, emblem) {
  return `
    <div class="historical-scoreboard-side ${sideClass}">
      <img
        class="historical-scoreboard-side__emblem"
        src="${escapeHtml(emblem)}"
        alt="${escapeHtml(label)}"
        width="128"
        height="128"
        loading="lazy"
        decoding="async"
        onerror="this.hidden = true; this.closest('.historical-scoreboard-side').classList.add('is-emblem-missing');"
      />
      <div class="historical-scoreboard-side__text">
        <strong>${escapeHtml(label)}</strong>
      </div>
    </div>
  `;
}

function renderMapHero(data, mapName, nodes) {
  if (!nodes.mapImage || !nodes.mapPlaceholder) {
    return;
  }
  const mapImagePath = resolveMapImagePath(data, mapName);
  nodes.mapPlaceholder.hidden = Boolean(mapImagePath);
  nodes.mapImage.hidden = !mapImagePath;
  if (!mapImagePath) {
    nodes.mapImage.removeAttribute("src");
    nodes.mapImage.alt = "";
    return;
  }
  nodes.mapImage.src = mapImagePath;
  nodes.mapImage.alt = mapName;
  nodes.mapImage.onerror = () => {
    nodes.mapImage.removeAttribute("src");
    nodes.mapImage.hidden = true;
    nodes.mapPlaceholder.hidden = false;
  };
}

function resolveMapImagePath(data, mapName) {
  const normalizedMap = normalizeLookupText(
    `${data.map_id || ""} ${data.map || ""} ${data.map_pretty_name || ""} ${mapName || ""}`,
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

function resolveTrustedScoreboardUrl(data) {
  const trustedUrl = CURRENT_MATCH_SCOREBOARDS[data.server_slug];
  return data.public_scoreboard_url === trustedUrl ? trustedUrl : "";
}

function formatServerDisplayName(data, fallbackName) {
  const trustedName = CURRENT_MATCH_SERVERS[data.server_slug];
  if (trustedName) {
    return trustedName;
  }

  const normalized = String(fallbackName || "").trim();
  const serverNumber = normalized.match(/^#0?([1-9])\b/);
  if (serverNumber) {
    return `Comunidad Hispana #${serverNumber[1].padStart(2, "0")}`;
  }

  return normalized || "Servidor no disponible";
}

function hasKnownScore(data) {
  return isNumericValue(data.allied_score) && isNumericValue(data.axis_score);
}

function formatPlayerCount(data) {
  if (!isReliablePlayerCount(data.player_count_quality)) {
    return "No verificado";
  }
  return formatPlayers(data.players, data.max_players);
}

function isReliablePlayerCount(quality) {
  return quality === "reliable" || quality === "a2s-query";
}

function isNumericValue(value) {
  return value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value));
}

function formatGameMode(value) {
  if (!value) {
    return "No disponible";
  }
  const normalized = String(value).replaceAll("_", " ").replaceAll("-", " ");
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function formatDuration(value) {
  const seconds = Number(value);
  if (!Number.isFinite(seconds) || seconds <= 0) {
    return "No disponible";
  }
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return hours > 0 ? `${hours} h ${remainingMinutes} min` : `${minutes} min`;
}

function formatKillFeedCoverage(scope) {
  if (scope === "open-admin-log-match-window") {
    return "Bajas detectadas en la partida actual.";
  }
  if (scope === "recent-admin-log-window") {
    return "Cobertura parcial desde AdminLog reciente.";
  }
  return "Todavia no se han detectado bajas en esta partida.";
}

function normalizeLookupText(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
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
