const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");

const root = path.resolve(__dirname, "../..");
const html = fs.readFileSync(path.join(root, "frontend/bots.html"), "utf8");
const audit = fs.readFileSync(path.join(root, "docs/PUBLIC_BOTS_AUDIT.md"), "utf8");
const css = fs.readFileSync(path.join(root, "frontend/assets/css/styles.css"), "utf8");
const staticServer = fs.readFileSync(path.join(root, "frontend/static_server.py"), "utf8");

const publishedCommandGroups = [...html.matchAll(/data-chat-command="([^"]+)"/g)].map((match) =>
  match[1].split(","),
);

test("bots guide replaces the placeholder and retains public navigation", () => {
  assert.doesNotMatch(html, /Guía en preparación|Próximamente encontrarás aquí/);
  assert.match(html, /Comandos en chat/);
  assert.match(html, /Automatizaciones del servidor/);
  assert.match(html, /Discord y soporte/);
  assert.match(html, /public-nav__group is-active[\s\S]*Comunidad/);
  assert.match(html, /public-nav__menu-link is-current" href="\.\/bots\.html" aria-current="page"/);
  assert.match(html, /src="\.\/assets\/js\/public-nav\.js\?v=321"/);
  assert.match(css, /\.command-grid/);
});

test("command cards are direct and contain only the editorial selection", () => {
  const commands = publishedCommandGroups.flat();
  assert.deepEqual(commands, [
    "!help",
    "!rewards",
    "!me",
    "!wkm",
    "!top",
    "!vip",
    "!redeploy",
    "!r",
    "!votemap",
    "!vm",
    "!nodos",
  ]);

  for (const removed of ["!discord", "!push", "!switch", "@switch", "@help"]) {
    assert.doesNotMatch(html, new RegExp(`<code>${removed.replace("!", "\\!")}</code>`));
  }
  assert.doesNotMatch(html, /<dl>|<dt>Quién<\/dt>|<dt>Dónde<\/dt>/);
  assert.doesNotMatch(html, /no distingue mayúsculas|respeta sus minúsculas/i);
  assert.match(html, /!redeploy[\s\S]*también <code>!r<\/code>[\s\S]*10 segundos/);
  assert.match(html, /!votemap[\s\S]*también <code>!vm<\/code>/);
});

test("Rewards is verified and Guide is not invented", () => {
  assert.match(html, /data-chat-command="!rewards"/);
  assert.match(html, /objetivos y recompensas VIP semanales activos/);
  assert.match(html, /Disponible en HLL #1 y HLL #2/);
  assert.match(audit, /\| `!rewards` \| ACTIVE \| Sí \|/);
  assert.match(audit, /Comando independiente de Guía \| NOT_VERIFIED/);
  assert.doesNotMatch(html, /data-chat-command="!(?:guia|guía|guide|retos|objetivos)"/i);
});

test("Discord status is removed while support and moderation remain", () => {
  assert.doesNotMatch(html, /Estado del servidor|Consultas desde Discord|-server[123]/);
  assert.match(html, /Tickets[\s\S]*Soporte guiado/);
  assert.match(html, /Convivencia[\s\S]*Moderación asistida/);
  assert.match(audit, /Consultas de estado en Discord \| ACTIVE \| SÍ \| NO \| Decisión editorial/);
});

test("audit preserves active commands and records editorial exclusions", () => {
  for (const command of ["!discord", "!push", "!switch"]) {
    assert.ok(audit.includes(`| \`${command}\``), `${command} must remain documented`);
    const editorialRow = audit
      .split("\n")
      .find((line) => line.startsWith(`| \`${command}\``));
    assert.match(editorialRow, /\| ACTIVE \| SÍ \| NO \|/);
  }
  assert.match(audit, /VISIBLE_EN_GUIA/);
});

test("every published game command is ACTIVE and technically publicable in the audit", () => {
  assert.ok(publishedCommandGroups.length > 0);
  for (const commands of publishedCommandGroups) {
    for (const command of commands) {
      const escaped = command.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      assert.match(
        audit,
        new RegExp(`\\|[^\\n]*\\\`${escaped}\\\`[^\\n]*\\| ACTIVE \\| Sí \\|`),
        `${command} must be ACTIVE/public in the audit`,
      );
    }
  }
});

test("dry-run, inactive and operations-only mechanisms are not advertised as active", () => {
  for (const omitted of [
    "Commander AFK",
    "control de nombres",
    "AutoBroadcast nativo",
    "Watch Kill Rate",
    "tanque en solitario",
    "bot de reinicio",
  ]) {
    assert.doesNotMatch(html, new RegExp(omitted, "i"));
  }
  assert.doesNotMatch(html, /DRY_RUN|OPERATIONS_ONLY|INACTIVE/);
  assert.match(audit, /\| Commander AFK \| DRY_RUN /);
  assert.match(audit, /\| Control de nombres \| DRY_RUN /);
});

test("public copy contains no operational vocabulary or secret-like additions", () => {
  for (const forbidden of [
    /comunidadhll-[a-z0-9@.-]+\.service/i,
    /\/opt\//i,
    /\/etc\//i,
    /\bdocker\b/i,
    /\bsystemctl\b/i,
    /\bRedis\b/i,
    /\bPostgreSQL\b/i,
    /BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY/i,
    /(?:api[_-]?key|password|passwd|secret|bearer|webhook)["']?\s*[:=]/i,
    /https?:\/\/[^\s"']+:[^\s"']+@/i,
  ]) {
    assert.doesNotMatch(html, forbidden);
  }
});

test("normativa, VIP, no-store and HLLV semantics remain intact", () => {
  assert.match(html, /href="\.\/normativa\.html"/);
  assert.match(html, /href="\.\/vip\.html"/);
  assert.match(staticServer, /no-store, no-cache, must-revalidate, max-age=0/);

  const mainJs = fs.readFileSync(path.join(root, "frontend/assets/js/main.js"), "utf8");
  assert.match(mainJs, /serverGame === "hllv" \? "server-card--game-hllv"/);
  assert.match(mainJs, /data-game="\$\{escapeHtml\(serverGame\)\}"/);
  assert.match(css, /\.server-card--game-hllv/);
});
