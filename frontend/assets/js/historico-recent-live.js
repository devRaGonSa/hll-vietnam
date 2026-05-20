(() => {
  const RECENT_MATCHES_ENDPOINT = "/api/historical/recent-matches";
  const REFRESH_DELAYS_MS = [150, 1000, 3000];

  document.addEventListener("DOMContentLoaded", () => {
    REFRESH_DELAYS_MS.forEach((delay) => {
      window.setTimeout(() => {
        void refreshDynamicRecentMatches();
      }, delay);
    });

    document.querySelectorAll("[data-server-slug]").forEach((button) => {
      button.addEventListener("click", () => {
        REFRESH_DELAYS_MS.forEach((delay) => {
          window.setTimeout(() => {
            void refreshDynamicRecentMatches(button.dataset.serverSlug);
          }, delay);
        });
      });
    });
  });

  async function refreshDynamicRecentMatches(forcedServerSlug) {
    const listNode = document.getElementById("recent-matches-list");
    const stateNode = document.getElementById("recent-matches-state");
    const metaNode = document.getElementById("recent-matches-snapshot-meta");
    const noteNode = document.getElementById("recent-matches-note");
    if (!listNode || !stateNode || !metaNode) {
      return;
    }

    const backendBaseUrl =
      document.body.dataset.backendBaseUrl || "http://127.0.0.1:8000";
    const serverSlug = normalizeDynamicServerSlug(forcedServerSlug || readServerFromUrl());

    try {
      const response = await fetch(
        `${backendBaseUrl}${RECENT_MATCHES_ENDPOINT}?server=${encodeURIComponent(
          serverSlug,
        )}&limit=10`,
        { cache: "no-store" },
      );
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const payload = await response.json();
      const data = payload?.data || {};
      const items = Array.isArray(data.items) ? data.items : [];
      if (!items.length) {
        setDynamicState(stateNode, "No hay partidas recientes disponibles para este alcance.");
        listNode.innerHTML = "";
        metaNode.textContent = "Datos recientes sin partidas disponibles.";
        return;
      }

      listNode.innerHTML = items.map((item) => renderDynamicRecentMatchCard(item)).join("");
      stateNode.hidden = true;
      if (noteNode) {
        noteNode.textContent = "Lista dinamica de partidas registradas por el modelo RCON reciente.";
      }
      metaNode.textContent = buildDynamicRecentMeta(data, items);
    } catch (error) {
      setDynamicState(stateNode, "No se pudieron cargar las partidas recientes dinamicas.", true);
      metaNode.textContent = "Error al leer las partidas recientes dinamicas.";
    }
  }

  function readServerFromUrl() {
    return new URLSearchParams(window.location.search).get("server") || "all-servers";
  }

  function normalizeDynamicServerSlug(value) {
    const normalized = String(value || "").trim();
    if (["comunidad-hispana-01", "comunidad-hispana-02", "all-servers"].includes(normalized)) {
      return normalized;
    }
    return "all-servers";
  }

  function renderDynamicRecentMatchCard(item) {
    const mapName = item?.map?.pretty_name || item?.map?.name || "Mapa no disponible";
    const serverName = item?.server?.name || "Servidor no disponible";
    const closedAt = item?.closed_at || item?.ended_at || item?.started_at;
    const detailUrl = buildDynamicInternalMatchDetailUrl(item);
    const externalUrl = normalizeDynamicExternalMatchUrl(item?.match_url);

    const actions = [
      `<span class="historical-match-card__result">${escapeDynamicHtml(formatDynamicResultLabel(item?.result))}</span>`,
      detailUrl
        ? `<a class="historical-match-card__link" href="${escapeDynamicHtml(detailUrl)}">Ver detalles</a>`
        : "",
      externalUrl
        ? `<a class="historical-match-card__link" href="${escapeDynamicHtml(externalUrl)}" target="_blank" rel="noopener noreferrer">Ver partida</a>`
        : "",
    ].join("");

    return `
      <article class="historical-match-card historical-match-card--clean">
        <div class="historical-match-card__top historical-match-card__top--clean">
          <h3 class="historical-match-card__title">${escapeDynamicHtml(mapName)}</h3>
        </div>
        <div class="historical-match-meta historical-match-meta--clean">
          <article>
            <p class="historical-match-meta__label">Servidor</p>
            <strong>${escapeDynamicHtml(serverName)}</strong>
          </article>
          <article>
            <p class="historical-match-meta__label">Cierre</p>
            <strong>${escapeDynamicHtml(formatDynamicTimestamp(closedAt))}</strong>
          </article>
          <article>
            <p class="historical-match-meta__label">Jugadores</p>
            <strong>${escapeDynamicHtml(formatDynamicNumber(item?.player_count))}</strong>
          </article>
          <article>
            <p class="historical-match-meta__label">Marcador</p>
            <strong>${escapeDynamicHtml(formatDynamicScore(item?.result))}</strong>
          </article>
          <article class="historical-match-card__actions-cell">
            <div class="historical-match-card__actions">
              ${actions}
            </div>
          </article>
        </div>
      </article>
    `;
  }

  function formatDynamicResultLabel(result) {
    const winner = String(result?.winner || "").toLowerCase();
    if (winner === "allies" || winner === "allied") {
      return "Victoria aliada";
    }
    if (winner === "axis") {
      return "Victoria axis";
    }
    return "Empate";
  }

  function buildDynamicInternalMatchDetailUrl(item) {
    const serverSlug = item?.server?.slug;
    const matchId = item?.internal_detail_match_id || item?.match_id;
    if (!serverSlug || matchId === undefined || matchId === null) {
      return "";
    }
    return `./historico-partida.html?server=${encodeURIComponent(String(serverSlug))}&match=${encodeURIComponent(String(matchId))}`;
  }

  function normalizeDynamicExternalMatchUrl(value) {
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

  function buildDynamicRecentMeta(data, items) {
    const newest = items[0]?.closed_at || items[0]?.ended_at || items[0]?.started_at;
    const source = data.selected_source || data.source || "rcon";
    const captureText = newest ? `Actualizado: ${formatDynamicTimestamp(newest)}` : "Actualizado recientemente";
    return `${captureText} | Fuente: ${source}`;
  }

  function setDynamicState(node, message, isError = false) {
    node.textContent = message;
    node.hidden = false;
    node.classList.toggle("is-error", Boolean(isError));
  }

  function formatDynamicTimestamp(value) {
    if (!value) {
      return "Fecha no disponible";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return String(value);
    }
    return new Intl.DateTimeFormat("es-ES", {
      day: "numeric",
      month: "numeric",
      year: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    }).format(date);
  }

  function formatDynamicNumber(value) {
    const number = Number(value);
    return Number.isFinite(number) ? new Intl.NumberFormat("es-ES").format(number) : "0";
  }

  function formatDynamicScore(result) {
    const allied = result?.allied_score;
    const axis = result?.axis_score;
    if (Number.isFinite(Number(allied)) && Number.isFinite(Number(axis))) {
      return `${allied} - ${axis}`;
    }
    return "- - -";
  }

  function escapeDynamicHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }
})();
