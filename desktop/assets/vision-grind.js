/* One shared native grind session; this page never manufactures loot or time. */
var visionGrindReading=null,visionGrindSelected=null,visionGrindDetail=null,visionGrindPending=false,visionGrindHistoryKey='';
function visionGrindNumber(value){return value==null?'Unpriced':Math.round(value).toLocaleString();}
function renderVisionGrind(reading){
  visionGrindReading=reading;var data=reading&&reading.crafting_loot;
  var tracker=data&&data.grind;var current=tracker&&tracker.current;
  var enabled=!!tracker;document.getElementById('visionGrindConnection').textContent=enabled?'Connected to your saved Vision history':'Enable optional loot sharing in Vision to connect this tracker';
  document.querySelectorAll('[data-grind-command]').forEach(function(button){button.disabled=!enabled||visionGrindPending;});
  if(!enabled){
    document.getElementById('visionGrindState').textContent='Your local history stays in Vision. Sharing is optional.';
    ['visionGrindValue','visionGrindRate','visionGrindTime','visionGrindDrops'].forEach(function(id){document.getElementById(id).textContent='—';});
    document.getElementById('visionGrindHistory').replaceChildren();document.getElementById('visionGrindFeed').textContent='Sharing is off.';document.getElementById('visionGrindFeed').dataset.readingKey='';
    visionGrindHistoryKey='';return;
  }
  var selected=visionGrindSelected&&visionGrindDetail&&visionGrindDetail.id===visionGrindSelected?visionGrindDetail:current;
  if(current&&current.id===visionGrindSelected)selected=current;
  renderVisionGrindCards(selected,tracker.history||[]);
  var history=tracker.history||[],key=JSON.stringify(history);
  if(key!==visionGrindHistoryKey){
    visionGrindHistoryKey=key;var body=document.getElementById('visionGrindHistory');var oldRows=new Map(Array.from(body.children).filter(function(row){return row.dataset.sessionId;}).map(function(row){return [row.dataset.sessionId,row];}));Array.from(body.children).filter(function(row){return !row.dataset.sessionId;}).forEach(function(row){row.remove();});
    history.forEach(function(run,index){
      var previous=oldRows.get(run.id);
      if(previous){
        var values=[new Date(run.started_at*1000).toLocaleString(),visionDuration(run.observed_seconds),visionGrindNumber(run.value),run.silver_hour==null?'Measuring…':visionGrindNumber(run.silver_hour),Math.round(run.coverage*100)+'%',run.ended_at?'Completed':run.available?'Observing':'Paused'];
        values.forEach(function(value,n){previous.children[n+1].textContent=value;});oldRows.delete(run.id);if(body.children[index]!==previous)body.insertBefore(previous,body.children[index]||null);return;
      }
      var row=document.createElement('tr'),name=document.createElement('td'),button=document.createElement('button');row.dataset.sessionId=run.id;
      button.type='button';button.className='cat-btn';button.textContent=run.spot;button.dataset.grindSelect=run.id;button.setAttribute('aria-label','Inspect grind session '+run.spot);name.appendChild(button);row.appendChild(name);
      [new Date(run.started_at*1000).toLocaleString(),visionDuration(run.observed_seconds),visionGrindNumber(run.value),run.silver_hour==null?'Measuring…':visionGrindNumber(run.silver_hour),Math.round(run.coverage*100)+'%',run.ended_at?'Completed':run.available?'Observing':'Paused'].forEach(function(value){var cell=document.createElement('td');cell.textContent=value;row.appendChild(cell);});body.insertBefore(row,body.children[index]||null);
    });
    oldRows.forEach(function(row){row.remove();});
    if(!history.length){var empty=document.createElement('tr');var cell=document.createElement('td');cell.colSpan=7;cell.textContent='Your completed and current grinds will appear here.';empty.appendChild(cell);body.appendChild(empty);}
    var list=document.getElementById('visionGrindSpots');list.replaceChildren();
    Array.from(new Set(history.map(function(run){return run.spot;}))).forEach(function(spot){var option=document.createElement('option');option.value=spot;list.appendChild(option);});
  }
}

