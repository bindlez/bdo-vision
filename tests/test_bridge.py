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

    def test_original_payload_and_timestamp(self):
        reading = self.bridge.send(350,3000,1.2,observed_at=time.time()-4,
                                   session_id='existing',source='ocr')
        h, data=self.get('/durability')
        parsed=json.loads(data)
        for key in ('current','maximum','seconds_per_craft','signal','sent_at'):
            self.assertIn(key,parsed)
            self.assertEqual(reading[key],parsed[key])
        self.assertAlmostEqual(parsed['observed_at'],reading['observed_at'])

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

    def test_legacy_file_cors_and_private_network_preflight(self):
        req=urllib.request.Request(self.bridge.base_url+'/durability',method='OPTIONS',
                                   headers={'Origin':'null',
                                            'Access-Control-Request-Private-Network':'true',
                                            'Access-Control-Request-Method':'GET'})
        with urllib.request.urlopen(req, timeout=3) as response:
            self.assertEqual(response.status,204)
            self.assertEqual(response.headers['Access-Control-Allow-Origin'],'null')
            self.assertEqual(response.headers['Access-Control-Allow-Private-Network'],'true')

    def test_fallback_port_when_original_port_busy(self):
        first=PlannerBridge(ROOT/'bdo-market-intelligence.html',ports=(7355,))
        second=PlannerBridge(ROOT/'bdo-market-intelligence.html',ports=(7355,7356))
        try:
            self.assertEqual(second.port,7356)
        finally:
            first.close();second.close()


if __name__=='__main__': unittest.main()
