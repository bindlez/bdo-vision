"""Workspace launcher for the passive Vision overlay."""
import tkinter as tk
from game_overlay import geometry, work_area
from overlay_layout import tile


class DockPanels:
    """One attached native panel, with its controller and data left alive."""

    def __init__(self, app):
        self.app = app
        self.active = None
        self.window = None
        self.on_fold = None

    def fold(self):
        if self.window is not None and self.window.winfo_exists():
            if self.on_fold:
                self.on_fold()
            else:
                self.window.withdraw()
        self.active = self.window = self.on_fold = None

    def show(self, key, opener, *, toggle=False, on_fold=None, reuse=None):
        same = self.active == key and self.window is not None and self.window.winfo_exists()
        if same and toggle and self.window.state() == 'normal':
            self.fold()
            return
        if not same and self.window is not reuse:
            self.fold()
        window = opener()
        if window is None:
            return
        self.active, self.window, self.on_fold = key, window, on_fold
        if window is not self.app.root and on_fold is None:
            window.protocol('WM_DELETE_WINDOW', self.fold)
        self.retile()
        window.lift()

    def retile(self):
        hud = self.app.loot.grind.live.hud
        window = self.window
        if hud is None or window is None or not window.winfo_exists() or window.state() != 'normal':
            return
        if self.on_fold:
            self.app.loot.grind.live.craft_panel.retile()
            return
        width, height = window.winfo_width(), window.winfo_height()
        if min(width, height) <= 1:
            width, height = (380, 560) if window is self.app.root else (1000, 680)
        geometry(window, tile((width, height), work_area(hud.surface.window), hud.surface.rect))


def open_apps(app, anchor):
    if hasattr(anchor, "_apps_menu"):
        menu = anchor._apps_menu
    else:
        menu = anchor._apps_menu = build_apps(app, anchor)
    menu.tk_popup(anchor.winfo_rootx(), anchor.winfo_rooty() + anchor.winfo_height())


def build_apps(app, anchor):
    c = app.colors
    menu = tk.Menu(anchor, tearoff=False, bg=c['panel'], fg=c['text'],
                   activebackground=c['violet'], activeforeground=c['text'],
                   font=('Segoe UI', 10))
    menu.add_command(label='Live tracking', command=lambda: app.show_timer(toggle=True))
    menu.add_checkbutton(label='Detailed Craft Tracking', variable=app.detailed_craft, command=app.change_detailed_craft)
    menu.add_command(label='Scan tool now', command=app.read_ocr)
    menu.add_command(label='Tool reader status', command=app.open_tools)
    for label, section in [('Workshop','craft'), ('Grind','grind'),
                           ('Guild quests','quests'), ('CP Intelligence','cp'),
                           ('Imperial delivery','imperial'), ('Silver','silver'),
                           ('Saved sessions','sessions')]:
        menu.add_command(label=label, command=lambda target=section: app.open_activity(target,toggle=True))
    menu.add_separator()
    menu.add_command(label='Craft Planner', command=app.open_planner)
    menu.add_command(label='Market', command=lambda: app.open_planner('market'))
    menu.add_command(label='Screenshot Lab · Tier −1', command=app.open_heavy_tools)
    menu.add_command(label='Vision settings', command=app.open_settings)
    menu.add_separator()
    menu.add_command(label='Exit Vision', command=app.close)
    return menu
