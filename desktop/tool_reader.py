"""On-demand visible utensil discovery and conservative active-tool evidence.

No region calibration, game input, memory reads or screenshot persistence.
Broad discovery is infrequent; normal reads use a bounded batch of label crops.
"""
from collections import defaultdict
import csv
import io
import math
import re
import time
from threading import local
from PIL import Image,ImageOps
from ocr_parser import extract_pairs
from ocr_runtime import run_ocr

TOOL=re.compile(r'(?:(?:[A-Za-z][A-Za-z\'-]*\s+){0,4})(?:Alchemy\s*Tool|Cooking\s*Utensil)',re.I)
MAX_TOOLS=8
PARTIAL_NAME='Tool · name partly covered'
COUNTER=re.compile(r'(?<![\d,?A-Za-z])(\d[\d,]{0,8})\s*[/|]\s*(\d[\d,]{0,8})(?!\d)')
_budget=local()


def family(name):
    return 'alchemy' if 'alchemy' in name.casefold() else 'cooking' if 'cooking' in name.casefold() else None


def character_anchor(image):
    """Cheap prior from paired in-world red/blue bars; centre is a fallback."""
    width,height=image.size;rgb=image if image.mode=='RGB' else image.convert('RGB');pixels=rgb.load();bars={'red':[],'blue':[]}
    for y in range(int(height*.32),int(height*.76),3):
        for color in bars:
            start=None
            for x in range(int(width*.28),int(width*.72),2):
                r,g,b=pixels[x,y]
                hit=(r>110 and r>g*1.45 and r>b*1.3) if color=='red' else (b>110 and b>r*1.3 and b>g*.85)
                if hit and start is None:start=x
                if start is not None and (not hit or x>=int(width*.72)-2):
                    if 32<=x-start<=240:bars[color].append((start,x,y))
                    start=None
    matches=[]
    for red in bars['red']:
        for blue in bars['blue']:
            if 0<blue[2]-red[2]<=20 and abs(red[0]-blue[0])<18:
                x=(min(red[0],blue[0])+max(red[1],blue[1]))/2;y=(red[2]+blue[2])/2
                matches.append((abs(x-width/2)+abs(y-height*.5)*.3,x,y))
    if matches:
        _,x,y=min(matches);return {'x':x,'y':y,'evidence':'paired character bars'}
    return {'x':width/2,'y':height*.5,'evidence':'screen-centre search prior'}


def words(tsv):
    result=[]
    for row in csv.DictReader(io.StringIO(tsv),delimiter='\t'):
        if row.get('level')!='5' or not row.get('text','').strip():continue
        try:
            left,top,width,height=[int(row[k]) for k in ('left','top','width','height')]
            confidence=float(row.get('conf',-1))
            if width<=0 or height<=0 or not math.isfinite(confidence):continue
        except (KeyError,TypeError,ValueError):continue
        result.append({'text':row['text'].strip(),'x':left,'y':top,'w':width,'h':height,'confidence':confidence})
        if len(result)>=6000:break
    return result


def lines(tokens):
    groups=[]
    for token in sorted(tokens,key=lambda w:(w['y']+w['h']/2,w['x'])):
        center=token['y']+token['h']/2
        group=next((g for g in groups if abs(g['y']-center)<=max(5,token['h']*.5)),None)
        if group is None:group={'y':center,'words':[]};groups.append(group)
        group['words'].append(token)
    result=[]
    for group in groups:
        part=[]
        for token in sorted(group['words'],key=lambda w:w['x']):
            if part and token['x']-(part[-1]['x']+part[-1]['w'])>max(45,token['h']*3):
                result.append(part);part=[]
            part.append(token)
        if part:result.append(part)
    return result


def label_name(text):
    match=TOOL.search(text)
    if not match:return PARTIAL_NAME if re.search(r'\b(?:Tool|Utensil)\s*[({\[]?\s*\d{1,6}\s*[/|]',text,re.I) else None
    name=' '.join(match.group().split())
    name=re.sub(r'Alchemy\s*Tool','Alchemy Tool',name,flags=re.I)
    name=re.sub(r'Cooking\s*Utensil','Cooking Utensil',name,flags=re.I)
    base='Alchemy Tool' if 'alchemy' in name.casefold() else 'Cooking Utensil'
    prefix=name[:-len(base)].strip().casefold().split()
    known={'morning','light','traditional','supreme','advanced','intermediate','basic','balenos','serendia','calpheon','mediah','valencia'}
    return name if all(word in known for word in prefix) else base


