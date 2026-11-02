"""Hand-checkable recovery models, capital constraints and cross-runtime parity."""
import json,math,random,subprocess,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'desktop'))
from cp_planner import calculate
from cp_forecast import analyze,productive_days,payback_days,income_at


def state(**extra):return {'cp':490,'percent':19.26,'counts':{'catalyst':750000},'cashPolicy':'best',**extra}


class ForecastTests(unittest.TestCase):
    def test_linear_ramp_integral_before_during_and_after(self):
        self.assertEqual(productive_days(4,5,10),0)
        self.assertEqual(productive_days(10,5,10),1.25)
        self.assertEqual(productive_days(15,5,10),5)
        self.assertEqual(productive_days(25,5,10),15)

    def test_exact_inverse_during_and_after_ramp(self):
        self.assertEqual(payback_days(125,100,5,10),10)
        self.assertEqual(payback_days(1500,100,5,10),25)
        for investment in (1,125,500,1500,10000000):
            day=payback_days(investment,100,5,10)
            self.assertAlmostEqual(productive_days(day,5,10)*100,investment,places=5)

    def test_zero_income_and_zero_cost_have_explicit_states(self):
        self.assertIsNone(payback_days(100,0))
        self.assertEqual(payback_days(0,0),0)
        r=calculate(state());a=analyze(r)
        self.assertEqual(a['title'],'Set your income plan');self.assertFalse(any(m['reached'] for m in a['milestones']))

    def test_setup_cost_affects_cp_routes_not_cash_route(self):
        r=calculate(state(setup=1000000))
        self.assertEqual(r['routes'][0]['setupCost'],0)
        for route in r['routes'][1:]:self.assertEqual(route['investment'],route['foregone']+1000000)

    def test_project_income_scales_to_deployed_cp_not_total_existing_cp(self):
        r=calculate(state(incomeMode='project',income=7700000,utilization=50))
        self.assertEqual(r['routes'][1]['daily'],3850000)
        self.assertEqual(r['routes'][2]['daily'],500000)

    def test_ramp_and_uptime_reduce_income_and_extend_payback(self):
        r=calculate(state(income=1000000,delay=5,ramp=10,utilization=50,days=15))
        all_cp=r['routes'][1]
        self.assertEqual(all_cp['earnings'],77*1000000*.5*5)
        self.assertGreater(all_cp['breakEvenDays'],calculate(state(income=1000000))['routes'][1]['breakEvenDays'])

    def test_optimizer_does_not_buy_idle_cp_after_deployment_cap(self):
        r=calculate(state(income=500000000,deploy=3));a=analyze(r)
        self.assertEqual(a['optimized']['cp'],493)
        self.assertEqual(a['optimized']['deployed'],3)

    def test_reserve_is_enforced_and_impossible_reserve_stays_unknown(self):
        r=calculate(state(income=10000000,reserve=10000000000));a=analyze(r)
        self.assertGreaterEqual(a['optimized']['cash'],10000000000)
        a=analyze(calculate(state(reserve=16000000000)))
        self.assertFalse(a['reserveFeasible']);self.assertIsNone(a['optimized'])

    def test_targets_within_setup_delay_are_unreachable(self):
        a=analyze(calculate(state(delay=100)))
        self.assertIsNone(a['requirements'][0]['daily']);self.assertIsNone(a['requirements'][1]['perCp'])

    def test_simulation_milestones_are_math_not_saved_income(self):
        r=calculate(state(income=1000000));route=r['routes'][2];day=route['breakEvenDays']
        a=analyze(r,elapsed=day)
        self.assertAlmostEqual(a['recovered'],100);self.assertAlmostEqual(a['simulatedProfit'],0,places=4)
        self.assertTrue(a['milestones'][-1]['reached'])

    def test_unproductive_partial_batch_exchange_has_no_setup_income(self):
        r=calculate(state(cp=490,percent=0,counts={'catalyst':10},setup=1000000,income=1000000))
        self.assertEqual(r['routes'][1]['gained'],0);self.assertEqual(r['routes'][1]['setupCost'],0)
        self.assertEqual(r['routes'][1]['daily'],0)

    def test_browser_advanced_forecast_parity(self):
        rng=random.Random(912);states=[]
        for i in range(40):states.append(state(cp=rng.randrange(450,575),percent=rng.randrange(10000)/100,counts={'catalyst':rng.randrange(1000000),'leaf':rng.randrange(100000)},income=rng.randrange(10000000),incomeMode='project' if i%2 else 'per_cp',utilization=rng.randrange(101),setup=rng.randrange(1000000000),ramp=rng.randrange(31),delay=rng.randrange(15),reserve=rng.randrange(1000000000),days=rng.randrange(1,366)))
        js="const fs=require('fs'),e=require('./desktop/assets/cp-engine.js').create(JSON.parse(fs.readFileSync('desktop/assets/cp-data.json'))),states=JSON.parse(fs.readFileSync(0,'utf8'));console.log(JSON.stringify(states.map(s=>{const r=e.calculate(s);return {r,a:e.analyze(r,'target',30)}})));"
        actual=json.loads(subprocess.check_output(['node','-e',js],input=json.dumps(states).encode(),cwd=ROOT))
        for state_value,value in zip(states,actual):
            r=calculate(state_value);a=analyze(r,'target',30)
            for left,right in zip(r['routes'],value['r']['routes']):
                for key in ('cash','daily','future','investment','recoveryPercent'):self.assertAlmostEqual(left[key],right[key],delta=max(.001,abs(left[key])*1e-10))
                if left['breakEvenDays'] is None:self.assertIsNone(right['breakEvenDays'])
                else:self.assertAlmostEqual(left['breakEvenDays'],right['breakEvenDays'],places=5)
            self.assertEqual(a['candidates'],value['a']['candidates'])
            self.assertEqual(a['optimized']['cp'] if a['optimized'] else None,value['a']['optimized']['cp'] if value['a']['optimized'] else None)


if __name__=='__main__':unittest.main()
