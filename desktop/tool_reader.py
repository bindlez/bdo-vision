"""On-demand visible utensil discovery and conservative active-tool evidence.

No region calibration, game input, memory reads or screenshot persistence.
Broad discovery is infrequent; normal reads use a bounded batch of label crops.
"""
from collections import defaultdict
import csv
import io
import math
import re
import subprocess
import time
from threading import local
from difflib import SequenceMatcher
from html.parser import HTMLParser
from PIL import Image,ImageOps,ImageChops,ImageStat
from ocr_parser import extract_pairs
from ocr_runtime import run_ocr

TOOL=re.compile(r'(?:(?:[A-Za-z][A-Za-z\'-]*\s+){0,4})(?:Alchemy\s*Tool|Cooking\s*Utensil)',re.I)
MAX_TOOLS=8
PARTIAL_NAME='Tool · name partly covered'
COUNTER=re.compile(r'(?<![\d,?A-Za-z])(\d[\d,]{0,8})\s*[/|]\s*(\d[\d,]{0,8})(?!\d)')
_budget=local()


class ToolBudgetExpired(RuntimeError):
    pass


def family(name):
    return 'alchemy' if 'alchemy' in name.casefold() else 'cooking' if 'cooking' in name.casefold() else None


def white_glyph_mask(image):
    red,green,blue=image.convert('RGB').split()
    low=ImageChops.darker(ImageChops.darker(red,green),blue)
    high=ImageChops.lighter(ImageChops.lighter(red,green),blue)
    return ImageChops.multiply(low.point(lambda v:255 if v>190 else 0),
                              ImageChops.subtract(high,low).point(lambda v:255 if v<35 else 0))


def label_signature(crop,region):
    """Tiny white-glyph mask of the title, excluding changing numeric digits."""
    width=(region.get('numbers',[region['box'][2]-70])[0]-region['box'][0])-3
    if width<12:return None
    image=crop.crop((0,3,min(crop.width,width),max(4,crop.height-3))).convert('RGB')
    mask=white_glyph_mask(image)
    factor=min(1,256/mask.width,36/mask.height)
    mask=mask.resize((max(1,int(mask.width*factor)),max(1,int(mask.height*factor))),Image.Resampling.NEAREST)
    return mask if ImageStat.Stat(mask).sum[0]>=12*255 else None


def signature_matches(reference,current):
    if reference is None or current is None:return reference is None
    if reference.size!=current.size:return False
    total=ImageStat.Stat(reference).sum[0]
    missing=ImageStat.Stat(ImageChops.subtract(reference,current)).sum[0]
    return missing/max(1,total)<.35


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
    for row in csv.DictReader(io.StringIO(tsv),delimiter='\t',quoting=csv.QUOTE_NONE):
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
    if not match:return PARTIAL_NAME if re.search(r'\b(?:Tool|ool|ol|Utensil)\s*[({\[]?\s*\d{1,6}\s*[/|]',text,re.I) else None
    name=' '.join(match.group().split())
    name=re.sub(r'Alchemy\s*Tool','Alchemy Tool',name,flags=re.I)
    name=re.sub(r'Cooking\s*Utensil','Cooking Utensil',name,flags=re.I)
    base='Alchemy Tool' if 'alchemy' in name.casefold() else 'Cooking Utensil'
    prefix=name[:-len(base)].strip().casefold().split()
    known={'morning','light','traditional','supreme','advanced','intermediate','basic','balenos','serendia','calpheon','mediah','valencia'}
    return name if all(word in known for word in prefix) else base


def discover_regions(tsv,size,scale=1,anchor=None):
    """Find name-bearing labels, never generic HUD fractions or nearby HP."""
    width,height=size;regions=[];tokens=words(tsv);groups=lines(tokens)
    for group in groups:
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
    for token in tokens:
        if label_name(token['text'])!=PARTIAL_NAME:continue
        center=(token['x']+token['w']/2)/scale;y=(token['y']+token['h']/2)/scale
        if any(r['box'][0]<=center<=r['box'][2] and r['box'][1]<=y<=r['box'][3] for r in regions):continue
        box=[max(0,int(token['x']/scale)-95),max(0,int(token['y']/scale)-8),
             min(width,int((token['x']+token['w'])/scale)+16),min(height,int((token['y']+token['h'])/scale)+8)]
        regions.append({'name':PARTIAL_NAME,'box':box})
    for region in regions:
        numbers=[]
        a,b,c,d=region['box']
        for group in groups:
            text=' '.join(w['text'] for w in group)
            y=(min(w['y'] for w in group)+max(w['y']+w['h'] for w in group))/2/scale
            if not b<=y<=d:continue
            def position(index):
                offset=0
                for token in group:
                    if offset<=index<=offset+len(token['text']):
                        return (token['x']+token['w']*(index-offset)/max(1,len(token['text'])))/scale
                    offset+=len(token['text'])+1
                return (group[-1]['x']+group[-1]['w'])/scale
            for match in COUNTER.finditer(text):
                current,maximum=[int(v.replace(',','')) for v in match.groups()]
                if not 0<=current<=maximum or not 100<=maximum<=100_000:continue
                x1=position(match.start(1));x2=position(match.end(2))
                if a<=(x1+x2)/2<=c and b<=y<=d:
                    numbers.append(([max(a,int(x1)-12),max(b,int(min(w['y'] for w in group)/scale)-6),
                                     min(c,int(x2)+14),min(d,int(max(w['y']+w['h'] for w in group)/scale)+7)],(current,maximum)))
        if len(numbers)==1:region['numbers'],region['coarse_pair']=numbers[0]
    if anchor:
        regions.sort(key=lambda r:abs((r['box'][0]+r['box'][2])/2-anchor['x'])+
                     .7*abs((r['box'][1]+r['box'][3])/2-(anchor['y']-140)))
    else:regions.sort(key=lambda r:(r['box'][1],r['box'][0]))
    return regions[:MAX_TOOLS]


