// Progressive enhancement for local frontend-backend checks.
const DEFAULT_SERVER_POLL_INTERVAL_MS = 120 * 1000;

document.addEventListener("DOMContentLoaded", () => {
  console.info("HLL Vietnam frontend ready");

  const backendBaseUrl =
    document.body.dataset.backendBaseUrl || "http://127.0.0.1:8000";
  const serverPollIntervalMs = getServerPollIntervalMs(
    document.body.dataset.serverRefreshMs,
  );
  const statusNode = document.getElementById("backend-status");
  const trailerFrame = document.getElementById("trailer-frame");
  const trailerTitle = document.getElementById("trailer-title");
  const serversTitle = document.getElementById("servers-title");
  const serversNote = document.getElementById("servers-note");
  const serversList = document.getElementById("servers-list");
  const serversBadge = document.getElementById("servers-badge");

  updateBackendStatus(statusNode, "Backend comprobando", "status-chip--idle");

  setServersDataState(serversBadge, { kind: "fallback" });

  let serverRefreshInFlight = false;
  const refreshServers = async () => {
    if (serverRefreshInFlight) {
      return;
    }

    serverRefreshInFlight = true;
    try {
      await hydrateServers(
        backendBaseUrl,
        serversTitle,
        serversNote,
        serversList,
        serversBadge,
      );
    } finally {
      serverRefreshInFlight = false;
    }
  };

  Promise.allSettled([
    fetchHealth(backendBaseUrl, statusNode),
    hydrateTrailer(backendBaseUrl, trailerFrame, trailerTitle),
    refreshServers(),
  ]).catch((error) => {
    console.warn("Progressive enhancement failed", error);
  });

  if (serverPollIntervalMs > 0) {
    window.setInterval(() => {
      void refreshServers();
    }, serverPollIntervalMs);
  }
});

async function fetchHealth(backendBaseUrl, statusNode) {
  try {
    const response = await fetch(`${backendBaseUrl}/health`);
    if (!response.ok) {
      throw new Error(`Health request failed with ${response.status}`);
    }

    const payload = await response.json();
    if (payload.status === "ok") {
      updateBackendStatus(statusNode, "Backend operativo", "status-chip--ok");
      return;
    }

    throw new Error("Unexpected health payload");
  } catch (error) {
    console.warn("Backend health check unavailable", error);
    updateBackendStatus(statusNode, "Modo estatico activo", "status-chip--fallback");
  }
}

async function hydrateTrailer(backendBaseUrl, trailerFrame, trailerTitle) {
  if (!trailerFrame || !trailerTitle) {
    return;
  }

  try {
    const response = await fetch(`${backendBaseUrl}/api/trailer`);
    if (!response.ok) {
      throw new Error(`Trailer request failed with ${response.status}`);
    }

    const payload = await response.json();
    const trailer = payload.data;
    if (!trailer || !trailer.video_url || !trailer.title) {
      throw new Error("Trailer payload incomplete");
    }

    trailerFrame.src = trailer.video_url;
    trailerFrame.title = trailer.title;
    trailerTitle.textContent = trailer.title;
  } catch (error) {
    console.warn("Trailer placeholder remains static", error);
  }
}

async function hydrateServers(
  backendBaseUrl,
  serversTitle,
  serversNote,
  serversList,
  serversBadge,
) {
  if (!serversTitle || !serversNote || !serversList || !serversBadge) {
    return;
  }

  try {
    const payload = await fetchJson(`${backendBaseUrl}/api/servers`);
    const serversData = payload.data;
    if (!serversData || !Array.isArray(serversData.items)) {
      throw new Error("Servers payload incomplete");
    }

    serversTitle.textContent =
      serversData.title || "Estado actual de servidores";
    setServersDataState(
      serversBadge,
      deriveSnapshotState(serversData),
    );
    serversNote.textContent = buildServersNote(serversData);

    if (serversData.items.length === 0) {
      serversList.innerHTML =
        '<p class="servers-empty">Informacion de servidores disponible mas adelante.</p>';
      return;
    }

    const visibleItems = selectPrimaryServerItems(serversData.items);
    serversList.innerHTML = renderServerSections(visibleItems);
  } catch (error) {
    console.warn("Servers panel remains on static fallback", error);
  }
}

function updateBackendStatus(statusNode, label, stateClass) {
  if (!statusNode) {
    return;
  }

  statusNode.textContent = label;
  statusNode.classList.remove("status-chip--ok", "status-chip--fallback");
  if (stateClass) {
    statusNode.classList.add(stateClass);
  }
}

