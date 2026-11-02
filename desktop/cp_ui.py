"""Native CP calculator. Lazy data, event-only work, shared market cache, no tick."""
import threading
import time
import uuid
import json
import sqlite3
from contextlib import closing
import webbrowser
import tkinter as tk
from tkinter import ttk
from cp_planner import calculate,data
from cp_forecast import analyze,income_at
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
        options=[('deploy','Max new CP actually used',100),('delay','Income delay · days',0),('utilization','Uptime / utilization %',100),('ramp','Ramp to full income · days',0),('setup','One-time setup silver',0),('reserve','Minimum cash to keep',0),('grindRate','Optional grind silver / hour',0)]
        for i,(key,label,default) in enumerate(options):
            cell=tk.Frame(self.options,bg=c['panel']);cell.grid(row=i//3,column=i%3,sticky='ew',padx=5,pady=5);self.options.columnconfigure(i%3,weight=1)
            tk.Label(cell,text=label,bg=c['panel'],fg=c['secondary'],font=('Segoe UI',9)).pack(anchor='w')
            self.fields[key]=tk.StringVar(value=str(self.saved.get(key,default)));ttk.Entry(cell,textvariable=self.fields[key],width=16,style='Vision.TEntry').pack(fill='x')
        self.fields['incomeMode']=tk.StringVar(value='Whole project / day' if self.saved.get('incomeMode')=='project' else 'Per deployed CP / day')
        ttk.Combobox(self.options,textvariable=self.fields['incomeMode'],values=('Per deployed CP / day','Whole project / day'),state='readonly',style='Vision.TCombobox',width=23).grid(row=2,column=1,columnspan=2,sticky='ew',padx=5)
        self.control_row=row=tk.Frame(body,bg=c['bg']);row.pack(fill='x',pady=8)
        self.app.action(row,'CALCULATE + SAVE',self.recalculate,primary=True).pack(side='left')
        self.app.text_button(row,'REFRESH EXISTING MARKET PRICES',self.refresh_prices).pack(side='left',padx=14)
        self.app.text_button(row,'ASSUMPTIONS',self.toggle_options).pack(side='left')
        self.note=tk.StringVar(value='Saved scenario · edit stock and income assumptions, then calculate.' if self.saved else 'First-use example: 750,000 catalysts at 490 CP + 19.26%. Edit to your actual stock. Income defaults to zero.')
        tk.Label(body,textvariable=self.note,bg=c['bg'],fg=c['bright'],wraplength=740,justify='left').pack(fill='x',pady=6)
        self.selected=tk.StringVar(value='Target, then cash');picker=ttk.Combobox(body,textvariable=self.selected,values=('Cash everything','All CP','Target, then cash','50% split'),state='readonly',style='Vision.TCombobox');picker.pack(fill='x',pady=6);picker.bind('<<ComboboxSelected>>',lambda event:self.recalculate(save=False))
        pages=ttk.Notebook(body,style='Vision.TNotebook');pages.pack(fill='x',pady=8)
        self.text_views={}
        for title in ('Decision','Payback','Milestones','Model'):
            panel=tk.Frame(pages,bg=c['panel']);pages.add(panel,text=title)
            text=tk.Text(panel,height=11,bg=c['panel'],fg=c['text'],font=('Consolas',10),relief='flat',wrap='word',state='disabled');scroll=ttk.Scrollbar(panel,command=text.yview);text.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y');text.pack(fill='both',expand=True);self.text_views[title]=text
        self.results=self.text_views['Decision']
        self.chart=tk.Canvas(body,height=145,bg=c['panel'],highlightthickness=0);self.chart.pack(fill='x')
        self.chart.bind('<Configure>',lambda e:self.draw_chart())
        tk.Label(body,text='Current market quotes from the existing price book. Market material exchanges are the primary cash route. Unknown exchange prices remain unpriced; leftovers stay in inventory. Future income is modeled, never added to your loot history.',bg=c['bg'],fg=c['muted'],font=('Segoe UI',9),wraplength=740,justify='left').pack(fill='x',pady=8)
        self.recalculate(save=False)

    def settings(self):return {'cp_plan':self.saved}

    def toggle_options(self):
        if self.options.winfo_manager():self.options.pack_forget()
        else:self.options.pack(before=self.control_row,fill='x',pady=8)

    def recalculate(self,save=True):
        if not self.fields:return
        state={k:v.get() for k,v in self.fields.items()};state['counts']={k:v.get() for k,v in self.stock.items()}
        state['incomeMode']='project' if state['incomeMode']=='Whole project / day' else 'per_cp'
        try:report=calculate(state,self.tracker.insights.prices.all())
        except ValueError as exc:self.note.set('Check your values: '+str(exc));return False
        self.saved=state;self.report=report
        if self.app.bridge:
            with self.app.bridge._lock:self.app.bridge.cp_plan=json.loads(json.dumps(state))
        if save:self.app.save_quietly();self.note.set('Saved locally. No extra CP income is assumed until you enter it.' if report['income']==0 else 'Saved scenario · future income is an assumption, not recorded silver.')
        selected_key={'Cash everything':'cash','All CP':'cp','Target, then cash':'target','50% split':'split'}[self.selected.get()]
        if not report['cashComplete']:
            text='MARKET PRICES NEEDED\nRefresh existing market prices to calculate material-exchange value. No NPC fallback is used.\n\n'+f"All CP: {report['routes'][1]['cp']} CP (+{report['routes'][1]['gained']})\nTo {report['target']} CP: {report['targetBatches']:,} full batches / {report['targetXp']:,.0f} EXP\n\nUnquoted rewards: "+', '.join(report['missing'])
            for view in self.text_views.values():view.configure(state='normal');view.delete('1.0','end');view.insert('1.0',text);view.configure(state='disabled')
            self.draw_chart();return True
        a=analyze(report,selected_key);chosen=next(row for row in report['routes'] if row['key']==selected_key)
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

    def draw_chart(self):
        if not getattr(self,'chart',None) or not hasattr(self,'report'):return
        c=self.chart;c.delete('all');r=self.report
        if not r['cashComplete']:return
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