function renderVisionGrindCards(run,history){
  var state=document.getElementById('visionGrindState');
  if(!run){state.textContent='Start a run, give your route a name, and let captured drops build your results.';
    ['visionGrindValue','visionGrindRate'].forEach(function(id){document.getElementById(id).textContent='—';});
    document.getElementById('visionGrindTime').textContent='00:00:00';document.getElementById('visionGrindDrops').textContent='0';
    document.getElementById('visionGrindFeed').textContent='Select a saved run below, or start a new one.';
    document.getElementById('visionGrindPursuit').textContent='Choose an optional treasure pursuit for your next run.';
    document.getElementById('visionGrindGoalBar').style.width='0%';return;
  }
  state.textContent=(run.ended_at?'COMPLETED':run.available?'OBSERVING':'PAUSED')+' · '+run.spot+' · '+(run.reason||run.events+' captured events');
  state.className='vision-state '+(run.available?'observing':'paused');
  document.getElementById('visionGrindValue').textContent=visionGrindNumber(run.value);
  document.getElementById('visionGrindRate').textContent=run.silver_hour==null?'Measuring…':visionGrindNumber(run.silver_hour);
  document.getElementById('visionGrindTime').textContent=visionDuration(run.observed_seconds);
  document.getElementById('visionGrindGaps').textContent=visionDuration(run.excluded_seconds)+' excluded · '+Math.round(run.coverage*100)+'% coverage';
  document.getElementById('visionGrindDrops').textContent=Number(run.units||0).toLocaleString();
  document.getElementById('visionGrindRare').textContent=run.rare+' rare-notice units';
  document.getElementById('visionGrindPartial').textContent=run.unpriced?'Partial value · '+run.unpriced+' item types remain unpriced':'Recorded market value · no costs or fees deducted';
  var target=document.getElementById('visionGrindPursuit');target.textContent=run.target?run.target_quantity+' / '+run.goal+' '+run.target+(run.target_quantity>=run.goal?' · GOAL REACHED':' · '+run.events_since_target+' captured events since the last target'):'Choose an optional treasure pursuit for your next run.';
  document.getElementById('visionGrindGoalBar').style.width=(run.target_progress==null?0:run.target_progress*100)+'%';
  var peers=history.filter(function(other){return other.id!==run.id&&other.ended_at&&other.spot.toLowerCase()===run.spot.toLowerCase()&&other.silver_hour!=null;}).map(function(other){return other.silver_hour;}).sort(function(a,b){return a-b;});
  var benchmark=document.getElementById('visionGrindBenchmark');
  if(peers.length>=3&&run.silver_hour!=null){var middle=Math.floor(peers.length/2),median=peers.length%2?peers[middle]:(peers[middle-1]+peers[middle])/2;benchmark.textContent='Your spot signature · '+visionGrindNumber(median)+' silver/hour median · this run '+(median?((run.silver_hour/median-1)*100).toFixed(1):'0')+'% · '+peers.length+' completed runs';}
  else benchmark.textContent='Your spot signature · '+peers.length+' / 3 completed runs needed for a personal baseline. No global income assumptions.';
  var pulse=document.getElementById('visionGrindPulse'),bins=run.pulse||[],max=Math.max.apply(null,[1].concat(bins));
  if(pulse.children.length!==bins.length){pulse.replaceChildren();bins.forEach(function(){pulse.appendChild(document.createElement('span'));});}
  bins.forEach(function(value,index){pulse.children[index].style.height=Math.max(2,value/max*100)+'%';pulse.children[index].title=value+' captured units in this interval';});
  var feed=document.getElementById('visionGrindFeed'),feedKey=JSON.stringify([run.id,run.latest]);if(feed.dataset.readingKey===feedKey)return;feed.dataset.readingKey=feedKey;feed.replaceChildren();
  (run.latest||[]).forEach(function(item){var line=document.createElement('div');line.className='vision-drop';var name=document.createElement('span');name.textContent=item.item;var count=document.createElement('strong');count.textContent='× '+item.quantity.toLocaleString();var at=document.createElement('small');at.textContent=new Date(item.at).toLocaleTimeString();line.append(name,count,at);feed.appendChild(line);});
  if(!(run.latest||[]).length)feed.textContent='No captured drops in this run yet.';
}

