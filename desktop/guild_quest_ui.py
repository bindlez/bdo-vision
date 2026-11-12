"""Small optional guild tracker; no worker or polling while disabled."""
import hashlib,json,math,shutil,threading,time,winsound
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from PIL import ImageGrab,Image
from guild_quest import GuildQuestProgress,recognize_quest
from ocr_debug import OCRReaderView,preview_image,source_image
from windows_bdo import visible_bdo_capture_bounds,item_regions_visible
from guild_reminder import ReminderGate,reminder_decision


class GuildQuestTracker:
    def __init__(self,tracker,settings):
        self.tracker=tracker;self.app=tracker.app;self.root=tracker.root
        self.model=GuildQuestProgress(tracker.ledger.db)
        self._forecast=None;self._estimated_alert=False;self._unclaimed_since=None;self._unclaimed_alert=False
        self.enabled=tk.BooleanVar(value=bool(settings.get('guild_quest_enabled',False)))
        self.missing_alert=tk.BooleanVar(value=bool(settings.get('guild_quest_missing_alert',True)))
        self.missing_gate=ReminderGate();self.last_absence={};self.reminder_payload=None;self._reminder_stamp=None;self._last_alert_sound=0;self._last_sound_key=None
        self.watch=tk.BooleanVar(value=bool(settings.get('guild_quest_watch',False)))
        self.watch_pending=None;self.watch_box=None;self.watch_context=None;self.watch_widget=None;self._watch_read=False
        self.sound=tk.BooleanVar(value=bool(settings.get('guild_quest_sound',True)))
        self.threshold=tk.StringVar(value=str(settings.get('guild_quest_threshold',95)))
        self.units_per_craft=tk.StringVar(value=str(settings.get('guild_units_per_craft',''))[:20])
        self.region=settings.get('guild_quest_region');self.frame=None;self.closed=False;self.busy=False;self.pending=None;self.generation=0
        self.progress=tk.StringVar(value='— / —');self.state=tk.StringVar(value='Guild Quest tracking is off')
        self.detail=tk.StringVar(value='Show the alchemy guild mission in BDO’s right-hand quest widget.')
        self.notice=tk.StringVar(value='Near-finish and completion alerts are sent once per quest.')
        self.debug=tk.StringVar();self.bar=None;self.cache=None
        self.read_failures=0
        self.reader_view=OCRReaderView(self.app,'Quest OCR reader',self.read_now)
        self.objective_rows={};self.objective_tree=None;self.waiting=False
        self.phase='ready' if self.enabled.get() else 'off';self.last_attempt_at=None;self.last_seconds=None;self.read_attempts=0
        self.pipeline=tk.StringVar(value='Ready for a tool + quest snapshot' if self.enabled.get() else 'Tracking off · no quest OCR running')
        tracker.ledger.db.execute('CREATE TABLE IF NOT EXISTS quest_objectives (key TEXT PRIMARY KEY,payload TEXT NOT NULL)')
        for key,payload in tracker.ledger.db.execute('SELECT key,payload FROM quest_objectives LIMIT 8'):
            try:self.objective_rows[key]=json.loads(payload)
            except (ValueError,TypeError):pass
        tracker.ledger.db.commit()
        if self.enabled.get():self.schedule(1000)

    def settings(self):
        return {'guild_quest_enabled':self.enabled.get(),'guild_quest_watch':self.watch.get(),'guild_quest_region':self.region,
                'guild_quest_missing_alert':self.missing_alert.get(),
                'guild_quest_threshold':self.safe_threshold(),'guild_quest_sound':self.sound.get(),
                'guild_units_per_craft':self.units_per_craft.get()[:20]}

    def safe_threshold(self):
        try:return max(1,min(99,int(self.threshold.get())))
        except (ValueError,TypeError):return 95

    def build(self,tabs):
        from ui_scroll import notebook_page
        c=self.app.colors;self.frame,frame=notebook_page(tabs,'Quests',c)
        row=tk.Frame(frame,bg=c['bg']);row.pack(fill='x')
        ttk.Checkbutton(row,text='Enable quest reader',variable=self.enabled,command=self.toggle,style='Vision.TCheckbutton').pack(side='left')
        ttk.Checkbutton(row,text='Sound alerts',variable=self.sound,command=self.app.save_quietly,style='Vision.TCheckbutton').pack(side='right')
        ttk.Checkbutton(frame,text='Smart quest watch while crafting (optional · 15s checks; Lite Use stops it)',variable=self.watch,command=self.watch_changed,style='Vision.TCheckbutton').pack(anchor='w',pady=(8,0))
        ttk.Checkbutton(frame,text='Remind when a guild quest is complete, missing, or unverified',variable=self.missing_alert,command=self.app.save_quietly,style='Vision.TCheckbutton').pack(anchor='w',pady=(5,0))
        estimate=tk.Frame(frame,bg=c['bg']);estimate.pack(fill='x',pady=(5,0))
        tk.Label(estimate,text='Quest units per craft (optional fallback)',bg=c['bg'],fg=c['secondary']).pack(side='left')
        units=ttk.Entry(estimate,textvariable=self.units_per_craft,width=8,style='Vision.TEntry')
        units.pack(side='left',padx=8)
        units.bind('<Return>',lambda event:self.app.save_quietly())
        units.bind('<FocusOut>',lambda event:self.app.save_quietly())

        tk.Label(frame,text='COOKING / ALCHEMY · GUILD QUEST',bg=c['bg'],fg=c['muted'],font=('Segoe UI Semibold',10)).pack(anchor='w',pady=(12,4))
        tk.Label(frame,textvariable=self.progress,bg=c['bg'],fg=c['bright'],font=('Segoe UI Semibold',26)).pack(anchor='w')
        self.bar=ttk.Progressbar(frame,maximum=100,style='Vision.Horizontal.TProgressbar');self.bar.pack(fill='x',pady=(10,14))
        tk.Label(frame,textvariable=self.state,bg=c['bg'],fg=c['bright'],font=('Segoe UI Semibold',11)).pack(anchor='w')
        tk.Label(frame,textvariable=self.pipeline,bg=c['panel2'],fg=c['secondary'],font=('Segoe UI',9),padx=10,pady=8,wraplength=700,justify='left').pack(fill='x',pady=(8,0))
        tk.Label(frame,textvariable=self.detail,bg=c['bg'],fg=c['secondary'],font=('Segoe UI',10),wraplength=700,justify='left').pack(anchor='w',pady=(8,16))
        alert=tk.Frame(frame,bg=c['panel'],padx=14,pady=14);alert.pack(fill='x')
        tk.Label(alert,text='Alert when progress reaches',bg=c['panel'],fg=c['text']).pack(side='left')
        picker=ttk.Combobox(alert,textvariable=self.threshold,values=('80','85','90','95','99'),width=5,state='readonly',style='Vision.TCombobox');picker.pack(side='left',padx=10);picker.bind('<<ComboboxSelected>>',lambda e:self.app.save_quietly())
        tk.Label(alert,text='%',bg=c['panel'],fg=c['text']).pack(side='left')
        self.app.text_button(alert,'TEST ALERT',lambda:self.alert('test')).pack(side='right')
        tk.Label(frame,textvariable=self.notice,bg=c['panel2'],fg=c['bright'],padx=12,pady=12,wraplength=840,justify='left',font=('Segoe UI',10)).pack(fill='x',pady=(12,18))
        buttons=tk.Frame(frame,bg=c['bg']);buttons.pack(fill='x')
        self.app.action(buttons,'SCAN TOOL + QUEST',self.read_now,primary=True).pack(side='left',padx=(0,8))
        self.app.action(buttons,'NEXT QUEST',self.next_quest,flat=True).pack(side='left')
        self.app.text_button(buttons,'LIVE OCR READER',self.reader_view.open).pack(side='left',padx=12)
        self.app.text_button(buttons,'CUSTOM AREA',self.select_region).pack(side='right')
        self.app.text_button(buttons,'USE AUTO AREA',self.auto_region).pack(side='right',padx=12)
        self.app.text_button(buttons,'SNOOZE REMINDER 10m',lambda:self.missing_gate.snooze(time.time())).pack(side='right',padx=8)
        tk.Label(frame,text='LAST SEEN · Default: quests accompany tool scans. Enable Smart watch to get completion and missing-quest alerts between tool scans. It checks the visible guild card while crafting. Exact unchanged pixels reuse verified text. With enough verified readings, the craft timer can estimate when to check the quest. Lite Use stops Smart watch. Vision never accepts quests automatically.',bg=c['bg'],fg=c['muted'],font=('Segoe UI',9),wraplength=700,justify='left').pack(anchor='w',pady=(18,8))
        tk.Label(frame,textvariable=self.debug,bg=c['bg'],fg=c['muted'],font=('Segoe UI',9),wraplength=700,justify='left').pack(anchor='w')
        tk.Label(frame,text='DAILY & BONUS · LAST VERIFIED',bg=c['bg'],fg=c['bright'],font=('Segoe UI Semibold',10)).pack(anchor='w',pady=(12,5))
        self.objective_tree=ttk.Treeview(frame,columns=('kind','objective','progress','seen'),show='headings',height=3,style='Loot.Treeview')
        for key,title,width in [('kind','QUEST',70),('objective','OBJECTIVE',450),('progress','PROGRESS',120),('seen','LAST SEEN',100)]:
            self.objective_tree.heading(key,text=title);self.objective_tree.column(key,width=width,minwidth=50,stretch=key=='objective')
        self.objective_tree.pack(fill='x')
        self.refresh()

    def schedule(self,delay=10000):
        """No watch callback exists unless the user explicitly enables it."""
        if self.watch_pending is not None:self.root.after_cancel(self.watch_pending);self.watch_pending=None
        if self.closed or not self.enabled.get() or not self.watch.get() or self.app.lite_use.get():return
        self.watch_pending=self.root.after(max(15000,delay),self.poll)

    def watch_changed(self):
        self.app.save_quietly();self.schedule();self.refresh()
        self.notice.set('Smart watch: small guild card checks every 15s while the craft timer runs. Tool OCR stays held.' if self.watch.get() else 'Paired snapshots only. No independent quest checks run.')

    def toggle(self):
        self.waiting=False
        self.generation+=1
        if self.pending is not None:self.root.after_cancel(self.pending);self.pending=None
        self.model.pause('Waiting for a visible mission' if self.enabled.get() else 'Guild Quest tracking is off')
        self.phase='ready' if self.enabled.get() else 'off'
        self.pipeline.set('Ready · SCAN TOOL + QUEST, then return to BDO. Current timers are retained.' if self.enabled.get() else 'Tracking off · no quest OCR running')
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
        self.model.reset();self._forecast=None;self._estimated_alert=False;self._unclaimed_since=None;self._unclaimed_alert=False;self.cache=None;self.last_absence={};self.generation+=1;self.notice.set('Previous progress archived. Show the next cooking or alchemy guild mission.');self.refresh()

    def poll(self):
        self.watch_pending=None
        if self.closed or not self.enabled.get() or not self.watch.get() or self.app.lite_use.get():return
        if not self.app.running or self.app.busy or self.tracker.busy or self.app.selecting_region or getattr(self.app,'cp_ocr_busy',False):self.schedule();return
        self._watch_read=True
        self.scan(paired=True)

    def read_now(self):
        if self.busy or self.app.busy or self.tracker.busy:self.notice.set('Wait for the current reader pass to finish.');return
        if not self.enabled.get():self.notice.set('Enable guild tracking to include a last-seen quest reading with tool scans.');return
        self.notice.set('Switch to BDO. Reading the tool and last-seen guild widget together…')
        self.app.rescan_tools()

    def saved_widget(self,bounds):
        auto_align=getattr(self.tracker,'auto_align',None)
        if auto_align is None or not auto_align.get() or not bounds:return None
        try:
            from loot_layout import find_saved_layout
            return find_saved_layout(bounds).get('quest_widget')
        except (OSError,ValueError):
            return None

    def capture_region(self):
        bounds=visible_bdo_capture_bounds()
        quest=self.saved_widget(bounds)
        if self._watch_read and self.watch_box:
            if bounds==self.watch_context and quest==self.watch_widget:
                a,b,c,d=self.watch_box;ready,reason=item_regions_visible([(a,b,c-a,d-b)])
                if not ready:raise RuntimeError(reason)
                return self.watch_box
            self.watch_box=None;self.watch_context=None;self.watch_widget=None
        if quest:
            ready,reason=item_regions_visible([quest])
            if not ready:raise RuntimeError(reason)
            x,y,w,h=quest;return (x,y,x+w,y+h)
        if self.region:
            ready,reason=item_regions_visible([self.region])
            if not ready:raise RuntimeError(reason)
            x,y,w,h=self.region;return (x,y,x+w,y+h)
        if bounds is None:raise RuntimeError('Bring BDO to the front with the alchemy guild objective visible.')
        _,left,top,right,bottom=bounds;w=right-left;h=bottom-top
        box=(left+int(w*.80),top+int(h*.32),left+int(w*.995),top+int(h*.94))
        ready,reason=item_regions_visible([(box[0],box[1],box[2]-box[0],box[3]-box[1])])
        if not ready:raise RuntimeError(reason)
        return box

    def scan(self,manual=False,paired=False,sample=None,ticket=None):
        if self.closed or not self.enabled.get():return
        if not paired:
            self.waiting=False;self.notice.set('Guild readings accompany tool scans. Use READ NOW to scan both.');return
        if ticket is not None and ticket[0]!=self.generation:self.waiting=False;return
        if self.busy:return
        if ticket is None:ticket=(self.generation,time.monotonic()+3)
        if self.app.busy or self.tracker.busy or self.app.selecting_region or getattr(self.app,'cp_ocr_busy',False):
            if time.monotonic()<ticket[1]:
                self.waiting=True;self.phase='queued';self.pipeline.set('Queued behind the current reader · your paired quest snapshot will run next')
                if self.pending is None:
                    def retry():
                        self.pending=None;self.scan(manual=manual,paired=True,sample=sample,ticket=ticket)
                    self.pending=self.root.after(100,retry)
            else:
                self.waiting=False;self._watch_read=False;self.phase='retry';self.pipeline.set('Snapshot could not get an idle reader slot · SCAN TOOL + QUEST to retry; saved counters are safe');self.schedule()
            return
        self.waiting=False
        tess=self.app.tess.get().strip().strip('"')
        if not (Path(tess).is_file() or shutil.which(tess)):
            self._watch_read=False;self.model.pause('Tesseract is unavailable; check Settings.');self.refresh();self.schedule();return
        try:box=self.capture_region()
        except Exception as exc:
            self._watch_read=False
            self.phase='blocked';self.pipeline.set('Capture blocked · '+str(exc)[:180])
            self.reader_view.paused(str(exc))
            self.model.pause(str(exc));self.refresh();self.schedule(5000);return
        if (box[2]-box[0])*(box[3]-box[1])>(250000 if self.region else 1_000_000):
            self.model.pause('Use a custom area around the current mission, up to 250,000 pixels.');self.refresh();self.schedule();return
        self.busy=True;self.app.busy=True;generation=self.generation;started=time.monotonic()
        self.last_attempt_at=time.time();self.read_attempts+=1;self.phase='reading';self.pipeline.set('Reading quest cards · verifying both counter passes; no progress is guessed')
        self.state.set('Reading the visible guild objective…')
        debug_token=self.reader_view.token()
        def work():
            try:
                if self.capture_region()!=box:raise RuntimeError('Mission area moved or was covered; retrying.')
                if sample is not None and sample[1]==box and 0<=time.time()-sample[2]<=10:
                    image=sample[0].convert('RGB');captured=sample[2]
                else:image=ImageGrab.grab(bbox=box,all_screens=True).convert('RGB');captured=time.time()
                if self.capture_region()!=box:raise RuntimeError('Mission area moved or was covered; retrying.')
                if image.width*image.height>250000:
                    scale=math.sqrt(249000/(image.width*image.height));image=image.resize((int(image.width*scale),int(image.height*scale)),Image.Resampling.LANCZOS)
                def diagnostic(frame,detail):
                    if debug_token is not None and self.reader_view.token()==debug_token:
                        picture=source_image(frame)
                        self.root.after(0,lambda:self.reader_view.show(debug_token,picture,detail,captured))
                diagnostic(image,'CAPTURE RECEIVED\nRegion: '+str(box)+'\nRecognition is starting. This frame is retained if a later OCR pass fails.')
                key=(tess,box,hashlib.sha256(image.tobytes()).digest());cached=self.cache
                if cached and cached[0]==key and time.monotonic()-cached[1]<60:reading,raw=cached[2],cached[3];reused=True
                else:
                    worker=getattr(self.app,'windows_ocr',None)
                    if worker is not None:
                        from structured_reader import recognize_quest_structured
                        reading,raw=recognize_quest_structured(image,tess,worker,diagnostic=diagnostic if debug_token is not None else None)
                    else:reading,raw=recognize_quest(image,tess,diagnostic=diagnostic if debug_token is not None else None)
                    reused=False
                if reading:self.cache=(key,time.monotonic(),reading,raw)
                if reading and reading.get('card_box'):
                    sx=(box[2]-box[0])/image.width;sy=(box[3]-box[1])/image.height;a,b,c,d=reading['card_box']
                    reading={**reading,'_card_region':(box[0]+int(a*sx),box[1]+int(b*sy),box[0]+int(c*sx),box[1]+int(d*sy))}
                if debug_token is not None and self.reader_view.token()==debug_token:
                    preview=preview_image(image)
                    detail=('VERIFIED RESULT\n'+json.dumps(reading,indent=2) if reading else 'NOT ACCEPTED: no scoped counter agreed in two passes.')+'\n\nOCR PASSES\n'+raw
                    self.root.after(0,lambda:self.reader_view.show(debug_token,preview,detail,captured))
                if not self.closed:self.root.after(0,lambda:self.finish(reading,raw,generation,captured,time.monotonic()-started,reused))
            except Exception as exc:
                message=str(exc)
                if not self.closed:self.root.after(0,lambda:self.failed(message,generation))
        threading.Thread(target=work,name='vision-guild-quest',daemon=True).start()

    def finish(self,reading,raw,generation,captured,duration,reused):
        was_watch=self._watch_read;self.busy=False;self.app.busy=False;self._watch_read=False
        if self.closed:return
        if generation!=self.generation:self.schedule();return
        verified=bool(reading and ('current' in reading or reading.get('completion_observed')))
        absent=bool(reading and reading.get('absence_observed') and reading.get('absence_votes')==2)
        if absent:self.last_absence={**reading,'absence_at':captured}
        elif verified:self.last_absence={}
        if was_watch and not verified:self.watch_box=None;self.watch_context=None
        self.last_seconds=round(duration,3);self.phase='verified' if verified else 'retry'
        self.pipeline.set(('Verified last-seen snapshot' if verified else 'No agreed guild counter · inspect LIVE OCR READER, then retry')+f' · {duration:.2f}s'+(' · exact pixels reused' if reused else ''))
        if not verified and (reading or {}).get('objectives'):
            self.phase='partial';self.pipeline.set(f"{len(reading['objectives'])} Daily/Bonus counter(s) verified · guild counter not readable; show the alchemy guild objective · {duration:.2f}s")
        if verified:
            prior=self.model.snapshot(captured)
            for event in self.model.accept(reading,self.safe_threshold(),captured):self.alert(event)
            self.update_craft_projection(prior,captured)
            if self.model.pending is not None:
                self.phase='confirming';self.pipeline.set('A different quest counter was seen · saved progress is retained until a second verified read, or use NEXT QUEST after accepting a new mission')
            if reading.get('_card_region'):
                self.watch_box=tuple(reading['_card_region']);self.watch_context=visible_bdo_capture_bounds()
                self.watch_widget=self.saved_widget(self.watch_context)
        else:
            if absent:
                self._forecast=None;self._estimated_alert=False;self._unclaimed_since=None;self._unclaimed_alert=False
            self.model.pause('Verified explicit no-active-guild-mission message' if absent else 'No agreed guild counter or completion message. Keep the quest widget visible.')
        for row in (reading or {}).get('objectives',[]):
            value={**row,'last_at':captured};previous=self.objective_rows.get(row['key'])
            self.objective_rows[row['key']]=value
            if not previous or any(previous.get(k)!=value[k] for k in ('current','target','objective')):
                with self.tracker.ledger.db:self.tracker.ledger.db.execute('INSERT INTO quest_objectives VALUES (?,?) ON CONFLICT(key) DO UPDATE SET payload=excluded.payload',(row['key'],json.dumps(value)))
            if row['current']==row['target'] and (not previous or previous['current']!=previous['target']):
                self.notice.set(f"{row['kind']} objective complete: {row['objective']}")
                if self.sound.get():winsound.MessageBeep(winsound.MB_ICONASTERISK)
        while len(self.objective_rows)>8:self.objective_rows.pop(min(self.objective_rows,key=lambda k:self.objective_rows[k]['last_at']))
        if self.objective_rows:
            keys=list(self.objective_rows)
            with self.tracker.ledger.db:self.tracker.ledger.db.execute('DELETE FROM quest_objectives WHERE key NOT IN ('+','.join('?' for _ in keys)+')',keys)
        self.debug.set(f"Reader {duration:.2f}s · "+('unchanged verified pixels reused' if reused else 'two OCR passes')+' · no screenshot saved')
        self.read_failures=0 if verified else self.read_failures+1
        self.refresh()
        self.check_crafting_quest()
        self.schedule()

    def update_craft_projection(self,prior,captured):
        view=self.model.snapshot(captured)
        if self.model.pending is not None:
            self._forecast=None
            return
        if view['complete']:
            self._forecast=None
            if self.app.detailed_craft.get() and view['available']:
                if self._unclaimed_since is None:self._unclaimed_since=captured
                elif not self._unclaimed_alert and captured-self._unclaimed_since>=20:
                    self._unclaimed_alert=True
                    self.alert('unclaimed')
            return
        if view['last_at']!=captured:return
        if prior['complete'] or prior['target']!=view['target'] or (prior['current'] is not None and view['current']<prior['current']):
            self._estimated_alert=False;self._forecast=None;self._unclaimed_since=None;self._unclaimed_alert=False
        eta=view['eta'];basis='observed pace'
        if eta is None and view['remaining']:
            try:
                units=float(self.units_per_craft.get())
                seconds=float(self.app.speed.get())
                if 0<units<=10000 and .05<=seconds<=3600:
                    eta=view['remaining']*seconds/units
                    basis='entered pace'
            except ValueError:pass
        if self.app.running and eta is not None:
            self._forecast={'session':self.app.session_id,'remaining':eta,
                            'clock':time.monotonic(),'running':True,'basis':basis}

    def timer_estimate_mode(self):
        return not self.app.grind_owns_tracking() and self.app.craft_state().estimate_quest

    def forecast_text(self):
        estimate=self._forecast
        if not self.enabled.get() or not estimate or estimate['session']!=self.app.session_id or not self.timer_estimate_mode():
            return ''
        if self._estimated_alert:return 'May be complete · verify in BDO'
        return 'Est. quest '+self.app.fmt(estimate['remaining'])

    def tick_craft_projection(self):
        estimate=self._forecast
        if not estimate or not self.enabled.get():return
        app=self.app
        if estimate['session']!=app.session_id or (self.model.mission_deadline is not None and time.time()>self.model.mission_deadline):
            self._forecast=None
            return
        now=time.monotonic()
        if app.running and estimate['running']:
            estimate['remaining']=max(0,estimate['remaining']-(now-estimate['clock']))
        estimate['running']=app.running;estimate['clock']=now
        if app.running and app.value>0 and self.timer_estimate_mode() and estimate['remaining']<=0 and not self._estimated_alert:
            self._estimated_alert=True
            self.alert('estimated',estimate['basis'])

    def check_crafting_quest(self):
        self.tick_craft_projection()
        if self.busy or self.waiting:return
        report=getattr(self.app,'tool_report',None) or {}
        active=None if self.app.grind_owns_tracking() else next((r for r in report.get('tools',[]) if r['id']==report.get('active_id')),None)
        if not active:
            if self.reminder_payload is not None:self.reminder_payload=None;self._reminder_stamp=None;self.refresh()
            return
        from tool_reader import family
        now=time.time();quest={**self.model.snapshot(now),**self.last_absence}
        decision=reminder_decision(quest,family(active['name']),now,enabled=self.missing_alert.get(),crafting=bool(self.app.running))
        stamp=(getattr(self.app,'session_id',''),bool(self.app.running),active['id'],repr(decision),self.sound.get())
        if stamp==self._reminder_stamp:return
        self._reminder_stamp=stamp;self.reminder_payload=decision
        event=self.missing_gate.accept(decision,getattr(self.app,'session_id',''),now)
        if event:
            self.notice.set(event['message'])
            self.app.status.set(event['message'])
            if event['sound']:self.play_alert_sound(event['key'])
        self.refresh()

    def failed(self,message,generation):
        self.busy=False;self.app.busy=False;self._watch_read=False
        self.reader_view.paused(message)
        if not self.closed:
            if generation!=self.generation:self.schedule();return
            self.phase='retry';self.pipeline.set('Snapshot failed · '+message[:180]+' · last verified progress retained')
            if generation==self.generation:self.model.pause(message);self.refresh()
            self.schedule()

    def play_alert_sound(self,key='complete'):
        now=time.monotonic()
        if self.sound.get() and (key!=self._last_sound_key or now-self._last_alert_sound>=2):
            self._last_alert_sound=now;self._last_sound_key=key;winsound.MessageBeep(winsound.MB_ICONASTERISK)

    def alert(self,event,basis='observed pace'):
        messages={'near':'Guild objective is nearly finished. Get ready to complete it and choose the next one.',
                  'complete':'Guild objective complete. Check BDO to finish the mission and accept the next one.',
                  'unclaimed':'Guild quest still shows Complete. Claim the rewards in BDO.',
                  'estimated':'Guild quest may be complete at the '+basis+'. Check BDO to confirm.',
                  'test':'Guild Quest test alert. This does not change your progress.'}
        message=messages[event];self.notice.set(message);self.app.status.set(message)
        self.play_alert_sound(event)

    def refresh(self):
        view=self.model.snapshot();current=view['current'];target=view['target']
        bridge=getattr(self.app,'bridge',None)
        published={**view,'enabled':self.enabled.get(),'threshold':self.safe_threshold(),'reminder':self.reminder_payload}
        held=bool(getattr(self.app,'_tool_scan_latched',False) or self.app.lite_use.get() and getattr(self.app,'lite_scan_complete',False))
        if not self.enabled.get():next_action='Enable quest reader, then SCAN TOOL + QUEST.'
        elif self.busy:next_action='Reading the visible objective now.'
        elif self.waiting:next_action='Queued behind the current reader; no new tool scan is needed.'
        elif self.model.pending is not None:next_action='Quest change needs confirmation. Read again, or use NEXT QUEST if you accepted a new mission in BDO.'
        elif self.watch.get() and not self.app.lite_use.get():next_action='Smart watch checks the visible guild card every 15s while crafting. Tool OCR stays held.'
        elif held:next_action='Tool timer is holding automatic OCR. Last-seen quests are retained; SCAN TOOL + QUEST reads again on demand.'
        else:next_action='Next tool acquisition includes a quest snapshot, or use SCAN TOOL + QUEST now.'
        published.update(read_stage=self.phase,next_action=next_action,read_attempts=self.read_attempts,last_read_seconds=self.last_seconds)
        if bridge and published!=getattr(self,'_published',None):bridge.update_guild_status(published);self._published=published
        def changed(variable,value):
            if variable.get()!=value:variable.set(value)
        changed(self.progress,'Complete' if view['complete'] else f'{current:,} / {target:,}' if current is not None else '— / —')
        if self.bar and float(self.bar['value'])!=view['percent']:self.bar['value']=view['percent']
        absent=self.last_absence.get('absence_at')
        if absent is not None and 0<=time.time()-absent<=35:state='NO ACTIVE GUILD MISSION · explicit message verified; accept a mission in BDO'
        elif view['complete']:state='Guild quest: Complete · '+('claim your rewards in BDO' if view['available'] else 'last seen; '+view['reason'])+(' · tracking off' if not self.enabled.get() else '')
        elif not self.enabled.get():state='MANUAL SNAPSHOT · automatic tracking off' if view['available'] else 'TRACKING OFF · saved progress retained'
        elif not view['available']:state=('LAST SEEN · saved snapshot' if current is not None else 'NO QUEST SNAPSHOT YET')+(' · Smart quest watch armed' if held and self.watch.get() and not self.app.lite_use.get() else ' · tool timer holds OCR' if held else ' · scan both readers when the objective is visible')
        else:state=f"LAST SEEN · {view['percent']:.1f}% · {view['remaining']:,} remaining"
        changed(self.state,state)
        age=max(0,int(time.time()-view['last_at'])) if view['last_at'] is not None else None
        detail=view['label']+'\n'+view['objective']+'\n'+next_action
        if view['completion_at'] is not None:
            detail+='\n'+view['completion_evidence']
            if current is not None:detail+=f'\nLast numeric counter: {current:,} / {target:,} (not inferred).'
            detail+=f"\nCompletion last seen {max(0,int(time.time()-view['completion_seen_at']))}s ago."
        if age is not None:detail+=f'\nLast verified {age}s ago.'
        if view['eta'] is not None:detail+=f" At the recent visible pace: about {int(view['eta']//60)}m {int(view['eta']%60)}s remaining."
        changed(self.detail,detail)
        if self.objective_tree:
            for key in self.objective_tree.get_children():
                if key not in self.objective_rows:self.objective_tree.delete(key)
            for key,row in self.objective_rows.items():
                values=(row['kind'],row['objective'],f"{row['current']:,} / {row['target']:,}",f"{max(0,int(time.time()-row['last_at']))}s ago")
                if self.objective_tree.exists(key):
                    if tuple(self.objective_tree.item(key)['values'])!=values:self.objective_tree.item(key,values=values)
                else:self.objective_tree.insert('','end',iid=key,values=values)

    def close(self):
        self.reader_view.close()
        self.closed=True;self.waiting=False;self.generation+=1
        if self.pending is not None:self.root.after_cancel(self.pending);self.pending=None
        if self.watch_pending is not None:self.root.after_cancel(self.watch_pending);self.watch_pending=None
        self.model.save()
