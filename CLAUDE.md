# CLAUDE.md: Dark Souls Hub (DS1 Companion)

Context for Claude Code sessions on any machine. Read this before changing anything.

## What this is

A desktop hub for **Dark Souls 1 / Remastered**, built for Lukas. It combines tools he used as separate
spreadsheets and websites:

| Tab (module) | Source it replaces |
|---|---|
| All Weapons / All Bosses (`modules/challenge.py`) | His Excel tracker `DarkSouls_Ultimate_Challenge_Tracker_Boss_RunLog.xlsm` (Dashboard sheet) |
| Level Calculator (`modules/level_calc.py`) | https://trifectaiii.github.io/DS1-Soul-Level-Calculator/ |
| Damage & Weaknesses (`modules/damage.py`) | Boss Weakness spreadsheet by u/RxndyOG (`data/boss_weaknesses.csv`) |
| Resources (`modules/links.py`) | Links: Fextralife wiki, speedrun.com DSR, DSR Any% Google Doc guide, his DSR-Bingo repo |

## Run

```
python main.py            # or double-click "Start DS Companion.bat" (Windows, uses pythonw)
```

Python 3.10+ with Tkinter (stdlib only, no pip installs). Developed on Python 3.14, Windows 11.

## Architecture

- `main.py`: window, theme, and **auto-discovery of tabs**. Every `modules/*.py` not starting with `_` that defines
  `PAGE_TITLE` + a `Page(ttk.Frame)` class becomes a tab, ordered by `PAGE_ORDER`. A module that crashes on import
  shows an error tab instead of killing the app. `app.show_page(title)` switches tabs.
- `modules/_template.py`: copy this to add a new tool.
- `core/theme.py`: all colours/fonts (dark, ember-gold accent). Use its constants, never literal colours.
- `core/widgets.py`: `ScrollFrame`, `StatCard`, `tree_with_scroll` (sortable Treeview), `make_sortable`.
- `core/storage.py`: `DATA_DIR`, `SAVE_DIR`, `load_json`, `save_json` (atomic write).
- `data/`: editable JSON/CSV. `save/challenge.json`: the user's run log (gitignored, see below).

### Challenge tracker model
One run log is the single source of truth; every stat is derived from it in `Tracker.stats()`.
A run: `{id, weapon, date, time "h:mm:ss", completed, killed: [boss], boss_deaths: {boss: n}, non_boss_deaths, notes}`.
Weapon counts as done when it has a completed run. `excluded` weapons don't count. Roulette =
`random.Random(seed).choice(sorted(remaining))`.

### Formulas (verified)
- Damage per type (`damage.ds_damage`): piecewise on AR/DEF ratio. Matches the sheet exactly: AR 151 vs DEF 64 gives 105.302.
- Level cost: table for SL 2–12 (673…847), then `round(0.02x³ + 3.06x² + 105.6x − 895)`. SL 13 costs 1039, SL 14 costs 1238.
- SL for a build = class SL + points added above that class's base stats.

## Known data caveats (verify before trusting)

- `data/weapons.json` has **117** weapons; Lukas's original sheet counted **112**. He should exclude the extra 5
  in the app (Weapons tab: "Include / exclude"). Ask him which ones if relevant.
- Upgrade materials, DLC flags and boss HP in `data/bosses.json` were written from memory, not a source.
  Boss HP is labelled "approx" in the UI. Cross-check with the Fextralife wiki when touching them.
- `boss_weaknesses.csv` values are boss **defenses** (lower = weaker), NG+0. Ornstein/Smough are separate rows
  there but one combined boss ("Ornstein & Smough") in `bosses.json`.
- His existing runs from the Excel tracker are **not imported**. Only the Dashboard sheet was exported. An importer
  for a Run Log CSV export is a requested-but-unbuilt feature.
- The DSR-Bingo repo (github.com/Meiselbach/DSR-Bingo) returned 404 to anonymous fetches, probably private.

## Next planned work: web version (NOT STARTED, awaiting Lukas's go-ahead)

He asked for a web version. Do not start building until he confirms. He explicitly said not to start
unprompted. The proposed plan (made with the `frontend-design` skill), shown to him and awaiting confirmation:

- **Job:** log a run fast and see the next weapon. Same 4 sections as the desktop app.
- **Look:** warm ash background, stone panels, bone-coloured text, ember/estus gold accent. Green/red only for
  kills/deaths. Fonts: **IM Fell English SC** (headings, evokes in-game item descriptions) + **Alegreya Sans**
  (body, tabular numbers).
- **One bold element:** the roulette's next weapon shown as an in-game item description card. Everything else quiet.
- Drop the desktop app's ALL-CAPS card labels and identical-card layout (generic-design tells per the skill).
- Layout: roulette + challenge status on the left, tabbed workspace on the right, one column on mobile.
- Persistence idea: if published as a claude.ai Artifact, use the `db` + `user` capabilities with runs private
  per user (`data/users/<id>/tracker` doc + `runs` subcollection), localStorage fallback, and import/export of the
  desktop `challenge.json` format so both versions share data.
- After building, audit it with the `web-design-guidelines` skill.

### Skills Lukas wants used for UI work
Load these before building or reviewing UI (they are not installed globally; fetch per session):
```
npx skills use "https://github.com/anthropics/skills" --skill "frontend-design"
npx skills use "https://github.com/vercel-labs/agent-skills" --skill "web-design-guidelines"
```
`web-design-guidelines` fetches its rules from
https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md

## Working with Lukas

- Writes in English and Spanish; reply in the language of his latest message.
- Wants to be asked before big new work starts (see web version note above).
- Gamer, not necessarily a developer: explain where files are and how to run things in plain terms.
- His progress lives in `save/challenge.json`, which is gitignored so a pull never overwrites it. To move progress
  between PCs, copy that file manually (or remove it from `.gitignore` if he wants it synced).
