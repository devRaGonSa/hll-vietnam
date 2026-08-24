// Progressive enhancement for local frontend-backend checks.
const DEFAULT_SERVER_POLL_INTERVAL_MS = 300 * 1000;
const SERVER_CARD_PRESENTATION = Object.freeze({
  "comunidad-hispana-01": Object.freeze({ label: "Servidor 1" }),
  "comunidad-hispana-02": Object.freeze({ label: "Servidor 2" }),
  "comunidad-hll-vietnam-01": Object.freeze({ label: "Servidor 3" }),
});
const TRUSTED_SERVER_ACTIONS = Object.freeze({
  "comunidad-hispana-01": Object.freeze({
    publicScoreboardUrl: "https://scoreboard.comunidadhll.es",
    historicalUrl: "./historico.html?server=comunidad-hispana-01",
    currentMatchUrl: "./partida-actual.html?server=comunidad-hispana-01",
  }),
  "comunidad-hispana-02": Object.freeze({
    publicScoreboardUrl: "https://scoreboard.comunidadhll.es:5443",
    historicalUrl: "./historico.html?server=comunidad-hispana-02",
    currentMatchUrl: "./partida-actual.html?server=comunidad-hispana-02",
  }),
});
const COMMUNITY_CLANS = Object.freeze([
  {
    name: "LCM",
    badge: "Clan CH",
    description:
      "Clan activo de la comunidad, con acceso directo a su discord.",
    logoSrc: "./assets/img/clans/lcm.png",
    logoAlt: "Logo de LCM",
    logoClassName: "clan-card__logo--standard",
    discordUrl: "https://discord.gg/9F9S353QZv",
    discordLabel: "Abrir Discord",
  },
  {
    name: "La 129",
    badge: "Clan CH",
    description:
      "Clan activo de la comunidad.",
    logoSrc: "./assets/img/clans/la129.png",
    logoAlt: "Logo de La 129",
    logoClassName: "clan-card__logo--wide",
    discordUrl: "",
    discordLabel: "Pr\u00f3ximamente",
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
    logoClassName: "clan-card__logo--standard",
    discordUrl: "https://discord.gg/tYnXK7MQjB",
    discordLabel: "Abrir Discord",
    placeholderLabel: "H9H",
  },
  {
    name: "BxB",
    badge: "Clan CH",
    description:
      "Clan activo de la comunidad, con acceso directo a su discord.",
    logoSrc: "./assets/img/clans/bxb.png",
    logoAlt: "Logo de BxB",
    logoClassName: "clan-card__logo--bxb",
    cardClassName: "clan-card--bxb",
    discordUrl: "https://discord.gg/R2hKrfYaZ6",
    discordLabel: "Abrir Discord",
    placeholderLabel: "BxB",

  },
  {
    name: "7dv",
    badge: "Clan CH",
    description:
      "Clan activo de la comunidad, con acceso directo a su discord.",
    logoSrc: "./assets/img/clans/7dv.png",
    logoAlt: "Logo de 7dv",
    logoClassName: "clan-card__logo--standard",
    discordUrl: "https://discord.gg/3sxNQZwrg6",
    discordLabel: "Abrir Discord",
  },
]);

