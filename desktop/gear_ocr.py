"""On-demand equipment text import. Never changes the loot reader or ledger."""
import base64
import io
import re
import subprocess
import os
from difflib import SequenceMatcher

ROMAN = {'I':1,'II':2,'III':3,'IV':4,'V':5,'VI':6,'VII':7,'VIII':8,'IX':9,'X':10}


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
    found=[]
    for raw in text.splitlines()[:150]:
        raw=raw.strip()
        if not 3<=len(raw)<=220:continue
        level=re.match(r'^(?:(?:PRI|DUO|TRI|TET|PEN|HEX|SEP|OCT|NOV|DEC)\s*\(([IVX]+)\)|([IVX]{1,4})|\+(\d{1,2}))(?:\s*[:\-]\s*|\s+|$)',raw,re.I)
        enhancement=None
        if level:
            roman=(level[1] or level[2] or '').upper()
            enhancement={'kind':'roman' if roman else 'numeric','value':ROMAN.get(roman) if roman else int(level[3]),'label':level[0].strip(' :-')}
            raw_name=raw[level.end():]
        else:raw_name=raw
        normalized=key(raw_name);matches=names.get(normalized,[]);score=1.0
        if not matches and len(normalized)>=10:
            ranked=sorted(((SequenceMatcher(None,normalized,k,autojunk=False).ratio(),k) for k in names if abs(len(k)-len(normalized))<=4),reverse=True)
            if ranked and ranked[0][0]>=.9 and (len(ranked)<2 or ranked[0][0]-ranked[1][0]>=.08):
                score=ranked[0][0];matches=names[ranked[0][1]]
        if len({m['id'] for m in matches})!=1:continue
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
    from PIL import ImageOps
    image.thumbnail((1800,1800));gray=ImageOps.autocontrast(ImageOps.grayscale(image));gray=gray.resize((gray.width*2,gray.height*2))
    png=io.BytesIO();gray.save(png,format='PNG')
    result=subprocess.run([str(tesseract),'stdin','stdout','--psm','11','-l','eng'],input=png.getvalue(),capture_output=True,timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0),env=dict(os.environ,OMP_THREAD_LIMIT='1',OMP_NUM_THREADS='1'))
    if result.returncode:raise RuntimeError('Equipment OCR could not read this image')
    return parse_equipment(result.stdout.decode('utf-8','replace'),catalog)
