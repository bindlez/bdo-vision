"""Deterministically embed owned CP assets and create an offline interactive demo."""
import json
from pathlib import Path

root=Path(__file__).resolve().parents[1]
assets=root/'desktop/assets'
spec=json.loads((assets/'cp-data.json').read_text(encoding='utf-8'))
css=(assets/'cp-planner.css').read_text(encoding='utf-8')
js='const VISION_CP_DATA='+json.dumps(spec,ensure_ascii=False,separators=(',',':'))+';\n'+(assets/'cp-engine.js').read_text(encoding='utf-8')+'\n'+(assets/'cp-analysis.js').read_text(encoding='utf-8')+'\n'+(assets/'cp-planner.js').read_text(encoding='utf-8')
integration="""
(function(){
 const nav=document.createElement('button');nav.className='nav-item';nav.dataset.view='cp';nav.id='navCP';nav.style.cssText='font:inherit;width:100%;text-align:left;background:none;border:0;color:inherit';nav.innerHTML='<span class="icon">◉</span> CP Intelligence';
 document.getElementById('sidebarNav').appendChild(nav);
 const view=document.createElement('section');view.id='viewCP';view.className='view';view.innerHTML='<div id="visionCP"></div>';document.getElementById('viewCraft').parentNode.appendChild(view);
 const original=showView;showView=function(name){original(name);view.classList.toggle('active',name==='cp');if(name==='cp'){document.querySelectorAll('.nav-item').forEach(n=>n.classList.toggle('active',n===nav));history.replaceState(null,'','#cp');window.VisionCPPage?.open();}};
 nav.addEventListener('click',e=>{e.stopPropagation();showView('cp');});window.addEventListener('hashchange',()=>{if(location.hash==='#cp')showView('cp');});
})();
"""
# The root must exist before the page script initializes. Open after it initializes.
script=integration+js+"\nif(location.hash==='#cp')showView('cp');\n"
block='<!-- VISION CP START -->\n<style>'+css+'</style>\n<script>'+script+'</script>\n<!-- VISION CP END -->'
target=root/'bdo-market-intelligence.html';html=target.read_text(encoding='utf-8')
start='<!-- VISION CP START -->';end='<!-- VISION CP END -->'
if start in html:
    a=html.index(start);b=html.index(end,a)+len(end);html=html[:a]+block+html[b:]
else:html=html.replace('</body>',block+'\n</body>',1)
target.write_text(html,encoding='utf-8')
demo='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>BDO Vision · CP Intelligence</title><style>body{margin:0;background:#0d0b15}'+css+'</style><div style="padding:10px 24px;background:#21192d;color:#d8c3f4;font:12px system-ui">INTERACTIVE PREVIEW · Verified exchange / CP data, example inventory. No game capture or live market connection.</div><div id="visionCP" data-demo="true"></div><script>'+js+'</script></html>'
(root/'demo/bdo-vision-cp-demo.html').write_text(demo,encoding='utf-8')
print('CP Info embedded in shipped planner; offline demo built')
