"""Measured recording sessions and gross valuation of observed items."""
import time
import uuid
import json
from item_names import canonical_item


def summarize(rows,prices,seconds=None):
    prices=dict(prices)
    for quote in list(prices.values()):
        if quote.get('market_name'):prices.setdefault(quote['market_name'],quote)
    grouped={}
    for row in rows:
        item=canonical_item(row[2]);matched=prices.get(item);item=matched.get('market_name',item) if matched else item
        entry=grouped.setdefault(item,{'item':item,'quantity':0,'rare':0,'crafted':0})
        entry['quantity']+=row[3]
        if row[6] in ('Rare drop','Rare craft'):entry['rare']+=row[3]
        if row[6] in ('Crafted','Rare craft'):entry['crafted']+=row[3]
    for item,entry in grouped.items():
        price=prices.get(item)
        entry.update(unit_price=price['unit_price'] if price else None,source=price['source'] if price else 'Unpriced',value=entry['quantity']*price['unit_price'] if price else None)
    items=sorted(grouped.values(),key=lambda e:(-(e['value'] or 0),e['item'].casefold()))
    value=sum(e['value'] or 0 for e in items);quantity=sum(e['quantity'] for e in items)
    priced=sum(e['unit_price'] is not None for e in items)
    valid_time=seconds is not None and seconds>=60
    return {'items':items,'quantity':quantity,'events':len(rows),'value':value if priced else None,'unpriced':len(items)-priced,'priced_types':priced,'total_types':len(items),'silver_hour':value*3600/seconds if valid_time and priced else None,'units_hour':quantity*3600/seconds if valid_time else None,'crafted':sum(e['crafted'] for e in items),'rare':sum(e['rare'] for e in items),'seconds':seconds,'warming_up':seconds is not None and seconds<60}


class SessionClock:
    def __init__(self,seconds=0,now=None):
        self.seconds=float(seconds);self.running=False;self.gate=False;self.last=time.monotonic() if now is None else now

    def tick(self,gate,now=None):
        now=time.monotonic() if now is None else now
        if self.running and self.gate:self.seconds+=max(0,now-self.last)
        self.last=now;self.gate=bool(gate)
        return self.seconds


