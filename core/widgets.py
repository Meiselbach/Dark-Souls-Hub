"""Small reusable widgets."""
import tkinter as tk
from tkinter import ttk

from core import theme


class ScrollFrame(ttk.Frame):
    """A vertically scrollable frame. Put children into `.inner`."""

    def __init__(self, parent, bg=theme.BG, **kw):
        super().__init__(parent, **kw)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas, style="Card.TFrame" if bg == theme.PANEL else "TFrame")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.vsb.pack(side="right", fill="y")
        # only scroll while the pointer is over this widget
        self.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._wheel))
        self.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

    def _wheel(self, event):
        if self.canvas.yview() != (0.0, 1.0):
            self.canvas.yview_scroll(int(-event.delta / 120), "units")


def sort_key(value: str):
    s = str(value).replace("%", "").replace(",", "").replace("*", "").strip()
    try:
        return (0, float(s))
    except ValueError:
        # h:mm:ss times sort numerically too
        if s.count(":") == 2:
            try:
                h, m, sec = (int(x) for x in s.split(":"))
                return (0, h * 3600 + m * 60 + sec)
            except ValueError:
                pass
        return (1, s.lower())


def make_sortable(tree: ttk.Treeview) -> None:
    """Click a column heading to sort; click again to reverse."""

    def sort(col, reverse):
        rows = [(tree.set(k, col), k) for k in tree.get_children("")]
        rows.sort(key=lambda r: sort_key(r[0]), reverse=reverse)
        for i, (_, k) in enumerate(rows):
            tree.move(k, "", i)
        tree.heading(col, command=lambda: sort(col, not reverse))

    for col in tree["columns"]:
        tree.heading(col, command=lambda c=col: sort(c, False))


def tree_with_scroll(parent, columns, widths=None, height=15, anchors=None):
    """Treeview + scrollbar packed in a frame. Returns (frame, tree)."""
    frame = ttk.Frame(parent)
    tree = ttk.Treeview(frame, columns=columns, show="headings", height=height)
    vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=vsb.set)
    for i, c in enumerate(columns):
        tree.heading(c, text=c)
        w = (widths or {}).get(c, 110)
        anchor = (anchors or {}).get(c, "w" if i == 0 else "center")
        tree.column(c, width=w, anchor=anchor, stretch=True)
    tree.tag_configure("odd", background=theme.PANEL)
    tree.tag_configure("even", background="#221f1a")
    tree.tag_configure("good", foreground=theme.GOOD)
    tree.tag_configure("bad", foreground=theme.BAD)
    tree.tag_configure("muted", foreground=theme.MUTED)
    tree.tag_configure("accent", foreground=theme.ACCENT)
    tree.pack(side="left", fill="both", expand=True)
    vsb.pack(side="right", fill="y")
    make_sortable(tree)
    return frame, tree


class StatCard(ttk.Frame):
    """A titled card with label/value rows."""

    def __init__(self, parent, title):
        super().__init__(parent, style="Card.TFrame", padding=12)
        ttk.Label(self, text=title, style="CardH.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        self.columnconfigure(1, weight=1)
        self._rows = {}

    def row(self, label, big=False, ember=False):
        r = len(self._rows) + 1
        ttk.Label(self, text=label, style="CardMuted.TLabel").grid(row=r, column=0, sticky="w", pady=2, padx=(0, 12))
        style = "CardEmber.TLabel" if ember else ("CardBig.TLabel" if big else "Card.TLabel")
        val = ttk.Label(self, text="—", style=style)
        val.grid(row=r, column=1, sticky="e", pady=2)
        self._rows[label] = val
        return val

    def set(self, label, value):
        self._rows[label].configure(text=str(value))
