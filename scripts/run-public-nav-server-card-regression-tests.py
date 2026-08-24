"""Frontend regression checks for the five-link nav and semantic HLLV cards."""

from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
PUBLIC_PAGES = (
    "index.html",
    "historico.html",
    "historico-partida.html",
    "stats.html",
    "ranking.html",
    "partida-actual.html",
    "vip.html",
)
EXPECTED_LINKS = (
    "./index.html",
    "./historico.html",
    "./stats.html",
    "./ranking.html",
    "./vip.html",
)
ACTIVE_PAGES = {
    "index.html": "./index.html",
    "historico.html": "./historico.html",
    "stats.html": "./stats.html",
    "ranking.html": "./ranking.html",
    "vip.html": "./vip.html",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


for page_name in PUBLIC_PAGES:
    html = (FRONTEND / page_name).read_text(encoding="utf-8-sig")
    navs = re.findall(r'<nav class="public-nav".*?</nav>', html, flags=re.DOTALL)
    require(len(navs) == 1, f"{page_name} must contain exactly one public nav")
    links = tuple(re.findall(r'href="([^"]+)"', navs[0]))
    require(links == EXPECTED_LINKS, f"{page_name} has an outdated public nav: {links}")
    if page_name in ACTIVE_PAGES:
        active = re.findall(
            r'<a class="public-nav__link is-active" href="([^"]+)"[^>]*aria-current="page"',
            navs[0],
        )
        require(active == [ACTIVE_PAGES[page_name]], f"{page_name} active nav is incorrect")

css = (FRONTEND / "assets/css/styles.css").read_text(encoding="utf-8-sig")
main_js = (FRONTEND / "assets/js/main.js").read_text(encoding="utf-8-sig")

require("grid-template-columns: repeat(5, minmax(0, 1fr));" in css, "Desktop nav is not five columns")
require("white-space: nowrap;" in css, "Nav labels may still wrap")
require("grid-template-columns: repeat(2, minmax(0, 1fr));" in css, "Mobile nav adaptation is missing")
require("normalizeServerGame(server.game)" in main_js, "Card variant does not use server.game")
require('serverGame === "hllv" ? "server-card--game-hllv"' in main_js, "HLLV class mapping is missing")
require('data-game="${escapeHtml(serverGame)}"' in main_js, "Normalized game metadata is missing")
require(".server-card--game-hllv" in css, "HLLV card color variant is missing")
normalizer = main_js[
    main_js.index("function normalizeServerGame") : main_js.index("function normalizeServerRegion")
]
require("serverName" not in normalizer, "Game detection must not inspect the server name")

print("Public nav and semantic HLLV card regression validation passed.")