class InsightsSession:
    def __init__(self,db):
        self.db=db
        db.execute('CREATE TABLE IF NOT EXISTS insight_sessions (id TEXT PRIMARY KEY, created_at REAL NOT NULL, active_seconds REAL NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS insight_members (session TEXT NOT NULL, loot_id INTEGER NOT NULL, PRIMARY KEY(session,loot_id))');db.commit()
        db.execute('CREATE TABLE IF NOT EXISTS craft_session_models (session_id TEXT PRIMARY KEY,payload TEXT NOT NULL)');db.commit()
        fields={r[1] for r in db.execute('PRAGMA table_info(insight_sessions)')}
        for name,kind in [('label',"TEXT NOT NULL DEFAULT ''"),('activity',"TEXT NOT NULL DEFAULT 'Other'"),('recipe',"TEXT NOT NULL DEFAULT ''"),('targets',"TEXT NOT NULL DEFAULT '[]'"),('ended_at','REAL'),('price_snapshot',"TEXT NOT NULL DEFAULT '{}'")]:
            if name not in fields:db.execute('ALTER TABLE insight_sessions ADD COLUMN '+name+' '+kind)
        db.commit()
        latest=db.execute('SELECT id,active_seconds,ended_at,activity FROM insight_sessions ORDER BY created_at DESC LIMIT 1').fetchone()
        self.id=latest[0] if latest else None;self.clock=SessionClock(latest[1] if latest else 0);self.ended=bool(latest and latest[2] is not None);self.last_persist=0
        self.activity=latest[3] if latest else 'Other'

    @property
    def grinding(self):
        return bool(self.id and not self.ended and self.activity in ('Grinding','Treasure hunt'))

    def start(self,gate=True,now=None,label='',activity='Other',recipe='',targets=None):
        self.save();self.id=uuid.uuid4().hex;self.clock=SessionClock(now=now);self.clock.running=True;self.clock.gate=bool(gate)
        self.ended=False
        with self.db:self.db.execute('INSERT INTO insight_sessions(id,created_at,active_seconds,label,activity,recipe,targets) VALUES (?, ?, 0, ?, ?, ?, ?)',(self.id,time.time(),label.strip()[:100] or time.strftime('Session %m/%d %H:%M'),activity,recipe,json.dumps(targets or [])))
        self.activity=activity

    def pause_resume(self,gate=True,now=None):
        if not self.id:self.start(gate,now);return
        if self.ended:raise ValueError('This session is finished. Start a new session.')
        self.clock.tick(gate,now);self.clock.running=not self.clock.running;self.save()

    def tick(self,gate,now=None):
        value=self.clock.tick(gate,now)
        if time.monotonic()-self.last_persist>=5:self.save()
        return value

    def observe(self,row_id,gate=True,*,captured=False):
        self.tick(gate)
        if self.id and self.clock.running and (gate or captured):
            with self.db:self.db.execute('INSERT OR IGNORE INTO insight_members VALUES (?, ?)',(self.id,row_id))

    def rows(self,session_id=None):
        selected=session_id or self.id
        if not selected:return []
        return self.db.execute('SELECT l.id,l.recorded_at,l.item,l.quantity,l.source,l.session,l.kind FROM loot l JOIN insight_members m ON l.id=m.loot_id WHERE m.session=? ORDER BY l.id DESC',(selected,)).fetchall()

    def finish(self,prices,gate=True,now=None):
        if not self.id or self.ended:return
        self.clock.tick(gate,now);self.clock.running=False;self.ended=True
        names={canonical_item(row[2]) for row in self.rows()}
        model=None
        meta=self.db.execute('SELECT activity,recipe FROM insight_sessions WHERE id=?',(self.id,)).fetchone()
        if meta and meta[0]=='Crafting' and meta[1]:
            from craft_economy import resolve_recipe
            recipe=resolve_recipe(meta[1])
            if recipe:
                names.update(m['name'] for m in recipe['mats'])
                if self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='craft_models'").fetchone():
                    model=self.db.execute('SELECT payload FROM craft_models WHERE recipe_id=?',(recipe['id'],)).fetchone()
                    if model:names.update(m['name'] for m in json.loads(model[0]).get('materials',[]))
                    if model and json.loads(model[0]).get('region') and self.db.execute("SELECT 1 FROM sqlite_master WHERE name='market_quotes'").fetchone():
                        region=json.loads(model[0])['region']
                        prices={name:{'unit_price':value,'source':'Central Market ('+region+')','updated_at':stamp,'region':region} for name,value,stamp in self.db.execute('SELECT item,unit_price,updated_at FROM market_quotes WHERE region=?',(region,))}
        snapshot={name:prices[name] for name in names if name in prices}
        with self.db:self.db.execute('UPDATE insight_sessions SET active_seconds=?,ended_at=?,price_snapshot=? WHERE id=?',(self.clock.seconds,time.time(),json.dumps(snapshot),self.id))
        if model:
            with self.db:self.db.execute('INSERT OR REPLACE INTO craft_session_models VALUES (?,?)',(self.id,model[0]))

    def history(self):
        columns=('id','created_at','active_seconds','label','activity','recipe','targets','ended_at','price_snapshot')
        return [dict(zip(columns,row)) for row in self.db.execute('SELECT '+','.join(columns)+' FROM insight_sessions ORDER BY created_at DESC')]

    def save(self):
        if self.id:
            with self.db:self.db.execute('UPDATE insight_sessions SET active_seconds=? WHERE id=?',(self.clock.seconds,self.id))
        self.last_persist=time.monotonic()
