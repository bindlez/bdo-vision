"""Crafting economy boundaries, exact market lookups and bounded history queries."""
import sys,unittest,subprocess,tempfile,sqlite3,time,json
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'desktop'))
from loot_tracker import LootLedger
from price_book import PriceBook
from market_match import ItemDatabase
from activity_data import timer_earnings
from silver_loot import silver_snapshot

class CraftingStudioTests(unittest.TestCase):
    def js(self,body):
        module=json.dumps(str(ROOT/'desktop/assets/crafting-engine.js'))
        result=subprocess.run(['node','-e',f'const assert=require("node:assert/strict"),C=require({module});'+body],capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stderr)

    def test_economy_counts_owned_inputs_and_sale_deductions(self):
        self.js('''
const r={name:'Elixir',type:'alchemy',sell:100,mats:[{name:'Herb',qty:2,fallback:10}]};
const p=C.plan(r,10,{yield:2,seconds:5,retention:80,extra:3},{quote:n=>({price:n==='Herb'?10:100}),recipes:[r],inventory:{herb:5}});
assert.equal(p.output,20);assert.equal(p.cost,230);assert.equal(p.cash,150);assert.equal(p.proceeds,1600);assert.equal(p.profit,1370);assert.equal(p.breakEven,14.375);assert.equal(p.seconds,50);
const missing=C.plan(r,1,{},{quote:()=>null,recipes:[r]});assert.equal(missing.warnings.length,2);
assert.equal(C.plan(r,1,{retention:0},{quote:()=>null,recipes:[r]}).breakEven,null);
''')

    def test_recursive_materials_cycles_and_missing_prices(self):
        self.js('''
const a={id:'a',name:'Meal',sell:100,mats:[{name:'Sauce',qty:3,fallback:10}]};
const b={id:'b',name:'Sauce',sell:10,mats:[{name:'Herb',qty:2,fallback:2}]};
const p=C.plan(a,2,{yield:1,seconds:5},{quote:()=>null,recipes:[a,b],make:{sauce:true},inventory:{sauce:1},configFor:()=>({yield:2,seconds:3})});
assert.equal(p.steps[0].batches,3);assert.equal(p.purchases[0].quantity,6);assert.equal(p.cost,22);assert.equal(p.seconds,19);
b.mats=[{name:'Meal',qty:1,fallback:100}];const cyc=C.plan(a,1,{},{quote:()=>null,recipes:[a,b],make:{sauce:true,meal:true}});assert.ok(cyc.warnings.some(x=>x.startsWith('Recipe cycle')));
assert.equal(C.series(Array.from({length:1000},(_,i)=>[i,i]),48).length,48);
''')

    def test_projection_is_opt_in_craft_only_current_gap_and_bounded(self):
        self.js('''
let now=100000,t={startAt:now,endAt:now+100000,status:'running',amount:20,vision:{},craftPlan:{type:'alchemy',estimate:true,seconds:5,yield:2,unitPrice:100,costPerBatch:10}},d={crafting_mode:true,available:false,reason:'Item area is covered by browser',updated_at:100};
assert.equal(C.projection(t,d,now).value,0);d.updated_at=110;assert.equal(C.projection(t,d,now+10000).value,400);
d.available=true;assert.equal(C.projection(t,d,now+11000).value,0);assert.equal(t.vision.gapAt,null);
d.available=false;d.updated_at=112;assert.equal(C.projection(t,d,now+12000).value,0);
t.craftPlan.type='grinding';assert.equal(C.projection(t,d,now+15000).value,0);t.craftPlan.type='alchemy';
for(const reason of ['Capture is stale','Recording is off','Unable to verify the visible BDO item area','BDO game window not found','Capture area is outside the visible BDO window']){d.reason=reason;assert.equal(C.projection(t,d,now+15000).value,0);}
d.reason='BDO must be visible, not minimized or in the tray';d.updated_at=115;assert.equal(C.projection(t,d,now+15000).value,0);
assert.equal(C.projection(t,d,now+40000).value,0);d.updated_at=140;assert.equal(C.projection(t,d,now+40000).value,0);
t.craftPlan.estimate=false;assert.equal(C.projection(t,d,now+41000).value,0);t.craftPlan.estimate=true;t.status='done';assert.equal(C.projection(t,d,now+42000).value,0);
t.status='running';assert.equal(C.projection(t,d,t.endAt).value,0);delete d.updated_at;assert.equal(C.projection(t,d,now+10000).value,0);
''')

    def test_aggregate_timer_preserves_event_quantities_and_filter(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger=LootLedger(Path(folder)/'loot.db')
            for i in range(200):ledger.add('Milk',i%4+1,kind='Crafted' if i%2 else 'Drop')
            ledger.add('Milk',2,kind='Rare craft');ledger.add('Unknown thing',3,kind='Crafted')
            prices={'Milk':{'unit_price':100,'source':'Central Market'}}
            expected=silver_snapshot(ledger.rows(),prices)
            actual=timer_earnings(ledger.path if hasattr(ledger,'path') else Path(folder)/'loot.db',prices)
            for key in ('units','events','market_silver','rare_units','unpriced_types','last_event_id'):
                if key in expected:self.assertEqual(actual[key],expected[key],key)
            self.assertEqual(actual['event_count'],202);self.assertEqual(len(actual['latest']),12)
            crafts=timer_earnings(Path(folder)/'loot.db',prices,kind='craft')
            self.assertEqual(crafts['event_count'],102);self.assertEqual(crafts['units'],305)
            ledger.close()

    def test_price_cache_invalidates_on_writes_and_exact_identity_only(self):
        with tempfile.TemporaryDirectory() as folder:
            book=PriceBook(Path(folder)/'prices.db')
            book.update_market([{'id':1,'name':'Milk','price':10}],'NA')
            with patch.object(book,'_all_uncached',wraps=book._all_uncached) as uncached:
                self.assertIs(book.all(),book.all());self.assertEqual(uncached.call_count,1)
                book.update_market([{'id':1,'name':'Milk','price':12}],'NA');self.assertEqual(book.all()['Milk']['unit_price'],12)
            book._item_database=ItemDatabase([{'id':1,'name':'Milk'},{'id':2,'name':'Milk Tea'},{'id':3,'name':'Oil'},{'id':4,'name':'Oil'}])
            with patch.object(book,'_fetch_quotes',return_value=[{'id':1,'sid':0,'name':'Milk','basePrice':15}]) as fetch:
                self.assertEqual(book.recipe_quotes(['Milk','Mil','Oil'],'NA'),[{'id':1,'name':'Milk','price':15}]);self.assertEqual(fetch.call_args.args,('NA',[1,3,4]))
                book.recipe_quotes(['Milk','Mil','Oil'],'NA');self.assertEqual(fetch.call_count,1)
            for names in ([],['a']*65,[None]):
                with self.assertRaises(ValueError):book.recipe_quotes(names,'NA')

    def test_recipe_quote_event_namesakes_need_one_verified_tradable_identity(self):
        with tempfile.TemporaryDirectory() as folder:
            book=PriceBook(Path(folder)/'prices.db')
            book._item_database=ItemDatabase([{'id':678,'name':'Elixir'},{'id':37193,'name':'Elixir'},{'id':1,'name':'Oil'},{'id':2,'name':'Oil'}])
            payload=[{'id':678,'sid':0,'name':'Elixir','basePrice':68000},{'id':1,'sid':0,'name':'Oil','basePrice':10},{'id':2,'sid':0,'name':'Oil','basePrice':10}]
            with patch.object(book,'_fetch_quotes',return_value=payload):
                result=book.recipe_quotes(['Elixir','Oil'],'NA')
                self.assertEqual(result,[{'id':678,'name':'Elixir','price':68000}])
                self.assertNotIn('Oil',book.all())

    def test_embedded_assets_match_production_sources(self):
        html=(ROOT/'bdo-market-intelligence.html').read_text(encoding='utf-8')
        for name in ('crafting-engine.js','crafting-studio.js','crafting-studio.css','vision-timers.js','crafting-loot-view.js'):
            self.assertIn((ROOT/'desktop/assets'/name).read_text(encoding='utf-8-sig').strip(),html,name)
        self.assertNotIn('<script src="https://cdn.jsdelivr.net/npm/tesseract',html)

    def test_recipe_quote_endpoint_uses_existing_origin_guard(self):
        from planner_bridge import PlannerBridge
        import urllib.request,urllib.error
        with tempfile.TemporaryDirectory() as folder:
            book=PriceBook(Path(folder)/'prices.db');bridge=PlannerBridge(ROOT/'bdo-market-intelligence.html',ports=(0,),price_book=book)
            try:
                with patch.object(book,'recipe_quotes',return_value=[{'id':1,'name':'Milk','price':100}]) as lookup:
                    request=urllib.request.Request(bridge.base_url+'/craft-quotes',data=b'{"names":["Milk"],"region":"NA"}',headers={'Content-Type':'application/json'},method='POST')
                    with urllib.request.urlopen(request) as response:self.assertEqual(json.load(response)['items'][0]['price'],100)
                    self.assertEqual(lookup.call_args.args,(['Milk'],'NA'))
                    request.add_header('Origin','https://example.com')
                    with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(request)
                    self.assertEqual(caught.exception.code,403)
            finally:bridge.close()

    def test_unchanged_bridge_payload_omits_items_without_mutating_history(self):
        from planner_bridge import PlannerBridge
        import urllib.request
        bridge=PlannerBridge(ROOT/'bdo-market-intelligence.html',ports=(0,))
        try:
            bridge.update_crafting_loot({'summary_revision':'revision-a','items':[{'item':'Milk','quantity':2}],'available':True})
            with urllib.request.urlopen(bridge.base_url+'/durability?loot_revision=revision-a') as response:slim=json.load(response)
            self.assertTrue(slim['crafting_loot']['items_unchanged']);self.assertNotIn('items',slim['crafting_loot'])
            with urllib.request.urlopen(bridge.base_url+'/durability?loot_revision=revision-b') as response:full=json.load(response)
            self.assertEqual(full['crafting_loot']['items'][0]['quantity'],2)
        finally:bridge.close()

if __name__=='__main__':unittest.main()