def discover_regions(tsv,size,scale=1,anchor=None):
    """Find name-bearing labels, never generic HUD fractions or nearby HP."""
    width,height=size;regions=[]
    for group in lines(words(tsv)):
        text=' '.join(w['text'] for w in group)
        name=label_name(text)
        if not name:continue
        left=max(0,int(min(w['x'] for w in group)/scale)-16)
        top=max(0,int(min(w['y'] for w in group)/scale)-10)
        right=min(width,int(max(w['x']+w['w'] for w in group)/scale)+40)
        bottom=min(height,int(max(w['y']+w['h'] for w in group)/scale)+10)
        if not 15<=bottom-top<=100 or not 50<=right-left<=800:continue
        if any(abs(left-r['box'][0])<20 and abs(top-r['box'][1])<15 for r in regions):continue
        regions.append({'name':name,'box':[left,top,right,bottom]})
    # Overlapping furniture names can erase the prefix while the literal
    # Tool(current/max) tail remains readable. Verify just that tail separately.
    for token in words(tsv):
        if label_name(token['text'])!=PARTIAL_NAME:continue
        center=(token['x']+token['w']/2)/scale;y=(token['y']+token['h']/2)/scale
        if any(r['box'][0]<=center<=r['box'][2] and r['box'][1]<=y<=r['box'][3] for r in regions):continue
        box=[max(0,int(token['x']/scale)-95),max(0,int(token['y']/scale)-8),
             min(width,int((token['x']+token['w'])/scale)+16),min(height,int((token['y']+token['h'])/scale)+8)]
        regions.append({'name':PARTIAL_NAME,'box':box})
    for region in regions:
        numbers=[]
        for token in words(tsv):
            for match in COUNTER.finditer(token['text']):
                current,maximum=[int(v.replace(',','')) for v in match.groups()]
                if not 0<=current<=maximum or not 100<=maximum<=100_000:continue
                x1=(token['x']+token['w']*match.start(1)/len(token['text']))/scale
                x2=(token['x']+token['w']*match.end(2)/len(token['text']))/scale
                y=(token['y']+token['h']/2)/scale
                a,b,c,d=region['box']
                if a<=(x1+x2)/2<=c and b<=y<=d:
                    numbers.append(([max(a,int(x1)-9),max(b,int(token['y']/scale)-6),
                                     min(c,int(x2)+12),min(d,int((token['y']+token['h'])/scale)+7)],(current,maximum)))
        if len(numbers)==1:region['numbers'],region['coarse_pair']=numbers[0]
    if anchor:
        regions.sort(key=lambda r:abs((r['box'][0]+r['box'][2])/2-anchor['x'])+
                     .7*abs((r['box'][1]+r['box'][3])/2-(anchor['y']-140)))
    else:regions.sort(key=lambda r:(r['box'][1],r['box'][0]))
    return regions[:MAX_TOOLS]


def ocr(image,tess,psm,numeric=False):
    blob=io.BytesIO();image.save(blob,format='PNG')
    command=[tess,'stdin','stdout','--psm',str(psm),'-l','eng']
    if numeric:command+=['-c','tessedit_char_whitelist=0123456789/()']
    remaining=getattr(_budget,'deadline',time.monotonic()+5)-time.monotonic()
    if remaining<.15:raise RuntimeError('Tool search reached its time budget; retrying automatically')
    result=run_ocr(command+['tsv'],
                   input=blob.getvalue(),capture_output=True,timeout=min(5,remaining))
    if result.returncode:raise RuntimeError('Tool OCR could not read the frame')
    return result.stdout.decode('utf-8','replace')


def mosaic(crops,ink_threshold=None):
    prepared=[]
    for image in crops:
        if ink_threshold is not None:
            from loot_capture import notification_ink
            gray=notification_ink(image,ink_threshold,False)
        else:gray=ImageOps.autocontrast(ImageOps.grayscale(image))
        factor=min(1 if ink_threshold is not None else 3,1600/max(1,gray.width),180/max(1,gray.height))
        gray=gray.resize((max(1,int(gray.width*factor)),max(1,int(gray.height*factor))))
        prepared.append(gray)
    width=max((im.width for im in prepared),default=1)+24
    height=sum(im.height+24 for im in prepared)
    output=Image.new('L',(width,height),255 if ink_threshold is not None else 0);bands=[];y=0
    for im in prepared:
        output.paste(im,(12,y+12));bands.append((y,y+im.height+24));y=bands[-1][1]
    return output,bands


