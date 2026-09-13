"""Live pick coach for Jotunnslayer: Hordes of Hel (Warden).

Tails the game's own analytics log while you play and prints what to take next.
Read-only: it never writes to the game, the save, or the log.

    python coach.py              watch live (starts at the end of the current log)
    python coach.py --replay     replay the newest log from the start, then watch
    python coach.py --replay --no-watch     replay only, then exit
"""

import argparse
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

ANALYTICS_DIR = Path(os.environ["USERPROFILE"]) / "AppData/LocalLow/Games Farm/Jotunnslayer/analytics"
LANG_XML = Path(
    r"F:\SteamLibrary\steamapps\common\Jotunnslayer Hordes of Hel"
    r"\Jotunnslayer_Data\StreamingAssets\language\language_eng.xml"
)
POLL_SECONDS = 1.0

# ---------------------------------------------------------------- build rules
# Priority order. kind: class_active | god_active | passive.
# Actives stay on the list until rank 3; then evolve when a chest offers it.
PRIORITY = [
    ("Iron Fist", "class_active"),
    ("Magnetized Anvil", "class_active"),
    ("Mjolnir", "god_active"),
    ("Ball Lightning", "god_active"),
    ("Arctic Arrow", "god_active"),
    ("Pulverize", "passive"),
    ("Resonance", "passive"),
    ("Might of Megingjord", "passive"),
    ("Overwhelming Potential", "passive"),
    ("King of Gods", "passive"),
    ("Guidance", "passive"),
    ("Torrents", "passive"),
    ("Blunt Force", "passive"),
    ("Law & Order", "passive"),
    ("Mannaz", "passive"),
    ("Ansuz", "passive"),
    ("Radiant Echo", "passive"),
    ("Inguz", "passive"),
    ("Frost Armor", "passive"),
    ("Rock Solid", "passive"),
]

# Acceptable stand-ins when the priority pick is not on offer.
ALSO_GOOD = {
    "Thunderstorm": "10 strikes x 20 dmg, CD 6 - fine third god slot",
    "Runic Boulder": "30 dmg, CD 3, rolls through a line",
    "Parasite": "12 x 10 dmg on CD 2.25",
    "Crystal Comet": "35 dmg, 4 m, 75% slow",
    "Valkyrie Descent": "35 dmg, CD 2.5, 100% slow",
    "Concentration": "-20% cooldowns while standing still",
    "Worthy Opponent": "+5% dmg, +20% vs elites",
    "Devastating Hit": "+10% crit, +30% crit damage",
    "Rune Mastery": "+5% double cast, heals 7 per proc",
    "Berkana": "+220 max HP",
    "Teiwaz": "+45% attack damage",
    "Goat Feast": "+200 max HP",
    "Fish Dinner": "heals 60 on every level up",
    "Crashing Wave": "100% stun on weapon skill",
    "Barricade": "+20% block (Shieldbearer builds)",
    "Deafening Impact": "block -> 30% stun (Shieldbearer builds)",
    "Punish": "block -> 13 dmg + knockback (Shieldbearer builds)",
    "Mithril Hammer": "attack splits into 4 projectiles",
}

