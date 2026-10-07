"""All Weapons / All Bosses challenge tracker.

One run log is the single source of truth: every stat on the dashboard,
weapon list and boss mastery view is derived from it.
Save file: save/challenge.json
"""
import csv
import datetime as dt
import random
import uuid
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from core import theme
from core.storage import DATA_DIR, SAVE_DIR, load_json, save_json
from core.widgets import ScrollFrame, StatCard, tree_with_scroll

PAGE_TITLE = "All Weapons / All Bosses"
PAGE_ORDER = 10

SAVE_FILE = SAVE_DIR / "challenge.json"
MILESTONES = [1, 5, 10, 25, 50, 75, 100]


# ---------------------------------------------------------------- helpers
def parse_time(text):
    """'h:mm:ss' or 'mm:ss' -> seconds, None if empty/invalid."""
    text = (text or "").strip()
    if not text:
        return None
    try:
        parts = [int(p) for p in text.split(":")]
    except ValueError:
        return None
    while len(parts) < 3:
        parts.insert(0, 0)
    h, m, s = parts[-3:]
    if m >= 60 or s >= 60 or min(parts) < 0:
        return None
    return h * 3600 + m * 60 + s


def fmt_time(seconds):
    if seconds is None:
        return "—"
    seconds = int(round(seconds))
    return f"{seconds // 3600}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


