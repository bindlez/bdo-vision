import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import time, threading, subprocess, os, re, json, ctypes, winsound, webbrowser, urllib.request, uuid, sys, shutil
from planner_bridge import PlannerBridge,PORTS
from loot_ui import LootTracker
from storage import prepare_storage,backup_profile,InstanceLock,focus_existing
from version import APP_VERSION
from pathlib import Path
from PIL import ImageGrab, Image, ImageOps, ImageEnhance, ImageFilter, ImageTk
from windows_bdo import is_bdo_foreground, send_ctrl_v_if_bdo_foreground, restore_bdo, super_restore_bdo, inspect_bdo_visibility
from ocr_parser import choose_reading, reading_is_plausible, extract_pairs
from scan_engine import select_ocr_passes, should_publish, candidate_is_stable, SpeedEstimator
from tracking_core import ReadingGate, remaining_at, align_to_capture, estimate_send
from spatial_ocr import tsv_candidates, choose_spatial_pair
from ocr_runtime import run_ocr
from tool_reader import AutomaticToolReader
from ocr_debug import OCRReaderView,label_montage,preview_image,source_image
from tool_status import ToolStatus,estimate_durability
from windows_bdo import foreground_bdo_capture_bounds

ROOT=(Path(sys.executable).resolve().parent if getattr(sys,'frozen',False)
      else Path(__file__).resolve().parent)
DATA_ROOT=prepare_storage(ROOT)
CFG=DATA_ROOT/'settings.json'
DEFAULT={'region':[520,210,520,55],'seconds_per_craft':1.0,'warning':10,'durability':1000,'maximum':3000,'tesseract':r'C:\Program Files\Tesseract-OCR\tesseract.exe','auto_scan':True,'scan_interval':10,'alarm_repeats':5,'quiet_mode':True,'wide_tracking':True}
try: config={**DEFAULT,**json.loads(CFG.read_text())}
except Exception: config=DEFAULT.copy()
if config.get('scan_interval')==5:config['scan_interval']=10

