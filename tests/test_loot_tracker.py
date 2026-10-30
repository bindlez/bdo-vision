import csv
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'desktop'))
from loot_tracker import LootLedger, LootSnapshots, parse_loot


class LootTests(unittest.TestCase):
    def test_supported_messages_and_rejected_chat(self):
        self.assertEqual(parse_loot('You have obtained [Black Stone] x1,200\nYou received [Ancient Relic] (2)\nYou obtained [Gold Bar].'), [('Black Stone',1200),('Ancient Relic',2),('Gold Bar',1)])
        self.assertEqual(parse_loot('Selling [Black Stone] x10\nYou obtained [Stone] x0\nYou obtained [Stone] x-3'), [])

    def test_baseline_overlap_and_identical_repeated_events(self):
        snapshots=LootSnapshots()
        a=('Stone',1); b=('Relic',2)
        self.assertEqual(snapshots.ingest([a]),([],False))
        self.assertEqual(snapshots.ingest([a]),([],False))
        self.assertEqual(snapshots.ingest([a,a]),([a],False))
        self.assertEqual(snapshots.ingest([a,b]),([b],False))
        self.assertEqual(snapshots.ingest([]),([],False))
        self.assertEqual(snapshots.ingest([a,b]),([],False))
        self.assertEqual(snapshots.ingest([('New loot',3)]),([('New loot',3)],True))

    def test_ledger_persistence_validation_and_csv(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'loot.db'
            ledger=LootLedger(path)
            ident=ledger.add('Black Stone',3,session='session1')
            ledger.close();ledger=LootLedger(path)
            self.assertEqual(ledger.rows()[0][3],3)
            ledger.add('=FORMULA',1)
            output=Path(temp)/'loot.csv';ledger.export(output)
            with output.open(encoding='utf-8-sig',newline='') as stream:rows=list(csv.reader(stream))
            self.assertEqual(rows[1][3],'3')
            self.assertEqual(rows[2][2],"'=FORMULA")
            with self.assertRaises(ValueError):ledger.add('',1)
            with self.assertRaises(ValueError):ledger.add('Stone',0)
            ledger.close()
