"""Read personal item notifications without treating other players' drops as ours."""
import re
from dataclasses import dataclass,field
from collections import Counter
from item_names import canonical_item,EXACT,known_item


@dataclass(frozen=True)
class ItemEvent:
    item: str
    quantity: int
    kind: str
    stamp: str = ''
    quantity_explicit: bool = field(default=True,compare=False)


def joined_messages(text):
    """BDO wraps item names and xN quantities onto separate physical lines."""
    output=[];current=''
    for raw in text.splitlines():
        line=' '.join(raw.replace('\ufffd',' ').split()).strip()
        if not line:continue
        if re.fullmatch(r'\[?system\]?\W*',line,re.I):continue
        # The outlined System badge can leave punctuation on either side.
        # Strip only that badge immediately before a personal receipt.
        line=re.sub(r'^\W{0,5}system\W{0,6}(?=you\s*(?:have|obtained|received|acquired|produced|crafted|created))','',line,flags=re.I)
        start=re.search(r'you\s*(?:have\s*)?(?:successfully\s*)?(?:obtained|received|acquired|produced|crafted|created)|^(?:(?:successfully\s+)?(?:obtained|received|produced|crafted)\b|(?:crafting|production)\s+(?:succeeded|complete)\b|\[?(?:rare item drop|item drop|crafting|production)\]?)',line,re.I)
        if start:
            if current:output.append(current)
            current=line
        elif current and (re.match(r'^[xX×]\s*\d[\d,]*\s*[.!]?\s*$',line) or (current.count('[')>current.count(']') and len(current)<180)):
            current+=' '+line
        elif not current:
            output.append(line)
    if current:output.append(current)
    return output


def notification_quantity(raw):
    """Only complete English integer counts; never truncate decimal/noisy fields."""
    if len(raw)>9 or not re.fullmatch(r'(?:[1-9]\d{0,6}|[1-9]\d{0,2}(?:,\d{3}){1,2})',raw):return None
    count=int(raw.replace(',',''))
    return count if count<=1_000_000 else None


def item_brackets(line):
    """Return the first complete item boundary and status text outside brackets."""
    depth=0;end=None;outside=[]
    for index,char in enumerate(line):
        if char=='[':depth+=1
        elif char==']' and depth:
            depth-=1
            if depth==0 and end is None:end=index
        elif not depth:outside.append(char)
    return end,''.join(outside)