let serverCountdownTimerId = null;

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
      stopServerCountdown();
      serversList.innerHTML =
        '<p class="servers-empty">Informaci\u00f3n de servidores disponible m\u00e1s adelante.</p>';
      return;
    }

    const visibleItems = selectPrimaryServerItems(serversData.items);
    serversList.innerHTML = renderServerSections(visibleItems);
    restartServerCountdown();
  } catch (error) {
    stopServerCountdown();
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
  const serverTargetKey = resolveServerTargetKey(server);
  const serverLabel = SERVER_CARD_PRESENTATION[serverTargetKey]?.label || "Servidor";
  const statusLabel = formatServerStatus(server.status);
  const stateClass =
    server.status === "online" ? "server-state--online" : "server-state--offline";
  const isRealSnapshot = isRealLiveSnapshot(server);
  const currentMap = getTrimmedServerValue(server.current_map) || "Mapa no disponible";
  const players = formatPopulationValue(server.players);
  const maxPlayers = formatPopulationValue(server.max_players);
  const actionMarkup = renderServerAction(server);
  const cardVariantClass = isRealSnapshot ? "server-card--real" : "server-card--reference";
  const serverGame = normalizeServerGame(server.game);
  const gameVariantClass =
    serverGame === "hllv" ? "server-card--game-hllv" : "";
  const gameLabel = formatServerGameLabel(serverGame);
  const mapImage = resolveServerMapImage(server, serverGame, currentMap);
  const score = resolveScorePresentation(server.allied_score, server.axis_score);
  const remainingSeconds = normalizeRemainingSeconds(
    server.remaining_match_time_seconds,
  );
  const remainingLabel = formatRemainingTime(remainingSeconds);
  const remainingAttribute = remainingSeconds === null
    ? ""
    : ` data-remaining-seconds="${remainingSeconds}"`;
  const mapImageAlt = mapImage.matched ? `Mapa ${currentMap}` : "";

  return `
    <article
      class="server-card server-card--stats ${cardVariantClass} ${gameVariantClass}"
      data-game="${escapeHtml(serverGame)}"
      data-server-target="${escapeHtml(serverTargetKey)}"
    >
      <div class="server-card__top server-card__top--stats">
        <div class="server-card__identity">
          <p class="server-card__eyebrow">${escapeHtml(gameLabel)}</p>
          <h3>${escapeHtml(serverLabel)}</h3>
        </div>
        <div class="server-card__status-column">
          <span class="server-state ${stateClass}">${escapeHtml(statusLabel)}</span>
          <p class="server-card__population">${escapeHtml(`${players} / ${maxPlayers}`)}</p>
        </div>
      </div>
      <div class="server-card__map" data-image-state="${mapImage.matched ? "resolved" : "fallback"}">
        <img
          class="server-card__map-image"
          src="${escapeHtml(mapImage.src)}"
          alt="${escapeHtml(mapImageAlt)}"
          width="960"
          height="540"
          loading="lazy"
          decoding="async"
          onerror="this.onerror=null;this.src='./assets/img/maps/unknown-day.webp';this.alt='';this.closest('.server-card__map').dataset.imageState='fallback';"
        />
        <strong class="server-card__map-name">${escapeHtml(currentMap)}</strong>
      </div>
      <div class="server-card__match-summary">
        <dl class="server-card__live-metrics" aria-label="Tiempo de la partida actual">
          <div class="server-card__live-metric">
            <dt>Tiempo restante</dt>
            <dd${remainingAttribute} aria-label="Tiempo restante: ${escapeHtml(remainingLabel)}">${escapeHtml(remainingLabel)}</dd>
          </div>
        </dl>
        ${renderScoreboardBar(score)}
      </div>
      <div class="server-card__footer">
        ${actionMarkup}
      </div>
    </article>
  `;
}

function renderServerSections(latestItems) {
  return latestItems.map((server) => renderServerStatsCard(server)).join("");
}

function normalizeServerGame(value) {
  const normalized = typeof value === "string" ? value.trim().toLowerCase() : "";
  if (normalized === "hll" || normalized === "hllv") {
    return normalized;
  }
  return "unknown";
}

function resolveServerTargetKey(server) {
  if (!server) {
    return "";
  }
  return [
    server.key,
    server.external_server_id,
    server.server_slug,
    server.target_key,
    server.slug,
    server.community_slug,
  ]
    .map(getTrimmedServerValue)
    .find((value) => SERVER_CARD_PRESENTATION[value]) || "";
}

function formatServerGameLabel(game) {
  if (game === "hll") {
    return "Hell Let Loose";
  }
  if (game === "hllv") {
    return "Hell Let Loose Vietnam";
  }
  return "Juego no disponible";
}

function formatPopulationValue(value) {
  return Number.isInteger(value) && value >= 0 ? String(value) : "—";
}

