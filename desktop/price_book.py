"""Central Market quote cache populated by the existing paired site."""
import sqlite3
from contextlib import closing
from datetime import datetime
import threading,time,json,urllib.request,urllib.error
from pathlib import Path
from market_match import match_item,ItemDatabase,market_name_key
from item_names import canonical_item,EXACT,set_exact_resolver
from item_catalog import DiskItemDatabase
from vendor_prices import fetch_vendor_quote

class PriceBook:
    def __init__(self,path,recipes_path=None):
        self.path=str(path)
        self.refreshing=False;self.last_attempt=0;self.last_error='';self.last_refresh=0
        self._match_cache={};self._catalog_version=None
        self._item_database=None
        self._resolved_names={}
        self._noticed_items=set()
        self.revision=0;self._quote_cache={};self._quote_lock=threading.RLock()
        self._catalog_lock=threading.Lock();self._recipe_lock=threading.Lock();self._recipe_cache={}
        with closing(sqlite3.connect(self.path)) as db,db:
            db.execute('CREATE TABLE IF NOT EXISTS market_quotes (region TEXT NOT NULL, item TEXT NOT NULL, unit_price INTEGER NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(region,item))')
            db.execute('CREATE TABLE IF NOT EXISTS market_context (id INTEGER PRIMARY KEY CHECK(id=1), region TEXT NOT NULL)')
            db.execute("INSERT OR IGNORE INTO market_context VALUES (1,'NA')")
            db.execute('CREATE TABLE IF NOT EXISTS market_items (region TEXT NOT NULL, id INTEGER NOT NULL, name TEXT NOT NULL, category INTEGER, PRIMARY KEY(region,id))')
            db.execute('CREATE TABLE IF NOT EXISTS market_quote_details (region TEXT NOT NULL, id INTEGER NOT NULL, payload TEXT NOT NULL, PRIMARY KEY(region,id))')
            db.execute('CREATE TABLE IF NOT EXISTS vendor_quotes (id INTEGER PRIMARY KEY,name TEXT NOT NULL,unit_price INTEGER NOT NULL,updated_at TEXT NOT NULL,source_url TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS vendor_checks (id INTEGER PRIMARY KEY,checked_at REAL NOT NULL)')

    def all(self,region=None):
        # Callers treat snapshots as immutable. Own writes invalidate immediately;
        # the short TTL also picks up other connections without a resident watcher.
        cache_key=str(region or '').upper();now=time.monotonic()
        with self._quote_lock:
            generation=self.revision
            cached=self._quote_cache.get(cache_key)
            if cached and now-cached[0]<2:return cached[1]
        result=self._all_uncached(region)
        with self._quote_lock:
            if generation==self.revision:
                if cached and result==cached[1]:result=cached[1]
                self._quote_cache[cache_key]=(now,result)
        return result

    def _all_uncached(self,region=None):
        with closing(sqlite3.connect(self.path)) as db:
            region=(str(region).upper() if region else db.execute('SELECT region FROM market_context WHERE id=1').fetchone()[0])
            quotes={r[0]:{'unit_price':r[1],'source':'Central Market ('+region+')','updated_at':r[2],'market_name':r[0],'region':region} for r in db.execute('SELECT item,unit_price,updated_at FROM market_quotes WHERE region=? ORDER BY item',(region,))}
            catalog=[{'id':r[0],'name':r[1]} for r in db.execute('SELECT id,name FROM market_items WHERE region=?',(region,))]
            for ident,name,value,stamp,url in db.execute('SELECT id,name,unit_price,updated_at,source_url FROM vendor_quotes'):
                if name not in quotes:
                    quotes[name]={'unit_price':value,'source':'NPC vendor (BDO Codex)','updated_at':stamp,'market_name':name,'region':region,'item_id':ident,'price_basis':'npc_vendor','source_url':url}
                    if not any(i['id']==ident for i in catalog):catalog.append({'id':ident,'name':name})
            for item in catalog:
                if item['name'] in quotes:quotes[item['name']]['item_id']=item['id']
            for ident,payload in db.execute('SELECT id,payload FROM market_quote_details WHERE region=?',(region,)):
                detail=json.loads(payload)
                name=detail.get('name')
                if name in quotes and quotes[name].get('item_id')==ident:
                    quotes[name].update({k:detail[k] for k in ('stock','last_sold_price','last_sold_at','price_basis','source','source_updated_at','fourteen_day_volume','daily_volume') if k in detail})
            version=(region,len(catalog),max((q['updated_at'] for q in quotes.values()),default=''))
            if version!=self._catalog_version:self._match_cache={};self._catalog_version=version
            cache=self._match_cache
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='loot'").fetchone():
                for (raw,) in db.execute('SELECT DISTINCT item FROM loot'):
                    name=canonical_item(raw)
                    if name in quotes:continue
                    key=(version,name)
                    if key not in cache:cache[key]=match_item(name,catalog)
                    matched=cache[key]
                    if matched and matched['name'] in quotes:quotes[name]=dict(quotes[matched['name']])
            return quotes

    def update_market(self,items,region,activate=True):
        region=str(region).upper()
        if region not in ('NA','EU'):raise ValueError('Unknown market region')
        if not isinstance(items,list) or len(items)>2000:raise ValueError('Invalid market quote list')
        quotes=[];identities=[];stamp=datetime.now().astimezone().isoformat(timespec='seconds')
        for item in items:
            if not isinstance(item,dict):raise ValueError('Invalid market quote')
            name=' '.join(str(item.get('name','')).split());value=item.get('price')
            if not name or len(name)>100 or isinstance(value,bool) or not isinstance(value,int) or not 0<=value<=1_000_000_000_000:raise ValueError('Invalid market quote')
            if value>0:quotes.append((region,name,value,stamp))
            ident=item.get('id')
            if isinstance(ident,int) and not isinstance(ident,bool) and ident>0:identities.append((region,ident,name,item.get('category')))
        with closing(sqlite3.connect(self.path)) as db,db:
            db.executemany('INSERT INTO market_quotes VALUES (?, ?, ?, ?) ON CONFLICT(region,item) DO UPDATE SET unit_price=excluded.unit_price,updated_at=excluded.updated_at',quotes)
            if activate:db.execute('UPDATE market_context SET region=? WHERE id=1',(region,))
            db.executemany('INSERT INTO market_items VALUES (?, ?, ?, ?) ON CONFLICT(region,id) DO UPDATE SET name=excluded.name,category=excluded.category',identities)
        with self._quote_lock:self._quote_cache.clear();self.revision+=1
        return len(quotes)

    def refresh_async(self,force=False):
        if self.refreshing or (not force and time.monotonic()-self.last_attempt<300):return
        self.refreshing=True;self.last_attempt=time.monotonic()
        threading.Thread(target=self._refresh,name='market-item-resolver',daemon=True).start()

    def _refresh(self):
        errors=[]
        try:
            with closing(sqlite3.connect(self.path)) as db:
                region=db.execute('SELECT region FROM market_context WHERE id=1').fetchone()[0]
                names=[r[0] for r in db.execute('SELECT DISTINCT item FROM loot')] if db.execute("SELECT 1 FROM sqlite_master WHERE name='loot'").fetchone() else []
            self.ensure_catalog()
            if not names:return
            ids=sorted({item['id'] for name in names for item in self._item_database.candidates(name)})
            received=[]
            for start in range(0,len(ids),40):
                try:
                    batch=ids[start:start+40]
                    data=self._fetch_quotes(region,batch)
                    received.extend(self._base_quotes(data,set(batch)))
                except Exception as exc:errors.append(str(exc))
            by_name={}
            for item in received:by_name.setdefault(market_name_key(item['name']),[]).append(item)
            safe=[group[0] for group in by_name.values() if len({i['id'] for i in group})==1]
            self.update_market(safe,region,activate=False)
            self._refresh_vendor_values(names,region)
            self.last_error='; '.join(errors)
            if not errors:self.last_refresh=time.time()
        except Exception as exc:self.last_error=str(exc)
        finally:self.refreshing=False

    def _load_catalog(self):
        cache=Path(self.path).parent/'market-item-database.json'
        index=cache.with_name('item-catalog.sqlite3')
        if cache.is_file():
            try:return DiskItemDatabase.from_json(cache,index)
            except (OSError,ValueError,sqlite3.Error):pass
        temporary=cache.with_suffix('.download')
        try:
            total=0
            with urllib.request.urlopen('https://api.arsha.io/util/db?lang=en',timeout=12) as response,temporary.open('wb') as output:
                while True:
                    chunk=response.read(65536)
                    if not chunk:break
                    total+=len(chunk)
                    if total>32*1024*1024:raise ValueError('Item database exceeds download budget')
                    output.write(chunk)
            catalog=DiskItemDatabase.from_json(temporary,index)
            temporary.replace(cache)
            return catalog
        finally:
            if temporary.exists():temporary.unlink()

    def resolve_name(self,name):
        if name in self._resolved_names:return self._resolved_names[name]
        # Verified non-market treasure names need no invented market ID/price.
        # Exact text only: do not add these exceptions to fuzzy OCR matching.
        from big_drops import BY_NAME,key
        treasure=BY_NAME.get(key(name))
        if treasure and treasure['category']=='Treasure':return treasure['item']
        observed=canonical_item(name)
        if self._item_database is None:return EXACT.get(observed.casefold())
        candidates=self._item_database.candidates(observed)
        names={item['name'] for item in candidates}
        result=next(iter(names)) if len(names)==1 else None
        if len(self._resolved_names)>=512:self._resolved_names.clear()
        self._resolved_names[name]=result
        return result

    def notice_item(self,name):
        if name not in self._noticed_items:
            if len(self._noticed_items)>=512:self._noticed_items.clear()
            self._noticed_items.add(name);self.last_attempt=0

    def ensure_catalog(self):
        with self._catalog_lock:
            if self._item_database is None:
                self._item_database=self._load_catalog()
                set_exact_resolver(self._item_database.exact_name)

    def recipe_quotes(self,names,region):
        """On-demand exact recipe identities; bounded and cached, never OCR fuzzy matches."""
        if region not in ('NA','EU') or not isinstance(names,list) or not 1<=len(names)<=64:raise ValueError('Invalid recipe lookup')
        if any(not isinstance(n,str) or not 1<=len(n)<=100 for n in names):raise ValueError('Invalid item names')
        key=(region,tuple(sorted(set(names))))
        with self._recipe_lock:
            cached=self._recipe_cache.get(key)
            if cached and time.monotonic()-cached[0]<300:return cached[1]
            self.ensure_catalog();ids=set()
            for name in key[1]:
                exact=[i for i in self._item_database.candidates(name) if market_name_key(i['name'])==market_name_key(name)]
                # Event-only catalog entries can share a normal item's name.
                # Query exact IDs, then let verified tradable responses disambiguate.
                identities={i['id'] for i in exact}
                if len(identities)<=8:ids.update(identities)
            items=[];ordered=sorted(ids)
            for start in range(0,len(ordered),40):
                batch=ordered[start:start+40];items.extend(self._base_quotes(self._fetch_quotes(region,batch),set(batch)))
            wanted={market_name_key(n) for n in names};groups={}
            for item in items:
                identity=market_name_key(item['name'])
                if identity in wanted:groups.setdefault(identity,[]).append(item)
            items=[group[0] for group in groups.values() if len({i['id'] for i in group})==1]
            self.update_market(items,region,activate=False)
            if len(self._recipe_cache)>=16:self._recipe_cache.clear()
            self._recipe_cache[key]=(time.monotonic(),items)
            return items

    def recipe_id_quotes(self,ids,region):
        """Exact public recipe IDs, with quote basis/freshness. No catalog download.

        Only selected plans request quotes. A five-minute shared cache avoids
        repeat calls while editing a recipe. Prices are provider base quotes,
        not promises that a large stack will sell at that price.
        """
        if region not in ('NA','EU') or not isinstance(ids,list) or not 1<=len(ids)<=64:
            raise ValueError('Use 1–64 recipe item IDs and NA/EU')
        if any(type(n) is not int or not 0<n<10_000_000 for n in ids):raise ValueError('Invalid recipe item ID')
        key=(region,tuple(sorted(set(ids))))
        with self._recipe_lock:
            cached=self._recipe_cache.get(key)
            if cached and time.monotonic()-cached[0]<300:return cached[1]
            items=[]
            def visit(value,requested):
                if isinstance(value,list):
                    for row in value:visit(row,requested)
                elif isinstance(value,dict):
                    base=self._base_quotes(value,requested)
                    if base:
                        row=base[0]
                        row.update({'price_basis':'market_base','updated_at':datetime.now().astimezone().isoformat(timespec='seconds'),'region':region,'source':'Arsha Central Market base price'})
                        for source,dest in (('currentStock','stock'),('lastSoldPrice','last_sold_price'),('lastSoldTime','last_sold_at')):
                            v=value.get(source)
                            if type(v) is int and v>=0:row[dest]=v
                        items.append(row)
            ordered=key[1]
            for start in range(0,len(ordered),40):
                batch=ordered[start:start+40];visit(self._fetch_quotes(region,batch),set(batch))
            with closing(sqlite3.connect(self.path)) as db:
                prior={ident:json.loads(payload) for ident,payload in db.execute('SELECT id,payload FROM market_quote_details WHERE region=?',(region,)) if ident in ordered}
            for row in items:
                old=prior.get(row['id'],{})
                for field in ('daily_volume','fourteen_day_volume','volume_source_updated_at'):
                    if field in old:row[field]=old[field]
                if 'daily_volume' in old and 'volume_source_updated_at' not in row:row['volume_source_updated_at']=old.get('source_updated_at')
            self.update_market(items,region,activate=False)
            with closing(sqlite3.connect(self.path)) as db,db:
                db.executemany('INSERT INTO market_quote_details VALUES (?,?,?) ON CONFLICT(region,id) DO UPDATE SET payload=excluded.payload',[(region,i['id'],json.dumps(i)) for i in items])
            with self._quote_lock:self._quote_cache.clear()
            if len(self._recipe_cache)>=32:self._recipe_cache.clear()
            self._recipe_cache[key]=(time.monotonic(),items)
            return items

    def recipe_market_snapshot(self,region):
        if region not in ('NA','EU'):raise ValueError('Unknown market region')
        key=(region,'recipe-market-snapshot')
        with self._recipe_lock:
            cached=self._recipe_cache.get(key)
            if cached and time.monotonic()-cached[0]<900:return cached[1]
            from craft_economy import craft_spec
            from recipe_market import fetch_recipe_market
            items=fetch_recipe_market(region,craft_spec()['items'])
            stamp=datetime.now().astimezone().isoformat(timespec='seconds')
            for row in items:row['updated_at']=stamp
            self.update_market(items,region,activate=False)
            with closing(sqlite3.connect(self.path)) as db,db:
                db.executemany('INSERT INTO market_quote_details VALUES (?,?,?) ON CONFLICT(region,id) DO UPDATE SET payload=excluded.payload',[(region,i['id'],json.dumps(i)) for i in items])
            with self._quote_lock:self._quote_cache.clear()
            if len(self._recipe_cache)>=32:self._recipe_cache.clear()
            self._recipe_cache[key]=(time.monotonic(),items)
            return items

    def _refresh_vendor_values(self,names,region):
        quotes=self.all(region);now=time.time();candidates={}
        with closing(sqlite3.connect(self.path)) as db:
            checks=dict(db.execute('SELECT id,checked_at FROM vendor_checks'))
        for name in names:
            resolved=self.resolve_name(name)
            if not resolved:continue
            quote=quotes.get(resolved)
            if quote and quote.get('price_basis')!='npc_vendor':continue
            items=self._item_database.candidates(resolved)
            if len({i['id'] for i in items})!=1:continue
            item=items[0]
            ttl=86400 if quote and quote.get('price_basis')=='npc_vendor' else 3600
            if now-checks.get(item['id'],0)<ttl:continue
            candidates[item['id']]=item
        for item in list(candidates.values())[:5]:
            try:quote=fetch_vendor_quote(item['id'],item['name'])
            except Exception:quote=None
            with closing(sqlite3.connect(self.path)) as db,db:
                db.execute('INSERT INTO vendor_checks VALUES (?,?) ON CONFLICT(id) DO UPDATE SET checked_at=excluded.checked_at',(item['id'],now))
                if quote:
                    stamp=datetime.now().astimezone().isoformat(timespec='seconds')
                    db.execute('INSERT INTO vendor_quotes VALUES (?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,unit_price=excluded.unit_price,updated_at=excluded.updated_at,source_url=excluded.source_url',(quote['id'],quote['name'],quote['price'],stamp,quote['source_url']))

    @staticmethod
    def _get_json(url):
        with urllib.request.urlopen(url,timeout=12) as response:return json.load(response)

    def _fetch_quotes(self,region,ids):
        prefix=f'https://api.arsha.io/v2/{region.lower()}/GetWorldMarketSubList?id='
        try:return self._get_json(prefix+','.join(map(str,ids))+'&lang=en')
        except urllib.error.HTTPError as exc:
            # The service fails an entire batch when one ID is an event-only item.
            # Isolate those IDs without discarding prices for tradable namesakes.
            if exc.code!=500 or len(ids)==1:raise
        results=[];deadline=time.monotonic()+45
        for ident in ids:
            if time.monotonic()>deadline:raise TimeoutError('Market lookup timed out')
            try:results.append(self._get_json(prefix+str(ident)+'&lang=en'))
            except urllib.error.HTTPError as exc:
                if exc.code not in (400,404,500):raise
        return results

    @staticmethod
    def _base_quotes(data,requested):
        if isinstance(data,list):
            return [q for entry in data for q in PriceBook._base_quotes(entry,requested)]
        if not isinstance(data,dict) or data.get('id') not in requested:return []
        if data.get('sid')!=0 or not data.get('name'):return []
        value=data.get('basePrice')
        if isinstance(value,bool) or not isinstance(value,int) or value<=0:return []
        return [{'id':data['id'],'name':data['name'],'price':value}]
