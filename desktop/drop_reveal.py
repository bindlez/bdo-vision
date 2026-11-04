"""Bounded, event-only Big Drop reveal. No game interaction or history mutation."""
import time
import tkinter as tk
from game_overlay import OverlaySurface, label, button, INK, PANEL, LINE, VIOLET, TEAL, GOLD, MUTED
from overlay_layout import RevealQueue, preferences, compact_silver


class DropReveals:
    def __init__(self, big):
        self.big = big;self.root = big.app.root;self.queue = RevealQueue()
        self.surface = None;self.job = None;self.until = 0;self.event = None

    def options(self):return preferences(self.big.tracker.platform_preferences.get('overlay'))

    def offer(self, event):
        if time.monotonic() < self.until:return
        if self.queue.add(event) and not self.surface:self.next()

    def obstacle(self):
        hud = getattr(self.big.tracker.grind.live, 'hud', None)
        panel=getattr(self.big.tracker.grind.live,'craft_panel',None)
        rectangles=[]
        if hud and hud.shown and hud.surface.window.winfo_exists():rectangles.append(hud.surface.rect)
        if panel and panel.surface:rectangles.append(panel.surface.rect)
        return rectangles or None

    def retile(self):
        if self.surface:
            self.surface.options = self.options();self.surface.options['locked'] = False
            self.surface.place(self.obstacle())

    def next(self):
        event = self.queue.take()
        if not event or not self.big.celebrate.get():return
        p = self.options();self.event = event
        # Popups are always dismissible. Click-through applies to the dashboard.
        p['locked'] = False
        self.surface = OverlaySurface(self.root, 'Vision · Drop reveal', (360, 204), p)
        self.big.toast = self.surface.window
        body = self.surface.body
        accent = GOLD if event['category'] == 'Huge Drop' else TEAL if event.get('treasure') or event['category'] == 'Treasure' or event.get('milestone') else VIOLET
        self.accent = tk.Canvas(body, bg=INK, height=22, highlightthickness=0);self.accent.pack(fill='x')
        self.accent.create_line(0, 1, 360, 1, fill=accent, width=2)
        self.gem = self.accent.create_polygon(180, 5, 187, 12, 180, 19, 173, 12, fill=accent, outline='')
        header = tk.Frame(body, bg=INK);header.pack(fill='x', padx=14)
        label(header, ('PREVIEW · ' if event.get('preview') else 'PROGRESS SAVED · ' if event.get('milestone') else 'LOOT SECURED · ')+event['category'].upper(), 9, accent).pack(side='left')
        button(header, '×', self.dismiss).pack(side='right')
        label(body, event['item'], 16, wraplength=330, justify='left', anchor='w').pack(fill='x', padx=14)
        value = event.get('display_value') or ('Unpriced treasure' if event.get('value') is None else compact_silver(event['value'])+' SILVER')
        row = tk.Frame(body, bg=INK);row.pack(fill='x', padx=14, pady=(6, 2))
        label(row, value, 22, accent).pack(side='left')
        label(row, '×'+str(event['quantity']), 12, MUTED).pack(side='right')
        label(body, 'SAMPLE DATA · no loot recorded' if event.get('preview') else 'Accepted output · forecasts excluded' if event.get('milestone') else 'Recorded value · saved in your Trophy Room', 9, MUTED, anchor='w').pack(fill='x', padx=14)
        footer = tk.Frame(body, bg=PANEL);footer.pack(side='bottom', fill='x')
        button(footer, 'VIEW CRAFT' if event.get('milestone') else 'VIEW TROPHY ROOM', self.open_journal, accent).pack(side='left', padx=7)
        self.waiting = label(footer, '', 8, MUTED);self.waiting.pack(side='right', padx=10)
        self.life = tk.Canvas(body, height=2, bg=LINE, highlightthickness=0);self.life.pack(side='bottom', fill='x')
        self.life_fill = self.life.create_rectangle(0, 0, 358, 2, fill=accent, outline='')
        self.surface.place(self.obstacle())
        if not self.surface.show():
            self.surface = None;self.big.toast = None;self.queue.clear();return
        self.started = time.monotonic();self.duration = p['seconds'];self.motion = p['motion'];self.paint()
        if p['sound']:
            try:
                import winsound
                winsound.PlaySound('SystemAsterisk', winsound.SND_ALIAS | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
            except (ImportError, RuntimeError):pass

    def paint(self):
        self.job = None
        if not self.surface:return
        elapsed = time.monotonic()-self.started
        if elapsed >= self.duration:self.dismiss();return
        self.waiting.configure(text=f'+{len(self.queue.pending)} queued' if self.queue.pending else 'SAVED' if not self.event.get('preview') else 'PREVIEW')
        self.life.coords(self.life_fill, 0, 0, 358*max(0, 1-elapsed/self.duration), 2)
        entering = self.motion and elapsed < .25
        if entering:
            radius = 3+4*min(1, elapsed/.25)
            self.accent.coords(self.gem, 180,12-radius,180+radius,12,180,12+radius,180-radius,12)
        self.job = self.root.after(32 if entering else 200, self.paint)

    def dismiss(self):
        self.close(clear=False);self.next()

    def open_journal(self):
        # Opening the full app is an explicit user action; never on drop receipt.
        preview = self.event and self.event.get('preview');milestone=self.event and self.event.get('milestone')
        self.close()
        if milestone:self.big.app.open_activity('craft')
        elif not preview:self.big.open()

    def snooze(self):self.until = time.monotonic()+600;self.close()

    def close(self, clear=True):
        if self.job is not None:
            try:self.root.after_cancel(self.job)
            except tk.TclError:pass
            self.job = None
        if self.surface:self.surface.close();self.surface = None
        self.big.toast = None;self.event = None
        if clear:self.queue.clear()
