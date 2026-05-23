const CURRENT_MATCH_POLL_INTERVAL_MS = 30 * 1000;
const CURRENT_MATCH_KILL_FEED_POLL_INTERVAL_MS = 1500;
const CURRENT_MATCH_PLAYER_STATS_POLL_INTERVAL_MS = 3000;
const CURRENT_MATCH_SERVERS = Object.freeze({
  "comunidad-hispana-01": "Comunidad Hispana #01",
  "comunidad-hispana-02": "Comunidad Hispana #02",
});
const CURRENT_MATCH_SCOREBOARDS = Object.freeze({
  "comunidad-hispana-01": "https://scoreboard.comunidadhll.es",
  "comunidad-hispana-02": "https://scoreboard.comunidadhll.es:5443",
});
const CURRENT_MATCH_KILL_FEED_LIMIT = 18;
const CURRENT_MATCH_WEAPONS = Object.freeze({
  "m1 garand": { label: "M1 Garand", icon: "m1_garand.PNG" },
  mp40: { label: "MP40", icon: "mp40.PNG" },
  "m1a1 thompson": { label: "M1A1 Thompson", icon: "thompson.PNG" },
  "m1a1": { label: "M1A1 Thompson", icon: "thompson.PNG" },
  thompson: { label: "M1A1 Thompson", icon: "thompson.PNG" },
  "gewehr 43": { label: "Gewehr 43", icon: "gewehr.PNG" },
  "gewehr43": { label: "Gewehr 43", icon: "gewehr.PNG" },
  g43: { label: "Gewehr 43", icon: "gewehr.PNG" },
  mg42: { label: "MG42", icon: "mg42.PNG" },
  kar98k: { label: "Kar98k", icon: "kar98k.PNG" },
  kar98: { label: "Kar98k", icon: "kar98k.PNG" },
  stg44: { label: "StG 44", icon: "stg44.PNG" },
  "stg 44": { label: "StG 44", icon: "stg44.PNG" },
  bar: { label: "BAR", icon: "" },
  "m1919": { label: "M1919", icon: "browing_m1919.PNG" },
  "m1919 browning": { label: "M1919", icon: "browing_m1919.PNG" },
  "browning m1919": { label: "M1919", icon: "browing_m1919.PNG" },
  "m1 carbine": { label: "M1 Carbine", icon: "m1_carabine.PNG" },
  "m1 carabine": { label: "M1 Carbine", icon: "m1_carabine.PNG" },
  luger: { label: "Luger", icon: "luger_p08.PNG" },
  "luger p08": { label: "Luger", icon: "luger_p08.PNG" },
  colt: { label: "Colt", icon: "colt_1911.PNG" },
  "colt 1911": { label: "Colt", icon: "colt_1911.PNG" },
  "colt m1911": { label: "Colt", icon: "colt_1911.PNG" },
  "frag grenade": { label: "Frag Grenade", icon: "" },
  grenade: { label: "Frag Grenade", icon: "" },
  "smoke grenade": { label: "Smoke Grenade", icon: "" },
  unknown: { label: "Arma desconocida", icon: "" },
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
    playersTitle: document.getElementById("current-match-players-title"),
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
  const playerStatsState = initializePlayerStats(nodes);
  let currentMatchRefreshInFlight = false;
  const refreshCurrentMatch = async () => {
    if (currentMatchRefreshInFlight) {
      return;
    }
    currentMatchRefreshInFlight = true;
    try {
      await loadCurrentMatch({ backendBaseUrl, serverSlug, nodes });
    } finally {
      currentMatchRefreshInFlight = false;
    }
  };

  let killFeedRefreshInFlight = false;
  const refreshKillFeed = async () => {
    if (killFeedRefreshInFlight) {
      return;
    }
    killFeedRefreshInFlight = true;
    try {
      await loadKillFeed({ backendBaseUrl, serverSlug, nodes, killFeedState });
    } finally {
      killFeedRefreshInFlight = false;
    }
  };

  let playerStatsRefreshInFlight = false;
  const refreshPlayerStats = async () => {
    if (playerStatsRefreshInFlight) {
      return;
    }
    playerStatsRefreshInFlight = true;
    try {
      await loadPlayerStats({ backendBaseUrl, serverSlug, nodes, playerStatsState });
    } finally {
      playerStatsRefreshInFlight = false;
    }
  };

  void refreshCurrentMatch();
  void refreshKillFeed();
  void refreshPlayerStats();
  window.setInterval(() => {
    void refreshCurrentMatch();
  }, CURRENT_MATCH_POLL_INTERVAL_MS);
  window.setInterval(() => {
    void refreshKillFeed();
  }, CURRENT_MATCH_KILL_FEED_POLL_INTERVAL_MS);
  window.setInterval(() => {
    void refreshPlayerStats();
  }, CURRENT_MATCH_PLAYER_STATS_POLL_INTERVAL_MS);
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
    const cursor = killFeedState.latestEventId
      ? `&since_event_id=${encodeURIComponent(killFeedState.latestEventId)}`
      : "";
    const payload = await fetchJson(
      `${backendBaseUrl}/api/current-match/kills?server=${encodeURIComponent(serverSlug)}&limit=${CURRENT_MATCH_KILL_FEED_LIMIT}${cursor}`,
    );
    renderKillFeed(payload?.data || {}, nodes, killFeedState);
  } catch (error) {
    setState(nodes.feedState, "No se pudo actualizar el feed de combate.", true);
  }
}

