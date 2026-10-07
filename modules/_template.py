"""Template for a new tab.

1. Copy this file to modules/my_tool.py (no leading underscore).
2. Change PAGE_TITLE / PAGE_ORDER and build your UI in Page.__init__.
3. Restart the app. The tab appears automatically.

Useful helpers:
  core.storage: DATA_DIR, SAVE_DIR, load_json, save_json
  core.widgets: ScrollFrame, StatCard, tree_with_scroll (sortable table)
  core.theme:   colours (ACCENT, PANEL, GOOD, BAD, ...)
  app.show_page("Level Calculator") switches to another tab.
"""
from tkinter import ttk

PAGE_TITLE = "My Tool"
PAGE_ORDER = 50  # lower = further left


class Page(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=16)
        self.app = app
        ttk.Label(self, text=PAGE_TITLE, style="H2.TLabel").pack(anchor="w")
        ttk.Label(self, text="Build your tool here.").pack(anchor="w", pady=8)

    def on_show(self):
        """Optional: called whenever the tab is selected."""
