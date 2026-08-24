const assert = require("node:assert/strict");
const test = require("node:test");

const { normalizeLookup, resolveMapImageAsset } = require("../assets/js/map-image-resolver.js");

test("classic map aliases and environments resolve to verified local CRCON assets", () => {
  assert.deepEqual(
    resolveMapImageAsset({ game: "hll", candidates: ["St. Mère Église Night"] }),
    {
      mapId: "stmereeglise",
      requestedMapId: "stmereeglise",
      game: "hll",
      environment: "night",
      src: "./assets/img/maps/stmereeglise-night.webp",
      matched: true,
      fallback: false,
    },
  );
  assert.equal(normalizeLookup("Đăk Tô Airfield"), "dak to airfield");
});

test("all six CRCON HLLV IDs and display aliases resolve to the local fallback", () => {
  const cases = [
    ["wdeva_warfare_day", "wdeva"],
    ["Quảng Ngãi", "wdevb"],
    ["Huế Outskirts", "wdevc"],
    ["Đăk Tô Airfield", "wdevd"],
    ["Cam Ranh Port", "wdeve"],
    ["Thanh Hóa Bridge", "wdevf"],
  ];
  for (const [candidate, mapId] of cases) {
    const result = resolveMapImageAsset({ game: "hllv", candidates: [candidate] });
    assert.equal(result.requestedMapId, mapId);
    assert.equal(result.game, "hllv");
    assert.equal(result.src, "./assets/img/maps/unknown-day.webp");
    assert.equal(result.matched, false);
    assert.equal(result.fallback, true);
  }
});

test("unknown maps never borrow an unrelated image", () => {
  const result = resolveMapImageAsset({ game: "hll", candidates: ["Future Map"] });
  assert.equal(result.mapId, "unknown");
  assert.equal(result.src, "./assets/img/maps/unknown-day.webp");
  assert.equal(result.matched, false);
  assert.equal(result.fallback, true);
});
