"""Optional, visible alchemy guild-mission progress. No inferred guild credit."""
from collections import deque
import io,json,math,re,time,subprocess
from PIL import ImageOps,Image,ImageChops
from ocr_runtime import run_ocr

NUMBER=r'(?:[1-9]\d{0,2}(?:,\d{3})+|0|[1-9]\d{0,7})'
PAIR=re.compile(r"(?<![\w,.?])("+NUMBER+r")\s*[:;]?\s*['‘’]?\s*/\s*/?\s*['‘’]?\s*("+NUMBER+r")(?![\w,.?])")
OBJECTIVE=re.compile(r'\b(?:obtain|produce|make|craft|perform|talk|reach|defeat|collect)\b',re.I)


def objective_block(lines,index):
    block=[lines[index]]
    for line in lines[index+1:index+4]:
        if OBJECTIVE.search(line) or re.search(r'\[(?:bonus|daily|weekly|alchemy)\b',line,re.I):break
        block.append(line)
    return '\n'.join(block)


def counter_in(text):
    text=re.sub(r'(?m)^\s*/\s*[-–—]\s*(?=\d)','/',text)
    pairs={(int(a.replace(',','')),int(b.replace(',',''))) for a,b in PAIR.findall(text)}
    if len(pairs)!=1:return None
    a,b=pairs.pop()
    return (a,b) if 0<=a<=b<=10_000_000 and b else None


def parse_objectives(text):
    """Named Daily/Bonus objectives, independently scoped and bounded."""
    lines=[s.strip() for s in str(text)[:6000].splitlines() if s.strip()];rows=[]
    starts=[i for i,s in enumerate(lines) if re.search(r'\[(?:bonus|daily|weekly|alchemy|main|event)\b',s,re.I)]
    for n,start in enumerate(starts):
        header=lines[start];kind=re.search(r'\[(Daily|Bonus)\]',header,re.I)
        if not kind:continue
        stop=starts[n+1] if n+1<len(starts) else len(lines)
        scope=lines[start+1:stop]
        for i,line in enumerate(scope):
            if not OBJECTIVE.search(line):continue
            block=objective_block(scope,i);pair=counter_in(block)
            if not pair:continue
            detail=re.sub(r'^[^\w]+','',PAIR.sub('',block).splitlines()[0]).strip().rstrip(" ()'\"")
            key=kind[1].casefold()+':'+re.sub(r'[^a-z]','',detail.casefold())[:100]
            rows.append({'key':key,'kind':kind[1].title(),'label':header[:120],'objective':detail[:160],'current':pair[0],'target':pair[1]})
    return rows[:8]


def parse_quest_text(text):
    text=str(text)[:6000];lines=[line.strip() for line in text.splitlines() if line.strip()]
    start=next((i for i,line in enumerate(lines) if 'guild' in line.casefold() and 'alchemy' in line.casefold() and any(w in line.casefold() for w in ('mission','quest','supp'))),None)
    if start is None:return None
    scope=[]
    for line in lines[start:start+24]:
        if scope and re.search(r'\[(?:bonus|daily|weekly|main|event|repeat|combat|story)\b',line,re.I):break
        scope.append(line)
    objective=next((i for i,line in enumerate(scope[1:],1) if re.search(r'\b(?:obtain|produce|make|craft|perform)\b',line,re.I)),None)
    if objective is None:return None
    text=objective_block(scope,objective)
    text=re.sub(r'(?<=\d)\s*[:;]\s*(?=/)','',text)
    text=re.sub(r"/\s*['‘’](\d[\d,]*)['‘’]",r'/\1',text)
    text=re.sub(r'(?m)^\s*/\s*[-–—]\s*(?=\d)','/',text)
    text=re.sub(r"(?<=\d)\s*['‘’]?\s*/\s*/?\s*(?=\d)",'/',text)
    pairs={(int(a.replace(',','')),int(b.replace(',',''))) for a,b in PAIR.findall(text)}
    if len(pairs)!=1:return None
    current,target=pairs.pop()
    if not 0<=current<=target<=10_000_000 or target==0:return None
    heading=re.sub(r'^[^\w\[]+','',scope[0]).strip()
    detail=re.sub(r'^[^\w\[]+','',PAIR.sub('',text).splitlines()[0]).strip().rstrip(" ()'\"")
    detail=re.sub(r'(?<=[A-Za-z])[\\/](?=[A-Za-z])',' ',detail)
    result={'current':current,'target':target,'label':heading[:120],'objective':detail[:160]}
    remaining=re.search(r'Remaining\s*:\s*(\d{1,4})\s*min','\n'.join(scope),re.I)
    if remaining:result['remaining_minutes']=int(remaining[1])
    return result


