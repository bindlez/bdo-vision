"""Native target-first CP plans, using the shared Python CP calculation model."""
import tkinter as tk
from tkinter import ttk
from cp_planner import target_plan

COLORS={'catalyst':'#c6a2ff','witch':'#66d8b1','leaf':'#f1bd6d','missing':'#5b5267'}


class CPTargetView:
    def __init__(self,parent,owner):
        self.owner=owner;self.plan=None;self.routes={};self.selected='owned'
        c=owner.app.colors;self.frame=tk.Frame(parent,bg=c['panel'],padx=12,pady=12)
        self.frame.pack(fill='x',pady=8)
        top=tk.Frame(self.frame,bg=c['panel']);top.pack(fill='x')
        tk.Label(top,text='REACH MY TARGET CP',bg=c['panel'],fg=c['bright'],font=('Segoe UI Semibold',12)).pack(side='left')
        picker=ttk.Combobox(top,textvariable=owner.fields['target'],values=(500,510,525,550,575,600),width=7,style='Vision.TCombobox');picker.pack(side='right')
        picker.bind('<<ComboboxSelected>>',lambda e:owner.recalculate());picker.bind('<Return>',lambda e:owner.recalculate())
        tk.Label(top,text='I want this CP:',bg=c['panel'],fg=c['text']).pack(side='right',padx=8)
        self.status=tk.StringVar();tk.Label(self.frame,textvariable=self.status,bg=c['panel'],fg=c['secondary'],justify='left',wraplength=730).pack(anchor='w',pady=8)
        self.tree=ttk.Treeview(self.frame,columns=('route','items','missing','end','cost'),show='headings',height=6,style='Loot.Treeview')
        for key,title,width in [('route','PLAN',230),('items','TURN IN',160),('missing','ADDITIONAL',95),('end','RESULT CP',75),('cost','SILVER GIVEN UP',130)]:
            self.tree.heading(key,text=title);self.tree.column(key,width=width,minwidth=65,stretch=key in ('route','items'))
        self.tree.pack(fill='x');self.tree.bind('<<TreeviewSelect>>',lambda e:self.choose())
        self.details=tk.StringVar();tk.Label(self.frame,textvariable=self.details,bg=c['panel'],fg=c['text'],justify='left',wraplength=730,font=('Segoe UI',9)).pack(anchor='w',pady=8)
        self.line=tk.Canvas(self.frame,bg=c['panel'],height=190,highlightthickness=0);self.line.pack(fill='x')
        self.pie=tk.Canvas(self.frame,bg=c['panel'],height=190,highlightthickness=0);self.pie.pack(fill='x')
        self.line.bind('<Configure>',lambda e:self.draw());self.pie.bind('<Configure>',lambda e:self.draw())
        tk.Label(self.frame,text='Lines: items required for each target CP. Catalyst and Delicacy overlap; Delicacy is dashed. Pie: owned complete-bundle EXP coverage for the selected plan. Missing items and unpriced silver stay explicit. No future production is assumed.',bg=c['panel'],fg=c['muted'],font=('Segoe UI',9),wraplength=730,justify='left').pack(anchor='w')

    def invalid(self,message):
        self.plan=None;self.routes={};self.status.set('Check your inputs: '+message)
        self.details.set('Previous target results are hidden until the inputs are valid.')
        self.tree.delete(*self.tree.get_children());self.line.delete('all');self.pie.delete('all')

    def update(self,report):
        self.plan=target_plan(report)
        plans=self.plan['singles']+[self.plan['owned'],self.plan['completion'],self.plan['balanced']]
        self.routes={p['key']:p for p in plans}
        for key in self.tree.get_children():
            if key not in self.routes:self.tree.delete(key)
        for p in plans:
            summary=' + '.join(f"{r['items']:,} {r['name']}" for r in p['allocation'] if r['items']) or 'No exchanges'
            shortage=f"{p['shortageItems']:,} items" if p['reachesTarget'] else f"{p['missingBatches']:,} bundles"
            cost='Unpriced' if p['opportunityCost'] is None else f"{p['opportunityCost']:,.0f}"
            values=(p['label'],summary,shortage,p['result']['cp'],cost)
            if self.tree.exists(p['key']):self.tree.item(p['key'],values=values)
            else:self.tree.insert('','end',iid=p['key'],values=values)
        self.status.set(f"From {report['cp']} CP + {report['percent']}% → {report['target']} CP: {report['targetXp']:,.0f} EXP / {report['targetBatches']:,} complete exchanges. Select a plan below.")
        self.tree.selection_set(self.selected if self.selected in self.routes else 'owned');self.choose()

    def choose(self):
        selection=self.tree.selection()
        if not selection or not self.plan:return
        self.selected=selection[0];route=self.routes[self.selected]
        lines=[]
        for p in route['allocation']:
            lines.append(f"{p['name']}: turn in {p['items']:,} ({p['batches']:,} bundles); own {p['owned']:,}; need {p['shortage']:,} more; keep {p['leftover']:,}.")
        lines.append(f"{route['xp']:,} EXP turned in; {self.plan['overshootXp']:,.0f} EXP over the target if fully completed. " + ('Uses owned stock only.' if route['ownedOnly'] else 'Additional items must be obtained.'))
        self.details.set('\n'.join(lines));self.draw()

    def draw(self):
        if not self.plan:return
        c=self.line;c.delete('all');p=self.plan;w=max(380,c.winfo_width());max_items=max(1,max(point['items'] for row in p['lines'] for point in row['points']))
        c.create_text(10,10,text='REQUIRED ITEMS BY TARGET CP',anchor='w',fill='#d2bfeb',font=('Segoe UI Semibold',9))
        left=72;right=w-20;top=30;bottom=150
        for i in range(5):
            y=bottom-(bottom-top)*i/4;c.create_line(left,y,right,y,fill='#382b43');c.create_text(left-5,y,text=f'{max_items*i/4:,.0f}',anchor='e',fill='#b9adcb',font=('Segoe UI',8))
        for n,row in enumerate(p['lines']):
            coords=[]
            for pt in row['points']:coords.extend((left+(pt['cp']-p['cp'])/max(1,p['target']-p['cp'])*(right-left),bottom-pt['items']/max_items*(bottom-top)))
            if len(coords)>2:c.create_line(*coords,fill=COLORS[row['key']],width=4 if row['key']=='catalyst' else 2,**({'dash':(4,4)} if row['key']=='witch' else {}))
            c.create_text(12+n*(w-24)/3,179,text=row['name'],anchor='w',fill=COLORS[row['key']],font=('Segoe UI',8))
        c.create_text(left,161,text=f"{p['cp']} CP",fill='#b9adcb',anchor='w',font=('Segoe UI',8));c.create_text(right,161,text=f"{p['target']} CP",fill='#b9adcb',anchor='e',font=('Segoe UI',8))
        c=self.pie;c.delete('all');route=self.routes.get(self.selected)
        if not route:return
        total=p['exchangeXp'];start=90;rows=[(a['key'],a['name'],a['ownedXp']) for a in route['allocation']]+[('missing','Missing EXP',route['missingXp'])]
        c.create_text(10,10,text='OWNED EXP COVERAGE · SELECTED PLAN',anchor='w',fill='#d2bfeb',font=('Segoe UI Semibold',9))
        if not total:c.create_text(15,55,text='Target already reached. No exchanges required.',anchor='w',fill='#d2bfeb');return
        for n,(key,name,xp) in enumerate(rows):
            fraction=xp/total
            if fraction:
                if fraction>=1:c.create_oval(15,30,160,175,fill=COLORS[key],outline='')
                else:c.create_arc(15,30,160,175,start=start,extent=-fraction*360,fill=COLORS[key],outline='')
                start-=fraction*360
            c.create_text(180,47+n*31,text=f'{name}: {fraction:.1%} · {xp:,} EXP',anchor='w',fill=COLORS[key],font=('Segoe UI',9))
        c.create_oval(52,67,123,138,fill=self.owner.app.colors['panel'],outline='')
        c.create_text(87,101,text=f"{route['ownedXp']/total:.0%}",fill='#f0e7f8',font=('Segoe UI Semibold',14))
