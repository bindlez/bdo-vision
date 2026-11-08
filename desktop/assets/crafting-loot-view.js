/* Optional recorded output. Prices are joined by market ID or exact item name. */
var visionLootLast=null,visionMarketById={},visionMarketByName={},visionMarketQuoteDetails={},visionMarketGeneration=0,visionLootTableKey=null;
function visionName(name){return String(name||'').normalize('NFKC').toLowerCase().replace(/[^\p{L}\p{N}]+/gu,' ').trim();}
function visionRememberMarketQuotes(list){
  visionMarketGeneration++;
  list.forEach(function(item){
    var key=String(item.marketRegion||region).toLowerCase()+':';
    if(Number.isSafeInteger(Number(item.price)) && Number(item.price)>0){
      if(item.id){visionMarketById[key+String(item.id)]=Number(item.price);visionMarketQuoteDetails[key+String(item.id)]={...item,updatedAt:item.updated_at||item.updatedAt||new Date().toISOString()};}
      visionMarketByName[key+visionName(item.name)]=Number(item.price);
    }
  });
  if(visionLootLast)renderVisionCraftingLoot(visionLootLast);
  if(window.VisionCPPage)for(var quoteRegion of new Set(list.map(i=>String(i.marketRegion||region).toUpperCase())))window.VisionCPPage.acceptQuotes(list.filter(i=>String(i.marketRegion||region).toUpperCase()===quoteRegion),quoteRegion);
}
function renderVisionCraftingLoot(reading){
  renderVisionCraftingStatus(reading);
  visionCraftPanelReply(reading);
  var panel=document.getElementById('visionCraftingLoot');
  var data=reading && reading.crafting_loot;
  if(!data){panel.hidden=true;visionLootLast=null;return;}
  visionLootLast=reading;panel.hidden=false;
  var auto=data.auto_craft,t=reading.companion;
  if(auto?.model&&auto.toolSession&&auto.toolSession===t?.session_id&&t.running&&Date.now()/1000-t.updated_at<=6&&Number.isFinite(t.remaining))auto={...auto,remainingValue:auto.model.perBatch*t.remaining};
  renderVisionAutomaticCraft(panel,auto,reading);
  var age=data.updated_at?Math.max(0,Date.now()/1000-Number(data.updated_at)):Infinity;
  var stamp=data.updated_at?new Date(Number(data.updated_at)*1000).toLocaleTimeString():'no reading yet';
  document.getElementById('visionLootState').textContent=data.available===true && age<=15?'Observed '+stamp:'Unavailable now · '+(data.reason||'reading is no longer current')+' · last observation '+stamp;
  document.getElementById('visionLootCounts').textContent=data.captured_items_available===true?(Number(data.elixir_units)||0).toLocaleString()+' recorded elixirs / draughts · '+(Number(data.extra_units)||0).toLocaleString()+' extra / other units · '+(Number(data.rare_units)||0).toLocaleString()+' rare-notice units':'No recorded loot totals available';
  var body=document.getElementById('visionLootItems');
  var tableKey=JSON.stringify([region,data.items,visionMarketGeneration]),rebuild=tableKey!==visionLootTableKey;
  if(rebuild){body.replaceChildren();visionLootTableKey=tableKey;}
  var total=0n,priced=0,unpriced=0,key=String(region).toLowerCase()+':';
  (Array.isArray(data.items)?data.items:[]).slice(0,300).forEach(function(item){
    var quantity=Number(item.quantity),unit=visionMarketById[key+String(item.market_id)]||visionMarketByName[key+visionName(item.item)];
    if(unit==null && item.market_region && String(item.market_region).toLowerCase()===String(region).toLowerCase())unit=item.unit_price;
    var known=Number.isSafeInteger(unit) && unit>=0 && Number.isSafeInteger(quantity) && quantity>=0;
    var value=known?BigInt(unit)*BigInt(quantity):null;
    if(known){total+=value;priced++;}else unpriced++;
    if(!rebuild)return;
    var row=document.createElement('tr');var nameCell=document.createElement('td');
    var recipe=RECIPES.find(function(recipe){return visionName(recipe.name)===visionName(item.item);});
    if(recipe){var button=document.createElement('button');button.type='button';button.className='cat-btn';button.textContent=String(item.item);button.setAttribute('aria-label','Open existing recipe for '+item.item);button.onclick=function(){selectRecipe(recipe.id);document.getElementById('craftDetail').scrollIntoView({block:'start'});};nameCell.appendChild(button);}
    else nameCell.textContent=String(item.item||'');
    if(item.market_id){var code=document.createElement('small');code.textContent=' · #'+item.market_id;nameCell.appendChild(code);}row.appendChild(nameCell);
    [Number.isSafeInteger(quantity)?quantity.toLocaleString():'—',known?unit.toLocaleString():'Unpriced',known?value.toLocaleString():'—',String(item.group||'')+(item.price_basis==='npc_vendor'?' · NPC vendor':'')].forEach(function(text){var cell=document.createElement('td');cell.textContent=text;row.appendChild(cell);});body.appendChild(row);
  });
  document.getElementById('visionLootSilver').textContent=priced?total.toLocaleString()+' silver of recorded item value':'Waiting for matched market prices';
  document.getElementById('visionLootCoverage').textContent=unpriced?'Partial total: '+unpriced+' unmatched / unpriced item types excluded.':'Quantity × market or verified NPC sell value. No costs or fees deducted.';
}
function renderVisionAutomaticCraft(panel,data,reading){
 var card=document.getElementById('visionAutomaticCraft');
 if(!data||!data.detected){if(card)card.hidden=true;return;}
 if(!card){card=document.createElement('section');card.id='visionAutomaticCraft';card.className='workshop-next';card.innerHTML='<small>CURRENT CRAFT · AUTOMATIC</small><h3 data-auto-title></h3><p data-auto-state role="status"></p><div class="craft-auto-essential"><div><small>TOOL / TIME LEFT</small><strong data-auto-end></strong></div><div><small>GUILD QUEST / LAST SEEN</small><strong data-auto-guild></strong></div></div><div class="studio-kpis"><div><small>Captured item value / observed hour</small><strong data-auto-rate></strong></div><div><small>Projected main + rare value / hour</small><strong data-auto-model></strong></div><div><small>Projected scanned-tool value</small><strong data-auto-tool></strong></div></div><p data-auto-note></p><button class="btn-secondary" data-auto-map title="Uses the last inferred product family; review recipe variants and substitutions in the map.">Open detected product’s production map</button><details><summary>Craft graphs & forecast details</summary><div data-auto-graphs></div><p data-auto-details></p></details>';panel.prepend(card);}
 card.hidden=!data||!data.detected;if(card.hidden)return;
 var num=n=>typeof n==='number'&&Number.isFinite(n)?Math.round(n).toLocaleString():'Unavailable',m=data.model;
 card.querySelector('[data-auto-title]').textContent=data.recipe+' · '+data.kind;
 card.querySelector('[data-auto-state]').textContent=data.status;
 var context=visionCraftStatusModel(reading||{});
 card.querySelector('[data-auto-end]').textContent=context.timer===null?context.tool:Math.floor(context.timer/3600)+':'+String(Math.floor(context.timer/60)%60).padStart(2,'0')+':'+String(context.timer%60).padStart(2,'0')+' / '+context.tool;
 card.querySelector('[data-auto-guild]').textContent=context.guild;

 card.querySelector('[data-auto-rate]').textContent=data.recordedPerHour==null?'Measuring / unpriced':num(data.recordedPerHour);
 card.querySelector('[data-auto-model]').textContent=num(m?.perHour);card.querySelector('[data-auto-tool]').textContent=num(m?.toolValue);
 card.querySelector('[data-auto-note]').textContent=num(data.recordedValue)+' captured silver value · '+num(data.units)+' units · '+num(data.remainingValue)+' remaining estimate · next milestone '+num(data.nextGoal)+(data.unpriced?.length?' · partial value: '+data.unpriced.length+' unpriced outputs':'');
 var map=card.querySelector('[data-auto-map]');if(map){var candidates=(typeof craftRecipeIndex!=='undefined'?craftRecipeIndex.byName.get(visionName(data.recipe))||[]:RECIPES.filter(r=>visionName(r.name)===visionName(data.recipe))).filter(r=>r.type===data.kind),current=typeof selectedRecipe!=='undefined'?selectedRecipe:null,r=candidates.find(r=>r.id===current?.id)||candidates[0];map.disabled=!r;map.onclick=()=>{if(!r)return;if(typeof showView==='function')showView('craft');if(typeof craftWorkflowSet==='function')craftWorkflowSet('planner');selectRecipe(r.id);};}
 var details=card.querySelector('details');function graphs(){if(!details.open)return;card.querySelector('[data-auto-graphs]').innerHTML=craftStudioGraph((data.points||[]).filter(p=>Number.isFinite(p[1])),'Captured craft value at current prices over observed seconds')+craftStudioPie((data.items||[]).filter(p=>Number.isFinite(p.value)).map(p=>({label:p.item,value:p.value})),'Captured output value','silver');card.querySelector('[data-auto-details]').textContent='Recipe inferred from repeated output and the tracked utensil. Tool forecast assumes this recipe uses the scanned '+num(data.scannedActions)+' actions, or remaining estimated actions after a recipe change. It does not assume maximum tool capacity. Model yields, speed and sale prices are estimates. Captured rates exclude unreadable/blocked time and need 60 observed seconds. Kept byproducts are excluded; forecasts omit random alchemy extras. '+(m?'Mastery '+m.mastery+'; modeled profit/hour '+num(m.netPerHourLow)+' to '+num(m.netPerHourHigh)+' at '+m.retention+'% retention and cheapest priced ingredient substitutions; actual consumed inputs are unknown.':'Forecast is paused until a verified active tool is available.');}
 details.ontoggle=graphs;graphs();
}