def parse_guild_completion(text):
    """Recognize the guild's literal finished widget, never a personal 'Complete'."""
    lines=[line.strip() for line in str(text)[:6000].splitlines() if line.strip()]
    for index,line in enumerate(lines):
        # Exact affirmative sentence: 'not complete', instructions and objectives
        # containing the word complete cannot satisfy this form.
        if re.fullmatch(r'[^\w]*The guild mission is complete[.!]?[^\w]*',line,re.I):
            return {'completion_observed':True,'completion_basis':'mission_message','completion_evidence':line[:240]}
        block=[]
        for part in lines[index:index+4]:
            if re.search(r'\[(?:bonus|daily|weekly|main|event|repeat|combat|story)\b',part,re.I):break
            block.append(part)
        phrase=' '.join(block)
        match=re.match(r'[^\w]*Claim your rewards via the ["\u201c\u201d\u2018\u2019\x27]?Complete\s+Mission["\u201c\u201d\u2018\u2019\x27]? button in the Guild Mission window\b',phrase,re.I)
        if match:
            evidence=match[0];evidence=evidence[evidence.casefold().index('claim'):]
            return {'completion_observed':True,'completion_basis':'reward_message','completion_evidence':evidence[:240]}
    return None


def guild_heading_crops(image):
    r,g,b=image.convert('RGB').split()
    mask=ImageChops.multiply(ImageChops.subtract(r,g).point(lambda p:255 if p>10 else 0),ImageChops.subtract(g,b).point(lambda p:255 if p>12 else 0))
    mask=ImageChops.multiply(mask,r.point(lambda p:255 if p>135 else 0))
    bands=[];top=None;last=None
    for y in range(mask.height):
        count=mask.crop((0,y,mask.width,y+1)).histogram()[255]
        if count>=max(10,mask.width*.02):
            if top is None:top=y
            last=y
        elif top is not None and y-last>2:
            if 4<=last-top+1<=30:bands.append((top,last+1))
            top=last=None
    if top is not None and 4<=last-top+1<=30:bands.append((top,last+1))
    result=[]
    for a,bottom in bands[:6]:
        box=mask.crop((0,a,mask.width,bottom)).getbbox()
        if box:
            source=(max(0,box[0]-6),max(0,a-4),min(image.width,box[2]+6),min(image.height,bottom+4))
            crop=image.crop(source);crop.info['quest_box']=source;result.append(crop)
    return result[:4]


