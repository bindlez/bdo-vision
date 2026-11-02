"""Event-driven rare-drop journal. No capture, polling, network or inferred loot."""
import json,math,re,time
from datetime import datetime

KABUA_SOURCE='https://www.naeu.playblackdesert.com/en-us/News/Detail?countryType=en-us&groupContentNo=6254'
TREASURE_SOURCE='https://blackdesert.pearlabyss.com/Asia/en-US/Game/Wiki?_masterWikiNo=109'


def key(name):
    return ' '.join(str(name).replace('\u2019',"'").casefold().split())


def spot_key(name):
    value=re.sub(r'[^a-z0-9]','',str(name).casefold())
    return {'darkseekersretreat':'darkseeker','darkseekerretreat':'darkseeker','dsr':'darkseeker',
            'darkseekers':'darkseeker','yzrahidhighlands':'yzrahid','yzrahid':'yzrahid'}.get(value,value)


def entry(name,kind,detail,spots=(),source=TREASURE_SOURCE):
    return {'item':name,'category':kind,'detail':detail,'spots':list(spots),'source':source,'global_odds':None}


CATALOG=[
    entry("Kabua's Artifact",'Jackpot',"Full artifact, not Kabua's Fragment. A tradable equipment drop; 100 fragments are an alternative crafting ingredient.",('darkseeker','yzrahid'),KABUA_SOURCE),
    entry("Archaeologist's Map Piece",'Treasure',"A component for the Archaeologist's Map. Text alone does not identify which map-piece variant dropped.",('roadsulfurmine','pilakujail')),
    entry("Lafi Bedmountain's Upgraded Compass Parts",'Treasure',"Compass component family. Identical text can represent different pieces; this tracker does not label it as the Elten piece.",('hystriaruins','aakmantemple')),
    entry('Upgraded Compass Parts','Treasure','Compass component family; exact piece variant is unknown from text alone.',('hystriaruins','aakmantemple')),
    entry("Lafi Bedmountain's Upgraded Telescope Parts",'Treasure','Telescope component family. A collection milestone; the exact variant is not inferred from text.',('darkseeker','tungradruins','cityofthedead')),
    entry("Rich Merchant's Ring Piece",'Treasure','A component for a long-term treasure. The piece variant cannot be determined from this item name alone.'),
]
for item in ("Sherekhan's Panacea","Ron's Tintinnabulum",'Ash Halfmoon Kagtunak',"Valtarra's Clairvoyance","Markthanan's Gland","Narc's Crimson Tear"):
    CATALOG.extend((entry(item,'Treasure','Full infinite-potion material; distinct from smaller pity materials.'),entry('Ancient '+item,'Treasure','Ancient full infinite-potion material; distinct from smaller pity materials.')))
BY_NAME={key(row['item']):row for row in CATALOG}
ITEM_NAMES=tuple(dict.fromkeys(name for row in CATALOG for name in (row['item'],row['item'].replace("'",'\u2019'))))
PLACEHOLDERS={'','unnamedgrindspot','unspecifiedspot','untitledrun'}


def classify(name,kind='Drop',quote=None):
    if kind in ('Crafted','Rare craft'):return None
    special=BY_NAME.get(key(name));price=quote.get('unit_price') if quote else None
    valid=type(price) in (int,float) and math.isfinite(price) and price>1_000_000_000
    if not special and not valid:return None
    result=dict(special or entry(str(name),'Big Drop','A high-value individual item, identified through your existing market quote.',source='https://na-trade.naeu.playblackdesert.com/'))
    result['category']='Huge Drop' if valid and price>10_000_000_000 else 'Big Drop' if valid else 'Treasure' if special['category']=='Treasure' else 'Spotlight'
    result['treasure']=bool(special and special['category']=='Treasure')
    return result


