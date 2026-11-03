"""Current craft inference/controller. Only accepted events and the existing tick."""
import json,math,sqlite3,threading,time
from contextlib import closing
import tkinter as tk
from tkinter import ttk
from auto_craft import CraftInference,families


class AutomaticCrafting:
    def __init__(self,tracker):
        self.tracker=tracker;self.app=tracker.app;self.db=tracker.ledger.db
        self.enabled=tk.BooleanVar(value=tracker.platform_preferences.get('auto_craft_enabled',True))
        self.db.execute('CREATE TABLE IF NOT EXISTS auto_craft_runs(id TEXT PRIMARY KEY,updated_at REAL NOT NULL,payload TEXT NOT NULL)');self.db.commit()
        self.db.execute('CREATE TABLE IF NOT EXISTS auto_craft_members(loot_id INTEGER PRIMARY KEY,run TEXT NOT NULL)');self.db.commit()
        saved=self.db.execute('SELECT payload FROM auto_craft_runs ORDER BY updated_at DESC LIMIT 1').fetchone()
        try:
            state=json.loads(saved[0]) if saved and len(saved[0])<2000000 else None
            if state and not all(k in state for k in ('tool','family','counts','observed','samples','actions','at')):state=None
            self.engine=CraftInference(state)
        except (ValueError,TypeError):self.engine=CraftInference()
        self.view=None;self.last_save=0;self.saved_key=None;self.fetching=False;self.requests={};self.quote_notice='Cached market prices; unknown values remain unpriced.'

    def context(self):
        a=self.app
        lite=getattr(a,'lite_use',None)
        if not self.enabled.get() or (lite is not None and lite.get()) or not getattr(a,'running',False) or not getattr(a,'has_reading',False) or getattr(a,'last_good_ocr',None) is None or getattr(a,'_active_tool_key',None) is None:return None
        status=a.tool_status.snapshot();row=next((r for r in status['tools'] if r['id']==status['active_id']),None)
        if not row:return None
        name=row['name'].casefold();kind='alchemy' if 'alchemy' in name else 'cooking' if 'cooking' in name else None
        try:speed=float(a.speed.get());remaining=float(a.value)
        except (ValueError,TypeError):return None
        if not kind or not math.isfinite(speed) or not .05<=speed<=3600 or not math.isfinite(remaining) or remaining<=0:return None
        return {'active':True,'tool':a.session_id,'kind':kind,'verified':row['current'],'remaining':remaining,'speed':speed}

    @staticmethod
    def run_id(run):return run['tool']+':'+run['family']+':'+str(run['at'])

    def save(self,run=None):
        run=run or self.engine.run
        if not run:return
        with self.db:self.db.execute('INSERT INTO auto_craft_runs VALUES (?,?,?) ON CONFLICT(id) DO UPDATE SET updated_at=excluded.updated_at,payload=excluded.payload',(self.run_id(run),time.time(),json.dumps(run)))
        self.last_save=time.monotonic()
        if run is self.engine.run:self.saved_key=(self.run_id(run),run['lastId'],run['observed'])

    def observe(self,ident,item,quantity,at=None):
        before=self.engine.run;changed=self.engine.observe(ident,item,quantity,self.context(),time.time() if at is None else at,now=time.monotonic())
        if changed:
            if before is not None and before is not self.engine.run:self.save(before)
            ids=self.engine.run.get('ids',[ident]) if before is not self.engine.run else [ident]
            with self.db:self.db.executemany('INSERT OR IGNORE INTO auto_craft_members VALUES (?,?)',[(i,self.run_id(self.engine.run)) for i in ids])
            self.save()
            if before is not self.engine.run:self.refresh_prices()

    def rows(self):
        """Derived activity labels only; never rewrite original accepted quantities."""
        return self.db.execute("SELECT l.id,l.recorded_at,l.item,l.quantity,l.source,l.session,CASE WHEN a.loot_id IS NULL THEN l.kind WHEN l.kind IN ('Rare drop','Rare craft') THEN 'Rare craft' ELSE 'Crafted' END FROM loot l LEFT JOIN auto_craft_members a ON a.loot_id=l.id ORDER BY l.id DESC").fetchall()

    def tick(self,ready):
        context=self.context();self.engine.tick(context,ready and self.enabled.get(),time.monotonic())
        if self.app.lite_use.get():
            if self.view and self.view.frame.winfo_exists() and self.view.title.get()!='Lite Use · automatic craft capture paused':self.view.title.set('Lite Use · automatic craft capture paused')
            return
        run=self.engine.run
        key=(self.run_id(run),run['lastId'],run['observed']) if run else None
        if key and key!=self.saved_key and time.monotonic()-self.last_save>=5:self.save()
        if context and ready and run and context['tool']==run['tool']:self.refresh_prices()
        if self.view and self.view.frame.winfo_exists() and self.view.frame.winfo_ismapped():self.view.refresh()

    def snapshot(self,ready=None):
        if ready is None:ready=self.tracker.capture_availability()[0]
        context=self.context();run=self.engine.run;kind=families()[0].get(run['family'],{}).get('kind') if run else None
        mastery=self.tracker.imperial.saved.get(kind,0) if kind else 0
        try:mastery=float(mastery);mastery=mastery if math.isfinite(mastery) and 0<=mastery<=3000 else 0
        except (ValueError,TypeError):mastery=0
        data=self.engine.snapshot(context,self.tracker.insights.prices.all() if run else {},ready,mastery)
        data['enabled']=self.enabled.get();data['priceStatus']=self.quote_notice
        if not self.enabled.get():data['status']='Automatic craft recognition is off.';data['available']=False
        elif getattr(self.app,'lite_use',None) is not None and self.app.lite_use.get():data['status']='Lite Use · loot OCR stopped; retained craft only.';data['available']=False
        return data

    def refresh_prices(self):
        run=self.engine.run
        if not run or not self.enabled.get() or self.fetching or self.app.lite_use.get():return
        prices=self.tracker.insights.prices
        with closing(sqlite3.connect(prices.path)) as db:region=db.execute('SELECT region FROM market_context WHERE id=1').fetchone()[0]
        key=(run['family'],region);now=time.monotonic()
        if now-self.requests.get(key,-1e9)<300:return
        self.requests[key]=now;self.fetching=True;self.quote_notice='Looking up detected recipe outputs and ingredients in the shared market cache…'
        family=families()[0][run['family']];wanted=[]
        from craft_economy import craft_spec
        spec=craft_spec()
        for r in family['recipes']:
            wanted.append(r['itemId'])
            if r.get('rare'):wanted.append(r['rare']['itemId'])
            wanted.extend(m['itemId'] for m in r['mats'])
        for r in family['recipes']:
            for m in r['mats']:wanted.extend(o['itemId'] for o in spec.get('groups',{}).get(str(m.get('groupId')),[]))
        ids=list(dict.fromkeys(wanted))[:64]
        def work():
            try:
                message=f'{len(prices.recipe_id_quotes(ids,region))} shared recipe quotes available · {region}.'
            except Exception:message='Market lookup unavailable; cached quotes retained. Unknown values stay unpriced.'
            def finish():
                self.fetching=False;self.quote_notice=message
                if self.engine.run and self.engine.run['family']!=key[0]:self.refresh_prices()
            try:self.tracker.root.after(0,finish)
            except (RuntimeError,tk.TclError):pass
        threading.Thread(target=work,name='detected-craft-quotes',daemon=True).start()

    def toggle(self):
        self.tracker.platform_preferences['auto_craft_enabled']=self.enabled.get();self.app.save_quietly()
        if self.view and self.view.frame.winfo_exists():self.view.refresh()