def recognize_quest(image,tess,diagnostic=None):
    if image.width<30 or image.height<15 or image.width*image.height>250_000:raise ValueError('Select only the current mission heading and progress, up to 250,000 pixels.')
    gray=ImageOps.autocontrast(image.convert('RGB').getchannel('R'));scale=min(2.5,math.sqrt(1_500_000/(gray.width*gray.height)))
    gray=gray.resize((max(1,int(gray.width*scale)),max(1,int(gray.height*scale))),Image.Resampling.LANCZOS)
    readings=[];texts=[];deadline=time.monotonic()+3
    for prepared in (gray,ImageOps.invert(gray)):
        data=io.BytesIO();prepared.save(data,format='PNG')
        remaining=deadline-time.monotonic()
        if remaining<.15:raise RuntimeError('Guild reader reached its work budget; retrying.')
        result=run_ocr([tess,'stdin','stdout','--psm','11','-l','eng'],input=data.getvalue(),capture_output=True,timeout=min(1.5,remaining))
        if result.returncode:raise RuntimeError('Guild mission OCR failed; retrying automatically.')
        text=result.stdout.decode('utf-8','replace')[:6000];texts.append(text);readings.append(parse_quest_text(text))
        if diagnostic is not None:diagnostic(prepared,'BROAD PASS '+str(len(texts))+'\n'+text+'\nSCOPED GUILD: '+str(readings[-1]))
    a,b=readings
    agreed=a if a and b and (a['current'],a['target'])==(b['current'],b['target']) else None
    completions=[parse_guild_completion(text) for text in texts]
    conflict=any(completions) and any(row and row['current']<row['target'] for row in readings)
    if all(completions) and not conflict:
        agreed={**completions[0],'completion_votes':2}
    focused=[]
    kinds=[{r['kind'] for r in parse_objectives(text)} for text in texts]
    if not agreed or {'Daily','Bonus'}-(kinds[0]&kinds[1]):
        headings=guild_heading_crops(image)
        for index,crop in enumerate(headings):
            remaining=deadline-time.monotonic()
            if remaining<.15:break
            prepared=ImageOps.autocontrast(crop.convert('RGB').getchannel('R'))
            prepared=prepared.resize((prepared.width*3,prepared.height*3),Image.Resampling.LANCZOS)
            data=io.BytesIO();prepared.save(data,format='PNG')
            try:result=run_ocr([tess,'stdin','stdout','--psm','7','-l','eng'],input=data.getvalue(),capture_output=True,timeout=min(1,remaining))
            except subprocess.TimeoutExpired:break
            header=result.stdout.decode('utf-8','replace').strip()[:240] if not result.returncode else ''
            folded=header.casefold()
            guild_header='guild' in folded and 'alchemy' in folded and any(w in folded for w in ('supp','mission','quest'))
            if guild_header:
                a,b=[parse_quest_text(header+'\n'+text) for text in texts[:2]]
                if a and b and (a['current'],a['target'])==(b['current'],b['target']):agreed=a
            if not (guild_header and not agreed or re.search(r'\[(Daily|Bonus)\]',header,re.I)) or 'quest_box' not in crop.info:continue
            source=crop.info['quest_box'];stop=min(image.height,source[3]+120)
            if index+1<len(headings) and 'quest_box' in headings[index+1].info:stop=min(stop,headings[index+1].info['quest_box'][1])
            if stop-source[3]<12:continue
            body=image.crop((max(0,source[0]-12),source[3],image.width,stop))
            field=ImageOps.autocontrast(body.convert('L')).resize((body.width*3,body.height*3),Image.Resampling.LANCZOS)
            verified=[]
            for variant in (field,ImageOps.invert(field)):
                remaining=deadline-time.monotonic()
                if remaining<.15:break
                data=io.BytesIO();variant.save(data,format='PNG')
                try:response=run_ocr([tess,'stdin','stdout','--psm','6','-l','eng'],input=data.getvalue(),capture_output=True,timeout=min(1,remaining))
                except subprocess.TimeoutExpired:break
                body_text=response.stdout.decode('utf-8','replace') if not response.returncode else ''
                texts.append('FOCUSED '+header+'\n'+body_text)
                verified.append(parse_quest_text(header+'\n'+body_text) if guild_header else parse_objectives(header+'\n'+body_text))
            if len(verified)==2:
                if guild_header:
                    a,b=verified
                    if a and b and (a['current'],a['target'])==(b['current'],b['target']):agreed=a
                else:
                    right={r['key']:r for r in verified[1]}
                    focused.extend(r for r in verified[0] if r['key'] in right and (r['current'],r['target'])==(right[r['key']]['current'],right[r['key']]['target']))
    left={r['key']:r for r in parse_objectives(texts[0])};right={r['key']:r for r in parse_objectives(texts[1])}
    objectives=[r for key,r in left.items() if key in right and (r['current'],r['target'])==(right[key]['current'],right[key]['target'])]
    objectives=list({r['key']:r for r in [*objectives,*focused]}.values())[:8]
    if conflict:agreed=None
    if objectives:agreed={**(agreed or {}),'objectives':objectives}
    return agreed,'\n\n'.join(texts)[:10000]


