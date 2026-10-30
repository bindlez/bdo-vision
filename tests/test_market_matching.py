import sys
import tempfile
import time
import tkinter as tk
import types
import urllib.error
import unittest
from pathlib import Path
from unittest.mock import MagicMock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from market_match import match_item,ItemDatabase
from price_book import PriceBook
from loot_tracker import LootLedger
from loot_ui import LootTracker
from silver_loot import silver_snapshot


class MarketMatchingTests(unittest.TestCase):
    def test_catalog_names_do_not_run_ocr_correction_on_the_ui_thread(self):
        items=[{'id':i+1,'name':'A catalog item '+str(i)} for i in range(1000)]
        with patch('market_match.canonical_item',side_effect=lambda value:value) as correct:
            match_item('A catalog item 999',items)
        self.assertEqual(correct.call_count,1)
    def test_event_only_id_does_not_block_other_market_quotes(self):
        def response(url):
            if '678,37193' in url or 'id=37193&' in url:
                raise urllib.error.HTTPError(url,500,'Event item has no listing',{},None)
            return [{'id':678,'sid':0,'name':'Elixir of Demihuman Hunt','basePrice':42300}]
        with tempfile.TemporaryDirectory() as folder:
            book=PriceBook(Path(folder)/'loot.db')
            with patch.object(book,'_get_json',side_effect=response):
                data=book._fetch_quotes('NA',[678,37193])
            self.assertEqual(PriceBook._base_quotes(data,{678,37193})[0]['price'],42300)

    def test_database_candidates_resolve_duplicate_event_name_by_tradable_id(self):
        catalog=[{'id':678,'name':'Elixir of Demihuman Hunt'},{'id':37193,'name':'Elixir of Demihuman Hunt'}]
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'loot.db';ledger=LootLedger(path);ledger.add('Elixir of Demihuman Hunt',4)
            book=PriceBook(path);book._item_database=ItemDatabase(catalog)
            self.assertIsNone(book._item_database.match('Elixir of Demihuman Hunt'))
            with patch.object(book,'_fetch_quotes',return_value=[{'id':678,'sid':0,'name':catalog[0]['name'],'basePrice':42300}]) as fetch:
                book._refresh()
            self.assertEqual(set(fetch.call_args[0][1]),{678,37193})
            self.assertEqual(silver_snapshot(ledger.rows(),book.all())['market_silver'],169200)
            ledger.close()

    def test_base_price_filter_ignores_enhancement_and_unrequested_items(self):
        rows=[[{'id':678,'sid':0,'name':'Elixir','basePrice':42300}],{'id':678,'sid':1,'name':'Elixir','basePrice':999999},{'id':679,'sid':0,'name':'Other','basePrice':128000}]
        self.assertEqual(PriceBook._base_quotes(rows,{678}),[{'id':678,'name':'Elixir','price':42300}])

    def test_failed_refresh_keeps_cached_value_and_region(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'loot.db';ledger=LootLedger(path);ledger.add('Elixir of Demihuman Hunt',1)
            book=PriceBook(path);book.update_market([{'id':678,'name':'Elixir of Demihuman Hunt','price':42}],'EU')
            book._item_database=ItemDatabase([{'id':678,'name':'Elixir of Demihuman Hunt'}])
            with patch.object(book,'_fetch_quotes',side_effect=OSError('offline')):book._refresh()
            self.assertEqual(book.all()['Elixir of Demihuman Hunt']['unit_price'],42)
            self.assertIn('offline',book.last_error)
            book.update_market([{'id':678,'name':'Elixir of Demihuman Hunt','price':90}],'NA',activate=False)
            self.assertEqual(book.all()['Elixir of Demihuman Hunt']['unit_price'],42)
            ledger.close()

    def test_quality_variants_are_distinct_and_unknown_is_not_guessed(self):
        items=[{'id':678,'name':'Elixir of Demihuman Hunt'},{'id':679,'name':'Elixir of Fierce Demihuman Hunt'}]
        self.assertEqual(match_item('6 Elixir, of Demihuman Hunt',items)['id'],678)
        self.assertEqual(match_item('Elixir of Fierce Demihuman Hunt',items)['id'],679)
        self.assertIsNone(match_item('luman Hunt',items))

    def test_item_id_lookup_produces_real_quantity_times_price_total(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'loot.db';ledger=LootLedger(path)
            ledger.add('6 Elixir, of Demihuman Hunt',4,kind='Drop')
            ledger.add('Elixir of Fierce Demihuman Hunt',1,kind='Drop')
            prices=PriceBook(path)
            prices.update_market([{'id':678,'name':'Elixir of Demihuman Hunt','price':42300},{'id':679,'name':'Elixir of Fierce Demihuman Hunt','price':128000}],'NA')
            value=silver_snapshot(ledger.rows(),prices.all())
            self.assertEqual(value['market_silver'],297200)
            self.assertEqual({r['market_id'] for r in value['items']},{678,679})
            self.assertEqual(value['units'],5);self.assertEqual(value['unpriced_types'],0)
            ledger.close()

    def test_shared_loot_does_not_require_crafting_mode(self):
        root=tk.Tk();root.withdraw()
        with tempfile.TemporaryDirectory() as folder:
            app=types.SimpleNamespace(root=root,save_quietly=MagicMock(),bridge=MagicMock())
            loot=LootTracker(app,Path(folder),{'loot_region':[1,1,200,100],'loot_enabled':True,'craft_tracking':False,'share_crafting_loot':True})
            try:
                loot.ledger.add('Elixir of Demihuman Hunt',4,kind='Drop')
                loot.last_scan_finished=time.time()
                with patch.object(loot,'can_capture',return_value=(True,'')):
                    snapshot=loot.planner_loot_snapshot();loot.refresh_shared_loot()
                self.assertEqual(snapshot['elixir_units'],4)
                self.assertEqual(snapshot['crafted_units'],0)
                self.assertTrue(snapshot['captured_items_available'])
                app.bridge.update_crafting_loot.assert_called_once()
            finally:loot.close();root.destroy()
