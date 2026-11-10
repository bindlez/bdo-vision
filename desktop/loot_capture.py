"""Notification OCR, independent of Tk and of durability's restricted digits OCR."""
import io
import re
import subprocess
import csv
import time
from collections import defaultdict
from pathlib import Path
from PIL import ImageOps,Image,ImageChops
from item_events import parse_events,agreed_events,joined_messages
from collections import Counter
from ocr_runtime import run_ocr


def capture_budget(regions):
    """Reject accidental full-screen feeds rather than allocating huge OCR masks."""
    if not regions:return False,'Select an item capture area'
    total=0
    for region in regions:
        if not isinstance(region,(list,tuple)) or len(region)!=4 or any(type(n) is not int for n in region):
            return False,'Select a valid rectangular item capture area'
        x,y,width,height=region
        if min(width,height)<8:return False,'Select a larger item capture area'
        total+=width*height
        if width*height>750_000 or total>1_000_000:
            return False,'Capture area too large; select only 6–8 complete personal loot rows'
    return True,''


def prepare_ink(image, colors=True):
    """Share the expensive palette/color decisions across consensus passes."""
    rgb=image.convert('RGB')
    red,green,blue=rgb.split()
    low=ImageChops.darker(ImageChops.darker(red,green),blue)
    high=ImageChops.lighter(ImageChops.lighter(red,green),blue)
    counts=Counter(rgb.getdata()) if colors else Counter()
    palette=[color for color,count in counts.most_common(60)
             if count>=18 and max(color)>100 and max(color)-min(color)>45]
    qualities={}
    if palette:
        decisions={8:{},16:{}}
        for color in counts:
            peak=max(color);distance=256
            if peak>65:
                for p in palette:
                    distance=min(distance,max(abs(value-peak*p[i]/max(p))
                                              for i,value in enumerate(color)))
                    if distance<=8:break
            for tolerance in decisions:
                decisions[tolerance][color]=255 if distance<=tolerance else 0
        for tolerance in decisions:
            quality=Image.new('L',image.size)
            quality.putdata([decisions[tolerance][color] for color in rgb.getdata()])
            qualities[tolerance]=quality
    return low,ImageChops.subtract(high,low),qualities


def notification_ink(image, threshold=80, colors=True, prepared=None):
    """Keep the neutral/colored letter fills; discard most moving brown scenery.

    Operate at source resolution so the game's dark text outline stays separate
    from its bright fill. Resize only after masking.
    """
    low,spread,qualities=prepared if prepared is not None else prepare_ink(image,colors)
    neutral=ImageChops.multiply(low.point(lambda p:255 if p>threshold else 0),
        spread.point(lambda p:255 if p<18 else 0))
    if colors:
        # UI letter fills repeat the exact same color many times. Learn those
        # colors from this frame instead of retaining every green/brown plant.
        if qualities:
            tolerance=8 if threshold<100 else 16
            neutral=ImageChops.lighter(neutral,qualities[tolerance])
    return ImageOps.invert(neutral).resize((image.width*3,image.height*3))


