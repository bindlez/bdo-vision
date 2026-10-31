"""Equipment import, bounded requests and history-independent build backups."""
import sys,unittest,tempfile,json,time,io,base64
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from urllib.request import Request,urlopen
from urllib.error import HTTPError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from gear_ocr import parse_equipment,read_equipment
from gear_store import save,load
from planner_bridge import PlannerBridge

CAT=[{'id':11013,'name':"Giath's Helmet",'mainCategory':15,'subCategory':1},
     {'id':12001,'name':'Yuria Ring','mainCategory':20,'subCategory':1},
     {'id':10101,'name':'Vangertz Shield','mainCategory':5,'subCategory':1}]
ENDGAME=[{'id':719897,'name':"Labreska's Helmet",'mainCategory':15,'subCategory':1},
         {'id':12294,'name':'Kharazad Belt','mainCategory':20,'subCategory':4},
         {'id':719899,'name':"Dahn's Gloves",'mainCategory':15,'subCategory':3}]


class GearTests(unittest.TestCase):
    def test_named_rank_without_roman_and_origin_title_after_scene_noise(self):
        text=('Unrelated scene text\n\n'*300)+"PEN: Kharazad Belt\nDistorted Labreskats Helmet"
        result=parse_equipment(text,CAT+ENDGAME)['candidates']
        self.assertEqual([(x['id'],x['enhancement']['value'],x['enhancement']['kind']) for x in result],[(12294,5,'roman'),(719897,2,'numeric')])

    def test_description_references_are_not_equipped_item_titles(self):
        text="Cron Stones can be used when enhancing Labreska's Helmet.\nused when enhancing Dahn's Gloves\n- Description: Kharazad Belt"
        self.assertEqual(parse_equipment(text,ENDGAME)['candidates'],[])

    def test_named_prefix_is_only_accepted_for_the_verified_armor_family(self):
        self.assertEqual(parse_equipment('Distorted Yuria Ring',CAT)['candidates'],[])
        self.assertEqual(parse_equipment("PEN (IV): Giath's Helmet",CAT)['candidates'],[])

    def test_level_on_separate_header_line(self):
        result=parse_equipment('PEN (V):\nKharazad Belt',ENDGAME)['candidates'][0]
        self.assertEqual(result['enhancement']['value'],5)

    def test_tooltip_capture_preserves_full_panel_at_screen_edges(self):
        from gear_sweep import tooltip_box
        rect=SimpleNamespace(left=0,top=0,right=1920,bottom=1080)
        for x,y in [(0,0),(1850,900),(1850,150),(900,500)]:
            box=tooltip_box(rect,SimpleNamespace(x=x,y=y))
            self.assertEqual(box[3]-box[1],1080)
            self.assertEqual(box[2]-box[0],1280)
            self.assertTrue(0<=box[0]<box[2]<=1920)

    def test_uncertain_scene_reads_retry_only_the_tooltip_header(self):
        from gear_ocr import recognize_image
        from PIL import Image
        tsv='level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n5\t1\t1\t1\t1\t1\t700\t400\t260\t30\t95\tEquipment(Helmet)\n'
        results=[SimpleNamespace(returncode=0,stdout=tsv.encode()),SimpleNamespace(returncode=0,stdout=b'Distorted Labreskats Helmet')]
        with patch('gear_ocr.subprocess.run',side_effect=results) as execute:
            report=recognize_image(Image.new('RGB',(800,600),'black'),ENDGAME,'unused')
        self.assertEqual(report['candidates'][0]['id'],719897)
        self.assertEqual(report['focused_passes'],1)
        self.assertEqual(execute.call_args_list[0].args[0][-1],'tsv')
        self.assertEqual(execute.call_args_list[1].args[0][4],'6')

    def test_nonmarket_supplement_requires_unique_index_identity(self):
        from item_catalog import DiskItemDatabase
        from gear_catalog import equipment_extras
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory,'public.json');source.write_text(json.dumps([{'id':12294,'name':'Kharazad Belt'},{'id':12140,'name':'Kharazad Ring'},{'id':999999,'name':'Kharazad Ring'}]),encoding='utf8')
            DiskItemDatabase.from_json(source,Path(directory,'item-catalog.sqlite3'))
            rows=equipment_extras(directory)
            self.assertEqual([r['id'] for r in rows],[12294])
            self.assertFalse(rows[0]['marketListed']);self.assertEqual(rows[0]['maxEnhance'],10)

    def test_level_and_identity_remain_separate(self):
        r=parse_equipment("PEN (V): Giath's Helmet\nDP: 80",CAT)
        self.assertEqual(r['candidates'][0]['id'],11013)
        self.assertEqual(r['candidates'][0]['enhancement']['value'],5)
        self.assertEqual(r['stats']['dp'],[80]);self.assertTrue(r['candidates'][0]['review_required'])

    def test_names_starting_with_roman_letters_are_not_truncated(self):
        r=parse_equipment('Vangertz Shield',CAT)['candidates'][0]
        self.assertEqual(r['id'],10101);self.assertIsNone(r['enhancement'])

    def test_ambiguous_and_unrelated_text_is_not_imported(self):
        self.assertEqual(parse_equipment('System chat\nDP 300\nUnknown equipment',CAT)['candidates'],[])
        self.assertEqual(parse_equipment("Giath's Helmet",CAT+[{**CAT[0],'id':99001}])['candidates'],[])

    def test_duplicate_rings_are_independent_candidates(self):
        r=parse_equipment('TET (IV): Yuria Ring\nPEN (V): Yuria Ring',CAT)
        self.assertEqual([x['enhancement']['value'] for x in r['candidates']],[4,5])

    def test_image_size_and_catalog_validation_precedes_ocr(self):
        with self.assertRaises(ValueError):read_equipment({'image':'data:image/png;base64,invalid','catalog':CAT},'missing')
        with self.assertRaises(ValueError):parse_equipment('',[{'id':1,'name':'Milk','mainCategory':35}])

    def test_synthetic_tooltip_pixels_use_real_ocr(self):
        from PIL import Image,ImageDraw,ImageFont
        tess=Path(r'C:\Program Files\Tesseract-OCR\tesseract.exe')
        if not tess.exists():self.skipTest('Tesseract unavailable')
        image=Image.new('RGB',(650,150),'white');draw=ImageDraw.Draw(image)
        font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',30)
        draw.text((20,25),"PEN (V): Giath's Helmet",font=font,fill='black')
        blob=io.BytesIO();image.save(blob,format='PNG')
        report=read_equipment({'image':'data:image/png;base64,'+base64.b64encode(blob.getvalue()).decode(),'catalog':CAT},tess)
        self.assertEqual(report['candidates'][0]['id'],11013)
        self.assertEqual(report['candidates'][0]['enhancement']['value'],5)

    def test_backup_retains_previous_without_creating_loot_db(self):
        with tempfile.TemporaryDirectory() as directory:
            a={'version':1,'active':'a','builds':[{'id':'a','name':'A','current':{},'target':{}}]}
            save(directory,a);a['builds'][0]['name']='B';save(directory,a)
            self.assertEqual(load(directory)['data']['builds'][0]['name'],'B')
            self.assertEqual(json.loads(Path(directory,'gear-builds.previous.json').read_text())['data']['builds'][0]['name'],'A')
            self.assertFalse(Path(directory,'loot-history.sqlite3').exists())

    def test_bridge_sweep_is_one_shot_and_releases_busy_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            bridge=PlannerBridge(Path(__file__).resolve().parents[1]/'bdo-market-intelligence.html',ports=(0,),price_book=SimpleNamespace(path=str(Path(directory,'history.sqlite3'))))
            try:
                with patch('gear_sweep.tooltip_sweep',return_value={'candidates':[],'text':'','stats':{}}):
                    req=Request(bridge.base_url+'/gear/sweep',json.dumps({'catalog':CAT}).encode(),{'Content-Type':'application/json'})
                    with urlopen(req,timeout=3) as reply:job=json.load(reply)
                    for _ in range(20):
                        with urlopen(bridge.base_url+'/gear/sweep?id='+job['id'],timeout=3) as reply:result=json.load(reply)
                        if result['stage']=='review':break
                        time.sleep(.01)
                    self.assertEqual(result['stage'],'review')
                self.assertTrue(bridge.gear_ocr_gate.acquire(timeout=1));bridge.gear_ocr_gate.release()
                bad=Request(bridge.base_url+'/gear/sweep',b'{"catalog":null}',{'Content-Type':'application/json'})
                with self.assertRaises(HTTPError) as error:urlopen(bad,timeout=3)
                self.assertEqual(error.exception.code,400)
                self.assertTrue(bridge.gear_ocr_gate.acquire(timeout=1));bridge.gear_ocr_gate.release()
                hostile=Request(bridge.base_url+'/gear/sweep',json.dumps({'catalog':CAT}).encode(),{'Content-Type':'application/json','Origin':'https://untrusted.example'})
                with self.assertRaises(HTTPError) as error:urlopen(hostile,timeout=3)
                self.assertEqual(error.exception.code,403)
            finally:bridge.close()