def ocr(image,tess,psm,numeric=False,characters=False):
    blob=io.BytesIO();image.save(blob,format='PNG')
    command=[tess,'stdin','stdout','--psm',str(psm),'-l','eng']
    if numeric:command+=['-c','tessedit_char_whitelist=0123456789/()']
    remaining=getattr(_budget,'deadline',time.monotonic()+5)-time.monotonic()
    if remaining<.15:raise ToolBudgetExpired('Tool search reached its time budget; retrying automatically')
    output=['-c','hocr_char_boxes=1','hocr'] if characters else ['tsv']
    result=run_ocr(command+output,
                   input=blob.getvalue(),capture_output=True,timeout=min(5,remaining))
    if result.returncode:raise RuntimeError('Tool OCR could not read the frame')
    text=result.stdout.decode('utf-8','replace')
    trace=getattr(_budget,'trace',None)
    if trace is not None and len(trace)<16:
        if characters:
            parser=CharacterBoxes();parser.feed(text);display=''.join(char for char,_ in parser.chars)+'\nExact glyph boxes: '+str(len(parser.chars))
        else:display=str([(w['text'],w['confidence'],w['x'],w['y']) for w in words(text)])
        trace.append(f'PSM {psm} numeric={numeric}\n'+display[:6000])
    return text


class CharacterBoxes(HTMLParser):
    """Exact glyph locations avoid estimating digits inside a merged OCR word."""
    def __init__(self):super().__init__();self.box=None;self.chars=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if 'ocrx_cinfo' in attrs.get('class',''):
            match=re.search(r'x_bboxes (\d+) (\d+) (\d+) (\d+)',attrs.get('title',''))
            self.box=list(map(int,match.groups())) if match else None
    def handle_data(self,data):
        if self.box is not None and data:
            self.chars.extend((char,self.box) for char in data);self.box=None


