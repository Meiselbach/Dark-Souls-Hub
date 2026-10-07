"""Dark Souls Companion: a hub for DS1 / DSR tools and resources.

Run:  python main.py
Tabs are loaded automatically from the modules/ folder.
"""
import importlib
import pkgutil
import sys
import traceback
from pathlib import Path

import tkinter as tk
from tkinter import ttk

sys.path.insert(0, str(Path(__file__).resolve().parent))

from core import theme  # noqa: E402
import modules  # noqa: E402


def discover_modules():
    found = []
    for info in pkgutil.iter_modules(modules.__path__):
        if info.name.startswith("_"):
            continue
        try:
            mod = importlib.import_module(f"modules.{info.name}")
        except Exception:
            found.append((999, info.name, None, traceback.format_exc()))
            continue
        if hasattr(mod, "Page") and hasattr(mod, "PAGE_TITLE"):
            found.append((getattr(mod, "PAGE_ORDER", 100), mod.PAGE_TITLE, mod, None))
    return sorted(found, key=lambda m: (m[0], m[1]))


def enable_hidpi():
    """Sharp text on scaled Windows displays instead of blurry bitmap scaling."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass


class App(tk.Tk):
    def __init__(self):
        enable_hidpi()
        super().__init__()
        self.title("Dark Souls Companion")
        scale = self.winfo_fpixels("1i") / 96
        w, h = int(1320 * scale), int(860 * scale)
        w, h = min(w, self.winfo_screenwidth() - 40), min(h, self.winfo_screenheight() - 80)
        self.geometry(f"{w}x{h}")
        self.minsize(int(1000 * scale), int(640 * scale))
        theme.apply(self)

        header = ttk.Frame(self, padding=(16, 12, 16, 4))
        header.pack(fill="x")
        ttk.Label(header, text="DARK SOULS COMPANION", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="   Prepare to die. Then log it.", style="Muted.TLabel").pack(side="left", pady=(8, 0))

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=12, pady=(4, 12))
        self.pages = {}

        for _, title, mod, error in discover_modules():
            if mod is not None:
                try:
                    page = mod.Page(self.nb, self)
                except Exception:
                    error = traceback.format_exc()
            if error:
                page = self._error_page(error)
            self.nb.add(page, text=f"  {title}  ")
            self.pages[title] = page

        self.nb.bind("<<NotebookTabChanged>>", self._on_tab)

    def _error_page(self, error):
        f = ttk.Frame(self.nb, padding=20)
        ttk.Label(f, text="This module failed to load", style="H2.TLabel").pack(anchor="w")
        txt = tk.Text(f, bg=theme.PANEL, fg=theme.BAD, relief="flat", height=20)
        txt.insert("1.0", error)
        txt.configure(state="disabled")
        txt.pack(fill="both", expand=True, pady=10)
        return f

    def _on_tab(self, _event):
        page = self.nametowidget(self.nb.select())
        if hasattr(page, "on_show"):
            page.on_show()

    def show_page(self, title):
        """Let one module jump to another, e.g. app.show_page("Level Calculator")."""
        page = self.pages.get(title)
        if page is not None:
            self.nb.select(page)


if __name__ == "__main__":
    App().mainloop()