SKIP = {
    "Kraken": "8 dmg x 4 on CD 8 - worst active in the file",
    "Frost Ring": "10 dmg on CD 4.5 - crowd control, not damage",
    "Huginn & Munnin": "14 dmg in a fixed 2.5 m circle",
    "Einherjar": "14 dmg - low output for a god slot",
    "Gungnir": "30 dmg on CD 2.5, single line",
    "Leviathan": "30 dmg on CD 4, small radius",
    "Vortex": "35 dmg on CD 8",
    "Water Bubble": "utility, no real damage",
    "Hammertime": "10 dmg - you only get 2 class actives",
    "Seismic Shock": "32 dmg on CD 4 - Anvil beats it",
    "Shieldwall": "21 x 4 on CD 5 - Anvil beats it",
    "Lightning Strike": "23 dmg on CD 3.25, fixed directions",
    "Sentinel": "30 dmg, 3 s uptime on CD 9",
    "Snow Fight": "15 dmg chip",
    "Cold Feet": "slow only",
    "Wintergrasp": "12% freeze on attack",
    "Fimbulwinter": "-15% enemy move speed",
    "Explosive Nature": "5 dmg proc",
    "Static Charge": "8 dmg when hit",
    "Discharge": "dash proc, 18 dmg",
    "Blows of Jarngreipr": "knockback, no damage",
    "Divine Wave": "10 dmg on CD 3.5",
    "Gambanteinn": "20 x 4 on CD 5",
    "Golden Discs": "23 x 3 on CD 4",
    "Clairvoyance": "+17% XP - economy, not power",
    "Brisingamen": "gold - economy, not power",
    "Gold is Life": "gold - economy, not power",
    "Bottomless Wealth": "gold - economy, not power",
    "Godlike Appeal": "pickup range",
    "Gold Hunter": "gold - economy, not power",
    "Retribution": "30% reflect - situational",
    "Jera": "pickup range rune",
    "Gebo": "XP rune",
    "Kaunaz": "reroll rune - farming only",
    "Ripped Lottery": "gold gamble",
}

CLASS_ACTIVE_CAP = 2
GOD_ACTIVE_CAP = 3
RANK_TARGET = 3

# Printed when a choice screen opens, and by --cheat.
GOD_ORDER = "Thor > Odin > Freya > Skadi > Njord > Loki > Nidhogg > Nerthus"

BANISH_FIRST = "Kraken, Frost Ring, Hammertime, Seismic Shock, Einherjar"

CHEAT = """
GOD SCREEN (3 options)     {gods}
  already have 3 god actives -> pick the god with passives you still want

CLASS SCREEN               Magnetized Anvil, Iron Fist. Shieldwall only if no Iron Fist.
                           never: Hammertime, Seismic Shock, a 3rd active

TIER 1 PASSIVES            Guidance, Mannaz, Ansuz, Overwhelming Potential,
                           Might of Megingjord, King of Gods, Pulverize (L8),
                           Law & Order, Torrents
TIER 2                     Inguz, Teiwaz, Resonance (L15), Radiant Echo,
                           Devastating Hit (L8), Concentration (L8), Frost Armor,
                           Berkana, Goat Feast, No Remorse, Gambler's Luck
TIER 3 (filler)            Blunt Force, Mithril Hammer, Rock Solid, Fish Dinner,
                           Worthy Opponent, Rune Mastery, Swiftness, Vigor
NEVER                      economy passives, All In, Retribution, Blows of Jarngreipr,
                           Static Charge, Explosive Nature, Jera, Gebo, Kaunaz

REROLL                     screen has nothing in tier 1-2
BANISH  (permanent)        {banish}
SEAL    (100% next time)   your held active's next rank, when you can't take it yet
"""


def cheat_sheet():
    return CHEAT.format(gods=GOD_ORDER, banish=BANISH_FIRST)

# Hero level a pick becomes available, from requiredLevel in prefabHierarchy_skills.json.
ACTIVE_GATE = {1: 1, 2: 6, 3: 12, 4: 18}      # rank -> hero level; rank 4 is the evolve
PASSIVE_GATE = {1: 1, 2: 8, 3: 15}
PASSIVE_GATE_L1 = {                            # passives that don't start at level 1
    "Pulverize": 8,
    "Resonance": 15,
    "Earthquake": 8,
    "Devastating Hit": 8,
    "Concentration": 8,
    "Self-sacrifice": 15,
}


def gate_for(name, kind, rank):
    if kind.endswith("active"):
        return ACTIVE_GATE.get(rank, 1)
    if rank == 1:
        return PASSIVE_GATE_L1.get(name, 1)
    return PASSIVE_GATE.get(rank, 1)

# ---------------------------------------------------------------- terminal


