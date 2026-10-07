"""Boss weaknesses, damage calculator and Longsword AR comparison.

Data comes from data/boss_weaknesses.csv (the Boss Weakness spreadsheet by
u/RxndyOG). Replace that file with an updated export and the tab follows.
"""
import csv
import re
import tkinter as tk
from tkinter import ttk

from core import theme
from core.storage import DATA_DIR, load_json
from core.widgets import ScrollFrame, tree_with_scroll

PAGE_TITLE = "Damage & Weaknesses"
PAGE_ORDER = 30

DMG_TYPES = ["Physical", "Magic", "Fire", "Lightning"]
STATUS_TYPES = ["Poison", "Toxic", "Bleed"]
SPECIAL_TYPES = ["Divine", "Occult"]

NOTES = [
    "Lightning is the best, followed by fire, then magic and physical.",
    "Bleed is the best, followed by toxic and poison.",
    "Occult is better than Divine. No boss is weak to Divine.",
    "All stats 10: Lightning is the best. All stats 50 / 99: Enchanted is the best.",
    "Chaos scales with Humanity (thanks u/kudsk98).",
    "Fire and Chaos raise the target's fire reduction by 3.5%; Lightning raises lightning reduction by 4%.",
    "All values are NG+0. Physical values marked ** are Strike physical. Some values may be inaccurate.",
    "Damage formula thanks to u/TheOneLeftFoot. Sheet by u/RxndyOG.",
]


def ds_damage(ar: float, defense: float) -> float:
    """DS1 attack-vs-defense curve (piecewise on AR/DEF ratio)."""
    if ar <= 0:
        return 0.0
    if defense <= 0:
        return ar * 0.9
    r = ar / defense
    if r < 0.125:
        m = 0.1
    elif r < 1:
        m = 19.2 / 49 * (r - 0.125) ** 2 + 0.1
    elif r < 2.5:
        m = -0.4 / 3 * (r - 2.5) ** 2 + 0.7
    elif r < 8:
        m = -0.8 / 121 * (r - 8) ** 2 + 0.9
    else:
        m = 0.9
    return ar * m


def num(cell):
    """'359**' -> 359.0, '---' / '' -> None."""
    m = re.match(r"\s*([\d.]+)", cell or "")
    return float(m.group(1)) if m else None