def read_bands(tsv,bands):
    grouped=defaultdict(list)
    for word in words(tsv):
        center=word['y']+word['h']/2
        index=next((i for i,(top,bottom) in enumerate(bands) if top<=center<bottom),None)
        if index is not None:grouped[index].append(word)
    result={}
    for index,group in grouped.items():
        text=' '.join(' '.join(w['text'] for w in line) for line in lines(group))
        name=label_name(text);pairs={(int(m[1].replace(',','')),int(m[2].replace(',',''))) for m in COUNTER.finditer(text)}
        if name and len(pairs)==1:
            current,maximum=next(iter(pairs))
            if 100<=maximum<=100_000:
                result[index]={'name':name,'current':current,'maximum':maximum,'confidence':sum(w['confidence'] for w in group)/len(group)}
    return result


def verify_labels(crops,regions,tess):
    result=[];pending=[];calls=0
    for index,(crop,region) in enumerate(zip(crops,regions)):
        if not region.get('numbers'):pending.append(index);continue
        a,b,c,d=region['numbers'];left,top,_,_=region['box']
        numeric=crop.crop((a-left,b-top,c-left,d-top))
        gray=ImageOps.autocontrast(ImageOps.grayscale(numeric)).resize((numeric.width*4,numeric.height*4),Image.Resampling.LANCZOS)
        readings=[];confidences=[]
        for variant in (gray,ImageOps.invert(gray)):
            tokens=words(ocr(variant,tess,7,numeric=True));calls+=1
            readings.append(set(extract_pairs(' '.join(w['text'] for w in tokens))))
            confidences.append(sum(w['confidence'] for w in tokens)/max(1,len(tokens)))
        if len(readings[0])==1 and readings[0]==readings[1]:
            current,maximum=next(iter(readings[0]))
            if 0<=current<=maximum and 100<=maximum<=100_000:
                result.append({'name':region['name'],'current':current,'maximum':maximum,'box':region['box'],'confidence':min(confidences),'votes':2})
                continue
        pending.append(index)
    if not pending:return result,calls
    # A bounded text-mask fallback handles labels whose numeric tail was not
    # localized cleanly. Unknown digits never become an implicit shorter value.
    fallback_regions=[regions[i] for i in pending];fallback_crops=[crops[i] for i in pending]
    extra,extra_calls=verify_text_labels(fallback_crops,fallback_regions,tess)
    return result+extra,calls+extra_calls


def verify_text_labels(crops,regions,tess):
    image,bands=mosaic(crops)
    first=read_bands(ocr(image,tess,6),bands)
    second=read_bands(ocr(ImageOps.invert(image),tess,6),bands)
    result=[];missing=[]
    for index,region in enumerate(regions):
        a,b=first.get(index),second.get(index)
        if not a or not b or (a['current'],a['maximum'])!=(b['current'],b['maximum']):missing.append(index);continue
        if a['name'].casefold()!=b['name'].casefold():
            kind=family(a['name'])
            name=('Alchemy Tool' if kind=='alchemy' else 'Cooking Utensil') if kind and kind==family(b['name']) else PARTIAL_NAME
            a={**a,'name':name}
        result.append({**a,'box':region['box'],'votes':2})
    calls=2
    if missing:
        subset=[crops[i] for i in missing]
        mask,bands=mosaic(subset,120);extra_a=read_bands(ocr(mask,tess,6),bands)
        mask,bands=mosaic(subset,140);extra_b=read_bands(ocr(mask,tess,6),bands);calls+=2
        for index,original in enumerate(missing):
            a,b=extra_a.get(index),extra_b.get(index)
            if not a or not b or (a['current'],a['maximum'])!=(b['current'],b['maximum']):continue
            name=a['name'] if a['name'].casefold()==b['name'].casefold() else PARTIAL_NAME
            result.append({**a,'name':name,'box':regions[original]['box'],'votes':2})
    return result,calls


