import json
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from grind_ui import grind_summary
from activity_data import grind_session_detail
from loot_tracker import LootLedger
from loot_insights import InsightsSession
from price_book import PriceBook
from market_match import ItemDatabase


class GrindTests(unittest.TestCase):
    def test_observed_zero_drop_period_is_zero_rather_than_unpriced(self):
        meta={'id':'run','created_at':0,'active_seconds':60,'targets':'[]'}
        result=grind_summary(meta,[],{},now=60,available=True)
        self.assertEqual(result['value'],0);self.assertEqual(result['silver_hour'],0)
        self.assertEqual(result['coverage'],1)
    def test_partial_value_rate_coverage_and_treasure_are_observed(self):
        meta={'id':'run','created_at':0,'active_seconds':60,'label':'My route','targets':'["Treasure Piece"]','goal':2}
        rows=[(3,'1970-01-01T00:01:30+00:00','Treasure Piece',1,'OCR','s','Rare drop'),(2,'1970-01-01T00:01:00+00:00','Elixir',4,'OCR','s','Drop')]
        result=grind_summary(meta,rows,{'Elixir':{'unit_price':100,'source':'Market'}},now=120)
        self.assertEqual(result['value'],400);self.assertEqual(result['silver_hour'],24000)
        self.assertEqual(result['coverage'],.5);self.assertEqual(result['excluded_seconds'],60)
        self.assertEqual(result['target_quantity'],1);self.assertEqual(result['target_progress'],.5)
        self.assertEqual(result['unpriced'],1);self.assertEqual(result['rare'],1)
        self.assertEqual(sum(result['pulse']),5)

    def test_treasure_dry_streak_is_event_count_not_an_odds_claim(self):
        meta={'id':'run','created_at':0,'active_seconds':10,'targets':'["Piece"]','goal':1}
        rows=[(3,'1970-01-01T00:00:03+00:00','Stone',3,'OCR','s','Drop'),(2,'1970-01-01T00:00:02+00:00','Piece',1,'OCR','s','Drop'),(1,'1970-01-01T00:00:01+00:00','Stone',1,'OCR','s','Drop')]
        result=grind_summary(meta,rows,{},now=20)
        self.assertEqual(result['events_since_target'],1);self.assertEqual(result['target_progress'],1)
        self.assertIsNone(result['value']);self.assertIsNone(result['silver_hour'])

    def test_finished_recap_retains_prices_and_membership(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'history.db';ledger=LootLedger(path);session=InsightsSession(ledger.db)
            session.start(label='Personal route',activity='Grinding',targets=['Piece'])
            ident=ledger.add('Elixir',4);session.observe(ident);session.clock.seconds=60
            prices={'Elixir':{'unit_price':100,'source':'Market'}};session.finish(prices)
            ledger.db.execute('CREATE TABLE grind_details(session TEXT PRIMARY KEY,spot TEXT,goal INTEGER)')
            ledger.db.execute('INSERT INTO grind_details VALUES (?,?,?)',(session.id,'Personal route',2));ledger.db.commit()
            result=grind_session_detail(path,{'Elixir':{'unit_price':900,'source':'New price'}},session.id)
            self.assertEqual(result['value'],400);self.assertEqual(result['spot'],'Personal route')
            self.assertFalse(result['available']);self.assertEqual(result['goal'],2)
            ledger.close()

    def test_validated_names_exclude_screen_noise_and_keep_nonmarket_treasure(self):
        with tempfile.TemporaryDirectory() as folder:
            book=PriceBook(Path(folder)/'history.db')
            book._item_database=ItemDatabase([{'id':678,'name':'Elixir of Demihuman Hunt'},{'id':999,'name':'Ancient Treasure Piece'}])
            self.assertEqual(book.resolve_name('Elixir of Demihuman Hunt'),'Elixir of Demihuman Hunt')
            self.assertEqual(book.resolve_name('Ancient Treasure Piece'),'Ancient Treasure Piece')
            self.assertEqual(book.resolve_name('Corrupt Power Source'),'Corrupt Power Source')
            self.assertIsNone(book.resolve_name('Corrupt Power Souree'))
            self.assertIsNone(book.resolve_name('21,500,000,000 funt'))
            self.assertIsNone(book.resolve_name('Amount +100%'))
