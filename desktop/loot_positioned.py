"""Bounded recovery of incomplete personal-feed rows using the existing OS worker.

Never interpret a bare item as personal loot. Reconstruct physical rows before
parsing, require two row-aligned reads, and leave unresolved rows as holes.
"""
from collections import Counter
import math
import re
import statistics
import unicodedata
from dataclasses import replace
from PIL import ImageOps
from item_events import parse_events


def physical_rows(words):
    valid=[]
    for word in words[:6000]:
        try:
            x,y,w,h=(float(word[k]) for k in ('x','y','w','h'))
            if not all(math.isfinite(n) for n in (x,y,w,h)) or min(w,h)<=0:continue
            valid.append((x,y+h/2,h,str(word.get('text',''))[:150]))
        except (ValueError,TypeError,KeyError):continue
    if not valid:return []
    typical=statistics.median(v[2] for v in valid);groups=[]
    for word in sorted(valid,key=lambda v:(v[1],v[0])):
        if not groups or abs(word[1]-statistics.median(v[1] for v in groups[-1]))>typical*.6:groups.append([])
        groups[-1].append(word)
    return [' '.join(v[3] for v in sorted(group)) for group in groups[:24]]


def personal_row(text,crafting,resolve_name):
    # Normalize only the receipt prefix. Item spelling and all count digits stay
    # untouched. These exact artifacts occur before the item boundary, not in it.
    before,mark,after=text.partition('[')
    if not mark:return None
    before=''.join(c for c in unicodedata.normalize('NFKD',before) if not unicodedata.combining(c))
    before=re.sub(r'(?i)(?<=have)[.7](?=obtained)', ' ',before)
    before=re.sub(r'(?i)(?<=have)\s*\.(?=obtained)', ' ',before)
    rows=parse_events(before+'['+after,crafting=crafting)
    if len(rows)!=1:return None
    event=rows[0];name=resolve_name(event.item) if resolve_name else None
    return replace(event,item=name) if name else None


def recover_personal_feed(image,worker,crafting,resolve_name,baseline):
    if worker is None or resolve_name is None:return None
    # No additional process or capture; the shared worker declines contention.
    scale=min(2,math.sqrt(1_500_000/max(1,image.width*image.height)))
    if scale<1:return None
    size=(max(1,int(image.width*scale)),max(1,int(image.height*scale)))
    readings=[];texts=[]
    for frame in (image.resize(size),ImageOps.autocontrast(image.convert('L')).resize(size)):
        result=worker.recognize(frame,timeout=1,lock_timeout=.01)
        rows=physical_rows(result.get('words',[]));texts.append('\n'.join(rows))
        readings.append([personal_row(row,crafting,resolve_name) for row in rows])
    if len(readings[0])!=len(readings[1]) or not 3<=len(readings[0])<=24:return None
    slots=[a if a is not None and a==b else None for a,b in zip(*readings)]
    events=[event for event in slots if event is not None]
    if len(events)<=len(baseline):return None
    # Recovery cannot contradict quantities already agreed by Tesseract.
    accepted=Counter(events)
    if any(accepted[event]<count for event,count in Counter(baseline).items()):return None
    return {'events':events,'slots':slots,'debug':'POSITIONED RECOVERY / two matching physical rows\n'+'\n---\n'.join(texts)}