def discover_scene(image,tess):
    """Prefer a higher-resolution narrow band over expensive whole-scene OCR."""
    width,height=image.size;anchor=character_anchor(image);calls=0
    def band(box,reference):
        crop=image.crop(box);scale=min(2,math.sqrt(2_200_000/max(1,crop.width*crop.height)))
        gray=ImageOps.autocontrast(ImageOps.grayscale(crop.resize((max(1,int(crop.width*scale)),max(1,int(crop.height*scale))))))
        raw=ocr(gray,tess,11)
        regions=discover_regions(raw,crop.size,scale,{'x':reference['x']-box[0],'y':reference['y']-box[1]})
        for row in regions:
            a,b,c,d=row['box'];row['box']=[a+box[0],b+box[1],c+box[0],d+box[1]]
            if row.get('numbers'):
                a,b,c,d=row['numbers'];row['numbers']=[a+box[0],b+box[1],c+box[0],d+box[1]]
        return regions
    top=max(0,int(anchor['y']-height*.278));bottom=max(top+1,min(height,int(anchor['y']-height*.046)))
    regions=band((0,top,width,bottom),anchor);calls+=1
    if regions:return regions,anchor,calls
    # A fallback broad pass also locates a movable Place Mode button. It is a
    # search aid only, never evidence that the nearest utensil is active.
    scale=min(1,1920/width,1080/height)
    overview=ImageOps.autocontrast(ImageOps.grayscale(image.resize((max(1,int(width*scale)),max(1,int(height*scale))))))
    raw=ocr(overview,tess,11);calls+=1
    for group in lines(words(raw)):
        if 'place mode' not in ' '.join(w['text'] for w in group).casefold():continue
        place={'x':sum(w['x']+w['w']/2 for w in group)/len(group)/scale,
               'y':sum(w['y']+w['h']/2 for w in group)/len(group)/scale,'evidence':'Place Mode search fallback'}
        top=min(height-1,max(0,int(place['y']+height*.018)))
        bottom=max(top+1,min(height,int(place['y']+height*.26)))
        regions=band((0,top,width,bottom),place);calls+=1
        if regions:return regions,place,calls
    return discover_regions(raw,(width,height),scale,anchor),anchor,calls


