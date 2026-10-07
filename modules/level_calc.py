"""DS1 Soul Level calculator (inspired by trifectaiii's DS1 Soul Level Calculator).

Enter the stats you want; it shows the resulting SL for every starting class,
which class gets there cheapest, and how many souls it costs.
"""
import tkinter as tk
from tkinter import ttk

from core import theme
from core.storage import DATA_DIR, load_json
from core.widgets import StatCard, tree_with_scroll

PAGE_TITLE = "Level Calculator"
PAGE_ORDER = 20

# Souls needed to *reach* levels 2..12; from 13 on the game uses a formula.
EARLY_COSTS = {2: 673, 3: 690, 4: 707, 5: 724, 6: 741, 7: 758, 8: 775, 9: 793, 10: 811, 11: 829, 12: 847}


def level_cost(target_level: int) -> int:
    """Souls to go from target_level-1 to target_level."""
    if target_level <= 1:
        return 0
    if target_level in EARLY_COSTS:
        return EARLY_COSTS[target_level]
    x = target_level
    return int(0.02 * x ** 3 + 3.06 * x ** 2 + 105.6 * x - 895 + 0.5)


def souls_between(start: int, end: int) -> int:
    return sum(level_cost(l) for l in range(start + 1, end + 1))


def attunement_slots(att: int) -> int:
    for threshold, slots in ((50, 10), (41, 9), (34, 8), (28, 7), (23, 6), (19, 5), (16, 4), (14, 3), (12, 2), (10, 1)):
        if att >= threshold:
            return slots
    return 0


