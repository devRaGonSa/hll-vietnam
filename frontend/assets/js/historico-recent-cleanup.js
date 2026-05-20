(() => {
  window.renderRecentMatchCard = function renderRecentMatchCard(item) {
    const mapName = item.map?.pretty_name || item.map?.name || "Mapa no disponible";
    const matchUrl = normalizeExternalMatchUrl(item.match_url);
    const detailUrl = buildInternalMatchDetailUrl(item);
    const actionLinks = [
      `<span class="historical-match-card__result">${escapeHtml(formatMatchResult(item.result))}</span>`,
      detailUrl
        ? `
          <a
            class="historical-match-card__link"
            href="${escapeHtml(detailUrl)}"
          >
            Ver detalles
          </a>
        `
        : "",
      matchUrl
        ? `
          <a
            class="historical-match-card__link"
            href="${escapeHtml(matchUrl)}"
            target="_blank"
            rel="noopener noreferrer"
          >
            Ver partida
          </a>
        `
        : "",
    ].join("");

    return `
      <article class="historical-match-card historical-match-card--clean">
        <div class="historical-match-card__top">
          <h3 class="historical-match-card__title">${escapeHtml(mapName)}</h3>
        </div>
        <div class="historical-match-meta historical-match-meta--clean">
          <article>
            <p class="historical-match-meta__label">Servidor</p>
            <strong>${escapeHtml(item.server?.name || "Servidor no disponible")}</strong>
          </article>
          <article>
            <p class="historical-match-meta__label">Cierre</p>
            <strong>${escapeHtml(formatTimestamp(item.closed_at))}</strong>
          </article>
          <article>
            <p class="historical-match-meta__label">Jugadores</p>
            <strong>${escapeHtml(formatNumber(item.player_count))}</strong>
          </article>
          <article>
            <p class="historical-match-meta__label">Marcador</p>
            <strong>${escapeHtml(formatScore(item.result))}</strong>
          </article>
          <article class="historical-match-card__actions-cell" aria-label="Acciones de la partida">
            <div class="historical-match-card__actions">
              ${actionLinks}
            </div>
          </article>
        </div>
      </article>
    `;
  };
})();
