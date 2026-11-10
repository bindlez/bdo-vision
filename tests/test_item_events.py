import sys
import shutil
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from item_events import ItemEvent,parse_events,agreed_events,PopupSnapshots


class ItemEventTests(unittest.TestCase):
    def test_actual_notification_and_wrapped_chat(self):
        wanted=ItemEvent('Elixir of Demihuman Hunt',4,'Crafted')
        self.assertEqual(parse_events('Elixir of Demihuman Hunt x 4: Tage',bare_items=True,crafting=True),[wanted])
        self.assertEqual(parse_events('System Youhave obtained & [Elixir of Demihuman\nHunt]\nx4.',crafting=True),[wanted])
        self.assertEqual(parse_events('Elixir of Demihuman Hunt x 4',bare_items=True),[ItemEvent(wanted.item,4,'Drop')])
        self.assertEqual(parse_events('* System *. You have obtained & [Corrupt Power Source] x10.'),[ItemEvent('Corrupt Power Source',10,'Drop')])

    def test_rare_production_prefix_quantity_and_other_player_guard(self):
        self.assertEqual(parse_events('[Rare Item Drop] [Black Stone] x2'),[ItemEvent('Black Stone',2,'Rare drop')])
        self.assertEqual(parse_events('You have produced [16] Potato'),[ItemEvent('Potato',16,'Crafted')])
        self.assertEqual(parse_events('Potato x3',bare_items=True,rare_feed=True),[ItemEvent('Potato',3,'Rare drop')])
        self.assertEqual(parse_events('Bob has obtained [Black Stone] x2'),[])
        self.assertEqual(parse_events('GO',bare_items=True),[])
        self.assertEqual(parse_events('You have obtained x2'),[])
        self.assertEqual(parse_events('Elixir of Demihuman Huntx4',bare_items=True,crafting=True),[ItemEvent('Elixir of Demihuman Hunt',4,'Crafted')])
        self.assertEqual(parse_events('Elixir of Demihuman Hunt x |',bare_items=True,crafting=True),[ItemEvent('Elixir of Demihuman Hunt',1,'Crafted')])

    def test_individual_agreement_keeps_valid_events(self):
        a=ItemEvent('Stone',1,'Drop');b=ItemEvent('Relic',2,'Rare drop')
        self.assertEqual(agreed_events([[a,b],[a],[b]]),[a,b])
        self.assertEqual(agreed_events([[a,a],[a,a],[]]),[a,a])
        self.assertEqual(agreed_events([[a],[],[]]),[])

    def test_popup_change_repeats_and_unreadable_scan(self):
        s=PopupSnapshots();a=ItemEvent('Milk',1,'Crafted');b=ItemEvent('Beer',2,'Crafted')
        self.assertEqual(s.ingest([a]),([],False))
        self.assertEqual(s.ingest([a,a]),([a],False))
        self.assertEqual(s.ingest([]),([],False))
        self.assertEqual(s.ingest([a,a]),([],False))
        self.assertEqual(s.ingest([b]),([b],False))
        s.ingest([],empty=True)
        self.assertEqual(s.ingest([b]),([b],False))

    def test_live_captured_popup_with_tesseract(self):
        tess=shutil.which('tesseract') or r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        if not Path(tess).is_file():self.skipTest('Tesseract not installed')
        from PIL import Image
        from loot_capture import recognize_feed
        with tempfile.TemporaryDirectory() as folder:
            with Image.open(Path(__file__).parent/'fixtures'/'item-drop-log.png') as image:
                result=recognize_feed(image,tess,'normal',True,folder)
            self.assertIn(ItemEvent('Elixir of Demihuman Hunt',4,'Crafted'),result['events'])

    def test_user_screenshot_to_saved_crafting_record(self):
        tess=shutil.which('tesseract') or r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        image_path=Path(__file__).parent/'fixtures'/'user-popup.png'
        if not Path(tess).is_file() or not image_path.is_file():self.skipTest('Screenshot / Tesseract unavailable')
        from PIL import Image
        from loot_capture import recognize_feed
        from loot_tracker import LootLedger
        with tempfile.TemporaryDirectory() as folder:
            with Image.open(image_path) as image:result=recognize_feed(image,tess,'normal',True,folder)
            self.assertIn(ItemEvent('Elixir of Demihuman Hunt',4,'Crafted'),result['events'])
            ledger=LootLedger(Path(folder)/'history.db')
            snapshots=PopupSnapshots(record_initial=True)
            fresh,_=snapshots.ingest(result['events'])
            for event in fresh:ledger.add(event.item,event.quantity,'Item Drop Log',kind=event.kind)
            self.assertTrue(any(r[2]=='Elixir of Demihuman Hunt' and r[3]==4 and r[6]=='Crafted' for r in ledger.rows()))
            ledger.close()

    def test_icon_noise_and_known_name_hints(self):
        from item_names import canonical_item
        self.assertEqual(canonical_item('nt Elixir of Demihuman Hunt'),'Elixir of Demihuman Hunt')
        self.assertEqual(canonical_item('Flixir of Demihuman Hunt'),'Elixir of Demihuman Hunt')
        self.assertEqual(canonical_item('Elixir of Fierce Demihuman Hunt'),'Elixir of Fierce Demihuman Hunt')
        self.assertEqual(canonical_item('An Unknown Rare Item'),'An Unknown Rare Item')
