"""On-demand equipment text import. Never changes the loot reader or ledger."""
import base64
import io
import re
import subprocess
import os
import csv
from difflib import SequenceMatcher

ROMAN = {'I':1,'II':2,'III':3,'IV':4,'V':5,'VI':6,'VII':7,'VIII':8,'IX':9,'X':10}
RANKS={'PRI':1,'DUO':2,'TRI':3,'TET':4,'PEN':5,'HEX':6,'SEP':7,'HEP':7,'OCT':8,'NOV':9,'ENE':9,'DEC':10}
ORIGIN_RANKS={'desperate':1,'distorted':2,'silent':3,'wailing':4,'obliterating':5}
ORIGIN_ITEMS={"labreska s helmet","fallen god s armor","dahn s gloves","ator s shoes"}


def key(text):
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', text.casefold()).split())


def parse_equipment(text, catalog):
    """Keep uncertain identity/levels explicit; user chooses destination slots."""
    items=[]
    for row in catalog:
        if not isinstance(row,dict) or type(row.get('id')) is not int or not 0<row['id']<10000000:
            raise ValueError('Invalid equipment identity')
        if row.get('mainCategory') not in (1,5,10,15,20,40,45,85) or not isinstance(row.get('name'),str) or not 1<=len(row['name'])<=150:
            raise ValueError('Equipment catalog required')
        items.append({k:row[k] for k in ('id','name','mainCategory','subCategory') if k in row})
    names={}
    for item in items:names.setdefault(key(item['name']),[]).append(item)
    # Sparse OCR can emit thousands of short/blank scene lines before a title.
    # Bound bytes instead of silently ignoring every title after line 150.
    lines=[line.strip() for line in text[:64000].splitlines() if line.strip()]
    suffixes={}
    for name in names:suffixes.setdefault(name.split()[-1],[]).append(name)
    found=[];pending=None
    for raw in lines[:4000]:
        if not 3<=len(raw)<=220:continue
        if re.search(r'(?i)(?:description\s*:|when enhancing|cron stones|used when|defeated by|item effect|quest reward)',raw):
            pending=None;continue
        level=re.match(r'^(?:(PRI|DUO|TRI|TET|PEN|HEX|SEP|HEP|OCT|NOV|ENE|DEC)(?:\s*\(([IVX]+)\))?|([IVX]{1,4})|\+(\d{1,2}))(?:\s*[:\-]\s*|\s+|$)',raw,re.I)
        enhancement=None;origin_rank=False
        if level:
            rank=(level[1] or '').upper();roman=(level[2] or level[3] or '').upper()
            value=ROMAN.get(roman) if roman else RANKS.get(rank) if rank else int(level[4])
            if value is None or rank and roman and RANKS[rank]!=value:continue
            enhancement={'kind':'numeric' if level[4] else 'roman','value':value,'label':level[0].strip(' :-')}
            raw_name=raw[level.end():]
            if not raw_name.strip():pending=enhancement;continue
        else:
            prefix=re.match(r'^(Desperate|Distorted|Silent|Wailing|Obliterating)(?:\s*:\s*|\s+|$)',raw,re.I)
            if prefix:
                origin_rank=True;enhancement={'kind':'numeric','value':ORIGIN_RANKS[prefix[1].lower()],'label':prefix[1]}
                raw_name=raw[prefix.end():]
            else:raw_name=raw
        if pending and not enhancement:enhancement=pending
        pending=None
        normalized=key(raw_name);matches=names.get(normalized,[]);score=1.0
        if not matches and len(normalized)>=10 and len(normalized.split())>=2:
            pool=suffixes.get(normalized.split()[-1],[])
            ranked=sorted(((SequenceMatcher(None,normalized,k,autojunk=False).ratio(),k) for k in pool if abs(len(k)-len(normalized))<=4),reverse=True)
            if ranked and ranked[0][0]>=.9 and (len(ranked)<2 or ranked[0][0]-ranked[1][0]>=.08):
                score=ranked[0][0];matches=names[ranked[0][1]]
        if len({m['id'] for m in matches})!=1:continue
        if origin_rank and key(matches[0]['name']) not in ORIGIN_ITEMS:continue
        found.append({**matches[0],'enhancement':enhancement,'confidence':round(score,3),'observed':raw,'review_required':True})
        if len(found)>=24:break
    stats={}
    for label,pattern in [('ap',r'(?im)^\s*(?:AP|Attack Power)\s*:?\s*(\d{1,4})(?:\s*[~\-]\s*(\d{1,4}))?'),('dp',r'(?im)^\s*(?:DP|Defense|Defense Power)\s*:?\s*(\d{1,4})')]:
        match=re.search(pattern,text)
        if match:stats[label]=[int(v) for v in match.groups() if v is not None]
    return {'candidates':found,'stats':stats,'text':text[:16000],
            'notice':'Review item, enhancement and slot before applying. Icon-only items and unreadable text remain unresolved.'}