def parse_events(text, crafting=False, rare_feed=False, bare_items=False):
    events=[]
    for raw in joined_messages(text):
        line=' '.join(raw.replace('×','x').replace('’',"'").replace('‘',"'").split()).strip()
        line=re.sub(r'^[\W_]{1,3}(?=you\s*(?:have|obtained|received))','',line,flags=re.I)
        # Notification fonts commonly turn a trailing 1 into a vertical stroke.
        # Apply this only to the quantity field, before testing the bare-item form.
        line=re.sub(r'([xX])\s*[|Il](?=[.!:\s]*$)',r'\1 1',line)
        if bare_items:
            line=re.sub(r'(?<=[A-Za-z\]])[xX](?=\s*\d)', ' x',line)
            line=line.lstrip('—–:| \t')
        stamp=''
        timestamp=re.match(r'^\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?\s*',line)
        if timestamp:
            stamp=timestamp[1];line=line[timestamp.end():]
        kind='Drop'
        tag=re.match(r'^\[?(Rare Item Drop|Item Drop|Private Item|Personal Item|System|Crafting|Production)(?!\s+(?:succeeded|complete)\b)\]?\s*:?\s*',line,re.I)
        tagged=False
        if tag:
            label=tag[1].lower();line=line[tag.end():].lstrip(' ’‘"™:');tagged=label in ('rare item drop','item drop','crafting','production')
            if label=='rare item drop':kind='Rare drop'
            elif label in ('crafting','production'):kind='Crafted'
        verb=re.match(r'^(?:you\s*(?:have\s*)?(?:successfully\s+)?(obtained|received|acquired|produced|crafted|created)|(?:successfully\s+)?(obtained|received|produced|crafted)|(?:crafting|production)\s+(?:succeeded|complete))\s*:?\s*',line,re.I)
        if verb:
            if any(word in verb[0].lower() for word in ('produc','craft','creat')):kind='Crafted'
            line=line[verb.end():]
        elif not tagged and not (bare_items and (re.search(r'\s[xX]\s*[\d,]+\b',line) or known_item(canonical_item(line.rstrip('.! '))))):
            continue
        # No verbs naming other players or an arbitrary chat speaker are accepted.
        if not line:continue
        line=line.rstrip('.! ')
        line=re.sub(r'([xX])\s*[|Il](?=[.!:\s]*$)',r'\1 1',line)
        # Item icons often become a stray OCR symbol immediately before '['.
        if '[' in line:
            prefix=line[:line.index('[')].strip()
            if len(prefix)<=3:line=line[line.index('['):]
        qty=1;explicit=False
        end,outside=item_brackets(line)
        before=re.match(r'^\[([\d,]+)\]\s+(.+)$',line)
        quantity_start=end+1 if line.startswith('[') and end is not None and not before else 0
        after=re.compile(r'\s*(?:(?:\s+|(?<=\]))[xX]\s*([\d,]+)(?![\w,]).*|\s*\(([\d,]+)\)|\s*\[([\d,]+)\])$').search(line,quantity_start)
        if before:
            explicit=True
            qty=notification_quantity(before[1]);line=before[2]
            if qty is None:continue
        elif after:
            explicit=True
            qty=notification_quantity(next(value for value in after.groups() if value))
            if qty is None:continue
            if after[1]:
                tail=line[after.end(1):]
                # A popup may include background words after the count. A
                # second number, bracket or slash is never safe suffix noise.
                punctuation=r'''[\s.!,:;—–"'|“”‘’_-]*'''
                suffix=punctuation+r"(?:[A-Za-z][A-Za-z '\u2019-]*)?" if bare_items else punctuation
                if not re.fullmatch(suffix,tail):continue
            line=line[:after.start()].strip()
        elif re.search(r'(?:\]|\s)[xX]\s*\S*|\([-\d,]+\)$',line[quantity_start:]):continue
        # Outlined text sometimes leaves a trailing dot/dash after an item with
        # no quantity (a genuine single drop). Never interpret a broken xN as 1.
        if line.startswith('[') and ']' in line:
            end=line.rfind(']')
            if re.fullmatch(r'[\s.!,:;—–-]*',line[end+1:]):line=line[:end+1]
        if line.startswith('[') and line.endswith(']'):line=line[1:-1].strip()
        line=canonical_item(line)
        if re.search(r'\b(?:has obtained|says|selling|failed|failure)\b',outside,re.I) and not known_item(line):continue
        if not 0<qty<=1_000_000 or not 1<=len(line)<=100 or not any(ch.isalpha() for ch in line):continue
        if re.fullmatch(r'[xX]\d+',line) or line.count('[')!=line.count(']'):continue
        if kind=='Drop':kind='Rare drop' if rare_feed else 'Crafted' if crafting else 'Drop'
        events.append(ItemEvent(line,qty,kind,stamp,explicit))
    return events


def agreed_events(readings):
    """Keep individual events agreed by >=2 passes; unrelated line errors don't block all."""
    if len(readings)<2:return []
    counts=[Counter(rows) for rows in readings]
    output=[]
    used=Counter()
    # Prefer the pass with the most readable events, preserving visible order.
    candidates=list(max(readings,key=len))
    for rows in readings:candidates.extend(rows)
    for event in candidates:
        support=sorted((count[event] for count in counts),reverse=True)
        limit=support[1]
        if used[event]<limit:
            output.append(event);used[event]+=1
    return output


class PopupSnapshots:
    """A changed notification counts once; stable notifications don't count again.

    An unreadable scan must not clear history. Only a visibly empty panel clears
    the baseline, so one OCR miss cannot turn an old notification into new loot.
    """
    def __init__(self,record_initial=False):
        self.previous=None
        self.record_initial=record_initial

    def ingest(self,rows,empty=False):
        if not rows:
            if empty:self.previous=[]
            return [],False
        old=self.previous
        self.previous=list(rows)
        if old is None:return (list(rows) if self.record_initial else []),False
        if old==rows:return [],False
        for size in range(min(len(old),len(rows)),0,-1):
            if old[-size:]==rows[:size]:return list(rows[size:]),False
        # A popup stack can completely replace itself, unlike scrolling chat.
        # Compare visible multiplicity so two identical rows remain two events.
        counts=Counter(old);fresh=[]
        for event in rows:
            if counts[event]:counts[event]-=1
            else:fresh.append(event)
        return fresh,False