def heat(events,seconds,baseline=None,available=True,ended=False,count=None,recent=None):
    """Retrospective pace/cluster rating, never a change in future drop odds."""
    events=[e for e in events if e.get('observed_seconds') is not None]
    count=len(events) if count is None else count
    ratio=None;basis='Recorded-drop momentum';score=0;title='READY FOR A SPARK'
    note='Every accepted big drop gets a place in your journal.'
    usable=baseline and baseline['runs']>=3 and baseline['seconds']>=7200 and baseline['hits']>=5 and seconds>=300
    if usable:
        expected=baseline['hits']*seconds/baseline['seconds'];ratio=count/expected if expected else None
        basis=f"Your history · {baseline['runs']} completed runs · {baseline['hits']} big-drop events"
        score=min(100,round(20*ratio)) if ratio is not None else 0
        title='INFERNO' if ratio>=5 else 'ON FIRE' if ratio>=3 else 'HOT' if ratio>=2 else 'WARMING UP' if count else 'READY FOR A SPARK'
        note=f"{ratio:.1f}× your recorded big-drop pace at this spot. Capture gaps excluded."
    elif count:
        recent=sum(0<=seconds-e['observed_seconds']<=900 for e in events) if recent is None else recent
        score=min(100,30+25*max(0,recent-1));title='ON FIRE' if recent>=3 else 'HOT' if recent>=2 else 'SPARK'
        note=('Three big-drop events inside 15 observed minutes.' if recent>=3 else 'Two big-drop events inside 15 observed minutes.' if recent>=2 else 'A big moment. Keep building your personal rarity history.')
        if recent==0:title='SPARK';score=20
    fire=title in ('ON FIRE','INFERNO')
    if not available and not ended:
        note+=' Capture paused; this is the last measured heat.'
    return {'title':title,'score':score,'ratio':ratio,'basis':basis,'note':note,'on_fire':fire,
            'message':"You're on fire. Strike while the iron is hot!" if fire else 'A run worth remembering.' if count else 'Your next chapter starts with a drop.',
            'footnote':'A celebration of recorded luck. Your next-drop chance is unchanged.'}


