import json
import sys
import tempfile
import unittest
import urllib.request
import urllib.error
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from price_book import PriceBook
from planner_bridge import PlannerBridge


class SharedPriceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.book=PriceBook(Path(cls.temp.name)/'prices.db')
        cls.bridge=PlannerBridge(Path(__file__).resolve().parents[1]/'bdo-market-intelligence.html',ports=(7375,),price_book=cls.book)
        assert cls.bridge.server

    @classmethod
    def tearDownClass(cls):cls.bridge.close();cls.temp.cleanup()

    def post(self,price,origin=None):
        headers={'Content-Type':'application/json'}
        if origin:headers['Origin']=origin
        req=urllib.request.Request(self.bridge.base_url+'/market-prices',json.dumps({'region':'NA','items':[{'name':'Shining Powder','price':price}]}).encode(),headers=headers,method='POST')
        with urllib.request.urlopen(req,timeout=3) as result:return json.load(result)

    def test_market_quote_is_shared_with_desktop(self):
        self.assertTrue(self.post(456)['ok'])
        self.assertEqual(self.book.all()['Shining Powder']['unit_price'],456)
        with urllib.request.urlopen(self.bridge.base_url+'/prices',timeout=3) as result:
            self.assertEqual(json.load(result)['prices']['Shining Powder']['source'],'Central Market (NA)')

    def test_rejects_foreign_origin_and_invalid_prices(self):
        for value,origin,status in [(10,'https://example.com',403),(-1,None,400),(1.25,None,400)]:
            with self.assertRaises(urllib.error.HTTPError) as caught:self.post(value,origin)
            self.assertEqual(caught.exception.code,status)
