# Dark Souls Companion

A desktop hub for Dark Souls 1 / Remastered. Pure Python + Tkinter, so there's nothing to install.

```
python main.py        (or double-click "Start DS Companion.bat")
```

## Tabs

| Tab | What it does |
|---|---|
| **All Weapons / All Bosses** | Challenge tracker: dashboard, weapon roulette (seeded), run log with per-boss deaths, weapon list, boss mastery, CSV export |
| **Level Calculator** | Target stats to SL and souls for every class, best starting class, equip load / roll thresholds, attunement slots |
| **Damage & Weaknesses** | Boss defense heatmap (from your spreadsheet), AR-vs-defense damage calculator, Longsword infusion AR tables |
| **Resources** | Link cards (wiki, speedrun.com, Any% guide, DSR Bingo, ...). Add or remove them in the app |

## Adding things

* **A link:** click **+ Add resource** on the Resources tab (saved to `data/links.json`).
* **A whole new tool/tab:** copy `modules/_template.py` to `modules/your_tool.py`, edit it, then restart. Any file in `modules/`
  that has `PAGE_TITLE` and a `Page` class becomes a tab. `PAGE_ORDER` sets the position.
* **Data:** everything is plain JSON/CSV in `data/`:
  * `weapons.json`: the challenge weapon list (name, class, upgrade material, dlc)
  * `bosses.json`: bosses in the run, area, approx HP, dlc flag
  * `classes.json`: starting classes and base stats
  * `boss_weaknesses.csv`: the Boss Weakness sheet. Drop in a new export to update it

## Your progress

Saved to `save/challenge.json` after every change. Back that file up to keep your runs.
