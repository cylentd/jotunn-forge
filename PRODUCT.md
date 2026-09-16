# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

David and a few friends who play Jotunnslayer: Hordes of Hel. All are expert players: they know the classes, gods, blessings, rank gates and difficulty ladder without explanation.

They use Jotunn Forge at three moments:

- **Mid-run glance** on a second screen: which card to take from the god on offer.
- **Between runs:** pick a build, check pick order and the temple virtues to buy next.
- **After a run:** compare what the run measured against the build's claims.

## Product Purpose

Jotunn Forge holds builds for every Jotunnslayer character and tells an expert what to pick, in what order, and why, backed by measured runs.

Success: at any of the three moments, the reader finds the answer they came for in seconds and trusts it because the evidence is visible.

## Positioning

Build grades come from the player's own analytics logs and the installed game's skill tables, not from opinion. A community guide can copy a pick list; it cannot copy measured damage shares from these runs.

## Operating Context

- The page sits beside the game on a second screen during play, and is read on its own between runs.
- Builds are selected from a switcher; each build carries its character, loadout, god boards, pick order, virtues and run evidence.
- Friends can fork a build in the editor and save their own variant.

## Capabilities and Constraints

- **Characters:** Warden is the only character covered today. Builds must name their character; site-wide chrome must not.
- **Filters:** character is the planned filter once a second character exists. Map is stored per build but gets no filter until two builds differ by map (open decision, 2026-09-12).
- **Saving:** builds save to the artifact database when the page runs as a Claude artifact, and to browser storage otherwise.
- **Data refresh:** a browser page cannot read the game's logs. Run data and skill tables are extracted outside the page and embedded (`forge/skills.js`, `forge/icons.js`, `forge/descriptions.js` via `node scripts/extract-descriptions.mjs`, `forge/scores.js` (route stat bars) via `node scripts/score-builds.mjs` after any route or virtue change, the runs tables in `forge/index.html`).
- **Retired:** the terminal pick coach (`archive/coach.py`) was retired on 2026-09-12; Forge is the only tool.

## Brand Commitments

- **Name:** Jotunn Forge.
- **Voice:** expert shorthand with jokes allowed in labels, art and advice lines. Numbers and pick advice stay exact.
- **Mascot:** the turkey-leg icon (the game's Gourmand art) in the masthead and site chrome is deliberate. Keep it.

## Evidence on Hand

- Installed game build 1.2.3.94815: skill table and icons, read 2026-09-12.
- Two logged wins, 2026-09-12: Hard (Skadi · Thor · Odin) and Insane + Railyard (Thor · Freya · Brokk), plus earlier Normal-run per-hit data.
- Frost Bastion comes from the Steam guide "Warden Endless Screensaver Build" and is untested in the logs.
- **Absent, never fabricate:** enemy HP, per-target damage attribution, weapon damage, freeze counts.

## Product Principles

1. **Readable at a glance.** God boards and pick order must answer "what do I take?" in about a second on a second screen.
2. **Measured beats claimed.** Measured runs outrank game data, which outranks guides. An untested build carries one clear tag, and every number traces to a source in the footer.
3. **Character-neutral site, character-specific builds.** The site never assumes a character; every build states its own.
4. **Expert shorthand.** Never explain a mechanic the players already know; show what is notable about this build.
5. **No structure before the data needs it.** Add a filter, section or field when real builds require it, not in anticipation.

## Accessibility & Inclusion

- Glance legibility: display type must stay unambiguous at size (a capital J must not read as D).
- Anything hidden behind hover opens on focus and tap as well.
