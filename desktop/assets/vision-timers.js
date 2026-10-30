/* Optional recorded earnings for one active timer. A craft ETA is a separate estimate. */
var visionLastTimerSave=0;
function visionEscape(value){return String(value==null?'':value).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function visionDuration(seconds){seconds=Math.floor(Math.max(0,Number(seconds)||0));return String(Math.floor(seconds/3600)).padStart(2,'0')+':'+String(Math.floor(seconds/60)%60).padStart(2,'0')+':'+String(seconds%60).padStart(2,'0');}
function visionSumItems(items){return (items||[]).reduce(function(total,item){return Number.isSafeInteger(item.unit_price)&&Number.isSafeInteger(item.quantity)?total+BigInt(item.unit_price)*BigInt(item.quantity):total;},0n);}

function attachVisionTimer(timer){
  var data=typeof visionLootLast!=='undefined'&&visionLootLast&&visionLootLast.crafting_loot;
  if(!data||!data.history_id||!data.capture_clock)return false;
  activeTimers.forEach(function(other){if(other.vision&&other.vision.tracking){other.vision.tracking=false;other.vision.status='Tracking moved to another timer';}});
  timer.vision={historyId:data.history_id,afterId:data.last_event_id||0,attachedAt:Date.now(),
    baseObserved:data.capture_clock.observed_seconds,basePaused:data.capture_clock.paused_seconds,
    observed:0,paused:0,tracking:true,status:'Waiting for the next captured drop',region:region,
    total:'0',units:0,unpriced:0,items:[],updatedAt:Date.now(),hadResult:false};
  saveState();return true;
}

async function refreshVisionTimerEarnings(base,reading){
  var data=reading&&reading.crafting_loot;
  if(!data){
    activeTimers.forEach(function(t){if(t.vision&&t.vision.tracking){t.vision.status='Optional loot sharing is off';t.vision.captureAvailable=false;}});
    return;
  }
  var owner=activeTimers.find(function(t){return t.vision&&t.vision.tracking;});
  if(!owner){owner=activeTimers.find(function(t){return t.status==='running'&&!t.vision;});if(owner)attachVisionTimer(owner);}
  if(!owner||!owner.vision)return;
  var v=owner.vision;
  if(v.historyId!==data.history_id){v.status='Different history detected · attach again to start a new measurement';return;}
  var clock=data.capture_clock||{};
  if(owner.status==='running'){
    v.observed=Math.max(0,(Number(clock.observed_seconds)||0)-v.baseObserved);
    v.paused=Math.max(0,(Number(clock.paused_seconds)||0)-v.basePaused);
  }
  v.captureAvailable=data.available===true;v.updatedAt=Date.now();
  v.status=v.captureAvailable?'Observing · new recorded drops count here':'Measurement paused · '+(data.reason||'capture unavailable');
  if(v.finalized)return;
  var url=base+'/timer-earnings?after='+encodeURIComponent(v.afterId)+'&history='+encodeURIComponent(v.historyId)+'&region='+encodeURIComponent(region)+'&since='+encodeURIComponent(v.attachedAt/1000);
  if(owner.status==='done')url+='&before='+encodeURIComponent(owner.endAt/1000);
  try{
    var response=await fetch(url,{cache:'no-store'});
    if(!response.ok)throw Error('Recorded earnings unavailable');
    var result=await response.json();
    if(result.history_id!==v.historyId)return;
    v.observed=Math.max(0,Number(result.observed_seconds)||0);v.paused=Math.max(0,Number(result.excluded_seconds)||0);
    v.items=result.items||[];v.total=visionSumItems(v.items).toString();v.units=result.units||0;
    v.unpriced=result.unpriced_types||0;v.priced=result.priced_types||0;v.events=result.event_count||0;
    v.region=region;v.hadResult=true;
    if(owner.status==='done'){v.finalized=true;v.tracking=false;v.status='Completed · recorded results';}
    if(Date.now()-visionLastTimerSave>5000||v.finalized){saveState();visionLastTimerSave=Date.now();}
  }catch(error){v.status='Earnings update paused · retained recorded results';v.captureAvailable=false;}
}

function visionTimerEarningsHTML(timer){
  var v=timer.vision;
  if(!v)return '<div class="vision-earnings optional"><span>Optional live earnings</span><p>Enable “Share recorded loot with planner” in Vision to measure drops during this timer.</p></div>';
  var stale=Date.now()-(v.updatedAt||0)>5000;
  var active=v.tracking&&v.captureAvailable&&!stale&&timer.status==='running';
  var total=BigInt(v.total||'0');
  var rate=v.observed<60?'Measuring…':v.priced||v.events===0?Math.round(Number(total)*3600/v.observed).toLocaleString():'Unpriced';
  var status=stale&&v.tracking?'Measurement paused · Vision disconnected':v.status;
  var coverage=v.observed+v.paused>0?Math.round(v.observed*100/(v.observed+v.paused)):0;
  return '<section class="vision-earnings" aria-label="Recorded earnings for this timer">'+
    '<div class="vision-earnings-head"><span class="vision-state '+(active?'observing':'paused')+'">'+visionEscape(status)+'</span><span>'+visionEscape(String(v.region||region).toUpperCase())+' market</span></div>'+
    '<div class="vision-metrics"><div><span>RECORDED ITEM VALUE</span><strong>'+(!v.hadResult?'Waiting for drops':v.events>0&&!v.priced?'Unpriced':total.toLocaleString())+'</strong><small>silver · '+(v.units||0).toLocaleString()+' captured units</small></div>'+
    '<div><span>SILVER / OBSERVED HOUR</span><strong>'+rate+'</strong><small>'+visionDuration(v.observed)+' observed · '+visionDuration(v.paused)+' excluded</small></div></div>'+
    '<div class="vision-coverage"><span style="width:'+coverage+'%"></span></div>'+
    '<p class="vision-earnings-note">'+(v.unpriced?'<b>Partial value:</b> '+v.unpriced+' unpriced item types excluded. ':'')+'Captured since this timer attached. '+coverage+'% observed coverage. Costs and fees are not deducted.</p>'+
    '<details class="vision-formula"><summary>How this is calculated</summary><p>Recorded value = Σ (new captured quantity × matching market or verified NPC unit value).</p><p>Silver/hour = recorded value ÷ observed seconds × 3,600. Rates appear after 60 observed seconds.</p><p>Blocked, minimized, stale and unreadable capture time is excluded. Readable periods with no drops still count. Missing loot is never estimated. The craft countdown remains an estimate of game progress.</p><p>Tracking attached '+new Date(v.attachedAt).toLocaleTimeString()+'. Earlier loot is excluded.</p></details></section>';
}

/* Keep focused controls, expanded formulas and scroll positions across live updates. */
function visionPatchTimers(body,markup){
  var template=document.createElement('template');template.innerHTML=markup;
  function patch(oldNode,newNode){
    if(oldNode.nodeType!==newNode.nodeType||oldNode.nodeName!==newNode.nodeName){oldNode.replaceWith(newNode.cloneNode(true));return;}
    if(oldNode.nodeType===3){if(oldNode.nodeValue!==newNode.nodeValue)oldNode.nodeValue=newNode.nodeValue;return;}
    if(oldNode.nodeType!==1)return;
    Array.from(oldNode.attributes).forEach(function(a){if(a.name!=='open'&&!newNode.hasAttribute(a.name))oldNode.removeAttribute(a.name);});
    Array.from(newNode.attributes).forEach(function(a){if(a.name!=='open'&&oldNode.getAttribute(a.name)!==a.value)oldNode.setAttribute(a.name,a.value);});
    var oldChildren=Array.from(oldNode.childNodes),newChildren=Array.from(newNode.childNodes);
    newChildren.forEach(function(child,index){if(oldChildren[index])patch(oldChildren[index],child);else oldNode.appendChild(child.cloneNode(true));});
    oldChildren.slice(newChildren.length).forEach(function(child){child.remove();});
  }
  var existing=new Map(Array.from(body.children).map(function(card){return [card.dataset.timerId,card];}));
  Array.from(template.content.children).forEach(function(card,index){
    var old=existing.get(card.dataset.timerId);
    if(old){patch(old,card);existing.delete(card.dataset.timerId);}
    else old=card.cloneNode(true);
    if(body.children[index]!==old)body.insertBefore(old,body.children[index]||null);
  });
  existing.forEach(function(card){card.remove();});
}
