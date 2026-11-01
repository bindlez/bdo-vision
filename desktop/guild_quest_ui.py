"""Small optional guild tracker; no worker or polling while disabled."""
import hashlib,shutil,threading,time,winsound
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from PIL import ImageGrab
from guild_quest import GuildQuestProgress,recognize_quest
from windows_bdo import foreground_bdo_capture_bounds,item_regions_visible


class GuildQuestTracker:
    def __init__(self,tracker,settings):
        self.tracker=tracker;self.app=tracker.app;self.root=tracker.root
        self.model=GuildQuestProgress(tracker.ledger.db)
        self.enabled=tk.BooleanVar(value=bool(settings.get('guild_quest_enabled',False)))
        self.sound=tk.BooleanVar(value=bool(settings.get('guild_quest_sound',True)))
        self.threshold=tk.StringVar(value=str(settings.get('guild_quest_threshold',95)))
        self.region=settings.get('guild_quest_region');self.frame=None;self.closed=False;self.busy=False;self.pending=None;self.generation=0
        self.progress=tk.StringVar(value='— / —');self.state=tk.StringVar(value='Guild Quest tracking is off')
        self.detail=tk.StringVar(value='Show the alchemy guild mission in BDO’s right-hand quest widget.')
        self.notice=tk.StringVar(value='Near-finish and completion alerts are sent once per quest.')
        self.debug=tk.StringVar();self.bar=None;self.cache=None
        if self.enabled.get():self.schedule(1000)

    def settings(self):
        return {'guild_quest_enabled':self.enabled.get(),'guild_quest_region':self.region,
                'guild_quest_threshold':self.safe_threshold(),'guild_quest_sound':self.sound.get()}

    def safe_threshold(self):
        try:return max(1,min(99,int(self.threshold.get())))
        except (ValueError,TypeError):return 95

    def build(self,tabs):
        c=self.app.colors;self.frame=frame=tk.Frame(tabs,bg=c['bg'],padx=20,pady=16);tabs.add(frame,text='Guild Quest')
        row=tk.Frame(frame,bg=c['bg']);row.pack(fill='x')
        ttk.Checkbutton(row,text='Track alchemy guild quest (optional)',variable=self.enabled,command=self.toggle,style='Vision.TCheckbutton').pack(side='left')
        ttk.Checkbutton(row,text='Sound alerts',variable=self.sound,command=self.app.save_quietly,style='Vision.TCheckbutton').pack(side='right')
        tk.Label(frame,text='ALCHEMY · GUILD QUEST',bg=c['bg'],fg=c['muted'],font=('Segoe UI Semibold',10)).pack(anchor='w',pady=(22,4))
        tk.Label(frame,textvariable=self.progress,bg=c['bg'],fg=c['bright'],font=('Segoe UI Semibold',36)).pack(anchor='w')
        self.bar=ttk.Progressbar(frame,maximum=100,style='Vision.Horizontal.TProgressbar');self.bar.pack(fill='x',pady=(10,14))
        tk.Label(frame,textvariable=self.state,bg=c['bg'],fg=c['bright'],font=('Segoe UI Semibold',11)).pack(anchor='w')
        tk.Label(frame,textvariable=self.detail,bg=c['bg'],fg=c['secondary'],font=('Segoe UI',10),wraplength=850,justify='left').pack(anchor='w',pady=(8,16))
        alert=tk.Frame(frame,bg=c['panel'],padx=14,pady=14);alert.pack(fill='x')
        tk.Label(alert,text='Alert when progress reaches',bg=c['panel'],fg=c['text']).pack(side='left')
        picker=ttk.Combobox(alert,textvariable=self.threshold,values=('80','85','90','95','99'),width=5,state='readonly',style='Vision.TCombobox');picker.pack(side='left',padx=10);picker.bind('<<ComboboxSelected>>',lambda e:self.app.save_quietly())
        tk.Label(alert,text='%',bg=c['panel'],fg=c['text']).pack(side='left')
        self.app.text_button(alert,'TEST ALERT',lambda:self.alert('test')).pack(side='right')
        tk.Label(frame,textvariable=self.notice,bg=c['panel2'],fg=c['bright'],padx=12,pady=12,wraplength=840,justify='left',font=('Segoe UI',10)).pack(fill='x',pady=(12,18))
        buttons=tk.Frame(frame,bg=c['bg']);buttons.pack(fill='x')
        self.app.action(buttons,'READ NOW',self.read_now,primary=True).pack(side='left',padx=(0,8))
        self.app.action(buttons,'NEXT QUEST',self.next_quest,flat=True).pack(side='left')
        self.app.text_button(buttons,'CUSTOM AREA',self.select_region).pack(side='right')
        self.app.text_button(buttons,'USE AUTO AREA',self.auto_region).pack(side='right',padx=12)
        tk.Label(frame,text='Default: read the alchemy guild mission in the right-hand quest widget every 10 seconds. For a moved widget, select a custom area containing its heading and current objective. Hidden or unclear counters pause measurement. No loot credit is inferred and no quest is accepted automatically.',bg=c['bg'],fg=c['muted'],font=('Segoe UI',9),wraplength=850,justify='left').pack(anchor='w',pady=(18,8))
        tk.Label(frame,textvariable=self.debug,bg=c['bg'],fg=c['muted'],font=('Segoe UI',9),wraplength=850,justify='left').pack(anchor='w')
        self.refresh()

    def schedule(self,delay=10000):
        if not self.closed and self.enabled.get() and self.pending is None:self.pending=self.root.after(delay,self.poll)

    def toggle(self):
        self.generation+=1
        if self.pending is not None:self.root.after_cancel(self.pending);self.pending=None
        self.model.pause('Waiting for a visible mission' if self.enabled.get() else 'Guild Quest tracking is off')
        self.app.save_quietly();self.refresh();self.schedule(500)

    def select_region(self):
        if self.busy or self.app.busy or self.tracker.busy:self.notice.set('Wait for the current reader pass to finish.');return
        self.app.select_region('guild')

    def set_region(self,region):
        if region[2]*region[3]>250000:self.notice.set('That area is too large. Select only the mission heading and its progress.');return
        self.region=region;self.cache=None;self.generation+=1;self.app.save_quietly()
        self.notice.set('Custom mission area saved. Tracking uses this area when enabled.')

    def auto_region(self):
        self.region=None;self.cache=None;self.generation+=1;self.app.save_quietly()
        self.notice.set('Automatic right-hand quest widget area selected.')

    def next_quest(self):
        self.model.reset();self.cache=None;self.generation+=1;self.notice.set('Previous progress archived. Show the next alchemy guild mission.');self.refresh()

    def poll(self):
        self.pending=None
        if self.closed or not self.enabled.get():return
        self.scan()

    def read_now(self):
        if self.busy or self.app.busy or self.tracker.busy:self.notice.set('Wait for the current reader pass to finish.');return
        self.notice.set('Switch to BDO now. Reading the guild objective in 3 seconds…')
        self.root.after(3000,lambda:self.scan(manual=True) if not self.closed else None)

    def capture_region(self):
        if self.region:
            ready,reason=item_regions_visible([self.region])
            if not ready:raise RuntimeError(reason)
            x,y,w,h=self.region;return (x,y,x+w,y+h)
        bounds=foreground_bdo_capture_bounds()
        if bounds is None:raise RuntimeError('Bring BDO to the front with the alchemy guild objective visible.')
        _,left,top,right,bottom=bounds;w=right-left;h=bottom-top
        return (left+int(w*.76),top+int(h*.32),left+int(w*.995),top+int(h*.70))

    def scan(self,manual=False):
        if self.closed:return
        if self.busy or self.app.busy or self.tracker.busy or self.app.selecting_region:
            if manual:self.notice.set('The readers are busy. Try READ NOW after this pass.')
            self.schedule(1000);return
        tess=self.app.tess.get().strip().strip('"')
        if not (Path(tess).is_file() or shutil.which(tess)):
            self.model.pause('Tesseract is unavailable; check Settings.');self.refresh();self.schedule();return
        try:box=self.capture_region()
        except Exception as exc:
            self.model.pause(str(exc));self.refresh();self.schedule(5000);return
        if (box[2]-box[0])*(box[3]-box[1])>250000:
            self.model.pause('Use a custom area around the current mission, up to 250,000 pixels.');self.refresh();self.schedule();return
        self.busy=True;self.app.busy=True;generation=self.generation;started=time.monotonic()
        self.state.set('Reading the visible guild objective…')
        def work():
            try:
                if self.capture_region()!=box:raise RuntimeError('Mission area moved or was covered; retrying.')
                image=ImageGrab.grab(bbox=box,all_screens=True).convert('RGB');captured=time.time()
                if self.capture_region()!=box:raise RuntimeError('Mission area moved or was covered; retrying.')
                key=(tess,box,hashlib.sha256(image.tobytes()).digest());cached=self.cache
                if cached and cached[0]==key and time.monotonic()-cached[1]<60:reading,raw=cached[2],cached[3];reused=True
                else:reading,raw=recognize_quest(image,tess);reused=False
                if reading:self.cache=(key,time.monotonic(),reading,raw)
                if not self.closed:self.root.after(0,lambda:self.finish(reading,raw,generation,captured,time.monotonic()-started,reused))
            except Exception as exc:
                message=str(exc)
                if not self.closed:self.root.after(0,lambda:self.failed(message,generation))
        threading.Thread(target=work,name='vision-guild-quest',daemon=True).start()

    def finish(self,reading,raw,generation,captured,duration,reused):
        self.busy=False;self.app.busy=False
        if self.closed:return
        if generation!=self.generation:self.schedule();return
        if reading:
            for event in self.model.accept(reading,self.safe_threshold(),captured):self.alert(event)
        else:self.model.pause('No agreed guild objective counter. Keep the guild heading and progress visible.')
        self.debug.set(f"Reader {duration:.2f}s · "+('unchanged verified pixels reused' if reused else 'two OCR passes')+' · no screenshot saved')
        self.refresh();self.schedule(10000 if reading else 30000)

    def failed(self,message,generation):
        self.busy=False;self.app.busy=False
        if not self.closed:
            if generation==self.generation:self.model.pause(message);self.refresh()
            self.schedule()

    def alert(self,event):
        messages={'near':'Alchemy guild objective is nearly finished. Get ready to complete it and choose the next one.',
                  'complete':'Guild objective complete. Check BDO to finish the mission and accept the next one.',
                  'test':'Guild Quest test alert. This does not change your progress.'}
        message=messages[event];self.notice.set(message);self.app.status.set(message)
        if self.sound.get():winsound.MessageBeep(winsound.MB_ICONASTERISK)

    def refresh(self):
        view=self.model.snapshot();current=view['current'];target=view['target']
        bridge=getattr(self.app,'bridge',None)
        published={**view,'enabled':self.enabled.get(),'threshold':self.safe_threshold()}
        if bridge and published!=getattr(self,'_published',None):bridge.update_guild_status(published);self._published=published
        def changed(variable,value):
            if variable.get()!=value:variable.set(value)
        changed(self.progress,f'{current:,} / {target:,}' if current is not None else '— / —')
        if self.bar and float(self.bar['value'])!=view['percent']:self.bar['value']=view['percent']
        if not self.enabled.get():state='MANUAL SNAPSHOT · automatic tracking off' if view['available'] else 'TRACKING OFF · saved progress retained'
        elif not view['available']:state='PAUSED · '+view['reason']
        elif view['complete']:state='OBJECTIVE COMPLETE · check BDO for the next quest'
        else:state=f"OBSERVING · {view['percent']:.1f}% · {view['remaining']:,} remaining"
        changed(self.state,state)
        age=max(0,int(time.time()-view['last_at'])) if view['last_at'] is not None else None
        detail=view['label']+'\n'+view['objective']
        if age is not None:detail+=f'\nLast verified {age}s ago.'
        if view['eta'] is not None:detail+=f" At the recent visible pace: about {int(view['eta']//60)}m {int(view['eta']%60)}s remaining."
        changed(self.detail,detail)

    def close(self):
        self.closed=True;self.generation+=1
        if self.pending is not None:self.root.after_cancel(self.pending);self.pending=None
        self.model.save()
