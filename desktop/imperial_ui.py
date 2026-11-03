"""Native Imperial planner. Local, event-driven comparisons; explicit price refresh."""
import sqlite3
from contextlib import closing
import threading
import tkinter as tk
from tkinter import ttk
from craft_economy import craft_spec
from imperial_planner import imperial_ranks


def money(value):return 'Unpriced' if value is None else f'{value:,.0f}'


class ImperialInfo:
    def __init__(self,tracker,settings):
        self.tracker=tracker;self.app=tracker.app;self.root=tracker.root
        self.saved=dict(settings.get('imperial_plan',{}));self.frame=None;self.busy=False;self.rows={}
        self.kind=tk.StringVar(value='Cooking');self.mastery=tk.StringVar(value=str(self.saved.get('cooking',0)))
        self.guru=tk.BooleanVar(value=bool(self.saved.get('guruOnly',False)));self.sort='buy';self.advanced=None
        self.report=None;self.note=tk.StringVar(value='Open Imperial or refresh prices. Cached quotes are reused; no background scans.')

    def settings(self):return {'imperial_plan':self.saved}

    def build(self,tabs):
        from ui_scroll import notebook_page
        c=self.app.colors;self.frame,body=notebook_page(tabs,'Imperial',c)
        tk.Label(body,text='IMPERIAL · WHAT MAKES THE MOST SILVER?',bg=c['bg'],fg=c['bright'],font=('Segoe UI Semibold',13)).pack(anchor='w',pady=8)
        row=tk.Frame(body,bg=c['bg']);row.pack(fill='x')
        activity=ttk.Combobox(row,textvariable=self.kind,values=('Cooking','Alchemy'),state='readonly',width=11,style='Vision.TCombobox');activity.pack(side='left');activity.bind('<<ComboboxSelected>>',lambda e:self.change_kind())
        tk.Label(row,text='Mastery',bg=c['bg'],fg=c['text']).pack(side='left',padx=(10,4))
        mastery=ttk.Entry(row,textvariable=self.mastery,width=7,style='Vision.TEntry');mastery.pack(side='left');mastery.bind('<Return>',lambda e:self.recalculate());mastery.bind('<FocusOut>',lambda e:self.recalculate())
        tk.Label(row,text='Total CP',bg=c['bg'],fg=c['text']).pack(side='left',padx=(10,4))
        self.cp=self.tracker.cp_info.fields['cp'];cp=ttk.Entry(row,textvariable=self.cp,width=6,style='Vision.TEntry');cp.pack(side='left');cp.bind('<Return>',lambda e:self.recalculate());cp.bind('<FocusOut>',lambda e:self.recalculate())
        ttk.Checkbutton(row,text='Guru boxes only',variable=self.guru,command=self.recalculate,style='Vision.TCheckbutton').pack(side='left',padx=10)
        actions=tk.Frame(body,bg=c['bg']);actions.pack(fill='x',pady=8)
        self.app.action(actions,'CALCULATE',self.recalculate,primary=True).pack(side='left')
        self.app.text_button(actions,'REFRESH MARKET PRICES',self.refresh_prices).pack(side='left',padx=12)
        self.app.text_button(actions,'ADVANCED DETAILS & GRAPHS',self.toggle_advanced).pack(side='right')
        tk.Label(body,textvariable=self.note,bg=c['bg'],fg=c['secondary'],wraplength=730,justify='left').pack(anchor='w',pady=5)
        cards=tk.Frame(body,bg=c['bg']);cards.pack(fill='x',pady=8);self.cards=[]
        for i,title in enumerate(('BEST TO BUY & PACK','BEST TO BUY & PACK · IN STOCK','BEST TO CRAFT & PACK','BEST TO CRAFT & PACK · IN STOCK')):
            panel=tk.Frame(cards,bg=c['panel'],padx=10,pady=9);panel.grid(row=i//2,column=i%2,sticky='nsew',padx=3,pady=3);cards.columnconfigure(i%2,weight=1,uniform='imperial')
            tk.Label(panel,text=title,bg=c['panel'],fg=c['muted'],font=('Segoe UI Semibold',8)).pack(anchor='w')
            value=tk.StringVar(value='Waiting for prices');tk.Label(panel,textvariable=value,bg=c['panel'],fg=c['bright'],font=('Segoe UI Semibold',10),wraplength=350,justify='left').pack(anchor='w',pady=4);self.cards.append(value)
        holder=tk.Frame(body,bg=c['bg']);holder.pack(fill='both',expand=True)
        columns=('item','tier','quantity','payout','buycost','craftcost','buyprofit','craftprofit','dailybuy','dailycraft')
        self.tree=ttk.Treeview(holder,columns=columns,show='headings',height=10,style='Loot.Treeview')
        titles=('MEAL / ELIXIR','BOX TIER','ITEMS / BOX','TURN-IN SILVER','BUY COST','CRAFT COST','BUY PROFIT ↓','CRAFT PROFIT ↕','DAILY BUY PROFIT','DAILY CRAFT PROFIT')
        for key,title in zip(columns,titles):self.tree.heading(key,text=title);self.tree.column(key,width=210 if key=='item' else 130 if key=='tier' else 105,minwidth=70,stretch=key=='item')
        self.tree.heading('buyprofit',command=lambda:self.set_sort('buy'));self.tree.heading('craftprofit',command=lambda:self.set_sort('craft'))
        y=ttk.Scrollbar(holder,orient='vertical',command=self.tree.yview);y.pack(side='right',fill='y')
        x=ttk.Scrollbar(holder,orient='horizontal',command=self.tree.xview);x.pack(side='bottom',fill='x');self.tree.configure(yscrollcommand=y.set,xscrollcommand=x.set)
        self.tree.pack(fill='both',expand=True);self.tree.bind('<<TreeviewSelect>>',lambda e:self.show_details())
        self.body=body
        tk.Label(body,text='Profit = Imperial payout − acquisition cost; no market-sale tax on delivery. Daily totals assume your full CP ÷ 2 allowance is unused. Stock must cover the full displayed run; unknown stock is excluded. Verify your life-skill box tier. No new OCR or polling.',bg=c['bg'],fg=c['muted'],wraplength=730,justify='left',font=('Segoe UI',9)).pack(anchor='w',pady=8)
        tabs.bind('<<NotebookTabChanged>>',lambda e:self.recalculate(save=False) if tabs.select()==str(self.frame) else None,add='+')

    def change_kind(self):
        self.mastery.set(str(self.saved.get(self.kind.get().lower(),0)));self.recalculate(save=False)

    def set_sort(self,mode):self.sort=mode;self.recalculate(save=False)

    def recalculate(self,save=True):
        if self.frame is None:return False
        try:
            mastery=float(self.mastery.get());cp=int(self.cp.get())
            if not 0<=cp<=3000:raise ValueError('CP must be 0–3,000')
            kind=self.kind.get().lower();levels={k:float(self.saved.get(k,0)) for k in ('cooking','alchemy')};levels[kind]=mastery
            with closing(sqlite3.connect(self.tracker.insights.prices.path)) as db:region=db.execute('SELECT region FROM market_context WHERE id=1').fetchone()[0]
            spec=craft_spec();quotes={q['item_id']:q for name,q in self.tracker.insights.prices.all(region).items() if q.get('item_id') and spec['items'].get(str(q['item_id']),{}).get('name')==name}
            boxes=cp//2;report=imperial_ranks(quotes,boxes=boxes or 1,mastery=levels,guru_only=self.guru.get())[kind]
        except (ValueError,TypeError) as exc:
            self.note.set('Check your inputs: '+str(exc));self.report=None;self.rows={};self.tree.delete(*self.tree.get_children())
            for card in self.cards:card.set('Check your inputs')
            return False
        self.saved.update(levels,guruOnly=self.guru.get());self.tracker.cp_info.saved['cp']=cp
        if save:self.app.save_quietly()
        self.report=report;self.boxes=boxes;made={r['boxRecipeId']:r for r in report['craft']}
        ordered=sorted(report['buy'],key=lambda b:((b if self.sort=='buy' else made.get(b['boxRecipeId'],{})).get('profit') is None,-((b if self.sort=='buy' else made.get(b['boxRecipeId'],{})).get('profit') or 0),b['name']))
        self.rows={b['boxRecipeId']:(b,made.get(b['boxRecipeId'])) for b in ordered}
        old=self.tree.selection();self.tree.delete(*self.tree.get_children())
        for b in ordered:
            m=made.get(b['boxRecipeId']);count=b['boxes']
            self.tree.insert('','end',iid=b['boxRecipeId'],values=(b['name'],b['boxName'],f"{b['quantity']/count:,.0f}",money(b['payout']/count),money(b['cost']/count if b['cost'] is not None else None),money(m['cost']/count if m and m['cost'] is not None else None),money(b['profit']/count if b['profit'] is not None else None),money(m['profit']/count if m and m['profit'] is not None else None),money(b['profit']) if boxes else '—',money(m['profit']) if boxes and m else '—'))
        self.tree.heading('buyprofit',text='BUY PROFIT ↓' if self.sort=='buy' else 'BUY PROFIT ↕');self.tree.heading('craftprofit',text='CRAFT PROFIT ↓' if self.sort=='craft' else 'CRAFT PROFIT ↕')
        recommendations=[report['buy'],[r for r in report['buy'] if r['inStock']],report['craft'],report['craftInStock']]
        self.winners=[]
        for index,options in enumerate(recommendations):
            known=[r for r in options if r['profit'] is not None];r=max(known,key=lambda r:r['profit']) if known else None;self.winners.append(r)
            self.cards[index].set((r['name']+'\n'+money(r['profit']/r['boxes'])+' profit / box'+('\n'+money(r['profit'])+' potential daily profit\n'+money(r['payout'])+' turn-in silver' if boxes else '')+(' · least loss' if r['profit']<=0 else '')) if r else 'No fully priced / stocked option')
        self.note.set(region+' cached prices · '+(str(boxes)+' boxes/day maximum' if boxes else 'enter CP for daily totals')+' · '+str(len(ordered))+' options. Mastery controls expected craft yields and payout; no side-output/surplus credit.')
        if old and old[0] in self.rows:self.tree.selection_set(old[0])
        elif ordered:self.tree.selection_set(ordered[0]['boxRecipeId'])
        self.show_details();return True

    def refresh_prices(self):
        if self.busy:return
        self.busy=True;self.note.set('Refreshing shared recipe market snapshot on demand…')
        def work():
            try:
                prices=self.tracker.insights.prices
                with closing(sqlite3.connect(prices.path)) as db:region=db.execute('SELECT region FROM market_context WHERE id=1').fetchone()[0]
                items=prices.recipe_market_snapshot(region);message=f'{len(items)} exact item quotes refreshed · {region}. Stock is a snapshot, not a reservation.'
            except Exception:message='Refresh unavailable. Cached prices retained; unpriced options remain unpriced.'
            def finish():
                self.busy=False
                if self.frame and self.frame.winfo_exists():self.recalculate(save=False);self.note.set(message)
            try:self.root.after(0,finish)
            except (RuntimeError,tk.TclError):pass
        threading.Thread(target=work,name='imperial-market-on-demand',daemon=True).start()

    def toggle_advanced(self):
        if self.advanced is not None and self.advanced.winfo_manager():self.advanced.pack_forget();return
        if self.advanced is None:
            c=self.app.colors;self.advanced=tk.Frame(self.body,bg=c['panel'],padx=12,pady=12)
            self.detail=tk.StringVar();tk.Label(self.advanced,textvariable=self.detail,bg=c['panel'],fg=c['text'],justify='left',wraplength=730,font=('Segoe UI',9)).pack(anchor='w')
            self.chart=tk.Canvas(self.advanced,height=230,bg=c['panel'],highlightthickness=0);self.chart.pack(fill='x');self.chart.bind('<Configure>',lambda e:self.show_details())
        self.advanced.pack(fill='x',pady=8);self.show_details()

    def show_details(self):
        if self.advanced is None or not self.advanced.winfo_manager() or not self.report:return
        selection=self.tree.selection();pair=self.rows.get(selection[0]) if selection else None
        if not pair:return
        b,m=pair;lines=[b['name']+' · '+b['boxName'],f"Turn in {b['quantity']:,} items for {b['boxes']} boxes. Payout {money(b['payout'])}; buy cost {money(b['cost'])}; buy profit {money(b['profit'])}.",f"Meal/elixir stock: {money(b['stock'])}. Unknown stock never qualifies as in stock."]
        if m and m['cost'] is not None:
            lines.append(f"Craft {m['runs']:,} actions; {m['surplus']:.2f} expected surplus, not credited. Craft cost {money(m['cost'])}; profit {money(m['profit'])}.")
            lines.extend(f"• {r['name']} × {r['quantity']:,} · {money(r['unit'])} each · {r['basis']} · stock {money(r['stock'])}" for r in m['ingredients'])
        lines.append('STOCKED CRAFT RECOMMENDATION')
        r=self.winners[3]
        if r:
            lines.append(r['name']+' · '+money(r['profit'])+' profit for the allowance; available variant/substitutions may cost more.')
            lines.extend(f"• {p['name']} × {p['quantity']:,} · {money(p['unit'])} each · {p['basis']}" for p in r['ingredients'])
        else:lines.append('No complete, priced, stocked ingredient plan found.')
        self.detail.set('\n'.join(lines));canvas=self.chart;canvas.delete('all');w=max(500,canvas.winfo_width());values=[]
        for mode,color in [('buy','#c6a2ff'),('craft','#66d8b1')]:
            rows=sorted((r for r in self.report[mode] if r['profit'] is not None),key=lambda r:-r['profit'])[:3]
            values.extend((mode+' · '+r['name'],r['profit']/r['boxes'],color) for r in rows)
        if not values:return
        low=min(0,min(v for _,v,_ in values));high=max(1,max(v for _,v,_ in values));x=lambda v:210+(v-low)/(high-low)*(w-330);zero=x(0)
        canvas.create_text(10,12,text='TOP EXPECTED PROFITS / BOX · BUY AND CRAFT',anchor='w',fill='#d2bfeb',font=('Segoe UI Semibold',9))
        canvas.create_line(zero,28,zero,220,fill='#88739b')
        for i,(label,value,color) in enumerate(values):
            y=35+i*29;canvas.create_text(5,y+8,text=label[:32],anchor='w',fill='#d2bfeb',font=('Segoe UI',8));canvas.create_rectangle(min(zero,x(value)),y,max(zero,x(value))+1,y+17,fill=color if value>=0 else '#ef929c',outline='');canvas.create_text(w-8,y+8,text=money(value),anchor='e',fill='#d2bfeb',font=('Segoe UI',8))
