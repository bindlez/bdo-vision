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
        self.milestone=tk.StringVar();self.canvas=None;self._summary_key=None;self._chart_key=None
        self.root.after(1000,self.tick)

    def rows(self):
        if self.scope.get()=='Timed session':return self.tracker.insights.session.rows()
        rows=self.tracker.ledger.rows()
        return [r for r in rows if r[1][:10]==time.strftime('%Y-%m-%d')] if self.scope.get()=='Today' else rows

    def build(self,tabs):
        self._rendered_key=None
        from ui_scroll import notebook_page
        c=self.tracker.app.colors;self.frame,frame=notebook_page(tabs,'Silver',c)
        controls=tk.Frame(frame,bg=c['bg']);controls.pack(fill='x')
        picker=ttk.Combobox(controls,style='Vision.TCombobox',textvariable=self.scope,values=('Today','Timed session','All recorded'),state='readonly',width=18);picker.pack(side='left');picker.bind('<<ComboboxSelected>>',lambda e:self.refresh())
        self.tracker.app.text_button(controls,'REFRESH MARKET MATCHES',lambda:self.tracker.insights.prices.refresh_async(force=True)).pack(side='left',padx=12)
        ttk.Checkbutton(controls,text='Share loot with planner / Fairy Codex (optional)',variable=self.tracker.share_loot,command=self.tracker.share_changed,style='Vision.TCheckbutton').pack(side='right')
        tk.Label(frame,textvariable=self.measurement,bg=c['bg'],fg=c['bright'],font=('Segoe UI Semibold',10),wraplength=700,justify='left').pack(anchor='w',pady=(16,0))
        tk.Label(frame,text='SILVER LOOTED · RECORDED VALUE',bg=c['bg'],fg=c['muted'],font=('Segoe UI Semibold',10)).pack(anchor='w',pady=(18,0))
        tk.Label(frame,textvariable=self.total,bg=c['bg'],fg=c['bright'],font=('Segoe UI Semibold',26)).pack(anchor='w',pady=(4,0))
        tk.Label(frame,textvariable=self.detail,bg=c['bg'],fg=c['text'],font=('Segoe UI',11)).pack(anchor='w',pady=(0,8))
        tk.Label(frame,textvariable=self.coverage,bg=c['bg'],fg=c['secondary'],wraplength=700,justify='left').pack(anchor='w',pady=(0,12))
        tk.Label(frame,textvariable=self.milestone,bg=c['bg'],fg=c['bright'],font=('Segoe UI Semibold',10)).pack(anchor='w',pady=(0,6))
        self.canvas=tk.Canvas(frame,height=100,bg=c['panel'],highlightthickness=0);self.canvas.pack(fill='x',pady=(0,10))
        self.canvas.bind('<Configure>',lambda e:self.draw_contributions(getattr(self,'_summary',{}),force=True))
        box=tk.Frame(frame,bg=c['bg']);box.pack(fill='both',expand=True)
        self.tree=ttk.Treeview(box,columns=('item','id','qty','price','value','group'),show='headings',style='Loot.Treeview',height=5)
        for name,label,width in [('item','MATCHED ITEM',280),('id','ITEM ID',75),('qty','QUANTITY',75),('price','UNIT SILVER',130),('value','TOTAL SILVER',130),('group','GROUP',140)]:self.tree.heading(name,text=label);self.tree.column(name,width=width,minwidth=65,stretch=name=='item')
        self.tree.pack(side='left',fill='both',expand=True);scroll=ttk.Scrollbar(box,orient='vertical',command=self.tree.yview);scroll.pack(side='right',fill='y');self.tree.configure(yscrollcommand=scroll.set)
        tk.Label(frame,text='Recorded quantity × market or verified NPC sell value. No material costs or fees deducted; this is item value, not a confirmed sale.',bg=c['bg'],fg=c['muted'],wraplength=700,justify='left',font=('Segoe UI',9)).pack(anchor='w',pady=(10,0))
        tabs.bind('<<NotebookTabChanged>>',lambda e:self.refresh(),add='+');self.refresh()

    def refresh(self):
        if not self.tree or not self.tree.winfo_exists():return
        prices=self.tracker.insights.prices.all();session=self.tracker.insights.session
        key=(self.scope.get(),self.tracker.ledger.revision,id(prices),session.id,time.strftime('%Y-%m-%d'))
        if key!=self._summary_key:
            self._summary=silver_snapshot(self.rows(),prices);self._summary_key=key
        result=self._summary
        self.total.set('No market quote yet' if result['market_silver'] is None else f"{result['market_silver']:,}")
        self.detail.set(f"{result['elixir_units']:,} elixirs / draughts  ·  {result['extra_units']:,} extra / other units  ·  {result['rare_units']:,} rare-notice units")
        self.coverage.set(f"{result['priced_types']}/{result['item_types']} item types priced. "+(f"Partial total: {result['unpriced_types']} unpriced types are excluded. " if result['unpriced_types'] else '')+'Matched by market item ID. Sharing is optional; unavailable readings are labeled on the site.')
        if self.tracker.insights.prices.last_error:self.coverage.set(self.coverage.get()+' Price refresh unavailable; cached quotes retained.')
        ready,reason=self.tracker.capture_availability()
        self.measurement.set('OBSERVING · qualified item notifications' if ready else 'MEASUREMENT PAUSED · '+reason+' · saved totals retained')
        if self.tracker.insights.prices.refreshing:self.coverage.set('Matching items and refreshing Central Market prices… '+self.coverage.get())
        self.draw_contributions(result)
        if self._rendered_key==key:return
        wanted={e['item'] for e in result['items']}
        for ident in self.tree.get_children():
            if ident not in wanted:self.tree.delete(ident);self._table_values.pop(ident,None)
        for index,entry in enumerate(result['items']):
            values=(entry['item'],entry['market_id'] or '—',f"{entry['quantity']:,}",'Unpriced' if entry['unit_price'] is None else f"{entry['unit_price']:,}",'—' if entry['value'] is None else f"{entry['value']:,}",entry['group']+(' · NPC' if entry.get('price_basis')=='npc_vendor' else ''))
            ident=entry['item']
            if self.tree.exists(ident):
                if self._table_values.get(ident)!=values:self.tree.item(ident,values=values)
                self.tree.move(ident,'',index)
            else:self.tree.insert('',index,iid=ident,values=values)
            self._table_values[ident]=values
        self._rendered_key=key

    def draw_contributions(self,result,force=False):
        if not self.canvas or not self.canvas.winfo_ismapped():return
        entries=[e for e in result.get('items',[]) if e.get('value')][:3]
        key=(result.get('market_silver'),tuple((e['item'],e['value']) for e in entries))
        if not force and self._chart_key==key:return
        self._chart_key=key;c=self.tracker.app.colors;canvas=self.canvas;canvas.delete('all')
        value=result.get('market_silver') or 0
        goal=next((g for g in (1_000_000,10_000_000,100_000_000,1_000_000_000,10_000_000_000) if g>value),max(1,value*2))
        self.milestone.set(f'NEXT MILESTONE · {value:,} / {goal:,} recorded silver · {min(100,value/goal*100):.1f}%')
        if not entries:
            canvas.create_text(12,45,anchor='w',text='Your top captured item values will appear here.',fill=c['muted']);return
        width=max(250,canvas.winfo_width());peak=max(e['value'] for e in entries)
        for index,e in enumerate(entries):
            y=8+index*30;label=e['item'][:32]
            canvas.create_text(10,y+8,anchor='w',text=label,fill=c['text'],font=('Segoe UI',9))
            left=min(240,width*.45);right=width-100
            canvas.create_rectangle(left,y+3,left+max(1,(right-left)*e['value']/peak),y+14,fill=c['bright'],outline='')
            canvas.create_text(width-10,y+8,anchor='e',text=f"{e['value']:,}",fill=c['text'],font=('Segoe UI',9))

    def tick(self):
        if self.closed:return
        try:
            if self.frame and self.frame.winfo_exists() and self.frame.winfo_ismapped():self.refresh()
        except Exception:self.coverage.set('Price display retry pending. Recorded history is retained.')
        finally:
            if not self.closed:self.root.after(1000,self.tick)

    def close(self):self.closed=True