# ------------------------------------------------------------------ model
class Tracker:
    def __init__(self):
        self.weapons = load_json(DATA_DIR / "weapons.json", [])
        self.bosses = load_json(DATA_DIR / "bosses.json", [])
        self.weapon_by_name = {w["name"]: w for w in self.weapons}
        self.dlc_bosses = {b["name"] for b in self.bosses if b.get("dlc")}
        self.state = load_json(SAVE_FILE, None) or {"runs": [], "excluded": [], "seed": 1}

    def save(self):
        save_json(SAVE_FILE, self.state)

    @property
    def runs(self):
        return self.state["runs"]

    @property
    def excluded(self):
        return set(self.state.get("excluded", []))

    def active_weapons(self):
        ex = self.excluded
        return [w for w in self.weapons if w["name"] not in ex]

    def completed_weapons(self):
        active = {w["name"] for w in self.active_weapons()}
        return {r["weapon"] for r in self.runs if r.get("completed")} & active

    def remaining_weapons(self):
        done = self.completed_weapons()
        return [w for w in self.active_weapons() if w["name"] not in done]

    @staticmethod
    def run_deaths(run):
        return sum(run.get("boss_deaths", {}).values()) + run.get("non_boss_deaths", 0)

    def upsert_run(self, run):
        for i, r in enumerate(self.runs):
            if r["id"] == run["id"]:
                self.runs[i] = run
                break
        else:
            self.runs.append(run)
        self.save()

    def delete_run(self, run_id):
        self.state["runs"] = [r for r in self.runs if r["id"] != run_id]
        self.save()

    def toggle_excluded(self, name):
        ex = self.excluded
        ex.symmetric_difference_update({name})
        self.state["excluded"] = sorted(ex)
        self.save()

    def roulette(self):
        pool = sorted(w["name"] for w in self.remaining_weapons())
        if not pool:
            return None
        return self.weapon_by_name[random.Random(self.state.get("seed", 1)).choice(pool)]

    def best_time(self, weapon):
        times = [parse_time(r.get("time")) for r in self.runs
                 if r.get("completed") and r["weapon"] == weapon]
        times = [t for t in times if t is not None]
        return min(times) if times else None

    def boss_table(self):
        """Per-boss aggregate: kills, deaths, deathless kills, worst single run."""
        table = {b["name"]: {"kills": 0, "deaths": 0, "deathless": 0, "worst": 0} for b in self.bosses}
        for r in self.runs:
            deaths = r.get("boss_deaths", {})
            for name, d in deaths.items():
                row = table.setdefault(name, {"kills": 0, "deaths": 0, "deathless": 0, "worst": 0})
                row["deaths"] += d
                row["worst"] = max(row["worst"], d)
            for name in r.get("killed", []):
                row = table.setdefault(name, {"kills": 0, "deaths": 0, "deathless": 0, "worst": 0})
                row["kills"] += 1
                if deaths.get(name, 0) == 0:
                    row["deathless"] += 1
        return table

    def stats(self):
        runs = self.runs
        completed = [r for r in runs if r.get("completed")]
        active = self.active_weapons()
        done = self.completed_weapons()
        times = [parse_time(r.get("time")) for r in completed]
        times = [t for t in times if t is not None]
        avg = sum(times) / len(times) if times else None
        remaining = len(active) - len(done)

        bosses = self.boss_table()
        boss_deaths = sum(b["deaths"] for b in bosses.values())
        non_boss = sum(r.get("non_boss_deaths", 0) for r in runs)
        dlc_deaths = sum(v["deaths"] for k, v in bosses.items() if k in self.dlc_bosses)

        nemesis = max(bosses.items(), key=lambda kv: kv[1]["deaths"], default=(None, {"deaths": 0}))
        worst = max(((k, v["deaths"] / v["kills"]) for k, v in bosses.items() if v["kills"]),
                    key=lambda kv: kv[1], default=(None, 0))
        most_one = max(bosses.items(), key=lambda kv: kv[1]["worst"], default=(None, {"worst": 0}))

        best_run = None
        timed = [(parse_time(r.get("time")), r) for r in completed if parse_time(r.get("time")) is not None]
        if timed:
            t, r = min(timed, key=lambda x: x[0])
            best_run = f"{r['weapon']} ({fmt_time(t)})"

        target = len(active)
        next_ms = next((m for m in MILESTONES if m > len(done) and m < target), target)

        return {
            "weapons_done": len(done),
            "weapons_left": remaining,
            "weapons_total": target,
            "completion": (len(done) / target * 100) if target else 0,
            "runs_completed": len(completed),
            "runs_total": len(runs),
            "deaths": boss_deaths + non_boss,
            "avg_time": avg,
            "est_hours": (remaining * avg / 3600) if avg else None,
            "bosses_slain": sum(len(r.get("killed", [])) for r in runs),
            "deathless_kills": sum(b["deathless"] for b in bosses.values()),
            "no_death_runs": sum(1 for r in completed if self.run_deaths(r) == 0),
            "dlc_deaths": dlc_deaths,
            "non_boss_deaths": non_boss,
            "nemesis": f"{nemesis[0]} ({nemesis[1]['deaths']})" if nemesis[1]["deaths"] else "—",
            "worst_boss": f"{worst[0]} ({worst[1]:.1f}/kill)" if worst[0] else "—",
            "most_one": f"{most_one[1]['worst']} ({most_one[0]})" if most_one[1]["worst"] else "—",
            "best_run": best_run or "—",
            "next_milestone": f"{next_ms} weapons" if remaining else "Challenge complete!",
        }


