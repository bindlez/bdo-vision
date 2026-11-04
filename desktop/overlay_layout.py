"""Small, deterministic overlay layout. No windows, captures or background work."""
from collections import deque
import math
import time

GAP = 10
SNAP = 20
DEFAULTS = {'corner': 'top-right', 'density': 'Compact', 'locked': False,
            'motion': True, 'sound': False, 'seconds': 7}


def preferences(raw):
    raw = raw if isinstance(raw, dict) else {}
    result = dict(DEFAULTS)
    if raw.get('corner') in ('top-right', 'top-left', 'bottom-right', 'bottom-left', 'custom'):
        result['corner'] = raw['corner']
    if raw.get('density') in ('Compact', 'Comfortable'):result['density'] = raw['density']
    for key in ('locked', 'motion', 'sound'):
        if type(raw.get(key)) is bool:result[key] = raw[key]
    if type(raw.get('seconds')) is int and raw['seconds'] in (7, 10, 14):result['seconds'] = raw['seconds']
    position = raw.get('position')
    if isinstance(position, (list, tuple)) and len(position) == 2 and all(type(n) is int and abs(n) <= 100000 for n in position):
        result['position'] = list(position)
    return result


def clamp(rect, area):
    x, y, w, h = rect;left, top, right, bottom = area
    w = min(w, max(1, right-left-2*GAP));h = min(h, max(1, bottom-top-2*GAP))
    return (max(left+GAP, min(x, right-w-GAP)), max(top+GAP, min(y, bottom-h-GAP)), w, h)


def dock(size, area, corner='top-right', position=None):
    w, h = size;left, top, right, bottom = area
    if corner == 'custom' and position is not None:return clamp((*position, w, h), area)
    return clamp((left+GAP if corner.endswith('left') else right-w-GAP,
                  top+GAP if corner.startswith('top') else bottom-h-GAP, w, h), area)


def snap(rect, area):
    x, y, w, h = clamp(rect, area);left, top, right, bottom = area
    for edge in (left+GAP, right-w-GAP):
        if abs(x-edge) <= SNAP:x = edge
    for edge in (top+GAP, bottom-h-GAP):
        if abs(y-edge) <= SNAP:y = edge
    corner = ('top' if y == top+GAP else 'bottom' if y == bottom-h-GAP else '')
    side = ('left' if x == left+GAP else 'right' if x == right-w-GAP else '')
    return (x, y, w, h), corner+'-'+side if corner and side else 'custom'


def overlap(a, b):
    return max(0, min(a[0]+a[2], b[0]+b[2])-max(a[0], b[0])) * max(0, min(a[1]+a[3], b[1]+b[3])-max(a[1], b[1]))


def tile(size, area, obstacle=None, corner='top-right'):
    """Try adjacent lanes, then corners; minimize obstruction on tiny monitors."""
    base = dock(size, area, corner)
    if obstacle is None:return base
    obstacles=[obstacle] if len(obstacle)==4 and isinstance(obstacle[0],(int,float)) else obstacle
    candidates=[];tw,th=size
    for x,y,w,h in obstacles:
        candidates += [(x,y+h+GAP,tw,th),(x,y-th-GAP,tw,th),(x-tw-GAP,y,tw,th),(x+w+GAP,y,tw,th)]
    candidates += [dock(size,area,c) for c in ('top-right','top-left','bottom-right','bottom-left')]
    candidates=[clamp(c,area) for c in candidates]
    return min(candidates,key=lambda c:sum(overlap(c,o) for o in obstacles))



class RevealQueue:
    """One reveal + at most four waiting moments; stale UI never changes history."""
    def __init__(self, clock=time.monotonic):
        self.clock = clock;self.pending = deque(maxlen=4);self.seen = deque(maxlen=64)

    def add(self, event):
        ident = event.get('id')
        if ident is not None and ident in self.seen:return False
        if ident is not None:self.seen.append(ident)
        self.pending.append((self.clock(), dict(event)));return True

    def take(self):
        now = self.clock()
        while self.pending:
            stamp, event = self.pending.popleft()
            if now-stamp <= 25:return event
        return None

    def clear(self):self.pending.clear()


def compact_silver(value):
    if type(value) not in (int, float) or not math.isfinite(value):return '—'
    if abs(value) >= 1e9:return f'{value/1e9:,.2f}B'
    if abs(value) >= 1e6:return f'{value/1e6:,.1f}M'
    if abs(value) >= 1e3:return f'{value/1e3:,.1f}K'
    return f'{value:,.0f}'
