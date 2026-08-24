const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const mapImages = require("../assets/js/map-image-resolver.js");
const source = fs.readFileSync(path.join(__dirname, "../assets/js/main.js"), "utf8");
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

test("score preserves real zero and distinguishes unknown", () => {
  assert.match(runtime.renderServerStatsCard(server({ allied_score: 0, axis_score: 0 })), /Puntuación: 0 — 0/);
  const unknown = runtime.renderServerStatsCard(server({ allied_score: null, axis_score: null }));
  assert.match(unknown, /Puntuación: —/);
  assert.doesNotMatch(unknown, /Puntuación: 0 — 0/);
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
