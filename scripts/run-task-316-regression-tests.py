"""Static frontend regression checks for TASK-316."""

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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


index = (FRONTEND / "index.html").read_text(encoding="utf-8-sig")
vip = (FRONTEND / "vip.html").read_text(encoding="utf-8")
historical_js = (FRONTEND / "assets/js/historico.js").read_text(encoding="utf-8-sig")
ranking_js = (FRONTEND / "assets/js/ranking.js").read_text(encoding="utf-8-sig")
stats_js = (FRONTEND / "assets/js/stats.js").read_text(encoding="utf-8-sig")

require("panel--vip" not in index, "VIP block remains on the home page")
require("release-countdown" not in index, "Launch countdown was restored")
for page_name in PUBLIC_PAGES:
    html = (FRONTEND / page_name).read_text(encoding="utf-8-sig")
    navs = re.findall(r'<nav class="public-nav".*?</nav>', html, flags=re.DOTALL)
    require(len(navs) == 1, f"{page_name} must contain one public nav")
    require('href="./vip.html"' in navs[0], f"{page_name} nav lacks VIP")
require('href="./vip.html" aria-current="page">VIP</a>' in vip, "VIP nav is not active")
require("HLL Vietnam</span><strong>+12 h VIP" in vip, "Verified HLLV Seed VIP is missing")
require("HLL #1 y HLL #2</span><strong>+24 h VIP" in vip, "Classic Seed VIP is missing")
require("Solo Hell Let Loose clásico · HLL #1 y HLL #2" in vip, "Weekly classic scope is ambiguous")
require("Estos retos no se aplican a HLL Vietnam" in vip, "Weekly HLLV exclusion is missing")
require("CDO" not in vip and "CDE" not in vip, "Unverified rewards were published")
require("item.player_name" in historical_js, "Historical does not use canonical player_name")
require("item.player?.name" not in historical_js, "Obsolete nested historical name contract remains")
require("Genera el snapshot" not in ranking_js, "Ranking still instructs snapshot generation")
require("Snapshot anual listo" not in ranking_js, "Ranking still labels CRCON data as a snapshot")
require("Estado de lectura" in ranking_js, "Ranking lacks CRCON read status wording")
require("describeAggregateProblem" in historical_js, "Historical lacks aggregate error states")
require("aggregateState" in ranking_js, "Ranking lacks aggregate error states")
require("describeAggregateProblem" in stats_js, "Stats lacks aggregate error states")
require("aggregateReason" in historical_js + ranking_js + stats_js, "Machine reasons are not preserved")
require("Jugador no identificado" in stats_js, "Stats opaque-name fallback is not safe")

print("TASK-316 frontend regression validation passed.")
