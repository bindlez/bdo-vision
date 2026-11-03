"""Local-first HTTP bridge compatible with the original BDO Vision planner.

GET /durability still has the original current/maximum/seconds_per_craft/signal/
sent_at values. The paired planner is also served at /planner on this same origin:
this avoids file:// -> localhost browser restrictions and stale mismatched files.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Lock, Thread, BoundedSemaphore, Event
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
    request_queue_size = 8

    def __init__(self,*args,**kwargs):
        self.request_slots=BoundedSemaphore(8)
        super().__init__(*args,**kwargs)

    def process_request(self,request,address):
        if not self.request_slots.acquire(blocking=False):
            try:
                request.settimeout(.5)
                request.sendall(b'HTTP/1.0 503 Service Unavailable\r\nConnection: close\r\nContent-Length: 0\r\n\r\n')
            except OSError:pass
            finally:self.shutdown_request(request)
            return
        try:super().process_request(request,address)
        except BaseException:
            self.request_slots.release()
            raise

    def process_request_thread(self,request,address):
        try:super().process_request_thread(request,address)
        finally:self.request_slots.release()

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
        self.cp_reading={'stage':'idle','message':'No CP snapshot requested'}
        self.cp_plan={}
        self.stream_enabled=False;self.stream_snapshot={}
        self.cp_request_at=-1e9
        self.gear_ocr_gate=BoundedSemaphore(1)
        self.gear_job=None;self.gear_stop=Event()
        self.ocr_paused=False
        self.gear_store_lock=Lock()
        self.tool_status={'stage':'idle','title':'Waiting for the native reader','tools':[]}
        self.companion_status={}
        self.guild_status={'enabled':False,'available':False,'current':None,'target':None}
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
            server_version='BDOVision'
            sys_version=''

            def setup(self):
                self.request.settimeout(3)
                super().setup()

            def _origin_allowed(self):
                return self.headers.get('Origin','') in ('',bridge.base_url,f'http://localhost:{bridge.port}')

            def parse_request(self):
                if not super().parse_request():return False
                hosts=self.headers.get_all('Host',[])
                if len(hosts)!=1 or hosts[0].lower() not in (f'127.0.0.1:{bridge.port}',f'localhost:{bridge.port}'):
                    self._send({'error':'Use the paired localhost planner'},403);return False
                if not self._origin_allowed() or self.headers.get('Sec-Fetch-Site','')=='cross-site':
                    self._send({'error':'Origin not allowed; open the planner from Vision'},403);return False
                return True

            def log_message(self, *args):
                pass

            def _headers(self, content_type, length):
                origin = self.headers.get('Origin', '')
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', str(length))
                self.send_header('Cache-Control', 'no-store')
                self.send_header('X-Content-Type-Options','nosniff')
                self.send_header('X-Frame-Options','DENY')
                self.send_header('Referrer-Policy','no-referrer')
                self.send_header('Cross-Origin-Resource-Policy','same-origin')
                self.send_header('Content-Security-Policy',"frame-ancestors 'none'; object-src 'none'; base-uri 'none'")
                # Opaque/sandboxed origins cannot be distinguished from file://.
                # Keep personal APIs on the paired local planner's exact origin.
                if origin and self._origin_allowed():
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
                if route=='/stream':
                    from live_grind import stream_page
                    self._send(stream_page(),content_type='text/html; charset=utf-8');return
                if route=='/stream-state':
                    with bridge._lock:enabled=bridge.stream_enabled;snapshot=copy.deepcopy(bridge.stream_snapshot)
                    if not enabled:self._send({'error':'OBS sharing is off'},403);return
                    self._send(snapshot);return
                if route=='/cp-reading':
                    with bridge._lock:status=copy.deepcopy(bridge.cp_reading)
                    self._send(status)
                elif route=='/cp-plan':
                    with bridge._lock:plan=copy.deepcopy(bridge.cp_plan)
                    self._send({'plan':plan})
                elif route=='/tool-reader':
                    with bridge._lock:status=copy.deepcopy(bridge.tool_status)
                    self._send(status)
                elif route=='/guild-quest':
                    with bridge._lock:status=copy.deepcopy(bridge.guild_status)
                    self._send(status)
                elif route in ('/', '/planner'):
                    try:
                        content = bridge.html_path.read_bytes()
                    except OSError:
                        self._send({'error': 'Planner HTML not found beside the app'}, 404)
                        return
                    self._send(content, 200, 'text/html; charset=utf-8')
                elif route=='/fairy':
                    try:content=bridge.html_path.with_name('fairycodex.html').read_bytes()
                    except OSError:self._send({'error':'Fairy Codex is not included in this build'},404);return
                    self._send(content,200,'text/html; charset=utf-8')
                elif route == '/gear/extras':
                    if not bridge.price_book:self._send({'items':[]});return
                    try:
                        from gear_catalog import equipment_extras
                        self._send({'items':equipment_extras(Path(bridge.price_book.path).parent)})
                    except (OSError,ValueError):self._send({'items':[],'notice':'Local equipment index unavailable'})
                elif route == '/gear/builds':
                    if not bridge.price_book:self._send({'error':'Windows profile unavailable'},503);return
                    try:
                        from gear_store import load
                        with bridge.gear_store_lock:payload=load(Path(bridge.price_book.path).parent)
                        self._send(payload if payload else {'error':'No Windows gear backup yet'},200 if payload else 404)
                    except (OSError,ValueError,KeyError):self._send({'error':'Gear backup could not be read; current browser builds are safe'},503)
                elif route == '/gear/sweep':
                    ident=parse_qs(urlsplit(self.path).query).get('id',[''])[0]
                    with bridge._lock:job=copy.deepcopy(bridge.gear_job)
                    if not job or ident!=job['id']:self._send({'error':'Import not found'},404);return
                    self._send(job)
                elif route == '/durability':
                    with bridge._lock:
                        value = dict(bridge.data)
                        value['companion']=copy.deepcopy(bridge.companion_status)
                        value['guild_status']=copy.deepcopy(bridge.guild_status)
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
                if route not in ('/ack','/market-prices','/craft-quotes','/craft-market','/craft-model','/show','/grind-command','/cp-read','/workerman','/gear/ocr','/gear/sweep','/gear/builds'):
                    self._send({'error': 'Unknown endpoint'}, 404)
                    return
                if not self._origin_allowed():
                    self._send({'error': 'Origin not allowed'}, 403)
                    return
                if self.headers.get('Content-Type', '').split(';')[0].strip() != 'application/json':
                    self._send({'error': 'JSON required'}, 415)
                    return
                try:
                    if self.headers.get('Transfer-Encoding') or len(self.headers.get_all('Content-Length',[]))!=1:
                        raise ValueError('Unambiguous content length required')
                    if self.headers.get('Content-Encoding','identity')!='identity':
                        raise ValueError('Encoded request bodies are not supported')
                    length = int(self.headers.get('Content-Length', 0))
                    if length <= 0 or length > (3500000 if route=='/gear/ocr' else 900000 if route=='/gear/sweep' else 300000 if route=='/gear/builds' else 250000 if route=='/market-prices' else 16384 if route=='/craft-quotes' else 4096):
                        raise ValueError('Invalid body length')
                    def reject_constant(value):raise ValueError('Finite JSON values required')
                    body = json.loads(self.rfile.read(length).decode('utf-8'),parse_constant=reject_constant)
                    if not isinstance(body,dict):raise ValueError('JSON object required')
                    if route=='/workerman':
                        if not bridge.price_book:self._send({'error':'Open the paired Windows app for Workerman modeling'},503);return
                        from workerman import reference_for,model_job
                        from cp_planner import calculate
                        provider=reference_for(str(Path(bridge.price_book.path).parent))
                        action=body.get('action')
                        if action=='reference':
                            try:reference=provider.refresh()
                            except (OSError,ValueError):self._send({'error':'Reference refresh unavailable; existing cached reference preserved'},503);return
                            self._send(reference);return
                        if action!='model':raise ValueError('Choose reference or model')
                        reference=provider.cached()
                        if not reference:raise ValueError('Load Workerman reference first')
                        job=next((j for j in reference['jobs'] if j['id']==str(body.get('node'))),None)
                        if not job:raise ValueError('Unknown Workerman node')
                        state=body.get('state');assumptions=body.get('assumptions',{})
                        if not isinstance(state,dict) or not isinstance(assumptions,dict):raise ValueError('Invalid CP / worker scenario')
                        quotes=bridge.price_book.all(body.get('region'))
                        self._send(model_job(job,calculate(state,quotes),quotes,assumptions));return
                    if route=='/cp-read':
                        if body.get('instance_id')!=bridge.instance_id:self._send({'error':'Unknown instance'},409);return
                        if bridge.ocr_paused:self._send({'error':'Lite Use stops extra OCR; disable it for a CP snapshot'},403);return
                        with bridge._lock:
                            if len(bridge.commands)>=5 or time.monotonic()-bridge.cp_request_at<15 or bridge.cp_reading.get('stage')=='waiting':
                                self._send({'error':'CP snapshot pending or cooling down; no extra read queued'},429);return
                            ident=uuid.uuid4().hex;bridge.cp_request_at=time.monotonic()
                            bridge.cp_reading={'stage':'waiting','requestId':ident,'message':'One CP snapshot queued'}
                            bridge.commands.append({'id':ident,'action':'cp-read'})
                        self._send({'accepted':True,'id':ident},202);return
                    if route=='/craft-model':
                        if body.get('instance_id')!=bridge.instance_id:self._send({'error':'Unknown instance'},409);return
                        if not bridge.price_book:self._send({'error':'Price book unavailable'},503);return
                        from craft_economy import save_model
                        model=save_model(bridge.price_book.path,body)
                        self._send({'ok':True,'model':model});return
                    if route=='/gear/builds':
                        if not bridge.price_book:self._send({'error':'Windows profile unavailable'},503);return
                        from gear_store import save
                        try:
                            with bridge.gear_store_lock:result=save(Path(bridge.price_book.path).parent,body)
                            self._send(result)
                        except OSError:self._send({'error':'Could not save Windows backup; export a JSON backup instead'},503)
                        return
                    if route in ('/gear/ocr','/gear/sweep'):
                        if bridge.ocr_paused:self._send({'error':'Lite Use is enabled; equipment OCR is paused'},403);return
                        if not bridge.price_book:self._send({'error':'Open the paired Windows app for equipment OCR'},503);return
                        if not bridge.gear_ocr_gate.acquire(blocking=False):self._send({'error':'Equipment reader is busy'},429);return
                        handed_off=False
                        try:
                            from gear_ocr import read_equipment
                            settings=Path(bridge.price_book.path).parent/'settings.json'
                            config=json.loads(settings.read_text(encoding='utf-8')) if settings.exists() else {}
                            if route=='/gear/sweep':
                                from gear_ocr import parse_equipment
                                catalog=body.get('catalog')
                                if not isinstance(catalog,list) or not catalog or len(catalog)>5000:raise ValueError('Invalid catalog')
                                parse_equipment('',catalog)
                                job={'id':uuid.uuid4().hex,'stage':'waiting','message':'Bring BDO to the front with equipment open.'}
                                with bridge._lock:bridge.gear_job=job
                                def sweep():
                                    def update(**fields):
                                        with bridge._lock:bridge.gear_job.update(fields)
                                    try:
                                        from gear_sweep import tooltip_sweep
                                        result=tooltip_sweep(catalog,config.get('tesseract',r'C:\Program Files\Tesseract-OCR\tesseract.exe'),update,bridge.gear_stop)
                                        update(stage='review' if result else 'cancelled',result=result,message='Review recognized equipment' if result else 'Import cancelled')
                                    except Exception as exc:update(stage='error',message=str(exc)[:180])
                                    finally:bridge.gear_ocr_gate.release()
                                Thread(target=sweep,name='vision-gear-import',daemon=True).start()
                                handed_off=True
                                self._send({'id':job['id'],'stage':'waiting'},202)
                                return
                            result=read_equipment(body,config.get('tesseract',r'C:\Program Files\Tesseract-OCR\tesseract.exe'))
                            self._send(result)
                        except (ValueError,TypeError,KeyError):self._send({'error':'Use a valid cropped equipment image and loaded gear catalog'},400)
                        except Exception:self._send({'error':'Equipment OCR unavailable. Check the reader in Windows settings or try a clearer tooltip capture.'},503)
                        finally:
                            if not handed_off:bridge.gear_ocr_gate.release()
                        return
                    if route in ('/craft-quotes','/craft-market'):
                        if not bridge.price_book:self._send({'error':'Price book unavailable'},503);return
                        try:
                            region=str(body['region']).upper()
                            items=bridge.price_book.recipe_market_snapshot(region) if route=='/craft-market' else bridge.price_book.recipe_id_quotes(body['ids'],region) if 'ids' in body else bridge.price_book.recipe_quotes(body['names'],region)
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
                except TimeoutError:
                    self._send({'error':'Request body timed out'},408)
                    return
                except (TypeError, ValueError, KeyError, UnicodeError, RecursionError):
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

    def send(self, current, maximum, seconds_per_craft, observed_at=None, session_id=None, source='manual',crafting_loot=None,guild_quest=None):
        if not self.server:
            raise RuntimeError(self.last_error or 'Local bridge offline')
        receipt=None
        if guild_quest is not None:
            receipt={k:guild_quest[k] for k in ('current','target','label','objective','last_at','complete','completion_at','completion_basis') if k in guild_quest}
            if len(json.dumps(receipt,allow_nan=False))>2000:raise ValueError('Guild receipt too large')
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
            if receipt is not None:self.data['guild_quest']=copy.deepcopy(receipt)
            return dict(self.data)

    def acknowledgment(self):
        with self._lock:
            return self.ack_signal, self.ack_at

    def update_tool_status(self,status):
        # Native-only, read-only diagnostics: never accept screenshots or paths.
        allowed=('stage','title','detail','tools','active_id','unreadable','last_read_at','scans','ocr_calls','cache_hits','last_seconds','revision','recent')
        value={key:status[key] for key in allowed if key in status}
        if len(json.dumps(value))>16000:raise ValueError('Tool status too large')
        with self._lock:self.tool_status=copy.deepcopy(value)

    def update_guild_status(self,status):
        allowed=('current','target','label','objective','available','last_at','percent','remaining','eta','complete','reason','enabled','threshold','completion_at','completion_seen_at','completion_basis','completion_evidence','read_stage','next_action','read_attempts','last_read_seconds','reminder')
        value={key:status[key] for key in allowed if key in status}
        if len(json.dumps(value,allow_nan=False))>4000:raise ValueError('Guild status too large')
        with self._lock:self.guild_status=copy.deepcopy(value)

    def update_companion_status(self,status):
        # Small current timer context; no images, paths, inventory or loot sharing.
        allowed=('remaining','maximum','seconds','running','has_reading','updated_at','observed_at','name','source','lite')
        value={key:status[key] for key in allowed if key in status}
        if len(json.dumps(value,allow_nan=False))>1500:raise ValueError('Companion status too large')
        with self._lock:self.companion_status=copy.deepcopy(value)

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
        self.gear_stop.set()
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
