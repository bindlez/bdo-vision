"""CP boundary math, real inventory accounting, model parity and fail-closed OCR."""
import json
import math
import random
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'desktop'))
from cp_planner import calculate,advance,xp_per_cp,to_target
from cp_reader import parse_hud,agreement,read_image
from PIL import Image


def state(**extra):return {'cp':490,'percent':19.26,'counts':{'catalyst':750000},'cashPolicy':'best',**extra}


class CPTests(unittest.TestCase):
    def test_market_default_has_no_npc_fallback_and_keeps_leftovers(self):
        s=state(counts={'catalyst':21});s.pop('cashPolicy')
        r=calculate(s)
        self.assertEqual(r['cashPolicy'],'market');self.assertFalse(r['cashComplete'])
        self.assertIsNone(r['cashTotal']);self.assertIsNone(r['winner'])
        self.assertTrue(all(a['cash'] is None and a['breakEvenDays'] is None for a in r['routes']))
        r=calculate(s,{'Clear Liquid Reagent':{'unit_price':12000}})
        self.assertTrue(r['cashComplete']);self.assertEqual(r['cashTotal'],400*12000*.845)
        self.assertEqual(r['routes'][1]['cash'],0)
        self.assertEqual(next(a for a in r['routes'][1]['allocation'] if a['key']=='catalyst')['remaining'],1)

    def test_750k_example_uses_current_curve(self):
        r=calculate(state());self.assertEqual(r['totalXp'],67500000);self.assertEqual(r['vendorTotal'],15000000000)
        end=r['routes'][1];self.assertEqual(end['cp'],567);self.assertAlmostEqual(end['percent'],95.86314600076523)
        self.assertEqual(r['nextBatches'],373);self.assertEqual(r['targetBatches'],4520)
        self.assertEqual(r['routes'][2]['allocation'][0]['items'],45200)

    def test_curve_boundaries_and_step_increase(self):
        self.assertEqual(xp_per_cp(499),414778);self.assertEqual(xp_per_cp(500),571594)
        self.assertEqual(xp_per_cp(525),914550);self.assertIsNone(xp_per_cp(600))
        self.assertEqual(advance(499,0,414778)['cp'],500)
        self.assertEqual(advance(499,0,414778+571594)['cp'],501)

    def test_fractional_start_carries_across_brackets(self):
        self.assertAlmostEqual(to_target(499,50,501),207389+571594)
        self.assertEqual(advance(499,50,207389)['cp'],500)

    def test_bounded_curve_never_invents_600_plus(self):
        r=calculate(state(cp=599,counts={'catalyst':1000000}))['routes'][1]
        self.assertEqual(r['cp'],600);self.assertIsNone(r['percent']);self.assertGreater(r['unmodeledXp'],0)

    def test_leftovers_keep_npc_value_no_fractional_turnins(self):
        r=calculate(state(counts={'catalyst':19,'leaf':19}))
        self.assertEqual(r['totalBatches'],1);self.assertEqual(r['routes'][1]['cash'],560000)
        self.assertEqual(r['routes'][1]['xp'],900)

    def test_exchange_quantities_tax_and_npc_baseline(self):
        r=calculate(state(counts={'catalyst':21},retention=65),{'Powder of Time':{'unit_price':10000}})
        self.assertEqual(r['cashTotal'],2620000)
        r=calculate(state(counts={'catalyst':21},retention=0),{'Powder of Time':{'unit_price':10000}})
        self.assertEqual(r['cashTotal'],420000)

    def test_unknown_prices_not_a_false_zero_or_global_best(self):
        r=calculate(state());self.assertEqual(len(r['missing']),7);self.assertEqual(r['cashTotal'],15000000000)
        for q in (float('nan'),float('inf'),True,-1):
            self.assertEqual(calculate(state(),{'Shining Powder':{'unit_price':q}})['cashTotal'],15000000000)

    def test_vendor_quote_not_confused_with_market_quote(self):
        r=calculate(state(),{'Shining Powder':{'unit_price':10**9,'price_basis':'npc_vendor'}})
        self.assertEqual(r['cashTotal'],r['vendorTotal'])

    def test_mixed_target_spends_cheapest_cp_exp_first(self):
        r=calculate(state(cp=490,percent=99.9,target=491,counts={'catalyst':10,'leaf':20}),{'Powder of Time':{'unit_price':100000}})
        used={a['key']:a['items'] for a in r['routes'][2]['allocation']}
        self.assertEqual(used,{'catalyst':0,'witch':0,'leaf':20})

    def test_cash_and_cp_exchanges_are_mutually_exclusive(self):
        r=calculate(state(counts={'catalyst':125},split=50))
        for route in r['routes']:
            for a in route['allocation']:
                self.assertEqual(a['items']+a['remaining'],r['products'][next(i for i,p in enumerate(r['products']) if p['key']==a['key'])]['count'])
            self.assertAlmostEqual(route['cash']+route['foregone'],r['cashTotal'])

    def test_target_already_reached_and_unreachable_target(self):
        self.assertEqual(calculate(state(target=490))['routes'][2]['batches'],0)
        r=calculate(state(target=599,counts={'catalyst':10}));self.assertFalse(r['targetReachable']);self.assertEqual(r['routes'][2]['batches'],1)

    def test_zero_incremental_income_no_invented_profit(self):
        r=calculate(state());self.assertEqual(r['winner'],'cash');self.assertEqual(r['routes'][1]['earnings'],0)
        self.assertIsNone(r['routes'][1]['breakEvenDays'])

    def test_deployment_cap_and_setup_delay(self):
        r=calculate(state(income=1000000,deploy=2,days=90,delay=10))['routes'][1]
        self.assertEqual(r['deployed'],2);self.assertEqual(r['earnings'],160000000)
        self.assertEqual(r['breakEvenDays'],7510)
        self.assertEqual(calculate(state(income=1000000,delay=100,days=90))['routes'][1]['earnings'],0)

    def test_invalid_inputs_fail_closed(self):
        for key,value in [('cp',600),('cp',490.5),('percent',100),('days',0),('income',float('nan')),('deploy',True),('retention',101)]:
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):calculate(state(**{key:value}))
        for count in (-1,1.5,True,10**10):
            with self.assertRaises(ValueError):calculate(state(counts={'catalyst':count}))

    def test_reader_understands_total_not_available_cp(self):
        self.assertEqual(parse_hud('157 67 11 / 464 1 / 490 (19.26%)'),(490,19.26,1))
        self.assertEqual(parse_hud('1/490 (19,26%)'),(490,19.26,1))

    def test_reader_ambiguous_malformed_disagreeing_stays_unknown(self):
        for text in ('490 19.26%','1 / 490 (19.2%)','500/490 (19.26%)','1/490 (100.00%)','1/490 (19.26%) 1/491 (19.26%)'):
            self.assertIsNone(parse_hud(text))
        self.assertIsNone(agreement('1/490 (19.26%)','1/490 (19.28%)'))
        self.assertEqual(agreement('1/490 (19.26%)','1 / 490 (19.26%)')['cp'],490)

    def test_reader_budget_rejects_full_frame_and_exactly_two_passes(self):
        with self.assertRaises(ValueError):read_image(Image.new('RGB',(1920,1080)),'unused')
        result=subprocess.CompletedProcess([],0,stdout=b'1 / 490 (19.26%)',stderr=b'')
        with patch('cp_reader.run_ocr',return_value=result) as runner:
            value,_=read_image(Image.new('RGB',(1000,100)),'tesseract')
            self.assertEqual(value['cp'],490);self.assertEqual(runner.call_count,2)
            self.assertTrue(all(c.kwargs['timeout']==2.5 for c in runner.call_args_list))

    def test_python_browser_numeric_parity(self):
        rng=random.Random(411);states=[]
        for i in range(100):states.append(state(cp=rng.randrange(0,600),percent=rng.randrange(10000)/100,target=rng.randrange(601),counts={k:rng.randrange(1000001) for k in ('catalyst','witch','leaf')},income=rng.randrange(1000000),delay=rng.randrange(50),days=rng.randrange(1,366),deploy=rng.randrange(100),split=rng.randrange(101)))
        quotes={'Milk':{'unit_price':10000},'Shining Powder':{'unit_price':200000}}
        js="const fs=require('fs'),e=require('./desktop/assets/cp-engine.js').create(JSON.parse(fs.readFileSync('desktop/assets/cp-data.json'))),v=JSON.parse(fs.readFileSync(0,'utf8'));console.log(JSON.stringify(v.states.map(s=>e.calculate(s,v.quotes))));"
        output=subprocess.check_output(['node','-e',js],input=json.dumps({'states':states,'quotes':quotes}).encode(),cwd=ROOT)
        actual=json.loads(output)
        for s,a in zip(states,actual):
            expected=calculate(s,quotes)
            for key in ('totalXp','targetBatches','nextBatches','cashTotal','winner'):self.assertEqual(a[key],expected[key])
            for x,y in zip(a['routes'],expected['routes']):
                for key in ('cp','gained','deployed','cash','future','difference'):self.assertAlmostEqual(x[key],y[key],places=2)
                if x['percent'] is not None:self.assertAlmostEqual(x['percent'],y['percent'],places=7)


if __name__=='__main__':unittest.main()
