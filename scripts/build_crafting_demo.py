"""Build an offline, synthetic preview from the real planner UI. No loopback access."""
from pathlib import Path
import re,json,argparse
parser=argparse.ArgumentParser();parser.add_argument("--cooking",action="store_true");parser.add_argument("--weight",action="store_true");args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
html=(root/'bdo-market-intelligence.html').read_text(encoding='utf-8')
html=html.replace('<head>',"<head><meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob:; connect-src 'none'; font-src 'none'; worker-src 'none'\">",1)
html=html.replace('<title>Black Desert Online · Central Market</title>','<title>BDO Vision · Crafting Studio demo</title>')
html=html.replace('"bdo_cm_v1"','"vision_demo_craft_state_v1"').replace('"bdo_cm_intel_v1"','"vision_demo_craft_intel_v1"').replace('vision.craft.studio.v1','vision.demo.craft.studio.v1')
html=html.replace('    loadState();','    /* Demo starts a fresh synthetic timer on each visit. */').replace('requestNotifyPermission();','/* Demo notifications disabled. */')
html=html.replace('setInterval(shareMarketPricesWithDesktop,5000);','/* Demo has no native market bridge. */')
html=html.replace('<body>','''<body><div class="demo-ribbon"><strong>CRAFTING STUDIO DEMO</strong><span>Dated NA market snapshot & simulated drops · no game OCR</span><button id="demoPlay">Play sample drops</button><button id="demoBlock">Block sample capture</button><span id="demoState" role="status">Ready</span><a href="https://github.com/bindlez/bdo-vision/releases">Get Windows app</a></div>''')
html=html.replace('</style>','''.demo-ribbon{position:sticky;top:0;z-index:9999;display:flex;gap:12px;flex-wrap:wrap;align-items:center;background:#30203e;padding:12px 20px;color:#f7eaff;font:12px "Segoe UI",sans-serif;border-bottom:1px solid #806092}.demo-ribbon button,.demo-ribbon a{background:#18101f;color:#f0dfff;border:1px solid #8865aa;border-radius:6px;padding:7px 10px;font:inherit;text-decoration:none}.demo-ribbon>span{color:#dac5e9}.demo-ribbon strong{letter-spacing:.1em}.sidebar{padding-top:75px} .topbar{top:65px}
  </style>''',1)