class Ink:
    def __init__(self, enabled):
        self.on = enabled

    def __call__(self, code, text):
        return f"\033[{code}m{text}\033[0m" if self.on else text

    def take(self, t):
        return self("32;1", t)

    def skip(self, t):
        return self("31;1", t)

    def warn(self, t):
        return self("33", t)

    def dim(self, t):
        return self("90", t)

    def head(self, t):
        return self("36;1", t)

    def name(self, t):
        return self("1", t)


def enable_vt():
    if os.name != "nt":
        return True
    try:
        import ctypes

        k = ctypes.windll.kernel32
        h = k.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if not k.GetConsoleMode(h, ctypes.byref(mode)):
            return False
        return bool(k.SetConsoleMode(h, mode.value | 0x0004))
    except Exception:
        return False


# ---------------------------------------------------------------- loc names


def load_names(path):
    """madloc id -> display text, from the game's English string table."""
    if not path.exists():
        return {}
    names = {}
    for key in ET.parse(path).getroot().iter("Key"):
        kid, text = key.get("id"), key.get("text")
        if kid and text:
            names[kid] = text
    return names


# ------------------------------------------------------------ log streaming


def newest_log(directory):
    logs = list(directory.glob("gameplay_analytics_*.json"))
    return max(logs, key=lambda p: p.stat().st_mtime) if logs else None


