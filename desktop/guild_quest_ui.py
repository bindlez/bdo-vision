"""Small optional guild tracker; no worker or polling while disabled."""
import hashlib,json,math,shutil,threading,time,winsound
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from PIL import ImageGrab,Image
from guild_quest import GuildQuestProgress,recognize_quest
from ocr_debug import OCRReaderView,preview_image,source_image
from windows_bdo import visible_bdo_capture_bounds,item_regions_visible


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
        self.read_failures=0
        self.reader_view=OCRReaderView(self.app,'Quest OCR reader',self.read_now)
        self.objective_rows={};self.objective_tree=None;self.waiting=False
        tracker.ledger.db.execute('CREATE TABLE IF NOT EXISTS quest_objectives (key TEXT PRIMARY KEY,payload TEXT NOT NULL)')
        for key,payload in tracker.ledger.db.execute('SELECT key,payload FROM quest_objectives LIMIT 8'):
            try:self.objective_rows[key]=json.loads(payload)
            except (ValueError,TypeError):pass
        tracker.ledger.db.commit()
        if self.enabled.get():self.schedule(1000)

    def settings(self):
        return {'guild_quest_enabled':self.enabled.get(),'guild_quest_region':self.region,
                'guild_quest_threshold':self.safe_threshold(),'guild_quest_sound':self.sound.get()}

    def safe_threshold(self):
        try:return max(1,min(99,int(self.threshold.get())))
        except (ValueError,TypeError):return 95

    def build(self,tabs):
        from ui_scroll import notebook_page
        c=self.app.colors;self.frame,frame=notebook_page(tabs,'Quests',c)
        row=tk.Frame(frame,bg=c['bg']);row.pack(fill='x')
        ttk.Checkbutton(row,text='Track Guild / Daily / Bonus quests',variable=self.enabled,command=self.toggle,style='Vision.TCheckbutton').pack(side='left')
        ttk.Checkbutton(row,text='Sound alerts',variable=self.sound,command=self.app.save_quietly,style='Vision.TCheckbutton').pack(side='right')
        tk.Label(frame,text='ALCHEMY · GUILD QUEST',bg=c['bg'],fg=c['muted'],font=('Segoe UI Semibold',10)).pack(anchor='w',pady=(12,4))
        tk.Label(frame,textvariable=self.progress,bg=c['bg'],fg=c['bright'],font=('Segoe UI Semibold',26)).pack(anchor='w')
        self.bar=ttk.Progressbar(frame,maximum=100,style='Vision.Horizontal.TProgressbar');self.bar.pack(fill='x',pady=(10,14))
        tk.Label(frame,textvariable=self.state,bg=c['bg'],fg=c['bright'],font=('Segoe UI Semibold',11)).pack(anchor='w')
        tk.Label(frame,textvariable=self.detail,bg=c['bg'],fg=c['secondary'],font=('Segoe UI',10),wraplength=700,justify='left').pack(anchor='w',pady=(8,16))
        alert=tk.Frame(frame,bg=c['panel'],padx=14,pady=14);alert.pack(fill='x')
        tk.Label(alert,text='Alert when progress reaches',bg=c['panel'],fg=c['text']).pack(side='left')
        picker=ttk.Combobox(alert,textvariable=self.threshold,values=('80','85','90','95','99'),width=5,state='readonly',style='Vision.TCombobox');picker.pack(side='left',padx=10);picker.bind('<<ComboboxSelected>>',lambda e:self.app.save_quietly())
        tk.Label(alert,text='%',bg=c['panel'],fg=c['text']).pack(side='left')
        self.app.text_button(alert,'TEST ALERT',lambda:self.alert('test')).pack(side='right')
        tk.Label(frame,textvariable=self.notice,bg=c['panel2'],fg=c['bright'],padx=12,pady=12,wraplength=840,justify='left',font=('Segoe UI',10)).pack(fill='x',pady=(12,18))
        buttons=tk.Frame(frame,bg=c['bg']);buttons.pack(fill='x')
        self.app.action(buttons,'READ NOW',self.read_now,primary=True).pack(side='left',padx=(0,8))
        self.app.action(buttons,'NEXT QUEST',self.next_quest,flat=True).pack(side='left')
        self.app.text_button(buttons,'LIVE OCR READER',self.reader_view.open).pack(side='left',padx=12)
        self.app.text_button(buttons,'CUSTOM AREA',self.select_region).pack(side='right')
        self.app.text_button(buttons,'USE AUTO AREA',self.auto_region).pack(side='right',padx=12)
        tk.Label(frame,text='Reads visible Guild, Daily and Bonus objective counters about every 10 seconds. For a moved widget, select a custom area containing the headings and objectives. Covered or unclear counters retain their last verified value. Vision never accepts quests automatically.',bg=c['bg'],fg=c['muted'],font=('Segoe UI',9),wraplength=700,justify='left').pack(anchor='w',pady=(18,8))
        tk.Label(frame,textvariable=self.debug,bg=c['bg'],fg=c['muted'],font=('Segoe UI',9),wraplength=700,justify='left').pack(anchor='w')
        tk.Label(frame,text='DAILY & BONUS · LAST VERIFIED',bg=c['bg'],fg=c['bright'],font=('Segoe UI Semibold',10)).pack(anchor='w',pady=(12,5))
        self.objective_tree=ttk.Treeview(frame,columns=('kind','objective','progress','seen'),show='headings',height=3,style='Loot.Treeview')
        for key,title,width in [('kind','QUEST',70),('objective','OBJECTIVE',450),('progress','PROGRESS',120),('seen','LAST SEEN',100)]:
            self.objective_tree.heading(key,text=title);self.objective_tree.column(key,width=width,minwidth=50,stretch=key=='objective')
        self.objective_tree.pack(fill='x')
        self.refresh()

    def schedule(self,delay=10000):
        if not self.closed and self.enabled.get() and self.pending is None:self.pending=self.root.after(delay,self.poll)

    def toggle(self):
        self.waiting=False
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
        self.waiting=True
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
        bounds=visible_bdo_capture_bounds()
        if bounds is None:raise RuntimeError('Bring BDO to the front with the alchemy guild objective visible.')
        _,left,top,right,bottom=bounds;w=right-left;h=bottom-top
        box=(left+int(w*.80),top+int(h*.32),left+int(w*.995),top+int(h*.94))
        ready,reason=item_regions_visible([(box[0],box[1],box[2]-box[0],box[3]-box[1])])
        if not ready:raise RuntimeError(reason)
        return box

    def scan(self,manual=False):
        if getattr(self.app,'lite_use',None) is not None and self.app.lite_use.get():
            self.waiting=False;self.model.pause('Lite Use · quest OCR paused');self.reader_view.paused('Lite Use');self.refresh();self.schedule();return
        if self.closed:return
        if self.busy or self.app.busy or self.tracker.busy or self.app.selecting_region:
            if manual:self.notice.set('The readers are busy. Try READ NOW after this pass.')
            self.waiting=self.enabled.get();self.schedule(250);return
        self.waiting=False
        tess=self.app.tess.get().strip().strip('"')
        if not (Path(tess).is_file() or shutil.which(tess)):
            self.model.pause('Tesseract is unavailable; check Settings.');self.refresh();self.schedule();return
        try:box=self.capture_region()
        except Exception as exc:
            self.reader_view.paused(str(exc))
            self.model.pause(str(exc));self.refresh();self.schedule(5000);return
        if (box[2]-box[0])*(box[3]-box[1])>(250000 if self.region else 1_000_000):
            self.model.pause('Use a custom area around the current mission, up to 250,000 pixels.');self.refresh();self.schedule();return
        self.busy=True;self.app.busy=True;generation=self.generation;started=time.monotonic()
        self.state.set('Reading the visible guild objective…')
        debug_token=self.reader_view.token()
        def work():
            try:
                if self.capture_region()!=box:raise RuntimeError('Mission area moved or was covered; retrying.')
                image=ImageGrab.grab(bbox=box,all_screens=True).convert('RGB');captured=time.time()
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
                else:reading,raw=recognize_quest(image,tess,diagnostic=diagnostic if debug_token is not None else None);reused=False
                if reading:self.cache=(key,time.monotonic(),reading,raw)
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
        self.busy=False;self.app.busy=False
        if self.closed:return
        if generation!=self.generation:self.schedule();return
        if reading and 'current' in reading:
            for event in self.model.accept(reading,self.safe_threshold(),captured):self.alert(event)
        else:self.model.pause('No agreed guild objective counter. Keep the guild heading and progress visible.')
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
        self.read_failures=0 if reading and 'current' in reading else self.read_failures+1
        retry=(3000,5000,10000,30000)[min(3,max(0,self.read_failures-1))]
        self.refresh();self.schedule(10000 if self.read_failures==0 else retry)

    def failed(self,message,generation):
        self.busy=False;self.app.busy=False
        self.reader_view.paused(message)
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
        self.model.save()
