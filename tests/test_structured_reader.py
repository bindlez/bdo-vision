import sys
from pathlib import Path
import unittest
from unittest.mock import patch
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from structured_reader import tool_regions,quest_objective_identity,StructuredLocator
from tool_reader import counter_context_error,anchored_title_family
from guild_quest import parse_quest_text,guild_heading_family
from windows_ocr import WindowsOCR


def positioned(text,line=1,x=0):
    return {'text':text,'line':line,'x':x,'y':20,'w':len(text)*8,'h':16}


class StructuredReaderTests(unittest.TestCase):
    def test_several_tools_on_one_engine_line_are_distinct_fields(self):
        result={'words':[positioned('Place Mode',1),positioned('Alchemy Tool(3000/3000)',2),positioned('Alchemy Tool(2950/3000)',2,300)]}
        regions,anchor=tool_regions(result)
        self.assertEqual([r['os_pair'] for r in regions],[(3000,3000),(2950,3000)])
        self.assertLess(regions[0]['numbers'][2],regions[1]['numbers'][0]);self.assertIn('Place Mode',anchor['evidence'])

    def test_locator_can_use_missing_slash_but_numeric_verifier_cannot(self):
        regions,_=tool_regions({'words':[positioned('Alchemy Tool(2491 3000)')]})
        self.assertEqual(regions[0]['os_pair'],(2491,3000))
        self.assertTrue(counter_context_error(249,3000,regions[0]))
        self.assertFalse(counter_context_error(2491,3000,regions[0]))
        self.assertTrue(counter_context_error(2492,3000,regions[0]))

    def test_detailed_locator_keeps_tools_beyond_the_nearest_one(self):
        class Worker:
            def recognize(self,*a,**kw):
                return {'words':[positioned('Place Mode',1,100),positioned('Alchemy Tool(3000/3000)',2,100),positioned('Alchemy Tool(2900/3000)',2,460)]}
        locator=StructuredLocator(Worker())
        regions,_,_=locator.locate_all(Image.new('RGB',(1280,720)),'engine')
        self.assertEqual([r['os_pair'] for r in regions],[(3000,3000),(2900,3000)])

    def test_damaged_title_still_does_not_repair_digits(self):
        self.assertEqual(anchored_title_family('2iMorningLightTraditionalAlchemvlocl24olys000)'), 'Alchemy Tool')
        regions,_=tool_regions({'words':[positioned('Alchemy Tool(29O0/3000)')]})
        self.assertFalse(regions)

    def test_wrapped_quest_and_cooking_scope(self):
        for text in ('49/\n600','0\n/600','\n101/600'):
            r=parse_quest_text('[Cooking] Guild Supply Mission\nObtain Beer via Cooking ('+text+')\n[Bonus] Alchemy\nMake Oil (50/100)')
            self.assertEqual(r['target'],600)
        self.assertEqual(guild_heading_family('LAIchemyl Glorious Guild Supply'),'alchemy')

    def test_catalog_name_resolution_does_not_merge_unrelated_objectives(self):
        identity=lambda text:quest_objective_identity({'objective':text})
        self.assertEqual(identity('Obtain Mysterious Gatalyst via Alchemy'),identity('Obtain Mysterious Catalyst via Alchemy'))
        self.assertNotEqual(identity('Obtain Catalyst via Alchemy'),identity('Make Oil via Alchemy'))

    def test_unavailable_worker_falls_back_without_guessing(self):
        class Worker:
            def recognize(self,*a,**kw):raise RuntimeError('Unavailable')
        locator=StructuredLocator(Worker())
        with patch('tool_reader.discover_scene',return_value=([],{},1)) as fallback:
            self.assertEqual(locator(Image.new('RGB',(640,480)),'engine'),([],{},1))
            fallback.assert_called_once();self.assertEqual(locator.last_error,'Unavailable')

    def test_transport_rejects_oversized_frame_before_starting(self):
        worker=WindowsOCR('does-not-exist.exe')
        with self.assertRaises(ValueError):worker.recognize(Image.new('L',(1501,1000)))
        self.assertIsNone(worker.process)


if __name__=='__main__':unittest.main()
