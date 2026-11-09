"""Workspace launcher for the passive Vision overlay."""
import tkinter as tk


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
    menu.add_command(label='Craft timer', command=app.show_timer)
    for label, section in [('Workshop','craft'), ('Grind','grind'),
                           ('Guild quests','quests'), ('CP Intelligence','cp'),
                           ('Imperial delivery','imperial'), ('Silver','silver'),
                           ('Saved sessions','sessions')]:
        menu.add_command(label=label, command=lambda target=section: app.open_activity(target))
    menu.add_separator()
    menu.add_command(label='Browser planner', command=app.open_planner)
    menu.add_command(label='Vision settings', command=app.open_settings)
    return menu
