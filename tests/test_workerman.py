"""Discrete CP investment, honest missing data and bounded public reference IO."""
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from workerman import model_job,normalize,WorkermanReference,quote_ids
from cp_planner import calculate

JOB={'id':'131','name':'Farm · Potato','town':'Velia','connectionCp':2,'distance':180,'workload':200,'samples':110,
     'outputs':[{'id':'7003','name':'Potato','quantity':16.5,'giant':27.2}]}
QUOTES={'Potato':{'item_id':7003,'unit_price':2000,'updated_at':'today'},'Clear Liquid Reagent':{'unit_price':12000},'Milk':{'unit_price':10000},'Stonetail Fodder':{'unit_price':4000000}}


class WorkermanTests(unittest.TestCase):
    def report(self,**kwargs):return calculate({'cp':490,'percent':19.26,'target':492,'counts':{'catalyst':750000},**kwargs},QUOTES)

    def test_exact_cycles_payback_and_delay_ramp_uptime(self):
        report=self.report(delay=3,ramp=10,utilization=50,setup=100000)
        m=model_job(JOB,report,QUOTES,{'operatingCost':10000})
        self.assertEqual(m['cycleMinutes'],30.8)
        gross=1440/30.8*16.5*2000
        self.assertAlmostEqual(m['grossPerDay'],gross)
        self.assertAlmostEqual(m['effectivePerDay'],(gross*.845-10000)*.5)
        self.assertAlmostEqual(m['breakEvenDays'],3+5+m['investment']/m['effectivePerDay'])
        self.assertEqual(m['timeline'][0]['earned'],0)
        self.assertAlmostEqual(m['timeline'][-1]['difference'],m['effectivePerDay']*(90-3-5)-m['investment'])

    def test_discrete_job_existing_cp_shortage_unknown_and_negative(self):
        small=model_job(JOB,self.report(target=491),QUOTES)
        self.assertFalse(small['eligible']);self.assertIsNone(small['breakEvenDays']);self.assertEqual(small['timeline'][-1]['earned'],0)
        existing=model_job(JOB,self.report(),QUOTES,{'additionalCp':0})
        self.assertFalse(existing['eligible']);self.assertIsNone(existing['breakEvenDays'])
        missing=model_job(JOB,self.report(),{k:v for k,v in QUOTES.items() if k!='Potato'})
        self.assertIsNone(missing['netPerDay']);self.assertIsNone(missing['breakEvenDays']);self.assertIsNone(missing['differenceAtHorizon'])
        loss=model_job(JOB,self.report(),QUOTES,{'operatingCost':1e8})
        self.assertLess(loss['netPerDay'],0);self.assertIsNone(loss['breakEvenDays'])
        shortage=model_job(JOB,self.report(counts={'catalyst':1}),QUOTES)
        self.assertFalse(shortage['ownedOnly']);self.assertGreater(shortage['shortageItems'],0);self.assertIn('Hypothetical',shortage['status'])
        for value in [float('nan'),-1,True,1.5]:
            with self.assertRaises(ValueError):model_job(JOB,self.report(),QUOTES,{'additionalCp':value})

    def test_identity_conflicts_and_zero_uptime(self):
        ambiguous=quote_ids({'a':{'item_id':1,'unit_price':5},'b':{'item_id':1,'unit_price':9}})
        self.assertNotIn('1',ambiguous)
        m=model_job(JOB,self.report(utilization=0),QUOTES)
        self.assertEqual(m['effectivePerDay'],0);self.assertIsNone(m['breakEvenDays'])

    def test_graph_route_cost_labels_and_single_revision_cache(self):
        raw={'nodes_links.json':{'1':{'is_base_town':True,'link_list':[21],'need_exploration_point':0},'21':{'link_list':[1,131],'need_exploration_point':1},'131':{'link_list':[21],'need_exploration_point':1}},
             'regioninfo.json':{'5':{'key':5,'waypoint':1,'npcWorkerCharacterKey':40018}},
             'loc.json':{'en':{'node':{'1':'Velia','21':'Farm'},'item':{'7003':'Potato'}}},
             'distances_tk2pzk.json':{'5':[[131,180]]},'plantzone.json':{'131':{'parent':21}},
             'manual/plantzone_drops.json':{'131':{'workload':200,'rolls':110,'unlucky':{'7003':16.5},'unlucky_gi':{'7003':27.2}}}}
        normalized=normalize(raw,'a'*40)
        self.assertEqual(normalized['jobs'][0]['connectionCp'],2)
        self.assertEqual(normalized['jobs'][0]['path'],['1','21','131'])
        self.assertEqual(normalized['jobs'][0]['name'],'Farm · Potato')
        with tempfile.TemporaryDirectory() as folder:
            provider=WorkermanReference(Path(folder)/'cache.json');calls=[]
            def fetch(url,limit):
                calls.append(url)
                if 'api.github' in url:return {'object':{'sha':'a'*40}}
                return raw[url.split('/data/')[1]]
            with patch('workerman._download',side_effect=fetch):
                self.assertEqual(provider.refresh()['revision'],'a'*40)
                self.assertEqual(provider.refresh()['revision'],'a'*40)
            self.assertEqual(len(calls),7)
            self.assertTrue(all('/'+'a'*40+'/' in u for u in calls[1:]))
            before=provider.path.read_bytes();cached=provider.cached();cached['fetchedAt']=0;provider.path.write_text(json.dumps(cached),encoding='utf-8')
            with patch('workerman._download',side_effect=OSError('offline')):
                with self.assertRaises(OSError):provider.refresh()
            self.assertEqual(provider.cached()['jobs'],normalized['jobs'])


if __name__=='__main__':unittest.main()
