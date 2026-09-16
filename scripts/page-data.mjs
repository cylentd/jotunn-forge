// Reads the BUILDS and VIRTUES tables out of forge/index.html, so scripts never keep their own copy.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

export const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const html = readFileSync(join(ROOT, "forge/index.html"), "utf8");

function table(name, open, close) {
  const m = html.match(new RegExp(`const ${name}=(\\${open}[\\s\\S]*?\\n\\${close});`));
  if (!m) throw new Error(`forge/index.html: const ${name} not found`);
  return Function(`"use strict";return (${m[1]})`)();
}

export const BUILDS = table("BUILDS", "[", "]");
const VIRTUES = table("VIRTUES", "{", "}");
export const virtueLines = build => (build.virtues || []).map(v => {
  if (!VIRTUES[v]) throw new Error(`build ${build.id}: unknown virtue ${v}`);
  return VIRTUES[v][1];
});
