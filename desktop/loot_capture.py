"""Notification OCR, independent of Tk and of durability's restricted digits OCR."""
import io
import subprocess
import csv
from collections import defaultdict
from pathlib import Path
from PIL import ImageOps
from item_events import parse_events,agreed_events


def recognize_feed(image,tess,kind,crafting,folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    image.save(folder/'last_capture.png')
    scaled=image.resize((image.width*3,image.height*3))
    gray=ImageOps.autocontrast(ImageOps.grayscale(scaled))
    passes=[(gray,6),(ImageOps.invert(gray),6),(gray,11)]
    readings=[];logs=[];raws=[]
    for variant,psm in passes:
        blob=io.BytesIO();variant.save(blob,format='PNG')
        result=subprocess.run([tess,'stdin','stdout','--psm',str(psm),'-l','eng'],input=blob.getvalue(),capture_output=True,timeout=4,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        raw=result.stdout.decode('utf-8','replace');raws.append(raw)
        if result.returncode:raise RuntimeError(result.stderr.decode('utf-8','replace')[:160])
        rows=parse_events(raw,crafting=crafting,rare_feed=kind=='rare',bare_items=kind!='chat')
        readings.append(rows);logs.append(f'PSM {psm}\n{raw}\nParsed: {rows!r}\n')
    # Busy game scenery can confuse a whole-panel pass. Find actual notification
    # text lines, then verify each tightly cropped line independently.
    wide_events=agreed_events(readings)
    verified_events=[]
    if kind!='chat' and max(map(len,readings),default=0)>0:
        blob=io.BytesIO();gray.save(blob,format='PNG')
        tsv=subprocess.run([tess,'stdin','stdout','--psm','11','-l','eng','tsv'],input=blob.getvalue(),capture_output=True,timeout=4,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        groups=defaultdict(list)
        for word in csv.DictReader(io.StringIO(tsv.stdout.decode('utf-8','replace')),delimiter='\t'):
            if word.get('text','').strip() and word.get('level')=='5':
                groups[(word['block_num'],word['par_num'],word['line_num'])].append(word)
        verified=[[],[]]
        for words in groups.values():
            line=' '.join(word['text'] for word in words)
            if not parse_events(line,crafting=crafting,rare_feed=kind=='rare',bare_items=True):continue
            left=max(0,min(int(w['left']) for w in words)-8);top=max(0,min(int(w['top']) for w in words)-8)
            right=min(gray.width,max(int(w['left'])+int(w['width']) for w in words)+8)
            bottom=min(gray.height,max(int(w['top'])+int(w['height']) for w in words)+8)
            crop=gray.crop((left,top,right,bottom))
            for index,variant in enumerate((crop,ImageOps.invert(crop))):
                blob=io.BytesIO();variant.save(blob,format='PNG')
                result=subprocess.run([tess,'stdin','stdout','--psm','7','-l','eng'],input=blob.getvalue(),capture_output=True,timeout=3,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                raw=result.stdout.decode('utf-8','replace')
                verified[index].extend(parse_events(raw,crafting=crafting,rare_feed=kind=='rare',bare_items=True))
                logs.append('Notification line: '+raw)
            if sum(map(len,verified))>=12:break
        readings.extend(verified)
        verified_events=agreed_events(verified)
    # Tightly isolated notification text takes precedence over scenery-contaminated
    # whole-panel words (e.g. "Flixir" versus "Elixir"). Don't save both names.
    events=[]
    names={e.item for e in verified_events+wide_events}
    for name in names:
        narrow=[e for e in verified_events if e.item==name]
        wide=[e for e in wide_events if e.item==name]
        # A crop that loses x4 must never replace the explicit count with implicit 1.
        explicit_narrow=[e for e in narrow if e.quantity_explicit]
        explicit_wide=[e for e in wide if e.quantity_explicit]
        events.extend(explicit_narrow or explicit_wide or narrow or wide)
    # Restore screen order after resolving implicit versus explicit quantities.
    order={e.item:i for i,e in reversed(list(enumerate(max(readings,key=len))))}
    events.sort(key=lambda e:order.get(e.item,999))
    debug='\n'.join(logs)+f'\nAGREED: {events!r}'
    (folder/'ocr_log.txt').write_text(debug,encoding='utf-8')
    # Empty text on all passes is only a candidate empty panel. UI requires two
    # consecutive empty captures before allowing identical notifications again.
    empty=all(not raw.strip() for raw in raws)
    return {'events':events,'empty':empty,'raw':raws[0],'recognized':max(map(len,readings)),'debug':debug}