function resolveScorePresentation(alliedScore, axisScore) {
  if (
    !Number.isInteger(alliedScore) || alliedScore < 0 ||
    !Number.isInteger(axisScore) || axisScore < 0
  ) {
    return {
      available: false,
      alliedScore: null,
      axisScore: null,
      leader: "unknown",
      leaderLabel: "Puntuaci\u00f3n no disponible",
      alliedPercent: 50,
      axisPercent: 50,
    };
  }

  const total = alliedScore + axisScore;
  const alliedPercent = total === 0 ? 50 : (alliedScore / total) * 100;
  const leader = alliedScore > axisScore
    ? "allies"
    : axisScore > alliedScore
      ? "axis"
      : "tie";
  const leaderLabel = leader === "allies"
    ? "Allies va ganando"
    : leader === "axis"
      ? "Axis va ganando"
      : "Empate";

  return {
    available: true,
    alliedScore,
    axisScore,
    leader,
    leaderLabel,
    alliedPercent,
    axisPercent: 100 - alliedPercent,
  };
}

function renderScoreboardBar(score) {
  const accessibilityLabel = score.available
    ? `Puntuaci\u00f3n: Allies ${score.alliedScore}, Axis ${score.axisScore}. ${score.leaderLabel}.`
    : "Puntuaci\u00f3n no disponible.";
  const shareStyle = score.available
    ? ` style="--allied-score-share: ${score.alliedPercent.toFixed(2)}%; --axis-score-share: ${score.axisPercent.toFixed(2)}%;"`
    : "";
  const alliedLabel = score.available ? String(score.alliedScore) : "—";
  const axisLabel = score.available ? String(score.axisScore) : "—";

  return `
    <section
      class="server-card__scoreboard server-card__scoreboard--${score.leader}"
      aria-label="${escapeHtml(accessibilityLabel)}"
      data-score-state="${score.leader}"
      ${shareStyle}
    >
      <div class="server-card__scoreboard-teams">
        <span class="server-card__scoreboard-team server-card__scoreboard-team--allies">
          <span>Allies</span>
          <strong>${escapeHtml(alliedLabel)}</strong>
        </span>
        <span class="server-card__scoreboard-team server-card__scoreboard-team--axis">
          <strong>${escapeHtml(axisLabel)}</strong>
          <span>Axis</span>
        </span>
      </div>
      <div class="server-card__scorebar" role="img" aria-label="${escapeHtml(accessibilityLabel)}">
        ${score.available ? `
          <span class="server-card__scorebar-side server-card__scorebar-side--allies"></span>
          <span class="server-card__scorebar-side server-card__scorebar-side--axis"></span>
        ` : '<span class="server-card__scorebar-unknown"></span>'}
      </div>
    </section>
  `;
}

function normalizeRemainingSeconds(value) {
  // /api/servers projects CRCON get_public_info.time_remaining as this field.
  return Number.isFinite(value) && value >= 0 ? Math.floor(value) : null;
}

function formatRemainingTime(value) {
  const seconds = normalizeRemainingSeconds(value);
  if (seconds === null) {
    return "—";
  }
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const trailingSeconds = seconds % 60;
  if (hours > 0) {
    return `${hours}:${String(minutes).padStart(2, "0")}:${String(trailingSeconds).padStart(2, "0")}`;
  }
  return `${String(minutes).padStart(2, "0")}:${String(trailingSeconds).padStart(2, "0")}`;
}

function resolveServerMapImage(server, serverGame, currentMap) {
  const resolver = globalThis.HLL_MAP_IMAGES?.resolveMapImageAsset ||
    globalThis.HLL_VIETNAM_MAP_IMAGES?.resolveMapImageAsset;
  if (typeof resolver !== "function") {
    return {
      src: "./assets/img/maps/unknown-day.webp",
      matched: false,
      fallback: true,
    };
  }
  return resolver({
    game: serverGame,
    candidates: [
      server.layer,
      server.layer_id,
      server.map_id,
      server.current_map,
      currentMap,
      server.game_mode,
    ],
  });
}

function stopServerCountdown(timerScope = globalThis) {
  if (serverCountdownTimerId !== null) {
    timerScope.clearInterval(serverCountdownTimerId);
    serverCountdownTimerId = null;
  }
}