async function visionGrindCommand(action){
  if(visionGrindPending||!bridgeSelectedOrigin||!visionGrindReading)return;
  var goal=Number(document.getElementById('visionGrindGoal').value);
  if(!Number.isInteger(goal)||goal<1||goal>1000000){document.getElementById('visionGrindCommandState').textContent='Enter a whole-number pursuit goal from 1 to 1,000,000.';return;}
  visionGrindPending=true;renderVisionGrind(visionGrindReading);
  try{
    var response=await fetch(bridgeSelectedOrigin+'/grind-command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({instance_id:visionGrindReading.instance_id,action:action,spot:document.getElementById('visionGrindSpot').value,target:document.getElementById('visionGrindTarget').value,goal:goal})});
    if(!response.ok)throw Error('Vision could not accept this command');
    visionGrindSelected=null;visionGrindDetail=null;document.getElementById('visionGrindCommandState').textContent='Accepted by Vision. The shared session state is shown below.';
  }catch(error){document.getElementById('visionGrindCommandState').textContent='Could not reach Vision. Your existing session and history are retained.';}
  finally{visionGrindPending=false;renderVisionGrind(visionGrindReading);}
}

document.getElementById('viewGrind').addEventListener('click',async function(event){
  var command=event.target.closest('[data-grind-command]');if(command){visionGrindCommand(command.dataset.grindCommand);return;}
  var selected=event.target.closest('[data-grind-select]');if(!selected||!bridgeSelectedOrigin)return;
  try{var response=await fetch(bridgeSelectedOrigin+'/grind-session?id='+encodeURIComponent(selected.dataset.grindSelect),{cache:'no-store'});if(!response.ok)throw Error('Recap unavailable');visionGrindSelected=selected.dataset.grindSelect;visionGrindDetail=await response.json();renderVisionGrind(visionGrindReading);document.getElementById('visionGrindState').scrollIntoView({block:'nearest'});}
  catch(error){document.getElementById('visionGrindCommandState').textContent='Recap is unavailable while Vision is disconnected. The run remains saved locally.';}
});

function visionGrindDisconnected(){
 document.getElementById('visionGrindConnection').textContent='Vision disconnected · saved results retained';
 document.getElementById('visionGrindState').textContent='PAUSED · waiting for your local tracker';
 document.querySelectorAll('[data-grind-command]').forEach(function(button){button.disabled=true;});
}

function visionSelectedGrind(){
 var data=visionGrindReading&&visionGrindReading.crafting_loot&&visionGrindReading.crafting_loot.grind;
 if(!data)return null;
 if(visionGrindSelected&&visionGrindDetail&&visionGrindDetail.id===visionGrindSelected)return visionGrindDetail;
 return data.current;
}
function visionDownload(blob,filename){var link=document.createElement('a'),url=URL.createObjectURL(blob);link.href=url;link.download=filename;document.body.appendChild(link);link.click();link.remove();setTimeout(function(){URL.revokeObjectURL(url);},1000);}
function visionGrindExportCSV(){
 var run=visionSelectedGrind();if(!run){document.getElementById('visionGrindCommandState').textContent='Start or select a run to export.';return;}
 function cell(value){value=String(value==null?'':value);if(/^[=+@-]/.test(value))value="'"+value;return '"'+value.replace(/"/g,'""')+'"';}
 var rows=[['Session','Observed seconds','Excluded seconds','Recorded value','Unpriced types'],[run.spot,run.observed_seconds,run.excluded_seconds,run.value,run.unpriced],[],['Item','Quantity','Unit silver','Value']];
 (run.items||[]).forEach(function(item){rows.push([item.item,item.quantity,item.unit_price,item.value]);});
 visionDownload(new Blob(['\uFEFF'+rows.map(function(row){return row.map(cell).join(',');}).join('\r\n')],{type:'text/csv;charset=utf-8'}),'BDO-Vision-run.csv');
}
function visionGrindSaveRecap(){
 var run=visionSelectedGrind();if(!run){document.getElementById('visionGrindCommandState').textContent='Start or select a run to save a recap.';return;}
 var canvas=document.createElement('canvas');canvas.width=1200;canvas.height=760;var ctx=canvas.getContext('2d');
 var gradient=ctx.createLinearGradient(0,0,1200,760);gradient.addColorStop(0,'#171021');gradient.addColorStop(1,'#080b12');ctx.fillStyle=gradient;ctx.fillRect(0,0,1200,760);
 ctx.fillStyle='#8d5ad8';ctx.fillRect(48,48,4,62);ctx.font='600 19px Segoe UI, sans-serif';ctx.fillStyle='#c1a3e3';ctx.fillText('BDO VISION / SESSION RECAP',74,72);
 ctx.font='700 36px Segoe UI, sans-serif';ctx.fillStyle='#f3eaff';var spot=run.spot;while(ctx.measureText(spot).width>980)spot=spot.slice(0,-2);if(spot!==run.spot)spot+='…';ctx.fillText(spot,74,118);
 ctx.font='16px Segoe UI, sans-serif';ctx.fillStyle='#a99bb9';ctx.fillText(new Date(run.started_at*1000).toLocaleString()+'  ·  '+(run.ended_at?'Completed run':'Run in progress'),74,150);
 var cards=[['RECORDED ITEM VALUE',visionGrindNumber(run.value)],['SILVER / OBSERVED HOUR',run.silver_hour==null?'Measuring…':visionGrindNumber(run.silver_hour)],['OBSERVED TIME',visionDuration(run.observed_seconds)],['CAPTURE COVERAGE',Math.round(run.coverage*100)+'%']];
 cards.forEach(function(card,index){var x=58+index*276;ctx.fillStyle='#21172e';ctx.fillRect(x,190,258,128);ctx.font='600 12px Segoe UI, sans-serif';ctx.fillStyle='#b4a1c6';ctx.fillText(card[0],x+18,219);ctx.font='700 27px Segoe UI, sans-serif';ctx.fillStyle='#e5ccff';ctx.fillText(card[1],x+18,269);});
 ctx.font='600 15px Segoe UI, sans-serif';ctx.fillStyle='#c4aed9';ctx.fillText('LOOT PULSE / CAPTURED UNITS',60,365);
 var bins=run.pulse||[],maximum=Math.max.apply(null,[1].concat(bins));bins.forEach(function(value,index){ctx.fillStyle='#9964dc';ctx.fillRect(60+index*45,455-65*value/maximum,36,Math.max(2,65*value/maximum));});
 ctx.font='600 18px Segoe UI, sans-serif';ctx.fillStyle='#ddc6f7';var pursuit=run.target?run.target_quantity+' / '+run.goal+' '+run.target:'Your captured results, your own baseline.';ctx.fillText(pursuit.slice(0,100),60,505);
 var items=(run.items||[]).filter(function(item){return item.value!=null;}).slice(0,3);ctx.font='16px Segoe UI, sans-serif';items.forEach(function(item,index){ctx.fillStyle='#c5b9d4';ctx.fillText(item.item.slice(0,70)+' × '+item.quantity,60,548+index*30);ctx.textAlign='right';ctx.fillStyle='#e5d2fd';ctx.fillText(visionGrindNumber(item.value),1140,548+index*30);ctx.textAlign='left';});
 ctx.fillStyle='#463252';ctx.fillRect(60,663,1080,1);ctx.font='14px Segoe UI, sans-serif';ctx.fillStyle='#a99ab9';ctx.fillText('Recorded item value before costs & fees · '+visionDuration(run.excluded_seconds)+' unobserved / paused',60,695);ctx.fillText(run.unpriced+' unpriced item types excluded · Missing loot is never estimated',60,722);
 if(document.body.dataset.visionPreview==='true'){ctx.font='600 13px Segoe UI, sans-serif';ctx.fillStyle='#d2a8ff';ctx.textAlign='right';ctx.fillText('SAMPLE DATA / PREVIEW',1140,70);ctx.textAlign='left';}
 var previous=document.getElementById('visionRecapDialog');if(previous)previous.remove();
 var dialog=document.createElement('dialog');dialog.id='visionRecapDialog';dialog.className='vision-recap-dialog';
 var heading=document.createElement('h2');heading.textContent='Your session recap';heading.tabIndex=-1;dialog.appendChild(heading);
 var preview=document.createElement('img');preview.src=canvas.toDataURL('image/png');preview.alt='Grind session recap card for '+run.spot;dialog.appendChild(preview);
 var actions=document.createElement('div');actions.className='vision-grind-actions';
 var download=document.createElement('button');download.className='btn-primary';download.textContent='Download PNG';download.onclick=function(){canvas.toBlob(function(blob){if(blob)visionDownload(blob,'BDO-Vision-recap.png');},'image/png');};
 var close=document.createElement('button');close.className='cat-btn';close.textContent='Close recap';close.onclick=function(){dialog.close();};
 actions.append(download,close);dialog.appendChild(actions);var note=document.createElement('p');note.className='vision-footnote';note.textContent='Generated locally. Nothing is uploaded or shared automatically.';dialog.appendChild(note);document.body.appendChild(dialog);dialog.showModal();heading.focus({preventScroll:true});dialog.scrollTop=0;
}
