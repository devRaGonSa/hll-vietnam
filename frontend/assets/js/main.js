// Progressive enhancement for local frontend-backend checks.
const RECENT_SNAPSHOT_WINDOW_MS = 30 * 60 * 1000;

document.addEventListener("DOMContentLoaded", () => {
  console.info("HLL Vietnam frontend ready");

  const backendBaseUrl =
    document.body.dataset.backendBaseUrl || "http://127.0.0.1:8000";
  const statusNode = document.getElementById("backend-status");
  const trailerFrame = document.getElementById("trailer-frame");
  const trailerTitle = document.getElementById("trailer-title");
  const serversTitle = document.getElementById("servers-title");
  const serversNote = document.getElementById("servers-note");
  const serversList = document.getElementById("servers-list");
  const serversBadge = document.getElementById("servers-badge");
  const serversSource = document.getElementById("servers-source");
  const serversSourceLabel = document.getElementById("servers-source-label");
  const serversSourceMeta = document.getElementById("servers-source-meta");
  const statsPreview = document.getElementById("stats-preview");
  const statsPreviewItems = document.getElementById("stats-preview-items");

  updateBackendStatus(statusNode, "Backend comprobando", "status-chip--idle");

  setServersDataState(
    {
      badgeNode: serversBadge,
      sourceNode: serversSource,
      labelNode: serversSourceLabel,
      metaNode: serversSourceMeta,
    },
    { kind: "fallback" },
  );

  Promise.allSettled([
    fetchHealth(backendBaseUrl, statusNode),
    hydrateTrailer(backendBaseUrl, trailerFrame, trailerTitle),
    hydrateServers(
      backendBaseUrl,
      serversTitle,
      serversNote,
      serversList,
      serversBadge,
      serversSource,
      serversSourceLabel,
      serversSourceMeta,
      statsPreview,
      statsPreviewItems,
    ),
  ]).catch((error) => {
    console.warn("Progressive enhancement failed", error);
  });
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
  serversSource,
  serversSourceLabel,
  serversSourceMeta,
  statsPreview,
  statsPreviewItems,
) {
  if (!serversTitle || !serversNote || !serversList || !serversBadge) {
    return;
  }

  try {
    const response = await fetch(`${backendBaseUrl}/api/servers`);
    if (!response.ok) {
      throw new Error(`Servers request failed with ${response.status}`);
    }

    const payload = await response.json();
    const serversData = payload.data;
    if (!serversData || !Array.isArray(serversData.items)) {
      throw new Error("Servers payload incomplete");
    }

    serversTitle.textContent =
      serversData.title || "Servidores actuales de Hell Let Loose";
    setServersDataState(
      {
        badgeNode: serversBadge,
        sourceNode: serversSource,
        labelNode: serversSourceLabel,
        metaNode: serversSourceMeta,
      },
      { kind: "fallback" },
    );

    if (serversData.context === "current-hll-reference") {
      serversNote.textContent =
        "Referencia provisional del HLL actual mientras no existan datos reales de HLL Vietnam.";
    }

    if (serversData.items.length === 0) {
      serversList.innerHTML =
        '<p class="servers-empty">Informacion de servidores disponible mas adelante.</p>';
      return;
    }

    serversList.innerHTML = serversData.items.map(renderServerCard).join("");
    await hydrateServerStats(
      backendBaseUrl,
      serversTitle,
      serversNote,
      serversList,
      serversBadge,
      serversSource,
      serversSourceLabel,
      serversSourceMeta,
      statsPreview,
      statsPreviewItems,
    );
  } catch (error) {
    console.warn("Servers panel remains on static fallback", error);
  }
}

async function hydrateServerStats(
  backendBaseUrl,
  serversTitle,
  serversNote,
  serversList,
  serversBadge,
  serversSource,
  serversSourceLabel,
  serversSourceMeta,
  statsPreview,
  statsPreviewItems,
) {
  if (!statsPreview || !statsPreviewItems) {
    return;
  }

  try {
    const latestPayload = await fetchJson(`${backendBaseUrl}/api/servers/latest`);
    const latestItems = latestPayload?.data?.items;
    if (!Array.isArray(latestItems) || latestItems.length === 0) {
      return;
    }

    const histories = await Promise.all(
      latestItems.map(async (server) => {
        const serverKey = server.external_server_id || server.server_id;
        const historyPayload = await fetchJson(
          `${backendBaseUrl}/api/servers/${encodeURIComponent(serverKey)}/history?limit=4`,
        );
        return {
          key: serverKey,
          items: Array.isArray(historyPayload?.data?.items)
            ? historyPayload.data.items
            : [],
        };
      }),
    );

    const historyByServer = new Map(
      histories.map((entry) => [String(entry.key), entry.items]),
    );
    const visibleItems = selectPrimaryServerItems(latestItems);
    const latestState = deriveSnapshotState(visibleItems);
    const hasRealSnapshots = visibleItems.some(isRealA2SSnapshot);

    serversTitle.textContent = hasRealSnapshots
      ? "Servidores activos con captura real"
      : latestPayload.data.title || "Actividad reciente de servidores";
    serversNote.textContent = hasRealSnapshots
      ? "La vista principal muestra solo servidores con snapshots reales A2S utilizables. El fallback provisional queda reservado para cuando el backend no aporta capturas validas."
      : "Vista ligera basada en snapshots persistidos del backend. Si no hay capturas reales utilizables, el panel conserva la referencia provisional.";
    setServersDataState(
      {
        badgeNode: serversBadge,
        sourceNode: serversSource,
        labelNode: serversSourceLabel,
        metaNode: serversSourceMeta,
      },
      latestState,
    );
    statsPreview.hidden = false;
    statsPreviewItems.innerHTML = renderStatsPreview(visibleItems);
    serversList.innerHTML = renderServerSections(visibleItems, historyByServer);
  } catch (error) {
    console.warn("Historical stats preview unavailable", error);
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

function setServersDataState(nodes, state) {
  const { badgeNode, sourceNode, labelNode, metaNode } = nodes;
  if (!badgeNode || !sourceNode || !labelNode || !metaNode) {
    return;
  }

  if (state.kind === "live") {
    badgeNode.textContent = "Snapshots A2S recientes";
    labelNode.textContent = "Captura real reciente";
    metaNode.textContent =
      state.timestampLabel
        ? `Ultima captura A2S registrada ${state.timestampLabel}.`
        : "El bloque muestra snapshots recientes procedentes del backend.";
    badgeNode.classList.remove("status-chip--fallback");
    badgeNode.classList.add("status-chip--ok");
    sourceNode.dataset.state = "live";
    return;
  }

  if (state.kind === "historical") {
    badgeNode.textContent = "Historico persistido";
    labelNode.textContent = "Persistencia local disponible";
    metaNode.textContent =
      state.timestampLabel
        ? `Se muestran snapshots guardados. Ultima captura ${state.timestampLabel}.`
        : "El backend devuelve historico persistido, aunque no sea una captura reciente.";
    badgeNode.classList.remove("status-chip--fallback");
    badgeNode.classList.add("status-chip--ok");
    sourceNode.dataset.state = "historical";
    return;
  }

  badgeNode.textContent = "Fallback estatico";
  labelNode.textContent = "Fallback estatico activo";
  metaNode.textContent =
    "La landing conserva la referencia provisional cuando el backend o el historico aun no aportan snapshots utilizables.";
  badgeNode.classList.remove("status-chip--ok");
  badgeNode.classList.add("status-chip--fallback");
  sourceNode.dataset.state = "fallback";
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
  const loadPercent =
    maxPlayers > 0 ? Math.max(0, Math.min(100, Math.round((players / maxPlayers) * 100))) : 0;

  return `
    <article class="server-card">
      <div class="server-card__top">
        <div class="server-card__identity">
          <p class="server-card__eyebrow">Servidor de referencia</p>
          <h3>${escapeHtml(serverName)}</h3>
        </div>
        <span class="server-state ${stateClass}">${escapeHtml(serverStatus)}</span>
      </div>
      <div class="server-card__load" aria-hidden="true">
        <span style="width: ${loadPercent}%"></span>
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

function renderServerStatsCard(server, historyItems) {
  const serverName = server.server_name || "Servidor sin nombre";
  const statusLabel = formatServerStatus(server.status);
  const stateClass =
    server.status === "online" ? "server-state--online" : "server-state--offline";
  const isRealSnapshot = server.snapshot_origin === "real-a2s";
  const currentMap = server.current_map || "Sin mapa disponible";
  const region = server.region || "Region pendiente";
  const players = Number.isFinite(server.players) ? server.players : 0;
  const maxPlayers = Number.isFinite(server.max_players) ? server.max_players : 0;
  const loadPercent =
    maxPlayers > 0 ? Math.max(0, Math.min(100, Math.round((players / maxPlayers) * 100))) : 0;
  const updatedAt = server.captured_at
    ? formatTimestamp(server.captured_at)
    : "Sin captura reciente";
  const updatedAgo = formatElapsedMinutes(server.history_summary?.minutes_since_last_capture);
  const trendMarkup = renderTrend(historyItems);
  const connectAction = renderConnectAction(server);
  const summaryMarkup = renderHistorySummary(server.history_summary);
  const cardVariantClass = isRealSnapshot ? "server-card--real" : "server-card--reference";
  const eyebrowLabel = isRealSnapshot ? "Snapshot real A2S" : "Referencia persistida";
  const quickFacts = renderQuickFacts([
    { label: "Mapa", value: currentMap },
    { label: "Region", value: region },
    { label: "Ultima captura", value: updatedAgo || updatedAt },
  ]);

  return `
    <article class="server-card server-card--stats ${cardVariantClass}">
      <div class="server-card__top server-card__top--stats">
        <div class="server-card__identity">
          <p class="server-card__eyebrow">${escapeHtml(eyebrowLabel)}</p>
          <h3>${escapeHtml(serverName)}</h3>
          <p class="server-card__meta">Mapa actual, region visible y ultima captura persistida del servidor.</p>
        </div>
        <div class="server-card__status-column">
          <span class="server-state ${stateClass}">${escapeHtml(statusLabel)}</span>
          <p class="server-card__population">${escapeHtml(`${players} / ${maxPlayers}`)}</p>
          ${connectAction}
        </div>
      </div>
      <div class="server-card__body">
        <div class="server-card__facts">
          ${quickFacts}
          ${summaryMarkup}
        </div>
        <div class="server-trend">
          <div class="server-trend__header">
            <p>Tendencia reciente</p>
            <span>${historyItems.length} capturas</span>
          </div>
          <div class="server-trend__bars" aria-hidden="true">${trendMarkup}</div>
        </div>
      </div>
      <div class="server-card__load" aria-hidden="true">
        <span style="width: ${loadPercent}%"></span>
      </div>
    </article>
  `;
}

function renderServerSections(latestItems, historyByServer) {
  const hasRealSnapshots = latestItems.some(isRealA2SSnapshot);

  return renderServerSection(
    hasRealSnapshots ? "Snapshots reales A2S" : "Historico persistido",
    hasRealSnapshots
      ? "Servidores reales validados y consultados desde el backend."
      : "Snapshots persistidos disponibles mientras no haya capturas reales utilizables.",
    hasRealSnapshots ? "server-panel-section--real" : "server-panel-section--reference",
    latestItems,
    historyByServer,
  );
}

function renderServerSection(title, intro, variantClass, items, historyByServer) {
  const cards = items
    .map((server) =>
      renderServerStatsCard(
        server,
        historyByServer.get(String(server.external_server_id || server.server_id)) || [],
      ),
    )
    .join("");

  return `
    <section class="server-panel-section ${variantClass}">
      <div class="server-panel-section__header">
        <h3>${escapeHtml(title)}</h3>
        <p>${escapeHtml(intro)}</p>
      </div>
      <div class="servers-grid servers-grid--section">
        ${cards}
      </div>
    </section>
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

function renderStatsPreview(items) {
  const latestTimestamp = items
    .map((item) => item.captured_at)
    .filter(Boolean)
    .sort()
    .at(-1);
  const totalPlayers = items.reduce(
    (sum, item) => sum + (Number.isFinite(item.players) ? item.players : 0),
    0,
  );
  const onlineServers = items.filter((item) => item.status === "online").length;

  return [
    renderStatsPreviewItem("Servidores", String(items.length)),
    renderStatsPreviewItem("Online", String(onlineServers)),
    renderStatsPreviewItem("Jugadores", String(totalPlayers)),
    renderStatsPreviewItem(
      "Ultima captura",
      latestTimestamp ? formatTimestamp(latestTimestamp) : "Pendiente",
    ),
  ].join("");
}

function renderHistorySummary(summary) {
  if (!summary) {
    return "";
  }

  return `
    <dl class="server-summary">
      <div class="server-summary__item">
        <dt>Visto online</dt>
        <dd>${escapeHtml(summary.last_seen_online_at ? formatTimestamp(summary.last_seen_online_at) : "Sin registro")}</dd>
      </div>
      <div class="server-summary__item">
        <dt>Capturas</dt>
        <dd>${escapeHtml(`${summary.recent_capture_count || 0}/${summary.window_size || 0}`)}</dd>
      </div>
      <div class="server-summary__item">
        <dt>Promedio</dt>
        <dd>${escapeHtml(formatPlayerMetric(summary.recent_average_players))}</dd>
      </div>
      <div class="server-summary__item">
        <dt>Pico</dt>
        <dd>${escapeHtml(formatPlayerMetric(summary.recent_peak_players))}</dd>
      </div>
    </dl>
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

function deriveSnapshotState(items) {
  const stateItems = Array.isArray(items) ? items : [];
  const realItems = stateItems.filter(isRealA2SSnapshot);
  const itemsForState = realItems.length > 0 ? realItems : stateItems;
  const latestTimestamp = itemsForState
    .map((item) => item.captured_at)
    .filter(Boolean)
    .sort()
    .at(-1);
  const latestDate = latestTimestamp ? new Date(latestTimestamp) : null;
  const latestTime = latestDate && !Number.isNaN(latestDate.getTime()) ? latestDate.getTime() : null;
  const timestampLabel = latestTimestamp ? formatTimestamp(latestTimestamp) : "";
  const hasRealA2S = realItems.length > 0;

  if (hasRealA2S && latestTime && Date.now() - latestTime <= RECENT_SNAPSHOT_WINDOW_MS) {
    return { kind: "live", timestampLabel };
  }

  return { kind: "historical", timestampLabel };
}

function renderStatsPreviewItem(label, value) {
  return `
    <article class="stats-preview__item">
      <p>${escapeHtml(label)}</p>
      <strong>${escapeHtml(value)}</strong>
    </article>
  `;
}

function renderTrend(historyItems) {
  if (!Array.isArray(historyItems) || historyItems.length === 0) {
    return '<span class="server-trend__bar server-trend__bar--empty"></span>';
  }

  const orderedItems = [...historyItems].reverse();
  return orderedItems
    .map((item) => {
      const players = Number.isFinite(item.players) ? item.players : 0;
      const maxPlayers = Number.isFinite(item.max_players) ? item.max_players : 0;
      const height =
        maxPlayers > 0 ? Math.max(14, Math.round((players / maxPlayers) * 100)) : 14;
      return `<span class="server-trend__bar" style="height: ${height}%"></span>`;
    })
    .join("");
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

function formatPlayerMetric(value) {
  return Number.isFinite(value) ? String(value) : "Sin dato";
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
