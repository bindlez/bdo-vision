"""User-operated tooltip sweep. Three seconds of bounded captures, then OCR."""
import time
import ctypes
from ctypes import wintypes
from gear_ocr import recognize_image


def tooltip_sweep(catalog,tesseract,update,stop):
    from PIL import ImageGrab
    from windows_bdo import is_bdo_foreground,_user32
    user32=_user32()
    update(stage='waiting',message='Bring BDO to the front with equipment open. Sampling starts in 3 seconds.',captured=0)
    if stop.wait(3):return None
    deadline=time.monotonic()+8
    while not is_bdo_foreground():
        if time.monotonic()>deadline:raise RuntimeError('BDO was not brought to the front. Try again with equipment open.')
        if stop.wait(.1):return None
    update(stage='capturing',message='Move clockwise over gear now. Pause briefly on each item.',captured=0)
    frames=[];started=time.monotonic()
    # At most twelve grayscale crops (~9 MiB); never save game images to disk.
    for index in range(12):
        wait=max(0,started+index*.25-time.monotonic())
        if stop.wait(wait):return None
        if not is_bdo_foreground():break
        point=wintypes.POINT();rect=wintypes.RECT()
        if not user32.GetCursorPos(ctypes.byref(point)) or not user32.GetWindowRect(user32.GetForegroundWindow(),ctypes.byref(rect)):continue
        box=(max(rect.left,point.x-520),max(rect.top,point.y-400),min(rect.right,point.x+520),min(rect.bottom,point.y+320))
        if box[2]-box[0]<50 or box[3]-box[1]<50:continue
        image=ImageGrab.grab(bbox=box,all_screens=True).convert('L')
        # A stationary hover needs its latest frame, after the tooltip settles.
        # Keep separate positions so two identical rings can still be reviewed.
        if frames and abs(frames[-1][1][0]-point.x)<18 and abs(frames[-1][1][1]-point.y)<18:
            frames.pop()[0].close()
        frames.append((image,(point.x,point.y)))
        update(stage='capturing',captured=len(frames),message='Tooltip sweep in progress · move clockwise')
    if not frames:raise RuntimeError('No visible game tooltips captured')
    found=[];texts=[]
    try:
        for index,(image,point) in enumerate(frames):
            if stop.is_set():return None
            update(stage='reading',captured=len(frames),processed=index,message=f'Reading tooltip {index+1} of {len(frames)}')
            report=recognize_image(image,catalog,tesseract);texts.append(report['text'])
            for candidate in report['candidates']:
                # Repeated hovers over the same item do not create copies. Two
                # physically different ring/earring positions remain distinct.
                label=(candidate.get('enhancement') or {}).get('label')
                duplicate=any(old['id']==candidate['id'] and (old.get('enhancement') or {}).get('label')==label and abs(old['hover'][0]-point[0])<28 and abs(old['hover'][1]-point[1])<28 for old in found)
                if not duplicate and len(found)<32:found.append({**candidate,'hover':list(point)})
            image.close()
        return {'candidates':found,'stats':{},'text':'\n'.join(texts)[:16000],
                'notice':'Review slot and enhancement before applying. A fast sweep may miss tooltips that did not finish appearing; repeat for remaining items.'}
    finally:
        for image,_ in frames:image.close()