/* One live context strip. Reuses /durability; never starts another poll or OCR. */
function visionCraftStatusModel(reading,now=Date.now()/1000){
 var t=reading?.companion||{},loot=reading?.crafting_loot,g=reading?.guild_status||{},auto=loot?.auto_craft;
 var fresh=Number.isFinite(t.updated_at)&&now>=t.updated_at-2&&now-t.updated_at<=6;
 var valid=fresh&&t.has_reading===true&&Number.isFinite(t.remaining)&&t.remaining>=0&&Number.isFinite(t.seconds)&&t.seconds>=.05&&t.seconds<=3600;
 var age=Number.isFinite(t.observed_at)?Math.max(0,Math.floor(now-t.observed_at)):null;
 var tool=valid?(t.running?'COUNTDOWN ESTIMATE':'PAUSED / FINISHED'):'WAITING FOR TOOL';
 var timer=valid?Math.ceil(t.remaining*t.seconds):null;
 var health=loot?.health||{};
 var guildFresh=g.available===true&&[g.completion_seen_at,g.last_at].some(at=>Number.isFinite(at)&&now>=at&&now-at<=35);
 return {tool:tool,timer:timer,toolNote:valid?String(t.name||'Craft timer')+' / '+Math.ceil(t.remaining).toLocaleString()+' uses / '+(age===null?'manual timer':'read '+age+'s ago'):'In Vision, choose Scan tool + quest with BDO visible.',
   craft:auto?.detected?String(auto.recipe):'Waiting for repeated output',craftNote:auto?.detected?String(auto.status):'Item detection uses recorded output and your utensil. Enable loot capture; no manual recipe is required.',
   loot:!loot?'LOOT SHARING OFF':loot.available?'OBSERVING':'CAPTURE PAUSED',
   lootNote:!loot?'Enable optional crafting loot sharing in Vision.':String(loot.reason||'Accepted drops only')+(health.holes?' / '+health.holes+' unreadable rows':'')+(health.uncertain?' / feed overlap lost; some rows skipped':'')+(health.unmatched?' / '+health.unmatched+' unmatched names':'')+(health.reader_seconds?' / OCR '+Number(health.reader_seconds).toFixed(2)+'s':''),
   guild:g.reminder?.message?String(g.reminder.message):g.complete?(guildFresh?'COMPLETE / ACCEPT NEXT QUEST':'Last seen complete / rescan to check next quest'):Number.isInteger(g.current)&&Number.isInteger(g.target)&&g.target>0?g.current.toLocaleString()+' / '+g.target.toLocaleString()+(guildFresh?'':' / last seen'):'Quest not verified',
   guildNote:g.reminder?.key==='unverified'?'Hidden or unreadable does not prove no quest is active.':String(g.next_action||'Scan tool + quest to keep a last-seen snapshot.'),
   warning:!valid||!loot?.available||Boolean(g.reminder),fresh:fresh};
}
function renderVisionCraftingStatus(reading){
 var host=document.getElementById('craftPlanningPanel');if(!host)return;
 var strip=document.getElementById('visionCraftStatus');
 if(!strip){strip=document.createElement('section');strip.id='visionCraftStatus';strip.className='craft-status-strip';strip.setAttribute('aria-label','Current crafting context');
  strip.innerHTML='<div class="craft-status-heading"><b>YOUR CRAFT / AT A GLANCE</b><div><button data-craft-cp class="btn-secondary">CP Info</button><button data-craft-imperial class="btn-secondary">Imperial</button><button data-craft-launcher class="btn-secondary">Open capture controls</button></div></div><div class="craft-status-grid">'+[['tool','TOOL & TIME'],['craft','DETECTED CRAFT'],['loot','LOOT CAPTURE'],['guild','GUILD QUEST']].map(([id,title])=>'<section><small>'+title+'</small><strong data-status-'+id+'></strong><p data-note-'+id+'></p></section>').join('')+'</div>';
  host.prepend(strip);
  strip.querySelector('[data-craft-cp]').onclick=()=>showView('cp');
  strip.querySelector('[data-craft-imperial]').onclick=()=>craftWorkflowSet('imperial');
 }
 var m=visionCraftStatusModel(reading),key=JSON.stringify(m);if(strip.dataset.renderKey===key)return;strip.dataset.renderKey=key;
 for(var id of ['tool','craft','loot','guild']){
  strip.querySelector('[data-status-'+id+']').textContent=id==='tool'&&m.timer!==null?Math.floor(m.timer/3600)+':'+String(Math.floor(m.timer/60)%60).padStart(2,'0')+':'+String(m.timer%60).padStart(2,'0')+' / '+m.tool:m[id];
  strip.querySelector('[data-note-'+id+']').textContent=m[id+'Note'];
 }
 var open=strip.querySelector('[data-craft-launcher]');open.disabled=!bridgeSelectedOrigin||!reading?.instance_id;
 open.onclick=async()=>{try{var result=await fetch(bridgeSelectedOrigin+'/show',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({instance_id:reading.instance_id}),signal:AbortSignal.timeout(3000)});if(!result.ok)throw Error('Launcher unavailable');}catch(e){toast('Open Vision','Use the Windows tray icon to open capture controls.',false);}};
}
function visionCraftStatusDisconnected(){
 var strip=document.getElementById('visionCraftStatus');if(!strip)return;
 delete strip.dataset.renderKey;
 strip.querySelector('[data-status-tool]').textContent='LOCAL APP DISCONNECTED';
 strip.querySelector('[data-note-tool]').textContent='Reconnect Vision. Existing planning timers keep their own estimates.';
 strip.querySelector('[data-status-loot]').textContent='UNAVAILABLE';
 strip.querySelector('[data-note-loot]').textContent='Previous loot is retained; no current capture is claimed.';
 strip.querySelector('[data-status-craft]').textContent='Last detected craft / connection lost';
 strip.querySelector('[data-status-guild]').textContent='Last seen quest / connection lost';
 strip.querySelector('[data-craft-launcher]').disabled=true;
}

