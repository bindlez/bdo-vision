import time
import tkinter as tk
from tkinter import ttk
from silver_loot import silver_snapshot
from insights_ui import number


class SilverLooted:
    def __init__(self,tracker):
        self.tracker=tracker;self.root=tracker.root
        self.scope=tk.StringVar(value='All recorded');self.total=tk.StringVar(value='—');self.detail=tk.StringVar();self.coverage=tk.StringVar()
        self.measurement=tk.StringVar();self._table_values={};self.frame=None;self.tree=None;self.closed=False
        self.root.after(1000,self.tick)

    def rows(self):
        if self.scope.get()=='Timed session':return self.tracker.insights.session.rows()
        rows=self.tracker.ledger.rows()
        return [r for r in rows if r[1][:10]==time.strftime('%Y-%m-%d')] if self.scope.get()=='Today' else rows

    def build(self,tabs):
        c=self.tracker.app.colors;self.frame=frame=tk.Frame(tabs,bg=c['bg'],padx=16,pady=12);tabs.add(frame,text='Silver')
        controls=tk.Frame(frame,bg=c['bg']);controls.pack(fill='x')
        picker=ttk.Combobox(controls,style='Vision.TCombobox',textvariable=self.scope,values=('Today','Timed session','All recorded'),state='readonly',width=18);picker.pack(side='left');picker.bind('<<ComboboxSelected>>',lambda e:self.refresh())
        self.tracker.app.text_button(controls,'REFRESH MARKET MATCHES',lambda:self.tracker.insights.prices.refresh_async(force=True)).pack(side='left',padx=12)
        ttk.Checkbutton(controls,text='Share recorded loot with planner (optional)',variable=self.tracker.share_loot,command=self.tracker.share_changed,style='Vision.TCheckbutton').pack(side='right')
        tk.Label(frame,textvariable=self.measurement,bg=c['bg'],fg=c['bright'],font=('Segoe UI Semibold',10),wraplength=880,justify='left').pack(anchor='w',pady=(16,0))
        tk.Label(frame,text='SILVER LOOTED · RECORDED VALUE',bg=c['bg'],fg=c['muted'],font=('Segoe UI Semibold',10)).pack(anchor='w',pady=(18,0))
        tk.Label(frame,textvariable=self.total,bg=c['bg'],fg=c['bright'],font=('Segoe UI Semibold',34)).pack(anchor='w',pady=(4,0))
        tk.Label(frame,textvariable=self.detail,bg=c['bg'],fg=c['text'],font=('Segoe UI',11)).pack(anchor='w',pady=(0,8))
        tk.Label(frame,textvariable=self.coverage,bg=c['bg'],fg=c['secondary'],wraplength=900,justify='left').pack(anchor='w',pady=(0,12))
        box=tk.Frame(frame,bg=c['bg']);box.pack(fill='both',expand=True)
        self.tree=ttk.Treeview(box,columns=('item','id','qty','price','value','group'),show='headings',style='Loot.Treeview',height=5)
        for name,label,width in [('item','MATCHED ITEM',280),('id','ITEM ID',75),('qty','QUANTITY',75),('price','UNIT SILVER',130),('value','TOTAL SILVER',130),('group','GROUP',140)]:self.tree.heading(name,text=label);self.tree.column(name,width=width,minwidth=65,stretch=name=='item')
        self.tree.pack(side='left',fill='both',expand=True);scroll=ttk.Scrollbar(box,orient='vertical',command=self.tree.yview);scroll.pack(side='right',fill='y');self.tree.configure(yscrollcommand=scroll.set)
        tk.Label(frame,text='Recorded quantity × market or verified NPC sell value. No material costs or fees deducted; this is item value, not a confirmed sale.',bg=c['bg'],fg=c['muted'],wraplength=900,justify='left',font=('Segoe UI',9)).pack(anchor='w',pady=(10,0))
        tabs.bind('<<NotebookTabChanged>>',lambda e:self.refresh(),add='+');self.refresh()

    def refresh(self):
        if not self.tree or not self.tree.winfo_exists():return
        result=silver_snapshot(self.rows(),self.tracker.insights.prices.all())
        self.total.set('No market quote yet' if result['market_silver'] is None else f"{result['market_silver']:,}")
        self.detail.set(f"{result['elixir_units']:,} elixirs / draughts  ·  {result['extra_units']:,} extra / other units  ·  {result['rare_units']:,} rare-notice units")
        self.coverage.set(f"{result['priced_types']}/{result['item_types']} item types priced. "+(f"Partial total: {result['unpriced_types']} unpriced types are excluded. " if result['unpriced_types'] else '')+'Matched by market item ID. Sharing is optional; unavailable readings are labeled on the site.')
        if self.tracker.insights.prices.last_error:self.coverage.set(self.coverage.get()+' Price refresh unavailable; cached quotes retained.')
        ready,reason=self.tracker.capture_availability()
        self.measurement.set('OBSERVING · qualified item notifications' if ready else 'MEASUREMENT PAUSED · '+reason+' · saved totals retained')
        wanted={e['item'] for e in result['items']}
        for ident in self.tree.get_children():
            if ident not in wanted:self.tree.delete(ident);self._table_values.pop(ident,None)
        if self.tracker.insights.prices.refreshing:self.coverage.set('Matching items and refreshing Central Market prices… '+self.coverage.get())
        for index,entry in enumerate(result['items']):
            values=(entry['item'],entry['market_id'] or '—',f"{entry['quantity']:,}",'Unpriced' if entry['unit_price'] is None else f"{entry['unit_price']:,}",'—' if entry['value'] is None else f"{entry['value']:,}",entry['group']+(' · NPC' if entry.get('price_basis')=='npc_vendor' else ''))
            ident=entry['item']
            if self.tree.exists(ident):
                if self._table_values.get(ident)!=values:self.tree.item(ident,values=values)
                self.tree.move(ident,'',index)
            else:self.tree.insert('',index,iid=ident,values=values)
            self._table_values[ident]=values

    def tick(self):
        if self.closed:return
        try:
            if self.frame and self.frame.winfo_exists() and self.frame.winfo_ismapped():self.refresh()
        except Exception:self.coverage.set('Price display retry pending. Recorded history is retained.')
        finally:
            if not self.closed:self.root.after(1000,self.tick)

    def close(self):self.closed=True
