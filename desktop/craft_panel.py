"""Native recipe sidecar; calculations belong to the paired website engine."""
import time
import tkinter as tk
from tkinter import ttk
from craft_economy import recipes
from game_overlay import OverlaySurface,label,button,INK,PANEL,TEAL,VIOLET,MUTED
from overlay_layout import compact_silver


class CraftPanel:
    def __init__(self,live):
        self.live=live;self.app=live.grind.tracker.app;self.surface=None;self.request=None;self.pending=None;self.rows=[];self.amounts={};self.anchor=None;self.last_result=None;self.started=0;self.last_packet=None

    def toggle(self):
        if self.surface:self.close();return
        self.open()

    def open(self,show=True):
        if self.surface:return
        self.surface=OverlaySurface(self.app.root,'Vision · Craft companion',(380,580),{'corner':'top-right'})
        outer=self.surface.body
        actions=tk.Frame(outer,bg=PANEL);actions.pack(fill='x',side='bottom')
        canvas=tk.Canvas(outer,bg=INK,highlightthickness=0);scroll=ttk.Scrollbar(outer,orient='vertical',command=canvas.yview);scroll.pack(side='right',fill='y');canvas.pack(fill='both',expand=True);canvas.configure(yscrollcommand=scroll.set)
        box=tk.Frame(canvas,bg=INK);item=canvas.create_window(0,0,window=box,anchor='nw');box.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')));canvas.bind('<Configure>',lambda e:canvas.itemconfigure(item,width=e.width))
        from ui_scroll import enable_page_wheel
        enable_page_wheel(canvas)
        head=tk.Frame(box,bg=INK);head.pack(fill='x',padx=12,pady=7)
        label(head,'◇ CRAFT / SEARCH & PACK',10,VIOLET).pack(side='left');button(head,'×',self.close).pack(side='right')
        self.search=tk.StringVar();entry=tk.Entry(box,textvariable=self.search,bg=PANEL,fg='#f5f0ff',insertbackground=TEAL,relief='flat',font=('Segoe UI',11));entry.pack(fill='x',padx=12,ipady=6)
        self.results=tk.Listbox(box,height=4,bg=PANEL,fg='#e8ddf4',selectbackground='#493257',bd=0,highlightthickness=0,font=('Segoe UI',10),exportselection=False);self.results.pack(fill='x',padx=12,pady=5)
        self.search.trace_add('write',lambda *args:self.find());self.results.bind('<<ListboxSelect>>',self.choose)
        self.title=label(box,'Choose a recipe',12,TEAL,anchor='w');self.title.pack(fill='x',padx=12)
        saved=self.app.loot.platform_preferences.get('craft_companion',{})
        if not isinstance(saved,dict):saved={}
        fields=tk.Frame(box,bg=INK);fields.pack(fill='x',padx=12,pady=5);self.fields={}
        for i,(key,title,value) in enumerate([('maximum','Maximum LT',''),('current','Carried LT',''),('reserve','Reserve LT','25'),('tool','Tool uses','')]):
            cell=tk.Frame(fields,bg=INK);cell.grid(row=i//2,column=i%2,sticky='ew',padx=3);fields.columnconfigure(i%2,weight=1)
            label(cell,title,8,MUTED).pack(anchor='w');v=self.fields[key]=tk.StringVar(value=str(saved.get(key,value))[:100])
            e=tk.Entry(cell,textvariable=v,bg=PANEL,fg='#f5f0ff',insertbackground=TEAL,relief='flat',width=12);e.pack(fill='x',ipady=3);e.bind('<Return>',lambda e:self.calculate());e.bind('<FocusOut>',lambda e:self.calculate())
        self.limit=tk.StringVar(value='hybrid');modes=tk.Frame(box,bg=INK);modes.pack(fill='x',padx=12)
        for value,text in [('hybrid','Weight + tool'),('ingredients','Weight only')]:tk.Radiobutton(modes,text=text,variable=self.limit,value=value,command=self.calculate,bg=INK,fg='#ded2ed',selectcolor=PANEL,activebackground=INK).pack(side='left')
        self.forecasts=tk.BooleanVar(value=self.app.loot.platform_preferences.get('craft_gap_forecast',True))
        def forecast_toggle():self.app.loot.platform_preferences['craft_gap_forecast']=self.forecasts.get();self.app.save_quietly()
        tk.Checkbutton(box,text='Show labeled forecasts during capture gaps',variable=self.forecasts,command=forecast_toggle,bg=INK,fg='#ded2ed',selectcolor=PANEL,activebackground=INK).pack(anchor='w',padx=12)
        self.milestones=tk.BooleanVar(value=self.app.loot.platform_preferences.get('craft_milestone_reveals',False))
        def milestone_toggle():self.app.loot.platform_preferences['craft_milestone_reveals']=self.milestones.get();self.app.save_quietly()
        tk.Checkbutton(box,text='Craft milestones (uses drop reveals)',variable=self.milestones,command=milestone_toggle,bg=INK,fg='#ded2ed',selectcolor=PANEL,activebackground=INK).pack(anchor='w',padx=12)
        self.independent=tk.BooleanVar(value=False)
        tk.Checkbutton(box,text='Edit ingredient quantities independently',variable=self.independent,command=self.calculate,bg=INK,fg='#ded2ed',selectcolor=PANEL,activebackground=INK).pack(anchor='w',padx=12)
        self.ingredients=tk.Frame(box,bg=INK);self.ingredients.pack(fill='x',padx=12)
        self.metrics=label(box,'',11,TEAL,anchor='w',justify='left');self.metrics.pack(fill='x',padx=12,pady=6)
        self.status=label(box,'Keep the paired crafting website open to calculate.\nPress Enter after editing a quantity.',9,MUTED,wraplength=350,justify='left',anchor='w');self.status.pack(fill='x',padx=12)
        button(actions,'WEBSITE',self.website,VIOLET).pack(side='left');button(actions,'USE SNAPSHOT',self.snapshot,TEAL).pack(side='left');button(actions,'FILL MAX',self.maximum,TEAL).pack(side='right')
        button(actions,'TIMER',lambda:self.calculate(start=True),TEAL).pack(side='right')
        self.find();self.retile()
        run=self.app.loot.auto_craft.engine.run
        if run and run.get('tool')==self.app.session_id and self.app.running:
            from auto_craft import families
            family=families()[0].get(run['family'])
            if family:
                self.search.set(family['name']);self.results.selection_set(0);self.choose()
        if show:self.surface.show(interactive=True);entry.focus_set()

    def website(self):
        import webbrowser
        bridge=getattr(self.app,'bridge',None)
        if bridge and bridge.base_url:webbrowser.open_new_tab(bridge.base_url+'/planner#companion')
        else:self.status.configure(text='The local planner connection is unavailable.')

    def find(self):
        if not self.surface:return
        q=self.search.get().strip().casefold();self.matches=[r for r in recipes() if r['type'] in ('cooking','alchemy') and not str(r.get('method','')).startswith('imperial') and q in r['name'].casefold()][:30]
        self.results.delete(0,'end')
        for r in self.matches:self.results.insert('end',r['name']+' / '+r['type'])

    def choose(self,event=None):
        picks=self.results.curselection()
        if not picks:return
        self.recipe=self.matches[picks[0]];self.title.configure(text=self.recipe['name']);self.amounts={};self.anchor=None;self.last_result=None
        self.snapshot();self.calculate()

    def snapshot(self):
        snap=getattr(getattr(self.app,'inventory',None),'snapshot',{}) or {}
        for key in ('maximum','current'):
            if snap.get(key) is not None:self.fields[key].set(str(snap[key]))
        if self.app.has_reading:self.fields['tool'].set(str(max(0,int(self.app.value))));self.last_tool=self.fields['tool'].get()
        self.bag={str(row['id']):row['quantity'] for row in snap.get('items',[]) if row.get('id') and row.get('quantity') is not None}
        if snap:self.status.configure(text='Partial inventory snapshot / '+time.strftime('%H:%M:%S',time.localtime(snap['at']))+'. Verify carried items and weight.')
        self.calculate()

    def maximum(self):self.amounts={};self.anchor=None;self.independent.set(False);self.calculate()

    def calculate(self,start=False):
        if not self.surface or not getattr(self,'recipe',None):return
        bridge=getattr(self.app,'bridge',None)
        if not bridge or not bridge.server:self.status.configure(text='Open the paired website from Vision.');return
        try:
            if self.app.has_reading and self.fields['tool'].get()==getattr(self,'last_tool',None):
                self.last_tool=str(max(0,int(self.app.value)));self.fields['tool'].set(self.last_tool)
            values={key:float(v.get()) if v.get().strip() else None for key,v in self.fields.items()}
            if any(values[key] is None for key in ('maximum','current','reserve')):raise ValueError('Enter maximum and carried LT, or use an inventory snapshot.')
            body={'recipe':self.recipe['id'],'start':start,'seconds':float(self.app.speed.get()),**values,'limit':self.limit.get(),'independent':self.independent.get(),'amounts':dict(self.amounts),'anchor':self.anchor,'bag':getattr(self,'bag',{})}
            self.last_packet=None;self.request=bridge.request_craft_panel(body);self.started=time.monotonic();self.status.configure(text='Calculating with the paired website…')
        except (ValueError,TypeError) as exc:self.status.configure(text=str(exc))

    def refresh(self):
        if not self.surface or not self.request:return
        bridge=getattr(self.app,'bridge',None)
        if not bridge:return
        with bridge._lock:packet=bridge.craft_panel_result
        if not packet or packet['id']!=self.request:
            if time.monotonic()-self.started>8:self.status.configure(text='Waiting for the paired website. Click WEBSITE and leave its tab open.');self.started=time.monotonic()
            return
        if self.last_packet==packet['at']:return
        self.last_packet=packet['at'];r=packet['result']
        if r.get('error'):self.status.configure(text=str(r['error'])[:300]);return
        if not isinstance(r.get('rows'),list) or len(r['rows'])>12:return
        self.last_result=r
        for widget in self.ingredients.winfo_children():widget.destroy()
        self.input_vars={}
        for row in r['rows']:
            line=tk.Frame(self.ingredients,bg=INK);line.pack(fill='x',pady=2)
            label(line,str(row['name'])[:34]+' / '+str(row['ratio'])+'×',9,MUTED).pack(side='left')
            value=self.amounts.get(str(row['id'])) if self.independent.get() else row['quantity'];v=tk.StringVar(value=str(value if value is not None else row['quantity']))
            self.input_vars[str(row['id'])]=v
            if str(row['id']) not in self.amounts:self.amounts[str(row['id'])]=str(row['quantity'])
            entry=tk.Entry(line,textvariable=v,width=10,bg=PANEL,fg='#f5f0ff',insertbackground=TEAL,relief='flat');entry.pack(side='right')
            def changed(event,ident=str(row['id']),variable=v):
                self.amounts={key:variable.get() for key,variable in self.input_vars.items()};self.anchor=int(ident);self.calculate()
            entry.bind('<Return>',changed)
        self.metrics.configure(text=f"{r['batches']:,} crafts / max {r['maxCrafts']:,}  ·  {r['seconds']/60:,.1f} min planned\nExpected output {r['output']:,.1f}  ·  Est. net/h {compact_silver(r.get('perHour'))}\nEst. gross {compact_silver(r.get('gross'))}  ·  Net {compact_silver(r.get('profit'))}")
        self.status.configure(text=('Planning timer started. Begin crafting in game yourself. ' if r.get('timerStarted') else '')+r.get('note','')[:300])

    def retile(self):
        if self.surface:
            parent=self.live.hud.surface.rect if self.live.hud else None
            if parent:self.surface.options['position']=list(parent[:2])
            self.surface.place(parent)

    def close(self):
        bridge=getattr(self.app,'bridge',None)
        if bridge:
            with bridge.craft_condition:
                if bridge.craft_panel_request and bridge.craft_panel_request['id']==self.request:
                    bridge.craft_panel_request=None;bridge.craft_condition.notify_all()
        if self.surface:
            self.app.loot.platform_preferences['craft_companion']={key:v.get()[:100] for key,v in self.fields.items()}
            self.app.save_quietly();self.surface.close();self.surface=None
        self.request=None