def recognize_feed(image,tess,kind,crafting,folder,resolve_name=None,diagnostics=True,positioned_worker=None):
    deadline=time.monotonic()+12
    def recognize(command, **options):
        remaining=deadline-time.monotonic()
        if remaining<=0:raise TimeoutError('Loot panel OCR exceeded its time budget')
        options['timeout']=min(options['timeout'],remaining)
        return run_ocr(command,**options)

    folder=Path(folder)
    if diagnostics:
        folder.mkdir(parents=True,exist_ok=True)
        image.save(folder/'last_capture.png')
    if kind=='chat':
        prepared=prepare_ink(image)
        passes=[(notification_ink(image,80,prepared=prepared),6),
                (notification_ink(image,110,prepared=prepared),6),
                (notification_ink(image,135,prepared=prepared),6),
                (notification_ink(image,135,False,prepared=prepared),6)]
    else:
        gray=ImageOps.autocontrast(ImageOps.grayscale(image.resize((image.width*3,image.height*3))))
        passes=[(gray,6),(ImageOps.invert(gray),6),(gray,11)]
    readings=[];logs=[];raws=[];slots=[];inset_slots=[]
    normal_passes=len(passes)
    if kind=='chat' and image.width>=300:
        # Retry without the System badge column when whole-panel OCR fails.
        for variant,_ in passes[-2:]:
            passes=passes+[(variant.crop((round(variant.width*.145),0,variant.width,variant.height)),6)]
    for variant,psm in passes:
        inset=len(raws)>=normal_passes
        if inset and agreed_events(readings[:normal_passes]):break
        blob=io.BytesIO();variant.save(blob,format='PNG')
        try:
            result=recognize([tess,'stdin','stdout','--psm',str(psm),'-l','eng'],input=blob.getvalue(),capture_output=True,timeout=4)
        except (TimeoutError,subprocess.TimeoutExpired):
            if not readings:raise
            logs.append('OCR pass timed out; keeping completed passes.')
            break
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
            (inset_slots if inset else slots).append(frame)
            if len(slots)==2 and len(frame)>=3 and all(frame) and frame==slots[0]:
                logs.append('Early exit: two complete ordered message reads agree.')
                break
    # Busy game scenery can confuse a whole-panel pass. Find actual notification
    # text lines, then verify each tightly cropped line independently.
    wide_events=agreed_events(readings)
    if kind=='normal' and sum(len(re.findall(r'\byou\s*have\s*obtained\b',raw,re.I))>=2 for raw in raws)>=2:
        reason='Item Drop Log box is on the text feed. Select the popup area in Capture Setup.'
        return {'events':[],'slots':None,'empty':False,'raw':raws[0],
                'recognized':0,'debug':'\n'.join(logs)+'\n'+reason,'mismatch':reason}
    agreed_slots=None
    if kind=='chat':
        # Compare the same physical message row, preserving repeats and order.
        # A global multiset vote can otherwise move a rare item to the end and
        # make retained chat rows look like new drops on the following scan.
        if len(inset_slots)==2 and len(inset_slots[0])==len(inset_slots[1]) and any(a and a==b for a,b in zip(*inset_slots)):
            slots=inset_slots
            logs.append('Retry without the System badge recovered matching rows.')
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
    if kind!='chat' and deadline-time.monotonic()>1 and max(map(len,readings),default=0)>0:
        blob=io.BytesIO();gray.save(blob,format='PNG')
        try:tsv=recognize([tess,'stdin','stdout','--psm','11','-l','eng','tsv'],input=blob.getvalue(),capture_output=True,timeout=2)
        except (TimeoutError,subprocess.TimeoutExpired):tsv=None
        groups=defaultdict(list)
        for word in csv.DictReader(io.StringIO(tsv.stdout.decode('utf-8','replace') if tsv else ''),delimiter='\t'):
            if word.get('text','').strip() and word.get('level')=='5':
                groups[(word['block_num'],word['par_num'],word['line_num'])].append(word)
        verified=[[],[]]
        for words in groups.values():
            if deadline-time.monotonic()<1:break
            line=' '.join(word['text'] for word in words)
            if not parse_events(line,crafting=crafting,rare_feed=kind=='rare',bare_items=True):continue
            left=max(0,min(int(w['left']) for w in words)-8);top=max(0,min(int(w['top']) for w in words)-8)
            right=min(gray.width,max(int(w['left'])+int(w['width']) for w in words)+8)
            bottom=min(gray.height,max(int(w['top'])+int(w['height']) for w in words)+8)
            crop=gray.crop((left,top,right,bottom))
            for index,variant in enumerate((crop,ImageOps.invert(crop))):
                blob=io.BytesIO();variant.save(blob,format='PNG')
                try:result=recognize([tess,'stdin','stdout','--psm','7','-l','eng'],input=blob.getvalue(),capture_output=True,timeout=1)
                except (TimeoutError,subprocess.TimeoutExpired):break
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
        if explicit_narrow and not (Counter(explicit_narrow)-Counter(explicit_wide)):
            events.extend(explicit_wide)
        else:events.extend(explicit_narrow or explicit_wide or narrow or wide)
    # Restore screen order after resolving implicit versus explicit quantities.
    order={e.item:i for i,e in reversed(list(enumerate(max(readings,key=len))))}
    events.sort(key=lambda e:order.get(e.item,999))
    if agreed_slots is not None:events=wide_events
    if kind=='chat' and (agreed_slots is None or any(event is None for event in agreed_slots)) and positioned_worker is not None:
        try:
            from loot_positioned import recover_personal_feed
            recovery=recover_personal_feed(image,positioned_worker,crafting,resolve_name,events)
            if recovery:
                events=recovery['events'];agreed_slots=recovery['slots'];logs.append(recovery['debug'])
        except (RuntimeError,OSError,ValueError):
            logs.append('Positioned recovery unavailable or busy; original consensus retained.')
    debug='\n'.join(logs)+f'\nAGREED: {events!r}'
    if diagnostics:(folder/'ocr_log.txt').write_text(debug,encoding='utf-8')
    # Empty text on all passes is only a candidate empty panel. UI requires two
    # consecutive empty captures before allowing identical notifications again.
    empty=len(raws)>=2 and all(not raw.strip() for raw in raws)
    return {'events':events,'slots':agreed_slots,'empty':empty,'raw':raws[0],'recognized':max(map(len,readings)),'debug':debug}
