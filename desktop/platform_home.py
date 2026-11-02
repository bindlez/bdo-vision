"""Shared activity overview and persistent rewards from accepted ledger rows."""
import time
import tkinter as tk
from tkinter import ttk


def progress_totals(rows,today):
    daily=[r for r in rows if r[1][:10]==today]
    return {'lifetime_units':sum(r[3] for r in rows),'today_units':sum(r[3] for r in daily),
            'crafted':sum(r[3] for r in daily if r[6] in ('Crafted','Rare craft')),
            'rare':sum(r[3] for r in daily if r[6] in ('Rare drop','Rare craft')),'events':len(daily)}


def ledger_totals(db,today):
    """Aggregate inside SQLite; Home need not allocate the complete loot history."""
    row=db.execute("""SELECT COALESCE(SUM(quantity),0),
        COALESCE(SUM(CASE WHEN substr(recorded_at,1,10)=? THEN quantity ELSE 0 END),0),
        COALESCE(SUM(CASE WHEN substr(recorded_at,1,10)=? AND kind IN ('Crafted','Rare craft') THEN quantity ELSE 0 END),0),
        COALESCE(SUM(CASE WHEN substr(recorded_at,1,10)=? AND kind IN ('Rare drop','Rare craft') THEN quantity ELSE 0 END),0),
        COUNT(CASE WHEN substr(recorded_at,1,10)=? THEN 1 END) FROM loot""",(today,)*4).fetchone()
    return dict(zip(('lifetime_units','today_units','crafted','rare','events'),row))


def unlocks(db,units):
    """Idempotent rewards; old accepted history qualifies without replaying alerts."""
    db.execute('CREATE TABLE IF NOT EXISTS platform_achievements (key TEXT PRIMARY KEY,unlocked_at REAL NOT NULL)')
    with db:
        for goal in (100,1000,10000,100000,1000000):
            if units>=goal:db.execute('INSERT OR IGNORE INTO platform_achievements VALUES (?,?)',('units:'+str(goal),time.time()))
    return db.execute('SELECT key FROM platform_achievements ORDER BY unlocked_at,key').fetchall()