function setServersDataState(badgeNode, state) {
  if (!badgeNode) {
    return;
  }

  if (state.kind === "live") {
    badgeNode.textContent = state.timestampLabel
      ? `Actualizado ${state.timestampLabel}`
      : "Datos en vivo";
    badgeNode.classList.remove("status-chip--fallback");
    badgeNode.classList.add("status-chip--ok");
    return;
  }

  if (state.kind === "historical") {
    badgeNode.textContent = state.timestampLabel
      ? `Snapshot ${state.timestampLabel}`
      : "Actividad reciente";
    badgeNode.classList.remove("status-chip--fallback");
    badgeNode.classList.add("status-chip--ok");
    return;
  }

  badgeNode.textContent = "Respaldo controlado";
  badgeNode.classList.remove("status-chip--ok");
  badgeNode.classList.add("status-chip--fallback");
}

function renderServerCard(server) {
  const serverName = server.server_name || "Servidor sin nombre";
  const serverStatus =
    server.status === "online" ? "Online" : server.status === "offline" ? "Offline" : "Estado pendiente";
  const stateClass =
    server.status === "online" ? "server-state--online" : "server-state--offline";
  const currentMap = server.current_map || "Sin mapa disponible";
  const region = server.region || "Region pendiente";
  const players = Number.isFinite(server.players) ? server.players : 0;
  const maxPlayers = Number.isFinite(server.max_players) ? server.max_players : 0;
  const occupancy = getPopulationPercent(players, maxPlayers);
  const sourceLabel = isRealA2SSnapshot(server) ? "Snapshot activo" : "Referencia actual";

  return `
    <article class="server-card">
      <div class="server-card__top">
        <div class="server-card__identity">
          <p class="server-card__eyebrow">${escapeHtml(sourceLabel)}</p>
          <h3>${escapeHtml(serverName)}</h3>
        </div>
        <div class="server-card__status-column">
          <span class="server-state ${stateClass}">${escapeHtml(serverStatus)}</span>
          <p class="server-card__population">${players} / ${maxPlayers}</p>
        </div>
      </div>
      <div class="server-card__load" aria-hidden="true">
        <span style="width: ${occupancy}%"></span>
      </div>
      <dl class="server-card__stats">
        <div class="server-stat server-stat--players">
          <dt>Jugadores</dt>
          <dd>${players} / ${maxPlayers}</dd>
        </div>
        <div class="server-stat">
          <dt>Mapa</dt>
          <dd>${escapeHtml(currentMap)}</dd>
        </div>
        <div class="server-stat">
          <dt>Region</dt>
          <dd>${escapeHtml(region)}</dd>
        </div>
      </dl>
    </article>
  `;
}

function renderServerStatsCard(server) {
  const serverName = server.server_name || "Servidor sin nombre";
  const statusLabel = formatServerStatus(server.status);
  const stateClass =
    server.status === "online" ? "server-state--online" : "server-state--offline";
  const isRealSnapshot = server.snapshot_origin === "real-a2s";
  const currentMap = server.current_map || "Sin mapa disponible";
  const region = server.region || "Region pendiente";
  const players = Number.isFinite(server.players) ? server.players : 0;
  const maxPlayers = Number.isFinite(server.max_players) ? server.max_players : 0;
  const occupancy = getPopulationPercent(players, maxPlayers);
  const updatedAt = server.captured_at
    ? formatTimestamp(server.captured_at)
    : "Sin captura reciente";
  const updatedAgo = formatElapsedMinutes(server.history_summary?.minutes_since_last_capture);
  const connectAction = renderConnectAction(server);
  const cardVariantClass = isRealSnapshot ? "server-card--real" : "server-card--reference";
  const quickFacts = renderQuickFacts([
    { label: "Mapa", value: currentMap },
    { label: "Region", value: region },
    { label: "Ultima captura", value: updatedAgo || updatedAt },
  ]);

  return `
    <article class="server-card server-card--stats ${cardVariantClass}">
      <div class="server-card__top server-card__top--stats">
        <div class="server-card__identity">
          <p class="server-card__eyebrow">${isRealSnapshot ? "Snapshot activo" : "Referencia actual"}</p>
          <h3>${escapeHtml(serverName)}</h3>
        </div>
        <div class="server-card__status-column">
          <span class="server-state ${stateClass}">${escapeHtml(statusLabel)}</span>
          <p class="server-card__population">${escapeHtml(`${players} / ${maxPlayers}`)}</p>
          ${connectAction}
        </div>
      </div>
      <div class="server-card__load" aria-hidden="true">
        <span style="width: ${occupancy}%"></span>
      </div>
      ${quickFacts}
    </article>
  `;
}

function renderServerSections(latestItems) {
  return `
    <div class="servers-grid servers-grid--section">
      ${latestItems.map((server) => renderServerStatsCard(server)).join("")}
    </div>
  `;
}