class EventStream:
    """Yields event dicts as the game appends them to its JSON log."""

    HEAD = re.compile(r"^\s*\{\s*\"Events\"\s*:\s*\[")

    def __init__(self, path, from_start):
        self.path = path
        self.buf = ""
        self.head_seen = False
        self.offset = 0 if from_start else path.stat().st_size
        if not from_start:
            self.head_seen = True

    def poll(self):
        size = self.path.stat().st_size
        if size < self.offset:  # file rewritten
            self.offset, self.buf, self.head_seen = 0, "", False
        if size == self.offset:
            return []
        with self.path.open("r", encoding="utf-8", errors="replace") as fh:
            fh.seek(self.offset)
            chunk = fh.read()
        self.offset = size
        self.buf += chunk
        return list(self._drain())

    def _drain(self):
        if not self.head_seen:
            m = self.HEAD.search(self.buf)
            if not m:
                return
            self.buf = self.buf[m.end():]
            self.head_seen = True
        while True:
            start = self.buf.find("{")
            if start < 0:
                self.buf = ""
                return
            end = self._match(start)
            if end is None:
                self.buf = self.buf[start:]
                return
            blob = self.buf[start:end]
            self.buf = self.buf[end:]
            try:
                yield json.loads(blob)
            except json.JSONDecodeError:
                continue

    def _match(self, start):
        depth, in_str, esc = 0, False, False
        for i in range(start, len(self.buf)):
            c = self.buf[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            elif c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return i + 1
        return None


# ---------------------------------------------------------------- run state


class Run:
    def __init__(self, ink, names):
        self.ink = ink
        self.names = names
        self.level = 1
        self.ranks = {}          # display name -> highest rank seen
        self.kinds = {}          # display name -> kind
        self.loadout_count = 0
        self.hero = "?"
        self.last_next = None

    # -- naming -------------------------------------------------------
    def label(self, event):
        key = event.get("Skill Name") or ""
        madloc = str(event.get("Madloc ID") or "")
        name = self.names.get(madloc) or key
        rank = None
        m = re.search(r"_L(\d+)$", key)
        if m:
            rank = int(m.group(1))
        return key, name, rank

    @staticmethod
    def kind_of(key):
        if "_subclass" in key:
            return "subclass"
        if "_ultimate" in key or "_weapon" in key:
            return "weapon"
        if "_active" in key:
            return "class_active" if key.startswith("warden") else "god_active"
        if "_passive" in key or "_pas_" in key:
            return "passive"
        if key.startswith("trinket"):
            return "trinket"
        if key.startswith("virtue"):
            return "virtue"
        return "other"

    # -- counting -----------------------------------------------------
    def owned(self, kind):
        return sorted(n for n, k in self.kinds.items() if k == kind)

    def record(self, name, kind, rank):
        self.kinds[name] = kind
        if rank:
            self.ranks[name] = max(rank, self.ranks.get(name, 0))
        else:
            self.ranks.setdefault(name, 1)

    # -- advice -------------------------------------------------------
    def next_up(self, limit=3):
        class_full = len(self.owned("class_active")) >= CLASS_ACTIVE_CAP
        god_full = len(self.owned("god_active")) >= GOD_ACTIVE_CAP
        out = []
        for name, kind in PRIORITY:
            have = name in self.kinds
            if have:
                rank = self.ranks.get(name, 1)
                if kind.endswith("active") and rank < RANK_TARGET:
                    gate = gate_for(name, kind, rank + 1)
                    tail = f" (L{gate})" if self.level < gate else ""
                    out.append(f"{name} -> rank {rank + 1}{tail}")
                continue
            if kind == "class_active" and class_full:
                continue
            if kind == "god_active" and god_full:
                continue
            gate = gate_for(name, kind, 1)
            out.append(f"{name} (L{gate})" if self.level < gate else name)
            if len(out) >= limit:
                break
        return out[:limit]

    # -- printing -----------------------------------------------------
    def start(self, event):
        ink = self.ink
        self.__init__(ink, self.names)
        loc = (event.get("Location Name") or event.get("Name") or "?").title()
        diff = event.get("Difficulty", "?")
        print()
        print(ink.head(f"== RUN  {loc} - {diff}  ".ljust(64, "=")))
        print(ink.dim(f"   skill points used {event.get('Skill Points Used', '?')}"
                      f" - resource bonus {event.get('Resource Bonus', '?')}%"))
        print(ink.dim("   plan    Iron Fist + Magnetized Anvil / Mjolnir + Ball Lightning"
                      " + Arctic Arrow / Pulverize + Resonance"))
        print(ink.dim("   banish  ") + BANISH_FIRST)
        print(ink.dim("   seal    two good cards on one screen: take one, seal the other"))

    def pick(self, event):
        ink = self.ink
        key, name, rank = self.label(event)
        kind = self.kind_of(key)

        if event.get("Event Time") == 0.0:    # pre-run loadout, not a choice you make
            self.loadout_count += 1
            if kind in ("weapon", "subclass"):
                print(ink.dim(f"   equipped  {name}"))
            return

        if kind == "trinket":                 # chest rewards and charms - just log them
            print(ink.dim(f" L{self.level:<3}  --   {name}"))
            return

        self.record(name, kind, rank)

        rank_txt = f"rank {rank}" if rank else ""
        slot = ""
        if kind == "class_active":
            slot = f"class {len(self.owned('class_active'))}/{CLASS_ACTIVE_CAP}"
        elif kind == "god_active":
            slot = f"god {len(self.owned('god_active'))}/{GOD_ACTIVE_CAP}"

        if name in SKIP:
            tag, note = ink.skip("SKIP"), SKIP[name]
        elif any(name == p for p, _ in PRIORITY):
            tag, note = ink.take("TAKE"), ""
        elif name in ALSO_GOOD:
            tag, note = ink.warn(" OK "), ALSO_GOOD[name]
        elif kind == "subclass":
            tag, note = ink.warn(" OK "), "subclass locked in for the run"
        else:
            tag, note = ink.dim(" -- "), ""

        line = f" L{self.level:<3} {tag}  {ink.name(name):<34} {rank_txt:<7} {ink.dim(slot)}"
        print(line.rstrip())
        if note:
            print(ink.dim(f"        {note}"))
        nxt = self.next_up()
        if nxt and nxt != self.last_next:      # only when the target list actually moves
            print(ink.dim("        next  ") + " . ".join(nxt))
            self.last_next = nxt

    def level_up(self, event):
        self.level = event.get("Level", self.level)

    def choice_screen(self):
        """Fires when the game opens a reward screen. The offered cards are not
        logged by the game, so print the shortlist and the spend rules instead."""
        ink = self.ink
        nxt = self.next_up(3)
        cls, god = len(self.owned("class_active")), len(self.owned("god_active"))
        slots = f"class {cls}/{CLASS_ACTIVE_CAP}  god {god}/{GOD_ACTIVE_CAP}"
        if cls >= CLASS_ACTIVE_CAP and god >= GOD_ACTIVE_CAP:
            slots += "  - passives only, any active is a dead pick"
        print()
        print(ink.head(f" >> L{self.level} CHOOSE  ") + ink.take(" . ".join(nxt) if nxt
                                                                else "anything tier 1"))
        print(ink.dim(f"            {slots}  - nothing good? reroll"))

    def end(self, event):
        ink = self.ink
        mins = (event.get("Event Time") or 0) / 60
        print()
        print(ink.head(f"-- END  {event.get('Reason', '?')} at level {self.level}"
                       f" after {mins:.1f} min ".ljust(64, "-")))
        for kind, cap in (("class_active", CLASS_ACTIVE_CAP), ("god_active", GOD_ACTIVE_CAP)):
            got = self.owned(kind)
            if got:
                print(ink.dim(f"   {kind.replace('_', ' ')}: ") + ", ".join(
                    f"{n} r{self.ranks.get(n, 1)}" for n in got))
        missed = [n for n, _ in PRIORITY if n not in self.kinds][:5]
        if missed:
            print(ink.dim("   never offered / not taken: ") + ", ".join(missed))
        print()


# ---------------------------------------------------------------- main loop


def handle(event, run):
    name = event.get("Event Name")
    if name == "Level Start" and event.get("Location Name"):
        run.start(event)
    elif name == "Character Change" and event.get("To"):
        run.hero = event["To"]
    elif name == "Level Up":
        run.level_up(event)
    elif name == "Activity" and event.get("Type") == "RewardScreen":
        run.choice_screen()
    elif name == "Skill Assigned":
        run.pick(event)
    elif name == "Level End" and str(event.get("Name") or "").startswith("Map_"):
        run.end(event)


def main():
    ap = argparse.ArgumentParser(description="Live pick coach for Jotunnslayer (Warden).")
    ap.add_argument("--replay", action="store_true", help="read the newest log from the start")
    ap.add_argument("--no-watch", action="store_true", help="stop after the replay")
    ap.add_argument("--no-color", action="store_true")
    ap.add_argument("--cheat", action="store_true", help="print the decision card and exit")
    ap.add_argument("--lang", type=Path, default=LANG_XML, help="path to language_eng.xml")
    ap.add_argument("--dir", type=Path, default=ANALYTICS_DIR, help="path to the analytics folder")
    args = ap.parse_args()

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ink = Ink(not args.no_color and enable_vt())

    if args.cheat:
        print(cheat_sheet())
        return 0

    names = load_names(args.lang)
    if not names:
        print(ink.warn(f"No string table at {args.lang} - showing raw skill keys."))

    log = newest_log(args.dir)
    if log is None:
        print(ink.skip(f"No analytics logs in {args.dir}"))
        return 1

    print(ink.head("Jotunnslayer coach") + ink.dim(f"  watching {log.name}"))
    print(ink.dim("Read-only. Ctrl+C to stop."))
    stream = EventStream(log, from_start=args.replay)
    run = Run(ink, names)

    for event in stream.poll():
        handle(event, run)
    if args.no_watch:
        return 0

    while True:
        try:
            time.sleep(POLL_SECONDS)
            current = newest_log(args.dir)
            if current and current != log:          # game started a new session log
                log = current
                stream = EventStream(log, from_start=True)
                print(ink.head(f"\n>> new session log: {log.name}"))
            for event in stream.poll():
                handle(event, run)
        except KeyboardInterrupt:
            print(ink.dim("\nstopped"))
            return 0
        except FileNotFoundError:
            time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    raise SystemExit(main())
