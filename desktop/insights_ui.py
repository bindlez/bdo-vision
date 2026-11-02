"""One compact Insights tab; using quotes from the existing Central Market site."""
import time
import tkinter as tk
from tkinter import ttk,messagebox
import webbrowser
import json
from pathlib import Path
from loot_insights import InsightsSession,summarize
from price_book import PriceBook


def number(value):
    if value is None:return '—'
    if abs(value)>=1_000_000_000:return f'{value/1_000_000_000:,.2f}B'
    if abs(value)>=1_000_000:return f'{value/1_000_000:,.2f}M'
    return f'{value:,.0f}'


class LootInsights:
    def __init__(self,tracker):
        self.tracker=tracker;self.root=tracker.root
        self.prices=PriceBook(tracker.path/'loot-history.sqlite3',tracker.path/'assets'/'recipes.json')
        self.session=InsightsSession(tracker.ledger.db)
        self.scope=tk.StringVar(value='Today');self.state=tk.StringVar();self.note=tk.StringVar()
        self.values=[tk.StringVar(value='—') for _ in range(4)]
        self.frame=None;self.tree=None;self.pause_button=None;self.closed=False
        self.last_lite_mode=None
        self.sessions_frame=None;self.sessions_tree=None;self.session_detail=None
        self.session_name=tk.StringVar();self.activity=tk.StringVar(value='Crafting' if tracker.crafting.get() else 'Grinding')
        self.recipe=tk.StringVar(value='No recipe');self.targets=tk.StringVar();self.session_note=tk.StringVar(value='Start a session to group future recorded loot. History is retained when starting another session.')
        self.root.after(1000,self.tick)

    def build(self,notebook):
        c=self.tracker.app.colors
        from ui_scroll import notebook_page
        self.frame,frame=notebook_page(notebook,'Insights',c)
        controls=tk.Frame(frame,bg=c['bg']);controls.pack(fill='x')
        scope=ttk.Combobox(controls,style='Vision.TCombobox',textvariable=self.scope,values=('Today','Timed session'),state='readonly',width=16);scope.pack(side='left',padx=(0,10));scope.bind('<<ComboboxSelected>>',lambda e:self.refresh())
        self.tracker.app.action(controls,'START NEW SESSION',self.start).pack(side='left')
        self.pause_button=self.tracker.app.action(controls,'RESUME',self.pause_resume);self.pause_button.pack(side='left',padx=8)
        self.tracker.app.text_button(controls,'OPEN CENTRAL MARKET',self.edit_prices).pack(side='right')
        tk.Label(frame,textvariable=self.state,bg=c['bg'],fg=c['secondary'],font=('Segoe UI',9),wraplength=700,justify='left').pack(anchor='w',pady=(10,12))
        cards=tk.Frame(frame,bg=c['bg']);cards.pack(fill='x')
        for i,label in enumerate(('OUTPUT VALUE · EST.','SILVER / HOUR · EST.','ITEMS / HOUR','CRAFTED / RARE UNITS')):
            cards.columnconfigure(i,weight=1,uniform='metrics')
            card=tk.Frame(cards,bg=c['panel'],padx=10,pady=12);card.grid(row=0,column=i,sticky='nsew',padx=(0,6))
            tk.Label(card,text=label,bg=c['panel'],fg=c['muted'],font=('Segoe UI Semibold',8)).pack(anchor='w')
            tk.Label(card,textvariable=self.values[i],bg=c['panel'],fg=c['bright'],font=('Segoe UI Semibold',15)).pack(anchor='w',pady=(8,0))
        tk.Label(frame,textvariable=self.note,bg=c['bg'],fg=c['secondary'],font=('Segoe UI',9),wraplength=700,justify='left').pack(anchor='w',pady=(12,10))
        table=tk.Frame(frame,bg=c['bg']);table.pack(fill='both',expand=True)
        columns=('item','qty','price','value','share','source')
        self.tree=ttk.Treeview(table,columns=columns,show='headings',style='Loot.Treeview',height=5)
        for name,label,width in [('item','VALUE CONTRIBUTORS',245),('qty','QTY',65),('price','UNIT SILVER',100),('value','VALUE',100),('share','SHARE',65),('source','PRICE BASIS',150)]:
            self.tree.heading(name,text=label);self.tree.column(name,width=width,minwidth=50,stretch=name=='item')
        self.tree.pack(side='left',fill='both',expand=True)
        scroll=ttk.Scrollbar(table,orient='vertical',command=self.tree.yview);scroll.pack(side='right',fill='y');self.tree.configure(yscrollcommand=scroll.set)
        tk.Label(frame,text='Gross observed value, not profit. Ingredients and fees are not deducted. Uses cached Central Market prices loaded by your existing site.',bg=c['bg'],fg=c['muted'],font=('Segoe UI',9),wraplength=700,justify='left').pack(anchor='w',pady=(10,0))
        notebook.bind('<<NotebookTabChanged>>',lambda e:self.refresh(),add='+')
        self.refresh()
        self.build_sessions(notebook)

    def start(self):
        if self.session.id and not self.session.ended:self.session.finish(self.prices.all(),self.gate())
        targets=[name.strip() for name in self.targets.get().split(',') if name.strip()]
        self.session.start(self.gate(),label=self.session_name.get(),activity=self.activity.get(),recipe='' if self.recipe.get()=='No recipe' else self.recipe.get(),targets=targets)
        if self.activity.get() in ('Crafting','Grinding','Treasure hunt'):
            self.tracker.crafting.set(self.activity.get()=='Crafting');self.tracker.app.save_quietly()
        self.scope.set('Timed session');self.tracker.generation+=1
        self.refresh();self.refresh_sessions()

    def gate(self):
        return self.tracker.capture_availability()[0]

    def pause_resume(self):
        if self.session.ended:self.start();return
        self.session.pause_resume(self.gate());self.scope.set('Timed session');self.refresh();self.refresh_sessions()

    def observe(self,row_id):
        self.session.observe(row_id,self.gate())

    def tick(self):
        if self.closed:return
        try:
            lite=self.tracker.app.lite_use.get()
            if lite:
                if self.last_lite_mode is not True:
                    self.tracker.capture_clock.tick(False,'Lite Use · timer only')
                    self.session.clock.gate=False;self.session.tick(False)
                    self.tracker.refresh_shared_loot()
                self.last_lite_mode=True
                home=getattr(self.tracker,'home',None)
                if home and home.frame.winfo_exists() and home.frame.winfo_ismapped():home.refresh()
                return
            ready,reason=self.tracker.capture_availability()
            self.tracker.capture_clock.tick(ready,reason)
            if not ready:self.session.clock.gate=False
            self.session.tick(ready)
            lite=self.tracker.app.lite_use.get()
            if not lite:self.prices.refresh_async()
            big=getattr(self.tracker,'big_drops',None)
            if big:big.refresh_pending()
            if not lite or lite!=self.last_lite_mode:self.tracker.refresh_shared_loot()
            self.last_lite_mode=lite
            home=getattr(self.tracker,'home',None)
            if home and home.frame.winfo_exists() and home.frame.winfo_ismapped():home.refresh()
            workshop=getattr(self.tracker,'craft_dashboard',None)
            if workshop and self.tracker.craft_tab.winfo_exists() and self.tracker.craft_tab.winfo_ismapped():workshop.session_cost.refresh()
            if self.frame and self.frame.winfo_exists() and self.frame.winfo_ismapped():self.refresh()
            if self.sessions_frame and self.sessions_frame.winfo_exists() and self.sessions_frame.winfo_ismapped():self.refresh_sessions()
            if self.tracker.grind.frame and self.tracker.grind.frame.winfo_exists() and self.tracker.grind.frame.winfo_ismapped():self.tracker.grind.refresh()
            big=getattr(self.tracker,'big_drops',None)
            if big and big.frame and big.frame.winfo_ismapped():big.refresh()
            guild=getattr(self.tracker,'guild',None)
            if guild and guild.frame and guild.frame.winfo_exists() and guild.frame.winfo_ismapped():guild.refresh()
        except Exception as exc:self.state.set('Tracking paused; automatic retry pending: '+str(exc))
        finally:
            if not self.closed:self.root.after(1000,self.tick)

    def edit_prices(self):
        bridge=getattr(self.tracker.app,'bridge',None)
        if bridge and bridge.base_url:webbrowser.open_new_tab(bridge.base_url+'/planner')
        else:messagebox.showinfo('Planner','Open the local planner connection to load Central Market quotes.',parent=self.tracker.window)

    def refresh(self):
        if not self.tree or not self.tree.winfo_exists():return
        timed=self.scope.get()=='Timed session'
        rows=self.session.rows() if timed else [r for r in self.tracker.ledger.rows() if r[1][:10]==time.strftime('%Y-%m-%d')]
        seconds=self.session.clock.seconds if timed and self.session.id else None
        prices=self.prices.all()
        if timed and self.session.ended:
            meta=next((h for h in self.session.history() if h['id']==self.session.id),None)
            if meta:prices=json.loads(meta['price_snapshot'])
        result=summarize(rows,prices,seconds)
        self.values[0].set(number(result['value']))
        self.values[1].set('Measuring…' if result['warming_up'] else number(result['silver_hour']))
        self.values[2].set(number(result['units_hour']))
        self.values[3].set(f"{number(result['crafted'])} / {number(result['rare'])}")
        status='Running' if self.session.clock.running and self.gate() else 'Paused'
        elapsed=int(self.session.clock.seconds)
        self.state.set((f'{status} · {elapsed//3600:02}:{elapsed%3600//60:02}:{elapsed%60:02} recording time. Rates appear after 60 seconds.' if timed and self.session.id else 'Today’s recorded output. Start a timed session to measure silver/hour; older records have no reliable tracked duration.'))
        if self.pause_button:self.pause_button.configure(text='NEW SESSION' if self.session.ended else 'PAUSE' if self.session.clock.running else 'RESUME')
        self.note.set(f"{result['events']:,} observed events · {result['quantity']:,} units · {result['priced_types']}/{result['total_types']} item types priced. "+(f"Partial value: {result['unpriced']} unpriced types excluded. " if result['unpriced'] else '')+'Unpriced items need a Central Market quote from the existing site. OCR misses reduce reported output.')
        self.tree.delete(*self.tree.get_children())
        for item in result['items']:
            share=f"{100*item['value']/result['value']:.1f}%" if item['value'] is not None and result['value'] else '—'
            self.tree.insert('','end',values=(item['item'],f"{item['quantity']:,}",number(item['unit_price']),number(item['value']),share,item['source']))

    def build_sessions(self,notebook):
        c=self.tracker.app.colors
        from ui_scroll import notebook_page
        self.sessions_frame,frame=notebook_page(notebook,'Sessions',c)
        fields=tk.Frame(frame,bg=c['bg']);fields.pack(fill='x')
        for label,var,width in [('Session name',self.session_name,24),('Treasure target names (comma-separated)',self.targets,36)]:
            field=tk.Frame(fields,bg=c['bg']);field.pack(side='left',fill='x',expand=True,padx=(0,10));tk.Label(field,text=label,bg=c['bg'],fg=c['secondary'],font=('Segoe UI',9)).pack(anchor='w');ttk.Entry(field,textvariable=var,width=width,style='Vision.TEntry').pack(fill='x',pady=(4,0))
        row=tk.Frame(frame,bg=c['bg']);row.pack(fill='x',pady=10)
        ttk.Combobox(row,style='Vision.TCombobox',textvariable=self.activity,values=('Crafting','Grinding','Treasure hunt','Other'),state='readonly',width=15).pack(side='left',padx=(0,8))
        recipes=json.loads((Path(__file__).parent/'assets'/'recipes.json').read_text(encoding='utf-8')) if (Path(__file__).parent/'assets'/'recipes.json').exists() else []
        ttk.Combobox(row,style='Vision.TCombobox',textvariable=self.recipe,values=['No recipe']+sorted(r['name'] for r in recipes),state='readonly',width=30).pack(side='left',padx=(0,8))
        self.tracker.app.action(row,'START NEW',self.start).pack(side='left')
        self.tracker.app.action(row,'PAUSE / RESUME',self.pause_resume).pack(side='left',padx=6)
        self.tracker.app.action(row,'FINISH',self.finish_session).pack(side='left')
        tk.Label(frame,textvariable=self.session_note,bg=c['bg'],fg=c['secondary'],wraplength=700,justify='left',font=('Segoe UI',9)).pack(anchor='w',pady=(0,8))
        box=tk.Frame(frame,bg=c['bg']);box.pack(fill='both',expand=True)
        columns=('name','activity','duration','value','units','targets','state')
        self.sessions_tree=ttk.Treeview(box,columns=columns,show='headings',style='Loot.Treeview',height=4)
        for name,title,width in [('name','SESSION',220),('activity','ACTIVITY',100),('duration','TIME',85),('value','EST. SILVER',110),('units','ITEMS',75),('targets','TREASURE',90),('state','STATE',95)]:self.sessions_tree.heading(name,text=title);self.sessions_tree.column(name,width=width,minwidth=55,stretch=name=='name')
        self.sessions_tree.pack(side='left',fill='both',expand=True);scroll=ttk.Scrollbar(box,orient='vertical',command=self.sessions_tree.yview);scroll.pack(side='right',fill='y');self.sessions_tree.configure(yscrollcommand=scroll.set)
        self.sessions_tree.bind('<<TreeviewSelect>>',lambda e:self.show_session())
        self.session_detail=tk.StringVar(value='Select a session to see its recipe, value contributors and captured treasure. Finished-session values keep the saved price assumptions.')
        tk.Label(frame,textvariable=self.session_detail,bg=c['panel'],fg=c['secondary'],wraplength=700,justify='left',padx=10,pady=10,font=('Segoe UI',9)).pack(fill='x',pady=(10,0))
        notebook.bind('<<NotebookTabChanged>>',lambda e:self.refresh_sessions(),add='+')
        self.refresh_sessions()

    def finish_session(self):
        self.session.finish(self.prices.all(),self.gate());self.refresh();self.refresh_sessions()

    def session_result(self,meta):
        prices=json.loads(meta['price_snapshot']) if meta['ended_at'] is not None else self.prices.all()
        result=summarize(self.session.rows(meta['id']),prices,meta['active_seconds'])
        targets={name.casefold() for name in json.loads(meta['targets'])}
        result['treasure']=sum(item['quantity'] for item in result['items'] if item['item'].casefold() in targets)
        return result

    def refresh_sessions(self):
        if not self.sessions_tree or not self.sessions_tree.winfo_exists():return
        selected=self.sessions_tree.selection();self.sessions_tree.delete(*self.sessions_tree.get_children())
        history=self.session.history()
        for meta in history:
            if meta['id']==self.session.id:meta['active_seconds']=self.session.clock.seconds
            result=self.session_result(meta);seconds=int(meta['active_seconds'])
            state='Finished' if meta['ended_at'] is not None else 'Running' if meta['id']==self.session.id and self.session.clock.running and self.gate() else 'Paused'
            self.sessions_tree.insert('','end',iid=meta['id'],values=(meta['label'],meta['activity'],f'{seconds//3600:02}:{seconds%3600//60:02}:{seconds%60:02}',number(result['value'])+(' +' if result['unpriced'] else ''),f"{result['quantity']:,}",result['treasure'],state))
        if selected and self.sessions_tree.exists(selected[0]):self.sessions_tree.selection_set(selected[0]);self.show_session()
        self.session_note.set('Time pauses when Tracking or Record loot is off. Capture outages can miss items. Treasure counts match your named targets; crafting counts use Crafting mode.')

    def show_session(self):
        selected=self.sessions_tree.selection()
        if not selected:return
        meta=next((h for h in self.session.history() if h['id']==selected[0]),None)
        if not meta:return
        if meta['id']==self.session.id:meta['active_seconds']=self.session.clock.seconds
        result=self.session_result(meta)
        top=', '.join(f"{e['item']} ×{e['quantity']:,}" for e in result['items'][:4]) or 'No recorded items in this session yet'
        basis='Frozen prices at finish' if meta['ended_at'] is not None else 'Current saved prices'
        self.session_detail.set(f"{meta['label']} · {meta['activity']} · Recipe: {meta['recipe'] or 'not assigned'}\n{basis} · Gross silver/hr: {number(result['silver_hour'])} · Crafted units: {result['crafted']:,} · Rare units: {result['rare']:,} · Treasure target units: {result['treasure']:,}\n{top}\n{result['unpriced']} unpriced item types excluded; ingredients and fees not deducted.")

    def close(self):
        self.closed=True;self.session.tick(self.gate());self.session.save()
