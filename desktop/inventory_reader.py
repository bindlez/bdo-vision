"""Optional I-key edge observer and bounded, verified visible inventory snapshots."""
import ctypes,json,re,threading,time,io,math
from pathlib import Path
from PIL import ImageGrab,ImageOps
from windows_bdo import foreground_bdo_capture_bounds,item_regions_visible


def parse_weight(text):
    if not re.search(r'\bInventory\b',text,re.I):return None
    match=re.search(r'\bWeight\s*[:：=]{0,2}\s*([\d,]+(?:\.\d+)?)\s*/\s*([\d,]+(?:\.\d+)?)\s*LT\b',text,re.I)
    if not match:return None
    def number(raw):
        if not re.fullmatch(r'(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?',raw):raise ValueError()
        return float(raw.replace(',',''))
    try:current,maximum=map(number,match.groups())
    except ValueError:return None
    if not 0<=current<=1e6 or not 0<maximum<=1e6:return None
    return {'current':current,'maximum':maximum}


def read_inventory_image(image,worker,tess):
    from ocr_runtime import run_ocr
    frame=image.copy();frame.thumbnail((1400,1000));coarse=worker.recognize(frame,timeout=1.5,lock_timeout=.02)
    if not re.search(r'\bInventory\b',coarse['text'],re.I):return None,coarse['text'],[]
    scale=frame.width/image.width;words=coarse.get('words',[])
    checks=[(int(w['x']/scale),int(w['y']/scale),max(1,int(w['w']/scale)),max(1,int(w['h']/scale))) for w in words if str(w.get('text','')).casefold()=='inventory']
    candidates=[w for w in words if str(w.get('text','')).casefold()=='weight']
    logs=[]
    for word in sorted(candidates,key=lambda w:w['y'],reverse=True)[:2]:
        box=(max(0,int((word['x']-8)/scale)),max(0,int((word['y']-.3*word['h'])/scale)),image.width,min(image.height,int((word['y']+1.5*word['h'])/scale)))
        if box[3]<=box[1] or (box[2]-box[0])*(box[3]-box[1])*9>1_500_000:continue
        crop=image.crop(box);crop=ImageOps.autocontrast(crop.convert('L')).resize((crop.width*3,crop.height*3))
        native=worker.recognize(crop,timeout=1.5,lock_timeout=.02)['text']
        blob=io.BytesIO();crop.save(blob,format='PNG')
        result=run_ocr([tess,'stdin','stdout','--psm','7','-l','eng'],input=blob.getvalue(),capture_output=True,timeout=2)
        raw=result.stdout.decode('utf-8','replace');logs.append('WINDOWS CROP\n'+native+'\nTESSERACT CROP\n'+raw)
        first,second=parse_weight('Inventory\n'+native),parse_weight('Inventory\n'+raw)
        if not result.returncode and first and first==second:
            headings=[w for w in words if str(w.get('text','')).casefold()=='inventory' and w['y']<word['y'] and abs(w['x']-word['x'])<300]
            if not headings:continue
            heading=max(headings,key=lambda w:w['h'])
            locator=(int(heading['x']/scale),int(heading['y']/scale),max(1,int(heading['w']/scale)),max(1,int(heading['h']/scale)))
            return first,'\n\n'.join(logs),[locator,(box[0],box[1],box[2]-box[0],box[3]-box[1])]
    return None,'\n\n'.join(logs) or coarse['text'],checks


