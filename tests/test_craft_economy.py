import json,sqlite3,sys,tempfile,unittest,urllib.request,urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'desktop'))
from craft_economy import session_economy,economy_points,save_model,load_model,validate_model,recipes
from loot_tracker import LootLedger
from loot_insights import InsightsSession
from price_book import PriceBook
from planner_bridge import PlannerBridge


class EconomyTests(unittest.TestCase):
    def test_materials_yield_tax_rare_value_and_no_fake_fallback(self):
        recipe={'name':'Elixir','mats':[{'name':'Herb','qty':2,'fallback':1}]}
        rows=[(1,'2026-11-01T10:00:00','Elixir',10,'OCR','','Crafted'),(2,'2026-11-01T10:00:01','Rare',1,'OCR','','Rare craft')]
        quotes={name:{'unit_price':value,'source':'market'} for name,value in [('Elixir',100),('Rare',500),('Herb',10)]}
        value=session_economy(recipe,rows,quotes,{'yield':2,'retention':80,'extra':5},120)
        self.assertEqual(value['gross'],1500);self.assertEqual(value['batches'],5)
        self.assertEqual(value['ingredient_cost'],100);self.assertEqual(value['profit'],1075)
        self.assertEqual(value['materials'][0]['modeled_quantity'],10)
        points=economy_points(recipe,rows,quotes,{'yield':2,'retention':80,'extra':5})
        self.assertEqual(points[-1][1:],(1500,1075))
        self.assertLessEqual(len(economy_points(recipe,rows*100,quotes,{'yield':2,'retention':80,'extra':5})),48)
        self.assertFalse(session_economy(recipe,rows,{k:v for k,v in quotes.items() if k!='Herb'},{'yield':2,'retention':80,'extra':5})['available'])

    def test_model_is_validated_and_receipt_freezes_inputs(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'loot-history.sqlite3';ledger=LootLedger(path);session=InsightsSession(ledger.db);recipe=recipes()[0]
            model={'recipe_id':recipe['id'],'yield':2,'retention':80,'extra':5};save_model(path,model)
            self.assertEqual(load_model(path,recipe['id']),model)
            for changed in ({'yield':0},{'retention':101},{'extra':float('nan')},{'yield':True},{'recipe_id':'unknown'}):
                with self.assertRaises(ValueError):validate_model({**model,**changed})
            session.start(label='Test',activity='Crafting',recipe=recipe['name']);ident=ledger.add(recipe['name'],4,kind='Crafted');session.observe(ident)
            quotes={name:{'unit_price':10,'source':'market'} for name in [recipe['name'],*[m['name'] for m in recipe['mats']]]}
            session.finish(quotes)
            receipt=json.loads(ledger.db.execute('SELECT payload FROM craft_session_models').fetchone()[0])
            save_model(path,{**model,'retention':90})
            self.assertEqual(receipt['retention'],80)
            saved=json.loads(ledger.db.execute('SELECT price_snapshot FROM insight_sessions').fetchone()[0]);self.assertIn(recipe['mats'][0]['name'],saved)
            ledger.close()

    def test_bridge_requires_current_instance_and_rejects_foreign_origin(self):
        with tempfile.TemporaryDirectory() as folder:
            book=PriceBook(Path(folder)/'loot-history.sqlite3');bridge=PlannerBridge(ROOT/'bdo-market-intelligence.html',ports=(0,),price_book=book)
            try:
                model={'recipe_id':recipes()[0]['id'],'yield':2,'retention':80,'extra':0,'instance_id':bridge.instance_id}
                for origin,instance,expected in [('https://evil.example',bridge.instance_id,403),(bridge.base_url,'wrong',409),(bridge.base_url,bridge.instance_id,200)]:
                    body={**model,'instance_id':instance};request=urllib.request.Request(bridge.base_url+'/craft-model',data=json.dumps(body).encode(),headers={'Content-Type':'application/json','Origin':origin})
                    try:
                        with urllib.request.urlopen(request) as response:self.assertEqual(response.status,expected)
                    except urllib.error.HTTPError as exc:self.assertEqual(exc.code,expected)
            finally:bridge.close()