var visionPanelHandled=null;
function visionCraftPanelCalculate(q){
 const r=craftRecipeIndex.byRecipe.get(q.recipe);if(!r||!['cooking','alchemy'].includes(r.type))throw Error('Choose a cooking or alchemy recipe');
 const ctx={...craftStudioContext(),inventory:{},make:{},configFor:x=>({...craftStudioConfig(x),...(x.id===r.id&&Number.isFinite(q.seconds)&&q.seconds>=.05&&q.seconds<=3600?{seconds:q.seconds}:{})})},cfg=VisionCraft.configure(r,ctx.configFor(r),VISION_CRAFT_DATA),mats=VisionCraft.resolved(r,ctx),amounts=q.amounts||{};
 const merged=new Map();for(const m of mats){const old=merged.get(m.itemId);merged.set(m.itemId,old?{...old,qty:old.qty+m.qty}:m);}const rows=[...merged.values()];
 const options={maximum:q.maximum,current:q.current,reserve:q.reserve??25,mode:'expected',bag:q.bag||{},tool:q.limit==='ingredients'?'':q.tool};
 if(q.limit!=='ingredients'&&(!Number.isSafeInteger(q.tool)||q.tool<0))throw Error('Read a tool or enter its remaining uses.');
 const capacity=VisionCraft.carry(r,options,ctx);if(!capacity.available)throw Error('Missing weight data: '+capacity.missing.join(', '));
 let count=capacity.batches,linked=null;
 if(q.anchor!=null&&!q.independent){linked=VisionCraft.ingredientRatio(r,q.anchor,amounts[q.anchor],ctx);count=linked.batches;}
 else if(q.independent){if(rows.some(m=>amounts[m.itemId]==null||amounts[m.itemId]===''||!Number.isSafeInteger(Number(amounts[m.itemId]))||Number(amounts[m.itemId])<0||Number(amounts[m.itemId])>1e12))throw Error('Enter each ingredient quantity');count=Math.min(...rows.map(m=>Math.floor(Number(amounts[m.itemId])/m.qty)));}
 if(!Number.isSafeInteger(count)||count<0||count>1e9)throw Error('Enter valid whole ingredient quantities');
 const selected=VisionCraft.carry(r,{...options,batches:count},ctx).selected,p=VisionCraft.plan(r,Math.max(1,count),cfg,ctx);
 return {recipe:r.id,name:r.name,batches:count,maxCrafts:capacity.batches,seconds:count*cfg.seconds,output:count*cfg.yield,
  gross:count?p.revenue:null,profit:count?p.profit:null,perHour:count?p.perHour:null,fits:selected.fits,peak:selected.peakWeight,
  rows:rows.map(m=>({id:m.itemId,name:m.name,ratio:m.qty,quantity:count*m.qty,leftover:q.independent?Number(amounts[m.itemId])-count*m.qty:linked&&m.itemId===Number(q.anchor)?linked.leftover:0})),
  unpriced:p.missing,note:'Model: '+cfg.mastery+' mastery / '+cfg.seconds+'s per action / '+cfg.retention+'% sale retention. Expected outputs and cached prices; input value is deducted. '+(selected.fits?'Fits the selected weight/tool model.':'Exceeds the entered weight or tool budget.')};
}
async function visionCraftPanelReply(reading){
 const q=reading?.craft_panel_request;if(!q||q.id===visionPanelHandled||!bridgeSelectedOrigin)return;visionPanelHandled=q.id;
 let result;try{result=visionCraftPanelCalculate(q);
 if(q.start===true){
  if(!Number.isFinite(q.created)||Date.now()/1000-q.created>15)throw Error('Timer request expired; click TIMER again in Vision.');
  if(!result.fits||result.batches<1)throw Error('Choose a positive load that fits weight and tool limits before starting.');
  if(!activeTimers.some(t=>t.companionRequestId===q.id)){
   const r=craftRecipeIndex.byRecipe.get(q.recipe),seconds=result.seconds/result.batches;
   if(activeTimers.some(t=>t.status==='running'&&t.recipeId===r.id)){visionRevealActiveTimer(r.id);throw Error('Existing timer opened in the website. Keep or cancel it before starting a replacement.');}
   startCraft({...r,secPerBatch:seconds},result.batches);
   const timer=activeTimers.find(t=>t.recipeId===r.id&&t.status==='running');if(timer){timer.companionRequestId=q.id;saveState();}
  }
  result.timerStarted=true;
 }
 }catch(e){result={error:String(e.message||e)};}
 async function publish(value){const response=await fetch(bridgeSelectedOrigin+'/craft-panel-result',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:q.id,instance_id:reading.instance_id,result:value}),signal:AbortSignal.timeout(3000)});if(!response.ok&&response.status!==409)visionPanelHandled=null;}
 try{await publish(result);}catch(e){visionPanelHandled=null;}
 if(result.unpriced&&typeof craftStudioLoadPrices==='function'){
  const r=craftRecipeIndex.byRecipe.get(q.recipe),ctx={...craftStudioContext(),make:{}};
  craftStudioLoadPrices(r,false,ctx).then(async quote=>{if(!quote.ok||visionPanelHandled!==q.id)return;try{const updated=visionCraftPanelCalculate(q);if(result.timerStarted)updated.timerStarted=true;await publish(updated);}catch(e){}});
 }

}

// Dedicated companion tab: event-driven requests keep hidden-tab timer throttling
// out of the native editing path. No extra capture or price-poll loop.
if(typeof window!=='undefined'&&typeof window.addEventListener==='function')window.addEventListener('load',()=>{
 if(location.hash!=='#companion'||!['127.0.0.1','localhost'].includes(location.hostname)||typeof EventSource==='undefined')return;
 bridgeSelectedOrigin=location.origin;
 const source=new EventSource('/craft-panel-events');
 source.onerror=()=>source.close();
 source.onmessage=e=>{try{visionCraftPanelReply(JSON.parse(e.data));}catch(error){}};
 window.addEventListener('pagehide',()=>source.close(),{once:true});
 if(typeof showView==='function')showView('craft');
});
