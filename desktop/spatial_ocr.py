"""Pure OCR parsing and spatial selection for Black Desert tool labels.

Tesseract returns multiple readings when several utensils are visible. We locate
all readings, group repeated recognition around the same screen position, and
prefer the tool whose durability label is closest to the player anchor.

No game memory reads, hooking or keyboard/mouse automation is used.
"""
from collections import defaultdict
import csv
import io
import re

PAIR = re.compile(r"(?<!\d)(\(?\s*)(\d{1,6})\s*\)?\s*[/|]\s*(\d{1,6})(?!\d)")
TOOL_WORDS = re.compile(r"tool|utensil|cooking|alchemy", re.I)


def parse_pairs(text):
    """Extract (current, maximum, explicit_opening_bracket) from OCR text."""
    results = []
    for match in PAIR.finditer(text):
        current, maximum = int(match.group(2)), int(match.group(3))
        if maximum > 0 and current <= maximum:
            results.append((current, maximum, '(' in match.group(1)))
    return results


def choose_pair(readings, expected=None, expected_max=None):
    """Vote on conflicting OCR readings, using brackets and the timer as evidence."""
    scores = defaultdict(float)
    votes = defaultdict(int)
    bracket_seen = set()
    parsed = []
    for raw in readings:
        for current, maximum, bracket in parse_pairs(raw):
            parsed.append((current, maximum, bracket))
            key = (current, maximum)
            scores[key] += 5.0 if bracket else 2.0
            votes[key] += 1
            if bracket:
                bracket_seen.add(key)
    if not parsed:
        return None
    for (current, maximum), score in list(scores.items()):
        if maximum == expected_max:
            scores[(current, maximum)] += .7
    for current, maximum, bracket in parsed:
        digits = str(current)
        if bracket or not (digits.startswith('1') and len(digits) >= 4):
            continue
        alternate = (int(digits[1:]), maximum)
        if alternate in bracket_seen:
            scores[alternate] += 4
        elif expected is not None and (expected_max is None or maximum == expected_max):
            margin = max(18., min(90., maximum*.02))
            if abs(alternate[0]-expected) <= margin and abs(current-expected) > max(100, maximum*.12):
                scores[alternate] += 3.3
    chosen = max(scores, key=lambda key:(scores[key], votes[key]))
    return chosen[0],chosen[1],votes.get(chosen,0),chosen not in votes


def tsv_candidates(tsv, x_offset=0, y_offset=0, scale=1, pass_name='scan'):
    """Return positioned durability candidates from a Tesseract TSV result.

    Matches single tokens like Tool(350/3000) and adjacent tokens like
    'Tool(' '350/3000)'. Coordinates are in SCREEN pixels, not enlarged pixels.
    """
    tokens=[]
    try:
        for row in csv.DictReader(io.StringIO(tsv), delimiter='\t'):
            if row.get('level') != '5' or not row.get('text','').strip():
                continue
            try:
                left,top,width,height=[int(row[k]) for k in ('left','top','width','height')]
                conf=float(row.get('conf','-1'))
            except (ValueError,TypeError,KeyError):
                continue
            tokens.append({'text':row['text'].strip(), 'left':left, 'top':top,
                           'right':left+width, 'bottom':top+height, 'conf':conf})
    except Exception:
        return []
    candidates=[]
    seen=set()
    # The label can be broken across OCR blocks, so use nearby words even
    # when Tesseract placed them in different TSV line/block groups.
    for i,t in enumerate(tokens):
        nearby=[t]
        for j in range(i+1,min(i+5,len(tokens))):
            other=tokens[j]
            if abs(other['top']-t['top'])>max(18*scale,(t['bottom']-t['top'])*1.6):
                break
            if other['left']-nearby[-1]['right']>55*scale:
                break
            nearby.append(other)
        for length in range(1,len(nearby)+1):
            group=nearby[:length]
            txt=' '.join(w['text'] for w in group)
            matches=list(PAIR.finditer(txt))
            for match in matches:
                value,maximum=int(match.group(2)),int(match.group(3))
                if not 0<=value<=maximum or maximum<100 or maximum>1000000:
                    continue
                # Estimate where the numeric pair appears in this text group.
                # Character widths vary, but this is far better than assuming
                # every number is located in the centre of the entire tile.
                char_at=0
                pair_left=group[0]['left']
                pair_right=group[-1]['right']
                for word in group:
                    length_chars=len(word['text'])
                    if char_at<=match.start(2)<char_at+length_chars:
                        ratio=(match.start(2)-char_at)/max(1,length_chars)
                        pair_left=word['left']+ratio*(word['right']-word['left'])
                    if char_at<=match.end(3)-1<char_at+length_chars:
                        ratio=(match.end(3)-char_at)/max(1,length_chars)
                        pair_right=word['left']+ratio*(word['right']-word['left'])
                    char_at+=length_chars+1
                center_x=x_offset+((pair_left+pair_right)/2)/scale
                center_y=y_offset+(min(w['top'] for w in group)+max(w['bottom'] for w in group))/2/scale
                bracket='(' in match.group(1)
                nearby_text=' '.join(w['text'] for w in tokens if
                    abs(w['top']-t['top'])<30*scale and
                    abs(w['left']-t['left'])<300*scale)
                tool=bool(TOOL_WORDS.search(nearby_text))
                key=(round(center_x/7),round(center_y/7),value,maximum,pass_name)
                if key in seen:continue
                seen.add(key)
                candidates.append({'current':value,'maximum':maximum,
                    'x':center_x,'y':center_y,'bracket':bracket,'tool':tool,
                    'confidence':max(-1, sum(w['conf'] for w in group)/len(group)),
                    'pass':pass_name})
    return candidates


