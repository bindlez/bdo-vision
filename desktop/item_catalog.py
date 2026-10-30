"""Disk-backed item identities with bounded lookup memory and streaming import."""
from contextlib import closing
from functools import lru_cache
from pathlib import Path
import json,os,sqlite3,tempfile
from market_match import market_name_key,normalized,match_item

SCHEMA_VERSION=1


def json_array_items(handle,chunk_size=65536):
    """Use the stdlib decoder incrementally; never retain the full catalog list."""
    decoder=json.JSONDecoder();buffer='';index=0;eof=False;started=False;need_comma=False;after_comma=False
    while True:
        while index>=len(buffer) or not buffer[index:].strip():
            if eof:raise ValueError('Incomplete item database')
            more=handle.read(chunk_size);buffer=buffer[index:]+more;index=0;eof=not more
            if eof and not buffer.strip():raise ValueError('Incomplete item database')
            if len(buffer)>2_000_000:raise ValueError('Oversized item record')
        while index<len(buffer) and buffer[index].isspace():index+=1
        if not started:
            if buffer[index]!='[':raise ValueError('Item database must be an array')
            index+=1;started=True;continue
        if buffer[index]==']':
            if after_comma:raise ValueError('Trailing item separator')
            if buffer[index+1:].strip() or any(chunk.strip() for chunk in iter(lambda:handle.read(chunk_size),'')):
                raise ValueError('Trailing item database content')
            return
        if need_comma:
            if buffer[index]!=',':raise ValueError('Missing item separator')
            index+=1;need_comma=False;after_comma=True;continue
        try:item,end=decoder.raw_decode(buffer,index)
        except json.JSONDecodeError:
            if eof:raise ValueError('Invalid item database')
            more=handle.read(chunk_size)
            buffer=buffer[index:]+more;index=0;eof=not more
            if len(buffer)>2_000_000:raise ValueError('Oversized item record')
            continue
        yield item
        index=end;need_comma=True;after_comma=False


class DiskItemDatabase:
    """Same conservative name/ID rules as ItemDatabase, held in SQLite.

    No open connection or catalog-sized Python index survives a lookup. Hot
    exact lookups are capped at 256 names; oversized fuzzy pools are unresolved.
    """
    def __init__(self,path):
        self.path=Path(path).resolve()
        self._cached_exact=lru_cache(maxsize=256)(self._read_exact)
        with closing(self._connect()) as db:
            meta=dict(db.execute('SELECT key,value FROM catalog_meta'))
            if meta.get('schema')!=str(SCHEMA_VERSION):raise ValueError('Unsupported item catalog')

    def _connect(self):
        db=sqlite3.connect(self.path.as_uri()+'?mode=ro',uri=True)
        db.execute('PRAGMA cache_size=-256');db.execute('PRAGMA mmap_size=0')
        return db

    @classmethod
    def from_json(cls,source,path):
        source=Path(source);path=Path(path);stat=source.stat()
        fingerprint=f'{stat.st_size}:{stat.st_mtime_ns}'
        if path.is_file():
            try:
                catalog=cls(path)
                with closing(catalog._connect()) as db:
                    if db.execute("SELECT value FROM catalog_meta WHERE key='source'").fetchone()[0]==fingerprint:
                        return catalog
            except (sqlite3.Error,ValueError,TypeError):pass
        path.parent.mkdir(parents=True,exist_ok=True)
        descriptor,name=tempfile.mkstemp(prefix='catalog-',suffix='.sqlite3',dir=path.parent);os.close(descriptor)
        temporary=Path(name)
        try:
            with closing(sqlite3.connect(temporary)) as db:
                db.executescript('PRAGMA cache_size=-512; PRAGMA mmap_size=0; '
                    'CREATE TABLE catalog_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL); '
                    'CREATE TABLE catalog_items(id INTEGER NOT NULL,name TEXT NOT NULL,name_key TEXT NOT NULL,PRIMARY KEY(id,name)) WITHOUT ROWID; '
                    'CREATE TABLE catalog_tokens(token TEXT NOT NULL,name_key TEXT NOT NULL,PRIMARY KEY(token,name_key)) WITHOUT ROWID;')
                records=[];tokens=[];count=0
                with source.open(encoding='utf-8') as stream:
                    for item in json_array_items(stream):
                        if not isinstance(item,dict) or type(item.get('id')) is not int or not isinstance(item.get('name'),str) or not item['name']:continue
                        key=market_name_key(item['name']);records.append((item['id'],item['name'],key));count+=1
                        tokens.extend((token,key) for token in set(key.split()))
                        if len(records)>=256:
                            db.executemany('INSERT OR IGNORE INTO catalog_items VALUES (?,?,?)',records)
                            db.executemany('INSERT OR IGNORE INTO catalog_tokens VALUES (?,?)',tokens)
                            records.clear();tokens.clear()
                db.executemany('INSERT OR IGNORE INTO catalog_items VALUES (?,?,?)',records)
                db.executemany('INSERT OR IGNORE INTO catalog_tokens VALUES (?,?)',tokens)
                db.execute('CREATE INDEX catalog_name ON catalog_items(name_key)')
                db.executemany('INSERT INTO catalog_meta VALUES (?,?)',
                    [('schema',str(SCHEMA_VERSION)),('source',fingerprint),('items',str(count))])
                db.commit()
                if not count or db.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise ValueError('Invalid generated item catalog')
            temporary.replace(path)
            return cls(path)
        finally:
            if temporary.exists():temporary.unlink()

    def _read_exact(self,key):
        with closing(self._connect()) as db:
            return tuple(db.execute('SELECT id,name FROM catalog_items WHERE name_key=? ORDER BY id,name',(key,)))

    def exact_name(self,name):
        rows=self._cached_exact(market_name_key(name));names={row[1] for row in rows}
        return next(iter(names)) if len(names)==1 else None

    def match(self,observed):
        key=market_name_key(observed);exact=self._cached_exact(key)
        if not exact:key=normalized(observed);exact=self._cached_exact(key)
        if len({row[0] for row in exact})==1:return {'id':exact[0][0],'name':exact[0][1]}
        if exact or len(key)<14:return None
        tokens=sorted({token for token in key.split() if len(token)>2})
        if not tokens:return None
        with closing(self._connect()) as db:
            placeholders=','.join('?' for _ in tokens)
            pool=db.execute(f'SELECT token,COUNT(*) FROM catalog_tokens WHERE token IN ({placeholders}) GROUP BY token ORDER BY COUNT(*),token LIMIT 1',tokens).fetchone()
            if not pool or pool[1]>2048:return None
            candidates=[{'id':ident,'name':name} for ident,name in db.execute(
                'SELECT i.id,i.name FROM catalog_items i JOIN catalog_tokens t ON i.name_key=t.name_key WHERE t.token=?',(pool[0],))]
        return match_item(observed,candidates)

    def candidates(self,observed):
        exact=self._cached_exact(market_name_key(observed)) or self._cached_exact(normalized(observed))
        if exact:return [{'id':ident,'name':name} for ident,name in exact]
        match=self.match(observed)
        return [match] if match else []
