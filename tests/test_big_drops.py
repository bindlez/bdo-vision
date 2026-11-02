import sqlite3,sys,time,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from big_drops import BigDropBook,classify,heat
from loot_insights import InsightsSession
from loot_tracker import LootLedger
from tempfile import TemporaryDirectory
from unittest.mock import Mock
from big_drops_ui import BigDrops


class BigDropRulesTests(unittest.TestCase):
    def test_nonmarket_treasure_exact_names_survive_without_a_market_catalog(self):
        from price_book import PriceBook
        with TemporaryDirectory() as folder:
            book=PriceBook(Path(folder)/'prices.db')
            self.assertEqual(book.resolve_name("Archaeologist’s Map Piece"),"Archaeologist's Map Piece")
            self.assertEqual(book.resolve_name("Lafi Bedmountain's Upgraded Compass Parts"),"Lafi Bedmountain's Upgraded Compass Parts")
            self.assertIsNone(book.resolve_name('Archaeologists Map Piece'))
            self.assertIsNone(book.resolve_name('Amount +100%'))
    def test_market_thresholds_are_strict_individual_prices_and_treasures_override(self):
        self.assertIsNone(classify('Ordinary',quote={'unit_price':1_000_000_000}))
        self.assertEqual(classify('Valuable',quote={'unit_price':1_000_000_001})['category'],'Big Drop')
        self.assertEqual(classify('Valuable',quote={'unit_price':10_000_000_000})['category'],'Big Drop')
        self.assertEqual(classify('Valuable',quote={'unit_price':10_000_000_001})['category'],'Huge Drop')
        self.assertEqual(classify("Archaeologist's Map Piece")['category'],'Treasure')
        self.assertIsNone(classify("Kabua's Fragment"));self.assertIsNone(classify('Blood Wolf Oath'))
        self.assertIsNone(classify('Valuable','Crafted',{'unit_price':30_000_000_000}))
        for value in (float('nan'),float('inf'),True,-1):self.assertIsNone(classify('Odd',quote={'unit_price':value}))

    def test_personal_average_and_burst_heat_have_separate_honest_bases(self):
        baseline={'runs':3,'seconds':10800,'hits':6}
        view=heat([],600,baseline,count=4,recent=1)
        self.assertEqual(view['title'],'INFERNO');self.assertEqual(view['ratio'],12)
        self.assertIn('Your history',view['basis']);self.assertIn("You're on fire",view['message'])
        burst=heat([{'observed_seconds':10},{'observed_seconds':30},{'observed_seconds':50}],100)
        self.assertEqual(burst['title'],'ON FIRE');self.assertIsNone(burst['ratio'])
        self.assertEqual(burst['basis'],'Recorded-drop momentum')
        cooled=heat([{'observed_seconds':10},{'observed_seconds':30},{'observed_seconds':50}],2000)
        self.assertFalse(cooled['on_fire'])
        paused=heat([],600,baseline,available=False,count=4)
        self.assertIn('last measured',paused['note'])

    def test_insufficient_history_never_becomes_a_global_probability(self):
        for baseline in ({'runs':2,'seconds':10000,'hits':20},{'runs':3,'seconds':1000,'hits':20},{'runs':3,'seconds':10000,'hits':2}):
            view=heat([],600,baseline,count=1,recent=1)
            self.assertIsNone(view['ratio']);self.assertFalse(view['on_fire'])


class BigDropBookTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.ledger=LootLedger(Path(self.tmp.name)/'history.db')
        self.db=self.ledger.db;self.session=InsightsSession(self.db)
        self.db.execute('CREATE TABLE grind_details(session TEXT PRIMARY KEY,spot TEXT,goal INTEGER)')
        self.book=BigDropBook(self.db);self.prices={"Kabua's Artifact":{'unit_price':9_350_000_000,'source':'Central Market (NA)'},'Expensive':{'unit_price':12_000_000_000,'source':'Central Market (NA)'}}

    def tearDown(self):self.ledger.close();self.tmp.cleanup()

    def snapshot(self):return self.book.snapshot(self.ledger.revision,self.session,self.prices,True)

    def test_live_drop_is_deduplicated_and_huge_item_joins_journal(self):
        self.session.start(label='Yzrahid',activity='Grinding');self.session.clock.seconds=60
        ident=self.ledger.add("Kabua's Artifact",1);self.session.observe(ident)
        event=self.book.observe(ident,self.session,self.prices)
        self.assertEqual(event['category'],'Big Drop');self.assertIsNone(self.book.observe(ident,self.session,self.prices))
        self.assertEqual(self.snapshot()['current_events'],1)
        expensive=self.ledger.add('Expensive',1);self.session.observe(expensive);self.book.observe(expensive,self.session,self.prices)
        view=self.snapshot();self.assertEqual(view['latest']['category'],'Huge Drop');self.assertEqual(view['lifetime_events'],2)
        self.assertEqual(view['latest']['value'],12_000_000_000)

    def test_retained_history_has_no_fabricated_timing_or_new_notification(self):
        ident=self.ledger.add("Archaeologist's Map Piece",1)
        view=self.snapshot();self.assertEqual(view['latest']['id'],ident);self.assertIsNone(view['latest']['observed_seconds'])
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM big_drop_moments').fetchone()[0],0)

    def test_restart_preserves_moment_and_unknown_prices_do_not_become_zero(self):
        self.session.start(label='Sulfur',activity='Treasure hunt')
        ident=self.ledger.add("Archaeologist's Map Piece",1);self.session.observe(ident);self.book.observe(ident,self.session,self.prices)
        self.book=BigDropBook(self.db);view=self.snapshot()
        self.assertIsNone(view['latest']['value']);self.assertEqual(view['current_events'],1)
        self.assertIsNone(self.book.observe(ident,self.session,self.prices))

    def test_zero_drop_runs_contribute_and_future_runs_do_not_contaminate_baseline(self):
        now=time.time()
        for index,hits in enumerate((3,3,0)):
            sid='past'+str(index);start=now-(index+2)*4000
            self.db.execute('INSERT INTO insight_sessions(id,created_at,active_seconds,label,activity,ended_at) VALUES (?,?,3600,?,?,?)',(sid,start,'Yzrahid','Grinding',start+3600))
            for _ in range(hits):
                ident=self.ledger.add("Kabua's Artifact",1);self.db.execute('INSERT INTO insight_members VALUES (?,?)',(sid,ident))
        self.db.commit();self.session.start(label='Yzrahid',activity='Grinding');self.session.clock.seconds=600
        view=self.snapshot();self.assertEqual(view['baseline'],{'runs':3,'seconds':10800.0,'hits':6})

    def test_common_drops_do_not_rebuild_rare_history_cache(self):
        self.snapshot();cached=self.book._cache
        for _ in range(20):
            ident=self.ledger.add('Cheap Stone',100000);self.assertIsNone(self.book.observe(ident,self.session,self.prices))
        self.snapshot();self.assertIs(cached,self.book._cache)

    def test_delayed_quote_preserves_original_observed_time_and_no_session_stays_unknown(self):
        self.session.start(label='Yzrahid',activity='Grinding');ident=self.ledger.add('Expensive',1);self.session.observe(ident)
        self.session.clock.seconds=900
        self.book.observe(ident,self.session,self.prices,moment=(self.session.id,100))
        self.assertEqual(self.snapshot()['latest']['observed_seconds'],100)
        other=self.ledger.add('Expensive',1);self.book.observe(other,self.session,self.prices,moment=(None,123))
        self.assertIsNone(self.snapshot()['latest']['observed_seconds'])

    def test_personal_rarity_shelf_has_eligible_hours_and_no_global_odds(self):
        now=time.time()
        for index in range(3):
            sid='sample'+str(index);start=now-(index+2)*4000
            self.db.execute('INSERT INTO insight_sessions(id,created_at,active_seconds,label,activity,ended_at) VALUES (?,?,3600,?,?,?)',(sid,start,'Yzrahid','Grinding',start+3600))
            ident=self.ledger.add("Kabua's Artifact",1);self.db.execute('INSERT INTO insight_members VALUES (?,?)',(sid,ident))
        self.db.commit();view=self.snapshot();kabua=next(r for r in view['comparisons'] if r['item']=="Kabua's Artifact")
        self.assertEqual(kabua['personal_hours_per_event'],1);self.assertIsNone(kabua['global_odds'])
        self.assertEqual(kabua['sample_runs'],3)

    def test_journal_is_bounded_without_truncating_totals(self):
        for _ in range(45):
            ident=self.ledger.add("Kabua's Artifact",1);self.book.observe(ident,self.session,self.prices)
        view=self.snapshot();self.assertEqual(len(view['journal']),40);self.assertEqual(view['lifetime_events'],45)


class DelayedBigDropTests(unittest.TestCase):
    def setUp(self):
        BigDropBookTests.setUp(self)
        self.ui=BigDrops.__new__(BigDrops);self.ui.book=self.book;self.ui.frame=None
        self.ui.pending={};self.ui._pending_price_revision=-1
        self.price_service=SimpleNamespace(all=Mock(side_effect=lambda:self.prices),revision=0)
        self.ui.tracker=SimpleNamespace(insights=SimpleNamespace(session=self.session,prices=self.price_service))
        self.ui.app=SimpleNamespace(status=Mock());self.ui.celebrate=Mock();self.ui.celebrate.get.return_value=False

    def tearDown(self):BigDropBookTests.tearDown(self)

    def test_pending_prices_are_bounded_and_retry_only_on_price_revision(self):
        self.session.start(label='Yzrahid',activity='Grinding')
        for index in range(40):
            ident=self.ledger.add('Unknown '+str(index),1);self.session.observe(ident);self.session.clock.seconds=500
            self.ui.observe(ident,SimpleNamespace(item='Unknown '+str(index),kind='Drop'))
        self.assertEqual(len(self.ui.pending),32)
        self.ui.refresh_pending();calls=self.price_service.all.call_count
        for _ in range(100):self.ui.refresh_pending()
        self.assertEqual(calls,self.price_service.all.call_count)
        self.session.clock.seconds=900
        self.prices={**self.prices,'Unknown 39':{'unit_price':12_000_000_000,'source':'Central Market (NA)'}}
        self.price_service.revision+=1;self.ui.refresh_pending()
        self.assertEqual(len(self.ui.pending),31);self.ui.app.status.set.assert_called_once()
        row=self.db.execute('SELECT observed_seconds FROM big_drop_moments WHERE loot_id=?',(ident,)).fetchone()
        self.assertEqual(row[0],500)
        self.ui.refresh_pending();self.ui.app.status.set.assert_called_once()
