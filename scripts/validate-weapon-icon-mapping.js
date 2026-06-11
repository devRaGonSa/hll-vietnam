const fs = require("fs");
const path = require("path");
const vm = require("vm");

const repoRoot = path.resolve(__dirname, "..");
const mappingPath = path.join(
  repoRoot,
  "frontend",
  "assets",
  "js",
  "current-match-weapon-icons.js",
);
const assetDir = path.join(
  repoRoot,
  "frontend",
  "assets",
  "img",
  "weapons",
  "black",
);

const source = fs.readFileSync(mappingPath, "utf8");
const context = {
  console: {
    warn() {},
  },
};
vm.createContext(context);
vm.runInContext(source, context, { filename: mappingPath });

const runtime = context.HLL_VIETNAM_CURRENT_MATCH_WEAPON_ICONS;
if (!runtime) {
  throw new Error("Weapon icon runtime was not exposed on globalThis.");
}

const actualFiles = new Set(
  fs.readdirSync(assetDir).filter((fileName) => fileName.endsWith(".svg")),
);
const declaredFiles = new Set(runtime.files);
const forbiddenLegacyTerms = [
  "browing",
  "mosing",
  "panzerchreck",
  "flammenwefer",
  "m1_carabine",
];

const errors = [];
runtime.files.forEach((fileName) => {
  if (!actualFiles.has(fileName)) {
    errors.push(`Declared SVG does not exist: ${fileName}`);
  }
});
actualFiles.forEach((fileName) => {
  if (!declaredFiles.has(fileName)) {
    errors.push(`Local SVG is not declared in runtime list: ${fileName}`);
  }
});
runtime.entries.forEach(([weapon, iconFile]) => {
  if (!actualFiles.has(iconFile)) {
    errors.push(`Mapping points to missing SVG: ${weapon} -> ${iconFile}`);
  }
});
forbiddenLegacyTerms.forEach((term) => {
  if (source.includes(term)) {
    errors.push(`Legacy typo term remains in runtime JS: ${term}`);
  }
});

if (runtime.unknown?.icon && !runtime.unknown.icon.endsWith("precision_strike_black.svg")) {
  errors.push(`Unexpected fallback icon: ${runtime.unknown.icon}`);
}

if (errors.length > 0) {
  errors.forEach((error) => console.error(error));
  process.exit(1);
}

console.log(
  `Weapon icon mapping OK: ${runtime.entries.length} RCON names, ${runtime.files.length} SVG files.`,
);
