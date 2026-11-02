import io,json,sqlite3,sys,tempfile,unittest,subprocess
from pathlib import Path
from unittest.mock import patch
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from guild_quest import GuildQuestProgress,parse_quest_text,recognize_quest,parse_objectives,parse_guild_completion


def reading(current,target=600):return {'current':current,'target':target,'label':'[Alchemy] Glorious Guild Supply Mission','objective':'Obtain Mysterious Catalyst via Alchemy'}


REWARD='Claim your rewards via the "Complete\nMission" button in the Guild Mission window.'
def completed():return {**parse_guild_completion(REWARD),'completion_votes':2}


class QuestParsingTests(unittest.TestCase):
    def test_complete_widget_works_with_obscured_heading_and_both_literal_messages(self):
        for text in (REWARD,'The guild mission is complete.', '[Alchemy] Guild Supply Mission\n'+REWARD):
            self.assertTrue(parse_guild_completion(text)['completion_observed'])
            self.assertNotIn('current',parse_guild_completion(text))

    def test_personal_complete_negation_and_instructions_cannot_complete_guild(self):
        for text in ('[Daily] Alchemy\nMake Oil (100/100)', 'Reach Lv. 57 (Complete)',
                     'The guild mission is not complete.', 'The guild mission is incomplete.',
                     'When the guild mission is complete.', 'Claim your rewards\n[Daily] Alchemy\nvia the "Complete Mission" button in the Guild Mission window.',
                     'Click the Complete Mission button in the Guild Mission window.',
                     'If ready: The guild mission is complete.'):
            self.assertIsNone(parse_guild_completion(text),text)

    def test_completion_requires_two_passes_and_rejects_conflicting_incomplete_counter(self):
        for texts,accepted in (((REWARD,REWARD),True),((REWARD,'nothing readable'),False),
                               ((REWARD,REWARD+'\n[Alchemy] Guild Supply Mission\nObtain Catalyst (599/600)'),False)):
            responses=[type('Result',(),{'returncode':0,'stdout':t.encode()})() for t in texts]
            with patch('guild_quest.run_ocr',side_effect=responses),patch('guild_quest.guild_heading_crops',return_value=[]):
                result,_=recognize_quest(Image.new('RGB',(300,100),'black'),'engine')
            self.assertEqual(bool(result and result.get('completion_observed')),accepted)

    def test_real_ocr_of_generated_completed_widget(self):
        engine=Path(r'C:\Program Files\Tesseract-OCR\tesseract.exe')
        if not engine.exists():self.skipTest('Tesseract unavailable')
        image=Image.new('RGB',(450,140),(20,21,25));draw=ImageDraw.Draw(image);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
        for at,text in enumerate(('Claim your rewards via the "Complete', 'Mission" button in the Guild Mission window.', '[Bonus] Skill Up for Alchemy', 'Make Reagent (15/100)')):
            draw.text((8,8+at*29),text,font=font,fill=(245,211,150))
        result,_=recognize_quest(image,str(engine))
        self.assertTrue(result['completion_observed']);self.assertEqual(result['completion_votes'],2)
        self.assertNotIn('current',result)

    def test_focused_guild_body_recovers_both_wrapped_heights_without_borrowing(self):
        crop=Image.new('RGB',(240,20),'black');crop.info['quest_box']=(0,0,240,20)
        for counter in ('49/\n600','\n101/600'):
            body='Obtain Catalyst ('+counter+')\n[Daily] Alchemy\nMake Oil (22/100)'
            responses=['no counter','no counter','[Alchemy] Guild Supply Mission',body,body]
            with patch('guild_quest.run_ocr',side_effect=[type('Result',(),{'returncode':0,'stdout':t.encode()})() for t in responses]),patch('guild_quest.guild_heading_crops',return_value=[crop]):
                result,raw=recognize_quest(Image.new('RGB',(300,150),'black'),'engine')
            self.assertEqual(result['current'],101 if '101' in counter else 49)
            self.assertEqual(result['target'],600);self.assertIn('FOCUSED',raw)

    def test_disagreeing_focused_guild_body_does_not_accept_a_number(self):
        crop=Image.new('RGB',(240,20),'black');crop.info['quest_box']=(0,0,240,20)
        responses=['no counter','no counter','[Alchemy] Guild Supply Mission','Obtain Catalyst (184/600)','Obtain Catalyst (84/600)']
        with patch('guild_quest.run_ocr',side_effect=[type('Result',(),{'returncode':0,'stdout':t.encode()})() for t in responses]),patch('guild_quest.guild_heading_crops',return_value=[crop]):
            self.assertIsNone(recognize_quest(Image.new('RGB',(300,150),'black'),'engine')[0])

    def test_optional_caption_timeout_preserves_verified_guild_counter(self):
        body=b'[Alchemy] Guild Supply Mission\nObtain Catalyst (184/600)'
        success=type('Result',(),{'returncode':0,'stdout':body})()
        with patch('guild_quest.run_ocr',side_effect=[success,success,subprocess.TimeoutExpired('engine',1)]),patch('guild_quest.guild_heading_crops',return_value=[Image.new('RGB',(200,20),'black')]):
            result,_=recognize_quest(Image.new('RGB',(300,100),'black'),'engine')
        self.assertEqual(result['current'],184)
    def test_daily_bonus_require_each_counter_to_agree(self):
        one='[Daily][Alchemy] Striving\nMake Oil (31/100)\n[Bonus] Skill Up for Alchemy\nMake Reagent (21/100)'
        two=one.replace('31/100','30/100')
        with patch('guild_quest.run_ocr',side_effect=[type('Result',(),{'returncode':0,'stdout':t.encode()})() for t in (one,two)]):
            result,_=recognize_quest(Image.new('RGB',(300,100),'black'),'engine')
        self.assertNotIn('current',result);self.assertEqual([(r['kind'],r['current']) for r in result['objectives']],[('Bonus',21)])

    def test_counter_placement_and_line_height_do_not_change_scoping(self):
        for block in ('Obtain Catalyst (49/\n600)','Obtain Catalyst (\n101/600)','Obtain Catalyst\n49/\n600'):
            r=parse_quest_text('[Alchemy] Guild Supply Mission\n'+block+'\n[Daily] Alchemy\nMake Oil (30/100)')
            self.assertEqual((r['current'],r['target']),(101 if '101' in block else 49,600))

    def test_daily_bonus_and_guild_counts_stay_in_their_objectives(self):
        text='[Alchemy] Guild Supply Mission\nObtain Catalyst (186/600)\n[Daily][Alchemy] Striving\nMake Oil of Corruption x100 (31/100)\nTalk to Liana\n[Bonus] Skill Up for Alchemy\nMake Pure Powder Reagent (21/100)'
        rows=parse_objectives(text)
        self.assertEqual([(r['kind'],r['current'],r['target']) for r in rows],[('Daily',31,100),('Bonus',21,100)])
        self.assertEqual(parse_quest_text(text)['current'],186)

    def test_wrapped_real_widget_ignores_personal_quest_counter(self):
        text='Unaccepted Quest\n[Alchemy] Glorious Guild Supp...\nRemaining: 287 min\n- Obtain Mysterious Catalyst via Alchemy (\n184 / 600 )\n[Bonus] Skill Up for Alchemy\nMake Pure Powder Reagent (2/100)'
        result=parse_quest_text(text);self.assertEqual((result['current'],result['target']),(184,600));self.assertIn('Mysterious Catalyst',result['objective'])

    def test_missing_next_heading_still_uses_only_guild_objective(self):
        result=parse_quest_text('[Alchemy] Guild Supply Mission\nObtain Mysterious Catalyst via Alchemy (\n184/600)\nMake Pure Powder Reagent (2/100)')
        self.assertEqual(result['current'],184)

    def test_no_counter_can_be_borrowed_from_a_personal_quest(self):
        self.assertIsNone(parse_quest_text('[Alchemy] Guild Supply Mission\nRemaining: 1 min\n[Bonus] Alchemy\nMake Pure Powder Reagent (2/100)'))
        self.assertIsNone(parse_quest_text('[Bonus] Alchemy\nObtain Mysterious Catalyst via Alchemy (184/600)'))

    def test_damaged_or_ambiguous_quantities_are_not_shortened(self):
        for counter in ('?84/600','1,84/600','184/60?','700/600','184/0','10/20 184/600'):
            self.assertIsNone(parse_quest_text('[Alchemy] Guild Supply Mission\nObtain Mysterious Catalyst '+counter),counter)

    def test_thousands_and_exact_completion(self):
        result=parse_quest_text('[Alchemy] Guild Supply Mission\nProduce elixirs (1,000/1,000)')
        self.assertEqual((result['current'],result['target']),(1000,1000))

    def test_wrapped_separator_noise_keeps_new_quest_count(self):
        result=parse_quest_text('[Alchemy] Glorious Guild Supply Mission\nObtain Mysterious Catalyst via Alchemy (13\n/-600)\n[Bonus] Make Reagent (8/100)')
        self.assertEqual((result['current'],result['target']),(13,600))
        self.assertIsNone(parse_quest_text('[Alchemy] Guild Supply Mission\nObtain Catalyst (13/-600)'))

    def test_live_double_slash_punctuation_preserves_literal_digits(self):
        text="[Alchemy] Glorious Guild Supply Mission\nObtain Mysterious Catalyst via Alchemy (\n362'//600))\n[Daily] Make Oil (24/100)"
        result=parse_quest_text(text)
        self.assertEqual((result['current'],result['target']),(362,600))
        for counter in ("?62'//600", "362'//60?", "362'//-600", "362'///600"):
            self.assertIsNone(parse_quest_text('[Alchemy] Guild Supply Mission\nObtain Catalyst ('+counter+')'),counter)

    def test_live_unpaired_goal_quote_keeps_525_and_rejects_damaged_digits(self):
        result=parse_quest_text("[Alchemy] Glorious Guild Supply Mission\nObtain Mysterious Catalyst via Alchemy (\n525 /'600))\n[Daily] Make Oil (27/100)")
        self.assertEqual((result['current'],result['target']),(525,600))
        self.assertIsNone(parse_quest_text("[Alchemy] Guild Supply Mission\nObtain Catalyst (525 /'60?)"))

    def test_real_ocr_of_generated_mission_widget(self):
        engine=Path(r'C:\Program Files\Tesseract-OCR\tesseract.exe')
        if not engine.exists():self.skipTest('Tesseract unavailable')
        image=Image.new('RGB',(480,170),(20,21,25));draw=ImageDraw.Draw(image);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
        for at,text in enumerate(('[Alchemy] Glorious Guild Supply Mission','Obtain Mysterious Catalyst via Alchemy','(540 / 600)','[Bonus] Skill Up for Alchemy','Make Pure Powder Reagent (2/100)')):draw.text((12,10+at*29),text,font=font,fill=(245,211,150) if at==0 else 'white')
        result,_=recognize_quest(image,str(engine));self.assertIsNotNone(result);self.assertEqual(result['current'],540)

    def test_two_passes_must_agree_before_progress_changes(self):
        texts=[b'[Alchemy] Guild Supply Mission\nObtain Catalyst (184/600)',b'[Alchemy] Guild Supply Mission\nObtain Catalyst (84/600)']
        with patch('guild_quest.run_ocr',side_effect=[type('Result',(),{'returncode':0,'stdout':t})() for t in texts]):
            self.assertIsNone(recognize_quest(Image.new('RGB',(300,100),'black'),'engine')[0])

    def test_oversized_crop_and_exhausted_budget_do_not_launch_ocr(self):
        with patch('guild_quest.run_ocr') as engine:
            with self.assertRaises(ValueError):recognize_quest(Image.new('RGB',(1000,1000)),'engine')
            engine.assert_not_called()
            with patch('guild_quest.time.monotonic',side_effect=[0,3.1]):
                with self.assertRaises(RuntimeError):recognize_quest(Image.new('RGB',(300,100)),'engine')
            engine.assert_not_called()

    def test_focused_gold_header_recovers_near_complete_counter(self):
        bodies=[b"Remaining: 258 min\nObtain Mysterious Catalyst via Alchemy (\n593:/'600')\nMake Oil (20/100)",b'Remaining: 258 min\nObtain Mysterious Catalyst via Alchemy (\n593/600)\nMake Oil (20/100)',b'[Alchemy] Glorious Guild Supp...']
        responses=[type('Result',(),{'returncode':0,'stdout':t})() for t in bodies]
        with patch('guild_quest.run_ocr',side_effect=responses),patch('guild_quest.guild_heading_crops',return_value=[Image.new('RGB',(240,20),'black')]):
            result,_=recognize_quest(Image.new('RGB',(300,100),'black'),'engine')
        self.assertEqual((result['current'],result['target']),(593,600))

    def test_focused_personal_header_cannot_supply_guild_context(self):
        bodies=[b'Obtain Mysterious Catalyst via Alchemy (593/600)']*2+[b'[Daily] Alchemy Mission']
        with patch('guild_quest.run_ocr',side_effect=[type('Result',(),{'returncode':0,'stdout':t})() for t in bodies]),patch('guild_quest.guild_heading_crops',return_value=[Image.new('RGB',(240,20),'black')]):
            self.assertIsNone(recognize_quest(Image.new('RGB',(300,100),'black'),'engine')[0])


