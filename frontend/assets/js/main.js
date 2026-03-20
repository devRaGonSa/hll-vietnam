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
  const serversList = document.getElementById("servers-list");
  const serversBadge = document.getElementById("servers-badge");

  updateBackendStatus(statusNode, "Backend comprobando", "status-chip--idle");
  setServersDataState(serversBadge, { timestampLabel: "" });
  bindCopyAddressActions();

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
    updateBackendStatus(
      statusNode,
      "Modo estatico activo",
      "status-chip--fallback",
    );
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
  serversList,
  serversBadge,
) {
  if (!serversTitle || !serversList || !serversBadge) {
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
    setServersDataState(serversBadge, deriveSnapshotState(serversData));

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

  const hasTimestamp = typeof state.timestampLabel === "string" && state.timestampLabel;
  badgeNode.textContent = hasTimestamp
    ? `Actualizado ${state.timestampLabel}`
    : "Actualizado no disponible";
  badgeNode.classList.toggle("status-chip--ok", Boolean(hasTimestamp));
  badgeNode.classList.toggle("status-chip--fallback", !hasTimestamp);
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
  const address = getServerAddress(server);
  const actionMarkup = renderServerAction(server);
  const cardVariantClass = isRealSnapshot ? "server-card--real" : "server-card--reference";
  const quickFacts = renderQuickFacts([
    { label: "Mapa", value: currentMap },
    { label: "Region", value: region },
    { label: "Direccion", value: address || "No disponible" },
  ]);

  return `
    <article class="server-card server-card--stats ${cardVariantClass}">
      <div class="server-card__top server-card__top--stats">
        <div class="server-card__identity">
          <p class="server-card__eyebrow">${isRealSnapshot ? "Servidor de comunidad" : "Referencia actual"}</p>
          <h3>${escapeHtml(serverName)}</h3>
        </div>
        <div class="server-card__status-column">
          <span class="server-state ${stateClass}">${escapeHtml(statusLabel)}</span>
          <p class="server-card__population">${escapeHtml(`${players} / ${maxPlayers}`)}</p>
          ${actionMarkup}
        </div>
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

function renderServerAction(server) {
  const address = getServerAddress(server);
  if (!address) {
    return "";
  }

  return `
    <div class="server-card__actions">
      <button
        class="server-copy-button"
        type="button"
        data-copy-address="${escapeHtml(address)}"
        data-default-label="Copiar IP"
      >
        Copiar IP
      </button>
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

function bindCopyAddressActions() {
  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-copy-address]");
    if (!(button instanceof HTMLButtonElement)) {
      return;
    }

    const address = button.dataset.copyAddress || "";
    if (!address) {
      return;
    }

    const defaultLabel = button.dataset.defaultLabel || "Copiar IP";
    button.disabled = true;

    try {
      await copyText(address);
      button.textContent = "IP copiada";
    } catch (error) {
      console.warn("Could not copy server address", error);
      button.textContent = "Copia manual";
    } finally {
      window.setTimeout(() => {
        button.textContent = defaultLabel;
        button.disabled = false;
      }, 1800);
    }
  });
}

async function copyText(value) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(value);
    return;
  }

  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "absolute";
  textarea.style.left = "-9999px";
  document.body.append(textarea);
  textarea.select();

  const copied = document.execCommand("copy");
  textarea.remove();

  if (!copied) {
    throw new Error("Clipboard copy command failed");
  }
}

function getServerAddress(server) {
  const host = typeof server?.host === "string" ? server.host.trim() : "";
  const gamePort = Number(server?.game_port);
  if (!host || !Number.isInteger(gamePort) || gamePort <= 0) {
    return "";
  }

  return `${host}:${gamePort}`;
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
  return {
    timestampLabel: serversData?.last_snapshot_at
      ? formatTimestamp(serversData.last_snapshot_at)
      : "",
  };
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