class App:
 def __init__(self,root):
  self.root=root
  root.title(f'BDO Vision {APP_VERSION}  •  Saved history')
  root.geometry('380x560+12+60')
  root.minsize(340,420)
  root.configure(bg='#08070d')
  try:
   icon_path=ROOT/'assets'/'bdo-lite.png'
   self.app_icon=ImageTk.PhotoImage(Image.open(icon_path))
   root.iconphoto(True,self.app_icon)
  except (OSError,tk.TclError):self.app_icon=None
  self.running=False;self.anchor=None;self.last_scan_started=0
  self.auto_enabled=tk.BooleanVar(value=bool(config.get('auto_scan',False)))
  self.scan_interval=tk.StringVar(value=str(config.get('scan_interval',10)))
  self.alarm_repeats=tk.StringVar(value=str(config.get('alarm_repeats',5)))
  self.last_good_ocr=None;self.value=float(config['durability']);self.alarmed=False
  self.busy=False;self.last_ocr=None;self.last_read_at=None;self.last_image=None;self.ocr_debug=''
  self.settings_window=None;self.photo=None;self.last_send_status='';self.super_restoring=False
  self.reading_gate=ReadingGate();self.has_reading=False;self.sync_armed=False;self.last_ocr_at=0.0;self.wide_tracking=tk.BooleanVar(value=bool(config.get('wide_tracking',True)))
  self.first_run=not CFG.exists();self.scan_button=None;self.auto_toggle=None
  self.region_confirmed=bool(config.get('region_confirmed',not self.first_run))
  self.auto_tools=tk.BooleanVar(value=bool(config.get('auto_tool_discovery',True)))
  self.lite_use=tk.BooleanVar(value=bool(config.get('lite_use',False)));self.lite_scan_complete=False
  if self.lite_use.get():self.auto_tools.set(True);self.auto_enabled.set(True)
  self._tool_scan_latched=False;self._tool_timer_estimated=False
  self.windows_ocr=None;self.tool_reader=App.make_tool_reader(self);self.tool_report=None;self.tool_window=None;self.tool_tree=None;self._active_tool_key=None
  self.tool_debug=OCRReaderView(self,'Tool OCR reader',self.rescan_tools)
  self.tool_status=ToolStatus();self._tool_view_at=0.;self._tool_bridge_revision=-1
  self.tool_title=tk.StringVar(value='Ready to find tools');self.tool_preview=tk.StringVar(value='Visible counters will appear here')
  self.tool_metrics=tk.StringVar(value='No reading yet');self.tool_empty=None
  self.tool_health=tk.StringVar(value='Automatic tool finder · no area selection needed')
  self.region_target='craft'
  self.selecting_region=False
  self.auto_health=tk.StringVar(value='Auto OCR: waiting for setup')
  self.loot=LootTracker(self,DATA_ROOT,config)
  self.last_published=None;self.last_publish_mono=0;self.last_capture_mono=0;self.scan_stats={'ok':0,'failed':0,'last_duration':0};self.speed_estimator=SpeedEstimator()
  self.session_id=uuid.uuid4().hex;self.pending_signal=0;self.last_ack_seen=0;self.pending_since=0;self.ack_timed_out=False
  self.region=[tk.StringVar(value=str(v)) for v in config['region']]
  self.speed=tk.StringVar(value=str(config['seconds_per_craft']))
  self.warning=tk.StringVar(value=str(config['warning']))
  self.dur=tk.StringVar(value=str(config['durability']))
  self.maximum=tk.StringVar(value=str(config['maximum']))
  self.tess=tk.StringVar(value=config['tesseract'])
  self.status=tk.StringVar(value=('Show your cooking/alchemy labels in BDO. Tool discovery needs no selected area.' if self.auto_tools.get() else 'Ready to scan. Readings stay local until you click Send.'))
  self.count=tk.StringVar(value='--:--:--')
  self.alarm_in=tk.StringVar(value='--:--:--')
  self.ocr_text=tk.StringVar(value='Waiting for first OCR reading')
  self.source=tk.StringVar(value='NO READING YET')
  self.alarm_state=tk.StringVar(value='Alarm ready')
  self.connection=tk.StringVar(value='Starting planner connection…')
  self.scan_health=tk.StringVar(value='OCR ready  ·  not scanned yet')
  self.speed_health=tk.StringVar(value='Speed calibration  ·  collecting readings')
  self.durability_display=tk.StringVar(value=f'{int(self.value):,} / {int(self.maximum.get()):,}')
  self.timer_state=tk.StringVar(value='WAITING FOR OCR')
  self.preview=None
  self.colors={
   'bg':'#0b0a10','panel':'#15131e','panel2':'#211c30','line':'#393047',
   'muted':'#b1a8c2','secondary':'#d1c9df','text':'#faf7ff',
   'violet':'#7744d4','violet2':'#6636bb','bright':'#d5baff',
   'good':'#89e4bc','warning':'#ffc47b','teal':'#63d9cf','teal_panel':'#153036'
  }
  c=self.colors
  style=ttk.Style();style.theme_use('clam')
  style.configure('Vision.Horizontal.TProgressbar',troughcolor=c['panel2'],background=c['violet'],bordercolor=c['panel2'],lightcolor=c['violet'],darkcolor=c['violet'],thickness=8)
  style.configure('Vision.TCombobox',fieldbackground=c['panel2'],background=c['panel2'],foreground=c['text'],arrowcolor=c['bright'],bordercolor=c['line'],padding=3)
  style.map('Vision.TCombobox',fieldbackground=[('readonly',c['panel2'])],foreground=[('readonly',c['text'])],selectbackground=[('readonly',c['panel2'])],selectforeground=[('readonly',c['text'])])
  style.configure('Vision.TEntry',fieldbackground=c['panel2'],foreground=c['text'],insertcolor=c['text'],bordercolor=c['line'],padding=3)
  style.configure('Vision.TNotebook',background=c['bg'],borderwidth=0)
  style.configure('Vision.TNotebook.Tab',background=c['panel2'],foreground=c['text'],padding=(8,5),font=('Segoe UI',9))
  style.map('Vision.TNotebook.Tab',background=[('selected',c['violet'])])
  style.map('Vision.TEntry',fieldbackground=[('!disabled',c['panel2'])],foreground=[('!disabled',c['text'])])
  style.configure('Vision.TCheckbutton',background=c['bg'],foreground=c['secondary'],font=('Segoe UI',9))
  style.map('Vision.TCheckbutton',background=[('active',c['bg'])],foreground=[('active',c['text'])])
  root.option_add('*selectBackground',c['violet'])
  root.option_add('*selectForeground','#ffffff')

  from main_ui import build_main_ui
  build_main_ui(self)
  self.send_button.configure(state='disabled')
  self.tray_button.configure(state='disabled')
  self.root.after(200,self.refresh_action_states)

  self.bridge=None;self.bridge_server=None
  self.start_bridge()
  if self.bridge and self.bridge.server:
   self.connection.set('●  LOCAL SERVER READY  ·  PORT '+str(self.bridge.port))
  else:self.connection.set('●  LOCAL SERVER OFFLINE  ·  CHECK SETTINGS')
  self.root.after(400,self.tick)
  self.root.after(500,self.poll_auto_ocr)
  self.root.protocol('WM_DELETE_WINDOW',self.close)

 def refresh_action_states(self):
  available=self.has_reading and bool(self.bridge and self.bridge.server)
  for button in (self.send_button,self.tray_button):
   wanted='normal' if available else 'disabled'
   if str(button['state'])!=wanted:button.configure(state=wanted)
  self.root.after(400,self.refresh_action_states)

 def action(self,parent,text,command,primary=False,flat=False):
  c=self.colors
  bg=c['violet'] if primary else c['panel2'] if not flat else c['panel']
  btn=tk.Button(parent,text=text,command=command,bg=bg,fg=c['text'],activebackground=c['violet2'],activeforeground='#ffffff',font=('Segoe UI Semibold',9),pady=6 if not flat else 5,borderwidth=0,relief='flat',disabledforeground=c['muted'],highlightthickness=1,highlightbackground=c['line'],highlightcolor=c['bright'],takefocus=True,cursor='hand2')
  btn.bind('<Enter>',lambda e: btn.configure(bg=c['violet2']) if btn['state']=='normal' else None)
  btn.bind('<Leave>',lambda e: btn.configure(bg=bg) if btn['state']=='normal' else None)
  return btn

 def text_button(self,parent,text,command):
  c=self.colors
  return tk.Button(parent,text=text,command=command,bg=c['bg'],fg=c['bright'],activebackground=c['panel'],activeforeground='#ffffff',font=('Segoe UI Semibold',9),padx=3,pady=3,borderwidth=0,relief='flat',highlightthickness=1,highlightbackground=c['bg'],highlightcolor=c['bright'],takefocus=True,cursor='hand2')

 def open_gear_planner(self):
  if self.bridge and self.bridge.server:webbrowser.open(self.bridge.base_url+'/planner#gear')
  else:self.status.set('Local planner is unavailable. Check the connection in Settings.')

 def open_guild_quest(self):
  self.loot.open()
  self.loot.tabs.select(self.loot.guild.frame)

 def open_activity(self,section):
  self.loot.open()
  targets={'home':self.loot.home.frame,'craft':self.loot.craft_tab,'grind':self.loot.grind.frame,'reader':self.loot.preview.master,'sessions':self.loot.insights.sessions_frame,'quests':self.loot.guild.frame,'cp':self.loot.cp_info.frame,'imperial':self.loot.imperial.frame,'silver':self.loot.silver.frame}
  self.loot.tabs.select(targets[section])

 def open_fairy(self):
  if self.bridge and self.bridge.server:webbrowser.open_new_tab(self.bridge.base_url+'/fairy')
  else:self.status.set('Start the local connection to open Fairy Codex.')

 def tool_mode_changed(self):
  self.lite_scan_complete=False;self._tool_scan_latched=False
  self.tool_reader=App.make_tool_reader(self);self.last_scan_started=0
  self.set_tool_stage('idle' if self.auto_tools.get() else 'off','Show tool labels in BDO.' if self.auto_tools.get() else 'Manual capture area is selected in Settings.')
  self.save_quietly()

 def make_tool_reader(self):
  worker=getattr(self,'windows_ocr',None)
  if worker is None and config.get('structured_reader',True):
   helper=ROOT/'assets'/'vision-windows-ocr.exe'
   if not helper.is_file() and not getattr(sys,'frozen',False):helper=ROOT.parent/'build'/'native'/'vision-windows-ocr.exe'
   if helper.is_file():
    from windows_ocr import WindowsOCR
    worker=WindowsOCR(helper);self.windows_ocr=worker
  if worker is not None:
   from structured_reader import StructuredLocator
   return AutomaticToolReader(StructuredLocator(worker))
  return AutomaticToolReader()

 def open_tools(self):
  if self.tool_window and self.tool_window.winfo_exists():self.tool_window.deiconify();self.tool_window.lift();return
  c=self.colors;win=self.tool_window=tk.Toplevel(self.root)
  win.title('BDO Vision • Tool reader');win.geometry('760x400');win.minsize(680,340);win.configure(bg=c['bg'])
  header=tk.Frame(win,bg=c['bg']);header.pack(fill='x',padx=22,pady=(20,10))
  tk.Label(header,text='TOOL READER',bg=c['bg'],fg=c['text'],font=('Segoe UI Semibold',15)).pack(side='left')
  self.text_button(header,'EXPORT READER STATUS',self.save_tool_status).pack(side='right')
  self.text_button(header,'LIVE OCR READER',self.tool_debug.open).pack(side='right',padx=10)
  tk.Label(win,textvariable=self.tool_title,bg=c['bg'],fg=c['bright'],font=('Segoe UI Semibold',12)).pack(anchor='w',padx=22)
  tk.Label(win,textvariable=self.tool_health,bg=c['bg'],fg=c['secondary'],wraplength=700,justify='left').pack(anchor='w',padx=22,pady=(5,12))
  style=ttk.Style();style.configure('Tools.Treeview',background=c['panel'],fieldbackground=c['panel'],foreground=c['text'],rowheight=28)
  style.configure('Tools.Treeview.Heading',background=c['panel2'],foreground=c['secondary'],font=('Segoe UI Semibold',9))
  body=tk.Frame(win,bg=c['panel']);body.pack(fill='both',expand=True,padx=22)
  self.tool_tree=ttk.Treeview(body,columns=('name','durability','estimate','state','age'),show='headings',height=7,style='Tools.Treeview')
  for name,label,width in [('name','VISIBLE TOOL',200),('durability','VERIFIED DURABILITY',140),('estimate','ESTIMATED DURA',125),('state','STATUS',210),('age','LAST READ',80)]:
   self.tool_tree.heading(name,text=label);self.tool_tree.column(name,width=width,minwidth=55,stretch=name=='name')
  self.tool_tree.tag_configure('active',background=c['panel2'],foreground=c['good'])
  self.tool_tree.tag_configure('stale',foreground=c['muted'])
  scroll=ttk.Scrollbar(body,orient='vertical',command=self.tool_tree.yview)
  self.tool_tree.configure(yscrollcommand=scroll.set);scroll.pack(side='right',fill='y')
  self.tool_tree.pack(side='left',fill='both',expand=True)
  self.tool_empty=tk.Label(body,text='No verified readings yet.\nShow tool labels in BDO; the search continues automatically.',bg=c['panel'],fg=c['muted'],font=('Segoe UI',11),justify='center')
  tk.Label(win,text='Estimate assumes continued crafting: verified − whole uses since last read.',bg=c['bg'],fg=c['muted'],font=('Segoe UI',9),wraplength=700,justify='left').pack(anchor='w',padx=22,pady=(8,0))
  footer=tk.Frame(win,bg=c['bg']);footer.pack(fill='x',padx=22,pady=14)
  tk.Label(footer,textvariable=self.tool_metrics,bg=c['bg'],fg=c['muted'],font=('Segoe UI',9)).pack(side='left')
  self.action(footer,'FIND AGAIN',self.rescan_tools,flat=True).pack(side='right')
  self._tool_table_values={}
  self.refresh_tools()

 def rescan_tools(self):
  if self.busy:self.status.set('The reader is already working. Results will appear automatically.');return
  self.tool_reader.last_discovery=-1e9;self.tool_reader.next_due=0
  self.read_ocr()

 def save_tool_status(self):
  path=filedialog.asksaveasfilename(parent=self.tool_window,defaultextension='.json',initialfile='vision-tool-status.json',filetypes=[('Reader status','*.json')])
  if path:
   try:Path(path).write_text(json.dumps({'version':APP_VERSION,**self.tool_status.snapshot()},indent=2),encoding='utf-8')
   except OSError as exc:messagebox.showerror('Save status',str(exc),parent=self.tool_window)

 def set_tool_stage(self,stage,detail):
  if not hasattr(self,'tool_status'):return
  if self.tool_status.set_stage(stage,detail):self.refresh_tool_view()
  if stage in ('off','paused','waiting','error'):self.tool_debug.paused(detail)
  if stage in ('off','paused','waiting','error'):self.mark_tool_estimate()

 def mark_tool_estimate(self):
  if self.running and self._active_tool_key is not None:
   self._tool_timer_estimated=True
   self.source.set('ESTIMATE · last verified tool · assumes crafting continues')

 def refresh_tool_view(self):
  if not hasattr(self,'tool_status'):return
  view=self.tool_status.snapshot();self._tool_view_at=time.monotonic()
  def set_changed(variable,value):
   if variable.get()!=value:variable.set(value)
  set_changed(self.tool_title,view['title']);set_changed(self.tool_health,view['detail'])
  age=max(0,int(time.time()-view['last_read_at'])) if view['last_read_at'] else None
  preview=' · '.join(f"{r['current']:,}/{r['maximum']:,}" for r in view['tools'][:3])
  fresh=age is not None and age<=15 and view['stage'] not in ('paused','error','off','searching','unreadable','absent','timer')
  set_changed(self.tool_preview,(('Readings: ' if fresh else 'Last verified: ')+preview) if preview else view['detail'])
  set_changed(self.tool_metrics,f"Last scan {view['last_seconds']:.2f}s · read {age}s ago" if age is not None else 'No reading yet · show labels in BDO')
  bridge=getattr(self,'bridge',None)
  if bridge and self._tool_bridge_revision!=view['revision']:
   bridge.update_tool_status(view);self._tool_bridge_revision=view['revision']
  self.refresh_tools(view)

 def refresh_tools(self,view=None):
  if not self.tool_tree or not self.tool_tree.winfo_exists():return
  if not self.tool_tree.winfo_ismapped():return
  view=view or self.tool_status.snapshot();wanted={r['id'] for r in view['tools']};cache=getattr(self,'_tool_table_values',{})
  for ident in self.tool_tree.get_children():
   if ident not in wanted:self.tool_tree.delete(ident);cache.pop(ident,None)
  age=max(0,int(time.time()-view['last_read_at'])) if view['last_read_at'] else 0
  current=view['stage'] not in ('paused','error','off','searching','unreadable','absent','timer') and age<=15
  try:pace=float(self.speed.get())
  except (ValueError,TypeError):pace=1.
  for index,row in enumerate(view['tools']):
   state=('Last verified · capture paused' if view['stage'] in ('paused','error','off') else 'Last verified · awaiting refresh') if not current else row['state']
   estimate=estimate_durability(row,age,view['active_id'],pace)
   estimated=f'≈ {estimate:,}' if estimate is not None else '—'
   values=(row['name'],f"{row['current']:,} / {row['maximum']:,}",estimated,state,f'{age}s ago')
   tag='active' if current and row['id']==view['active_id'] else 'stale' if not current else ''
   key=(values,tag)
   if not self.tool_tree.exists(row['id']):self.tool_tree.insert('',index,iid=row['id'],values=values,tags=(tag,))
   elif cache.get(row['id'])!=key:self.tool_tree.item(row['id'],values=values,tags=(tag,))
   cache[row['id']]=key
  self._tool_table_values=cache
  if self.tool_empty:
   if wanted:self.tool_empty.place_forget()
   else:
    self.tool_empty.configure(text=view['title']+'\n'+view['detail'],wraplength=600)
    self.tool_empty.place(relx=.5,rely=.55,anchor='center')

 def wait_for_tool_capture(self,tess,deadline):
  if self.bdo_foreground():self.capture_tools(tess,False);return
  if time.monotonic()>=deadline:
   self.busy=False
   if self.scan_button:self.scan_button.configure(state='normal',text='◎  SCAN & TRACK')
   self.set_tool_stage('paused','No game capture taken: BDO did not come to the front. Press READ NOW and switch to BDO.');return
  self.set_tool_stage('waiting','Waiting for BDO in front; no OCR runs until the game is visible.')
  self.root.after(250,lambda:self.wait_for_tool_capture(tess,deadline))

 def capture_tools(self,tess,automatic=False):
  self.set_tool_stage('reading','Checking visible tool labels and durability. Loot recording remains independent.')
  reader=self.tool_reader;interval=self.safe_scan_interval()
  guild=self.loot.guild;guild_generation=guild.generation if guild.enabled.get() else None
  debug_token=self.tool_debug.token();debug_frames=[]
  def diagnostic(crops,observations,scene):
   if self.tool_debug.token()==debug_token and debug_token is not None:
    debug_frames[:]=[source_image(scene) if scene is not None else label_montage(crops)]
  reader.diagnostic=diagnostic if debug_token is not None else None
  def work():
   quest_sample=None;quest_box=None
   try:
    bounds=foreground_bdo_capture_bounds()
    if bounds is None:raise RuntimeError('Bring BDO to the front with cooking/alchemy tool labels visible')
    if guild_generation is not None:
     try:quest_box=guild.capture_region()
     except RuntimeError:pass
    def grab(box):
     nonlocal quest_sample
     if foreground_bdo_capture_bounds()!=bounds:raise RuntimeError('BDO moved or lost focus; waiting to reacquire tool labels')
     image=ImageGrab.grab(bbox=box,all_screens=True)
     if quest_box and quest_sample is None and box[0]<=quest_box[0]<quest_box[2]<=box[2] and box[1]<=quest_box[1]<quest_box[3]<=box[3]:
      quest_sample=(image.crop((quest_box[0]-box[0],quest_box[1]-box[1],quest_box[2]-box[0],quest_box[3]-box[1])),quest_box,time.time())
     if debug_token is not None and self.tool_debug.token()==debug_token:
      preview=source_image(image);observed=time.time()
      self.root.after(0,lambda:self.tool_debug.show(debug_token,preview,'Capture received. Recognition in progress; this image remains available if OCR times out.',observed))
     return image
    captured_at=time.time();captured_mono=time.monotonic()
    report=reader.read(tess,bounds,grab,interval=interval,confirm_pair=not self.lite_use.get())
    if debug_frames:
     detail=json.dumps({k:report.get(k) for k in ('reason','confirmation','pair_result','anchor','tools','unreadable','duration','ocr_calls','cache_hits','camera_reacquired','engine','locator_error')},indent=2)+'\n\nOCR PASSES\n'+report.pop('_debug_raw','Unchanged verified crops reused; no new OCR text.')
     image=debug_frames[0]
     self.root.after(0,lambda:self.tool_debug.show(debug_token,image,detail,report.get('captured_at')))
    self.root.after(0,lambda:self.finish_tool_attempt(report,reader,automatic,captured_at,captured_mono,quest_sample,guild_generation))
   except Exception as exc:
    message=str(exc);reader.next_due=time.monotonic()+10
    self.root.after(0,lambda:self.finish_tool_attempt(None,reader,automatic,None,None,quest_sample,guild_generation,message))
   finally:reader.diagnostic=None
  threading.Thread(target=work,name='vision-tool-finder',daemon=True).start()

 def finish_tool_attempt(self,report,reader,automatic,captured_at,captured_mono,quest_sample=None,guild_generation=None,error=None):
  if error is not None:self.tool_failed(error,reader)
  else:self.finish_tools(report,reader,automatic,captured_at,captured_mono)
  guild=self.loot.guild
  if reader is self.tool_reader and guild_generation is not None and guild_generation==guild.generation and guild.enabled.get():
   guild.scan(paired=True,sample=quest_sample)
  elif reader is self.tool_reader and hasattr(guild,'check_crafting_quest'):guild.check_crafting_quest()

 def tool_failed(self,message,reader):
  self.busy=False
  if self.scan_button:self.scan_button.configure(state='normal',text='◎  SCAN & TRACK')
  if reader is self.tool_reader:self.set_tool_stage('error',message)
  self.tool_debug.paused(message)
  if getattr(reader,'last_failure_trace',''):self.tool_debug.paused(message+'\nPARTIAL OCR OUTPUT:\n'+reader.last_failure_trace)

 def finish_tools(self,report,reader,automatic,captured_at,captured_mono):
  self.busy=False
  if self.scan_button:self.scan_button.configure(state='normal',text='◎  SCAN & TRACK')
  if reader is not self.tool_reader or not self.auto_tools.get():return
  captured_at=report.get('captured_at',captured_at);captured_mono=report.get('captured_mono',captured_mono)
  self.tool_report=report;rows=report['tools'];self.tool_status.accept(report);self.refresh_tool_view()
  active=next((r for r in rows if r['id']==report['active_id']),None)
  if not active:
   if self._active_tool_key is not None:
    self.update_value();self.mark_tool_estimate()
   self.scan_health.set(f"Tool finder · {report['duration']:.1f}s · {report['ocr_calls']} OCR passes")
   self.status.set(self.tool_status.detail+(' Countdown continues from the last verified value; assumes crafting continues.' if self.running and self._active_tool_key is not None else ''))
   return
  if report['active_key']!=self._active_tool_key:
   from tracking_core import replacement_needs_use
   self.update_value()
   if replacement_needs_use(self._active_tool_key,report['active_key'],self.value,active['current'],active['maximum'],active.get('wear_streak',0),getattr(self,'_allow_tool_change',False)):
    reader.next_due=min(reader.next_due,time.monotonic()+3)
    self.set_tool_stage('confirming','Current tool is nearly empty. A different high-durability tool must show repeated use before replacing this timer.')
    self.status.set('Keeping the current countdown. Checking whether the replacement tool is actually being used.');return
   self._active_tool_key=report['active_key'];self.has_reading=False;self.reading_gate=ReadingGate()
   self.session_id=uuid.uuid4().hex;self.speed_estimator.reset();self.last_good_ocr=None
  a,b=active['current'],active['maximum']
  self._allow_tool_change=False
  self.finish_ocr([(a,b),(a,b)],[],[],automatic,captured_at,captured_mono,report['duration'])
  if self.reading_gate.pending is not None:
   reader.next_due=min(reader.next_due,time.monotonic()+3)
   self.status.set('Confirming the first reading · '+active['name'])
  elif self.lite_use.get() and self.lite_scan_complete:
   self.set_tool_stage('timer','Lite Use · no more tool scans. Optional paired guild snapshot finishes once; SCAN & TRACK reads the next tool.')
   self.source.set('LITE USE · countdown estimate · tool OCR stopped')
   self.status.set('Tool read. Timer running; no further automatic OCR after the optional paired guild read. Assumes crafting continues.')
  elif self.running and (active.get('wear_streak',0)>=2 or report.get('confirmation')=='two-frame comparison'):
   self._tool_scan_latched=True
   self.set_tool_stage('timer','Crafting use confirmed · tool OCR stopped until this countdown finishes. Guild quests stay last seen; loot follows its own setting.')
   self.source.set('CRAFT TIMER · confirmed start · estimate')
   self.status.set('Active crafting confirmed. No more tool scans until the countdown finishes; SCAN & TRACK overrides this.')
  elif report.get('confirmation')=='Place Mode position':
   self.source.set('PLACE MODE SELECTED · verified durability');self.status.set('Countdown started for '+active['name']+'. Checking durability use next.')
  else:self.status.set('Tracking '+active['name']+'. All readings are in VIEW TOOLS.')

 def open_planner(self):
  """Serve the paired planner from our own bridge; no cross-origin file permissions."""
  if not self.bridge or not self.bridge.planner_url:
   messagebox.showerror('Planner offline','The local bridge did not start. Use TEST LINK for details.')
   return
  if not self.bridge.html_path.is_file():
   messagebox.showerror('Planner not found','Keep bdo-market-intelligence.html beside the desktop folder.')
   return
  try:
   webbrowser.open_new_tab(self.bridge.planner_url)
   self.status.set(f'Opened paired planner at {self.bridge.planner_url}. Waiting for the website to connect…')
  except Exception as exc:messagebox.showerror('Open planner',str(exc))

 def test_connection(self):
  """Measure the actual listener response and report browser acknowledgments."""
  def check():
   try:
    if not self.bridge or not self.bridge.base_url:
     raise RuntimeError('No free port from 7283–7292. Close extra BDO Vision programs.')
    url=self.bridge.base_url+'/health'
    with urllib.request.urlopen(url,timeout=2) as response:
     health=json.load(response)
    if not health.get('ok') or health.get('instance_id')!=self.bridge.instance_id:
     raise RuntimeError('Another app responded instead of this BDO Vision instance.')
    seen=health['last_ack_signal'];sent=health['signal']
    if sent==0:
     msg=f'Bridge OK at {url}. No reading sent yet. Open Planner, then click SEND NOW.'
    elif seen>=sent:
     msg=f'Bridge OK on port {self.bridge.port}. Website confirmed reading #{seen}.'
    else:
     msg=(f'Bridge OK on port {self.bridge.port}, but website has not acknowledged reading #{sent}. '
          'Click OPEN PLANNER and check that the correct tab says App connected.')
   except Exception as exc:
    msg='Bridge connection failed: '+str(exc)
   self.root.after(0,lambda: self.status.set(msg))
  threading.Thread(target=check,daemon=True).start()

 def send_and_tray(self):
  # Use the active bridge object, not a stale fixed-port server reference.
  if not self.bridge or not self.bridge.server:
   self.status.set('Cannot send: local planner bridge is offline. Click TEST LINK.');return
  if not self.send_to_planner():return
  self.status.set('Reading sent. Switch to BDO now — Ctrl+V in 2 seconds…')
  self.root.after(2000,self._finish_tray)

 def _finish_tray(self):
  ok,msg=send_ctrl_v_if_bdo_foreground()
  self.status.set(msg)
  if ok:
   # A delivered shortcut is not proof that the game entered native tray mode.
   self.root.after(1400,self._verify_tray)

 def _verify_tray(self):
  try:
   state=inspect_bdo_visibility()
   if state=='hidden':
    self.status.set('Ctrl+V delivered; BDO window is hidden/minimized (tray mode likely).')
   elif state=='visible':
    self.status.set('Ctrl+V delivered, but BDO window remains visible. Check the tray keybind.')
   else:
    self.status.set('Ctrl+V delivered. Could not verify BDO tray state; check its tray icon.')
  except Exception as exc:
   self.status.set('Ctrl+V sent; tray verification unavailable: '+str(exc))

 def restore_game(self):
  ok,msg=restore_bdo()
  self.status.set(msg)

 def super_restore_game(self):
  if self.super_restoring:
   self.status.set('Super Restore is already checking the BDO tray icon.')
   return
  self.super_restoring=True
  self.status.set('Looking for BDO tray icon… Windows may take a few seconds to restore the game.')
  def worker():
   try:
    ok,msg=super_restore_bdo()
   except Exception as exc:
    ok,msg=False,'Super Restore error: '+str(exc)
   def done():
    self.super_restoring=False
    self.status.set(msg)
   self.root.after(0,done)
  threading.Thread(target=worker,daemon=True).start()

 def open_settings(self):
  if self.settings_window and self.settings_window.winfo_exists():
   self.settings_window.lift();return
  c=self.colors
  win=tk.Toplevel(self.root);self.settings_window=win
  win.title('BDO Vision Lite  •  Settings');win.geometry('560x600');win.minsize(500,460)
  win.configure(bg=c['bg'])
  container=tk.Frame(win,bg=c['bg']);container.pack(fill='both',expand=True)
  scroller=tk.Canvas(container,bg=c['bg'],highlightthickness=0,borderwidth=0)
  scrollbar=tk.Scrollbar(container,orient='vertical',command=scroller.yview)
  scroller.configure(yscrollcommand=scrollbar.set)
  scrollbar.pack(side='right',fill='y')
  scroller.pack(side='left',fill='both',expand=True)
  main=tk.Frame(scroller,bg=c['bg'],padx=21,pady=17)
  inner_id=scroller.create_window((0,0),window=main,anchor='nw')
  main.bind('<Configure>',lambda e:scroller.configure(scrollregion=scroller.bbox('all')))
  scroller.bind('<Configure>',lambda e:scroller.itemconfigure(inner_id,width=e.width))
  def wheel(event):
   if event.delta:scroller.yview_scroll(-int(event.delta/120),'units')
  win.bind('<MouseWheel>',wheel)
  footer=tk.Frame(win,bg=c['bg'],padx=21,pady=10)
  footer.pack(side='bottom',fill='x')
  tk.Label(main,text='OCR & TIMER SETTINGS',bg=c['bg'],fg=c['bright'],font=('Segoe UI Semibold',16)).pack(anchor='w')
  tk.Label(main,text='Advanced options stay here. The main window remains simple.',bg=c['bg'],fg=c['muted']).pack(anchor='w',pady=(3,15))
  def heading(text):
   tk.Label(main,text=text,bg=c['bg'],fg=c['secondary'],font=('Segoe UI Semibold',10)).pack(anchor='w',pady=(13,5))
  def fields(items):
   row=tk.Frame(main,bg=c['bg']);row.pack(fill='x',pady=3)
   for name,var,width in items:
    tk.Label(row,text=name,bg=c['bg'],fg=c['secondary'],font=('Segoe UI',9)).pack(side='left')
    ttk.Entry(row,textvariable=var,width=width,style='Vision.TEntry').pack(side='left',padx=(5,13))
  heading('CRAFT TIMER')
  fields([('Durability',self.dur,9),('Maximum',self.maximum,9)])
  fields([('Seconds / craft',self.speed,7),('Warn early (s)',self.warning,7)])
  row=tk.Frame(main,bg=c['bg']);row.pack(fill='x',pady=(6,0))
  self.action(row,'APPLY MANUAL READING',self.start,primary=True).pack(side='left',fill='x',expand=True,padx=(0,5))
  self.action(row,'PAUSE',self.pause).pack(side='left',fill='x',expand=True,padx=(5,0))
  heading('OCR HEALTH')
  tk.Label(main,textvariable=self.scan_health,bg=c['bg'],fg=c['muted']).pack(anchor='w')
  tk.Label(main,textvariable=self.speed_health,bg=c['bg'],fg=c['muted']).pack(anchor='w')
  ttk.Checkbutton(main,text='Automatically find tools · no area selection',variable=self.auto_tools,command=self.tool_mode_changed,style='Vision.TCheckbutton').pack(anchor='w',pady=(8,0))
  self.text_button(main,'SHOW NEARBY TOOLS',self.open_tools).pack(anchor='w')
  heading('OPTIONAL MANUAL AREA  •  X / Y / WIDTH / HEIGHT')
  fields([(name,var,6) for name,var in zip(('X','Y','W','H'),self.region)])
  row=tk.Frame(main,bg=c['bg']);row.pack(fill='x',pady=(7,0))
  self.action(row,'SELECT REGION',self.select_region).pack(side='left',fill='x',expand=True,padx=(0,5))
  self.action(row,'READ OCR NOW',self.read_ocr).pack(side='left',fill='x',expand=True,padx=(5,0))
  ttk.Checkbutton(main,text='Wide fallback when labels move (recommended)',variable=self.wide_tracking,command=self.save,style='Vision.TCheckbutton').pack(anchor='w',pady=(7,0))
  fields([('Scan every (s)',self.scan_interval,7),('Beep count',self.alarm_repeats,7)])
  presets=tk.Frame(main,bg=c['bg']);presets.pack(fill='x',pady=6)
  self.text_button(presets,'TESTING · 10 SEC',lambda:self.set_scan_preset(10)).pack(side='left')
  self.text_button(presets,'NORMAL · 2 MIN',lambda:self.set_scan_preset(120)).pack(side='left',padx=15)
  heading('TESSERACT OCR')
  ttk.Entry(main,textvariable=self.tess,style='Vision.TEntry').pack(fill='x')
  heading('OCR PREVIEW')
  self.preview=tk.Label(main,text='Automatic readings appear in VIEW TOOLS.\nManual area preview is optional.',bg=c['panel'],fg=c['muted'],height=3,font=('Segoe UI',9))
  self.preview.pack(fill='x',pady=(0,4))
  if self.last_image:self.show_preview(self.last_image)
  row=tk.Frame(footer,bg=c['bg']);row.pack(fill='x',pady=(0,6))
  self.text_button(row,'VIEW DIAGNOSTICS',self.open_diagnostics).pack(side='left')
  self.text_button(row,'TEST ALARM',self.alarm).pack(side='left',padx=15)
  self.text_button(row,'BACK UP HISTORY',self.backup_history).pack(side='left',padx=10)
  ttk.Checkbutton(main,text='Share recorded loot with planner (optional)',variable=self.loot.share_loot,command=self.loot.share_changed,style='Vision.TCheckbutton').pack(anchor='w',pady=8)
  self.action(footer,'SAVE SETTINGS',self.save,primary=True).pack(fill='x')
  def close_settings():
   self.preview=None;self.settings_window=None;win.destroy()
  win.protocol('WM_DELETE_WINDOW',close_settings)

 def start_bridge(self):
  try:
   self.bridge=PlannerBridge(ROOT.parent/'bdo-market-intelligence.html',
                            current=int(self.value),maximum=int(self.maximum.get()),
                            seconds_per_craft=float(self.speed.get()),price_book=self.loot.insights.prices,
                             ports=tuple(dict.fromkeys((int(config.get('bridge_port',7288)),*PORTS))))
   self.bridge_server=self.bridge.server
   self.bridge.ocr_paused=self.lite_use.get()
   if self.lite_use.get():self.bridge.gear_stop.set()
   if self.bridge_server:
    runtime=json.dumps({'planner_url':self.bridge.planner_url,'base_url':self.bridge.base_url,'pid':os.getpid(),'data_path':str(DATA_ROOT)})
    (DATA_ROOT/'runtime-status.json').write_text(runtime)
    (ROOT/'runtime-status.json').write_text(runtime)
   if not self.bridge_server:self.status.set(self.bridge.last_error)
  except Exception as exc:
   self.bridge=None;self.bridge_server=None;self.status.set('Bridge startup failed: '+str(exc))

 def send_to_planner(self, measurement=None, observed_at=None, source='manual'):
  try:
   if not self.has_reading and measurement is None:
    self.status.set('No durability yet. Use SCAN & TRACK, or enter a value in Settings.')
    return False
   d,m,s,_=self.parse_inputs()
   self.update_value()
   if measurement is not None:
    d,m=measurement
   elif self.running:
    d=estimate_send(self.value,self.anchor,time.monotonic(),s,True)
   if not self.bridge or not self.bridge.server:
    self.status.set('Cannot send: local bridge is offline. Use TEST LINK.')
    return False
   extra={}
   loot=getattr(self,'loot',None)
   if loot is not None and loot.share_loot.get():extra['crafting_loot']=loot.planner_loot_snapshot()
   if loot is not None:
    guild=loot.guild.model.snapshot()
    if guild['current'] is not None or guild['complete']:extra['guild_quest']={k:guild[k] for k in ('current','target','label','objective','last_at','complete','completion_at','completion_basis')}
   event=self.bridge.send(d,m,s,observed_at=observed_at,
                          session_id=self.session_id,source=('estimate' if self.running and measurement is None else source),**extra)
   self.sync_armed=True
   self.pending_signal=event['signal'];self.pending_since=time.monotonic();self.ack_timed_out=False
   self.status.set(f'Sent {d:,}/{m:,} to planner. Waiting for confirmation…')
   return True
  except Exception as exc:
   self.status.set('Send failed: '+str(exc))
   return False

 def track_ack(self):
  if not self.bridge or not self.pending_signal:return
  acknowledged,_=self.bridge.acknowledgment()
  if acknowledged>=self.pending_signal and acknowledged!=self.last_ack_seen:
   self.last_ack_seen=acknowledged;self.pending_signal=0;self.ack_timed_out=False
   self.connection.set('●  PLANNER SYNC CONFIRMED   ·   port '+str(self.bridge.port))
   self.status.set('Planner confirmed · your live session is linked and will update with OCR.')
  elif time.monotonic()-self.pending_since>=8 and not self.ack_timed_out:
   self.ack_timed_out=True
   self.connection.set('●  BRIDGE ONLINE  ·  PLANNER NOT CONFIRMED')
   self.status.set('Bridge is online, but the website has not acknowledged. Click OPEN PLANNER and TEST LINK.')

 def parse_inputs(self):
  d=int(self.dur.get().replace(',',''));m=int(self.maximum.get().replace(',',''));s=float(self.speed.get());w=float(self.warning.get())
  if not (0<=d<=m and m>0 and .05<=s<=3600 and w>=0):raise ValueError('Check durability, maximum, seconds per craft, and warning threshold.')
  return d,m,s,w
 def save(self):
  try:
   d,m,s,w=self.parse_inputs();r=[int(v.get()) for v in self.region]
   if r[2]<=0 or r[3]<=0:raise ValueError('Region width and height must be positive.')
   if not (2<=float(self.scan_interval.get())<=600 and 1<=int(self.alarm_repeats.get())<=20):raise ValueError('Auto scan interval must be 2–600 seconds and alarm beeps 1–20.')
   CFG.write_text(json.dumps({**self.loot.settings(),'lite_use':self.lite_use.get(),'auto_tool_discovery':self.auto_tools.get(),'region_confirmed':self.region_confirmed,'region':r,'seconds_per_craft':s,'warning':w,'durability':d,'maximum':m,'tesseract':self.tess.get(),'auto_scan':self.auto_enabled.get(),'scan_interval':float(self.scan_interval.get()),'alarm_repeats':int(self.alarm_repeats.get()),'wide_tracking':self.wide_tracking.get()},indent=2));self.status.set('Settings saved')
  except Exception as e:messagebox.showerror('Settings',str(e))
 def refresh_auto_scan_label(self):
  if self.auto_toggle:
   enabled=self.auto_enabled.get()
   self.auto_toggle.configure(text=(('●  AUTO OCR ON · %ds'%self.safe_scan_interval()) if enabled else '○  AUTO OCR OFF'),
                              fg=(self.colors['good'] if enabled else self.colors['muted']))

 def toggle_auto_scan(self):
  self.auto_enabled.set(not self.auto_enabled.get())
  self.refresh_auto_scan_label()
  self.last_scan_started=0
  self.save_quietly()

 def save_quietly(self):
  """Persist a toggle without replacing useful sync or OCR status messages."""
  old=self.status.get()
  self.save()
  if self.status.get()=='Settings saved':self.status.set(old)

 def start(self):
  try:
   d,m,s,w=self.parse_inputs();self.value=float(d);self.anchor=time.monotonic();self.running=True;self.alarmed=False;self.session_id=uuid.uuid4().hex;self.speed_estimator.reset();self.has_reading=True;self.reading_gate=ReadingGate();self.sync_armed=False;self.status.set('Manual estimate running. Click SEND NOW to link this session.');self.alarm_state.set('Alarm armed');self.source.set('ESTIMATED • timer running')
  except Exception as e:messagebox.showerror('Timer',str(e))
 def pause(self):
  self.update_value();self.running=False;self.dur.set(str(max(0,int(self.value))));self.status.set('Timer paused');self.source.set('PAUSED • last estimate')
 def update_value(self):
  if self.running and self.anchor is not None:
   now=time.monotonic()
   try:s=max(.05,float(self.speed.get()))
   except:s=1.0
   self.value=max(0,self.value-(now-self.anchor)/s);self.anchor=now
 def backup_history(self):
  folder=backup_profile(DATA_ROOT,'manual');self.status.set('History backup saved and verified.');os.startfile(str(folder))

 def show_saved_history(self):
  self.root.deiconify();self.root.lift();self.loot.open()

 def tick(self):
  if time.monotonic()-getattr(self,'_tool_view_at',0)>=1:self.refresh_tool_view()
  if self.bridge and self.bridge.consume_show_request():self.show_saved_history()
  if self.bridge:
   for command in self.bridge.consume_commands():
    try:
     if command.get('action')=='cp-read':self.loot.cp_info.read_once(command['id'])
     else:self.loot.grind.dispatch(command)
    except Exception as exc:self.status.set('Session command could not be applied: '+str(exc))
  self.update_value()
  if getattr(self,'_tool_scan_latched',False) and self.value<=0:
   self._tool_scan_latched=False;self.tool_reader.next_due=0;self.tool_reader.last_discovery=-1e9
   if self.lite_use.get():self.set_tool_stage('timer','Lite Use · countdown finished; OCR remains stopped. SCAN & TRACK reads the next tool.')
   else:self.set_tool_stage('idle','Countdown finished. Ready to find the next active tool.')
  try:
   _,m,s,w=self.parse_inputs() if not self.running else (0,max(1,int(self.maximum.get())),max(.05,float(self.speed.get())),max(0,float(self.warning.get())))
   self.bar['value']=100*min(1.,max(0.,self.value/m)) if self.has_reading else 0
   self.durability_display.set(f'{max(0,int(self.value + .999)):,} / {m:,}' if self.has_reading else '— / —')
   if self.running and self.lite_use.get() and self.lite_scan_complete:self.timer_state.set('LITE USE · TIMER ONLY')
   elif self.running and getattr(self,'_tool_scan_latched',False):self.timer_state.set('CRAFT TIMER · TOOL OCR OFF')
   elif self.running and getattr(self,'_tool_timer_estimated',False):self.timer_state.set('ESTIMATE · TOOL UNCONFIRMED')
   elif self.running and self.last_ocr_at:
    age=max(0,int(time.monotonic()-self.last_ocr_at))
    self.timer_state.set('OCR · %ds AGO'%age if age<10 else 'ESTIMATE · %ds'%age)
   elif self.running:self.timer_state.set('MANUAL ESTIMATE')
   elif self.has_reading:self.timer_state.set('PAUSED / FINISHED')
   else:self.timer_state.set('WAITING FOR OCR')
   if self.running and not getattr(self,'_tool_timer_estimated',False) and not self.lite_scan_complete and not getattr(self,'_tool_scan_latched',False) and self.last_ocr_at and time.monotonic()-self.last_ocr_at < 15:
    self.state_label.configure(fg=self.colors['good'])
   elif self.running:
    self.state_label.configure(fg=self.colors['warning'])
   else:
    self.state_label.configure(fg=self.colors['muted'])
   left=self.value*s;self.count.set(self.fmt(left) if self.running else '--:--');self.alarm_in.set(self.fmt(max(0,left-w)) if self.running else '--:--')
   if self.running and not self.alarmed and left<=w:self.alarmed=True;self.alarm();self.alarm_state.set('ALARM TRIGGERED • Change tool soon!');self.status.set('ALARM • Change your tool! (estimated)')
  except Exception:pass
  try:self.track_ack()
  except Exception as exc:self.connection.set('Planner check retry pending: '+str(exc))
  self.root.after(400,self.tick)
 def change_lite_use(self):
  self.lite_scan_complete=bool(self.lite_use.get() and self.running and self.has_reading and self.last_good_ocr is not None)
  self.tool_reader=App.make_tool_reader(self)
  self.loot.generation+=1;self.loot.guild.generation+=1;self.loot.guild.waiting=False
  if self.loot.guild.pending is not None:self.root.after_cancel(self.loot.guild.pending);self.loot.guild.pending=None
  self.loot.guild.schedule()
  if self.bridge:
   self.bridge.ocr_paused=self.lite_use.get()
   if self.lite_use.get():self.bridge.gear_stop.set()
   else:self.bridge.gear_stop.clear()
  if self.lite_use.get():self.auto_tools.set(True);self.auto_enabled.set(True)
  self.tool_reader.next_due=0
  if self.lite_scan_complete:
   self.set_tool_stage('timer','Lite Use · existing verified countdown retained; all OCR stopped.')
   self.source.set('LITE USE · countdown estimate · all OCR stopped')
  self.save_quietly()
  self.status.set('Lite Use: initial tool durability only. Loot, quest and gear OCR are paused; after acceptance only the timer runs.' if self.lite_use.get() else 'Normal tracking restored with your existing options.')

 def poll_auto_ocr(self):
  # Keep scanning alive independently of timer / planner update failures.
  finder=bool(getattr(self,'auto_tools',None) and self.auto_tools.get())
  delay=500
  try:
   if self.lite_use.get() and self.lite_scan_complete:
    message=('LITE USE · paired guild snapshot finishing · tool OCR stopped' if getattr(getattr(self.loot,'guild',None),'busy',False) else 'LITE USE · timer estimate only · scan manually for a new tool')
    if self.auto_health.get()!=message:self.auto_health.set(message)
    delay=2000
   elif getattr(self,'_tool_scan_latched',False):
    message='Tool OCR stopped · countdown finishes before the next automatic tool scan'
    if self.auto_health.get()!=message:self.auto_health.set(message)
    delay=1000
   elif not self.auto_enabled.get():
    self.auto_health.set('Auto OCR: OFF')
    if finder:self.set_tool_stage('off','Automatic scanning is off. SCAN & TRACK still reads on demand.')
   elif self.selecting_region:self.auto_health.set('Auto OCR: selecting capture area')
   elif not finder and not self.region_confirmed:self.auto_health.set('Auto OCR: select your craft area in Settings')
   elif not finder and getattr(self.loot,'enabled',None) is not None and self.loot.enabled.get() and not self.loot.crafting.get() and not self.running:
    self.auto_health.set('Tool OCR idle during grinding · enable Crafting mode when needed')
   elif not self.bdo_foreground():
    self.auto_health.set('Auto OCR: waiting for BDO in front')
    if finder and not self.busy:self.set_tool_stage('paused','Bring BDO to the front. Last verified counters are preserved; no hidden tool is read.')
   elif self.busy or self.loot.busy or getattr(getattr(self.loot,'guild',None),'waiting',False):self.auto_health.set('Auto OCR: scan in progress')
   else:
    if finder and getattr(getattr(self,'tool_status',None),'stage',None)=='paused':
     self.tool_reader.next_due=0
     self.set_tool_stage('idle','BDO is visible again. Rechecking tool counters.')
    remaining=max(0,self.tool_reader.next_due-time.monotonic()) if finder else max(0,self.safe_scan_interval()-(time.monotonic()-self.last_scan_started))
    self.auto_health.set('Auto OCR: next scan in %ds'%int(remaining+.999))
    if remaining<=0:
     self.last_scan_started=time.monotonic()
     self.read_ocr(delayed=False,automatic=True)
  except Exception as exc:self.auto_health.set('Auto OCR: retry pending · '+str(exc))
  finally:self.root.after(delay,self.poll_auto_ocr)

 def set_scan_preset(self,seconds):
  self.scan_interval.set(str(seconds));self.last_scan_started=0
  self.save_quietly();self.refresh_auto_scan_label()
  self.status.set('OCR interval: %s seconds (%s).'%(seconds,'testing' if seconds==10 else 'normal use'))

 def bdo_foreground(self):
  try:
   return is_bdo_foreground()
  except Exception:return False
 def safe_scan_interval(self):
  try:return max(2,float(self.scan_interval.get()))
  except:return 10
 @staticmethod
 def fmt(t):
  t=max(0,int(t+0.999));return f'{t//3600:02}:{(t//60)%60:02}:{t%60:02}'
 def alarm(self):
  def play():
   for _ in range(max(1,min(20,int(self.alarm_repeats.get())))):
    try:winsound.Beep(950,260)
    except Exception:winsound.MessageBeep()
    time.sleep(.18)
  threading.Thread(target=play,daemon=True).start()
 def select_region(self,target='craft'):
  self.region_target=target
  self.selecting_region=True
  # Hide BOTH windows; otherwise Settings remains over the game and the user
  # accidentally selects part of our own UI as the OCR region.
  self.root.withdraw()
  if self.loot.window and self.loot.window.winfo_exists():self.loot.window.withdraw()
  if self.settings_window and self.settings_window.winfo_exists():self.settings_window.withdraw()
  self.root.after(1600,self._overlay)
 def _restore_region_windows(self):
  self.selecting_region=False
  self.root.deiconify()
  if self.loot.window and self.loot.window.winfo_exists():self.loot.window.deiconify()
  if self.settings_window and self.settings_window.winfo_exists():
   self.settings_window.deiconify();self.settings_window.lift()
 def _overlay(self):
  overlay=tk.Toplevel(self.root);overlay.attributes('-fullscreen',True);overlay.attributes('-topmost',True);overlay.attributes('-alpha',.28);overlay.configure(bg='#181020');canvas=tk.Canvas(overlay,cursor='crosshair',bg='#181020',highlightthickness=0);canvas.pack(fill='both',expand=True);pos=[0,0];rect=[None]
  def down(e):pos[:]=[e.x_root,e.y_root];rect[0]=canvas.create_rectangle(e.x,e.y,e.x,e.y,outline='yellow',width=3)
  def move(e):
   if rect[0]:canvas.coords(rect[0],pos[0],pos[1],e.x_root,e.y_root)
  def up(e):
   x1,y1=pos;x2,y2=e.x_root,e.y_root;overlay.destroy();self._restore_region_windows()
   if abs(x2-x1)>5 and abs(y2-y1)>5:
    selected=[min(x1,x2),min(y1,y2),abs(x2-x1),abs(y2-y1)]
    if self.region_target=='guild':self.loot.guild.set_region(selected);return
    if self.region_target in ('loot','loot_rare'):
     self.loot.set_region(selected,rare=self.region_target=='loot_rare');return
    for v,n in zip(self.region,selected):v.set(str(n))
    self.region_confirmed=True
    self.last_scan_started=0
    self.auto_enabled.set(True)
    self.refresh_auto_scan_label()
    self.save_quietly()
    self.status.set('OCR area saved. Auto OCR is ON; switch back to BDO.')
  canvas.bind('<ButtonPress-1>',down);canvas.bind('<B1-Motion>',move);canvas.bind('<ButtonRelease-1>',up);overlay.bind('<Escape>',lambda e:(overlay.destroy(),self._restore_region_windows()))
 def read_ocr(self,delayed=True,automatic=False):
  if self.busy or getattr(self,'cp_ocr_busy',False):return
  if automatic and (self.lite_use.get() and self.lite_scan_complete or self._tool_scan_latched):return
  if not automatic:self._allow_tool_change=True
  try:
   tess=self.tess.get().strip().strip('\"')
   if not (Path(tess).is_file() or shutil.which(tess)):
    if not automatic:self.status.set('Tesseract OCR not found. Install it or set its location in Settings.')
    else:self.scan_health.set('OCR unavailable · check Tesseract path in Settings')
    return
   if self.auto_tools.get():
    if not automatic:
     self.lite_scan_complete=False;self._tool_scan_latched=False
     self.tool_reader.last_discovery=-1e9;self.tool_reader.next_due=0
    self.busy=True;self.last_scan_started=time.monotonic()
    if delayed:
     self.status.set('Switch to BDO now — finding visible tools in 3 seconds…')
     self.set_tool_stage('waiting','Switch to BDO. Reading starts in 3 seconds.')
    if self.scan_button:self.scan_button.configure(state='disabled',text='FINDING TOOLS…')
    if delayed and not automatic:self.root.after(3000,lambda:self.wait_for_tool_capture(tess,time.monotonic()+12))
    else:self.root.after(1,lambda:self.capture_tools(tess,automatic))
    return
   x,y,w,h=[int(v.get()) for v in self.region]
   if w<3 or h<3:raise ValueError('Select a valid capture region.')
   # Allow time to focus BDO before capture.
   self.busy=True;self.last_scan_started=time.monotonic()
   if delayed:self.status.set('Switch to BDO now — capturing in 3 seconds…')
   elif not automatic:self.status.set('Scanning BDO…')
   if self.scan_button:self.scan_button.configure(state='disabled',text='SCANNING…')
   self.root.after(3000 if delayed else 1,lambda:self.capture(x,y,w,h,automatic))
  except Exception as e:
   self.busy=False
   if self.scan_button:self.scan_button.configure(state='normal',text='◎  SCAN & TRACK')
   if automatic:self.scan_health.set('Auto OCR error: '+str(e))
   else:messagebox.showerror('OCR',str(e))
 def capture(self,x,y,w,h,automatic=False):
  if automatic and not self.bdo_foreground():
   self.busy=False
   if self.scan_button:self.scan_button.configure(state='normal',text='◎  SCAN & TRACK')
   return
  try:
   wide=None
   if self.wide_tracking.get():
    # Capture a larger area at the SAME instant, but OCR it only if needed.
    # Anchor on the calibrated utensil instead of assuming the screen center.
    left=x-max(250,w//2);top=y-max(65,h)
    right=x+w+max(250,w//2);bottom=y+h+max(65,h)
    wide=ImageGrab.grab(bbox=(left,top,right,bottom),all_screens=True)
    im=wide.crop((x-left,y-top,x-left+w,y-top+h))
    wide_info=(wide,left,top,x+w/2,y+h/2)
   else:
    im=ImageGrab.grab(bbox=(x,y,x+w,y+h),all_screens=True)
    wide_info=None
   captured_at=time.time();captured_mono=time.monotonic();self.last_capture_mono=captured_mono;self.last_image=im.copy();self.show_preview(im)
   tess=self.tess.get().strip().strip(chr(34))
   if not automatic:self.status.set('Recognizing durability…')
   threading.Thread(target=self.recognize,args=(im,tess,automatic,captured_at,captured_mono,wide_info),daemon=True).start()
  except Exception as e:
   self.busy=False
   if self.scan_button:self.scan_button.configure(state='normal',text='◎  SCAN & TRACK')
   self.status.set('Capture failed: '+str(e))
 def show_preview(self,im):
  if self.preview is None or not self.preview.winfo_exists():return
  preview=im.copy();preview.thumbnail((535,95));preview=preview.resize((max(1,preview.width),max(1,preview.height)));self.photo=ImageTk.PhotoImage(preview);self.preview.configure(image=self.photo,text='')
 def open_diagnostics(self):
  folder=DATA_ROOT/'ocr-diagnostics';folder.mkdir(exist_ok=True);os.startfile(str(folder))
 def recognize(self,im,tess,automatic=False,captured_at=None,captured_mono=None,wide_info=None):
  """Quick two-pass OCR first; fallback only if recognition is uncertain.

  Tesseract invocation is usually the costliest part of scanning. Previous builds
  always ran eighteen subprocesses. This version typically uses two, or up to six
  on ambiguous images, without blocking the Tk main thread.
  """
  from collections import Counter
  import tempfile
  folder=DATA_ROOT/'ocr-diagnostics';folder.mkdir(exist_ok=True)
  start=time.monotonic();candidates=[];singles=[];lines=[]
  try:
   gray=ImageOps.grayscale(im)
   scale=3 if max(im.width,im.height)>600 else 4
   big=gray.resize((max(1,gray.width*scale),max(1,gray.height*scale)),Image.Resampling.LANCZOS)
   contrast=ImageOps.autocontrast(big)
   variants={
    'contrast':contrast,
    'inverted':ImageOps.invert(contrast),
    'threshold':contrast.point(lambda v:255 if v>165 else 0),
    'natural':big,
   }
   # Diagnostics are overwritten only when a scan is performed, not on every UI tick.
   if not automatic: im.save(folder/'last_capture.png')
   try:seconds=max(.05,float(self.speed.get()))
   except:seconds=1.0
   expected=remaining_at(self.value,self.anchor,captured_mono or time.monotonic(),seconds,self.running) if self.running else None
   maximum=int(self.maximum.get())
   for name,psm in select_ocr_passes():
    # Feed the image through stdin; avoid repeated PNG disk I/O.
    import io
    png=io.BytesIO();variants[name].save(png,format='PNG')
    cmd=[tess,'stdin','stdout','--psm',str(psm),'-l','eng',
         '-c','tessedit_char_whitelist=0123456789/(),|']
    try:
     flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
     proc=run_ocr(cmd,input=png.getvalue(),capture_output=True,timeout=5,creationflags=flags)
     proc_stdout=proc.stdout.decode('utf-8','replace');proc_stderr=proc.stderr.decode('utf-8','replace')
     raw=proc_stdout.strip()
     lines.append(f'{name} psm={psm} exit={proc.returncode}: {raw!r} {proc_stderr.strip()[:100]}')
     candidates.extend(extract_pairs(raw))
     singles.extend(int(n) for n in re.findall(r'(?<!\d)\d{1,6}(?!\d)',raw))
     if candidate_is_stable(candidates,expected,maximum):
      break
    except (OSError,subprocess.TimeoutExpired) as exc:
     lines.append(f'{name}: {type(exc).__name__}: {exc}')
   spatial=None
   # If fast OCR cannot reliably see the selected tool, look in a wider area.
   # This pass runs only on misses / initial acquisition / uncertain candidates.
   if wide_info is not None and (not candidates or not candidate_is_stable(candidates,expected,maximum)):
    try:
     wide,left,top,anchor_x,anchor_y=wide_info
     graywide=ImageOps.autocontrast(ImageOps.grayscale(wide))
     scale=2
     imagewide=graywide.resize((wide.width*scale,wide.height*scale),Image.Resampling.BILINEAR)
     import io
     png=io.BytesIO();imagewide.save(png,format='PNG')
     flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
     cmd=[tess,'stdin','stdout','--psm','11','-l','eng','tsv']
     proc=run_ocr(cmd,input=png.getvalue(),capture_output=True,timeout=6,creationflags=flags)
     positioned=tsv_candidates(proc.stdout.decode('utf-8','replace'),x_offset=left,y_offset=top,scale=scale)
     spatial=choose_spatial_pair(positioned,anchor_x,expected=expected,expected_max=maximum,anchor_y=anchor_y)
     lines.append('Wide fallback: '+str(len(positioned))+' positioned candidates; picked '+str(spatial))
    except (OSError,subprocess.TimeoutExpired,ValueError) as exc:
     lines.append('Wide fallback error: '+str(exc))
   duration=time.monotonic()-start
   if not automatic or not candidates: (folder/'ocr_log.txt').write_text('\n'.join(lines),encoding='utf-8')
   self.root.after(0,lambda:self.finish_ocr(candidates,singles,lines,automatic,captured_at,captured_mono,duration,spatial))
  except Exception as exc:
   duration=time.monotonic()-start
   error=str(exc)
   self.root.after(0,lambda:self.finish_ocr([],[],['OCR error: '+error],automatic,captured_at,captured_mono,duration,None))
 def finish_ocr(self,results,singles,lines,automatic=False,captured_at=None,captured_mono=None,duration=0,spatial=None):
  """Apply readings at screenshot time; never turn one dubious scan into a new tool."""
  from collections import Counter
  self.busy=False
  if self.scan_button:self.scan_button.configure(state='normal',text='◎  SCAN & TRACK')
  self.scan_stats['last_duration']=round(duration,2)
  now=time.monotonic()
  try:
   old_max=int(self.maximum.get().replace(',',''))
   seconds=max(.05,float(self.speed.get()))
  except Exception:
   old_max=3000;seconds=1.0
  measured_at=captured_mono if captured_mono is not None else now
  expected=(remaining_at(self.value,self.anchor,measured_at,seconds,True)
            if self.running else self.value if self.has_reading else None)
  picked=None
  if results:
   try:
    value,votes,was_corrected=choose_reading(results,expected=expected,expected_max=old_max)
    picked=(*value,votes,was_corrected)
   except ValueError:pass
  if spatial is not None:
   a,b,votes,corrected,*_=spatial
   # When a wide search disagrees with an already established tool, defer to
   # the validated reading gate rather than blindly switching to a neighbor.
   if picked is None or not self.has_reading:
    picked=(a,b,votes,corrected)
  if picked:
   a,b,votes,was_corrected=picked
   decision=self.reading_gate.evaluate((a,b),expected,old_max,now,
                                       votes=votes,has_baseline=self.has_reading)
   if decision.kind=='confirm':
    self.ocr_text.set(f'Uncertain OCR: {a:,}/{b:,} · checking again')
    self.scan_health.set('○ OCR needs confirmation · %.1fs'%duration)
    if not automatic:self.status.set(decision.message + ' Use SCAN again if needed.')
    return
   new_tool=decision.kind=='new_tool'
   if new_tool:
    self.session_id=uuid.uuid4().hex
    self.speed_estimator.reset()
   prior_ocr=self.last_good_ocr
   self.has_reading=True
   if getattr(self,'lite_use',None) is not None and self.lite_use.get():self.lite_scan_complete=True
   self.last_good_ocr=(a,b)
   self._tool_timer_estimated=False
   self.last_ocr_at=measured_at
   self.dur.set(str(a));self.maximum.set(str(b))
   self.value=align_to_capture(float(a),measured_at,now,seconds)
   self.anchor=now;self.running=self.value>0
   if new_tool:self.alarmed=False
   elif prior_ocr is None:self.alarmed=False
   elif a>prior_ocr[0]:self.alarmed=False
   self.source.set('OCR CONFIRMED · '+time.strftime('%H:%M:%S',time.localtime(captured_at or time.time())))
   self.ocr_text.set(f'{a:,}/{b:,} · {votes} OCR confirmation(s)'+(' · corrected' if was_corrected else ''))
   observed_speed=self.speed_estimator.add(a,b,captured_at or time.time(),self.session_id)
   if observed_speed is not None:
    self.speed_health.set(f'Observed speed · {observed_speed:.2f}s/craft (configured {seconds:g}s)')
   self.scan_stats['ok']+=1
   self.scan_health.set(f'● OCR OK · {duration:.1f}s · {self.scan_stats["ok"]} accepted')
   if not automatic:self.status.set('OCR confirmed %s · %s'%(
       f'{a:,}/{b:,}', 'new utensil detected' if new_tool else 'tracking started'))
   # Never publish before SEND NOW. After linking, new OCR readings keep the
   # same planner session synchronized, and confirmed replacements get new IDs.
   if self.sync_armed and self.bridge and self.bridge.server:
    if should_publish(self.last_published,(a,b),self.last_publish_mono,now,self.session_id):
     if self.send_to_planner(measurement=(a,b),observed_at=captured_at,source='ocr'):
      self.last_published=(a,b,self.session_id);self.last_publish_mono=now
   return
  try:maximum=int(self.maximum.get().replace(',',''))
  except:maximum=3000
  valid=[n for n in singles if 0<=n<=maximum]
  if valid:
   n,votes=Counter(valid).most_common(1)[0]
   self.ocr_text.set(f'Partial: {n} · maximum missing ({votes} passes)')
   if not automatic:self.status.set('Only part of the label is visible. Widen the OCR region in Settings.')
   return
  self.scan_stats['failed']+=1
  self.scan_health.set(f'○ OCR uncertain · {duration:.1f}s · {self.scan_stats["failed"]} misses')
  self.ocr_text.set('No reliable current/max durability pair')
  if not automatic:self.status.set('No reading found. Move the camera or adjust the region in Settings.')
 def close(self):
  self.tool_debug.close()
  try:self.save()
  except:pass
  try:
   if self.bridge:self.bridge.close()
  except Exception:pass
  self.loot.close()
  if getattr(self,'windows_ocr',None) is not None:self.windows_ocr.close()
  self.root.destroy()

if __name__=='__main__':
 if '--self-check' in sys.argv:
  from self_check import run_self_check
  run_self_check(App,ROOT,DATA_ROOT)
  raise SystemExit(0)
 try:ctypes.windll.shcore.SetProcessDpiAwareness(2)
 except Exception:pass
 instance=InstanceLock(DATA_ROOT)
 if not instance.acquire():
  if not focus_existing(DATA_ROOT):
   notice=tk.Tk();notice.withdraw();messagebox.showinfo('BDO Vision','Vision is already open. Your shared history is safe; restore its window from the taskbar.');notice.destroy()
  raise SystemExit(0)
 try:
  backup_profile(DATA_ROOT,'startup')
  root=tk.Tk();App(root);root.mainloop()
 finally:instance.release()