recipe=next(r['id'] for r in json.loads((root/'desktop/assets/recipes.json').read_text(encoding='utf-8')) if r['name']==('Nurungji' if args.weight else 'Organic Feed' if args.cooking else 'Elixir of Demihuman Hunt'))
snapshot=json.loads((root/'desktop/assets/demo-market-snapshot.json').read_text(encoding='utf-8'))
boot=r'''
/* Demo adapter. Everything below is generated sample data, separate from live OCR. */
var demoCraft={running:false,blocked:false,events:[],observed:0,paused:0,last:Date.now(),count:0};
var demoQuotes=DEMO_MARKET_SNAPSHOT;
demoQuotes.sort((a,b)=>({678:0,679:1,9733:2}[a.id]??3)-({678:0,679:1,9733:2}[b.id]??3));
shareMarketPricesWithDesktop=async function(){desktopMarketBatch=[];};
ensureOcrWorker=async function(){throw Error('Live game OCR requires the Windows app. This demo uses simulated drops.');};
visionGrindCommand=async function(){toast('Crafting preview','Use the separate loot and grind demo to try a sample grind.',false);};
craftStudioLoadMarket=async function(){var e=document.getElementById('recipeMarketStatus');if(e)e.textContent='Offline snapshot already loaded. The Windows planner can fetch current recipe prices and volumes.';};
craftStudioLoadPrices=async function(){var e=document.getElementById('studioMarketState');if(e)e.textContent='DEMO · fixed example prices. The Windows app fetches actual market quotes.';};
loadData=async function(){rememberPrices(demoQuotes.map(function(q){return {...q,marketRegion:region};}));currentItems=demoQuotes.map(function(q){return {...q,stock:100,trades:1000};});renderListings();setStatus('ok','Demo example prices');};
loadCategory=async function(){return demoQuotes;};loadHot=async function(){return demoQuotes;};
function demoItemRows(events){var groups=new Map();events.forEach(function(e){var row=groups.get(e.item)||{item:e.item,quantity:0,unit_price:e.price,group:e.item.includes('Elixir')?'Elixirs':'Extras / other loot',market_region:region,rare:0};row.quantity+=e.quantity;if(e.rare)row.rare+=e.quantity;groups.set(e.item,row);});return [...groups.values()];}
refreshVisionTimerEarnings=async function(base,reading){
 var data=reading.crafting_loot,owner=activeTimers.find(function(t){return t.vision&&t.vision.tracking;});if(!owner){owner=activeTimers.find(function(t){return t.status==='running'&&!t.vision;});if(owner)attachVisionTimer(owner);}if(!owner||!owner.vision)return;
 var v=owner.vision,events=demoCraft.events.filter(function(e){return e.id>v.afterId&&(!v.finalized)&&(owner.status!=='done'||e.at<=owner.endAt);});if(v.finalized)return;
 v.items=demoItemRows(events);v.total=visionSumItems(v.items).toString();v.units=events.reduce(function(s,e){return s+e.quantity;},0);v.events=events.length;v.priced=v.items.length;v.unpriced=0;v.hadResult=true;v.region=region;v.updatedAt=Date.now();v.observed=Math.max(0,demoCraft.observed-v.baseObserved);v.paused=Math.max(0,demoCraft.paused-v.basePaused);v.captureAvailable=data.available;v.status=data.available?'DEMO · observing sample drops':'DEMO · '+data.reason;
 v.points=v.points||[];var point=[Date.now(),Number(v.total)];if(!v.points.length||v.points[v.points.length-1][1]!==point[1]){v.points.push(point);v.points=VisionCraft.series(v.points,48);}
 if(owner.status==='done'){v.finalized=true;v.tracking=false;var receipt=craftHistory.find(function(h){return h.timerId===owner.id;});if(receipt)receipt.earnings=craftStudioReceipt(owner);renderHistory();}saveState();
};
pollBridge=async function(){
 var d=demoCraft,now=Date.now(),dt=Math.min(5,(now-d.last)/1000);d.last=now;if(d.running){if(d.blocked)d.paused+=dt;else{d.observed+=dt;d.count++;var q=demoQuotes[d.count%4===0?1:0];d.events.push({id:d.events.length+1,at:now,item:q.name,price:q.price,quantity:d.count%4===0?1:4,rare:d.count%4===0});if(d.count%9===0)d.events.push({id:d.events.length+1,at:now,item:'Shining Powder',price:demoQuotes.find(q=>q.id===9733).price,quantity:1});}if(d.count>=160)d.running=false;}
 var items=demoItemRows(d.events),data={history_id:'synthetic-crafting-demo',last_event_id:d.events.length,crafting_mode:true,available:d.running&&!d.blocked,reason:d.blocked?'Item area is covered by demo window':d.running?'':'Sample playback paused',updated_at:now/1000,capture_clock:{observed_seconds:d.observed,paused_seconds:d.paused},items:items,captured_items_available:items.length>0,elixir_units:items.filter(function(i){return i.group==='Elixirs';}).reduce(function(s,i){return s+i.quantity;},0),extra_units:items.filter(function(i){return i.group!=='Elixirs';}).reduce(function(s,i){return s+i.quantity;},0),rare_units:items.reduce(function(s,i){return s+i.rare;},0)};

 if(d.count>=2){var detectedRecipe=RECIPES.find(r=>r.itemId===678),plan=VisionCraft.plan(detectedRecipe,1,{yield:2.5,seconds:5,retention:84.5},{...craftStudioContext(),make:{},inventory:{}}),perBatch=plan.revenue;
 var captured=items.reduce((sum,i)=>sum+i.quantity*i.unit_price,0),units=items.reduce((sum,i)=>sum+i.quantity,0);
 data.auto_craft={detected:true,recipe:detectedRecipe.name,kind:'alchemy',status:'DEMO · '+(data.available?'observing synthetic craft outputs':'capture paused'),recordedValue:captured,recordedPerHour:d.observed>=60?captured*3600/d.observed:null,units:units,nextGoal:Math.ceil((units+1)/100)*100,unpriced:[],scannedActions:1000,remainingValue:perBatch==null?null:Math.max(0,1000-(d.observed+d.paused)/5)*perBatch,model:{perHour:perBatch==null?null:perBatch*720,toolValue:perBatch==null?null:perBatch*1000,mastery:0,retention:84.5,netPerHourLow:plan.perHour,netPerHourHigh:plan.perHour},items:items.map(i=>({item:i.item,value:i.quantity*i.unit_price})),points:[[0,0],[d.observed,captured]]};}
 bridgeWasConnected=true;bridgeStatus(true,'Synthetic demo · no native connection');document.getElementById('demoState').textContent=d.running?(d.blocked?'Capture blocked · projection only':'Playing sample drops'):'Ready / paused';document.getElementById('demoPlay').textContent=d.running?'Pause sample drops':'Play sample drops';
 renderVisionCraftingLoot({crafting_loot:data});await refreshVisionTimerEarnings('',{crafting_loot:data});if(currentView==='craft')renderActiveTimers();
};
document.getElementById('demoPlay').onclick=function(){demoCraft.running=!demoCraft.running;pollBridge();};
document.getElementById('demoBlock').onclick=function(){demoCraft.blocked=!demoCraft.blocked;this.textContent=demoCraft.blocked?'Restore sample capture':'Block sample capture';pollBridge();};
rememberPrices(demoQuotes);selectedRecipe=RECIPES.find(function(r){return r.id===DEMO_RECIPE;});lastCraftAmount=100;
recipeTab=selectedRecipe.type;
if(selectedRecipe.type==='alchemy'&&!craftStudioState.config[selectedRecipe.id])craftStudioState.config[selectedRecipe.id]={yield:2.5,seconds:5,retention:84.5,extra:0,goal:1000000,estimate:true};
showView('craft');if(selectedRecipe.type==='cooking'){craftStudioChainRoute(selectedRecipe,true);craftStudioRender(selectedRecipe,lastCraftAmount);}
'''.replace('DEMO_RECIPE',json.dumps(recipe)).replace('DEMO_MARKET_SNAPSHOT',json.dumps(snapshot['items'],separators=(',',':')))
if args.weight:
    # Separate preview settings; never seed a real character's weight profile.
    html=html.replace('vision_demo_craft_state_v1','vision_demo_weight_state_v1').replace('vision_demo_craft_intel_v1','vision_demo_weight_intel_v1').replace('vision.demo.craft.studio.v1','vision.demo.weight.studio.v1')
    html=html.replace('CRAFTING STUDIO DEMO','WEIGHT & PRODUCTION DEMO').replace('Dated NA market snapshot & simulated drops · no game OCR','Example 2,700 LT character · editable sample values · no game OCR')
    boot=boot.replace("showView('craft');", "craftStudioState.carry={maximum:2700,current:0,reserve:25,mode:'expected',roundTo:100,bag:{},at:Date.now()};\nshowView('craft');")
    boot+="\ndocument.querySelector('[data-section=\"carry\"]').scrollIntoView({block:'start'});\n"
marker='    processTimers();ensureTick();updateNavBadge();'
assert marker in html;html=html.replace(marker,boot+'\n'+marker,1)
target=root/'demo'/('bdo-vision-weight-demo.html' if args.weight else 'bdo-vision-cooking-demo.html' if args.cooking else 'bdo-vision-crafting-demo.html');target.write_text(html,encoding='utf-8');print(target.name,target.stat().st_size,'bytes')