class Page(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=16)
        data = load_json(DATA_DIR / "classes.json")
        self.stat_names = data["stats"]
        self.classes = data["classes"]

        left = ttk.Frame(self)
        left.pack(side="left", fill="y", padx=(0, 16))
        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True)

        ttk.Label(left, text="Soul Level Calculator", style="H2.TLabel").grid(row=0, column=0, columnspan=4, sticky="w")
        ttk.Label(left, text="Type the stats you want to end up with.", style="Muted.TLabel").grid(
            row=1, column=0, columnspan=4, sticky="w", pady=(0, 10))

        ttk.Label(left, text="Starting class").grid(row=2, column=0, sticky="w")
        self.cls = tk.StringVar(value="Pyromancer")
        cb = ttk.Combobox(left, textvariable=self.cls, values=list(self.classes), state="readonly", width=16)
        cb.grid(row=2, column=1, columnspan=3, sticky="w", pady=4)
        cb.bind("<<ComboboxSelected>>", lambda e: self.update())

        ttk.Label(left, text="Stat", style="Muted.TLabel").grid(row=3, column=0, sticky="w", pady=(10, 2))
        ttk.Label(left, text="Base", style="Muted.TLabel").grid(row=3, column=1, pady=(10, 2))
        ttk.Label(left, text="Target", style="Muted.TLabel").grid(row=3, column=2, pady=(10, 2))
        ttk.Label(left, text="+", style="Muted.TLabel").grid(row=3, column=3, pady=(10, 2))

        self.target, self.base_lbl, self.diff_lbl = {}, {}, {}
        for i, stat in enumerate(self.stat_names, start=4):
            ttk.Label(left, text=stat).grid(row=i, column=0, sticky="w", pady=3)
            b = ttk.Label(left, text="", style="Muted.TLabel", width=4, anchor="center")
            b.grid(row=i, column=1)
            v = tk.StringVar()
            v.trace_add("write", lambda *_: self.update())
            ttk.Spinbox(left, from_=1, to=99, textvariable=v, width=6, command=self.update).grid(row=i, column=2, padx=6)
            d = ttk.Label(left, text="", width=4, anchor="center")
            d.grid(row=i, column=3)
            self.target[stat], self.base_lbl[stat], self.diff_lbl[stat] = v, b, d

        row = 4 + len(self.stat_names)
        ttk.Label(left, text="Current SL (optional)").grid(row=row, column=0, sticky="w", pady=(14, 3))
        self.current = tk.StringVar()
        self.current.trace_add("write", lambda *_: self.update())
        ttk.Entry(left, textvariable=self.current, width=8).grid(row=row, column=2, pady=(14, 3))

        btns = ttk.Frame(left)
        btns.grid(row=row + 1, column=0, columnspan=4, sticky="w", pady=10)
        ttk.Button(btns, text="Reset to class base", command=self.reset).pack(side="left")
        ttk.Button(btns, text="Use best class", style="Accent.TButton", command=self.use_best).pack(side="left", padx=6)

        presets = ttk.LabelFrame(left, text="Quick presets", padding=8)
        presets.grid(row=row + 2, column=0, columnspan=4, sticky="ew")
        for j, (name, vals) in enumerate(PRESETS.items()):
            ttk.Button(presets, text=name, style="Small.TButton",
                       command=lambda v=vals: self.apply_preset(v)).grid(row=j // 2, column=j % 2, sticky="ew", padx=2, pady=2)

        # results
        cards = ttk.Frame(right)
        cards.pack(fill="x")
        cards.columnconfigure(0, weight=1)
        cards.columnconfigure(1, weight=1)
        self.res = StatCard(cards, "RESULT")
        self.res.row("Soul Level", big=True)
        self.res.row("Souls from class start", ember=True)
        self.res.row("Souls from current SL")
        self.res.row("Next level costs")
        self.res.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        self.der = StatCard(cards, "DERIVED")
        self.der.row("Equip load")
        self.der.row("Medium roll (<50%)")
        self.der.row("Fast roll (<25%)")
        self.der.row("Attunement slots")
        self.der.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        ttk.Label(right, text="Every class for this build", style="H2.TLabel").pack(anchor="w", pady=(16, 4))
        frame, self.tree = tree_with_scroll(right, ("Class", "Start SL", "Final SL", "Souls needed", "Wasted points"),
                                            widths={"Class": 150}, height=11)
        frame.pack(fill="x")
        self.tree.tag_configure("best", foreground=theme.GOOD, font=theme.FONT_BOLD)
        self.tree.tag_configure("current", background=theme.SELECT)

        ttk.Label(right, text="Level cost lookup", style="H2.TLabel").pack(anchor="w", pady=(16, 4))
        lk = ttk.Frame(right)
        lk.pack(anchor="w")
        ttk.Label(lk, text="From SL").pack(side="left")
        self.lk_from, self.lk_to = tk.StringVar(value="1"), tk.StringVar(value="120")
        for v in (self.lk_from, self.lk_to):
            v.trace_add("write", lambda *_: self.update_lookup())
        ttk.Entry(lk, textvariable=self.lk_from, width=6).pack(side="left", padx=6)
        ttk.Label(lk, text="to SL").pack(side="left")
        ttk.Entry(lk, textvariable=self.lk_to, width=6).pack(side="left", padx=6)
        self.lk_out = ttk.Label(lk, text="", style="H2.TLabel")
        self.lk_out.pack(side="left", padx=12)

        ttk.Label(right, style="Muted.TLabel", wraplength=640, justify="left",
                  text="SL = class SL + points added. A target below a class's base stat is wasted points "
                       "for that class. Level costs use the DS1 table up to SL 12 and the in-game formula "
                       "0.02x³ + 3.06x² + 105.6x − 895 after.").pack(anchor="w", pady=(14, 0))
        self.reset()
        self.update_lookup()

    # ---------------------------------------------------------------
    def _targets(self):
        out = {}
        for s, v in self.target.items():
            try:
                out[s] = max(1, min(99, int(v.get())))
            except ValueError:
                out[s] = None
        return out

    def build_sl(self, cls, targets):
        c = self.classes[cls]
        added = wasted = 0
        for s in self.stat_names:
            t = targets.get(s) or c["stats"][s]
            diff = t - c["stats"][s]
            if diff >= 0:
                added += diff
            else:
                wasted += -diff
        return c["level"] + added, wasted

    def reset(self):
        base = self.classes[self.cls.get()]["stats"]
        self._bulk = True
        for s in self.stat_names:
            self.target[s].set(str(base[s]))
        self._bulk = False
        self.update()

    def apply_preset(self, vals):
        self._bulk = True
        base = self.classes[self.cls.get()]["stats"]
        for s in self.stat_names:
            self.target[s].set(str(vals.get(s, base[s])))
        self._bulk = False
        self.update()

    def use_best(self):
        targets = self._targets()
        best = min(self.classes, key=lambda c: (self.build_sl(c, targets)[0], c))
        self.cls.set(best)
        self.update()

    def update(self):
        if getattr(self, "_bulk", False) or not hasattr(self, "tree"):
            return
        cls = self.cls.get()
        base = self.classes[cls]["stats"]
        targets = self._targets()
        for s in self.stat_names:
            self.base_lbl[s].configure(text=str(base[s]))
            t = targets[s]
            if t is None:
                self.diff_lbl[s].configure(text="?", foreground=theme.BAD)
            elif t < base[s]:
                self.diff_lbl[s].configure(text=f"{t - base[s]}", foreground=theme.BAD)
            else:
                self.diff_lbl[s].configure(text=f"+{t - base[s]}" if t > base[s] else "·",
                                           foreground=theme.ACCENT if t > base[s] else theme.MUTED)

        sl, _ = self.build_sl(cls, targets)
        start = self.classes[cls]["level"]
        self.res.set("Soul Level", sl)
        self.res.set("Souls from class start", f"{souls_between(start, sl):,}")
        try:
            cur = int(self.current.get())
            self.res.set("Souls from current SL", f"{souls_between(cur, sl):,}" if cur <= sl else "already past")
        except ValueError:
            self.res.set("Souls from current SL", "—")
        self.res.set("Next level costs", f"{level_cost(sl + 1):,}")

        end = targets["Endurance"] or base["Endurance"]
        load = 40 + end
        self.der.set("Equip load", f"{load:.1f}")
        self.der.set("Medium roll (<50%)", f"≤ {load * 0.5:.1f}")
        self.der.set("Fast roll (<25%)", f"≤ {load * 0.25:.1f}")
        self.der.set("Attunement slots", attunement_slots(targets["Attunement"] or base["Attunement"]))

        rows = []
        for c, info in self.classes.items():
            fsl, wasted = self.build_sl(c, targets)
            rows.append((fsl, c, info["level"], wasted))
        rows.sort()
        best_sl = rows[0][0]
        self.tree.delete(*self.tree.get_children())
        for fsl, c, start_sl, wasted in rows:
            tags = []
            if fsl == best_sl:
                tags.append("best")
            if c == cls:
                tags.append("current")
            self.tree.insert("", "end", values=(c, start_sl, fsl, f"{souls_between(start_sl, fsl):,}", wasted),
                             tags=tags)

    def update_lookup(self):
        try:
            a, b = int(self.lk_from.get()), int(self.lk_to.get())
        except ValueError:
            self.lk_out.configure(text="")
            return
        if b < a:
            a, b = b, a
        self.lk_out.configure(text=f"{souls_between(a, min(b, 713)):,} souls")


PRESETS = {
    "Quality (40/40)": {"Vitality": 40, "Endurance": 40, "Strength": 40, "Dexterity": 40},
    "Pyro (SL ~40)": {"Vitality": 30, "Endurance": 25, "Strength": 16, "Dexterity": 14, "Attunement": 14},
    "Sorcery (Int 45)": {"Vitality": 30, "Attunement": 30, "Endurance": 25, "Intelligence": 45},
    "Faith (Fai 50)": {"Vitality": 30, "Attunement": 16, "Endurance": 30, "Strength": 28, "Faith": 50},
    "Dex (Dex 40)": {"Vitality": 40, "Endurance": 40, "Strength": 16, "Dexterity": 40},
    "Str (Str 50)": {"Vitality": 40, "Endurance": 40, "Strength": 50, "Dexterity": 14},
}
