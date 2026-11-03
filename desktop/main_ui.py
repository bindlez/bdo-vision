"""Compact native timer. Detailed workspaces open only when requested."""
import tkinter as tk
from tkinter import ttk
from ui_scroll import enable_page_wheel


def build_main_ui(app):
    c = app.colors
    shell = tk.Frame(app.root, bg=c['bg'])
    shell.pack(fill='both', expand=True)
    canvas = tk.Canvas(shell, bg=c['bg'], highlightthickness=0)
    scroll = ttk.Scrollbar(shell, orient='vertical', command=canvas.yview)
    canvas.configure(yscrollcommand=scroll.set)
    scroll.pack(side='right', fill='y')
    canvas.pack(side='left', fill='both', expand=True)
    main = tk.Frame(canvas, bg=c['bg'], padx=12, pady=10)
    content = canvas.create_window(0, 0, window=main, anchor='nw')
    main.bind('<Configure>', lambda event: canvas.configure(scrollregion=canvas.bbox('all')))
    canvas.bind('<Configure>', lambda event: canvas.itemconfigure(content, width=event.width))
    enable_page_wheel(canvas)

    header = tk.Frame(main, bg=c['bg'])
    header.pack(fill='x')
    tk.Label(header, text='✦ BDO VISION', bg=c['bg'], fg=c['text'],
             font=('Segoe UI Semibold', 13)).pack(side='left')
    app.text_button(header, 'SETTINGS', app.open_settings).pack(side='right')

    hero = tk.Frame(main, bg=c['panel'], padx=12, pady=10,
                    highlightbackground=c['line'], highlightthickness=1)
    hero.pack(fill='x', pady=(10, 8))
    cap = tk.Frame(hero, bg=c['panel'])
    cap.pack(fill='x')
    tk.Label(cap, text='CURRENT TOOL', bg=c['panel'], fg=c['muted'],
             font=('Segoe UI Semibold', 8)).pack(side='left')
    app.state_label = tk.Label(cap, textvariable=app.timer_state, bg=c['panel2'],
                               fg=c['good'], font=('Segoe UI Semibold', 8), padx=5, pady=2)
    app.state_label.pack(side='right')
    tk.Label(hero, textvariable=app.durability_display, bg=c['panel'], fg=c['text'],
             font=('Segoe UI Semibold', 27)).pack(anchor='w', pady=(2, 4))
    app.bar = ttk.Progressbar(hero, maximum=100, style='Vision.Horizontal.TProgressbar')
    app.bar.pack(fill='x', pady=(0, 7))
    tk.Label(hero, textvariable=app.tool_title, bg=c['panel'], fg=c['bright'],
             font=('Segoe UI Semibold', 9), wraplength=300, justify='left').pack(anchor='w')
    tk.Label(hero, textvariable=app.tool_preview, bg=c['panel'], fg=c['secondary'],
             font=('Segoe UI', 9), wraplength=300, justify='left').pack(anchor='w', pady=(3, 6))
    metrics = tk.Frame(hero, bg=c['panel'])
    metrics.pack(fill='x')
    for title, value in [('REMAINING', app.count), ('WARNING IN', app.alarm_in)]:
        col = tk.Frame(metrics, bg=c['panel'])
        col.pack(side='left', fill='x', expand=True)
        tk.Label(col, text=title, bg=c['panel'], fg=c['muted'], font=('Segoe UI', 8)).pack(anchor='w')
        tk.Label(col, textvariable=value, bg=c['panel'], fg=c['bright'],
                 font=('Cascadia Mono', 16)).pack(anchor='w')

    actions = tk.Frame(main, bg=c['bg'])
    actions.pack(fill='x')
    actions.columnconfigure((0, 1), weight=1, uniform='actions')
    app.scan_button = app.action(actions, 'SCAN & TRACK', app.read_ocr, primary=True)
    app.send_button = app.action(actions, 'SEND NOW', app.send_to_planner)
    app.tray_button = app.action(actions, 'SEND + TRAY', app.send_and_tray)
    planner = app.action(actions, 'PLANNER', app.open_planner, flat=True)
    for index, button in enumerate((app.scan_button, app.send_button, app.tray_button, planner)):
        button.grid(row=index // 2, column=index % 2, sticky='ew', padx=2, pady=3)
    ttk.Checkbutton(main, text='Lite Use · initial scan, then timer only', variable=app.lite_use,
                    command=app.change_lite_use, style='Vision.TCheckbutton').pack(anchor='w', pady=6)

    nav = tk.Frame(main, bg=c['bg'])
    nav.pack(fill='x')
    for index, (label, action) in enumerate([
        ('HOME', lambda: app.open_activity('home')),
        ('CRAFT', lambda: app.open_activity('craft')),
        ('GRIND', lambda: app.open_activity('grind')),
    ]):
        nav.columnconfigure(index, weight=1, uniform='navigation')
        app.action(nav, label, action, flat=True).grid(row=0, column=index, sticky='ew', padx=2)

    details = tk.Frame(main, bg=c['bg'])
    def toggle_details():
        if details.winfo_manager():
            details.pack_forget()
            more.configure(text='MORE CONTROLS ▾')
        else:
            details.pack(fill='x', after=more, pady=5)
            more.configure(text='FEWER CONTROLS ▴')
    more = app.text_button(main, 'MORE CONTROLS ▾', toggle_details)
    more.pack(anchor='w', pady=(5, 0))
    app.auto_toggle = app.text_button(details, '', app.toggle_auto_scan)
    app.auto_toggle.grid(row=0, column=0, sticky='w')
    app.refresh_auto_scan_label()
    for index, (label, action) in enumerate([
        ('TOOL OCR DEBUG', app.tool_debug.open), ('QUESTS', app.open_guild_quest),
        ('SILVER VALUE', lambda: app.open_activity('silver')),
        ('TOOL DETAILS', app.open_tools),
        ('GEAR', app.open_gear_planner), ('FAIRY CODEX', app.open_fairy),
        ('CP INFO', lambda: app.open_activity('cp')), ('IMPERIAL', lambda: app.open_activity('imperial')),
        ('RESTORE BDO', app.restore_game), ('RESTORE FROM TRAY', app.super_restore_game),
        ('TEST LINK', app.test_connection),
    ], start=1):
        app.text_button(details, label, action).grid(row=index // 2, column=index % 2, sticky='w', padx=3, pady=2)
    for value in (app.auto_health, app.scan_health, app.tool_metrics):
        tk.Label(details, textvariable=value, bg=c['bg'], fg=c['muted'],
                 font=('Segoe UI', 9), wraplength=315, justify='left').grid(column=0, columnspan=2, sticky='w', pady=2)

    app.connection_label = tk.Label(main, textvariable=app.connection, bg=c['bg'], fg=c['good'],
                                    font=('Segoe UI', 8), wraplength=315, justify='left')
    app.connection_label.pack(anchor='w', pady=(5, 2))
    tk.Label(main, textvariable=app.status, bg=c['bg'], fg=c['secondary'], font=('Segoe UI', 9),
             wraplength=315, justify='left').pack(anchor='w')