class InventoryReader:
    def __init__(self,app):
        from ocr_debug import OCRReaderView
        self.debug=OCRReaderView(app,'Inventory OCR reader',self.read_delayed)
        self.app=app;self.root=app.root;self.path=app.loot.path/'inventory-snapshot.json';self.snapshot={};self.busy=False;self.down=False;self.job=None;self.pending=None;self.closed=False
        try:
            if self.path.stat().st_size>65536:raise ValueError('Snapshot too large')
            saved=json.loads(self.path.read_text(encoding='utf-8'))
            parsed=parse_weight('Inventory Weight '+str(saved.get('current'))+' / '+str(saved.get('maximum'))+' LT')
            if type(saved.get('at')) in (int,float) and math.isfinite(saved['at']) and 0<=saved['at']<=time.time()+60 and parsed:self.snapshot={'at':saved['at'],**parsed,'items':[],'partial':True}
        except (OSError,ValueError,TypeError):pass
        if self.enabled():self.poll()

    def enabled(self):return self.app.loot.platform_preferences.get('inventory_key_capture',False) is True

    def toggle(self):
        p=self.app.loot.platform_preferences;p['inventory_key_capture']=not self.enabled();self.app.save_quietly()
        self.app.status.set('Inventory I-key snapshots '+('enabled. Only a verified visible Inventory/Weight panel is accepted.' if self.enabled() else 'disabled.'))
        if self.enabled() and self.job is None:self.poll()

    def poll(self):
        self.job=None
        if self.closed or not self.enabled():return
        if self.app.lite_use.get():self.down=False;self.job=self.root.after(1000,self.poll);return
        try:
            down=bool(ctypes.windll.user32.GetAsyncKeyState(0x49)&0x8000)
            if down and not self.down and not self.app.lite_use.get() and foreground_bdo_capture_bounds() is not None and self.pending is None:
                self.pending=self.root.after(600,self.read)
            self.down=down
        except (AttributeError,OSError):pass
        self.job=self.root.after(40,self.poll)

    def read(self):
        self.pending=None
        if self.closed or self.busy or self.app.lite_use.get():return
        worker=getattr(self.app,'windows_ocr',None)
        bounds=foreground_bdo_capture_bounds()
        if not worker or bounds is None:self.app.status.set('Inventory snapshot: show BDO inventory; Windows reader must be available.');return
        if self.app.busy or self.app.loot.busy:self.app.status.set('Inventory snapshot skipped: another reader is busy. Press I again or use Read inventory.');return
        _,left,top,right,bottom=bounds
        try:image=ImageGrab.grab(bbox=(left,top,right,bottom),all_screens=True)
        except OSError:return
        self.busy=True;token=self.debug.token();captured=time.time();tess=self.app.tess.get().strip().strip(chr(34))
        def work():
            detail='No agreed weight';checks=[]
            try:
                weight,detail,relative=read_inventory_image(image,worker,tess)
                checks=[(left+x,top+y,w,h) for x,y,w,h in relative]
                result={**weight,'at':captured,'items':[],'partial':True,'scope':'Visible inventory weight only; icon identities and stack quantities are unknown.'} if weight else None
            except (RuntimeError,OSError,ValueError,KeyError) as exc:result=None;detail=str(exc)
            def finish():
                self.busy=False
                if self.closed:return
                self.debug.show(token,image,detail+'\n\nResult: '+str(result),captured)
                if foreground_bdo_capture_bounds()!=bounds: self.app.status.set('Inventory changed or lost focus; snapshot discarded.');return
                if result and (not checks or not item_regions_visible(checks)[0]):self.app.status.set('Inventory labels are covered; snapshot discarded.');return
                if not result:self.app.status.set('Inventory weight not verified. Show Inventory and its Weight / LT line, then retry.');return
                self.snapshot=result
                temporary=self.path.with_suffix('.tmp')
                try:temporary.write_text(json.dumps(result),encoding='utf-8');temporary.replace(self.path)
                except OSError:self.app.status.set('Inventory read in memory; snapshot could not be saved to disk.');return
                bridge=getattr(self.app,'bridge',None)
                if bridge:
                    with bridge._lock:bridge.inventory_snapshot=dict(result)
                self.app.status.set(f"Inventory snapshot saved: {result['current']:,.2f} / {result['maximum']:,.2f} LT. Item stacks remain unknown.")
            if not self.closed:self.root.after(0,finish)
        threading.Thread(target=work,name='vision-inventory-snapshot',daemon=True).start()

    def read_delayed(self):
        if self.pending is None:self.pending=self.root.after(1800,self.read);self.app.status.set('Switch to BDO inventory. Snapshot in 1.8 seconds; Lite Use prevents it.')

    def close(self):
        self.closed=True;self.debug.close()
        for job in (self.job,self.pending):
            if job is not None:self.root.after_cancel(job)
