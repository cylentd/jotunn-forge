// Writes forge/scores.js: DMG, BOSS, CC and DEF lenses for every build route the attack model can score.
// Usage: node scripts/score-builds.mjs
import { writeFileSync } from "node:fs";
import { join } from "node:path";
import { CARDS, IGNORED, GUESSES, evaluate, ranksOf } from "./attack-model.mjs";
import { BUILDS, ROOT, virtueLines } from "./page-data.mjs";

// Builds whose damage is mostly basic attacks. Others need an active-skill model before they can be scored.
const MODELLED = new Set(["hammer"]);

// Fixed tier cutoffs, highest first. A tier never moves when another build is added.
const LENSES = [
  { key: "dmg", label: "DMG", unit: "x", max: 3.5, cut: [2.8, 2.4, 2.0, 1.6, 1.2], what: "damage to a pack, vs the same virtues with no passives" },
  { key: "boss", label: "BOSS", unit: "x", max: 3.5, cut: [2.8, 2.4, 2.0, 1.6, 1.2], what: "damage to one elite, stun-immune" },
  { key: "cc", label: "CC", unit: "%", max: 1, cut: [0.7, 0.55, 0.4, 0.25, 0.1], what: "share of time a hit enemy is stunned, frozen or feared by Attack procs" },
  { key: "def", label: "DEF", unit: "x", max: 5, cut: [5, 3.5, 2.5, 1.8, 1.3], what: "effective health from health and damage reduction, vs base" },
];
const TIERS = ["S", "A", "B", "C", "D", "F"];
const tier = (v, cut) => TIERS[cut.findIndex(c => v >= c) === -1 ? 5 : cut.findIndex(c => v >= c)];

const out = {};
for (const b of BUILDS.filter(b => MODELLED.has(b.id))) {
  const vl = virtueLines(b);
  out[b.id] = b.routes.map(r => {
    const ranks = ranksOf(r.passives);
    const unknown = Object.keys(ranks).filter(n => !CARDS[n] && !IGNORED.has(n));
    if (unknown.length) console.warn(`${b.id} · ${r.gods.join("/")}: not modelled, scored as zero: ${unknown.join(", ")}`);
    const runs = GUESSES.map(P => {
      const e = evaluate(ranks, vl, P), base = evaluate({}, vl, P);
      return { dmg: e.pack / base.pack, boss: e.boss / base.boss, cc: e.cc, def: e.ehp };
    });
    const lens = { sig: JSON.stringify([r.gods, r.passives]) }; // the page hides bars whose route has changed since
    for (const L of LENSES) {
      const vals = runs.map(x => x[L.key]), mid = vals[1];
      lens[L.key] = { v: +mid.toFixed(3), lo: +Math.min(...vals).toFixed(3), hi: +Math.max(...vals).toFixed(3), tier: tier(mid, L.cut) };
    }
    console.log(`${b.id} · ${r.gods.join(" · ")}: ` + LENSES.map(L => `${L.label} ${lens[L.key].tier} ${lens[L.key].v}`).join("  "));
    return lens;
  });
}

const meta = { lenses: LENSES.map(({ key, label, unit, max, what }) => ({ key, label, unit, max, what })),
  guesses: GUESSES.map(g => `${g.name}: ${g.D} dmg, ${g.crit}% crit, ${g.aps} attacks/s, ${g.hp} HP`) };
writeFileSync(join(ROOT, "forge/scores.js"), "window.SCORES = " + JSON.stringify({ meta, builds: out }) + ";\n");