function tickServerCountdown(ownerDocument = document) {
  const nodes = Array.from(
    ownerDocument.querySelectorAll("[data-remaining-seconds]"),
  );
  nodes.forEach((node) => {
    const currentSeconds = normalizeRemainingSeconds(
      Number(node.dataset.remainingSeconds),
    );
    if (currentSeconds === null) {
      return;
    }
    const nextSeconds = Math.max(0, currentSeconds - 1);
    const label = formatRemainingTime(nextSeconds);
    node.dataset.remainingSeconds = String(nextSeconds);
    node.textContent = label;
    node.setAttribute("aria-label", `Tiempo restante: ${label}`);
  });
}

function restartServerCountdown(
  ownerDocument = document,
  timerScope = globalThis,
) {
  stopServerCountdown(timerScope);
  if (!ownerDocument.querySelector("[data-remaining-seconds]")) {
    return null;
  }
  serverCountdownTimerId = timerScope.setInterval(
    () => tickServerCountdown(ownerDocument),
    1000,
  );
  return serverCountdownTimerId;
}

function normalizeServerRegion(value) {
  if (typeof value !== "string") {
    return "";
  }
  const trimmedValue = value.trim();
  if (!trimmedValue) {
    return "";
  }
  const normalizedValue = trimmedValue
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
  const placeholderValues = new Set([
    "region pendiente",
    "region pending",
    "pending",
    "unknown",
    "desconocida",
    "no disponible",
    "por confirmar",
    "n/a",
  ]);
  return placeholderValues.has(normalizedValue) ? "" : trimmedValue;
}

function renderServerAction(server) {
  const actions = getTrustedServerActions(server);
  if (!actions) {
    return "";
  }

  return `
    <div class="server-card__actions">
      <a class="server-action-link" href="${escapeHtml(actions.historicalUrl)}">
        Hist\u00f3rico
      </a>
      <a class="server-action-link" href="${escapeHtml(actions.currentMatchUrl)}">
        Partida actual
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
  const cardClassName = clan.cardClassName ? ` ${escapeHtml(clan.cardClassName)}` : "";

  return `
    <article class="clan-card${cardClassName}">
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

function getTrustedServerActions(server) {
  const trustedActionKey = resolveTrustedServerActionKey(server);
  return TRUSTED_SERVER_ACTIONS[trustedActionKey] || null;
}

function resolveTrustedServerActionKey(server) {
  if (!server) {
    return "";
  }

  const externalServerId = getTrimmedServerValue(server.external_server_id);
  if (TRUSTED_SERVER_ACTIONS[externalServerId]) {
    return externalServerId;
  }

  const trustedSlugFields = [
    server.server_slug,
    server.target_key,
    server.slug,
    server.community_slug,
  ];
  const trustedSlug = trustedSlugFields
    .map(getTrimmedServerValue)
    .find((value) => TRUSTED_SERVER_ACTIONS[value]);
  if (trustedSlug) {
    return trustedSlug;
  }

  const serverNames = [server.server_name, server.name].map(getTrimmedServerValue);
  if (
    serverNames.some(
      (name) => name.startsWith("#01") || name.includes("Comunidad Hispana #01"),
    )
  ) {
    return "comunidad-hispana-01";
  }
  if (
    serverNames.some(
      (name) => name.startsWith("#02") || name.includes("Comunidad Hispana #02"),
    )
  ) {
    return "comunidad-hispana-02";
  }

  const serverReference = [
    getTrimmedServerValue(server.source_ref),
    externalServerId,
  ].join(" ");
  if (serverReference.includes("152.114.195.174") || serverReference.includes(":7779")) {
    return "comunidad-hispana-01";
  }
  if (serverReference.includes("152.114.195.150") || serverReference.includes(":7879")) {
    return "comunidad-hispana-02";
  }

  return "";
}

function getTrimmedServerValue(value) {
  return typeof value === "string" ? value.trim() : "";
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
      : `\u00daltimo snapshot ${timestampLabel}`,
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
