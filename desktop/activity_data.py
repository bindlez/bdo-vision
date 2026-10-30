"""Read-only, event-ID based valuation for one attached website timer."""
import sqlite3
import json
import time
import math
from contextlib import closing
from datetime import datetime
from silver_loot import silver_snapshot


def timer_earnings(path,prices,after_id=0,before=None,since=None,kind=None):
    after_id=max(0,int(after_id))
    with closing(sqlite3.connect(str(path))) as db:
        query='SELECT id,recorded_at,item,quantity,source,session,kind FROM loot WHERE id>?'
        args=[after_id]
        if kind=='craft':query+=" AND kind IN ('Crafted','Rare craft')"
        elif kind is not None:raise ValueError('Invalid activity filter')
        if before is not None:
            end=float(before)
            if not math.isfinite(end):raise ValueError('Invalid end time')
            query+=" AND julianday(recorded_at)<=julianday(?,'unixepoch')";args.append(end)
        if since is not None:
            start=float(since)
            if not math.isfinite(start):raise ValueError('Invalid start time')
            query+=" AND julianday(recorded_at)>=julianday(?,'unixepoch')";args.append(start)
        # Aggregate inside SQLite: memory grows with item types, not drop count.
        where=query[query.index(' WHERE '):]
        groups=db.execute('SELECT MAX(id),MAX(recorded_at),item,SUM(quantity),NULL,NULL,kind,COUNT(*) FROM loot'+where+' GROUP BY item,kind',args).fetchall()
        rows=[r[:7] for r in groups]
        latest=db.execute(query+' ORDER BY id DESC LIMIT 12',args).fetchall()
        observed=0;elapsed=0
        if since is not None:
            end=min(time.time(),float(before)) if before is not None else time.time();start=float(since)
            if not math.isfinite(start) or not 0<=start<=end:raise ValueError('Invalid observation window')
            elapsed=end-start
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='capture_spans'").fetchone():
                observed=db.execute('SELECT COALESCE(SUM(MAX(0,MIN(ended_at,?)-MAX(started_at,?))),0) FROM capture_spans WHERE ended_at>? AND started_at<?',(end,start,start,end)).fetchone()[0]
    snapshot=silver_snapshot(rows,prices)
    snapshot['after_id']=after_id;snapshot['event_count']=sum(r[7] for r in groups)
    snapshot['events']=snapshot['event_count']
    snapshot['last_event_id']=max((r[0] for r in rows),default=after_id)
    snapshot['latest']=[{'id':r[0],'at':r[1],'item':r[2],'quantity':r[3],'kind':r[6]} for r in latest]
    snapshot['observed_seconds']=observed;snapshot['excluded_seconds']=max(0,elapsed-observed)
    return snapshot


def grind_session_detail(path,prices,session_id):
    from grind_ui import grind_summary
    with closing(sqlite3.connect(str(path))) as db:
        db.row_factory=sqlite3.Row
        meta=db.execute('SELECT * FROM insight_sessions WHERE id=?',(session_id,)).fetchone()
        if not meta or meta['activity'] not in ('Grinding','Treasure hunt'):return None
        meta=dict(meta);detail=db.execute('SELECT spot,goal FROM grind_details WHERE session=?',(session_id,)).fetchone()
        if detail:meta.update(dict(detail))
        rows=db.execute('SELECT loot.id,loot.recorded_at,loot.item,loot.quantity,loot.source,loot.session,loot.kind FROM loot JOIN insight_members ON loot.id=insight_members.loot_id WHERE insight_members.session=? ORDER BY loot.id DESC',(session_id,)).fetchall()
        if meta.get('ended_at'):prices=json.loads(meta['price_snapshot'])
    return grind_summary(meta,rows,prices,reason='Session completed' if meta.get('ended_at') else 'Retained session')