# ------------------------------------------------------------- run editor
class RunEditor(tk.Toplevel):
    def __init__(self, page, run=None, weapon=None):
        super().__init__(page)
        self.page = page
        self.tracker = page.tracker
        self.run = run or {
            "id": uuid.uuid4().hex, "weapon": weapon or "", "date": dt.date.today().isoformat(),
            "time": "", "completed": False, "killed": [], "boss_deaths": {},
            "non_boss_deaths": 0, "notes": "",
        }
        self.title("Edit run" if run else "New run")
        self.configure(bg=theme.BG)
        self.geometry("620x780")
        self.transient(page.winfo_toplevel())
        self.grab_set()

        top = ttk.Frame(self, padding=12)
        top.pack(fill="x")
        top.columnconfigure(1, weight=1)
        top.columnconfigure(3, weight=1)

        ttk.Label(top, text="Weapon").grid(row=0, column=0, sticky="w")
        names = [w["name"] for w in self.tracker.weapons]
        self.weapon = tk.StringVar(value=self.run["weapon"])
        cb = ttk.Combobox(top, textvariable=self.weapon, values=names)
        cb.grid(row=0, column=1, columnspan=3, sticky="ew", padx=6, pady=3)

        ttk.Label(top, text="Date").grid(row=1, column=0, sticky="w")
        self.date = tk.StringVar(value=self.run["date"])
        ttk.Entry(top, textvariable=self.date, width=12).grid(row=1, column=1, sticky="w", padx=6, pady=3)
        ttk.Label(top, text="Time (h:mm:ss)").grid(row=1, column=2, sticky="e")
        self.time = tk.StringVar(value=self.run.get("time", ""))
        ttk.Entry(top, textvariable=self.time, width=10).grid(row=1, column=3, sticky="w", padx=6, pady=3)

        self.completed = tk.BooleanVar(value=self.run.get("completed", False))
        ttk.Checkbutton(top, text="Run completed (all bosses dead / credits rolled)",
                        variable=self.completed).grid(row=2, column=0, columnspan=4, sticky="w", pady=4)

        ttk.Label(top, text="Non-boss deaths").grid(row=3, column=0, sticky="w")
        self.non_boss = tk.IntVar(value=self.run.get("non_boss_deaths", 0))
        self._counter(top, self.non_boss).grid(row=3, column=1, sticky="w", padx=6)

        bar = ttk.Frame(self, padding=(12, 0))
        bar.pack(fill="x")
        ttk.Label(bar, text="Bosses", style="H2.TLabel").pack(side="left")
        ttk.Button(bar, text="Clear all", style="Small.TButton", command=lambda: self._mark_all(False)).pack(side="right")
        ttk.Button(bar, text="Mark all killed", style="Small.TButton", command=lambda: self._mark_all(True)).pack(side="right", padx=4)
        self.total_lbl = ttk.Label(bar, text="", style="Muted.TLabel")
        self.total_lbl.pack(side="right", padx=12)

        sf = ScrollFrame(self, bg=theme.PANEL)
        sf.pack(fill="both", expand=True, padx=12, pady=6)
        self.killed_vars, self.death_vars = {}, {}
        killed = set(self.run.get("killed", []))
        deaths = self.run.get("boss_deaths", {})
        for i, b in enumerate(self.tracker.bosses):
            name = b["name"]
            kv = tk.BooleanVar(value=name in killed)
            dv = tk.IntVar(value=deaths.get(name, 0))
            self.killed_vars[name], self.death_vars[name] = kv, dv
            row = ttk.Frame(sf.inner, style="Card.TFrame", padding=(8, 2))
            row.pack(fill="x")
            ttk.Checkbutton(row, variable=kv, style="TCheckbutton").pack(side="left")
            label = name + ("  [DLC]" if b.get("dlc") else "")
            ttk.Label(row, text=label, style="Card.TLabel", width=34).pack(side="left")
            ttk.Label(row, text=b.get("area", ""), style="CardMuted.TLabel", width=20).pack(side="left")
            self._counter(row, dv, card=True).pack(side="right")
            dv.trace_add("write", lambda *_: self._update_total())
        self.non_boss.trace_add("write", lambda *_: self._update_total())
        self._update_total()

        ttk.Label(self, text="Notes", padding=(12, 0)).pack(anchor="w")
        self.notes = tk.Text(self, height=3, bg=theme.PANEL2, fg=theme.FG, insertbackground=theme.FG, relief="flat")
        self.notes.insert("1.0", self.run.get("notes", ""))
        self.notes.pack(fill="x", padx=12)

        btns = ttk.Frame(self, padding=12)
        btns.pack(fill="x")
        ttk.Button(btns, text="Save", style="Accent.TButton", command=self._save).pack(side="right")
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right", padx=6)

    def _counter(self, parent, var, card=False):
        f = ttk.Frame(parent, style="Card.TFrame" if card else "TFrame")

        def bump(n):
            try:
                var.set(max(0, var.get() + n))
            except tk.TclError:
                var.set(0)
        ttk.Button(f, text="−", width=2, style="Small.TButton", command=lambda: bump(-1)).pack(side="left")
        ttk.Entry(f, textvariable=var, width=4, justify="center").pack(side="left", padx=2)
        ttk.Button(f, text="+", width=2, style="Small.TButton", command=lambda: bump(1)).pack(side="left")
        return f

    def _mark_all(self, value):
        for v in self.killed_vars.values():
            v.set(value)

    def _int(self, var):
        try:
            return max(0, int(var.get()))
        except (tk.TclError, ValueError):
            return 0

    def _update_total(self):
        total = sum(self._int(v) for v in self.death_vars.values()) + self._int(self.non_boss)
        self.total_lbl.configure(text=f"Deaths this run: {total}")

    def _save(self):
        weapon = self.weapon.get().strip()
        if not weapon:
            messagebox.showwarning("Missing weapon", "Pick the weapon for this run.", parent=self)
            return
        if weapon not in self.tracker.weapon_by_name:
            if not messagebox.askyesno("Unknown weapon",
                                       f"'{weapon}' is not in data/weapons.json. Save anyway?", parent=self):
                return
        if self.time.get().strip() and parse_time(self.time.get()) is None:
            messagebox.showwarning("Bad time", "Use h:mm:ss, e.g. 3:22:58", parent=self)
            return
        self.run.update({
            "weapon": weapon,
            "date": self.date.get().strip(),
            "time": self.time.get().strip(),
            "completed": self.completed.get(),
            "killed": [n for n, v in self.killed_vars.items() if v.get()],
            "boss_deaths": {n: self._int(v) for n, v in self.death_vars.items() if self._int(v)},
            "non_boss_deaths": self._int(self.non_boss),
            "notes": self.notes.get("1.0", "end").strip(),
        })
        self.tracker.upsert_run(self.run)
        self.page.refresh()
        self.destroy()