class ToolInventory:
    def __init__(self):
        self.tracks={};self.sequence=0;self.context=None

    def update(self,observations,now,context=None):
        if context!=self.context:self.tracks={};self.context=context
        used=set();visible=[]
        for row in observations:
            left,top,right,bottom=row['box'];x=(left+right)/2;y=(top+bottom)/2
            possible=[]
            for ident,old in self.tracks.items():
                if row['maximum']!=old['maximum']:continue
                if family(row['name']) and family(old['name']) and family(row['name'])!=family(old['name']):continue
                distance=math.hypot(x-old['x'],y-old['y'])
                elapsed=now-old['seen_at'];drop=old['current']-row['current']
                # Durability is an identity fingerprint when the camera moves.
                # A large increase is a replacement, not a nearby-label match.
                if not 0<elapsed<=180 or not 0<=drop<=max(4,elapsed*20+4):continue
                pace=sorted(old['pace'])
                expected=old['current']-(elapsed/pace[len(pace)//2] if pace else 0)
                score=min(abs(row['current']-old['current']),abs(row['current']-expected))
                possible.append((score,ident,old,distance))
            possible.sort(key=lambda p:p[0])
            match=possible[0] if possible and possible[0][1] not in used and (len(possible)==1 or possible[1][0]-possible[0][0]>=3) else None
            if match:
                _,ident,old,_=match;elapsed=now-old['seen_at'];drop=old['current']-row['current']
                valid_wear=1<=drop<=max(4,elapsed*20+4) and 1<=elapsed<=180
                streak=old['wear_streak']+1 if valid_wear else old['wear_streak'] if drop==0 and old['idle_reads']==0 else 0
                idle=0 if valid_wear else old['idle_reads']+1
                cycle=old['cycle']+(1 if row['current']>old['current'] else 0)
                pace=(old['pace']+[elapsed/drop])[-5:] if valid_wear else old['pace'] if drop==0 else []
            else:
                self.sequence+=1;ident='tool-'+str(self.sequence);elapsed=0;drop=0;streak=0;idle=0;cycle=0;pace=[]
            used.add(ident)
            track={**row,'id':ident,'x':x,'y':y,'seen_at':now,'wear_streak':streak,'idle_reads':idle,
                   'last_drop':drop,'cycle':cycle,'pace':pace,'percent':round(100*row['current']/row['maximum'],1)}
            self.tracks[ident]=track;visible.append(track)
        self.tracks={k:v for k,v in self.tracks.items() if now-v['seen_at']<=180}
        for ident,track in self.tracks.items():
            if ident not in used:track['wear_streak']=0;track['idle_reads']=2
        moving=[r for r in visible if r['current']>0 and r['wear_streak']>=2 and r['idle_reads']<=1]
        active=moving[0] if len(moving)==1 else None
        tools=[]
        for row in visible:
            state='Active · repeated durability use' if active and row['id']==active['id'] else 'Empty' if row['current']==0 else 'Also changing · uncertain active tool' if row in moving else 'Visible · waiting for use'
            pace=sorted(row['pace'])
            tools.append({k:v for k,v in row.items() if k not in ('pace','x','y')}|{'state':state,'seconds_per_use':pace[len(pace)//2] if len(pace)>=2 else None})
        return {'tools':tools,'active_id':active['id'] if active else None,
                'active_key':f"{active['id']}:{active['cycle']}" if active else None,
                'reason':'Repeated durability decreases identify one tool' if active else 'Several tools are changing; active tool is uncertain' if moving else 'Watching for repeated durability use' if visible else 'No verified visible tool labels',
                'observed_at':now}


class AutomaticToolReader:
    def __init__(self):
        self.regions=[];self.context=None;self.inventory=ToolInventory()
        self.last_discovery=-1e9;self.next_due=0;self.misses=0
        self.anchor=None
        self.quiet_reads=0

    def read(self,tess,bounds,grab,now=None,interval=10):
        _budget.deadline=time.monotonic()+6
        try:return self._read(tess,bounds,grab,now,interval)
        finally:del _budget.deadline

    def _read(self,tess,bounds,grab,now=None,interval=10):
        """bounds=(window_id,left,top,right,bottom); grab is screen-capture adapter."""
        started=time.monotonic();now=started if now is None else now
        hwnd,left,top,right,bottom=bounds;width=right-left;height=bottom-top
        if width<100 or height<100 or width*height>16_000_000:raise ValueError('Unsupported visible game window size')
        context=(hwnd,left,top,width,height)
        if context!=self.context:self.regions=[];self.context=context
        discover=not self.regions or now-self.last_discovery>=30
        calls=0
        if discover:
            image=grab((left,top,right,bottom)).convert('RGB')
            captured_mono=time.monotonic();captured_at=time.time()
            self.regions,self.anchor,used_calls=discover_scene(image,tess);calls+=used_calls
            self.last_discovery=now
            crops=[image.crop(r['box']) for r in self.regions]
            del image
        else:
            captured_mono=time.monotonic();captured_at=time.time()
            crops=[grab((left+r['box'][0],top+r['box'][1],left+r['box'][2],top+r['box'][3])) for r in self.regions]
        observations,used_calls=verify_labels(crops,self.regions,tess) if crops else ([],0)
        calls+=used_calls
        if not discover and len(observations)<len(self.regions):
            # Camera motion invalidates remembered label rectangles. Reacquire
            # this scan rather than waiting for the broad-discovery heartbeat.
            image=grab((left,top,right,bottom)).convert('RGB')
            captured_mono=time.monotonic();captured_at=time.time()
            self.regions,self.anchor,used_calls=discover_scene(image,tess);calls+=used_calls
            crops=[image.crop(r['box']) for r in self.regions]
            observations,used_calls=verify_labels(crops,self.regions,tess) if crops else ([],0)
            calls+=used_calls
            self.last_discovery=now;discover=True
        report=self.inventory.update(observations,now,context)
        self.misses=self.misses+1 if not observations else 0
        self.regions=[r for r in self.regions if any(r['box']==o['box'] for o in observations)]
        if any(row['last_drop']>0 for row in report['tools']) or discover:self.quiet_reads=0
        else:self.quiet_reads+=1
        delay=max(3,min(120,interval)) if report['active_id'] else min(30,3*max(1,self.quiet_reads-2)) if observations else min(120,30*self.misses)
        self.next_due=time.monotonic()+delay
        report.update(duration=time.monotonic()-started,ocr_calls=calls,discovery=discover,
                      next_seconds=delay,visible_limit=MAX_TOOLS,anchor=self.anchor,
                      captured_mono=captured_mono,captured_at=captured_at)
        return report
