import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from item_events import ItemEvent,parse_events
from loot_tracker import TextFeedSnapshots

def event(q):return ItemEvent('Tungrad Ruins Fragment',q,'Drop')

class TextFeedTests(unittest.TestCase):
    def test_broken_quantity_never_becomes_one(self):
        for quantity in ('xT','x?','x1B','x-4'):
            self.assertEqual(parse_events('You have obtained [Milk] '+quantity),[])

    def test_icon_punctuation_and_single_colored_drop(self):
        self.assertEqual(parse_events("~ You have obtained # [Milk] x18."),[ItemEvent('Milk',18,'Drop')])
        self.assertEqual(parse_events("You have obtained # [Laila’s Petal]. - ."),[ItemEvent("Laila's Petal",1,'Drop',quantity_explicit=False)])

    def test_retained_holes_do_not_shift_or_recount_loot(self):
        tracker=TextFeedSnapshots();initial=list(map(event,range(1,9)))
        tracker.ingest_slots(initial)
        frame=initial[2:]+[None,event(10)]
        fresh,ambiguous=tracker.ingest_slots(frame)
        self.assertFalse(ambiguous);self.assertEqual(fresh,[event(10)])
        frame[-2]=event(9)
        self.assertEqual(tracker.ingest_slots(frame),([event(9)],False))
        self.assertEqual(tracker.ingest_slots(frame),([],False))
        missing=frame.copy();missing[2]=None
        self.assertEqual(tracker.ingest_slots(missing),([],False))
        self.assertEqual(tracker.ingest_slots(frame),([],False))

    def test_no_overlap_is_reported_without_fabricating_loot(self):
        tracker=TextFeedSnapshots();tracker.ingest_slots(list(map(event,range(1,9))))
        self.assertEqual(tracker.ingest_slots(list(map(event,range(10,18)))),([],True))
        self.assertEqual(tracker.ingest_slots([None]*8),([],False))

    def test_confirmed_empty_baseline_records_first_drop_once(self):
        tracker=TextFeedSnapshots()
        tracker.ingest_capture([],[],empty=True)
        self.assertEqual(tracker.ingest_capture([event(10)],None),([event(10)],False))
        self.assertEqual(tracker.ingest_capture([event(10)],None),([],False))

    def test_identical_rows_are_conservative(self):
        tracker=TextFeedSnapshots();tracker.ingest_slots([event(7)]*8)
        self.assertEqual(tracker.ingest_slots([event(7)]*8),([],False))

if __name__=='__main__':unittest.main()
