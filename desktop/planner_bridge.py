"""Local-first HTTP bridge compatible with the original BDO Vision planner.

GET /durability still has the original current/maximum/seconds_per_craft/signal/
sent_at values. The paired planner is also served at /planner on this same origin:
this avoids file:// -> localhost browser restrictions and stale mismatched files.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock, Thread
import socket
import os
import json
import time
import uuid
import copy
from urllib.parse import urlsplit,parse_qs
from activity_data import timer_earnings,grind_session_detail
from version import APP_VERSION

PORTS = tuple(range(7283, 7293))


class ExclusiveHTTPServer(ThreadingHTTPServer):
    # Windows SO_REUSEADDR allows competing listeners; reserve one app per port.
    allow_reuse_address = False

    def server_bind(self):
        if os.name == 'nt':
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


class PlannerBridge:
    def __init__(self, html_path, current=1000, maximum=3000, seconds_per_craft=1, ports=PORTS, price_book=None):
        self.html_path = Path(html_path)
        self.price_book = price_book
        self._lock = Lock()
        self.instance_id = uuid.uuid4().hex
        self.signal = 0
        self.ack_signal = 0
        self.ack_at = 0.0
        self.last_error = ''
        self.show_requested=False
        self.commands=[]
        self.data = {
            'current': int(current), 'maximum': int(maximum),
            'seconds_per_craft': float(seconds_per_craft),
            'signal': 0, 'sent_at': 0,
            'observed_at': 0, 'instance_id': self.instance_id,
            'session_id': '', 'bridge_version': 13,
        }
        self.server = None
        self.port = None
        self._start(ports)

    @property
    def base_url(self):
        return f'http://127.0.0.1:{self.port}' if self.port else None

    @property
    def planner_url(self):
        return self.base_url + '/planner#craft' if self.base_url else None

    def _start(self, ports):
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _headers(self, content_type, length):
                origin = self.headers.get('Origin', '')
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(length))
                self.send_header('Cache-Control', 'no-store')
                # Allow standalone local file:// planner as a fallback, but not
                # arbitrary internet origins accessing the user's local bridge.
                if origin == 'null' or origin.startswith(('http://127.0.0.1:', 'http://localhost:')):
                    self.send_header('Access-Control-Allow-Origin', origin)
                    self.send_header('Vary', 'Origin')
                    self.send_header('Access-Control-Allow-Private-Network', 'true')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')

            def _send(self, payload, status=200, content_type='application/json; charset=utf-8'):
                blob = payload if isinstance(payload, bytes) else json.dumps(payload).encode('utf-8')
                self.send_response(status)
                self._headers(content_type, len(blob))
                self.end_headers()
                if self.command != 'HEAD':
                    self.wfile.write(blob)

            def do_OPTIONS(self):
                self._send(b'', 204)

            def do_GET(self):
                route = urlsplit(self.path).path
                if route in ('/', '/planner'):
                    try:
                        content = bridge.html_path.read_bytes()
                    except OSError:
                        self._send({'error': 'Planner HTML not found beside the app'}, 404)
                        return
                    self._send(content, 200, 'text/html; charset=utf-8')
                elif route == '/durability':
                    with bridge._lock:
                        value = dict(bridge.data)
                    shared=value.get('crafting_loot')
                    revision=parse_qs(urlsplit(self.path).query).get('loot_revision',[''])[0]
                    if shared and revision and revision==shared.get('summary_revision'):
                        value['crafting_loot']={k:v for k,v in shared.items() if k!='items'}
                        value['crafting_loot']['items_unchanged']=True
                    self._send(value)
                elif route == '/health':
                    with bridge._lock:
                        self._send({
                            'ok': True, 'bridge_version': 13, 'app_version':APP_VERSION,'instance_id': bridge.instance_id,
                            'signal': bridge.signal, 'last_ack_signal': bridge.ack_signal,
                            'last_ack_at': bridge.ack_at, 'port': bridge.port,
                            'planner_exists': bridge.html_path.is_file(),
                            'app_id':'bdo-vision','pid':os.getpid(),
                            'data_path':str(Path(bridge.price_book.path).resolve().parent) if bridge.price_book else '',
                        })
                elif route == '/prices':
                    if bridge.price_book:
                        self._send({'prices':bridge.price_book.all()})
                    else:self._send({'error':'Price book unavailable'},503)
                elif route == '/timer-earnings':
                    with bridge._lock:shared=bridge.data.get('crafting_loot')
                    if not shared or not bridge.price_book:
                        self._send({'error':'Optional loot sharing is off'},403);return
                    try:
                        query=parse_qs(urlsplit(self.path).query)
                        after=int(query.get('after',['0'])[0]);before=query.get('before',[None])[0]
                        history=query.get('history',[''])[0]
                        if history!=shared.get('history_id'):
                            self._send({'error':'History changed; reattach this timer'},409);return
                        region=query.get('region',['NA'])[0].upper()
                        if region not in ('NA','EU'):raise ValueError('Unknown market region')
                        since=query.get('since',[None])[0]
                        kind=query.get('kind',[None])[0]
                        value=timer_earnings(bridge.price_book.path,bridge.price_book.all(region),after,before,since,kind)
                        self._send({'history_id':shared['history_id'],**value})
                    except (ValueError,OverflowError):self._send({'error':'Invalid timer range'},400)
                elif route == '/grind-session':
                    with bridge._lock:shared=bridge.data.get('crafting_loot')
                    if not shared or not bridge.price_book:self._send({'error':'Optional loot sharing is off'},403);return
                    query=parse_qs(urlsplit(self.path).query);session=query.get('id',[''])[0]
                    if len(session)>64:self._send({'error':'Invalid session'},400);return
                    result=grind_session_detail(bridge.price_book.path,bridge.price_book.all(),session)
                    self._send(result if result else {'error':'Session not found'},200 if result else 404)
                elif route == '/favicon.ico':
                    self._send(b'', 204)
                else:
                    self._send({'error': 'Unknown endpoint'}, 404)

            def do_POST(self):
                route=urlsplit(self.path).path
                if route not in ('/ack','/market-prices','/craft-quotes','/show','/grind-command'):
                    self._send({'error': 'Unknown endpoint'}, 404)
                    return
                if self.headers.get('Origin', '') not in ('', 'null', bridge.base_url, f'http://localhost:{bridge.port}'):
                    self._send({'error': 'Origin not allowed'}, 403)
                    return
                if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
                    self._send({'error': 'JSON required'}, 415)
                    return
                try:
                    length = int(self.headers.get('Content-Length', 0))
                    if length <= 0 or length > (250000 if route=='/market-prices' else 16384 if route=='/craft-quotes' else 4096):
                        raise ValueError('Invalid body length')
                    body = json.loads(self.rfile.read(length).decode('utf-8'))
                    if route=='/craft-quotes':
                        if not bridge.price_book:self._send({'error':'Price book unavailable'},503);return
                        try:items=bridge.price_book.recipe_quotes(body['names'],str(body['region']).upper())
                        except (OSError,RuntimeError):self._send({'error':'Market lookup unavailable; cached values retained'},503);return
                        self._send({'items':items,'region':str(body['region']).upper()});return
                    if not isinstance(body,dict):raise ValueError('JSON object required')
                    if route=='/grind-command':
                        if body.get('instance_id')!=bridge.instance_id:
                            self._send({'error':'Unknown instance'},409);return
                        with bridge._lock:shared=bridge.data.get('crafting_loot')
                        if not shared:self._send({'error':'Optional loot sharing is off'},403);return
                        action=body.get('action')
                        if action not in ('start','pause','finish'):raise ValueError('Invalid action')
                        spot=str(body.get('spot','')).strip()[:100];target=str(body.get('target','')).strip()[:100]
                        goal=int(body.get('goal',1))
                        if not 1<=goal<=1_000_000:raise ValueError('Invalid goal')
                        command={'id':uuid.uuid4().hex,'action':action,'spot':spot,'target':target,'goal':goal}
                        with bridge._lock:
                            if len(bridge.commands)>=5:self._send({'error':'Command pending'},429);return
                            bridge.commands.append(command)
                        self._send({'accepted':True,'id':command['id']},202);return
                    if route=='/show':
                        if body.get('instance_id')!=bridge.instance_id:
                            self._send({'error':'Unknown instance'},409);return
                        with bridge._lock:bridge.show_requested=True
                        self._send({'ok':True});return
                    if route=='/market-prices':
                        if not bridge.price_book:
                            self._send({'error':'Price book unavailable'},503);return
                        count=bridge.price_book.update_market(body['items'],body['region'])
                        self._send({'ok':True,'quotes_received':count});return
                    signal = int(body['signal'])
                    instance_id = str(body['instance_id'])
                except (TypeError, ValueError, KeyError, UnicodeError):
                    self._send({'error': 'Invalid price or acknowledgment'}, 400)
                    return
                with bridge._lock:
                    if instance_id != bridge.instance_id or signal <= 0 or signal > bridge.signal:
                        self._send({'error': 'Unknown event'}, 409)
                        return
                    bridge.ack_signal = max(bridge.ack_signal, signal)
                    bridge.ack_at = time.time()
                self._send({'ok': True, 'acknowledged_signal': signal})

        for port in ports:
            try:
                server = ExclusiveHTTPServer(('127.0.0.1', int(port)), Handler)
                self.server = server
                self.port = server.server_address[1]
                Thread(target=server.serve_forever, name='bdo-planner-bridge', daemon=True).start()
                return
            except OSError as exc:
                self.last_error = str(exc)
        self.last_error = 'All local bridge ports busy: ' + ', '.join(map(str, ports))

    def send(self, current, maximum, seconds_per_craft, observed_at=None, session_id=None, source='manual',crafting_loot=None):
        if not self.server:
            raise RuntimeError(self.last_error or 'Local bridge offline')
        with self._lock:
            self.signal += 1
            self.data = {
                'current': int(current), 'maximum': int(maximum),
                'seconds_per_craft': float(seconds_per_craft),
                'signal': self.signal, 'sent_at': time.time(),
                'observed_at': float(observed_at or time.time()),
                'instance_id': self.instance_id, 'session_id': str(session_id or ''),
                'bridge_version': 12, 'source': str(source),
            }
            if crafting_loot is not None:self.data['crafting_loot']=copy.deepcopy(crafting_loot)
            return dict(self.data)

    def acknowledgment(self):
        with self._lock:
            return self.ack_signal, self.ack_at

    def consume_show_request(self):
        with self._lock:
            value=self.show_requested;self.show_requested=False;return value

    def consume_commands(self):
        with self._lock:
            commands=self.commands;self.commands=[];return commands

    def clear_crafting_loot(self):
        with self._lock:self.data.pop('crafting_loot',None)

    def update_crafting_loot(self,snapshot):
        with self._lock:self.data['crafting_loot']=copy.deepcopy(snapshot)

    def close(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