class GuildQuestProgress:
    def __init__(self,db):
        self.db=db;self.current=None;self.target=None;self.label='Alchemy guild mission';self.objective='';self.last_at=None
        self.near_sent=False;self.complete_sent=False;self.available=False;self.reason='No verified guild mission yet'
        self.samples=deque(maxlen=8);self.pending=None;self.mission_deadline=None;self.legacy_saved=False
        self.completion_at=None;self.completion_seen_at=None;self.completion_basis='';self.completion_evidence=''
        db.execute('CREATE TABLE IF NOT EXISTS guild_quest_state (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS guild_quest_history (id INTEGER PRIMARY KEY, saved_at REAL NOT NULL, label TEXT NOT NULL, current INTEGER NOT NULL, target INTEGER NOT NULL)');db.commit()
        row=db.execute('SELECT payload FROM guild_quest_state WHERE id=1').fetchone()
        if row:
            try:
                state=json.loads(row[0]);a,b=state['current'],state['target']
                self.legacy_saved=bool(state.get('legacy_saved','mission_deadline' not in state))
                completed_at=state.get('completion_at')
                visual=state.get('complete_sent') and state.get('completion_basis') in ('mission_message','reward_message') and type(completed_at) in (int,float) and math.isfinite(completed_at)
                if (type(a) is int and type(b) is int and 0<=a<=b<=10_000_000 and b) or (a is None and b is None and visual):
                    self.current=a;self.target=b;self.label=str(state.get('label',self.label))[:120]
                    self.objective=str(state.get('objective',''))[:160]
                    self.near_sent=bool(state.get('near_sent'));self.complete_sent=bool(state.get('complete_sent'))
                    stamp=state.get('last_at');self.last_at=float(stamp) if type(stamp) in (int,float) and math.isfinite(stamp) else None
                    self.reason='Last saved progress; waiting for a fresh visible counter'
                    deadline=state.get('mission_deadline')
                    if type(deadline) in (int,float) and math.isfinite(deadline):self.mission_deadline=deadline
                    if visual:
                        self.completion_at=float(completed_at);self.completion_seen_at=self.completion_at
                        self.completion_basis=state['completion_basis'];self.completion_evidence=str(state.get('completion_evidence',''))[:240]
                        self.reason='Last saved completion; waiting for the visible guild widget'
            except (ValueError,TypeError,KeyError):pass

    def save(self):
        if self.current is None and self.completion_at is None:
            with self.db:self.db.execute('DELETE FROM guild_quest_state WHERE id=1')
            return
        state={key:getattr(self,key) for key in ('current','target','label','objective','last_at','near_sent','complete_sent','mission_deadline','legacy_saved','completion_at','completion_basis','completion_evidence')}
        with self.db:self.db.execute('INSERT INTO guild_quest_state VALUES (1,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',(json.dumps(state),))

    def reset(self):
        if self.current is not None:
            with self.db:self.db.execute('INSERT INTO guild_quest_history(saved_at,label,current,target) VALUES (?,?,?,?)',(time.time(),self.label,self.current,self.target))
        self.current=self.target=self.last_at=None;self.near_sent=self.complete_sent=False;self.samples.clear();self.pending=None;self.mission_deadline=None;self.legacy_saved=False
        self.completion_at=self.completion_seen_at=None;self.completion_basis=self.completion_evidence=''
        self.pause('Ready for the next alchemy guild mission');self.save()

    def pause(self,reason):
        self.available=False;self.reason=str(reason)[:180];self.samples.clear()

    def accept(self,reading,threshold=95,at=None):
        at=time.time() if at is None else at
        if reading.get('completion_observed') is True:
            if reading.get('completion_votes')!=2 or reading.get('completion_basis') not in ('mission_message','reward_message'):return []
            changed=self.completion_at is None;alert=not self.complete_sent
            if changed:
                self.completion_at=at;self.completion_basis=reading['completion_basis']
                self.completion_evidence=str(reading.get('completion_evidence',''))[:240]
            self.completion_seen_at=at;self.complete_sent=self.near_sent=True
            self.available=True;self.pending=None;self.samples.clear();self.reason='Verified visible guild mission completion'
            if changed or alert:self.save()
            return ['complete'] if alert else []
        a,b=reading.get('current'),reading.get('target')
        if type(a) is not int or type(b) is not int or not 0<=a<=b<=10_000_000 or not b:return []
        minutes=reading.get('remaining_minutes');deadline=at+minutes*60 if type(minutes) is int and 0<=minutes<=1440 else None
        if (self.completion_at is not None and a<b) or (self.current is not None and (b!=self.target or a<self.current)):
            candidate=self.pending
            timer_reset=deadline is not None and self.mission_deadline is not None and deadline>self.mission_deadline+120
            legacy_restart=self.legacy_saved and deadline is not None
            if (self.complete_sent or timer_reset or legacy_restart) and candidate and candidate[1]==b and candidate[0]<=a and 1<=at-candidate[2]<=60:self.reset()
            else:
                self.pending=(a,b,at);self.pause('Counter decreased or target changed. Confirm the new quest, or use NEXT QUEST.');return []
        self.pending=None;changed=(a,b)!=(self.current,self.target)
        self.current=a;self.target=b;self.label=str(reading.get('label','Alchemy guild mission'))[:120];self.objective=str(reading.get('objective',''))[:160];self.last_at=at
        if deadline is not None:self.mission_deadline=deadline;self.legacy_saved=False
        self.available=True;self.reason='Verified visible mission counter'
        if not self.samples or self.samples[-1][1]!=a:self.samples.append((at,a))
        alerts=[];threshold=max(1,min(99,int(threshold)))
        if a==b and not self.complete_sent:
            self.near_sent=True;self.complete_sent=True;alerts=['complete'];changed=True
        elif a*100>=b*threshold and not self.near_sent:
            self.near_sent=True;alerts=['near'];changed=True
        if changed:self.save()
        return alerts

    def snapshot(self,now=None):
        now=time.time() if now is None else now;stamp=self.completion_seen_at if self.completion_at is not None else self.last_at
        fresh=self.available and stamp is not None and 0<=now-stamp<=35
        remaining=0 if self.complete_sent else self.target-self.current if self.current is not None else None;eta=None
        if fresh and len(self.samples)>=2:
            elapsed=self.samples[-1][0]-self.samples[0][0];gain=self.samples[-1][1]-self.samples[0][1]
            if elapsed>=15 and gain>0:eta=remaining*elapsed/gain
        return {'current':self.current,'target':self.target,'label':self.label,'objective':self.objective,'available':fresh,'last_at':self.last_at,
                'percent':100 if self.complete_sent else 100*self.current/self.target if self.target else 0,'remaining':remaining,'eta':eta,
                'completion_at':self.completion_at,'completion_seen_at':self.completion_seen_at,'completion_basis':self.completion_basis,'completion_evidence':self.completion_evidence,
                'complete':self.complete_sent,'reason':self.reason if fresh or not self.available else 'Last verified progress; waiting for a fresh reading'}
