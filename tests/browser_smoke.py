"""Run full inline planner JS in Chromium with a localhost HTTP proxy.

The CI container blocks Chrome network navigation. Serve the actual HTML into
Chromium with set_content and proxy the JS fetch back to the real Python server.
This exercises the actual bridge protocol and planner state without faking its JS.
"""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'desktop'))
from planner_bridge import PlannerBridge

html=ROOT/'bdo-market-intelligence.html'
bridge=PlannerBridge(html,ports=(7283,))
assert bridge.server


def bridge_http(url,method,body):
    if not url.startswith(bridge.base_url+'/'):
        raise ValueError('Unknown local address')
    req=urllib.request.Request(url=url,data=body.encode() if body else None,method=method,
                               headers={'Content-Type':'application/json'} if body else {})
    with urllib.request.urlopen(req,timeout=3) as r:
        return json.loads(r.read())


try:
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page()
        errors=[]
        page.on('pageerror',lambda err:errors.append(str(err)))
        page.expose_function('__bridgeRequest',bridge_http)
        source=html.read_text()
        source=re.sub(r'<script\s+[^>]*src=[^>]*>\s*</script>','',source)
        source=re.sub(r'<link[^>]*https://[^>]*>', '', source)
        shim='''<script>
            window.fetch=async function(url,opts){
              var str=String(url);
              if(str.includes('127.0.0.1:')) {
                try {
                  var data=await window.__bridgeRequest(str,(opts&&opts.method)||'GET',(opts&&opts.body)||'');
                  return new Response(JSON.stringify(data),{status:200,headers:{'Content-Type':'application/json'}});
                }catch(e){throw new TypeError('Proxy: '+e);}
              }
              return new Response('[]',{status:200,headers:{'Content-Type':'application/json'}});
            };
         </script>'''
        source=source.replace('<head>','<head>'+shim,1)
        page.set_content(source,wait_until='domcontentloaded',timeout=15000)
        page.wait_for_timeout(500)
        # Verify JS was initialized rather than merely finding static markup.
        page.evaluate('() => showView("craft")')
        print('planner rendered',page.title())
        reading=bridge.send(350,3000,1,observed_at=time.time()-3,session_id='toolA',source='ocr')
        for i in range(12):
            page.wait_for_timeout(450)
            if bridge.acknowledgment()[0]>=reading['signal']:break
        assert bridge.acknowledgment()[0]>=reading['signal'],f'No acknowledgment. JS errors: {errors}'
        state=page.evaluate('''() => ({pill:document.querySelector('#bridgePill').textContent,
             timers:activeTimers.filter(t=>t.recipeId==='durability_timer').map(t=>({amount:t.amount,endAt:t.endAt,bridgeSessionId:t.bridgeSessionId}))})''')
        print('initial signal:',state)
        assert len(state['timers'])==1 and state['timers'][0]['amount']==350
        assert abs(state['timers'][0]['endAt']-(reading['observed_at']+350)*1000)<40
        # Automatic readings must not pull the user out of the Market view.
        page.evaluate('() => showView("market")')
        second=bridge.send(340,3000,1,observed_at=time.time()-1,session_id='toolA',source='ocr')
        for i in range(12):
            page.wait_for_timeout(450)
            if bridge.acknowledgment()[0]>=second['signal']:break
        timers=page.evaluate("() => activeTimers.filter(t=>t.recipeId==='durability_timer').map(t=>t.amount)")
        assert page.evaluate('() => currentView') == 'market', 'Background OCR switched tabs'
        print('followup signal:',timers)
        assert timers==[340],timers
        third=bridge.send(3000,3000,1,observed_at=time.time(),session_id='toolB',source='ocr')
        for i in range(12):
            page.wait_for_timeout(450)
            if bridge.acknowledgment()[0]>=third['signal']:break
        timers=page.evaluate("() => activeTimers.filter(t=>t.recipeId==='durability_timer').map(t=>({amount:t.amount,session:t.bridgeSessionId}))")
        print('new tool signal:',timers)
        assert len(timers)==1 and timers[0]['amount']==3000 and timers[0]['session']=='toolB'
        print('page errors:',errors)
        assert not errors,errors
        browser.close()
finally:
    bridge.close()
