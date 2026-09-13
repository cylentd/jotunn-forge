# Jotunnslayer coach

Prints what to take next while you play. Read-only — it tails the game's own
telemetry log and never touches the game, the save, or the log.

## Run it

```
python coach.py
```

Start it before or during a run, in a terminal beside the game. `Ctrl+C` stops it.

| Flag | What it does |
|---|---|
| `--replay` | replay the newest log from the start, then keep watching |
| `--no-watch` | with `--replay`, print the replay and exit |
| `--no-color` | plain text |
| `--lang PATH` | path to `language_eng.xml` if the game isn't on `F:` |
| `--dir PATH` | path to the analytics folder |

## What it reads

| Source | Used for |
|---|---|
| `%USERPROFILE%\AppData\LocalLow\Games Farm\Jotunnslayer\analytics\gameplay_analytics_*.json` | your picks, levels, run start/end |
| `...\Jotunnslayer_Data\StreamingAssets\language\language_eng.xml` | turning `warden_active_D` into "Magnetized Anvil" |

The coach follows the newest log file and switches automatically when the game
starts a new session. Pick advice arrives as fast as the game flushes its log —
that interval is the game's, not the script's.

## The build it coaches

Warden, stun-and-lightning:

- **Class actives (cap 2):** Iron Fist, Magnetized Anvil
- **God actives (cap 3):** Mjolnir, Ball Lightning, Arctic Arrow
- **Passives first:** Pulverize, Resonance, Might of Megingjord, Overwhelming Potential, King of Gods
- **Skip on sight:** Kraken, Frost Ring, Huginn & Munnin, Einherjar

Rankings come from `Survivor_SkillDescription.csv` in the game install, read
2026-09-12. Edit `PRIORITY`, `ALSO_GOOD` and `SKIP` at the top of `coach.py` to
coach a different build; names there are the game's own display names.
