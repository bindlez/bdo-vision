import sys
from pathlib import Path
import unittest
from unittest.mock import patch
import tempfile
import types
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from frame_cache import FeedCache
from item_events import ItemEvent
from loot_tracker import TextFeedSnapshots
from loot_capture import recognize_feed,capture_budget
from ocr_runtime import run_ocr


class FeedReuseTests(unittest.TestCase):
    def setUp(self):
        self.image=Image.new('RGB',(160,80),'black')
        self.cache=FeedCache(seconds=15)
        self.key=FeedCache.key(self.image,'engine','chat',False)
        self.events=[ItemEvent('Stone',q,'Drop') for q in range(1,9)]
        self.result={'events':self.events,'slots':self.events,'empty':False}

    def test_identical_frame_isolated_and_expires_without_extending_lifetime(self):
        self.cache.put(self.key,self.result,now=0)
        first=self.cache.get(self.key,now=4);first['events'].clear()
        self.assertEqual(self.cache.get(self.key,now=14)['events'],self.events)
        self.assertIsNone(self.cache.get(self.key,now=15))

    def test_pixel_mode_context_changes_force_fresh_read(self):
        self.cache.put(self.key,self.result,now=0)
        self.image.putpixel((159,79),(1,2,3))
        for key in (FeedCache.key(self.image,'engine','chat',False),
                    FeedCache.key(self.image,'other-engine','chat',False),
                    FeedCache.key(self.image,'engine','chat',True)):
            self.assertIsNone(self.cache.get(key,now=1))

    def test_uncertain_empty_and_popup_reads_are_never_reused(self):
        for result in ({**self.result,'slots':[self.events[0],None]},
                       {**self.result,'error':'timeout'},
                       {**self.result,'unresolved':[self.events[0]]},
                       {**self.result,'slots':[]}):
            cache=FeedCache();cache.put(self.key,result,now=0)
            self.assertIsNone(cache.get(self.key,now=1))
        key=FeedCache.key(self.image,'engine','normal',False)
        self.cache.put(key,self.result,now=0)
        self.assertIsNone(self.cache.get(key,now=1))

    def test_repeated_frame_does_not_count_retained_or_new_rows_twice(self):
        tracker=TextFeedSnapshots();tracker.ingest_slots(self.events)
        arrived=self.events[1:]+[ItemEvent('Relic',4,'Drop')]
        result={**self.result,'slots':arrived,'events':arrived}
        self.cache.put(self.key,result,now=0)
        counted=[]
        for second in (1,2,3,4):
            fresh,ambiguous=tracker.ingest_slots(self.cache.get(self.key,now=second)['slots'])
            self.assertFalse(ambiguous);counted.extend(fresh)
        self.assertEqual(counted,[arrived[-1]])

    def test_cache_is_bounded(self):
        for i in range(20):
            self.cache.put(self.key+(i,),self.result,now=i)
        self.assertLessEqual(len(self.cache.entries),3)


class QuietOCRTests(unittest.TestCase):
    def test_accidental_fullscreen_feed_is_rejected_without_losing_multimonitor_support(self):
        self.assertFalse(capture_budget([[0,0,1920,1080]])[0])
        self.assertTrue(capture_budget([[-1400,100,1000,300],[20,100,1000,300]])[0])
        self.assertFalse(capture_budget([[0,0,1000,600],[0,0,1000,600]])[0])
        self.assertFalse(capture_budget([[0,0,'100',200]])[0])

    def test_worker_limits_keep_timeout_and_input(self):
        with patch('ocr_runtime.subprocess.run') as run:
            run_ocr(['ocr'],input=b'pixels',timeout=4,capture_output=True,
                    env={'OMP_NUM_THREADS':'12'})
        options=run.call_args.kwargs
        self.assertEqual(options['env']['OMP_THREAD_LIMIT'],'1')
        self.assertEqual(options['env']['OMP_NUM_THREADS'],'1')
        self.assertEqual(options['input'],b'pixels');self.assertEqual(options['timeout'],4)

    def test_no_diagnostic_writes_when_disabled(self):
        raw=b'You have obtained [Stone] x1.\nYou have obtained [Relic] x2.\nYou have obtained [Milk] x3.'
        response=types.SimpleNamespace(stdout=raw,stderr=b'',returncode=0)
        with tempfile.TemporaryDirectory() as folder, patch('loot_capture.run_ocr',return_value=response):
            diagnostics=Path(folder)/'disabled'
            result=recognize_feed(Image.new('RGB',(100,50),'black'),'ocr','chat',False,diagnostics,diagnostics=False)
            self.assertEqual(len(result['events']),3)
            self.assertFalse(diagnostics.exists())


if __name__=='__main__':unittest.main()
