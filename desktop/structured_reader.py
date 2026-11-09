"""Positioned OS text locates fields; literal numeric verification stays separate."""
import math
import re


def tool_regions(result,origin=(0,0),scale=1):
    from tool_reader import anchored_title_family
    groups={}
    for word in result.get('words',[]):groups.setdefault(word['line'],[]).append(word)
    anchor=None;regions=[]
    for group in groups.values():
        text=' '.join(w['text'] for w in group)
        def box(words,pad=0):
            return [int(min(w['x'] for w in words)/scale+origin[0])-pad,
                    int(min(w['y'] for w in words)/scale+origin[1])-pad,
                    math.ceil(max(w['x']+w['w'] for w in words)/scale+origin[0])+pad,
                    math.ceil(max(w['y']+w['h'] for w in words)/scale+origin[1])+pad]
        if re.sub(r'\W','',text).casefold()=='placemode':
            a,b,c,d=box(group);anchor={'x':(a+c)/2,'y':(b+d)/2,'evidence':'Place Mode · positioned Windows OCR'}
        previous=0
        for pair in re.finditer(r'[(\{]\s*(\d{1,6})\s*(?:[/|]|\s)\s*(\d{2,6})\s*[)}]',text):
            family=anchored_title_family(text[previous:pair.start()]+'(')
            segment_start=previous;previous=pair.end()
            if not family:continue
            current,maximum=map(int,pair.groups())
            if not 0<=current<=maximum or not 100<=maximum<=100000:continue
            offset=0;numeric=[];full_words=[];start_x=None
            for word in group:
                end=offset+len(word['text'])
                if end>segment_start and offset<pair.end():full_words.append(word)
                if end>pair.start(1) and offset<pair.end():
                    numeric.append(word)
                    if start_x is None:
                        index=max(0,pair.start(1)-offset)
                        start_x=(word['x']+word['w']*index/max(1,len(word['text'])))/scale+origin[0]
                offset=end+1
            if not numeric:continue
            full=box(full_words,5);field=box(numeric,6);field[0]=int(start_x)-16
            full=[min(full[0],field[0]),min(full[1],field[1]),max(full[2],field[2]),max(full[3],field[3])]
            regions.append({'name':family,'box':full,'numbers':field,'os_pair':(current,maximum),
                            'white_numeric':True,'title_evidence':'Positioned Windows OCR title and complete bounded counter'})
    return regions,anchor


def quest_objective_identity(reading):
    # The item resolver permits only an unambiguous close long catalog name.
    # This repairs a named item, never counter digits or another objective.
    from item_names import canonical_item,known_item
    text=reading['objective']
    match=re.fullmatch(r'(Obtain|Make|Produce|Craft)\s+(.+?)\s+(via\s+(?:Alchemy|Cooking))',text,re.I)
    if match:
        name=canonical_item(match[2])
        if known_item(name):text=match[1]+' '+name+' '+match[3]
    return re.sub(r'[^a-z]','',text.casefold())


class StructuredLocator:
    def __init__(self,worker):self.worker=worker;self.last_error=''

    def locate_all(self,image,tess):
        return self(image,tess,all_candidates=True)

    def __call__(self,image,tess,focused=True,*,all_candidates=False):
        from tool_reader import discover_scene,place_selected
        from PIL import ImageOps
        self.last_error=''
        try:
            # Upper world/residence strip only. One engine request and no full
            # screen upscale. Crop scale adapts without exceeding the pipe cap.
            box=(int(image.width*.25),0 if all_candidates else int(image.height*.08),int(image.width*.82),int(image.height*.32))
            crop=ImageOps.autocontrast(image.crop(box).convert('L'))
            scale=min(2.,math.sqrt(1400000/(crop.width*crop.height)))
            prepared=crop.resize((int(crop.width*scale),int(crop.height*scale)))
            result=self.worker.recognize(prepared,timeout=1.5)
            regions,anchor=tool_regions(result,origin=box[:2],scale=scale)
            if anchor and regions:
                clipped=[]
                for r in regions:
                    for key in ('box','numbers'):
                        a,b,c,d=r[key];r[key]=[max(0,a),max(0,b),min(image.width,c),min(image.height,d)]
                    if r['numbers'][2]>r['numbers'][0] and r['numbers'][3]>r['numbers'][1]:clipped.append(r)
                # Use positional evidence to choose a crop, not to accept its
                # value. The full literal counter is verified independently.
                provisional=[dict(r,current=r['os_pair'][0],maximum=r['os_pair'][1],votes=2) for r in clipped]
                chosen=None if all_candidates else place_selected({'anchor':anchor,'tools':provisional},image.height)
                if chosen:clipped=[r for r in clipped if r['numbers']==chosen['numbers']]
                if clipped:return clipped,anchor,1
            self.last_error='No complete anchored counter from Windows OCR'
        except (RuntimeError,ValueError,OSError) as exc:self.last_error=str(exc)[:200]
        # Availability and recognition failures retain the conservative released
        # route. The failure remains visible to diagnostics, not an invented read.
        return discover_scene(image,tess,focused=focused)


