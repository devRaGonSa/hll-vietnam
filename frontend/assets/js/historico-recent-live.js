(() => {
  const RECENT_MATCHES_ENDPOINT = "/api/historical/snapshots/recent-matches";
  const REFRESH_DELAYS_MS = [150, 1000, 3000, 6000];
  const RECENT_MATCHES_POLL_INTERVAL_MS = 60000;
  const RECENT_MATCHES_LIMIT = 100;
  const DEFAULT_RECENT_MATCHES_PAGE_SIZE = 10;
  const RECENT_MATCHES_PAGE_SIZES = Object.freeze([10, 25, 50, 100]);
  const LIVE_PAGINATION_ID = "recent-matches-live-pagination";
  const LEGACY_PAGINATION_ID = "recent-matches-pagination";

  const recentMatchesState = {
    items: [],
    serverSlug: "all-servers",
    page: 1,
    pageSize: DEFAULT_RECENT_MATCHES_PAGE_SIZE,
    activeRequestId: 0,
    rendering: false,
    observerReady: false,
  };

  document.addEventListener("DOMContentLoaded", () => {
    ensureDynamicPaginationControls();
    setupRecentMatchesOwnershipObserver();

    REFRESH_DELAYS_MS.forEach((delay) => {
      window.setTimeout(() => {
        void refreshDynamicRecentMatches();
      }, delay);
    });
    window.setInterval(() => {
      void refreshDynamicRecentMatches();
    }, RECENT_MATCHES_POLL_INTERVAL_MS);

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

    if (!listNode || !stateNode || !metaNode) return;

    const backendBaseUrl = document.body.dataset.backendBaseUrl || "http://127.0.0.1:8000";
    const serverSlug = normalizeDynamicServerSlug(forcedServerSlug || readServerFromUrl());
    const shouldResetPage = serverSlug !== recentMatchesState.serverSlug;
    const requestId = recentMatchesState.activeRequestId + 1;
    recentMatchesState.activeRequestId = requestId;
    recentMatchesState.serverSlug = serverSlug;

    try {
      const response = await fetch(`${backendBaseUrl}${RECENT_MATCHES_ENDPOINT}?server=${encodeURIComponent(serverSlug)}&limit=${RECENT_MATCHES_LIMIT}`, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      const payload = await response.json();
      if (requestId !== recentMatchesState.activeRequestId || serverSlug !== recentMatchesState.serverSlug) {
        return;
      }
      const data = payload?.data || {};
      const items = Array.isArray(data.items) ? data.items : [];

      recentMatchesState.items = items;
      if (shouldResetPage) {
        recentMatchesState.page = 1;
      }

      if (!items.length) {
        recentMatchesState.page = 1;
        setDynamicState(stateNode, "No hay partidas recientes disponibles para este alcance.");
        renderOwnedList(listNode, "");
        metaNode.textContent = "Datos recientes sin partidas disponibles.";
        renderDynamicPagination();
        return;
      }

      stateNode.hidden = true;
      if (noteNode) noteNode.textContent = "Lista dinámica de partidas registradas.";
      metaNode.textContent = buildDynamicRecentMeta(items);
      renderDynamicRecentMatchesPage();
    } catch (error) {
      if (requestId !== recentMatchesState.activeRequestId || serverSlug !== recentMatchesState.serverSlug) {
        return;
      }
      recentMatchesState.items = [];
      recentMatchesState.page = 1;
      setDynamicState(stateNode, "No se pudieron cargar las partidas recientes dinámicas.", true);
      metaNode.textContent = "Error al leer las partidas recientes dinámicas.";
      renderDynamicPagination();
    }
  }

  function renderDynamicRecentMatchesPage() {
    const listNode = document.getElementById("recent-matches-list");
    const stateNode = document.getElementById("recent-matches-state");
    if (!listNode || !stateNode) return;

    const totalItems = recentMatchesState.items.length;
    const totalPages = getDynamicTotalPages();
    recentMatchesState.page = clampDynamicPage(recentMatchesState.page, totalPages);

    if (!totalItems) {
      renderOwnedList(listNode, "");
      setDynamicState(stateNode, "No hay partidas recientes disponibles para este alcance.");
      renderDynamicPagination();
      return;
    }

    const startIndex = (recentMatchesState.page - 1) * recentMatchesState.pageSize;
    const pageItems = recentMatchesState.items.slice(startIndex, startIndex + recentMatchesState.pageSize);
    renderOwnedList(listNode, pageItems.map((item) => renderDynamicRecentMatchCard(item)).join(""));
    stateNode.hidden = true;
    renderDynamicPagination();
  }

  function renderOwnedList(listNode, html) {
    recentMatchesState.rendering = true;
    listNode.innerHTML = html;
    window.queueMicrotask(() => {
      recentMatchesState.rendering = false;
    });
  }

  function setupRecentMatchesOwnershipObserver() {
    const listNode = document.getElementById("recent-matches-list");
    if (!listNode || recentMatchesState.observerReady || typeof MutationObserver === "undefined") return;

    recentMatchesState.observerReady = true;
    const observer = new MutationObserver(() => {
      if (recentMatchesState.rendering || !recentMatchesState.items.length) return;
      window.setTimeout(() => {
        if (!recentMatchesState.rendering && recentMatchesState.items.length) {
          renderDynamicRecentMatchesPage();
        }
      }, 0);
    });
    observer.observe(listNode, { childList: true });
  }

  function ensureDynamicPaginationControls() {
    const listNode = document.getElementById("recent-matches-list");
    if (!listNode || document.getElementById(LIVE_PAGINATION_ID)) return;

    const paginationNode = document.createElement("div");
    paginationNode.className = "historical-pagination";
    paginationNode.id = LIVE_PAGINATION_ID;
    paginationNode.hidden = true;

    const sizeLabel = document.createElement("label");
    sizeLabel.className = "historical-pagination__size";
    sizeLabel.append("Mostrar ");

    const pageSizeSelect = document.createElement("select");
    pageSizeSelect.id = "recent-matches-live-page-size";
    pageSizeSelect.setAttribute("aria-label", "Partidas por pagina");
    RECENT_MATCHES_PAGE_SIZES.forEach((size) => {
      const option = document.createElement("option");
      option.value = String(size);
      option.textContent = String(size);
      option.selected = size === DEFAULT_RECENT_MATCHES_PAGE_SIZE;
      pageSizeSelect.append(option);
    });
    sizeLabel.append(pageSizeSelect);

    const navNode = document.createElement("div");
    navNode.className = "historical-pagination__nav";
    navNode.setAttribute("aria-label", "Paginacion de partidas recientes");

    const prevButton = document.createElement("button");
    prevButton.className = "historical-tab";
    prevButton.type = "button";
    prevButton.id = "recent-matches-live-prev";
    prevButton.textContent = "Anterior";

    const pageLabel = document.createElement("p");
    pageLabel.id = "recent-matches-live-page-label";
    pageLabel.textContent = "Pagina 1 de 1";

    const nextButton = document.createElement("button");
    nextButton.className = "historical-tab";
    nextButton.type = "button";
    nextButton.id = "recent-matches-live-next";
    nextButton.textContent = "Siguiente";

    navNode.append(prevButton, pageLabel, nextButton);
    paginationNode.append(sizeLabel, navNode);
    listNode.insertAdjacentElement("afterend", paginationNode);

    pageSizeSelect.addEventListener("change", () => {
      const nextPageSize = Number(pageSizeSelect.value);
      recentMatchesState.pageSize = RECENT_MATCHES_PAGE_SIZES.includes(nextPageSize) ? nextPageSize : DEFAULT_RECENT_MATCHES_PAGE_SIZE;
      recentMatchesState.page = 1;
      renderDynamicRecentMatchesPage();
    });
    prevButton.addEventListener("click", () => {
      recentMatchesState.page -= 1;
      renderDynamicRecentMatchesPage();
    });
    nextButton.addEventListener("click", () => {
      recentMatchesState.page += 1;
      renderDynamicRecentMatchesPage();
    });
  }

  function hideLegacyPagination() {
    const legacyPagination = document.getElementById(LEGACY_PAGINATION_ID);
    if (legacyPagination) {
      legacyPagination.hidden = true;
    }
  }

  function renderDynamicPagination() {
    ensureDynamicPaginationControls();
    hideLegacyPagination();

    const paginationNode = document.getElementById(LIVE_PAGINATION_ID);
    const pageSizeSelect = document.getElementById("recent-matches-live-page-size");
    const prevButton = document.getElementById("recent-matches-live-prev");
    const nextButton = document.getElementById("recent-matches-live-next");
    const pageLabel = document.getElementById("recent-matches-live-page-label");
    if (!paginationNode || !pageSizeSelect || !prevButton || !nextButton || !pageLabel) return;

    const totalItems = recentMatchesState.items.length;
    const totalPages = getDynamicTotalPages();
    recentMatchesState.page = clampDynamicPage(recentMatchesState.page, totalPages);
    paginationNode.hidden = totalItems <= recentMatchesState.pageSize;
    pageSizeSelect.value = String(recentMatchesState.pageSize);
    prevButton.disabled = recentMatchesState.page <= 1;
    nextButton.disabled = recentMatchesState.page >= totalPages;
    pageLabel.textContent = `Pagina ${recentMatchesState.page} de ${totalPages}`;
  }

  function getDynamicTotalPages() {
    return Math.max(1, Math.ceil(recentMatchesState.items.length / recentMatchesState.pageSize));
  }

  function clampDynamicPage(page, totalPages) {
    const numericPage = Number(page);
    if (!Number.isFinite(numericPage)) return 1;
    return Math.min(Math.max(1, Math.trunc(numericPage)), totalPages);
  }

  function renderDynamicRecentMatchCard(item) {
    const mapName = item?.map?.pretty_name || item?.map?.name || "Mapa no disponible";
    const serverName = item?.server?.name || "Servidor no disponible";
    const closedAt = item?.closed_at || item?.ended_at || item?.started_at;
    const detailUrl = buildDynamicInternalMatchDetailUrl(item);
    const actionLinks = [`<span class="historical-match-card__result">${escapeDynamicHtml(formatDynamicResultLabel(item?.result))}</span>`, detailUrl ? `<a class="historical-match-card__link" href="${escapeDynamicHtml(detailUrl)}">Ver detalles</a>` : ""].join("");

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

          <article class="historical-match-card__actions-cell" aria-label="Acciones de la partida">
            <div class="historical-match-card__actions">
              ${actionLinks}
            </div>
          </article>
        </div>
      </article>
    `;
  }

  function readServerFromUrl() {
    return new URLSearchParams(window.location.search).get("server") || "all-servers";
  }

  function normalizeDynamicServerSlug(value) {
    const normalized = String(value || "").trim();
    if (["comunidad-hispana-01", "comunidad-hispana-02", "all-servers"].includes(normalized)) return normalized;
    return "all-servers";
  }

  function buildDynamicRecentMeta(items) {
    const newest = items[0]?.closed_at || items[0]?.ended_at || items[0]?.started_at;
    return newest ? `Actualizado: ${formatDynamicTimestamp(newest)}` : "Actualizado recientemente";
  }

  function setDynamicState(node, message, isError = false) {
    node.textContent = message;
    node.hidden = false;
    node.classList.toggle("is-error", Boolean(isError));
  }

  function formatDynamicTimestamp(value) {
    if (!value) return "Fecha no disponible";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return new Intl.DateTimeFormat("es-ES", { day: "numeric", month: "numeric", year: "2-digit", hour: "2-digit", minute: "2-digit" }).format(date);
  }

  function formatDynamicNumber(value) {
    const number = Number(value);
    return Number.isFinite(number) ? new Intl.NumberFormat("es-ES").format(number) : "0";
  }

  function formatDynamicScore(result) {
    const allied = result?.allied_score;
    const axis = result?.axis_score;
    if (Number.isFinite(Number(allied)) && Number.isFinite(Number(axis))) return `${allied} - ${axis}`;
    return "- - -";
  }

  function formatDynamicResultLabel(result) {
    const winner = String(result?.winner || "").toLowerCase();
    if (winner === "allies" || winner === "allied") return "Victoria aliada";
    if (winner === "axis") return "Victoria axis";
    return "Empate";
  }

  function buildDynamicInternalMatchDetailUrl(item) {
    const serverSlug = item?.server?.slug;
    const matchId = item?.internal_detail_match_id || item?.match_id;
    if (!serverSlug || matchId === undefined || matchId === null) return "";
    return `./historico-partida.html?server=${encodeURIComponent(String(serverSlug))}&match=${encodeURIComponent(String(matchId))}`;
  }

  function normalizeDynamicExternalMatchUrl(value) {
    if (typeof value !== "string" || !value.trim()) return "";
    try {
      const url = new URL(value.trim());
      return ["http:", "https:"].includes(url.protocol) ? url.href : "";
    } catch (error) {
      return "";
    }
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
