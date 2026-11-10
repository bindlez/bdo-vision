"""Opt-in native live window and loopback OBS view; reuse the existing app tick."""
import tkinter as tk
from pathlib import Path
from datetime import datetime
import time
import json


def stream_page():
    js=(Path(__file__).parent/'assets/stream-overlay.js').read_text(encoding='utf-8')
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><title>Vision OBS</title><style>body{margin:0;background:transparent;color:#faf7ff;font:14px system-ui}main{border:1px solid #675480;border-top:3px solid #63d9cf;border-radius:12px;background:#14101eeb;padding:14px;max-width:440px}h1{font-size:14px;color:#63d9cf;margin:0 0 10px}section{display:grid;grid-template-columns:1fr 1fr;gap:12px}small{display:block;color:#cbbbdc}b{display:block;font-size:20px}p{font-size:12px}progress{width:100%;accent-color:#63d9cf}ul{font-size:12px;padding-left:18px}</style><main><h1>BDO VISION · LIVE</h1><div id="status" role="status">Connecting…</div><section><div><small>Recorded value</small><b id="value">—</b></div><div><small>Silver / observed hour</small><b id="rate">—</b></div><div><small>Observed / excluded</small><b id="time">—</b></div><div id="clockBox"><small>Local clock</small><b id="clock">—</b></div></section><p id="goal"></p><progress id="progress" max="1" value="0"></progress><ul id="loot"></ul></main><script>'+js+'</script></html>').encode('utf-8')


class LiveGrind:
    def __init__(self,grind):
        from craft_panel import CraftPanel
        self.grind=grind;self.window=None;self.hud=None;self.last=None;self.craft_panel=CraftPanel(self);self.craft_metrics=None

    def open(self):
        if self.window and self.window.winfo_exists():return
        from live_hud import LiveHUD
        self.hud=LiveHUD(self)
        if not self.hud.shown:
            self.window=None;self.hud=None
            self.grind.state.set('Windows could not create a passive overlay. The main tracker is still available.')
            return
        self.window=self.hud.surface.window
        big=getattr(self.grind.tracker,'big_drops',None)
        if big:big.reveals.retile()
        self.refresh()

    def settings(self):
        from live_hud import settings
        settings(self)

    def payload(self):
        g=self.grind;s=g.insights.session
        if not s.id or s.ended:return {'available':False,'status':'No active run','updatedAt':time.time()}
        # The session DB is shared with legacy tuple readers; use cursor metadata.
        cursor=s.db.execute('SELECT * FROM insight_sessions WHERE id=?',(s.id,));row=cursor.fetchone()
        if not row:return {'available':False,'status':'No active run','updatedAt':time.time()}
        meta=dict(zip([d[0] for d in cursor.description],row))
        if meta['activity'] not in ('Grinding','Treasure hunt'):return {'available':False,'status':'Current session is not a grind run','updatedAt':time.time()}
        detail=s.db.execute('SELECT spot,goal FROM grind_details WHERE session=?',(s.id,)).fetchone()
        if detail:meta.update(spot=detail[0],goal=detail[1])
        goal=s.db.execute('SELECT silver FROM grind_money_goals WHERE session=?',(s.id,)).fetchone()
        meta['silver_goal']=goal[0] if goal else g.tracker.platform_preferences.get('grind_silver_goal',0)
        ready,reason=g.tracker.capture_availability();meta['active_seconds']=s.clock.seconds
        from loot_insights import summarize
        from item_names import canonical_item
        prices=g.insights.prices.all();key=(s.id,g.tracker.ledger.revision,id(prices))
        if getattr(self,'cache_key',None)!=key:
            grouped=s.db.execute('SELECT MAX(l.id),MAX(l.recorded_at),l.item,SUM(l.quantity),NULL,NULL,l.kind FROM loot l JOIN insight_members m ON l.id=m.loot_id WHERE m.session=? GROUP BY l.item,l.kind',(s.id,)).fetchall()
            self.stats=summarize(grouped,prices)
            recent=s.db.execute('SELECT l.item,l.quantity FROM loot l JOIN insight_members m ON l.id=m.loot_id WHERE m.session=? ORDER BY l.id DESC LIMIT 6',(s.id,)).fetchall()
            self.latest=[{'item':canonical_item(item),'quantity':quantity} for item,quantity in recent];self.cache_key=key
        data=self.stats;observed=s.clock.seconds;elapsed=max(observed,time.time()-meta['created_at'])
        target=json.loads(meta.get('targets') or '[]');target=target[0] if target else ''
        count=sum(p['quantity'] for p in data['items'] if canonical_item(p['item']).casefold()==canonical_item(target).casefold()) if target else 0
        goal=max(1,int(meta.get('goal',1)))
        from grind_ui import duration
        return {'available':ready and s.clock.running,'status':('Observing' if ready and s.clock.running else 'Paused · '+(reason or 'manual pause'))+' · '+meta.get('spot',meta.get('label','Run')),
                'value':data['value'],'rate':data['value']*3600/observed if data['value'] is not None and observed>=60 else None,
                'time':duration(observed)+' / '+duration(max(0,elapsed-observed)),
                'goal':target,'count':count,'required':goal,'progress':min(1,count/goal) if target else None,
                'sessionActive':True,'unpriced':data['unpriced'],'latest':self.latest,'updatedAt':time.time(),'silverGoal':meta['silver_goal']}

    def refresh_craft_metrics(self,availability=None,snapshot=None):
        tracker=self.grind.tracker;app=tracker.app
        if not self.hud or not app.detailed_craft.get() or app.lite_use.get() or app.grind_owns_tracking():
            self.close_craft_metrics()
            return
        if app.selecting_region:return
        if self.craft_metrics is None:
            from craft_metrics_hud import CraftMetricsHUD
            self.craft_metrics=CraftMetricsHUD(self)
        ready,reason=tracker.capture_availability() if availability is None else availability
        self.craft_metrics.update(tracker.auto_craft.snapshot(ready) if snapshot is None else snapshot,reason)

    def close_craft_metrics(self):
        if self.craft_metrics is not None:
            self.craft_metrics.close()
            self.craft_metrics=None

    def refresh(self,availability=None,craft_snapshot=None):
        visible=self.window and self.window.winfo_exists() and self.window.winfo_ismapped()
        enabled=bool(self.grind.tracker.platform_preferences.get('obs_enabled',False));bridge=getattr(self.grind.tracker.app,'bridge',None)
        if bridge:
            with bridge._lock:bridge.stream_enabled=enabled
        if visible or enabled:
            data=self.payload()
            if bridge:
                with bridge._lock:bridge.stream_snapshot=data if enabled else {}
            if visible:self.hud.update(data)
        self.craft_panel.refresh()
        self.refresh_craft_metrics(availability,craft_snapshot)

    def obs_changed(self):
        self.grind.tracker.platform_preferences['obs_enabled']=self.grind.obs_enabled.get();self.grind.tracker.app.save_quietly();self.refresh()

    def copy_url(self):
        bridge=getattr(self.grind.tracker.app,'bridge',None)
        if not bridge:self.grind.state.set('Open the local planner bridge first.');return
        self.grind.root.clipboard_clear();self.grind.root.clipboard_append(bridge.base_url+'/stream')
        self.grind.state.set('OBS browser-source URL copied. Enable Share with OBS. Optional URL flags: ?clock=0&loot=0 for compact widgets.')
