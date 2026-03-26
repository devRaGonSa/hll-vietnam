// Progressive enhancement for local frontend-backend checks.
const DEFAULT_SERVER_POLL_INTERVAL_MS = 300 * 1000;
const SERVER_HISTORY_URLS_FALLBACK = Object.freeze({
  "comunidad-hispana-01": "https://scoreboard.comunidadhll.es/games",
  "comunidad-hispana-02": "https://scoreboard.comunidadhll.es:5443/games",
  "comunidad-hispana-03": "https://scoreboard.comunidadhll.es:3443/games",
});
const COMMUNITY_CLANS = Object.freeze([
  {
    name: "LCM",
    badge: "Clan CH",
    description:
      "Clan activo de la comunidad, con acceso directo a su discord.",
    logoSrc: "./assets/img/clans/lcm.png",
    logoAlt: "Logo de LCM",
    logoClassName: "",
    discordUrl: "https://discord.gg/9F9S353QZv",
    discordLabel: "Abrir Discord",
  },
  {
    name: "La 129",
    badge: "Clan CH",
    description:
      "Clan activo de la comunidad, con acceso directo a su discord.",
    logoSrc: "./assets/img/clans/la129.png",
    logoAlt: "Logo de La 129",
    logoClassName: "clan-card__logo--wide",
    discordUrl: "",
    discordLabel: "Proximamente",
  },
  {
    name: "250 Hispania",
    badge: "Clan CH",
    description:
      "Clan activo de la comunidad, con acceso directo a su discord.",
    logoSrc: "./assets/img/clans/250hispania-shield.png",
    logoAlt: "Escudo de 250 Hispania",
    logoClassName: "clan-card__logo--shield",
    discordUrl: "https://discord.gg/3E62Yb6Aw3",
    discordLabel: "Abrir Discord",
  },
  {
    name: "H9H",
    badge: "Clan CH",
    description:
      "Clan activo de la comunidad, con acceso directo a su discord.",
    logoSrc: "./assets/img/clans/h9h.png",
    logoAlt: "",
    logoClassName: "",
    discordUrl: "https://discord.gg/tYnXK7MQjB",
    discordLabel: "Abrir Discord",
    placeholderLabel: "H9H",
  },
  {
    name: "BxB",
    badge: "Clan CH",
    description:
      "Clan activo de la comunidad, son raretes.",
    logoSrc: "./assets/img/clans/bxb.png",
    logoAlt: "Logo de BxB",
    logoClassName: "",
    discordUrl: "",
    discordLabel: "Proximamente",
  },
  {
    name: "7dv",
    badge: "Clan CH",
    description:
      "Clan activo de la comunidad, con acceso directo a su discord.",
    logoSrc: "./assets/img/clans/7dv.png",
    logoAlt: "Logo de 7dv",
    logoClassName: "",
    discordUrl: "https://discord.gg/3sxNQZwrg6",
    discordLabel: "Abrir Discord",
  },
]);

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
  const communityClansList = document.getElementById("community-clans-list");

  updateBackendStatus(statusNode, "Backend comprobando", "status-chip--idle");
  setServersDataState(serversBadge, { timestampLabel: "" });
  renderServersLoadingState(serversList);
  hydrateCommunityClans(communityClansList);

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
    console.warn("Servers panel failed to hydrate with live data", error);
    serversList.innerHTML =
      '<p class="servers-empty">No se pudo cargar el estado real de servidores en este momento.</p>';
    setServersDataState(serversBadge, {
      label: "Actualizacion no disponible",
      isFresh: false,
    });
  }
}

function renderServersLoadingState(serversList) {
  if (!serversList) {
    return;
  }
  serversList.innerHTML = `
    <div class="servers-loading">
      <span class="servers-loading__pulse"></span>
      <p>Cargando estado real de servidores...</p>
    </div>
  `;
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

  const hasLabel = typeof state.label === "string" && state.label;
  badgeNode.textContent = hasLabel
    ? state.label
    : "Actualizado no disponible";
  badgeNode.classList.toggle("status-chip--ok", Boolean(hasLabel && state.isFresh));
  badgeNode.classList.toggle(
    "status-chip--fallback",
    !hasLabel || !state.isFresh,
  );
}

