"""Small in-memory reader status, shared by the native view and local diagnostics."""
from collections import deque
import time


TITLES={'idle':'Ready to find tools','reading':'Reading visible tools','waiting':'Switch to BDO',
        'searching':'Looking for readable labels','confirming':'Confirming the active tool',
        'found':'Tools found · waiting for use','tracking':'Active tool confirmed',
        'ambiguous':'Several tools are changing','paused':'Capture paused','off':'Automatic reader off',
        'error':'Reader will retry','empty':'Visible tools are empty'}


class ToolStatus:
    def __init__(self):
        self.stage='idle';self.detail='Show cooking/alchemy labels in BDO. No box is needed.'
        self.tools=[];self.unreadable=0;self.active_id=None;self.last_at=None
        self.scans=0;self.calls=0;self.hits=0;self.duration=0.;self.revision=0
        self.events=deque(maxlen=16)

    def set_stage(self,stage,detail):
        detail=str(detail)[:220]
        if (stage,detail)==(self.stage,self.detail):return False
        self.stage=stage;self.detail=detail;self.revision+=1
        self.events.append({'at':round(time.time(),3),'stage':stage,'detail':detail})
        return True

    def accept(self,report):
        fields=('id','name','current','maximum','percent','state','wear_streak','seconds_per_use','cache_hit')
        self.tools=[{k:row[k] for k in fields if k in row} for row in report.get('tools',[])[:8]]
        self.unreadable=len(report.get('unreadable',[])[:8]);self.active_id=report.get('active_id')
        self.last_at=report.get('captured_at',time.time());self.duration=round(report.get('duration',0),3)
        self.scans+=1;self.calls+=report.get('ocr_calls',0);self.hits+=report.get('cache_hits',0);self.revision+=1
        active=next((r for r in self.tools if r['id']==self.active_id),None)
        if active:stage='tracking';detail=f"{active['name']} · {active['current']:,} / {active['maximum']:,}"
        elif not self.tools:stage='searching';detail='Keep the full tool label and durability on screen. Search continues automatically.'
        elif all(r['current']==0 for r in self.tools):stage='empty';detail='The readable tools have no durability remaining.'
        elif sum(r.get('wear_streak',0)>=2 for r in self.tools)>1:stage='ambiguous';detail='Waiting for enough evidence to identify your tool safely.'
        elif any(r.get('wear_streak',0)>0 for r in self.tools):stage='confirming';detail='Durability use detected. Waiting for one more change.'
        else:stage='found';detail=f"{len(self.tools)} readable tool(s). Start crafting to confirm which one is active."
        if self.unreadable:detail+=f' {self.unreadable} other label(s) unreadable.'
        self.set_stage(stage,detail)

    def snapshot(self):
        return {'stage':self.stage,'title':TITLES.get(self.stage,self.stage),'detail':self.detail,
                'tools':[dict(row) for row in self.tools],'active_id':self.active_id,'unreadable':self.unreadable,
                'last_read_at':self.last_at,'scans':self.scans,'ocr_calls':self.calls,'cache_hits':self.hits,
                'last_seconds':self.duration,'revision':self.revision,'recent':list(self.events)}
