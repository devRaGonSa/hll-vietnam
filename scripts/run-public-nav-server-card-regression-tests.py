"""Static frontend regression checks for TASK-321 and semantic HLLV cards."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
PUBLIC_PAGES = ("index.html", "historico.html", "historico-partida.html", "stats.html", "ranking.html", "partida-actual.html", "vip.html", "normativa.html", "bots.html")
EXPECTED_LINKS = ("./index.html", "./historico.html", "./stats.html", "./ranking.html", "./vip.html", "./normativa.html", "./bots.html")
CURRENT = {"historico.html": "./historico.html", "stats.html": "./stats.html", "ranking.html": "./ranking.html", "vip.html": "./vip.html", "normativa.html": "./normativa.html", "bots.html": "./bots.html"}
SERVER_PAGES = {"historico.html", "historico-partida.html", "stats.html", "ranking.html", "partida-actual.html"}
COMMUNITY_PAGES = {"vip.html", "normativa.html", "bots.html"}

def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)

structures = []
for page_name in PUBLIC_PAGES:
    html = (FRONTEND / page_name).read_text(encoding="utf-8-sig")
    navs = re.findall(r'<nav class="public-nav".*?</nav>', html, flags=re.DOTALL)
    require(len(navs) == 1, f"{page_name} must contain exactly one public nav")
    nav = navs[0]
    structures.append(re.sub(r"\s+", "", re.sub(r" is-active| is-current| aria-current=\"page\"", "", nav)))
    require(tuple(re.findall(r'href="([^"]+)"', nav)) == EXPECTED_LINKS, f"{page_name} nav links are wrong")
    require(len(re.findall(r'class="public-nav__(?:link|trigger)', nav)) == 3, f"{page_name} must have three top-level controls")
    require(nav.count("data-nav-trigger") == 2 and nav.count('aria-expanded="false"') == 2, f"{page_name} dropdown ARIA is missing")
    require(nav.count('aria-haspopup="true"') == 2 and "public-nav.js?v=321" in html, f"{page_name} shared accessible nav is incomplete")
    require('<main class="content' in html, f"{page_name} does not use the shared non-overlapping content layout")
    if page_name == "index.html":
        require('public-nav__link is-active" href="./index.html" aria-current="page"' in nav, "Home active state is wrong")
    if page_name in SERVER_PAGES:
        require('public-nav__group is-active' in nav and "Servidores" in nav.split('public-nav__group is-active', 1)[1].split("</button>", 1)[0], f"{page_name} server group is not active")
    if page_name in COMMUNITY_PAGES:
        require('public-nav__group is-active' in nav and "Comunidad" in nav.split('public-nav__group is-active', 1)[1].split("</button>", 1)[0], f"{page_name} community group is not active")
    if page_name in CURRENT:
        require(f'class="public-nav__menu-link is-current" href="{CURRENT[page_name]}" aria-current="page"' in nav, f"{page_name} current destination is wrong")
require(len(set(structures)) == 1, "Public pages do not share the same navigation structure")

css = (FRONTEND / "assets/css/styles.css").read_text(encoding="utf-8-sig")
nav_js = (FRONTEND / "assets/js/public-nav.js").read_text(encoding="utf-8")
main_js = (FRONTEND / "assets/js/main.js").read_text(encoding="utf-8-sig")
normative = (FRONTEND / "normativa.html").read_text(encoding="utf-8")
bots = (FRONTEND / "bots.html").read_text(encoding="utf-8")
vip = (FRONTEND / "vip.html").read_text(encoding="utf-8")
static_server = (FRONTEND / "static_server.py").read_text(encoding="utf-8")
normative_source = (ROOT / "docs/NORMATIVA_PUBLICA_SOURCE.md").read_text(encoding="utf-8")

for fragment in ('"click"', '"Escape"', "ownerDocument.addEventListener", "closeAll(group)"):
    require(fragment in nav_js, f"Shared nav behavior lacks {fragment}")
require("grid-template-columns: repeat(3, minmax(0, 1fr));" in css, "Nav is not three columns")
require("position: absolute;" in css and "z-index: 60;" in css, "Dropdown overlay positioning is missing")
require("margin-top: -28px;" not in css, "Shared content still overlaps the hero")
require(re.search(r"\.content\s*\{[^}]*margin-top:\s*24px;", css, flags=re.DOTALL) is not None, "Shared content lacks positive hero spacing")
require(re.search(r"\.public-nav__chevron\s*\{[^}]*font-size:\s*1\.05em;", css, flags=re.DOTALL) is not None, "Dropdown chevron remains too small")
require(re.search(r"\.public-nav__group\.is-open \.public-nav__chevron\s*\{[^}]*rotate\(180deg\)", css, flags=re.DOTALL) is not None, "Open dropdown no longer rotates its chevron")
require("position: sticky;" in css and ".normative-index--mobile" in css, "Responsive normative index is missing")
require(".content.normative-layout" in css, "Normative layout lacks its centered container")
require("width: min(1240px, calc(100vw - (var(--page-shell-gutter) * 2)));" in css, "Normative container is not width-constrained")
require("grid-template-columns: minmax(220px, 240px) minmax(0, 960px);" in css, "Normative desktop columns are not constrained")
require("max-width: 960px;" in css, "Normative article lacks a readable maximum width")
require("@media (max-width: 1024px)" in css, "Normative layout does not collapse for tablet widths")

ids = ("servidores-usuarios", "seedeo", "servidores-clanes", "discord-usuarios", "discord-clanes", "eventos", "miembros-vip", "creadores-contenido", "sanciones", "confrontacion")
for section_id in ids:
    require(f'id="{section_id}"' in normative, f"Missing normative section #{section_id}")
    require(normative.count(f'href="#{section_id}"') == 2, f"Index anchor #{section_id} is missing")
require("NORMATIVA DEL STAFF" not in normative.upper(), "Staff rules were published")
require("Ver original en Discord" not in normative and "normative-source" not in normative, "Public original-source buttons remain in normative HTML")
source_links = set(re.findall(r"https://discord\.com/\S+", normative_source))
require(len(source_links) == 9, "Editorial source no longer retains all nine original Discord links")
require("IntersectionObserver" in (FRONTEND / "assets/js/normativa.js").read_text(encoding="utf-8"), "Active-section behavior is missing")
require("Guía en preparación" not in bots, "Bots page is still a placeholder")
require("Comandos en chat" in bots and "Automatizaciones del servidor" in bots, "Verified bots guide is missing")
require('href="./normativa.html"' in bots and 'href="./vip.html"' in bots, "Bots guide links are incomplete")
require("Activo de 09:30 a 21:30 Europe/Madrid." in vip, "Verified VIP schedule changed")
for removed in ("VIP indefinido", "acumulación/ciclos", "temporal/indefinido"):
    require(removed.lower() not in vip.lower(), f"Removed VIP wording returned: {removed}")
require("no-store, no-cache, must-revalidate, max-age=0" in static_server, "HTML no-store policy changed")
require("normalizeServerGame(server.game)" in main_js, "Card variant does not use server.game")
require('serverGame === "hllv" ? "server-card--game-hllv"' in main_js, "HLLV class mapping is missing")
require('data-game="${escapeHtml(serverGame)}"' in main_js and ".server-card--game-hllv" in css, "Semantic HLLV card variant is missing")
normalizer = main_js[main_js.index("function normalizeServerGame") : main_js.index("function normalizeServerRegion")]
require("serverName" not in normalizer, "Game detection must not inspect the server name")
print("TASK-321 public nav, normative content, bots page, cache and HLLV validation passed.")