def choose_spatial_pair(candidates, anchor_x, expected=None, expected_max=None,
                        anchor_y=None, previous_x=None):
    """Choose the target label, returning (current,max,votes,corrected,x,y).

    * Centre/character proximity is PRIMARY to prevent reading other utensils.
    * Multiple OCR variants of the same label vote on the actual digits.
    * A spurious leading '1' is corrected only with corroborating evidence.
    * We do not guess when the nearest label has insufficient recognition.
    """
    valid=[c for c in candidates if c['maximum']>=100 and 0<=c['current']<=c['maximum']]
    if not valid:return None
    # Cluster observations of the same label by on-screen position + max size.
    clusters=[]
    for c in sorted(valid,key=lambda v:abs(v['x']-anchor_x)):
        group=next((g for g in clusters if g['maximum']==c['maximum'] and
                    abs(g['x']-c['x'])<=86 and abs(g['y']-c['y'])<=42),None)
        if group is None:
            group={'x':c['x'],'y':c['y'],'maximum':c['maximum'],'members':[]}
            clusters.append(group)
        group['members'].append(c)
        n=len(group['members'])
        group['x']+=(c['x']-group['x'])/n
        group['y']+=(c['y']-group['y'])/n
    ranked=[]
    for group in clusters:
        members=group['members']
        # Deduplicate repeated TSV extraction of the same visual token in one pass.
        uniq={}
        for c in members:
            key=(c['pass'],c['current'],c['maximum'])
            old=uniq.get(key)
            if old is None or c['confidence']>old['confidence']:uniq[key]=c
        members=list(uniq.values())
        raw=[('(' if c['bracket'] else '')+str(c['current'])+'/'+str(c['maximum']) for c in members]
        pair=choose_pair(raw,expected=expected,expected_max=expected_max)
        if not pair:continue
        current,maximum,votes,corrected=pair
        proximity=abs(group['x']-anchor_x)
        # Optional y target only to break close horizontal ties.
        if anchor_y is not None:proximity+=abs(group['y']-anchor_y)*.12
        # A confirmed actual label near player beats a background number.
        tool_bonus=40 if any(c['tool'] for c in members) else 0
        confidence=max((c['confidence'] for c in members),default=0)
        support=len(set(c['pass'] for c in members))
        # Bad OCR in one centre tile must not beat an adjacent, well-confirmed label.
        quality=min(45,support*12)+min(20,max(0,confidence)/5)+tool_bonus
        rank=proximity-quality
        ranked.append((rank,-support,-confidence,current,maximum,votes,corrected,group['x'],group['y']))
    if not ranked:return None
    ranked.sort()
    _,_,_,value,maximum,votes,corrected,x,y=ranked[0]
    return value,maximum,votes,corrected,x,y
