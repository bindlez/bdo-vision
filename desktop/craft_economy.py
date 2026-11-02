"""Recipe-linked session economics. Costs use quotes; batches remain modeled."""
import json,math,sqlite3,time
from functools import lru_cache
from contextlib import closing
from pathlib import Path
from datetime import datetime
from loot_insights import summarize


@lru_cache(maxsize=1)
def recipes():
    return json.loads((Path(__file__).parent/'assets/recipes.json').read_text(encoding='utf-8'))


def validate_model(body):
    ident=body.get('recipe_id')
    if not isinstance(ident,str) or ident not in {r['id'] for r in recipes()}:raise ValueError('Unknown recipe')
    result={'recipe_id':ident}
    for key,low,high in [('yield',.01,100),('retention',0,100),('extra',0,10**12)]:
        value=body.get(key)
        if type(value) not in (int,float) or not math.isfinite(value) or not low<=value<=high:raise ValueError('Invalid '+key)
        result[key]=value
    return result


def save_model(path,body):
    model=validate_model(body)
    with closing(sqlite3.connect(path)) as db,db:
        db.execute('CREATE TABLE IF NOT EXISTS craft_models (recipe_id TEXT PRIMARY KEY,payload TEXT NOT NULL)')
        db.execute('INSERT INTO craft_models VALUES (?,?) ON CONFLICT(recipe_id) DO UPDATE SET payload=excluded.payload',(model['recipe_id'],json.dumps(model)))
    return model


def load_model(path,ident):
    with closing(sqlite3.connect(path)) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='craft_models'").fetchone():return None
        row=db.execute('SELECT payload FROM craft_models WHERE recipe_id=?',(ident,)).fetchone()
    return validate_model(json.loads(row[0])) if row else None


def session_economy(recipe,rows,quotes,model,seconds=0):
    gross=summarize(rows,quotes,seconds);missing=[];materials=[];unit_cost=0
    if not model:return {'available':False,'reason':'Open this recipe in the paired planner to link its yield, tax and expense assumptions.'}
    for mat in recipe.get('mats',[]):
        quote=quotes.get(mat['name']);price=quote.get('unit_price') if quote else None
        if price is None:missing.append(mat['name'])
        else:unit_cost+=mat['qty']*price
        materials.append({'item':mat['name'],'per_batch':mat['qty'],'unit_price':price})
    main=sum(r[3] for r in rows if r[2].casefold()==recipe['name'].casefold())
    if missing or gross['unpriced'] or gross['value'] is None or not main:
        return {'available':False,'reason':'Missing material quotes: '+', '.join(missing) if missing else 'Need priced output and recorded main output for this recipe.','materials':materials}
    batches=main/model['yield'];ingredient_cost=batches*unit_cost;extra=batches*model['extra'];proceeds=gross['value']*model['retention']/100
    for mat in materials:mat['modeled_quantity']=mat['per_batch']*batches
    return {'available':True,'gross':gross['value'],'tax':gross['value']-proceeds,'ingredient_cost':ingredient_cost,'extra':extra,
            'profit':proceeds-ingredient_cost-extra,'batches':batches,'materials':materials,'units':gross['quantity'],
            'profit_hour':(proceeds-ingredient_cost-extra)*3600/seconds if seconds>=60 else None,
            'basis':'Yield-based batch estimate from recorded main output; not verified inventory consumption. Rare/extra outputs add value when priced; unobserved batches are unknown.'}


