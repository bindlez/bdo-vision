"""Event-driven session charts and comparable personal-best pacing; no new OCR."""
import tkinter as tk


def personal_best(current,history,prices):
    if not current or current.get('unpriced') or current.get('observed_seconds',0)<60:return None
    candidates=[]
    for row in history:
        if row['id']==current['id'] or not row.get('ended_at') or row['spot'].casefold()!=current['spot'].casefold():continue
        if row.get('activity','Grinding')!=current.get('activity','Grinding') or row['observed_seconds']<600:continue
        items=row['items']
        if not items or any(not prices.get(p['item']) or prices[p['item']].get('unit_price') is None for p in items):continue
        # Reprice accepted quantities on today's same price book, never compare
        # current prices against old frozen prices as if they were performance.
        value=sum(p['quantity']*prices[p['item']]['unit_price'] for p in items)
        candidates.append((value*3600/row['observed_seconds'],row['id']))
    if not candidates:return None
    best,ident=max(candidates)
    if best<=0 or current.get('silver_hour') is None:return None
    baseline=best*current['observed_seconds']/3600
    return {'bestHour':best,'run':ident,'pacePercent':current['silver_hour']/best*100,
            'aheadSilver':current['value']-baseline,'projectedHour':current['silver_hour']}


class GrindCharts:
    def __init__(self,parent,colors):
        self.colors=colors;self.row=None
        self.canvas=tk.Canvas(parent,height=235,bg=colors['panel'],highlightthickness=0)
        self.canvas.pack(fill='x',pady=8);self.canvas.bind('<Configure>',lambda e:self.draw(self.row))

    def draw(self,row):
        self.row=row;c=self.canvas;c.delete('all');colors=self.colors
        if not row:return
        w=max(440,c.winfo_width());palette=[colors.get('teal','#63d9cf'),colors['bright'],'#edbc76','#88aefa','#e69bbd','#92899f']
        values=[(p['item'],p['value']) for p in row['items'] if p['value'] is not None and p['value']>0]
        values.sort(key=lambda p:-p[1]);values=values[:5]+([('Other priced items',sum(v for _,v in values[5:]))] if len(values)>5 else [])
        self.donut(76,95,58,values,palette)
        c.create_text(12,16,text='LOOT VALUE MIX · PRICED ITEMS',fill=colors['secondary'],anchor='w',font=('Segoe UI Semibold',8))
        total=sum(v for _,v in values)
        for i,(name,value) in enumerate(values):
            c.create_text(12,164+i*11,text=f'{name[:25]} · {value/total:.0%}',anchor='w',fill=palette[i],font=('Segoe UI',8))
        x=w*.65;observed=row['observed_seconds'];excluded=row['excluded_seconds']
        self.donut(x,95,58,[('Observed',observed),('Excluded',excluded)],[palette[0],'#4e425f'])
        c.create_text(x,16,text='OBSERVED / EXCLUDED TIME',fill=colors['secondary'],font=('Segoe UI Semibold',8))
        c.create_text(x,95,text=f"{row['coverage']:.0%}",fill=colors['text'],font=('Segoe UI Semibold',16))
        c.create_text(x,165,text=f'{observed:,.0f}s observed · {excluded:,.0f}s excluded',fill=colors['secondary'],font=('Segoe UI',8))
        c.create_text(x,185,text=f"{row['unpriced']} unpriced types excluded from value",fill=colors['muted'],font=('Segoe UI',8))

    def donut(self,x,y,r,values,colors):
        total=sum(max(0,v) for _,v in values);c=self.canvas
        if not total:c.create_oval(x-r,y-r,x+r,y+r,fill='#45394f',outline='')
        start=90
        for i,(_,value) in enumerate(values):
            if value<=0 or not total:continue
            extent=360*value/total
            if extent>=359.999:c.create_oval(x-r,y-r,x+r,y+r,fill=colors[i%len(colors)],outline='')
            else:c.create_arc(x-r,y-r,x+r,y+r,start=start,extent=-extent,fill=colors[i%len(colors)],outline='')
            start-=extent
        c.create_oval(x-r*.63,y-r*.63,x+r*.63,y+r*.63,fill=self.colors['panel'],outline='')
