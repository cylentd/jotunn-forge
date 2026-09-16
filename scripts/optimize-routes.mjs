// Prints the best passive picks for a god draw: every rank allocation inside the pick budget, best pack damage,
// optionally with a minimum CC uptime.
// Usage: node scripts/optimize-routes.mjs <build id> "<God>,<God>,<God>" [ccFloor=0.4] [budget=14]
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { CARDS, GUESSES, evaluate } from "./attack-model.mjs";
import { BUILDS, ROOT, virtueLines } from "./page-data.mjs";

const [id = "hammer", godArg = "Nidhogg,Njord,Thor", floorArg = "0.4", budgetArg = "14"] = process.argv.slice(2);
const gods = godArg.split(",").map(s => s.trim()), floor = +floorArg, budget = +budgetArg;
const build = BUILDS.find(b => b.id === id);
const vl = virtueLines(build);
const FIXED = 3; // Mithril Hammer ×3

const src = readFileSync(join(ROOT, "forge/skills.js"), "utf8");
const godOf = Object.fromEntries(JSON.parse(src.slice(src.indexOf("["), src.lastIndexOf("]") + 1)).map(s => [s.name.replace(/’/g, "'"), s.god]));
const pool = Object.keys(CARDS).filter(n => godOf[n] === "Warden" || gods.includes(godOf[n]));

for (const P of GUESSES) {
  const base = evaluate({}, vl, P);
  let top = null; const ranks = {};
  (function rec(i, used) {
    if (i === pool.length) {
      const e = evaluate(ranks, vl, P);
      if (e.cc >= floor && (!top || e.pack > top.e.pack)) top = { e, ranks: { ...ranks } };
      return;
    }
    for (let k = 0; k <= CARDS[pool[i]][0] && used + k <= budget - FIXED; k++) { ranks[pool[i]] = k; rec(i + 1, used + k); }
    ranks[pool[i]] = 0;
  })(0, 0);
  if (!top) { console.log(`${P.name}: no allocation reaches ${floor * 100}% CC`); continue; }
  const picks = Object.entries(top.ranks).filter(x => x[1]).map(([n, k]) => k > 1 ? `${n}×${k}` : n).join(", ");
  console.log(`${P.name}: ${(top.e.pack / base.pack).toFixed(2)}x pack  ${(top.e.boss / base.boss).toFixed(2)}x boss  CC ${(top.e.cc * 100).toFixed(0)}% | ${picks}`);
}