class PlatformHome:
    def __init__(self,tracker,tabs):
        self.tracker=tracker;self.app=tracker.app;c=self.app.colors;self.last_key=None
        self.frame=tk.Frame(tabs,bg=c['bg']);tabs.insert(0,self.frame,text='Home')
        canvas=tk.Canvas(self.frame,bg=c['bg'],highlightthickness=0,takefocus=True)
        scroll=ttk.Scrollbar(self.frame,orient='vertical',command=canvas.yview);scroll.pack(side='right',fill='y')
        canvas.configure(yscrollcommand=scroll.set);canvas.pack(fill='both',expand=True)
        content=tk.Frame(canvas,bg=c['bg'],padx=10,pady=10);window=canvas.create_window(0,0,window=content,anchor='nw')
        content.bind('<Configure>',lambda event:canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>',lambda event:canvas.itemconfigure(window,width=event.width))
        canvas.bind('<Next>',lambda event:canvas.yview_scroll(1,'pages'));canvas.bind('<Prior>',lambda event:canvas.yview_scroll(-1,'pages'))
        from ui_scroll import enable_page_wheel
        enable_page_wheel(canvas)
        tk.Label(content,text='YOUR VISION WORKSPACE',bg=c['bg'],fg=c['text'],font=('Segoe UI Semibold',16)).pack(anchor='w')
        self.mode=tk.StringVar();tk.Label(content,textvariable=self.mode,bg=c['panel2'],fg=c['bright'],padx=12,pady=10,wraplength=850,justify='left').pack(fill='x',pady=(10,14))
        nav=tk.Frame(content,bg=c['bg']);nav.pack(fill='x')
        for label,target in [('WORKSHOP','craft'),('GRIND','grind'),('SESSIONS','sessions'),('QUESTS','quests')]:
            self.app.action(nav,label,lambda section=target:self.app.open_activity(section),flat=True).pack(side='left',expand=True,fill='x',padx=3)
        cards=tk.Frame(content,bg=c['bg']);cards.pack(fill='x',pady=14)
        self.states={}
        for index,(key,label) in enumerate([('tool','CURRENT TOOL'),('loot','LOOT CAPTURE'),('guild','GUILD QUEST'),('session','RECORDING SESSION')]):
            box=tk.Frame(cards,bg=c['panel'],padx=12,pady=12,highlightthickness=1,highlightbackground=c['line'])
            box.grid(row=index//2,column=index%2,sticky='nsew',padx=4,pady=4);cards.columnconfigure(index%2,weight=1)
            tk.Label(box,text=label,bg=c['panel'],fg=c['muted'],font=('Segoe UI Semibold',9)).pack(anchor='w')
            value=self.states[key]=tk.StringVar()
            tk.Label(box,textvariable=value,bg=c['panel'],fg=c['text'],wraplength=370,justify='left',font=('Segoe UI',10)).pack(anchor='w',pady=(6,0))
        self.metrics=tk.StringVar();tk.Label(content,textvariable=self.metrics,bg=c['bg'],fg=c['bright'],font=('Segoe UI Semibold',13)).pack(anchor='w',pady=10)
        goal=tk.Frame(content,bg=c['bg']);goal.pack(fill='x')
        tk.Label(goal,text='Daily recorded-unit goal',bg=c['bg'],fg=c['secondary']).pack(side='left')
        self.goal=tk.StringVar(value=str(tracker.platform_preferences.get('daily_goal',1000)))
        ttk.Entry(goal,textvariable=self.goal,width=10,style='Vision.TEntry').pack(side='left',padx=10)
        self.app.text_button(goal,'SAVE GOAL',self.save_goal).pack(side='left')
        self.bar=ttk.Progressbar(content,maximum=100,style='Vision.Horizontal.TProgressbar');self.bar.pack(fill='x',pady=8)
        self.goal_text=tk.StringVar();tk.Label(content,textvariable=self.goal_text,bg=c['bg'],fg=c['secondary'],wraplength=850,justify='left').pack(anchor='w')
        self.rewards=tk.StringVar();tk.Label(content,textvariable=self.rewards,bg=c['panel'],fg=c['text'],padx=12,pady=12,wraplength=850,justify='left').pack(fill='x',pady=12)
        links=tk.Frame(content,bg=c['bg']);links.pack(fill='x')
        for title,action in [('TOOL DEBUG',self.app.tool_debug.open),('QUEST DEBUG',tracker.guild.reader_view.open),('FAIRY CODEX',self.app.open_fairy),('GEAR',self.app.open_gear_planner)]:
            self.app.text_button(links,title,action).pack(side='left',padx=8)
        tk.Label(content,text='Rewards use accepted recorded items only. Quiet by design: no animations, audio or extra capture. Unknown and hidden drops never count.',bg=c['bg'],fg=c['muted'],wraplength=850,justify='left').pack(anchor='w',pady=12)
        self.refresh()

    def save_goal(self):
        try:value=int(self.goal.get().replace(',',''));assert 1<=value<=100000000
        except (ValueError,AssertionError):self.goal_text.set('Enter a goal between 1 and 100,000,000 recorded units.');return
        self.tracker.platform_preferences['daily_goal']=value;self.last_key=None;self.app.save_quietly();self.refresh()

    def refresh(self):
        lite=self.app.lite_use.get();tool=self.app.tool_status.snapshot();guild=self.tracker.guild.model.snapshot()
        values={'tool':tool['title']+' · '+tool['detail'],
                'loot':'Paused by Lite Use' if lite else self.tracker.capture_state.get(),
                'guild':'Paused by Lite Use' if lite else ('Guild quest: Complete · '+guild['reason'] if guild['complete'] else f"Last verified {guild['current']} / {guild['target']} · "+guild['reason'] if guild['current'] is not None else guild['reason']),
                'session':('No active session · start one in Sessions' if not self.tracker.insights.session.id else 'Finished' if self.tracker.insights.session.ended else 'Recording' if self.tracker.insights.session.clock.running else 'Paused')}
        if self.tracker.insights.session.clock.running and not self.tracker.capture_clock.available:values['session']='Session armed · capture paused; excluded time does not earn silver/hour'
        self.mode.set('LITE USE · initial tool scan then timer only. Loot, quests and equipment OCR are paused.' if lite else 'NORMAL TRACKING · independent tool, loot and quest readers. Capture must be visible; each status below explains availability.')
        for key,value in values.items():
            if self.states[key].get()!=value:self.states[key].set(value)
        today=time.strftime('%Y-%m-%d');revision=(self.tracker.ledger.revision,today,self.tracker.platform_preferences.get('daily_goal',1000))
        if revision==self.last_key:return
        self.last_key=revision;totals=ledger_totals(self.tracker.ledger.db,today)
        self.metrics.set(f"TODAY   {totals['today_units']:,} units · {totals['crafted']:,} crafted · {totals['rare']:,} rare")
        target=self.tracker.platform_preferences.get('daily_goal',1000);self.bar['value']=min(100,totals['today_units']/target*100)
        self.goal_text.set(f"{totals['today_units']:,} / {target:,} recorded units · "+('GOAL COMPLETE' if totals['today_units']>=target else f"{target-totals['today_units']:,} to go")+' · resets with the local day')
        awards=unlocks(self.tracker.ledger.db,totals['lifetime_units'])
        self.rewards.set('LIFETIME MILESTONES\n'+(' · '.join(f"{int(row[0].split(':')[1]):,} units unlocked" for row in awards) if awards else 'Your first milestone: 100 recorded units.'))
