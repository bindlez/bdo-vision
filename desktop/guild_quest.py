"""Optional, visible alchemy guild-mission progress. No inferred guild credit."""
from collections import deque
import io,json,math,re,time
from PIL import ImageOps,Image
from ocr_runtime import run_ocr

NUMBER=r'(?:[1-9]\d{0,2}(?:,\d{3})+|0|[1-9]\d{0,7})'
PAIR=re.compile(r'(?<![\w,.?])('+NUMBER+r')\s*/\s*('+NUMBER+r')(?![\w,.?])')


def parse_quest_text(text):
    text=str(text)[:6000];lines=[line.strip() for line in text.splitlines() if line.strip()]
    start=next((i for i,line in enumerate(lines) if 'guild' in line.casefold() and 'alchemy' in line.casefold() and any(w in line.casefold() for w in ('mission','quest','supp'))),None)
    if start is None:return None
    scope=[]
    for line in lines[start:start+9]:
        if scope and re.search(r'\[(?:bonus|daily|weekly|main|event|repeat|combat|story)\b',line,re.I):break
        scope.append(line)
    objective=next((i for i,line in enumerate(scope[1:],1) if re.search(r'\b(?:obtain|produce|make|craft|perform)\b',line,re.I)),None)
    if objective is None:return None
    text='\n'.join(scope[objective:objective+2])
    pairs={(int(a.replace(',','')),int(b.replace(',',''))) for a,b in PAIR.findall(text)}
    if len(pairs)!=1:return None
    current,target=pairs.pop()
    if not 0<=current<=target<=10_000_000 or target==0:return None
    heading=re.sub(r'^[^\w\[]+','',scope[0]).strip()
    detail=re.sub(r'^[^\w\[]+','',PAIR.sub('',scope[objective])).strip().rstrip(' ()')
    return {'current':current,'target':target,'label':heading[:120],'objective':detail[:160]}


def recognize_quest(image,tess):
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
    a,b=readings
    agreed=a if a and b and (a['current'],a['target'])==(b['current'],b['target']) else None
    return agreed,'\n\n'.join(texts)[:1200]


class GuildQuestProgress:
    def __init__(self,db):
        self.db=db;self.current=None;self.target=None;self.label='Alchemy guild mission';self.objective='';self.last_at=None
        self.near_sent=False;self.complete_sent=False;self.available=False;self.reason='No verified guild mission yet'
        self.samples=deque(maxlen=8);self.pending=None
        db.execute('CREATE TABLE IF NOT EXISTS guild_quest_state (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS guild_quest_history (id INTEGER PRIMARY KEY, saved_at REAL NOT NULL, label TEXT NOT NULL, current INTEGER NOT NULL, target INTEGER NOT NULL)');db.commit()
        row=db.execute('SELECT payload FROM guild_quest_state WHERE id=1').fetchone()
        if row:
            try:
                state=json.loads(row[0]);a,b=state['current'],state['target']
                if type(a) is int and type(b) is int and 0<=a<=b<=10_000_000 and b:
                    self.current=a;self.target=b;self.label=str(state.get('label',self.label))[:120]
                    self.objective=str(state.get('objective',''))[:160]
                    self.near_sent=bool(state.get('near_sent'));self.complete_sent=bool(state.get('complete_sent'))
                    stamp=state.get('last_at');self.last_at=float(stamp) if type(stamp) in (int,float) and math.isfinite(stamp) else None
                    self.reason='Last saved progress; waiting for a fresh visible counter'
            except (ValueError,TypeError,KeyError):pass

    def save(self):
        if self.current is None:
            with self.db:self.db.execute('DELETE FROM guild_quest_state WHERE id=1')
            return
        state={key:getattr(self,key) for key in ('current','target','label','objective','last_at','near_sent','complete_sent')}
        with self.db:self.db.execute('INSERT INTO guild_quest_state VALUES (1,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',(json.dumps(state),))

    def reset(self):
        if self.current is not None:
            with self.db:self.db.execute('INSERT INTO guild_quest_history(saved_at,label,current,target) VALUES (?,?,?,?)',(time.time(),self.label,self.current,self.target))
        self.current=self.target=self.last_at=None;self.near_sent=self.complete_sent=False;self.samples.clear();self.pending=None
        self.pause('Ready for the next alchemy guild mission');self.save()

    def pause(self,reason):
        self.available=False;self.reason=str(reason)[:180];self.samples.clear()

    def accept(self,reading,threshold=90,at=None):
        at=time.time() if at is None else at;a,b=reading['current'],reading['target']
        if type(a) is not int or type(b) is not int or not 0<=a<=b<=10_000_000 or not b:return []
        if self.current is not None and (b!=self.target or a<self.current):
            candidate=self.pending
            if self.complete_sent and candidate and candidate[1]==b and candidate[0]<=a and 1<=at-candidate[2]<=60:self.reset()
            else:
                self.pending=(a,b,at);self.pause('Counter decreased or target changed. Confirm the new quest, or use NEXT QUEST.');return []
        self.pending=None;changed=(a,b)!=(self.current,self.target)
        self.current=a;self.target=b;self.label=str(reading.get('label','Alchemy guild mission'))[:120];self.objective=str(reading.get('objective',''))[:160];self.last_at=at
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
        now=time.time() if now is None else now;fresh=self.available and self.last_at is not None and 0<=now-self.last_at<=35
        remaining=self.target-self.current if self.current is not None else None;eta=None
        if fresh and len(self.samples)>=2:
            elapsed=self.samples[-1][0]-self.samples[0][0];gain=self.samples[-1][1]-self.samples[0][1]
            if elapsed>=15 and gain>0:eta=remaining*elapsed/gain
        return {'current':self.current,'target':self.target,'label':self.label,'objective':self.objective,'available':fresh,'last_at':self.last_at,
                'percent':100*self.current/self.target if self.target else 0,'remaining':remaining,'eta':eta,
                'complete':self.complete_sent,'reason':self.reason if fresh or not self.available else 'Last verified progress; waiting for a fresh reading'}
