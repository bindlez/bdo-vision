"""Notification OCR, independent of Tk and of durability's restricted digits OCR."""
import io
import subprocess
import csv
from collections import defaultdict
from pathlib import Path
from PIL import ImageOps,Image,ImageChops
from item_events import parse_events,agreed_events,joined_messages
from collections import Counter


def notification_ink(image, threshold=80, colors=True):
    """Keep the neutral/colored letter fills; discard most moving brown scenery.

    Operate at source resolution so the game's dark text outline stays separate
    from its bright fill. Resize only after masking.
    """
    red,green,blue=image.convert('RGB').split()
    low=ImageChops.darker(ImageChops.darker(red,green),blue)
    high=ImageChops.lighter(ImageChops.lighter(red,green),blue)
    neutral=ImageChops.multiply(low.point(lambda p:255 if p>threshold else 0),
        ImageChops.subtract(high,low).point(lambda p:255 if p<18 else 0))
    if colors:
        # UI letter fills repeat the exact same color many times. Learn those
        # colors from this frame instead of retaining every green/brown plant.
        rgb=image.convert('RGB');counts=Counter(rgb.getdata())
        palette=[color for color,count in counts.most_common(60)
                 if count>=18 and max(color)>100 and max(color)-min(color)>45]
        if palette:
            tolerance=8 if threshold<100 else 16
            decisions={}
            for color in counts:
                peak=max(color)
                colored=peak>65 and any(max(abs(value-peak*p[i]/max(p))
                    for i,value in enumerate(color))<=tolerance for p in palette)
                decisions[color]=255 if colored else 0
            pixels=[decisions[color] for color in rgb.getdata()]
            quality=Image.new('L',image.size);quality.putdata(pixels)
            neutral=ImageChops.lighter(neutral,quality)
    return ImageOps.invert(neutral).resize((image.width*3,image.height*3))


def recognize_feed(image,tess,kind,crafting,folder,resolve_name=None):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    image.save(folder/'last_capture.png')
    scaled=image.resize((image.width*3,image.height*3))
    gray=ImageOps.autocontrast(ImageOps.grayscale(scaled))
    passes=([(notification_ink(image,80),6),(notification_ink(image,110),6),(notification_ink(image,95,False),6)]
            if kind=='chat' else [(gray,6),(ImageOps.invert(gray),6),(gray,11)])
    readings=[];logs=[];raws=[];slots=[]
    for variant,psm in passes:
        blob=io.BytesIO();variant.save(blob,format='PNG')
        result=subprocess.run([tess,'stdin','stdout','--psm',str(psm),'-l','eng'],input=blob.getvalue(),capture_output=True,timeout=4,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        raw=result.stdout.decode('utf-8','replace');raws.append(raw)
        if result.returncode:raise RuntimeError(result.stderr.decode('utf-8','replace')[:160])
        rows=parse_events(raw,crafting=crafting,rare_feed=kind=='rare',bare_items=kind!='chat')
        if resolve_name:
            from dataclasses import replace
            rows=[replace(e,item=resolve_name(e.item) or e.item) for e in rows]
        readings.append(rows);logs.append(f'PSM {psm}\n{raw}\nParsed: {rows!r}\n')
        if kind=='chat':
            frame=[]
            for message in joined_messages(raw):
                parsed=parse_events(message,crafting=crafting)
                event=parsed[0] if len(parsed)==1 else None
                if event and resolve_name:
                    from dataclasses import replace
                    resolved=resolve_name(event.item)
                    event=replace(event,item=resolved) if resolved else None
                frame.append(event)
            slots.append(frame)
            if len(slots)==2 and len(frame)>=3 and all(frame) and frame==slots[0]:
                logs.append('Early exit: two complete ordered message reads agree.')
                break
    # Busy game scenery can confuse a whole-panel pass. Find actual notification
    # text lines, then verify each tightly cropped line independently.
    wide_events=agreed_events(readings)
    agreed_slots=None
    if kind=='chat':
        # Compare the same physical message row, preserving repeats and order.
        # A global multiset vote can otherwise move a rare item to the end and
        # make retained chat rows look like new drops on the following scan.
        size=Counter(map(len,slots)).most_common(1)[0][0]
        aligned=[frame for frame in slots if len(frame)==size]
        if len(aligned)>=2:
            agreed_slots=[]
            for index in range(size):
                votes=Counter(frame[index] for frame in aligned if frame[index] is not None)
                event,count=votes.most_common(1)[0] if votes else (None,0)
                agreed_slots.append(event if count>=2 else None)
            wide_events=[event for event in agreed_slots if event is not None]
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
    if agreed_slots is not None:events=wide_events
    debug='\n'.join(logs)+f'\nAGREED: {events!r}'
    (folder/'ocr_log.txt').write_text(debug,encoding='utf-8')
    # Empty text on all passes is only a candidate empty panel. UI requires two
    # consecutive empty captures before allowing identical notifications again.
    empty=all(not raw.strip() for raw in raws)
    return {'events':events,'slots':agreed_slots,'empty':empty,'raw':raws[0],'recognized':max(map(len,readings)),'debug':debug}