function renderServerStatsCard(server) {
  const serverName = server.server_name || "Servidor sin nombre";
  const statusLabel = formatServerStatus(server.status);
  const stateClass =
    server.status === "online" ? "server-state--online" : "server-state--offline";
  const isRealSnapshot = isRealLiveSnapshot(server);
  const currentMap = server.current_map || "Sin mapa disponible";
  const region = server.region || "Region pendiente";
  const players = Number.isFinite(server.players) ? server.players : 0;
  const maxPlayers = Number.isFinite(server.max_players) ? server.max_players : 0;
  const actionMarkup = renderServerAction(server);
  const cardVariantClass = isRealSnapshot ? "server-card--real" : "server-card--reference";
  const eyebrowLabel = isRealSnapshot ? "Servidor de comunidad" : "Referencia actual";
  const quickFacts = renderQuickFacts([
    { label: "Mapa", value: currentMap, valueClassName: "server-card__quickfact-value--map" },
    { label: "Region", value: region },
  ]);

  return `
    <article class="server-card server-card--stats ${cardVariantClass}">
      <div class="server-card__top server-card__top--stats">
        <div class="server-card__identity">
          <p class="server-card__eyebrow">${escapeHtml(eyebrowLabel)}</p>
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
  return latestItems.map((server) => renderServerStatsCard(server)).join("");
}

function renderServerAction(server) {
  const historyState = getServerHistoryState(server);
  if (!historyState.available) {
    return `
      <div class="server-card__actions">
        <span
          class="server-action-link server-action-link--disabled"
          aria-disabled="true"
        >
          Historico no disponible
        </span>
      </div>
    `;
  }

  const historyUrl = historyState.url;
  if (!historyUrl) {
    return "";
  }

  return `
    <div class="server-card__actions">
      <a
        class="server-action-link"
        href="${escapeHtml(historyUrl)}"
        target="_blank"
        rel="noreferrer"
      >
        Historico
      </a>
    </div>
  `;
}

function hydrateCommunityClans(listNode) {
  if (!listNode) {
    return;
  }

  listNode.innerHTML = shuffleItems(COMMUNITY_CLANS)
    .map((clan) => renderCommunityClanCard(clan))
    .join("");
}

function renderCommunityClanCard(clan) {
  const logoMarkup = renderClanLogo(clan);
  const discordMarkup = renderClanDiscordLink(clan);

  return `
    <article class="clan-card">
      <div class="clan-card__brand">
        ${logoMarkup}
        <div class="clan-card__copy">
          <p class="clan-card__eyebrow">${escapeHtml(clan.badge)}</p>
          <h3>${escapeHtml(clan.name)}</h3>
          <p>${escapeHtml(clan.description)}</p>
        </div>
      </div>
      ${discordMarkup}
    </article>
  `;
}

function renderClanLogo(clan) {
  const logoClassNames = ["clan-card__logo"];
  if (clan.logoClassName) {
    logoClassNames.push(clan.logoClassName);
  }

  if (clan.logoSrc) {
    return `
      <div class="${escapeHtml(logoClassNames.join(" "))}">
        <img
          src="${escapeHtml(clan.logoSrc)}"
          alt="${escapeHtml(clan.logoAlt)}"
          decoding="async"
        />
      </div>
    `;
  }

  return `
    <div class="${escapeHtml(logoClassNames.join(" "))}">
      <div class="clan-card__logo-placeholder" aria-label="Logo pendiente de ${escapeHtml(clan.name)}">
        ${escapeHtml(clan.placeholderLabel || clan.name)}
      </div>
    </div>
  `;
}

function renderClanDiscordLink(clan) {
  if (!clan.discordUrl) {
    return `
      <span
        class="server-action-link server-action-link--disabled clan-card__link"
        aria-disabled="true"
      >
        ${escapeHtml(clan.discordLabel)}
      </span>
    `;
  }

  return `
    <a
      class="server-action-link clan-card__link"
      href="${escapeHtml(clan.discordUrl)}"
      target="_blank"
      rel="noreferrer"
    >
      ${escapeHtml(clan.discordLabel)}
    </a>
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
              <strong class="${escapeHtml(item.valueClassName || "")}">${escapeHtml(item.value)}</strong>
            </article>
          `,
        )
        .join("")}
    </div>
  `;
}

function getServerHistoryUrl(server) {
  if (typeof server?.community_history_url === "string" && server.community_history_url.trim()) {
    return server.community_history_url.trim();
  }

  const externalServerId =
    typeof server?.external_server_id === "string"
      ? server.external_server_id.trim()
      : "";
  if (!externalServerId) {
    return "";
  }

  return SERVER_HISTORY_URLS_FALLBACK[externalServerId] || "";
}

function getServerHistoryState(server) {
  const historyUrl = getServerHistoryUrl(server);
  return {
    available: Boolean(historyUrl),
    url: historyUrl,
  };
}

function selectPrimaryServerItems(items) {
  if (!Array.isArray(items)) {
    return [];
  }

  const realItems = items.filter(isRealLiveSnapshot);
  return realItems.length > 0 ? realItems : items;
}

function isRealLiveSnapshot(item) {
  return item?.snapshot_origin === "real-a2s" || item?.snapshot_origin === "real-rcon";
}

function deriveSnapshotState(serversData) {
  const timestampLabel = serversData?.last_snapshot_at
    ? formatTimestamp(serversData.last_snapshot_at)
    : "";
  if (!timestampLabel) {
    return {
      label: "",
      isFresh: false,
    };
  }

  const isFresh = serversData?.is_stale !== true;
  return {
    label: isFresh
      ? `Actualizado ${timestampLabel}`
      : `Ultimo snapshot ${timestampLabel}`,
    isFresh,
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

function shuffleItems(items) {
  const shuffledItems = [...items];
  for (let currentIndex = shuffledItems.length - 1; currentIndex > 0; currentIndex -= 1) {
    const randomIndex = Math.floor(Math.random() * (currentIndex + 1));
    [shuffledItems[currentIndex], shuffledItems[randomIndex]] = [
      shuffledItems[randomIndex],
      shuffledItems[currentIndex],
    ];
  }

  return shuffledItems;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
