const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(
  path.join(__dirname, "../assets/js/main.js"),
  "utf8",
);
const runtime = {
  console: { info() {}, warn() {} },
  document: { addEventListener() {} },
};
vm.createContext(runtime);
vm.runInContext(source, runtime);

function server(overrides = {}) {
  return {
    server_name: "Servidor de prueba",
    status: "online",
    players: 50,
    max_players: 100,
    current_map: "Mapa de prueba",
    snapshot_origin: "real-rcon",
    game: "hll",
    ...overrides,
  };
}

test("classic HLL cards retain the default game styling", () => {
  const markup = runtime.renderServerStatsCard(
    server({ server_name: "HLL Vietnam escrito en el nombre", game: "hll" }),
  );
  assert.match(markup, /data-game="hll"/);
  assert.doesNotMatch(markup, /server-card--game-hllv/);
});

test("HLLV cards receive the semantic visual variant", () => {
  const markup = runtime.renderServerStatsCard(
    server({ server_name: "Nombre clásico deliberado", game: "hllv" }),
  );
  assert.match(markup, /data-game="hllv"/);
  assert.match(markup, /server-card--game-hllv/);
});

test("unknown games do not accidentally receive the Vietnam variant", () => {
  const markup = runtime.renderServerStatsCard(server({ game: "future-game" }));
  assert.match(markup, /data-game="unknown"/);
  assert.doesNotMatch(markup, /server-card--game-hllv/);
});
