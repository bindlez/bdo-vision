import sqlite3,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from platform_home import progress_totals,ledger_totals,unlocks
from loot_tracker import LootLedger


class ProgressTests(unittest.TestCase):
    def test_rewards_persist_without_duplicate_awards(self):
        db=sqlite3.connect(':memory:')
        try:
            self.assertEqual(len(unlocks(db,1500)),2)
            first=db.execute('SELECT * FROM platform_achievements ORDER BY key').fetchall()
            self.assertEqual(len(unlocks(db,1500)),2)
            self.assertEqual(first,db.execute('SELECT * FROM platform_achievements ORDER BY key').fetchall())
            self.assertEqual(len(unlocks(db,10000)),3)
        finally:db.close()

    def test_daily_goal_and_lifetime_counts_have_distinct_scopes(self):
        rows=[(1,'2026-11-01T10:00:00','Elixir',4,'OCR','','Crafted'),(2,'2026-11-01T10:00:01','Rare',1,'OCR','','Rare craft'),(3,'2026-10-31T10:00:00','Loot',100,'OCR','','Drop')]
        self.assertEqual(progress_totals(rows,'2026-11-01'),{'lifetime_units':105,'today_units':5,'crafted':5,'rare':1,'events':2})

    def test_sql_aggregate_matches_recorded_history_without_loading_rows(self):
        ledger=LootLedger(':memory:')
        try:
            self.assertEqual(ledger_totals(ledger.db,'2026-11-01')['lifetime_units'],0)
            for item,count,day,kind in [('Elixir',4,'2026-11-01','Crafted'),('Rare',1,'2026-11-01','Rare craft'),('Loot',100,'2026-10-31','Drop')]:
                ledger.add(item,count,recorded_at=day+'T10:00:00',kind=kind)
            self.assertEqual(ledger_totals(ledger.db,'2026-11-01'),progress_totals(ledger.rows(),'2026-11-01'))
        finally:ledger.close()