class CurrentCraftView:
    def __init__(self,parent,controller):
        self.controller=controller;controller.view=self;c=controller.app.colors
        self.frame=tk.Frame(parent,bg=c['panel'],padx=12,pady=12,highlightbackground=c.get('teal',c['bright']),highlightthickness=1);self.frame.pack(fill='x',pady=(0,12))
        top=tk.Frame(self.frame,bg=c['panel']);top.pack(fill='x')
        tk.Label(top,text='CURRENT CRAFT · AUTOMATIC',bg=c['panel'],fg=c.get('teal',c['bright']),font=('Segoe UI Semibold',12)).pack(side='left')
        ttk.Checkbutton(top,text='Detect automatically',variable=controller.enabled,command=controller.toggle,style='Vision.TCheckbutton').pack(side='right')
        self.title=tk.StringVar();tk.Label(self.frame,textvariable=self.title,bg=c['panel'],fg=c['text'],font=('Segoe UI Semibold',12),wraplength=700,justify='left').pack(anchor='w',pady=8)
        self.numbers=tk.StringVar();tk.Label(self.frame,textvariable=self.numbers,bg=c['panel'],fg=c['bright'],font=('Segoe UI Semibold',11),wraplength=700,justify='left').pack(anchor='w')
        self.progress=ttk.Progressbar(self.frame,maximum=100,style='Vision.Horizontal.TProgressbar');self.progress.pack(fill='x',pady=8)
        self.note=tk.StringVar();tk.Label(self.frame,textvariable=self.note,bg=c['panel'],fg=c['secondary'],wraplength=700,justify='left',font=('Segoe UI',9)).pack(anchor='w')
        self.more=controller.app.text_button(self.frame,'CRAFT GRAPHS & MODEL DETAILS',self.toggle_graphs);self.more.pack(anchor='w',pady=6)
        self.graphs=tk.Frame(self.frame,bg=c['panel']);self.line=tk.Canvas(self.graphs,height=160,bg=c['panel'],highlightthickness=0);self.line.pack(fill='x')
        from grind_charts import GrindCharts
        self.pies=GrindCharts(self.graphs,c);self.details=tk.StringVar();tk.Label(self.graphs,textvariable=self.details,bg=c['panel'],fg=c['secondary'],wraplength=700,justify='left',font=('Segoe UI',9)).pack(anchor='w')
        self.line.bind('<Configure>',lambda e:self.refresh());self.refresh()

    def toggle_graphs(self):
        if self.graphs.winfo_manager():self.graphs.pack_forget()
        else:self.graphs.pack(fill='x');self.refresh()

    def refresh(self):
        from insights_ui import number
        d=self.controller.snapshot();self.data=d
        if not d.get('detected'):
            self.title.set(d['status']);self.numbers.set('No recipe entry needed. Scan the active tool and enable recorded loot capture.');self.note.set('Two separate matching output captures identify the recipe family. Ambiguous or hidden output stays unknown.');self.progress['value']=0;self.line.delete('all');self.pies.draw(None);return
        m=d.get('model');self.title.set(d['recipe']+' · '+d['kind']+'\n'+d['status'])
        self.numbers.set('RECORDED: '+number(d['recordedValue'])+' silver · '+number(d['recordedPerHour'])+' / observed hour\n'+('PROJECTED: '+number(m['perHour'])+' / hour · '+number(m['toolValue'])+' for scanned tool\nREMAINING: '+number(d['remainingValue'])+' estimated silver' if m else 'Forecast paused until this craft has an active verified tool.'))
        self.progress['value']=100*(d['progress'] or 0)
        self.note.set(f"{d['units']:,} captured output units · next milestone {d['nextGoal']:,} ({max(0,d['nextGoal']-d['units']):,} to go). "+(f"Partial recorded value: {len(d['unpriced'])} unpriced outputs excluded. " if d['unpriced'] else '')+'Rates appear after 60 readable seconds. Byproducts are kept and not assigned sale value. '+d['priceStatus'])
        if not self.graphs.winfo_manager():return
        run=self.controller.engine.run;elapsed=max(d['observedSeconds'],time.time()-run['at'])
        self.pies.draw({'items':d['items'],'observed_seconds':d['observedSeconds'],'excluded_seconds':max(0,elapsed-d['observedSeconds']),'coverage':d['observedSeconds']/elapsed if elapsed else 0,'unpriced':len(d['unpriced'])})
        c=self.line;c.delete('all');points=[p for p in d['points'] if p[1] is not None];w=max(400,c.winfo_width())
        c.create_text(10,12,text='CAPTURED VALUE · CURRENT QUOTES · OBSERVED SECONDS',anchor='w',fill='#cbbbdc',font=('Segoe UI',8))
        if len(points)>=2:
            xmax=max(1,points[-1][0]);ymax=max(1,max(p[1] for p in points));coords=[v for x,y in points for v in (20+(w-40)*x/xmax,130-95*y/ymax)]
            c.create_line(*coords,fill='#63d9cf',width=2);c.create_text(w-20,147,text=number(points[-1][1])+' silver',anchor='e',fill='#cbbbdc')
        self.details.set(('Model: '+str(m['mastery'])+' mastery from saved Imperial profile (0 = base assumption); '+str(m['retention'])+'% sale retention for profit range.\nModeled profit/hour: '+number(m['netPerHourLow'])+' to '+number(m['netPerHourHigh'])+f" · {m['pricedVariants']} / {m['variants']} priced variants.\n" if m else '')+f"Tool forecast models {d['scannedActions']:,.1f} actions from its verified scan (or remaining estimate after a recipe change), never the tool’s maximum capacity. Assumes this recipe continues. Yield and speed are estimates; rare/alchemy extras are not guaranteed. Main+rare outputs only in forecasts; captured extras count only when actually read. Ingredient costs use cheapest priced valid substitutions, not known consumed materials. This is not confirmed sale profit. "+('Recipe changed; forecast restarted from remaining durability. Earlier craft run stays saved.' if d['changedRecipe'] else ''))
