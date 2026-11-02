"""Explicit one-shot HUD read. Two passes, strict agreement, no recurring work."""
import io
import re
from PIL import Image, ImageOps, ImageGrab
from ocr_runtime import run_ocr

HUD=re.compile(r'(?<![\d./])(?P<free>\d{1,3})\s*/\s*(?P<cp>\d{1,3})\s*\(\s*(?P<pct>\d{1,2}[.,]\d{2})\s*%\s*\)')


def parse_hud(text):
    found=set()
    for match in HUD.finditer(str(text)[:5000]):
        free=int(match['free']);cp=int(match['cp']);pct=float(match['pct'].replace(',','.'))
        if 0<=free<=cp<=599 and 0<=pct<100:found.add((cp,pct,free))
    return next(iter(found)) if len(found)==1 else None


def agreement(first,second):
    a=parse_hud(first);b=parse_hud(second)
    return {'cp':a[0],'percent':a[1],'unused':a[2]} if a is not None and a==b else None


def read_image(image,executable):
    """Only a bounded HUD crop is accepted. Never OCR the entire screen."""
    if image.width>1600 or image.height>180 or image.width*image.height>240000:
        raise ValueError('CP reader requires a small HUD strip')
    gray=ImageOps.autocontrast(image.convert('L'))
    variants=[gray,gray.point(lambda p:0 if p>=185 else 255)]
    texts=[]
    for variant in variants:
        variant=variant.resize((variant.width*2,variant.height*2),Image.Resampling.LANCZOS)
        buffer=io.BytesIO();variant.save(buffer,format='PNG')
        result=run_ocr([str(executable),'stdin','stdout','-l','eng','--psm','6'],input=buffer.getvalue(),capture_output=True,timeout=2.5)
        if result.returncode:raise RuntimeError('CP OCR failed; check Tesseract English in Settings')
        texts.append(result.stdout.decode('utf-8',errors='replace')[:5000])
    result=agreement(*texts)
    return result,'PASS 1\n'+texts[0]+'\nPASS 2\n'+texts[1]+'\nAgreement: '+str(result)


def capture_once(executable):
    from windows_bdo import foreground_bdo_capture_bounds,item_regions_visible
    bounds=foreground_bdo_capture_bounds()
    if not bounds:raise ValueError('Bring BDO to the front with the CP HUD visible, then request another snapshot')
    _,left,top,right,bottom=bounds
    box=hud_box(bounds);x,y,x2,y2=box;width=x2-x;height=y2-y
    visible,reason=item_regions_visible([(x,y,width,height)])
    if not visible:raise ValueError(reason)
    image=ImageGrab.grab(bbox=box,all_screens=True)
    result,detail=read_image(image,executable)
    # A focus/coverage change during recognition invalidates this snapshot.
    if foreground_bdo_capture_bounds()!=bounds:raise ValueError('BDO moved or lost focus during the read; values preserved')
    visible,reason=item_regions_visible([(x,y,width,height)])
    if not visible:raise ValueError(reason)
    return result,image,detail


def hud_box(bounds):
    """Default HUD CP group only; custom HUD layouts fail closed to manual input.

    At 1080p this is about 175×32 px instead of a screen-wide scan. Keep unused
    CP, total CP and percentage together so slash/percentage context is required.
    """
    _,left,top,right,bottom=bounds;w=right-left;h=bottom-top
    return (left+round(w*.167),top+round(h*.003),left+round(w*.26),top+round(h*.035))
