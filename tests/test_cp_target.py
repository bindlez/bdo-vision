import json
import math
from pathlib import Path
import random
import subprocess
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'desktop'))
from cp_planner import calculate,target_plan


class CPTargetTests(unittest.TestCase):
    def test_target_alone_mixed_and_shortage_quantities(self):
        r=calculate({'cp':490,'percent':19.26,'target':500,'counts':{'catalyst':19,'witch':20,'leaf':39}})
        p=target_plan(r);need=math.ceil(r['targetXp']/900)
        self.assertEqual(p['requiredBatches'],need)
        for solo in p['singles']:
            used=next(x for x in solo['allocation'] if x['key']==solo['key'])
            self.assertEqual(used['items'],need*used['batch']);self.assertEqual(used['shortage'],max(0,used['items']-used['owned']))
            self.assertTrue(solo['reachesTarget']);self.assertGreaterEqual(solo['result']['cp'],500)
        self.assertFalse(p['owned']['reachesTarget']);self.assertTrue(p['owned']['ownedOnly'])
        for row in p['owned']['allocation']:self.assertLessEqual(row['items'],row['owned'])
        for name in ('completion','balanced'):
            self.assertTrue(p[name]['reachesTarget']);self.assertEqual(p[name]['batches'],need)
            self.assertGreater(p[name]['shortageItems'],0)
        self.assertEqual(p['owned']['ownedXp']+p['owned']['missingXp'],p['exchangeXp'])
        self.assertFalse(p['economicOrderKnown']);self.assertIsNone(p['completion']['opportunityCost'])

    def test_target_already_reached_requires_no_exchanges(self):
        p=target_plan(calculate({'cp':509,'percent':46.24,'target':500,'counts':{}}))
        self.assertTrue(p['alreadyReached']);self.assertEqual(p['requiredBatches'],0)
        self.assertTrue(all(r['batches']==0 for r in p['singles']))

    def test_cheapest_known_owned_mix_is_bundle_rounded(self):
        quotes={'Clear Liquid Reagent':{'unit_price':12000},'Milk':{'unit_price':10000},'Stonetail Fodder':{'unit_price':4000000}}
        r=calculate({'cp':490,'percent':19.26,'target':500,'counts':{'catalyst':100000,'witch':1000,'leaf':100000}},quotes)
        p=target_plan(r);allocation={a['key']:a for a in p['owned']['allocation']}
        self.assertTrue(p['economicOrderKnown']);self.assertEqual(allocation['witch']['batches'],100)
        self.assertEqual(allocation['leaf']['batches'],0);self.assertEqual(p['owned']['missingBatches'],0)
        self.assertTrue(all(a['items']%a['batch']==0 for a in allocation.values()))

    def test_browser_native_target_parity(self):
        rng=random.Random(77);states=[]
        for i in range(45):states.append({'cp':rng.randrange(600),'percent':rng.randrange(10000)/100,'target':rng.randrange(601),'counts':{k:rng.randrange(100001) for k in ('catalyst','witch','leaf')}})
        states.extend([{'cp':599,'target':600,'counts':{}},{'cp':490,'target':503,'counts':{}}])
        script="const fs=require('fs'),e=require('./desktop/assets/cp-engine.js').create(JSON.parse(fs.readFileSync('desktop/assets/cp-data.json')));console.log(JSON.stringify(JSON.parse(fs.readFileSync(0,'utf8')).map(s=>e.targetPlan(e.calculate(s)))));"
        actual=json.loads(subprocess.check_output(['node','-e',script],input=json.dumps(states).encode(),cwd=ROOT))
        for state,other in zip(states,actual):
            expected=target_plan(calculate(state))
            self.assertEqual(other,expected)


if __name__=='__main__':unittest.main()