def read_equipment(body, tesseract):
    from PIL import Image,ImageOps
    catalog=body.get('catalog')
    if not isinstance(catalog,list) or len(catalog)>5000:raise ValueError('Invalid catalog size')
    # Validate identities before spending CPU on OCR.
    parse_equipment('',catalog)
    encoded=body.get('image','')
    if not isinstance(encoded,str) or len(encoded)>2800000:raise ValueError('Image too large')
    if ',' not in encoded or encoded.split(',',1)[0] not in ('data:image/png;base64','data:image/jpeg;base64'):raise ValueError('PNG or JPEG required')
    blob=base64.b64decode(encoded.split(',',1)[1],validate=True)
    with Image.open(io.BytesIO(blob)) as source:
        if source.width*source.height>6000000 or min(source.size)<10:raise ValueError('Use a cropped equipment image up to 6 megapixels')
        source.load();image=source.convert('RGB')
    return recognize_image(image,catalog,tesseract)


def recognize_image(image,catalog,tesseract):
    from PIL import ImageOps,ImageStat
    image.thumbnail((1800,1800));gray=ImageOps.autocontrast(ImageOps.grayscale(image));gray=gray.resize((gray.width*2,gray.height*2))
    def run(pixels,psm,tsv=False):
        png=io.BytesIO();pixels.save(png,format='PNG')
        result=subprocess.run([str(tesseract),'stdin','stdout','--psm',str(psm),'-l','eng']+(['tsv'] if tsv else []),input=png.getvalue(),capture_output=True,timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),env=dict(os.environ,OMP_THREAD_LIMIT='1',OMP_NUM_THREADS='1'))
        if result.returncode:raise RuntimeError('Equipment OCR could not read this image')
        return result.stdout.decode('utf-8','replace')
    grouped={}
    for word in csv.DictReader(io.StringIO(run(gray,11,True)),delimiter='\t'):
        if word.get('level')!='5' or not word.get('text','').strip():continue
        group=tuple(word.get(k) for k in ('block_num','par_num','line_num'))
        grouped.setdefault(group,[]).append(word)
    lines=[];anchors=[]
    for words in grouped.values():
        words.sort(key=lambda w:int(w['left']));line=' '.join(w['text'] for w in words);lines.append(line)
        normalized=key(line)
        if re.search(r'(?i)\bequipment\s*[\(\[]',line) or re.search(r'\bequipment\s+(?:helmet|armor|gloves|shoes|belt|ring|earring|necklace|weapon)\b',normalized):
            anchors.append((min(int(w['left']) for w in words),min(int(w['top']) for w in words),max(int(w['left'])+int(w['width']) for w in words),max(int(w['top'])+int(w['height']) for w in words)))
    report=parse_equipment('\n'.join(lines),catalog);focused=[]
    # A short second pass targets the tooltip header only, rather than asking
    # a general scene scan to read tiny colored title text among combat/chat.
    if not report['candidates'] or any(c['enhancement'] is None for c in report['candidates']):
        for left,top,right,bottom in anchors[:2]:
            crop=gray.crop((max(0,left-1050),max(0,top-8),min(gray.width,right+100),min(gray.height,bottom+190)))
            if ImageStat.Stat(crop).mean[0]<128:crop=ImageOps.invert(crop)
            raw=run(crop,6);focused.append(raw)
            extra=parse_equipment(raw,catalog)
            for candidate in extra['candidates']:
                existing=next((old for old in report['candidates'] if old['id']==candidate['id']),None)
                if existing is None:report['candidates'].append(candidate)
                elif existing['enhancement'] is None and candidate['enhancement'] is not None:existing['enhancement']=candidate['enhancement']
    report['text']=(('FOCUSED TOOLTIP HEADER\n'+'\n'.join(focused)+'\n\nSCENE OCR\n' if focused else '')+'\n'.join(lines))[:16000]
    report['focused_passes']=len(focused)
    return report
