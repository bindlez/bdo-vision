"""Compact live dashboard, with settings reachable even when click-through is on."""
import tkinter as tk
from tkinter import ttk
from game_overlay import OverlaySurface, label, button, INK, PANEL, LINE, MUTED, VIOLET, TEAL, GOLD
from overlay_layout import preferences, compact_silver


class LiveHUD:
    def __init__(self, live):
        self.live = live;self.tracker = live.grind.tracker;self.app = self.tracker.app
        self.options = preferences(self.tracker.platform_preferences.get('overlay'))
        wide = self.options['density'] == 'Comfortable';self.width = 380 if wide else 320
        self.surface = OverlaySurface(self.app.root, 'Vision · Grind overlay', (self.width, 262 if wide else 246), self.options, self.save_position)
        body = self.surface.body
        rail = tk.Frame(body, bg=VIOLET, height=2);rail.pack(fill='x')
        head = tk.Frame(body, bg=INK);head.pack(fill='x', padx=12, pady=(3, 2))
        brand = label(head, '◇  VISION / GRIND', 9, VIOLET);brand.pack(side='left')
        button(head, '×', self.close).pack(side='right')
        button(head, 'SETUP', self.live.settings).pack(side='right')
        self.surface.draggable(head, brand)
        self.surface.feedback = lambda text:brand.configure(text=text)
        self.status = label(body, 'READY · Start a grind run', 9, TEAL, anchor='w');self.status.pack(fill='x', padx=12)
        metrics = tk.Frame(body, bg=INK);metrics.pack(fill='x', padx=12, pady=(5, 3))
        metrics.columnconfigure(0, weight=1);metrics.columnconfigure(1, weight=1)
        label(metrics, 'RECORDED VALUE', 8, MUTED).grid(row=0, column=0, sticky='w')
        label(metrics, 'SILVER / OBSERVED H', 8, MUTED).grid(row=0, column=1, sticky='w', padx=(8, 0))
        self.value = label(metrics, '—', 24 if wide else 22);self.value.grid(row=1, column=0, sticky='w')
        self.rate = label(metrics, '—', 18, TEAL);self.rate.grid(row=1, column=1, sticky='w', padx=(8, 0))
        self.goal = label(body, 'Set a silver goal in Grind', 9, MUTED, anchor='w');self.goal.pack(fill='x', padx=12)
        self.bar = tk.Canvas(body, height=3, bg=LINE, highlightthickness=0);self.bar.pack(fill='x', padx=12, pady=(4, 7))
        self.fill = self.bar.create_rectangle(0, 0, 0, 3, fill=TEAL, outline='')
        self.latest = label(body, 'Latest drop · Waiting for accepted loot', 9, VIOLET, anchor='w');self.latest.pack(fill='x', padx=12)
        self.time = label(body, 'Observed —  /  excluded —', 8, MUTED, anchor='w');self.time.pack(fill='x', padx=12, pady=(4, 0))
        footer = tk.Frame(body, bg=PANEL);footer.pack(fill='x', side='bottom')
        self.pause = button(footer, 'PAUSE / RESUME', self.live.grind.pause, TEAL);self.pause.pack(side='left', padx=5)
        label(footer, 'VALUE ≠ PROFIT', 8, MUTED).pack(side='right', padx=10)
        self.key = None;self.surface.place();self.shown = self.surface.show()

    def save_position(self, options):
        self.tracker.platform_preferences['overlay'] = dict(options);self.app.save_quietly()
        big = getattr(self.tracker, 'big_drops', None)
        if big and getattr(big, 'reveals', None):big.reveals.retile()

    def update(self, data):
        key = repr({k:v for k,v in data.items() if k != 'updatedAt'})
        if key == self.key:return
        self.key = key
        status = data.get('status', 'No active run')
        self.status.configure(text=('LIVE · ' if data.get('available') else 'PAUSED · ' if data.get('sessionActive') else 'READY · ')+status,
                              fg=TEAL if data.get('available') else GOLD)
        # Clip just the long labels; the full spot / item remains in the main app.
        self.status.configure(text=self.status.cget('text')[:48])
        self.value.configure(text=compact_silver(data.get('value')));self.rate.configure(text=compact_silver(data.get('rate')))
        unpriced = data.get('unpriced', 0)
        target = data.get('silverGoal', 0);value = data.get('value')
        if target and value is not None:
            ratio = max(0, min(1, value/target));goal = ('GOAL REACHED · ' if ratio == 1 else 'GOAL · ')+compact_silver(value)+' / '+compact_silver(target)
        elif data.get('goal'):
            ratio = data.get('progress') or 0;goal = f"{data.get('count',0)} / {data['required']} · {data['goal']}"
        else:ratio = 0;goal = 'Set a silver goal in Grind'
        if unpriced:goal = f'{unpriced} unpriced item types · partial value'
        self.goal.configure(text=goal[:53], fg=GOLD if unpriced else MUTED)
        self.bar.coords(self.fill, 0, 0, max(0, (self.width-26)*ratio), 3)
        recent = data.get('latest') or []
        self.latest.configure(text=(f"+{recent[0]['quantity']}  {recent[0]['item']}" if recent else 'Latest drop · Waiting for accepted loot')[:53])
        self.time.configure(text='Observed / excluded  '+data.get('time','—')+(' · rate after 60s' if data.get('sessionActive') and data.get('rate') is None else ''))
        self.pause.configure(text='PAUSE' if data.get('available') else 'PAUSE / RESUME')

    def close(self):
        self.surface.close();self.live.window = None;self.live.hud = None


