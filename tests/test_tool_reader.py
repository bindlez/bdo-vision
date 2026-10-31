from pathlib import Path
import sys,unittest
from unittest.mock import patch
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from tool_reader import ToolInventory,AutomaticToolReader,character_anchor,discover_regions,PARTIAL_NAME,label_name,read_bands


def row(value,x=200,name='Supreme Alchemy Tool',maximum=5000):
    return {'name':name,'current':value,'maximum':maximum,'box':[x,250,x+200,280],'votes':2,'confidence':90}


class ActiveToolTests(unittest.TestCase):
    def test_active_needs_two_separate_decreases(self):
        tracker=ToolInventory()
        for at,value in ((0,800),(3,797)):
            self.assertIsNone(tracker.update([row(value),row(5000,800)],at)['active_id'])
        result=tracker.update([row(794),row(5000,800)],6)
        self.assertEqual(next(t for t in result['tools'] if t['id']==result['active_id'])['current'],794)

    def test_camera_motion_reacquires_by_durability_not_nearest_position(self):
        tracker=ToolInventory()
        tracker.update([row(800,100),row(5000,800)],0)
        tracker.update([row(797,100),row(5000,800)],3)
        result=tracker.update([row(794,100),row(5000,800)],6);active=result['active_id']
        moved=tracker.update([row(791,900),row(5000,200)],9)
        self.assertEqual(moved['active_id'],active)
        self.assertEqual(next(t for t in moved['tools'] if t['id']==active)['current'],791)

    def test_multiple_changing_tools_remain_ambiguous(self):
        tracker=ToolInventory()
        for at,values in ((0,(800,4000)),(3,(797,3997)),(6,(794,3994))):
            result=tracker.update([row(values[0]),row(values[1],800)],at)
        self.assertIsNone(result['active_id']);self.assertIn('Several',result['reason'])

    def test_missing_labels_reset_wear_evidence(self):
        tracker=ToolInventory()
        for at,value in ((0,800),(3,797),(6,794)):tracker.update([row(value)],at)
        tracker.update([],9)
        self.assertIsNone(tracker.update([row(788)],12)['active_id'])

    def test_large_jump_does_not_select_another_tool(self):
        tracker=ToolInventory()
        tracker.update([row(4000)],0)
        self.assertIsNone(tracker.update([row(10)],3)['active_id'])

    def test_identical_counts_do_not_create_consumption_evidence(self):
        tracker=ToolInventory()
        for at in (0,3,6,9):
            self.assertIsNone(tracker.update([row(5000,200),row(5000,800)],at)['active_id'])

    def test_replacement_and_changed_client_reset_selection(self):
        tracker=ToolInventory()
        for at,value in ((0,800),(3,797),(6,794)):tracker.update([row(value)],at,'window-1')
        self.assertIsNone(tracker.update([row(5000)],9,'window-1')['active_id'])
        self.assertIsNone(tracker.update([row(4997)],12,'window-2')['active_id'])

    def test_partially_covered_name_keeps_count_evidence_without_inventing_prefix(self):
        tracker=ToolInventory()
        for at,value in ((0,800),(3,797),(6,794)):
            result=tracker.update([row(value,name=PARTIAL_NAME)],at)
        self.assertIsNotNone(result['active_id']);self.assertEqual(result['tools'][0]['name'],PARTIAL_NAME)


class DiscoveryTests(unittest.TestCase):
    def test_damaged_leading_digit_never_becomes_a_shorter_durability(self):
        header='level\tleft\ttop\twidth\theight\tconf\ttext\n'
        damaged=header+'5\t0\t0\t200\t20\t90\tAlchemy Tool(?5/3000)\n'
        self.assertEqual(read_bands(damaged,[(0,30)]),{})
    def test_literal_tool_tail_is_supported_but_hp_is_not(self):
        self.assertEqual(label_name('Tool{2890/3000)'),PARTIAL_NAME)
        self.assertIsNone(label_name('HP 2373/2373 Weight 34/464'))
        self.assertEqual(label_name('Rr raditional Alchemy Tool'),'Alchemy Tool')

    def test_character_anchor_uses_bars_without_requiring_them(self):
        image=Image.new('RGB',(1000,700),'black');draw=ImageDraw.Draw(image)
        draw.rectangle((450,350,550,353),fill=(220,30,30))
        draw.rectangle((450,360,550,363),fill=(20,70,230))
        anchor=character_anchor(image)
        self.assertEqual(anchor['evidence'],'paired character bars');self.assertLess(abs(anchor['x']-500),5)
        self.assertEqual(character_anchor(Image.new('RGB',(1000,700),'white'))['evidence'],'screen-centre search prior')

    def test_camera_lost_cached_labels_trigger_discovery_in_same_scan(self):
        reader=AutomaticToolReader();bounds=(1,0,0,1200,800)
        reader.context=(1,0,0,1200,800);reader.last_discovery=10
        reader.regions=[{'name':'Alchemy Tool','box':[100,200,350,240]}]
        image=Image.new('RGB',(1200,800),'black');grabs=[]
        def grab(box):grabs.append(box);return image.crop(box)
        with patch('tool_reader.verify_labels',side_effect=[([],2),([row(500)],2)]),patch('tool_reader.ocr',return_value=''),patch('tool_reader.discover_regions',return_value=[{'name':'Alchemy Tool','box':[800,200,1050,240]}]):
            result=reader.read('engine',bounds,grab,now=12)
        self.assertIn((0,0,1200,800),grabs)
        self.assertTrue(result['discovery']);self.assertEqual(result['tools'][0]['current'],500)

    def test_real_ocr_discovers_and_tracks_without_calibration_after_camera_shift(self):
        from PIL import ImageFont
        engine=Path(r'C:\Program Files\Tesseract-OCR\tesseract.exe')
        if not engine.exists():self.skipTest('Tesseract unavailable')
        font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
        reader=AutomaticToolReader();active=None
        for at,current,positions in [(0,1475,(100,760)),(3,1472,(100,760)),(6,1469,(100,760)),(9,1466,(900,100))]:
            image=Image.new('RGB',(1280,720),(45,45,45));draw=ImageDraw.Draw(image)
            draw.text((positions[0],220),f'Alchemy Tool({current}/3000)',font=font,fill='white',stroke_width=1,stroke_fill='black')
            draw.text((positions[1],260),'Alchemy Tool(995/3000)',font=font,fill='white',stroke_width=1,stroke_fill='black')
            result=reader.read(str(engine),(1,0,0,1280,720),lambda box:image.crop(box),now=at)
            self.assertIn(current,[r['current'] for r in result['tools']])
            if at==6:active=result['active_id'];self.assertIsNotNone(active)
            if at==9:self.assertEqual(result['active_id'],active)


if __name__=='__main__':unittest.main()
