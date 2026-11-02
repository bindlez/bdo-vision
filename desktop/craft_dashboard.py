"""Bounded native crafting progress; uses recorded events, never another capture."""
import tkinter as tk
from tkinter import ttk
from decimal import Decimal,InvalidOperation


def profit_breakdown(gross,ingredients,retention,expenses,unpriced=0):
    if gross is None or unpriced:return 'Profit unavailable · some recorded output has no price.'
    try:
        cost,keep,extra=[Decimal(str(v).replace(',','').strip()) for v in (ingredients,retention,expenses)]
        if not all(v.is_finite() for v in (cost,keep,extra)) or not 0<=keep<=100 or not 0<=cost<=10**15 or not 0<=extra<=10**15:raise ValueError()
    except (InvalidOperation,ValueError):return 'Enter today’s ingredient spend, sale retention (0–100%) and other costs to model profit. Enter 0 for a known zero cost.'
    gross=Decimal(str(gross));proceeds=gross*keep/100;tax=gross-proceeds
    return f'MODELED PROFIT: {proceeds-cost-extra:,.0f} silver\nGross {gross:,.0f} − tax/fees {tax:,.0f} − ingredients {cost:,.0f} − other costs {extra:,.0f}. Assumes all recorded output sells; no sale is confirmed.'


