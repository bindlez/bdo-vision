"""End-to-end bridge HTTP contract without a Windows desktop or real game."""
import json
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'desktop'))
from planner_bridge import PlannerBridge


class BridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bridge = PlannerBridge(ROOT / 'bdo-market-intelligence.html', ports=(7344,))
        assert cls.bridge.server

    @classmethod
    def tearDownClass(cls):
        cls.bridge.close()

    def get(self, path):
        with urllib.request.urlopen(self.bridge.base_url + path, timeout=3) as result:
            return result.headers, result.read()

    def post(self, path, payload, origin=None):
        headers={'Content-Type':'application/json'}
        if origin: headers['Origin']=origin
        request=urllib.request.Request(self.bridge.base_url+path,
                                      json.dumps(payload).encode('utf-8'),
                                      headers=headers, method='POST')
        with urllib.request.urlopen(request, timeout=3) as response:
            return json.load(response)

    def test_serves_full_planner_same_origin(self):
        h, text = self.get('/planner')
        self.assertIn('text/html', h['Content-Type'])
        self.assertIn(b'function pollBridge()', text)

    def test_fairy_is_served_locally_with_original_version_and_opt_in_link(self):
        headers,body=self.get('/fairy')
        self.assertIn('text/html',headers['Content-Type'])
        self.assertIn(b'FairyCodex V36.1',body)
        self.assertIn(b'vision-connect',body)
        self.assertIn(b'fairycodex.treasure.v1',body)
        self.assertNotIn(b'id="vision-connect" type="checkbox" checked',body)

    def test_tool_diagnostics_are_small_isolated_and_read_only(self):
        status={'stage':'found','tools':[{'id':'a','current':95}], 'screenshot':'excluded'}
        self.bridge.update_tool_status(status);status['tools'][0]['current']=7
        _,data=self.get('/tool-reader');view=json.loads(data)
        self.assertEqual(view['tools'][0]['current'],95);self.assertNotIn('screenshot',view)
        request=urllib.request.Request(self.bridge.base_url+'/tool-reader',headers={'Origin':'https://foreign.example'})
        with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(request,timeout=3)
        self.assertEqual(caught.exception.code,403)
        with self.assertRaises(ValueError):self.bridge.update_tool_status({'detail':'x'*17000})

    def test_guild_status_is_read_only_bounded_and_local(self):
        self.bridge.update_guild_status({'current':184,'target':600,'available':True,'image':'excluded'})
        _,data=self.get('/guild-quest');view=json.loads(data)
        self.assertEqual(view['current'],184);self.assertNotIn('image',view)
        request=urllib.request.Request(self.bridge.base_url+'/guild-quest',headers={'Origin':'https://foreign.example'})
        with self.assertRaises(urllib.error.HTTPError) as caught:urllib.request.urlopen(request,timeout=3)
        self.assertEqual(caught.exception.code,403)
        with self.assertRaises(ValueError):self.bridge.update_guild_status({'objective':'x'*5000})

    def test_original_payload_and_timestamp(self):
        reading = self.bridge.send(350,3000,1.2,observed_at=time.time()-4,
                                   session_id='existing',source='ocr')
        h, data=self.get('/durability')
        parsed=json.loads(data)
        for key in ('current','maximum','seconds_per_craft','signal','sent_at'):
            self.assertIn(key,parsed)
            self.assertEqual(reading[key],parsed[key])
        self.assertAlmostEqual(parsed['observed_at'],reading['observed_at'])

    def test_sent_guild_receipt_is_last_seen_and_frozen(self):
        quest={'current':49,'target':600,'last_at':100,'label':'Alchemy guild','objective':'Obtain Catalyst','eta':999,'image':'excluded'}
        self.bridge.send(350,3000,1,guild_quest=quest);quest['current']=500
        _,data=self.get('/durability');saved=json.loads(data)['guild_quest']
        self.assertEqual(saved['current'],49);self.assertEqual(saved['last_at'],100)
        self.assertNotIn('eta',saved);self.assertNotIn('image',saved)

    def test_website_acknowledgment(self):
        reading=self.bridge.send(270,3000,1, session_id='batch')
        ack=self.post('/ack',{'instance_id':reading['instance_id'],'signal':reading['signal']})
        self.assertTrue(ack['ok'])
        self.assertEqual(self.bridge.acknowledgment()[0], reading['signal'])

    def test_rejects_foreign_ack(self):
        event=self.bridge.send(250,3000,1)
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.post('/ack',{'instance_id':'different','signal':event['signal']})
        self.assertEqual(caught.exception.code,409)

    def test_opaque_file_and_sandbox_origins_cannot_read_personal_bridge(self):
        req=urllib.request.Request(self.bridge.base_url+'/durability',method='OPTIONS',
                                   headers={'Origin':'null',
                                            'Access-Control-Request-Private-Network':'true',
                                            'Access-Control-Request-Method':'GET'})
        with self.assertRaises(urllib.error.HTTPError) as response:
            urllib.request.urlopen(req,timeout=3)
        self.assertEqual(response.exception.code,403)
        self.assertIsNone(response.exception.headers.get('Access-Control-Allow-Origin'))

    def test_fallback_port_when_original_port_busy(self):
        first=PlannerBridge(ROOT/'bdo-market-intelligence.html',ports=(7355,))
        second=PlannerBridge(ROOT/'bdo-market-intelligence.html',ports=(7355,7356))
        try:
            self.assertEqual(second.port,7356)
        finally:
            first.close();second.close()


if __name__=='__main__': unittest.main()