def economy_points(recipe,rows,quotes,model,limit=48):
    ordered=sorted(rows,key=lambda r:r[0]);points=[];gross=0;main=0
    cost_per_batch=sum(m['qty']*quotes[m['name']]['unit_price'] for m in recipe['mats'])+model['extra']
    stride=max(1,(len(ordered)+limit-2)//max(1,limit-1))
    for index,row in enumerate(ordered):
        quote=quotes.get(row[2])
        if not quote or quote.get('unit_price') is None:return []
        gross+=row[3]*quote['unit_price']
        if row[2].casefold()==recipe['name'].casefold():main+=row[3]
        if index%stride==0 or index==len(ordered)-1:
            try:at=datetime.fromisoformat(row[1]).timestamp()
            except ValueError:return []
            points.append((at,gross,gross*model['retention']/100-main/model['yield']*cost_per_batch))
    return points[-limit:]


class SessionCostView:
    def __init__(self,tracker,parent):
        import tkinter as tk
        from tkinter import ttk
        self.tracker=tracker;self.last_key=None;c=tracker.app.colors
        self.frame=tk.Frame(parent,bg=c['panel'],padx=12,pady=12);self.frame.pack(fill='x',pady=10)
        tk.Label(self.frame,text='RECIPE-LINKED SESSION PROFIT',bg=c['panel'],fg=c['bright'],font=('Segoe UI Semibold',12)).pack(anchor='w')
        self.text=tk.StringVar();tk.Label(self.frame,textvariable=self.text,bg=c['panel'],fg=c['text'],font=('Segoe UI',10),wraplength=810,justify='left').pack(anchor='w',pady=8)
        self.materials=ttk.Treeview(self.frame,columns=('name','quantity','price'),show='headings',height=4,style='Loot.Treeview')
        for name,title,width in [('name','INGREDIENT',340),('quantity','MODELED QUANTITY',150),('price','UNIT SILVER',130)]:
            self.materials.heading(name,text=title);self.materials.column(name,width=width,minwidth=60)
        self.materials.pack(fill='x')
        self.chart=tk.Canvas(self.frame,bg=c['panel2'],height=150,highlightthickness=0);self.chart.pack(fill='x',pady=8)
        self.points=[];self.chart.bind('<Configure>',lambda event:self.draw())
        actions=tk.Frame(self.frame,bg=c['panel']);actions.pack(fill='x',pady=8)
        tracker.app.text_button(actions,'START / SELECT RECIPE SESSION',lambda:tracker.app.open_activity('sessions')).pack(side='left')
        tracker.app.text_button(actions,'LINK YIELD / TAX IN PLANNER',tracker.app.open_planner).pack(side='left',padx=10)
        tracker.app.text_button(actions,'REFRESH MATERIAL QUOTES',self.refresh_quotes).pack(side='left')
        self.recipe=None;self.fetching=False;self.refresh()

    def draw(self):
        self.chart.delete('all');c=self.tracker.app.colors;width=max(300,self.chart.winfo_width())
        self.chart.create_text(12,14,text='GROSS (purple) / MODELED NET (green) · recorded time',anchor='w',fill=c['secondary'])
        if len(self.points)<2:return
        low=min(0,*[p[2] for p in self.points]);high=max(1,*[p[1] for p in self.points]);span=max(1,self.points[-1][0]-self.points[0][0])
        for field,color in [(1,c['violet']),(2,c['good'])]:
            coords=[]
            for at,gross,net in self.points:
                value=gross if field==1 else net
                coords.extend((16+(at-self.points[0][0])/span*(width-32),130-(value-low)/(high-low)*95))
            self.chart.create_line(*coords,fill=color,width=2)

    def unavailable(self,text):
        self.text.set(text);self.last_key=None;self.points=[];self.draw()
        self.materials.delete(*self.materials.get_children())

    def refresh_quotes(self):
        if self.fetching or self.recipe is None:return
        import threading
        recipe=self.recipe;self.fetching=True;self.text.set('Refreshing this recipe’s exact ingredient quotes…')
        def worker():
            try:
                prices=self.tracker.insights.prices
                quotes=prices.all();region=next((q.get('region') for q in quotes.values() if q.get('region') in ('NA','EU')),'NA')
                prices.recipe_quotes([recipe['name'],*[m['name'] for m in recipe['mats']]],region)
                error=None
            except Exception as exc:error=str(exc)[:180]
            def finish():
                self.fetching=False;self.last_key=None
                if not self.frame.winfo_exists():return
                if error:self.text.set('Quotes unavailable; cached prices preserved. '+error)
                else:self.refresh()
            if not self.tracker.closed:self.tracker.root.after(0,finish)
        threading.Thread(target=worker,name='vision-recipe-quotes',daemon=True).start()

    def refresh(self):
        session=self.tracker.insights.session
        if not session.id:
            self.unavailable('Start a Crafting session in Sessions and select its recipe. Open the same recipe in the planner to link yield, tax and expenses. No duplicate item prices to enter.');return
        row=self.tracker.ledger.db.execute('SELECT activity,recipe,ended_at,price_snapshot,created_at FROM insight_sessions WHERE id=?',(session.id,)).fetchone()
        if not row or row[0]!='Crafting' or not row[1]:self.unavailable('Current session is not linked to a crafting recipe. Select a recipe when starting a Crafting session.');return
        choices=[r for r in recipes() if r['name']==row[1]]
        if len(choices)!=1:self.unavailable('Recipe identity is missing or ambiguous; costs are unavailable.');return
        recipe=self.recipe=choices[0]
        if row[2] is not None:
            model_row=self.tracker.ledger.db.execute('SELECT payload FROM craft_session_models WHERE session_id=?',(session.id,)).fetchone()
            model=json.loads(model_row[0]) if model_row else None;quotes=json.loads(row[3])
        else:model=load_model(self.tracker.path/'loot-history.sqlite3',recipe['id']);quotes=self.tracker.insights.prices.all()
        key=(session.id,self.tracker.ledger.revision,self.tracker.insights.prices.revision,json.dumps(model,sort_keys=True),row[2],int(session.clock.seconds//10))
        if key==self.last_key:return
        self.last_key=key;self.materials.delete(*self.materials.get_children())
        rows=session.rows();value=session_economy(recipe,rows,quotes,model,session.clock.seconds)
        if not value['available']:self.unavailable(recipe['name']+' · '+value['reason']);return
        self.points=economy_points(recipe,rows,quotes,model);self.draw()
        rate=f"{value['profit_hour']:,.0f} / observed hour" if value['profit_hour'] is not None else 'Rate appears after 60 observed seconds'
        excluded=max(0,(row[2] or time.time())-row[4]-session.clock.seconds)
        self.text.set(f"{recipe['name']} · {'frozen receipt' if row[2] else 'current quote model'}\nGross {value['gross']:,.0f} − tax {value['tax']:,.0f} − ingredients {value['ingredient_cost']:,.0f} − other costs {value['extra']:,.0f}\nMODELED NET {value['profit']:,.0f} silver · {rate}\nObserved {session.clock.seconds:,.0f}s · excluded {excluded:,.0f}s\n{value['batches']:,.2f} estimated batches · "+value['basis'])
        for mat in value['materials']:self.materials.insert('','end',values=(mat['item'],f"{mat['modeled_quantity']:,.2f}",f"{mat['unit_price']:,}"))
