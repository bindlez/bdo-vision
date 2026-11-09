"""Compact, passive craft value and loot view attached to the Vision dock."""
import math
import tkinter as tk

from game_overlay import GOLD, INK, LINE, MUTED, TEAL, VIOLET, OverlaySurface, geometry, label, work_area
from overlay_layout import compact_silver, overlap, tile


class CraftMetricsHUD:
    SIZE = (280, 178)

    def __init__(self, live):
        self.live = live
        self.tracker = live.grind.tracker
        self.surface = OverlaySurface(self.tracker.app.root, 'Vision · Craft loot', self.SIZE, {'locked':True})
        body = self.surface.body
        tk.Frame(body, bg=TEAL, height=2).pack(fill='x')
        self.heading = label(body, 'CRAFT / LOOT', 10, TEAL, anchor='w')
        self.heading.pack(fill='x', padx=10, pady=(4, 0))
        self.state = label(body, 'Waiting for a verified tool', 9, GOLD, anchor='w')
        self.state.pack(fill='x', padx=10)
        metrics = tk.Frame(body, bg=INK)
        metrics.pack(fill='x', padx=10, pady=4)
        self.numbers = []
        for name in ('RECORDED VALUE', 'EST. SILVER / H', 'UNITS'):
            cell = tk.Frame(metrics, bg=INK)
            cell.pack(side='left', fill='x', expand=True)
            label(cell, name, 8, MUTED).pack(anchor='w')
            value = label(cell, '—', 11, TEAL)
            value.pack(anchor='w')
            self.numbers.append(value)
        graphs = tk.Frame(body, bg=INK)
        graphs.pack(fill='x', padx=10)
        self.value_graph = self.make_graph(graphs, 'CAPTURED VALUE', 132)
        self.loot_graph = self.make_graph(graphs, 'RECORDED LOOT', 114)
        self.note = label(body, '', 8, MUTED, anchor='w')
        self.note.pack(fill='x', padx=10, pady=(3, 0))
        self.key = None
        self.shown = False
        self.retile()

    @staticmethod
    def make_graph(parent, title, width):
        cell = tk.Frame(parent, bg=INK)
        cell.pack(side='left', fill='x', expand=True)
        label(cell, title, 8, MUTED).pack(anchor='w')
        canvas = tk.Canvas(cell, width=width, height=47, bg=INK, highlightthickness=0)
        canvas.pack(anchor='w')
        return canvas

    def retile(self):
        hud = self.live.hud
        if hud is None or not self.surface.window.winfo_exists():
            return
        regions = list(self.tracker.capture_regions().values())
        guild = self.tracker.guild
        if guild.region:regions.append(guild.region)
        quest_box = guild.watch_box
        if quest_box:
            x0, y0, x1, y1 = quest_box
            regions.append((x0, y0, x1-x0, y1-y0))
        app = self.tracker.app
        reader = app.tool_reader
        if reader.context:
            _, left, top, _, _ = reader.context
            for region in reader.regions:
                x0, y0, x1, y1 = region['box']
                regions.append((left+x0, top+y0, x1-x0, y1-y0))
        regions = [region for region in regions if isinstance(region,(list,tuple))
                   and len(region)==4 and all(type(n) is int for n in region)
                   and min(region[2:])>0]
        obstacles = [hud.surface.rect, *regions]
        child = app.dock_panels.window
        if child is not None and child.winfo_exists() and child.winfo_ismapped():
            obstacles.append((child.winfo_rootx(), child.winfo_rooty(), child.winfo_width(), child.winfo_height()))
        rect = tile(self.SIZE, work_area(hud.surface.window), obstacles)
        if any(overlap(rect, region) for region in obstacles):
            if self.shown:
                self.surface.window.withdraw()
                self.shown = False
            return
        if self.surface.rect != rect:
            self.surface.rect = rect
            geometry(self.surface.window, rect)
        if not self.shown:
            self.shown = self.surface.show()

    def update(self, snapshot, capture_reason=''):
        self.retile()
        if not self.shown:
            return
        key = (snapshot, capture_reason)
        if key == self.key:
            return
        self.key = key
        self.heading.configure(text=('CRAFT / '+snapshot['recipe'][:26]) if snapshot.get('recipe') else 'CRAFT / LOOT')
        detected = snapshot.get('detected', False)
        live = bool(snapshot.get('current'))
        if snapshot.get('available'):
            state = 'LIVE'
        elif live:
            state = 'PAUSED'+(' · '+capture_reason if capture_reason else '')
        else:
            state = 'LAST RUN · waiting for tool' if detected else 'WAITING FOR VERIFIED TOOL'
        self.state.configure(text=state[:48], fg=TEAL if snapshot.get('available') else GOLD)
        units = snapshot.get('units')
        values = (compact_silver(snapshot.get('recordedValue')), compact_silver(snapshot.get('recordedPerHour')), f'{units:,}' if units is not None else '—')
        for label_widget, value in zip(self.numbers, values):
            label_widget.configure(text=value)
        observed = snapshot.get('observedSeconds')
        note = f'{observed:.0f}s observed' if observed is not None else 'Silver appears after 10s of readable craft loot'
        if snapshot.get('unpriced'):
            note += f" · {len(snapshot['unpriced'])} unpriced"
        self.note.configure(text=note)
        self.draw_value(snapshot.get('points') or [])
        self.draw_loot(snapshot.get('items') or [])

    def draw_value(self, points):
        canvas = self.value_graph
        canvas.delete('all')
        rows = [(x, y) for x, y in points[-32:] if isinstance(y, (int, float)) and math.isfinite(y)]
        if len(rows) < 2:
            canvas.create_text(4, 22, anchor='w', text='Waiting for history', fill=MUTED, font=('Segoe UI', 8))
            return
        t0, t1 = rows[0][0], rows[-1][0]
        peak = max(1, *(value for _, value in rows))
        coords = [(3+126*(stamp-t0)/max(1, t1-t0), 42-36*value/peak) for stamp, value in rows]
        canvas.create_line(3, 43, 130, 43, fill=LINE)
        canvas.create_line(*[n for pair in coords for n in pair], fill=TEAL, width=2)

    def draw_loot(self, items):
        canvas = self.loot_graph
        canvas.delete('all')
        rows = sorted(items, key=lambda item:item['quantity'], reverse=True)[:3]
        if not rows:
            canvas.create_text(4, 22, anchor='w', text='No recorded items', fill=MUTED, font=('Segoe UI', 8))
            return
        peak = max(1, rows[0]['quantity'])
        for i, item in enumerate(rows):
            y = 2+i*15
            canvas.create_rectangle(3, y, 3+107*item['quantity']/peak, y+13, fill=LINE, outline='')
            canvas.create_text(5, y+7, anchor='w', text=item['item'][:13], fill=MUTED, font=('Segoe UI', 8))
            canvas.create_text(110, y+7, anchor='e', text=f"{item['quantity']:,}", fill=VIOLET, font=('Segoe UI', 8))

    def close(self):
        self.surface.close()
