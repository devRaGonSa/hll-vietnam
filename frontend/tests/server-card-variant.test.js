const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const mapImages = require("../assets/js/map-image-resolver.js");
const source = fs.readFileSync(path.join(__dirname, "../assets/js/main.js"), "utf8");
const css = fs.readFileSync(path.join(__dirname, "../assets/css/styles.css"), "utf8");
const runtime = {
  HLL_MAP_IMAGES: mapImages,
  console: { info() {}, warn() {} },
  document: { addEventListener() {} },
};
vm.createContext(runtime);
vm.runInContext(source, runtime);

function server(overrides = {}) {
  return {
    external_server_id: "comunidad-hispana-01",
    server_name: "#1 [ESP] - Comu Hispana - Allies vs Axis - discord.comunidadhll.es",
    status: "online",
    players: 50,
    max_players: 100,
    current_map: "St. Mere Eglise",
    allied_score: 3,
    axis_score: 2,
    remaining_match_time_seconds: 2052,
    snapshot_origin: "real-rcon",
    game: "hll",
    ...overrides,
  };
}

test("trusted target IDs map to the three compact server labels", () => {
  const cases = [
    ["comunidad-hispana-01", "Servidor 1"],
    ["comunidad-hispana-02", "Servidor 2"],
    ["comunidad-hll-vietnam-01", "Servidor 3"],
  ];
  for (const [target, label] of cases) {
    const markup = runtime.renderServerStatsCard(server({ external_server_id: target }));
    assert.match(markup, new RegExp(`<h3>${label}</h3>`));
    assert.match(markup, new RegExp(`data-server-target="${target}"`));
    assert.doesNotMatch(markup, /Comu Hispana|Allies vs Axis|discord\.comunidadhll\.es/);
  }
});

test("visible names never determine the compact server number", () => {
  const markup = runtime.renderServerStatsCard(server({
    external_server_id: "unknown-target",
    server_name: "Comunidad Hispana #01",
  }));
  assert.match(markup, /<h3>Servidor<\/h3>/);
  assert.doesNotMatch(markup, /<h3>Servidor 1<\/h3>/);
});

test("classic and Vietnam variants derive only from the semantic game field", () => {
  const classic = runtime.renderServerStatsCard(server({
    server_name: "HLL Vietnam escrito en el nombre",
    game: "hll",
  }));
  assert.match(classic, /data-game="hll"/);
  assert.doesNotMatch(classic, /server-card--game-hllv/);
  assert.match(classic, /Hell Let Loose/);

  const vietnam = runtime.renderServerStatsCard(server({
    external_server_id: "comunidad-hll-vietnam-01",
    server_name: "Nombre clásico deliberado",
    current_map: "Huế Outskirts",
    game: "hllv",
  }));
  assert.match(vietnam, /data-game="hllv"/);
  assert.match(vietnam, /server-card--game-hllv/);
  assert.match(vietnam, /Hell Let Loose Vietnam/);
});