function renderConnectAction(server) {
  if (!server || !isRealA2SSnapshot(server)) {
    return "";
  }

  const host = typeof server.host === "string" ? server.host.trim() : "";
  const gamePort = Number.isInteger(server.game_port) ? server.game_port : Number(server.game_port);
  if (!host || !Number.isInteger(gamePort) || gamePort <= 0) {
    return "";
  }

  const connectUrl = `steam://connect/${host}:${gamePort}`;
  return `
    <div class="server-card__actions">
      <a class="server-connect-button" href="${escapeHtml(connectUrl)}">Conectar</a>
    </div>
  `;
}

function renderQuickFacts(items) {
  return `
    <div class="server-card__quickfacts">
      ${items
        .map(
          (item) => `
            <article class="server-card__quickfact">
              <p>${escapeHtml(item.label)}</p>
              <strong>${escapeHtml(item.value)}</strong>
            </article>
          `,
        )
        .join("")}
    </div>
  `;
}

function selectPrimaryServerItems(items) {
  if (!Array.isArray(items)) {
    return [];
  }

  const realItems = items.filter(isRealA2SSnapshot);
  return realItems.length > 0 ? realItems : items;
}

function isRealA2SSnapshot(item) {
  return item?.snapshot_origin === "real-a2s";
}

function deriveSnapshotState(serversData) {
  const timestampLabel = serversData?.last_snapshot_at
    ? formatTimestamp(serversData.last_snapshot_at)
    : "";

  if (!serversData) {
    return { kind: "fallback", timestampLabel };
  }

  if (serversData.freshness === "fresh" && serversData.source === "real-time-a2s-refresh") {
    return { kind: "live", timestampLabel };
  }

  if (Array.isArray(serversData.items) && serversData.items.length > 0) {
    return { kind: "historical", timestampLabel };
  }

  return { kind: "fallback", timestampLabel };
}

function buildServersNote(serversData) {
  const lastSnapshotLabel = serversData.last_snapshot_at
    ? formatTimestamp(serversData.last_snapshot_at)
    : "sin timestamp disponible";
  const snapshotAgeLabel = formatSnapshotAge(serversData.snapshot_age_seconds);

  if (serversData.freshness === "fresh") {
    return `Estado real consultado desde backend. Ultimo snapshot: ${lastSnapshotLabel}${snapshotAgeLabel ? `, ${snapshotAgeLabel}.` : "."}`;
  }

  if (Array.isArray(serversData.items) && serversData.items.length > 0) {
    return `El backend no pudo refrescar ahora mismo y muestra el ultimo snapshot valido. Captura: ${lastSnapshotLabel}${snapshotAgeLabel ? `, ${snapshotAgeLabel}.` : "."}`;
  }

  return "El backend no pudo obtener un snapshot valido de los 2 servidores en este momento.";
}

function formatServerStatus(status) {
  if (status === "online") {
    return "Online";
  }

  if (status === "offline") {
    return "Offline";
  }

  return "Estado pendiente";
}

function formatTimestamp(timestamp) {
  const value = new Date(timestamp);
  if (Number.isNaN(value.getTime())) {
    return "Fecha no disponible";
  }

  return new Intl.DateTimeFormat("es-ES", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(value);
}

function formatElapsedMinutes(minutes) {
  if (!Number.isFinite(minutes)) {
    return "";
  }

  if (minutes < 1) {
    return "hace menos de 1 min";
  }

  if (minutes < 60) {
    return `hace ${minutes} min`;
  }

  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `hace ${hours} h`;
  }

  const days = Math.floor(hours / 24);
  return `hace ${days} d`;
}

function formatSnapshotAge(snapshotAgeSeconds) {
  if (!Number.isFinite(snapshotAgeSeconds)) {
    return "";
  }

  if (snapshotAgeSeconds < 60) {
    return `hace ${snapshotAgeSeconds} s`;
  }

  const wholeMinutes = Math.floor(snapshotAgeSeconds / 60);
  if (wholeMinutes < 60) {
    return `hace ${wholeMinutes} min`;
  }

  const wholeHours = Math.floor(wholeMinutes / 60);
  return `hace ${wholeHours} h`;
}

function getPopulationPercent(players, maxPlayers) {
  if (!Number.isFinite(players) || !Number.isFinite(maxPlayers) || maxPlayers <= 0) {
    return 0;
  }

  return Math.max(0, Math.min(100, Math.round((players / maxPlayers) * 100)));
}

function getServerPollIntervalMs(rawValue) {
  const parsedValue = Number(rawValue);
  if (!Number.isFinite(parsedValue) || parsedValue <= 0) {
    return DEFAULT_SERVER_POLL_INTERVAL_MS;
  }

  return parsedValue;
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
