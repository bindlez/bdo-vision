"""Real localhost requests: origins, rebinding, malformed bodies and worker bounds."""
import http.client
import json
from pathlib import Path
import socket
import sys
import unittest
from urllib.request import Request, urlopen
from urllib.error import HTTPError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'desktop'))
from planner_bridge import PlannerBridge


class BridgeSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bridge=PlannerBridge(Path(__file__).resolve().parents[1]/'bdo-market-intelligence.html',ports=(0,))

    @classmethod
    def tearDownClass(cls):cls.bridge.close()

    def test_reads_reject_foreign_and_other_local_origins(self):
        for origin in ('https://untrusted.example','null','http://127.0.0.1:1','http://localhost:1'):
            with self.subTest(origin=origin),self.assertRaises(HTTPError) as error:
                urlopen(Request(self.bridge.base_url+'/health',headers={'Origin':origin}),timeout=3)
            self.assertEqual(error.exception.code,403)
            self.assertIsNone(error.exception.headers.get('Access-Control-Allow-Origin'))

    def test_local_preflight_and_protective_headers(self):
        request=Request(self.bridge.base_url+'/health',method='OPTIONS',headers={'Origin':self.bridge.base_url})
        with urlopen(request,timeout=3) as reply:
            self.assertEqual(reply.status,204)
            self.assertEqual(reply.headers['Access-Control-Allow-Origin'],self.bridge.base_url)
            self.assertEqual(reply.headers['X-Frame-Options'],'DENY')
            self.assertEqual(reply.headers['X-Content-Type-Options'],'nosniff')

    def test_rebinding_host_and_cross_site_fetch_rejected(self):
        for headers in ({'Host':'attacker.example'}, {'Sec-Fetch-Site':'cross-site'}):
            with self.subTest(headers=headers),self.assertRaises(HTTPError) as error:
                urlopen(Request(self.bridge.base_url+'/health',headers=headers),timeout=3)
            self.assertEqual(error.exception.code,403)

    def raw(self,headers,body=b''):
        connection=http.client.HTTPConnection('127.0.0.1',self.bridge.port,timeout=5)
        try:
            connection.putrequest('POST','/ack')
            connection.putheader('Content-Type','application/json')
            for name,value in headers:connection.putheader(name,value)
            connection.endheaders(body)
            reply=connection.getresponse();status=reply.status;reply.read()
            return status
        finally:connection.close()

    def test_ambiguous_and_oversized_requests_fail_before_reading_body(self):
        for headers in ([('Content-Length','4097')],
                        [('Content-Length','2'),('Content-Length','2')],
                        [('Content-Length','2'),('Transfer-Encoding','chunked')],
                        [('Content-Length','2'),('Content-Encoding','gzip')]):
            self.assertEqual(self.raw(headers),400)

    def test_nonfinite_and_deep_json_return_a_controlled_error(self):
        for body in (b'{"signal":NaN}', b'{"x":'+b'['*1200+b'0'+b']'*1200+b'}'):
            self.assertEqual(self.raw([('Content-Length',str(len(body)))],body),400)

    def test_slow_body_times_out_and_server_recovers(self):
        self.assertEqual(self.raw([('Content-Length','20')],b'{'),408)
        with urlopen(self.bridge.base_url+'/health',timeout=3) as reply:
            self.assertTrue(json.load(reply)['ok'])

    def test_worker_limit_rejects_excess_and_recovers(self):
        slots=self.bridge.server.request_slots;acquired=0
        try:
            for _ in range(8):
                self.assertTrue(slots.acquire(timeout=1));acquired+=1
            # Closing an unread excess request can reset the socket on Windows;
            # both an explicit 503 and a closed connection are bounded refusal.
            with self.assertRaises((HTTPError,ConnectionError)) as error:
                urlopen(self.bridge.base_url+'/health',timeout=3)
            if isinstance(error.exception,HTTPError):self.assertEqual(error.exception.code,503)
            self.assertFalse(slots.acquire(blocking=False))
        finally:
            for _ in range(acquired):slots.release()
        with urlopen(self.bridge.base_url+'/health',timeout=3) as reply:self.assertEqual(reply.status,200)


if __name__=='__main__':unittest.main()
