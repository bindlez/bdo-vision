"""Capture-aware grind sessions, personal benchmarks and treasure pursuits."""
import csv
import json
import statistics
import time
import tkinter as tk
from datetime import datetime
from tkinter import ttk,filedialog
from loot_insights import summarize
from item_names import canonical_item


def duration(seconds):
    value=max(0,int(seconds));return f'{value//3600:02}:{value%3600//60:02}:{value%60:02}'


def grind_summary(meta,rows,prices,now=None,available=False,reason=''):
    now=time.time() if now is None else now
    measured=max(0,meta.get('active_seconds',0))
    result=summarize(rows,prices,measured)
    elapsed=max(measured,(meta.get('ended_at') or now)-meta['created_at'])
    goals=json.loads(meta.get('targets') or '[]');target=goals[0] if goals else ''
    goal=max(1,int(meta.get('goal',1)))
    count=sum(r[3] for r in rows if target and canonical_item(r[2]).casefold()==canonical_item(target).casefold())
    latest=[{'id':r[0],'at':r[1],'item':canonical_item(r[2]),'quantity':r[3],'rare':r[6] in ('Rare drop','Rare craft')} for r in rows[:12]]
    pulse=[0]*24;span=max(60,elapsed);since_target=0;last_target=None
    for event in rows:
        try:index=min(23,max(0,int((datetime.fromisoformat(event[1]).timestamp()-meta['created_at'])/span*24)));pulse[index]+=event[3]
        except ValueError:pass
        if target and last_target is None:
            if canonical_item(event[2]).casefold()==canonical_item(target).casefold():last_target=event[1]
            else:since_target+=1
    return {'id':meta['id'],'label':meta.get('label') or 'Untitled run','spot':meta.get('spot') or meta.get('label') or 'Unspecified spot',
            'started_at':meta['created_at'],'ended_at':meta.get('ended_at'),'observed_seconds':measured,
            'excluded_seconds':max(0,elapsed-measured),'coverage':measured/elapsed if elapsed else 0,
            'available':bool(available),'reason':reason,'value':0 if not rows else result['value'],
            'silver_hour':0 if not rows and measured>=60 else result['silver_hour'],
            'units':result['quantity'],'events':result['events'],'rare':result['rare'],'unpriced':result['unpriced'],
            'priced':result['priced_types'],'items':result['items'],'latest':latest,
            'target':target,'target_quantity':count,'goal':goal,'target_progress':min(1,count/goal) if target else None,
            'pulse':pulse,'events_since_target':since_target,'last_target_at':last_target}


