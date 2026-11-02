/* Big Drops: render only. Uses the existing bridge update, never starts polling. */
function visionBigEscape(value){return String(value==null?'':value).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
function visionBigSilver(value){return value==null?'Unpriced':Number(value)>=1e9?(Number(value)/1e9).toFixed(2)+'B silver':Number(value)>=1e6?(Number(value)/1e6).toFixed(1)+'M silver':Number(value).toLocaleString()+' silver';}
function visionBigDropMarkup(data,selectedId){
 if(!data)return '<div class="bd-empty"><span class="bd-eyebrow">BIG DROPS / TROPHY ROOM</span><h2>Your next big moment.</h2><p>Connect optional loot sharing in Vision. Big &gt;1B per item, Huge &gt;10B, and treasure pieces regardless of price.</p></div>';
 var esc=visionBigEscape,journal=Array.isArray(data.journal)?data.journal.slice(0,40):[],event=journal.find(function(e){return e.id===selectedId;})||data.latest;
 var heat=data.heat||{},score=Math.max(0,Math.min(100,Number(heat.score)||0)),huge=event&&event.category==='Huge Drop';
 var html='<div class="bd-top"><span class="bd-eyebrow">BIG DROPS / THE TROPHY ROOM</span><span class="bd-chip">'+esc(data.lifetime_events||0)+' recorded moments</span></div>';
 html+='<div class="bd-layout"><article class="bd-hero '+(huge?'bd-huge':'')+'"><span class="bd-sigil" aria-hidden="true">✦</span><div><span class="bd-eyebrow">'+esc(event?event.category:'THE NEXT CHAPTER')+'</span><h2>'+esc(event?event.item:'Your next big moment.')+'</h2><p class="bd-value">'+esc(event?visionBigSilver(event.value):'Big >1B / Huge >10B / Treasure')+'</p><p>'+esc(event?'×'+event.quantity+' · '+event.lifetime_units+' recorded lifetime':'Only accepted recorded drops become trophies.')+'</p></div></article>';
 html+='<aside class="bd-heat '+(heat.on_fire?'bd-fire':'')+'"><span class="bd-eyebrow">CURRENT RUN / HEAT</span><h3>'+esc(heat.title||'READY FOR A SPARK')+'</h3><div class="bd-meter" role="meter" aria-label="Recorded drop heat" aria-valuemin="0" aria-valuemax="100" aria-valuenow="'+score+'"><span style="width:'+score+'%"></span></div><b>'+score+'/100</b><p class="bd-message">'+esc(heat.message)+'</p><small>'+esc(heat.basis)+'<br>'+esc(heat.note)+'</small></aside></div>';
 if(event){html+='<details class="bd-detail" open><summary>Inside this drop · '+esc(event.category)+'</summary><p>'+esc(event.detail)+'</p><div class="bd-facts"><span><b>RECORDED</b>'+esc(event.at)+'</span><span><b>TIME TO DROP</b>'+esc(event.observed_seconds==null?'Not captured for this retained drop':(event.observed_seconds/60).toFixed(1)+' observed minutes')+'</span><span><b>PRICE BASIS</b>'+esc(event.price_source)+' · item value, no tax/cost deducted</span></div></details>';}
 html+='<div class="bd-heading"><h3>Rarity shelf</h3><span>Your observed history · global odds stay unknown</span></div><div class="bd-shelf">';
 (data.comparisons||[]).slice(0,8).forEach(function(row){html+='<div class="bd-compare"><span class="bd-eyebrow">'+esc(row.category)+'</span><h4>'+esc(row.item)+'</h4><b>'+esc(row.personal_hours_per_event==null?'Building your sample':Number(row.personal_hours_per_event).toFixed(2)+' observed h / event')+'</b><small>'+esc(row.sample_events||0)+' events · '+esc(row.sample_hours||0)+' observed hours · '+esc(row.sample_runs||0)+' runs</small></div>';});
 html+='</div><details class="bd-journal"><summary>Drop journal · '+journal.length+' most recent moments</summary><div class="bd-journal-scroll">';
 journal.forEach(function(row){var id=Number.isSafeInteger(row.id)&&row.id>0?row.id:0;html+='<button type="button" class="bd-journal-row" data-big-drop="'+id+'"><span>'+esc(row.item)+' ×'+esc(row.quantity)+'<small>'+esc(row.at)+'</small></span><b>'+esc(visionBigSilver(row.value))+'</b></button>';});
 html+='</div></details><p class="bd-footnote">Big &gt;1B and Huge &gt;10B use the individual item quote, not a stack of cheap trash. Treasures bypass price thresholds. Heat uses your same-spot history after 3 runs, 2 observed hours and 5 big-drop events, or labeled burst momentum before that. These are your recorded hours across eligible spots, not global odds. '+esc(heat.footnote)+'</p>';
 return html;
}
function renderVisionBigDrops(data){
 var root=document.getElementById('visionBigDrops');if(!root)return;
 var token=JSON.stringify(data||null);if(root.dataset.readingKey===token)return;
 root.dataset.readingKey=token;root._bigDropData=data;root.innerHTML=visionBigDropMarkup(data,root._bigDropSelected);
 if(!root._bigDropBound){root._bigDropBound=true;root.addEventListener('click',function(event){var button=event.target.closest('[data-big-drop]');if(!button)return;root._bigDropSelected=Number(button.dataset.bigDrop);root.innerHTML=visionBigDropMarkup(root._bigDropData,root._bigDropSelected);});}
}
if(typeof module!=='undefined')module.exports={visionBigDropMarkup:visionBigDropMarkup};