def load_sheet():
    with open(DATA_DIR / "boss_weaknesses.csv", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    header = rows[0]
    idx = {name: header.index(name) for name in DMG_TYPES + STATUS_TYPES + SPECIAL_TYPES if name in header}

    bosses = []
    for row in rows[1:]:
        if not row or not row[0].strip():
            break
        bosses.append({"name": row[0].strip(), **{k: (row[i].strip() if i < len(row) else "") for k, i in idx.items()}})

    blocks = []
    for i, row in enumerate(rows):
        if row and re.match(r"\d+ Str /", row[0]):
            head = rows[i + 1]
            block = {"title": row[0], "columns": head[1:], "rows": [], "bonus": rows[i + 6][1:], "total": rows[i + 7][1:]}
            for r in rows[i + 2:i + 6]:
                block["rows"].append((r[0], r[1:]))
            blocks.append(block)
        if row and row[0].startswith("Longsword DmgReduction"):
            blocks.append({"title": "Target damage reduction %", "columns": rows[i][1:],
                           "rows": [(r[0], r[1:]) for r in rows[i + 1:i + 5]], "bonus": None, "total": None})
    return bosses, blocks


class Page(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.bosses, self.blocks = load_sheet()
        hp_data = load_json(DATA_DIR / "bosses.json", [])
        self.hp = {b["name"]: b.get("hp") for b in hp_data}

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.t_weak = ttk.Frame(nb, padding=12)
        self.t_calc = ttk.Frame(nb, padding=12)
        self.t_ar = ttk.Frame(nb, padding=12)
        nb.add(self.t_weak, text="Boss Weaknesses")
        nb.add(self.t_calc, text="Damage Calculator")
        nb.add(self.t_ar, text="Longsword AR / Infusions")

        self.sort_col, self.sort_rev = None, False
        self.mode = tk.StringVar(value="row")
        self._build_weak()
        self._build_calc()
        self._build_ar()

    # ---------------------------------------------------- weakness heatmap
    def _build_weak(self):
        top = ttk.Frame(self.t_weak)
        top.pack(fill="x", pady=(0, 8))
        ttk.Label(top, text="Boss defenses (NG+0). Lower number = takes more damage.", style="Muted.TLabel").pack(side="left")
        ttk.Radiobutton(top, text="Highlight best element per boss", value="row", variable=self.mode,
                        command=self._draw_grid).pack(side="right")
        ttk.Radiobutton(top, text="Highlight weakest bosses per element", value="col", variable=self.mode,
                        command=self._draw_grid).pack(side="right", padx=12)
        self.grid_sf = ScrollFrame(self.t_weak)
        self.grid_sf.pack(fill="both", expand=True)
        legend = ttk.Frame(self.t_weak)
        legend.pack(fill="x", pady=(8, 0))
        for color, text in ((theme.TINT_GOOD, "weakest"), (theme.TINT_BAD, "strongest"), (theme.TINT_NONE, "immune ---")):
            tk.Label(legend, bg=color, width=2).pack(side="left")
            ttk.Label(legend, text=f" {text}    ", style="Muted.TLabel").pack(side="left")
        ttk.Label(legend, text="Click a column heading to sort.", style="Muted.TLabel").pack(side="right")
        self._draw_grid()

    def _sort(self, col):
        self.sort_rev = not self.sort_rev if self.sort_col == col else False
        self.sort_col = col
        self._draw_grid()

    def _draw_grid(self):
        g = self.grid_sf.inner
        for w in g.winfo_children():
            w.destroy()
        cols = ["Boss"] + DMG_TYPES + ["Best"] + STATUS_TYPES + SPECIAL_TYPES
        bosses = list(self.bosses)
        for b in bosses:
            vals = {t: num(b.get(t)) for t in DMG_TYPES}
            vals = {k: v for k, v in vals.items() if v is not None}
            b["Best"] = min(vals, key=vals.get) if vals else "—"
        if self.sort_col:
            def key(b):
                if self.sort_col in ("Boss", "Best"):
                    return (0, b.get("name" if self.sort_col == "Boss" else "Best", ""))
                v = num(b.get(self.sort_col))
                return (1, 0) if v is None else (0, v)
            bosses.sort(key=key, reverse=self.sort_rev)

        col_ranges = {}
        for t in DMG_TYPES + STATUS_TYPES:
            vs = [num(b.get(t)) for b in self.bosses if num(b.get(t)) is not None]
            col_ranges[t] = (min(vs), max(vs)) if vs else (0, 1)

        for c, name in enumerate(cols):
            arrow = (" ▼" if self.sort_rev else " ▲") if self.sort_col == name else ""
            lbl = tk.Label(g, text=name + arrow, bg=theme.PANEL2, fg=theme.ACCENT, font=("Segoe UI", 9, "bold"),
                           padx=8, pady=6, cursor="hand2")
            lbl.grid(row=0, column=c, sticky="nsew", padx=1, pady=1)
            lbl.bind("<Button-1>", lambda e, n=name: self._sort(n))
            g.columnconfigure(c, weight=3 if c == 0 else 1)

        for r, b in enumerate(bosses, start=1):
            row_vals = {t: num(b.get(t)) for t in DMG_TYPES}
            present = [v for v in row_vals.values() if v is not None]
            lo, hi = (min(present), max(present)) if present else (0, 0)
            for c, name in enumerate(cols):
                text = b["name"] if name == "Boss" else b.get(name, "")
                bg, fg = theme.PANEL, theme.FG
                if name in DMG_TYPES + STATUS_TYPES:
                    v = num(text)
                    if v is None:
                        bg, fg = theme.TINT_NONE, theme.MUTED
                    elif self.mode.get() == "row" and name in DMG_TYPES:
                        bg = theme.TINT_GOOD if v == lo else (theme.TINT_BAD if v == hi and hi != lo else theme.PANEL)
                    elif self.mode.get() == "col":
                        cmin, cmax = col_ranges[name]
                        frac = (v - cmin) / (cmax - cmin) if cmax > cmin else 0
                        bg = theme.TINT_GOOD if frac < 0.15 else (theme.TINT_BAD if frac > 0.6 else theme.PANEL)
                elif name == "Best":
                    fg = {"Lightning": "#e8d36a", "Fire": theme.EMBER, "Magic": "#7fa8e0", "Physical": theme.FG}.get(text, theme.MUTED)
                elif name in SPECIAL_TYPES:
                    fg = theme.GOOD if "weak" in text else theme.MUTED
                tk.Label(g, text=text, bg=bg, fg=fg, padx=8, pady=4,
                         anchor="w" if name == "Boss" else "center",
                         font=theme.FONT_BOLD if name in ("Boss", "Best") else theme.FONT
                         ).grid(row=r, column=c, sticky="nsew", padx=1, pady=1)

        # summary: how many bosses are weakest to each element
        r = len(bosses) + 1
        tk.Label(g, text="Bosses weakest to it", bg=theme.PANEL2, fg=theme.MUTED, padx=8, pady=4, anchor="w"
                 ).grid(row=r, column=0, sticky="nsew", padx=1, pady=(6, 1))
        for c, name in enumerate(DMG_TYPES, start=1):
            n = sum(1 for b in self.bosses if b["Best"] == name)
            tk.Label(g, text=str(n), bg=theme.PANEL2, fg=theme.ACCENT, font=theme.FONT_BOLD
                     ).grid(row=r, column=c, sticky="nsew", padx=1, pady=(6, 1))

        notes = ttk.Frame(g)
        notes.grid(row=r + 1, column=0, columnspan=len(cols), sticky="w", pady=(14, 0))
        ttk.Label(notes, text="Notes from the sheet", style="H2.TLabel").pack(anchor="w")
        for n in NOTES:
            ttk.Label(notes, text="•  " + n, style="Muted.TLabel").pack(anchor="w")

    # -------------------------------------------------- damage calculator
    def _build_calc(self):
        f = self.t_calc
        left = ttk.Frame(f)
        left.pack(side="left", fill="y", padx=(0, 20))
        right = ttk.Frame(f)
        right.pack(side="left", fill="both", expand=True)

        ttk.Label(left, text="Damage Calculator", style="H2.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(left, text="Your weapon's AR vs. a target's defense.", style="Muted.TLabel").grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(0, 10))

        ttk.Label(left, text="Target").grid(row=2, column=0, sticky="w")
        self.target = tk.StringVar(value=self.bosses[0]["name"])
        cb = ttk.Combobox(left, textvariable=self.target, state="readonly", width=28,
                          values=["Custom"] + [b["name"] for b in self.bosses])
        cb.grid(row=2, column=1, columnspan=2, sticky="w", pady=4)
        cb.bind("<<ComboboxSelected>>", lambda e: self._fill_target())

        ttk.Label(left, text="", ).grid(row=3, column=0)
        ttk.Label(left, text="Your AR", style="Muted.TLabel").grid(row=3, column=1)
        ttk.Label(left, text="Target defense", style="Muted.TLabel").grid(row=3, column=2)
        self.ar, self.df = {}, {}
        defaults = {"Physical": "200", "Magic": "0", "Fire": "0", "Lightning": "0"}
        for i, t in enumerate(DMG_TYPES, start=4):
            ttk.Label(left, text=t).grid(row=i, column=0, sticky="w", pady=3)
            self.ar[t] = tk.StringVar(value=defaults[t])
            self.df[t] = tk.StringVar()
            ttk.Entry(left, textvariable=self.ar[t], width=10).grid(row=i, column=1, padx=6)
            ttk.Entry(left, textvariable=self.df[t], width=10).grid(row=i, column=2, padx=6)

        r = 4 + len(DMG_TYPES)
        self.mv = tk.StringVar(value="100")
        self.bonus = tk.StringVar(value="100")
        self.hp_var = tk.StringVar()
        for j, (label, var) in enumerate((("Motion value %", self.mv), ("Bonus multiplier %", self.bonus),
                                          ("Target HP", self.hp_var))):
            ttk.Label(left, text=label).grid(row=r + j, column=0, sticky="w", pady=(10 if j == 0 else 3, 3))
            ttk.Entry(left, textvariable=var, width=10).grid(row=r + j, column=1, padx=6, pady=(10 if j == 0 else 3, 3))
        ttk.Label(left, style="Muted.TLabel", wraplength=300, justify="left",
                  text="Bonus multiplier: e.g. 110 for Divine/Occult vs. the right enemy type. "
                       "Boss HP values are approximate (NG); verify on the wiki.").grid(
            row=r + 3, column=0, columnspan=3, sticky="w", pady=(4, 0))

        for v in list(self.ar.values()) + list(self.df.values()) + [self.mv, self.bonus, self.hp_var]:
            v.trace_add("write", lambda *_: self._calc())

        self.out = tk.Text(right, height=11, bg=theme.PANEL, fg=theme.FG, relief="flat", font=("Consolas", 11),
                           padx=12, pady=10)
        self.out.pack(fill="x")
        self.out.tag_configure("big", foreground=theme.ACCENT, font=("Consolas", 14, "bold"))
        self.out.tag_configure("muted", foreground=theme.MUTED)

        ttk.Label(right, text="Same weapon against every boss", style="H2.TLabel").pack(anchor="w", pady=(14, 4))
        frame, self.cmp_tree = tree_with_scroll(right, ("Boss", "Damage / hit", "% of AR", "HP (approx)", "Hits to kill"),
                                                widths={"Boss": 230}, height=14)
        frame.pack(fill="both", expand=True)
        self._fill_target()

    def _boss_hp(self, name):
        if name in self.hp:
            return self.hp[name]
        for k, v in self.hp.items():
            if name.split(",")[0].split()[0] in k:
                return v
        return None

    def _fill_target(self):
        name = self.target.get()
        b = next((b for b in self.bosses if b["name"] == name), None)
        if b:
            for t in DMG_TYPES:
                v = num(b.get(t))
                self.df[t].set("" if v is None else f"{v:g}")
            hp = self._boss_hp(name)
            self.hp_var.set(str(hp) if hp else "")
        self._calc()

    @staticmethod
    def _f(var, default=0.0):
        try:
            return float(var.get().replace(",", "."))
        except ValueError:
            return default

    def _hit(self, defenses):
        mult = self._f(self.mv, 100) / 100 * self._f(self.bonus, 100) / 100
        parts, total_ar = {}, 0.0
        for t in DMG_TYPES:
            ar = self._f(self.ar[t]) * mult
            total_ar += ar
            d = defenses.get(t)
            parts[t] = (ar, None if d is None else ds_damage(ar, d))
        total = sum(p[1] for p in parts.values() if p[1] is not None)
        return parts, total, total_ar

    def _calc(self):
        if not hasattr(self, "cmp_tree"):
            return
        defenses = {t: (self._f(self.df[t]) if self.df[t].get().strip() else None) for t in DMG_TYPES}
        parts, total, total_ar = self._hit(defenses)
        o = self.out
        o.configure(state="normal")
        o.delete("1.0", "end")
        o.insert("end", f"{'Type':<11}{'AR':>9}{'Def':>9}{'Damage':>10}{'Reduced':>10}\n", "muted")
        for t, (ar, dmg) in parts.items():
            d = defenses[t]
            if ar == 0:
                continue
            if dmg is None:
                o.insert("end", f"{t:<11}{ar:>9.1f}{'---':>9}{'immune':>10}\n")
            else:
                o.insert("end", f"{t:<11}{ar:>9.1f}{d:>9.0f}{dmg:>10.1f}{(1 - dmg / ar) * 100:>9.1f}%\n")
        o.insert("end", "\n")
        o.insert("end", f"Damage per hit: {total:,.1f}\n", "big")
        if total_ar:
            o.insert("end", f"Damage reduced: {(1 - total / total_ar) * 100:.1f}% of {total_ar:,.1f} AR\n")
        hp = self._f(self.hp_var, 0)
        if hp and total:
            eff = hp / (total / total_ar) if total_ar else 0
            o.insert("end", f"Hits to kill:   {hp / total:.2f}  ({int(-(-hp // total))} hits)\n")
            o.insert("end", f"Effective HP:   {eff:,.1f}\n", "muted")
        o.configure(state="disabled")

        t = self.cmp_tree
        t.delete(*t.get_children())
        for b in self.bosses:
            d = {k: num(b.get(k)) for k in DMG_TYPES}
            _, dmg, ar = self._hit(d)
            hp = self._boss_hp(b["name"])
            if all(v is None for v in d.values()):
                t.insert("", "end", values=(b["name"], "—", "—", hp or "—", "—"), tags=("muted",))
                continue
            t.insert("", "end", values=(b["name"], f"{dmg:.1f}", f"{dmg / ar * 100:.0f}%" if ar else "—",
                                        hp or "—", f"{-(-hp // dmg):.0f}" if hp and dmg else "—"))

    # ------------------------------------------------------- AR tables
    def _build_ar(self):
        sf = ScrollFrame(self.t_ar)
        sf.pack(fill="both", expand=True)
        g = sf.inner
        ttk.Label(g, text="Longsword by infusion: AR (base + scaling) at different stat levels",
                  style="H2.TLabel").pack(anchor="w", pady=(0, 8))
        for block in self.blocks:
            ttk.Label(g, text=block["title"], style="H2.TLabel").pack(anchor="w", pady=(12, 4))
            tbl = ttk.Frame(g)
            tbl.pack(anchor="w", fill="x")
            cols = [""] + [c for c in block["columns"] if c]
            n = len(cols)
            totals = [num(x) for x in (block["total"] or [])][:n - 1]
            best = max((v for v in totals if v is not None), default=None)
            for c, name in enumerate(cols):
                tk.Label(tbl, text=name, bg=theme.PANEL2, fg=theme.ACCENT, font=("Segoe UI", 9, "bold"),
                         padx=6, pady=4, wraplength=90).grid(row=0, column=c, sticky="nsew", padx=1, pady=1)
                tbl.columnconfigure(c, weight=1)
            body = list(block["rows"])
            if block["bonus"] and any(x.strip() for x in block["bonus"]):
                body.append(("Bonus % (vs. undead)", block["bonus"]))
            for r, (label, vals) in enumerate(body, start=1):
                tk.Label(tbl, text=label, bg=theme.PANEL, fg=theme.MUTED, padx=6, pady=3, anchor="w"
                         ).grid(row=r, column=0, sticky="nsew", padx=1, pady=1)
                for c in range(1, n):
                    v = vals[c - 1] if c - 1 < len(vals) else ""
                    fg = theme.MUTED if v.strip() in ("0", "") else theme.FG
                    tk.Label(tbl, text=v, bg=theme.PANEL, fg=fg, padx=6, pady=3
                             ).grid(row=r, column=c, sticky="nsew", padx=1, pady=1)
            if totals:
                r = len(body) + 1
                tk.Label(tbl, text="Total AR", bg=theme.PANEL2, fg=theme.FG, font=theme.FONT_BOLD, padx=6, pady=3,
                         anchor="w").grid(row=r, column=0, sticky="nsew", padx=1, pady=1)
                for c, v in enumerate(totals, start=1):
                    is_best = v is not None and v == best
                    tk.Label(tbl, text="" if v is None else f"{v:g}",
                             bg=theme.TINT_GOOD if is_best else theme.PANEL2,
                             fg=theme.GOOD if is_best else theme.FG, font=theme.FONT_BOLD, padx=6, pady=3
                             ).grid(row=r, column=c, sticky="nsew", padx=1, pady=1)
