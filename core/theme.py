"""Dark Souls flavoured ttk theme."""
import tkinter as tk
from tkinter import ttk

BG = "#141210"
PANEL = "#1e1b17"
PANEL2 = "#2a2520"
BORDER = "#3a332b"
FG = "#e6dccb"
MUTED = "#9a8f7e"
ACCENT = "#d9a441"
EMBER = "#e2703a"
GOOD = "#7fb069"
BAD = "#c8553d"
SELECT = "#4a3b22"

# heat-map tints (dark backgrounds that keep light text readable)
TINT_GOOD = "#2f4a2a"
TINT_OK = "#3d3a22"
TINT_BAD = "#4d2a22"
TINT_NONE = "#24211d"

FONT = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
SERIF = "Georgia"


def apply(root: tk.Tk) -> None:
    root.configure(bg=BG)
    s = ttk.Style(root)
    s.theme_use("clam")
    s.configure(".", background=BG, foreground=FG, fieldbackground=PANEL2,
                bordercolor=BORDER, lightcolor=PANEL, darkcolor=PANEL,
                troughcolor=PANEL, font=FONT, insertcolor=FG,
                selectbackground=SELECT, selectforeground=FG)

    s.configure("TFrame", background=BG)
    s.configure("Card.TFrame", background=PANEL)

    s.configure("TLabel", background=BG, foreground=FG)
    s.configure("Muted.TLabel", foreground=MUTED)
    s.configure("Title.TLabel", font=(SERIF, 20, "bold"), foreground=ACCENT)
    s.configure("H2.TLabel", font=(SERIF, 13, "bold"), foreground=ACCENT)
    s.configure("Card.TLabel", background=PANEL)
    s.configure("CardMuted.TLabel", background=PANEL, foreground=MUTED)
    s.configure("CardH.TLabel", background=PANEL, foreground=ACCENT, font=(SERIF, 11, "bold"))
    s.configure("CardBig.TLabel", background=PANEL, font=("Segoe UI", 15, "bold"))
    s.configure("CardEmber.TLabel", background=PANEL, foreground=EMBER, font=("Segoe UI", 15, "bold"))

    s.configure("TButton", background=PANEL2, foreground=FG, padding=(10, 5), borderwidth=1)
    s.map("TButton", background=[("active", BORDER), ("disabled", PANEL)],
          foreground=[("disabled", MUTED)])
    s.configure("Accent.TButton", background=ACCENT, foreground="#1a1410", font=FONT_BOLD)
    s.map("Accent.TButton", background=[("active", "#f0bd5a")])
    s.configure("Small.TButton", padding=(4, 1))

    s.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(0, 4, 0, 0))
    s.configure("TNotebook.Tab", background=PANEL, foreground=MUTED, padding=(14, 6), borderwidth=0)
    s.map("TNotebook.Tab", background=[("selected", PANEL2)], foreground=[("selected", ACCENT)])

    s.configure("Treeview", background=PANEL, fieldbackground=PANEL, foreground=FG,
                rowheight=int(24 * root.winfo_fpixels("1i") / 96), borderwidth=0)
    s.configure("Treeview.Heading", background=PANEL2, foreground=ACCENT, relief="flat",
                font=("Segoe UI", 9, "bold"))
    s.map("Treeview", background=[("selected", SELECT)], foreground=[("selected", FG)])
    s.map("Treeview.Heading", background=[("active", BORDER)])

    for w in ("TEntry", "TSpinbox", "TCombobox"):
        s.configure(w, fieldbackground=PANEL2, foreground=FG, arrowcolor=FG, background=PANEL2)
    s.map("TCombobox", fieldbackground=[("readonly", PANEL2)], foreground=[("readonly", FG)],
          selectbackground=[("readonly", PANEL2)], selectforeground=[("readonly", FG)])
    root.option_add("*TCombobox*Listbox.background", PANEL2)
    root.option_add("*TCombobox*Listbox.foreground", FG)
    root.option_add("*TCombobox*Listbox.selectBackground", SELECT)

    s.configure("TCheckbutton", background=BG, foreground=FG)
    s.map("TCheckbutton", background=[("active", BG)],
          indicatorcolor=[("selected", ACCENT), ("!selected", PANEL2)])
    s.configure("TRadiobutton", background=BG, foreground=FG)
    s.map("TRadiobutton", background=[("active", BG)],
          indicatorcolor=[("selected", ACCENT), ("!selected", PANEL2)])

    s.configure("TLabelframe", background=BG, bordercolor=BORDER)
    s.configure("TLabelframe.Label", background=BG, foreground=ACCENT, font=(SERIF, 11, "bold"))
    s.configure("Vertical.TScrollbar", background=PANEL2, troughcolor=BG, arrowcolor=FG, bordercolor=BG)
    s.configure("Horizontal.TScrollbar", background=PANEL2, troughcolor=BG, arrowcolor=FG, bordercolor=BG)
