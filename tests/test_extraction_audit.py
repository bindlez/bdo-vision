"""Quantity and mixed-message audit regressions, independent of image quality."""
import sys,unittest,random
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from item_events import parse_events,ItemEvent,agreed_events
from loot_tracker import TextFeedSnapshots

class ExtractionAuditTests(unittest.TestCase):
    def test_integer_quantity_forms_preserve_exact_count(self):
        for q,expected in [('1',1),('17',17),('1000',1000),('1,000',1000),('1,000,000',1000000)]:
            for text in (f'You have obtained [Milk] x{q}.',f'You have produced [{q}] Milk',f'You have obtained [Milk] ({q})',f'You have obtained [Milk] [{q}]'):
                with self.subTest(text=text):self.assertEqual([(e.item,e.quantity) for e in parse_events(text)],[('Milk',expected)])

    def test_malformed_quantities_never_become_smaller_valid_counts(self):
        for q in ('x0','x-1','x1.5','x1,5','x1,,000','x,5','x1,','x4 x5','x1 / 3','x1e3','x1O','x?','x1000001'):
            for bare in (False,True):
                with self.subTest(q=q,bare=bare):self.assertEqual(parse_events('You have obtained [Milk] '+q,bare_items=bare),[])

    def test_comma_validation_also_applies_to_prefix_and_bracket_forms(self):
        for q in ('1,5','1,,000','1,','10,00'):
            for text in (f'You have produced [{q}] Milk',f'You have obtained [Milk] ({q})',f'You have obtained [Milk] [{q}]'):
                with self.subTest(text=text):self.assertEqual(parse_events(text),[])

    def test_huge_digit_noise_does_not_abort_the_capture(self):
        for q in ('9'*5000,'0'*5000+'1'):
            self.assertEqual(parse_events('You have obtained [Milk] x'+q),[])

    def test_supported_verbs_work_inside_mixed_feeds(self):
        verbs={'You have obtained':'Drop','You have received':'Drop','You have acquired':'Drop','You have produced':'Crafted','You have crafted':'Crafted','You have created':'Crafted','Obtained':'Drop','Received':'Drop','Successfully obtained':'Drop','Crafting succeeded':'Crafted','Production complete':'Crafted'}
        for verb,kind in verbs.items():
            with self.subTest(verb=verb):
                text=f'You have obtained [Milk] x1\n{verb} [Beer] x2\nYou have obtained [Black Stone] x3'
                self.assertEqual(parse_events(text),[ItemEvent('Milk',1,'Drop'),ItemEvent('Beer',2,kind),ItemEvent('Black Stone',3,'Drop')])

    def test_popup_background_suffix_is_kept_but_second_count_is_not(self):
        self.assertEqual(parse_events('Elixir of Demihuman Hunt x 4: Tage',bare_items=True),[ItemEvent('Elixir of Demihuman Hunt',4,'Drop')])
        for text in ('Elixir of Demihuman Hunt x4 / 5','Elixir of Demihuman Hunt x4 [Beer] x5'):
            self.assertEqual(parse_events(text,bare_items=True),[])

    def test_harmless_ocr_quote_after_complete_count_keeps_the_row(self):
        for tail in (' "'," '",' |','._'):
            self.assertEqual(parse_events('You have obtained [Milk] x9.'+tail),[ItemEvent('Milk',9,'Drop')])
        for tail in ('.5',' / 3',' x5'):
            self.assertEqual(parse_events('You have obtained [Milk] x9'+tail),[])

    def test_unknown_or_other_player_chat_does_not_gain_personal_items(self):
        for text in ('Bob has obtained [Black Stone] x2','[Guild] Alice: You have obtained [Milk] x3','Selling [Milk] x10','Quest: collect [Milk] x5'):
            self.assertEqual(parse_events(text),[])

    def test_bracketed_names_keep_internal_quantity_words(self):
        for name in ('Desert Seal x12 Reward Bundle','Sealed Quturan\'s Ashen Leaf x1','[Event] Premium Outfit Box x10','Mass of Pure Magic Bundle - x10'):
            self.assertEqual(parse_events(f'You have obtained [{name}] x17'),[ItemEvent(name,17,'Drop')])
            self.assertEqual(parse_events(f'You have obtained [{name}]'),[ItemEvent(name,1,'Drop',quantity_explicit=False)])

    def test_failed_item_name_is_not_a_failed_action(self):
        for name in ('Failed Dish','Aura of Failed Kzarka',"Yolu's Records #31: Cause of Failure"):
            self.assertEqual(parse_events(f'You have obtained [{name}] x2'),[ItemEvent(name,2,'Drop')])
        self.assertEqual(parse_events('You have failed [Milk] x2'),[])

    def test_ocr_underscore_before_personal_message_does_not_hide_the_row(self):
        for prefix in ('_','__',':_'):
            self.assertEqual(parse_events(prefix+'You have obtained [Milk] x7'),[ItemEvent('Milk',7,'Drop')])
        self.assertEqual(parse_events('Someone_You have obtained [Milk] x7'),[])

    def test_notification_matrix_preserves_items_counts_and_crafting_kinds(self):
        names=('Elixir of Demihuman Hunt','Elixir of Fierce Demihuman Hunt','Shining Powder','Milk',"Laila's Petal",'Tungrad Ruins Fragment','Ancient Spirit Dust','Black Stone')
        verbs=('You have obtained','You have received','You have acquired','You have produced','You have crafted','You have created','Obtained','Received','Successfully obtained')
        for name in names:
            for verb in verbs:
                kind='Crafted' if any(word in verb.lower() for word in ('produced','crafted','created')) else 'Drop'
                for q in (1,2,4,17,999,1000,1000000):
                    with self.subTest(name=name,verb=verb,q=q):
                        self.assertEqual(parse_events(f'{verb} [{name}] x{q:,}.'),[ItemEvent(name,q,kind)])

    def test_seeded_scroll_holes_and_repeated_frames_never_double_record(self):
        rng=random.Random(10421);tracker=TextFeedSnapshots();stream=[ItemEvent('Milk',i+1,'Drop') for i in range(8)];tracker.ingest_slots(stream);seen=set()
        for index in range(8,2008):
            stream.append(ItemEvent('Milk',index+1,'Drop'));frame=[None if rng.random()<.06 else event for event in stream[-8:]]
            fresh,ambiguous=tracker.ingest_slots(frame);self.assertFalse(ambiguous)
            for event in fresh:
                self.assertNotIn(event.quantity,seen);seen.add(event.quantity)
            if index%9==0:self.assertEqual(tracker.ingest_slots(frame),([],False))
            if index%17==0:self.assertEqual(tracker.ingest_slots([None]*8),([],False))
        self.assertEqual(seen,set(range(9,2009)))

if __name__=='__main__':unittest.main()
