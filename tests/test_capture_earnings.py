import json
import os
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
import urllib.request
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from capture_clock import CaptureClock
from activity_data import timer_earnings
from loot_tracker import LootLedger
from price_book import PriceBook
from storage import prepare_storage,backup_profile,InstanceLock,data_root
from planner_bridge import PlannerBridge


class CaptureEarningsTests(unittest.TestCase):
    def test_profile_location_is_independent_of_virtualized_appdata(self):
        env={k:v for k,v in os.environ.items() if k!='BDO_VISION_DATA_DIR'}
        with patch.dict(os.environ,env,clear=True):
            expected=data_root()
            with patch.dict(os.environ,{'LOCALAPPDATA':'C:/some/virtualized/appdata'}):self.assertEqual(data_root(),expected)
        self.assertEqual(expected.name,'.bdo-vision')
    def test_timer_observation_window_survives_page_gaps_and_clips_at_completion(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'history.db';ledger=LootLedger(path);clock=CaptureClock(ledger.db,now=0)
            clock.tick(True,now=0,wall=1000);clock.tick(True,now=4,wall=1004)
            clock.tick(False,'Covered',now=5,wall=1005);clock.tick(True,now=10,wall=1010)
            clock.tick(True,now=14,wall=1014)
            result=timer_earnings(path,{},before=1012,since=1002)
            self.assertEqual(result['observed_seconds'],4)
            self.assertEqual(result['excluded_seconds'],6)
            ledger.close()
    def test_blocked_time_and_long_suspensions_are_excluded(self):
        with sqlite3.connect(':memory:') as db:
            clock=CaptureClock(db,now=0)
            clock.tick(True,now=0);clock.tick(True,now=4)
            clock.tick(False,'Covered',now=5);clock.tick(False,'Covered',now=15)
            clock.tick(True,now=16);clock.tick(True,now=20)
            self.assertEqual(clock.observed,8)
            self.assertEqual(clock.paused,12)
            clock.tick(True,now=100)
            self.assertEqual(clock.observed,8)
            clock.save();restored=CaptureClock(db,now=1000)
            self.assertEqual(restored.history_id,clock.history_id)
            restored.tick(True,now=1000)
            self.assertEqual(restored.observed,8)

    def test_timer_baseline_excludes_earlier_loot_and_keeps_unknowns(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'history.db';ledger=LootLedger(path)
            before=ledger.add('Elixir',99);ledger.add('Elixir',4);ledger.add('Unknown',1)
            result=timer_earnings(path,{'Elixir':{'unit_price':100,'source':'Central Market'}},before)
            self.assertEqual(result['market_silver'],400)
            self.assertEqual(result['units'],5)
            self.assertEqual(result['event_count'],2)
            self.assertEqual(result['unpriced_types'],1)
            ledger.close()

    def test_timer_endpoint_requires_opt_in_and_correct_history(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'history.db';ledger=LootLedger(path);ledger.add('Elixir',4)
            book=PriceBook(path);book.update_market([{'name':'Elixir','price':100,'id':678}],'NA')
            bridge=PlannerBridge(Path(__file__).parents[1]/'bdo-market-intelligence.html',ports=(0,),price_book=book)
            # Test ephemeral port avoids collisions with the user's running apps.
            bridge.port=bridge.server.server_address[1]
            try:
                with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(bridge.base_url+'/timer-earnings?history=test')
                self.assertEqual(error.exception.code,403)
                bridge.update_crafting_loot({'history_id':'test'})
                with urllib.request.urlopen(bridge.base_url+'/timer-earnings?history=test&after=0&region=na') as response:result=json.load(response)
                self.assertEqual(result['market_silver'],400)
                with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(bridge.base_url+'/timer-earnings?history=other')
                self.assertEqual(error.exception.code,409)
            finally:bridge.close();ledger.close()

    def test_install_migration_never_overwrites_shared_history(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);first=base/'old';fresh=base/'fresh';shared=base/'shared'
            first.mkdir();fresh.mkdir()
            ledger=LootLedger(first/'loot-history.sqlite3');ledger.add('Preserved',4);ledger.close()
            (first/'settings.json').write_text('{"share_crafting_loot":true}')
            empty=LootLedger(fresh/'loot-history.sqlite3');empty.close()
            with patch.dict(os.environ,{'BDO_VISION_DATA_DIR':str(shared)}):
                self.assertEqual(prepare_storage(first),shared)
                self.assertEqual(prepare_storage(fresh),shared)
            with closing(sqlite3.connect(shared/'loot-history.sqlite3')) as db:self.assertEqual(db.execute('select sum(quantity) from loot').fetchone()[0],4)
            saved=backup_profile(shared)
            with closing(sqlite3.connect(saved/'loot-history.sqlite3')) as db:self.assertEqual(db.execute('pragma integrity_check').fetchone()[0],'ok')
            self.assertTrue(json.loads((saved/'settings.json').read_text())['share_crafting_loot'])

    @unittest.skipUnless(os.name=='nt','Windows native instance lock')
    def test_only_one_install_can_open_the_shared_profile(self):
        with tempfile.TemporaryDirectory() as folder:
            first=InstanceLock(folder);second=InstanceLock(folder)
            try:
                self.assertTrue(first.acquire());self.assertFalse(second.acquire())
                first.release();self.assertTrue(second.acquire())
            finally:first.release();second.release()
