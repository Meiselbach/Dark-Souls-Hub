"""Resource links. Stored in data/links.json; add/remove from the UI or edit the file."""
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox

from core import theme
from core.storage import DATA_DIR, load_json, save_json
from core.widgets import ScrollFrame

PAGE_TITLE = "Resources"
PAGE_ORDER = 90

LINKS_FILE = DATA_DIR / "links.json"


class LinkDialog(tk.Toplevel):
    def __init__(self, page, categories):
        super().__init__(page)
        self.page = page
        self.title("Add resource")
        self.configure(bg=theme.BG)
        self.transient(page.winfo_toplevel())
        self.grab_set()
        f = ttk.Frame(self, padding=16)
        f.pack(fill="both", expand=True)
        self.vars = {}
        for i, (key, label) in enumerate((("title", "Title"), ("url", "URL"), ("category", "Category"),
                                          ("description", "Description"))):
            ttk.Label(f, text=label).grid(row=i, column=0, sticky="w", pady=4)
            v = tk.StringVar()
            if key == "category":
                w = ttk.Combobox(f, textvariable=v, values=categories, width=48)
            else:
                w = ttk.Entry(f, textvariable=v, width=50)
            w.grid(row=i, column=1, sticky="ew", padx=8, pady=4)
            self.vars[key] = v
        b = ttk.Frame(f)
        b.grid(row=5, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(b, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(b, text="Add", style="Accent.TButton", command=self._ok).pack(side="right", padx=6)

    def _ok(self):
        link = {k: v.get().strip() for k, v in self.vars.items()}
        if not link["title"] or not link["url"]:
            messagebox.showwarning("Missing info", "Title and URL are required.", parent=self)
            return
        if not link["url"].startswith(("http://", "https://")):
            link["url"] = "https://" + link["url"]
        link["category"] = link["category"] or "Other"
        self.page.links.append(link)
        self.page.save()
        self.destroy()


class Page(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=16)
        self.app = app
        self.links = load_json(LINKS_FILE, [])
        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 10))
        ttk.Label(top, text="Resources", style="H2.TLabel").pack(side="left")
        ttk.Label(top, text="   Links open in your browser. Tools marked BUILT IN also have their own tab.",
                  style="Muted.TLabel").pack(side="left")
        ttk.Button(top, text="+ Add resource", style="Accent.TButton",
                   command=lambda: LinkDialog(self, self._categories())).pack(side="right")
        self.sf = ScrollFrame(self)
        self.sf.pack(fill="both", expand=True)
        self.render()

    def _categories(self):
        return sorted({l.get("category", "Other") for l in self.links})

    def save(self):
        save_json(LINKS_FILE, self.links)
        self.render()

    def remove(self, link):
        if messagebox.askyesno("Remove", f"Remove '{link['title']}'?"):
            self.links.remove(link)
            self.save()

    def render(self):
        g = self.sf.inner
        for w in g.winfo_children():
            w.destroy()
        g.columnconfigure(0, weight=1)
        g.columnconfigure(1, weight=1)
        row = 0
        for cat in self._categories():
            ttk.Label(g, text=cat.upper(), style="H2.TLabel").grid(row=row, column=0, columnspan=2, sticky="w", pady=(12, 4))
            row += 1
            items = [l for l in self.links if l.get("category", "Other") == cat]
            for i, link in enumerate(items):
                card = ttk.Frame(g, style="Card.TFrame", padding=12)
                card.grid(row=row + i // 2, column=i % 2, sticky="nsew", padx=4, pady=4)
                card.columnconfigure(0, weight=1)
                head = ttk.Frame(card, style="Card.TFrame")
                head.grid(row=0, column=0, columnspan=2, sticky="ew")
                ttk.Label(head, text=link["title"], style="CardH.TLabel").pack(side="left")
                if link.get("builtin"):
                    tk.Label(head, text=" BUILT IN ", bg=theme.TINT_GOOD, fg=theme.GOOD,
                             font=("Segoe UI", 8, "bold")).pack(side="left", padx=8)
                if link.get("description"):
                    ttk.Label(card, text=link["description"], style="Card.TLabel", wraplength=480,
                              justify="left").grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 2))
                url = link["url"]
                ttk.Label(card, text=url if len(url) < 70 else url[:67] + "...", style="CardMuted.TLabel"
                          ).grid(row=2, column=0, sticky="w")
                btns = ttk.Frame(card, style="Card.TFrame")
                btns.grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))
                ttk.Button(btns, text="Open ↗", command=lambda u=url: webbrowser.open(u)).pack(side="left")
                if link.get("builtin") and link["builtin"] in self.app.pages:
                    ttk.Button(btns, text="Go to tab", style="Accent.TButton",
                               command=lambda t=link["builtin"]: self.app.show_page(t)).pack(side="left", padx=6)
                ttk.Button(btns, text="Remove", style="Small.TButton",
                           command=lambda l=link: self.remove(l)).pack(side="right", padx=(20, 0))
            row += (len(items) + 1) // 2
