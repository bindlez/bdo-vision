import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from loot_insights import summarize,SessionClock,InsightsSession
from loot_tracker import LootLedger
from price_book import PriceBook
from item_events import parse_events


def row(item,qty,kind='Drop'):
    return (1,'2026-10-29T20:00:00-04:00',item,qty,'Item Drop Log','s',kind)


class InsightsTests(unittest.TestCase):
    def test_partial_value_and_measured_rates(self):
        value=summarize([row('Milk',4,'Crafted'),row('Unknown',2,'Rare drop')],{'Milk':{'unit_price':10,'source':'Bundled estimate'}},1800)
        self.assertEqual(value['value'],40);self.assertEqual(value['silver_hour'],80)
        self.assertEqual(value['units_hour'],12);self.assertEqual(value['unpriced'],1)
        self.assertEqual(value['crafted'],4);self.assertEqual(value['rare'],2)

    def test_no_invented_rates_and_zero_price_is_valid(self):
        rows=[row('Milk',2)]
        self.assertIsNone(summarize(rows,{},3600)['value'])
        self.assertIsNone(summarize(rows,{},None)['silver_hour'])
        self.assertTrue(summarize(rows,{},59)['warming_up'])
        zero=summarize(rows,{'Milk':{'unit_price':0,'source':'Planner override'}},60)
        self.assertEqual(zero['silver_hour'],0);self.assertEqual(zero['unpriced'],0)

    def test_clock_pause_and_recording_gate(self):
        clock=SessionClock(now=0);clock.running=True;clock.gate=True
        clock.tick(False,10);clock.tick(True,100);clock.tick(True,110)
        self.assertEqual(clock.seconds,20)
        clock.running=False;clock.tick(True,500);self.assertEqual(clock.seconds,20)

    def test_sessions_membership_and_finished_price_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger=LootLedger(Path(folder)/'history.db');session=InsightsSession(ledger.db)
            before=ledger.add('Milk',2)
            session.start(label='Alchemy run',activity='Crafting',recipe='Milk',targets=['Milk'])
            observed=ledger.add('Milk',4,kind='Crafted');session.observe(observed)
            session.pause_resume();ignored=ledger.add('Milk',8);session.observe(ignored)
            self.assertEqual([r[0] for r in session.rows()],[observed])
            prices={'Milk':{'unit_price':10,'source':'Bundled estimate'}}
            session.finish(prices)
            prices['Milk']['unit_price']=100
            history=session.history()[0]
            self.assertEqual(json.loads(history['price_snapshot'])['Milk']['unit_price'],10)
            self.assertEqual(history['label'],'Alchemy run');self.assertIsNotNone(history['ended_at'])
            with self.assertRaises(ValueError):session.pause_resume()
            restored=InsightsSession(ledger.db);self.assertFalse(restored.clock.running);self.assertTrue(restored.ended)
            session.start(label='Next run');self.assertEqual(session.rows(),[])
            ledger.close()

    def test_existing_recipes_preserved_and_market_regions_are_separate(self):
        source=Path(__file__).resolve().parents[1]/'desktop/assets/recipes.json'
        recipes=json.loads(source.read_text(encoding='utf-8'))
        import re
        html=(source.parents[2]/'bdo-market-intelligence.html').read_text(encoding='utf-8')
        self.assertEqual(recipes,json.loads(re.search(r'const RECIPES = (\[.*?\]);',html,re.S)[1]))
        self.assertNotIn('lootPricePanel',html)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'prices.db';book=PriceBook(path,source)
            self.assertEqual(book.all(),{})
            book.update_market([{'name':'Beer','price':1234}],'NA')
            self.assertEqual(book.all()['Beer']['unit_price'],1234)
            book.update_market([{'name':'Beer','price':999}],'EU')
            self.assertEqual(book.all()['Beer']['unit_price'],999)
            book.update_market([],'NA')
            self.assertEqual(book.all()['Beer']['unit_price'],1234)
            with self.assertRaises(ValueError):book.update_market([{'name':'Beer','price':1.5}],'NA')
            with self.assertRaises(ValueError):book.update_market([{'name':'Beer','price':True}],'NA')

    def test_known_single_item_notification(self):
        events=parse_events('Shining Powder',bare_items=True,crafting=True)
        self.assertEqual(len(events),1);self.assertEqual(events[0].quantity,1)
        self.assertFalse(events[0].quantity_explicit)