def recognize_quest_structured(image,tess,worker,diagnostic=None):
    """OS-positioned card + an independent literal body read, else safe fallback."""
    import io
    import subprocess
    from PIL import ImageOps
    from guild_quest import guild_heading_family,parse_quest_text,parse_objectives,recognize_quest
    from ocr_runtime import run_ocr
    from guild_reminder import explicit_absence
    try:
        scale=min(2.,math.sqrt(1400000/(image.width*image.height)))
        frame=ImageOps.autocontrast(image.convert('L')).resize((int(image.width*scale),int(image.height*scale)))
        result=worker.recognize(frame,timeout=1.5);raw=result['text']
        if explicit_absence(raw):
            blob=io.BytesIO();frame.save(blob,format='PNG')
            response=run_ocr([tess,'stdin','stdout','--psm','6','-l','eng'],input=blob.getvalue(),capture_output=True,timeout=1.2)
            text=response.stdout.decode('utf-8','replace')[:6000] if not response.returncode else ''
            if explicit_absence(text):
                return {'absence_observed':True,'absence_votes':2,'absence_evidence':explicit_absence(raw),'reader_path':'Independent engines · explicit no-mission message'},raw+'\n\nINDEPENDENT VERIFICATION\n'+text
        groups={}
        for w in result['words']:groups.setdefault(w['line'],[]).append(w)
        headers=[(line,words) for line,words in groups.items() if guild_heading_family(' '.join(w['text'] for w in words))]
        if diagnostic:diagnostic(frame,'POSITIONED WINDOWS OCR\n'+raw)
        for line,words in headers[:1]:
            header=' '.join(w['text'] for w in words);kind=guild_heading_family(header)
            top=max(0,int(min(w['y'] for w in words)/scale)-5)
            bottom=min(image.height,int(max(w['y']+w['h'] for w in words)/scale)+135)
            for other,ws in groups.items():
                text=' '.join(w['text'] for w in ws)
                if other>line and (re.search(r'\[(?:Daily|Bonus|Weekly|Main)\]',text,re.I) or guild_heading_family(text)):
                    bottom=min(bottom,max(top+1,int(min(w['y'] for w in ws)/scale)-3));break
            scoped='\n'.join(' '.join(w['text'] for w in ws) for k,ws in groups.items() if k>=line and min(w['y'] for w in ws)/scale<bottom)
            first=parse_quest_text(scoped)
            if not first:continue
            crop=image.crop((0,top,image.width,bottom))
            prepared=ImageOps.autocontrast(crop.convert('L')).resize((crop.width*3,crop.height*3))
            blob=io.BytesIO();prepared.save(blob,format='PNG')
            response=run_ocr([tess,'stdin','stdout','--psm','6','-l','eng'],input=blob.getvalue(),capture_output=True,timeout=1.2)
            if response.returncode:continue
            text=response.stdout.decode('utf-8','replace')[:6000]
            # Card identity is supplied by the independent positioned heading;
            # the second engine must read the objective and counter itself.
            second=parse_quest_text('['+kind.title()+'] Guild Supply Mission\n'+text)
            if diagnostic:diagnostic(prepared,'INDEPENDENT CARD VERIFICATION\n'+text)
            identity=quest_objective_identity
            if first and second and (first['current'],first['target'])==(second['current'],second['target']) and identity(first)==identity(second):
                left={r['key']:r for r in parse_objectives(raw)};right={r['key']:r for r in parse_objectives(text)}
                objectives=[r for k,r in left.items() if k in right and (r['current'],r['target'])==(right[k]['current'],right[k]['target'])]
                return {**first,'label':header.replace('\ufffd',''),'card_box':[0,top,image.width,bottom],'objectives':objectives,'reader_path':'Positioned Windows OCR + independent guild-card verification'},raw+'\n\nINDEPENDENT VERIFICATION\n'+text
    except (RuntimeError,ValueError,OSError,KeyError,TimeoutError,subprocess.TimeoutExpired):pass
    return recognize_quest(image,tess,diagnostic=diagnostic)