def settings(live):
    existing = getattr(live, 'settings_window', None)
    if existing and existing.winfo_exists():existing.lift();return
    tracker = live.grind.tracker;app = tracker.app
    p = preferences(tracker.platform_preferences.get('overlay'))
    win = live.settings_window = tk.Toplevel(app.root);win.title('Vision · Overlay studio')
    win.configure(bg=INK);win.resizable(False, False)
    box = tk.Frame(win, bg=INK, padx=20, pady=16);box.pack(fill='both', expand=True)
    label(box, 'YOUR VIEW. YOUR MOMENT.', 15, VIOLET).pack(anchor='w')
    label(box, 'Drag the overlay header. Edges snap; reveals tile beside it.', 9, MUTED).pack(anchor='w', pady=(4, 12))
    variables = {}
    label(box, 'SNAP TO A CORNER', 9, TEAL).pack(anchor='w')
    variables['corner'] = tk.StringVar(value=p['corner'])
    dock_buttons = tk.Frame(box, bg=INK);dock_buttons.pack(fill='x', pady=(5,10))
    corners = []
    def choose(corner):
        variables['corner'].set(corner)
        for name, b in corners:b.configure(bg=LINE if corner==name else PANEL)
    for i, (corner, title) in enumerate([('top-left','↖ Top left'),('top-right','Top right ↗'),('bottom-left','↙ Bottom left'),('bottom-right','Bottom right ↘')]):
        b = button(dock_buttons,title,lambda value=corner:choose(value),TEAL)
        b.grid(row=i//2,column=i%2,sticky='ew',padx=3,pady=3);corners.append((corner,b))
        dock_buttons.columnconfigure(i%2,weight=1)
    choose(p['corner'])
    for key, title, values in [('density','Size',('Compact','Comfortable')),
                                ('seconds','Reveal duration (seconds)',(7,10,14))]:
        row = tk.Frame(box, bg=INK);row.pack(fill='x', pady=5)
        label(row, title, 10).pack(side='left')
        variable = tk.StringVar(value=str(p[key]));variables[key] = variable
        ttk.Combobox(row, textvariable=variable, values=values, width=17, state='readonly').pack(side='right')
    for key, title in [('locked','Lock overlay · clicks pass through to the game'), ('motion','Brief drop entrance animation'), ('sound','Play a quiet Windows notification sound')]:
        variables[key] = tk.BooleanVar(value=p[key])
        tk.Checkbutton(box, text=title, variable=variables[key], bg=INK, fg='#f5f0ff', selectcolor=PANEL,
                       activebackground=INK, activeforeground='#f5f0ff', font=('Segoe UI',10), anchor='w').pack(fill='x', pady=4)
    label(box, 'Locked? Reopen this studio from Grind → Overlay settings.\nReveals never take keyboard focus. Sound is off by default.\nWindowed / borderless BDO recommended; exclusive fullscreen may hide overlays.', 9, MUTED, justify='left').pack(anchor='w', pady=10)
    def apply():
        updated = dict(p)
        for key, var in variables.items():updated[key] = int(var.get()) if key == 'seconds' else var.get()
        tracker.platform_preferences['overlay'] = preferences(updated);app.save_quietly()
        opened = live.window and live.window.winfo_exists()
        if opened:live.hud.close();live.open()
        big = tracker.big_drops
        big.reveals.retile()
        win.destroy()
    row = tk.Frame(box, bg=INK);row.pack(fill='x', pady=(6, 0))
    button(row, 'SAVE SETTINGS', apply, TEAL).pack(side='right')
    button(row, 'TEST DROP', tracker.big_drops.preview, VIOLET).pack(side='left')
    def snooze():
        tracker.big_drops.reveals.snooze();win.destroy()
        app.status.set('Drop popups muted for 10 minutes. Loot and Big Drops journal still record normally.')
    button(box, 'MUTE POPUPS FOR 10 MINUTES', snooze).pack(anchor='w', pady=(8,0))