class BigDropBook:
    def __init__(self,db):
        self.db=db;self._cache_key=None;self._cache=None;self.revision=0;self._prices=None;self.names=ITEM_NAMES
        db.execute('CREATE TABLE IF NOT EXISTS big_drop_moments (loot_id INTEGER PRIMARY KEY, session_id TEXT, observed_seconds REAL)')
        db.commit()

    def _names_for(self,prices):
        if prices is self._prices:return
        self._prices=prices;names=set(ITEM_NAMES)
        for name,quote in prices.items():
            if classify(name,quote=quote):
                resolved=quote.get('market_name') or name
                names.update((name,resolved,resolved.replace("'",'\u2019')))
        self.names=tuple(sorted(names));self._cache_key=None

    def observe(self,loot_id,session,prices=None,moment=None):
        prices={} if prices is None else prices;self._names_for(prices)
        row=self.db.execute('SELECT id,recorded_at,item,quantity,source,session,kind FROM loot WHERE id=?',(loot_id,)).fetchone()
        identity=classify(row[2],row[6],prices.get(row[2])) if row else None
        if not identity:return None
        member=self.db.execute('SELECT m.session FROM insight_members m JOIN insight_sessions s ON s.id=m.session WHERE m.loot_id=? AND s.activity IN (\'Grinding\',\'Treasure hunt\') ORDER BY s.created_at DESC LIMIT 1',(loot_id,)).fetchone()
        selected=member[0] if member else None
        seconds=session.clock.seconds if selected and selected==session.id else None
        if moment is not None and selected is not None and selected==moment[0]:seconds=moment[1]
        with self.db:
            inserted=self.db.execute('INSERT OR IGNORE INTO big_drop_moments VALUES (?,?,?)',(loot_id,selected,seconds)).rowcount
        if not inserted:return None
        self._cache_key=None;self.revision+=1
        return {'id':row[0],'at':row[1],'item':row[2],'quantity':row[3],'category':identity['category'],'observed_seconds':seconds}

    def _load(self,revision,session):
        cache_key=(self.revision,session.id,session.ended,self.names)
        if cache_key==self._cache_key:return self._cache
        slots=','.join('?' for _ in self.names);condition=f"l.item COLLATE NOCASE IN ({slots}) AND l.kind NOT IN ('Crafted','Rare craft')"
        rows=self.db.execute(f'SELECT l.id,l.recorded_at,l.item,l.quantity,l.kind,b.session_id,b.observed_seconds FROM loot l LEFT JOIN big_drop_moments b ON b.loot_id=l.id WHERE {condition} ORDER BY l.id DESC LIMIT 40',self.names).fetchall()
        totals=self.db.execute(f'SELECT l.item,SUM(l.quantity),COUNT(*),MIN(l.recorded_at),MAX(l.recorded_at) FROM loot l WHERE {condition} GROUP BY l.item',self.names).fetchall()
        # Zero-drop sessions are deliberately included in the denominator.
        runs=self.db.execute("SELECT s.id,s.active_seconds,s.created_at,s.ended_at,COALESCE(d.spot,s.label),COUNT(l.id) FROM insight_sessions s LEFT JOIN grind_details d ON d.session=s.id LEFT JOIN insight_members m ON m.session=s.id LEFT JOIN loot l ON l.id=m.loot_id AND "+condition+" WHERE s.activity IN ('Grinding','Treasure hunt') AND s.ended_at IS NOT NULL GROUP BY s.id ORDER BY s.created_at DESC LIMIT 200",self.names).fetchall()
        # Read membership for retained observations; do not invent their time-to-drop.
        oldest=min((r[0] for r in rows),default=0)
        memberships={r[0]:r[1] for r in self.db.execute(f'SELECT l.id,m.session FROM loot l JOIN insight_members m ON m.loot_id=l.id JOIN insight_sessions s ON s.id=m.session WHERE {condition} AND l.id>=? AND s.activity IN (\'Grinding\',\'Treasure hunt\') ORDER BY s.created_at',(*self.names,oldest))} if rows else {}
        compare_names=tuple(dict.fromkeys((*ITEM_NAMES,*(r[2] for r in rows))))
        run_ids=tuple(r[0] for r in runs);item_runs={}
        if run_ids:
            item_slots=','.join('?' for _ in compare_names);run_slots=','.join('?' for _ in run_ids)
            grouped=self.db.execute(f"SELECT l.item,m.session,COUNT(*) FROM loot l JOIN insight_members m ON m.loot_id=l.id WHERE m.session IN ({run_slots}) AND l.item COLLATE NOCASE IN ({item_slots}) AND l.kind NOT IN ('Crafted','Rare craft') GROUP BY l.item,m.session",(*run_ids,*compare_names))
            for name,run,hits in grouped:
                values=item_runs.setdefault(key(name),{});values[run]=values.get(run,0)+hits
        self._cache=(rows,totals,runs,memberships,item_runs);self._cache_key=cache_key;return self._cache

    def snapshot(self,revision,session,prices,available=False):
        self._names_for(prices)
        rows,totals,runs,memberships,item_runs=self._load(revision,session)
        meta=self.db.execute('SELECT activity,label,ended_at,created_at FROM insight_sessions WHERE id=?',(session.id,)).fetchone() if session.id else None
        grind=bool(meta and meta[0] in ('Grinding','Treasure hunt'));seconds=session.clock.seconds if grind else 0
        detail=self.db.execute('SELECT spot FROM grind_details WHERE session=?',(session.id,)).fetchone() if grind else None
        spot=spot_key(detail[0] if detail else meta[1]) if grind else ''
        # For a saved session, future runs must never become its prior baseline.
        peers=[r for r in runs if grind and r[0]!=session.id and r[3]<=meta[3] and spot_key(r[4])==spot and spot not in PLACEHOLDERS and r[1]>=300 and r[1]/max(1,r[3]-r[2])>=.8]
        baseline={'runs':len(peers),'seconds':sum(r[1] for r in peers),'hits':sum(r[5] for r in peers)}
        journal=[];counts={}
        for name,quantity,hits,first,last in totals:
            previous=counts.setdefault(key(name),{'quantity':0,'events':0,'first_at':first,'last_at':last})
            previous['quantity']+=quantity;previous['events']+=hits;previous['first_at']=min(first,previous['first_at']);previous['last_at']=max(last,previous['last_at'])
        for ident,at,name,quantity,kind,linked,observed in rows:
            special=BY_NAME.get(key(name));quote=prices.get(name) or prices.get(special['item']) if special else prices.get(name)
            item=classify(name,kind,quote)
            if not item:continue
            value=quote.get('unit_price') if quote else None
            journal.append({'id':ident,'at':at,'item':name,'quantity':quantity,'category':item['category'],'detail':item['detail'],'source':item['source'],
                            'session_id':linked or memberships.get(ident),'observed_seconds':observed,'unit_price':value,'value':value*quantity if value is not None else None,
                            'price_source':quote.get('source','Unpriced') if quote else 'Unpriced','lifetime_units':counts[key(name)]['quantity'],'first_at':counts[key(name)]['first_at']})
        slots=','.join('?' for _ in self.names)
        counts_now=self.db.execute(f"SELECT COUNT(*),COALESCE(SUM(l.quantity),0),COALESCE(SUM(CASE WHEN b.observed_seconds BETWEEN ? AND ? THEN 1 ELSE 0 END),0) FROM loot l JOIN insight_members m ON m.loot_id=l.id LEFT JOIN big_drop_moments b ON b.loot_id=l.id AND b.session_id=m.session WHERE m.session=? AND l.item COLLATE NOCASE IN ({slots}) AND l.kind NOT IN ('Crafted','Rare craft')",(seconds-900,seconds,session.id,*self.names)).fetchone() if grind else (0,0,0)
        coverage=seconds/max(1,(meta[2] or time.time())-meta[3]) if grind else 0
        qualified=baseline if coverage>=.8 else None
        rating=heat([],seconds,qualified,available,session.ended,count=counts_now[0],recent=counts_now[2]) if grind else heat([],0)
        if not grind and journal:
            rating.update(title='TROPHY SECURED',score=30,basis='Drop journal · no measured grind session',note='Start a grind session to measure your own pace and heat.',message='A big moment. Yours to keep.')
        comparisons=[];compare_catalog=list(CATALOG)
        for row in journal:
            if key(row['item']) not in BY_NAME:compare_catalog.append(classify(row['item'],quote=prices.get(row['item'])))
        seen=set()
        for item in compare_catalog:
            if not item or key(item['item']) in seen:continue
            seen.add(key(item['item']))
            own=counts.get(key(item['item']),{})
            hits=item_runs.get(key(item['item']),{})
            locations=set(item['spots'])|{spot_key(r[4]) for r in runs if hits.get(r[0],0)}
            samples=[r for r in runs if spot_key(r[4]) in locations and spot_key(r[4]) not in PLACEHOLDERS and r[1]>=300 and r[1]/max(1,r[3]-r[2])>=.8 and (not grind or r[3]<=meta[3])]
            observed=sum(r[1] for r in samples);found=sum(hits.get(r[0],0) for r in samples)
            enough=len(samples)>=3 and observed>=7200 and found>=3
            comparisons.append({**item,'lifetime_units':own.get('quantity',0),'events':own.get('events',0),'first_at':own.get('first_at'),
                                'personal_hours_per_event':observed/3600/found if enough else None,'sample_runs':len(samples),'sample_hours':round(observed/3600,2),'sample_events':found,
                                'comparison':'Global odds not established here; no numerical rarity ranking is claimed.'})
        return {'journal':journal,'latest':journal[0] if journal else None,'heat':rating,'baseline':baseline,
                'session_id':session.id if grind else None,'observed_seconds':seconds,'current_events':counts_now[0],'current_units':counts_now[1],
                'lifetime_events':sum(r['events'] for r in counts.values()),'lifetime_units':sum(r['quantity'] for r in counts.values()),
                'comparisons':comparisons,'basis':'Accepted recorded loot only. Personal pace is not a global drop probability. Historical timing is unknown unless captured by Big Drops.'}
