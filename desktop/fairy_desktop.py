"""Compact read-only treasure catalog and recorded loot; the website owns the vault."""
import json
import tkinter as tk
from tkinter import ttk
from pathlib import Path
from big_drops import BY_NAME,key


def catalog():return json.loads((Path(__file__).parent/'assets/fairy-catalog.json').read_text(encoding='utf-8'))


class FairyDesktop:
    def __init__(self,app):self.app=app;self.window=None
    def open(self):
        if self.window and self.window.winfo_exists():self.window.lift();return
        c=self.app.colors;win=self.window=tk.Toplevel(self.app.root);win.title('Vision · Fairy Codex / compact');win.geometry('700x520');win.configure(bg=c['bg'])
        canvas=tk.Canvas(win,bg=c['bg'],highlightthickness=0);scroll=ttk.Scrollbar(win,orient='vertical',command=canvas.yview);scroll.pack(side='right',fill='y');canvas.pack(fill='both',expand=True);canvas.configure(yscrollcommand=scroll.set)
        top=tk.Frame(canvas,bg=c['bg'],padx=14,pady=12);item=canvas.create_window(0,0,window=top,anchor='nw');top.bind('<Configure>',lambda e:canvas.configure(scrollregion=canvas.bbox('all')));canvas.bind('<Configure>',lambda e:canvas.itemconfigure(item,width=e.width))
        from ui_scroll import enable_page_wheel
        enable_page_wheel(canvas)
        tk.Label(top,text='FAIRY CODEX / TREASURE DESK',bg=c['bg'],fg=c['bright'],font=('Segoe UI Semibold',14)).pack(anchor='w')
        self.app.text_button(top,'FULL FAIRY CODEX / COLLECTION & SIMULATORS',self.app.open_fairy).pack(anchor='w',pady=7)
        self.items=catalog();self.tree=ttk.Treeview(top,columns=('name','rarity'),show='headings',height=5,style='Loot.Treeview');self.tree.heading('name',text='TREASURE');self.tree.heading('rarity',text='CATALOG RARITY');self.tree.column('name',width=420);self.tree.column('rarity',width=150);self.tree.pack(fill='x')
        for row in self.items:self.tree.insert('','end',iid=row['id'],values=(row['name'],row.get('rarity','')))
        self.detail=tk.StringVar();tk.Label(top,textvariable=self.detail,bg=c['bg'],fg=c['text'],justify='left',wraplength=650,font=('Segoe UI',10)).pack(fill='x',pady=10)
        self.loot=tk.StringVar();tk.Label(top,textvariable=self.loot,bg=c['bg'],fg=c.get('teal',c['bright']),justify='left',wraplength=650,font=('Segoe UI',9)).pack(fill='x')
        self.app.text_button(top,'REFRESH RECORDED FINDS',self.select).pack(anchor='w',pady=8)
        tk.Label(top,text='Recorded finds are observations, not verified ownership. Identical map/compass/telescope text cannot identify a specific piece. The website remains the full collection vault.',bg=c['bg'],fg=c['muted'],wraplength=650,justify='left',font=('Segoe UI',9)).pack(anchor='w')
        self.tree.bind('<<TreeviewSelect>>',self.select);self.tree.selection_set(self.items[0]['id']);self.select()
    def select(self,event=None):
        picks=self.tree.selection()
        if not picks:return
        r=next(v for v in self.items if v['id']==picks[0]);self.detail.set(r['name']+'\n'+r.get('benefit','')+'\n\n'+'\n'.join('• '+p[1]+' / '+p[2] for p in r['parts']))
        rows=self.app.loot.ledger.db.execute('SELECT item,SUM(quantity) FROM loot GROUP BY item').fetchall()
        known=[(name,n) for name,n in rows if key(name) in BY_NAME and BY_NAME[key(name)]['category']=='Treasure']
        self.loot.set('ALL RECORDED TREASURE FINDS\n'+('\n'.join(name+' × '+str(n) for name,n in known[:10]) or 'No recognized treasure-family drops recorded yet.'))
