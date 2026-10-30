"""Automatic item-drop panels and optional crafting activity, with visible diagnostics."""
import shutil
import threading
import time
import json
from datetime import datetime
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox, filedialog
from PIL import ImageGrab, ImageTk
from dataclasses import replace
from loot_tracker import LootLedger, LootSnapshots,TextFeedSnapshots
from item_events import PopupSnapshots, ItemEvent
from loot_capture import recognize_feed
from windows_bdo import item_regions_visible
from insights_ui import LootInsights
from silver_ui import SilverLooted
from silver_loot import silver_snapshot
from capture_clock import CaptureClock
from grind_ui import GrindTracker


class LootTracker:
    def __init__(self,app,root_path,settings):
        self.app=app;self.root=app.root;self.path=root_path
        self.ledger=LootLedger(root_path/'loot-history.sqlite3')
        self.capture_clock=CaptureClock(self.ledger.db)
        self.ledger.db.execute('CREATE TABLE IF NOT EXISTS notification_baselines (feed TEXT PRIMARY KEY, items TEXT NOT NULL, saved_at REAL NOT NULL)')
        self.ledger.db.execute('CREATE TABLE IF NOT EXISTS uncertain_observations (item TEXT NOT NULL, quantity INTEGER NOT NULL, feed TEXT NOT NULL, first_seen REAL NOT NULL, last_seen REAL NOT NULL, sightings INTEGER NOT NULL, PRIMARY KEY(item,quantity,feed))');self.ledger.db.commit()
        self.restore_baselines=True;self.last_scan_ok=None;self.capture_reason='Waiting for a readable capture'
        self.session=str(time.time_ns())
        self.region=settings.get('item_drop_region',settings.get('loot_region'))
        self.rare_region=settings.get('rare_drop_region')
        self.feed=tk.StringVar(value=settings.get('loot_feed','Item Drop logs'))
        self.crafting=tk.BooleanVar(value=bool(settings.get('craft_tracking',False)))
        self.track_rare=tk.BooleanVar(value=bool(settings.get('track_rare',True)))
        self.interval=tk.StringVar(value=str(settings.get('loot_interval',2)))
        self.enabled=tk.BooleanVar(value=bool(settings.get('loot_enabled',False) and self.region))
        self.recording=tk.BooleanVar(value=bool(settings.get('record_loot',True)))
        self.share_loot=tk.BooleanVar(value=bool(settings.get('share_crafting_loot',False)))
        self.status=tk.StringVar(value='Select Item Drop Log. Optionally select Rare Item Drop Log above it. Then turn tracking ON.')
        self.capture_state=tk.StringVar(value='Item tracking: ON' if self.enabled.get() else 'Item tracking: OFF')
        self.summary=tk.StringVar();self.raw=tk.StringVar(value='No item notifications read yet.')
        self.last_read=tk.StringVar(value='Last read: no item identified yet')
        self.last_saved=tk.StringVar(value='Recording is ON — item names, quantities and times save locally.' if self.recording.get() else 'Preview only — recording is OFF.')
        self.last_scan_finished=0;self.capture_time=None;self.visible_tree=None;self.last_ocr_duration=0;self.scan_count=0;self.last_capture_gap=0
        self.tabs=None;self.window=None;self.tree=None;self.totals_tree=None;self.crafts_tree=None;self.preview=None;self.photo=None;self.debug_text=None
        self.closed=False;self.busy=False;self.generation=0;self.last_scan=0
        self.snapshots=LootSnapshots();self.channels={};self.empty_counts={};self.recent=[];self._baseline_persisted={}
        self.insights=LootInsights(self)
        self.silver=SilverLooted(self)
        self.grind=GrindTracker(self)
        self.root.after(250,self.poll)

    def settings(self):
        return {'loot_region':self.region,'item_drop_region':self.region,'rare_drop_region':self.rare_region,'loot_enabled':self.enabled.get(),'loot_feed':self.feed.get(),'craft_tracking':self.crafting.get(),'track_rare':self.track_rare.get(),'loot_interval':self.safe_interval(),'record_loot':self.recording.get(),'share_crafting_loot':self.share_loot.get()}

    def safe_interval(self):
        try:return max(.5,min(30,float(self.interval.get())))
        except ValueError:return 2

    def open(self):
        if self.window and self.window.winfo_exists():
            self.window.deiconify();self.window.lift()
            if self.tabs and self.silver.frame:self.tabs.select(self.silver.frame)
            return
        self._history_display_cache={};self._totals_cache=None;self._crafts_cache=None;self._last_refresh_key=None
        c=self.app.colors
        win=self.window=tk.Toplevel(self.root);win.title('BDO Vision • Silver, Grind & saved history');win.geometry('1000x900+20+20');win.minsize(940,820);win.configure(bg=c['bg'])
        main=tk.Frame(win,bg=c['bg'],padx=24,pady=20);main.pack(fill='both',expand=True)
        header=tk.Frame(main,bg=c['bg']);header.pack(fill='x')
        tk.Label(header,text='ACTIVITY',bg=c['bg'],fg=c['text'],font=('Segoe UI Semibold',22)).pack(side='left')
        self.tracker_setup_button=self.app.text_button(header,'CAPTURE SETUP',self.toggle_setup);self.tracker_setup_button.pack(side='right')
        tk.Label(main,textvariable=self.summary,bg=c['bg'],fg=c['bright'],font=('Segoe UI',10)).pack(anchor='w',pady=(4,14))
        setup_holder=tk.Frame(main,bg=c['bg']);setup_holder.pack(fill='x')
        self.setup_frame=tk.Frame(setup_holder,bg=c['bg']);self.setup_frame.pack(fill='x')
        controls=tk.Frame(self.setup_frame,bg=c['bg']);controls.pack(fill='x')
        self.app.action(controls,'SELECT ITEM DROP LOG',self.select_region).pack(side='left')
        self.app.action(controls,'SELECT RARE DROP LOG',lambda:self.select_region(True)).pack(side='left',padx=8)
        ttk.Checkbutton(controls,text='Tracking ON',variable=self.enabled,command=self.toggle,style='Vision.TCheckbutton').pack(side='left',padx=8)
        ttk.Checkbutton(controls,text='Record loot',variable=self.recording,command=self.toggle_recording,style='Vision.TCheckbutton').pack(side='left',padx=8)
        options=tk.Frame(self.setup_frame,bg=c['bg']);options.pack(fill='x',pady=(12,0))
        ttk.Checkbutton(options,text='Crafting mode',variable=self.crafting,command=self.toggle,style='Vision.TCheckbutton').pack(side='left')
        ttk.Checkbutton(options,text='Include rare log',variable=self.track_rare,command=self.toggle,style='Vision.TCheckbutton').pack(side='left',padx=12)
        ttk.Combobox(options,style='Vision.TCombobox',textvariable=self.feed,values=('Item Drop logs','Text feed'),state='readonly',width=17).pack(side='left')
        options.winfo_children()[-1].bind('<<ComboboxSelected>>',lambda e:self.toggle())
        tk.Label(options,text='Scan seconds',bg=c['bg'],fg=c['secondary']).pack(side='left',padx=(12,5))
        picker=ttk.Combobox(options,style='Vision.TCombobox',textvariable=self.interval,values=('0.5','1','2','3','5','10'),state='readonly',width=4);picker.pack(side='left');picker.bind('<<ComboboxSelected>>',lambda e:self.toggle())
        tk.Label(self.setup_frame,text='For grinding, Text feed + the personal “You have obtained…” panel retains drops longer. Select one feed only. Keep at least 6–8 complete rows visible. Crafting mode labels captured items as craft output.',bg=c['bg'],fg=c['muted'],font=('Segoe UI',9),wraplength=880,justify='left').pack(anchor='w',pady=(10,5))
        if self.region:self.setup_frame.pack_forget()
        tk.Label(main,textvariable=self.capture_state,bg=c['bg'],fg=c['bright'],font=('Segoe UI Semibold',10)).pack(anchor='w')
        tk.Label(main,textvariable=self.status,bg=c['bg'],fg=c['secondary'],wraplength=880,justify='left').pack(anchor='w',pady=(5,12))
        tk.Label(main,textvariable=self.last_read,bg=c['panel'],fg=c['text'],font=('Segoe UI Semibold',10),padx=12,pady=8,wraplength=850,justify='left').pack(fill='x')
        tk.Label(main,textvariable=self.last_saved,bg=c['bg'],fg=c['bright'],wraplength=880,justify='left').pack(anchor='w',pady=(5,10))
        style=ttk.Style();style.configure('Loot.Treeview',borderwidth=0,relief='flat',lightcolor=c['panel'],darkcolor=c['panel'],bordercolor=c['line'],background=c['panel'],fieldbackground=c['panel'],foreground=c['text'],rowheight=29,font=('Segoe UI',10));style.configure('Loot.Treeview.Heading',relief='flat',borderwidth=0,lightcolor=c['panel2'],darkcolor=c['panel2'],bordercolor=c['panel2'],background=c['panel2'],foreground=c['text'],font=('Segoe UI Semibold',9));style.map('Loot.Treeview',background=[('selected',c['violet'])],foreground=[('selected',c['text'])]);style.configure('Loot.TNotebook',background=c['bg'],borderwidth=0);style.configure('Loot.TNotebook.Tab',borderwidth=0,focuscolor=c['panel2'],background=c['panel2'],foreground=c['text'],padding=(12,10));style.map('Loot.TNotebook.Tab',background=[('selected',c['violet'])])
        self.tabs=tabs=ttk.Notebook(main,style='Loot.TNotebook');tabs.pack(fill='both',expand=True)
        def table(title,columns):
            frame=tk.Frame(tabs,bg=c['bg']);tabs.add(frame,text=title)
            tree=ttk.Treeview(frame,columns=tuple(name for name,_,_ in columns),show='headings',style='Loot.Treeview',height=8)
            for name,label,width in columns:tree.heading(name,text=label);tree.column(name,width=width,minwidth=60,stretch=name=='item')
            tree.pack(side='left',fill='both',expand=True);scroll=ttk.Scrollbar(frame,orient='vertical',command=tree.yview);scroll.pack(side='right',fill='y');tree.configure(yscrollcommand=scroll.set)
            return tree
        self.visible_tree=table('Live',[('item','RECOGNIZED ITEM',420),('qty','QUANTITY',100),('kind','ACTIVITY',120),('source','FEED',130)])
        self.tree=table('Loot',[('time','TIME',145),('item','ITEM',320),('qty','QUANTITY',90),('kind','ACTIVITY',100),('source','FEED',110)])
        self.crafts_tree=table('Crafts',[('item','CRAFTED ITEM',500),('qty','QUANTITY',120)])
        self.totals_tree=table('Totals',[('item','ITEM',440),('qty','QUANTITY',100),('kind','ACTIVITY',130)])
        self.insights.build(tabs)
        self.silver.build(tabs)
        self.grind.build(tabs)
        reader=tk.Frame(tabs,bg=c['bg']);tabs.add(reader,text='OCR reader')
        self.preview=tk.Label(reader,bg=c['panel'],fg=c['muted'],text='Latest capture will appear here.');self.preview.pack(fill='x',pady=8)
        self.debug_text=tk.Text(reader,height=10,bg=c['panel'],fg=c['text'],font=('Consolas',10),wrap='word',relief='flat',state='disabled');self.debug_text.pack(fill='both',expand=True)
        footer=tk.Frame(main,bg=c['bg']);footer.pack(fill='x',pady=(12,0))
        self.app.text_button(footer,'OPEN OCR DIAGNOSTICS',self.open_diagnostics).pack(side='left')
        self.app.action(footer,'EXPORT CSV',self.export).pack(side='right')
        self.refresh()
        tabs.select(self.silver.frame)

    def toggle_setup(self):
        if self.setup_frame.winfo_ismapped():self.setup_frame.pack_forget()
        else:self.setup_frame.pack(fill='x',pady=(0,12))

    def refresh(self):
        key=(self.ledger.revision,time.strftime('%Y-%m-%d'))
        if getattr(self,'_last_refresh_key',None)==key:return
        self._last_refresh_key=key
        rows=self.ledger.rows();today=time.strftime('%Y-%m-%d');current=[r for r in rows if r[1][:10]==today];totals={};crafts={}
        for row in current:
            key=(row[2],row[6]);totals[key]=totals.get(key,0)+row[3]
            if row[6] in ('Crafted','Rare craft'):crafts[row[2]]=crafts.get(row[2],0)+row[3]
        rare=sum(r[3] for r in current if r[6] in ('Rare drop','Rare craft'))
        self.summary.set(f'Saved history: {len(rows):,} events · {sum(r[3] for r in rows):,} items   |   Today ({today}): {sum(r[3] for r in current):,} items')
        if self.tree and self.tree.winfo_exists():
            cache=getattr(self,'_history_display_cache',{})
            for index,(ident,when,item,qty,source,session,kind) in enumerate(rows):
                values=(when[:19].replace('T',' '),item,f'{qty:,}',kind,source)
                if cache.get(ident)==values:continue
                if self.tree.exists(str(ident)):self.tree.item(str(ident),values=values)
                else:self.tree.insert('',index,iid=str(ident),values=values)
                cache[ident]=values
            self._history_display_cache=cache
            totals_key=tuple(sorted(totals.items()));crafts_key=tuple(sorted(crafts.items()))
            if getattr(self,'_totals_cache',None)!=totals_key:
                self.totals_tree.delete(*self.totals_tree.get_children())
                for (item,kind),qty in totals_key:self.totals_tree.insert('','end',values=(item,f'{qty:,}',kind))
                self._totals_cache=totals_key
            if getattr(self,'_crafts_cache',None)!=crafts_key:
                self.crafts_tree.delete(*self.crafts_tree.get_children())
                for item,qty in crafts_key:self.crafts_tree.insert('','end',values=(item,f'{qty:,}'))
                self._crafts_cache=crafts_key

    def export(self):
        path=filedialog.asksaveasfilename(parent=self.window,defaultextension='.csv',initialfile='bdo-item-activity.csv',filetypes=[('CSV','*.csv')])
        if path:
            try:self.ledger.export(path);self.status.set('Item history exported.')
            except OSError as exc:messagebox.showerror('Export',str(exc),parent=self.window)

    def open_diagnostics(self):
        import os
        folder=self.path/'loot-diagnostics';folder.mkdir(exist_ok=True);os.startfile(str(folder))

    def toggle(self):
        self.restore_baselines=False
        self.generation+=1;self.snapshots=LootSnapshots();self.channels={};self.empty_counts={};self.recent=[];self.last_scan=0
        if self.enabled.get() and not self.region:self.enabled.set(False);self.status.set('Select Item Drop Log before enabling tracking.')
        else:self.status.set('Tracking enabled. Visible popup items are recorded once, then only new notifications.' if self.enabled.get() else 'Tracking OFF. Saved history is retained.')
        self.capture_state.set('Item tracking: ON' if self.enabled.get() else 'Item tracking: OFF');self.app.save_quietly()

    def toggle_recording(self):
        self.toggle()
        self.last_saved.set('Recording ON — identified popup items will save locally.' if self.recording.get() else 'Preview only — recording OFF; saved history is retained.')

    def capture_regions(self):
        feeds={'chat' if self.feed.get()=='Text feed' else 'normal':self.region} if self.region else {}
        if self.feed.get()!='Text feed' and self.track_rare.get() and self.rare_region:feeds['rare']=self.rare_region
        return feeds

    def can_capture(self):
        return item_regions_visible(list(self.capture_regions().values()))

    def capture_availability(self):
        if not self.enabled.get():return False,'Loot tracking is off'
        if not self.recording.get():return False,'Recording is off'
        if getattr(self.app,'selecting_region',False):return False,'Selecting a capture area'
        ready,reason=self.can_capture()
        if not ready:return False,reason
        if not self.last_scan_finished:return False,'Waiting for the first readable capture'
        if time.time()-self.last_scan_finished>max(15,self.safe_interval()*3):return False,'Capture is stale; waiting for OCR'
        if self.last_scan_ok is False:return False,self.capture_reason
        return True,''


    def select_region(self,rare=False):
        if self.app.busy or self.busy:self.status.set('Wait for the current scan to finish.');return
        self.enabled.set(False);self.toggle();self.app.select_region('loot_rare' if rare else 'loot')

    def set_region(self,region,rare=False):
        if rare:self.rare_region=region
        else:self.region=region
        self.enabled.set(False);self.toggle();self.status.set(('Rare' if rare else 'Item')+' Drop Log area saved. Turn tracking ON and return to BDO.')

    def poll(self):
        if self.closed:return
        try:
            if self.enabled.get():
                if self.busy:self.capture_state.set('Tracking ON · reading item notifications')
                elif self.app.selecting_region:self.capture_state.set('Tracking ON · selecting capture area')
                else:
                    delay=max(0,self.safe_interval()-(time.monotonic()-self.last_scan))
                    if delay<=0:
                        ready,reason=self.can_capture()
                        if ready:self.scan()
                        else:self.capture_state.set('Tracking ON · '+reason)
                    else:self.capture_state.set('Tracking ON · next scan in %.1fs'%delay)
        except Exception as exc:self.status.set('Item OCR retry pending: '+str(exc))
        finally:
            if not self.closed:self.root.after(250,self.poll)

    def scan(self):
        if self.closed or self.busy or not self.enabled.get() or not self.region:return
        ready,reason=self.can_capture()
        if not ready:self.capture_state.set(reason);return
        started=time.monotonic();self.last_capture_gap=started-self.last_scan if self.last_scan else 0
        self.last_scan=started;tess=self.app.tess.get().strip().strip(chr(34))
        if not (shutil.which(tess) or Path(tess).is_file()):self.status.set('Tesseract missing. Set its path in Settings.');return
        try:
            feeds=self.capture_regions()
            images={}
            self.capture_time=time.time()
            for name,(x,y,w,h) in feeds.items():images[name]=ImageGrab.grab(bbox=(x,y,x+w,y+h),all_screens=True)
            if self.preview and self.preview.winfo_exists() and self.preview.winfo_ismapped():
                preview=images[next(iter(images))].copy();preview.thumbnail((820,180));self.photo=ImageTk.PhotoImage(preview);self.preview.configure(image=self.photo,text='')
            self.busy=True;self.status.set('Reading '+', '.join(feeds)+' notifications…')
            threading.Thread(target=self.recognize,args=(images,tess,self.generation,self.crafting.get()),daemon=True).start()
        except Exception as exc:self.busy=False;self.status.set('Item capture failed: '+str(exc))

    def recognize(self,images,tess,generation,crafting):
        started=time.monotonic()
        try:
            results={}
            for name,image in images.items():
                try:results[name]=recognize_feed(image,tess,name,crafting,self.path/'loot-diagnostics'/name,resolve_name=self.insights.prices.resolve_name)
                except Exception as exc:
                    # A rare-panel failure must not discard normal loot already read.
                    results[name]={'events':[],'empty':False,'recognized':0,'error':str(exc),'debug':'OCR error: '+str(exc)}
            if crafting and 'rare' in results:results['rare']['events']=[replace(e,kind='Rare craft') for e in results['rare']['events']]
            for result in results.values():
                valid=[];unresolved=[]
                for event in result['events']:
                    name=self.insights.prices.resolve_name(event.item)
                    if name:valid.append(replace(event,item=name))
                    else:unresolved.append(event)
                result['events']=valid;result['unresolved']=unresolved
                if unresolved:result['debug']+='\nUNMATCHED OCR (excluded automatically): '+repr(unresolved)
            duration=time.monotonic()-started
            if not self.closed:self.root.after(0,lambda:self.finish(results,generation,duration))
        except Exception as exc:
            error=str(exc)
            if not self.closed:self.root.after(0,lambda:self.failed(error,generation))

    def failed(self,error,generation):
        self.busy=False
        if not self.closed and self.enabled.get() and generation==self.generation:self.status.set('Item OCR failed: '+error)

    def commit(self,event,feed):
        if not self.recording.get():return False
        now=time.monotonic();self.recent=[r for r in self.recent if now-r['at']<=max(5,self.safe_interval()*3)]
        key=(event.item,event.quantity)
        # Match normal/rare duplicates one-to-one, preserving repeated real crafts.
        match=next((r for r in self.recent if r['key']==key and r['feed']!=feed and not r['paired']),None) if feed in ('normal','rare') else None
        if match:
            match['paired']=True
            if feed=='rare':self.ledger.mark_rare(match['id'],event.kind)
            return False
        observed_at=datetime.fromtimestamp(self.capture_time).astimezone().isoformat(timespec='milliseconds') if self.capture_time else None
        ident=self.ledger.add(event.item,event.quantity,{'normal':'Item Drop Log','rare':'Rare Drop Log','chat':'Text feed'}[feed],self.session,recorded_at=observed_at,kind=event.kind)
        self.insights.observe(ident)
        self.insights.prices.notice_item(event.item)
        self.recent.append({'id':ident,'key':key,'feed':feed,'at':now,'paired':False})
        return True

    def finish(self,results,generation,duration=0):
        self.busy=False
        if self.closed or not self.enabled.get() or generation!=self.generation:return
        # Compatibility with the pre-1.3 text snapshot tests and imported feeds.
        if isinstance(results,list):results={'chat':{'events':[ItemEvent(i,q,'Drop') for i,q in results],'empty':False,'debug':'','recognized':len(results)}}
        self.last_scan_finished=time.time()
        self.last_ocr_duration=duration;self.scan_count+=1
        primary=results.get('normal',results.get('chat',next(iter(results.values()),{})))
        self.last_scan_ok=bool(primary.get('events') or primary.get('empty'))
        self.capture_reason='OCR uncertain; waiting for a readable notification' if not primary.get('error') else 'OCR error; automatic retry pending'
        saved=0;skipped=0;baselines=0;messages=[];visible=[];saved_items=[]
        for name,result in results.items():
            rows=result['events'];visible.extend((event,name) for event in rows)
            accepted=', '.join(f'{e.item} ×{e.quantity}' for e in rows) or 'No agreed item name + quantity'
            messages.append(name.upper()+' — IDENTIFIED: '+accepted+'\n\n'+result['debug'])
            if name not in self.channels:
                tracker=TextFeedSnapshots() if name=='chat' else PopupSnapshots(record_initial=True)
                stored=self.ledger.db.execute('SELECT items,saved_at FROM notification_baselines WHERE feed=?',(name,)).fetchone()
                if self.restore_baselines and stored and 0<=time.time()-stored[1]<=120:
                    try:tracker.previous=[ItemEvent(**event) if event else None for event in json.loads(stored[0])]
                    except (ValueError,TypeError):pass
                self.channels[name]=tracker
            tracker=self.channels[name]
            baseline=tracker.previous is None
            if result['empty']:self.empty_counts[name]=self.empty_counts.get(name,0)+1
            else:self.empty_counts[name]=0
            if name=='chat' and result.get('slots') is not None:
                fresh,ambiguous=tracker.ingest_slots(result['slots'])
            else:fresh,ambiguous=tracker.ingest(rows) if name=='chat' else tracker.ingest(rows,empty=self.empty_counts[name]>=2)
            if tracker.previous is not None:
                baseline_key=tuple(tracker.previous);persisted=self._baseline_persisted.get(name);saved_at=time.time()
                if not persisted or persisted[0]!=baseline_key or saved_at-persisted[1]>=30:
                    data=[{'item':e.item,'quantity':e.quantity,'kind':e.kind,'stamp':e.stamp,'quantity_explicit':e.quantity_explicit} if e else None for e in tracker.previous]
                    with self.ledger.db:self.ledger.db.execute('INSERT INTO notification_baselines VALUES (?,?,?) ON CONFLICT(feed) DO UPDATE SET items=excluded.items,saved_at=excluded.saved_at',(name,json.dumps(data),saved_at))
                    self._baseline_persisted[name]=(baseline_key,saved_at)
            for event in result.get('unresolved',[]):
                with self.ledger.db:self.ledger.db.execute('INSERT INTO uncertain_observations VALUES (?,?,?,?,?,1) ON CONFLICT(item,quantity,feed) DO UPDATE SET last_seen=excluded.last_seen,sightings=sightings+1',(event.item,event.quantity,name,time.time(),time.time()))
            if baseline and rows:baselines+=1
            if ambiguous:skipped+=len(rows)
            else:
                for event in fresh:
                    if self.commit(event,name):saved+=1;saved_items.append(f'{event.item} ×{event.quantity}')
        self.last_read.set('Read at '+time.strftime('%H:%M:%S')+': '+('; '.join(f'{e.item} ×{e.quantity}' for e,_ in visible) or 'No item identified — see Live OCR reader.'))
        if saved_items:self.last_saved.set('Saved: '+', '.join(saved_items))
        elif not self.recording.get():self.last_saved.set('Preview only — recording is OFF.')
        elif skipped:self.last_saved.set('Feed overlap lost — uncertain rows skipped. Keep more complete message rows visible.')
        elif visible:self.last_saved.set('Already recorded / unchanged notification — not counted again.')
        if self.visible_tree and self.visible_tree.winfo_exists():
            self.visible_tree.delete(*self.visible_tree.get_children())
            for event,name in visible:self.visible_tree.insert('','end',values=(event.item,f'{event.quantity:,}',event.kind,name))
        self.raw.set('\n\n'.join(messages))
        if self.debug_text and self.debug_text.winfo_exists() and self.debug_text.winfo_ismapped():self.debug_text.configure(state='normal');self.debug_text.delete('1.0','end');self.debug_text.insert('1.0',self.raw.get());self.debug_text.configure(state='disabled')
        recognized=sum(len(r['events']) for r in results.values())
        unresolved=sum(len(r.get('unresolved',[])) for r in results.values())
        self.status.set(f'{saved} new events saved · {recognized} agreed notifications · {skipped} uncertain skipped'+(' · baseline set' if baselines else '')+(' · no readable item yet: check Live OCR reader and capture area' if not recognized else ''))
        if unresolved:self.status.set(self.status.get()+f' · {unresolved} unmatched OCR observations excluded automatically')
        errors=[name for name,result in results.items() if result.get('error')]
        if errors:self.status.set(self.status.get()+' · '+', '.join(errors)+' OCR error: see reader')
        if duration:self.status.set(self.status.get()+f' · OCR {duration:.2f}s · capture gap {self.last_capture_gap:.2f}s')
        holes=sum(sum(event is None for event in r.get('slots') or []) for r in results.values())
        if holes:self.status.set(self.status.get()+f' · {holes} unreadable message rows; retrying automatically')
        if skipped:self.status.set(self.status.get()+' · feed overlap lost; some drops could not be counted safely')
        self.refresh()

    def close(self):
        self.closed=True;self.generation+=1;self.capture_clock.save();self.silver.close();self.insights.close();self.ledger.close()

    def planner_loot_snapshot(self):
        prices=self.insights.prices
        quotes=prices.all()
        key=(self.ledger.revision,prices.revision,id(quotes))
        if getattr(self,'_shared_summary_key',None)!=key:
            rows=self.ledger.rows()
            self._shared_summary={**silver_snapshot(rows,quotes),
                'last_event_id':max((r[0] for r in rows),default=0),'captured_items_available':bool(rows),
                'crafted_units':sum(r[3] for r in rows if r[6] in ('Crafted','Rare craft'))}
            self._shared_summary_key=key
            self._shared_summary['summary_revision']=str(time.monotonic_ns())
        fresh,reason=self.capture_availability()
        return {'scope':'All recorded loot','available':fresh,'status':'current' if fresh else 'paused','reason':reason,
                'updated_at':time.time(),'last_capture_at':self.last_scan_finished or None,
                'history_id':self.capture_clock.history_id,'crafting_mode':self.crafting.get(),
                'capture_clock':self.capture_clock.snapshot(),'grind':self.grind.snapshot(),**self._shared_summary}

    def refresh_shared_loot(self):
        bridge=getattr(self.app,'bridge',None)
        if self.share_loot.get() and bridge:
            bridge.update_crafting_loot(self.planner_loot_snapshot())

    def share_changed(self):
        self.app.save_quietly()
        bridge=getattr(self.app,'bridge',None)
        if not self.share_loot.get() and bridge:bridge.clear_crafting_loot()
        elif bridge:self.refresh_shared_loot()
