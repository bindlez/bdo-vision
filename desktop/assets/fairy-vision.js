/* Local observation adapter. No writes to the Fairy vault or native ledger. */
(function(root){
  'use strict';
  function nameKey(value){return String(value||'').normalize('NFKC').toLowerCase().replace(/[’‘]/g,"'").replace(/\s+/g,' ').trim();}
  function matchRows(items,catalog){
    const names=new Map();
    for(const treasure of catalog||[])for(const part of treasure.parts||[]){
      const key=nameKey(part.name);if(!names.has(key))names.set(key,[]);names.get(key).push(treasure.name);
    }
    return (items||[]).filter(row=>typeof row.item==='string'&&Number.isSafeInteger(row.quantity)&&row.quantity>0)
      .map(row=>({item:row.item,quantity:row.quantity,matches:[...new Set(names.get(nameKey(row.item))||[])]}))
      .sort((a,b)=>b.matches.length-a.matches.length||b.quantity-a.quantity).slice(0,80);
  }
  function sessionReceipt(historyId,session){
    if(typeof historyId!=='string'||!historyId||historyId.length>80||!session||typeof session.id!=='string'||session.id.length>80||!session.ended_at)throw Error('Select a completed run');
    if(!Number.isFinite(session.observed_seconds)||session.observed_seconds<0)throw Error('Invalid observed time');
    const silver=session.value==null?'unpriced':Number(session.value).toLocaleString()+' gross silver'+(session.unpriced?' (partial)':'');
    return {key:historyId+':'+session.id,text:'Vision completed run: '+String(session.spot||session.label||'Unspecified spot').slice(0,100)+
      ' | observed '+Math.round(session.observed_seconds)+'s | excluded '+Math.round(session.excluded_seconds||0)+'s | '+silver+
      ' | recorded '+Number(session.units||0).toLocaleString()+' units | kills unknown; inventory ownership unchanged.'};
  }
  const api={nameKey,matchRows,sessionReceipt};
  if(typeof module!=='undefined'&&module.exports){module.exports=api;return;}
  root.VisionFairyLoot=api;
  const connect=document.getElementById('vision-connect'),state=document.getElementById('vision-loot-state'),body=document.getElementById('vision-loot-rows');
  if(!connect||!state||!body)return;
  let timer=null,busy=false,generation=0;
  let linkedLoot=null;
  function schedule(){clearTimeout(timer);timer=null;if(connect.checked&&!document.hidden)timer=setTimeout(refresh,10000);}
  async function refresh(){
    if(!connect.checked||document.hidden||busy)return;
    busy=true;const token=generation;
    try{
      const response=await fetch('/durability',{cache:'no-store',signal:AbortSignal.timeout(5000)});
      if(!response.ok)throw Error('Local bridge unavailable');
      const reading=await response.json();if(token!==generation)return;
      const loot=reading.crafting_loot;
      linkedLoot=loot||null;
      if(!loot){body.replaceChildren();state.textContent='Optional loot sharing is off. Enable it in Vision to connect this page.';return;}
      body.replaceChildren();
      const select=document.getElementById('vision-receipt'),selected=select.value;select.replaceChildren();
      const placeholder=document.createElement('option');placeholder.value='';placeholder.textContent='Select a completed run';select.append(placeholder);
      for(const run of (loot.grind?.history||[]).filter(s=>s.ended_at).slice(0,30)){
        const option=document.createElement('option');option.value=run.id;option.textContent=String(run.spot||run.label||'Run')+' · '+Math.round(run.observed_seconds)+'s observed';select.append(option);
      }
      select.value=selected;
      const rows=matchRows(loot.items,root.VisionTreasureCatalog);
      for(const row of rows){
        const tr=document.createElement('tr');
        for(const value of [row.item,row.quantity,row.matches.join(', ')||'No exact treasure match']){
          const cell=document.createElement('td');cell.textContent=String(value);cell.style.padding='8px';tr.append(cell);
        }
        if(row.matches.length)tr.style.background='#30203e';body.append(tr);
      }
      state.textContent=(loot.available?'Observing':'Paused: '+(loot.reason||'capture unavailable'))+
        ' · '+Number(loot.units||0).toLocaleString()+' recorded units · '+Number(loot.events||0).toLocaleString()+
        ' events · '+(loot.market_silver==null?'value unavailable':Number(loot.market_silver).toLocaleString()+' gross silver')+
        ' · all recorded history, not just this session · showing up to 80 items. Refreshed '+new Date().toLocaleTimeString();
    }catch(error){if(token===generation)state.textContent='Disconnected: '+error.message+'. Last displayed observations may be stale.';}
    finally{busy=false;schedule();}
  }
  connect.addEventListener('change',()=>{generation++;clearTimeout(timer);if(connect.checked)refresh();else{body.replaceChildren();state.textContent='Disconnected. Loot observation link is off.';}});
  document.getElementById('vision-refresh').addEventListener('click',refresh);
  document.getElementById('vision-import-receipt').addEventListener('click',()=>{
    const status=document.getElementById('vision-receipt-state');
    try{
      if(!connect.checked||!linkedLoot)throw Error('Connect recorded loot first');
      const run=(linkedLoot.grind?.history||[]).find(s=>s.id===document.getElementById('vision-receipt').value);
      const receipt=sessionReceipt(linkedLoot.history_id,run);
      if(confirm(receipt.text+'\n\nSave this receipt to the current Fairy journal?'))status.textContent=root.VisionImportReceipt(receipt);
    }catch(error){status.textContent=error.message;}
  });
  document.addEventListener('visibilitychange',()=>{if(document.hidden){clearTimeout(timer);generation++;}else if(connect.checked)refresh();});
})(typeof window==='undefined'?globalThis:window);