def durability_bars(image):
    """Cheap gold-line candidates; OCR still has to prove a tool and a fraction."""
    width,height=image.size
    small=image.resize((max(1,width//2),max(1,height//2)),Image.Resampling.NEAREST).convert('RGB')
    red,green,blue=small.split()
    mask=ImageChops.multiply(ImageChops.multiply(red.point(lambda p:255 if p>170 else 0),
        green.point(lambda p:255 if p>140 else 0)),blue.point(lambda p:255 if p<160 else 0))
    data=mask.tobytes();sw,sh=small.size;groups=[];pattern=re.compile(b'\xff{4,110}')
    start=int(sw*.12);end=int(sw*.87)
    for y in range(int(sh*.12),int(sh*.66)):
        for hit in pattern.finditer(data[y*sw+start:y*sw+end]):
            a=start+hit.start();b=start+hit.end()
            previous=next((g for g in reversed(groups) if 0<=y-g[3]<=1 and abs((a+b-g[0]-g[2])/2)<6),None)
            if previous:previous[0]=min(previous[0],a);previous[2]=max(previous[2],b);previous[3]=y+1
            elif len(groups)<96:groups.append([a,y,b,y+1])
    candidates=[[a*2,b*2,c*2,d*2] for a,b,c,d in groups if 1<=d-b<=3]
    candidates.sort(key=lambda b:abs((b[0]+b[2])/2-width*.5)+abs(b[1]-height*.28)*.5)
    pixels=image.load();unit=max(.6,min(2.,height/1080));bars=[]
    for a,b,c,d in candidates[:32]:
        middle=(a+c)//2;tracks=[]
        for y in (b-1,b-2,d+1,d):
            if not 0<=y<height or max(pixels[middle,y][:3])>=175:continue
            cutoff=min(175,max(60,max(pixels[middle,y][:3])+25))
            left=right=middle
            while left>max(0,middle-int(210*unit)) and max(pixels[left-1,y][:3])<cutoff:left-=1
            while right<min(width-1,middle+int(210*unit)) and max(pixels[right+1,y][:3])<cutoff:right+=1
            if 50*unit<=right-left<=180*unit and left<=a+4 and right>=c-4:tracks.append((abs((right-left)-100*unit),left,right))
        if not tracks:
            if c-a<60*unit:continue
            left,right=a,c
        else:_,left,right=min(tracks)
        if any(abs(left-r['box'][0])<10 and abs(b-r['box'][1])<8 for r in bars):continue
        # A bright/transparent track can stop the dark-run search halfway.
        # Such a fragment still locates text, but cannot veto its numeric value.
        trusted=bool(tracks and right-left>=75*max(1.,unit))
        bars.append({'box':[left,b,right,d],'fill':min(1.,(c-a)/max(1,right-left)) if trusted else None})
    return bars[:MAX_TOOLS]


def anchored_title_family(text):
    """Name-only fallback for a Place Mode + visible durability-bar locator.

    Never repair or guess digits. A damaged title can identify a generic family;
    two literal numeric reads and bar consistency still have to verify its value.
    """
    # A decorative icon can be recognized as a leading digit. It must not
    # truncate the real name before we even reach the utensil title.
    title=re.sub(r'^[^A-Za-z]+','',text)
    prefix=re.split(r'[({]|\d',title,maxsplit=1)[0]
    letters=re.sub('[^a-z]','',prefix.casefold())[-45:]
    if re.search(r'alchem[yv]i?[tl]o[oc]l$',letters):return 'Alchemy Tool'
    for target,name in (('alchemytool','Alchemy Tool'),('cookingutensil','Cooking Utensil')):
        for length in range(len(target)-1,len(target)+3):
            if len(letters)>=length and SequenceMatcher(None,letters[-length:],target,autojunk=False).ratio()>=.82:
                return name
    return None


def discover_bar_labels(image,tess,known=(),anchor=None):
    width,height=image.size;unit=max(.6,min(2.,height/1080));regions=[];calls=0
    bars=durability_bars(image)
    if anchor:
        bars=[bar for bar in bars if abs((bar['box'][0]+bar['box'][2])/2-anchor['x'])<=340*unit and -65*unit<=bar['box'][1]-anchor['y']<=150*unit]
        bars.sort(key=lambda bar:abs((bar['box'][0]+bar['box'][2])/2-anchor['x'])+.8*abs(bar['box'][1]-anchor['y']-60*unit))
        bars=bars[:3]
    for bar in bars:
        left,top,right,bottom=bar['box']
        center=(left+right)/2
        if any(r.get('locator')=='durability bar' and r.get('numbers') and r['box'][0]<=center<=r['box'][2] and r['box'][1]<=top-10*unit<=r['box'][3] for r in known):continue
        box=[max(0,int(left-190*unit)),max(0,int(top-26*unit)),min(width,int(left+310*unit)),max(1,int(top-6*unit))]
        crop=image.crop(box)
        if crop.height<8:continue
        # Gold furniture trim also looks like a durability bar. A readable
        # tool title must contain the same white glyphs used by motion checks;
        # skip blank/color-only candidates before launching another OCR worker.
        if white_glyph_mask(crop).histogram()[255]<12:continue
        prepared=ImageOps.autocontrast(crop.convert('L')).resize((crop.width*3,crop.height*3),Image.Resampling.LANCZOS)
        parser=CharacterBoxes();parser.feed(ocr(prepared,tess,7,characters=True));calls+=1
        text=''.join(char for char,_ in parser.chars)
        if re.search(r'(?:Tool|Utensil)\(\d{4,}\)',text,re.I):
            box[0]+=1;box[2]=min(width,box[2]+1);crop=image.crop(box)
            prepared=ImageOps.autocontrast(crop.convert('L')).resize((crop.width*3,crop.height*3),Image.Resampling.BICUBIC)
            parser=CharacterBoxes();parser.feed(ocr(prepared,tess,7,characters=True));calls+=1
            text=''.join(char for char,_ in parser.chars)
        kind='Alchemy Tool' if re.search(r'alc[hkn]emy',text,re.I) else 'Cooking Utensil' if re.search(r'cookin[gqc]',text,re.I) else None
        partial_family=anchored_title_family(text) if anchor and kind is None else None
        if partial_family:kind=partial_family
        name=label_name(text)
        if not kind and name!=PARTIAL_NAME and 'traditional' not in text.casefold():continue
        candidates=list(re.finditer(r'[(\{][^(){}]{3,24}[)\}]',text))
        if not candidates:candidates=list(re.finditer(r'[\dOIlS?][\dOIlS?,.:]{0,12}[/|][\dOIlS?,.:]{1,12}',text))
        if not candidates and anchor and kind:
            # A damaged slash/open bracket is a location hint only. Crop the
            # complete tail and require fresh literal numeric consensus below;
            # never turn these corrupted characters into a durability value.
            candidates=list(re.finditer(r'\d[\dA-Za-z?,.:/|]{3,22}[)}]',text))
        for match in candidates:
            boxes=[b for _,b in parser.chars[match.start():match.end()]]
            if not boxes or sum(c.isdigit() for c in match.group())<3:continue
            a=min(b[0] for b in boxes)/3+box[0];b=max(b[2] for b in boxes)/3+box[0]
            primary=left+20*unit<=(a+b)/2<=left+300*unit
            prefix=text[max(0,match.start()-60):match.start()]
            if not primary and not re.search(r'(?:Tool|Utensil)$',prefix,re.I):continue
            numeric=[max(box[0],int(a-16*unit)),box[1],min(box[2],int(b+10*unit)),box[3]]
            strict=re.fullmatch(r'[({]?(\d[\d,]*)\s*[/|]\s*(\d[\d,]*)[)}]?',match.group())
            region={'name':name if name and name!=PARTIAL_NAME else kind or PARTIAL_NAME,'box':box,'numbers':numeric,'locator':'durability bar'}
            if anchor and primary and bar['fill'] is not None:
                region['bar_geometry']=[left,top,right,bottom]
                region['box']=[*box[:3],min(height,max(box[3],bottom+3))]
            if partial_family:region['title_evidence']='Family read from partial title near Place Mode'
            if primary:region['bar_fill']=bar['fill']
            else:region['name']=label_name(prefix) or PARTIAL_NAME
            if strict:region['bar_pair']=tuple(int(n.replace(',','')) for n in strict.groups())
            damaged=re.fullmatch(r'[({](\d[\d,]*)[^\w\s](\d[\d,]*)[)}]',match.group()) if not strict else None
            if not primary and not strict and not damaged and not re.search(r'[/|]',match.group()):continue
            if damaged:
                # A damaged separator is geometry only. Recognize each digit
                # field independently; never turn an unknown glyph into '/'.
                region['bar_pair']=tuple(int(n.replace(',','')) for n in damaged.groups())
                region['digit_boxes']=[]
                for part in (1,2):
                    glyphs=[b for _,b in parser.chars[match.start()+damaged.start(part):match.start()+damaged.end(part)]]
                    region['digit_boxes'].append([int(min(g[0] for g in glyphs)/3+box[0]),box[1]+2,
                        int(max(g[2] for g in glyphs)/3+box[0]),box[3]])
            if not any(abs((r['numbers'][0]+r['numbers'][2]-numeric[0]-numeric[2])/2)<16 and abs(r['box'][1]-box[1])<8 for r in regions):regions.append(region)
    return regions[:MAX_TOOLS],calls


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


def counter_context_error(current,maximum,region):
    if region.get('os_pair') is not None and tuple(region['os_pair'])!=(current,maximum):
        return 'Independent Windows OCR and literal numeric verification disagree'
    coarse=region.get('coarse_pair')
    if coarse and coarse[0]==0 and current!=0:
        return 'Numeric crop conflicts with the full-label empty tool counter'
    if coarse and (coarse[1]!=maximum or abs(coarse[0]-current)>max(4,maximum*.015)):
        return f'Numeric {current}/{maximum} conflicts with full-label {coarse[0]}/{coarse[1]}'
    if region.get('bar_pair') is not None and tuple(region['bar_pair'])!=(current,maximum):
        return 'Numeric crop conflicts with the independently located label counter'
    if maximum and region.get('bar_fill') is not None and abs(current/maximum-region['bar_fill'])>.04:
        return f'Numeric {current}/{maximum} conflicts with bar fill {region["bar_fill"]:.1%}'
    return ''


def unreadable_regions(regions,observations):
    result=[]
    for region in regions:
        if any(region['box']==o['box'] for o in observations):continue
        # The broad pass may also locate a clipped tail inside an independently
        # verified counter. It is a second locator for that field, not a missed
        # neighboring utensil. Keep genuinely separate unresolved labels.
        if region['name']==PARTIAL_NAME and not region.get('numbers'):
            a,b,c,d=region['box'];x=(a+c)/2;y=(b+d)/2
            if any(o.get('numbers') and o['numbers'][0]<=x<=o['numbers'][2] and o['numbers'][1]<=y<=o['numbers'][3] for o in observations):continue
        result.append({k:region[k] for k in ('name','box','rejection','coarse_pair','bar_fill') if k in region})
    return result


def current_bar_fill(crop,region):
    """Refresh cheap bar evidence from this capture; never reuse an old fill."""
    geometry=region.get('bar_geometry')
    if not geometry:return None
    left,top=region['box'][:2];a,b,c,d=geometry
    if not (0<=a-left<c-left<=crop.width and 0<=b-top<d-top<=crop.height):return None
    red,green,blue=crop.crop((a-left,b-top,c-left,d-top)).convert('RGB').split()
    mask=ImageChops.multiply(ImageChops.multiply(red.point(lambda p:255 if p>170 else 0),green.point(lambda p:255 if p>140 else 0)),blue.point(lambda p:255 if p<160 else 0))
    return max(mask.crop((0,y,mask.width,y+1)).histogram()[255] for y in range(mask.height))/mask.width


def verify_labels(crops,regions,tess,cache=None):
    result=[];calls=0
    for crop,region in zip(crops,regions):
        try:
            rows,used=_verify_labels([crop],[region],tess,cache)
        except (ToolBudgetExpired,subprocess.TimeoutExpired):
            region['rejection']='Read budget exhausted; retrying'
            break
        result.extend(rows);calls+=used
    return result,calls


def _verify_labels(crops,regions,tess,cache):
    import hashlib
    result=[];calls=0
    for crop,region in zip(crops,regions):
        fill=current_bar_fill(crop,region)
        if fill is not None:region['bar_fill']=fill
        region['rejection']='No numeric field located'
        if not region.get('numbers'):continue
        region['rejection']='Numeric passes did not agree on one complete current / maximum pair'
        original=region['numbers'];left,top,_,_=region['box']
        windows=[original]
        if region.get('locator')=='durability bar' and not region.get('digit_boxes'):windows.append([max(left,original[0]-3),*original[1:]])
        for window in windows:
            a,b,c,d=window;numeric=crop.crop((a-left,b-top,c-left,d-top))
            if numeric.width<8 or numeric.height<5:continue
            key=(tess,tuple(window),hashlib.sha256(numeric.tobytes()).digest())
            cached=cache.get(key) if cache is not None else None
            if cached and time.monotonic()-cached[0]<8 and not counter_context_error(cached[1]['current'],cached[1]['maximum'],region):
                result.append({**cached[1],'name':region['name'],'box':region['box'],'cache_hit':True});region['numbers']=window;region.pop('bar_pair',None);region.pop('bar_fill',None);region.pop('coarse_pair',None);region.pop('rejection',None);break
            gray=ImageOps.autocontrast(ImageOps.grayscale(numeric)).resize((numeric.width*4,numeric.height*4),Image.Resampling.LANCZOS)
            readings=[];confidences=[];context_region=region;recovered=False;alternate_mode=None
            if region.get('digit_boxes'):
                fields=[]
                for x1,y1,x2,y2 in region['digit_boxes']:
                    field=ImageOps.autocontrast(crop.crop((x1-left,y1-top,x2-left,y2-top)).convert('L'))
                    field=field.resize((field.width*4,field.height*4),Image.Resampling.LANCZOS)
                    values=[]
                    for variant in (field,ImageOps.invert(field)):
                        tokens=words(ocr(variant,tess,7,numeric=True));calls+=1
                        literal=''.join(w['text'] for w in tokens)
                        values.append(int(literal) if re.fullmatch(r'\d{1,6}',literal) else None)
                    fields.append(values[0] if values[0] is not None and values[0]==values[1] else None)
                if all(value is not None for value in fields):readings=[{tuple(fields)}]*2;confidences=[0,0]
                elif region.get('bar_fill') is not None:
                    # A damaged slash can be included in a digit box (e.g.
                    # "4/5000"). Read the complete literal field from white
                    # glyphs twice; never remove/replace a digit to repair it.
                    mask=white_glyph_mask(numeric).resize((numeric.width*4,numeric.height*4),Image.Resampling.LANCZOS)
                    for variant in (mask,ImageOps.invert(mask)):
                        tokens=words(ocr(variant,tess,7,numeric=True));calls+=1
                        readings.append(set(extract_pairs(' '.join(w['text'] for w in tokens))))
                        confidences.append(sum(w['confidence'] for w in tokens)/max(1,len(tokens)))
                    # The malformed HOCR pair only located the failed split.
                    # The fresh bar fill still independently checks magnitude.
                    context_region={k:v for k,v in region.items() if k!='bar_pair'}
                    recovered=True
                else:continue
            else:
                base=(white_glyph_mask(numeric).resize((numeric.width*4,numeric.height*4),Image.Resampling.LANCZOS)
                      if region.get('white_numeric') else gray)
                for variant in (base,ImageOps.invert(base)):
                    tokens=words(ocr(variant,tess,7,numeric=True));calls+=1
                    readings.append(set(extract_pairs(' '.join(w['text'] for w in tokens))))
                    confidences.append(sum(w['confidence'] for w in tokens)/max(1,len(tokens)))
            agreed=len(readings)==2 and len(readings[0])==1 and readings[0]==readings[1]
            valid=agreed and not counter_context_error(*next(iter(readings[0])),context_region)
            if not valid and region.get('bar_geometry') and not region.get('digit_boxes'):
                # Bright walls and animated backgrounds can change which mask
                # preserves a glyph. Retry the complete field, never its digits.
                use_white=not region.get('white_numeric',False)
                alternative=white_glyph_mask(numeric).resize((numeric.width*4,numeric.height*4),Image.Resampling.LANCZOS) if use_white else gray
                retries=[];scores=[]
                for variant in (alternative,ImageOps.invert(alternative)):
                    tokens=words(ocr(variant,tess,7,numeric=True));calls+=1
                    retries.append(set(extract_pairs(' '.join(w['text'] for w in tokens))));scores.append(sum(w['confidence'] for w in tokens)/max(1,len(tokens)))
                if len(retries[0])==1 and retries[0]==retries[1] and not counter_context_error(*next(iter(retries[0])),context_region):
                    readings=retries;confidences=scores;alternate_mode=use_white
            if len(readings[0])==1 and readings[0]==readings[1]:
                current,maximum=next(iter(readings[0]))
                error=counter_context_error(current,maximum,context_region)
                if error:region['rejection']=error;continue
                if 0<=current<=maximum and 100<=maximum<=100_000:
                    result.append({'name':region['name'],'current':current,'maximum':maximum,'box':region['box'],'numbers':window,'confidence':min(confidences),'votes':2})
                    if region.get('title_evidence'):result[-1]['name_evidence']=region['title_evidence']
                    if recovered:result[-1]['numeric_recovery']='Two complete white-glyph reads; bar-fill agreement'
                    # Per-digit glyph boxes belong to one captured font shape.
                    # Reusing them after digits change can clip 2491 into 241.
                    if recovered or region.get('digit_boxes'):region.pop('digit_boxes',None);region['white_numeric']=True
                    if alternate_mode is not None:region['white_numeric']=alternate_mode;result[-1]['numeric_recovery']='Two complete contrast reads; current bar agrees'
                    region['numbers']=window
                    region.pop('bar_pair',None)
                    region.pop('bar_fill',None)
                    region.pop('coarse_pair',None)
                    region.pop('rejection',None)
                    if cache is not None:
                        if len(cache)>=16:cache.pop(next(iter(cache)))
                        cache[key]=(time.monotonic(),dict(result[-1]))
                    break
    return result,calls


def discover_scene(image,tess,focused=True):
    """Prefer a higher-resolution narrow band over expensive whole-scene OCR."""
    width,height=image.size;anchor=character_anchor(image);calls=0
    def band(box,reference,white=False):
        nonlocal calls
        crop=image.crop(box);scale=min(2,math.sqrt(2_200_000/max(1,crop.width*crop.height)))
        gray=ImageOps.invert(white_glyph_mask(crop)) if white else ImageOps.autocontrast(ImageOps.grayscale(crop))
        gray=gray.resize((max(1,int(crop.width*scale)),max(1,int(crop.height*scale))))
        raw=ocr(gray,tess,11)
        calls+=1
        regions=discover_regions(raw,crop.size,scale,{'x':reference['x']-box[0],'y':reference['y']-box[1]})
        for row in regions:
            if white:row['white_numeric']=True
            a,b,c,d=row['box'];row['box']=[a+box[0],b+box[1],c+box[0],d+box[1]]
            if row.get('numbers'):
                a,b,c,d=row['numbers'];row['numbers']=[a+box[0],b+box[1],c+box[0],d+box[1]]
        return regions
    # Residence controls stay legible when furniture names move above the
    # character-centred band. Read this small header before searching labels.
    header_box=(int(width*.28),int(height*.08),int(width*.66),int(height*.25))
    header=image.crop(header_box);header_scale=1.5
    header=ImageOps.autocontrast(header.convert('L')).resize((int(header.width*header_scale),int(header.height*header_scale)))
    header_raw=ocr(header,tess,11);calls+=1;place=None
    def header_anchor(raw,scale):
        for group in lines(words(raw)):
            if 'placemode' not in re.sub(r'\W','',' '.join(w['text'] for w in group)).casefold():continue
            group=[w for w in group if re.search(r'place|mode',w['text'],re.I)] or group
            return {'x':sum(w['x']+w['w']/2 for w in group)/len(group)/scale+header_box[0],
                    'y':sum(w['y']+w['h']/2 for w in group)/len(group)/scale+header_box[1],
                    'evidence':'Place Mode anchor'}
    place=header_anchor(header_raw,header_scale)
    if place is None:
        # Stone walls can swamp grayscale. Retry only the small residence header;
        # successful ordinary discovery pays no additional OCR cost.
        mask=white_glyph_mask(image.crop(header_box))
        if ImageStat.Stat(mask).sum[0]>=12*255:
            header=ImageOps.invert(mask).resize((mask.width*2,mask.height*2))
            place=header_anchor(ocr(header,tess,11),2);calls+=1
    if place and focused:
        # The current utensil is the latency-critical result. Start with at most
        # three nearby bars and their tiny labels before a screen-wide OCR band.
        fast,used_calls=discover_bar_labels(image,tess,anchor=place);calls+=used_calls
        if fast:return fast,{**place,'evidence':'Place Mode anchor + focused durability bar'},calls
    # Camera tilt can put the active label just above the residence control.
    top=max(0,int(place['y']-height*.065)) if place else max(0,int(anchor['y']-height*.278))
    if place is None:
        # A moved residence control may sit outside the cheap central header.
        # Search only the upper client strip, not an additional full frame.
        strip=image.crop((0,0,width,int(height*.32)))
        scale=min(1.,math.sqrt(900000/max(1,strip.width*strip.height)))
        strip=ImageOps.autocontrast(strip.convert('L')).resize((max(1,int(strip.width*scale)),max(1,int(strip.height*scale))))
        raw=ocr(strip,tess,11);calls+=1
        for group in lines(words(raw)):
            if 'placemode' not in re.sub(r'\W','',' '.join(w['text'] for w in group)).casefold():continue
            group=[w for w in group if re.search(r'place|mode',w['text'],re.I)] or group
            place={'x':sum(w['x']+w['w']/2 for w in group)/len(group)/scale,
                   'y':sum(w['y']+w['h']/2 for w in group)/len(group)/scale,'evidence':'Place Mode expanded header'}
            top=max(0,int(place['y']-height*.065));break
    bottom=min(height,int(place['y']+height*.24)) if place else max(top+1,min(height,int(anchor['y']-height*.046)))
    if place:anchor=place
    regions=band((0,top,width,bottom),anchor)
    if place and not any(r.get('numbers') for r in regions) and ImageStat.Stat(white_glyph_mask(image.crop((0,top,width,bottom)))).sum[0]>=12*255:
        fallback=band((0,top,width,bottom),anchor,white=True)
        if any(r.get('numbers') for r in fallback):regions=fallback
    bar_regions,used_calls=discover_bar_labels(image,tess,regions);calls+=used_calls
    if not bar_regions and not any(r.get('numbers') for r in regions):
        wide_top=max(0,int(anchor['y']-height*.36))
        wider=band((0,wide_top,width,bottom),anchor)
        if any(r.get('numbers') for r in wider):regions=wider
    if regions or bar_regions:return (regions+bar_regions)[:MAX_TOOLS],{**anchor,'evidence':('Place Mode anchor + durability bars' if place else 'visible durability bars + label band') if bar_regions else anchor['evidence']},calls
    # A fallback broad pass also locates a movable Place Mode button. It is a
    # search aid only, never evidence that the nearest utensil is active.
    scale=min(1,1920/width,1080/height)
    overview=ImageOps.autocontrast(ImageOps.grayscale(image.resize((max(1,int(width*scale)),max(1,int(height*scale))))))
    raw=ocr(overview,tess,11);calls+=1
    for group in lines(words(raw)):
        if 'place mode' not in ' '.join(w['text'] for w in group).casefold():continue
        place={'x':sum(w['x']+w['w']/2 for w in group)/len(group)/scale,
               'y':sum(w['y']+w['h']/2 for w in group)/len(group)/scale,'evidence':'Place Mode search fallback'}
        top=min(height-1,max(0,int(place['y']-height*.065)))
        bottom=max(top+1,min(height,int(place['y']+height*.26)))
        regions=band((0,top,width,bottom),place)
        if regions:return regions,place,calls
    return discover_regions(raw,(width,height),scale,anchor),anchor,calls


def distinct_counters(observations):
    """Merge locators for the same field; conflicting values remain unreadable."""
    groups=[]
    for row in observations:
        box=row.get('numbers')
        if not box:groups.append([row]);continue
        group=next((g for g in groups if g[0].get('numbers') and
            abs(sum(g[0]['numbers'][::2])-sum(box[::2]))<80 and
            abs(sum(g[0]['numbers'][1::2])-sum(box[1::2]))<32),None)
        if group is None:groups.append([row])
        else:group.append(row)
    return [g[0] for g in groups if len({(r['current'],r['maximum']) for r in g})==1]


def changing_fields(before,after,elapsed,*,max_elapsed=2.25):
    """Return changed fields only when every located field is verified."""
    if not 1.25<=elapsed<=max_elapsed or not before or len(before)!=len(after):return []
    candidates=[]
    for a,b in zip(before,after):
        if not a.get('numbers') or a.get('numbers')!=b.get('numbers') or a['maximum']!=b['maximum']:return []
        if min(a.get('votes',0),b.get('votes',0))<2:return []
        if family(a['name']) and family(b['name']) and family(a['name'])!=family(b['name']):return []
        drop=a['current']-b['current']
        if drop<0 or drop>elapsed*20+4:return []
        if drop and b['current']>0:candidates.append(tuple(b['numbers']))
    return candidates


def changing_tool(before,after,elapsed):
    candidates=changing_fields(before,after,elapsed)
    return candidates[0] if len(candidates)==1 else None


def place_selected(report,height,*,uncontested=False):
    if report.get('ambiguous_use'):return None
    anchor=report.get('anchor') or {}
    if 'Place Mode' not in anchor.get('evidence',''):return None
    unit=max(.6,min(2.,height/1080));ranked=[]
    for row in report.get('tools',[]):
        if row.get('votes',0)<2 or row['current']<=0:continue
        box=row.get('numbers') or row['box'];x=(box[0]+box[2])/2;y=(box[1]+box[3])/2
        if not anchor['y']-60*unit<=y<=anchor['y']+280*unit:continue
        score=abs(x-anchor['x']-40*unit)+.6*abs(y-anchor['y']-55*unit)
        if score<=350*unit:ranked.append((score,row))
    ranked.sort(key=lambda r:r[0])
    if not ranked or len(ranked)>1 and (uncontested or ranked[1][0]-ranked[0][0]<8*unit):return None
    return ranked[0][1]


class ToolInventory:
    def __init__(self):
        self.tracks={};self.sequence=0;self.context=None

    def update(self,observations,now,context=None,confirmed_field=None):
        if context!=self.context:self.tracks={};self.context=context
        for old in self.tracks.values():old['missing']=old.get('missing',0)+1
        used=set();visible=[]
        for row in observations:
            left,top,right,bottom=row['box'];x=(left+right)/2;y=(top+bottom)/2
            possible=[]
            for ident,old in self.tracks.items():
                if old.get('missing',0)>2:continue
                if row['maximum']!=old['maximum']:continue
                if family(row['name']) and family(old['name']) and family(row['name'])!=family(old['name']):continue
                distance=math.hypot(x-old['x'],y-old['y'])
                elapsed=now-old['seen_at'];drop=old['current']-row['current']
                # Durability is an identity fingerprint when the camera moves.
                # A large increase is a replacement, not a nearby-label match.
                if not 0<elapsed<=180 or not 0<=drop<=max(4,elapsed*20+4):continue
                pace=sorted(old['pace'])
                expected=old['current']-(elapsed/pace[len(pace)//2] if pace else 0)
                score=min(abs(row['current']-old['current']),abs(row['current']-expected))+max(0,old.get('missing',1)-1)*5
                possible.append((score,ident,old,distance))
            possible.sort(key=lambda p:p[0])
            match=possible[0] if possible and possible[0][1] not in used and (len(possible)==1 or possible[1][0]-possible[0][0]>=3) else None
            if confirmed_field and tuple(row.get('numbers',()))==confirmed_field:
                same_field=[p for p in possible if p[1] not in used and tuple(p[2].get('numbers',()))==confirmed_field]
                if len(same_field)==1:match=same_field[0]
            if match is None:
                stationary=[p for p in possible if p[1] not in used and p[2]['current']==row['current'] and p[2]['wear_streak']==0]
                stationary.sort(key=lambda p:p[3])
                if stationary and stationary[0][3]<32 and (len(stationary)==1 or stationary[1][3]-stationary[0][3]>32):match=stationary[0]
            if match:
                _,ident,old,_=match;elapsed=now-old['seen_at'];drop=old['current']-row['current']
                valid_wear=1<=drop<=max(4,elapsed*20+4) and 1<=elapsed<=180
                streak=old['wear_streak']+1 if valid_wear else old['wear_streak'] if drop==0 and old['idle_reads']==0 else 0
                idle=0 if valid_wear else old['idle_reads']+1
                cycle=old['cycle']+(1 if row['current']>old['current'] else 0)
                changed=now if valid_wear or drop!=0 else old.get('changed_at',old['seen_at'])
                pace=(old['pace']+[(now-old.get('changed_at',old['seen_at']))/drop])[-5:] if valid_wear and old['idle_reads']<2 else old['pace'] if drop==0 else []
                if valid_wear and confirmed_field and tuple(row.get('numbers',()))==confirmed_field:streak=max(2,streak)
            else:
                self.sequence+=1;ident='tool-'+str(self.sequence);elapsed=0;drop=0;streak=0;idle=0;cycle=0;pace=[];changed=now
                if confirmed_field and tuple(row.get('numbers',()))==confirmed_field:streak=2
            used.add(ident)
            track={**row,'id':ident,'x':x,'y':y,'seen_at':now,'wear_streak':streak,'idle_reads':idle,
                   'last_drop':drop,'cycle':cycle,'pace':pace,'changed_at':changed,'missing':0,'percent':round(100*row['current']/row['maximum'],1)}
            self.tracks[ident]=track;visible.append(track)
        self.tracks={k:v for k,v in self.tracks.items() if now-v['seen_at']<=180 and v['missing']<=2}
        for ident,track in self.tracks.items():
            if ident not in used and track['missing']>=2:track['wear_streak']=0;track['idle_reads']=2
        moving=[r for r in visible if r['current']>0 and r['wear_streak']>=2 and r['idle_reads']<=1]
        active=moving[0] if len(moving)==1 else None
        tools=[]
        for row in visible:
            state='Active · repeated durability use' if active and row['id']==active['id'] else 'Empty' if row['current']==0 else 'Also changing · uncertain active tool' if row in moving else 'Visible · waiting for use'
            pace=sorted(row['pace'])
            tools.append({k:v for k,v in row.items() if k not in ('pace','x','y')}|{'state':state,'seconds_per_use':pace[len(pace)//2] if len(pace)>=2 else None})
        return {'tools':tools,'active_id':active['id'] if active else None,
                'active_key':f"{active['id']}:{active['cycle']}" if active else None,
                'ambiguous_use':len(moving)>1,
                'reason':'Repeated durability decreases identify one tool' if active else 'Several tools are changing; active tool is uncertain' if moving else 'Watching for repeated durability use' if visible else 'No verified visible tool labels',
                'observed_at':now}


class AutomaticToolReader:
    def __init__(self,scene_locator=None):
        self.scene_locator=scene_locator
        self.regions=[];self.context=None;self.inventory=ToolInventory()
        self.last_discovery=-1e9;self.next_due=0;self.misses=0
        self.anchor=None
        self.quiet_reads=0
        self.numeric_cache={};self.signatures={}
        self.last_pair=-1e9
        self.previous_positioned=None
        self.diagnostic=None

    def read(self,tess,bounds,grab,now=None,interval=10,confirm_pair=False,require_use=False):
        started=time.monotonic();_budget.deadline=started+6
        self.last_failure_trace=''
        if self.diagnostic is not None:_budget.trace=[]
        try:
            report=self._read(tess,bounds,grab,now,interval,require_use=require_use)
            selected=place_selected(report,bounds[4]-bounds[2])
            if selected and report['active_id'] and selected['id']!=report['active_id']:
                # Repeated verified consumption outranks a camera-dependent
                # positional prior when the player moves to another utensil.
                report['confirmation']='Repeated durability use overrides Place Mode position'
            provisional=None if require_use else place_selected(report,bounds[4]-bounds[2],uncontested=True)
            if provisional and not getattr(self,'position_started',False):
                # First verified read is usable immediately; confirm use on
                # the following scan without holding the initial countdown.
                self.position_started=True
            elif confirm_pair and not report['active_id'] and report['tools'] and time.monotonic()-self.last_pair>=15 and _budget.deadline-time.monotonic()>=2.5:
                self.last_pair=time.monotonic()
                try:report=self.compare_pair(tess,bounds,grab,report,interval,require_use=require_use)
                except (RuntimeError,TimeoutError,subprocess.TimeoutExpired):report['pair_result']='Comparison interrupted; no active tool inferred'
            if not report['active_id'] and provisional and not report.get('ambiguous_use') and not report.get('position_conflict'):
                selected=provisional
                report.update(active_id=selected['id'],active_key=f"{selected['id']}:{selected.get('cycle',0)}",confirmation='Place Mode position')
                selected['state']='Selected by Place Mode · checking use'
                report['next_seconds']=1.5;self.next_due=max(time.monotonic(),report.get('captured_mono',time.monotonic())+1.5)
            report['duration']=time.monotonic()-started
            if hasattr(_budget,'trace'):report['_debug_raw']='\n\n'.join(_budget.trace)[-12000:]
            return report
        except Exception:
            self.last_failure_trace='\n\n'.join(getattr(_budget,'trace',[]))[-12000:]
            raise
        finally:
            del _budget.deadline
            if hasattr(_budget,'trace'):del _budget.trace

    def compare_pair(self,tess,bounds,grab,report,interval,*,require_use=False):
        """Two small label batches 1.5 seconds apart; never retain full frames."""
        _,left,top,_,_=bounds
        verified_boxes={tuple(row['box']) for row in report['tools']}
        regions=[dict(r) for r in self.regions if tuple(r['box']) in verified_boxes]
        if not regions:return report
        def capture():return [grab((left+r['box'][0],top+r['box'][1],left+r['box'][2],top+r['box'][3])) for r in regions]
        a_mono=time.monotonic();first=capture()
        time.sleep(max(0,1.5-(time.monotonic()-a_mono)))
        b_mono=time.monotonic();b_wall=time.time();second=capture()
        for r,a,b in zip(regions,first,second):
            signature=label_signature(a,r)
            if signature is None or not signature_matches(signature,label_signature(b,r)):
                report['pair_result']='Labels moved; waiting to reacquire';return report
        a,calls_a=verify_labels(first,[dict(r) for r in regions],tess,self.numeric_cache)
        b,calls_b=verify_labels(second,[dict(r) for r in regions],tess,self.numeric_cache)
        if self.diagnostic is not None:self.diagnostic(second,b,None)
        report['ocr_calls']+=calls_a+calls_b
        candidates=changing_fields(a,b,b_mono-a_mono) if len(a)==len(regions) and len(b)==len(regions) else []
        field=candidates[0] if len(candidates)==1 else None
        if len(candidates)>1:
            report['ambiguous_use']=True
            report['pair_result']='Several verified counters changed; tool selection withheld'
            return report
        report['duration']+=time.monotonic()-a_mono
        selected=None if require_use else place_selected(report,bounds[4]-bounds[2])
        if field and selected and tuple(selected.get('numbers',()))!=field:
            field=None
            report['position_conflict']=True
            report['pair_result']='A nearby tool changed, but it does not match Place Mode; confirmation withheld'
        else:report['pair_result']='One verified changing tool' if field else 'No unique verified durability change'
        if field:
            self.inventory.update(a,a_mono,self.context)
            confirmed=self.inventory.update(b,b_mono,self.context,confirmed_field=field)
            report.update(confirmed,captured_mono=b_mono,captured_at=b_wall,confirmation='two-frame comparison')
            self.signatures={tuple(r['box']):label_signature(crop,r) for r,crop in zip(regions,second)}
            self.next_due=time.monotonic()+max(3,min(120,interval));report['next_seconds']=max(3,min(120,interval))
        return report

    def _read(self,tess,bounds,grab,now=None,interval=10,*,require_use=False):
        """bounds=(window_id,left,top,right,bottom); grab is screen-capture adapter."""
        started=time.monotonic();now=started if now is None else now;scene=None
        hwnd,left,top,right,bottom=bounds;width=right-left;height=bottom-top
        if width<100 or height<100 or width*height>16_000_000:raise ValueError('Unsupported visible game window size')
        context=(hwnd,left,top,width,height)
        locator=self.scene_locator or discover_scene
        if require_use:locator=getattr(self.scene_locator,'locate_all',None) or locator
        if context!=self.context:self.regions=[];self.context=context;self.signatures={};self.numeric_cache={};self.position_started=False
        discover=not self.regions or now-self.last_discovery>=30
        calls=0
        if discover:
            image=grab((left,top,right,bottom)).convert('RGB')
            scene=image
            captured_mono=time.monotonic();captured_at=time.time()
            self.regions,self.anchor,used_calls=locator(image,tess);calls+=used_calls
            self.last_discovery=now
            crops=[image.crop(r['box']) for r in self.regions]
            del image
        else:
            captured_mono=time.monotonic();captured_at=time.time()
            crops=[grab((left+r['box'][0],top+r['box'][1],left+r['box'][2],top+r['box'][3])) for r in self.regions]
        stable=[(crop,r) for crop,r in zip(crops,self.regions) if discover or
                signature_matches(self.signatures.get(tuple(r['box'])),label_signature(crop,r))]
        shifted=len(stable)!=len(crops)
        observations=[];used_calls=0
        if stable and (require_use or not shifted):
            stable_crops,stable_regions=zip(*stable)
            observations,used_calls=verify_labels(stable_crops,stable_regions,tess,self.numeric_cache)
        calls+=used_calls
        # Reading a nearby empty utensil is not success at finding the current
        # tool. A valid but irrelevant neighbor must not suppress reacquisition.
        needs_current=not observations if require_use else not place_selected({'anchor':self.anchor,'tools':observations},height)
        focused_locator=any(s in (self.anchor or {}).get('evidence','') for s in ('focused durability bar','positioned Windows OCR'))
        if discover and scene is not None and needs_current and focused_locator and _budget.deadline-time.monotonic()>1:
            self.regions,self.anchor,used_calls=discover_scene(scene,tess,focused=False);calls+=used_calls
            crops=[scene.crop(r['box']) for r in self.regions]
            observations,used_calls=verify_labels(crops,self.regions,tess,self.numeric_cache) if crops else ([],0);calls+=used_calls
        if not discover and (not observations or not require_use and len(observations)<len(self.regions)):
            # Camera motion invalidates remembered label rectangles. Reacquire
            # this scan rather than waiting for the broad-discovery heartbeat.
            image=grab((left,top,right,bottom)).convert('RGB')
            scene=image
            captured_mono=time.monotonic();captured_at=time.time()
            self.regions,self.anchor,used_calls=locator(image,tess);calls+=used_calls
            crops=[image.crop(r['box']) for r in self.regions]
            del image
            observations,used_calls=verify_labels(crops,self.regions,tess,self.numeric_cache) if crops else ([],0)
            calls+=used_calls
            self.last_discovery=now;discover=True
        if scene is not None and _budget.deadline-time.monotonic()>1 and any(r.get('locator')!='durability bar' and not any(o['box']==r['box'] for o in observations) for r in self.regions):
            known=[r for r in self.regions if r.get('locator')=='durability bar' or any(o['box']==r['box'] for o in observations)]
            try:extra,used_calls=discover_bar_labels(scene,tess,known)
            except (ToolBudgetExpired,subprocess.TimeoutExpired):extra,used_calls=[],0
            calls+=used_calls
            verified=[r for r in self.regions if any(o['box']==r['box'] for o in observations)]
            extra=extra[:max(0,MAX_TOOLS-len(verified))]
            extra_crops=[scene.crop(r['box']) for r in extra]
            rescued,used_calls=verify_labels(extra_crops,extra,tess,self.numeric_cache) if extra else ([],0);calls+=used_calls
            self.regions+=extra;crops+=extra_crops;observations+=rescued
        if self.diagnostic is not None:
            self.diagnostic(crops,observations,scene)
        scene=None
        observations=distinct_counters(observations)
        suspicious_drop=any(old.get('numbers')==row.get('numbers') and old['maximum']==row['maximum'] and old['current']-row['current']>max(30,(now-old['seen_at'])*20+4)
                            for row in observations for old in self.inventory.tracks.values())
        if suspicious_drop:self.last_discovery=-1e9
        field=None;candidates=[];previous=self.previous_positioned
        selected=place_selected({'anchor':self.anchor,'tools':observations},height)
        if previous and previous['context']==context and not shifted:
            elapsed=captured_mono-previous['at']
            if require_use and not discover:
                candidates=changing_fields(previous['observations'],observations,elapsed,max_elapsed=8)
                if len(candidates)==1:field=candidates[0]
            elif selected:
                candidates=changing_fields(previous['observations'],observations,elapsed)
                if len(candidates)==1 and candidates[0]==previous['field']==tuple(selected.get('numbers',())):field=candidates[0]
        report=self.inventory.update(observations,now,context,confirmed_field=field)
        if len(candidates)>1 and (require_use or not report['active_id']):
            report.update(active_id=None,active_key=None,ambiguous_use=True,reason='Several verified counters changed; active tool is uncertain')
        if field and report['active_id']:
            report['confirmation']='consecutive verified reads'
            report['pair_result']='One verified counter decreased between scans'
        self.previous_positioned={'context':context,'observations':[dict(row) for row in observations],
                                  'at':captured_mono,'field':tuple(selected.get('numbers',())) if selected else None}
        if not (observations and (require_use or selected) and all(row.get('votes',0)>=2 for row in observations)):
            self.previous_positioned=None
        unreadable=unreadable_regions(self.regions,observations)
        if require_use and unreadable and observations:
            self.last_discovery=min(self.last_discovery,now-20)
        self.misses=self.misses+1 if not observations else 0
        if discover:self.signatures={tuple(r['box']):label_signature(crop,r) for r,crop in zip(self.regions,crops) if any(r['box']==o['box'] for o in observations)}
        self.regions=[r for r in self.regions if any(r['box']==o['box'] for o in observations)]
        if any(row['last_drop']>0 for row in report['tools']) or discover:self.quiet_reads=0
        else:self.quiet_reads+=1
        delay=max(3,min(120,interval)) if report['active_id'] else min(30,3*max(1,self.quiet_reads-2)) if observations else (3,10,30,60,120)[min(4,self.misses-1)]
        self.next_due=time.monotonic()+delay
        report.update(duration=time.monotonic()-started,ocr_calls=calls,discovery=discover,
                      engine='Positioned Windows OCR + independent numeric verification' if any(r.get('os_pair') for r in self.regions) else 'Tesseract locator + numeric verification',
                      locator_error=getattr(self.scene_locator,'last_error',''),
                      next_seconds=delay,visible_limit=MAX_TOOLS,anchor=self.anchor,
                      captured_mono=captured_mono,captured_at=captured_at,unreadable=unreadable,
                      cache_hits=sum(bool(r.get('cache_hit')) for r in observations),camera_reacquired=shifted)
        return report