async function loadPlayerStats({ backendBaseUrl, serverSlug, nodes, playerStatsState }) {
  try {
    const payload = await fetchJson(
      `${backendBaseUrl}/api/current-match/players?server=${encodeURIComponent(serverSlug)}`,
    );
    renderPlayerStats(payload?.data || {}, nodes, playerStatsState);
  } catch (error) {
    setState(
      nodes.playerStatsState,
      "Todavía no hay estadísticas fiables de jugadores para esta partida.",
      true,
    );
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
    ? "Lectura en vivo recibida. El feed de bajas se actualiza en tiempo casi real."
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
        <section class="current-match-killfeed-screen" aria-label="Bajas recientes en la partida actual">
          <div class="current-match-killfeed" id="current-match-feed-list"></div>
        </section>
      `,
    );
  }
  nodes.feedState = document.getElementById("current-match-feed-state");
  nodes.feedList = document.getElementById("current-match-feed-list");
  return {
    byId: new Map(),
    latestEventId: "",
    visibleSignature: "",
  };
}

function initializePlayerStats(nodes) {
  const shell = nodes.playersTitle?.closest(".panel__shell");
  if (shell) {
    shell.insertAdjacentHTML(
      "beforeend",
      `
        <p class="historical-state" id="current-match-player-stats-state" aria-live="polite">
          Cargando estadisticas en vivo...
        </p>
        <div class="historical-table-shell" id="current-match-player-stats-shell" hidden></div>
      `,
    );
  }
  nodes.playerStatsState = document.getElementById("current-match-player-stats-state");
  nodes.playerCount = document.getElementById("current-match-player-count");
  nodes.playerStatsShell = document.getElementById("current-match-player-stats-shell");
  return {
    visibleSignature: "",
  };
}

function renderKillFeed(data, nodes, state) {
  const incoming = Array.isArray(data.items) ? data.items : [];
  if (data.scope === "no-current-match-events") {
    state.byId.clear();
    state.latestEventId = "";
  }
  incoming.forEach((event) => {
    if (event?.event_id) {
      state.byId.set(event.event_id, event);
    }
  });
  const events = [...state.byId.values()]
    .sort(compareKillFeedEvents)
    .slice(-CURRENT_MATCH_KILL_FEED_LIMIT);
  state.byId = new Map(events.map((event) => [event.event_id, event]));
  state.latestEventId = events[events.length - 1]?.event_id || state.latestEventId;
  if (events.length === 0) {
    nodes.feedList.innerHTML = "";
    state.visibleSignature = "";
    setState(nodes.feedState, "Todavía no se han detectado bajas en esta partida.");
    return;
  }
  const visualEvents = events;
  const visibleSignature = visualEvents.map((event) => event.event_id).join("|");
  if (visibleSignature !== state.visibleSignature) {
    nodes.feedList.innerHTML = renderKillFeedColumns(visualEvents);
    state.visibleSignature = visibleSignature;
  }
  nodes.feedState.textContent = formatKillFeedCoverage(data.scope);
  nodes.feedState.classList.remove("historical-state--error");
}

function compareKillFeedEvents(left, right) {
  const leftTime = Number(left.server_time);
  const rightTime = Number(right.server_time);
  if (Number.isFinite(leftTime) && Number.isFinite(rightTime) && leftTime !== rightTime) {
    return leftTime - rightTime;
  }
  return (
    String(left.event_timestamp || "").localeCompare(String(right.event_timestamp || "")) ||
    String(left.event_id || "").localeCompare(String(right.event_id || ""))
  );
}

function renderKillFeedColumns(events) {
  const splitIndex = Math.ceil(events.length / 2);
  return [events.slice(0, splitIndex), events.slice(splitIndex)]
    .map(
      (columnEvents) => `
        <div class="current-match-killfeed__column">
          ${columnEvents.map(renderKillFeedRow).join("")}
        </div>
      `,
    )
    .join("");
}

function renderKillFeedRow(event) {
  const weapon = resolveKillFeedWeapon(event.weapon);
  const killerTeam = getKillFeedTeamDisplay(event.killer_team);
  const victimTeam = getKillFeedTeamDisplay(event.victim_team);
  const teamkillBadge = event.is_teamkill
    ? '<span class="current-match-killfeed__teamkill">TK</span>'
    : "";
  return `
    <article
      class="current-match-killfeed__row${event.is_teamkill ? " is-teamkill" : ""}"
      data-event-id="${escapeHtml(event.event_id || "")}"
    >
      <span class="current-match-killfeed__player current-match-killfeed__player--killer">
        <strong class="current-match-killfeed__player-name" title="${escapeHtml(event.killer_name || "Jugador no disponible")}">
          ${escapeHtml(event.killer_name || "Jugador no disponible")}
        </strong>
        <span class="current-match-killfeed__player-meta">
          ${renderKillFeedTeamBadge(killerTeam)}
          ${teamkillBadge}
        </span>
      </span>
      <span
        class="current-match-killfeed__weapon"
        title="${escapeHtml(weapon.label)}"
        aria-label="${escapeHtml(weapon.label)}"
      >
        ${renderKillFeedWeaponIcon(weapon)}
        <em>${escapeHtml(weapon.label)}</em>
      </span>
      <span class="current-match-killfeed__player current-match-killfeed__player--victim">
        <span class="current-match-killfeed__player-name" title="${escapeHtml(event.victim_name || "Objetivo no disponible")}">
          ${escapeHtml(event.victim_name || "Objetivo no disponible")}
        </span>
        ${renderKillFeedTeamBadge(victimTeam)}
      </span>
    </article>
  `;
}

function getKillFeedTeamDisplay(value) {
  const team = getPlayerTeamDisplay(value);
  return team.key === "unknown" ? { key: "unknown", label: "N/D" } : team;
}

function renderKillFeedTeamBadge(team) {
  return `
    <span class="current-match-killfeed__team-badge current-match-killfeed__team-badge--${team.key}">
      ${escapeHtml(team.label)}
    </span>
  `;
}

function resolveKillFeedWeapon(value) {
  const key = normalizeLookupText(value);
  return CURRENT_MATCH_WEAPONS[key] || {
    label: String(value || CURRENT_MATCH_WEAPONS.unknown.label),
    icon: CURRENT_MATCH_WEAPONS.unknown.icon,
  };
}

function renderKillFeedWeaponIcon(weapon) {
  if (!weapon.icon) {
    return '<span class="current-match-killfeed__weapon-fallback" aria-hidden="true">?</span>';
  }
  return `
    <img
      class="current-match-killfeed__weapon-icon"
      src="./assets/img/weapons/${escapeHtml(weapon.icon)}"
      alt=""
      width="88"
      height="32"
      loading="lazy"
      decoding="async"
      onerror="this.hidden = true; this.nextElementSibling.hidden = false;"
    />
    <span class="current-match-killfeed__weapon-fallback" aria-hidden="true" hidden>?</span>
  `;
}

function renderPlayerStats(data, nodes, state) {
  const items = Array.isArray(data.items) ? sortPlayerStats(data.items) : [];
  renderDetectedPlayerCount(items.length, nodes);
  if (items.length === 0) {
    state.visibleSignature = "";
    nodes.playerStatsShell.innerHTML = "";
    nodes.playerStatsShell.hidden = true;
    setState(
      nodes.playerStatsState,
      "Todavía no hay estadísticas fiables de jugadores para esta partida.",
    );
    return;
  }
  const signature = items
    .map((item) =>
      [
        item.player_name,
        item.team,
        item.kills,
        item.deaths,
        item.teamkills,
        item.deaths_by_teamkill,
        item.favorite_weapon,
        item.last_seen_at,
      ].join(":"),
    )
    .join("|");
  if (signature !== state.visibleSignature) {
    nodes.playerStatsShell.innerHTML = renderPlayerStatsTable(items);
    state.visibleSignature = signature;
  }
  nodes.playerStatsShell.hidden = false;
  setState(nodes.playerStatsState, "Estadisticas derivadas de los eventos recientes.");
}

function renderDetectedPlayerCount(count, nodes) {
  if (nodes.playerCount) {
    nodes.playerCount.textContent = `Jugadores detectados: ${count}`;
  }
}

function sortPlayerStats(items) {
  return [...items].sort(
    (left, right) =>
      toStatNumber(right.kills) - toStatNumber(left.kills) ||
      toStatNumber(left.deaths) - toStatNumber(right.deaths) ||
      String(left.player_name || "").localeCompare(String(right.player_name || ""), "es", {
        sensitivity: "base",
      }),
  );
}

function renderPlayerStatsTable(items) {
  return `
    <table class="historical-table historical-table--players">
      <thead>
        <tr>
          <th>Jugador</th>
          <th>Equipo</th>
          <th>Bajas</th>
          <th>Muertes</th>
          <th>TK</th>
          <th>Muertes TK</th>
          <th>Arma frecuente</th>
        </tr>
      </thead>
      <tbody>
        ${items.map(renderPlayerStatsRow).join("")}
      </tbody>
    </table>
  `;
}

function renderPlayerStatsRow(item) {
  const team = getPlayerTeamDisplay(item.team);
  return `
    <tr class="historical-player-row historical-player-row--${team.key}">
      <td>${escapeHtml(item.player_name || "Jugador no disponible")}</td>
      <td class="historical-player-team-cell">
        <span class="historical-player-team-badge historical-player-team-badge--${team.key}">
          ${escapeHtml(team.label)}
        </span>
      </td>
      <td>${escapeHtml(formatStatNumber(item.kills))}</td>
      <td>${escapeHtml(formatStatNumber(item.deaths))}</td>
      <td>${escapeHtml(formatStatNumber(item.teamkills))}</td>
      <td>${escapeHtml(formatStatNumber(item.deaths_by_teamkill))}</td>
      <td>${escapeHtml(item.favorite_weapon || "No disponible")}</td>
    </tr>
  `;
}

function getPlayerTeamDisplay(value) {
  const normalized = String(value || "").trim().toLowerCase();
  if (normalized === "allies" || normalized === "allied" || normalized === "aliados") {
    return { key: "allies", label: "Aliados" };
  }
  if (normalized === "axis" || normalized === "eje") {
    return { key: "axis", label: "Eje" };
  }
  return { key: "unknown", label: "No disponible" };
}

function toStatNumber(value) {
  return Number.isFinite(Number(value)) ? Number(value) : 0;
}

function formatStatNumber(value) {
  return Number.isFinite(Number(value)) ? String(Number(value)) : "0";
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
  if (scope === "no-current-match-events") {
    return "Todavía no se han detectado bajas en esta partida.";
  }
  return "Todavía no se han detectado bajas en esta partida.";
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
