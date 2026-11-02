"""Bounded streaming and guarded, cached opportunity scans; no live network."""
import io,json,sys,tempfile,unittest,urllib.request,urllib.error
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'desktop'))
from recipe_market import market_rows,fetch_recipe_market
from price_book import PriceBook
from planner_bridge import PlannerBridge


class RecipeMarketTests(unittest.TestCase):
    def test_streaming_handles_split_unicode_and_rejects_truncation(self):
        class BytesAtATime(io.BytesIO):
            def read(self,n=-1):return super().read(1)
        raw=json.dumps({'result':{'data':[{'itemId':1,'name':'Crème','enhancementLevels':[{'x':1}]}]}},ensure_ascii=False).encode()
        self.assertEqual(list(market_rows(BytesAtATime(raw)))[0]['name'],'Crème')
        for value in (raw[:-5],b'{"error":"no data"}',b'{"result":{"data":[1]}}'):
            with self.assertRaises(ValueError):list(market_rows(io.BytesIO(value)))
        with self.assertRaises(ValueError):list(market_rows(io.BytesIO(raw),maximum=20))

    def test_keeps_only_exact_recipe_id_names_and_labels_average_volume(self):
        rows=[{'itemId':1,'name':'Milk','price':12000,'fourteenDayVolume':140,'inStock':0,'updatedAt':100000},
              {'itemId':2,'name':'Other','price':900},{'itemId':1,'name':'Wrong identity','price':1}]
        raw=io.BytesIO(json.dumps({'result':{'data':rows}}).encode())
        with patch('recipe_market.urllib.request.urlopen',return_value=raw):items=fetch_recipe_market('NA',{'1':{'name':'Milk'}})
        self.assertEqual(len(items),1);self.assertEqual(items[0]['daily_volume'],10)
        self.assertEqual(items[0]['stock'],0);self.assertEqual(items[0]['source_updated_at'],100)

    def test_snapshot_cached_and_origin_guarded(self):
        with tempfile.TemporaryDirectory() as folder:
            book=PriceBook(Path(folder)/'prices.db');row={'id':9065,'name':'Milk','price':12000,'daily_volume':10,'fourteen_day_volume':140,'region':'NA','source':'Public market reference','price_basis':'market_reference'}
            with patch('recipe_market.fetch_recipe_market',return_value=[row]) as fetch:
                self.assertIs(book.recipe_market_snapshot('NA'),book.recipe_market_snapshot('NA'));self.assertEqual(fetch.call_count,1)
                self.assertEqual(book.all('NA')['Milk']['daily_volume'],10)
                bridge=PlannerBridge(ROOT/'bdo-market-intelligence.html',ports=(0,),price_book=book)
                try:
                    request=urllib.request.Request(bridge.base_url+'/craft-market',data=b'{"region":"NA"}',headers={'Content-Type':'application/json'})
                    with urllib.request.urlopen(request) as response:self.assertEqual(json.load(response)['items'][0]['id'],9065)
                    request.add_header('Origin','https://invalid.example')
                    with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(request)
                    self.assertEqual(error.exception.code,403)
                finally:bridge.close()


if __name__=='__main__':unittest.main()