class CraftDashboard:
    def __init__(self, tracker, parent):
        self.tracker=tracker
        c=tracker.app.colors
        self.frame=tk.Frame(parent,bg=c['bg'],padx=16,pady=12)
        self.frame.pack(side='top',fill='x')
        tk.Label(self.frame,text='CRAFTING · TODAY',bg=c['bg'],fg=c['bright'],font=('Segoe UI Semibold',18)).pack(anchor='w')
        self.summary=tk.StringVar()
        tk.Label(self.frame,textvariable=self.summary,bg=c['bg'],fg=c['text'],font=('Segoe UI Semibold',12),wraplength=820,justify='left').pack(anchor='w',pady=8)
        self.canvas=tk.Canvas(self.frame,height=250,bg=c['panel'],highlightthickness=0)
        self.canvas.pack(fill='x')
        self.note=tk.StringVar()
        self.market=tk.StringVar(value='Market valuation appears as quotes become available.')
        tk.Label(self.frame,textvariable=self.market,bg=c['bg'],fg=c['bright'],font=('Segoe UI Semibold',11),wraplength=820,justify='left').pack(anchor='w',pady=8)
        scopes=ttk.Notebook(self.frame,style='Loot.TNotebook');scopes.pack(fill='x',pady=8)
        self.recipe_frame=tk.Frame(scopes,bg=c['bg']);scopes.add(self.recipe_frame,text='Recipe session profit')
        manual_frame=tk.Frame(scopes,bg=c['bg'],padx=10,pady=10);scopes.add(manual_frame,text='Manual daily estimate')
        tk.Label(manual_frame,text='Independent daily budget estimate. Do not add this to session profit.',bg=c['bg'],fg=c['secondary'],wraplength=800,justify='left').pack(anchor='w',pady=8)
        import time
        saved=tracker.craft_economy if tracker.craft_economy.get('day')==time.strftime('%Y-%m-%d') else {}
        self.inputs={name:tk.StringVar(value=saved.get(name,'')) for name in ('ingredients','retention','expenses')}
        fields=tk.Frame(manual_frame,bg=c['bg']);fields.pack(fill='x')
        for name,label in [('ingredients','Ingredients spent TODAY'),('retention','Sale retention % after tax'),('expenses','Other costs TODAY')]:
            col=tk.Frame(fields,bg=c['bg']);col.pack(side='left',fill='x',expand=True,padx=4)
            tk.Label(col,text=label,bg=c['bg'],fg=c['secondary'],font=('Segoe UI',9)).pack(anchor='w')
            entry=tk.Entry(col,textvariable=self.inputs[name],bg=c['panel2'],fg=c['text'],insertbackground=c['text'],width=18);entry.pack(fill='x')
            entry.bind('<FocusOut>',lambda event:self.save_economy())
        self.profit=tk.StringVar()
        tk.Label(manual_frame,textvariable=self.profit,bg=c['bg'],fg=c['text'],wraplength=820,justify='left').pack(anchor='w',pady=8)
        self.last_value=None
        for variable in self.inputs.values():variable.trace_add('write',lambda *args:self.refresh_profit())
        tk.Label(self.frame,textvariable=self.note,bg=c['bg'],fg=c['secondary'],wraplength=820,justify='left').pack(anchor='w',pady=8)
        actions=tk.Frame(self.frame,bg=c['bg']);actions.pack(fill='x')
        tracker.app.text_button(actions,'CRAFTING PLANNER',tracker.app.open_planner).pack(side='left')
        tracker.app.text_button(actions,'TOOL READER',tracker.app.open_tools).pack(side='left',padx=12)
        tracker.app.text_button(actions,'QUEST OCR READER',tracker.guild.reader_view.open).pack(side='left')
        self.data=[]
        from craft_economy import SessionCostView
        self.session_cost=SessionCostView(tracker,self.recipe_frame)
        self.canvas.bind('<Configure>',lambda event:self.draw())
        self.update([])

    def refresh_profit(self):
        if self.last_value is None:return
        value=self.last_value
        self.profit.set(profit_breakdown(value['market_silver'],*(self.inputs[k].get() for k in ('ingredients','retention','expenses')),value['unpriced_types']))

    def save_economy(self):
        import time
        self.tracker.craft_economy={'day':time.strftime('%Y-%m-%d'),**{k:v.get() for k,v in self.inputs.items()}}
        self.tracker.app.save_quietly()

    def update(self, rows):
        events=sorted((r for r in rows if r[6] in ('Crafted','Rare craft')),key=lambda r:r[0])
        units=sum(r[3] for r in events);rare=sum(r[3] for r in events if r[6]=='Rare craft')
        from silver_loot import silver_snapshot
        value=silver_snapshot(events,self.tracker.insights.prices.all())
        self.last_value=value;self.refresh_profit()
        amount=f"{value['market_silver']:,}" if value['market_silver'] is not None else "unavailable"
        self.market.set(f"Recorded item value: {amount} silver · {value['unpriced_types']} unpriced types excluded · before costs and fees")
        totals={}
        for row in events:totals[row[2]]=totals.get(row[2],0)+row[3]
        self.leaders=sorted(totals.items(),key=lambda pair:pair[1],reverse=True)[:3]
        milestone=next((n for n in (100,500,1000,2500,5000,10000,25000,50000) if n>units),((units//50000)+1)*50000)
        self.summary.set(f'{units:,} recorded units   ·   {rare:,} rare units   ·   {len(events):,} drop events')
        self.note.set(f'Next milestone: {milestone:,} units · {milestone-units:,} to go. Rare share: {100*rare/units:.1f}% of recorded units.' if units else 'Your workshop starts here. Enable Crafting mode and Record loot in Capture setup. Confirmed output will fill this graph; nothing is estimated.')
        # At most 48 points, retaining the final total and chronological shape.
        total=0;points=[];step=max(1,(len(events)+46)//47)
        for i,row in enumerate(events):
            total+=row[3]
            if i%step==0 or i==len(events)-1:points.append(total)
        self.data=points[-48:];self.draw()

    def draw(self):
        canvas=self.canvas;c=self.tracker.app.colors;canvas.delete('all')
        width=max(300,canvas.winfo_width());height=180
        canvas.create_text(16,18,text='CUMULATIVE CRAFTED UNITS · event order',anchor='w',fill=c['secondary'],font=('Segoe UI',9))
        for y in (55,95,135):canvas.create_line(16,y,width-16,y,fill=c['line'])
        if not self.data:
            canvas.create_text(width/2,100,text='Ready for your first recorded craft',fill=c['muted'],font=('Segoe UI',12));return
        values=[0,*self.data];peak=max(1,values[-1]);coords=[]
        for i,value in enumerate(values):coords.extend((20+i*(width-40)/max(1,len(values)-1),145-100*value/peak))
        canvas.create_line(*coords,fill=c['bright'],width=3)
        canvas.create_text(width-20,163,text=f'{peak:,} units',anchor='e',fill=c['text'])
        for i,(name,quantity) in enumerate(self.leaders):
            y=185+i*22
            canvas.create_rectangle(20,y,20+(width-40)*quantity/max(1,self.leaders[0][1]),y+17,fill=c['violet'],outline='')
            canvas.create_text(26,y+8,text=f'{name} · {quantity:,}',anchor='w',fill=c['text'],font=('Segoe UI',9))
