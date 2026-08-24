(() => {
  const MAP_IMAGE_VARIANTS = Object.freeze({
    carentan: Object.freeze(["day", "dusk", "night", "rain"]),
    driel: Object.freeze(["dawn", "day", "night"]),
    elalamein: Object.freeze(["day", "dusk"]),
    elsenbornridge: Object.freeze(["dawn", "day", "dusk", "night"]),
    foy: Object.freeze(["day", "night"]),
    hill400: Object.freeze(["day", "dusk", "night"]),
    hurtgenforest: Object.freeze(["day", "night"]),
    junobeach: Object.freeze(["dawn", "day", "night"]),
    kharkov: Object.freeze(["day", "night"]),
    kursk: Object.freeze(["day", "night"]),
    mortain: Object.freeze(["day", "dusk", "night", "overcast"]),
    omahabeach: Object.freeze(["day", "dusk"]),
    purpleheartlane: Object.freeze(["dawn", "day", "night", "rain"]),
    remagen: Object.freeze(["day", "night"]),
    smolensk: Object.freeze(["day", "dusk", "night"]),
    stalingrad: Object.freeze(["day", "dusk", "night", "overcast"]),
    stmariedumont: Object.freeze(["day", "night", "rain"]),
    stmereeglise: Object.freeze(["dawn", "day", "night"]),
    tobruk: Object.freeze(["dawn", "day", "dusk"]),
    utahbeach: Object.freeze(["day", "night"]),
    unknown: Object.freeze(["day"]),
  });

  const MAP_ALIASES = Object.freeze({
    carentan: Object.freeze(["carentan"]),
    driel: Object.freeze(["driel"]),
    elalamein: Object.freeze(["elalamein", "el alamein"]),
    elsenbornridge: Object.freeze(["elsenbornridge", "elsenborn ridge"]),
    foy: Object.freeze(["foy"]),
    hill400: Object.freeze(["hill400", "hill 400"]),
    hurtgenforest: Object.freeze(["hurtgenforest", "hurtgen forest", "hurtgen"]),
    junobeach: Object.freeze(["junobeach", "juno beach"]),
    kharkov: Object.freeze(["kharkov"]),
    kursk: Object.freeze(["kursk"]),
    mortain: Object.freeze(["mortain"]),
    omahabeach: Object.freeze(["omahabeach", "omaha beach"]),
    purpleheartlane: Object.freeze(["purpleheartlane", "purple heart lane"]),
    remagen: Object.freeze(["remagen"]),
    smolensk: Object.freeze(["smolensk"]),
    stalingrad: Object.freeze(["stalingrad"]),
    stmariedumont: Object.freeze([
      "stmariedumont",
      "st marie du mont",
      "saint marie du mont",
      "sainte marie du mont",
    ]),
    stmereeglise: Object.freeze([
      "stmereeglise",
      "st mere eglise",
      "saint mere eglise",
      "sainte mere eglise",
    ]),
    tobruk: Object.freeze(["tobruk"]),
    utahbeach: Object.freeze(["utahbeach", "utah beach"]),
  });

  // CRCON/hllrcon HLL Vietnam catalog. Dedicated artwork is not bundled yet,
  // so these stable IDs and display aliases intentionally resolve to the local
  // fallback instead of borrowing an unrelated HLL image or hotlinking.
  const HLLV_MAP_ALIASES = Object.freeze({
    wdeva: Object.freeze(["wdeva", "van tuong", "vạn tường"]),
    wdevb: Object.freeze(["wdevb", "quang ngai", "quảng ngãi"]),
    wdevc: Object.freeze(["wdevc", "hue outskirts", "huế outskirts"]),
    wdevd: Object.freeze(["wdevd", "dak to airfield", "đak to airfield", "đăk tô airfield"]),
    wdeve: Object.freeze(["wdeve", "cam ranh port"]),
    wdevf: Object.freeze(["wdevf", "thanh hoa bridge", "thanh hóa bridge"]),
  });

  const ENVIRONMENT_ALIASES = Object.freeze({
    day: Object.freeze(["day"]),
    night: Object.freeze(["night"]),
    dawn: Object.freeze(["dawn"]),
    dusk: Object.freeze(["dusk"]),
    overcast: Object.freeze(["overcast"]),
    rain: Object.freeze(["rain"]),
  });

  const DEFAULT_ENVIRONMENT_PRIORITY = Object.freeze([
    "day",
    "dawn",
    "dusk",
    "overcast",
    "rain",
    "night",
  ]);

  const ORDERED_MAP_MATCHERS = Object.freeze(
    Object.entries(MAP_ALIASES)
      .flatMap(([mapId, aliases]) =>
        aliases.map((alias) => ({
          mapId,
          compactAlias: compactLookup(alias),
        })),
      )
      .sort((left, right) => right.compactAlias.length - left.compactAlias.length),
  );

  const ORDERED_HLLV_MAP_MATCHERS = Object.freeze(
    Object.entries(HLLV_MAP_ALIASES)
      .flatMap(([mapId, aliases]) =>
        aliases.map((alias) => ({
          mapId,
          compactAlias: compactLookup(alias),
        })),
      )
      .sort((left, right) => right.compactAlias.length - left.compactAlias.length),
  );

  function normalizeLookup(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[đĐ]/g, "d")
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, " ")
      .trim();
  }

  function compactLookup(value) {
    return normalizeLookup(value).replace(/\s+/g, "");
  }

  function resolveMapId(candidates, matchers = ORDERED_MAP_MATCHERS) {
    const normalizedCandidates = candidates
      .map((candidate) => compactLookup(candidate))
      .filter(Boolean);
    for (const candidate of normalizedCandidates) {
      for (const matcher of matchers) {
        if (candidate.includes(matcher.compactAlias)) {
          return matcher.mapId;
        }
      }
    }
    return null;
  }

  function resolveEnvironment(candidates) {
    const combined = candidates
      .map((candidate) => normalizeLookup(candidate))
      .filter(Boolean)
      .join(" ");
    if (!combined) {
      return null;
    }
    for (const [environment, aliases] of Object.entries(ENVIRONMENT_ALIASES)) {
      for (const alias of aliases) {
        if (combined.includes(alias)) {
          return environment;
        }
      }
    }
    return null;
  }

  function resolveVariant(mapId, requestedEnvironment) {
    const variants = MAP_IMAGE_VARIANTS[mapId];
    if (!Array.isArray(variants) || variants.length === 0) {
      return null;
    }
    if (requestedEnvironment && variants.includes(requestedEnvironment)) {
      return requestedEnvironment;
    }
    for (const candidate of DEFAULT_ENVIRONMENT_PRIORITY) {
      if (variants.includes(candidate)) {
        return candidate;
      }
    }
    return variants[0] || null;
  }

  function buildUnknownResult(options = {}) {
    const environment = resolveVariant("unknown", "day") || "day";
    return {
      mapId: "unknown",
      requestedMapId: options.requestedMapId || null,
      game: options.game || "unknown",
      environment,
      src: `./assets/img/maps/unknown-${environment}.webp`,
      matched: false,
      fallback: true,
    };
  }

  function resolveMapImageAsset(options = {}) {
    const candidates = Array.isArray(options.candidates) ? options.candidates : [];
    const game = normalizeLookup(options.game);
    const hllvMapId = resolveMapId(candidates, ORDERED_HLLV_MAP_MATCHERS);
    if (game === "hllv" || hllvMapId) {
      return buildUnknownResult({ game: "hllv", requestedMapId: hllvMapId });
    }
    const mapId = resolveMapId(candidates);
    if (!mapId) {
      return buildUnknownResult({ game: game || "unknown" });
    }
    const requestedEnvironment = resolveEnvironment(candidates);
    const environment = resolveVariant(mapId, requestedEnvironment);
    if (!environment) {
      return buildUnknownResult({ game: game || "hll", requestedMapId: mapId });
    }
    return {
      mapId,
      requestedMapId: mapId,
      game: game || "hll",
      environment,
      src: `./assets/img/maps/${mapId}-${environment}.webp`,
      matched: true,
      fallback: false,
    };
  }

  const api = Object.freeze({
    normalizeLookup,
    resolveMapImageAsset,
  });
  globalThis.HLL_MAP_IMAGES = api;
  globalThis.HLL_VIETNAM_MAP_IMAGES = api;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})();
