from pathlib import Path
import sys,unittest
from unittest.mock import patch
from PIL import Image,ImageDraw
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from tool_reader import ToolInventory,AutomaticToolReader,character_anchor,discover_regions,PARTIAL_NAME,label_name,read_bands,verify_labels,label_signature,signature_matches,words,CharacterBoxes,durability_bars,distinct_counters,changing_tool


def row(value,x=200,name='Supreme Alchemy Tool',maximum=5000):
    return {'name':name,'current':value,'maximum':maximum,'box':[x,250,x+200,280],'votes':2,'confidence':90}


class ActiveToolTests(unittest.TestCase):
    def test_pair_requires_one_plausible_verified_change_in_same_fields(self):
        a=[{**row(800),'numbers':[100,10,160,25]},{**row(5000,800),'numbers':[800,10,860,25]}]
        b=[{**a[0],'current':798},dict(a[1])]
        self.assertEqual(changing_tool(a,b,1.5),(100,10,160,25))
        for invalid in ([{**b[0],'current':10},b[1]],[b[0],{**b[1],'current':4998}],[{**b[0],'maximum':9000},b[1]],[{**b[0],'numbers':[300,10,360,25]},b[1]],[{**b[0],'votes':1},b[1]]):
            self.assertIsNone(changing_tool(a,invalid,1.5))
        self.assertIsNone(changing_tool(a,a,1.5));self.assertIsNone(changing_tool(a,b,.2))

    def test_verified_pair_confirms_a_unique_tool_after_one_interval(self):
        inv=ToolInventory();a={**row(800),'numbers':[100,10,160,25]}
        inv.update([a],10,'game')
        result=inv.update([{**a,'current':798}],11.5,'game',confirmed_field=(100,10,160,25))
        self.assertIsNotNone(result['active_id']);self.assertEqual(result['tools'][0]['wear_streak'],2)

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

    def test_two_missing_frames_reset_wear_evidence(self):
        tracker=ToolInventory()
        for at,value in ((0,800),(3,797),(6,794)):tracker.update([row(value)],at)
        tracker.update([],9)
        tracker.update([],12)
        self.assertIsNone(tracker.update([row(785)],15)['active_id'])

    def test_single_ocr_gap_preserves_identity_but_never_reports_hidden_tool(self):
        tracker=ToolInventory()
        for at,value in ((0,800),(3,797),(6,794)):result=tracker.update([row(value)],at)
        active=result['active_id'];self.assertIsNotNone(active)
        self.assertIsNone(tracker.update([],9)['active_id'])
        self.assertEqual(tracker.update([row(788)],12)['active_id'],active)

    def test_unchanged_reads_count_toward_consumption_time(self):
        tracker=ToolInventory()
        for at,value in ((0,800),(3,797),(6,797),(9,794)):result=tracker.update([row(value)],at)
        self.assertEqual(tracker.tracks[result['active_id']]['pace'],[1.,2.])

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
    def test_place_mode_starts_first_read_without_waiting_for_pair(self):
        reader=AutomaticToolReader();tool={**row(800),'id':'chosen','numbers':[1040,240,1100,260],'cycle':0}
        report={'active_id':None,'tools':[tool],'anchor':{'x':1025,'y':190,'evidence':'Place Mode anchor'}}
        with patch.object(reader,'_read',return_value=report),patch.object(reader,'compare_pair') as compare:
            result=reader.read('engine',(1,0,0,1920,1080),lambda b:None,confirm_pair=True)
        self.assertEqual(result['active_id'],'chosen');self.assertEqual(result['confirmation'],'Place Mode position')
        self.assertEqual(result['next_seconds'],1.5);compare.assert_not_called()

    def test_pair_captures_only_label_crops_1_5_seconds_apart(self):
        reader=AutomaticToolReader();reader.context='game'
        region={'name':'Alchemy Tool','box':[100,200,300,230],'numbers':[200,200,280,230]};reader.regions=[region]
        a={**region,'current':800,'maximum':3000,'votes':2};b={**a,'current':798}
        clock=[10.];captures=[];crop=Image.new('RGB',(200,30),'white')
        def grab(box):captures.append((box,clock[0]));return crop
        def sleep(seconds):clock[0]+=seconds
        original={'active_id':None,'tools':[a],'ocr_calls':1,'duration':.1}
        with patch('tool_reader.time.monotonic',side_effect=lambda:clock[0]),patch('tool_reader.time.sleep',side_effect=sleep),patch('tool_reader.label_signature',return_value=Image.new('L',(12,12),'white')),patch('tool_reader.verify_labels',side_effect=[([a],2),([b],2)]):
            result=reader.compare_pair('engine',(1,0,0,1200,800),grab,original,10)
        self.assertEqual([t for _,t in captures],[10.,11.5]);self.assertEqual(captures[0][0],(100,200,300,230))
        self.assertIsNotNone(result['active_id']);self.assertEqual(result['tools'][0]['current'],798)
        self.assertEqual(result['confirmation'],'two-frame comparison')

    def test_confirmed_tracking_does_not_take_an_extra_pair(self):
        reader=AutomaticToolReader()
        with patch.object(reader,'_read',return_value={'active_id':'a','tools':[row(100)]}),patch.object(reader,'compare_pair') as pair:
            reader.read('engine',(1,0,0,1200,800),lambda box:None,confirm_pair=True)
            pair.assert_not_called()

    def test_quote_noise_cannot_swallow_following_tsv_rows(self):
        text='level\tleft\ttop\twidth\theight\tconf\ttext\n5\t0\t0\t10\t20\t10\t"noise\n5\t100\t200\t250\t20\t95\tAlchemy Tool(95/3000)\n'
        tokens=words(text)
        self.assertEqual(len(tokens),2);self.assertEqual(tokens[1]['text'],'Alchemy Tool(95/3000)')
        self.assertEqual(discover_regions(text,(1000,700))[0]['coarse_pair'],(95,3000))

    def test_character_locations_preserve_merged_word_geometry(self):
        parser=CharacterBoxes();parser.feed('<span class="ocrx_cinfo" title="x_bboxes 12 3 18 19; x_conf 90">2</span><span class="ocrx_cinfo" title="x_bboxes 19 3 22 19">/</span>')
        self.assertEqual(parser.chars,[('2',[12,3,18,19]),('/',[19,3,22,19])])

    def test_gold_icons_without_a_thin_shadow_track_are_rejected(self):
        im=Image.new('RGB',(1280,720),'white');draw=ImageDraw.Draw(im)
        draw.rectangle((400,210,440,218),fill=(240,200,70))
        self.assertEqual(durability_bars(im),[])
        draw.rectangle((600,210,669,215),fill=(50,50,50));draw.rectangle((600,211,661,213),fill=(240,200,70))
        self.assertEqual(len(durability_bars(im)),1)

    def test_two_locators_merge_one_counter_and_disagreement_is_excluded(self):
        a={**row(95),'numbers':[100,10,160,25]};b={**row(95,800),'numbers':[103,10,163,25]}
        self.assertEqual(len(distinct_counters([a,b])),1)
        self.assertEqual(distinct_counters([a,{**b,'current':5}]),[])

    def test_bar_validation_is_discovery_only_and_does_not_freeze_counter(self):
        region={'name':'Alchemy Tool','box':[0,0,100,30],'numbers':[20,0,100,30],'locator':'durability bar','bar_pair':(95,3000),'bar_fill':.032}
        header='level\tleft\ttop\twidth\theight\tconf\ttext\n5\t0\t0\t80\t20\t90\t'
        crop=Image.new('RGB',(100,30),'white')
        with patch('tool_reader.ocr',return_value=header+'95/3000\n'):
            self.assertEqual(verify_labels([crop],[region],'engine')[0][0]['current'],95)
        self.assertNotIn('bar_pair',region);self.assertNotIn('bar_fill',region)
        with patch('tool_reader.ocr',return_value=header+'92/3000\n'):
            self.assertEqual(verify_labels([crop],[region],'engine')[0][0]['current'],92)

    def test_bad_numeric_digit_cannot_disagree_with_a_nearly_full_bar(self):
        region={'name':'Alchemy Tool','box':[0,0,100,30],'numbers':[20,0,100,30],'locator':'durability bar','bar_fill':.97}
        raw='level\tleft\ttop\twidth\theight\tconf\ttext\n5\t0\t0\t80\t20\t90\t290/3000\n'
        with patch('tool_reader.ocr',return_value=raw):
            self.assertEqual(verify_labels([Image.new('RGB',(100,30),'white')],[region],'engine')[0],[])

    def test_damaged_separator_requires_independent_digit_field_agreement(self):
        region={'name':PARTIAL_NAME,'box':[0,0,100,30],'numbers':[10,0,95,30],
            'locator':'durability bar','bar_pair':(574,3000),'digit_boxes':[[15,2,40,28],[50,2,90,28]]}
        header='level\tleft\ttop\twidth\theight\tconf\ttext\n5\t0\t0\t20\t20\t90\t'
        crop=Image.new('RGB',(100,30),'white')
        responses=[header+n+'\n' for n in ('574','574','3000','3000')]
        with patch('tool_reader.ocr',side_effect=responses) as engine:
            rows,calls=verify_labels([crop],[dict(region)],'engine')
            self.assertEqual((rows[0]['current'],rows[0]['maximum']),(574,3000));self.assertEqual(calls,4)
        for numbers in (('574','574','73000','73000'),('574','574','3000','300')):
            with patch('tool_reader.ocr',side_effect=[header+n+'\n' for n in numbers]):
                self.assertEqual(verify_labels([crop],[dict(region)],'engine')[0],[])
    def test_fraction_split_across_tokens_gets_one_numeric_crop(self):
        header='level\tleft\ttop\twidth\theight\tconf\ttext\n'
        raw=header+'5\t100\t200\t80\t20\t90\tAlchemy\n5\t185\t200\t60\t20\t90\tTool(95\n5\t250\t200\t6\t20\t90\t/\n5\t260\t200\t50\t20\t90\t3000)\n'
        regions=discover_regions(raw,(1000,700))
        self.assertEqual(len(regions),1);self.assertEqual(regions[0]['coarse_pair'],(95,3000))
        self.assertLess(regions[0]['numbers'][0],240);self.assertGreater(regions[0]['numbers'][2],300)

    def test_verified_numeric_cache_is_exact_bounded_and_expires(self):
        region={'name':'Alchemy Tool','box':[0,0,100,30],'numbers':[20,0,100,30]}
        crop=Image.new('RGB',(100,30),'white');cache={}
        raw='level\tleft\ttop\twidth\theight\tconf\ttext\n5\t0\t0\t80\t20\t90\t95/3000\n'
        with patch('tool_reader.ocr',return_value=raw) as engine,patch('tool_reader.time.monotonic',return_value=100):
            self.assertEqual(verify_labels([crop],[region],'engine',cache)[1],2)
            rows,calls=verify_labels([crop],[region],'engine',cache)
            self.assertEqual(calls,0);self.assertTrue(rows[0]['cache_hit']);self.assertEqual(engine.call_count,2)
        with patch('tool_reader.ocr',return_value=raw),patch('tool_reader.time.monotonic',return_value=109):
            self.assertEqual(verify_labels([crop],[region],'engine',cache)[1],2)
            for number in range(25):
                changed=Image.new('RGB',(100,30),(number,number,number))
                verify_labels([changed],[region],'engine',cache)
            self.assertLessEqual(len(cache),16)

    def test_title_signature_ignores_digits_and_rejects_moved_title(self):
        region={'box':[0,0,200,30],'numbers':[100,0,190,30]}
        image=Image.new('RGB',(200,30),'black');draw=ImageDraw.Draw(image)
        draw.rectangle((10,8,45,17),fill='white');draw.rectangle((110,8,140,17),fill='white')
        original=label_signature(image,region)
        draw.rectangle((100,0,199,29),fill='black')
        self.assertTrue(signature_matches(original,label_signature(image,region)))
        draw.rectangle((0,0,99,29),fill='black');draw.rectangle((55,8,90,17),fill='white')
        self.assertFalse(signature_matches(original,label_signature(image,region)))

    def test_no_labels_retry_quickly_then_back_off(self):
        reader=AutomaticToolReader();image=Image.new('RGB',(1200,800),'black')
        with patch('tool_reader.discover_scene',return_value=([],None,1)):
            delays=[reader.read('engine',(1,0,0,1200,800),lambda box:image.crop(box),now=at)['next_seconds'] for at in (0,3,13,43,103,223)]
        self.assertEqual(delays,[3,10,30,60,120,120])
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