class QuestStateTests(unittest.TestCase):
    def setUp(self):self.db=sqlite3.connect(':memory:');self.state=GuildQuestProgress(self.db)
    def tearDown(self):self.db.close()

    def test_visual_completion_preserves_last_numeric_counter_and_deduplicates(self):
        self.state.accept(reading(599),at=100)
        self.assertEqual(self.state.accept(completed(),at=110),['complete'])
        self.assertEqual(self.state.accept(completed(),at=120),[])
        view=self.state.snapshot(121)
        self.assertTrue(view['complete']);self.assertTrue(view['available'])
        self.assertEqual((view['current'],view['target'],view['last_at']),(599,600,100))
        self.assertEqual((view['percent'],view['remaining'],view['completion_at']),(100,0,110))
        restarted=GuildQuestProgress(self.db)
        self.assertTrue(restarted.snapshot(121)['complete']);self.assertFalse(restarted.snapshot(121)['available'])
        self.assertEqual(restarted.accept(completed(),at=130),[])

    def test_completion_before_any_counter_persists_and_next_quest_needs_two_reads(self):
        self.state.accept(completed(),at=100);self.state=GuildQuestProgress(self.db)
        self.assertIsNone(self.state.current);self.assertTrue(self.state.complete_sent)
        self.state.accept(reading(0),at=110);self.assertTrue(self.state.complete_sent)
        self.state.accept(reading(2),at=120);self.assertFalse(self.state.complete_sent)
        self.assertEqual(self.state.current,2);self.assertIsNone(self.state.completion_at)

    def test_visual_completion_then_same_or_higher_incomplete_counter_reconfirms_new_quest(self):
        self.state.accept(reading(599),at=100);self.state.accept(completed(),at=110)
        self.state.accept(reading(599),at=120);self.assertTrue(self.state.complete_sent)
        self.state.accept(reading(599),at=130);self.assertFalse(self.state.complete_sent)
        self.assertEqual(self.db.execute('SELECT current FROM guild_quest_history').fetchone()[0],599)

    def test_completion_cache_refresh_does_not_write_database_each_read(self):
        self.state.accept(completed(),at=100);writes=self.db.total_changes
        self.state.accept(completed(),at=120)
        self.assertEqual(writes,self.db.total_changes);self.assertTrue(self.state.snapshot(140)['available'])
        self.state.pause('Window covered');self.assertTrue(self.state.snapshot(141)['complete'])
        self.assertFalse(self.state.snapshot(141)['available'])
        self.state.reset();self.assertFalse(self.state.snapshot(142)['complete'])

    def test_unverified_completion_cannot_change_saved_state(self):
        self.state.accept(reading(599),at=100)
        for r in ({'completion_observed':True},{**completed(),'completion_votes':1},{**completed(),'completion_basis':'loot'}):
            self.assertEqual(self.state.accept(r,at=110),[]);self.assertFalse(self.state.complete_sent)

    def test_default_warning_waits_until_95_percent(self):
        self.assertEqual(self.state.accept(reading(569),at=100),[])
        self.assertEqual(self.state.accept(reading(570),at=110),['near'])
        self.assertEqual(self.state.accept(reading(571),at=120),[])

    def test_refilled_mission_timer_confirms_new_quest_without_false_completion(self):
        self.state.accept({**reading(590),'remaining_minutes':200},at=100)
        self.state.accept({**reading(10),'remaining_minutes':299},at=110)
        self.assertEqual(self.state.current,590)
        self.state.accept({**reading(12),'remaining_minutes':299},at=120)
        self.assertEqual(self.state.current,12);self.assertFalse(self.state.complete_sent)
        self.assertEqual(self.db.execute('SELECT current FROM guild_quest_history').fetchone()[0],590)

    def test_legacy_saved_mission_migrates_only_after_two_new_visible_reads(self):
        self.state.accept(reading(414),at=100)
        payload=json.loads(self.db.execute('SELECT payload FROM guild_quest_state').fetchone()[0]);payload.pop('mission_deadline');payload.pop('legacy_saved')
        self.db.execute('UPDATE guild_quest_state SET payload=?',(json.dumps(payload),));self.db.commit()
        migrated=GuildQuestProgress(self.db)
        migrated.save();migrated=GuildQuestProgress(self.db)
        migrated.accept({**reading(57),'remaining_minutes':299},at=200)
        self.assertEqual(migrated.current,414)
        migrated.accept({**reading(60),'remaining_minutes':299},at=210)
        self.assertEqual(migrated.current,60);self.assertFalse(migrated.complete_sent)
        self.assertEqual(self.db.execute('SELECT current FROM guild_quest_history').fetchone()[0],414)

    def test_near_and_complete_alert_once_and_survive_restart(self):
        self.assertEqual(self.state.accept(reading(184),90,100),[])
        self.assertEqual(self.state.accept(reading(540),90,120),['near'])
        self.assertEqual(self.state.accept(reading(590),90,130),[])
        self.assertEqual(self.state.accept(reading(600),90,140),['complete'])
        restarted=GuildQuestProgress(self.db)
        self.assertFalse(restarted.snapshot(141)['available'])
        self.assertEqual(restarted.accept(reading(600),90,150),[])

    def test_first_complete_read_has_one_completion_alert(self):
        self.assertEqual(self.state.accept(reading(600),90,100),['complete'])

    def test_blocked_capture_retains_actual_value_and_clears_eta(self):
        self.state.accept(reading(100),at=100);self.state.accept(reading(200),at=120)
        self.assertEqual(self.state.snapshot(120)['eta'],80)
        self.state.pause('Window covered');view=self.state.snapshot(130)
        self.assertEqual(view['current'],200);self.assertFalse(view['available']);self.assertIsNone(view['eta'])

    def test_old_reading_is_stale_without_advancing_progress(self):
        self.state.accept(reading(184),at=100);view=self.state.snapshot(136)
        self.assertFalse(view['available']);self.assertEqual(view['remaining'],416)

    def test_unexpected_decrease_or_target_change_cannot_reset_live_quest(self):
        self.state.accept(reading(400),at=100)
        for at,r in ((110,reading(40)),(120,reading(400,1000))):
            self.assertEqual(self.state.accept(r,at=at),[]);self.assertEqual(self.state.current,400);self.assertEqual(self.state.target,600)

    def test_completed_quest_reset_needs_two_separate_readings(self):
        self.state.accept(reading(600),at=100)
        self.state.accept(reading(0),at=110);self.assertEqual(self.state.current,600)
        self.state.accept(reading(2),at=120);self.assertEqual(self.state.current,2)
        self.assertEqual(self.db.execute('SELECT count(*) FROM guild_quest_history').fetchone()[0],1)

    def test_next_quest_archives_previous_progress(self):
        self.state.accept(reading(184),at=100);self.state.reset()
        self.assertIsNone(self.state.current)
        self.assertEqual(self.db.execute('SELECT current,target FROM guild_quest_history').fetchone(),(184,600))
