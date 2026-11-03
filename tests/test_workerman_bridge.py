import json,sys,tempfile,unittest,urllib.request,urllib.error
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'desktop'))
from planner_bridge import PlannerBridge
from price_book import PriceBook
from workerman import reference_for
from test_workerman import JOB,QUOTES


class WorkermanBridgeTests(unittest.TestCase):
    def test_local_model_uses_cache_and_blocks_cross_origin_and_large_body(self):
        with tempfile.TemporaryDirectory() as folder:
            book=PriceBook(Path(folder)/'prices.db');reference={'schema':1,'revision':'a'*40,'fetchedAt':1,'jobs':[JOB]}
            reference_for(folder).path.write_text(json.dumps(reference),encoding='utf-8')
            bridge=PlannerBridge(ROOT/'bdo-market-intelligence.html',ports=(0,),price_book=book)
            def request(body,origin=None):
                headers={'Content-Type':'application/json'}
                if origin:headers['Origin']=origin
                with urllib.request.urlopen(urllib.request.Request(bridge.base_url+'/workerman',data=json.dumps(body).encode(),headers=headers)) as response:return json.load(response)
            try:
                body={'action':'model','node':'131','state':{'target':492,'counts':{'catalyst':750000}},'region':'NA'}
                with patch.object(book,'all',return_value=QUOTES) as prices,patch('workerman._download') as external:
                    self.assertGreater(request(body)['breakEvenDays'],0);external.assert_not_called();prices.assert_called_with('NA')
                    for bad in [dict(body,node='unknown'),dict(body,extra='x'*5000)]:
                        with self.assertRaises(urllib.error.HTTPError) as error:request(bad)
                        self.assertEqual(error.exception.code,400)
                    with self.assertRaises(urllib.error.HTTPError) as error:request(body,'https://evil.example')
                    self.assertEqual(error.exception.code,403)
            finally:bridge.close()


if __name__=='__main__':unittest.main()
