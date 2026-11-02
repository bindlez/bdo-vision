"""Quiet until a big drop: native journal, heat ribbon and one optional reveal."""
import time,webbrowser
import tkinter as tk
import ctypes
from tkinter import ttk
from big_drops import BigDropBook,classify


def silver(value):
    if value is None:return 'Unpriced'
    return f'{value/1e9:,.2f}B silver' if value>=1e9 else f'{value/1e6:,.1f}M silver' if value>=1e6 else f'{value:,.0f} silver'


class BigDrops:
    def __init__(self,tracker):
        self.tracker=tracker;self.app=tracker.app;self.book=BigDropBook(tracker.ledger.db)
        self.frame=None;self.tree=None;self.selected_id=None;self.toast=None;self.toast_job=None;self._draw_key=None
        self.celebrate=tk.BooleanVar(value=bool(tracker.platform_preferences.get('big_drop_celebrations',True)))
        self.title=tk.StringVar(value='YOUR NEXT BIG MOMENT');self.subtitle=tk.StringVar()
        self.heat_title=tk.StringVar(value='READY FOR A SPARK');self.heat_note=tk.StringVar();self.heat_message=tk.StringVar()
        self.detail=tk.StringVar(value='Your rare drops become a local trophy journal. Existing recorded drops appear automatically.')
        self.compare=tk.StringVar();self.source=None;self.meter=None
        self._snapshot_key=None;self._snapshot=None
        self.pending={};self._pending_price_revision=-1

    def snapshot(self):
        ready,_=self.tracker.capture_availability()
        session=self.tracker.insights.session;prices=self.tracker.insights.prices.all()
        stamp=(self.book.revision,session.id,session.ended,int(session.clock.seconds/15),ready,id(prices))
        if self._snapshot_key!=stamp:
            self._snapshot=self.book.snapshot(self.tracker.ledger.revision,session,prices,ready);self._snapshot_key=stamp
        return self._snapshot

    def observe(self,loot_id,item_event=None,moment=None):
        prices=self.tracker.insights.prices.all();session=self.tracker.insights.session
        if item_event is not None:
            if not classify(item_event.item,item_event.kind,prices.get(item_event.item)):
                if item_event.kind not in ('Crafted','Rare craft') and item_event.item not in prices:
                    if len(self.pending)>=32:self.pending.pop(next(iter(self.pending)))
                    self.pending[loot_id]=(session.id,session.clock.seconds)
                return
        elif moment is not None:
            row=self.book.db.execute('SELECT item,kind FROM loot WHERE id=?',(loot_id,)).fetchone()
            if row and not classify(row[0],row[1],prices.get(row[0])) and row[0] not in prices:
                self.pending[loot_id]=moment;return
        event=self.book.observe(loot_id,session,prices,moment)
        if not event:return
        self.selected_id=event['id'];self.app.status.set(event['category'].upper()+' · '+event['item']+' × '+str(event['quantity'])+' · saved in Big Drops')
        if self.frame and self.frame.winfo_ismapped():self.refresh()
        if self.celebrate.get():self.reveal(event)

    def refresh_pending(self):
        revision=self.tracker.insights.prices.revision
        if not self.pending or revision==self._pending_price_revision:return
        self._pending_price_revision=revision
        for ident,moment in list(self.pending.items()):
            self.pending.pop(ident,None);self.observe(ident,moment=moment)

    def toggle(self):
        self.tracker.platform_preferences['big_drop_celebrations']=self.celebrate.get();self.app.save_quietly()

    def open(self):
        self.book._cache_key=None;self._snapshot_key=None
        self.tracker.open();self.tracker.tabs.select(self.frame);self.refresh()

    def build(self,tabs):
        from ui_scroll import notebook_page
        c=self.app.colors;self.frame,frame=notebook_page(tabs,'Big Drops',c)
        top=tk.Frame(frame,bg=c['bg']);top.pack(fill='x')
        tk.Label(top,text='BIG DROPS / THE TROPHY ROOM',bg=c['bg'],fg=c['bright'],font=('Segoe UI Semibold',12)).pack(side='left')
        ttk.Checkbutton(top,text='Drop reveals',variable=self.celebrate,command=self.toggle,style='Vision.TCheckbutton').pack(side='right')
        hero=tk.Frame(frame,bg=c['panel'],highlightbackground=c['violet'],highlightthickness=1,padx=14,pady=14);hero.pack(fill='x',pady=(10,8))
        tk.Label(hero,textvariable=self.title,bg=c['panel'],fg='#ffe2a8',font=('Segoe UI Semibold',21),wraplength=680,justify='left').pack(anchor='w')
        tk.Label(hero,textvariable=self.subtitle,bg=c['panel'],fg=c['secondary'],font=('Segoe UI',10),wraplength=680,justify='left').pack(anchor='w',pady=(5,0))
        hot=tk.Frame(frame,bg=c['panel2'],padx=14,pady=12);hot.pack(fill='x',pady=(0,10))
        tk.Label(hot,textvariable=self.heat_title,bg=c['panel2'],fg='#ffc47b',font=('Segoe UI Semibold',15)).pack(anchor='w')
        self.meter=ttk.Progressbar(hot,maximum=100,style='Vision.Horizontal.TProgressbar');self.meter.pack(fill='x',pady=7)
        tk.Label(hot,textvariable=self.heat_message,bg=c['panel2'],fg=c['text'],font=('Segoe UI Semibold',11),wraplength=680,justify='left').pack(anchor='w')
        tk.Label(hot,textvariable=self.heat_note,bg=c['panel2'],fg=c['secondary'],font=('Segoe UI',9),wraplength=680,justify='left').pack(anchor='w',pady=(5,0))
        self.tree=ttk.Treeview(frame,columns=('item','kind','quantity','value'),show='headings',height=5,style='Loot.Treeview')
        for name,label,width in [('item','DROP JOURNAL',330),('kind','MOMENT',100),('quantity','QTY',50),('value','MARKET VALUE',140)]:
            self.tree.heading(name,text=label);self.tree.column(name,width=width,minwidth=45,stretch=name=='item')
        self.tree.pack(fill='x');self.tree.bind('<<TreeviewSelect>>',self.select)
        tk.Label(frame,textvariable=self.detail,bg=c['bg'],fg=c['text'],font=('Segoe UI',10),wraplength=700,justify='left').pack(anchor='w',pady=(10,6))
        self.app.text_button(frame,'ITEM / TREASURE SOURCE',self.open_source).pack(anchor='w')
        tk.Label(frame,text='RARITY SHELF · JACKPOT VS TREASURE',bg=c['bg'],fg=c['bright'],font=('Segoe UI Semibold',11)).pack(anchor='w',pady=(12,6))
        tk.Label(frame,textvariable=self.compare,bg=c['bg'],fg=c['secondary'],font=('Segoe UI',10),wraplength=700,justify='left').pack(anchor='w')
        tk.Label(frame,text='A market price is value, not a drop probability. Heat celebrates recorded outcomes; it does not change future odds. Capture gaps, buffs and missed OCR can affect personal comparisons.',bg=c['bg'],fg=c['muted'],font=('Segoe UI',9),wraplength=700,justify='left').pack(anchor='w',pady=(12,0))
        self.refresh()

    def select(self,event=None):
        picks=self.tree.selection()
        if picks:self.selected_id=int(picks[0]);self._draw_key=None;self.refresh()

    def refresh(self):
        self.refresh_pending()
        data=self.snapshot();event=next((r for r in data['journal'] if r['id']==self.selected_id),data['latest']);rating=data['heat']
        draw_key=(repr(data),self.selected_id)
        if draw_key==self._draw_key:return
        self._draw_key=draw_key
        self.title.set(event['item'] if event else 'YOUR NEXT BIG MOMENT')
        self.subtitle.set((event['category'].upper()+' · '+silver(event['value'])+f" · ×{event['quantity']} · {event['lifetime_units']} recorded lifetime") if event else 'Big >1B per item · Huge >10B per item · treasures count regardless of price. Only accepted loot counts.')
        self.heat_title.set(rating['title']+f" · {rating['score']}/100");self.heat_message.set(rating['message']);self.meter['value']=rating['score']
        self.heat_note.set(rating['basis']+'\n'+rating['note'])
        ids={str(r['id']) for r in data['journal']}
        for ident in self.tree.get_children():
            if ident not in ids:self.tree.delete(ident)
        for index,row in enumerate(data['journal']):
            ident=str(row['id']);values=(row['item'],row['category'],row['quantity'],silver(row['value']))
            if self.tree.exists(ident):
                if tuple(self.tree.item(ident)['values'])!=values:self.tree.item(ident,values=values)
            else:self.tree.insert('',index,iid=ident,values=values)
        if event:
            timing=f"{event['observed_seconds']/60:.1f} observed minutes into the run" if event['observed_seconds'] is not None else 'Time-to-drop not captured for this retained observation'
            self.detail.set(event['detail']+'\n'+event['at']+' · '+timing+'\nPrice basis: '+event['price_source']+'. Recorded item value; no sale, tax or crafting cost assumed.')
            self.source=event['source']
        own=[r for r in data['comparisons'] if r['lifetime_units']]
        shelf=[]
        for row in data['comparisons'][:8]:
            pace=f"{row['personal_hours_per_event']:.2f} observed h / event" if row['personal_hours_per_event'] is not None else 'Building a personal sample'
            shelf.append(row['item']+' · '+pace+f" · {row['sample_events']} events / {row['sample_hours']:.1f}h")
        self.compare.set('BIG >1B / item · HUGE >10B / item · TREASURE regardless of price\n\n'+'\n'.join(shelf)+'\n\nYour collection: '+(' · '.join(r['item']+f" ×{r['lifetime_units']}" for r in own[:6]) or 'Your first trophy is waiting.')+'\n\nThese are your observed grind hours, across eligible recorded spots; not per-kill or global odds. The pace heat needs 3 runs, 2 observed hours and 5 big-drop events at this spot. Without that sample, burst heat celebrates recorded clusters.')

    def open_source(self):
        if self.source:webbrowser.open_new_tab(self.source)

    def reveal(self,event):
        self.close_toast();c=self.app.colors;win=self.toast=tk.Toplevel(self.app.root,takefocus=False)
        win.withdraw()
        win.overrideredirect(True);win.attributes('-topmost',True);win.configure(bg='#ffe2a8' if event['category']=='Huge Drop' else c['violet'])
        win.geometry(f'330x135+{max(0,win.winfo_screenwidth()-350)}+{max(0,win.winfo_screenheight()-210)}')
        box=tk.Frame(win,bg=c['panel'],padx=14,pady=12);box.pack(fill='both',expand=True,padx=1,pady=1)
        tk.Label(box,text='✦ '+event['category'].upper(),bg=c['panel'],fg='#ffe2a8',font=('Segoe UI Semibold',11)).pack(anchor='w')
        tk.Label(box,text=event['item']+' ×'+str(event['quantity']),bg=c['panel'],fg=c['text'],font=('Segoe UI Semibold',12),wraplength=295,justify='left').pack(anchor='w',pady=6)
        tk.Button(box,text='VIEW TROPHY',command=lambda:(self.close_toast(),self.open()),bg=c['violet'],fg=c['text'],relief='flat',takefocus=False).pack(side='left')
        tk.Button(box,text='×',command=self.close_toast,bg=c['panel'],fg=c['muted'],relief='flat',takefocus=False).pack(side='right')
        # A celebration must never steal BDO's focus and interrupt capture.
        # This changes only our own newly-created window, before it is shown.
        try:
            win.update_idletasks();user32=ctypes.windll.user32
            user32.GetAncestor.argtypes=[ctypes.c_void_p,ctypes.c_uint];user32.GetAncestor.restype=ctypes.c_void_p
            user32.GetWindowLongW.argtypes=[ctypes.c_void_p,ctypes.c_int]
            user32.SetWindowLongW.argtypes=[ctypes.c_void_p,ctypes.c_int,ctypes.c_long]
            handle=user32.GetAncestor(win.winfo_id(),2)
            style=user32.GetWindowLongW(handle,-20);user32.SetWindowLongW(handle,-20,style|0x08000000|0x00000080)
            if not user32.GetWindowLongW(handle,-20)&0x08000000:raise RuntimeError('Passive window style unavailable')
            win.deiconify()
        except (AttributeError,OSError,tk.TclError,RuntimeError):
            self.close_toast();return  # Journal and status remain; never force focus.
        self.toast_job=self.app.root.after(6500,self.close_toast)

    def close_toast(self):
        if self.toast_job is not None:self.app.root.after_cancel(self.toast_job);self.toast_job=None
        if self.toast is not None:
            try:self.toast.destroy()
            except tk.TclError:pass
            self.toast=None
