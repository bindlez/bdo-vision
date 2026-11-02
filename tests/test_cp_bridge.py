"""Explicit CP snapshot requests share the protected, bounded loopback bridge."""
import json
import sys
import unittest
import urllib.request
import urllib.error
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'desktop'))
from planner_bridge import PlannerBridge


class CPBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bridge=PlannerBridge(ROOT/'bdo-market-intelligence.html',ports=(7379,7380))
        assert cls.bridge.server

    @classmethod
    def tearDownClass(cls):cls.bridge.close()

    def setUp(self):
        b=self.bridge;b.commands=[];b.cp_request_at=-1e9;b.cp_reading={'stage':'idle'};b.ocr_paused=False

    def request(self,path,body=None,origin=None):
        headers={}
        if body is not None:headers['Content-Type']='application/json'
        if origin:headers['Origin']=origin
        req=urllib.request.Request(self.bridge.base_url+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
        with urllib.request.urlopen(req,timeout=3) as response:return response.status,json.load(response)

    def test_read_is_an_explicit_command_no_live_capture_in_http_thread(self):
        status,r=self.request('/cp-read',{'instance_id':self.bridge.instance_id})
        self.assertEqual(status,202);self.assertEqual(self.bridge.consume_commands(),[{'id':r['id'],'action':'cp-read'}])
        _,reading=self.request('/cp-reading');self.assertEqual(reading['requestId'],r['id']);self.assertEqual(reading['stage'],'waiting')
        with self.assertRaises(urllib.error.HTTPError) as caught:self.request('/cp-read',{'instance_id':self.bridge.instance_id})
        self.assertEqual(caught.exception.code,429)

    def test_lite_mode_and_stale_instance_do_not_queue(self):
        for body,paused,code in (({'instance_id':'old'},False,409),({'instance_id':self.bridge.instance_id},True,403)):
            self.bridge.ocr_paused=paused
            with self.assertRaises(urllib.error.HTTPError) as caught:self.request('/cp-read',body)
            self.assertEqual(caught.exception.code,code);self.assertFalse(self.bridge.consume_commands())

    def test_cp_status_rejects_foreign_origins(self):
        for route,body in (('/cp-reading',None),('/cp-plan',None),('/cp-read',{'instance_id':self.bridge.instance_id})):
            with self.assertRaises(urllib.error.HTTPError) as caught:self.request(route,body,'https://foreign.example')
            self.assertEqual(caught.exception.code,403)

    def test_native_cp_scenario_is_a_read_only_snapshot(self):
        self.bridge.cp_plan={'cp':'490','counts':{'catalyst':'90000'},'ramp':'10','incomeMode':'project'}
        _,result=self.request('/cp-plan');self.assertEqual(result['plan']['counts']['catalyst'],'90000')
        result['plan']['counts']['catalyst']='0'
        self.assertEqual(self.bridge.cp_plan['counts']['catalyst'],'90000')

    def test_bounded_request_and_queue(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:self.request('/cp-read',{'instance_id':self.bridge.instance_id,'extra':'x'*5000})
        self.assertEqual(caught.exception.code,400)
        self.bridge.commands=[{}]*5
        with self.assertRaises(urllib.error.HTTPError) as caught:self.request('/cp-read',{'instance_id':self.bridge.instance_id})
        self.assertEqual(caught.exception.code,429)


if __name__=='__main__':unittest.main()
