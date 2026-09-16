// Basic-attack model for Warden builds: turns a set of passive ranks and virtues into damage, CC and defence numbers.
// Card numbers come from forge/skills.js; triggers from the game's descriptions (only "on each Attack" cards count).
// Status damage from language_eng.xml Statuses_*: Bleed 8/s, Shock 6 per 0.7 s.
// Warden base stats are not in the game data, so every call takes a guess P = { D, crit, aps, hp }.
// Assumed stacking: bonuses on the same stat add, different stats multiply (unverified in data).

export const GUESSES = [
  { name: "low", D: 10, crit: 5, aps: 1, hp: 200 },
  { name: "mid", D: 20, crit: 5, aps: 1, hp: 300 },
  { name: "high", D: 40, crit: 10, aps: 1.5, hp: 400 },
];
const PACK_HITS = 8;   // enemies hit per attack in a pack: 4 hammers plus ricochet
const STAND = 0.5;     // share of time standing still
const REGEN = 3;       // HP/s, for Magic Fangs
const BT_DPS = (8 + 6 / 0.7) / 2; // Blood & Thunder applies Bleed or Shock: average damage per second
const DR_CAP = 90;

// name -> [max ranks, effect(stats, rank)]
export const CARDS = {
  "Blunt Force":         [1, s => s.stun.push(0.07)],
  "Pulverize":           [1, s => { s.pulverize = 0.25 }],
  "Blood & Thunder":     [1, s => { s.bt = 0.45 }],
  "Explosive Nature":    [1, s => { s.en = 1 }],
  "Blows of Jarngreipr": [1, s => s.stun.push(0.15)], // rank 2 lists no new number
  "Devastating Hit":     [1, s => { s.cc += 10; s.cd += 30 }],
  "No Remorse":          [3, (s, k) => { s.all += 8 * k }],
  "Wings of Fury":       [3, (s, k) => { s.ms += 8 * k }],
  "Sheer Terror":        [1, s => { s.fear = 0.08 }],
  "Sea Legs":            [1, s => { s.seaLegs = 2 }],
  "Ebb & Swell":         [1, s => { s.ms += 10; s.regen += 1.5 }], // shifts between 0-20% speed and 0-3 regen
  "Salted Wounds":       [1, s => { s.salted = 25 }],
  "Teiwaz":              [3, (s, k) => { s.atk += 15 * k }],
  "Raido":               [3, (s, k) => { s.as += 8 * k }],
  "Perth":               [3, (s, k) => { s.cc += 5 * k }],
  "Sleipnir's Speed":    [3, (s, k) => { s.as += 10 * k }],
  "Worthy Opponent":     [1, s => { s.all += 5; s.elite += 20 }],
  "Overlord":            [2, (s, k) => { s.overlord = 3 * k }],
  "Swiftness":           [2, (s, k) => { s.as += 7 * k; s.ms += 7 * k }],
  "Magic Fangs":         [3, (s, k) => { s.fangs = 2 * k }],
  "Shapeshifter":        [2, (s, k) => { s.shape = 0.25 * k }],
  "Gambler's Luck":      [1, s => { s.cd += 30 }],
  "Wintergrasp":         [1, s => { s.freeze = 0.12 }],
  "Last Stand":          [3, (s, k) => { s.cc += 5 * k * STAND }],
  // defence
  "Frost Armor":         [3, (s, k) => { s.dr += 8 * k }],
  "Rock Solid":          [2, (s, k) => { s.hp += 80 * k }],
  "Goat Feast":          [2, (s, k) => { s.hp += 100 * k }],
  "Older than Time":     [2, (s, k) => { s.hp += 75 * k }],
  "Berkana":             [3, (s, k) => { s.hp += [0, 100, 160, 220][k] }],
  "Cure Wounds":         [2, (s, k) => { s.regen += k }],
  "Jotunn's Blood":      [3, (s, k) => { s.regen += 2 * k }],
  "Vigor":               [1, s => { s.regen += 2 }],
};
// Cards the model knows but deliberately scores as zero (fixed on every route, or no Attack trigger).
export const IGNORED = new Set(["Mithril Hammer"]);

// Virtue stat lines on the page, e.g. "+20% attack damage", read into the same stats.
const VIRTUE_LINES = [
  [/^\+(\d+)% attack damage$/, (s, n) => { s.atk += n }],
  [/^\+(\d+)% all damage$/, (s, n) => { s.all += n }],
  [/^\+(\d+)% attack speed$/, (s, n) => { s.as += n }],
  [/^\+(\d+)% movement speed$/, (s, n) => { s.ms += n }],
  [/^\+(\d+)% crit damage$/, (s, n) => { s.cd += n }],
  [/^\+(\d+)% crit chance$/, (s, n) => { s.cc += n }],
  [/^[−-](\d+)% damage taken$/, (s, n) => { s.dr += n }],
  [/^\+(\d+) max health$/, (s, n) => { s.hp += n }],
  [/^\+(\d+) HP\/s$/, (s, n) => { s.regen += n }],
];

const uptime = (p, aps, dur) => 1 - Math.pow(1 - p, aps * dur);

export function evaluate(ranks, virtueLines, P) {
  const s = { atk: 0, all: 0, as: 0, ms: 0, cc: P.crit, cd: 50, elite: 0, stun: [], freeze: 0, fear: 0, pulverize: 0, bt: 0, en: 0,
    seaLegs: 0, salted: 0, overlord: 0, fangs: 0, shape: 0, dr: 0, hp: 0, regen: 0 };
  for (const line of virtueLines) for (const [re, f] of VIRTUE_LINES) { const m = line.match(re); if (m) f(s, +m[1]) }
  for (const n in ranks) if (ranks[n] && CARDS[n]) CARDS[n][1](s, ranks[n]);
  const hpTotal = P.hp + s.hp;
  const aps = P.aps * (1 + (s.as + s.shape * s.ms) / 100);
  const cc = Math.min(s.cc, 100) / 100;
  const hit = P.D * (1 + (s.atk + s.seaLegs * s.ms + s.overlord * hpTotal / 100 + s.fangs * (REGEN + s.regen)) / 100) * (1 + cc * s.cd / 100);
  const stunUp = uptime(1 - s.stun.reduce((q, p) => q * (1 - p), 1), aps, 2);
  const ccUp = 1 - (1 - stunUp) * (1 - uptime(s.freeze, aps, 2)) * (1 - uptime(s.fear, aps, 2));
  const allM = 1 + s.all / 100, salt = 1 + s.salted / 200; // Salted Wounds: half of hits land under half health
  const btDps = s.bt ? uptime(cc * s.bt, aps, 4) * BT_DPS : 0;
  const enPack = s.en ? Math.min(aps * PACK_HITS * 0.15, 1 / 0.3) * 25 / PACK_HITS : 0; // 5 dmg × 5 targets, 0.3 s cooldown
  const enBoss = s.en ? Math.min(aps * 0.15, 1 / 0.3) * 5 : 0;
  return {
    pack: (aps * hit * salt + btDps + enPack) * allM * (1 + s.pulverize * stunUp),
    boss: (aps * hit * salt + btDps + enBoss) * (allM + s.elite / 100), // bosses assumed stun-immune
    cc: ccUp,
    ehp: hpTotal / P.hp / (1 - Math.min(s.dr, DR_CAP) / 100), // effective health vs base health, no damage reduction
  };
}

// Picks list ([name, rank, gate]) -> { name: highest rank }
export function ranksOf(picks) {
  const r = {};
  for (const [n, k] of picks) r[n] = Math.max(r[n] || 0, k || 1);
  return r;
}