# ------------------------------------------------------------------- page
class Page(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=10)
        self.app = app
        self.tracker = Tracker()

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True)
        self.dash = ttk.Frame(nb, padding=12)
        self.log = ttk.Frame(nb, padding=12)
        self.wep = ttk.Frame(nb, padding=12)
        self.boss = ttk.Frame(nb, padding=12)
        nb.add(self.dash, text="Dashboard")
        nb.add(self.log, text="Run Log")
        nb.add(self.wep, text="Weapons")
        nb.add(self.boss, text="Boss Mastery")

        self._build_dashboard()
        self._build_log()
        self._build_weapons()
        self._build_bosses()
        self.refresh()

    # dashboard -------------------------------------------------------
    def _build_dashboard(self):
        f = self.dash
        ttk.Label(f, text="DARK SOULS: ALL WEAPONS / ALL BOSSES", style="H2.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(f, text="One run log. One source of truth. Every death remembers where it happened.",
                  style="Muted.TLabel").grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 10))
        for c in range(3):
            f.columnconfigure(c, weight=1, uniform="dash")

        self.c_status = StatCard(f, "CHALLENGE STATUS")
        for k in ("Weapons completed", "Weapons remaining", "Overall completion", "Completed runs",
                  "Total deaths", "Average finish time", "Est. hours remaining"):
            self.c_status.row(k, big=k in ("Overall completion",))
        self.c_status.grid(row=2, column=0, sticky="nsew", padx=(0, 8), pady=4)

        # roulette
        r = ttk.Frame(f, style="Card.TFrame", padding=12)
        r.grid(row=2, column=1, sticky="nsew", padx=8, pady=4)
        r.columnconfigure(1, weight=1)
        ttk.Label(r, text="NEXT RUN: ROULETTE", style="CardH.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        self.r_weapon = ttk.Label(r, text="—", style="CardEmber.TLabel")
        self.r_weapon.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 6))
        self.r_rows = {}
        for i, k in enumerate(("Class", "Upgrade material", "DLC weapon?", "Previous PB"), start=2):
            ttk.Label(r, text=k, style="CardMuted.TLabel").grid(row=i, column=0, sticky="w", pady=2)
            v = ttk.Label(r, text="—", style="Card.TLabel")
            v.grid(row=i, column=1, sticky="e")
            self.r_rows[k] = v
        seed_row = ttk.Frame(r, style="Card.TFrame")
        seed_row.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Label(seed_row, text="Reroll seed", style="CardMuted.TLabel").pack(side="left")
        self.seed = tk.IntVar(value=self.tracker.state.get("seed", 1))
        sp = ttk.Spinbox(seed_row, from_=0, to=999999, textvariable=self.seed, width=8, command=self._seed_changed)
        sp.pack(side="left", padx=6)
        sp.bind("<Return>", lambda e: self._seed_changed())
        sp.bind("<FocusOut>", lambda e: self._seed_changed())
        ttk.Button(seed_row, text="🎲 Reroll", command=self._reroll).pack(side="left")
        ttk.Button(r, text="Start run with this weapon", style="Accent.TButton",
                   command=self._start_roulette_run).grid(row=8, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        self.c_char = StatCard(f, "CHARACTER SHEET")
        for k in ("Weapons slain", "Bosses slain", "Deaths", "Best run", "Nemesis", "DLC deaths", "Next milestone"):
            self.c_char.row(k, ember=k == "Nemesis")
        self.c_char.grid(row=2, column=2, sticky="nsew", padx=(8, 0), pady=4)

        self.c_runs = StatCard(f, "RUN TOTALS")
        for k in ("Runs logged", "Completed runs", "Bosses slain", "Completed no-death runs", "Non-boss deaths"):
            self.c_runs.row(k)
        self.c_runs.grid(row=3, column=0, sticky="nsew", padx=(0, 8), pady=8)

        self.c_boss = StatCard(f, "BOSS SNAPSHOT")
        for k in ("Worst boss (deaths/kill)", "Most deaths to one boss in a run", "Deathless boss kills", "DLC boss deaths"):
            self.c_boss.row(k)
        self.c_boss.grid(row=3, column=1, sticky="nsew", padx=8, pady=8)

        prog = ttk.Frame(f, style="Card.TFrame", padding=12)
        prog.grid(row=3, column=2, sticky="nsew", padx=(8, 0), pady=8)
        ttk.Label(prog, text="PROGRESS BY CLASS", style="CardH.TLabel").pack(anchor="w", pady=(0, 6))
        self.class_canvas = tk.Canvas(prog, bg=theme.PANEL, highlightthickness=0, height=200)
        self.class_canvas.pack(fill="both", expand=True)
        self.class_canvas.bind("<Configure>", lambda e: self._draw_class_progress())

        self.progress_canvas = tk.Canvas(f, bg=theme.BG, highlightthickness=0, height=28)
        self.progress_canvas.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(6, 0))
        self.progress_canvas.bind("<Configure>", lambda e: self._draw_progress())

    def _draw_progress(self):
        c = self.progress_canvas
        c.delete("all")
        w, h = c.winfo_width(), 22
        s = self._stats
        frac = s["weapons_done"] / s["weapons_total"] if s["weapons_total"] else 0
        c.create_rectangle(0, 3, w, h + 3, fill=theme.PANEL2, outline="")
        c.create_rectangle(0, 3, w * frac, h + 3, fill=theme.ACCENT, outline="")
        c.create_text(w / 2, h / 2 + 3, fill=theme.FG, font=theme.FONT_BOLD,
                      text=f"{s['weapons_done']} / {s['weapons_total']} weapons  ·  {s['completion']:.1f}%")

    def _draw_class_progress(self):
        c = self.class_canvas
        c.delete("all")
        done = self.tracker.completed_weapons()
        totals = {}
        for w in self.tracker.active_weapons():
            t = totals.setdefault(w["class"], [0, 0])
            t[1] += 1
            t[0] += w["name"] in done
        width = max(c.winfo_width(), 200)
        rows = list(totals.items())
        c.configure(height=max(200, len(rows) * 15))
        label_w, bar_x = 120, 125
        for i, (cls, (d, t)) in enumerate(rows):
            y = i * 15 + 2
            c.create_text(label_w, y + 6, text=cls, anchor="e", fill=theme.MUTED, font=("Segoe UI", 8))
            bw = width - bar_x - 40
            c.create_rectangle(bar_x, y + 2, bar_x + bw, y + 11, fill=theme.PANEL2, outline="")
            if d:
                c.create_rectangle(bar_x, y + 2, bar_x + bw * d / t, y + 11,
                                   fill=theme.GOOD if d == t else theme.ACCENT, outline="")
            c.create_text(width - 2, y + 6, text=f"{d}/{t}", anchor="e", fill=theme.FG, font=("Segoe UI", 8))

    def _seed_changed(self):
        try:
            self.tracker.state["seed"] = int(self.seed.get())
        except (tk.TclError, ValueError):
            return
        self.tracker.save()
        self._refresh_roulette()

    def _reroll(self):
        self.seed.set(random.randint(0, 999999))
        self._seed_changed()

    def _refresh_roulette(self):
        w = self.tracker.roulette()
        if not w:
            self.r_weapon.configure(text="Every weapon done!")
            for v in self.r_rows.values():
                v.configure(text="—")
            return
        self.r_weapon.configure(text=w["name"])
        self.r_rows["Class"].configure(text=w["class"])
        self.r_rows["Upgrade material"].configure(text=w["material"])
        self.r_rows["DLC weapon?"].configure(text="Yes" if w.get("dlc") else "No")
        self.r_rows["Previous PB"].configure(text=fmt_time(self.tracker.best_time(w["name"])))

    def _start_roulette_run(self):
        w = self.tracker.roulette()
        if w:
            RunEditor(self, weapon=w["name"])

    # run log ---------------------------------------------------------
    def _build_log(self):
        bar = ttk.Frame(self.log)
        bar.pack(fill="x", pady=(0, 8))
        ttk.Button(bar, text="+ New run", style="Accent.TButton", command=lambda: RunEditor(self)).pack(side="left")
        ttk.Button(bar, text="Edit", command=self._edit_selected).pack(side="left", padx=6)
        ttk.Button(bar, text="Delete", command=self._delete_selected).pack(side="left")
        ttk.Button(bar, text="Export CSV", command=self._export_csv).pack(side="right")
        ttk.Label(bar, text="Double-click a run to edit it.", style="Muted.TLabel").pack(side="left", padx=12)
        cols = ("Date", "Weapon", "Class", "Status", "Time", "Bosses", "Boss deaths", "Other deaths", "Total deaths", "Notes")
        frame, self.log_tree = tree_with_scroll(self.log, cols, widths={
            "Date": 95, "Weapon": 190, "Class": 120, "Status": 95, "Time": 80, "Bosses": 70,
            "Boss deaths": 85, "Other deaths": 85, "Total deaths": 85, "Notes": 260}, height=22,
            anchors={"Weapon": "w", "Notes": "w"})
        frame.pack(fill="both", expand=True)
        self.log_tree.bind("<Double-1>", lambda e: self._edit_selected())

    def _selected_run(self):
        sel = self.log_tree.selection()
        if not sel:
            return None
        return next((r for r in self.tracker.runs if r["id"] == sel[0]), None)

    def _edit_selected(self):
        run = self._selected_run()
        if run:
            RunEditor(self, run=dict(run))

    def _delete_selected(self):
        run = self._selected_run()
        if run and messagebox.askyesno("Delete run", f"Delete the {run['weapon']} run from {run['date']}?"):
            self.tracker.delete_run(run["id"])
            self.refresh()

    def _export_csv(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")],
                                            initialfile="ds_run_log.csv")
        if not path:
            return
        boss_names = [b["name"] for b in self.tracker.bosses]
        with open(path, "w", newline="", encoding="utf-8") as f:
            wr = csv.writer(f)
            wr.writerow(["Date", "Weapon", "Completed", "Time", "Non-boss deaths", "Notes"]
                        + [f"{b} deaths" for b in boss_names] + [f"{b} killed" for b in boss_names])
            for r in self.tracker.runs:
                d = r.get("boss_deaths", {})
                k = set(r.get("killed", []))
                wr.writerow([r["date"], r["weapon"], r.get("completed"), r.get("time", ""),
                             r.get("non_boss_deaths", 0), r.get("notes", "")]
                            + [d.get(b, 0) for b in boss_names] + [b in k for b in boss_names])
        messagebox.showinfo("Exported", f"Saved {len(self.tracker.runs)} runs to\n{path}")

    # weapons ---------------------------------------------------------
    def _build_weapons(self):
        bar = ttk.Frame(self.wep)
        bar.pack(fill="x", pady=(0, 8))
        ttk.Label(bar, text="Show").pack(side="left")
        self.w_filter = tk.StringVar(value="All")
        cb = ttk.Combobox(bar, textvariable=self.w_filter, state="readonly", width=12,
                          values=["All", "Remaining", "Completed", "Excluded"])
        cb.pack(side="left", padx=6)
        cb.bind("<<ComboboxSelected>>", lambda e: self._refresh_weapons())
        ttk.Label(bar, text="Class").pack(side="left", padx=(10, 0))
        self.w_class = tk.StringVar(value="All")
        classes = ["All"] + sorted({w["class"] for w in self.tracker.weapons})
        cb2 = ttk.Combobox(bar, textvariable=self.w_class, state="readonly", width=18, values=classes)
        cb2.pack(side="left", padx=6)
        cb2.bind("<<ComboboxSelected>>", lambda e: self._refresh_weapons())
        ttk.Label(bar, text="Search").pack(side="left", padx=(10, 0))
        self.w_search = tk.StringVar()
        self.w_search.trace_add("write", lambda *_: self._refresh_weapons())
        ttk.Entry(bar, textvariable=self.w_search, width=20).pack(side="left", padx=6)

        ttk.Button(bar, text="Start run with selected", style="Accent.TButton",
                   command=self._run_selected_weapon).pack(side="right")
        ttk.Button(bar, text="Include / exclude", command=self._toggle_weapon).pack(side="right", padx=6)

        cols = ("Weapon", "Class", "Upgrade material", "DLC", "Status", "Best time", "Attempts", "Deaths")
        frame, self.w_tree = tree_with_scroll(self.wep, cols, widths={"Weapon": 240, "Class": 140, "Upgrade material": 150}, height=22)
        frame.pack(fill="both", expand=True)
        self.w_tree.bind("<Double-1>", lambda e: self._run_selected_weapon())
        ttk.Label(self.wep, style="Muted.TLabel",
                  text="Excluded weapons don't count toward the challenge or the roulette. "
                       "Edit data/weapons.json to change the list.").pack(anchor="w", pady=(6, 0))

    def _toggle_weapon(self):
        for item in self.w_tree.selection():
            self.tracker.toggle_excluded(item)
        self.refresh()

    def _run_selected_weapon(self):
        sel = self.w_tree.selection()
        if sel:
            RunEditor(self, weapon=sel[0])

    def _refresh_weapons(self):
        t = self.w_tree
        t.delete(*t.get_children())
        done, ex = self.tracker.completed_weapons(), self.tracker.excluded
        attempts, deaths = {}, {}
        for r in self.tracker.runs:
            attempts[r["weapon"]] = attempts.get(r["weapon"], 0) + 1
            deaths[r["weapon"]] = deaths.get(r["weapon"], 0) + self.tracker.run_deaths(r)
        flt, cls, q = self.w_filter.get(), self.w_class.get(), self.w_search.get().lower()
        for i, w in enumerate(self.tracker.weapons):
            n = w["name"]
            status = "Excluded" if n in ex else ("Completed" if n in done else "Remaining")
            if flt != "All" and status != flt:
                continue
            if cls != "All" and w["class"] != cls:
                continue
            if q and q not in n.lower():
                continue
            tag = {"Completed": "good", "Excluded": "muted"}.get(status, "")
            t.insert("", "end", iid=n, tags=(tag,), values=(
                n, w["class"], w["material"], "Yes" if w.get("dlc") else "", status,
                fmt_time(self.tracker.best_time(n)), attempts.get(n, 0), deaths.get(n, 0)))

    # bosses ----------------------------------------------------------
    def _build_bosses(self):
        cols = ("Boss", "Area", "DLC", "Kills", "Deaths", "Deathless kills", "Deaths / kill", "Worst run", "Mastery")
        frame, self.b_tree = tree_with_scroll(self.boss, cols, widths={"Boss": 230, "Area": 170}, height=26,
                                              anchors={"Area": "w"})
        frame.pack(fill="both", expand=True)
        ttk.Label(self.boss, style="Muted.TLabel",
                  text="Mastery = share of kills done deathless. Click a header to sort.").pack(anchor="w", pady=(6, 0))

    def _refresh_bosses(self):
        t = self.b_tree
        t.delete(*t.get_children())
        table = self.tracker.boss_table()
        areas = {b["name"]: b for b in self.tracker.bosses}
        for name, s in table.items():
            b = areas.get(name, {})
            ratio = s["deaths"] / s["kills"] if s["kills"] else None
            mastery = s["deathless"] / s["kills"] * 100 if s["kills"] else None
            tag = "bad" if ratio is not None and ratio >= 2 else ("good" if mastery == 100 else "")
            t.insert("", "end", tags=(tag,), values=(
                name, b.get("area", ""), "Yes" if b.get("dlc") else "", s["kills"], s["deaths"], s["deathless"],
                f"{ratio:.2f}" if ratio is not None else "—", s["worst"],
                f"{mastery:.0f}%" if mastery is not None else "—"))

    # ---------------------------------------------------------------
    def refresh(self):
        s = self._stats = self.tracker.stats()
        cs = self.c_status
        cs.set("Weapons completed", s["weapons_done"])
        cs.set("Weapons remaining", s["weapons_left"])
        cs.set("Overall completion", f"{s['completion']:.1f}%")
        cs.set("Completed runs", s["runs_completed"])
        cs.set("Total deaths", s["deaths"])
        cs.set("Average finish time", fmt_time(s["avg_time"]))
        cs.set("Est. hours remaining", f"{s['est_hours']:.1f}" if s["est_hours"] is not None else "—")
        cc = self.c_char
        cc.set("Weapons slain", s["weapons_done"])
        cc.set("Bosses slain", s["bosses_slain"])
        cc.set("Deaths", s["deaths"])
        cc.set("Best run", s["best_run"])
        cc.set("Nemesis", s["nemesis"])
        cc.set("DLC deaths", s["dlc_deaths"])
        cc.set("Next milestone", s["next_milestone"])
        cr = self.c_runs
        cr.set("Runs logged", s["runs_total"])
        cr.set("Completed runs", s["runs_completed"])
        cr.set("Bosses slain", s["bosses_slain"])
        cr.set("Completed no-death runs", s["no_death_runs"])
        cr.set("Non-boss deaths", s["non_boss_deaths"])
        cb = self.c_boss
        cb.set("Worst boss (deaths/kill)", s["worst_boss"])
        cb.set("Most deaths to one boss in a run", s["most_one"])
        cb.set("Deathless boss kills", s["deathless_kills"])
        cb.set("DLC boss deaths", s["dlc_deaths"])
        self._refresh_roulette()
        self._draw_progress()
        self._draw_class_progress()

        t = self.log_tree
        t.delete(*t.get_children())
        for i, r in enumerate(sorted(self.tracker.runs, key=lambda r: r.get("date", ""), reverse=True)):
            w = self.tracker.weapon_by_name.get(r["weapon"], {})
            bd = sum(r.get("boss_deaths", {}).values())
            status = "Completed" if r.get("completed") else "In progress"
            t.insert("", "end", iid=r["id"], tags=("good" if r.get("completed") else "",), values=(
                r.get("date", ""), r["weapon"], w.get("class", "?"), status, r.get("time") or "—",
                f"{len(r.get('killed', []))}/{len(self.tracker.bosses)}", bd, r.get("non_boss_deaths", 0),
                bd + r.get("non_boss_deaths", 0), r.get("notes", "").replace("\n", " ")))
        self._refresh_weapons()
        self._refresh_bosses()