test("map name and lazy local thumbnail replace the static MAPA label", () => {
  const markup = runtime.renderServerStatsCard(server());
  assert.match(markup, /server-card__map-name">St\. Mere Eglise/);
  assert.match(markup, /src="\.\/assets\/img\/maps\/stmereeglise-day\.webp"/);
  assert.match(markup, /alt="Mapa St\. Mere Eglise"/);
  assert.match(markup, /loading="lazy"/);
  assert.doesNotMatch(markup, />MAPA</i);
  assert.match(css, /\.server-card__map\s*\{[\s\S]*?grid-template-columns:\s*82px minmax\(0, 1fr\)/);
  assert.match(css, /\.server-card__map-image\s*\{[\s\S]*?height:\s*46px;[\s\S]*?object-fit:\s*contain;/);
  assert.doesNotMatch(css, /\.server-card__map-image\s*\{[\s\S]*?object-fit:\s*cover;/);
  assert.match(css, /@media \(max-width: 640px\)[\s\S]*?\.server-card__map-image\s*\{\s*height:\s*42px;/);
});

test("unknown and HLLV maps use the explicit local fallback", () => {
  for (const overrides of [
    { current_map: "Mapa futuro", game: "hll" },
    { current_map: "Huế Outskirts", game: "hllv", external_server_id: "comunidad-hll-vietnam-01" },
  ]) {
    const markup = runtime.renderServerStatsCard(server(overrides));
    assert.match(markup, /data-image-state="fallback"/);
    assert.match(markup, /src="\.\/assets\/img\/maps\/unknown-day\.webp"/);
    assert.match(markup, /alt=""/);
  }
});

test("scorebar represents Allies lead, Axis lead and ties proportionally", () => {
  const allies = runtime.renderServerStatsCard(server({ allied_score: 3, axis_score: 2 }));
  assert.match(allies, /server-card__scoreboard--allies/);
  assert.match(allies, /--allied-score-share: 60\.00%; --axis-score-share: 40\.00%/);
  assert.match(allies, /server-card__scoreboard-team--allies[\s\S]*?<span>Allies<\/span>[\s\S]*?<strong>3<\/strong>/);
  assert.match(allies, /server-card__scoreboard-team--axis[\s\S]*?<strong>2<\/strong>[\s\S]*?<span>Axis<\/span>/);
  assert.doesNotMatch(allies, />3 — 2</);

  const axis = runtime.renderServerStatsCard(server({ allied_score: 2, axis_score: 3 }));
  assert.match(axis, /server-card__scoreboard--axis/);
  assert.match(axis, /--allied-score-share: 40\.00%; --axis-score-share: 60\.00%/);
  assert.match(axis, /<span>Allies<\/span>[\s\S]*?<strong>2<\/strong>/);
  assert.match(axis, /<strong>3<\/strong>[\s\S]*?<span>Axis<\/span>/);

  const tie = runtime.renderServerStatsCard(server({ allied_score: 2, axis_score: 2 }));
  assert.match(tie, /server-card__scoreboard--tie/);
  assert.match(tie, /--allied-score-share: 50\.00%; --axis-score-share: 50\.00%/);
  assert.match(tie, /Puntuación: Allies 2, Axis 2\. Empate\./);
  assert.doesNotMatch(tie, />2 — 2</);

  assert.match(css, /server-card__scorebar-side--allies[\s\S]*?#426d91/);
  assert.match(css, /server-card__scorebar-side--axis[\s\S]*?#b95c54/);
});

test("scorebar preserves real zero and distinguishes unknown", () => {
  const zero = runtime.renderServerStatsCard(server({ allied_score: 0, axis_score: 0 }));
  assert.match(zero, /Puntuación: Allies 0, Axis 0\. Empate\./);
  assert.match(zero, /<span>Allies<\/span>[\s\S]*?<strong>0<\/strong>/);
  assert.match(zero, /<strong>0<\/strong>[\s\S]*?<span>Axis<\/span>/);
  assert.doesNotMatch(zero, />0 — 0</);
  assert.match(zero, /--allied-score-share: 50\.00%; --axis-score-share: 50\.00%/);
  const unknown = runtime.renderServerStatsCard(server({ allied_score: null, axis_score: null }));
  assert.match(unknown, /aria-label="Puntuación no disponible\."/);
  assert.equal((unknown.match(/<strong>—<\/strong>/g) || []).length, 2);
  assert.match(unknown, /server-card__scoreboard--unknown/);
  assert.match(unknown, /server-card__scorebar-unknown/);
  assert.doesNotMatch(unknown, /server-card__scorebar-side--allies/);
});

test("remaining time formats real, long, zero and unknown values", () => {
  assert.equal(runtime.formatRemainingTime(2052), "34:12");
  assert.equal(runtime.formatRemainingTime(4354), "1:12:34");
  assert.equal(runtime.formatRemainingTime(0), "00:00");
  assert.equal(runtime.formatRemainingTime(null), "—");
  const unknown = runtime.renderServerStatsCard(server({ remaining_match_time_seconds: null }));
  assert.match(unknown, /Tiempo restante: —/);
  assert.doesNotMatch(unknown, /data-remaining-seconds/);
});

test("countdown never drops below zero and replaces its interval on refresh", () => {
  const node = {
    dataset: { remainingSeconds: "1" },
    textContent: "00:01",
    setAttribute(name, value) { this[name] = value; },
  };
  const ownerDocument = {
    querySelector: () => node,
    querySelectorAll: () => [node],
  };
  const cleared = [];
  let nextTimer = 0;
  const timerScope = {
    setInterval() { nextTimer += 1; return nextTimer; },
    clearInterval(id) { cleared.push(id); },
  };
  assert.equal(runtime.restartServerCountdown(ownerDocument, timerScope), 1);
  assert.equal(runtime.restartServerCountdown(ownerDocument, timerScope), 2);
  assert.deepEqual(cleared, [1]);
  runtime.tickServerCountdown(ownerDocument);
  runtime.tickServerCountdown(ownerDocument);
  assert.equal(node.textContent, "00:00");
  assert.equal(node.dataset.remainingSeconds, "0");
});

test("historical and current-match links remain trusted for supported targets", () => {
  const markup = runtime.renderServerStatsCard(server());
  assert.match(markup, /href="\.\/historico\.html\?server=comunidad-hispana-01"/);
  assert.match(markup, /href="\.\/partida-actual\.html\?server=comunidad-hispana-01"/);
});
