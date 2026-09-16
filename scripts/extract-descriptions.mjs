// Writes forge/descriptions.js: in-game skill name -> in-game description, read from the game's language_eng.xml.
// Keyed by the game's spelling; the page resolves skills.js spellings through its ALIAS table.
// Usage: node scripts/extract-descriptions.mjs [path/to/language_eng.xml]
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const LANG = process.argv[2] ||
  "F:/SteamLibrary/steamapps/common/Jotunnslayer Hordes of Hel/Jotunnslayer_Data/StreamingAssets/language/language_eng.xml";
const root = join(dirname(fileURLToPath(import.meta.url)), "..");

const decode = s => s
  .replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, '"').replace(/&apos;/g, "'")
  .replace(/&#10;/g, " ").replace(/&amp;/g, "&")
  .replace(/<\/?color[^>]*>/g, "").replace(/\s+/g, " ").trim();
const norm = s => s.replace(/’/g, "'");

const xml = readFileSync(LANG, "utf8");
const keys = [...xml.matchAll(/<Key id="(\d+)" name="([^"]+)" text="([^"]*)"/g)].map(m => ({ id: +m[1], name: m[2], text: decode(m[3]) }));
const byName = new Map(keys.map(k => [k.name, k]));
const byId = new Map(keys.map(k => [k.id, k]));

// A skill name key is Skills_* or <God>N_Act_*/<God>N_Pas_*. Its description is <key>_Des, <key>_Desc,
// or else the key at id + 1 when that key is a description.
const isSkillKey = n => /^Skills_|^[A-Za-z]+N_(Act|Pas|Pass)_/.test(n) && !/_Desc?$|_L_|_EL_/.test(n);
const out = {};
for (const k of keys) {
  if (!isSkillKey(k.name) || !k.text) continue;
  const next = byId.get(k.id + 1);
  const des = byName.get(k.name + "_Des") || byName.get(k.name + "_Desc") ||
    (next && next.name.startsWith(k.name) && /_Desc?$/.test(next.name) ? next : null);
  if (des && !(norm(k.text) in out)) out[norm(k.text)] = des.text;
}

writeFileSync(join(root, "forge/descriptions.js"), "window.DESCS = " + JSON.stringify(out) + ";\n");
console.log(`${Object.keys(out).length} descriptions written`);

const src = readFileSync(join(root, "forge/skills.js"), "utf8");
const missing = JSON.parse(src.slice(src.indexOf("["), src.lastIndexOf("]") + 1)).map(s => norm(s.name)).filter(n => !(n in out));
if (missing.length) console.log("skills.js names not in the game text (the page's ALIAS must cover them): " + missing.join(", "));
