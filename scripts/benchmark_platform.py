"""Synthetic domain benchmark; does not capture BDO or measure game FPS."""
import json,statistics,sys,time,tracemalloc,sqlite3
from datetime import datetime,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'desktop'))
from platform_home import ledger_totals
from craft_economy import session_economy,economy_points


def main():
    rows=[(i,(datetime(2026,11,1,10)+timedelta(seconds=i)).isoformat(), 'Elixir',2,'synthetic','test','Crafted') for i in range(20000)]
    recipe={'name':'Elixir','mats':[{'name':'Herb','qty':2}]}
    quotes={name:{'unit_price':price,'source':'synthetic'} for name,price in [('Elixir',100),('Herb',10)]}
    model={'yield':2,'retention':80,'extra':1}
    db=sqlite3.connect(':memory:')
    db.execute('CREATE TABLE loot (recorded_at TEXT,quantity INTEGER,kind TEXT)')
    db.executemany('INSERT INTO loot VALUES (?,?,?)',((r[1],r[3],r[6]) for r in rows));db.commit()
    calls={'home_sql_totals':lambda:ledger_totals(db,'2026-11-01'),
           'session_economics':lambda:session_economy(recipe,rows,quotes,model,3600),
           'bounded_profit_graph':lambda:economy_points(recipe,rows,quotes,model)}
    result={'rows':len(rows),'python':sys.version.split()[0],'scope':'Synthetic in-process domain calls; no OCR, UI, network, child-process memory or FPS measurement. Input allocations excluded.','results':{}}
    for name,call in calls.items():
        call();samples=[]
        for _ in range(20):
            start=time.perf_counter();call();samples.append((time.perf_counter()-start)*1000)
        tracemalloc.start();value=call();_,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
        result['results'][name]={'median_ms':round(statistics.median(samples),3),'p95_ms':round(sorted(samples)[18],3),'peak_python_allocation_bytes':peak}
        if name=='bounded_profit_graph':assert len(value)<=48;result['results'][name]['points']=len(value)
    db.close()
    folder=ROOT/'build';folder.mkdir(exist_ok=True);(folder/'platform-benchmark.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
