"""Native CP calculator. Lazy data, event-only work, shared market cache, no tick."""
import threading
import time
import uuid
import json
import sqlite3
import math
from contextlib import closing
import webbrowser
import tkinter as tk
from tkinter import ttk
from cp_planner import calculate,data,build_route
from cp_forecast import analyze,income_at,productive_days
from ocr_debug import OCRReaderView


def silver(n):
    if n is None:return '—'
    return f'{n/1e9:,.2f}B' if abs(n)>=1e9 else f'{n/1e6:,.2f}M' if abs(n)>=1e6 else f'{n:,.0f}'


def duration(days):
    if days is None:return 'Not reached'
    if days==0:return 'No investment'
    if days>3650:return '10+ years'
    return f'{days:.1f} days' if days<60 else f'{days/30.4375:.1f} months' if days<730 else f'{days/365.25:.1f} years'


class CPInfo:
    def __init__(self,tracker,settings):
        self.tracker=tracker;self.app=tracker.app;self.root=tracker.root
        self.saved=settings.get('cp_plan',{});self.frame=None;self.fields={};self.stock={}
        self.busy=False;self.quote_busy=False;self.gate_acquired=False;self.reading={'stage':'idle','message':'No CP snapshot requested'}
        self.reader=OCRReaderView(self.app,'CP HUD · one-shot reading',self.read_once)

    def build(self,tabs):
        from ui_scroll import notebook_page
        c=self.app.colors;self.frame,body=notebook_page(tabs,'CP Info',c)
        tk.Label(body,text='CP INTELLIGENCE',font=('Segoe UI Semibold',16),bg=c['bg'],fg=c['text']).pack(anchor='w',pady=(4,6))
        tk.Label(body,text='Cash now, more CP, or reach a target and keep the rest. No background scanning.',bg=c['bg'],fg=c['secondary']).pack(anchor='w')
        actions=tk.Frame(body,bg=c['bg']);actions.pack(fill='x',pady=10)
        for title,action in [('FULL PLANNER + GRAPHS',self.open_browser),('READ CP ONCE',self.read_once),('CP OCR READER',self.reader.open)]:
            self.app.text_button(actions,title,action).pack(side='left',padx=(0,12))
        grid=tk.Frame(body,bg=c['bg']);grid.pack(fill='x')
        definitions=[('cp','Total CP (not unused)',490),('percent','CP progress %',19.26),('target','Target CP',500),('days','Simulation days',90),('income','Extra net income / day',0),('retention','Market sale retained %',84.5)]
        for i,(key,label,default) in enumerate(definitions):
            cell=tk.Frame(grid,bg=c['bg']);cell.grid(row=i//3,column=i%3,sticky='ew',padx=5,pady=5);grid.columnconfigure(i%3,weight=1)
            tk.Label(cell,text=label,bg=c['bg'],fg=c['secondary'],font=('Segoe UI',9)).pack(anchor='w')
            self.fields[key]=tk.StringVar(value=str(self.saved.get(key,default)))
            ttk.Entry(cell,textvariable=self.fields[key],width=16,style='Vision.TEntry').pack(fill='x')
        stocks=tk.Frame(body,bg=c['bg']);stocks.pack(fill='x',pady=8)
        for i,p in enumerate(data()['products']):
            cell=tk.Frame(stocks,bg=c['bg']);cell.pack(side='left',fill='x',expand=True,padx=5)
            tk.Label(cell,text=p['name'],bg=c['bg'],fg=c['secondary'],font=('Segoe UI',9)).pack(anchor='w')
            default=750000 if p['key']=='catalyst' else 0
            self.stock[p['key']]=tk.StringVar(value=str(self.saved.get('counts',{}).get(p['key'],default)))
            ttk.Entry(cell,textvariable=self.stock[p['key']],width=20,style='Vision.TEntry').pack(fill='x')
        self.options=tk.Frame(body,bg=c['panel'],padx=8,pady=8)
        options=[('deploy','Max new CP actually used',100),('delay','Income delay · days',0),('utilization','Uptime / utilization %',100),('ramp','Ramp to full income · days',0),('setup','One-time setup silver',0),('reserve','Minimum cash to keep',0),('grindRate','Optional grind silver / hour',0),('split','Custom stock to CP %',50)]
        for i,(key,label,default) in enumerate(options):
            cell=tk.Frame(self.options,bg=c['panel']);cell.grid(row=i//3,column=i%3,sticky='ew',padx=5,pady=5);self.options.columnconfigure(i%3,weight=1)
            tk.Label(cell,text=label,bg=c['panel'],fg=c['secondary'],font=('Segoe UI',9)).pack(anchor='w')
            self.fields[key]=tk.StringVar(value=str(self.saved.get(key,default)));ttk.Entry(cell,textvariable=self.fields[key],width=16,style='Vision.TEntry').pack(fill='x')
        self.fields['incomeMode']=tk.StringVar(value='Whole project / day' if self.saved.get('incomeMode')=='project' else 'Per deployed CP / day')
        ttk.Combobox(self.options,textvariable=self.fields['incomeMode'],values=('Per deployed CP / day','Whole project / day'),state='readonly',style='Vision.TCombobox',width=23).grid(row=3,column=0,columnspan=2,sticky='ew',padx=5)
        policy_names={'market':'Material exchanges','vendor':'Direct NPC sale','best':'Best priced option'}
        self.fields['cashPolicy']=tk.StringVar(value=policy_names.get(self.saved.get('cashPolicy','market'),'Material exchanges'))
        ttk.Combobox(self.options,textvariable=self.fields['cashPolicy'],values=tuple(policy_names.values()),state='readonly',style='Vision.TCombobox',width=20).grid(row=3,column=2,sticky='ew',padx=5)
        self.control_row=row=tk.Frame(body,bg=c['bg']);row.pack(fill='x',pady=8)
        self.app.action(row,'CALCULATE + SAVE',self.recalculate,primary=True).pack(side='left')
        self.app.text_button(row,'REFRESH EXISTING MARKET PRICES',self.refresh_prices).pack(side='left',padx=14)
        self.app.text_button(row,'ASSUMPTIONS',self.toggle_options).pack(side='left')
        self.note=tk.StringVar(value='Saved scenario · edit stock and income assumptions, then calculate.' if self.saved else 'First-use example: 750,000 catalysts at 490 CP + 19.26%. Edit to your actual stock. Income defaults to zero.')
        tk.Label(body,textvariable=self.note,bg=c['bg'],fg=c['bright'],wraplength=740,justify='left').pack(fill='x',pady=6)
        from cp_target_ui import CPTargetView
        self.target_view=CPTargetView(body,self)
        from cp_workerman_ui import CPWorkermanView
        self.workerman=CPWorkermanView(body,self,self.saved.get('workerman'))
        self.selected=tk.StringVar(value='Target, then cash');picker=ttk.Combobox(body,textvariable=self.selected,values=('Cash everything','All CP','Target, then cash','Custom split'),state='readonly',style='Vision.TCombobox');picker.pack(fill='x',pady=6);picker.bind('<<ComboboxSelected>>',lambda event:self.recalculate(save=False))
        pages=ttk.Notebook(body,style='Vision.TNotebook');pages.pack(fill='x',pady=8)
        self.text_views={}
        for title in ('Decision','Payback','Milestones','Model','Exchanges','CP curve'):
            panel=tk.Frame(pages,bg=c['panel']);pages.add(panel,text=title)
            text=tk.Text(panel,height=11,bg=c['panel'],fg=c['text'],font=('Consolas',10),relief='flat',wrap='word',state='disabled');scroll=ttk.Scrollbar(panel,command=text.yview);text.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');text.pack(fill='both',expand=True);self.text_views[title]=text
        self.results=self.text_views['Decision']
        self.chart_mode=tk.StringVar(value='Cash outcomes');chart_picker=ttk.Combobox(body,textvariable=self.chart_mode,values=('Cash outcomes','Allocation frontier','Income sensitivity'),state='readonly',style='Vision.TCombobox');chart_picker.pack(fill='x',pady=4);chart_picker.bind('<<ComboboxSelected>>',lambda e:self.draw_chart())
        self.chart=tk.Canvas(body,height=145,bg=c['panel'],highlightthickness=0);self.chart.pack(fill='x')
        self.chart.bind('<Button-1>',self.choose_frontier)
        self.elapsed=tk.DoubleVar(value=0);self.recovery=tk.StringVar(value='Modeled recovery · not recorded income')
        self.simulation_scale=ttk.Scale(body,from_=0,to=90,variable=self.elapsed,command=lambda day:self.update_recovery(float(day)));self.simulation_scale.pack(fill='x')
        tk.Label(body,textvariable=self.recovery,bg=c['bg'],fg=c['secondary'],wraplength=730,justify='left').pack(anchor='w')
        self.recovery_bar=ttk.Progressbar(body,maximum=100);self.recovery_bar.pack(fill='x',pady=5)
        solvers=tk.Frame(body,bg=c['bg']);solvers.pack(fill='x',pady=4)
        self.app.text_button(solvers,'APPLY BEST AFFORDABLE TARGET',self.apply_best).pack(side='left')
        self.payback_goal=tk.StringVar(value='90');ttk.Combobox(solvers,textvariable=self.payback_goal,values=(30,90,180,365,730),width=6,style='Vision.TCombobox').pack(side='left',padx=8)
        self.app.text_button(solvers,'SET INCOME FOR PAYBACK DAYS',self.solve_income).pack(side='left')
        self.chart.bind('<Configure>',lambda e:self.draw_chart())
        tk.Label(body,text='Current market quotes from the existing price book. Market material exchanges are the primary cash route. Unknown exchange prices remain unpriced; leftovers stay in inventory. Future income is modeled, never added to your loot history.',bg=c['bg'],fg=c['muted'],font=('Segoe UI',9),wraplength=740,justify='left').pack(fill='x',pady=8)
        self.recalculate(save=False)
        tabs.bind('<<NotebookTabChanged>>',lambda event:self.recalculate(save=False) if tabs.select()==str(self.frame) else None,add='+')

    def settings(self):return {'cp_plan':{**self.saved,**({'workerman':self.workerman.settings()} if hasattr(self,'workerman') else {})}}

    def toggle_options(self):
        if self.options.winfo_manager():self.options.pack_forget()
        else:self.options.pack(before=self.control_row,fill='x',pady=8)

    def recalculate(self,save=True):
        if not self.fields:return
        state={k:v.get() for k,v in self.fields.items()};state['counts']={k:v.get() for k,v in self.stock.items()}
        state['incomeMode']='project' if state['incomeMode']=='Whole project / day' else 'per_cp'
        state['cashPolicy']={'Material exchanges':'market','Direct NPC sale':'vendor','Best priced option':'best'}.get(state['cashPolicy'],state['cashPolicy'])
        try:report=calculate(state,self.tracker.insights.prices.all())
        except ValueError as exc:
            self.note.set('Check your values: '+str(exc));self.target_view.invalid(str(exc));self.report=None;self.chart.delete('all');self.workerman.update();return False
        self.saved=state;self.report=report
        self.target_view.update(report)
        self.workerman.update()
        self.populate_reference(report)
        if self.app.bridge:
            with self.app.bridge._lock:self.app.bridge.cp_plan=json.loads(json.dumps(state))
        if save:self.app.save_quietly();self.note.set('Saved locally. No extra CP income is assumed until you enter it.' if report['income']==0 else 'Saved scenario · future income is an assumption, not recorded silver.')
        selected_key=self.selected_key()
        if not report['cashComplete']:
            text='MARKET PRICES NEEDED\nRefresh existing market prices to calculate material-exchange value. No NPC fallback is used.\n\n'+f"All CP: {report['routes'][1]['cp']} CP (+{report['routes'][1]['gained']})\nTo {report['target']} CP: {report['targetBatches']:,} full batches / {report['targetXp']:,.0f} EXP\n\nUnquoted rewards: "+', '.join(report['missing'])
            for key in ('Decision','Payback','Milestones','Model'):
                view=self.text_views[key];view.configure(state='normal');view.delete('1.0','end');view.insert('1.0',text);view.configure(state='disabled')
            self.analysis=None;self.update_recovery(0);self.draw_chart();return True
        a=analyze(report,selected_key);chosen=next(row for row in report['routes'] if row['key']==selected_key)
        self.analysis=a;self.simulation_scale.configure(to=report['days']);self.elapsed.set(min(self.elapsed.get(),report['days']));self.update_recovery(self.elapsed.get())
        labels=('CASH EVERYTHING','ALL AVAILABLE CP','TARGET, THEN CASH','50% OF BATCHES TO CP')
        lines=[f"To next CP: {report['nextXp']:,.2f} EXP / {report['nextBatches']:,} batches",f"To {report['target']} CP: {report['targetXp']:,.2f} EXP / {report['targetBatches']:,} batches",f"Available: {report['totalXp']:,} EXP · optional NPC alternative {silver(report['vendorTotal'])} silver",'']
        for title,r in zip(labels,report['routes']):
            percent=f" + {r['percent']:.2f}%" if r['percent'] is not None else ' · curve limit'
            lines.append(f"{title}: {r['cp']} CP{percent} (+{r['gained']})\n  Cash now {silver(r['cash'])} · day {report['days']} {silver(r['future'])} · vs cash {silver(r['difference'])}")
        all_cp=report['routes'][1]
        if all_cp['requiredPerCpDay'] is not None:lines.append(f"All-CP break-even requirement: {all_cp['requiredPerCpDay']:,.0f} silver / deployed CP / day over {report['days']} days")
        if report['missing']:lines.append(f"Incomplete prices: {len(report['missing'])} rewards. Best means best available material exchange; unknown alternatives may be better.")
        if not report['targetReachable']:lines.append('Target not fully covered by this stock.')
        decision=[a['title'].upper(),a['reason'],f"Payback: {duration(chosen['breakEvenDays'])}",f"Investment: {silver(chosen['investment'])} · extra net/day: {silver(chosen['daily'])}",f"Day {report['days']}: {chosen['recoveryPercent']:.1f}% recovered · CP minus cash {silver(chosen['difference'])}",'',*lines]
        payoff=['PAYBACK TARGETS · daily income required after delay / ramp',*[(f"{row['day']:>3} days: {silver(row['daily'])}/day total · {silver(row['perCp'])} per CP/day before uptime") for row in a['requirements']], '','INCOME STRESS TEST · modeled, not tracked',*[f"{row['label']}: {duration(row['payback'])} · day {report['days']} CP minus cash {silver(row['difference'])}" for row in a['scenarios']], '','OUTCOME LEDGER',*[f"Day {row['day']:>3}: extra {silver(row['earned'])} · versus cash {silver(row['difference'])}" for row in a['timeline']]]
        best=a['optimized'];milestones=[('Best modeled affordable target: '+str(best['cp'])+' CP · keep '+silver(best['cash'])) if best else 'No route can keep the chosen cash reserve.',f"{a['candidates']} whole-CP targets checked · reserve {silver(report['reserve'])}",'',*[f"{row['target']} CP: invest {silver(row['investment'])} · keep {silver(row['cash'])} · payback {duration(row['breakEvenDays'])}" for row in a['targets']], '', 'RECOVERY LADDER · projected checkpoints only',*[f"{int(row['fraction']*100)}% recovered: {duration(row['day'])}" for row in a['milestones']]]
        model=[f"Income basis: {self.fields['incomeMode'].get()} · {chosen['deployed']} new CP deployed of {chosen['gained']} gained",f"Uptime {report['utilization']}% · delay {report['delay']}d · ramp {report['ramp']}d",f"Foregone cash {silver(chosen['foregone'])} + setup {silver(chosen['setupCost'])} = investment {silver(chosen['investment'])}",f"Cost / whole CP {silver(chosen['costPerCp'])} · / deployed CP {silver(chosen['costPerDeployedCp'])}",f"Missing exchange prices: {len(report['missing'])}",'','Income ramps linearly after the delay. Break-even solves cumulative additional income = investment. No interest, future byproduct production or automatic item sales are assumed. Whole-project income scales by deployed CP relative to the all-CP plan. Milestones are a simulation, not earned achievements. Open Full Planner for interactive graphs, target solvers and sensitivity tables.']
        for title,values in [('Decision',decision),('Payback',payoff),('Milestones',milestones),('Model',model)]:
            text=self.text_views[title];text.configure(state='normal');text.delete('1.0','end');text.insert('1.0','\n'.join(values));text.configure(state='disabled')
        self.draw_chart()
        return True

    def selected_key(self):return {'Cash everything':'cash','All CP':'cp','Target, then cash':'target','Custom split':'split'}[self.selected.get()]

    def populate_reference(self,report):
        exchanges=['ALL EXCHANGE OPTIONS · one reward per bundle, not all rewards together','Market material exchanges are the default. NPC sale is only used if explicitly selected.','']
        for p in report['products']:
            exchanges.extend([p['name']+f" · {p['batch']} items → {p['xp']} CP EXP",'Exchange NPC: '+p['npc']])
            for r in p['routes']:
                exchanges.append(f"  {r['item']} × {r['units']} / bundle · unit {silver(r['unit'])} · stock net {silver(r['net'])} · {r['source']}")
            exchanges.append('')
        spec=data();curve=['CURRENT CP → NEXT POINT · EXP REQUIRED','Complete exchange quantities always round up. Higher brackets apply as you gain CP.','']
        for i,(start,xp) in enumerate(spec['curve']):
            end=spec['curve'][i+1][0]-1 if i+1<len(spec['curve']) else 599
            curve.append(f"{start}–{end} CP: {xp:,} EXP / point · {xp/90:,.2f} 10-item byproducts or {xp/45:,.2f} Blush Leaves per CP (continuous efficiency).")
        for title,lines in [('Exchanges',exchanges),('CP curve',curve)]:
            widget=self.text_views[title];widget.configure(state='normal');widget.delete('1.0','end');widget.insert('1.0','\n'.join(lines));widget.configure(state='disabled')

    def update_recovery(self,day):
        r=getattr(self,'report',None)
        if not r or not hasattr(self,'recovery_bar'):return
        if not r['cashComplete']:self.recovery.set('Refresh exchange prices to model recovery. Quantities remain available.');self.recovery_bar['value']=0;return
        route=next(a for a in r['routes'] if a['key']==self.selected_key());earned=income_at(r,route,max(0,min(r['days'],day)));investment=route['investment']
        recovered=min(100,earned/investment*100) if investment else 100
        self.recovery_bar['value']=recovered;self.recovery.set(f"SIMULATION · day {day:.1f}: {silver(earned)} extra income · {recovered:.1f}% investment recovered · versus cash {silver(earned-investment)}. Not recorded silver.")

    def apply_best(self):
        analysis=getattr(self,'analysis',None);best=analysis.get('optimized') if analysis else None
        if not best:self.note.set('Refresh prices and check your cash reserve before solving a target.');return
        self.fields['target'].set(str(best['cp']));self.selected.set('Target, then cash');self.recalculate()

    def solve_income(self):
        r=getattr(self,'report',None)
        if not r or not r['cashComplete']:self.note.set('Refresh prices before solving income.');return
        try:days=float(self.payback_goal.get())
        except ValueError:self.note.set('Enter valid payback days.');return
        if not math.isfinite(days) or not 0<days<=3650:self.note.set('Payback days must be 1–3,650.');return
        route=next(a for a in r['routes'] if a['key']==self.selected_key());effective=productive_days(days,r['delay'],r['ramp']);factor=route['deployed']*r['utilization']/100
        if not effective or not factor:self.note.set('The route needs deployed new CP, uptime and productive days to repay its cost.');return
        income=math.ceil(route['investment']/(effective*factor)*(r['referenceDeployed'] if r['incomeMode']=='project' else 1))
        self.fields['income'].set(str(income));self.recalculate()

    def choose_frontier(self,event):
        points=getattr(self,'frontier_points',[])
        if not points:return
        best=min(points,key=lambda p:(p[0]-event.x)**2+(p[1]-event.y)**2)
        if (best[0]-event.x)**2+(best[1]-event.y)**2>144:return
        self.fields['split'].set(str(best[2]));self.selected.set('Custom split');self.recalculate(save=False)

    def draw_analysis_chart(self,r,mode):
        c=self.chart;w=max(380,c.winfo_width())
        if mode=='Allocation frontier':
            samples=[build_route(r,'split',math.floor(r['totalBatches']*i/20)) for i in range(21)]
            points=[(v['gained'],v['cash'],i*5) for i,v in enumerate(samples)];title='ALLOCATION FRONTIER · CLICK A POINT TO CHOOSE YOUR SPLIT';xlabel='new whole CP'
        else:
            a=getattr(self,'analysis',None)
            if not a:return
            points=[(p['multiplier'],p['difference'],None) for p in a['sensitivity']];title='INCOME SENSITIVITY · 0× TO 2× YOUR EXTRA INCOME';xlabel='income multiplier'
        if not points:return
        xmax=max(1,max(p[0] for p in points));low=min(0,min(p[1] for p in points));high=max(1,max(p[1] for p in points));xx=lambda x:68+x/xmax*(w-88);yy=lambda y:109-(y-low)/(high-low)*77
        c.create_text(10,12,text=title,anchor='w',fill='#cbbbdc',font=('Segoe UI',9))
        if low<0:c.create_line(68,yy(0),w-20,yy(0),fill='#67526f')
        c.create_line(*[v for p in points for v in (xx(p[0]),yy(p[1]))],fill='#c3a0ff',width=2)
        c.create_text(62,32,text=silver(high),anchor='e',fill='#b9adcb',font=('Segoe UI',8));c.create_text(62,109,text=silver(low),anchor='e',fill='#b9adcb',font=('Segoe UI',8));c.create_text(w-20,130,text=str(xmax)+' '+xlabel,anchor='e',fill='#b9adcb',font=('Segoe UI',8))
        if mode=='Allocation frontier':
            self.frontier_points=[(xx(p[0]),yy(p[1]),p[2]) for p in points]
            for x,y,_ in self.frontier_points:c.create_oval(x-3,y-3,x+3,y+3,fill='#f2ca79',outline='')

    def draw_chart(self):
        if not getattr(self,'chart',None) or not getattr(self,'report',None):return
        c=self.chart;c.delete('all');r=self.report
        self.frontier_points=[]
        if not r['cashComplete']:c.create_text(12,20,text='Refresh exchange prices to unlock silver graphs.',anchor='w',fill='#b9adcb');return
        mode=self.chart_mode.get()
        if mode!='Cash outcomes':self.draw_analysis_chart(r,mode);return
        w=max(380,c.winfo_width());maximum=max(1,max(a['future'] for a in r['routes'][:3]));minimum=min(0,min(a['cash'] for a in r['routes'][:3]))
        c.create_text(10,12,text='CASH + EXTRA MODELED INCOME · DAY 0 → '+str(r['days']),anchor='w',fill='#cbbbdc',font=('Segoe UI',9))
        for n,(a,color) in enumerate(zip(r['routes'][:3],('#70e6b3','#c3a0ff','#f2ca79'))):
            points=[]
            for day in sorted(set([r['days']*i/24 for i in range(25)]+[min(r['days'],r['delay']),min(r['days'],r['delay']+r['ramp'])])):
                points.extend((12+(w-24)*day/r['days'],112-(a['cash']+income_at(r,a,day)-minimum)/(maximum-minimum)*80))
            c.create_line(*points,fill=color,width=2)
            c.create_text(12+n*180,119,text=('Cash','All CP','Target')[n]+': '+silver(a['future']),anchor='w',fill=color,font=('Segoe UI',9))

    def open_browser(self):
        if not self.recalculate():return
        if self.app.bridge and self.app.bridge.base_url:webbrowser.open(self.app.bridge.base_url+'/planner?cp_native=1#cp')

    def refresh_prices(self):
        if self.quote_busy:return
        self.quote_busy=True;self.note.set('One market request for exact reward names · using your existing price book…')
        prices=self.tracker.insights.prices
        def worker():
            try:
                with closing(sqlite3.connect(prices.path)) as db:region=db.execute('SELECT region FROM market_context WHERE id=1').fetchone()[0]
                from craft_economy import craft_spec
                wanted={name for p in data()['products'] for name,_ in p['rewards']}
                received=prices.recipe_id_quotes([m['id'] for m in craft_spec()['items'].values() if m['name'] in wanted],region)
                message=f'{len(received)} market prices refreshed. Missing prices remain unpriced.'
            except Exception:message='Market refresh unavailable. Cached quotes and NPC values are retained.'
            def finish():
                self.quote_busy=False
                if self.frame and self.frame.winfo_exists():self.recalculate(save=False);self.note.set(message)
            try:self.root.after(0,finish)
            except RuntimeError:pass
        threading.Thread(target=worker,name='cp-market-on-demand',daemon=True).start()

    def publish(self,**value):
        self.reading=value
        bridge=self.app.bridge
        if bridge:
            with bridge._lock:bridge.cp_reading=dict(value)

    def read_once(self,request_id=None):
        ident=request_id or uuid.uuid4().hex
        if self.busy:return
        if self.app.lite_use.get():
            self.publish(stage='rejected',requestId=ident,message='Lite Use stops all extra OCR. Turn it off for an explicit CP snapshot.');self.app.status.set(self.reading['message']);return
        self.busy=True;self.publish(stage='waiting',requestId=ident,message='Bring BDO to the front · snapshot in 3 seconds')
        self.app.status.set(self.reading['message'])
        executable=self.app.tess.get();token=self.reader.token()
        def start():
            if self.app.lite_use.get():self.finish_read(ident,None,None,'Lite Use was enabled; no CP capture taken.',token);return
            if getattr(self.app,'busy',False) or self.tracker.busy:self.finish_read(ident,None,None,'Another OCR reader is busy. No CP read was attempted; try again when idle.',token);return
            bridge=self.app.bridge
            if bridge:
                self.gate_acquired=bridge.gear_ocr_gate.acquire(blocking=False)
                if not self.gate_acquired:self.finish_read(ident,None,None,'Equipment OCR is busy. No additional reader was started.',token);return
            self.app.cp_ocr_busy=True
            def worker():
                image=None;result=None
                try:
                    from cp_reader import capture_once
                    result,image,detail=capture_once(executable)
                except Exception as exc:detail=str(exc)[:800]
                try:self.root.after(0,lambda:self.finish_read(ident,result,image,detail,token))
                except RuntimeError:pass
            threading.Thread(target=worker,name='cp-one-shot-ocr',daemon=True).start()
        self.root.after(3000,start)

    def finish_read(self,ident,result,image,detail,token):
        self.busy=False;self.app.cp_ocr_busy=False
        if self.gate_acquired:
            self.app.bridge.gear_ocr_gate.release();self.gate_acquired=False
        if self.app.lite_use.get():result=None;detail='Lite Use enabled during read; values preserved.'
        message='Accepted: two HUD passes agree. Last seen CP only; inventory counts are unchanged.' if result else 'No agreed CP reading. Inputs preserved. '+detail[:250]
        self.publish(stage='accepted' if result else 'rejected',requestId=ident,at=time.time(),message=message,**(result or {}),diagnostic=detail)
        self.app.status.set(message[:230]);self.reader.show(token,image,detail)
        if result:
            self.saved.update(cp=result['cp'],percent=result['percent'])
            for key in ('cp','percent'):
                if key in self.fields:self.fields[key].set(str(result[key]))
            if self.frame and self.frame.winfo_exists():self.recalculate(save=False)
            self.app.save_quietly()
        if self.frame and self.frame.winfo_exists():self.note.set(message[:300])
