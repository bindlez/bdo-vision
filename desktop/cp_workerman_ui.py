"""Lazy native Workerman panel: no activity while collapsed or after calculation."""
import threading
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from workerman import reference_for,model_job


class CPWorkermanView:
    def __init__(self,parent,owner,saved=None):
        self.owner=owner;self.saved=dict(saved or {});self.frame=None;self.busy=False;self.reference=None;self.model=None
        self.parent=parent;self.fields={};self.jobs={}
        self.button=owner.app.text_button(parent,'WORKERMAN · MODEL MY CP PAYBACK',self.toggle);self.button.pack(fill='x',pady=8)

    def settings(self):return self.saved

    def toggle(self):
        if self.frame is not None and self.frame.winfo_manager():self.frame.pack_forget();return
        if self.frame is None:self.build()
        self.frame.pack(after=self.button,fill='x',pady=8)
        self.update()

    def build(self):
        c=self.owner.app.colors;self.frame=tk.Frame(self.parent,bg=c['panel'],padx=12,pady=12)
        tk.Label(self.frame,text='PUT NEW CP TO WORK',bg=c['panel'],fg=c['bright'],font=('Segoe UI Semibold',12)).pack(anchor='w')
        tk.Label(self.frame,text='One additional worker job · public Workerman averages + your cached market prices. No account access.',bg=c['panel'],fg=c['secondary'],wraplength=730,justify='left').pack(anchor='w',pady=5)
        row=tk.Frame(self.frame,bg=c['panel']);row.pack(fill='x')
        self.owner.app.text_button(row,'LOAD / REFRESH WORKERMAN',self.load).pack(side='left')
        self.owner.app.text_button(row,'REFRESH SHARED MARKET PRICES',self.refresh_prices).pack(side='left',padx=12)
        self.choice=tk.StringVar();self.picker=ttk.Combobox(self.frame,textvariable=self.choice,state='readonly',style='Vision.TCombobox');self.picker.pack(fill='x',pady=8);self.picker.bind('<<ComboboxSelected>>',lambda e:self.choose())
        inputs=tk.Frame(self.frame,bg=c['panel']);inputs.pack(fill='x')
        for i,(key,label,default) in enumerate((('workSpeed','Worker work speed',150),('moveSpeed','Worker move speed',7.5),('productivity','Node productivity %',0),('additionalCp','Additional CP needed',1),('operatingCost','Feeding / costs per full day',0))):
            cell=tk.Frame(inputs,bg=c['panel']);cell.grid(row=i//3,column=i%3,sticky='ew',padx=4,pady=4);inputs.columnconfigure(i%3,weight=1)
            tk.Label(cell,text=label,bg=c['panel'],fg=c['secondary'],font=('Segoe UI',9)).pack(anchor='w')
            self.fields[key]=tk.StringVar(value=str(self.saved.get(key,default)));ttk.Entry(cell,textvariable=self.fields[key],width=14,style='Vision.TEntry').pack(fill='x')
        self.giant=tk.BooleanVar(value=bool(self.saved.get('giant',False)))
        ttk.Checkbutton(self.frame,text='Use observed giant-worker yields',variable=self.giant,style='Vision.TCheckbutton').pack(anchor='w',pady=5)
        row=tk.Frame(self.frame,bg=c['panel']);row.pack(fill='x')
        self.owner.app.text_button(row,'CALCULATE PAYBACK',lambda:self.owner.recalculate()).pack(side='left')
        self.owner.app.text_button(row,'USE THIS JOB’S MINIMUM TARGET',self.use_target).pack(side='left',padx=12)
        self.status=tk.StringVar(value='Load public reference data when wanted. Existing CP income is never counted as new income.')
        tk.Label(self.frame,textvariable=self.status,bg=c['panel'],fg=c['text'],wraplength=730,justify='left').pack(anchor='w',pady=8)
        self.chart=tk.Canvas(self.frame,bg=c['panel'],height=180,highlightthickness=0);self.chart.pack(fill='x');self.chart.bind('<Configure>',lambda e:self.draw())
        tk.Label(self.frame,text='Full route CP is a starting estimate; confirm incremental connections, lodging and other CP yourself. Cost defaults to zero, so add feeding costs. Shared CP assumptions control sale retention, uptime, delay, ramp and setup. Luck drops, skills, stamina/refeeding interruptions and future market movement are excluded. One job only; unused new CP has no assumed income.',bg=c['panel'],fg=c['muted'],wraplength=730,justify='left',font=('Segoe UI',9)).pack(anchor='w')
        cached=self.provider().cached()
        if cached:self.accept(cached)

    def provider(self):return reference_for(str(Path(self.owner.tracker.insights.prices.path).parent))

    def background(self,action):
        if self.busy:return
        self.busy=True;self.status.set('Loading on demand. No game input or capture is used…')
        def run():
            try:result=action();error=None
            except Exception:result=None;error='Reference or market request unavailable. Cached data retained; try again later.'
            def finish():
                self.busy=False
                if not self.frame.winfo_exists():return
                if error:self.status.set(error);return
                if result:self.accept(result)
                self.owner.recalculate(save=False)
            try:self.owner.root.after(0,finish)
            except (RuntimeError,tk.TclError):pass
        threading.Thread(target=run,name='cp-workerman-on-demand',daemon=True).start()

    def load(self):self.background(self.provider().refresh)

    def refresh_prices(self):
        def action():
            import sqlite3
            from contextlib import closing
            prices=self.owner.tracker.insights.prices
            with closing(sqlite3.connect(prices.path)) as db:region=db.execute('SELECT region FROM market_context WHERE id=1').fetchone()[0]
            prices.recipe_market_snapshot(region);return None
        self.background(action)

    def accept(self,reference):
        self.reference=reference
        self.jobs={j['name']+' · '+j['town']+' · #'+j['id']:j for j in sorted(reference['jobs'],key=lambda j:(j['name'],j['id']))}
        self.picker.configure(values=tuple(self.jobs))
        chosen=next((name for name,j in self.jobs.items() if j['id']==str(self.saved.get('node',''))),next(iter(self.jobs)))
        self.choice.set(chosen)
        if 'additionalCp' not in self.saved:self.fields['additionalCp'].set(str(self.jobs[chosen]['connectionCp']))

    def choose(self):
        job=self.jobs.get(self.choice.get())
        if job:self.fields['additionalCp'].set(str(job['connectionCp']));self.owner.recalculate()

    def use_target(self):
        try:target=int(self.owner.fields['cp'].get())+int(self.fields['additionalCp'].get())
        except ValueError:return
        if target>600:self.status.set('This job exceeds the CP curve supported by this planner.');return
        self.owner.fields['target'].set(str(target));self.owner.recalculate()

    def update(self):
        if self.frame is None or not self.frame.winfo_manager():return
        report=getattr(self.owner,'report',None);job=self.jobs.get(self.choice.get());self.model=None;self.chart.delete('all')
        if not report:self.status.set('Correct the CP inputs above before calculating payback.');return
        if not job:return
        try:
            a={k:v.get() for k,v in self.fields.items()};a['giant']=self.giant.get()
            m=model_job(job,report,self.owner.tracker.insights.prices.all(),a)
        except ValueError as exc:self.status.set('Check worker assumptions: '+str(exc));return
        self.model=m;self.saved={**a,'node':job['id']}
        from cp_ui import silver,duration
        source=self.reference['revision'][:8]
        outputs='\n'.join(f"{p['name']}: {p['perDay']:,.1f}/full day × {silver(p['quote']['price'] if p['quote'] else None)} · {p['quote']['at'] if p['quote'] else 'unpriced'}" for p in m['outputs'])
        self.status.set(f"{job['town']} → {job['name']}\nFull route {job['connectionCp']} CP (housing excluded); your incremental requirement {m['requiredCp']} CP.\n{m['cycleMinutes']:.2f} min/cycle · {m['cyclesPerDay']:.1f} cycles/full day · {job['samples']} yield samples\n{outputs}\nModeled net/day after sale retention, declared costs and uptime: {silver(m['effectivePerDay'])}\nCP silver given up: {silver(m['opportunityCost'])} + setup {silver(report['setup'])}\nBreak-even: {duration(m['breakEvenDays'])} · day {report['days']} advantage over cash: {silver(m['differenceAtHorizon'])}\n{m['status']}\n{m['shortageItems']:,} additional byproducts needed; {m['unassignedCp']} new CP unassigned. Workerman revision {source}.")
        self.draw()

    def draw(self):
        if not self.model:return
        c=self.chart;c.delete('all');m=self.model
        if m['investment'] is None or m['effectivePerDay'] is None or m['effectivePerDay']<=0 or not m['eligible']:return
        points=m['timeline'];w=max(380,c.winfo_width());horizon=max(1,points[-1]['day']);high=max(1,m['investment'],max(p['earned'] for p in points));x=lambda d:65+d/horizon*(w-90);y=lambda v:140-v/high*110
        c.create_text(10,12,text='MODELED RECOVERY · INCOME LINE VS INVESTMENT LINE',anchor='w',fill='#cbbbdc',font=('Segoe UI',9))
        c.create_line(65,y(m['investment']),w-25,y(m['investment']),fill='#f2ca79',dash=(4,3))
        c.create_line(*[v for p in points for v in (x(p['day']),y(p['earned']))],fill='#70e6b3',width=2)
        c.create_text(65,160,text='0 days',anchor='w',fill='#b9adcb');c.create_text(w-25,160,text=f'{horizon:g} days',anchor='e',fill='#b9adcb')
