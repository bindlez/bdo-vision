import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from vendor_prices import parse_vendor_quote
from price_book import PriceBook
from loot_tracker import LootLedger
from silver_loot import silver_snapshot


class VendorValueTests(unittest.TestCase):
    def test_published_sell_value_requires_matching_id_and_name(self):
        markup='<title>Caterpillar - BDO Codex</title><div>ID: 5599</div><p>Buy price: 100<br>Sell price: 10<br>Repair price: -</p>'
        quote=parse_vendor_quote(markup,5599,'Caterpillar')
        self.assertEqual(quote['price'],10)
        self.assertIsNone(parse_vendor_quote(markup,5600,'Caterpillar'))
        self.assertIsNone(parse_vendor_quote(markup,5599,'Different item'))
        self.assertIsNone(parse_vendor_quote(markup.replace('Sell price: 10','Sell price: 0'),5599,'Caterpillar'))

    def test_market_prices_take_priority_and_vendor_values_cover_unlisted_loot(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'history.db';ledger=LootLedger(path);ledger.add('Caterpillar',4);book=PriceBook(path)
            with closing(sqlite3.connect(path)) as db,db:db.execute('INSERT INTO vendor_quotes VALUES (5599,?,10,?,?)',('Caterpillar','2026-10-30','https://bdocodex.com/us/item/5599/'))
            result=silver_snapshot(ledger.rows(),book.all())
            self.assertEqual(result['market_silver'],40);self.assertEqual(result['items'][0]['price_basis'],'npc_vendor')
            book.update_market([{'id':5599,'name':'Caterpillar','price':20}],'NA')
            self.assertEqual(silver_snapshot(ledger.rows(),book.all())['market_silver'],80)
            ledger.close()