class GrindTracker:
    def __init__(self,tracker):
        self.tracker=tracker;self.root=tracker.root;self.insights=tracker.insights
        self.frame=None;self.tree=None;self.history_tree=None;self.canvas=None
        self.spot=tk.StringVar();self.target=tk.StringVar();self.goal=tk.StringVar(value='1')
        self.state=tk.StringVar(value='Start a run to record your own results.');self.pursuit=tk.StringVar();self.benchmark=tk.StringVar()
        self.metrics=[tk.StringVar(value='—') for _ in range(4)]
        self.insights.session.db.execute('CREATE TABLE IF NOT EXISTS grind_details (session TEXT PRIMARY KEY, spot TEXT NOT NULL, goal INTEGER NOT NULL)');self.insights.session.db.commit()

    def build(self,tabs):
        from ui_scroll import notebook_page
        c=self.tracker.app.colors;self.frame,frame=notebook_page(tabs,'Grind',c)
        top=tk.Frame(frame,bg=c['bg']);top.pack(fill='x')
        for title,var,width in [('SPOT / ROUTE',self.spot,27),('TREASURE PURSUIT · OPTIONAL',self.target,28),('GOAL',self.goal,5)]:
            field=tk.Frame(top,bg=c['bg']);field.pack(side='left',fill='x',expand=title!='GOAL',padx=(0,12))
            tk.Label(field,text=title,font=('Segoe UI Semibold',8),bg=c['bg'],fg=c['muted']).pack(anchor='w')
            ttk.Entry(field,textvariable=var,width=width,style='Vision.TEntry').pack(fill='x',pady=(5,0))
        actions=tk.Frame(frame,bg=c['bg']);actions.pack(fill='x',pady=(12,10))
        self.tracker.app.action(actions,'START GRIND',self.start,primary=True).pack(side='left')
        self.tracker.app.text_button(actions,'PAUSE / RESUME',self.pause).pack(side='left',padx=12)
        self.tracker.app.text_button(actions,'FINISH RUN',self.finish).pack(side='left',padx=12)
        self.tracker.app.text_button(actions,'BIG DROPS',lambda:self.tracker.big_drops.open()).pack(side='left',padx=8)
        self.tracker.app.text_button(actions,'EXPORT RUN',self.export).pack(side='right')
        tk.Label(frame,textvariable=self.state,bg=c['bg'],fg=c['bright'],wraplength=700,justify='left',font=('Segoe UI Semibold',10)).pack(anchor='w',pady=(0,10))
        cards=tk.Frame(frame,bg=c['bg']);cards.pack(fill='x')
        for index,label in enumerate(('RECORDED VALUE','SILVER / OBSERVED HOUR','OBSERVED / EXCLUDED','RARE-NOTICE UNITS')):
            cards.columnconfigure(index,weight=1,uniform='grind')
            card=tk.Frame(cards,bg=c['panel'],padx=12,pady=12);card.grid(row=0,column=index,sticky='nsew',padx=(0,7))
            tk.Label(card,text=label,bg=c['panel'],fg=c['muted'],font=('Segoe UI Semibold',8)).pack(anchor='w')
            tk.Label(card,textvariable=self.metrics[index],bg=c['panel'],fg=c['text'],font=('Segoe UI Semibold',15 if index!=2 else 11)).pack(anchor='w',pady=(7,0))
        tk.Label(frame,textvariable=self.benchmark,bg=c['bg'],fg=c['secondary'],font=('Segoe UI',9),wraplength=700,justify='left').pack(anchor='w',pady=(10,5))
        tk.Label(frame,textvariable=self.pursuit,bg=c['bg'],fg=c['bright'],font=('Segoe UI Semibold',10),wraplength=700,justify='left').pack(anchor='w',pady=(0,8))
        self.canvas=tk.Canvas(frame,height=66,bg=c['panel'],highlightthickness=0);self.canvas.pack(fill='x',pady=(0,10))
        tk.Label(frame,text='RUN HISTORY · select a finished run to inspect it',bg=c['bg'],fg=c['muted'],font=('Segoe UI Semibold',8)).pack(anchor='w',pady=(0,5))
        box=tk.Frame(frame,bg=c['bg']);box.pack(fill='both',expand=True)
        self.history_tree=ttk.Treeview(box,columns=('spot','time','value','rate','coverage'),show='headings',style='Loot.Treeview',height=5)
        for name,title,width in [('spot','SPOT / SESSION',270),('time','OBSERVED',95),('value','VALUE',145),('rate','SILVER / H',145),('coverage','COVERAGE',100)]:
            self.history_tree.heading(name,text=title);self.history_tree.column(name,width=width,minwidth=70,stretch=name=='spot')
        self.history_tree.pack(side='left',fill='both',expand=True)
        scroll=ttk.Scrollbar(box,orient='vertical',command=self.history_tree.yview);scroll.pack(side='right',fill='y');self.history_tree.configure(yscrollcommand=scroll.set)
        self.history_tree.bind('<<TreeviewSelect>>',lambda e:self.refresh_cards(self.selected()))
        tk.Label(frame,text='Value = captured quantity × market or verified NPC unit value. Rate = value ÷ observed seconds × 3,600. Capture gaps and manual pauses are excluded; missed drops are not estimated. Items without verified prices remain unpriced.',bg=c['bg'],fg=c['muted'],font=('Segoe UI',9),wraplength=700,justify='left').pack(anchor='w',pady=(10,0))
        self.refresh()

    def start(self):
        try:goal=max(1,min(1_000_000,int(self.goal.get())))
        except ValueError:self.state.set('Enter a whole number for the pursuit goal.');return
        session=self.insights.session
        if session.id and not session.ended:session.finish(self.insights.prices.all(),self.insights.gate())
        spot=self.spot.get().strip()[:100] or 'Unnamed grind spot'
        session.start(self.insights.gate(),label=spot,activity='Grinding',targets=[self.target.get().strip()[:100]] if self.target.get().strip() else [])
        self.tracker.generation+=1;self.tracker.last_scan=0
        with session.db:session.db.execute('INSERT INTO grind_details VALUES (?,?,?)',(session.id,spot,goal))
        self.tracker.crafting.set(False);self.tracker.app.save_quietly()
        if self.history_tree:self.history_tree.selection_remove(self.history_tree.selection())
        self.refresh()

    def pause(self):
        session=self.insights.session
        if not session.id or session.ended:self.state.set('Start a grind session first.');return
        session.pause_resume(self.insights.gate());self.refresh()

    def finish(self):
        self.insights.session.finish(self.insights.prices.all(),self.insights.gate());self.refresh()

    def dispatch(self,command):
        if command['action']=='start':
            self.spot.set(command.get('spot',''));self.target.set(command.get('target',''));self.goal.set(str(command.get('goal',1)));self.start()
        elif command['action']=='pause':self.pause()
        elif command['action']=='finish':self.finish()

    def summaries(self,limit=None):
        session=self.insights.session;ready,reason=self.tracker.capture_availability();current_prices=self.insights.prices.all()
        details={r[0]:{'spot':r[1],'goal':r[2]} for r in session.db.execute('SELECT session,spot,goal FROM grind_details')}
        results=[]
        for meta in session.history():
            if meta['activity'] not in ('Grinding','Treasure hunt'):continue
            meta.update(details.get(meta['id'],{}))
            live=meta['id']==session.id and not session.ended
            if live:meta['active_seconds']=session.clock.seconds
            prices=json.loads(meta['price_snapshot']) if meta['ended_at'] is not None else current_prices
            results.append(grind_summary(meta,session.rows(meta['id']),prices,available=live and session.clock.running and ready,
                reason='' if live and session.clock.running and ready else 'Session completed' if meta['ended_at'] else 'Manually paused' if live and not session.clock.running else reason))
            if limit is not None and len(results)>=limit:break
        return results

    def snapshot(self):
        results=self.summaries(limit=30);current=next((r for r in results if r['id']==self.insights.session.id),None)
        return {'current':current,'history':[{k:v for k,v in r.items() if k not in ('items','latest')} for r in results[:30]]}

    def selected(self):
        selection=self.history_tree.selection() if self.history_tree else ()
        results=self.summaries();wanted=selection[0] if selection else self.insights.session.id
        return next((r for r in results if r['id']==wanted),None)

    def refresh(self):
        if not self.frame or not self.frame.winfo_exists():return
        results=self.summaries();selected=self.history_tree.selection();ids={r['id'] for r in results}
        for ident in self.history_tree.get_children():
            if ident not in ids:self.history_tree.delete(ident)
        for row in results:
            values=(row['spot'],duration(row['observed_seconds']),'Unpriced' if row['value'] is None else f"{row['value']:,}", 'Measuring…' if row['silver_hour'] is None else f"{row['silver_hour']:,.0f}",f"{row['coverage']:.0%}")
            if self.history_tree.exists(row['id']):self.history_tree.item(row['id'],values=values)
            else:self.history_tree.insert('','end',iid=row['id'],values=values)
        self.refresh_cards(self.selected())

    def refresh_cards(self,row):
        if not row:
            self.state.set('Start a grind to measure your actual recorded results. Your existing loot history is preserved.')
            self.pursuit.set('Optional pursuit: track a treasure piece or rare item by name.');self.benchmark.set('Personal benchmarks unlock after three completed runs at the same spot.');return
        self.metrics[0].set('Unpriced' if row['value'] is None else f"{row['value']:,}")
        self.metrics[1].set('Measuring…' if row['silver_hour'] is None else f"{row['silver_hour']:,.0f}")
        self.metrics[2].set(duration(row['observed_seconds'])+' / '+duration(row['excluded_seconds']))
        self.metrics[3].set(str(row['rare']))
        self.state.set(('OBSERVING' if row['available'] else 'COMPLETED' if row['ended_at'] else 'PAUSED')+' · '+row['spot']+' · '+(row['reason'] or f"{row['events']} captured events")+f" · {row['unpriced']} unpriced types excluded")
        self.pursuit.set((f"PURSUIT · {row['target']}  {row['target_quantity']:,} / {row['goal']:,} · "+('GOAL REACHED' if row['target_quantity']>=row['goal'] else 'Only captured drops count')) if row['target'] else 'No pursuit selected · all captured loot still counts toward your session.')
        peers=[r['silver_hour'] for r in self.summaries() if r['id']!=row['id'] and r['ended_at'] and r['spot'].casefold()==row['spot'].casefold() and r['silver_hour'] is not None]
        if len(peers)>=3 and row['silver_hour'] is not None and statistics.median(peers)>0:
            median=statistics.median(peers);self.benchmark.set(f"YOUR BASELINE · {median:,.0f} silver/hour median · this run {row['silver_hour']/median-1:+.1%} · {len(peers)} completed runs")
        else:self.benchmark.set(f"PERSONAL BASELINE · {len(peers)} / 3 completed runs at this spot. Compare your own results, with capture gaps visible.")
        self.draw_pulse(row)

    def draw_pulse(self,row):
        if not self.canvas:return
        c=self.tracker.app.colors;canvas=self.canvas;canvas.delete('all');width=max(200,canvas.winfo_width());bins=[0]*24
        session=self.insights.session
        rows=session.rows(row['id']);end=row['ended_at'] or time.time();span=max(60,end-row['started_at'])
        for event in rows:
            try:index=min(23,max(0,int((datetime.fromisoformat(event[1]).timestamp()-row['started_at'])/span*24)));bins[index]+=event[3]
            except ValueError:continue
        maximum=max(bins,default=0) or 1;bar=max(1,(width-24)/24)
        for index,value in enumerate(bins):
            if value:canvas.create_rectangle(12+index*bar,57-36*value/maximum,12+(index+1)*bar-3,58,fill=c['violet'],outline='')
        canvas.create_text(12,11,anchor='w',text='LOOT PULSE · captured units across this run',fill=c['muted'],font=('Segoe UI',8))

    def export(self):
        row=self.selected()
        if not row:self.state.set('Select or start a run to export.');return
        path=filedialog.asksaveasfilename(parent=self.tracker.window,defaultextension='.csv',initialfile='BDO-grind-session.csv',filetypes=[('CSV','*.csv')])
        if not path:return
        with open(path,'w',newline='',encoding='utf-8-sig') as output:
            writer=csv.writer(output);writer.writerow(['Session','Observed seconds','Excluded seconds','Recorded value','Unpriced types']);writer.writerow(["'"+row['spot'],round(row['observed_seconds']),round(row['excluded_seconds']),row['value'],row['unpriced']]);writer.writerow([]);writer.writerow(['Item','Quantity','Unit silver','Value'])
            for item in row['items']:writer.writerow(["'"+item['item'],item['quantity'],item['unit_price'],item['value']])
        self.state.set('Session export saved.')
