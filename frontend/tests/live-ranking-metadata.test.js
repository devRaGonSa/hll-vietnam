"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

function read(relativePath) {
  return fs.readFileSync(path.join(__dirname, "..", relativePath), "utf8");
}

const ranking = read("assets/js/ranking.js");
const stats = read("assets/js/stats.js");
const historical = read("assets/js/historico.js");
const recentHistorical = read("assets/js/historico-recent-live.js");
const home = read("assets/js/main.js");
const statsHtml = read("stats.html");
const styles = read("assets/css/styles.css");

test("global and annual rankings omit generated update metadata", () => {
  assert.doesNotMatch(ranking, /label:\s*"Actualizado"/);
  assert.doesNotMatch(ranking, /source\.generated_at/);
  assert.doesNotMatch(stats, /<p>Actualizado<\/p>/);
  assert.doesNotMatch(stats, /data\.generated_at/);

  assert.match(ranking, /label:\s*"Periodo"/);
  assert.match(stats, /<p>Partidas base<\/p>/);
  assert.match(stats, /const year = safeInt\(data\.year/);
  assert.match(stats, /"current-week": "Semana actual"/);
  assert.match(statsHtml, /Temporada/);
  assert.match(styles, /\.stats-annual-meta\s*\{[\s\S]*?repeat\(auto-fit,/);
  assert.match(styles, /\.ranking-meta\s*\{[\s\S]*?repeat\(auto-fit,/);
});

test("historical live lists hide update metadata but retain domain dates", () => {
  assert.doesNotMatch(historical, /Actualizado:/);
  assert.doesNotMatch(historical, /buildSnapshotMetaText/);
  assert.doesNotMatch(recentHistorical, /Actualizado(?: recientemente|:)/);

  assert.match(historical, /Semana activa/);
  assert.match(historical, /payload\?\.window_start/);
  assert.match(historical, /payload\?\.window_end/);
  assert.match(historical, /formatTimestamp\(item\.closed_at\)/);
  assert.match(recentHistorical, /item\?\.closed_at \|\| item\?\.ended_at \|\| item\?\.started_at/);
  assert.match(recentHistorical, /<p class="historical-match-meta__label">Cierre<\/p>/);
});

test("operational home freshness and request topology stay unchanged", () => {
  assert.match(home, /`Actualizado \$\{timestampLabel\}`/);
  assert.equal(
    home.split("\n").filter((line) => line.includes("fetchJson(") && line.includes("/api/servers")).length,
    1,
  );

  assert.match(historical, /api\/historical\/snapshots\/leaderboard/);
  assert.match(ranking, /api\/ranking/);
  assert.match(stats, /api\/stats\/rankings\/annual/);
});
